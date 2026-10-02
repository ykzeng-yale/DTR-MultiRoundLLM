"""Frozen mechanical lead driver for one owned nine-stage sprint allocation.

This program makes no scientific choices, samples no randomization, submits no
jobs and executes no candidate code. It advances exact pinned public-state and
sanitized grading receipts through the existing frozen helpers. Private case
values stay in the qualified remote grader. Administrative failure stops this
driver with immutable evidence; it never retries a stage or substitutes a job.

Run `--make-plan SPEC --out PLAN` before committing the driver/plan, then launch
`--plan PLAN`. SPEC supplies exact saved job/SSH identities and existing files.
All generated raw files remain in ignored work; only hash manifests are committed.
"""
import argparse
import base64
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import resource
import shlex
import signal
import subprocess
import sys
import tarfile
import threading
import time

# Must precede numpy imports in the trusted fitted-Q helpers.
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.sprint import pipeline_v1 as pipeline
from experiments.sprint import receiver_v1 as receiver
from experiments.sprint import worker_v2 as worker_source
from experiments.sprint_analysis import inference_v1 as inference
from experiments.landmark.collect import receiver_state
from experiments.measurement_sprint_v4 import execution_v4 as execution
from experiments.containment import stdio_sprint_qualification_v4 as qualification
from scripts import prepare_sprint_release_v1 as release
from scripts import run_sprint_pipeline as helpers
from scripts import audit_sprint_generation_v1 as generation_audit
from scripts import audit_sprint_grading_v1 as grading_audit

VERSION='sprint-one-owned-job-mechanical-lead-v5'
SHA=re.compile(r'[0-9a-f]{64}')
COMMIT=re.compile(r'[0-9a-f]{40}')
STAGES=tuple(worker_source.STAGES)
GRADES=tuple(worker_source.GRADING)
LOCAL_CAPS={'wall_seconds':72*3600,'cpu_seconds':7200,'rss_bytes':8<<30,
            'retained_bytes':100<<30,'file_bytes':2<<30,'poll_seconds':30,
            'batch_wall_seconds':3600,'batch_cpu_seconds':14000,
            'batch_retained_bytes':20<<30,'transport_seconds':1200,'paid_usd':0}


def require(value,reason):
    if not value:raise ValueError(reason)


def canonical(value):return receiver.canonical(value)
def sha(value):return receiver.sha(value)
def digest(path):return receiver.file_sha(Path(path))


def read(path,cap=2<<30):
    p=Path(path);require(not p.is_symlink() and p.stat().st_size<=cap,'bounded regular JSON file')
    return generation_audit.strict_json(p.read_bytes())


def relative(value):
    require(type(value) is str and value and '\x00' not in value,'relative path string')
    p=PurePosixPath(value)
    require(not p.is_absolute() and '..' not in p.parts and p.parts[0]!='.git','owned relative path')
    return str(p)


def raw_write(path,raw):
    """Immutable publication; matching existing bytes are recovery, not overwrite."""
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        require(not p.is_symlink() and digest(p)==hashlib.sha256(raw).hexdigest(),'immutable local file changed')
        return p
    with p.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return p


def write(path,value):return raw_write(path,canonical(value)+b'\n')


def ssh_command(route,command):
    """One correctly quoted nested SSH command; local shell is never invoked."""
    require(set(route)=={'outer','inner'},'SSH route schema')
    for argv in route.values():
        require(type(argv) is list and all(type(a) is str and a and '\x00' not in a for a in argv),'SSH argv')
        require(not argv or Path(argv[0]).name=='ssh','only SSH transport')
    require(route['inner'],'inner authenticated Bouchet route required')
    inner=route['inner']+[command]
    return route['outer']+[shlex.join(inner)] if route['outer'] else inner


def generation_go(report):
    """Completed isolated service failure retains the declared fallback law.

    Fatal receiver/admin/cap errors never authorize another stage. Missing
    outputs are preserved in the audit, not reclassified as STOP or zero.
    """
    require(report['unattempted']==0 and report['terminal_error'] is None and
            report['global_cap_reason'] is None and report['receiver_state_unchanged'] is True and
            report['all_returned_tokenizer_reconciled'] and
            not report['nonzero_cached_token_execution_ids'] and
            set(report['failure_kind_counts']) <= {'isolated_service_failure'},
            'generation fatal/admin/drift/incomplete evidence: preserve and stop')
    return True


def grade_caps(worker,used,remaining_wall,actual_owned_bytes,prior_bytes,caps=LOCAL_CAPS):
    """Reserve actual measured prior batches plus the pinned audit allowance.

    Monotone worker charges are bounded above by twice actual current owned
    files plus its fixed log/control/prior reserve. This is deliberately more
    conservative than the worker's live retained counter.
    """
    allowance=worker['grading_reconciliation_seconds']
    reserve=2*worker['server_log_cap_bytes']+receiver.FIXED_RESERVE+prior_bytes
    cases=worker['max_case_starts']-sum(r['case_starts'] for r in used)
    cpu=worker['max_grading_cpu_seconds']-sum(r['cpu_seconds'] for r in used)-allowance
    wall=int(remaining_wall)-allowance-150
    retained=worker['max_retained_bytes']-(2*actual_owned_bytes+reserve)-receiver.FIXED_RESERVE
    result={'max_case_starts':cases,'max_cpu_seconds':min(caps['batch_cpu_seconds'],int(cpu)),
            'max_wall_seconds':min(caps['batch_wall_seconds'],wall),
            'max_retained_bytes':min(caps['batch_retained_bytes'],retained)}
    require(all(type(v) is int and v>0 for v in result.values()),'finite global grading envelope exhausted')
    return result


def owned_bytes(directory,cap):
    total=0;count=0
    for p in Path(directory).rglob('*'):
        require(not p.is_symlink(),'local evidence symlink refused')
        if p.is_file():
            count+=1;require(count<=2000000,'local evidence file count cap')
            total+=p.stat().st_size;require(total<=cap,'global local retained cap')
    return total


def make_plan(spec,repo):
    """Data-only freeze. No SSH, job action, RNG, private payload or fitting."""
    repo=Path(repo).resolve()
    keys={'job_id','remote_dir','job_name','account','partition','user','ssh_route',
          'worker_plan','tasks','source_manifest','bundle_dir','development_config',
          'development0_state','development0_requests','tuning_config','tuning0_state',
          'evaluation_randomization','evaluation_namespace_seed','output_dir','manifest_prefix','recovery_checkpoint'}
    require(set(spec)==keys,'exact driver specification fields')
    require(re.fullmatch(r'[0-9]+',spec['job_id']) and spec['job_id']!='27982976','one new saved job, never old collector')
    require(type(spec['remote_dir']) is str and spec['remote_dir'].startswith('/nfs/') and '..' not in PurePosixPath(spec['remote_dir']).parts,'owned Bouchet directory')
    ssh_command(spec['ssh_route'],'true')
    require(type(spec['evaluation_namespace_seed']) is int,'prospectively pinned namespace, never RNG source')
    for name in ('job_name','account','partition','user'):
        require(re.fullmatch(r'[a-zA-Z0-9_.-]+',spec[name]),'saved scheduler identity')
    for name in keys-{'job_id','remote_dir','job_name','account','partition','user','ssh_route','evaluation_namespace_seed'}:
        relative(spec[name])
    require(spec['output_dir'].startswith('work/') and spec['manifest_prefix'].startswith('results/'),'ignored raw/public hash manifest separation')
    worker=read(repo/spec['worker_plan']);require(worker['mode']=='finite-stage-spool-v6' and tuple(worker['stage_ids'])==STAGES and tuple(worker['grading_ids'])==GRADES,'unchanged full nine-stage worker')
    require(worker['resources']['account']==spec['account'] and worker['resources']['partition']==spec['partition'] and worker['paid_usd']==0,'exact saved resource association')
    require(len(worker['resume_completed_stages'])==1 and worker['resume_completed_stages'][0]['stage_id']=='dev0','only terminal original dev0 can resume')
    inputs={name:{'path':spec[name],'sha256':digest(repo/spec[name])} for name in
        ('recovery_checkpoint','worker_plan','tasks','source_manifest','development_config','development0_state','development0_requests','tuning_config','tuning0_state','evaluation_randomization')}
    checkpoint=read(repo/spec['recovery_checkpoint'])
    require(checkpoint['job_id']=='28091783','exact preserved checkpoint job')
    def artifact_paths(value):
        if isinstance(value,str) and value.startswith('work/') and (repo/value).is_file():return [value]
        if isinstance(value,dict):return [p for v in value.values() for p in artifact_paths(v)]
        if isinstance(value,list):return [p for v in value for p in artifact_paths(v)]
        return []
    for i,path in enumerate(sorted(set(artifact_paths(checkpoint['done'])))):
        inputs['recovery_artifact_'+str(i)]={'path':path,'sha256':digest(repo/path)}
    pins=dict(worker['files'])
    for module in (sys.modules[__name__],release,helpers,generation_audit,grading_audit,inference):
        p=Path(module.__file__).resolve();pins[str(p.relative_to(repo))]=digest(p)
    for p,pin in pins.items():require(digest(repo/relative(p))==pin,'prospectively pinned source drift')
    dev=read(repo/spec['development_config']);tune=read(repo/spec['tuning_config'])
    public=helpers.tasks(repo/spec['tasks'])
    pipeline.validate_config(dev,public);pipeline.validate_config(tune,public)
    require(dev['mode']=='development' and tune['mode']=='tuning' and dev['pins']==tune['pins'] and
            len(dev['initials'])==5472 and len(tune['initials'])==444,'complete frozen initial studies')
    pipeline.validate_randomization(read(repo/spec['evaluation_randomization']),public,'evaluation',32)
    value={'version':VERSION,'spec':spec,'inputs':inputs,'files':pins,'caps':dict(LOCAL_CAPS),
        'stages':list(STAGES),'grading_ids':list(GRADES),'no_job_submission':True,'no_candidate_execution':True,
        'no_rng_sampling':True,'no_automatic_retries':True,'private_values_in_git':False,
        'local_memory_enforcement':'RSS measured at boundaries; Linux AS bound; Darwin AS limit unsupported',
        'classification':'mechanical frozen finite operational study; no broad efficacy claim'}
    value['plan_sha256']=sha(value)
    return value


# Fixed trusted remote file/metadata helper. It never imports project/candidate
# code. A write is confined to this driver's work subtree or the exact spool.
REMOTE_HELPER=r'''
import base64,hashlib,json,os,pathlib,subprocess,sys,time
x=json.load(sys.stdin);root=pathlib.Path(x['root']).resolve();assert root.is_dir()
def path(value):
 p=pathlib.PurePosixPath(value);assert not p.is_absolute() and '..' not in p.parts
 q=root/str(p);assert q.resolve().is_relative_to(root);assert not q.is_symlink();return q
op=x['op']
if op=='exists':
 q=path(x['path']);print(json.dumps({'exists':q.is_file(),'bytes':q.stat().st_size if q.is_file() else None}))
elif op=='write':
 name=x['path'];assert name.startswith(x['write_prefix']+'/') or name.startswith(x['spool_prefix']+'/')
 q=path(name);raw=base64.b64decode(x['raw'],validate=True);assert len(raw)<=x['cap']
 assert hashlib.sha256(raw).hexdigest()==x['sha256'];q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():assert q.is_file() and hashlib.sha256(q.read_bytes()).hexdigest()==x['sha256']
 else:
  temporary=q.with_name(q.name+'.driver-tmp-'+str(os.getpid()))
  with temporary.open('xb') as s:s.write(raw);s.flush();os.fsync(s.fileno())
  os.link(temporary,q);temporary.unlink()
 print(json.dumps({'path':name,'sha256':x['sha256'],'bytes':len(raw)}))
elif op=='verify':
 q=path(x['path']);assert q.is_file() and q.stat().st_size<=x['cap']
 raw=q.read_bytes();assert hashlib.sha256(raw).hexdigest()==x['sha256']
 print(json.dumps({'path':x['path'],'sha256':x['sha256'],'bytes':len(raw),'read_only':True}))
elif op=='stats':
 import os
 import stat
 import time


 def inventory(root, *, seconds=60, max_entries=2000000, max_bytes=100<<30):
     root=os.path.abspath(root)
     if os.path.islink(root) or not os.path.isdir(root):
         raise ValueError('regular owned directory required')
     deadline=time.monotonic()+seconds
     pending=[root];entries=files=total=0
     while pending:
         if time.monotonic()>=deadline:
             raise TimeoutError('incomplete inventory; no capacity conclusion')
         with os.scandir(pending.pop()) as scan:
             for entry in scan:
                 entries+=1
                 if entries>max_entries or time.monotonic()>=deadline:
                     raise TimeoutError('incomplete inventory; no capacity conclusion')
                 info=entry.stat(follow_symlinks=False)
                 if stat.S_ISDIR(info.st_mode):pending.append(entry.path)
                 elif stat.S_ISREG(info.st_mode):
                     files+=1;total+=info.st_size
                     if total>max_bytes:raise ValueError('retained byte cap exceeded')
                 else:raise ValueError('nonregular evidence entry refused')
     return {'complete':True,'files':files,'entries':entries,'bytes':total}

 print(json.dumps(inventory(path(x['path']),seconds=300)))
elif op=='job':
 jid=x['job_id'];assert jid.isdigit()
 def run(a):
  r=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=True)
  assert len(r.stdout)<65536;return r.stdout.decode()
 queue=run(['squeue','-h','-j',jid,'-o','%i|%j|%a|%P|%u|%T|%M|%l|%R|%Z'])
 acct=run(['sacct','-n','-P','-j',jid,'--format=JobIDRaw,JobName%100,Account%100,Partition%64,User%64,State,ExitCode,ElapsedRaw,TimelimitRaw,Start,End'])
 print(json.dumps({'queue':queue,'accounting':acct,'observed_unix':time.time()}))
else:raise ValueError('fixed metadata operation')
'''


class Transport:
    def __init__(self,plan):self.plan=plan;self.spec=plan['spec'];self.calls=0
    def command(self,command):return ssh_command(self.spec['ssh_route'],command)
    def rpc(self,op,**fields):
        payload=dict(root=self.spec['remote_dir'],op=op,**fields)
        command='/usr/bin/python3 -c '+shlex.quote(REMOTE_HELPER)
        # Bounded transport-only retry. Writes are idempotent: exact existing
        # bytes must match and the exclusive atomic release is never replaced.
        for attempt in range(2):
            result=subprocess.run(self.command(command),input=canonical(payload),stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,timeout=min(360 if op=='stats' else 120,self.plan['caps']['transport_seconds']),check=False)
            if result.returncode==0:break
            if result.returncode!=255 or attempt==1:
                raise subprocess.CalledProcessError(result.returncode,self.command(command),output=result.stdout,stderr=result.stderr)
            time.sleep(2)

        require(len(result.stdout)<=1<<20 and len(result.stderr)<=65536,'bounded SSH metadata response')
        self.calls+=1;return generation_audit.strict_json(result.stdout)
    def exists(self,path):return self.rpc('exists',path=relative(path))['exists']
    def upload(self,path,local):
        raw=Path(local).read_bytes();require(len(raw)<=self.plan['caps']['file_bytes'],'bounded exact upload')
        name=relative(path)
        if not (name.startswith(self.spec['output_dir']+'/') or name.startswith(self.worker['spool_dir']+'/')):
            return self.rpc('verify',path=name,sha256=hashlib.sha256(raw).hexdigest(),cap=self.plan['caps']['file_bytes'])
        return self.rpc('write',path=name,write_prefix=self.spec['output_dir'],
            spool_prefix=self.worker['spool_dir'],raw=base64.b64encode(raw).decode(),
            sha256=hashlib.sha256(raw).hexdigest(),cap=self.plan['caps']['file_bytes'])
    def fetch(self,paths,destination,*,root=None):
        """Bounded tar stream of receipt files only; reject links/traversal/devices."""
        root=root or self.spec['remote_dir'];paths=[relative(p) for p in paths]
        require(root.startswith('/nfs/') and paths,'owned retrieval root')
        command='tar --hard-dereference -C '+shlex.quote(root)+' -cf - -- '+shlex.join(paths)
        error=Path(destination)/'transport-stderr.tmp';Path(destination).mkdir(parents=True,exist_ok=True)
        with error.open('wb') as err:
            proc=subprocess.Popen(self.command(command),stdout=subprocess.PIPE,stderr=err)
            timer=threading.Timer(self.plan['caps']['transport_seconds'],proc.kill);timer.start()
            count=0;total=0;owned=owned_bytes(self.local_output,self.plan['caps']['retained_bytes'])
            try:
                with tarfile.open(fileobj=proc.stdout,mode='r|') as archive:
                    for member in archive:
                        count+=1;require(count<=2000000,'retrieval file count cap')
                        name=relative(member.name);target=Path(destination)/name
                        if member.isdir():target.mkdir(parents=True,exist_ok=True);continue
                        require(member.isfile() and member.size<=self.plan['caps']['file_bytes'],'only bounded regular evidence')
                        total+=member.size;require(total<=self.plan['caps']['retained_bytes'],'retrieval retained cap')
                        additional=0 if target.exists() else member.size
                        # A duplicate is streamed to a temporary file before its
                        # old immutable hash is checked, so reserve it too.
                        require(owned+member.size<=self.plan['caps']['retained_bytes'],'global local retained cap before retrieval')
                        target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.retrieving')
                        require(not temporary.exists(),'partial retrieval requires lead disposition, never blind repeat')
                        h=hashlib.sha256()
                        with archive.extractfile(member) as inp,temporary.open('xb') as out:
                            remaining=member.size
                            while remaining:
                                block=inp.read(min(1<<20,remaining));require(block,'truncated evidence stream')
                                out.write(block);h.update(block);remaining-=len(block)
                        if target.exists():require(not target.is_symlink() and digest(target)==h.hexdigest(),'immutable fetched evidence drift');temporary.unlink()
                        else:temporary.rename(target);owned+=additional
                require(proc.wait(timeout=20)==0,'SSH retrieval failed; preserve partial files')
                require(error.stat().st_size<=65536,'SSH stderr cap')
            finally:
                timer.cancel()
                if proc.poll() is None:proc.kill();proc.wait()
        error.unlink();self.calls+=1;return {'bytes':total,'files':count}


def parse_job(raw,spec):
    rows=[line.split('|') for line in raw['accounting'].splitlines() if line.strip()]
    base=[r for r in rows if r[0]==spec['job_id']]
    require(len(base)==1,'saved job accounting identity unavailable/ambiguous')
    r=base[0];require(len(r)>=11 and r[1]==spec['job_name'] and r[2]==spec['account'] and
        r[3]==spec['partition'] and r[4]==spec['user'],'foreign or changed scheduler identity')
    queue=[line.split('|') for line in raw['queue'].splitlines() if line.strip()]
    require(len(queue)<=1 and all(len(q)>=10 and q[0]==spec['job_id'] and q[1:5]==[spec['job_name'],spec['account'],spec['partition'],spec['user']] and q[9]==spec['remote_dir'] for q in queue),'foreign queue/directory identity')
    state=(queue[0][5] if queue else r[5]).split()[0]
    return {'job_id':spec['job_id'],'state':state,'elapsed_seconds':int(r[7]),'exit_code':r[6],
            'start':r[9],'end':r[10],'observed_unix':raw['observed_unix']}


class GitFreeze:
    """Commit only an allowlisted metadata manifest, preserving unrelated edits."""
    def __init__(self,repo,plan,check):self.repo=Path(repo);self.plan=plan;self.check=check
    def git(self,*args):
        r=subprocess.run(['git',*args],cwd=self.repo,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120,check=True)
        require(len(r.stdout)<=1<<20 and len(r.stderr)<=1<<20,'bounded git output')
        return r.stdout.decode().strip()
    def freeze(self,name,value):
        self.check();require(re.fullmatch('[a-z0-9_-]+',name),'allowlisted manifest identity')
        require(self.git('branch','--show-current')=='main','direct main integration only')
        require(self.git('config','user.name')=='Yukang Zeng' and self.git('config','user.email')=='ykzeng2019@gmail.com','owner commit identity')
        path=self.plan['spec']['manifest_prefix']+'_'+name+'.json';relative(path)
        raw=canonical(value)+b'\n';p=self.repo/path
        if p.exists():require(p.read_bytes()==raw,'previous immutable manifest conflict')
        else:raw_write(p,raw)
        # --only excludes already-staged unrelated files. No credentials/private
        # values enter value: caller supplies only explicit metadata fields.
        tracked=self.git('ls-files','--',path)
        if not tracked:self.git('add','--',path)
        changed=self.git('status','--porcelain','--',path)
        if changed:self.git('commit','--only','-m','Freeze sprint '+name,'--',path)
        self.git('fetch','origin')
        main=self.git('rev-parse','refs/remotes/origin/main');head=self.git('rev-parse','HEAD')
        self.git('show','--no-patch','--format=%H','refs/remotes/origin/main')
        if main!=head:
            common=self.git('merge-base','HEAD','refs/remotes/origin/main')
            if common!=main:self.git('merge','--no-edit','refs/remotes/origin/main')
        self.check();self.git('push','origin','HEAD:main')
        head=self.git('rev-parse','HEAD');require(COMMIT.fullmatch(head),'published freeze commit')
        witness=self.git('log','-1','--format=%H','--',path)
        require(COMMIT.fullmatch(witness),'manifest freeze witness')
        require(self.git('merge-base',witness,'refs/remotes/origin/main')==witness,'freeze not published')
        return witness


def audit_receiver_record(call,request,check):
    require(set(check)=={'execution_id','payload_sha256','template_prompt_sha256','tokens','context_tokens','completion_reserved','tokenizer_reserve'} and
        check['payload_sha256']==sha(request['payload']) and SHA.fullmatch(check['template_prompt_sha256']) and
        type(check['tokens']) is int and 0<=check['tokens']<=7152 and check['context_tokens']==8192 and
        check['completion_reserved']==1024 and check['tokenizer_reserve']==16,'receiver tokenizer/reservation metadata')
    response=call['response'];choices=response['choices'];usage=response['usage']
    require(type(choices) is list and len(choices)==1 and choices[0]['finish_reason'] in ('stop','length') and
        type(choices[0]['message']['content']) is str,'receiver response shape')
    require(hashlib.sha256(choices[0]['message']['content'].encode()).hexdigest()==call['raw_response_sha256'],'receiver response hash')
    require(type(usage['prompt_tokens']) is int and 0<=usage['prompt_tokens']<=7168 and
        type(usage['completion_tokens']) is int and 0<=usage['completion_tokens']<=1024 and
        call['prompt_tokens']==usage['prompt_tokens'] and call['completion_tokens']==usage['completion_tokens'] and
        abs(call['tokenizer_difference'])<=16 and call['tokenizer_difference']==call['prompt_tokens']-check['tokens'] and
        usage.get('prompt_tokens_details',{}).get('cached_tokens',0)==0 and
        usage.get('total_tokens',call['prompt_tokens']+call['completion_tokens'])==call['prompt_tokens']+call['completion_tokens'],
        'receiver token usage/caching/discrepancy fields')
    require(type(call['seconds']) in (int,float) and math.isfinite(call['seconds']) and call['seconds']>=0,'receiver measured latency')


def audit_qualification_fixture(row,index,name,definition,ready,att,caps):
    source,stdin,expected,status,reason=definition;receipt=row['receipt'];e=receipt['execution']
    require(row['assignment']==index and row['fixture']==name and row['source_sha256']==hashlib.sha256(source.encode()).hexdigest() and
        row['stdin_sha256']==hashlib.sha256(stdin).hexdigest() and row['expected_stdout_sha256']==hashlib.sha256(expected).hexdigest() and
        row['stdin_bytes']==len(stdin) and row['expected_stdout_bytes']==len(expected),'whole frozen fixture identity/value binding')
    require(receipt['status']==status and e['cleanup'] is True and e['payload_started'] is True and
        e['runtime_manifest_sha256']==ready['runtime_manifest_sha256'] and e['caps']==caps and
        e['source_sha256']==row['source_sha256'] and e['stdin_sha256']==row['stdin_sha256'] and
        e['host_binding']==att['host_binding'] and e['bootstrap_receipt']['source_sha256']==row['source_sha256'] and
        type(e['bootstrap_receipt']['nonce']) is str and re.fullmatch('[0-9a-f]{32}',e['bootstrap_receipt']['nonce']) and
        {'socket','fork','clone','execve','unshare','mount','ptrace','memfd_create'}<=set(e['bootstrap_receipt']['denied']) and
        (reason is None or receipt['reason']==reason),'independent trusted fixture criterion')
    if status=='PASS':
        require(e['disposition']=='completed' and e['returncode']==0 and e['outcome_available'] is True and
            e['stdout_sha256']==row['expected_stdout_sha256'] and e['stdout_bytes']==len(expected),
            'trusted PASS requires exact saved output hash/length')
    else:
        require(e['outcome_available'] is True and receipt['outcome']==0,'trusted failure is a completed operational zero')
    require(row['passed'] is True,'fixture reported flag disagreement')
    require(type(e['seconds']) in (int,float) and math.isfinite(e['seconds']) and e['seconds']>=0,'trusted execution measured wall')

def audit_qualification(directory,worker,ready,remote_output,job_id):
    """Recount 26 fixed controls and18 exact receiver metadata, data only."""
    d=Path(directory);q=d/'qualification';plan=read(worker['qualification_plan_path'],1<<20)
    require(digest(worker['qualification_plan_path'])==worker['qualification_plan_sha256'],'qualification plan pin')
    summary=read(q/'summary.json',2<<20);att=read(q/'attestation.json',2<<20)
    runtime=read(q/'runtime-manifest.json',2<<20)
    require(summary==att and digest(q/'attestation.json')==ready['attestation_file_sha256'] and
        digest(q/'runtime-manifest.json')==ready['runtime_manifest_sha256'] and
        runtime['version']==qualification.runtime.VERSION,
        'fresh attestation/runtime raw bindings')
    require(att['job_id']==job_id and att['plan_sha256']==worker['qualification_plan_sha256'] and
        att['caps']==plan['caps'] and att['error'] is None and att['host_canary_unchanged'] and att['passed'] is True and
        att['planned_fixtures']==att['passed_fixtures']==list(execution.REQUIRED_FIXTURES) and
        (q/'host-canary').read_text()=='owned qualification sentinel; not mounted\n','qualified actual job/caps/canary')
    bindings=execution.source_bindings();require(att['host_binding']['source_sha256s']==bindings,'runtime executor source binding')
    definitions=qualification.fixtures(plan['caps'],Path(remote_output)/'qualification'/'host-canary')
    rows=[generation_audit.strict_json(r) for r in (q/'journal.jsonl').read_bytes().splitlines()]
    require(len(rows)==len(execution.REQUIRED_FIXTURES)==26,'all fixed isolation controls retained')
    for index,name in enumerate(execution.REQUIRED_FIXTURES):
        audit_qualification_fixture(rows[index],index,name,definitions[name],ready,att,plan['caps'])
    require(att['completed']==26 and att['failures']==0 and att['unattempted']==0,'qualification all-assigned recount')
    props=read(d/'props-before.json',1<<20)
    require(len(props)==worker['server_count'] and all(sha(receiver_state(p))==worker['receiver_state_sha256'] for p in props),'actual receiver state all instances')
    cal=read(d/'receiver-qualification'/'summary.json',2<<20)
    require(digest(d/'receiver-qualification'/'summary.json')==ready['receiver_qualification_sha256'],'receiver qualification pin')
    calls=cal['calls'];journal=[generation_audit.strict_json(r) for r in (d/'receiver-qualification'/'journal.jsonl').read_bytes().splitlines()]
    require(len(calls)==18 and cal['unattempted']==0 and {c['execution_id']:c for c in calls}=={c['execution_id']:c for c in journal} and len(journal)==18,'all receiver synthetic assignments/raw equality')
    requested=worker_source.synthetic_requests(worker['receiver_qualification_seed'],worker['server_count'])
    checks={c['execution_id']:c for c in cal['tokenizer_preflight']}
    by_id={c['execution_id']:c for c in calls}
    require(set(by_id)==set(checks)=={r['execution_id'] for r in requested},'receiver tokenizer/assignment completeness')
    for request in requested:
        c=by_id[request['execution_id']];check=checks[c['execution_id']]
        require(c['status']=='returned' and c['payload_sha256']==sha(request['payload']) and
            c['server_index']==request['payload']['seed']%worker['server_count'] and
            all(c[k]==request[k] for k in generation_audit.IDENTITY_KEYS),'receiver exact seed/route/identity')
        audit_receiver_record(c,request,check)
    require(ready['job_id']==job_id and ready['node'] and ready['hardware_epoch']==worker['hardware_epoch'] and
        len(ready['gpu_identity'].splitlines())==2 and all(', NVIDIA H100' in line for line in ready['gpu_identity'].splitlines()),'actual continuation hardware epoch')
    return {'job_id':job_id,'qualification_controls':26,'receiver_calls':18,'runtime_manifest_sha256':ready['runtime_manifest_sha256'],
            'attestation_sha256':ready['attestation_file_sha256'],'receiver_qualification_sha256':ready['receiver_qualification_sha256'],
            'limitations':['bounded fixed-control recount, not kernel/security proof','freshness/no-interference remain assumptions'],
            'candidate_execution_here':False}


def rebind_checkpoint(old,plan):
    """Only exact terminal-prefix recovery; never discard completed steps."""
    require(old['job_id']=='28091783' and plan['spec']['job_id']!=old['job_id'],'new owned allocation for terminal old job')
    done=dict(old['done'])
    require(all(k in done for k in ('development_join','fit','tuning_join','select_b1','evaluation_freeze','eval0_generation','eval0_public','eval0_advance')) and
            not any(k in done for k in ('eval1_generation','final_analysis')),
            'exact interrupted pre-eval0-public checkpoint')
    require(len(old['grading'])==7,'all completed grading records retained')
    done.pop('qualified',None)
    return {'version':VERSION,'plan_sha256':plan['plan_sha256'],'job_id':plan['spec']['job_id'],
            'done':done,'grading':old['grading'],'recovered_checkpoint_sha256':sha(old),'prior_job_id':old['job_id']}


class Driver:
    def __init__(self,plan,repo,transport=None,git=None):
        self.plan=plan;self.spec=plan['spec'];self.repo=Path(repo).resolve();self.out=self.repo/self.spec['output_dir']
        self.out.mkdir(parents=True,exist_ok=True);self.raw=self.out/'retrieved';self.raw.mkdir(exist_ok=True)
        self.worker=read(self.repo/self.spec['worker_plan']);self.worker['_file_sha256']=digest(self.repo/self.spec['worker_plan'])
        self.transport=transport or Transport(plan);self.transport.worker=self.worker;self.transport.local_output=self.out
        self.started=time.monotonic();self.job=None;self.job_check_at=0;self.ready=None
        self.checkpoint=self.out/'checkpoint.json';self.journal=self.out/'driver-journal.jsonl'
        self.state=read(self.checkpoint) if self.checkpoint.exists() else rebind_checkpoint(read(self.repo/self.spec['recovery_checkpoint']),plan)
        if not self.checkpoint.exists():write(self.checkpoint,self.state)
        require(self.state['plan_sha256']==plan['plan_sha256'] and self.state['job_id']==self.spec['job_id'],'same saved driver recovery only')
        self.git=git or GitFreeze(self.repo,plan,self.verify)
        self.public=helpers.tasks(self.repo/self.spec['tasks']);self.lock_handle=None
        self.prior_bytes=self.worker['prior_artifact_bytes']
    def verify(self):
        require(sha({k:v for k,v in self.plan.items() if k!='plan_sha256'})==self.plan['plan_sha256'],'driver plan drift')
        for path,pin in self.plan['files'].items():require(digest(self.repo/path)==pin,'frozen local source drift: '+path)
        for entry in self.plan['inputs'].values():require(digest(self.repo/entry['path'])==entry['sha256'],'frozen existing data drift')
        require(time.monotonic()-self.started<self.plan['caps']['wall_seconds'],'local driver wall cap')
        use=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
        require(use.ru_utime+use.ru_stime+children.ru_utime+children.ru_stime<self.plan['caps']['cpu_seconds'],'local driver CPU cap')
        rss=use.ru_maxrss*(1 if sys.platform=='darwin' else 1024)
        require(rss<=self.plan['caps']['rss_bytes'],'local driver RSS cap')
        owned_bytes(self.out,self.plan['caps']['retained_bytes'])
    def event(self,kind,**fields):
        record={'kind':kind,'job_id':self.spec['job_id'],'at':datetime.now(timezone.utc).isoformat(),**fields}
        with self.journal.open('ab') as stream:stream.write(canonical(record)+b'\n');stream.flush();os.fsync(stream.fileno())
    def save(self,key,value):
        require(key not in self.state['done'] or self.state['done'][key]==value,'checkpoint immutable disposition conflict')
        self.state['done'][key]=value
        temp=self.checkpoint.with_suffix('.tmp');temp.write_bytes(canonical(self.state)+b'\n');os.replace(temp,self.checkpoint)
    def once(self,key,operation):
        if key in self.state['done']:return self.state['done'][key]
        self.verify();value=operation();self.save(key,value);self.event('completed_step',step=key);return value
    def owned_job(self,force=False):
        if force or self.job is None or time.monotonic()-self.job_check_at>=300:
            self.job=parse_job(self.transport.rpc('job',job_id=self.spec['job_id']),self.spec)
            self.job_check_at=time.monotonic();self.event('scheduler_observation',**{k:v for k,v in self.job.items() if k!='job_id'})
        return self.job
    def wait(self,path):
        active_begin=None
        while not self.transport.exists(path):
            self.verify();job=self.owned_job()
            require(job['state'] in ('PENDING','RUNNING','CONFIGURING','COMPLETING'),'owned job terminal before expected evidence; reconcile, never resubmit')
            if job['state']!='PENDING':
                if active_begin is None:active_begin=time.monotonic()
                require(time.monotonic()-active_begin<=self.worker['stage_wait_seconds'],'bounded active-stage receipt wait')
            require(time.time()<datetime.fromisoformat(self.worker['owner_deadline_iso'].replace('Z','+00:00')).timestamp(),'owner deadline')
            time.sleep(self.plan['caps']['poll_seconds'])
    def collect(self,paths):
        self.transport.fetch(paths,self.raw);return self.raw
    def data(self,name,value):
        path=self.spec['output_dir']+'/prepared/'+relative(name)+'.json';raw=canonical(value)+b'\n'
        require(len(raw)<=self.plan['caps']['file_bytes'],'bounded generated exact data')
        if not (self.repo/path).exists():require(owned_bytes(self.out,self.plan['caps']['retained_bytes'])+len(raw)+(1<<20)<=self.plan['caps']['retained_bytes'],'local retained reserve before data')
        raw_write(self.repo/path,raw);return path
    def metadata_freeze(self,name,paths,extra=None):
        self.verify();info={'version':VERSION,'job_id':self.spec['job_id'],'driver_plan_sha256':self.plan['plan_sha256'],
            'files':{p:{'sha256':digest(self.repo/p),'bytes':(self.repo/p).stat().st_size} for p in paths},
            'private_values_included':False,'candidate_execution':False,'no_new_randomization':True,**(extra or {})}
        return self.git.freeze(name,info)
    def upload(self,paths):
        for p in paths:self.transport.upload(p,self.repo/p)
    def qualify(self):
        self.wait(self.worker['output_dir']+'/ready.json')
        prefix=self.worker['output_dir'];paths=[prefix+'/ready.json',prefix+'/props-before.json',prefix+'/receiver-qualification',prefix+'/resume-completed-stages.json']
        paths += [prefix+'/qualification/'+p for p in ('summary.json','attestation.json','runtime-manifest.json','journal.jsonl','host-canary')]
        self.collect(paths);self.ready=read(self.raw/prefix/'ready.json',1<<20);release.binding(self.worker,self.ready)
        report=audit_qualification(self.raw/prefix,self.worker,self.ready,self.spec['remote_dir']+'/'+prefix,self.spec['job_id'])
        p=self.data('qualification-recount',report);self.metadata_freeze('qualified_worker',[p],{'qualified_controls':26,'receiver_calls':18})
        self.save('qualified',{'report':p,'ready_file_sha256':digest(self.raw/prefix/'ready.json')})
    def resume_dev0(self):
        entry=self.worker['resume_completed_stages'][0];oldroot=str(Path(entry['original_worker_plan_path']).parent)
        paths=[str(Path(entry[k]).relative_to(oldroot)) for k in ('original_worker_plan_path','stage_plan_path','summary_path','journal_path','started_path')]
        destination=self.out/'original-dev0';self.transport.fetch(paths,destination,root=oldroot)
        for name in ('original_worker_plan','stage_plan','summary','journal','started'):
            key=name+'_path';pin=name+'_sha256' if name!='stage_plan' else 'stage_plan_file_sha256'
            require(digest(destination/str(Path(entry[key]).relative_to(oldroot)))==entry[pin],'immutable original resume input hash')
        plan_path=destination/str(Path(entry['stage_plan_path']).relative_to(oldroot))
        report=generation_audit.audit_files(stage_plan=plan_path,requests=self.repo/self.spec['development0_requests'],
            state=self.repo/self.spec['development0_state'],config=self.repo/self.spec['development_config'],
            summary=destination/str(Path(entry['summary_path']).relative_to(oldroot)),journal=destination/str(Path(entry['journal_path']).relative_to(oldroot)),
            started=destination/str(Path(entry['started_path']).relative_to(oldroot)),job_id=entry['original_job_id'],repo_root=self.repo)
        require(report['complete_generation_integrity'] and report['assigned']==report['returned']==5472,'no partial/failed dev0 resume or replay')
        p=self.data('dev0-generation-recount',report);self.metadata_freeze('dev0_preserved',[p],{'original_job_id':entry['original_job_id'],'returned':5472})
        return str((destination/str(Path(entry['summary_path']).relative_to(oldroot))).relative_to(self.repo))
    def generate(self,stage,config_path,state_path,model_lock=None):
        requests_path=self.data(stage+'-requests',read(self.repo/state_path)['requests'])
        freeze=self.metadata_freeze(stage+'_inputs',[config_path,state_path,requests_path])
        gp=release.stage_plan(self.worker,self.ready,stage,config_path,state_path,requests_path,freeze,model_lock)
        plan_path=self.data(stage+'-stage-plan',gp)
        self.metadata_freeze(stage+'_release',[plan_path],{'input_freeze':freeze,'assigned_calls':gp['max_calls']})
        self.upload([config_path,state_path,requests_path,plan_path])
        record={'stage_id':stage,'stage_plan_path':plan_path,'stage_plan_file_sha256':digest(self.repo/plan_path),'worker_plan_sha256':self.worker['_file_sha256']}
        release_path=self.data(stage+'-atomic-release',record)
        self.transport.upload(self.worker['spool_dir']+'/'+stage+'.ready.json',self.repo/release_path)
        self.event('stage_released',stage=stage,assigned=gp['max_calls'],plan_sha256=record['stage_plan_file_sha256'])
        prefix=self.worker['output_dir']+'/'+stage;self.wait(prefix+'/summary.json');self.collect([prefix])
        d=self.raw/prefix
        report=generation_audit.audit_files(stage_plan=self.repo/plan_path,requests=self.repo/requests_path,state=self.repo/state_path,
            config=self.repo/config_path,summary=d/'summary.json',journal=d/'journal.jsonl' if (d/'journal.jsonl').exists() else None,
            started=d/'started.jsonl' if (d/'started.jsonl').exists() else None,job_id=self.spec['job_id'],repo_root=self.repo)
        # V2 retains after-props separately: independently bind the actual state.
        s=read(d/'summary.json');props=read(d/'props-after.json')
        require(digest(d/'props-after.json')==s['props_after_sha256'] and
            len(props)==self.worker['server_count'] and all(sha(receiver_state(p))==self.worker['receiver_state_sha256'] for p in props),
            'saved after receiver state drift')
        p=self.data(stage+'-generation-recount',report);self.metadata_freeze(stage+'_reconciled',[p],{'returned':report['returned'],'failed':report['failed'],'unattempted':report['unattempted']})
        generation_go(report);return str((d/'summary.json').relative_to(self.repo))
    def remaining(self):
        actual=self.transport.rpc('stats',path=self.worker['output_dir'])['bytes']
        job=self.owned_job(force=True);require(job['state']=='RUNNING','grading requires actual running owned allocation')
        elapsed=job['elapsed_seconds']+max(0,time.time()-job['observed_unix'])
        wall=min(self.worker['max_seconds']-elapsed,datetime.fromisoformat(self.worker['owner_deadline_iso'].replace('Z','+00:00')).timestamp()-time.time())
        return grade_caps(self.worker,self.state['grading'],wall,actual,self.prior_bytes,self.plan['caps'])
    def grade(self,gid,config_path,state_path,assignments):
        assignment_path=self.data(gid+'-assignments',assignments)
        self.metadata_freeze(gid+'_inputs',[config_path,state_path,assignment_path],{'scope':gid.rsplit('_',1)[1],'assigned_units':len(assignments)})
        plan_path=self.spec['output_dir']+'/prepared/'+gid+'-grading-plan.json'
        if (self.repo/plan_path).exists():
            gp=read(self.repo/plan_path);caps={k:gp[k] for k in ('max_wall_seconds','max_cpu_seconds','max_case_starts','max_retained_bytes')}
        else:
            caps=self.remaining();gp=None
        expected=release.grading_plan(self.worker,self.ready,gid,config_path,state_path,assignment_path,
            self.spec['source_manifest'],self.spec['bundle_dir'],max_wall_seconds=caps['max_wall_seconds'],
            max_cpu_seconds=caps['max_cpu_seconds'],max_case_starts=caps['max_case_starts'])
        expected['max_retained_bytes']=caps['max_retained_bytes']
        require(gp is None or gp==expected,'previous frozen grade plan differs from exact inputs')
        gp=expected;plan_path=self.data(gid+'-grading-plan',gp)
        self.metadata_freeze(gid+'_release',[plan_path],{'scope':gp['scope'],'caps':caps})
        self.upload([config_path,state_path,assignment_path,plan_path])
        record={'grading_id':gid,'scope':gp['scope'],'plan_path':plan_path,'plan_sha256':digest(self.repo/plan_path),'worker_plan_sha256':self.worker['_file_sha256']}
        rp=self.data(gid+'-atomic-release',record);self.transport.upload(self.worker['spool_dir']+'/'+gid+'.grading.ready.json',self.repo/rp)
        prefix=self.worker['output_dir'];completion=prefix+'/'+gid+'.grading-complete.json';self.wait(completion)
        self.collect([completion,prefix+'/grading/'+gid,prefix+'/grading-cache',prefix+'/grading-reconciliation/'+gid+'.json'])
        completed=read(self.raw/completion,1<<20)
        require(completed['grading_id']==gid and completed['plan_sha256']==record['plan_sha256'],'actual grading completion identity')
        remote_output=self.spec['remote_dir']+'/'+prefix
        mappings=[remote_output+'='+str(self.raw/prefix),prefix+'='+str(self.raw/prefix),
                  self.spec['remote_dir']+'='+str(self.repo)]
        report=grading_audit.audit_batch(self.repo/plan_path,self.raw/prefix/'grading'/gid,root=self.repo,path_prefix=mappings)
        require(report['safe_to_advance'] and report['status']=='RECONCILED_COMPLETE','all assigned grading must reconcile before advance')
        worker_audit=self.raw/prefix/'grading-reconciliation'/(gid+'.json')
        require(digest(worker_audit)==completed['reconciliation_file_sha256'] and sha(read(worker_audit))==completed['reconciliation_sha256'] and read(worker_audit)['safe_to_advance'],'worker allocation independent recount pin')
        p=self.data(gid+'-grading-recount',report);self.metadata_freeze(gid+'_reconciled',[p],{'assigned_units':report['assigned_units'],'fresh_case_starts':report['fresh_case_starts']})
        if not any(r['grading_id']==gid for r in self.state['grading']):self.state['grading'].append(completed)
        return str((self.raw/prefix/'grading'/gid/'observations.json').relative_to(self.repo))
    def phase(self,stage,config_path,state_path,receipt_path,model_lock=None):
        config=read(self.repo/config_path);state=read(self.repo/state_path);receipt=read(self.repo/receipt_path)
        need_public=int(stage[-1])<2 or stage=='eval2'
        assignments=pipeline.public_assignments(state,receipt)
        if need_public:
            obs_path=self.once(stage+'_public',lambda:self.grade(stage+'_public',config_path,state_path,assignments))
            receipts=read(self.repo/obs_path)
        else:
            require(assignments==[],'unfrozen final public grading demand');receipts=[]
        observe=helpers.observer(receipts,'public',config['pins']['public_observer'])
        next_state=pipeline.advance(state,receipt,config,self.public,observe)
        next_path=self.data(stage[:-1]+str(int(stage[-1])+1)+'-state',next_state)
        self.metadata_freeze(stage+'_advanced',[next_path],{'phase':next_state['phase'],'retained_policy_rows':len(next_state['rows'])})
        return next_path
    def terminal(self,prefix,config_path,state_path):
        config=read(self.repo/config_path);state=read(self.repo/state_path);assignments=pipeline.private_assignments(state)
        obs_path=self.once(prefix+'2_private',lambda:self.grade(prefix+'2_private',config_path,state_path,assignments))
        grade=helpers.observer(read(self.repo/obs_path),'private',config['pins']['private_observer'])
        joined=pipeline.terminal_label_join(state,config,self.public,grade)
        path=self.data(prefix+'-terminal-label-join',joined);self.metadata_freeze(prefix+'_labels',[path],{'assigned_labels':len(joined['labels'])})
        return path
    def modes(self):
        devconfig=self.data('development-config',read(self.repo/self.spec['development_config']));state_path=self.data('development0-state',read(self.repo/self.spec['development0_state']))
        receipt=self.once('preserved_dev0',self.resume_dev0)
        for phase in range(3):
            stage='dev'+str(phase)
            if phase:receipt=self.once(stage+'_generation',lambda s=stage,sp=state_path:self.generate(s,devconfig,sp))
            state_path=self.once(stage+'_advance',lambda s=stage,sp=state_path,rp=receipt:self.phase(s,devconfig,sp,rp))
        labels=self.once('development_join',lambda:self.terminal('dev',devconfig,state_path))
        def fit():
            result=pipeline.fit_models(read(self.repo/state_path),read(self.repo/labels),read(self.repo/devconfig),self.public)
            path=self.data('fitted-models',result);freeze=self.metadata_freeze('actual_models',[path],{'model_sha256s':result['model_sha256s'],'no_evaluation_fit':True})
            return {'path':path,'freeze':freeze,'development_info_sha256':sha({'state':digest(self.repo/state_path),'labels':digest(self.repo/labels),'models':digest(self.repo/path)})}
        fitted=self.once('fit',fit)
        tuneconfig=self.data('tuning-config',read(self.repo/self.spec['tuning_config']));state_path=self.data('tuning0-state',read(self.repo/self.spec['tuning0_state']))
        for phase in range(3):
            stage='tune'+str(phase);receipt=self.once(stage+'_generation',lambda s=stage,sp=state_path:self.generate(s,tuneconfig,sp))
            state_path=self.once(stage+'_advance',lambda s=stage,sp=state_path,rp=receipt:self.phase(s,tuneconfig,sp,rp))
        labels=self.once('tuning_join',lambda:self.terminal('tune',tuneconfig,state_path))
        def select():
            result=pipeline.select_b1(read(self.repo/state_path),read(self.repo/labels),read(self.repo/tuneconfig))
            path=self.data('b1-choice',result);freeze=self.metadata_freeze('actual_b1',[path],{'selected_b1':result['selected_b1'],'choice_sha256':sha(result)})
            return {'path':path,'freeze':freeze,'tuning_info_sha256':sha({'state':digest(self.repo/state_path),'labels':digest(self.repo/labels),'choice':digest(self.repo/path)})}
        selected=self.once('select_b1',select)
        def evaluation():
            models=read(self.repo/fitted['path']);choice=read(self.repo/selected['path']);table=read(self.repo/self.spec['evaluation_randomization'])
            config=pipeline.make_config(self.public,mode='evaluation',repeats=32,seed=self.spec['evaluation_namespace_seed'],
                pins=read(self.repo/devconfig)['pins'],strategies=list(inference.STRATEGIES),model_sha256s=models['model_sha256s'],
                selected_b1=choice['selected_b1'],choice_lock_sha256=sha(choice),randomization=table)
            state=pipeline.initialize(config,self.public,models=models['models']);ip=inference.make_plan(config,self.public,conditioning={
                'nonrandom_protocol_sha256':self.worker['contract_sha256'],'development_info_sha256':fitted['development_info_sha256'],
                'tuning_info_sha256':selected['tuning_info_sha256'],'policies_lock_sha256':inference.policy_lock(config)})
            cp=self.data('evaluation-config',config);sp=self.data('eval0-state',state);pp=self.data('evaluation-inference-plan',ip)
            lock={'model_sha256s':models['model_sha256s'],'selected_b1':choice['selected_b1'],'choice_lock_sha256':sha(choice),
                  'freeze_commit':self.metadata_freeze('evaluation_before_calls',[cp,sp,pp],{'models_fit_commit':fitted['freeze'],'baseline_commit':selected['freeze'],'policy_sha256':inference.policy_lock(config),'inference_plan_sha256':ip['plan_sha256']})}
            return {'config':cp,'state':sp,'inference':pp,'lock':lock}
        evaluation=self.once('evaluation_freeze',evaluation);config_path=evaluation['config'];state_path=evaluation['state']
        for phase in range(3):
            stage='eval'+str(phase);receipt=self.once(stage+'_generation',lambda s=stage,sp=state_path:self.generate(s,config_path,sp,evaluation['lock']))
            state_path=self.once(stage+'_advance',lambda s=stage,sp=state_path,rp=receipt:self.phase(s,config_path,sp,rp))
        labels=self.once('evaluation_join',lambda:self.terminal('eval',config_path,state_path))
        def final():
            state=read(self.repo/state_path);joined=read(self.repo/labels);config=read(self.repo/config_path)
            report=inference.analyze(read(self.repo/evaluation['inference']),state,joined,config,self.public)
            account=pipeline.accounting(state);descriptive=pipeline.analyze(state,joined,config)
            rp=self.data('final-inference',report);ap=self.data('final-accounting',account);dp=self.data('final-descriptive',descriptive)
            freeze=self.metadata_freeze('final_all_assigned',[rp,ap,dp],{'quality_decision':report['decision'],'classification':'finite-source operational grade; no broad efficacy or total-cost claim'})
            return {'inference':rp,'accounting':ap,'descriptive':dp,'freeze':freeze}
        return self.once('final_analysis',final)
    def run(self):
        lock_path=self.out/'exclusive-driver.lock';self.lock_handle=lock_path.open('a+')
        fcntl.flock(self.lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.lock_handle.seek(0);self.lock_handle.truncate();self.lock_handle.write(json.dumps({'pid':os.getpid(),'plan_sha256':self.plan['plan_sha256'],'job_id':self.spec['job_id']}));self.lock_handle.flush()
        os.chdir(self.repo)
        try:
            self.verify();self.event('driver_started',pid=os.getpid(),no_job_submission=True)
            self.owned_job(force=True)
            if 'qualified' not in self.state['done']:self.qualify()
            else:
                prefix=self.worker['output_dir'];self.ready=read(self.raw/prefix/'ready.json');release.binding(self.worker,self.ready)
                audit_qualification(self.raw/prefix,self.worker,self.ready,self.spec['remote_dir']+'/'+prefix,self.spec['job_id'])
            result=self.modes();self.wait(self.worker['output_dir']+'/summary.json');self.collect([self.worker['output_dir']+'/summary.json'])
            final_worker=read(self.raw/self.worker['output_dir']/'summary.json')
            require(final_worker['error'] is None and not final_worker['unentered_stage_ids'],'all nine stages/worker terminal reconcile')
            self.event('study_complete',**result);return result
        except BaseException as exc:
            # No private/model exception text is emitted to logs; raw evidence
            # remains for the lead. Never cancel, renew, resubmit or regrade.
            self.event('driver_stopped',exception_type=type(exc).__name__,reason=str(exc)[:512] if isinstance(exc,ValueError) else 'execution/transport interrupted; preserved evidence requires lead review')
            raise
        finally:
            fcntl.flock(self.lock_handle,fcntl.LOCK_UN);self.lock_handle.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--make-plan',type=Path);group.add_argument('--plan',type=Path);group.add_argument('--preflight',type=Path)
    parser.add_argument('--out',type=Path);parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    if args.make_plan:
        require(args.out is not None,'fresh plan output required');write(args.out,make_plan(read(args.make_plan,1<<20),args.repo));return
    plan=read(args.plan or args.preflight,1<<20);require(plan['version']==VERSION and plan['caps']==LOCAL_CAPS,'frozen bounded driver version/caps')
    if args.preflight:
        require(sha({k:v for k,v in plan.items() if k!='plan_sha256'})==plan['plan_sha256'],'driver plan drift')
        for path,pin in plan['files'].items():require(digest(args.repo/path)==pin,'frozen source drift')
        for entry in plan['inputs'].values():require(digest(args.repo/entry['path'])==entry['sha256'],'existing data drift')
        actual=parse_job(Transport(plan).rpc('job',job_id=plan['spec']['job_id']),plan['spec'])
        require(actual['state'] in ('PENDING','RUNNING','CONFIGURING'),'saved job already terminal; preserve and review')
        print(json.dumps({'version':VERSION,'plan_sha256':plan['plan_sha256'],'job_id':actual['job_id'],'state':actual['state'],
            'candidate_executions':0,'job_actions':0,'local_process_started':False},sort_keys=True));return
    # Global process CPU bound plus main-thread wall bound. RSS is measured in
    # verify and AS constrained where supported; no shell/candidate execution.
    resource.setrlimit(resource.RLIMIT_CPU,(LOCAL_CAPS['cpu_seconds'],LOCAL_CAPS['cpu_seconds']+5))
    if sys.platform!='darwin':resource.setrlimit(resource.RLIMIT_AS,(LOCAL_CAPS['rss_bytes'],LOCAL_CAPS['rss_bytes']))
    resource.setrlimit(resource.RLIMIT_FSIZE,(LOCAL_CAPS['file_bytes'],LOCAL_CAPS['file_bytes']))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('bounded driver wall cap')))
    signal.alarm(LOCAL_CAPS['wall_seconds'])
    Driver(plan,args.repo).run()


if __name__=='__main__':main()
