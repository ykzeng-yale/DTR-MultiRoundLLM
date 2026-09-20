#!/usr/bin/env python3
"""Exploratory frozen-split fixed-budget selection recheck; no model/code execution.

All initial candidates are kept regardless of future routing. Uses recorded public
features and full-test outcomes; this reused benchmark is not a pristine test set.
"""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
import numpy as np
from scipy.stats import t as student_t
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments' / 'audits'))
from g1a_selection_pilot import code_features, FAIL_CLASSES


def load_all_first(path):
    per = {}
    for line in path.open():
        r = json.loads(line)
        ds = r.get('decisions') or []
        if not ds:
            raise ValueError('Missing first candidate')
        d = ds[0]; v = d['validation']
        if not isinstance(v.get('passed'), bool) or not (type(r.get('success_first_candidate')) in (bool, int) and r['success_first_candidate'] in (0, 1)):
            raise ValueError('Outcome/visible indicator missing')
        f = code_features(d.get('code') or '')
        f.update(visible_pass=int(v['passed']), frac_fail=float(v.get('frac_fail') or 0),
                 n_asserts=int(v.get('n_asserts') or 0),
                 completion_tokens=int(d.get('completion_tokens') or 0),
                 prompt_tokens=int(d.get('prompt_tokens') or 0),
                 is_humaneval=int(r['task_uid'].startswith('humaneval')),
                 timed_out=int(bool(v.get('timed_out'))))
        for k in FAIL_CLASSES:
            f['fc_'+k] = int(str(v.get('fail_class') or 'none') == k)
        per.setdefault((r['task_uid'], d['model_alias']), []).append(
            dict(f=f, outcome=int(r['success_first_candidate'])))
    if not all(len(v) == 4 for v in per.values()):
        raise ValueError('Expected exactly four first candidates per task/receiver')
    return per


def summary(x):
    x=np.asarray(x, float)
    se=float(x.std(ddof=1)/np.sqrt(len(x)))
    half=float(student_t.ppf(.975,len(x)-1)*se)
    return dict(mean=float(x.mean()), task_se=se,
                exploratory_task_ci95=[float(x.mean()-half),float(x.mean()+half)])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--episodes', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=20260920)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    cells=load_all_first(a.episodes)
    tasks=sorted({k[0] for k in cells})
    order=np.random.default_rng(a.seed).permutation(tasks)
    train=set(order[:int(.6*len(tasks))])
    splits={u:('train' if u in train else 'evaluation') for u in tasks}
    models=sorted({k[1] for k in cells})
    features=sorted(next(iter(cells.values()))[0]['f'])
    manifest=dict(seed=a.seed, split_fraction_train=.6, split_unit='task_uid',
                  source_sha256=hashlib.sha256(a.episodes.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  source_path=str(a.episodes), task_split=splits, features=features,
                  algorithms={'gbm':dict(max_iter=200,max_depth=4,learning_rate=.06,random_state=0),
                              'logit':dict(max_iter=2000,C=1)},
                  python=platform.python_version(),
                  target='fixed bank of four initial candidates, all four calls charged to all selectors',
                  evidence='exploratory reused full-test labels; task families unresolved; no prospective validation')
    # Write manifest before fitting/evaluation.
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    report={'models':{},'limitations':[
        'All labels are from an already analysed source; this is not confirmatory.',
        'Intervals are conditional-training task-level diagnostics, assuming independent task roots. Family dependence is unaudited.',
        'All selectors pay four generation calls. Adaptive best-of-N is a different cost comparator.',
        'Outcome is recorded full-test success, not independently rescored hidden-only success.',
        'No claim of no possible learnable signal follows from these two algorithms.',
        'Generation token costs match by construction; scoring and selector CPU costs are not measured.']}
    rows=[]
    for m in models:
        tr=[c for (u,mm),cs in cells.items() if mm==m and u in train for c in cs]
        X=np.array([[c['f'][k] for k in features] for c in tr]);y=np.array([c['outcome'] for c in tr])
        evalitems=sorted((u,cs) for (u,mm),cs in cells.items() if mm==m and u not in train)
        report['models'][m]={}
        for name,clf in [('gbm',HistGradientBoostingClassifier(max_iter=200,max_depth=4,learning_rate=.06,random_state=0)),
                         ('logit',make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,C=1)))]:
            clf.fit(X,y)
            rr=[]
            for u,cs in evalitems:
                xx=np.array([[c['f'][k] for k in features] for c in cs])
                p=clf.predict_proba(xx)[:,1]
                yy=np.array([c['outcome'] for c in cs])
                vis=np.array([c['f']['visible_pass'] for c in cs],bool)
                # Uniform tie-breaking and permutation-average visible picker.
                # With all four paid, visible chooses uniformly among passes, else all.
                chosen=(p==p.max());eligible=vis if vis.any() else np.ones(4,bool)
                row=dict(task_uid=u,receiver=m,algorithm=name,
                         learned=float(yy[chosen].mean()),visible=float(yy[eligible].mean()),
                         random=float(yy.mean()),oracle=int(yy.any()),
                         predicted_probabilities=p.tolist(),outcomes=yy.tolist(),
                         completion_tokens=sum(c['f']['completion_tokens'] for c in cs),
                         prompt_tokens=sum(c['f']['prompt_tokens'] for c in cs))
                rr.append(row);rows.append(row)
            report['models'][m][name]=dict(n_training_tasks=len(train),n_evaluation_tasks=len(rr),
                learned=summary([r['learned'] for r in rr]),
                visible=summary([r['visible'] for r in rr]),
                random=summary([r['random'] for r in rr]),oracle=summary([r['oracle'] for r in rr]),
                learned_minus_visible=summary([r['learned']-r['visible'] for r in rr]),
                generation_calls_per_task=4,
                mean_completion_tokens=float(np.mean([r['completion_tokens'] for r in rr])),
                mean_prompt_tokens=float(np.mean([r['prompt_tokens'] for r in rr])))
    (a.out/'per_task.json').write_text(json.dumps(rows,indent=2))
    (a.out/'summary.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
