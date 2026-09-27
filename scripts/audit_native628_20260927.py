#!/usr/bin/env python3
"""Frozen finite measurement audit; controlled reference/control code only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.prompt_choice.dependency_sandbox_v1 import run

PLAN=Path('experiments/prompt_choice/native628_plan_20260927.json')
SUPPLEMENT="""ax=task_func()
lines=ax.get_lines()
assert len(lines)>0
ys=list(lines[0].get_ydata())
assert len(ys)>=3
assert all(math.isfinite(float(y)) for y in ys)
assert max(ys)-min(ys)>1e-6
plt.close('all')
print('AUDIT_RESULT '+json.dumps({'passed':True,'checks':1}))
"""


def controls():
    common="import math\nimport matplotlib.pyplot as plt\ndef task_func():\n    fig,ax=plt.subplots()\n    ax.set_title('Random Sine Wave')\n    ax.set_xlabel('Time')\n    ax.set_ylabel('Amplitude')\n"
    return {'empty_axes':common+'    return ax\n', 'constant_line':common+'    ax.plot([0,1,2],[0,0,0])\n    return ax\n'}


def program(source,battery,test):
    prefix='import random,json,math\nrandom.seed(628)\n'
    if battery=='supplement':return prefix+source+'\n'+SUPPLEMENT
    methods=['test_case_1'] if battery=='public' else ['test_case_2','test_case_3','test_case_4','test_case_5']
    return prefix+source+'\n'+test+"\nimport io\nsuite=unittest.TestSuite(TestCases(n) for n in "+repr(methods)+")\nr=unittest.TextTestRunner(stream=io.StringIO()).run(suite)\nprint('AUDIT_RESULT '+json.dumps({'passed':r.wasSuccessful() and r.testsRun==len("+repr(methods)+") and not r.skipped and not r.expectedFailures,'checks':r.testsRun}))\n"


def main():
    a=argparse.ArgumentParser();a.add_argument('--freeze',required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    plan=json.loads(PLAN.read_bytes())
    for path,h in plan['input_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h:raise ValueError('input changed: '+path)
    for path in [str(PLAN),__file__,*plan['committed_sources']]:
        p=Path(path);rel=p.resolve().relative_to(Path.cwd()).as_posix()
        if subprocess.check_output(['git','show',args.freeze+':'+rel])!=p.read_bytes():raise ValueError('freeze mismatch: '+rel)
    if args.out.exists():raise ValueError('refuse existing output')
    args.out.mkdir(parents=True)
    row=json.loads(Path(plan['source_path']).read_bytes())
    artifacts={'reference':row['complete_prompt']+row['canonical_solution'],**controls()}
    start=time.monotonic();results=[]
    for artifact in ['reference','empty_axes','constant_line']:
        for battery in ['public','private','supplement']:
            if time.monotonic()-start>120:raise RuntimeError('overall wall cap')
            src=program(artifacts[artifact],battery,row['test'])
            raw=run(src,bundle=plan['bundle'],tree_sha256=plan['tree_sha256'],timeout_s=10,cpu_seconds=5,output_cap=16384,mem_bytes=1<<30)
            grade=None
            if raw['execution']['disposition']=='completed_ungraded':
                lines=[l for l in raw['raw_process']['stdout'].splitlines() if l.startswith('AUDIT_RESULT ')]
                if len(lines)==1:
                    obj=json.loads(lines[0][13:]);expected=4 if battery=='private' else 1
                    if type(obj.get('passed')) is bool and obj.get('checks')==expected:grade=int(obj['passed'])
            elif battery=='supplement' and raw['raw_process']['returncode']==1 and 'AssertionError' in raw['raw_process']['stderr']:
                grade=0
            record={'artifact':artifact,'battery':battery,'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'grade':grade,'result':raw,'freeze':args.freeze,'config_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest()}
            (args.out/(artifact+'_'+battery+'.json')).write_text(json.dumps(record,indent=2)+'\n');results.append(record)
    summary={'freeze':args.freeze,'config_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest(),'scope':'Finite measurement development with known nonadversarial controls; marker/exception parsing not valid as general untrusted grader','slots':[{'artifact':r['artifact'],'battery':r['battery'],'grade':r['grade'],'disposition':r['result']['execution']['disposition']} for r in results],'seconds':time.monotonic()-start,'model_calls':0}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
