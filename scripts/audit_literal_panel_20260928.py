"""Lead frozen54-artifact development measurement audit, no receiver calls."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.prompt_choice.literal_observation_v1 import evaluate
PLAN=Path('experiments/prompt_choice/literal_panel_plan_20260928.json')

def aggregate(statuses):
    return 'FAIL' if 'FAIL' in statuses else 'INCOMPLETE' if 'INCOMPLETE' in statuses else 'PASS'

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    freeze=subprocess.check_output(['git','rev-parse',a.freeze],text=True).strip();plan=json.loads(PLAN.read_bytes())
    for f,h in plan['files'].items():
        b=Path(f).read_bytes()
        if hashlib.sha256(b).hexdigest()!=h:raise ValueError('input hash')
        if not f.startswith('work/') and subprocess.check_output(['git','show',freeze+':'+f])!=b:raise ValueError('code freeze')
    if subprocess.check_output(['git','show',freeze+':'+str(PLAN)])!=PLAN.read_bytes():raise ValueError('plan freeze')
    a.out.mkdir(exist_ok=False);start=time.monotonic();rows=[];count=0
    summary={'freeze':freeze,'config_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest(),'rows':rows,'error':None,'receiver_calls':0}
    try:
        for root in plan['roots']:
            pub=json.loads(Path(plan['package']+'/public/'+root+'.json').read_bytes());pri=json.loads(Path(plan['package']+'/private/'+root+'.json').read_bytes())
            artifacts=[('reference',pri['reference']),*[(c['kind'],c) for c in pri['controls']]]
            for kind,obj in artifacts:
                row={'root':pub['task_id'],'artifact':kind,'code_sha256':hashlib.sha256(obj['code'].encode()).hexdigest(),'batteries':{}};rows.append(row)
                batteries={'public':[pub['public_case']],**{k:v['cases'] for k,v in pri['batteries'].items()}}
                for name,cases in batteries.items():
                    statuses=[]
                    for j,case in enumerate(cases):
                        if time.monotonic()-start>1197:raise RuntimeError('wall budget')
                        import ast
                        receipt=evaluate(obj['code'],pub['entry_point'],case['args_literal'],ast.literal_eval(case['expected_literal']))
                        (a.out/f'{root}_{kind}_{name}_{j}.json').write_text(json.dumps(receipt)+'\n');count+=1;statuses.append(receipt['status'])
                    row['batteries'][name]=aggregate(statuses)
                row['private_predictions_match']=all((row['batteries'][k]=='PASS')==obj['predicted'][k] and row['batteries'][k]!='INCOMPLETE' for k in ['original_private','supplement_v1'])
                if sum(p.stat().st_size for p in a.out.glob('*.json'))>64<<20:raise RuntimeError('retained output cap')
    except BaseException as e:summary['error']=repr(e);raise
    finally:
        summary.update(elapsed_seconds=time.monotonic()-start,case_slots_completed=count,artifacts_completed=sum(len(x['batteries'])==3 for x in rows),all_private_predictions_match=len(rows)==54 and all(x.get('private_predictions_match',False) for x in rows))
        (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))

if __name__=='__main__':main()
