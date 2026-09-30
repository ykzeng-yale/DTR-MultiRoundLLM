#!/usr/bin/env python3
"""Bounded public-column source inquiry, not task admission or execution.

Never deserialize private_test_cases/metadata/reference columns, pickle objects,
or executable dataset/benchmark code. Parquet footer metadata is necessarily
read to locate columns; statistics for forbidden columns are never exported.
Only public column chunks are fetched. Parser footer readahead is satisfied by
an explicitly virtual metadata-only view, not by fetching adjacent data pages.
"""
import argparse
import ast
import collections
import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import struct
import sys
import time
import urllib.parse
import urllib.request

REVISION = '25d8cb8f0db2efe1b589941eb8c26a219850d4d2'
DATASET = 'livecodebench/code_generation_lite'
URL_PREFIX = f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/'
SHARDS = tuple(f'release_v6/test-{i:05d}-of-00009.parquet' for i in range(9))
SHARD_BYTES = dict(zip(SHARDS, (75385387, 353243448, 547148226, 879660215,
                              635992480, 1159591686, 514869763, 78448917, 90113345)))
PUBLIC_COLUMNS = ('question_title', 'question_content', 'platform', 'question_id',
                  'contest_id', 'contest_date', 'starter_code', 'difficulty',
                  'public_test_cases')
FORBIDDEN_COLUMNS = ('private_test_cases', 'metadata', 'reference', 'solution', 'solutions')
MAX_BYTES = 64 * 1024 * 1024
MAX_REQUEST = 8 * 1024 * 1024
MAX_SECONDS = 500


class InquiryError(ValueError):
    pass


class BudgetExceeded(InquiryError):
    pass


def hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode()


def json_value(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, list):
        return [json_value(v) for v in value]
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in value.items()}
    if value is None or type(value) in (str, int, float, bool):
        if type(value) is float and not math.isfinite(value):
            raise InquiryError('nonfinite public scalar')
        return value
    raise InquiryError('unsupported public scalar type')


def validate_plan(plan):
    fields = {'schema', 'dataset', 'revision', 'url_prefix', 'shards', 'shard_bytes', 'public_columns',
              'expected_declared_rows', 'max_fetched_bytes', 'max_request_bytes',
              'wall_seconds', 'cpu_seconds', 'cpu_count', 'runner_sha256'}
    if type(plan) is not dict or set(plan) != fields:
        raise InquiryError('exact frozen inquiry plan required')
    if (plan['schema'] != 'lcb-public-source-inquiry-v1' or plan['dataset'] != DATASET or
            plan['revision'] != REVISION or plan['url_prefix'] != URL_PREFIX or
            plan['shards'] != list(SHARDS) or plan['shard_bytes'] != SHARD_BYTES or
            plan['public_columns'] != list(PUBLIC_COLUMNS)):
        raise InquiryError('immutable source/projection/shape pin drift')
    if type(plan['shard_bytes']) is not dict or any(type(v) is not int for v in plan['shard_bytes'].values()):
        raise InquiryError('integer immutable shard lengths required')
    if (any(type(plan[k]) is not int for k in ('expected_declared_rows', 'max_fetched_bytes',
                                               'max_request_bytes', 'wall_seconds', 'cpu_seconds', 'cpu_count')) or
            plan['expected_declared_rows'] != 1055 or
            plan['max_fetched_bytes'] != MAX_BYTES or plan['max_request_bytes'] != MAX_REQUEST or
            plan['wall_seconds'] != MAX_SECONDS or plan['cpu_seconds'] != MAX_SECONDS or
            plan['cpu_count'] != 1):
        raise InquiryError('declared count or finite resource envelope drift')
    digest = plan['runner_sha256']
    if type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest):
        raise InquiryError('runner digest')
    return plan


class Budget:
    def __init__(self, *, max_bytes=MAX_BYTES, seconds=MAX_SECONDS, clock=time.monotonic):
        self.max_bytes = max_bytes
        self.seconds = seconds
        self.clock = clock
        self.started = clock()
        self.fetched = 0

    def check(self, additional=0):
        if self.clock() - self.started > self.seconds:
            raise BudgetExceeded('global wall-time cap')
        if self.fetched + additional > self.max_bytes:
            raise BudgetExceeded('global fetched-byte cap')

    def add(self, count):
        self.check(count)
        self.fetched += count


class StrictRangeFile(io.RawIOBase):
    """Seekable HTTP206-only file with audited exact range reads.

    Initial read/seek/tell exposes a metadata-only virtual file. After a footer
    has been parsed, permit_public_columns enables exact public data intervals;
    reads outside their union are refused. Cached bytes are not fetched twice.
    """
    def __init__(self, url, *, budget, directory, opener=urllib.request.urlopen,
                 max_request=MAX_REQUEST, expected_size=None):
        super().__init__()
        self.url = url
        self.budget = budget
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.opener = opener
        self.max_request = max_request
        self.position = 0
        self.size = None
        self.expected_size = expected_size
        if expected_size is not None and (type(expected_size) is not int or expected_size < 12):
            raise InquiryError('pinned server total size')
        self.cache = []
        self.receipts = []
        self.allowed = []
        self.metadata_only = True
        self.ledger = (self.directory / 'requests.jsonl').open('xb')
        header = self._fetch(0, 3)
        if header != b'PAR1' or self.size < 12:
            raise InquiryError('Parquet header/size')
        trailer = self._fetch(self.size - 8, self.size - 1)
        if trailer[4:] != b'PAR1':
            raise InquiryError('Parquet trailer')
        self.footer_length = struct.unpack('<I', trailer[:4])[0]
        self.footer_start = self.size - 8 - self.footer_length
        if self.footer_start < 4 or self.footer_length == 0:
            raise InquiryError('invalid Parquet footer length')
        footer = self._fetch_chunks(self.footer_start, self.size - 9)
        self.footer_sha256 = hash_bytes(footer)
        self.allowed = [(0, 4), (self.footer_start, self.size)]

    def _fetch(self, start, end):
        length = end - start + 1
        if type(start) is not int or type(end) is not int or start < 0 or length < 1 or length > self.max_request:
            raise InquiryError('bounded exact range required')
        # Reserve the single-byte oversize probe too; failure never knowingly
        # consumes more than the global fetched-body allowance.
        self.budget.check(length + 1)
        request = urllib.request.Request(self.url,
            headers={'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'})
        receipt = {'request': len(self.receipts), 'url': self.url, 'start': start,
                   'end_inclusive': end, 'requested_bytes': length, 'fetched_bytes': 0,
                   'status': 'FAILED', 'payload_sha256': None}
        body = bytearray()
        error = None
        response = None
        try:
            timeout = min(20., max(.01, self.budget.seconds - (self.budget.clock() - self.budget.started)))
            response = self.opener(request, timeout=timeout)
            if response.getcode() != 206:
                raise InquiryError('server did not honor HTTP206; full-body read refused')
            cr = response.headers.get('Content-Range')
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', cr or '')
            if not match:
                raise InquiryError('exact Content-Range required')
            actual_start, actual_end, total = map(int, match.groups())
            if (actual_start != start or actual_end != end or total <= end or
                    (self.size is not None and total != self.size) or
                    (self.expected_size is not None and total != self.expected_size)):
                raise InquiryError('Content-Range bounds/server total drift')
            receipt['server_total_bytes'] = total
            encoding = response.headers.get('Content-Encoding')
            if encoding not in (None, '', 'identity'):
                raise InquiryError('encoded range body refused')
            declared_length = response.headers.get('Content-Length')
            if declared_length is not None and declared_length != str(length):
                raise InquiryError('Content-Length mismatch')
            while len(body) < length:
                self.budget.check()
                chunk = response.read(min(65536, length - len(body)))
                if not chunk:
                    raise InquiryError('short range body')
                self.budget.add(len(chunk))
                body.extend(chunk)
            extra = response.read(1)
            if extra:
                self.budget.add(len(extra))
                body.extend(extra)
                raise InquiryError('oversize range body')
            self.size = total
            receipt['status'] = 'VERIFIED'
        except Exception as exc:
            error = exc
            receipt['error_type'] = type(exc).__name__
            # Network/parser error messages can contain remote text; never echo it.
        finally:
            if response is not None:
                response.close()
            receipt['fetched_bytes'] = len(body)
            if body:
                name = f'range-{receipt["request"]:05d}.bin'
                (self.directory / name).write_bytes(body)
                receipt['payload_path'] = name
                receipt['payload_sha256'] = hash_bytes(body)
            self.receipts.append(receipt)
            self.ledger.write(json_bytes(receipt) + b'\n')
            self.ledger.flush()
        if error is not None:
            raise error
        data = bytes(body)
        self.cache.append((start, end + 1, data))
        return data

    def _fetch_chunks(self, start, end):
        parts = []
        while start <= end:
            stop = min(end, start + self.max_request - 1)
            parts.append(self._fetch(start, stop))
            start = stop + 1
        return b''.join(parts)

    def _interval(self, start, end):
        """Serve cached intersections and fetch only uncovered exact bytes."""
        result = bytearray()
        cursor = start
        for left, right, data in sorted(self.cache):
            if right <= cursor or left >= end:
                continue
            if left > cursor:
                result.extend(self._fetch_chunks(cursor, left - 1))
                cursor = left
            stop = min(end, right)
            if stop > cursor:
                result.extend(data[cursor - left:stop - left])
                cursor = stop
        if cursor < end:
            result.extend(self._fetch_chunks(cursor, end - 1))
        return bytes(result)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        if type(offset) is not int or whence not in (io.SEEK_SET, io.SEEK_CUR, io.SEEK_END):
            raise InquiryError('seek')
        target = offset + (0 if whence == io.SEEK_SET else self.position if whence == io.SEEK_CUR else self.size)
        if target < 0:
            raise InquiryError('negative seek')
        self.position = target
        return target

    def read(self, size=-1):
        self.budget.check()
        if type(size) is not int:
            raise InquiryError('read size')
        start = min(self.position, self.size)
        end = self.size if size < 0 else min(self.size, start + size)
        if end <= start:
            return b''
        if end - start > MAX_BYTES or (self.metadata_only and end - start > MAX_REQUEST):
            raise InquiryError('logical read allocation cap')
        pieces = []
        cursor = start
        for left, right in self.allowed:
            left, right = max(left, start), min(right, end)
            if left >= right:
                continue
            if left > cursor:
                if not self.metadata_only:
                    raise InquiryError('read touches unapproved/private column interval')
                pieces.append(b'\0' * (left - cursor))
            pieces.append(self._interval(left, right))
            cursor = right
        if cursor < end:
            if not self.metadata_only:
                raise InquiryError('read touches unapproved/private column interval')
            pieces.append(b'\0' * (end - cursor))
        self.position += end - start
        return b''.join(pieces)

    def readinto(self, target):
        data = self.read(len(target))
        target[:len(data)] = data
        return len(data)

    def permit_public_columns(self, metadata, columns=PUBLIC_COLUMNS):
        if tuple(columns) != PUBLIC_COLUMNS or set(columns) & set(FORBIDDEN_COLUMNS):
            raise InquiryError('forbidden/changed column projection')
        names = [metadata.schema.column(i).path for i in range(metadata.num_columns)]
        if len(set(names)) != len(names) or not set(columns) <= set(names):
            raise InquiryError('exact public leaf columns absent/duplicated')
        intervals = [(0, 4), (self.footer_start, self.size)]
        public_ranges = []
        forbidden_ranges = []
        for g in range(metadata.num_row_groups):
            rg = metadata.row_group(g)
            for i, name in enumerate(names):
                column = rg.column(i)
                offsets = [column.data_page_offset]
                if column.has_dictionary_page:
                    offsets.append(column.dictionary_page_offset)
                left = min(offsets)
                right = left + column.total_compressed_size
                if left < 4 or right > self.footer_start or right <= left:
                    raise InquiryError('column range lies outside data region')
                if name in columns:
                    public_ranges.append((left, right))
                else:
                    forbidden_ranges.append((left, right))
        if any(a < d and c < b for a, b in public_ranges for c, d in forbidden_ranges):
            raise InquiryError('public/private column byte ranges overlap')
        intervals += public_ranges
        merged = []
        for left, right in sorted(intervals):
            if merged and left <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(right, merged[-1][1]))
            else:
                merged.append((left, right))
        self.allowed = merged
        self.metadata_only = False
        return {'public_data_ranges': [list(v) for v in sorted(public_ranges)],
                'private_data_ranges': [list(v) for v in sorted(forbidden_ranges)]}

    def close(self):
        if hasattr(self, 'ledger') and not self.ledger.closed:
            self.ledger.close()
        super().close()


def project_shard(source, columns=PUBLIC_COLUMNS):
    """Parse footer, whitelist public chunks and decode public fields only."""
    if tuple(columns) != PUBLIC_COLUMNS:
        raise InquiryError('forbidden/changed column projection')
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    parquet = pq.ParquetFile(source, pre_buffer=False, memory_map=False, buffer_size=0)
    ranges = source.permit_public_columns(parquet.metadata, columns)
    schema = {name: str(parquet.schema_arrow.field(name).type) for name in columns}
    records = []
    for batch in parquet.iter_batches(batch_size=128, columns=list(columns), use_threads=False):
        source.budget.check()
        for row in batch.to_pylist():
            if set(row) != set(columns):
                raise InquiryError('decoded projection drift')
            records.append(json_value(row))
    if len(records) != parquet.metadata.num_rows:
        raise InquiryError('projected/footer row count mismatch')
    return records, {'rows': len(records), 'row_groups': parquet.metadata.num_row_groups,
                     'public_schema': schema, 'footer_metadata_sha256': source.footer_sha256,
                     'footer_start': source.footer_start, 'footer_bytes': source.footer_length,
                     'server_total_bytes': source.size, **ranges}


def public_cases(value):
    if not isinstance(value, str):
        return {'format': 'nonstring', 'count': None}
    try:
        cases = json.loads(value)
    except (ValueError, TypeError):
        return {'format': 'invalid-json', 'count': None}
    if type(cases) is not list:
        return {'format': 'json-not-list', 'count': None}
    shapes = collections.Counter()
    types = collections.Counter()
    invalid = 0
    for case in cases:
        if type(case) is not dict:
            invalid += 1
            continue
        shapes[','.join(sorted(case))] += 1
        types[str(case.get('testtype', 'UNDECLARED'))] += 1
        if 'input' not in case or 'output' not in case:
            invalid += 1
    return {'format': 'json-list', 'count': len(cases), 'case_shapes': dict(shapes),
            'declared_testtypes': dict(types), 'invalid_case_shapes': invalid}


def starter_interface(value):
    if value in (None, ''):
        return {'kind': 'empty-stdio-proposal', 'parsed': False}
    if not isinstance(value, str):
        return {'kind': 'nonstring', 'parsed': False}
    try:
        tree = ast.parse(value)
    except (SyntaxError, ValueError, TypeError):
        return {'kind': 'unparsed-source', 'parsed': False}
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({'name': node.name, 'positional_parameters': len(node.args.posonlyargs) + len(node.args.args),
                              'keyword_only_parameters': len(node.args.kwonlyargs),
                              'varargs': node.args.vararg is not None, 'kwargs': node.args.kwarg is not None,
                              'async': isinstance(node, ast.AsyncFunctionDef)})
    return {'kind': 'parsed-source', 'parsed': True, 'functions': functions,
            'classes': [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]}


def inventory(records):
    rows = []
    identities = collections.Counter()
    platforms = collections.Counter()
    difficulties = collections.Counter()
    interfaces = collections.Counter()
    cases = collections.Counter()
    absent = collections.Counter()
    content_hashes = collections.defaultdict(list)
    for i, row in enumerate(records):
        if set(row) != set(PUBLIC_COLUMNS):
            raise InquiryError('public record schema')
        hashes = {name: hash_bytes(json_bytes(row[name])) for name in PUBLIC_COLUMNS}
        key = (str(row['platform']), str(row['question_id']))
        identities[key] += 1
        platforms[str(row['platform'])] += 1
        difficulties[str(row['difficulty'])] += 1
        for name, value in row.items():
            if value in (None, ''):
                absent[name] += 1
        interface = starter_interface(row['starter_code'])
        case = public_cases(row['public_test_cases'])
        interfaces[interface['kind']] += 1
        cases[case['format']] += 1
        content_hashes[hashes['question_content']].append(i)
        rows.append({'source_row': i, 'platform': row['platform'], 'question_id': row['question_id'],
                     'contest_id': row['contest_id'], 'contest_date': row['contest_date'],
                     'difficulty': row['difficulty'], 'field_sha256': hashes,
                     'public_row_sha256': hash_bytes(json_bytes(row)),
                     'starter_interface': interface, 'public_case_structure': case,
                     'approved_for_evaluation': False})
    return {'rows': rows, 'actual_rows': len(rows), 'unique_platform_question_ids': len(identities),
            'duplicate_identities': [{'platform': p, 'question_id': q, 'count': n}
                                     for (p, q), n in sorted(identities.items()) if n > 1],
            'duplicate_content_hash_groups': [v for v in content_hashes.values() if len(v) > 1],
            'platform_counts': dict(platforms), 'difficulty_counts': dict(difficulties),
            'starter_interface_counts': dict(interfaces), 'public_case_format_counts': dict(cases),
            'missing_field_counts': dict(absent), 'admitted_rows': 0}


def run(plan, output, *, opener=urllib.request.urlopen, budget=None):
    validate_plan(plan)
    if hash_bytes(Path(__file__).read_bytes()) != plan['runner_sha256']:
        raise InquiryError('runner source hash drift')
    output = Path(output)
    work = (Path(__file__).resolve().parents[1] / 'work').resolve()
    if not output.resolve().is_relative_to(work) or output.resolve() == work:
        raise InquiryError('raw source output must be under this repository ignored work/')
    if output.exists():
        raise InquiryError('fresh ignored output directory required')
    output.mkdir(parents=True)
    (output / 'plan.json').write_bytes(json_bytes(plan) + b'\n')
    budget = budget or Budget()
    records = []
    shard_summaries = []
    sources = []
    summary = {'schema': 'lcb-public-source-inquiry-result-v1', 'status': 'FAILED',
               'dataset': DATASET, 'revision': REVISION,
               'plan_sha256': hash_bytes(json_bytes(plan)), 'admitted_rows': 0,
               'model_calls': 0, 'candidate_reference_benchmark_executions': 0}
    try:
        import pyarrow
        summary['runtime'] = {'python': sys.version.split()[0], 'pyarrow': pyarrow.__version__}
        for i, shard in enumerate(plan['shards']):
            budget.check()
            summary['last_attempted_shard'] = shard
            source = StrictRangeFile(plan['url_prefix'] + shard, budget=budget,
                                     directory=output / 'ranges' / f'shard-{i:02d}', opener=opener,
                                     max_request=plan['max_request_bytes'], expected_size=plan['shard_bytes'][shard])
            sources.append(source)
            public, detail = project_shard(source, plan['public_columns'])
            detail.update(shard=shard, public_projection_sha256=hash_bytes(json_bytes(public)),
                          fetched_bytes=sum(r['fetched_bytes'] for r in source.receipts),
                          request_count=len(source.receipts))
            shard_summaries.append(detail)
            records.extend(public)
            with (output / 'public-rows.jsonl').open('ab') as raw:
                for row in public:
                    raw.write(json_bytes(row) + b'\n')
            source.close()
        report = inventory(records)
        (output / 'sanitized-inventory.json').write_bytes(json_bytes(report) + b'\n')
        summary.update(status='COMPLETE' if len(records) == plan['expected_declared_rows'] else 'COMPLETE_COUNT_MISMATCH',
                       actual_rows=len(records), expected_declared_rows=plan['expected_declared_rows'],
                       declared_count_matches=len(records) == plan['expected_declared_rows'],
                       public_projection_sha256=hash_bytes(json_bytes(records)),
                       sanitized_inventory_sha256=hash_bytes(json_bytes(report)))
    except Exception as exc:
        summary.update(error_type=type(exc).__name__)
        if isinstance(exc, InquiryError):
            summary['boundary_error'] = str(exc)
        # A partial prefix remains a source failure, never a replacement frame.
        summary['completed_public_prefix_rows'] = len(records)
    finally:
        for source in sources:
            source.close()
        summary.update(shards=shard_summaries, fetched_bytes=budget.fetched,
                       elapsed_seconds=budget.clock() - budget.started)
        (output / 'summary.json').write_bytes(json_bytes(summary) + b'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    plan = validate_plan(json.loads(Path(args.plan).read_text()))
    # Main owns one sequential worker; no scheduler/job/model invocation occurs.
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    resource.setrlimit(resource.RLIMIT_CPU, (min(500, soft) if soft >= 0 else 500,
                                           min(501, hard) if hard >= 0 else 501))
    def expired(signum, frame):
        raise BudgetExceeded('global wall-time cap')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(500)
    result = run(plan, args.out)
    signal.alarm(0)
    print(json.dumps({'status': result['status'], 'fetched_bytes': result['fetched_bytes'],
                      'actual_rows': result.get('actual_rows'), 'admitted_rows': 0}))
    return 0 if result['status'] == 'COMPLETE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
