"""Pure mocked grader verification; never launches a payload or qualification."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from experiments.sprint_grading import batch_v1 as batch


class MockBudget:
    def __init__(self, cap=100):self.cap=cap;self.case_starts=0;self.stop_reason=None
    def check(self, start=False):
        if self.stop_reason:return False
        if start:
            if self.case_starts>=self.cap:self.stop_reason='global_case_start_cap';return False
            self.case_starts+=1
        return True
    def unavailable(self, reason):self.stop_reason=reason


class MockRunner:
    """Returns inert synthetic receipts. Does not eval/exec/subprocess code."""
    def __init__(self, outputs):self.outputs=outputs;self.calls=[]
    def __call__(self, code, stdin, *, caps):
        self.calls.append((code,stdin))
        value=self.outputs[stdin]
        common={'version':batch.execution.VERSION,'source_sha256':batch.text_sha(code),
            'stdin_sha256':batch.runtime.sha256(stdin),'stdin_bytes':len(stdin),'caps':caps,
            'runtime_manifest_sha256':'0'*64}
        if value is None:
            return {**common,'disposition':'observer_unavailable','outcome_available':False,
                    'payload_started':False,'failure':'mock_namespace_failure'}
        return {**common,'disposition':'completed','outcome_available':True,'payload_started':True,
            'returncode':0,'cleanup':True,'stdout':value,'stdout_bytes':len(value),
            'stdout_sha256':batch.runtime.sha256(value),'stderr_bytes':0,
            'stderr_sha256':batch.runtime.sha256(b''),'seconds':.01}


def fixture(outputs, scope='private'):
    cases=[{'case_id':'r:'+scope+':'+str(i),'scope':scope,'stdin':str(i),
            'expected_stdout':str(expected)} for i,expected in enumerate(outputs)]
    instrument=batch.observer.freeze_instrument(cases,scope=scope,
        normalization='ascii_whitespace_tokens_v1',runtime_manifest_sha256='0'*64,
        source_contract_sha256='1'*64)
    return cases,instrument


def state_fixture(scope='private'):
    frozen={'assignment_id':'a','initial_execution_id':'u','root':'r'}
    config={'ledger':[frozen],'initials':[{'initial_execution_id':'u','root':'r'}],
            'extractor':batch.EXTRACTOR}
    config['config_sha256']=batch.sha(config)
    state={'config_sha256':config['config_sha256'],'phase':3 if scope=='private' else 0,
           'requests':[],'rows':[{**frozen,'disposition':'HORIZON' if scope=='private' else 'active',
                'final_program':'print(1)','final_raw':'print(1)'}]}
    assignments=[{'grading_unit_id':'u','root':'r','program':'print(1)',
        'program_sha256':batch.text_sha('print(1)'),'scope':scope,'extractor':batch.EXTRACTOR}]
    return state,config,assignments


class SprintGradingTests(unittest.TestCase):
    def test_primitive_separates_repetitions_and_scope(self):
        pin='a'*64;program='b'*64
        x=batch.primitive_id('public','u1','r',program,pin)
        self.assertNotEqual(x,batch.primitive_id('public','u2','r',program,pin))
        self.assertNotEqual(x,batch.primitive_id('private','u1','r',program,pin))
        self.assertEqual(x,batch.sha(['public','u1','r',program,pin]))

    def test_exact_terminal_gate_and_all_assignments(self):
        state,config,assignments=state_fixture()
        batch.check_state(state,config,'private',assignments)
        for change in ({'phase':2},{'requests':[{}]}):
            broken={**state,**change}
            with self.assertRaisesRegex(ValueError,'terminal phase3'):
                batch.check_state(broken,config,'private',assignments)
        with self.assertRaisesRegex(ValueError,'all terminal artifact'):
            batch.check_state(state,config,'private',[])

    def test_terminal_program_must_match_exact_extractor(self):
        state,config,assignments=state_fixture();state['rows'][0]['final_raw']='print(2)'
        with self.assertRaisesRegex(ValueError,'artifact drift'):
            batch.check_state(state,config,'private',assignments)

    def test_duplicate_public_primitive_refused(self):
        state,config,assignments=state_fixture('public')
        with self.assertRaisesRegex(ValueError,'duplicate'):
            batch.check_state(state,config,'public',assignments*2)

    def test_private_gate_precedes_source_bundle_constructor(self):
        state,config,assignments=state_fixture();state['phase']=2
        plan={'version':batch.VERSION,'workers':4,'scope':'private','files':{},
              **{k:100000 for k in ('max_wall_seconds','max_cpu_seconds','max_case_starts',
                'max_retained_bytes','max_rss_bytes','max_input_file_bytes','max_output_file_bytes')},
              'study_config_path':'c','study_config_file_sha256':'x','state_path':'s','state_file_sha256':'x',
              'assignments_path':'a','assignments_file_sha256':'x','assignments_sha256':batch.sha(assignments),
              'state_sha256':batch.sha(state),'study_config_sha256':config['config_sha256'],
              'observer_sha256':'o'}
        config['pins']={'private_observer':'o'};config['config_sha256']=batch.sha({k:v for k,v in config.items() if k!='config_sha256'})
        state['config_sha256']=config['config_sha256'];plan['state_sha256']=batch.sha(state);plan['study_config_sha256']=config['config_sha256']
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'plan.json';path.write_text(json.dumps(plan))
            with mock.patch.object(batch,'bound_json',side_effect=[config,state,assignments]),mock.patch.object(batch,'SourceBundle') as source:
                with self.assertRaisesRegex(ValueError,'terminal phase3'):batch.run_batch(path,Path(d)/'out')
                source.assert_not_called()

    def test_known_primary_zero_does_not_skip_unresolved_diagnostic(self):
        cases,instrument=fixture([1,2,3]);runner=MockRunner({b'0':b'wrong',b'1':b'2',b'2':b'3'})
        rows=[];budget=MockBudget()
        result=batch.battery_grade('not executed',cases,instrument,scope='private',runner=runner,
            budget=budget,record=lambda raw:rows.append(json.loads(raw)),diagnostic_ordinals=[1,2])
        self.assertEqual(result['primary']['value'],0);self.assertEqual(result['diagnostic']['value'],1)
        self.assertEqual(result['case_starts'],3);self.assertEqual(len(rows),3)
        self.assertTrue(all('expected_stdout' not in row for row in rows))
        self.assertEqual([stdin for _,stdin in runner.calls],[b'0',b'1',b'2'])

    def test_known_diagnostic_zero_skips_remaining_with_witness(self):
        cases,instrument=fixture([1,2,3]);runner=MockRunner({b'0':b'wrong',b'1':b'2',b'2':b'3'})
        rows=[]
        result=batch.battery_grade('not executed',cases,instrument,scope='private',runner=runner,
            budget=MockBudget(),record=lambda raw:rows.append(json.loads(raw)),diagnostic_ordinals=[0,2])
        self.assertEqual(result['case_starts'],1);self.assertEqual(result['primary']['value'],0)
        self.assertEqual(result['diagnostic']['value'],0)
        self.assertEqual([r['disposition'] for r in rows],['EXECUTED','SKIPPED_KNOWN_ZERO','SKIPPED_KNOWN_ZERO'])
        self.assertEqual(rows[2]['diagnostic_zero_witness_ordinal'],0)

    def test_unavailable_is_unknown_and_all_cases_retained(self):
        cases,instrument=fixture([1,2]);rows=[]
        result=batch.battery_grade('not executed',cases,instrument,scope='private',
            runner=MockRunner({b'0':None,b'1':b'2'}),budget=MockBudget(),
            record=lambda raw:rows.append(json.loads(raw)),diagnostic_ordinals=[1])
        self.assertIsNone(result['primary']['value']);self.assertIsNone(result['diagnostic']['value'])
        self.assertEqual(result['assigned_cases'],2);self.assertEqual(result['accounted_cases'],2)
        self.assertEqual(rows[1]['disposition'],'UNATTEMPTED_GLOBAL_CAP')

    def test_case_start_cap_never_creates_a_zero(self):
        cases,instrument=fixture([1,2]);rows=[]
        result=batch.battery_grade('not executed',cases,instrument,scope='private',
            runner=MockRunner({b'0':b'1',b'1':b'2'}),budget=MockBudget(1),
            record=lambda raw:rows.append(json.loads(raw)),diagnostic_ordinals=[0,1])
        self.assertIsNone(result['primary']['value']);self.assertEqual(result['case_starts'],1)
        self.assertEqual(len(rows),2)

    def test_actual_stdout_never_enters_case_receipt(self):
        cases,instrument=fixture([1]);rows=[]
        batch.battery_grade('not executed',cases,instrument,scope='private',
            runner=MockRunner({b'0':b'secret wrong output'}),budget=MockBudget(),
            record=lambda raw:rows.append(raw),diagnostic_ordinals=[0])
        self.assertNotIn(b'secret wrong output',b''.join(rows))
        self.assertIn(b'stdout_sha256',rows[0])

    def test_same_context_cache_immutable_across_public_phases(self):
        with tempfile.TemporaryDirectory() as d:
            batch._cache_context(Path(d)/'cache',{'config':'c','runtime':'r'})
            batch._cache_context(Path(d)/'cache',{'config':'c','runtime':'r'})
            with self.assertRaisesRegex(ValueError,'cannot cross'):
                batch._cache_context(Path(d)/'cache',{'config':'different','runtime':'r'})

    def test_battery_audit_reconstructs_exact_receipt(self):
        audit={'scope':'private','primitive_id':'p','grading_unit_id':'u','root':'r',
            'program_sha256':'a'*64,'observer_sha256':'b'*64,'elapsed_seconds':1.5,
            'unavailability_reason':'none','result':{'case_starts':2,'primary':{'status':'FAIL','value':0},
                'diagnostic':{'status':'PASS','value':1}}}
        primary,diagnostic=batch.observations_from_audit(audit)
        self.assertEqual(primary['observation']['value'],0)
        self.assertEqual(diagnostic['observation']['value'],1)
        self.assertEqual(primary['observation']['audit_sha256'],batch.sha(audit))
        self.assertNotEqual(primary['observation']['primitive_id'],diagnostic['observation']['primitive_id'])


if __name__=='__main__':unittest.main()
