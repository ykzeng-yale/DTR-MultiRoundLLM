#!/usr/bin/env python3
"""G1a' pilot -- can a policy-observable rule recover any of the selection headroom?

This is the question the whole programme now rests on. G0e showed that the correct
answer is often already generated and the cheap visible check fails to identify it:
oracle pass@3 = 0.8075 against adaptive best-of-N's achieved 0.7461, a 6.1-point gap
that is pure SELECTION. Audit A3 showed 4.6 points in stopping. Both are upper bounds
available to something that peeks at the hidden verdict.

The empirical question is what a rule that CANNOT peek recovers. If a
policy-observable feature map carries no signal about the hidden verdict beyond the
visible check, no selection rule recovers any of it and the programme's remaining claim
collapses to the reporting result.

Run at zero GPU cost on the sibling project's completed log, which holds several
independent candidates per (task, receiver) with the visible and hidden verdicts
recorded separately.

Three pickers, on the same candidate sets:
  VISIBLE   the incumbent: return the first candidate whose visible check passes.
  LEARNED   return argmax of a cross-fitted model of P(hidden pass | features), where
            the features EXCLUDE the hidden verdict and everything derived from it.
  ORACLE    return a hidden-passing candidate if one exists. The ceiling.

Cross-fitting is over TASKS, so the model never sees the task it is scored on. This
matters: candidates of one task share its difficulty, and a candidate-level split would
leak it and manufacture skill.
"""
from __future__ import annotations

import argparse, ast, json, re, time
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[2]
SRC = Path('/Users/yukangzengcmac/DTR-AgentEvals/results/code_routing/log/episodes.jsonl')

FAIL_CLASSES = ['none', 'assert', 'exception', 'timeout', 'syntax', 'empty', 'other']


def code_features(code: str) -> dict:
    """Cheap, policy-observable structure of the candidate. Nothing here touches the
    hidden tests, the reference solution, or any grade."""
    c = code or ''
    f = {
        'len_chars': len(c),
        'n_lines': c.count('\n') + 1,
        'n_def': len(re.findall(r'\bdef\s', c)),
        'has_for': int('for ' in c),
        'has_while': int('while ' in c),
        'has_if': int('if ' in c),
        'has_try': int('try:' in c),
        'has_import': int(re.search(r'^[ \t]*(import|from)[ \t]', c, re.M) is not None),
        'n_return': len(re.findall(r'\breturn\b', c)),
        'has_recursion': 0,
        'parses': 0,
        'n_nodes': 0,
        'max_depth': 0,
    }
    try:
        tree = ast.parse(c)
        f['parses'] = 1
        nodes = list(ast.walk(tree))
        f['n_nodes'] = len(nodes)
        names = {n.name for n in nodes if isinstance(n, ast.FunctionDef)}
        calls = {n.func.id for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        f['has_recursion'] = int(bool(names & calls))
        def depth(n, d=0):
            ch = list(ast.iter_child_nodes(n))
            return d if not ch else max(depth(c2, d + 1) for c2 in ch)
        f['max_depth'] = depth(tree)
    except Exception:
        pass
    return f


def load(path: Path, min_reps: int):
    per = defaultdict(list)
    for line in path.open():
        r = json.loads(line)
        ds = r.get('decisions') or []
        if not ds:
            continue
        models = {d.get('model_alias') for d in ds if d.get('model_alias')}
        if len(models) > 1:
            continue
        d0 = ds[0]
        val = d0.get('validation') or {}
        nf = val.get('n_fail')
        if nf is None:
            continue
        feats = code_features(d0.get('code') or '')
        feats.update({
            'visible_pass': int(nf == 0),
            'frac_fail': float(val.get('frac_fail') or 0.0),
            'n_asserts': int(val.get('n_asserts') or 0),
            'completion_tokens': int(d0.get('completion_tokens') or 0),
            'prompt_tokens': int(d0.get('prompt_tokens') or 0),
            'is_humaneval': int(str(r['task_uid']).startswith('humaneval')),
            'timed_out': int(bool(val.get('timed_out'))),
        })
        fc = str(val.get('fail_class') or 'none')
        for k in FAIL_CLASSES:
            feats['fc_' + k] = int(fc == k)
        per[(r['task_uid'], models.pop() if models else 'unknown')].append(
            {'f': feats, 'hidden': int(bool(r.get('success_first_candidate')))})
    return {k: v for k, v in per.items() if len(v) >= min_reps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=str(SRC))
    ap.add_argument('--min-reps', type=int, default=3)
    ap.add_argument('--folds', type=int, default=5)
    ap.add_argument('--seed', type=int, default=20260919)
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'g1a_selection'))
    a = ap.parse_args()

    cells = load(Path(a.episodes), a.min_reps)
    # group by receiver, and by TASK for the folds
    by_model = defaultdict(list)
    for (uid, m), cands in cells.items():
        by_model[m].append((uid, cands))

    out = {'audit': 'G1a_prime_selection_pilot',
           'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
           'source': str(a.episodes), 'folds': a.folds, 'receivers': {}}

    for m, items in sorted(by_model.items()):
        uids = sorted({u for u, _ in items})
        rng = np.random.default_rng(a.seed)
        fold_of = {u: int(f) for u, f in zip(uids, rng.permutation(np.arange(len(uids)) % a.folds))}
        keys = sorted(items[0][1][0]['f'].keys())

        X = np.array([[c['f'][k] for k in keys] for _, cands in items for c in cands], float)
        y = np.array([c['hidden'] for _, cands in items for c in cands], int)
        grp = np.array([fold_of[u] for u, cands in items for _ in cands], int)

        # cross-fitted scores, model never trained on the task it scores
        for name, mk in (('gbm', lambda: HistGradientBoostingClassifier(max_iter=200, max_depth=4,
                                                                       learning_rate=0.06, random_state=0)),
                         ('logit', lambda: LogisticRegression(max_iter=2000, C=1.0))):
            score = np.full(len(y), np.nan)
            for f in range(a.folds):
                tr, te = grp != f, grp == f
                if y[tr].min() == y[tr].max():
                    continue
                clf = mk()
                if name == 'logit':
                    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
                    clf.fit((X[tr] - mu) / sd, y[tr])
                    score[te] = clf.predict_proba((X[te] - mu) / sd)[:, 1]
                else:
                    clf.fit(X[tr], y[tr])
                    score[te] = clf.predict_proba(X[te])[:, 1]
            # per-task picking
            i = 0
            rows = []
            for u, cands in items:
                n = len(cands)
                sl = slice(i, i + n)
                i += n
                hid = np.array([c['hidden'] for c in cands])
                vis = np.array([c['f']['visible_pass'] for c in cands])
                s = score[sl]
                if np.isnan(s).any():
                    continue
                vis_idx = int(np.argmax(vis)) if vis.any() else n - 1       # first visible pass else last
                rows.append({'uid': u, 'r': n,
                             'single': float(hid.mean()),
                             'visible_picker': int(hid[vis_idx]),
                             'learned_picker': int(hid[int(np.argmax(s))]),
                             'oracle': int(hid.any())})
            def mse(k):
                v = np.array([r[k] for r in rows], float)
                return {'mean': float(v.mean()), 'se': float(v.std(ddof=1) / np.sqrt(len(v)))}
            res = {'n_tasks': len(rows), 'single_attempt': mse('single'),
                   'visible_picker': mse('visible_picker'),
                   'learned_picker': mse('learned_picker'), 'oracle': mse('oracle')}
            d = np.array([r['learned_picker'] - r['visible_picker'] for r in rows], float)
            se = float(d.std(ddof=1) / np.sqrt(len(d)))
            res['learned_minus_visible'] = {'delta': float(d.mean()), 'se': se,
                                            'ci95': [float(d.mean() - 1.96 * se), float(d.mean() + 1.96 * se)]}
            gap = res['oracle']['mean'] - res['visible_picker']['mean']
            res['selection_gap_oracle_minus_visible'] = gap
            res['fraction_of_gap_recovered'] = (float(d.mean()) / gap) if gap > 1e-9 else None
            out['receivers'].setdefault(m, {})[name] = res
        out['receivers'][m]['feature_names'] = keys

    outdir = Path(a.out) / out['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(out, indent=2))
    for m, mm in out['receivers'].items():
        print('\n=== %s ===' % m)
        for name in ('gbm', 'logit'):
            r = mm[name]
            print(' %-6s n=%d  single %.4f | visible picker %.4f | LEARNED %.4f | oracle %.4f'
                  % (name, r['n_tasks'], r['single_attempt']['mean'], r['visible_picker']['mean'],
                     r['learned_picker']['mean'], r['oracle']['mean']))
            lv = r['learned_minus_visible']
            print('        learned - visible = %+.4f [%+.4f, %+.4f] ; selection gap %.4f ; fraction recovered %s'
                  % (lv['delta'], lv['ci95'][0], lv['ci95'][1], r['selection_gap_oracle_minus_visible'],
                     ('%.3f' % r['fraction_of_gap_recovered']) if r['fraction_of_gap_recovered'] is not None else 'n/a'))
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
