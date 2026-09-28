"""Bounded predeclared synthetic qualification; append-only per-replicate journal."""
import argparse,hashlib,json,os,resource,signal,subprocess,sys,time
import numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.sequential.pooled_qualification import replicate,exact_value,public_oracle

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();plan=json.loads(a.plan.read_bytes())
 for f,h in plan['files'].items():
  if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h:raise ValueError('source drift '+f)
 a.out.mkdir(exist_ok=False);start=time.monotonic()
 resource.setrlimit(resource.RLIMIT_CPU,(plan['wall_seconds'],plan['wall_seconds']+5))
 def timeout(signum,frame):raise TimeoutError('finite wall cap')
 signal.signal(signal.SIGALRM,timeout);signal.alarm(plan['wall_seconds'])
 summary={'classification':'synthetic pooled-regression qualification, not LLM/policy efficacy','pid':os.getpid(),'python':sys.version,'numpy':np.__version__,'thread_env':{k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')},'freeze':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'plan_sha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),'planned':len(plan['assignments']),'completed':0,'error':None,'oracle':{g:exact_value(public_oracle(g),g)[0] for g in plan['regimes']}}
 (a.out/'launch.json').write_text(json.dumps(summary,indent=2)+'\n')
 try:
  with (a.out/'journal.jsonl').open('x') as f:
   for row in plan['assignments']:
    result=replicate(row['n'],row['seed'],row['regime'],plan['heldout_n']);f.write(json.dumps(result)+'\n');f.flush();summary['completed']+=1
    if f.tell()>plan['retained_bytes']:raise RuntimeError('output cap')
 except BaseException as e:summary['error']=repr(e);raise
 finally:
  signal.alarm(0);summary['seconds']=time.monotonic()-start;(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
