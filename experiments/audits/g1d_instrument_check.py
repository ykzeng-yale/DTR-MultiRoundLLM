#!/usr/bin/env python3
"""G1d -- are the negative results about the world, or about my instruments?

Five negative results led to a STOP recommendation. Before accepting that, each
instrument has to be interrogated. This script tests the three ways the instruments could
be producing the nulls by themselves.

CHECK 1 -- PROBE DEGENERACY. G1b manufactured probe inputs by mutating the literals of
the visible assertion. If those mutations mostly produce INVALID inputs (a negative
length, an empty sequence where one element is assumed), every candidate raises the same
exception, agreement is trivially perfect, and the reported "1.63 clusters per task" is a
property of my probe generator rather than of the model. Measured here: per-probe error
rates, how many probes actually discriminate between candidates, and how many tasks have
NO discriminating probe. Then the agreement analysis is redone on the subset where the
probes demonstrably work.

CHECK 2 -- POWER. The selection question only lives on the MIXED stratum, and within it
only where the incumbent visible check fails: 33 of 448 tasks. A null over 33 units is not
evidence of absence unless the detectable effect is smaller than the effect that matters.
Computed here as an exact binomial MDE on the harvestable subset.

CHECK 3 -- STRATUM CONFLATION, the one that may overturn the conclusion. The decomposition
called the 81 "every draw wrong" tasks hopeless. They are hopeless for SELECTION. But this
project is about FEEDBACK, and those are precisely the tasks feedback is supposed to
rescue -- audit A3 measured a 23.9% repair rate on failures. So the stratum I dismissed is
the stratum the original hypothesis targets. Recomputed here with the FINAL (post-feedback)
outcome, to see how much feedback moves tasks that resampling cannot.
"""
from __future__ import annotations

import argparse, json, sys, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments' / 'audits'))
sys.path.insert(0, str(ROOT / 'experiments' / 'common'))
import g1b_execution_agreement as g1b     # noqa: E402
from scoring import split_assertions      # noqa: E402
from concurrent.futures import ProcessPoolExecutor


def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    import math
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mde_paired_binary(n, base, power=0.80, alpha=0.05):
    """Minimum detectable paired difference in a proportion, n paired units."""
    from scipy.stats import norm
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    # conservative: paired SD of a difference of two Bernoullis bounded by sqrt(2p(1-p))
    sd = np.sqrt(2 * base * (1 - base))
    return float((za + zb) * sd / np.sqrt(max(n, 1)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=str(g1b.SRC))
    ap.add_argument('--tasks', default=str(ROOT / 'work' / 'data' / 'tasks.json'))
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'g1d_instrument'))
    a = ap.parse_args()

    tasks = {t['uid']: t for t in json.loads(Path(a.tasks).read_text())}
    cells = defaultdict(list)
    for line in Path(a.episodes).open():
        r = json.loads(line)
        ds = r.get('decisions') or []
        if not ds:
            continue
        ms = {d.get('model_alias') for d in ds if d.get('model_alias')}
        if len(ms) > 1:
            continue
        d0 = ds[0]
        v = d0.get('validation') or {}
        nf = v.get('n_fail')
        if nf is None or not (d0.get('code') or '').strip():
            continue
        cells[(r['task_uid'], ms.pop() if ms else '?')].append({
            'code': d0['code'], 'visible': int(nf == 0),
            'hidden': int(bool(r.get('success_first_candidate'))),
            'final': int(bool(r.get('success'))),
            'calls': int(r.get('n_decisions') or len(ds))})
    cells = {k: v for k, v in cells.items() if len(v) >= 3}

    jobs = []
    for (uid, m), cands in sorted(cells.items()):
        t = tasks.get(uid)
        if t is None:
            continue
        pr = g1b.probes_for(t)
        if not pr or len(pr) < 2:
            continue
        jobs.append(((uid, m), t['entry_point'], pr, split_assertions(t)['preamble'], cands))

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        res = dict(ex.map(g1b.run_cell, jobs, chunksize=2))
    print('executed %d cells in %.1f s\n' % (len(res), time.time() - t0))

    out = {'audit': 'G1d_instrument_check',
           'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()), 'receivers': {}}

    for model in ('qwen2.5-3b-instruct', 'qwen2.5-7b-instruct'):
        sel = [(k, e, p, pre, c) for (k, e, p, pre, c) in jobs if k[1] == model]
        # ---------------- CHECK 1: probe degeneracy ----------------
        n_probe_slots = 0
        n_all_err = 0
        n_all_same = 0
        n_discriminating = 0
        per_task_disc = []
        rows = []
        for key, entry, pr, pre, cands in sel:
            vecs = res.get(key)
            if vecs is None:
                continue
            P = len(pr)
            disc = 0
            for j in range(P):
                col = [v[j] for v in vecs]
                n_probe_slots += 1
                errs = sum(1 for x in col if x.startswith('ERR:') or x == 'MISSING')
                if errs == len(col):
                    n_all_err += 1
                elif len(set(col)) == 1:
                    n_all_same += 1
                else:
                    n_discriminating += 1
                    disc += 1
            per_task_disc.append(disc)
            vis = np.array([c['visible'] for c in cands])
            hid = np.array([c['hidden'] for c in cands])
            fin = np.array([c['final'] for c in cands])
            n = len(cands)
            cnt = Counter(vecs)

            def pick_agree(idxs):
                sub = Counter(vecs[i] for i in idxs)
                top = max(sub.values())
                cand = [i for i in idxs if sub[vecs[i]] == top]
                for i in cand:
                    if vis[i]:
                        return i
                return cand[0]
            vp = [i for i in range(n) if vis[i]]
            i_vis = int(np.argmax(vis)) if vis.any() else n - 1
            i_av = pick_agree(vp) if vp else pick_agree(list(range(n)))
            s = int(hid.sum())
            rows.append({'uid': key[0], 'r': n, 's': s, 'n_disc': disc,
                         'mixed': int(0 < s < n), 'all_wrong': int(s == 0),
                         'visible_right': int(hid[i_vis]), 'agree_right': int(hid[i_av]),
                         'oracle': int(s > 0),
                         'harvestable': int(0 < s < n and hid[i_vis] == 0),
                         'final_any': int(fin.any()), 'final_mean': float(fin.mean()),
                         'calls_mean': float(np.array([c['calls'] for c in cands]).mean())})

        r1 = {'probe_slots': n_probe_slots,
              'all_candidates_errored': n_all_err,
              'all_candidates_identical': n_all_same,
              'discriminating': n_discriminating,
              'frac_all_err': n_all_err / max(n_probe_slots, 1),
              'frac_all_same': n_all_same / max(n_probe_slots, 1),
              'frac_discriminating': n_discriminating / max(n_probe_slots, 1),
              'tasks_with_zero_discriminating_probe': int(sum(1 for d in per_task_disc if d == 0)),
              'tasks_total': len(per_task_disc),
              'median_discriminating_probes_per_task': float(np.median(per_task_disc))}

        # redo the agreement contrast where the probes demonstrably work
        def contrast(subset, key_a='agree_right', key_b='visible_right'):
            if len(subset) < 8:
                return None
            d = np.array([x[key_a] - x[key_b] for x in subset], float)
            se = float(d.std(ddof=1) / np.sqrt(len(d)))
            return {'n': len(subset), 'delta': float(d.mean()), 'se': se,
                    'ci95': [float(d.mean() - 1.96 * se), float(d.mean() + 1.96 * se)]}
        works = [x for x in rows if x['n_disc'] >= 2]
        harvest = [x for x in rows if x['harvestable']]
        harvest_works = [x for x in harvest if x['n_disc'] >= 2]
        r1['agreement_contrast_all_tasks'] = contrast(rows)
        r1['agreement_contrast_probes_work'] = contrast(works)
        r1['agreement_contrast_harvestable_only'] = contrast(harvest)
        r1['agreement_contrast_harvestable_and_probes_work'] = contrast(harvest_works)

        # ---------------- CHECK 2: power ----------------
        nh = len(harvest)
        base = float(np.mean([x['visible_right'] for x in rows])) if rows else 0.5
        r2 = {'n_harvestable': nh,
              'n_all_tasks': len(rows),
              'ceiling_as_frac_of_all_tasks': nh / max(len(rows), 1),
              'MDE_on_harvestable_subset_80pct': mde_paired_binary(nh, 0.5),
              'MDE_on_all_tasks_80pct': mde_paired_binary(len(rows), base),
              'note': ('An effect confined to the harvestable subset is diluted by '
                       'n_harvestable/n_all when measured over all tasks. The MDE that '
                       'matters is the all-task MDE divided by that dilution factor.')}
        r2['effect_over_all_tasks_needed_to_detect'] = r2['MDE_on_all_tasks_80pct']
        r2['implied_within_harvestable_effect_needed'] = (
            r2['MDE_on_all_tasks_80pct'] / max(r2['ceiling_as_frac_of_all_tasks'], 1e-9))

        # ---------------- CHECK 3: stratum conflation ----------------
        allw = [x for x in rows if x['all_wrong']]
        mixed = [x for x in rows if x['mixed']]
        r3 = {
            'n_all_draws_wrong': len(allw),
            'of_those_final_outcome_correct_after_feedback': int(sum(x['final_any'] for x in allw)),
            'frac_rescued_by_feedback': (sum(x['final_any'] for x in allw) / len(allw)) if allw else None,
            'wilson95': wilson(sum(x['final_any'] for x in allw), len(allw)) if allw else None,
            'mean_calls_in_that_stratum': float(np.mean([x['calls_mean'] for x in allw])) if allw else None,
            'n_mixed': len(mixed),
            'note': ('These tasks were called hopeless by the selection decomposition. For '
                     'SELECTION they are: resampling the first attempt never succeeds. But '
                     'they are exactly the stratum FEEDBACK targets, and this project is '
                     'about feedback.'),
        }
        out['receivers'][model] = {'check1_probe_degeneracy': r1, 'check2_power': r2,
                                   'check3_stratum_conflation': r3}

    outdir = Path(a.out) / out['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(out, indent=2))

    for m, rr in out['receivers'].items():
        print('=' * 78)
        print(m)
        c1 = rr['check1_probe_degeneracy']
        print('\nCHECK 1 -- probe degeneracy (%d probe slots over %d tasks)' % (c1['probe_slots'], c1['tasks_total']))
        print('  all candidates errored on the probe : %5d  (%.3f)' % (c1['all_candidates_errored'], c1['frac_all_err']))
        print('  all candidates identical (no signal): %5d  (%.3f)' % (c1['all_candidates_identical'], c1['frac_all_same']))
        print('  DISCRIMINATING                      : %5d  (%.3f)' % (c1['discriminating'], c1['frac_discriminating']))
        print('  tasks with NO discriminating probe  : %d / %d' % (c1['tasks_with_zero_discriminating_probe'], c1['tasks_total']))
        print('  median discriminating probes/task   : %.1f' % c1['median_discriminating_probes_per_task'])
        for k in ('agreement_contrast_all_tasks', 'agreement_contrast_probes_work',
                  'agreement_contrast_harvestable_only', 'agreement_contrast_harvestable_and_probes_work'):
            v = c1[k]
            if v:
                print('  %-46s n=%4d  delta %+.4f [%+.4f, %+.4f]' % (k.replace('agreement_contrast_', ''), v['n'], v['delta'], v['ci95'][0], v['ci95'][1]))
        c2 = rr['check2_power']
        print('\nCHECK 2 -- power')
        print('  harvestable tasks %d of %d (%.4f of all)' % (c2['n_harvestable'], c2['n_all_tasks'], c2['ceiling_as_frac_of_all_tasks']))
        print('  MDE over all tasks at 80%% power      : %.4f' % c2['MDE_on_all_tasks_80pct'])
        print('  => within-harvestable effect needed  : %.4f  (i.e. the method must fix this'
              % c2['implied_within_harvestable_effect_needed'])
        print('     fraction of the 33 harvestable tasks before we could see it at all)')
        c3 = rr['check3_stratum_conflation']
        print('\nCHECK 3 -- the stratum I called hopeless')
        print('  tasks where every independent draw failed: %d' % c3['n_all_draws_wrong'])
        print('  of those, FINAL outcome correct after feedback: %d (%.3f) 95%% CI [%.3f, %.3f]'
              % (c3['of_those_final_outcome_correct_after_feedback'], c3['frac_rescued_by_feedback'],
                 c3['wilson95'][0], c3['wilson95'][1]))
        print('  mean calls spent there: %.2f' % c3['mean_calls_in_that_stratum'])
        print()
    print('wrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
