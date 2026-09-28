"""Frozen local source-separated grading, never executes generated code on host."""
import argparse,ast,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.landmark.grade import extract_code
from experiments.landmark.collect import digest
from experiments.prompt_choice.literal_observation_v1 import evaluate
from scripts.audit_literal_panel_20260928 import aggregate


def bounds(status):return (1,1) if status=='PASS' else (0,0) if status=='FAIL' else (0,1)


def describe(rows,baseline):
    roots=sorted({x['root'] for x in baseline});lookup={(r['root'],r['artifact'],r['arm']):r for r in rows}
    root_results=[]
    for root in roots:
        artifacts=[x for x in baseline if x['root']==root];values={a:[] for a in ['STOP','PATCH','RETHINK','FRESH']}
        for b in artifacts:
            values['STOP'].append(bounds(b['batteries']['supplement_v1']))
            for arm in ['PATCH','RETHINK','FRESH']:
                r=lookup.get((root,b['artifact'],arm));values[arm].append(bounds(r['batteries']['supplement_v1']) if r else (0,1))
        means={a:[sum(x[j] for x in v)/len(v) for j in [0,1]] for a,v in values.items()}
        root_results.append({'root':root,'mean_bounds':means})
    means={a:[sum(r['mean_bounds'][a][j] for r in root_results)/len(roots) for j in [0,1]] for a in ['STOP','PATCH','RETHINK','FRESH']}
    contrasts={a+'-'+b:[means[a][0]-means[b][1],means[a][1]-means[b][0]] for a,b in [('PATCH','RETHINK'),('PATCH','FRESH'),('RETHINK','FRESH'),('PATCH','STOP'),('RETHINK','STOP')]}
    by_kind={}
    for kind in sorted({b['artifact'] for b in baseline}):
        by_kind[kind]={}
        for arm in ['PATCH','RETHINK','FRESH']:
            statuses=[lookup.get((b['root'],kind,arm),{}).get('batteries',{}).get('supplement_v1','INCOMPLETE') for b in baseline if b['artifact']==kind]
            by_kind[kind][arm]={s:statuses.count(s) for s in ['PASS','FAIL','INCOMPLETE']}
    return {'classification':'equal-root-weight descriptive finite constructed-checkpoint scores; no CI, causal population generalization or independent policy claim','root_count':len(roots),'mean_bounds':means,'contrast_bounds':contrasts,'by_root':root_results,'by_initial_artifact_kind':by_kind}


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    plan=json.loads(a.plan.read_bytes());receipt=json.loads(a.receipt.read_bytes())
    if hashlib.sha256(a.plan.read_bytes()).hexdigest()!=receipt['config_sha256']:raise ValueError('receipt plan mismatch')
    for f,h in plan['local_grading_files'].items():
        if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h:raise ValueError('grading input mismatch')
    reqs=json.loads(Path(plan['requests_path']).read_bytes());calls=receipt['calls']
    if len(calls)>162 or receipt['unattempted']!=162-len(calls):raise ValueError('assigned accounting')
    for call,req in zip(calls,reqs):
        if any(call[k]!=req[k] for k in ['slot','root','artifact','arm']) or call['payload_sha256']!=digest(req['payload']):raise ValueError('assignment mismatch')
    a.out.mkdir(exist_ok=False);start=time.monotonic();rows=[];count=0;summary={'rows':rows,'error':None,'source_receipt_sha256':hashlib.sha256(a.receipt.read_bytes()).hexdigest()}
    lookup={c['slot']:c for c in calls}
    try:
        for req in reqs:
            row={k:req[k] for k in ['slot','root','artifact','arm']};row['batteries']={k:'INCOMPLETE' for k in ['public','original_private','supplement_v1']};rows.append(row)
            call=lookup.get(req['slot'])
            if not call or call['status']!='returned':row['reason']='generation_unavailable';continue
            raw=call['response']['choices'][0]['message']['content']
            try:
                code=extract_code(raw);tree=ast.parse(code)
                if not tree.body:raise ValueError('empty source')
            except (ValueError,SyntaxError,TypeError):row['reason']='extraction_or_syntax_unavailable';continue
            root=req['root'].replace('/','_');pub=json.loads(Path(plan['package']+'/public/'+root+'.json').read_bytes());pri=json.loads(Path(plan['package']+'/private/'+root+'.json').read_bytes())
            row['artifact_sha256']=hashlib.sha256(code.encode()).hexdigest();row['reason']='evaluated'
            cases={'public':[pub['public_case']],**{k:v['cases'] for k,v in pri['batteries'].items()}}
            for battery,items in cases.items():
                statuses=[]
                for j,item in enumerate(items):
                    if time.monotonic()-start>3597:raise RuntimeError('grading time cap')
                    r=evaluate(code,pub['entry_point'],item['args_literal'],ast.literal_eval(item['expected_literal']))
                    (a.out/f"{req['slot']:03d}_{battery}_{j}.json").write_text(json.dumps(r)+'\n');count+=1;statuses.append(r['status'])
                row['batteries'][battery]=aggregate(statuses)
            if sum(x.stat().st_size for x in a.out.glob('*.json'))>128<<20:raise RuntimeError('grading output cap')
    except BaseException as e:summary['error']=repr(e);raise
    finally:
        summary.update(elapsed_seconds=time.monotonic()-start,case_starts=count,assigned=162,rows_accounted=len(rows))
        # Missing rows remain unknown through the fixed baseline lookup.
        baseline=json.loads(Path(plan['baseline_path']).read_bytes())['rows'];summary['descriptive']=describe(rows,baseline)
        (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary['descriptive']))

if __name__=='__main__':main()
