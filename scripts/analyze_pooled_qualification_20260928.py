"""Reconcile every frozen synthetic assignment without suppressing failed fits."""
import json,hashlib,statistics,math
from pathlib import Path
from collections import Counter

def stats(xs):
 return {'n':len(xs),'mean':statistics.mean(xs) if xs else None,'mc_se':statistics.stdev(xs)/math.sqrt(len(xs)) if len(xs)>1 else None}

def main():
 base=Path('work/pooled_qualification_20260928');planpath=Path('experiments/sequential/pooled_qualification_plan_20260928.json');p=json.loads(planpath.read_bytes());s=json.loads((base/'summary.json').read_bytes());rows=[json.loads(l) for l in (base/'journal.jsonl').read_text().splitlines()]
 assert s['plan_sha256']==hashlib.sha256(planpath.read_bytes()).hexdigest()
 assert len(rows)==s['completed']==2700 and s['error'] is None
 for r,a in zip(rows,p['assignments']):assert all(r[k]==a[k] for k in a)
 for f,h in p['files'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
 old={ (r['regime'],r['n'],r['seed']):r for r in (json.loads(l) for l in Path('work/sequential_qualification_20260928/journal.jsonl').read_text().splitlines())}
 cells=[]
 for g in p['regimes']:
  for n in (256,1024,4096):
   rr=[r for r in rows if r['regime']==g and r['n']==n];cell={'regime':g,'n':n,'assigned':len(rr),'variants':{}}
   for v in ('history','last'):
    allv=[r['variants'][v] for r in rr];fit=[r for r in allv if not r['fit_error']];scores=[r for r in fit if not r['score_error']]
    assert all(r['exact_value']<=s['oracle'][g]+1e-12 for r in fit)
    if g=='null':assert all(abs(r['exact_value']-.55)<1e-12 for r in fit)
    cell['variants'][v]={'minimum_stage_action_count':min((min(stage['action_counts']) for r in fit for stage in r['stage_action_counts']),default=None),'fit_failures':dict(Counter(r['fit_error'] for r in allv if r['fit_error'])),'score_failures':dict(Counter(r['score_error'] for r in fit if r['score_error'])),'value_conditional_on_fit':stats([r['exact_value'] for r in fit]),'regret_conditional_on_fit':stats([s['oracle'][g]-r['exact_value'] for r in fit]),'all_assigned_value_bounds':[sum(r['exact_value'] for r in fit)/len(rr),(sum(r['exact_value'] for r in fit)+len(rr)-len(fit))/len(rr)],'unseen_history_decisions_conditional_on_fit':stats([r['expected_unseen_history_decisions'] for r in fit]),'holdout_error_conditional_on_score':{m:stats([r[m]-r['exact_value'] for r in scores]) for m in ('ipw','dr')}}
   pairs=[r for r in rr if all(not r['variants'][v]['fit_error'] for v in ('history','last'))]
   cell['paired_vs_tabular']={}
   for v in ('history','last'):
    pairs_old=[(r['variants'][v],old[(r['regime'],r['n'],r['seed'])]['variants'][v]) for r in rr]
    good=[(a,b) for a,b in pairs_old if not a['fit_error'] and not b['fit_error']]
    cell['paired_vs_tabular'][v]={'both_fit':len(good),'difference_conditional_on_both_fit':stats([a['exact_value']-b['exact_value'] for a,b in good])}
   cell['paired_difference_conditional_on_both_fit']=stats([r['variants']['history']['exact_value']-r['variants']['last']['exact_value'] for r in pairs]);cells.append(cell)
 out={'classification':'synthetic; all assigned failures retained, conditional summaries explicitly labeled','freeze':s['freeze'],'seconds':s['seconds'],'planned_and_reconciled':2700,'oracle':s['oracle'],'cells':cells,'artifact_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [planpath,*base.glob('*')] if f.is_file()}}
 Path('results/pooled_qualification_reconciliation_20260928.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
