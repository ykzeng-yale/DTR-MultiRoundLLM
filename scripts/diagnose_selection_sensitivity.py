#!/usr/bin/env python3
"""Prespecified exploratory sensitivity; never pool repeated splits as new data."""
import argparse, hashlib, json, sys, platform, time, warnings
from pathlib import Path
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
sys.path.insert(0,str(Path(__file__).resolve().parent))
from recheck_selection import load_all_first, summary


def run_fit(cells, features, seed, model):
    tasks=sorted({k[0] for k in cells})
    order=np.random.default_rng(seed).permutation(tasks)
    train=set(order[:int(.6*len(tasks))])
    tr=[c for (u,m),cs in cells.items() if m==model and u in train for c in cs]
    X=np.array([[c['f'][f] for f in features] for c in tr]);y=np.array([c['outcome'] for c in tr])
    clf=make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,C=1))
    clf.fit(X,y)
    rows=[]
    for (u,m),cs in sorted(cells.items()):
        if m!=model or u in train: continue
        Xte=np.array([[c['f'][f] for f in features] for c in cs])
        p=clf.predict_proba(Xte)[:,1]
        yy=np.array([c['outcome'] for c in cs]);vis=np.array([c['f']['visible_pass'] for c in cs],bool)
        vv=vis if vis.any() else np.ones(4,bool);ss=p==p.max()
        learned=float(yy[ss].mean());visible=float(yy[vv].mean())
        rows.append(dict(task_uid=u,benchmark=u.split('/')[0],learned=learned,visible=visible,
                         delta=learned-visible,oracle=float(yy.max()),all_same_outcome=bool(np.all(yy==yy[0]))))
    coef=dict(zip(features,clf.named_steps['logisticregression'].coef_[0].tolist()))
    return dict(seed=seed,receiver=model,n_training_roots=len(train),n_evaluation_roots=len(rows),
                contrast=summary([r['delta'] for r in rows]),
                learned=summary([r['learned'] for r in rows]),
                visible=summary([r['visible'] for r in rows]),
                positive_roots=sum(r['delta']>0 for r in rows),negative_roots=sum(r['delta']<0 for r in rows),
                standardized_coefficients=coef,per_task=rows)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--episodes',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    source=hashlib.sha256(a.episodes.read_bytes()).hexdigest()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',SyntaxWarning);cells=load_all_first(a.episodes)
    features=sorted(next(iter(cells.values()))[0]['f'])
    check=[f for f in features if f.startswith('fc_') or f in ['visible_pass','frac_fail','n_asserts','timed_out']]
    token=['completion_tokens','prompt_tokens']
    structure=[f for f in features if f not in check+token+['is_humaneval']]
    sets={'full':features,'public_check_only':check,'code_structure_only':structure,'tokens_only':token}
    models=sorted({k[1] for k in cells});seeds=list(range(20260920,20260930))
    manifest=dict(source_sha256=source,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  loader_sha256=hashlib.sha256((Path(__file__).parent/'recheck_selection.py').read_bytes()).hexdigest(),
                  plan='docs/scientific_diagnostic_plan_20260920.md',plan_commit='9961025',
                  seeds=seeds,feature_sets=sets,learner='StandardScaler(training only) + LogisticRegression(C=1,max_iter=2000)',
                  data_status='reused and repeatedly inspected; exploratory only',python=platform.python_version(),model_calls=0,paid_spend_usd=0)
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    start=time.perf_counter();records=[]
    for model in models:
        for seed in seeds:
            r=run_fit(cells,features,seed,model);r['features']='full';records.append(r)
        for name,fs in sets.items():
            if name=='full': continue
            r=run_fit(cells,fs,seeds[0],model);r['features']=name;records.append(r)
    (a.out/'fits.json').write_text(json.dumps(records,indent=2))
    report=dict(elapsed_seconds=time.perf_counter()-start,split_summary={},ablations=[],
                caveat='Splits overlap and are not independent replications. No pooled p-value or best-split result is valid. Feature ablations are post-hoc diagnostics, not causal mediation.')
    for model in models:
        rr=[r for r in records if r['receiver']==model and r['features']=='full'];d=np.array([r['contrast']['mean'] for r in rr])
        report['split_summary'][model]=dict(all_differences=d.tolist(),median=float(np.median(d)),minimum=float(d.min()),maximum=float(d.max()),positive_splits=int((d>0).sum()),n_splits=len(d))
    for r in records:
        if r['seed']==seeds[0]:report['ablations'].append({k:v for k,v in r.items() if k not in ['per_task','standardized_coefficients']})
    (a.out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
