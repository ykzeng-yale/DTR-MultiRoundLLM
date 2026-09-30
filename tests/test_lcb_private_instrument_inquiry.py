import base64
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from scripts import inquire_lcb_private_instrument_20260930 as q


def wrapped_pickle(text):
    raw = text.encode()
    payload = b'\x80\x04X' + struct.pack('<I',len(raw)) + raw + b'\x94.'
    return base64.b64encode(zlib.compress(payload)).decode()


class DecoderTests(unittest.TestCase):
    def setUp(self):
        self.cases = [{'input':'2\n','output':'4\n','testtype':'stdin'}]
        self.text = json.dumps(self.cases)

    def test_direct_json(self):
        self.assertEqual(q.decode_cases(self.text),(self.cases,'direct-json'))

    def test_wrapped_json(self):
        value=base64.b64encode(zlib.compress(self.text.encode())).decode()
        self.assertEqual(q.decode_cases(value),(self.cases,'base64-zlib-json'))

    def test_single_string_pickle_is_inspected_not_executed(self):
        self.assertEqual(q.decode_cases(wrapped_pickle(self.text)),(self.cases,'base64-zlib-inert-single-string-pickle-json'))

    def test_pickle_executable_and_container_opcodes_refused(self):
        for payload in (b'cos\nsystem\n(S\'echo bad\'\ntR.', b'\x80\x04].',b'\x80\x04K\x01.',b'\x80\x04\x8c\x01a\x8c\x01b.'):
            with self.subTest(payload=payload):
                with self.assertRaises(q.InstrumentError):q.inert_pickle_string(payload)

    def test_trailing_pickle_and_zlib_refused(self):
        with self.assertRaises(q.InstrumentError):q.inert_pickle_string(b'\x80\x04\x8c\x01a\x94.junk')
        with self.assertRaises(q.InstrumentError):q.bounded_inflate(zlib.compress(b'a')+b'trailing')

    def test_bomb_and_truncated_zlib_refused(self):
        with self.assertRaises(q.InstrumentError):q.bounded_inflate(zlib.compress(b'a'*1000),limit=10)
        with self.assertRaises(q.InstrumentError):q.bounded_inflate(zlib.compress(b'a')[:-1])

    def test_frames_and_memo_validated(self):
        body=b'\x8c\x01a\x94.'
        self.assertEqual(q.inert_pickle_string(b'\x80\x04\x95'+struct.pack('<Q',len(body))+body),'a')
        with self.assertRaises(q.InstrumentError):q.inert_pickle_string(b'\x80\x04\x95'+struct.pack('<Q',999)+body)
        with self.assertRaises(q.InstrumentError):q.inert_pickle_string(b'\x80\x04\x8c\x01a\x94\x94.')

    def test_bad_case_shapes_duplicate_keys_and_nonfinite_refused(self):
        for value in ('{}','[{}]', '[{"input":"a","input":"b","output":"c","testtype":"stdin"}]',
                      '[{"input":NaN,"output":"c","testtype":"stdin"}]',
                      '[{"input":"a","output":1,"testtype":"stdin"}]'):
            with self.subTest(value=value):
                with self.assertRaises(q.InstrumentError):q.decode_cases(value)

    def test_summary_no_private_values_and_leak_overlap_flags(self):
        cases=self.cases*2+[{'input':'2\n','output':'five','testtype':'stdin'},
                           {'input':'a'*65537,'output':'','testtype':'stdin'}]
        r=q.summarize_cases(cases,self.cases)
        self.assertEqual(r['case_count'],4)
        self.assertEqual(r['unique_case_count'],3)
        self.assertEqual(r['exact_public_case_duplicates'],2)
        self.assertEqual(r['private_inputs_with_different_expected_outputs'],1)
        self.assertEqual(r['private_cases_with_public_input'],3)
        self.assertEqual(r['overlapping_inputs_with_different_public_private_expectations'],1)
        self.assertEqual(r['cases_exceeding_64k_stdin'],1)
        self.assertNotIn('five',json.dumps(r))

    def test_disk_cache_and_projection_with_real_parquet(self):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ModuleNotFoundError:
            self.skipTest('real parser qualification runs in existing data reader')
        sink=io.BytesIO()
        pq.write_table(pa.table({'platform':['atcoder'],'question_id':['abc000_a'],
                               'private_test_cases':[self.text],'reference':['NEVER_READ_REFERENCE']}),sink)
        data=sink.getvalue()
        def opener(request,timeout=None):
            left,right=map(int,request.headers['Range'].removeprefix('bytes=').split('-'))
            class Response(io.BytesIO):
                def getcode(self):return 206
            r=Response(data[left:right+1]);r.headers={'Content-Range':f'bytes {left}-{right}/{len(data)}',
                'Content-Length':str(right-left+1)};return r
        with tempfile.TemporaryDirectory() as d:
            with q.PrivateRangeFile('https://fixture',budget=q.source.Budget(),directory=Path(d)/'ranges',opener=opener,expected_size=len(data)) as raw:
                p=pq.ParquetFile(raw,pre_buffer=False,buffer_size=0)
                intervals=raw.permit_instrument_columns(p.metadata)
                rows=p.read(columns=list(q.COLUMNS),use_threads=False).to_pylist()
                self.assertEqual(rows[0]['private_test_cases'],self.text)
                self.assertTrue(all(isinstance(v[2],Path) for v in raw.cache))
                self.assertTrue(all(not (a<r['end_inclusive']+1 and r['start']<b)
                    for a,b in intervals['excluded_data_ranges'] for r in raw.receipts))

    def test_old_public_projection_unchanged(self):
        self.assertNotIn('private_test_cases',q.source.PUBLIC_COLUMNS)
        self.assertIn('private_test_cases',q.COLUMNS)

    def test_stdout_exactly_at_cap_is_saturation(self):
        r=q.summarize_cases([{'input':'1','output':'a'*65536,'testtype':'stdin'}],[])
        self.assertEqual(r['cases_saturating_64k_stdout'],1)

    def test_request_and_receipt_caps_precede_next_write(self):
        budget=q.InstrumentBudget();budget.requests=q.MAX_REQUESTS
        with self.assertRaises(q.LimitReached):budget.reserve_request()
        with tempfile.TemporaryDirectory() as d:
            ledger=q.ReceiptLedger(Path(d)/'journal')
            with self.assertRaises(q.LimitReached):ledger.write(b'a'*(q.MAX_RECEIPT+1))
            self.assertEqual(ledger.tell(),0);ledger.close()

    def test_large_footer_refused_before_fetch(self):
        data=b'PAR1'+struct.pack('<I',q.MAX_FOOTER+1)+b'PAR1';calls=[]
        def opener(request,timeout=None):
            left,right=map(int,request.headers['Range'].removeprefix('bytes=').split('-'));calls.append((left,right))
            class Response(io.BytesIO):
                def getcode(self):return 206
            r=Response(data[left:right+1]);r.headers={'Content-Range':f'bytes {left}-{right}/{len(data)}','Content-Length':str(right-left+1)};return r
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(q.InstrumentError):q.PrivateRangeFile('https://fixture',budget=q.source.Budget(),directory=Path(d)/'ranges',opener=opener,expected_size=len(data))
        self.assertEqual(calls,[(0,3),(4,11)])

    def test_plan_refuses_projection_cap_and_source_changes(self):
        path=Path(__file__).resolve().parents[1]/'experiments/sources/lcb_private_inquiry_plan_20260930.json'
        plan=json.loads(path.read_text());q.validate_plan(plan)
        for field,value in (('columns',['private_test_cases','reference']),('rows',1054),
                            ('cpu_count',2),('max_fetched_bytes',q.MAX_FETCH+1),
                            ('wall_seconds',q.WALL+1),('minimum_free_bytes',0),
                            ('revision','unfrozen-main'),('runner_sha256','wrong')):
            changed=dict(plan);changed[field]=value
            with self.subTest(field=field):
                with self.assertRaises(q.InstrumentError):q.validate_plan(changed)


if __name__ == '__main__':unittest.main()
