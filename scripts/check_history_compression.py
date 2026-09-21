#!/usr/bin/env python3
"""Exact population compressed-regression diagnostic; never samples trajectories."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/e0'))
from simulator import P_E, P_Z, p_s1, kernel, make_beh, true_value  # noqa: E402


def initial_mass():
    return P_E[:, None, None] * np.array([1 - P_Z, P_Z])[None, :, None] * np.stack(
        [p_s1(e) for e in range(len(P_E))])[:, None, :]


def compressed_limit(transitions, behavior, target, horizon):
    """Population limit of state/time tabular sequential regression, no smoothing."""
    if not np.allclose(behavior[0], behavior[1], rtol=0, atol=1e-14):
        raise ValueError('This diagnostic requires gz=0: assignment depends only on observed state.')
    if horizon < 1 or not np.allclose(behavior.sum(axis=-1), 1) or np.any(behavior <= 0):
        raise ValueError('Require positive assignment probabilities and positive horizon.')
    active = [initial_mass()]
    for _ in range(horizon - 1):
        active.append(np.einsum('ezs,zsa,ezsak->ezk', active[-1], behavior[:, :, 1:], transitions[:, :, :, 1:, :]))
    ns, na = transitions.shape[2:4]
    v = (np.arange(ns) == ns - 1).astype(float)
    tables = []
    for t in reversed(range(horizon)):
        q = np.empty((ns, na))
        q[:, 0] = np.arange(ns) == ns - 1
        for s in range(ns):
            for a in range(1, na):
                weights = active[t][:, :, s] * behavior[None, :, s, a]
                q[s, a] = np.sum(weights * (transitions[:, :, s, a, :] @ v)) / weights.sum()
        tables.append(q)
        v = q @ target
    return {
        'value': float(initial_mass().sum(axis=(0, 1)) @ v),
        'q_tables': [q.tolist() for q in reversed(tables)],
        'active_mass_by_stage': [float(m.sum()) for m in active],
    }


def history_oracle(transitions, target, horizon):
    """Posterior recursion on complete synthetic state/action histories, not latent-aware actions."""
    ns, na = transitions.shape[2:4]
    nodes = 0

    def walk(t, state, posterior):
        nonlocal nodes
        nodes += 1
        if t == horizon:
            return float(state == ns - 1)
        value = target[0] * float(state == ns - 1)
        for a in range(1, na):
            if target[a] == 0:
                continue
            for nxt in range(ns):
                joint = posterior * transitions[:, :, state, a, nxt]
                probability = float(joint.sum())
                if probability > 0:
                    value += target[a] * probability * walk(t + 1, nxt, joint / probability)
        return value

    value = 0.0
    mass = initial_mass()
    for s in range(ns):
        probability = float(mass[:, :, s].sum())
        value += probability * walk(0, s, mass[:, :, s] / probability)
    return {'value': float(value), 'history_tree_nodes': nodes}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    config_path = ROOT / 'experiments/e0/history_compression_config_v1.json'
    config = json.loads(config_path.read_text())
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    paths = list(config['source_hashes']) + [str(config_path.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT)),
                                           'docs/history_compression_plan_20260921.md', 'tests/test_history_compression.py']
    hashes = {}
    for name in paths:
        data = (ROOT / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if name in config['source_hashes'] and digest != config['source_hashes'][name]:
            raise ValueError('Changed pinned input: ' + name)
        committed = subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
        if data != committed:
            raise ValueError('Freeze must contain exact running source: ' + name)
        hashes[name] = digest
    if config['gz'] != 0 or config['horizon'] != 3:
        raise ValueError('Unexpected frozen scope')
    started = time.perf_counter()
    target = np.asarray(config['target'])
    transitions = kernel(config['cmult'])
    truth = true_value(transitions, target, config['horizon'])
    full = history_oracle(transitions, target, config['horizon'])
    if abs(full['value'] - truth) > 1e-12:
        raise ValueError('Full-history oracle differs from independent DP truth')
    rows = []
    for cell in config['cells']:
        behavior = make_beh(cell['kappa'], cell['floor'], config['gz'])
        value = compressed_limit(transitions, behavior, target, config['horizon'])
        rows.append(dict(cell=cell['name'], **value, truth=truth,
                         compression_bias=value['value'] - truth, full_history_value=full['value']))
    elapsed = time.perf_counter() - started
    if elapsed > config['resource_cap']['wall_seconds']:
        raise TimeoutError('Exact calculation exceeded cap')
    report = {
        'created_utc': datetime.now(timezone.utc).isoformat(), 'freeze_revision': revision,
        'source_hashes': hashes, 'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__,
        'config': config, 'full_history_reference': full, 'rows': rows,
        'usage': {'calculation_seconds': elapsed, 'receiver_calls': 0, 'receiver_tokens': 0,
                  'paid_usd': 0, 'sampled_trajectories': 0, 'fitted_models': 0},
        'scope': 'Exact synthetic population diagnostic; not fitted full-history validation, finite-sample inference or prompt efficacy.'
    }
    encoded = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if len(encoded.encode()) > config['resource_cap']['output_bytes']:
        raise ValueError('Output cap exceeded')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        f.write(encoded)
    print(json.dumps({'rows': [{k:r[k] for k in ('cell','value','truth','compression_bias')} for r in rows], 'usage': report['usage']}))


if __name__ == '__main__':
    main()
