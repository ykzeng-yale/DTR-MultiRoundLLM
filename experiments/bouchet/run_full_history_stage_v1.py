"""Frozen staged full-history development collection; model code never executed here."""
import argparse,hashlib,json,os,signal,socket,subprocess,sys,threading,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.landmark.collect import receiver_state,digest,NoRedirect

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def main(plan_path=Path('experiments/bouchet/full_history_phase0_plan_v1.json')):
    plan=json.loads(plan_path.read_bytes())
    for p,h in plan['files'].items():
        if sha(p)!=h:raise ValueError('input mismatch: '+p)
    if sha('model.gguf')!=plan['model_sha256']:raise ValueError('model mismatch')
    if sha('build-sha256.txt')!=plan['build_manifest_sha256']:raise ValueError('unfrozen build manifest')
    subprocess.run(['sha256sum','-c','build-sha256.txt'],check=True)
    if not Path('build-complete.txt').exists():raise ValueError('build incomplete')
    out=Path('generation');out.mkdir(exist_ok=False)
    rec={'classification':'natural-start full-history operational pilot; no efficacy claim','job_id':os.environ['SLURM_JOB_ID'],'config_sha256':sha(plan_path),'build_manifest_sha256':sha('build-sha256.txt'),'freeze':Path('freeze.txt').read_text().strip(),'calls':[],'error':None}
    (out/'build-sha256.txt').write_bytes(Path('build-sha256.txt').read_bytes())
    start=time.monotonic();proc=None;log_thread=None;failure=[]
    def save(): (out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
    def stop():
        if proc and proc.poll() is None:
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
    def interrupted(signum,frame):raise RuntimeError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def http(path,payload=None,timeout=3):
        req=urllib.request.Request('http://127.0.0.1:18193'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with opener.open(req,timeout=timeout) as r:b=r.read(262145)
        if len(b)>262144:raise ValueError('response limit')
        return json.loads(b)
    try:
        with socket.socket() as s:s.bind(('127.0.0.1',18193))
        env=dict(os.environ,LLAMA_MEDIA_MARKER=plan['media_marker'])
        cmd=['build/bin/llama-server','-m','model.gguf','--alias','qwen2.5-3b-instruct','--host','127.0.0.1','--port','18193','-ngl','99','-np','4','-c','32768','--jinja']
        rec['command']=cmd;save()
        proc=subprocess.Popen(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        def log():
            total=0
            with (out/'server.log').open('xb') as f:
                while True:
                    b=proc.stdout.read1(4096)
                    if not b:break
                    left=8388608-total;f.write(b[:max(0,left)]);total+=len(b)
                    if total>8388608:failure.append('log cap');stop();break
        log_thread=threading.Thread(target=log,daemon=True);log_thread.start()
        ready=False
        while time.monotonic()-start<120:
            if proc.poll() is not None:raise RuntimeError('startup exit')
            try:ready=http('/health').get('status')=='ok'
            except Exception:pass
            if ready:break
            time.sleep(.5)
        if not ready:raise RuntimeError('startup timeout')
        props=http('/props');(out/'props_before.json').write_text(json.dumps(props,indent=2)+'\n')
        if digest(receiver_state(props))!=plan['receiver_state_sha256']:raise ValueError('declared receiver properties differ')
        rec['ready_seconds']=time.monotonic()-start
        requests=json.loads(Path(plan['requests_path']).read_bytes())
        if len(requests)!=plan['max_calls'] or not 0<len(requests)<=18:raise ValueError('assignment count')
        for req in requests:
            if failure or proc.poll() is not None:raise RuntimeError('server/log failure')
            if time.monotonic()-start>700:raise RuntimeError('remaining budget')
            call={'slot':req['slot'],'status':'assigned','payload_sha256':digest(req['payload']),'root':req['root'],'artifact':req['artifact'],'arm':req['arm'],'replicate':req['replicate']};rec['calls'].append(call);save();t=time.monotonic()
            try:
                response=http('/v1/chat/completions',req['payload'],120)
                call.update(status='returned',seconds=time.monotonic()-t,response=response)
                n=response.get('usage',{}).get('completion_tokens')
                if type(n) is not int or not 0<=n<=1024:raise ValueError('completion accounting')
                prompt=response['usage'].get('prompt_tokens')
                if type(prompt) is not int or prompt+1024>8192:raise ValueError('context accounting')
            except Exception as e:call.update(status='failed',error=repr(e));raise
            finally:save()
        rec['state_unchanged']=digest(receiver_state(http('/props')))==plan['receiver_state_sha256']
        if not rec['state_unchanged']:raise ValueError('state drift')
    except BaseException as e:rec['error']=repr(e);raise
    finally:
        stop()
        if proc:
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
            rec['server_returncode']=proc.returncode
        if log_thread:log_thread.join(timeout=5)
        rec.update(elapsed_seconds=time.monotonic()-start,unattempted=plan['max_calls']-len(rec['calls']),guard_failures=failure,paid_usd=0,energy_measured=False)
        save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,default=Path('experiments/bouchet/full_history_phase0_plan_v1.json'));args=parser.parse_args();main(args.plan)
