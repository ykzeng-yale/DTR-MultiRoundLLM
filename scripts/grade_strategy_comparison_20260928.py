"""All-assigned terminal strategy comparison, no fitting or population claims."""
import argparse,ast,hashlib,json,sys,time
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.bouchet.strategy_comparison_v1 import POLICIES,assignment_table
from experiments.bouchet.full_history_pilot_v1 import source
from experiments.prompt_choice.literal_observation_v1 import evaluate
from scripts.audit_literal_panel_20260928 import aggregate

def describe(rows):
    lookup={(r['trajectory'],r['policy']):r for r in rows}
    bounds={};counts={}
    for policy in POLICIES:
        statuses=[lookup.get((i,policy),{}).get('batteries',{}).get('supplement_v1','INCOMPLETE') for i in range(18)]
        counts[policy]=dict(Counter(statuses));bounds[policy]=[statuses.count('PASS')/18,(statuses.count('PASS')+statuses.count('INCOMPLETE'))/18]
    return {'counts':counts,'equal_root_descriptive_bounds':bounds,
            'contrasts_vs_resample':{p:[v[0]-bounds['RESAMPLE_SELECT'][1],v[1]-bounds['RESAMPLE_SELECT'][0]] for p,v in bounds.items() if p!='RESAMPLE_SELECT'},
            'scope':'all18starts, nine reused roots, no CI or population policy claim; missing outcomes do not cancel'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--state',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();c=json.loads(a.contract.read_bytes())
    for f,h in c['files'].items():
        if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h:raise ValueError('contract mismatch '+f)
    state=json.loads(a.state.read_bytes());ledger=assignment_table();initial=json.loads(Path(c['initial_path']).read_bytes())
    if state['requests'] or state['phase']!=2 or len(state['rows'])!=162 or any(any(r[k]!=l[k] for k in l) for r,l in zip(state['rows'],ledger)):raise ValueError('terminal assignment mismatch')
    a.out.mkdir(exist_ok=False);start=time.monotonic();result={'assigned':162,'rows':[],'case_starts':0,'error':None,'state_sha256':hashlib.sha256(a.state.read_bytes()).hexdigest()}
    try:
        for row in state['rows']:
            r={k:row[k] for k in ('slot','trajectory','policy','root','replicate','disposition')};r['initial_usage']=initial[row['trajectory']]['initial_usage'];r['initial_seconds']=initial[row['trajectory']]['initial_seconds'];r['public_checks_including_initial']=len(row['candidates']);r['batteries']={b:'INCOMPLETE' for b in ('original_private','supplement_v1')}
            r['continuation_calls']=len(row['calls']);r['continuation_prompt_tokens']=sum((x['record'] or {}).get('response',{}).get('usage',{}).get('prompt_tokens',0) for x in row['calls']);r['continuation_completion_tokens']=sum((x['record'] or {}).get('response',{}).get('usage',{}).get('completion_tokens',0) for x in row['calls']);r['continuation_seconds']=sum((x['record'] or {}).get('seconds',0) for x in row['calls']);result['rows'].append(r)
            if row['disposition']=='generation_unavailable':continue
            try:code=source(row['final_raw'])
            except (ValueError,SyntaxError,TypeError):continue
            name=row['root'].replace('/','_')+'.json';pub=json.loads((Path(c['package'])/'public'/name).read_bytes());pri=json.loads((Path(c['package'])/'private'/name).read_bytes())
            for b,data in pri['batteries'].items():
                statuses=[]
                for j,case in enumerate(data['cases']):
                    if result['case_starts']>=1500 or time.monotonic()-start>3500:raise RuntimeError('grading cap')
                    v=evaluate(code,pub['entry_point'],case['args_literal'],ast.literal_eval(case['expected_literal']));(a.out/f"{row['slot']}-{b}-{j}.json").write_text(json.dumps(v)+'\n');statuses.append(v['status']);result['case_starts']+=1
                r['batteries'][b]=aggregate(statuses)
            if sum(f.stat().st_size for f in a.out.glob('*.json'))>256<<20:raise RuntimeError('output cap')
    except BaseException as e:result['error']=repr(e);raise
    finally:
        result.update(seconds=time.monotonic()-start,descriptive=describe(result['rows']));(a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
