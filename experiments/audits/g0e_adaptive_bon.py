#!/usr/bin/env python3
"""G0e -- does multi-turn interaction beat ADAPTIVE best-of-N? Zero GPU cost.

Why this is the first thing to run. Best-of-N is the comparator that can kill this
project: it converts the same extra compute into quality with no multi-turn machinery,
no feedback and no causal inference at all. In its ADAPTIVE form it is stronger still
-- draw candidates one at a time, stop as soon as the cheap visible check passes -- so
it spends fewer calls than plain best-of-N for the same quality. If multi-turn feedback
does not beat adaptive best-of-N at matched budget, the programme needs reframing
before a single new token is generated. This is kill criterion K1.

The data already exist. The sibling project's completed 4,488-episode log contains,
for each (task, receiver), several INDEPENDENT episodes that begin from the same prompt
with different seeds. Their first candidates are therefore i.i.d. draws, which is
exactly the material best-of-N needs -- and the same log records what the multi-turn
loop actually achieved. So the comparison costs no GPU time.

Three arms, all read off the same log:
  MULTI-TURN      what the loop did: its own feedback-driven retries, final hidden verdict.
  ADAPTIVE BoN    draw up to k i.i.d. candidates, return the FIRST whose VISIBLE check
                  passes, else the last; cost is the position of that first pass.
                  Computed exactly by enumerating ordered samples, not simulated.
  ORACLE BoN      success if ANY of k passes the HIDDEN tests: the unbiased pass@k,
                  1 - C(r-s, k)/C(r, k). Not achievable -- it peeks at the outcome --
                  and reported only as a ceiling.

Matched budget. Adaptive BoN's cost is its expected number of calls, so the comparison
is made at matched expected calls and, separately, at matched completion tokens.
"""
from __future__ import annotations

import argparse, json, math, time
from collections import defaultdict
from itertools import permutations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = Path('/Users/yukangzengcmac/DTR-AgentEvals/results/code_routing/log/episodes.jsonl')


def load(path: Path):
    """One record per episode, keyed by (task, first-decision receiver)."""
    per = defaultdict(list)
    skipped_mixed = 0
    for line in path.open():
        r = json.loads(line)
        ds = r.get('decisions') or []
        if not ds:
            continue
        models = {d.get('model_alias') for d in ds if d.get('model_alias')}
        if len(models) > 1:
            # the source project routes between receivers mid-episode; such an episode
            # is not a draw from one receiver and cannot serve as an i.i.d. sample.
            skipped_mixed += 1
            continue
        m = ds[0].get('model_alias') or 'unknown'
        val = ds[0].get('validation') or {}
        nf = val.get('n_fail')
        per[(r['task_uid'], m)].append({
            'first_hidden': bool(r.get('success_first_candidate')),
            'first_visible': (nf == 0) if nf is not None else None,
            'final_hidden': bool(r.get('success')),
            'calls': int(r.get('n_decisions') or len(ds)),
            'completion': int(r.get('completion_tokens') or 0),
            'prompt': int(sum(d.get('prompt_tokens') or 0 for d in ds)),
        })
    return per, skipped_mixed


def adaptive_bon_exact(vis, hid, k: int):
    """Exact E[success] and E[calls] for: draw k without replacement in random order,
    return the first with visible pass, else the last drawn.

    Enumerates every ordered k-sample. r is small (a handful of episodes per task), so
    this is exact rather than Monte Carlo.
    """
    r = len(vis)
    if k > r:
        return None
    tot = 0
    succ = 0.0
    calls = 0.0
    for order in permutations(range(r), k):
        tot += 1
        pos = None
        for j, idx in enumerate(order):
            if vis[idx]:
                pos = j
                break
        if pos is None:
            succ += 1.0 if hid[order[-1]] else 0.0
            calls += k
        else:
            succ += 1.0 if hid[order[pos]] else 0.0
            calls += pos + 1
    return succ / tot, calls / tot


def pass_at_k(s: int, r: int, k: int):
    """Unbiased pass@k = 1 - C(r-s, k)/C(r, k)."""
    if k > r:
        return None
    if r - s < k:
        return 1.0
    return 1.0 - math.comb(r - s, k) / math.comb(r, k)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=str(SRC))
    ap.add_argument('--min-reps', type=int, default=3, help='minimum episodes per (task, receiver)')
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'g0e'))
    a = ap.parse_args()

    per, skipped = load(Path(a.episodes))
    usable = {k: v for k, v in per.items()
              if len(v) >= a.min_reps and all(e['first_visible'] is not None for e in v)}
    by_model = defaultdict(list)
    for (uid, m), eps in usable.items():
        by_model[m].append((uid, eps))

    out = {'audit': 'G0e_adaptive_best_of_n',
           'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
           'source': str(a.episodes), 'episodes_skipped_mixed_receiver': skipped,
           'min_reps_per_cell': a.min_reps, 'receivers': {}}

    for m, items in sorted(by_model.items()):
        rows = []
        for uid, eps in items:
            vis = [e['first_visible'] for e in eps]
            hid = [e['first_hidden'] for e in eps]
            r = len(eps)
            s = sum(hid)
            rec = {'uid': uid, 'r': r, 's_hidden_first': s,
                   'mt_success': float(np.mean([e['final_hidden'] for e in eps])),
                   'mt_calls': float(np.mean([e['calls'] for e in eps])),
                   'mt_completion': float(np.mean([e['completion'] for e in eps])),
                   'single': float(np.mean(hid)), 'bon': {}, 'oracle': {}}
            for k in range(1, min(r, 6) + 1):
                ab = adaptive_bon_exact(vis, hid, k)
                if ab:
                    rec['bon'][k] = {'success': ab[0], 'calls': ab[1]}
                pk = pass_at_k(s, r, k)
                if pk is not None:
                    rec['oracle'][k] = pk
            rows.append(rec)

        n = len(rows)
        def cl(vals):
            v = np.array(vals, float)
            return {'mean': float(v.mean()), 'se': float(v.std(ddof=1) / np.sqrt(len(v)))}

        mt = cl([x['mt_success'] for x in rows])
        mt_calls = float(np.mean([x['mt_calls'] for x in rows]))
        mt_comp = float(np.mean([x['mt_completion'] for x in rows]))
        res = {'n_tasks': n,
               'multi_turn': {**mt, 'mean_calls': mt_calls, 'mean_completion_tokens': mt_comp},
               'single_attempt': cl([x['single'] for x in rows]),
               'adaptive_bon': {}, 'oracle_bon': {}, 'paired_vs_multi_turn': {}}
        for k in range(1, 7):
            have = [x for x in rows if k in x['bon']]
            if len(have) < 0.8 * n:
                continue
            res['adaptive_bon'][k] = {**cl([x['bon'][k]['success'] for x in have]),
                                      'mean_calls': float(np.mean([x['bon'][k]['calls'] for x in have])),
                                      'n_tasks': len(have)}
            ora = [x for x in rows if k in x['oracle']]
            res['oracle_bon'][k] = {**cl([x['oracle'][k] for x in ora]), 'n_tasks': len(ora)}
            # paired difference, multi-turn minus adaptive BoN, over the same tasks
            d = np.array([x['mt_success'] - x['bon'][k]['success'] for x in have], float)
            dc = np.array([x['mt_calls'] - x['bon'][k]['calls'] for x in have], float)
            se = float(d.std(ddof=1) / np.sqrt(len(d)))
            res['paired_vs_multi_turn'][k] = {
                'delta_success': float(d.mean()), 'se': se,
                'ci95': [float(d.mean() - 1.96 * se), float(d.mean() + 1.96 * se)],
                'delta_calls': float(dc.mean()), 'n_tasks': len(d)}
        out['receivers'][m] = res
        out['receivers'][m]['_per_task'] = rows

    outdir = Path(a.out) / out['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(out, indent=2))

    print('episodes skipped (receiver switched mid-episode): %d' % skipped)
    for m, r in out['receivers'].items():
        print('\n=== %s :: %d tasks with >= %d independent episodes ===' % (m, r['n_tasks'], a.min_reps))
        print('  single attempt        success %.4f (SE %.4f)' % (r['single_attempt']['mean'], r['single_attempt']['se']))
        print('  MULTI-TURN (the loop) success %.4f (SE %.4f)   mean calls %.2f, completion %.0f tok'
              % (r['multi_turn']['mean'], r['multi_turn']['se'], r['multi_turn']['mean_calls'],
                 r['multi_turn']['mean_completion_tokens']))
        print('  %-3s %-28s %-22s %s' % ('k', 'adaptive BoN success', 'mean calls', 'MULTI-TURN minus BoN (95% CI)'))
        for k, v in r['adaptive_bon'].items():
            p = r['paired_vs_multi_turn'][k]
            print('  %-3d %.4f (SE %.4f)          %.2f                  %+.4f [%+.4f, %+.4f]  Dcalls %+.2f'
                  % (k, v['mean'], v['se'], v['mean_calls'], p['delta_success'], p['ci95'][0], p['ci95'][1], p['delta_calls']))
        print('  oracle pass@k (unachievable ceiling): %s'
              % {k: round(v['mean'], 4) for k, v in r['oracle_bon'].items()})
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
