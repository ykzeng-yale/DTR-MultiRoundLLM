#!/usr/bin/env python3
"""Reconcile stored diagnostic records; no fitting, simulation or model execution."""
import argparse
import hashlib
import json
import math
import statistics as stats
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    started = time.perf_counter()
    checks = []
    inputs = {}

    def read(name, jsonl=False):
        raw = (ROOT / name).read_bytes()
        inputs[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        return [json.loads(line) for line in raw.splitlines()] if jsonl else json.loads(raw)

    def check(name, condition):
        if not condition:
            raise ValueError(name)
        checks.append(name)

    def close(name, actual, expected):
        check(name, math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12))

    def moments(values):
        mean = stats.fmean(values)
        se = stats.stdev(values) / math.sqrt(len(values))
        return {'mean': mean, 'se': se, 'ci95': [mean - 1.96 * se, mean + 1.96 * se]}

    base = 'results/mechanism_diagnosis_20260920/'
    roots = read(base + 'root_scores.jsonl', True)
    source = read(base + 'summary.json')
    check('root_receiver_records', len(roots) == 1122)
    check('unique_root_receiver_records', len({(r['uid'], r['model']) for r in roots}) == 1122)
    repair = {}
    for receiver, archived in source['by_receiver'].items():
        rows = [r for r in roots if r['model'] == receiver]
        check(receiver + ':root_count', len(rows) == archived['n_tasks'] == 561)
        table = {}
        for key in ('initial_success', 'repair', 'degradation', 'net_repair_gain',
                    'bon3_net_gain', 'augmented_calls', 'bon3_calls'):
            table[key] = stats.fmean(r[key] for r in rows)
            close(receiver + ':' + key, table[key], archived['means'][key]['mean'])
        for r in rows:
            close(receiver + ':' + r['uid'] + ':decomposition',
                  r['repair'] - r['degradation'], r['net_repair_gain'])
        contrast = moments([r['net_repair_gain'] - r['bon3_net_gain'] for r in rows])
        expected = archived['net_repair_minus_bon3_net']
        for key in ('mean', 'se'):
            close(receiver + ':contrast:' + key, contrast[key], expected[key])
        for i in range(2):
            close(receiver + ':contrast_endpoint:' + str(i), contrast['ci95'][i], expected['ci95'][i])
        table['repair_minus_resampling'] = contrast
        repair[receiver] = table

    base = 'results/selection_sensitivity_20260920/'
    fits = read(base + 'fits.json')
    source = read(base + 'summary.json')
    selection = {}
    for receiver, archived in source['split_summary'].items():
        selected = sorted((r for r in fits if r['receiver'] == receiver and r['features'] == 'full'),
                          key=lambda r: r['seed'])
        check(receiver + ':split_seeds', [r['seed'] for r in selected] == list(range(20260920, 20260930)))
        deltas = []
        for fit in selected:
            prefix = receiver + ':' + str(fit['seed'])
            rows = fit['per_task']
            check(prefix + ':heldout_count', len(rows) == fit['n_evaluation_roots'] == 225)
            check(prefix + ':unique_roots', len({r['task_uid'] for r in rows}) == 225)
            check(prefix + ':training_count', fit['n_training_roots'] == 336)
            for row in rows:
                close(prefix + ':' + row['task_uid'] + ':difference', row['delta'], row['learned'] - row['visible'])
            delta = stats.fmean(r['learned'] - r['visible'] for r in rows)
            close(prefix + ':mean', delta, fit['contrast']['mean'])
            deltas.append(delta)
        actual = {'original': deltas[0], 'median': stats.median(deltas),
                  'minimum': min(deltas), 'maximum': max(deltas),
                  'positive_splits': sum(v > 0 for v in deltas), 'n_splits': len(deltas)}
        for key in ('median', 'minimum', 'maximum', 'positive_splits', 'n_splits'):
            close(receiver + ':split_summary:' + key, actual[key], archived[key])
        selection[receiver] = actual

    base = 'results/matched_estimator_diagnosis_20260920/'
    records = read(base + 'replicates.json')
    source = read(base + 'summary.json')
    check('matched:records', len(records) == source['n_replications'] == 400)
    check('matched:unique_cell_seed', len({(r['cell'], r['seed']) for r in records}) == 400)
    matched = {}
    for cell, archived in source['results'].items():
        rows = [r for r in records if r['cell'] == cell]
        check(cell + ':replicate_count', len(rows) == 80)
        table = {}
        for method in ('plugin', 'dr'):
            errors = [r[method] - r['truth'] for r in rows]
            bias, rmse = stats.fmean(errors), math.sqrt(stats.fmean(e * e for e in errors))
            close(cell + ':' + method + ':bias', bias, archived[method]['bias'])
            close(cell + ':' + method + ':rmse', rmse, archived[method]['rmse'])
            table[method] = {'bias': bias, 'rmse': rmse}
        paired = moments([(r['dr'] - r['truth'])**2 - (r['plugin'] - r['truth'])**2 for r in rows])
        expected = archived['paired_mse_dr_minus_plugin']
        close(cell + ':mse_difference', paired['mean'], expected['mean'])
        close(cell + ':mse_mcse', paired['se'], expected['mcse'])
        for i in range(2):
            close(cell + ':mse_interval:' + str(i), paired['ci95'][i], expected['mc_interval95'][i])
        coverage = stats.fmean(r['dr_interval'][0] <= r['truth'] <= r['dr_interval'][1] for r in rows)
        close(cell + ':coverage', coverage, archived['dr_coverage'])
        table.update(paired_mse_dr_minus_plugin=paired, dr_coverage=coverage)
        matched[cell] = table

    script = Path(__file__).read_bytes()
    result = {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'script_sha256': hashlib.sha256(script).hexdigest(),
        'inputs': inputs, 'checks_passed': len(checks), 'checks': checks,
        'repair': repair, 'selection': selection, 'matched_estimators': matched,
        'usage': {'model_calls': 0, 'model_tokens': 0, 'paid_usd': 0,
                  'candidate_code_executions': 0, 'simulation_or_fit_runs': 0,
                  'elapsed_seconds': time.perf_counter() - started},
        'scope': 'Stored-data arithmetic reconciliation only. Does not repeat raw-log extraction, refit policies, verify family independence or establish efficacy. Use script_sha256 to identify the executed script; source_revision alone may not include working-tree changes.'
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({'output': str(args.output), 'checks_passed': len(checks), 'usage': result['usage']}))


if __name__ == '__main__':
    main()
