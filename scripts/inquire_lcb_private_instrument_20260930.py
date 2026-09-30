#!/usr/bin/env python3
"""Frozen data-only private-test feasibility inquiry; never unpickle or execute.

All source rows stay assigned. Only identities and the private test column are
read. Private inputs/answers remain in ignored raw storage and never appear in
policy inputs, reports or exception messages. This is not task admission.
"""
import argparse
import base64
import collections
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import pickletools
import resource
import shutil
import signal
import struct
import sys
import time
import zlib

try:
    import inquire_lcb_public_frame_20260930 as source
except ModuleNotFoundError:
    from scripts import inquire_lcb_public_frame_20260930 as source

COLUMNS = ('platform', 'question_id', 'private_test_cases')
MAX_FETCH = 5 * 1024**3
MAX_RETAIN = 6 * 1024**3
WALL = 7200
CPU = 3600
MAX_ENCODED = 128 * 1024**2
MAX_INFLATED = 256 * 1024**2
MAX_CASES = 100000
EXPECTED_ROWS = 1055
MAX_REQUESTS = 1024
MAX_RECEIPT = 2048
MAX_FOOTER = 16384
MAX_JOURNAL = 20*1024**2
MAX_META_FILE = 1024**2
MAX_RSS = 16*1024**3


class InstrumentError(ValueError):
    pass


class LimitReached(InstrumentError):
    pass


class InstrumentBudget(source.Budget):
    def __init__(self):
        super().__init__(max_bytes=MAX_FETCH,seconds=WALL)
        self.requests = 0
    def check(self, additional=0):
        super().check(additional)
        usage=resource.getrusage(resource.RUSAGE_SELF)
        rss=usage.ru_maxrss*(1 if sys.platform=='darwin' else 1024)
        if rss>MAX_RSS: raise LimitReached('measured-rss-post-allocation-cap')
        if usage.ru_utime+usage.ru_stime>=CPU: raise LimitReached('cpu-cap')
    def reserve_request(self):
        self.check()
        if self.requests>=MAX_REQUESTS: raise LimitReached('request-count-cap')
        self.requests += 1


class ReceiptLedger:
    def __init__(self,path): self.file=Path(path).open('xb')
    def write(self,value):
        if len(value)>MAX_RECEIPT or self.file.tell()+len(value)>MAX_REQUESTS*MAX_RECEIPT:
            raise LimitReached('pre-write-receipt-cap')
        return self.file.write(value)
    def __getattr__(self,name): return getattr(self.file,name)


def digest(b):
    return hashlib.sha256(b).hexdigest()


def canonical(value):
    return source.json_bytes(value)


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result: raise InstrumentError('duplicate-json-key')
            result[key] = item
        return result
    def nonfinite(_): raise InstrumentError('nonfinite-json')
    return json.loads(value,object_pairs_hook=pairs,parse_constant=nonfinite)


def bounded_inflate(data, limit=MAX_INFLATED):
    """Do not allocate an unbounded decompression bomb or accept trailing data."""
    decoder = zlib.decompressobj()
    value = decoder.decompress(data, limit + 1)
    if len(value) > limit or decoder.unconsumed_tail:
        raise InstrumentError('inflated-size-cap')
    if not decoder.eof or decoder.unused_data:
        raise InstrumentError('invalid-or-trailing-zlib')
    return value


def inert_pickle_string(data):
    """Inspect opcodes only: one literal Unicode string, framing and no execution.

    No Unpickler or pickle.loads exists in this program. GLOBAL, REDUCE, BUILD,
    persistent IDs, container/memo retrieval and arbitrary object reconstruction
    are refused. A non-whitelisted encoding is retained as an unresolved row.
    """
    allowed = {'PROTO', 'FRAME', 'BINUNICODE', 'SHORT_BINUNICODE',
               'BINUNICODE8', 'UNICODE', 'MEMOIZE', 'BINPUT', 'LONG_BINPUT',
               'PUT', 'STOP'}
    literals = []
    stopped = False
    protocols = frames = memo = 0
    for op, argument, position in pickletools.genops(data):
        if op.name not in allowed:
            raise InstrumentError('unsupported-pickle-opcode')
        if op.name == 'PROTO':
            protocols += 1
            if position != 0 or protocols != 1 or argument not in range(0, 6):
                raise InstrumentError('pickle-protocol')
        elif op.name == 'FRAME':
            frames += 1
            if frames != 1 or literals or argument != len(data) - position - 9:
                raise InstrumentError('pickle-frame')
        elif op.name in {'BINUNICODE', 'SHORT_BINUNICODE', 'BINUNICODE8', 'UNICODE'}:
            literals.append(argument)
            if len(literals) != 1 or type(argument) is not str:
                raise InstrumentError('single-string-only')
        elif op.name in {'MEMOIZE', 'BINPUT', 'LONG_BINPUT', 'PUT'}:
            memo += 1
            if len(literals) != 1 or memo != 1 or (op.name != 'MEMOIZE' and argument != 0):
                raise InstrumentError('pickle-memo')
        elif op.name == 'STOP':
            if position != len(data) - 1 or len(literals) != 1:
                raise InstrumentError('pickle-trailing-or-empty')
            stopped = True
    if not stopped:
        raise InstrumentError('pickle-stop')
    return literals[0]


def decode_cases(value):
    if type(value) is not str or len(value.encode('utf-8')) > MAX_ENCODED:
        raise InstrumentError('encoded-field-size-or-type')
    try:
        parsed = strict_json(value)
        encoding = 'direct-json'
    except json.JSONDecodeError:
        compressed = base64.b64decode(value.encode('ascii'), validate=True)
        inflated = bounded_inflate(compressed)
        # JSON-only variants are accepted explicitly. No fallback executes data.
        try:
            parsed = strict_json(inflated.decode('utf-8'))
            encoding = 'base64-zlib-json'
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = strict_json(inert_pickle_string(inflated))
            encoding = 'base64-zlib-inert-single-string-pickle-json'
    if type(parsed) is not list or len(parsed) > MAX_CASES:
        raise InstrumentError('case-list-or-count')
    if any(type(c) is not dict or set(c) != {'input', 'output', 'testtype'} or
           type(c['input']) is not str or type(c['output']) is not str or
           c['testtype'] not in ('stdin', 'functional') for c in parsed):
        raise InstrumentError('exact-case-schema')
    return parsed, encoding


def summarize_cases(cases, public_cases):
    private_keys = [digest(canonical(c)) for c in cases]
    public_keys = {digest(canonical(c)) for c in public_cases}
    input_sizes = [len(c['input'].encode()) for c in cases]
    output_sizes = [len(c['output'].encode()) for c in cases]
    private_inputs = collections.defaultdict(set)
    public_inputs = collections.defaultdict(set)
    for c in cases:
        private_inputs[digest(c['input'].encode())].add(digest(c['output'].encode()))
    for c in public_cases:
        public_inputs[digest(c['input'].encode())].add(digest(c['output'].encode()))
    return {
        'case_count': len(cases), 'types': dict(collections.Counter(c['testtype'] for c in cases)),
        'case_ledger_sha256': digest(canonical(private_keys)),
        'unique_case_count': len(set(private_keys)),
        'exact_public_case_duplicates': sum(k in public_keys for k in private_keys),
        'private_inputs_with_different_expected_outputs': sum(len(v)>1 for v in private_inputs.values()),
        'private_cases_with_public_input': sum(digest(c['input'].encode()) in public_inputs for c in cases),
        'overlapping_inputs_with_different_public_private_expectations': sum(v!=public_inputs[k] for k,v in private_inputs.items() if k in public_inputs),
        'input_bytes_total': sum(input_sizes), 'output_bytes_total': sum(output_sizes),
        'input_bytes_max': max(input_sizes, default=0), 'output_bytes_max': max(output_sizes, default=0),
        'cases_exceeding_64k_stdin': sum(v > 65536 for v in input_sizes),
        'cases_saturating_64k_stdout': sum(v >= 65536 for v in output_sizes),
        'empty_inputs': sum(v == 0 for v in input_sizes),
        'empty_outputs': sum(v == 0 for v in output_sizes),
    }


class PrivateRangeFile(source.StrictRangeFile):
    """Versioned data inquiry: disk-backed range cache and exact projection."""
    def __init__(self,url,*,budget,directory,opener=source.urllib.request.urlopen,
                 expected_size=None,expected_footer=None):
        io.RawIOBase.__init__(self)
        self.url=url; self.budget=budget; self.directory=Path(directory)
        self.directory.mkdir(parents=True,exist_ok=False)
        self.opener=opener; self.max_request=source.MAX_REQUEST
        self.position=0; self.size=None; self.expected_size=expected_size
        self.cache=[]; self.receipts=[]; self.allowed=[]; self.metadata_only=True
        self.ledger=ReceiptLedger(self.directory/'requests.jsonl')
        header=self._fetch(0,3)
        if header!=b'PAR1' or self.size<12: raise InstrumentError('parquet-header')
        trailer=self._fetch(self.size-8,self.size-1)
        if trailer[4:]!=b'PAR1': raise InstrumentError('parquet-trailer')
        self.footer_length=struct.unpack('<I',trailer[:4])[0]
        self.footer_start=self.size-8-self.footer_length
        if not 0<self.footer_length<=MAX_FOOTER or self.footer_start<4:
            raise InstrumentError('footer-cap')
        if expected_footer is not None and self.footer_length!=expected_footer['footer_bytes']:
            raise InstrumentError('footer-length-drift')
        footer=self._fetch_chunks(self.footer_start,self.size-9)
        self.footer_sha256=digest(footer)
        if expected_footer is not None and self.footer_sha256!=expected_footer['footer_sha256']:
            raise InstrumentError('footer-hash-drift')
        self.allowed=[(0,4),(self.footer_start,self.size)]

    def _fetch(self, start, end):
        if hasattr(self.budget,'reserve_request'): self.budget.reserve_request()
        value = super()._fetch(start, end)
        left, right, _ = self.cache.pop()
        self.cache.append((left, right, self.directory / self.receipts[-1]['payload_path']))
        return value

    def _interval(self, start, end):
        result = bytearray()
        cursor = start
        for left, right, path in sorted(self.cache):
            if right <= cursor or left >= end:
                continue
            if left > cursor:
                result.extend(self._fetch_chunks(cursor, left - 1))
                cursor = left
            stop = min(end, right)
            if stop > cursor:
                with path.open('rb') as handle:
                    handle.seek(cursor - left)
                    data = handle.read(stop - cursor)
                if len(data) != stop - cursor:
                    raise InstrumentError('cache-size-drift')
                result.extend(data)
                cursor = stop
        if cursor < end:
            result.extend(self._fetch_chunks(cursor, end - 1))
        return bytes(result)

    def read(self, size=-1):
        self.budget.check()
        if type(size) is not int:
            raise InstrumentError('read-size')
        start = min(self.position, self.size)
        end = self.size if size < 0 else min(self.size, start + size)
        if end <= start:
            return b''
        if end - start > 1280 * 1024**2 or (self.metadata_only and end-start > source.MAX_REQUEST):
            raise InstrumentError('logical-read-cap')
        parts = []
        cursor = start
        for left, right in self.allowed:
            left, right = max(left, start), min(right, end)
            if left >= right:
                continue
            if left > cursor:
                if not self.metadata_only:
                    raise InstrumentError('read-outside-projection')
                parts.append(b'\0' * (left-cursor))
            parts.append(self._interval(left, right)); cursor = right
        if cursor < end:
            if not self.metadata_only:
                raise InstrumentError('read-outside-projection')
            parts.append(b'\0' * (end-cursor))
        self.position += end-start
        return b''.join(parts)

    def permit_instrument_columns(self, metadata):
        names = [metadata.schema.column(i).path for i in range(metadata.num_columns)]
        if len(names) != len(set(names)) or not set(COLUMNS) <= set(names):
            raise InstrumentError('projection-schema')
        selected, excluded = [], []
        for g in range(metadata.num_row_groups):
            for i, name in enumerate(names):
                c = metadata.row_group(g).column(i)
                offsets = [c.data_page_offset]
                if c.has_dictionary_page: offsets.append(c.dictionary_page_offset)
                left = min(offsets); right = left + c.total_compressed_size
                if left < 4 or right > self.footer_start or right <= left:
                    raise InstrumentError('invalid-column-interval')
                (selected if name in COLUMNS else excluded).append((left, right))
        if any(a < d and c < b for a,b in selected for c,d in excluded):
            raise InstrumentError('selected-excluded-overlap')
        merged = []
        for left,right in sorted([(0,4),(self.footer_start,self.size)] + selected):
            if merged and left <= merged[-1][1]: merged[-1] = (merged[-1][0],max(right,merged[-1][1]))
            else: merged.append((left,right))
        self.allowed = merged; self.metadata_only = False
        return {'selected_data_ranges': selected, 'excluded_data_ranges': excluded,
                'footer_start': self.footer_start, 'footer_sha256': self.footer_sha256}


def validate_plan(plan):
    expected = {'schema','dataset','revision','url_prefix','shards','shard_bytes','columns',
                'rows','max_fetched_bytes','max_retained_bytes','max_request_bytes','wall_seconds',
                'cpu_seconds','cpu_count','minimum_free_bytes','max_encoded_field_bytes',
                'max_inflated_bytes','max_cases_per_row','public_rows_path','public_rows_sha256',
                'runner_sha256','range_source_sha256','pyarrow_version','python_version',
                'footer_pins','max_request_count','max_receipt_bytes','max_footer_bytes',
                'max_journal_bytes','max_metadata_file_bytes','max_rss_bytes'}
    if type(plan) is not dict or set(plan) != expected: raise InstrumentError('exact-plan-schema')
    pins = dict(schema='lcb-private-instrument-feasibility-v1',dataset=source.DATASET,
        revision=source.REVISION,url_prefix=source.URL_PREFIX,shards=list(source.SHARDS),
        shard_bytes=source.SHARD_BYTES,columns=list(COLUMNS),rows=EXPECTED_ROWS,
        max_fetched_bytes=MAX_FETCH,max_retained_bytes=MAX_RETAIN,max_request_bytes=source.MAX_REQUEST,
        wall_seconds=WALL,cpu_seconds=CPU,cpu_count=1,minimum_free_bytes=10*1024**3,
        max_encoded_field_bytes=MAX_ENCODED,max_inflated_bytes=MAX_INFLATED,max_cases_per_row=MAX_CASES,
        max_request_count=MAX_REQUESTS,max_receipt_bytes=MAX_RECEIPT,max_footer_bytes=MAX_FOOTER,
        max_journal_bytes=MAX_JOURNAL,max_metadata_file_bytes=MAX_META_FILE,max_rss_bytes=MAX_RSS)
    if any(plan.get(k) != v or type(plan.get(k)) is not type(v) for k,v in pins.items()):
        raise InstrumentError('source-projection-resource-drift')
    for field in ('runner_sha256','range_source_sha256','public_rows_sha256'):
        if type(plan[field]) is not str or len(plan[field]) != 64 or any(c not in '0123456789abcdef' for c in plan[field]):
            raise InstrumentError('hash-pin')
    footers=plan['footer_pins']
    if type(footers) is not list or len(footers)!=len(source.SHARDS):raise InstrumentError('footer-pins')
    for shard, pin in zip(source.SHARDS,footers):
        if type(pin) is not dict or set(pin)!={'shard','footer_sha256','footer_bytes','row_groups','rows','private_compressed_bytes','private_uncompressed_bytes'}:
            raise InstrumentError('footer-pin-schema')
        if any(type(pin[k]) is not int for k in ('footer_bytes','row_groups','rows','private_compressed_bytes','private_uncompressed_bytes')):
            raise InstrumentError('integer-footer-descriptors')
        if pin['shard']!=shard or pin['row_groups']!=1 or pin['rows'] not in (117,118):raise InstrumentError('footer-shape-pin')
        if type(pin['footer_bytes']) is not int or not 0<pin['footer_bytes']<=MAX_FOOTER:raise InstrumentError('footer-size-pin')
        if type(pin['footer_sha256']) is not str or len(pin['footer_sha256'])!=64 or any(c not in '0123456789abcdef' for c in pin['footer_sha256']):raise InstrumentError('footer-digest-pin')
        if not 0<pin['private_compressed_bytes']<=1280*1024**2 or not 0<pin['private_uncompressed_bytes']<=1280*1024**2:raise InstrumentError('column-size-pin')
    # Guaranteed retained serialized artifact allowance, checked before writes.
    if MAX_FETCH+MAX_REQUESTS*MAX_RECEIPT+MAX_JOURNAL+2*MAX_META_FILE>=MAX_RETAIN:
        raise InstrumentError('retained-envelope-proof')
    return plan


def run(plan, out):
    validate_plan(plan)
    import pyarrow as pa
    import pyarrow.parquet as pq
    if pa.__version__ != plan['pyarrow_version'] or sys.version.split()[0] != plan['python_version']:
        raise InstrumentError('parser-runtime-drift')
    if digest(Path(__file__).read_bytes()) != plan['runner_sha256'] or digest(Path(source.__file__).read_bytes()) != plan['range_source_sha256']:
        raise InstrumentError('source-hash-drift')
    root = Path(__file__).resolve().parents[1]
    public_path = (root / plan['public_rows_path']).resolve()
    if not public_path.is_relative_to(root/'work') or digest(public_path.read_bytes()) != plan['public_rows_sha256']:
        raise InstrumentError('public-projection-pin')
    public = [json.loads(v) for v in public_path.read_text().splitlines()]
    if len(public) != EXPECTED_ROWS: raise InstrumentError('public-rows')
    out = Path(out).resolve()
    if not out.is_relative_to(root/'work') or out == root/'work' or out.exists():
        raise InstrumentError('fresh-ignored-output')
    if shutil.disk_usage(root).free < plan['minimum_free_bytes']:
        raise InstrumentError('free-storage-preflight')
    out.mkdir(parents=True)
    plan_bytes=canonical(plan)+b'\n'
    if len(plan_bytes)>MAX_META_FILE:raise InstrumentError('plan-pre-write-cap')
    (out/'plan.json').write_bytes(plan_bytes)
    budget = InstrumentBudget()
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    summary = {'schema':'lcb-private-instrument-feasibility-result-v1','status':'FAILED',
               'plan_sha256':digest(canonical(plan)),'model_calls':0,'task_code_executions':0,
               'unpickler_executions':0,'admitted_tasks':0,'rows_processed':0,'shards':[]}
    offset = 0
    try:
        with (out/'rows.jsonl').open('xb') as ledger:
            for i, shard in enumerate(source.SHARDS):
                budget.check()
                if shutil.disk_usage(root).free < 2*1024**3: raise InstrumentError('remaining-storage-floor')
                pin=plan['footer_pins'][i]
                with PrivateRangeFile(source.URL_PREFIX+shard,budget=budget,directory=out/'ranges'/f'shard-{i:02d}',expected_size=source.SHARD_BYTES[shard],expected_footer=pin) as raw:
                    parquet = pq.ParquetFile(raw,pre_buffer=False,memory_map=False,buffer_size=0)
                    private_index=[parquet.metadata.schema.column(c).path for c in range(parquet.metadata.num_columns)].index('private_test_cases')
                    if (parquet.metadata.num_row_groups!=pin['row_groups'] or parquet.metadata.num_rows!=pin['rows'] or
                        sum(parquet.metadata.row_group(g).column(private_index).total_compressed_size for g in range(parquet.metadata.num_row_groups))!=pin['private_compressed_bytes'] or
                        sum(parquet.metadata.row_group(g).column(private_index).total_uncompressed_size for g in range(parquet.metadata.num_row_groups))!=pin['private_uncompressed_bytes']):
                        raise InstrumentError('column-descriptor-pin-drift')
                    boundaries = raw.permit_instrument_columns(parquet.metadata)
                    count = 0
                    for batch in parquet.iter_batches(batch_size=1,columns=list(COLUMNS),use_threads=False):
                        budget.check()
                        for row in batch.to_pylist():
                            assigned = public[offset]
                            if set(row) != set(COLUMNS) or (row['platform'],row['question_id']) != (assigned['platform'],assigned['question_id']):
                                raise InstrumentError('identity-or-row-alignment-drift')
                            encoded = row['private_test_cases']
                            record = {'source_row':offset,'platform':row['platform'],'question_id':row['question_id'],
                                'public_row_sha256':digest(canonical(assigned)),'status':'UNRESOLVED','admitted':False}
                            if type(encoded) is str:
                                record.update(encoded_bytes=len(encoded.encode()),private_field_sha256=digest(encoded.encode()))
                            try:
                                cases, encoding = decode_cases(encoded)
                                record.update(status='DECODED_SCHEMA_ONLY',encoding=encoding,
                                              **summarize_cases(cases,json.loads(assigned['public_test_cases'])))
                                del cases
                            except Exception as exc:
                                if isinstance(exc,LimitReached):raise
                                record['failure_type'] = type(exc).__name__
                                # Finite, fixed exception tags only; no private text.
                                if isinstance(exc,InstrumentError): record['failure_tag'] = str(exc)
                            record_bytes=canonical(record)+b'\n'
                            if ledger.tell()+len(record_bytes)>MAX_JOURNAL:raise LimitReached('journal-pre-write-cap')
                            ledger.write(record_bytes); ledger.flush()
                            offset += 1; count += 1; summary['rows_processed'] = offset
                        del batch; gc.collect()
                    if count != parquet.metadata.num_rows: raise InstrumentError('footer-count')
                    summary['shards'].append({'shard':shard,'rows':count,**boundaries,
                         'request_count':len(raw.receipts),'fetched_bytes':sum(x['fetched_bytes'] for x in raw.receipts)})
                    del parquet
                gc.collect()
        budget.check()
        if offset != EXPECTED_ROWS: raise InstrumentError('complete-assignment-count')
        summary['status'] = 'COMPLETED'
    except Exception as exc:
        summary['failure_type'] = type(exc).__name__
        if isinstance(exc,InstrumentError): summary['failure_tag'] = str(exc)
    finally:
        summary.update(fetched_bytes=budget.fetched,elapsed_seconds=budget.clock()-budget.started,
                       unattempted_rows=EXPECTED_ROWS-offset,
                       max_rss_platform_units=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       cpu_user_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime,
                       cpu_system_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_stime,
                       rss_units='bytes-on-macos-kib-on-linux')
        retained = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
        summary['retained_bytes_before_summary'] = retained
        if retained > MAX_RETAIN: summary['status'] = 'RETAINED_CAP_EXCEEDED'
        if (out/'rows.jsonl').exists(): summary['journal_sha256'] = digest((out/'rows.jsonl').read_bytes())
        summary_bytes=canonical(summary)+b'\n'
        if len(summary_bytes)>MAX_META_FILE:raise InstrumentError('summary-pre-write-cap')
        (out/'summary.json').write_bytes(summary_bytes)
    return summary


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--plan',required=True); parser.add_argument('--out',required=True)
    args = parser.parse_args(); plan = json.loads(Path(args.plan).read_text())
    validate_plan(plan)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU,CPU+1))
    try:resource.setrlimit(resource.RLIMIT_AS,(MAX_RSS,MAX_RSS))
    except (ValueError,OSError):pass  # OS enforcement remains explicitly unproved.
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(LimitReached('global-wall-cap')))
    signal.signal(signal.SIGXCPU,lambda *_: (_ for _ in ()).throw(LimitReached('global-cpu-cap')))
    signal.alarm(WALL)
    summary = run(plan,args.out)
    print(json.dumps({k:summary[k] for k in ('status','rows_processed','unattempted_rows','fetched_bytes','elapsed_seconds')},sort_keys=True))
    return 0 if summary['status']=='COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
