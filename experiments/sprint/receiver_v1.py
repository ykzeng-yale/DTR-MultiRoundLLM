"""Finite four-slot CUDA receiver collection; generated programs never execute.

Owns only its newly started llama-server process group. All requests are frozen
and tokenizer-checked without truncation before generation. A service failure
retains its assignment and does not automatically discard unrelated calls.
Completed call rows are append/fsync journaled; summary is atomic once terminal.
This source alone releases neither study collection nor candidate execution.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.landmark.collect import receiver_state, NoRedirect

VERSION='sprint-cuda-four-slot-receiver-v1'
MODEL_SHA256='626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d'
STATE_SHA256='411ebaa409af6e3968161cfba76ddb1e52a04f43a1692d8f3499384d48f36795'
RESPONSE_CAP=262144
LOG_CAP=8<<20
FIXED_RESERVE=4<<20
PAYLOAD_KEYS={'messages','stream','cache_prompt','temperature','top_p','top_k','min_p','max_tokens','seed'}
REQUEST_KEYS={'slot','execution_id','grading_unit_id','root','artifact','arm','replicate','phase','payload'}


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_requests(requests,plan):
    if type(requests) is not list or len(requests)!=plan['max_calls'] or not 0<len(requests)<=plan['assignment_cap']:
        raise ValueError('exact finite request assignment count')
    ids=set();slots=set()
    for q in requests:
        if set(q)!=REQUEST_KEYS or q['execution_id'] in ids or q['slot'] in slots:
            raise ValueError('exact unique request identities')
        if type(q['slot']) is not int or q['slot']<0 or type(q['phase']) is not int or q['phase'] not in (0,1,2) or type(q['replicate']) is not int or q['replicate']<0 or any(type(q[k]) is not str or not q[k] for k in ('execution_id','grading_unit_id','root','artifact','arm')):
            raise ValueError('request identity types')
        p=q['payload']
        if set(p)!=PAYLOAD_KEYS or p['stream'] is not False or p['cache_prompt'] is not False or any(p[k]!=v for k,v in {'temperature':.7,'top_p':.95,'top_k':40,'min_p':.05,'max_tokens':1024}.items()) or type(p['seed']) is not int or not 0<=p['seed']<2**32:
            raise ValueError('frozen receiver decoding drift')
        if type(p['messages']) is not list or not p['messages'] or any(type(m) is not dict or set(m)!={'role','content'} or m['role'] not in ('system','user','assistant') or type(m['content']) is not str for m in p['messages']):
            raise ValueError('exact untruncated public message schema')
        if len(canonical(p))>plan['max_payload_bytes']:
            raise ValueError('frozen request byte cap')
        ids.add(q['execution_id']);slots.add(q['slot'])
    if plan['max_completion_tokens']!=1024*len(requests):
        raise ValueError('complete token reservation')
    if sha(requests)!=plan['requests_canonical_sha256']:
        raise ValueError('canonical assignment binding')


def response_check(response,preflight_tokens):
    usage=response.get('usage',{});choices=response.get('choices')
    if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason') not in ('stop','length'):
        raise ValueError('incomplete response choice')
    raw=choices[0].get('message',{}).get('content')
    if type(raw) is not str:raise ValueError('assistant UTF-8 response required')
    raw.encode('utf-8',errors='strict')
    completion=usage.get('completion_tokens');prompt=usage.get('prompt_tokens')
    if type(completion) is not int or not 0<=completion<=1024 or type(prompt) is not int or not 0<=prompt<=7168:
        raise ValueError('completion/context token accounting')
    # Template/tokenizer implementations can differ by a BOS token. Reserve16
    # prospectively, disclose mismatch rather than claiming exact certification.
    if abs(prompt-preflight_tokens)>16:
        raise ValueError('tokenizer versus actual prompt count drift')
    return {'raw_response_sha256':hashlib.sha256(raw.encode()).hexdigest(),
            'prompt_tokens':prompt,'completion_tokens':completion,
            'tokenizer_difference':prompt-preflight_tokens}


def preflight(http,q):
    templated=http('/apply-template',{'messages':q['payload']['messages']},30)
    prompt=templated.get('prompt')
    if type(prompt) is not str:raise ValueError('unsupported exact server chat-template endpoint')
    tokens=http('/tokenize',{'content':prompt,'add_special':True,'parse_special':True,'with_pieces':False},30).get('tokens')
    if type(tokens) is not list or any(type(t) is not int for t in tokens):
        raise ValueError('unsupported exact server tokenization')
    if len(tokens)+1024+16>8192:
        raise ValueError('original history exceeds frozen context; no truncation')
    return {'execution_id':q['execution_id'],'payload_sha256':sha(q['payload']),
            'template_prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
            'tokens':len(tokens),'context_tokens':8192,'completion_reserved':1024,
            'tokenizer_reserve':16}


def collect(requests,plan,http,alive,journal,remaining,stop_event,*,on_start=None,can_submit=None,transport_factory=None):
    """Four bounded worker calls; pure injectable transport for focused tests."""
    workers=plan.get('workers',4)
    servers=plan.get('server_count',1)
    if servers not in (1,2) or workers!=4*servers:raise ValueError('fixed four slots per one/two receiver instances')
    slots=[threading.BoundedSemaphore(4) for _ in range(servers)]
    def slot(q):return slots[q['payload']['seed']%servers]
    def bounded_preflight(q):
        reservation=slot(q)
        if not reservation.acquire(timeout=max(.01,remaining()-35)):
            raise RuntimeError('preflight global wall cap before receiver slot')
        try:return preflight(transport_factory(q) if transport_factory else http,q)
        finally:reservation.release()
    checks=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(bounded_preflight,q):q for q in requests}
        try:
            for future in futures:
                if remaining()<=35:raise RuntimeError('preflight global wall cap')
                checks.append(future.result())
        except BaseException:
            stop_event.set()
            for future in futures:future.cancel()
            raise
    check_by_id={p['execution_id']:p for p in checks}
    completed={};attempted=set();errors=[];global_reason=[None]
    def generate_on_slot(q):
        if stop_event.is_set() or remaining()<=35 or not alive():
            return None
        timeout=min(plan['request_timeout_seconds'],remaining()-30)
        if timeout<=0:return None
        t=time.monotonic()
        record={k:q[k] for k in REQUEST_KEYS-{'payload'}}
        record.update(status='assigned',payload_sha256=sha(q['payload']),
                      server_index=q['payload']['seed']%plan.get('server_count',1))
        if on_start is not None:on_start(record)
        attempted.add(q['execution_id'])
        try:
            transport=transport_factory(q) if transport_factory else http
            response=transport('/v1/chat/completions',q['payload'],timeout)
        except Exception as exc:
            kind='receiver_lost' if not alive() else 'administrative_deadline' if timeout<plan['request_timeout_seconds'] else 'isolated_service_failure'
            record.update(status='failed',error=repr(exc)[:2048],failure_kind=kind)
            if not alive():global_reason[0]='receiver_lost';stop_event.set()
        else:
            try:
                metadata=response_check(response,check_by_id[q['execution_id']]['tokens'])
                record.update(status='returned',response=response,**metadata)
            except Exception as exc:
                record.update(status='failed',response=response,error=repr(exc)[:2048],failure_kind='receiver_contract_violation')
        record['seconds']=time.monotonic()-t
        return record
    def generate(q):
        reservation=slot(q)
        while not stop_event.is_set() and remaining()>35 and alive():
            if reservation.acquire(timeout=min(1,max(.01,remaining()-35))):
                try:return generate_on_slot(q)
                finally:reservation.release()
        # No HTTP start receipt/cost is invented for an assignment that never
        # acquired a declared per-instance slot before administrative closure.
        return None
    with ThreadPoolExecutor(max_workers=workers) as pool:
        iterator=iter(requests);pending={}
        def fill():
            while len(pending)<workers and not stop_event.is_set() and remaining()>35 and alive():
                if can_submit is not None and not can_submit(len(pending)+1):
                    global_reason[0]='retained_artifact_cap';stop_event.set();break
                try:q=next(iterator)
                except StopIteration:break
                pending[pool.submit(generate,q)]=q
        fill()
        while pending:
            done,_=wait(pending,timeout=min(1,max(.01,remaining())),return_when=FIRST_COMPLETED)
            if remaining()<=30 or not alive():
                global_reason[0]='global_wall_or_owner_deadline' if remaining()<=30 else 'receiver_lost'
                stop_event.set()
            for future in done:
                q=pending.pop(future);record=future.result()
                if record is not None:
                    journal(record);completed[q['execution_id']]=record
                    if record['status']=='failed':errors.append(q['execution_id'])
            fill()
    ordered=[completed[q['execution_id']] for q in requests if q['execution_id'] in completed]
    if len(ordered)<len(requests) and global_reason[0] is None:
        global_reason[0]='global_wall_or_owner_deadline' if remaining()<=35 else 'receiver_lost' if not alive() else 'administrative_stop'
    return {'calls':ordered,'unattempted':len(requests)-len(ordered),'global_cap_reason':global_reason[0],
            'unattempted_execution_ids':[q['execution_id'] for q in requests if q['execution_id'] not in completed],
            'service_failed_execution_ids':errors,'tokenizer_preflight':checks,
            'attempted_without_journal':sorted(attempted-set(completed))}


def main(plan_path):
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_bytes())
    if plan['model_sha256']!=MODEL_SHA256 or plan['receiver_state_sha256']!=STATE_SHA256 or plan['workers']!=4 or plan['paid_usd']!=0:
        raise ValueError('pinned model/receiver/four-slot/$0 law')
    if plan['max_retained_bytes']<LOG_CAP+FIXED_RESERVE or not 120<plan['max_seconds']<=plan['wall_seconds']-15 or not 0<plan['request_timeout_seconds']<=120:
        raise ValueError('finite retained/wall/timeout envelope')
    for path,digest in plan['files'].items():
        if file_sha(path)!=digest:raise ValueError('frozen source/input mismatch: '+path)
    for path,key in (('model.gguf','model_sha256'),('build-sha256.txt','build_manifest_sha256')):
        if file_sha(path)!=plan[key]:raise ValueError('pinned runtime/build mismatch')
    subprocess.run(['sha256sum','-c','build-sha256.txt'],check=True,timeout=30)
    if not Path('build-complete.txt').exists():raise ValueError('receiver build incomplete')
    path=Path(plan['requests_path'])
    if path.stat().st_size>plan['max_requests_bytes'] or file_sha(path)!=plan['requests_file_sha256']:
        raise ValueError('frozen request file binding/byte cap')
    requests=json.loads(path.read_bytes());validate_requests(requests,plan)
    out=Path(plan.get('output_dir','generation'));out.mkdir(exist_ok=False)
    job=os.environ['SLURM_JOB_ID'];array=os.environ.get('SLURM_ARRAY_TASK_ID','')
    port=10000+int(hashlib.sha256((job+':'+array).encode()).hexdigest()[:8],16)%50000
    result={'version':VERSION,'job_id':job,'array_task_id':array,'port':port,
        'config_sha256':file_sha(plan_path),'study_config_sha256':plan['study_config_sha256'],
        'state_sha256':plan['state_sha256'],'requests_sha256':plan['requests_canonical_sha256'],
        'build_manifest_sha256':plan['build_manifest_sha256'],'freeze':Path('freeze.txt').read_text().strip(),
        'calls':[],'unattempted':len(requests),'error':None,'state_unchanged':False}
    start=time.monotonic();proc=None;thread=None;stop_event=threading.Event();log_fail=[];journal_bytes=0
    started_lock=threading.Lock();started_bytes=0
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def remaining():return plan['max_seconds']-(time.monotonic()-start)
    def http(endpoint,body=None,timeout=3):
        if remaining()<=15:raise RuntimeError('global receiver wall cap')
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+endpoint,
            data=None if body is None else canonical(body),headers={'Content-Type':'application/json'})
        with opener.open(req,timeout=min(timeout,max(.1,remaining()-15))) as response:
            raw=response.read(RESPONSE_CAP+1)
        if len(raw)>RESPONSE_CAP:raise ValueError('bounded receiver response exceeded')
        return json.loads(raw)
    def alive():return proc is not None and proc.poll() is None and not log_fail
    def kill_owned():
        stop_event.set()
        if proc is not None and proc.poll() is None:
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
    def interrupted(signum,frame):
        kill_owned();raise RuntimeError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def journal(record):
        nonlocal journal_bytes
        raw=canonical(record)+b'\n'
        # Reserve a second copy for the final summary before every write.
        if 2*(journal_bytes+len(raw))+LOG_CAP+FIXED_RESERVE>plan['max_retained_bytes']:
            kill_owned();raise RuntimeError('pre-write retained artifact cap')
        with (out/'journal.jsonl').open('ab') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        journal_bytes+=len(raw)
    def started(record):
        nonlocal started_bytes
        raw=canonical(record)+b'\n'
        with started_lock:
            if len(raw)>4096:raise ValueError('bounded call-start receipt')
            with (out/'started.jsonl').open('ab') as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            started_bytes+=len(raw)
    def can_submit(pending):
        # Reserve every in-flight response before starting it, including its
        # second final-summary copy; avoid a call that cannot be retained.
        return 2*(journal_bytes+pending*(RESPONSE_CAP+4096))+started_bytes+LOG_CAP+FIXED_RESERVE<plan['max_retained_bytes']
    try:
        with socket.socket() as sock:sock.bind(('127.0.0.1',port))
        command=['build/bin/llama-server','-m','model.gguf','--alias','qwen2.5-3b-instruct',
                 '--host','127.0.0.1','--port',str(port),'-ngl','99','-np','4','-c','32768','--jinja']
        result['command']=command
        proc=subprocess.Popen(command,env=dict(os.environ,LLAMA_MEDIA_MARKER=plan['media_marker']),
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        def log():
            total=0
            with (out/'server.log').open('xb') as stream:
                while True:
                    block=proc.stdout.read1(4096)
                    if not block:break
                    left=LOG_CAP-total
                    stream.write(block[:max(0,left)]);total+=len(block)
                    if total>LOG_CAP:
                        log_fail.append('server_log_cap');kill_owned();break
        thread=threading.Thread(target=log,daemon=True);thread.start()
        while time.monotonic()-start<120:
            if not alive():raise RuntimeError('owned receiver startup failed')
            try:
                if http('/health').get('status')=='ok':break
            except Exception:pass
            time.sleep(.5)
        else:raise RuntimeError('receiver startup timeout')
        before=http('/props')
        (out/'props-before.json').write_bytes(canonical(before))
        if sha(receiver_state(before))!=STATE_SHA256:raise ValueError('receiver properties differ from frozen CUDA law')
        result['ready_seconds']=time.monotonic()-start
        result.update(collect(requests,plan,http,alive,journal,remaining,stop_event,
                              on_start=started,can_submit=can_submit))
        after=http('/props');(out/'props-after.json').write_bytes(canonical(after))
        result['state_unchanged']=sha(receiver_state(after))==STATE_SHA256
        if not result['state_unchanged']:raise ValueError('receiver state drift')
    except BaseException as exc:
        result['error']=repr(exc)[:2048]
    finally:
        kill_owned()
        if proc is not None:
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
            result['server_returncode']=proc.returncode
        if thread:thread.join(timeout=5)
        # A cap/signal can interrupt collect() after fsynced rows. Reconstruct
        # the retained actual prefix from our own journal, never rerun calls.
        if (out/'journal.jsonl').exists():
            recovered=[json.loads(line) for line in (out/'journal.jsonl').read_bytes().splitlines()]
            mapped={r['execution_id']:r for r in recovered}
            if len(mapped)!=len(recovered):raise ValueError('duplicate persisted execution')
            result['calls']=[mapped[q['execution_id']] for q in requests if q['execution_id'] in mapped]
        if (out/'started.jsonl').exists():
            starts=[json.loads(line) for line in (out/'started.jsonl').read_bytes().splitlines()]
            mapped={c['execution_id']:c for c in result['calls']}
            if len({s['execution_id'] for s in starts})!=len(starts):raise ValueError('duplicate persisted call start')
            for record in starts:
                if record['execution_id'] not in mapped:
                    record.update(status='failed',error='started call lacked completed journal at terminal collection',
                                  failure_kind='interrupted_inflight_service',seconds=None)
                    mapped[record['execution_id']]=record
            result['calls']=[mapped[q['execution_id']] for q in requests if q['execution_id'] in mapped]
            result['started_sha256']=file_sha(out/'started.jsonl')
            result['started_bytes']=started_bytes
        result['unattempted']=len(requests)-len(result['calls'])
        result['unattempted_execution_ids']=[q['execution_id'] for q in requests if q['execution_id'] not in {c['execution_id'] for c in result['calls']}]
        result.update(elapsed_seconds=time.monotonic()-start,paid_usd=0,energy_measured=False,
                      journal_sha256=file_sha(out/'journal.jsonl') if (out/'journal.jsonl').exists() else None,
                      journal_bytes=journal_bytes,guard_failures=log_fail)
        encoded=canonical(result)+b'\n'
        retained=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
        if retained+len(encoded)>plan['max_retained_bytes']:
            raise RuntimeError('final retained artifact cap; immutable journal preserved')
        temp=out/'summary.json.tmp'
        with temp.open('xb') as stream:stream.write(encoded);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,out/'summary.json')
    if result['error']:raise RuntimeError(result['error'])
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True)
    path=parser.parse_args().plan
    if json.loads(path.read_bytes()).get('mode')=='finite-stage-spool-v1':
        from experiments.sprint.worker_v1 import run
        run(path)
    else:
        main(path)
