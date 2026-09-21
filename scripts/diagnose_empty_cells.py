#!/usr/bin/env python3
"""Frozen, reused-seed sensitivity to absent-cell fallback; no new efficacy data."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/e0'))
from simulator import simulate, kernel, make_beh, UNIF5
from estimators import fit_q, dr_scores
from run_grid import CELLS


def array_fit(d, train, population_q=None):
    """Original recursion, except optional oracle filling of ALL absent cells."""
    n, T = d['elig'].shape
    mask = np.zeros(n, bool)
    mask[train] = True
    last = np.max(np.where(d['elig'], np.arange(T), -1), axis=1)
    tables = np.zeros((T, 4, 5))
    counts = np.zeros((T, 4, 5), int)
    roots = np.zeros_like(counts)
    nextv = np.zeros(n)
    for t in reversed(range(T)):
        m = d['elig'][:, t] & mask
        y = np.where(last == t, d['Y'], nextv)
        for a in range(5):
            ma = m & (d['A'][:, t] == a)
            fallback = y[ma].mean() if ma.any() else (y[m].mean() if m.any() else 0.)
            for s in range(4):
                cell = ma & (d['S'][:, t] == s)
                counts[t, s, a] = cell.sum()
                roots[t, s, a] = np.unique(d['task'][cell]).size
                tables[t, s, a] = (y[cell].mean() if cell.any() else
                    fallback if population_q is None else population_q[t, s, a])
        nextv = np.zeros(n)
        active = d['elig'][:, t]
        nextv[active] = tables[t, d['S'][active, t]] @ UNIF5
    return nextv, tables, counts, roots


def table_dr(d, tables):
    """Same sequential correction on table fits; independently parity tested."""
    n, T = d['elig'].shape
    last = np.max(np.where(d['elig'], np.arange(T), -1), axis=1)
    v = np.zeros((n, T + 1)); q = np.zeros((n, T)); reward = np.zeros((n, T))
    ratio = np.ones((n, T))
    for t in range(T):
        m = d['elig'][:, t]
        qs = tables[t, d['S'][m, t]]
        v[m, t] = qs @ UNIF5
        q[m, t] = qs[np.arange(m.sum()), d['A'][m, t]]
        reward[last == t, t] = d['Y'][last == t]
        ratio[m, t] = UNIF5[d['A'][m, t]] / d['B'][m, t]
    return v[:, 0] + np.sum(np.cumprod(ratio, axis=1) * d['elig'] * (reward + v[:, 1:] - q), axis=1)


def digest_arrays(d, keys):
    h = hashlib.sha256()
    for key in keys:
        a = np.ascontiguousarray(d[key])
        h.update(key.encode()); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def replay(seed, old, pop):
    cfg = CELLS['FAIL_positivity']; rng = np.random.default_rng(seed)
    d = simulate(cfg['n_tasks'], cfg['runs'], cfg['T'], kernel(cfg['cmult']),
        make_beh(cfg['kappa'], cfg['floor'], cfg['gz']), rng,
        mislabel=cfg['mislabel'], template_sd=cfg['template_sd'], cmult=cfg['cmult'])
    # Exactly the old RNG consumption order; instrumentation below draws nothing.
    fold = rng.permutation(np.arange(cfg['n_tasks']) % 3)[d['task']]
    pred = {k: np.zeros(len(d['Y'])) for k in ['plugin', 'dr', 'oracle_fill_plugin', 'oracle_fill_dr']}
    cells = []; max_parity = 0.
    for k in range(3):
        train = np.flatnonzero(fold != k); test = fold == k
        Q, fb, original = fit_q(d, cfg['T'], UNIF5, idx=train)
        original_dr = dr_scores(d, cfg['T'], UNIF5, Q, fb)
        v, table, count, roots = array_fit(d, train)
        max_parity = max(max_parity, float(np.max(np.abs(v-original))),
                        float(np.max(np.abs(table_dr(d, table)-original_dr))))
        if max_parity > 1e-10:
            raise ValueError(f'Independent array parity failed: {max_parity}')
        ov, ot, _, _ = array_fit(d, train, pop)
        pred['plugin'][test] = original[test]; pred['dr'][test] = original_dr[test]
        pred['oracle_fill_plugin'][test] = ov[test]
        pred['oracle_fill_dr'][test] = table_dr(d, ot)[test]
        exposure = []
        for t in range(cfg['T']):
            m = test & d['elig'][:, t]
            exposure.append(float(((count[t, d['S'][m, t]] == 0) @ UNIF5).mean()) if m.any() else None)
        cells.append(dict(fold=k, episode_counts=count.tolist(), root_counts=roots.tolist(),
                          target_action_mass_on_empty_cells_among_eligible_eval=exposure))
    estimates = {k: float(v.mean()) for k, v in pred.items()}
    discrepancy = max(abs(estimates[k]-old[k]) for k in ['plugin', 'dr'])
    if discrepancy > 1e-10:
        raise ValueError(f'Archived estimate mismatch: {discrepancy}')
    estimates['population_q_initial'] = float((pop[0, d['S'][:, 0]] @ UNIF5).mean())
    return dict(seed=seed, truth=old['truth'], estimates=estimates, cells=cells,
        reproduced_max_error=discrepancy, array_parity_max_error=max_parity,
        data_hash=digest_arrays(d, ['task','e','z','S','A','B','elig','Y']),
        fold_hash=digest_arrays({'fold':fold}, ['fold']))


def mc(x):
    x = np.asarray(x); mean = float(x.mean()); se = float(x.std(ddof=1)/np.sqrt(len(x)))
    return dict(mean=mean, mcse=se, approximate_mc_interval95=[mean-1.96*se, mean+1.96*se])


def summarize(rows):
    truth = np.array([r['truth'] for r in rows]); errors = {}
    for k in rows[0]['estimates']:
        e = np.array([r['estimates'][k] for r in rows])-truth
        errors[k] = e
    result = {k: dict(bias=mc(e), rmse=float(np.sqrt(np.mean(e**2)))) for k,e in errors.items()}
    paired = {}
    for kind in ['plugin', 'dr']:
        old, new = errors[kind], errors['oracle_fill_'+kind]
        paired[kind] = dict(estimate_change=mc(new-old), squared_error_change=mc(new**2-old**2))
    counts = np.array([[f['episode_counts'] for f in r['cells']] for r in rows])
    roots = np.array([[f['root_counts'] for f in r['cells']] for r in rows])
    exposure = np.array([[f['target_action_mass_on_empty_cells_among_eligible_eval'] for f in r['cells']] for r in rows])
    return dict(estimator_diagnostics=result, paired_oracle_fill_minus_original=paired,
        sparsity=dict(exposure_distribution='logger-generated eligible held-out histories; equal averaging over folds and seeds, not target history occupancy', total_fold_cells=int(counts.size), empty_fold_cells=int((counts==0).sum()),
        one_to_four_episode_cells=int(((counts>0)&(counts<5)).sum()),
        one_to_four_root_cells=int(((roots>0)&(roots<5)).sum()),
        mean_empty_fraction_by_stage=(counts==0).mean(axis=(0,1,3,4)).tolist(),
        mean_target_mass_exposure_by_stage=exposure.mean(axis=(0,1)).tolist()))


def main():
    start = time.perf_counter()
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    config_path = 'experiments/e0/sparse_cell_config_v1.json'
    config = json.loads((ROOT/config_path).read_text())
    hashes = dict(config['source_hashes'])
    for path in [config_path, 'scripts/diagnose_empty_cells.py', 'tests/test_empty_cells.py',
                 'docs/sparse_cell_diagnostic_plan_20260921.md']:
        hashes[path] = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    for path, expected in hashes.items():
        actual = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        frozen = hashlib.sha256(subprocess.check_output(['git','show',f'{revision}:{path}'], cwd=ROOT)).hexdigest()
        if expected != actual or actual != frozen:
            raise ValueError(f'Source not pinned at freeze: {path}')
    a.out.mkdir(parents=True, exist_ok=False)
    manifest = dict(freeze_revision=revision, source_hashes=hashes, config=config,
        created_utc=datetime.now(timezone.utc).isoformat(), python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
        classification='reused-seed synthetic diagnostic; population-Q interventions unavailable in practice')
    (a.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    old = {r['seed']:r for r in json.loads((ROOT/'results/matched_estimator_diagnosis_20260920/replicates.json').read_text()) if r['cell']==config['cell']}
    pop = np.array(next(r for r in json.loads((ROOT/'results/history_compression_20260921.json').read_text())['rows'] if r['cell']==config['cell'])['q_tables'])
    rows = []; status = 'complete'; failure = None
    with (a.out/'replicates.jsonl').open('x') as f:
        for seed in config['seeds']:
            if time.perf_counter()-start > config['resource_cap']['process_seconds']-5:
                status = 'incomplete_time_cap'; break
            try:
                r = replay(seed, old[seed], pop)
            except Exception as exc:
                status = 'failed_reproduction_or_execution'; failure = repr(exc); break
            f.write(json.dumps(r)+'\n'); f.flush(); rows.append(r)
            if sum(p.stat().st_size for p in a.out.iterdir()) > config['resource_cap']['output_bytes']-65536:
                status = 'incomplete_output_cap'; break
    report = dict(status=status, failure=failure, completed=len(rows), planned=len(config['seeds']),
        summary=summarize(rows) if len(rows)>1 else None,
        max_reproduction_error=max((r['reproduced_max_error'] for r in rows), default=None),
        max_array_parity_error=max((r['array_parity_max_error'] for r in rows), default=None),
        usage=dict(elapsed_seconds=time.perf_counter()-start, workers=1, receiver_calls=0,
                   receiver_tokens=0, candidate_executions=0, paid_usd=0),
        interpretation='Only a complete run supports the frozen 80-seed comparison. No efficacy or deployable-method claim.')
    (a.out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if status != 'complete':
        raise SystemExit(1)

if __name__ == '__main__':
    main()
