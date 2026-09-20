#!/usr/bin/env python3
"""G1c -- does agreement-GATED compute allocation beat uniform allocation at matched cost?

G1b separated two questions that had been conflated:
  SELECTION  -- which of several candidates to return. Agreement recovers ~13% of the
                oracle gap, interval covering zero. It fails, and the mechanism is
                visible: at k ~ 3.5 a weak model's draws mostly agree (1.63 clusters per
                task, top cluster holding 83% of candidates), so clustering has almost
                nothing to discriminate.
  CONFIDENCE -- whether the answer in hand is right. Here agreement is strong and
                consistent across both receivers: accuracy 0.879 when the top cluster is
                large against 0.552 when it is small (3B), 0.878 against 0.526 (7B).

A stopping rule does not need to know which candidate is right. It needs to know when it
does not know, so that compute goes to the tasks that need it. This script prices that
directly, at matched expected cost, by exact enumeration over draw orders.

Policies, all using only policy-observable information (candidate source, the one visible
assertion, and outputs on probe inputs whose correct answers are unknown):

  U_k        uniform adaptive best-of-k: draw until the visible assertion passes, up to k.
  GATE(k1,k2) draw k1; if the drawn candidates' output vectors AGREE and one passes the
             visible assertion, stop; otherwise escalate to k2 total draws and return the
             agreement-plus-visible pick.

The comparison is success against EXPECTED DRAWS, so a policy that spends less is not
rewarded for it and a policy that spends more must earn it.
"""
from __future__ import annotations

import argparse, json, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from itertools import permutations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments' / 'audits'))
sys.path.insert(0, str(ROOT / 'experiments' / 'common'))
# imported by module NAME, not by file path: a spec-loaded module cannot be pickled to
# ProcessPoolExecutor workers, which re-import by name.
import g1b_execution_agreement as g1b   # noqa: E402
from scoring import split_assertions    # noqa: E402


def eval_task(vecs, vis, hid, k_list, gates):
    """Exact expected success and draws for each policy, over all ordered samples."""
    r = len(vis)
    out = {}
    for k in k_list:
        if k > r:
            continue
        s = c = n = 0
        for o in permutations(range(r), k):
            n += 1
            pos = next((j for j, i in enumerate(o) if vis[i]), None)
            idx = o[pos] if pos is not None else o[-1]
            c += (pos + 1) if pos is not None else k
            s += hid[idx]
        out['U%d' % k] = (s / n, c / n)
    for (k1, k2) in gates:
        if k2 > r:
            continue
        s = c = n = 0
        for o in permutations(range(r), k2):
            n += 1
            first = o[:k1]
            agree = len({vecs[i] for i in first}) == 1
            vp = [i for i in first if vis[i]]
            if agree and vp:
                s += hid[vp[0]]
                c += k1
            else:
                sub = Counter(vecs[i] for i in o)
                top = max(sub.values())
                cand = [i for i in o if sub[vecs[i]] == top]
                pick = next((i for i in cand if vis[i]), cand[0])
                s += hid[pick]
                c += k2
        out['G%d_%d' % (k1, k2)] = (s / n, c / n)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=str(g1b.SRC))
    ap.add_argument('--tasks', default=str(ROOT / 'work' / 'data' / 'tasks.json'))
    ap.add_argument('--min-reps', type=int, default=4, help='need >= 4 draws to price a 2->4 gate')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'g1c_allocation'))
    a = ap.parse_args()

    tasks = {t['uid']: t for t in json.loads(Path(a.tasks).read_text())}
    cells = defaultdict(list)
    for line in Path(a.episodes).open():
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
        if nf is None or not (d0.get('code') or '').strip():
            continue
        cells[(r['task_uid'], models.pop() if models else '?')].append({
            'code': d0['code'], 'visible': int(nf == 0),
            'hidden': int(bool(r.get('success_first_candidate')))})
    cells = {k: v for k, v in cells.items() if len(v) >= a.min_reps}

    jobs = []
    for (uid, m), cands in sorted(cells.items()):
        t = tasks.get(uid)
        if t is None:
            continue
        pr = g1b.probes_for(t)
        if not pr or len(pr) < 2:
            continue
        jobs.append(((uid, m), t['entry_point'], pr, split_assertions(t)['preamble'], cands))
    print('cells with >= %d draws and usable probes: %d' % (a.min_reps, len(jobs)))

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        res = dict(ex.map(g1b.run_cell, jobs, chunksize=2))
    print('executed in %.1f s' % (time.time() - t0))

    K = [1, 2, 3, 4]
    GATES = [(2, 3), (2, 4), (3, 4)]
    by_model = defaultdict(list)
    for key, entry, pr, pre, cands in jobs:
        vecs = res.get(key)
        if vecs is None:
            continue
        vis = [c['visible'] for c in cands]
        hid = [c['hidden'] for c in cands]
        e = eval_task(vecs, vis, hid, K, GATES)
        e['_oracle'] = (float(any(hid)), float(len(hid)))
        by_model[key[1]].append(e)

    out = {'audit': 'G1c_allocation_policy',
           'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
           'min_reps': a.min_reps, 'receivers': {}}
    for m, rows in sorted(by_model.items()):
        pol = sorted({k for r in rows for k in r if not k.startswith('_')})
        rr = {'n_tasks': len(rows), 'policies': {}}
        for p in pol:
            have = [r for r in rows if p in r]
            if len(have) < 0.9 * len(rows):
                continue
            s = np.array([r[p][0] for r in have], float)
            c = np.array([r[p][1] for r in have], float)
            rr['policies'][p] = {'success': float(s.mean()),
                                 'se': float(s.std(ddof=1) / np.sqrt(len(s))),
                                 'expected_draws': float(c.mean()), 'n': len(have)}
        # paired comparisons of each gate against the uniform policy with the closest cost
        rr['gate_vs_uniform'] = {}
        for g in [p for p in rr['policies'] if p.startswith('G')]:
            gc = rr['policies'][g]['expected_draws']
            best = min([p for p in rr['policies'] if p.startswith('U')],
                       key=lambda u: abs(rr['policies'][u]['expected_draws'] - gc))
            have = [r for r in rows if g in r and best in r]
            d = np.array([r[g][0] - r[best][0] for r in have], float)
            dc = np.array([r[g][1] - r[best][1] for r in have], float)
            se = float(d.std(ddof=1) / np.sqrt(len(d)))
            rr['gate_vs_uniform'][g] = {
                'compared_to': best, 'delta_success': float(d.mean()), 'se': se,
                'ci95': [float(d.mean() - 1.96 * se), float(d.mean() + 1.96 * se)],
                'delta_draws': float(dc.mean()), 'n': len(have)}
        out['receivers'][m] = rr

    outdir = Path(a.out) / out['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(out, indent=2))
    for m, rr in out['receivers'].items():
        print('\n=== %s :: %d tasks ===' % (m, rr['n_tasks']))
        print('  %-8s %-22s %s' % ('policy', 'success', 'expected draws'))
        for p, v in sorted(rr['policies'].items(), key=lambda kv: kv[1]['expected_draws']):
            print('  %-8s %.4f (SE %.4f)      %.3f' % (p, v['success'], v['se'], v['expected_draws']))
        print('  --- agreement-gated vs the closest-cost uniform policy ---')
        for g, v in rr['gate_vs_uniform'].items():
            print('  %-8s vs %-4s  Delta success %+.4f [%+.4f, %+.4f]  Delta draws %+.3f'
                  % (g, v['compared_to'], v['delta_success'], v['ci95'][0], v['ci95'][1], v['delta_draws']))
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
