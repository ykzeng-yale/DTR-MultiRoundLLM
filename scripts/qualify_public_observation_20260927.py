"""Frozen public/private routing controls; no receiver or benchmark tasks."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.prompt_choice.public_observation_v1 import public_check,private_check
from experiments.prompt_choice.status_feedback_v1 import TEXT
PLAN=Path('experiments/prompt_choice/public_observation_plan_20260927.json')


def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    freeze=subprocess.check_output(['git','rev-parse',a.freeze],text=True).strip();plan=json.loads(PLAN.read_bytes())
    for f,h in plan['files'].items():
        if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h or subprocess.check_output(['git','show',freeze+':'+f])!=Path(f).read_bytes():raise ValueError('code freeze')
    if subprocess.check_output(['git','show',freeze+':'+str(PLAN)])!=PLAN.read_bytes():raise ValueError('plan freeze')
    a.out.mkdir(exist_ok=False);start=time.monotonic();rows=[]
    summary={'classification':'synthetic public/private routing qualification; no benchmark or receiver calls','freeze':freeze,'config_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest(),'rows':rows,'error':None}
    try:
        for item in plan['cases']:
            if time.monotonic()-start>27:raise RuntimeError('total cap')
            pub=public_check(item['code'],plan['public_case'])
            private=private_check(item['code'],plan['private_case'])
            result={'name':item['name'],'public':pub,'private':private}
            path=a.out/(item['name']+'.json');path.write_text(json.dumps(result,indent=2)+'\n')
            rows.append({'name':item['name'],'public_status':pub['audit']['receipt']['status'],'private_status':private['receipt']['status'],'feedback_matches':pub['feedback_text']==TEXT[item['public_status']],'predictions_match':pub['audit']['receipt']['status']==item['public_status'] and private['receipt']['status']==item['private_status'],'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    except BaseException as e:summary['error']=repr(e);raise
    finally:
        summary.update(elapsed_seconds=time.monotonic()-start,completed_pairs=len(rows),passed=len(rows)==4 and all(r['predictions_match'] and r['feedback_matches'] for r in rows))
        (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
