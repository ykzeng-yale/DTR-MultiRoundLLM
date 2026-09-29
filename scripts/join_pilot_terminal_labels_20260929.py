"""Bind public pilot views to separately graded terminal labels; no policy fit.

Only sanitized case aggregates are read. All assigned trajectories, including
missing grades, remain in the output; a missing label is never treated as STOP.
"""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.sequential.text_history_q import validate

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def join(export, grading):
    if export['state_sha256']!=grading['state_sha256']:
        raise ValueError('different saved trajectories')
    by_id={}
    for row in export['decisions']:
        md=row['metadata'];i=md['trajectory']
        if i not in by_id:by_id[i]=dict(root=md['root'],replicate=md['replicate'],steps=[])
        ep=by_id[i]
        if (md['root'],md['replicate'])!=(ep['root'],ep['replicate']) or md['turn']!=len(ep['steps'])+1:
            raise ValueError('decision order or identity drift')
        ep['steps'].append({'view':row['view'],'selection':row['selection']})
    if len(by_id)!=grading['assigned'] or len(grading['rows'])!=grading['assigned']:
        raise ValueError('assigned trajectory not retained')
    episodes=[];missing=[]
    for i,grade in enumerate(grading['rows']):
        ep=by_id.get(i)
        if ep is None or grade['trajectory']!=i or grade['root']!=ep['root'] or grade['replicate']!=ep['replicate']:
            raise ValueError('grade/view identity drift')
        actions=[step['selection']['chosen_id'] for step in ep['steps']]
        statuses=[step['view']['public_observations'][-1]['status'] for step in ep['steps']]
        if actions!=grade['actions'] or statuses!=grade['public_statuses']:
            raise ValueError('terminal grade linked to different action/status history')
        if grade['disposition'] not in ('stopped','horizon'):
            missing.append({'trajectory':i,'reason':grade['disposition']})
        outcome=grade['batteries']['supplement_v1']
        if outcome not in ('PASS','FAIL'):
            missing.append({'trajectory':i,'reason':'terminal_'+outcome})
            value=None
        else:value=int(outcome=='PASS')
        episodes.append({'episode':str(i),'family':ep['root'],'steps':ep['steps'],'outcome':value})
    if not missing:validate(episodes)
    return episodes,missing

def main():
    out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
    exported=Path('work/pilot_public_export_verified_20260928')
    export_summary=json.loads((exported/'summary.json').read_text())
    decisions=exported/'decisions.jsonl'
    if sha(decisions)!=export_summary['export_sha256']:raise ValueError('public export hash')
    grade_path=Path('results/full_history_terminal_grading_20260928.json')
    grading=json.loads(grade_path.read_text())
    data={'state_sha256':export_summary['state_sha256'],'decisions':[json.loads(line) for line in decisions.read_text().splitlines()]}
    episodes,missing=join(data,grading)
    rows=out/'episodes.jsonl';rows.write_text(''.join(json.dumps(e,sort_keys=True)+'\n' for e in episodes))
    receipt={'classification':'reused nine-root label-join interface check; no fitting or efficacy','assigned':len(episodes),'decision_count':sum(len(e['steps']) for e in episodes),'missing':missing,'complete_labels':sum(e['outcome'] is not None for e in episodes),'families':len({e['family'] for e in episodes}),'source_sha256':{'public_export':sha(decisions),'public_export_summary':sha(exported/'summary.json'),'sanitized_grading':sha(grade_path),'join_source':sha(__file__),'validator_source':sha('experiments/sequential/text_history_q.py')},'rows_sha256':sha(rows),'policy_fitted':False,'independent_families_claimed':False}
    (out/'summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('assigned','decision_count','missing','complete_labels','families')}))
if __name__=='__main__':main()
