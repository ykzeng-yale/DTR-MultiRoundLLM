"""Finite known-control native-test audit; not an untrusted verdict transport."""
import hashlib,json,subprocess,sys,time,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.prompt_choice.dependency_sandbox_v1 import run
PLAN=Path('experiments/prompt_choice/native_measurement_controls_plan_20260928.json')
CONTROLS={58:"import numpy as np\nimport matplotlib.pyplot as plt\ndef task_func(mu,sigma,num_samples):\n    fig,ax=plt.subplots()\n    ax.hist([0,0,0])\n    ax.plot([0,1],[0,0])\n    ax.set_title('Normal Distribution')\n    return fig\n",59:"def task_func(page_title):\n    return None\n"}
def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();plan=json.loads(PLAN.read_bytes())
 for f,h in plan['input_sha256'].items():
  if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h:raise ValueError('input mismatch '+f)
 for f in [str(PLAN),*plan['committed_sources']]:
  if subprocess.check_output(['git','show',a.freeze+':'+f])!=Path(f).read_bytes():raise ValueError('freeze mismatch')
 a.out.mkdir(exist_ok=False);start=time.monotonic();summary={'slots':[],'error':None,'classification':'known nonadversarial wrong controls; native tests only, no semantic efficacy','freeze':a.freeze}
 try:
  for task in [58,59]:
   if time.monotonic()-start>35:raise RuntimeError('overall cap')
   row=json.loads(Path(f'work/native_measurement_controls_20260928/{task}.json').read_bytes());n=5 if task==58 else 6
   src='import json\n'+CONTROLS[task]+'\n'+row['test']+"\nimport io\nr=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestCases))\nprint('AUDIT_RESULT '+json.dumps({'passed':r.wasSuccessful(),'checks':r.testsRun,'skipped':len(r.skipped)}))\n"
   raw=run(src,bundle=plan['bundle'],tree_sha256=plan['tree_sha256'],timeout_s=15,cpu_seconds=5,output_cap=16384,mem_bytes=1<<30)
   result=None
   if raw['execution']['disposition']=='completed_ungraded':
    lines=[l[13:] for l in raw['raw_process']['stdout'].splitlines() if l.startswith('AUDIT_RESULT ')]
    if len(lines)==1:
     obj=json.loads(lines[0]);result=obj if obj.get('checks')==n and obj.get('skipped')==0 else None
   record={'task':task,'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'result':result,'raw':raw};(a.out/f'{task}.json').write_text(json.dumps(record,indent=2)+'\n');summary['slots'].append({'task':task,'result':result,'disposition':raw['execution']['disposition']})
 except BaseException as e:summary['error']=repr(e);raise
 finally:
  summary['seconds']=time.monotonic()-start;(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
