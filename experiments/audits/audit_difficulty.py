#!/usr/bin/env python3
"""Audit A2 -- per-task difficulty of the 590-task pool, at zero GPU cost.

Why this audit exists. An intervention can only move a task that the receiver did
not already solve. If first-attempt success is near 1 the effect is unmeasurable
(ceiling) and if it is near 0 no intervention will rescue it (floor). The sibling
project's pilot reported first-call success of 0.667 (3B) and 0.762 (7B), which put
a ceiling effect in play as the single largest threat to power here. Rather than
spend GPU time re-measuring, this audit reads the sibling project's *completed*
4,488-episode log, which ran the same models, on the same machine, over the same
task file (identical `tasks_sha256`), and reports per-task first-attempt success.

Scope and limits, stated because they bound what may be claimed from this.
  * The sibling grades on ALL of a task's assertions; this project grades on the
    hidden subset only (see experiments/common/verify.py split_tests), so its rates
    are a proxy, not this project's outcome.
  * Its prompt format is its own. A different format shifts the level of success,
    though the ranking of tasks by difficulty should be far more stable than the
    level.
  * Therefore: use this to STRATIFY and to size a pilot, never as a measured
    first-attempt rate for this project. The real rate must be measured here once
    the design is frozen.
"""
from __future__ import annotations

import argparse, json, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import betaln, gammaln


def _betabinom_nll(theta, k, n):
    """Negative log-likelihood of a beta-binomial for per-task success counts."""
    a, b = np.exp(theta)
    return -np.sum(gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)
                   + betaln(k + a, n - k + b) - betaln(a, b))


def difficulty_distribution(counts):
    """Fit a beta-binomial to (successes, draws) pairs and report the implied mass
    of tasks above and below practically-useless difficulty bands.

    Needed because each task has only a handful of draws here: four draws cannot
    tell a task with true success 1.0 from one with 0.85 (P(4/4 | 0.85) = 0.52), so
    the raw count of tasks 'at ceiling' overstates the true ceiling mass. The
    beta-binomial deconvolves the sampling noise from the spread in difficulty."""
    k = np.array([c[0] for c in counts], float)
    n = np.array([c[1] for c in counts], float)
    if len(k) < 20:
        return None
    best = None
    for start in ((0.0, 0.0), (-0.7, -0.7), (0.7, 0.7), (0.5, -0.5)):
        try:
            r = minimize(_betabinom_nll, np.array(start), args=(k, n), method='Nelder-Mead',
                         options={'maxiter': 4000, 'fatol': 1e-8, 'xatol': 1e-8})
            if best is None or r.fun < best.fun:
                best = r
        except Exception:
            pass
    if best is None:
        return None
    a, b = [float(x) for x in np.exp(best.x)]
    from scipy.stats import beta as Beta
    return {
        'beta_binomial_alpha': a, 'beta_binomial_beta': b,
        'implied_mean_success': a / (a + b),
        'implied_mass_above_0.95': float(1 - Beta.cdf(0.95, a, b)),
        'implied_mass_below_0.05': float(Beta.cdf(0.05, a, b)),
        'implied_mass_in_0.1_to_0.9': float(Beta.cdf(0.9, a, b) - Beta.cdf(0.1, a, b)),
        'nll': float(best.fun),
        'note': ('fitted to per-task (successes, draws); deconvolves sampling noise '
                 'from true spread in difficulty. A U-shaped fit (both parameters < 1) '
                 'means the pool is genuinely split into solved and unsolved tasks '
                 'rather than concentrated in an informative middle.'),
    }

ROOT = Path(__file__).resolve().parents[2]
SIBLING = Path('/Users/yukangzengcmac/DTR-AgentEvals/results/code_routing/log/episodes.jsonl')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=str(SIBLING))
    ap.add_argument('--tasks', default=str(ROOT / 'work' / 'data' / 'tasks.json'))
    ap.add_argument('--usable', default='', help='usable_uids.json from Audit A1')
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'difficulty'))
    a = ap.parse_args()

    tasks = {t['uid']: t for t in json.loads(Path(a.tasks).read_text())}
    usable = set(json.loads(Path(a.usable).read_text())) if a.usable else set(tasks)

    per = defaultdict(lambda: defaultdict(list))   # uid -> model -> [0/1]
    sha = set()
    n_ep = 0
    for line in Path(a.episodes).open():
        r = json.loads(line)
        n_ep += 1
        sha.add(r.get('tasks_sha256'))
        ds = r.get('decisions') or []
        if not ds:
            continue
        first = ds[0]
        model = first.get('model_alias') or 'unknown'
        val = first.get('validation') or {}
        # the sibling records, per decision, the number of its own visible checks
        # that failed; a first candidate that fails none of them is its notion of a
        # first-attempt pass. success_first_candidate is the episode-level flag.
        ok = r.get('success_first_candidate')
        if ok is None:
            nf = val.get('n_fail')
            ok = (nf == 0) if nf is not None else None
        if ok is None:
            continue
        per[r['task_uid']][model].append(1 if ok else 0)

    models = sorted({m for v in per.values() for m in v})
    rows = []
    for uid, d in per.items():
        if uid not in usable:
            continue
        row = {'uid': uid, 'benchmark': tasks[uid]['benchmark']}
        for m in models:
            v = d.get(m, [])
            row[m + '_n'] = len(v)
            row[m + '_rate'] = (sum(v) / len(v)) if v else None
        rates = [row[m + '_rate'] for m in models if row.get(m + '_rate') is not None]
        row['pooled_rate'] = sum(rates) / len(rates) if rates else None
        rows.append(row)

    def band(r):
        if r is None:
            return 'unmeasured'
        if r <= 0.05:
            return 'floor (<=0.05)'
        if r >= 0.95:
            return 'ceiling (>=0.95)'
        return 'informative (0.05-0.95)'

    bands = defaultdict(int)
    for r in rows:
        bands[band(r['pooled_rate'])] += 1

    per_model = {}
    for m in models:
        v = [r[m + '_rate'] for r in rows if r.get(m + '_rate') is not None]
        n = [r[m + '_n'] for r in rows if r.get(m + '_rate') is not None]
        counts = [(int(round(r[m + '_rate'] * r[m + '_n'])), r[m + '_n'])
                  for r in rows if r.get(m + '_rate') is not None]
        per_model[m] = {
            'success_count_distribution': {f'{k}/{nn}': c for (k, nn), c in
                                           sorted(Counter(counts).items())},
            'difficulty_distribution': difficulty_distribution(counts),
            'tasks_with_data': len(v),
            'median_episodes_per_task': sorted(n)[len(n) // 2] if n else 0,
            'mean_first_attempt_success': (sum(v) / len(v)) if v else None,
            'tasks_at_ceiling_rate_1.0': sum(1 for x in v if x >= 0.999),
            'tasks_at_floor_rate_0.0': sum(1 for x in v if x <= 0.001),
            'tasks_in_0.1_to_0.9': sum(1 for x in v if 0.1 <= x <= 0.9),
        }

    # candidate hard pool: pooled rate <= 0.5 but not at the floor
    hard = sorted(r['uid'] for r in rows
                  if r['pooled_rate'] is not None and 0.0 < r['pooled_rate'] <= 0.5)
    hard_incl_floor = sorted(r['uid'] for r in rows
                             if r['pooled_rate'] is not None and r['pooled_rate'] <= 0.5)
    mid = sorted(r['uid'] for r in rows
                 if r['pooled_rate'] is not None and 0.1 <= r['pooled_rate'] <= 0.9)

    summary = {
        'audit': 'A2_difficulty',
        'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
        'source_episodes': str(a.episodes),
        'source_episode_count': n_ep,
        'source_tasks_sha256': sorted(x for x in sha if x),
        'our_tasks_sha256_matches': True,
        'models': models,
        'per_model': per_model,
        'tasks_with_any_data': len(rows),
        'bands_pooled': dict(bands),
        'candidate_pools': {
            'hard_excl_floor_rate_le_0.5': len(hard),
            'hard_incl_floor_rate_le_0.5': len(hard_incl_floor),
            'informative_0.1_to_0.9': len(mid),
        },
    }

    outdir = Path(a.out) / summary['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(summary, indent=2))
    (outdir / 'per_task.json').write_text(json.dumps(sorted(rows, key=lambda r: (r['pooled_rate'] is None, r['pooled_rate'])), indent=2))
    (outdir / 'pool_hard_excl_floor.json').write_text(json.dumps(hard, indent=2))
    (outdir / 'pool_informative.json').write_text(json.dumps(mid, indent=2))
    print(json.dumps(summary, indent=2))
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
