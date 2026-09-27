#!/usr/bin/env python3
"""Bounded owned-receiver synthetic resource calibration; never benchmark scoring."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.landmark.collect import receiver_state, digest, SYSTEM, NoRedirect
from scripts.launch_own_receiver_v31 import process_identity, terminate_owned_child

PLAN=Path('experiments/prompt_choice/receiver_calibration_plan_v2_20260927.json')


def sha_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def build_requests(plan):
    return [{'slot':i,'length_label':row['length_label'],'payload':{
        'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':plan['instruction']+'\n'+plan['context_line']*row['repeats']}],
        'stream':False,'cache_prompt':False,'temperature':.7,'top_p':.95,'top_k':40,'min_p':.05,
        'max_tokens':512,'seed':row['seed']}} for i,row in enumerate(plan['assignments'])]


def measurement(pid=None):
    pressure=subprocess.check_output(['memory_pressure','-Q'],text=True,timeout=3)
    swap=subprocess.check_output(['sysctl','-n','vm.swapusage'],text=True,timeout=3)
    free=int(re.search(r'free percentage: (\d+)%',pressure).group(1))
    used=float(re.search(r'used = ([\d.]+)M',swap).group(1))
    rss=None
    if pid:
        q=subprocess.run(['ps','-p',str(pid),'-o','rss='],capture_output=True,text=True,timeout=3)
        if q.returncode==0 and q.stdout.strip():rss=int(q.stdout.strip())*1024
    v=os.statvfs('.')
    return {'memory_pressure_free_percent':free,'swap_used_mib':used,'rss_bytes':rss,'disk_available_bytes':v.f_bavail*v.f_frsize}


def resource_violation(point,baseline,plan):
    if point['memory_pressure_free_percent']<plan['min_pressure_free_percent']:return 'memory_pressure'
    if point['swap_used_mib']-baseline['swap_used_mib']>plan['max_swap_growth_mib']:return 'swap_growth'
    if point['rss_bytes'] is not None and point['rss_bytes']>plan['max_receiver_rss_bytes']:return 'receiver_rss'
    if point['disk_available_bytes']<plan['min_disk_available_bytes']:return 'disk_available'
    return None


def http(path,payload=None,timeout=5):
    req=urllib.request.Request('http://127.0.0.1:8193'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(req,timeout=timeout) as response:
        raw=response.read(262145)
    if len(raw)>262144:raise ValueError('HTTP response cap')
    return json.loads(raw)


def capture_log(stream, output, cap, on_limit):
    """Retain at most cap bytes; never buffer the complete server stream."""
    total=0
    read=getattr(stream, 'read1', stream.read)
    while True:
        block=read(min(4096, cap-total+1))
        if not block:return total
        remaining=cap-total
        output.write(block[:remaining]);output.flush();total+=min(len(block),remaining)
        if len(block)>remaining:
            on_limit();return total


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    plan=json.loads(PLAN.read_bytes())
    for path in [str(PLAN),*plan['committed_sources']]:
        if subprocess.check_output(['git','show',args.freeze+':'+path])!=Path(path).read_bytes():raise ValueError('freeze mismatch: '+path)
    for path,h in plan['input_sha256'].items():
        if sha_file(path)!=h:raise ValueError('source hash mismatch')
    manifest=json.loads(Path('experiments/env/llama_server_manifest.json').read_bytes())
    for name,record in manifest['files'].items():
        if sha_file(Path('work/bin')/name)!=record['sha256']:raise ValueError('binary mismatch')
    snap=json.loads(Path('results/receiver_props_snapshot_8193.json').read_bytes());model=snap['model_path']
    if sha_file(model)!=plan['model_sha256']:raise ValueError('model mismatch')
    if args.out.exists():raise ValueError('refuse output reuse')
    peers=subprocess.run(['pgrep','-x','llama-server'],capture_output=True,text=True,timeout=3)
    if peers.returncode!=1:raise RuntimeError('receiver exists or inspection failed')
    with socket.socket() as probe:probe.bind(('127.0.0.1',8193))
    baseline=measurement()
    if resource_violation(baseline,baseline,plan):raise RuntimeError('resource preflight failed')
    args.out.mkdir(parents=True)
    requests=build_requests(plan)
    (args.out/'requests.json').write_text(json.dumps(requests,indent=2)+'\n')
    start=time.monotonic();stop=threading.Event();guard_failure=[];samples=[];calls=[];proc=None
    record={'classification':'synthetic receiver resource calibration; no task correctness, policy effect or benchmark inference',
            'freeze':args.freeze,'config_sha256':sha_file(PLAN),'started_utc':datetime.now(timezone.utc).isoformat(),
            'baseline':baseline,'model_sha256':plan['model_sha256'],'verified_build_files':len(manifest['files']),
            'planned_calls':len(requests),'calls':calls,'resource_samples':samples,'guard_failure':guard_failure,'error':None}
    def guard():
        while not stop.wait(2):
            try:
                point=measurement(proc.pid);point['seconds']=time.monotonic()-start;samples.append(point)
                reason=resource_violation(point,baseline,plan)
                if point['seconds']>=plan['total_wall_seconds']:reason='total_wall_cap'
                if (args.out/'server.log').stat().st_size>=plan['log_cap_bytes']:reason='log_cap'
                if reason:
                    guard_failure.append(reason);terminate_owned_child(proc);return
            except Exception as exc:
                guard_failure.append('monitor_error:'+type(exc).__name__);terminate_owned_child(proc);return
    try:
        cmd=[str(Path('work/bin/llama-server').resolve()),'-m',model,'--alias','qwen2.5-3b-instruct','--port','8193','-ngl','99','-np','4','-c','32768','--jinja','--host','127.0.0.1']
        env=dict(os.environ,LLAMA_MEDIA_MARKER=snap['media_marker'])
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        def log_limit():
            guard_failure.append('log_cap');terminate_owned_child(proc)
        def logger():
            try:
                with (args.out/'server.log').open('xb') as log:
                    capture_log(proc.stdout,log,plan['log_cap_bytes'],log_limit)
            except Exception as exc:
                guard_failure.append('log_capture_error:'+type(exc).__name__);terminate_owned_child(proc)
        log_thread=threading.Thread(target=logger,daemon=True);log_thread.start()
        record.update(pid=proc.pid,process_identity=process_identity(proc.pid),command=cmd)
        (args.out/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
        monitor=threading.Thread(target=guard,daemon=True);monitor.start()
        ready=False
        while time.monotonic()-start<plan['startup_wall_seconds']:
            if proc.poll() is not None or guard_failure:raise RuntimeError('receiver exited during startup')
            try:ready=http('/health',timeout=1).get('status')=='ok'
            except Exception:pass
            if ready:break
            time.sleep(.25)
        if not ready:raise RuntimeError('startup timeout')
        record['ready_seconds']=time.monotonic()-start
        props=http('/props');(args.out/'props_before.json').write_text(json.dumps(props,indent=2)+'\n')
        if digest(receiver_state(props))!=plan['receiver_state_sha256']:raise RuntimeError('receiver state mismatch')
        slots=http('/slots')
        if len(slots)!=4 or any(s.get('is_processing') is not False for s in slots):raise RuntimeError('unexpected busy slots')
        for request in requests:
            if guard_failure or proc.poll() is not None:raise RuntimeError('receiver unavailable')
            if time.monotonic()-start>plan['total_wall_seconds']-plan['per_call_wall_seconds']:raise RuntimeError('insufficient remaining call budget')
            # Persist assignment before dispatch. No same-cell retry.
            call={'slot':request['slot'],'length_label':request['length_label'],'status':'assigned','payload_sha256':digest(request['payload'])}
            calls.append(call);path=args.out/f"call_{request['slot']:02d}.json";path.write_text(json.dumps(call,indent=2)+'\n')
            t=time.monotonic()
            try:
                response=http('/v1/chat/completions',request['payload'],plan['per_call_wall_seconds'])
                call.update(status='returned',seconds=time.monotonic()-t,response=response)
                count=response.get('usage',{}).get('completion_tokens')
                if type(count) is not int or not 0<=count<=512:raise ValueError('missing or exceeded completion accounting')
                call['completion_tokens']=count;call['prompt_tokens']=response.get('usage',{}).get('prompt_tokens')
                if type(call['prompt_tokens']) is not int or call['prompt_tokens']+512>8192:raise ValueError('context accounting')
            except Exception as exc:
                call.update(status='failed',seconds=time.monotonic()-t,error=str(exc));raise
            finally:path.write_text(json.dumps(call,indent=2)+'\n')
        after=http('/props');(args.out/'props_after.json').write_text(json.dumps(after,indent=2)+'\n')
        record['state_unchanged']=digest(receiver_state(after))==plan['receiver_state_sha256']
        if not record['state_unchanged']:raise RuntimeError('receiver state drift')
    except BaseException as exc:
        record['error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        stop.set()
        if 'monitor' in locals():monitor.join(timeout=10)
        if proc is not None:
            terminate_owned_child(proc);record['receiver_exit_code']=proc.returncode;record['receiver_exit_observed']=proc.poll() is not None
            if 'log_thread' in locals():
                log_thread.join(timeout=5)
                if log_thread.is_alive():record['log_capture_incomplete']=True
            if proc.stdout is not None:proc.stdout.close()
        record['elapsed_seconds']=time.monotonic()-start
        record['calls_assigned']=len(calls);record['calls_returned']=sum(c['status']=='returned' for c in calls)
        record['completion_tokens']=sum(c.get('completion_tokens',0) for c in calls)
        record['paid_usd']=0;record['energy_measured']=False
        (args.out/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['calls_assigned','calls_returned','completion_tokens','elapsed_seconds','receiver_exit_observed','error']}))


if __name__=='__main__':main()
