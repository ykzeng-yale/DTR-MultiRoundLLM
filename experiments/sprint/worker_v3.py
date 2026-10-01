"""Nine ordered, bounded stage releases inside one owned GPU allocation.

The receiver executes no candidate programs. Between exact stage releases the
allocation may run a separately frozen qualified isolated CPU grading batch;
private access remains guarded by that batch's all-terminal state check. A
trusted lead publishes each committed exact stage plan to the owned spool.
Finite waiting consumes the same allocation/owner deadline. Only the declared
ordered stages can reach the owned local receiver; this is no collection release.

Version2 repairs cumulative diagnostic capacity and resumes only wholly
completed original dev0. It never replays an initial generation or reuses an
old node's qualification. The scientific receiver and assignment law remain
source-pinned; retained evidence and reserved calls remain cumulative.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time

from experiments.landmark.collect import receiver_state, NoRedirect
from experiments.sprint import receiver_v1 as receiver
sha=receiver.sha
import urllib.request

STAGES=('dev0','dev1','dev2','tune0','tune1','tune2','eval0','eval1','eval2')
VERSION='sprint-nine-stage-persistent-spool-v3'
# Explicit administrative repair; frozen receiver/model/decode stay unchanged.
LOG_CAP=128<<20
RESUME_CALLS=5472
GRADING=('dev0_public','dev1_public','dev2_private','tune0_public','tune1_public','tune2_private',
         'eval0_public','eval1_public','eval2_public','eval2_private')
PREDECESSOR_GRADE={'dev1':'dev0_public','dev2':'dev1_public','tune0':'dev2_private',
                   'tune1':'tune0_public','tune2':'tune1_public','eval0':'tune2_private',
                   'eval1':'eval0_public','eval2':'eval1_public'}


def stage_released(stage,release_exists,completed_grading):
    """A premature file cannot bypass the prior source-bound grading gate."""
    return release_exists and (stage not in PREDECESSOR_GRADE or
                               PREDECESSOR_GRADE[stage] in completed_grading)


class RetainedLedger:
    """Monotone conservative owned-byte accounting, with rare boundary scans.

    Server logs and control reserve remain charged even when they are smaller.
    Completed receiver journals reserve two copies (journal and final summary);
    publishing the actual final summary can overcount, which is conservative.
    Only external qualification/grading boundaries require filesystem scans.
    """
    def __init__(self,directory,cap,*,fixed_reserve=2*LOG_CAP+receiver.FIXED_RESERVE):
        self.directory=Path(directory);self.cap=cap;self.fixed_reserve=fixed_reserve
        self.charged=fixed_reserve;self.lock=threading.RLock();self.scans=0
        if self.charged>cap:raise ValueError('retained fixed reserve exceeds frozen cap')
    def total(self):
        with self.lock:return self.charged
    def fits(self,extra):
        with self.lock:return type(extra) is int and extra>=0 and self.charged+extra<=self.cap
    def charge(self,count,*,additional=0):
        with self.lock:
            if type(count) is not int or count<0 or type(additional) is not int or additional<0 or self.charged+count+additional>self.cap:
                raise RuntimeError('pre-write owned retained artifact cap')
            self.charged+=count
    def append(self,path,raw,*,copies=1,additional=0):
        # Charge before writing; failed writes keep a conservative charge.
        with self.lock:
            self.charge(copies*len(raw),additional=additional)
            with Path(path).open('ab') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    def publish(self,path,value):
        raw=receiver.canonical(value)+b'\n'
        with self.lock:
            self.charge(len(raw));atomic(path,value)
    def rescan_external(self):
        with self.lock:
            from scripts.sprint_metadata_inventory_v2 import inventory
            actual=inventory(self.directory,seconds=300,max_bytes=self.cap)['bytes']
            self.scans+=1;self.charged=max(self.charged,actual+self.fixed_reserve)
            if self.charged>self.cap:raise RuntimeError('external owned retained envelope exceeded')
            return actual


def qualification_check(output,plan_path):
    """Recount trusted fixture criteria/hashes, then source/host/runtime check."""
    from experiments.measurement_sprint_v4 import execution_v4 as execution
    from experiments.containment import stdio_sprint_qualification_v4 as qualification
    # Qualifier.run resolves its output before constructing the source-bound
    # canary fixture. Use the same absolute path during independent recount.
    output=Path(output).resolve();plan=json.loads(Path(plan_path).read_bytes())
    att=execution.verify_attestation(output/'attestation.json')
    if att['plan_sha256']!=receiver.file_sha(plan_path) or att['job_id']!=os.environ['SLURM_JOB_ID']:
        raise ValueError('fresh qualification plan/actual allocation identity')
    definitions=qualification.fixtures(plan['caps'],output/'host-canary')
    rows=[json.loads(line) for line in (output/'journal.jsonl').read_bytes().splitlines()]
    if len(rows)!=len(execution.REQUIRED_FIXTURES):raise ValueError('all qualification fixture assignments required')
    for index,name in enumerate(execution.REQUIRED_FIXTURES):
        row=rows[index];source,stdin,expected,status,reason=definitions[name];receipt=row['receipt']
        if row['assignment']!=index or row['fixture']!=name or row['source_sha256']!=hashlib.sha256(source.encode()).hexdigest() or row['stdin_sha256']!=hashlib.sha256(stdin).hexdigest() or row['expected_stdout_sha256']!=hashlib.sha256(expected).hexdigest() or row['stdin_bytes']!=len(stdin) or row['expected_stdout_bytes']!=len(expected):
            raise ValueError('qualification fixed-control source/value binding')
        passed=receipt['status']==status and receipt['execution'].get('cleanup') is True and (reason is None or receipt['reason']==reason)
        if not passed or row['passed']!=passed:raise ValueError('qualification independently recounted fixture failure')
    if (output/'host-canary').read_text()!='owned qualification sentinel; not mounted\n':
        raise ValueError('qualification host canary changed')
    return att


def synthetic_requests(seed,server_count=1):
    requests=[]
    for i in range(9*server_count):
        identity='receiver-qualification-'+str(i)
        requests.append({'slot':i,'execution_id':identity,'grading_unit_id':identity,
            'root':'trusted-synthetic-'+str(i),'artifact':'trusted-receiver-qualification',
            'arm':'RECEIVER_QUALIFICATION','replicate':i,'phase':0,
            'payload':{'messages':[{'role':'system','content':'Answer the given arithmetic question concisely.'},
                                  {'role':'user','content':f'Return only the integer equal to {i+2} plus {i+3}.'}],
                       'stream':False,'cache_prompt':False,'temperature':.7,'top_p':.95,'top_k':40,
                       'min_p':.05,'max_tokens':1024,'seed':seed+i}})
    return requests


def bound_json(path,digest,cap):
    with Path(path).open('rb') as stream:raw=stream.read(cap+1)
    if len(raw)>cap or hashlib.sha256(raw).hexdigest()!=digest:
        raise ValueError('exact frozen data file hash/byte cap: '+str(path))
    return json.loads(raw)


def stage_inputs(stage,release,global_plan):
    if set(release)!={'stage_id','stage_plan_path','stage_plan_file_sha256','worker_plan_sha256'} or release['stage_id']!=stage or release['worker_plan_sha256']!=global_plan['_actual_worker_plan_sha256']:
        raise ValueError('ordered atomic stage release schema')
    plan=bound_json(release['stage_plan_path'],release['stage_plan_file_sha256'],1<<20)
    if plan['stage_id']!=stage or plan['contract_sha256']!=global_plan['contract_sha256'] or plan['workers']!=global_plan.get('workers',4) or plan.get('server_count',1)!=global_plan.get('server_count',1) or plan['receiver_state_sha256']!=receiver.STATE_SHA256 or plan['model_sha256']!=receiver.MODEL_SHA256 or plan['build_manifest_sha256']!=global_plan['build_manifest_sha256']:
        raise ValueError('stage/science/source/receiver contract drift')
    if '_attestation_file_sha256' in global_plan and (plan['attestation_file_sha256']!=global_plan['_attestation_file_sha256'] or plan['runtime_manifest_sha256']!=global_plan['_runtime_manifest_sha256']):
        raise ValueError('first qualified allocation runtime/instrument drift')
    commit=plan['freeze_commit']
    if type(commit) is not str or len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('committed stage freeze witness required')
    for path,digest in plan['files'].items():
        if receiver.file_sha(path)!=digest:raise ValueError('stage source pin drift')
    if receiver.file_sha(plan['state_path'])!=plan['state_sha256']:
        raise ValueError('frozen exact stage state drift')
    config=bound_json(plan['study_config_path'],plan['study_config_file_sha256'],64<<20)
    if config['config_sha256']!=plan['study_config_sha256'] or sha({k:v for k,v in config.items() if k!='config_sha256'})!=config['config_sha256']:
        raise ValueError('source-bound study config hash')
    expected_mode={'dev':'development','tune':'tuning','eval':'evaluation'}[stage[:-1]]
    if config['mode']!=expected_mode:raise ValueError('development/tuning/evaluation order')
    if stage.startswith('eval'):
        lock=plan['model_lock']
        if set(lock)!={'model_sha256s','selected_b1','choice_lock_sha256','freeze_commit'} or lock['model_sha256s']!=config['model_sha256s'] or lock['selected_b1']!=config['selected_b1'] or lock['choice_lock_sha256']!=config['choice_lock_sha256']:
            raise ValueError('evaluation model/comparator frozen lock differs from requests')
        if type(lock['freeze_commit']) is not str or len(lock['freeze_commit'])!=40 or any(c not in '0123456789abcdef' for c in lock['freeze_commit']):
            raise ValueError('earlier fixed model/comparator freeze witness')
        if set(lock['model_sha256s'])!={'FULL_HISTORY_Q','COMPRESSED_HISTORY_Q'}:
            raise ValueError('both actually locked fitted history learners required')
    elif plan.get('model_lock') is not None:
        raise ValueError('premature evaluation model lock')
    requests=bound_json(plan['requests_path'],plan['requests_file_sha256'],plan['max_requests_bytes'])
    if plan['max_calls']==0:
        if requests!=[] or plan['max_completion_tokens']!=0 or sha(requests)!=plan['requests_canonical_sha256']:
            raise ValueError('empty stage identity')
    else:
        receiver.validate_requests(requests,plan)
    if any(q['phase']!=int(stage[-1]) for q in requests):raise ValueError('stage request phase')
    return plan,requests


def _bound_jsonl(path,digest,cap):
    """Strict complete-line ledger, bounded before parsing; data only."""
    with Path(path).open('rb') as stream:raw=stream.read(cap+1)
    if len(raw)>cap or hashlib.sha256(raw).hexdigest()!=digest or (raw and not raw.endswith(b'\n')):
        raise ValueError('exact complete resumed journal hash/byte cap')
    return [json.loads(line) for line in raw.splitlines()]


def remaining_stages(resumed):
    """Verified completed dev0 is never regenerated, even without a release."""
    return tuple(stage for stage in STAGES if stage not in {s['stage_id'] for s in resumed['stages']})


def verify_owner_extension(old,plan):
    """A changed administrative deadline requires an exact committed receipt.

    The file records the owner's authorization; this function cannot establish
    authorship. It only checks the prospectively source-pinned bounded change.
    All scientific/global call, token and retained-budget keys remain checked
    separately by verify_resume.
    """
    if plan['owner_deadline_iso']==old['owner_deadline_iso']:
        if 'owner_extension_receipt_path' in plan or 'owner_extension_receipt_sha256' in plan:
            raise ValueError('unexpected owner extension without changed deadline')
        return None
    if not all(k in plan for k in ('owner_extension_receipt_path','owner_extension_receipt_sha256')):
        raise ValueError('changed deadline requires exact owner extension receipt')
    receipt=bound_json(plan['owner_extension_receipt_path'],plan['owner_extension_receipt_sha256'],64<<10)
    fixed={'version':'sprint-owner-bounded-deadline-extension-v1',
        'original_deadline_iso':'2026-10-01T02:54:40Z',
        'extended_deadline_iso':'2026-10-02T18:00:00Z',
        'lead_recorded_instruction_iso':'2026-09-30T23:08:00Z',
        'directive':'autonomous remaining research with six-hour checks',
        'contract_sha256':plan['contract_sha256'],'allocation_seconds':14400,'max_gpu_hours':24}
    if (set(receipt)!=set(fixed)|{'freeze_commit'} or any(receipt.get(k)!=v for k,v in fixed.items()) or
        receipt['original_deadline_iso']!=old['owner_deadline_iso'] or
        receipt['extended_deadline_iso']!=plan['owner_deadline_iso'] or
        plan['wall_seconds']!=receipt['allocation_seconds'] or
        type(receipt['freeze_commit']) is not str or len(receipt['freeze_commit'])!=40 or
        any(c not in '0123456789abcdef' for c in receipt['freeze_commit'])):
        raise ValueError('owner deadline extension receipt/scope/commit mismatch')
    return plan['owner_extension_receipt_sha256']


def verify_original_dev0(plan):
    """Only immutable, wholly successful original dev0 can cross allocations.

    This does not reuse qualification or grading. The fresh allocation must
    pass its original controls, then grade dev0 under the separately frozen
    instrument. No partial/failed generation is extended or rerun here.
    The full prior owned artifact tree is charged to the same global envelope.
    """
    entries=plan.get('resume_completed_stages')
    if type(entries) is not list or len(entries)!=1:
        raise ValueError('exactly one terminal dev0 resume required')
    entry=entries[0]
    keys={'stage_id','original_job_id','original_worker_plan_path','original_worker_plan_sha256',
          'stage_plan_path','stage_plan_file_sha256','summary_path','summary_sha256',
          'journal_path','journal_sha256','started_path','started_sha256',
          'prior_output_dir','retained_files'}
    if type(entry) is not dict or set(entry)!=keys or entry['stage_id']!='dev0':
        raise ValueError('dev0-only exact resume manifest')
    old=bound_json(entry['original_worker_plan_path'],entry['original_worker_plan_sha256'],1<<20)
    extension_sha=verify_owner_extension(old,plan)
    if old.get('mode')!='finite-stage-spool-v1' or any(old[k]!=plan[k] for k in
            ('contract_sha256','model_sha256','receiver_state_sha256','build_manifest_sha256',
             'workers','server_count','max_calls','max_completion_tokens','max_retained_bytes')) or tuple(old['stage_ids'])!=STAGES:
        raise ValueError('original scientific/global budget law changed on resume')
    old['_actual_worker_plan_sha256']=entry['original_worker_plan_sha256']
    stage,requests=stage_inputs('dev0',dict(stage_id='dev0',stage_plan_path=entry['stage_plan_path'],
        stage_plan_file_sha256=entry['stage_plan_file_sha256'],
        worker_plan_sha256=entry['original_worker_plan_sha256']),old)
    if len(requests)!=RESUME_CALLS or stage['max_calls']!=RESUME_CALLS:
        raise ValueError('all 5472 original dev0 assignments required')
    state=bound_json(stage['state_path'],stage['state_sha256'],512<<20)
    if state.get('phase')!=0 or state.get('config_sha256')!=stage['study_config_sha256'] or state.get('requests')!=requests:
        raise ValueError('original dev0 complete initial state/request identity')
    receipt=bound_json(entry['summary_path'],entry['summary_sha256'],2<<30)
    if (receipt.get('stage_id')!='dev0' or receipt.get('job_id')!=entry['original_job_id'] or
        receipt.get('config_sha256')!=entry['stage_plan_file_sha256'] or
        receipt.get('study_config_sha256')!=stage['study_config_sha256'] or
        receipt.get('state_sha256')!=stage['state_sha256'] or
        receipt.get('requests_sha256')!=stage['requests_canonical_sha256'] or
        receipt.get('freeze')!=stage['freeze_commit'] or receipt.get('model_lock') is not None or
        receipt.get('state_unchanged') is not True or receipt.get('error') is not None or
        receipt.get('global_cap_reason') is not None or receipt.get('unattempted')!=0 or
        receipt.get('unattempted_execution_ids')!=[] or receipt.get('service_failed_execution_ids')!=[] or
        receipt.get('attempted_without_journal')!=[] or
        receipt.get('journal_sha256')!=entry['journal_sha256'] or
        receipt.get('started_sha256')!=entry['started_sha256']):
        raise ValueError('resume requires completed error-free undrifted dev0')
    journal=_bound_jsonl(entry['journal_path'],entry['journal_sha256'],2<<30)
    starts=_bound_jsonl(entry['started_path'],entry['started_sha256'],RESUME_CALLS*4096)
    ids=[q['execution_id'] for q in requests]
    if len(journal)!=RESUME_CALLS or len(starts)!=RESUME_CALLS:
        raise ValueError('resume partial assigned/started/completed ledger')
    by_id={c['execution_id']:c for c in journal};start_ids={c['execution_id']:c for c in starts}
    if len(by_id)!=RESUME_CALLS or len(start_ids)!=RESUME_CALLS or set(by_id)!=set(ids) or set(start_ids)!=set(ids):
        raise ValueError('resume duplicate/changed assignment ledger')
    checks=receipt.get('tokenizer_preflight',[])
    preflight={c['execution_id']:c for c in checks}
    if len(checks)!=RESUME_CALLS or len(preflight)!=RESUME_CALLS or set(preflight)!=set(ids):
        raise ValueError('resume exact original tokenizer preflight required')
    for q in requests:
        c=by_id[q['execution_id']];started=start_ids[q['execution_id']];check=preflight[q['execution_id']]
        base={k:q[k] for k in receiver.REQUEST_KEYS-{'payload'}}
        if (any(c.get(k)!=v or started.get(k)!=v for k,v in base.items()) or
            c.get('status')!='returned' or started.get('status')!='assigned' or
            c.get('payload_sha256')!=sha(q['payload']) or started.get('payload_sha256')!=sha(q['payload']) or
            c.get('server_index')!=q['payload']['seed']%plan['server_count'] or
            started.get('server_index')!=c.get('server_index') or check.get('payload_sha256')!=sha(q['payload']) or
            check.get('context_tokens')!=8192 or check.get('completion_reserved')!=1024 or check.get('tokenizer_reserve')!=16 or
            type(check.get('tokens')) is not int or check['tokens']<0 or check['tokens']+1040>8192):
            raise ValueError('resume exact returned assignment/payload binding')
        metadata=receiver.response_check(c['response'],check['tokens'])
        if any(c.get(k)!=v for k,v in metadata.items()):
            raise ValueError('resume response/token/response-hash drift')
    if receipt.get('calls')!=[by_id[i] for i in ids]:
        raise ValueError('resume summary/raw journal mismatch')
    prior=Path(entry['prior_output_dir']).resolve()
    # Absolute original artifact root must match the source-pinned old plan.
    old_root=Path(entry['original_worker_plan_path']).resolve().parent
    if prior!=(old_root/old['output_dir']).resolve():
        raise ValueError('prior owned output root differs from original plan')
    paths={p.resolve() for p in prior.rglob('*') if p.is_file()}
    retained=entry['retained_files']
    if type(retained) is not list or not 0<len(retained)<=10000:
        raise ValueError('bounded complete prior retained file manifest')
    listed=set();total=0
    for item in retained:
        if type(item) is not dict or set(item)!={'path','sha256','bytes'} or type(item['bytes']) is not int or item['bytes']<0:
            raise ValueError('source-bound prior retained file identity')
        p=Path(item['path']);resolved=p.resolve()
        if p.is_symlink() or not resolved.is_relative_to(prior) or resolved in listed or p.stat().st_size!=item['bytes'] or receiver.file_sha(p)!=item['sha256']:
            raise ValueError('prior retained file changed/outside/duplicated')
        listed.add(resolved);total+=item['bytes']
    required={Path(entry[k]).resolve() for k in ('summary_path','journal_path','started_path')}
    if listed!=paths or not required<=listed:
        raise ValueError('all prior owned retained artifacts must remain charged')
    if total+2*LOG_CAP+receiver.FIXED_RESERVE>plan['max_retained_bytes'] or RESUME_CALLS>plan['max_calls']:
        raise ValueError('resumed cumulative retained/call budget exceeds frozen envelope')
    witness={'version':VERSION,'stage_id':'dev0','original_job_id':entry['original_job_id'],
        'summary_sha256':entry['summary_sha256'],'journal_sha256':entry['journal_sha256'],
        'started_sha256':entry['started_sha256'],'stage_plan_file_sha256':entry['stage_plan_file_sha256'],
        'original_worker_plan_sha256':entry['original_worker_plan_sha256'],
        'retained_manifest_sha256':sha(retained),'retained_bytes':total,'returned_calls':RESUME_CALLS,
        'owner_extension_receipt_sha256':extension_sha}
    return {'reserved_calls':RESUME_CALLS,'retained_bytes':total,'receipt':witness,
            'stage_contracts':{'dev':stage['study_config_sha256']},
            'stages':[{'stage_id':'dev0','summary_sha256':entry['summary_sha256'],'returned':RESUME_CALLS,
                       'failed':0,'unattempted':0,'error':None,'resumed':True,'original_job_id':entry['original_job_id']}]}


def verify_resume(plan):
    from experiments.sprint.recovery_v1 import verify
    return verify(plan,verify_original_dev0(plan))


def atomic(path,value):
    path=Path(path);raw=receiver.canonical(value)+b'\n';temp=path.with_name(path.name+'.tmp')
    with temp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)


def capture_stage_props(directory,all_props,publish):
    """Retain exact post-stage properties before interpreting state equality."""
    path=Path(directory)/'props-after.json'
    raw_props=all_props()
    publish(path,raw_props)
    return {'props_after_sha256':receiver.file_sha(path),
            'state_unchanged':all(sha(receiver_state(p))==receiver.STATE_SHA256 for p in raw_props)}


def audit_grading(plan_path,grade_out,report_path,publish,*,timeout_seconds):
    """Main-thread, alarm-bounded metadata recount; executes no programs.

    Refusals are retained outside the immutable grade batch before stopping.
    The caller measures CPU around both execution and this separate recount.
    """
    if threading.current_thread() is not threading.main_thread() or not 0<timeout_seconds<=600:
        raise ValueError('bounded main-thread grading reconciliation required')
    from scripts.audit_sprint_grading_v1 import audit_batch
    if signal.getitimer(signal.ITIMER_REAL)!=(0.0,0.0):
        raise ValueError('cannot replace an existing administrative alarm')
    previous=signal.getsignal(signal.SIGALRM)
    def expired(signum,frame):raise TimeoutError('data-only grading reconciliation wall cap')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,timeout_seconds)
    try:
        result=audit_batch(plan_path,grade_out,root=Path.cwd())
        if (result.get('safe_to_advance') is not True or result.get('status')!='RECONCILED_COMPLETE' or
            result.get('plan_file_sha256')!=receiver.file_sha(plan_path) or
            result.get('summary_file_sha256')!=receiver.file_sha(Path(grade_out)/'summary.json') or
            result.get('unreconciled_units')!=0 or type(result.get('assigned_units')) is not int or
            result['assigned_units']<0 or type(result.get('accounted_units')) is not int or
            result['assigned_units']!=result['accounted_units'] or
            result.get('model_calls')!=0 or result.get('candidate_executions')!=0 or
            result.get('private_values_reported') is not False):
            raise ValueError('grading independent recount refuses advancement')
    except Exception as exc:
        result={'status':'RECONCILIATION_REFUSED','safe_to_advance':False,
            'exception_type':type(exc).__name__,'reason':'metadata evidence reconciliation refused; inspect preserved raw files',
            'model_calls':0,'candidate_executions':0,'private_values_reported':False}
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
    if len(receiver.canonical(result))>1<<20:
        result={'status':'RECONCILIATION_REFUSED','safe_to_advance':False,'reason':'reconciliation report byte cap'}
    path=Path(report_path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.resolve().is_relative_to(Path(grade_out).resolve()):
        raise ValueError('reconciliation report must be outside immutable grade batch')
    publish(path,result)
    if result['safe_to_advance'] is not True:
        raise RuntimeError('grading independent recount refused; evidence preserved')
    return result


def run(plan_path):
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_bytes())
    plan['_actual_worker_plan_sha256']=receiver.file_sha(plan_path)
    if plan.get('mode')!='finite-stage-spool-v3' or plan.get('server_log_cap_bytes')!=LOG_CAP:
        raise ValueError('versioned explicit administrative log-cap repair')
    if plan.get('hardware_epoch')!='h100-evaluation-recovery-v1' or plan.get('grading_reconciliation_seconds')!=600 or 'scripts/audit_sprint_grading_v1.py' not in plan['files']:
        raise ValueError('explicit H100 epoch and frozen bounded grading auditor required')
    resumed=verify_resume(plan)
    server_count=plan.get('server_count',1)
    if tuple(plan['stage_ids'])!=STAGES or plan['model_sha256']!=receiver.MODEL_SHA256 or plan['receiver_state_sha256']!=receiver.STATE_SHA256 or server_count not in (1,2) or plan['workers']!=4*server_count or plan['paid_usd']!=0:
        raise ValueError('finite nine-stage/four-slot/pinned receiver law')
    if plan['max_completion_tokens']!=1024*plan['max_calls'] or not 0<plan['max_calls']<=82428 or not 0<plan['max_retained_bytes']<=100*(1<<30) or not 0<plan['wait_poll_seconds']<=60 or not 0<plan['max_seconds']<=plan['wall_seconds']-20:
        raise ValueError('frozen global resource envelope')
    for path,digest in plan['files'].items():
        if receiver.file_sha(path)!=digest:raise ValueError('global source pin drift')
    if receiver.file_sha('model.gguf')!=receiver.MODEL_SHA256 or receiver.file_sha('build-sha256.txt')!=plan['build_manifest_sha256'] or not Path('build-complete.txt').exists():
        raise ValueError('frozen actual build/model binding')
    subprocess.run(['sha256sum','-c','build-sha256.txt'],check=True,timeout=30)
    deadline=datetime.fromisoformat(plan['owner_deadline_iso'].replace('Z','+00:00')).timestamp()
    start=time.monotonic();owner_remaining=deadline-time.time()
    total_window=min(plan['max_seconds'],owner_remaining)
    if total_window<=120:raise ValueError('insufficient finite owner/allocation window')
    out=Path(plan['output_dir']);out.mkdir(exist_ok=False)
    # Prior artifacts are outside this fresh output tree. Include their bytes
    # in the permanent reserve so every later external grading scan still
    # counts prior+new artifacts, rather than max(prior,new).
    retained_ledger=RetainedLedger(out,plan['max_retained_bytes'],
        fixed_reserve=2*LOG_CAP+receiver.FIXED_RESERVE+resumed['retained_bytes'])
    spool=Path(plan['spool_dir']);spool.mkdir(exist_ok=True)
    job=os.environ['SLURM_JOB_ID'];array=os.environ.get('SLURM_ARRAY_TASK_ID','')
    # Exclusive sentinel refuses a duplicate worker in this experiment spool.
    # A stopped allocation cannot silently renew this same stage ledger.
    with (spool/'claimed-worker.json').open('x') as claim:
        json.dump({'job_id':job,'array_task_id':array,'worker_plan_sha256':plan['_actual_worker_plan_sha256']},claim)
        claim.flush();os.fsync(claim.fileno())
    port=10000+2*(int(hashlib.sha256((job+':'+array).encode()).hexdigest()[:8],16)%25000)
    ports=[port+i for i in range(server_count)]
    devices=os.environ.get('CUDA_VISIBLE_DEVICES','').split(',')
    if len(devices)!=server_count or len(set(devices))!=server_count or any(not d for d in devices):
        raise ValueError('exact assigned CUDA_VISIBLE_DEVICES inventory required')
    summary={'version':VERSION,'job_id':job,'ports':ports,'server_count':server_count,'cuda_devices':devices,
             'worker_plan_sha256':receiver.file_sha(plan_path),
             'contract_sha256':plan['contract_sha256'],'stages':resumed['stages'],'error':None,
             'resume':resumed['receipt'],'server_log_cap_bytes':LOG_CAP,
             'hardware_epoch':plan['hardware_epoch'],
             'grading_cpu_seconds_measured':sum(r['cpu_seconds'] for r in resumed['grading']),'grading_wall_seconds_measured':sum(r['wall_seconds'] for r in resumed['grading']),
             'assigned_calls_reserved':0,'completion_tokens_reserved':0,'paid_usd':0,'grading':resumed['grading']}
    procs=[];threads=[];stopping=threading.Event();log_errors=[];journal_bytes=0;started_bytes=0
    started_lock=threading.Lock();reserved=resumed['reserved_calls'];stage_contracts=resumed['stage_contracts'];eval_lock=resumed['eval_lock']
    retained_ledger.publish(out/'resume-completed-stages.json',resumed['receipt'])
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def remaining():return min(total_window-(time.monotonic()-start),deadline-time.time())
    def alive():return len(procs)==server_count and all(p.poll() is None for p in procs) and not log_errors
    def kill_owned():
        stopping.set()
        for proc in procs:
            if proc.poll() is None:
                try:os.killpg(proc.pid,signal.SIGTERM)
                except ProcessLookupError:pass
    def interrupt(signum,frame):kill_owned();raise RuntimeError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    def http(endpoint,body=None,timeout=3,server_index=0):
        if remaining()<=20:raise RuntimeError('global spool/allocation/owner deadline')
        request=urllib.request.Request(f'http://127.0.0.1:{ports[server_index]}'+endpoint,
            data=None if body is None else receiver.canonical(body),headers={'Content-Type':'application/json'})
        with opener.open(request,timeout=min(timeout,max(.1,remaining()-20))) as response:
            raw=response.read(receiver.RESPONSE_CAP+1)
        if len(raw)>receiver.RESPONSE_CAP:raise ValueError('receiver response byte cap')
        return json.loads(raw)
    def transport_factory(q):
        index=q['payload']['seed']%server_count
        return lambda endpoint,body=None,timeout=3:http(endpoint,body,timeout,index)
    def all_props():return [http('/props',server_index=i) for i in range(server_count)]
    def stable_props():return all(sha(receiver_state(p))==receiver.STATE_SHA256 for p in all_props())
    def retained():
        return retained_ledger.total()
    def publish(path,value):retained_ledger.publish(path,value)
    def process_grading(allowed):
        grading_id=next((g for g in GRADING if g not in {r['grading_id'] for r in summary['grading']} and g in allowed),None)
        if grading_id is None:return
        path=spool/(grading_id+'.grading.ready.json')
        if not path.exists():return
        if path.stat().st_size>4096:raise ValueError('bounded grading release')
        release=json.loads(path.read_bytes())
        if set(release)!={'grading_id','scope','plan_path','plan_sha256','worker_plan_sha256'} or release['grading_id']!=grading_id or release['scope']!=grading_id.rsplit('_',1)[1] or release['worker_plan_sha256']!=plan['_actual_worker_plan_sha256']:
            raise ValueError('finite source-bound grading release')
        gp=bound_json(release['plan_path'],release['plan_sha256'],1<<20)
        if gp['contract_sha256']!=plan['contract_sha256'] or gp['scope']!=release['scope'] or gp['workers']!=4 or gp['attestation_sha256']!=plan['_attestation_file_sha256'] or Path(gp['attestation_path']).resolve()!=attestation_path.resolve() or gp['owner_deadline_iso']!=plan['owner_deadline_iso']:
            raise ValueError('same qualified allocation grading/science binding')
        # Persistent primitive caching is required across phases, but it must
        # remain inside the owned output envelope counted by retained().
        if not Path(gp['cache_dir']).resolve().is_relative_to(out.resolve()):
            raise ValueError('grading cache outside owned retained envelope')
        used_cases=sum(r['case_starts'] for r in summary['grading'])
        used_cpu=sum(r['cpu_seconds'] for r in summary['grading'])
        audit_allowance=plan['grading_reconciliation_seconds']
        if gp['max_case_starts']>plan['max_case_starts']-used_cases or gp['max_cpu_seconds']+audit_allowance>plan['max_grading_cpu_seconds']-used_cpu or gp['max_wall_seconds']+audit_allowance>remaining()-30 or gp['max_retained_bytes']>plan['max_retained_bytes']-retained()-receiver.FIXED_RESERVE:
            raise ValueError('global finite grading case/CPU/wall/retained reservation')
        from experiments.sprint_grading.batch_v1 import run_batch
        grade_out=out/'grading'/grading_id
        grade_out.parent.mkdir(exist_ok=True)
        before_cpu=os.times();before=time.monotonic()
        audit_path=out/'grading-reconciliation'/(grading_id+'.json')
        try:
            result=run_batch(release['plan_path'],grade_out,attestation_path=attestation_path)
            audit=audit_grading(release['plan_path'],grade_out,audit_path,publish,
                timeout_seconds=min(audit_allowance,max(.01,remaining()-30)))
        finally:
            after_cpu=os.times();cpu=max(0,after_cpu.user+after_cpu.system+after_cpu.children_user+after_cpu.children_system-before_cpu.user-before_cpu.system-before_cpu.children_user-before_cpu.children_system)
            summary['grading_cpu_seconds_measured']+=cpu
            summary['grading_wall_seconds_measured']+=time.monotonic()-before
        retained_ledger.rescan_external()
        starts=result.get('case_starts',result.get('cases_started'))
        if type(starts) is not int or not 0<=starts<=gp['max_case_starts']:
            raise ValueError('graded case accounting required')
        if cpu+used_cpu>plan['max_grading_cpu_seconds']:
            raise RuntimeError('graded execution plus independent audit CPU cap; evidence preserved')
        summary['grading'].append({'grading_id':grading_id,'plan_sha256':release['plan_sha256'],
            'case_starts':starts,'cpu_seconds':cpu,'wall_seconds':time.monotonic()-before,
            'output_dir':str(grade_out),'result_sha256':sha(result),
            'reconciliation_path':str(audit_path),'reconciliation_file_sha256':receiver.file_sha(audit_path),
            'reconciliation_sha256':sha(audit)})
        publish(out/(grading_id+'.grading-complete.json'),summary['grading'][-1])
    try:
        qp=Path(plan['qualification_plan_path'])
        if receiver.file_sha(qp)!=plan['qualification_plan_sha256'] or not 0<plan['qualification_timeout_seconds']<=240:
            raise ValueError('frozen fresh allocation qualification plan/cap')
        qualification_out=out/'qualification'
        subprocess.run(['/usr/bin/python3','scripts/qualify_stdio_sprint_v4.py','--plan',str(qp),
                        '--out',str(qualification_out),'--freeze','freeze.txt'],
                       check=True,timeout=min(plan['qualification_timeout_seconds'],remaining()-30))
        qualification=qualification_check(qualification_out,qp)
        retained_ledger.rescan_external()
        attestation_path=qualification_out/'attestation.json'
        plan['_attestation_file_sha256']=receiver.file_sha(attestation_path)
        plan['_runtime_manifest_sha256']=qualification['runtime_manifest_sha256']
        summary['attestation_file_sha256']=plan['_attestation_file_sha256']
        summary['runtime_manifest_sha256']=plan['_runtime_manifest_sha256']
        for index,instance_port in enumerate(ports):
            with socket.socket() as sock:sock.bind(('127.0.0.1',instance_port))
            command=['build/bin/llama-server','-m','model.gguf','--alias','qwen2.5-3b-instruct',
                '--host','127.0.0.1','--port',str(instance_port),'-ngl','99','-np','4','-c','32768','-t','4','--jinja']
            procs.append(subprocess.Popen(command,env=dict(os.environ,LLAMA_MEDIA_MARKER=plan['media_marker'],CUDA_VISIBLE_DEVICES=devices[index],OMP_NUM_THREADS='4'),
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True))
        def log(proc,index):
            count=0
            with (out/f'server-{index}.log').open('xb') as stream:
                while True:
                    raw=proc.stdout.read1(4096)
                    if not raw:break
                    stream.write(raw[:max(0,LOG_CAP-count)]);count+=len(raw)
                    if count>LOG_CAP:log_errors.append('server_log_cap');kill_owned();break
        for index,proc in enumerate(procs):
            thread=threading.Thread(target=log,args=(proc,index),daemon=True);thread.start();threads.append(thread)
        receiver_start=time.monotonic()
        while time.monotonic()-receiver_start<120 and remaining()>40:
            if not alive():raise RuntimeError('owned persistent receiver startup failed')
            try:
                if all(http('/health',server_index=i).get('status')=='ok' for i in range(server_count)):break
            except Exception:pass
            time.sleep(.5)
        else:raise RuntimeError('persistent receiver startup timeout')
        props=all_props()
        if not all(sha(receiver_state(p))==receiver.STATE_SHA256 for p in props):raise ValueError('actual persistent receiver states differ')
        publish(out/'props-before.json',props)
        synthetic=synthetic_requests(plan['receiver_qualification_seed'],server_count)
        synthetic_plan={'request_timeout_seconds':120,'workers':4*server_count,'server_count':server_count}
        synthetic_out=out/'receiver-qualification';synthetic_out.mkdir(exist_ok=False)
        def synthetic_journal(record):
            retained_ledger.append(synthetic_out/'journal.jsonl',receiver.canonical(record)+b'\n',copies=2)
        calibration=receiver.collect(synthetic,synthetic_plan,http,alive,synthetic_journal,remaining,threading.Event(),transport_factory=transport_factory)
        if len(calibration['calls'])!=9*server_count or calibration['unattempted'] or any(c['status']!='returned' for c in calibration['calls']):
            publish(synthetic_out/'summary.json',calibration);raise ValueError('frozen nine-call receiver qualification failed')
        if not stable_props():raise ValueError('qualification receiver drift')
        publish(synthetic_out/'summary.json',calibration)
        gpu=subprocess.run(['nvidia-smi','--query-gpu=uuid,name,memory.total','--format=csv,noheader'],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=10)
        if len(gpu.stdout)>4096:raise ValueError('GPU identity response cap')
        gpu_identity=gpu.stdout.decode('utf-8',errors='strict')
        if len(gpu_identity.splitlines())!=server_count or not all(', NVIDIA H100' in line for line in gpu_identity.splitlines()):
            raise ValueError('actual GPUs differ from explicit H100 continuation epoch')
        publish(out/'ready.json',{'version':VERSION,'job_id':job,'ports':ports,'server_count':server_count,
                               'routing':'payload seed modulo server_count; preflight and generation same instance',
                               'receiver_state_sha256':receiver.STATE_SHA256,
                               'build_manifest_sha256':plan['build_manifest_sha256'],'model_sha256':receiver.MODEL_SHA256,
                               'worker_plan_sha256':receiver.file_sha(plan_path),'owner_deadline_iso':plan['owner_deadline_iso'],
                               'attestation_file_sha256':plan['_attestation_file_sha256'],
                               'runtime_manifest_sha256':plan['_runtime_manifest_sha256'],
                               'receiver_qualification_sha256':receiver.file_sha(synthetic_out/'summary.json'),
                               'node':os.environ.get('SLURMD_NODENAME'),'gpu_identity':gpu_identity,
                               'hardware_epoch':plan['hardware_epoch'],
                               'owner_extension_receipt_sha256':resumed['receipt']['owner_extension_receipt_sha256']})
        for stage in remaining_stages(resumed):
            release_path=spool/(stage+'.ready.json');wait_start=time.monotonic()
            while not stage_released(stage,release_path.exists(),{g['grading_id'] for g in summary['grading']}):
                if not alive() or remaining()<=40 or time.monotonic()-wait_start>plan['stage_wait_seconds']:
                    raise RuntimeError('finite wait expired before '+stage)
                completed_stages={s['stage_id'] for s in summary['stages']}
                allowed={g for g in GRADING if g.rsplit('_',1)[0] in completed_stages}
                if 'eval2_public' not in {g['grading_id'] for g in summary['grading']}:allowed.discard('eval2_private')
                process_grading(allowed)
                time.sleep(min(plan['wait_poll_seconds'],remaining()-35))
            if release_path.stat().st_size>4096:raise ValueError('bounded atomic stage release')
            release=json.loads(release_path.read_bytes());stage_plan,requests=stage_inputs(stage,release,plan)
            if stage[:-1] in stage_contracts and stage_contracts[stage[:-1]]!=stage_plan['study_config_sha256']:
                raise ValueError('within-study config mutation across phases')
            stage_contracts[stage[:-1]]=stage_plan['study_config_sha256']
            if stage.startswith('eval'):
                if eval_lock is not None and eval_lock!=stage_plan['model_lock']:raise ValueError('evaluation model/comparator lock changed')
                eval_lock=stage_plan['model_lock']
            if reserved+len(requests)>plan['max_calls']:raise ValueError('global all-stage call/token reservation exceeded')
            reserved+=len(requests)
            stage_out=out/stage;stage_out.mkdir(exist_ok=False)
            stage_stop=threading.Event();stage_result={'version':receiver.VERSION,'stage_id':stage,'job_id':job,
                'config_sha256':release['stage_plan_file_sha256'],'study_config_sha256':stage_plan['study_config_sha256'],
                'state_sha256':stage_plan['state_sha256'],'requests_sha256':stage_plan['requests_canonical_sha256'],
                'freeze':stage_plan['freeze_commit'],'model_lock':stage_plan.get('model_lock'),'error':None,
                'state_unchanged':False,'calls':[],'unattempted':len(requests)}
            stage_start=time.monotonic()
            def journal(record):
                nonlocal journal_bytes
                raw=receiver.canonical(record)+b'\n'
                try:retained_ledger.append(stage_out/'journal.jsonl',raw,copies=2,
                    additional=receiver.RESPONSE_CAP*8+receiver.FIXED_RESERVE)
                except RuntimeError:stage_stop.set();raise
                journal_bytes+=len(raw)
            def started(record):
                nonlocal started_bytes
                raw=receiver.canonical(record)+b'\n'
                if len(raw)>4096:raise ValueError('bounded started receipt')
                with started_lock:
                    retained_ledger.append(stage_out/'started.jsonl',raw)
                    started_bytes+=len(raw)
            def can_submit(pending):
                return retained_ledger.fits(2*pending*(receiver.RESPONSE_CAP+4096)+receiver.FIXED_RESERVE)
            try:
                if requests:stage_result.update(receiver.collect(requests,stage_plan,http,alive,journal,remaining,stage_stop,on_start=started,can_submit=can_submit,transport_factory=transport_factory))
                else:stage_result.update(calls=[],unattempted=0,tokenizer_preflight=[])
                stage_result.update(capture_stage_props(stage_out,all_props,publish))
                if not stage_result['state_unchanged']:raise ValueError('persistent receiver drift')
            except BaseException as exc:stage_result['error']=repr(exc)[:2048]
            finally:
                completed={}
                if (stage_out/'journal.jsonl').exists():
                    for line in (stage_out/'journal.jsonl').read_bytes().splitlines():
                        record=json.loads(line)
                        if record['execution_id'] in completed:raise ValueError('duplicate immutable stage journal')
                        completed[record['execution_id']]=record
                if (stage_out/'started.jsonl').exists():
                    for line in (stage_out/'started.jsonl').read_bytes().splitlines():
                        record=json.loads(line)
                        if record['execution_id'] not in completed:
                            record.update(status='failed',seconds=None,error='interrupted started request without completed journal',failure_kind='interrupted_inflight_service')
                            completed[record['execution_id']]=record
                stage_result['calls']=[completed[q['execution_id']] for q in requests if q['execution_id'] in completed]
                stage_result['unattempted']=len(requests)-len(stage_result['calls'])
                stage_result['unattempted_execution_ids']=[q['execution_id'] for q in requests if q['execution_id'] not in completed]
                stage_result.update(elapsed_seconds=time.monotonic()-stage_start,paid_usd=0,energy_measured=False,
                    journal_sha256=receiver.file_sha(stage_out/'journal.jsonl') if (stage_out/'journal.jsonl').exists() else None,
                    started_sha256=receiver.file_sha(stage_out/'started.jsonl') if (stage_out/'started.jsonl').exists() else None)
                if retained()+len(receiver.canonical(stage_result))+receiver.FIXED_RESERVE>plan['max_retained_bytes']:
                    raise RuntimeError('stage final retained cap; journals retained')
                publish(stage_out/'summary.json',stage_result)
                summary['stages'].append({'stage_id':stage,'summary_sha256':receiver.file_sha(stage_out/'summary.json'),
                                         'returned':sum(c['status']=='returned' for c in stage_result['calls']),
                                         'failed':sum(c['status']=='failed' for c in stage_result['calls']),
                                         'unattempted':stage_result['unattempted'],'error':stage_result['error']})
            if stage_result['error'] or not stage_result['state_unchanged']:raise RuntimeError('failed/drifted stage; preserve before continuation: '+stage)
        # Final public resampling check precedes terminal phase3/private grade.
        final_wait=time.monotonic()
        while not {'eval2_public','eval2_private'}<={g['grading_id'] for g in summary['grading']}:
            if not alive() or remaining()<=40 or time.monotonic()-final_wait>plan['stage_wait_seconds']:
                raise RuntimeError('finite wait before final terminal grading')
            done_grades={g['grading_id'] for g in summary['grading']}
            process_grading({'eval2_public'} if 'eval2_public' not in done_grades else {'eval2_private'})
            time.sleep(min(plan['wait_poll_seconds'],remaining()-35))
    except BaseException as exc:summary['error']=repr(exc)[:2048]
    finally:
        kill_owned()
        for proc in procs:
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
        summary['server_returncodes']=[p.returncode for p in procs]
        for thread in threads:thread.join(timeout=5)
        summary.update(elapsed_seconds=time.monotonic()-start,assigned_calls_reserved=reserved,
            completion_tokens_reserved=1024*reserved,retained_bytes=retained(),
            retained_bytes_conservative_charged=retained(),
            retained_accounting='monotone conservative charges, bounded log/control reserve; scans only after qualification/grading',
            retained_boundary_scans=retained_ledger.scans,guard_failures=log_errors,
            unentered_stage_ids=[s for s in STAGES if s not in {r['stage_id'] for r in summary['stages']}])
        publish(out/'summary.json',summary)
    if summary['error']:raise RuntimeError(summary['error'])
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    run(parser.parse_args().plan)
