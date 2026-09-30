"""Pure synthetic evidence mutations: no candidate/observer execution."""
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('audit_sprint_grading',Path(__file__).resolve().parents[1]/'scripts/audit_sprint_grading_v1.py')
a=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(a)
BINDINGS={k:chr(97+i)*64 for i,k in enumerate(('execution','runtime','observer','qualification'))}
RUNTIME='f'*64;SOURCE='e'*64


def fixture(outcomes=(1,1),scope='private',public_inputs=()):
    program='inert source, never executed';root='root'
    metadata={s:[] for s in ('public','private')};cases=[];bindings=[];rows=[]
    for i,value in enumerate(outcomes):
        stdin=str(i);expected=str(i+1);case={'case_id':root+':'+scope+':'+str(i),'scope':scope,'stdin':stdin,'expected_stdout':expected}
        m={'ordinal':i,'stdin_sha256':a.text_sha(stdin),'expected_stdout_sha256':a.text_sha(expected),
           'canonical_expected_sha256':a.text_sha(expected),'stdin_bytes':len(stdin),'expected_stdout_bytes':len(expected)}
        metadata[scope].append(m);cases.append(case)
        bindings.append({'case_id':case['case_id'],'scope':scope,'case_sha256':a.sha(case),
                         **{k:m[k] for k in ('stdin_sha256','stdin_bytes','expected_stdout_sha256','expected_stdout_bytes')}})
    if scope=='private':
        metadata['public']=[{'stdin_sha256':a.text_sha(str(i))} for i in public_inputs]
    entry={'root_source_sha256':'d'*64,'normalization':'ascii_whitespace_tokens_v1',
           scope:{'case_count':len(cases),'cases_sha256':a.sha(cases),'case_metadata_sha256':a.sha(metadata[scope])},
           'private':{'case_count':len(cases) if scope=='private' else 0,
                      'cases_sha256':a.sha(cases) if scope=='private' else a.sha([]),
                      'case_metadata_sha256':a.sha(metadata['private']),
                      'private_input_disjoint_ordinals':[i for i in range(len(cases)) if i not in public_inputs] if scope=='private' else []}}
    if scope=='public':entry['public']={'case_count':len(cases),'cases_sha256':a.sha(cases)}
    assignment={'grading_unit_id':'u','root':root,'program':program,'program_sha256':a.text_sha(program),'scope':scope,'extractor':a.EXTRACTOR}
    instrument={'version':a.OBSERVER_VERSION,'scope':scope,'cases':bindings,'normalization':entry['normalization'],
                'caps':a.CAPS,'runtime_manifest_sha256':RUNTIME,'source_contract_sha256':a.sha([SOURCE,root,entry['root_source_sha256'],scope]),
                'source_sha256s':BINDINGS,'endpoint':'finite pinned conjunction'}
    pin=a.sha(instrument)
    for i,value in enumerate(outcomes):
        m=metadata[scope][i];actual=str(i+1) if value else 'wrong'
        execution={'version':a.EXECUTION_VERSION,'source_sha256':assignment['program_sha256'],
            'stdin_sha256':m['stdin_sha256'],'stdin_bytes':m['stdin_bytes'],'caps':a.CAPS,
            'runtime_manifest_sha256':RUNTIME,'seconds':.01,'disposition':'completed','returncode':0,
            'cleanup':True,'payload_started':True,'outcome_available':True,
            'stdout_bytes':len(actual),'stdout_sha256':a.text_sha(actual)}
        receipt={'version':a.OBSERVER_VERSION,**bindings[i],'artifact_sha256':assignment['program_sha256'],
            'instrument_sha256':pin,'normalization':entry['normalization'],'execution':execution,
            'status':'PASS' if value else 'FAIL','outcome':value,'reason':'external_frozen_stdout_comparison'}
        rows.append({'case_ordinal':i,'case_id':bindings[i]['case_id'],'case_sha256':bindings[i]['case_sha256'],
            'diagnostic_member':scope=='private' and i not in public_inputs,'disposition':'EXECUTED','outcome':value,'receipt':receipt})
    primary=a.aggregate(list(outcomes));diagnostic=a.aggregate([v for i,v in enumerate(outcomes) if i not in public_inputs]) if scope=='private' else None
    audit={'version':a.BATCH_VERSION,'grading_unit_id':'u','root':root,'program_sha256':assignment['program_sha256'],
        'scope':scope,'observer_sha256':'c'*64,'primitive_id':a.sha([scope,'u',root,assignment['program_sha256'],'c'*64]),
        'elapsed_seconds':.1,'unavailability_reason':'observer_unavailable','raw_stdout_retained':False,'raw_stderr_retained':False,
        'result':{'primary':primary,'diagnostic':diagnostic,'case_starts':len(rows),'assigned_cases':len(rows),'accounted_cases':len(rows),
                  'primary_zero_witness_ordinal':next((i for i,v in enumerate(outcomes) if v==0),None),
                  'diagnostic_zero_witness_ordinal':next((i for i,v in enumerate(outcomes) if v==0 and i not in public_inputs),None),
                  'instrument_sha256':pin}}
    return audit,instrument,rows,assignment,entry,metadata


def recount(f):
    return a.recount_battery(*f,runtime_pin=RUNTIME,source_pin=SOURCE,bindings=BINDINGS)


def filesystem_fixture(directory):
    """Construct only inert metadata; no executor/qualifier is invoked."""
    root=Path(directory).resolve();batch=root/'batch';batch.mkdir()
    def write(path,value):
        path=root/path;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(a.canonical(value)+b'\n');return a.file_sha(path)
    f=fixture(scope='public');audit,instrument,rows,assignment,entry,metadata=f
    source_paths={name:'experiments/'+('containment/stdio_sprint_qualification_v4.py' if name=='qualification' else 'measurement_sprint_v4/'+('stdio' if name=='observer' else name)+'_v4.py') for name in BINDINGS}
    files={}
    for name,path in source_paths.items():files[path]=write(path,{'inert_source_pin':name})
    bindings={name:files[path] for name,path in source_paths.items()}
    metadata_raw=a.canonical(metadata)+b'\n';compressed=gzip.compress(metadata_raw,mtime=0)
    mp=root/'metadata.json.gz';mp.write_bytes(compressed)
    entry['case_metadata']={'path':str(mp),'stored_bytes':len(compressed),'plain_bytes':len(metadata_raw),'sha256':a.file_sha(mp)}
    index_path='instruments.json';index_pin=write(index_path,{'root':entry})
    source_pin=write('source-manifest.json',{'artifacts':{'instruments':{'path':index_path,'sha256':index_pin}}})
    frozen={'assignment_id':'assignment','initial_execution_id':'u','root':'root'}
    config={'ledger':[frozen],'initials':[{'initial_execution_id':'u','root':'root'}],
            'pins':{'public_observer':'c'*64,'private_observer':'c'*64}}
    config['config_sha256']=a.sha(config);config_pin=write('config.json',config)
    state={'config_sha256':config['config_sha256'],'phase':0,'requests':[],'rows':[{**frozen,'disposition':'active'}]}
    state_pin=write('state.json',state);assign_pin=write('assignments.json',[assignment])
    qp_pin=write('qualification-plan.json',{'caps':a.CAPS})
    att={'passed':True,'plan_sha256':qp_pin,'caps':a.CAPS,'runtime_manifest_sha256':RUNTIME,'job_id':'synthetic-job'}
    att_pin=write('attestation.json',att)
    plan={'version':a.BATCH_VERSION,'workers':4,'scope':'public','files':files,'max_input_file_bytes':10<<20,
        'study_config_path':'config.json','study_config_file_sha256':config_pin,'study_config_sha256':config['config_sha256'],
        'state_path':'state.json','state_file_sha256':state_pin,'state_sha256':a.sha(state),
        'assignments_path':'assignments.json','assignments_file_sha256':assign_pin,'assignments_sha256':a.sha([assignment]),
        'observer_sha256':'c'*64,'source_manifest_path':'source-manifest.json','source_manifest_sha256':source_pin,
        'attestation_path':'attestation.json','attestation_sha256':att_pin,'qualification_plan_path':'qualification-plan.json',
        'qualification_plan_sha256':qp_pin,'max_output_file_bytes':10<<20,'contract_sha256':'b'*64,
        'cache_dir':'cache','max_case_starts':10,'max_cpu_seconds':100,'max_wall_seconds':100,'max_retained_bytes':10<<20}
    plan_pin=write('plan.json',plan)
    instrument['source_contract_sha256']=a.sha([source_pin,'root',entry['root_source_sha256'],'public']);instrument['source_sha256s']=bindings
    instrument_pin=a.sha(instrument);instrument_path=batch/'instruments'/(instrument_pin+'.json')
    instrument_file_pin=write(instrument_path,instrument)
    for r in rows:r['receipt']['instrument_sha256']=instrument_pin
    identifier=audit['primitive_id'];battery=batch/'batteries'/identifier;battery.mkdir(parents=True)
    journal=battery/'cases.jsonl';journal.write_bytes(b''.join(a.canonical(r)+b'\n' for r in rows))
    audit.update(config_sha256=config['config_sha256'],state_sha256=a.sha(state),runtime_manifest_sha256=RUNTIME,
        instrument_path=str(instrument_path),instrument_file_sha256=instrument_file_pin,
        case_journal_path=str(journal),case_journal_sha256=a.file_sha(journal))
    audit['result']['instrument_sha256']=instrument_pin
    audit_path=battery/'summary.json';audit_file_pin=write(audit_path,audit)
    receipt,diagnostic=a.make_receipts(audit,audit['result'])
    cache=root/'cache'/config['config_sha256'];cache.mkdir(parents=True)
    context={'version':a.BATCH_VERSION,'config_sha256':config['config_sha256'],'contract_sha256':plan['contract_sha256'],
        'source_manifest_sha256':source_pin,'observer_sha256s':{s:config['pins'][s+'_observer'] for s in ('public','private')},
        'runtime_manifest_sha256':RUNTIME,'attestation_sha256':att_pin,'job_id':att['job_id']}
    write(cache/'context.json',context)
    cp=cache/(identifier+'.json');write(cp,{'receipt':receipt,'diagnostic':diagnostic,'audit_path':str(audit_path),'audit_file_sha256':audit_file_pin})
    op=write(batch/'observations.json',[receipt]);dp=write(batch/'diagnostics.json',[]);write(batch/'unreconciled_assignments.json',[])
    summary={'version':a.BATCH_VERSION,'plan_sha256':plan_pin,'scope':'public','contract_sha256':plan['contract_sha256'],
        'state_sha256':a.sha(state),'config_sha256':config['config_sha256'],'job_id':att['job_id'],'workers':4,
        'network_calls':0,'model_calls':0,'private_expected_answers_in_policy':False,'observations_sha256':a.sha([receipt]),
        'observations_file_sha256':op,'diagnostics_file_sha256':dp,'assigned_units':1,'accounted_units':1,
        'unreconciled_units':0,'assigned_cases':2,'cached_units':0,'case_starts':2,'status':'COMPLETE',
        'remaining_case_reservation':0,'cpu_seconds':.1,'elapsed_seconds':.2,
        'retained_bytes_before_summary':sum(p.stat().st_size for p in batch.rglob('*') if p.is_file())+cp.stat().st_size}
    write(batch/'summary.json',summary)
    return root,plan,batch,cache,write


class AuditGradingTests(unittest.TestCase):
    def test_complete_exact_byte_pass_recount(self):
        result,counts=recount(fixture());self.assertEqual(result['primary']['value'],1)
        self.assertEqual(counts['exact_byte_pass_reconfirmed'],2);self.assertEqual(result['case_starts'],2)

    def test_false_failure_for_identical_raw_output_refused(self):
        f=fixture();r=f[2][0];r['outcome']=0;r['receipt']['outcome']=0;r['receipt']['status']='FAIL'
        with self.assertRaisesRegex(ValueError,'falsely failed'):recount(f)

    def test_unavailable_never_becomes_zero(self):
        f=fixture();r=f[2][0];r['receipt']['execution']['disposition']='observer_unavailable'
        r['receipt']['execution']['outcome_available']=False;r['receipt']['status']='INCOMPLETE'
        r['outcome']=0;r['receipt']['outcome']=0
        with self.assertRaisesRegex(ValueError,'unavailable cannot'):recount(f)

    def test_duplicate_or_missing_raw_ordinal_refused(self):
        f=fixture();f[2][1]['case_ordinal']=0
        with self.assertRaisesRegex(ValueError,'ordinal completeness'):recount(f)

    def test_invalid_skip_zero_witness_refused(self):
        f=fixture();f[2][1].update(disposition='SKIPPED_KNOWN_ZERO',outcome=None,
            primary_zero_witness_ordinal=0,diagnostic_zero_witness_ordinal=0)
        with self.assertRaisesRegex(ValueError,'zero-witness'):recount(f)

    def test_primary_zero_outside_diagnostic_keeps_diagnostic_execution(self):
        result,counts=recount(fixture((0,1),'private',(0,)))
        self.assertEqual(result['primary']['value'],0);self.assertEqual(result['diagnostic']['value'],1)
        self.assertEqual(counts['EXECUTED'],2)

    def test_valid_known_zero_skip_reconciles_both_conjunctions(self):
        f=fixture((0,1));f[2][1].update(disposition='SKIPPED_KNOWN_ZERO',outcome=None,
            primary_zero_witness_ordinal=0,diagnostic_zero_witness_ordinal=0)
        f[0]['result']['case_starts']=1;f[0]['result']['diagnostic']=a.aggregate([0,None])
        result,_=recount(f);self.assertEqual(result['primary']['value'],0);self.assertEqual(result['case_starts'],1)

    def test_diagnostic_membership_must_match_source_public_input_hashes(self):
        f=fixture();f[4]['private']['private_input_disjoint_ordinals']=[0]
        with self.assertRaisesRegex(ValueError,'diagnostic membership'):recount(f)

    def test_program_identity_drift_refused(self):
        f=fixture();f[2][0]['receipt']['execution']['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'strict identity'):recount(f)

    def test_source_metadata_input_size_drift_refused(self):
        f=fixture(scope='public');f[5]['public'][0]['stdin_bytes']+=1
        with self.assertRaisesRegex(ValueError,'metadata/instrument'):recount(f)

    def test_aggregate_cannot_promote_missing_to_pass(self):
        f=fixture(scope='public');f[2][0].update(disposition='UNATTEMPTED_GLOBAL_CAP',outcome=None,reason='global_case_start_cap')
        with self.assertRaisesRegex(ValueError,'aggregate/count'):recount(f)

    def test_raw_private_values_are_not_receipt_fields(self):
        f=fixture();result,_=recount(f);receipt,diagnostic=a.make_receipts(f[0],result)
        self.assertEqual(set(receipt),{'grading_unit_id','root','program_sha256','scope','observer_sha256','observation'})
        self.assertNotIn('stdin',json.dumps(receipt));self.assertNotIn('expected_stdout',json.dumps(diagnostic))

    def test_path_prefix_mapping_is_metadata_only(self):
        with tempfile.TemporaryDirectory() as d:
            reader=a.Reader(d,['/remote/study='+d]);self.assertEqual(reader.path('/remote/study/b.json'),Path(d).resolve()/'b.json')
            self.assertEqual(reader.path('relative.json'),Path(d).resolve()/'relative.json')

    def test_complete_filesystem_reconciliation(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan,batch,cache,write=filesystem_fixture(d)
            report=a.audit_batch(root/'plan.json',batch,root=root)
            self.assertTrue(report['safe_to_advance']);self.assertEqual(report['fresh_case_starts'],2)
            self.assertEqual(report['case_disposition_and_validation_counts']['exact_byte_pass_reconfirmed'],2)

    def test_cached_outcome_tampering_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan,batch,cache,write=filesystem_fixture(d)
            cp=next(p for p in cache.glob('*.json') if p.name!='context.json')
            value=json.loads(cp.read_bytes());value['receipt']['observation']['status']='FAIL';write(cp,value)
            with self.assertRaisesRegex(ValueError,'cache receipt disagreement'):a.audit_batch(root/'plan.json',batch,root=root)

    def test_reported_physical_case_starts_recounted(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan,batch,cache,write=filesystem_fixture(d)
            summary=json.loads((batch/'summary.json').read_bytes());summary['case_starts']=0;write(batch/'summary.json',summary)
            with self.assertRaisesRegex(ValueError,'summary count'):a.audit_batch(root/'plan.json',batch,root=root)

    def test_source_metadata_gzip_pin_mutation_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan,batch,cache,write=filesystem_fixture(d)
            path=root/'metadata.json.gz';raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
            with self.assertRaisesRegex(ValueError,'file hash drift'):a.audit_batch(root/'plan.json',batch,root=root)

    def test_next_public_phase_rechecks_raw_cached_battery_without_new_starts(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan,batch,cache,write=filesystem_fixture(d)
            state=json.loads((root/'state.json').read_bytes());state['phase']=1
            plan['state_path']='state-next.json';plan['state_file_sha256']=write('state-next.json',state);plan['state_sha256']=a.sha(state)
            plan_pin=write('plan-next.json',plan);next_batch=root/'batch-next';next_batch.mkdir()
            summary=json.loads((batch/'summary.json').read_bytes())
            for name in ('observations.json','diagnostics.json','unreconciled_assignments.json'):
                (next_batch/name).write_bytes((batch/name).read_bytes())
            summary.update(plan_sha256=plan_pin,state_sha256=plan['state_sha256'],cached_units=1,case_starts=0,
                retained_bytes_before_summary=sum(p.stat().st_size for p in next_batch.iterdir()))
            write(next_batch/'summary.json',summary)
            report=a.audit_batch(root/'plan-next.json',next_batch,root=root)
            self.assertTrue(report['safe_to_advance']);self.assertEqual(report['cached_units'],1)
            self.assertEqual(report['fresh_case_starts'],0);self.assertEqual(report['raw_batteries_checked'],1)

    def test_cached_raw_journal_hash_mutation_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,plan,batch,cache,write=filesystem_fixture(d)
            journal=next((batch/'batteries').glob('*/cases.jsonl'));journal.write_bytes(journal.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'journal hash'):a.audit_batch(root/'plan.json',batch,root=root)


if __name__=='__main__':unittest.main()
