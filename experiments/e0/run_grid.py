#!/usr/bin/env python3
"""E0 grid driver: 17 cells, exact truth, task-clustered inference. CPU only.

Usage
  python run_grid.py --list                      show the cells
  python run_grid.py --cell base --reps 200      one cell
  python run_grid.py --reps 1000                 the whole grid (pre-registered R)

Every cell writes an immutable directory under results/e0/<stamp>/<cell>/ with a
manifest recording the seed table, the code hash, the exact truth it was graded
against, and the metrics. A completed cell is never overwritten.
"""
from __future__ import annotations

import argparse, hashlib, json, platform, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from simulator import (ARMS, K, NS, UNIF5, kernel, make_beh, simulate,          # noqa: E402
                       true_blips_posterior, true_value, optimal_rule, Vtab, P_E, P_Z, p_s1, NE)
from estimators import (blip_ipw, blip_mediator, blip_naive_conditional,        # noqa: E402
                        blip_naive_marginal, learned_rule, value_dr, value_gcomp, value_ipw)

CORR = [a for a in ARMS if a != 'STOP']

#: base configuration; every sweep changes exactly one field.
BASE = dict(n_tasks=230, runs=40, T=3, kappa=1.0, floor=0.10, cmult=1.0,
            gz=0.0, mislabel=0.0, template_sd=0.0)

def _c(**kw):
    d = dict(BASE)
    d.update(kw)
    return d

#: 17 cells: base, 12 one-factor sweeps, 4 failure cells.
CELLS = {
    'base':            _c(),
    # confounding strength
    'kappa0':          _c(kappa=0.0, floor=0.20),   # floor 0.20 at K=5 is exactly uniform
    'kappa0.5':        _c(kappa=0.5),
    'kappa2':          _c(kappa=2.0),
    # positivity floor (K * floor <= 1, so 0.20 is the maximum at K = 5)
    'floor0.05':       _c(floor=0.05),
    'floor0.02':       _c(floor=0.02),
    # horizon
    'T2':              _c(T=2),
    'T5':              _c(T=5),
    # sample size
    'n590':            _c(n_tasks=590),
    'runs10':          _c(runs=10),
    'runs160':         _c(runs=160),
    # effect size
    'half_effect':     _c(cmult=0.5),
    # a second confounding shape: the logging policy tracks the LATENT error type
    'latent_track':    _c(gz=1.0),
    # ---- failure cells: the estimators are expected to break in these ----
    'FAIL_positivity': _c(kappa=2.5, floor=0.02),
    'FAIL_latent':     _c(gz=2.0),
    'FAIL_mislabel':   _c(mislabel=0.15),
    'FAIL_coarsening': _c(template_sd=0.28),
}


def code_sha256() -> str:
    h = hashlib.sha256()
    for f in ('simulator.py', 'estimators.py', 'run_grid.py'):
        h.update((HERE / f).read_bytes())
    return h.hexdigest()


def one_rep(args):
    seed, cfg = args
    rng = np.random.default_rng(seed)
    Kk = kernel(cfg['cmult'])
    beh = make_beh(cfg['kappa'], cfg['floor'], cfg['gz'])
    d = simulate(cfg['n_tasks'], cfg['runs'], cfg['T'], Kk, beh, rng,
                 mislabel=cfg['mislabel'], template_sd=cfg['template_sd'],
                 cmult=cfg['cmult'])
    out = {'blip': {}, 'marg': blip_naive_marginal(d)}
    for s in range(NS):
        out['blip'][s] = {
            'naive_cond': blip_naive_conditional(d, s),
            'mediator': blip_mediator(d, s),
            'ipw': blip_ipw(d, s, cfg['T']),
        }
    out['v_gcomp'] = value_gcomp(d, cfg['T'])
    out['v_ipw'] = value_ipw(d, cfg['T'])
    out['v_dr'] = value_dr(d, cfg['T'], rng=rng)
    out['rule'] = {'%d,%d' % k: v for k, v in learned_rule(d, cfg['T']).items()}
    out['n_mislabelled'] = d['n_mislabelled']
    return out


def chunk(args):
    base, cnt, cfg = args
    return [one_rep((base + i, cfg)) for i in range(cnt)]


def rule_value(Kk, rule: dict, T: int) -> float:
    """Exact value of a deterministic state-only rule, by dynamic programming."""
    V = np.zeros((T + 2, NE, 2, NS))
    for e in range(NE):
        for z in (0, 1):
            V[T + 1, e, z, :] = (np.arange(NS) == 3)
    for t in range(T, 0, -1):
        for e in range(NE):
            for z in (0, 1):
                for s in range(NS):
                    ai = rule.get('%d,%d' % (t - 1, s), rule.get((t - 1, s), 0))
                    V[t, e, z, s] = ((1.0 if s == 3 else 0.0) if ai == 0
                                     else float(Kk[e, z, s, ai] @ V[t + 1, e, z, :]))
    return sum(P_E[e] * (P_Z if z else 1 - P_Z) * float(p_s1(e) @ V[1, e, z, :])
               for e in range(NE) for z in (0, 1))


def metrics(reps, cfg) -> dict:
    Kk = kernel(cfg['cmult'])
    T = cfg['T']
    tp = true_blips_posterior(Kk, T)
    v_true = true_value(Kk, UNIF5, T)
    opt = optimal_rule(Kk, T)
    v_opt = rule_value(Kk, {'%d,%d' % (t, s): opt[(t + 1, s)] for t in range(T) for s in range(NS)}, T)

    m = {'n_reps': len(reps), 'truth': {'V_uniform5': v_true, 'V_state_only_optimal': v_opt,
                                        'blip_posterior': {'s%d' % s: {a: tp[(s, a)] for a in CORR}
                                                           for s in range(NS)}}}
    # --- P1: ordering recovery in the repair strata -------------------------
    m['ordering'] = {}
    for s in (0, 1, 2, 3):
        truth = np.array([tp[(s, a)] for a in CORR])
        top_true = CORR[int(np.argmax(truth))]
        cell = {}
        for nm in ('naive_cond', 'mediator', 'ipw'):
            M = np.array([[r['blip'][s][nm][a] for a in CORR] for r in reps], float)
            ok = ~np.isnan(M).any(1)
            M = M[ok]
            if not len(M):
                continue
            taus = [kendalltau(truth, row).statistic for row in M]
            cell[nm] = {'mean_kendall_tau': float(np.mean(taus)),
                        'P_tau_gt_0': float(np.mean(np.array(taus) > 0)),
                        'P_top_arm_correct': float(np.mean([CORR[int(np.argmax(r))] == top_true for r in M])),
                        'bias': {a: float(M.mean(0)[i] - truth[i]) for i, a in enumerate(CORR)},
                        'rmse': {a: float(np.sqrt(((M[:, i] - truth[i]) ** 2).mean())) for i, a in enumerate(CORR)},
                        'n_usable_reps': int(len(M))}
        # the marginal critic has no state, so its ordering is compared at every s
        Mm = np.array([[r['marg'][a] for a in CORR] for r in reps], float)
        ok = ~np.isnan(Mm).any(1)
        Mm = Mm[ok]
        taus = [kendalltau(truth, row).statistic for row in Mm]
        cell['naive_marginal'] = {'mean_kendall_tau': float(np.mean(taus)),
                                  'P_tau_gt_0': float(np.mean(np.array(taus) > 0)),
                                  'P_top_arm_correct': float(np.mean([CORR[int(np.argmax(r))] == top_true for r in Mm])),
                                  'n_usable_reps': int(len(Mm))}
        m['ordering']['s%d' % s] = cell
    # --- P2: value estimation and coverage ----------------------------------
    m['value'] = {'truth': v_true}
    for nm, key in (('gcomp', 'v_gcomp'), ('ipw', 'v_ipw'), ('dr', 'v_dr')):
        if key == 'v_gcomp':
            est = np.array([r[key] for r in reps], float)
            m['value'][nm] = {'mean': float(est.mean()), 'bias': float(est.mean() - v_true),
                              'sd': float(est.std(ddof=1))}
        else:
            est = np.array([r[key][0] for r in reps], float)
            lo = np.array([r[key][2] for r in reps], float)
            hi = np.array([r[key][3] for r in reps], float)
            m['value'][nm] = {'mean': float(est.mean()), 'bias': float(est.mean() - v_true),
                              'sd': float(est.std(ddof=1)),
                              'mean_se': float(np.mean([r[key][1] for r in reps])),
                              'coverage_95': float(np.mean((lo <= v_true) & (v_true <= hi)))}
    # --- P3: decision quality ----------------------------------------------
    vals = [rule_value(Kk, r['rule'], T) for r in reps]
    m['decision'] = {'V_state_only_optimal': v_opt,
                     'mean_V_of_learned_rule': float(np.mean(vals)),
                     'mean_regret': float(v_opt - np.mean(vals)),
                     'P_learned_rule_optimal': float(np.mean([abs(v - v_opt) < 1e-12 for v in vals]))}
    m['n_mislabelled_mean'] = float(np.mean([r['n_mislabelled'] for r in reps]))
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cell', action='append', default=None)
    ap.add_argument('--reps', type=int, default=1000)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--seed-base', type=int, default=20260919)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--out', default=str(ROOT / 'results' / 'e0'))
    a = ap.parse_args()
    if a.list:
        for k, v in CELLS.items():
            print('%-18s %s' % (k, {kk: vv for kk, vv in v.items() if vv != BASE.get(kk) or kk == 'n_tasks'}))
        return 0
    names = a.cell or list(CELLS)
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    root = Path(a.out) / stamp
    root.mkdir(parents=True, exist_ok=True)
    (root / 'grid_manifest.json').write_text(json.dumps({
        'created_utc': stamp, 'reps_per_cell': a.reps, 'seed_base': a.seed_base,
        'workers': a.workers, 'code_sha256': code_sha256(),
        'python': sys.version.split()[0], 'platform': platform.platform(),
        'cells': {n: CELLS[n] for n in names},
        'note': ('Exact truth is recomputed per cell from the cell own cmult and T. '
                 'Blips are graded against the POSTERIOR-weighted truth, because an '
                 'estimator that conditions on the observed state targets that object, '
                 'not the prior-weighted one.'),
    }, indent=2))
    for ci, name in enumerate(names):
        cfg = CELLS[name]
        outdir = root / name
        outdir.mkdir(exist_ok=True)
        per = max(1, a.reps // a.workers)
        jobs = [(a.seed_base + 1_000_000 * ci + 10_000 * w, per, cfg) for w in range(a.workers)]
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            reps = [r for c in ex.map(chunk, jobs) for r in c]
        el = time.time() - t0
        mm = metrics(reps, cfg)
        mm['elapsed_seconds'] = round(el, 1)
        mm['seconds_per_rep'] = round(el / max(len(reps), 1), 4)
        mm['cell'] = name
        mm['config'] = cfg
        (outdir / 'metrics.json').write_text(json.dumps(mm, indent=2))
        o1 = mm['ordering']['s1']
        print('%-18s R=%4d %6.1fs  s=1 tau: marg %+.3f  cond %+.3f  ipw %+.3f | '
              'P(top) marg %.3f ipw %.3f | DR bias %+.4f cov %.3f | regret %.4f'
              % (name, len(reps), el,
                 o1['naive_marginal']['mean_kendall_tau'], o1['naive_cond']['mean_kendall_tau'],
                 o1['ipw']['mean_kendall_tau'], o1['naive_marginal']['P_top_arm_correct'],
                 o1['ipw']['P_top_arm_correct'], mm['value']['dr']['bias'],
                 mm['value']['dr']['coverage_95'], mm['decision']['mean_regret']))
    print('\nwrote', root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
