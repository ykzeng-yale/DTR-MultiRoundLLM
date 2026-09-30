"""Mock HTTP and synthetic Parquet tests; no internet or task execution."""
import copy
import io
import json
import re
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.inquire_lcb_public_frame_20260930 import (
    Budget, BudgetExceeded, DATASET, InquiryError, MAX_BYTES, MAX_REQUEST,
    PUBLIC_COLUMNS, REVISION, SHARDS, SHARD_BYTES, StrictRangeFile, URL_PREFIX,
    inventory, project_shard, run, validate_plan,
)


class Response:
    def __init__(self, body, *, status, headers):
        self.body = io.BytesIO(body)
        self.status = status
        self.headers = headers
        self.read_calls = 0
        self.closed = False

    def getcode(self):
        return self.status

    def read(self, count=-1):
        self.read_calls += 1
        return self.body.read(count)

    def close(self):
        self.closed = True


class Server:
    def __init__(self, payload, alter=None):
        self.payload = payload
        self.alter = alter
        self.requests = []
        self.responses = []

    def __call__(self, request, timeout):
        value = request.get_header('Range')
        match = re.fullmatch(r'bytes=(\d+)-(\d+)', value)
        start, end = map(int, match.groups())
        self.requests.append((start, end))
        headers = {'Content-Range': f'bytes {start}-{end}/{len(self.payload)}',
                   'Content-Length': str(end - start + 1)}
        status, body = 206, self.payload[start:end + 1]
        if self.alter is not None:
            status, headers, body = self.alter(len(self.requests), status, headers, body)
        response = Response(body, status=status, headers=headers)
        self.responses.append(response)
        return response


def payload():
    footer = b'metadata-only-footer'
    return b'PAR1' + b'PRIVATE-COLUMN-BYTES' * 20 + footer + struct.pack('<I', len(footer)) + b'PAR1'


def plan():
    return {'schema': 'lcb-public-source-inquiry-v1', 'dataset': DATASET,
            'revision': REVISION, 'url_prefix': URL_PREFIX, 'shards': list(SHARDS),
            'shard_bytes': dict(SHARD_BYTES),
            'public_columns': list(PUBLIC_COLUMNS), 'expected_declared_rows': 1055,
            'max_fetched_bytes': MAX_BYTES, 'max_request_bytes': MAX_REQUEST,
            'wall_seconds': 500, 'cpu_seconds': 500, 'cpu_count': 1,
            'runner_sha256': 'a' * 64}


class RangeTests(unittest.TestCase):
    def test_exact_metadata_only_read_seek_tell_and_cache(self):
        data = payload()
        server = Server(data)
        with tempfile.TemporaryDirectory() as parent:
            budget = Budget()
            source = StrictRangeFile('https://fake.invalid/data', budget=budget,
                                     directory=Path(parent) / 'ranges', opener=server)
            source.seek(-len(data), io.SEEK_END)
            self.assertEqual(source.tell(), 0)
            virtual = source.read(len(data))
            self.assertEqual(virtual[:4], b'PAR1')
            self.assertEqual(virtual[4:source.footer_start], b'\0' * (source.footer_start - 4))
            self.assertEqual(virtual[source.footer_start:], data[source.footer_start:])
            count = len(server.requests)
            source.seek(source.footer_start)
            buf = bytearray(source.footer_length)
            self.assertEqual(source.readinto(buf), source.footer_length)
            self.assertEqual(len(server.requests), count)
            self.assertEqual(budget.fetched, 12 + source.footer_length)
            self.assertTrue(all(r['status'] == 'VERIFIED' for r in source.receipts))
            source.close()

    def test_server_200_refused_before_any_full_body_read(self):
        server = Server(payload(), lambda n, status, headers, body: (200, headers, payload()))
        with tempfile.TemporaryDirectory() as parent:
            with self.assertRaisesRegex(InquiryError, 'HTTP206'):
                StrictRangeFile('https://fake.invalid/data', budget=Budget(),
                                directory=Path(parent) / 'ranges', opener=server)
            self.assertEqual(server.responses[0].read_calls, 0)
            self.assertTrue(server.responses[0].closed)
            receipt = json.loads((Path(parent) / 'ranges' / 'requests.jsonl').read_text())
            self.assertEqual(receipt['fetched_bytes'], 0)

    def test_wrong_bounds_unknown_total_and_encoding_are_refused(self):
        for bad in ('bytes 1-4/1000', 'bytes 0-3/*', 'bytes 0-3/3'):
            def alter(n, status, headers, body, value=bad):
                headers['Content-Range'] = value
                return status, headers, body
            with self.subTest(content_range=bad), tempfile.TemporaryDirectory() as parent:
                server = Server(payload(), alter)
                with self.assertRaises(InquiryError):
                    StrictRangeFile('https://fake.invalid/data', budget=Budget(),
                                    directory=Path(parent) / 'ranges', opener=server)
                self.assertEqual(server.responses[0].read_calls, 0)
        def compressed(n, status, headers, body):
            headers['Content-Encoding'] = 'gzip'
            return status, headers, body
        with tempfile.TemporaryDirectory() as parent:
            with self.assertRaisesRegex(InquiryError, 'encoded'):
                StrictRangeFile('https://fake.invalid/data', budget=Budget(),
                                directory=Path(parent) / 'ranges', opener=Server(payload(), compressed))

    def test_server_total_drift_short_and_oversize_payload_fail(self):
        def drift(n, status, headers, body):
            if n == 2:
                headers['Content-Range'] = headers['Content-Range'].rsplit('/', 1)[0] + '/9999'
            return status, headers, body
        alterations = [drift, lambda n, s, h, b: (s, h, b[:-1]),
                       lambda n, s, h, b: (s, h, b + b'x')]
        for alter in alterations:
            with self.subTest(alter=alter), tempfile.TemporaryDirectory() as parent:
                with self.assertRaises(InquiryError):
                    StrictRangeFile('https://fake.invalid/data', budget=Budget(),
                                    directory=Path(parent) / 'ranges', opener=Server(payload(), alter))

    def test_first_server_total_must_match_independent_pinned_shard_length(self):
        with tempfile.TemporaryDirectory() as parent:
            server = Server(payload())
            with self.assertRaisesRegex(InquiryError, 'server total drift'):
                StrictRangeFile('https://fake.invalid/data', budget=Budget(),
                                directory=Path(parent) / 'ranges', opener=server,
                                expected_size=len(payload()) + 1)
            self.assertEqual(server.responses[0].read_calls, 0)

    def test_global_byte_time_and_perrequest_caps_fail_before_network(self):
        with tempfile.TemporaryDirectory() as parent:
            server = Server(payload())
            with self.assertRaises(BudgetExceeded):
                StrictRangeFile('https://fake.invalid/data', budget=Budget(max_bytes=4),
                                directory=Path(parent) / 'ranges', opener=server)
            self.assertFalse(server.requests)
        ticks = iter((0., 501.))
        with self.assertRaises(BudgetExceeded):
            Budget(clock=lambda: next(ticks)).check()
        with tempfile.TemporaryDirectory() as parent:
            server = Server(payload())
            with self.assertRaises(InquiryError):
                StrictRangeFile('https://fake.invalid/data', budget=Budget(),
                                directory=Path(parent) / 'ranges', opener=server, max_request=3)
            self.assertFalse(server.requests)


class PlanAndInventoryTests(unittest.TestCase):
    def test_immutable_plan_shape_projection_count_and_caps(self):
        self.assertEqual(validate_plan(plan()), plan())
        for key, value in (('revision', 'main'), ('public_columns', list(PUBLIC_COLUMNS) + ['private_test_cases']),
                           ('shards', list(SHARDS[:-1])), ('expected_declared_rows', 1), ('cpu_count', 8),
                           ('wall_seconds', 999), ('url_prefix', 'https://fake.invalid/')):
            bad = copy.deepcopy(plan())
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(InquiryError):
                validate_plan(bad)

    def test_sanitized_inventory_retains_every_id_without_public_answers_or_statements(self):
        record = {'question_title': 'DO NOT REDISTRIBUTE TITLE', 'question_content': 'DO NOT REDISTRIBUTE TASK',
                  'platform': 'atcoder', 'question_id': 'task-1', 'contest_id': 'contest',
                  'contest_date': '2024-07-01', 'starter_code': 'class Solution:\n def solve(self, n):\n  pass\n',
                  'difficulty': 'easy', 'public_test_cases': json.dumps([{'input': 'PUBLIC INPUT',
                      'output': 'PUBLIC ANSWER', 'testtype': 'functional'}])}
        report = inventory([record, copy.deepcopy(record)])
        text = json.dumps(report)
        for forbidden in ('PUBLIC ANSWER', 'PUBLIC INPUT', 'DO NOT REDISTRIBUTE TITLE', 'DO NOT REDISTRIBUTE TASK'):
            self.assertNotIn(forbidden, text)
        self.assertEqual(report['actual_rows'], 2)
        self.assertEqual(report['admitted_rows'], 0)
        self.assertEqual(report['unique_platform_question_ids'], 1)
        self.assertEqual(report['rows'][0]['public_case_structure']['count'], 1)
        self.assertEqual(report['rows'][0]['starter_interface']['classes'], ['Solution'])
        self.assertEqual(report['duplicate_content_hash_groups'], [[0, 1]])

    def test_projector_forbidden_columns_rejected_before_parquet_import_or_read(self):
        with self.assertRaisesRegex(InquiryError, 'projection'):
            project_shard(None, list(PUBLIC_COLUMNS) + ['metadata'])

    def test_runner_source_hash_and_fresh_output_gate_precede_fetch(self):
        with self.assertRaisesRegex(InquiryError, 'source hash'):
            run(plan(), 'work/never-created-unit-test-output', opener=lambda *a, **k: self.fail('network'))


class SyntheticParquetTests(unittest.TestCase):
    def test_public_projection_fetches_no_forbidden_data_intervals(self):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest('pyarrow unavailable; run with existing source_reader interpreter')
        row = {'question_title': 'title', 'question_content': 'public task', 'platform': 'codeforces',
               'question_id': '1', 'contest_id': 'c', 'contest_date': '2024-01-01',
               'starter_code': '', 'difficulty': 'easy', 'public_test_cases': '[]'}
        columns = {name: [row[name], row[name]] for name in PUBLIC_COLUMNS}
        columns['private_test_cases'] = ['NEVER DECODE PRIVATE SECRET' * 8000] * 2
        columns['metadata'] = ['NEVER DECODE METADATA SECRET'] * 2
        sink = io.BytesIO()
        pq.write_table(pa.table(columns), sink, compression='NONE', row_group_size=1, write_statistics=False)
        data = sink.getvalue()
        server = Server(data)
        with tempfile.TemporaryDirectory() as parent:
            source = StrictRangeFile('https://fake.invalid/data', budget=Budget(),
                                     directory=Path(parent) / 'ranges', opener=server)
            records, detail = project_shard(source)
            self.assertEqual(records, [row, row])
            self.assertEqual(detail['rows'], 2)
            self.assertTrue(detail['private_data_ranges'])
            for start, end in server.requests:
                for left, right in detail['private_data_ranges']:
                    self.assertFalse(start < right and left <= end,
                                     f'private data fetched by range {start}-{end}')
            source.seek(detail['private_data_ranges'][0][0])
            with self.assertRaisesRegex(InquiryError, 'private'):
                source.read(1)
            self.assertLess(source.budget.fetched, len(data) / 4)
            source.close()


if __name__ == '__main__':
    unittest.main()
