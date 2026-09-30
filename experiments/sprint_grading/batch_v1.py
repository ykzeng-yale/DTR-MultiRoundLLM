"""Four-worker source-bound grading in the same owned GPU allocation.

Stdlib only. Expected answers stay in this trusted host supervisor; the strict
executor receives program/stdin alone. Private payloads open only after exact
terminal-state and assignment checks. Immutable caching is limited to a single
initial-execution vector, never across task repetitions. No job submission,
receiver call, bare execution fallback, automatic retry or source admission.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import threading
import time

from experiments.measurement_sprint_v4 import execution_v4 as execution
from experiments.measurement_sprint_v4 import runtime_v4 as runtime
from experiments.measurement_sprint_v4 import stdio_v4 as observer

VERSION = 'sprint-qualified-batch-grading-v1'
EXTRACTOR = 'single-python-fence-or-raw-utf8-v1'
ROOT = Path(__file__).resolve().parents[2]
MAX_ROOT_PLAIN = 512 << 20
CASE_RESERVE = 512
OBS_RESERVE = 4096
CASE_RECEIPT_CAP = 8192


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(value): return hashlib.sha256(canonical(value)).hexdigest()
def text_sha(value): return hashlib.sha256(value.encode('utf-8','strict')).hexdigest()


def primitive_id(scope, unit, root, program_sha256, observer_sha256):
    return sha([scope,unit,root,program_sha256,observer_sha256])


def bound_json(path, expected_sha256, cap):
    path=Path(path)
    if path.is_symlink(): raise ValueError('pinned data symlink refused')
    with path.open('rb') as stream: raw=stream.read(cap+1)
    if len(raw)>cap or hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('pinned data byte/hash drift')
    return json.loads(raw)


def extract_program(raw):
    text_sha(raw)
    if '```' not in raw: return raw
    blocks=list(re.finditer(r'```([^\n]*)\n(.*?)```',raw,re.S))
    if len(blocks)!=1 or raw.count('```')!=2 or blocks[0].group(1).strip().lower() not in ('','python','python3','py'):
        raise ValueError('pinned extraction failed')
    return blocks[0].group(2)


def check_state(state, config, scope, assignments):
    """Pure gate; caller must run this BEFORE reading private payloads."""
    if (config.get('config_sha256')!=sha({k:v for k,v in config.items() if k!='config_sha256'}) or
        state.get('config_sha256')!=config['config_sha256'] or config.get('extractor')!=EXTRACTOR):
        raise ValueError('frozen state/config/extractor drift')
    ledger={r['assignment_id']:r for r in config['ledger']}
    if len(ledger)!=len(config['ledger']) or len(state['rows'])!=len(ledger) or {r['assignment_id'] for r in state['rows']}!=set(ledger):
        raise ValueError('complete assigned state ledger required')
    for row in state['rows']:
        frozen=ledger[row['assignment_id']]
        if any(row.get(k)!=v for k,v in frozen.items()):
            raise ValueError('assigned branch state drift')
    if scope=='private':
        if state['phase']!=3 or state['requests'] or any(r['disposition']=='active' for r in state['rows']):
            raise ValueError('private payload requires exact terminal phase3')
        expected={}
        for row in state['rows']:
            program=row['final_program']
            if program is not None:
                if row['final_raw'] is None or extract_program(row['final_raw'])!=program:
                    raise ValueError('terminal extraction/raw artifact drift')
                key=(row['initial_execution_id'],row['root'],text_sha(program))
                expected[key]=program
        actual={(r['grading_unit_id'],r['root'],r['program_sha256']):r['program'] for r in assignments}
        if actual!=expected:
            raise ValueError('all terminal artifact grading assignments required')
    elif scope=='public':
        if state['phase'] not in (0,1,2): raise ValueError('public stage phase')
    else: raise ValueError('scope')
    units={(r['initial_execution_id'],r['root']) for r in config['initials']}
    seen=set()
    for row in assignments:
        fields={'grading_unit_id','root','program','program_sha256','scope','extractor'}
        if set(row) not in (fields,fields|{'raw_sha256'}) or row['scope']!=scope or row['extractor']!=EXTRACTOR:
            raise ValueError('exact artifact grading assignment schema')
        if ((row['grading_unit_id'],row['root']) not in units or
            type(row['program']) is not str or text_sha(row['program'])!=row['program_sha256']):
            raise ValueError('assigned unit/root/program identity drift')
        if len(row['grading_unit_id'].encode())>128 or len(row['root'].encode())>128:
            raise ValueError('bounded frozen assignment identity')
        key=(row['grading_unit_id'],row['root'],row['program_sha256'])
        if key in seen: raise ValueError('duplicate grading primitive assignment')
        seen.add(key)


def qualify_allocation(plan_path, out, freeze_path):
    """Trusted fixed controls in a subprocess, once per job BEFORE model calls.

    The qualification's CPU rlimit belongs to its own process, never the long-
    lived GPU coordinator. No downloads or task/receiver execution are added.
    Caller already froze/verified qualification source and its complete plan.
    """
    plan=json.loads(Path(plan_path).read_bytes())
    output=Path(out).absolute()
    if output.exists(): raise ValueError('fresh allocation qualification output required')
    command=[sys.executable,str(ROOT/'scripts/qualify_stdio_sprint_v4.py'),
             '--plan',str(plan_path),'--out',str(output),'--freeze',str(freeze_path)]
    process=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                           timeout=plan['global_wall_seconds']+15,close_fds=True)
    if process.returncode!=0 or not (output/'attestation.json').is_file():
        # Raw trusted-control stdout/stderr stay with qualification evidence;
        # no automatic repeat or fallback is permitted.
        output.mkdir(parents=True,exist_ok=True)
        (output/'supervisor.returncode.json').write_bytes(canonical({'returncode':process.returncode})+b'\n')
        raise RuntimeError('fresh allocation qualification failed; evidence retained')
    path=output/'attestation.json'
    return {'attestation_path':str(path),'attestation_sha256':runtime.file_hash(path),
            'qualification_output':str(output)}


def verify_allocation_attestation(path, expected_sha256):
    if runtime.file_hash(path)!=expected_sha256:
        raise ValueError('exact same-worker attestation hash drift')
    attestation=execution.verify_attestation(path)
    job=os.environ.get('SLURM_JOB_ID')
    if job is None or attestation.get('job_id')!=job:
        raise ValueError('qualification must belong to this same allocation')
    if os.environ.get('SLURM_CPUS_PER_TASK') is not None and int(os.environ['SLURM_CPUS_PER_TASK'])<8:
        raise ValueError('four receiver slots plus four grader CPUs require8 allocated CPUs')
    if attestation['caps']!=execution.DEFAULT_CAPS:
        raise ValueError('prospective source-cap qualification required')
    return attestation


class Budget:
    def __init__(self, plan, assigned_cases, assigned_units):
        self.plan=plan;self.started=time.monotonic();self.lock=threading.RLock()
        self.deadline=datetime.fromisoformat(plan['owner_deadline_iso'].replace('Z','+00:00')).timestamp()
        self.cpu_base=self.cpu();self.retained=0;self.case_starts=0;self.stop_reason=None
        self.pending_case_reserve=CASE_RESERVE*assigned_cases
        self.final_reserve=OBS_RESERVE*assigned_units+(2<<20)
        self.active_receipt_reserve=0
        self.case_start_cap=plan['max_case_starts']
        if self.pending_case_reserve+self.final_reserve>plan['max_retained_bytes']:
            raise ValueError('complete assigned-case/receipt reservation exceeds retained cap')
    @staticmethod
    def cpu():
        own=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
        return own.ru_utime+own.ru_stime+children.ru_utime+children.ru_stime
    def remaining(self):
        return min(self.plan['max_wall_seconds']-(time.monotonic()-self.started),self.deadline-time.time())
    def check(self, *, start=False):
        with self.lock:
            if self.stop_reason: return False
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            if self.remaining()<execution.DEFAULT_CAPS['wall_seconds']+6:
                self.stop_reason='global_wall_or_owner_deadline'
            elif self.cpu()-self.cpu_base>self.plan['max_cpu_seconds']-4*(execution.DEFAULT_CAPS['cpu_hard_seconds']+1):
                self.stop_reason='global_cpu_cap'
            elif rss>self.plan['max_rss_bytes']:
                self.stop_reason='supervisor_rss_cap'
            elif start and self.case_starts>=self.case_start_cap:
                self.stop_reason='global_case_start_cap'
            elif start and self.retained+self.pending_case_reserve+self.final_reserve+self.active_receipt_reserve+CASE_RECEIPT_CAP>self.plan['max_retained_bytes']:
                self.stop_reason='pre_start_retained_cap'
            if self.stop_reason:return False
            if start:
                self.case_starts+=1;self.active_receipt_reserve+=CASE_RECEIPT_CAP
            return True
    def unavailable(self, reason):
        with self.lock:
            if self.stop_reason is None:self.stop_reason=reason
    def write(self, path, raw, *, case_record=False, final=False):
        with self.lock:
            reserve=self.pending_case_reserve-(CASE_RESERVE if case_record else 0)
            if case_record and (len(raw)>CASE_RECEIPT_CAP or reserve<0):
                raise ValueError('bounded case journal record required')
            started=(case_record and json.loads(raw).get('disposition') in ('EXECUTED','OBSERVER_UNAVAILABLE'))
            active=self.active_receipt_reserve-(CASE_RECEIPT_CAP if started else 0)
            if active<0:raise ValueError('case start/receipt reservation mismatch')
            additional=0 if final else reserve+self.final_reserve+active
            if self.retained+len(raw)+additional>self.plan['max_retained_bytes']:
                raise RuntimeError('pre-write retained cap; complete assignment reservation retained')
            path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('ab' if case_record else 'xb') as stream:
                stream.write(raw);stream.flush()
            self.retained+=len(raw)
            if case_record:
                self.pending_case_reserve=reserve;self.active_receipt_reserve=active


class SourceBundle:
    """Hash-checked gzip root payloads; no remote loader or unsafe unpickler."""
    def __init__(self, manifest_path, manifest_sha256, bundle_dir, cap):
        self.manifest=bound_json(manifest_path,manifest_sha256,1<<20)
        self.directory=Path(bundle_dir).resolve(strict=True)
        reference=self.manifest['artifacts']['instruments']
        path=ROOT/reference['path']
        if not path.resolve().is_relative_to(self.directory):
            raise ValueError('sealed index outside source bundle')
        self.index=bound_json(path,reference['sha256'],cap)
        self.instruments={};self.lock=threading.RLock()
    def count(self, root, scope):
        if root not in self.index: raise ValueError('root outside frozen source bundle')
        return self.index[root][scope]['case_count']
    def load(self, root, scope):
        entry=self.index[root];reference=entry[scope]
        path=ROOT/reference['path']
        if (path.is_symlink() or not path.resolve().is_relative_to(self.directory) or
            path.stat().st_size!=reference['stored_bytes'] or runtime.file_hash(path)!=reference['sha256']):
            raise ValueError('sealed case payload hash/size/path drift')
        with gzip.open(path,'rb') as stream: raw=stream.read(MAX_ROOT_PLAIN+1)
        if len(raw)>MAX_ROOT_PLAIN or len(raw)!=reference['plain_bytes']:
            raise ValueError('sealed decompressed root cap/drift')
        cases=json.loads(raw)
        if (len(cases)!=reference['case_count'] or sha(cases)!=reference['cases_sha256'] or
            not cases or any(c.get('scope')!=scope for c in cases)):
            raise ValueError('complete nonempty ordered sealed case ledger required')
        return cases,entry


def battery_grade(code, cases, instrument, *, scope, runner, budget, record,
                  diagnostic_ordinals=None):
    """Execute the union needed by primary and diagnostic conjunctions.

    A proved primary zero may skip only cases irrelevant to a still-unresolved
    diagnostic. No unknown observation is called zero. Every case keeps its
    source ordinal and disposition; no second execution is used to rescue it.
    """
    pin=observer.instrument_sha256(instrument);primary=[];diagnostic=[]
    diag_set=set(diagnostic_ordinals or ())
    if diagnostic_ordinals is not None and (not diag_set or any(type(i) is not int or not 0<=i<len(cases) for i in diag_set)):
        raise ValueError('nonempty separately declared diagnostic membership')
    starts=0;known_primary=None;known_diag=None
    for ordinal,case in enumerate(cases):
        member=ordinal in diag_set
        identity={'case_ordinal':ordinal,'case_id':case['case_id'],
                  'case_sha256':instrument['cases'][ordinal]['case_sha256'],
                  'diagnostic_member':member}
        if known_primary is not None and (not member or known_diag is not None):
            row={**identity,'disposition':'SKIPPED_KNOWN_ZERO','outcome':None,
                 'primary_zero_witness_ordinal':known_primary,
                 'diagnostic_zero_witness_ordinal':known_diag}
        elif not budget.check(start=True):
            row={**identity,'disposition':'UNATTEMPTED_GLOBAL_CAP','outcome':None,
                 'reason':budget.stop_reason or 'batch_cap'}
            primary.append(None)
            if member:diagnostic.append(None)
        else:
            starts+=1
            try:
                receipt=observer.evaluate_case(code,case,instrument=instrument,
                    expected_instrument_sha256=pin,scope=scope,runner=runner)
                result=receipt['outcome']
                row={**identity,'disposition':'EXECUTED','outcome':result,'receipt':receipt}
                if result is None:budget.unavailable('observer_unavailable_no_retry')
            except Exception as exc:
                result=None;budget.unavailable('observer_integrity_or_supervisor_failure')
                row={**identity,'disposition':'OBSERVER_UNAVAILABLE','outcome':None,
                     'reason':'observer_integrity_or_supervisor_failure','exception_type':type(exc).__name__}
            primary.append(result)
            if member:diagnostic.append(result)
            if result==0:
                if known_primary is None:known_primary=ordinal
                if member and known_diag is None:known_diag=ordinal
        raw=canonical(row)+b'\n'
        record(raw)
    def aggregate(values,witness):
        if witness is not None:return {'status':'FAIL','value':0,'bounds':[0,0]}
        if any(v is None for v in values):return {'status':'INCOMPLETE','value':None,'bounds':[0,1]}
        return {'status':'PASS','value':1,'bounds':[1,1]}
    return {'primary':aggregate(primary,known_primary),
            'diagnostic':aggregate(diagnostic,known_diag) if diagnostic_ordinals is not None else None,
            'case_starts':starts,'assigned_cases':len(cases),'accounted_cases':len(cases),
            'primary_zero_witness_ordinal':known_primary,'diagnostic_zero_witness_ordinal':known_diag,
            'instrument_sha256':pin}


def _cache_context(directory, context):
    directory=Path(directory).resolve();directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    if directory.is_symlink():raise ValueError('owned immutable cache directory required')
    path=directory/'context.json'
    if path.exists():
        if path.read_bytes()!=canonical(context)+b'\n':
            raise ValueError('cache cannot cross config/source/runtime/allocation')
    else:
        with path.open('xb') as stream:stream.write(canonical(context)+b'\n')
    return directory


def observations_from_audit(audit):
    result=audit['result'];grade=result['primary'];scope=audit['scope']
    common={'elapsed_seconds':audit['elapsed_seconds'],'case_starts':result['case_starts'],
            'audit_sha256':sha(audit),'primitive_id':audit['primitive_id']}
    reason=None if grade['value'] is not None else audit['unavailability_reason']
    if scope=='public': observation={**common,'status':grade['status'],'reason':reason}
    else: observation={**common,'status':'OBSERVED' if grade['value'] is not None else 'UNAVAILABLE',
                       'value':grade['value'],'reason':reason}
    receipt={k:audit[k] for k in ('grading_unit_id','root','program_sha256','scope','observer_sha256')}
    receipt['observation']=observation;diag_receipt=None
    if result['diagnostic'] is not None:
        diagnostic=result['diagnostic']
        diag_receipt={**{k:receipt[k] for k in receipt if k!='observation'},'scope':'private_input_disjoint',
            'observation':{**common,'primitive_id':primitive_id('private_input_disjoint',audit['grading_unit_id'],
                audit['root'],audit['program_sha256'],audit['observer_sha256']),
                'status':'OBSERVED' if diagnostic['value'] is not None else 'UNAVAILABLE',
                'value':diagnostic['value'],'reason':None if diagnostic['value'] is not None else audit['unavailability_reason']}}
    return receipt,diag_receipt


def run_batch(plan_path, out, *, attestation_path=None):
    """Called only by a frozen owned worker release; no automatic submission."""
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_bytes())
    if plan.get('version')!=VERSION or plan['workers']!=4 or plan['scope'] not in ('public','private'):
        raise ValueError('exact four-worker grading version/scope')
    numeric=('max_wall_seconds','max_cpu_seconds','max_case_starts','max_retained_bytes',
             'max_rss_bytes','max_input_file_bytes','max_output_file_bytes')
    if any(type(plan[k]) is not int or plan[k]<(0 if k=='max_case_starts' else 1) for k in numeric):
        raise ValueError('finite positive frozen batch resource caps')
    for path,digest in plan['files'].items():
        if runtime.file_hash(ROOT/path)!=digest:raise ValueError('grader/observer source pin drift')
    config=bound_json(plan['study_config_path'],plan['study_config_file_sha256'],plan['max_input_file_bytes'])
    state=bound_json(plan['state_path'],plan['state_file_sha256'],plan['max_input_file_bytes'])
    assignments=bound_json(plan['assignments_path'],plan['assignments_file_sha256'],plan['max_input_file_bytes'])
    if (sha(state)!=plan['state_sha256'] or sha(assignments)!=plan['assignments_sha256'] or
        config['config_sha256']!=plan['study_config_sha256'] or
        config['pins'][plan['scope']+'_observer']!=plan['observer_sha256']):
        raise ValueError('exact batch/state/config/observer hashes required')
    check_state(state,config,plan['scope'],assignments)
    # No source private payload has been opened before this gate.
    source=SourceBundle(plan['source_manifest_path'],plan['source_manifest_sha256'],
                        plan['bundle_dir'],plan['max_input_file_bytes'])
    actual_attestation=attestation_path or plan['attestation_path']
    attestation=verify_allocation_attestation(actual_attestation,plan['attestation_sha256'])
    if runtime.file_hash(plan['qualification_plan_path'])!=plan['qualification_plan_sha256'] or attestation['plan_sha256']!=plan['qualification_plan_sha256']:
        raise ValueError('actual complete qualification plan identity drift')
    runner=execution.QualifiedRunner(actual_attestation)
    case_count=sum(source.count(a['root'],plan['scope']) for a in assignments)
    budget=Budget(plan,case_count,len(assignments));budget.check()
    output=Path(out).resolve();output.mkdir(mode=0o700,parents=False,exist_ok=False)
    context={'version':VERSION,'config_sha256':config['config_sha256'],
        'contract_sha256':plan['contract_sha256'],'source_manifest_sha256':plan['source_manifest_sha256'],
        'observer_sha256s':{s:config['pins'][s+'_observer'] for s in ('public','private')},
        'runtime_manifest_sha256':attestation['runtime_manifest_sha256'],
        'attestation_sha256':plan['attestation_sha256'],'job_id':attestation['job_id']}
    cache=_cache_context(Path(plan['cache_dir'])/config['config_sha256'],context)
    cached=[];pending=[];cached_diagnostics=[]
    for a in assignments:
        identifier=primitive_id(plan['scope'],a['grading_unit_id'],a['root'],a['program_sha256'],plan['observer_sha256'])
        path=cache/(identifier+'.json')
        if path.exists():
            saved=json.loads(path.read_bytes())
            expected={k:a[k] for k in ('grading_unit_id','root','program_sha256','scope')}
            if any(saved['receipt'][k]!=v for k,v in expected.items()) or saved['receipt']['observer_sha256']!=plan['observer_sha256']:
                raise ValueError('immutable primitive cache identity drift')
            if runtime.file_hash(saved['audit_path'])!=saved['audit_file_sha256']:
                raise ValueError('cached immutable battery audit drift')
            audit=json.loads(Path(saved['audit_path']).read_bytes())
            if (runtime.file_hash(audit['case_journal_path'])!=audit['case_journal_sha256'] or
                audit.get('instrument_path') is not None and runtime.file_hash(audit['instrument_path'])!=audit['instrument_file_sha256']):
                raise ValueError('cached full case/instrument audit drift')
            expected_receipt,expected_diagnostic=observations_from_audit(audit)
            if saved['receipt']!=expected_receipt or saved.get('diagnostic')!=expected_diagnostic:
                raise ValueError('cached sanitized outcome differs from frozen battery audit')
            cached.append(saved['receipt'])
            if saved.get('diagnostic') is not None:cached_diagnostics.append(saved['diagnostic'])
            # A cached primitive accounts this whole battery without new starts.
            budget.pending_case_reserve-=CASE_RESERVE*source.count(a['root'],plan['scope'])
        else:pending.append((a,identifier))
    all_instrument_headers={};header_lock=threading.RLock()
    def grade_impl(item):
        assignment,identifier=item;started=time.monotonic()
        cases,entry=source.load(assignment['root'],plan['scope'])
        caps=observer.caps_from_source_contract(entry['resource_contract'])
        if caps!=attestation['caps']:raise ValueError('sealed source/qualified resource contract drift')
        instrument=observer.freeze_instrument(cases,scope=plan['scope'],normalization=entry['normalization'],
            runtime_manifest_sha256=attestation['runtime_manifest_sha256'],
            source_contract_sha256=sha([plan['source_manifest_sha256'],assignment['root'],entry['root_source_sha256'],plan['scope']]),caps=caps)
        instrument_pin=observer.instrument_sha256(instrument)
        with header_lock:
            if instrument_pin not in all_instrument_headers:
                path=output/'instruments'/(instrument_pin+'.json')
                budget.write(path,canonical(instrument)+b'\n');all_instrument_headers[instrument_pin]=str(path)
        battery_dir=output/'batteries'/identifier;battery_dir.mkdir(parents=True,exist_ok=False)
        journal=battery_dir/'cases.jsonl'
        def record(raw):budget.write(journal,raw,case_record=True)
        diagnostic=(entry['private']['private_input_disjoint_ordinals'] if plan['scope']=='private' else None)
        result=battery_grade(assignment['program'],cases,instrument,scope=plan['scope'],runner=runner,
            budget=budget,record=record,diagnostic_ordinals=diagnostic)
        elapsed=time.monotonic()-started
        audit={'version':VERSION,'primitive_id':identifier,'scope':plan['scope'],
            'grading_unit_id':assignment['grading_unit_id'],'root':assignment['root'],
            'program_sha256':assignment['program_sha256'],'observer_sha256':plan['observer_sha256'],
            'config_sha256':config['config_sha256'],'state_sha256':plan['state_sha256'],
            'runtime_manifest_sha256':attestation['runtime_manifest_sha256'],
            'instrument_path':all_instrument_headers[instrument_pin],
            'instrument_file_sha256':runtime.file_hash(all_instrument_headers[instrument_pin]),
            'case_journal_path':str(journal),'case_journal_sha256':runtime.file_hash(journal),
            'result':result,'elapsed_seconds':elapsed,
            'unavailability_reason':budget.stop_reason or 'observer_unavailable',
            'raw_stdout_retained':False,'raw_stderr_retained':False}
        audit_path=battery_dir/'summary.json';budget.write(audit_path,canonical(audit)+b'\n')
        receipt,diag_receipt=observations_from_audit(audit)
        cached_value={'receipt':receipt,'diagnostic':diag_receipt,'audit_path':str(audit_path),
                      'audit_file_sha256':runtime.file_hash(audit_path)}
        budget.write(cache/(identifier+'.json'),canonical(cached_value)+b'\n')
        return receipt,diag_receipt
    def unknown(item,exception_type, *, known_resource_failure=False):
        assignment,identifier=item;entry=source.index[assignment['root']]
        battery_dir=output/'batteries'/identifier;battery_dir.mkdir(parents=True,exist_ok=True)
        journal=battery_dir/'cases.jsonl';existing={}
        if journal.exists():
            with journal.open('rb') as stream:
                for line in stream:
                    row=json.loads(line);existing[row['case_ordinal']]=row
        count=entry[plan['scope']]['case_count']
        diag_set=set(entry['private']['private_input_disjoint_ordinals']) if plan['scope']=='private' else set()
        for ordinal in range(count):
            if ordinal in existing:continue
            row={'case_ordinal':ordinal,'case_id':assignment['root']+':'+plan['scope']+':'+str(ordinal),
                'source_complete_case_ledger_sha256':entry[plan['scope']]['cases_sha256'],
                'diagnostic_member':ordinal in diag_set,
                'disposition':'SKIPPED_KNOWN_SOURCE_ZERO' if known_resource_failure else 'UNATTEMPTED_OBSERVER_UNAVAILABLE',
                'outcome':0 if known_resource_failure else None,
                'reason':'source_byte_cap' if known_resource_failure else budget.stop_reason or 'supervisor_failure'}
            budget.write(journal,canonical(row)+b'\n',case_record=True);existing[ordinal]=row
        def result(ordinals):
            values=[existing[i].get('outcome') for i in ordinals]
            if any(v==0 for v in values):return {'status':'FAIL','value':0,'bounds':[0,0]}
            if values and all(v==1 for v in values):return {'status':'PASS','value':1,'bounds':[1,1]}
            return {'status':'INCOMPLETE','value':None,'bounds':[0,1]}
        old_summary=battery_dir/'summary.json'
        audit={'version':VERSION,'primitive_id':identifier,'scope':plan['scope'],
            'grading_unit_id':assignment['grading_unit_id'],'root':assignment['root'],
            'program_sha256':assignment['program_sha256'],'observer_sha256':plan['observer_sha256'],
            'config_sha256':config['config_sha256'],'state_sha256':plan['state_sha256'],
            'runtime_manifest_sha256':attestation['runtime_manifest_sha256'],
            'instrument_path':None,'instrument_file_sha256':None,
            'case_journal_path':str(journal),'case_journal_sha256':runtime.file_hash(journal),
            'result':{'primary':result(range(count)),'diagnostic':result(diag_set) if plan['scope']=='private' else None,
                'case_starts':sum(r['disposition'] in ('EXECUTED','OBSERVER_UNAVAILABLE') for r in existing.values()),
                'assigned_cases':count,'accounted_cases':count},
            'elapsed_seconds':0,'unavailability_reason':budget.stop_reason or 'supervisor_failure',
            'supervisor_exception_type':exception_type,'raw_stdout_retained':False,'raw_stderr_retained':False}
        audit_path=battery_dir/('failure-summary.json' if old_summary.exists() else 'summary.json')
        budget.write(audit_path,canonical(audit)+b'\n')
        receipt,diagnostic=observations_from_audit(audit)
        cache_path=cache/(identifier+'.json')
        if not cache_path.exists():
            budget.write(cache_path,canonical({'receipt':receipt,'diagnostic':diagnostic,
                'audit_path':str(audit_path),'audit_file_sha256':runtime.file_hash(audit_path)})+b'\n')
        return receipt,diagnostic
    def grade(item):
        if len(item[0]['program'].encode('utf-8','strict'))>execution.DEFAULT_CAPS['source_bytes']:
            # This prospective operational endpoint failure is decided from
            # the returned artifact alone. No private payload or execution is
            # needed; preserve the entire source case ledger and other units.
            return unknown(item,'SourceByteCap',known_resource_failure=True)
        if not budget.check():return unknown(item,'GlobalCapBeforePayload')
        try:return grade_impl(item)
        except Exception as exc:
            budget.unavailable('observer_integrity_or_supervisor_failure')
            return unknown(item,type(exc).__name__)
    outputs=list(cached);diagnostics=list(cached_diagnostics);failure_types=[]
    # Exactly four trusted supervisors; each payload is single-process Python
    # with clone/fork denied. The owned allocation enforces aggregate resources.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(grade,item) for item in pending]
        for future in futures:
            try:
                receipt,diagnostic=future.result();outputs.append(receipt)
                if diagnostic is not None:diagnostics.append(diagnostic)
            except Exception as exc:
                budget.unavailable('unreconciled_supervisor_failure')
                failure_types.append(type(exc).__name__)
    assigned_keys={(a['grading_unit_id'],a['root'],a['program_sha256']) for a in assignments}
    output_keys={(r['grading_unit_id'],r['root'],r['program_sha256']) for r in outputs}
    if output_keys!=assigned_keys:
        # Never synthesize a successful/missing observation from a corrupt
        # instrument or incomplete journal. Assigned identities remain explicit.
        missing=[{'grading_unit_id':a['grading_unit_id'],'root':a['root'],'program_sha256':a['program_sha256'],
            'scope':plan['scope'],'disposition':'UNRECONCILED_SUPERVISOR_FAILURE'} for a in assignments
            if (a['grading_unit_id'],a['root'],a['program_sha256']) not in output_keys]
    else:missing=[]
    order={(a['grading_unit_id'],a['root'],a['program_sha256']):i for i,a in enumerate(assignments)}
    outputs.sort(key=lambda r:order[(r['grading_unit_id'],r['root'],r['program_sha256'])])
    diagnostics.sort(key=lambda r:order[(r['grading_unit_id'],r['root'],r['program_sha256'])])
    observations_path=output/'observations.json';raw=canonical(outputs)+b'\n'
    if len(raw)>plan['max_output_file_bytes']:raise ValueError('sanitized observations output byte cap')
    budget.write(observations_path,raw,final=True)
    budget.write(output/'diagnostics.json',canonical(diagnostics)+b'\n',final=True)
    budget.write(output/'unreconciled_assignments.json',canonical(missing)+b'\n',final=True)
    summary={'version':VERSION,'scope':plan['scope'],'status':'COMPLETE' if not missing else 'UNRECONCILED_FAILURE',
        'job_id':attestation['job_id'],'plan_sha256':runtime.file_hash(plan_path),
        'contract_sha256':plan['contract_sha256'],'state_sha256':plan['state_sha256'],
        'config_sha256':config['config_sha256'],'assigned_units':len(assignments),
        'accounted_units':len(outputs),'unreconciled_units':len(missing),'assigned_cases':case_count,
        'case_starts':budget.case_starts,'cached_units':len(cached),'workers':4,
        'remaining_case_reservation':budget.pending_case_reserve,'stop_reason':budget.stop_reason,
        'failure_types':failure_types,'elapsed_seconds':time.monotonic()-budget.started,
        'cpu_seconds':budget.cpu()-budget.cpu_base,'retained_bytes_before_summary':budget.retained,
        'observations_path':str(observations_path),'observations_file_sha256':runtime.file_hash(observations_path),
        'observations_sha256':sha(outputs),'diagnostics_file_sha256':runtime.file_hash(output/'diagnostics.json'),
        'private_expected_answers_in_policy':False,'network_calls':0,'model_calls':0,
        'cache_semantics':'same initial-execution vector/root/program/scope/observer only; no cross-repetition reuse'}
    budget.write(output/'summary.json',canonical(summary)+b'\n',final=True)
    if missing:raise RuntimeError('assigned grading primitives unreconciled; immutable partial journals retained')
    return summary
