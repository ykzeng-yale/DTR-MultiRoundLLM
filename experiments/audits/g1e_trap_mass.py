#!/usr/bin/env python3
"""G1e -- consensus-trap mass: a PROBE-FREE upper bound on any leakage-free selector.

Why this is the right measurement. My earlier selection work was invalidated two ways:
the probe generator was inert on most tasks, and the candidate banks were selected on a
variable downstream of the outcome. Both flaws attach to the *instrument*. Trap mass has
neither problem -- it needs no probes at all, and it is computed on the complete corpus.

It answers the question directly. A selector that cannot see hidden tests can only net-gain
on a task where the incumbent's pick is hidden-WRONG while a hidden-CORRECT candidate sits
in the same bank. Count those tasks and you have an assumption-free ceiling for every such
selector, learned or clustering-based, at this bank size.

The decomposition that matters most: is the correct candidate INSIDE the visible-passing
set, or outside it? A selector that respects the visible filter (our agree+visible rule,
and the filtering-plus-reranking stack the literature studies) can only reorder WITHIN that
set. Opportunities where the only correct candidate fails the visible check are unreachable
without overriding the filter -- and overriding it is what the literature measures as
harmful.

Two corrections from the theory workstream's audit are applied here:
  * ALL initial candidates are retained regardless of later receiver switching. Dropping
    switchers conditions on a post-treatment variable and produced 0.698 vs 0.105
    first-candidate success between retained and excluded episodes.
  * The incumbent flag is `validation.passed`, the flag the source loop actually stopped
    on, not `n_fail == 0`.
"""
from __future__ import annotations

import argparse, json, math, time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = Path('/Users/yukangzengcmac/DTR-AgentEvals/results/code_routing/log/episodes.jsonl')


def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=str(SRC))
    ap.add_argument('--min-reps', type=int, default=3)
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'g1e_trap_mass'))
    a = ap.parse_args()

    cells = defaultdict(list)
    n_ep = n_switch = 0
    for line in Path(a.episodes).open():
        r = json.loads(line)
        ds = r.get('decisions') or []
        if not ds:
            continue
        n_ep += 1
        d0 = ds[0]
        val = d0.get('validation') or {}
        if 'passed' not in val:
            continue
        models = {d.get('model_alias') for d in ds if d.get('model_alias')}
        if len(models) > 1:
            n_switch += 1
        # the FIRST decision's receiver defines the bank; later switching is irrelevant to
        # the first candidate and must not be used to filter it.
        m = d0.get('model_alias') or 'unknown'
        cells[(r['task_uid'], m)].append({
            'visible': int(bool(val.get('passed'))),
            'visible_nfail0': int(val.get('n_fail') == 0),
            'hidden': int(bool(r.get('success_first_candidate'))),
        })
    print('episodes read %d; episodes that later switched receiver %d (RETAINED, not dropped)'
          % (n_ep, n_switch))
    flagdiff = sum(1 for v in cells.values() for c in v if c['visible'] != c['visible_nfail0'])
    print('first decisions where validation.passed disagrees with n_fail==0: %d' % flagdiff)

    cells = {k: v for k, v in cells.items() if len(v) >= a.min_reps}
    out = {'audit': 'G1e_trap_mass', 'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
           'episodes': n_ep, 'episodes_switched_retained': n_switch,
           'flag_disagreements': flagdiff, 'receivers': {}}

    for m in sorted({k[1] for k in cells}):
        rows = [v for k, v in cells.items() if k[1] == m]
        n = len(rows)
        st = defaultdict(int)
        for cands in rows:
            vis = np.array([c['visible'] for c in cands])
            hid = np.array([c['hidden'] for c in cands])
            r = len(cands)
            VP = np.nonzero(vis)[0]
            any_corr = bool(hid.any())
            st['tasks'] += 1
            if not any_corr:
                st['no_correct_candidate_anywhere'] += 1
                continue
            if vis.all() and hid.all():
                st['everything_correct_and_passing'] += 1
            # incumbent A: first visible pass, else last
            iA = int(VP[0]) if len(VP) else r - 1
            # incumbent B: uniform among visible-passing (the audit's comparator)
            pB = float(hid[VP].mean()) if len(VP) else float(hid[-1])
            if hid[iA] == 0:
                st['OPPORTUNITY_first_visible_rule'] += 1
                if len(VP) and hid[VP].any():
                    st['  reachable_within_visible_set'] += 1
                else:
                    st['  correct_only_OUTSIDE_visible_set'] += 1
            if pB < 1.0:
                st['OPPORTUNITY_uniform_visible_rule'] += 1
            # strict consensus trap: a visible-passing majority that is hidden-wrong
            if len(VP) >= 2:
                wrong = int((hid[VP] == 0).sum())
                if wrong > len(VP) / 2 and hid[VP].any():
                    st['STRICT_consensus_trap'] += 1
        res = {'n_tasks': n}
        for k in sorted(st):
            if k == 'tasks':
                continue
            res[k.strip()] = {'count': st[k], 'frac': st[k] / n, 'wilson95': wilson(st[k], n)}
        out['receivers'][m] = res

    outdir = Path(a.out) / out['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(out, indent=2))
    for m, res in out['receivers'].items():
        print('\n=== %s :: %d tasks (all candidates retained) ===' % (m, res['n_tasks']))
        for k, v in res.items():
            if k == 'n_tasks':
                continue
            print('  %-42s %4d  %.4f  [%.4f, %.4f]' % (k, v['count'], v['frac'], v['wilson95'][0], v['wilson95'][1]))
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
