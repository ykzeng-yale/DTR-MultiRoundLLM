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
                       true_blips_posterior, true_value, reference_state_rule, template_kernel,
                       true_logging_conditional_blips, P_E, P_Z, p_s1, NE)
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
    # Truth follows the actual replicate's frozen template mixture.
    actual_kernel = template_kernel(cfg['cmult'], d['template_offsets'])
    tp = true_blips_posterior(actual_kernel, cfg['T'])
    assoc = true_logging_conditional_blips(actual_kernel, cfg['T'], beh)
    ref = reference_state_rule(actual_kernel, cfg['T'])
    out = {'seed': seed, 'blip': {}, 'marg': blip_naive_marginal(d),
           'template_offsets': d['template_offsets'],
           'truth': {'value': true_value(actual_kernel, UNIF5, cfg['T']),
                     'uniform_blips': {str(s): {a: tp[s, a] for a in ARMS} for s in range(NS)},
                     'logging_association': {str(s): {a: assoc[s, a] for a in ARMS} for s in range(NS)},
                     'reference_rule_value': rule_value(actual_kernel, {(t-1,s): a for (t,s),a in ref.items()}, cfg['T'])}}

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
    out['learned_rule_value'] = rule_value(actual_kernel, out['rule'], cfg['T'])
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
    truths = np.array([r['truth']['value'] for r in reps])
    refs = np.array([r['truth']['reference_rule_value'] for r in reps])
    m = {'n_reps': len(reps), 'truth': {'V_uniform5_mean': float(truths.mean()),
          'V_uniform5_range': [float(truths.min()), float(truths.max())],
          'V_heuristic_reference_mean': float(refs.mean())},
          'target_note': 'IPW targets uniform continuation. Naive conditional targets logging association; its uniform-target error includes target mismatch.',
          'ordering': {}}
    for s in range(NS):
        target = np.array([[r['truth']['uniform_blips'][str(s)][a] for a in CORR] for r in reps])
        cell = {}
        for nm in ('naive_cond', 'mediator', 'ipw'):
            M = np.array([[r['blip'].get(s, r['blip'].get(str(s)))[nm][a] for a in CORR] for r in reps])
            ok = np.isfinite(M).all(axis=1)
            if not ok.any():
                continue
            error = M[ok] - target[ok]
            taus = np.array([kendalltau(t, row).statistic for t, row in zip(target[ok], M[ok])])
            cell[nm] = {'target': 'uniform_continuation',
                'mean_kendall_tau': float(np.nanmean(taus)) if np.isfinite(taus).any() else None,
                'P_top_arm_correct': float(np.mean(M[ok].argmax(1) == target[ok].argmax(1))),
                'bias': dict(zip(CORR, error.mean(0).tolist())),
                'rmse': dict(zip(CORR, np.sqrt((error**2).mean(0)).tolist())),
                'n_usable_reps': int(ok.sum())}
            if nm == 'naive_cond':
                own = np.array([[r['truth']['logging_association'][str(s)][a] for a in CORR] for r in reps])
                cell[nm]['bias_against_own_logging_target'] = dict(zip(CORR, (M[ok]-own[ok]).mean(0).tolist()))
        m['ordering']['s%d' % s] = cell
    m['value'] = {}
    for nm, key in (('gcomp', 'v_gcomp'), ('ipw', 'v_ipw'), ('dr', 'v_dr')):
        est = np.array([r[key] if nm == 'gcomp' else r[key][0] for r in reps])
        err = est - truths
        mm = {'mean': float(est.mean()), 'bias': float(err.mean()),
              'bias_mcse': float(err.std(ddof=1)/np.sqrt(len(reps))),
              'rmse': float(np.sqrt((err**2).mean())), 'sd': float(est.std(ddof=1))}
        if nm != 'gcomp':
            coverage = np.mean([r[key][2] <= r['truth']['value'] <= r[key][3] for r in reps])
            mm.update(mean_se=float(np.mean([r[key][1] for r in reps])),
                      coverage_95=float(coverage), coverage_mcse=float(np.sqrt(coverage*(1-coverage)/len(reps))))
        m['value'][nm] = mm
    vals = np.array([r['learned_rule_value'] for r in reps])
    m['decision'] = {'reference_is_optimal': False,
        'mean_V_of_learned_rule': float(vals.mean()),
        'mean_V_heuristic_reference': float(refs.mean()),
        'mean_learned_minus_reference': float((vals-refs).mean()),
        'note': 'Exact value of fitted compressed-state heuristic, not regret to an optimum.'}
    m['n_mislabelled_mean'] = float(np.mean([r['n_mislabelled'] for r in reps]))
    return m


def seed_jobs(reps, workers, base):
    """Exactly reps distinct seeds, independent of worker count."""
    if reps < 2 or workers < 1:
        raise ValueError('require reps >= 2 and workers >= 1')
    return np.array_split(np.arange(base, base+reps), min(workers, reps))


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
    root.mkdir(parents=True, exist_ok=False)
    (root / 'grid_manifest.json').write_text(json.dumps({
        'created_utc': stamp, 'reps_per_cell': a.reps, 'seed_base': a.seed_base,
        'workers': a.workers, 'code_sha256': code_sha256(),
        'python': sys.version.split()[0], 'platform': platform.platform(),
        'cells': {n: CELLS[n] for n in names},
        'schema': 'corrected-e0-v2',
        'note': 'Actual replicate template mixture truth; known behavior scores; compressed-state fitted Q. Original E0 results preserved.',
    }, indent=2))
    for ci, name in enumerate(names):
        cfg = CELLS[name]
        outdir = root / name
        outdir.mkdir(exist_ok=True)
        cell_base = a.seed_base + 1_000_000 * list(CELLS).index(name)
        jobs = [(int(seeds[0]), len(seeds), cfg) for seeds in seed_jobs(a.reps, a.workers, cell_base)]
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            reps = [r for c in ex.map(chunk, jobs) for r in c]
        (outdir / 'replicates.json').write_text(json.dumps(reps, indent=2))
        el = time.time() - t0
        mm = metrics(reps, cfg)
        mm['elapsed_seconds'] = round(el, 1)
        mm['seconds_per_rep'] = round(el / max(len(reps), 1), 4)
        mm['cell'] = name
        mm['config'] = cfg
        (outdir / 'metrics.json').write_text(json.dumps(mm, indent=2))
        print('%-18s R=%4d %6.1fs | DR bias %+.4f cov %.3f | learned-reference %+.4f'
              % (name, len(reps), el, mm['value']['dr']['bias'],
                 mm['value']['dr']['coverage_95'], mm['decision']['mean_learned_minus_reference']), flush=True)
    print('\nwrote', root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
