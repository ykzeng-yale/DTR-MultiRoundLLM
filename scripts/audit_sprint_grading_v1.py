"""Data-only independent recount of immutable sprint grading evidence.

No frozen collector/observer is imported; no candidate, model, subprocess,
network, pickle or source-case payload execution occurs. Hash-bound source case
METADATA supplies expectations' hashes/sizes, never their values. Stdout bytes
were deliberately not retained by the grader: non-identical token comparisons
remain trusted pinned-observer assertions, an explicit evidence limitation.
"""
import argparse
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

VERSION='sprint-grading-independent-metadata-recount-v1'
BATCH_VERSION='sprint-qualified-batch-grading-v1'
EXECUTION_VERSION='stdio-sprint-bwrap-strict-v4'
OBSERVER_VERSION='stdio-sprint-finite-operational-grade-v4'
EXTRACTOR='single-python-fence-or-raw-utf8-v1'
DIGEST=re.compile('[0-9a-f]{64}')
CAPS={'stdin_bytes':16<<20,'stdout_bytes':16<<20,'stderr_bytes':256<<10,
      'source_bytes':1<<20,'memory_bytes':1<<30,'cpu_soft_seconds':4,
      'cpu_hard_seconds':5,'wall_seconds':8.0,'file_bytes':16<<20,'open_files':64}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def sha(value):return hashlib.sha256(canonical(value)).hexdigest()
def text_sha(value):return hashlib.sha256(value.encode('utf-8','strict')).hexdigest()
def require(condition,reason):
    if not condition:raise ValueError(reason)


def finite(value):return type(value) in (int,float) and math.isfinite(value) and value>=0

def file_sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):result.update(block)
    return result.hexdigest()


def extract(raw):
    text_sha(raw)
    if '```' not in raw:return raw
    blocks=list(re.finditer(r'```([^\n]*)\n(.*?)```',raw,re.S))
    require(len(blocks)==1 and raw.count('```')==2 and blocks[0].group(1).strip().lower() in ('','python','python3','py'),'extraction drift')
    return blocks[0].group(2)


class Reader:
    def __init__(self,root,mappings=()):
        self.root=Path(root).resolve();self.mappings=[]
        for item in mappings:
            old,new=item.split('=',1);self.mappings.append((old.rstrip('/'),Path(new).resolve()))
        self.mappings.sort(key=lambda item:-len(item[0]));self.bytes_read=0;self.files={}
    def path(self,value):
        value=str(value)
        for old,new in self.mappings:
            if value==old or value.startswith(old+'/'):return new/value[len(old):].lstrip('/')
        p=Path(value);return p if p.is_absolute() else self.root/p
    def raw(self,value,cap,expected=None):
        path=self.path(value);require(not path.is_symlink(),'evidence symlink')
        require(path.stat().st_size<=cap,'evidence byte cap')
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        require(expected is None or digest==expected,'evidence file hash drift')
        self.bytes_read+=len(raw);self.files[str(path)]={'bytes':len(raw),'sha256':digest}
        return raw
    def json(self,value,cap,expected=None):return json.loads(self.raw(value,cap,expected))
    def metadata(self,reference):
        path=self.path(reference['path']);require(path.stat().st_size==reference['stored_bytes'],'metadata stored size')
        self.raw(path,16<<20,reference['sha256'])
        with gzip.open(path,'rb') as stream:raw=stream.read((16<<20)+1)
        require(len(raw)<=16<<20 and len(raw)==reference['plain_bytes'],'metadata plaintext size')
        return json.loads(raw)


def aggregate(values):
    if any(v==0 for v in values):return {'status':'FAIL','value':0,'bounds':[0,0]}
    if not values or any(v is None for v in values):return {'status':'INCOMPLETE','value':None,'bounds':[0,1]}
    return {'status':'PASS','value':1,'bounds':[1,1]}


def make_receipts(audit,result):
    common={'elapsed_seconds':audit['elapsed_seconds'],'case_starts':result['case_starts'],
            'audit_sha256':sha(audit),'primitive_id':audit['primitive_id']}
    grade=result['primary'];reason=None if grade['value'] is not None else audit['unavailability_reason']
    obs={**common,'status':grade['status'],'reason':reason} if audit['scope']=='public' else {
        **common,'status':'OBSERVED' if grade['value'] is not None else 'UNAVAILABLE','value':grade['value'],'reason':reason}
    fields=('grading_unit_id','root','program_sha256','scope','observer_sha256')
    primary={**{k:audit[k] for k in fields},'observation':obs};diagnostic=None
    if result['diagnostic'] is not None:
        g=result['diagnostic'];diagnostic={**{k:audit[k] for k in fields},'scope':'private_input_disjoint',
            'observation':{**common,'primitive_id':sha(['private_input_disjoint',audit['grading_unit_id'],audit['root'],audit['program_sha256'],audit['observer_sha256']]),
                'status':'OBSERVED' if g['value'] is not None else 'UNAVAILABLE','value':g['value'],
                'reason':None if g['value'] is not None else audit['unavailability_reason']}}
    return primary,diagnostic


def recount_battery(audit,instrument,rows,assignment,entry,metadata,*,runtime_pin,source_pin,bindings):
    """Pure recount: all case assignments, trusted receipt law and zero proofs."""
    scope=assignment['scope'];count=entry[scope]['case_count'];source=metadata[scope]
    require(len(source)==count and [m['ordinal'] for m in source]==list(range(count)),'source metadata ordinal ledger')
    if scope=='private':require(sha(source)==entry['private']['case_metadata_sha256'],'source metadata canonical pin')
    require(len(rows)==count and [r['case_ordinal'] for r in rows]==list(range(count)),'raw case ordinal completeness')
    require(audit['raw_stdout_retained'] is False and audit['raw_stderr_retained'] is False,'raw-output transport changed')
    require(finite(audit['elapsed_seconds']),'invalid audit wall cost')
    diag=set(entry['private']['private_input_disjoint_ordinals']) if scope=='private' else set()
    if scope=='private':
        public_inputs={r['stdin_sha256'] for r in metadata['public']}
        require(diag=={i for i,m in enumerate(source) if m['stdin_sha256'] not in public_inputs},'diagnostic membership drift')
        require(bool(diag),'empty diagnostic')
    instrument_pin=sha(instrument) if instrument is not None else None
    if instrument is not None:
        require(instrument['version']==OBSERVER_VERSION and instrument['scope']==scope and instrument['caps']==CAPS and
                instrument['normalization']==entry['normalization'] and instrument['runtime_manifest_sha256']==runtime_pin and
                instrument['source_contract_sha256']==sha([source_pin,assignment['root'],entry['root_source_sha256'],scope]) and
                instrument['source_sha256s']==bindings,'instrument law/source pin')
        require(len(instrument['cases'])==count,'instrument case completeness')
    values=[];diag_values=[];starts=0;first_zero=None;first_diag_zero=None;stats=Counter()
    for i,(row,m) in enumerate(zip(rows,source)):
        require(row['case_id']==assignment['root']+':'+scope+':'+str(i) and row['diagnostic_member']==(i in diag),'source case identity/membership')
        if 'case_sha256' in row:
            require(instrument is not None and row['case_sha256']==instrument['cases'][i]['case_sha256'],'case hash drift')
        else:require(row.get('source_complete_case_ledger_sha256')==entry[scope]['cases_sha256'],'unattempted source ledger drift')
        binding=None
        if instrument is not None:
            binding=instrument['cases'][i]
            require(binding['case_id']==row['case_id'] and binding['scope']==scope and all(binding[k]==m[k] for k in ('stdin_sha256','stdin_bytes','expected_stdout_sha256','expected_stdout_bytes')),'source metadata/instrument disagreement')
        disposition=row['disposition'];value=row['outcome'];stats[disposition]+=1
        require(value is None or type(value) is int and value in (0,1),'binary/unknown case outcome')
        if disposition=='EXECUTED':
            starts+=1;r=row['receipt'];e=r['execution']
            require(binding is not None and r['version']==OBSERVER_VERSION and all(r[k]==v for k,v in binding.items()) and
                    r['artifact_sha256']==assignment['program_sha256'] and r['instrument_sha256']==instrument_pin and
                    r['normalization']==entry['normalization'] and r['outcome']==value,'executed observer identity')
            require(e['version']==EXECUTION_VERSION and e['source_sha256']==assignment['program_sha256'] and
                    e['stdin_sha256']==m['stdin_sha256'] and e['stdin_bytes']==m['stdin_bytes'] and
                    e['caps']==CAPS and e['runtime_manifest_sha256']==runtime_pin and 'stdout' not in e and 'stderr' not in e,'executed strict identity/raw exclusion')
            require(finite(e['seconds']),'case cost')
            if e['disposition']=='observer_unavailable':
                require(value is None and r['status']=='INCOMPLETE' and e['outcome_available'] is False and r['reason'],'observer unavailable cannot be zero')
            elif e['disposition']=='operational_failure':
                require(value==0 and r['status']=='FAIL' and e['outcome_available'] is True and e['payload_started'] is True and e['cleanup'] is True and r['reason']==e['failure'],'operational failure requires strict bootstrap/zero')
            else:
                require(e['disposition']=='completed' and e['returncode']==0 and e['cleanup'] is True and e['payload_started'] is True and e['outcome_available'] is True and
                        type(e['stdout_bytes']) is int and 0<=e['stdout_bytes']<=CAPS['stdout_bytes'] and DIGEST.fullmatch(e['stdout_sha256']) and value in (0,1) and r['status']==('PASS' if value else 'FAIL'),'completed comparison receipt')
                identical=e['stdout_sha256']==m['expected_stdout_sha256'] and e['stdout_bytes']==m['expected_stdout_bytes']
                require(not identical or value==1,'exact-byte equal output falsely failed')
                stats['exact_byte_pass_reconfirmed' if identical else 'comparison_requires_trusted_observer_flag']+=1
        elif disposition=='OBSERVER_UNAVAILABLE':
            starts+=1;require(value is None and row.get('reason'),'supervisor unavailable cannot be zero')
        elif disposition=='SKIPPED_KNOWN_ZERO':
            require(value is None and first_zero is not None and row['primary_zero_witness_ordinal']==first_zero and
                    row['diagnostic_zero_witness_ordinal']==first_diag_zero and (i not in diag or first_diag_zero is not None),'invalid zero-witness short circuit')
        elif disposition=='SKIPPED_KNOWN_SOURCE_ZERO':
            require(len(assignment['program'].encode())>CAPS['source_bytes'] and value==0 and row['reason']=='source_byte_cap','false source-resource zero')
        elif disposition in ('UNATTEMPTED_GLOBAL_CAP','UNATTEMPTED_OBSERVER_UNAVAILABLE'):
            require(value is None and row.get('reason'),'administrative unattempted cannot be zero')
        else:raise ValueError('undeclared case disposition')
        if value==0:
            if first_zero is None:first_zero=i
            if i in diag and first_diag_zero is None:first_diag_zero=i
        values.append(value)
        if i in diag:diag_values.append(value)
    result={'primary':aggregate(values),'diagnostic':aggregate(diag_values) if scope=='private' else None,
            'case_starts':starts,'assigned_cases':count,'accounted_cases':count}
    reported=audit['result']
    require(all(reported.get(k)==v for k,v in result.items()),'battery aggregate/count disagreement')
    if 'primary_zero_witness_ordinal' in reported:require(reported['primary_zero_witness_ordinal']==first_zero and reported['diagnostic_zero_witness_ordinal']==first_diag_zero,'reported witness drift')
    if 'instrument_sha256' in reported:require(reported['instrument_sha256']==instrument_pin,'result instrument hash drift')
    return result,stats


def audit_batch(plan_path,batch_path,*,root='.',path_prefix=()):
    reader=Reader(root,path_prefix);plan=reader.json(plan_path,1<<20);batch=reader.path(batch_path)
    require(plan['version']==BATCH_VERSION and plan['workers']==4,'batch law')
    cap=min(plan['max_input_file_bytes'],2<<30)
    config=reader.json(plan['study_config_path'],cap,plan['study_config_file_sha256'])
    state=reader.json(plan['state_path'],cap,plan['state_file_sha256'])
    assignments=reader.json(plan['assignments_path'],cap,plan['assignments_file_sha256'])
    require(config['config_sha256']==sha({k:v for k,v in config.items() if k!='config_sha256'})==plan['study_config_sha256'] and
            state['config_sha256']==config['config_sha256'] and sha(state)==plan['state_sha256'] and sha(assignments)==plan['assignments_sha256'],'state/config/assignment pins')
    ledger={r['assignment_id']:r for r in config['ledger']}
    require(len(ledger)==len(config['ledger'])==len(state['rows']) and {r['assignment_id'] for r in state['rows']}==set(ledger),'all-assigned state')
    require(all(all(r.get(k)==v for k,v in ledger[r['assignment_id']].items()) for r in state['rows']),'frozen state assignment drift')
    scope=plan['scope'];require(scope in ('public','private') and config['pins'][scope+'_observer']==plan['observer_sha256'],'scope/observer law')
    if scope=='private':
        require(state['phase']==3 and state['requests']==[] and all(r['disposition']!='active' for r in state['rows']),'private terminal gate')
        expected=set()
        for row in state['rows']:
            if row['final_program'] is not None:
                require(extract(row['final_raw'])==row['final_program'],'terminal raw extraction')
                expected.add((row['initial_execution_id'],row['root'],text_sha(row['final_program'])))
    else:require(state['phase'] in (0,1,2),'public phase')
    assigned={};units={(i['initial_execution_id'],i['root']) for i in config['initials']}
    for a in assignments:
        k=(a['grading_unit_id'],a['root'],a['program_sha256']);require(k not in assigned and k[:2] in units and
            a['scope']==scope and a['extractor']==EXTRACTOR and text_sha(a['program'])==k[2],'assigned artifact identity/duplicates');assigned[k]=a
    if scope=='private':require(set(assigned)==expected,'complete terminal artifact assignments')
    manifest=reader.json(plan['source_manifest_path'],1<<20,plan['source_manifest_sha256'])
    index_ref=manifest['artifacts']['instruments'];index=reader.json(index_ref['path'],2<<20,index_ref['sha256'])
    att=reader.json(plan['attestation_path'],2<<20,plan['attestation_sha256'])
    require(att['passed'] is True and att['plan_sha256']==plan['qualification_plan_sha256'] and att['caps']==CAPS,'qualified instrument pin')
    qualification_plan=reader.json(plan['qualification_plan_path'],1<<20,plan['qualification_plan_sha256'])
    bindings={name:plan['files'][path] for name,path in {'execution':'experiments/measurement_sprint_v4/execution_v4.py',
        'runtime':'experiments/measurement_sprint_v4/runtime_v4.py','observer':'experiments/measurement_sprint_v4/stdio_v4.py',
        'qualification':'experiments/containment/stdio_sprint_qualification_v4.py'}.items()}
    for path,pin in plan['files'].items():require(file_sha(reader.path(path))==pin,'frozen execution source drift')
    summary=reader.json(batch/'summary.json',2<<20)
    observations=reader.json(batch/'observations.json',plan['max_output_file_bytes'],summary['observations_file_sha256'])
    diagnostics=reader.json(batch/'diagnostics.json',plan['max_output_file_bytes'],summary['diagnostics_file_sha256'])
    missing=reader.json(batch/'unreconciled_assignments.json',plan['max_output_file_bytes'])
    require(summary['version']==BATCH_VERSION and summary['plan_sha256']==file_sha(reader.path(plan_path)) and
            summary['scope']==scope and summary['contract_sha256']==plan['contract_sha256'] and summary['state_sha256']==plan['state_sha256'] and
            summary['config_sha256']==config['config_sha256'] and summary['job_id']==att['job_id'] and summary['workers']==4 and
            summary['network_calls']==summary['model_calls']==0 and summary['private_expected_answers_in_policy'] is False,'summary science/job/pin drift')
    require(sha(observations)==summary['observations_sha256'],'observation canonical pin')
    cache=reader.path(plan['cache_dir'])/config['config_sha256']
    context=reader.json(cache/'context.json',1<<20)
    require(context=={'version':BATCH_VERSION,'config_sha256':config['config_sha256'],'contract_sha256':plan['contract_sha256'],
        'source_manifest_sha256':plan['source_manifest_sha256'],'observer_sha256s':{s:config['pins'][s+'_observer'] for s in ('public','private')},
        'runtime_manifest_sha256':att['runtime_manifest_sha256'],'attestation_sha256':plan['attestation_sha256'],'job_id':att['job_id']},'cache crossed frozen allocation/vector law')
    stats=Counter();expected_diag=[];seen=set();fresh_starts=0;cached=0;assigned_cases=sum(index[a['root']][scope]['case_count'] for a in assignments)
    metadata_cache={};checked_audits=set();new_cache_bytes=0
    for receipt in observations:
        require(set(receipt)=={'grading_unit_id','root','program_sha256','scope','observer_sha256','observation'},'sanitized receipt schema')
        key=(receipt['grading_unit_id'],receipt['root'],receipt['program_sha256'])
        require(key in assigned and key not in seen and receipt['scope']==scope and receipt['observer_sha256']==plan['observer_sha256'],'receipt assigned identity');seen.add(key)
        a=assigned[key];identifier=sha([scope,*key,plan['observer_sha256']]);cache_path=cache/(identifier+'.json')
        saved=reader.json(cache_path,1<<20);require(saved['receipt']==receipt,'cache receipt disagreement')
        audit_path=reader.path(saved['audit_path']);raw_audit=reader.raw(audit_path,2<<20,saved['audit_file_sha256']);audit=json.loads(raw_audit)
        require(all(audit[k]==receipt[k] for k in ('grading_unit_id','root','program_sha256','scope','observer_sha256')) and
                audit['version']==BATCH_VERSION and audit['primitive_id']==identifier and audit['config_sha256']==config['config_sha256'] and
                audit['runtime_manifest_sha256']==att['runtime_manifest_sha256'],'raw battery artifact/vector identity')
        is_new=audit_path.is_relative_to(batch.resolve())
        if is_new:require(audit['state_sha256']==plan['state_sha256'],'new audit state pin');new_cache_bytes+=cache_path.stat().st_size
        else:cached+=1
        entry=index[a['root']]
        if a['root'] not in metadata_cache:metadata_cache[a['root']]=reader.metadata(entry['case_metadata'])
        instrument=None
        if audit['instrument_path'] is not None:instrument=reader.json(audit['instrument_path'],16<<20,audit['instrument_file_sha256'])
        journal_path=reader.path(audit['case_journal_path']);require(file_sha(journal_path)==audit['case_journal_sha256'],'raw case journal hash')
        rows=[]
        with journal_path.open('rb') as stream:
            for line in stream:
                require(len(line)<=8192,'case receipt byte cap');rows.append(json.loads(line))
        if instrument is None:
            pin=next((r['receipt']['instrument_sha256'] for r in rows if r['disposition']=='EXECUTED'),None)
            if pin is not None:instrument=reader.json(audit_path.parent.parent.parent/'instruments'/(pin+'.json'),16<<20)
        result,counts=recount_battery(audit,instrument,rows,a,entry,metadata_cache[a['root']],runtime_pin=att['runtime_manifest_sha256'],source_pin=plan['source_manifest_sha256'],bindings=bindings)
        reconstructed,diagnostic=make_receipts(audit,result)
        require(reconstructed==receipt and saved.get('diagnostic')==diagnostic,'sanitized grade differs from independently recounted raw battery')
        if diagnostic is not None:expected_diag.append(diagnostic)
        if is_new:fresh_starts+=result['case_starts']
        stats.update(counts);stats['units_'+receipt['observation']['status']]+=1;checked_audits.add(str(audit_path))
    missing_keys={(r['grading_unit_id'],r['root'],r['program_sha256']) for r in missing}
    require(len(missing_keys)==len(missing) and missing_keys==set(assigned)-seen and all(r['scope']==scope and r['disposition']=='UNRECONCILED_SUPERVISOR_FAILURE' for r in missing),'missing assignments silently lost')
    require(diagnostics==expected_diag,'diagnostic complete ordered receipts')
    require(summary['assigned_units']==len(assignments) and summary['accounted_units']==len(seen) and summary['unreconciled_units']==len(missing) and
            summary['assigned_cases']==assigned_cases and summary['cached_units']==cached and summary['case_starts']==fresh_starts and
            summary['status']==('COMPLETE' if not missing else 'UNRECONCILED_FAILURE'),'summary count/disposition disagreement')
    require(summary['remaining_case_reservation']==512*sum(index[assigned[k]['root']][scope]['case_count'] for k in missing_keys),'remaining assignment reservation disagreement')
    require(0<=fresh_starts<=plan['max_case_starts'] and finite(summary['cpu_seconds']) and finite(summary['elapsed_seconds']),'resource counters')
    batch_bytes=sum(p.stat().st_size for p in batch.rglob('*') if p.is_file())
    require(summary['retained_bytes_before_summary']==batch_bytes-(batch/'summary.json').stat().st_size+new_cache_bytes,'retained file bytes disagreement')
    require(batch_bytes+new_cache_bytes<=plan['max_retained_bytes'],'retained cap exceeded')
    resource_violations=[]
    for actual,ceiling,name in ((summary['cpu_seconds'],plan['max_cpu_seconds'],'cpu'),(summary['elapsed_seconds'],plan['max_wall_seconds'],'wall')):
        if actual>ceiling:resource_violations.append(name)
    require(not resource_violations,'reported resource cap violation')
    return {'version':VERSION,'status':'RECONCILED_COMPLETE' if not missing else 'RECONCILED_FAILURE','safe_to_advance':not missing,
        'scope':scope,'job_id':att['job_id'],'plan_file_sha256':file_sha(reader.path(plan_path)),
        'summary_file_sha256':file_sha(batch/'summary.json'),'source_manifest_sha256':plan['source_manifest_sha256'],
        'assigned_units':len(assignments),'accounted_units':len(seen),'unreconciled_units':len(missing),
        'assigned_cases':assigned_cases,'fresh_case_starts':fresh_starts,'cached_units':cached,'raw_batteries_checked':len(checked_audits),
        'case_disposition_and_validation_counts':dict(stats),'reported_cpu_seconds':summary['cpu_seconds'],
        'reported_elapsed_seconds':summary['elapsed_seconds'],'retained_bytes_recounted':batch_bytes+new_cache_bytes,
        'metadata_bytes_read':reader.bytes_read,'metadata_files_read':len(reader.files),
        'limitations':['This independently recounts source-bound metadata, identities, raw receipts, skips and aggregates; it executes no programs.',
            'Actual stdout bytes and normalized stdout hashes were not retained. Non-identical raw output comparisons rely on pinned trusted-observer flags.',
            'CPU/wall and payload bootstrap are recorded execution receipts, not independent live resource/security measurements.',
            'Case input/expectation values are not opened by this audit; source metadata is bound to the predecoded source manifest.',
            'No semantic truth, broad-family transport, fresh-execution independence or efficacy follows from this reconciliation.'],
        'model_calls':0,'candidate_executions':0,'private_values_reported':False}


def main():
    parser=argparse.ArgumentParser()
    for name in ('plan','batch','out'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('--path-prefix',action='append',default=[])
    args=parser.parse_args();args.out.mkdir(parents=False,exist_ok=False)
    try:
        result=audit_batch(args.plan,args.batch,root=args.root,path_prefix=args.path_prefix)
    except Exception as exc:
        result={'version':VERSION,'status':'RECONCILIATION_REFUSED','safe_to_advance':False,'exception_type':type(exc).__name__,
                'reason':str(exc) if isinstance(exc,ValueError) else 'evidence unavailable or malformed; inspect local raw files',
                'model_calls':0,'candidate_executions':0,'private_values_reported':False}
    (args.out/'report.json').write_bytes(canonical(result)+b'\n')
    print(json.dumps({k:result[k] for k in ('status','safe_to_advance')},sort_keys=True))
    if not result['safe_to_advance']:raise SystemExit(1)


if __name__=='__main__':main()
