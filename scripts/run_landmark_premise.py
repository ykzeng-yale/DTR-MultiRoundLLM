#!/usr/bin/env python3
"""Prespecified synthetic policy-premise diagnostic; never calls an LLM."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np

CELLS = ("homogeneous_null", "qualitative_interaction", "weak_interaction", "unavailable_signal")
N_TRAIN = N_TEST = 800
REPLICATIONS = 300
SEED = 2026092100


def means(cell, x, z):
    if cell == "homogeneous_null":
        return np.full((len(x), 2), .65)
    state = z if cell == "unavailable_signal" else x
    high, low = (.64, .56) if cell == "weak_interaction" else (.8, .4)
    return np.where(state[:, None] == np.arange(2)[None, :], high, low)


def public_q(cell):
    if cell == "homogeneous_null":
        return np.full((2, 2), .65)
    if cell == "unavailable_signal":
        return np.full((2, 2), .6)
    return means(cell, np.arange(2), np.zeros(2, dtype=int))


def fit_policy(x, a, y):
    q = np.full((2, 2), .5)
    fixed = np.full(2, .5)
    for arm in range(2):
        if np.any(a == arm):
            fixed[arm] = np.mean(y[a == arm])
        for state in range(2):
            mask = (x == state) & (a == arm)
            if np.any(mask):
                q[state, arm] = np.mean(y[mask])
    return q.argmax(axis=1), int(fixed.argmax())


def replicate(cell, seed, n_train=N_TRAIN, n_test=N_TEST):
    rng = np.random.default_rng(seed)
    x, z, a = [rng.integers(0, 2, n_train) for _ in range(3)]
    train_y = rng.binomial(1, means(cell, x, z)[np.arange(n_train), a])
    policy, baseline = fit_policy(x, a, train_y)
    q = public_q(cell)
    population_value = float(q[np.arange(2), policy].mean())
    baseline_value = float(q[:, baseline].mean())
    oracle_value = float(q.max(axis=1).mean())
    true_delta = population_value - baseline_value
    x, z = [rng.integers(0, 2, n_test) for _ in range(2)]
    p = means(cell, x, z)
    # Same four draws support both r analyses, never counted as independent datasets.
    outcomes = rng.binomial(1, p[:, :, None], size=(n_test, 2, 4))
    rows = []
    for r in (1, 4):
        branch_means = outcomes[:, :, :r].mean(axis=2)
        d = branch_means[np.arange(n_test), policy[x]] - branch_means[:, baseline]
        estimate = float(d.mean())
        se = float(d.std(ddof=1) / np.sqrt(n_test))
        lower, upper = estimate - 1.96 * se, estimate + 1.96 * se
        rows.append({"cell": cell, "seed": seed, "branch_repetitions": r,
                     "learned_policy": policy.tolist(), "fixed_comparator": baseline,
                     "true_policy_gain": true_delta, "estimated_policy_gain": estimate,
                     "se": se, "coverage": lower <= true_delta <= upper,
                     "lower_above_zero": lower > 0,
                     "public_oracle_value": oracle_value,
                     "public_oracle_gain": oracle_value - baseline_value,
                     "policy_regret": oracle_value - population_value,
                     "sample_max_value": float(branch_means.max(axis=1).mean()),
                     "sample_max_excess_over_public_oracle": float(branch_means.max(axis=1).mean()) - oracle_value})
    return rows


def summarize(rows):
    out = []
    for cell in CELLS:
        for r in (1, 4):
            selected = [v for v in rows if v["cell"] == cell and v["branch_repetitions"] == r]
            result = {"cell": cell, "branch_repetitions": r, "replications": len(selected)}
            for key in ("true_policy_gain", "estimated_policy_gain", "coverage", "lower_above_zero",
                        "public_oracle_value", "public_oracle_gain", "policy_regret", "sample_max_value",
                        "sample_max_excess_over_public_oracle"):
                v = np.asarray([x[key] for x in selected], dtype=float)
                result[key] = {"mean": float(v.mean()), "mcse": float(v.std(ddof=1) / np.sqrt(len(v)))}
            out.append(result)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    rows = []
    for ci, cell in enumerate(CELLS):
        for b in range(REPLICATIONS):
            rows.extend(replicate(cell, SEED + 10000 * ci + b))
    for name, value in [("replicates.json", rows), ("summary.json", summarize(rows))]:
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
    manifest = {"evidence_type": "synthetic_known_truth", "plan": "docs/landmark_premise_simulation_plan.md",
                "plan_freeze_commit": "4f957af", "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "n_train": N_TRAIN, "n_test": N_TEST, "replications_per_cell": REPLICATIONS,
                "datasets": len(CELLS) * REPLICATIONS, "paired_policy_evaluations": len(rows),
                "branch_repetition_analyses_are_nested": True, "python": platform.python_version(),
                "numpy": np.__version__, "wall_seconds": time.monotonic() - started,
                "llm_calls": 0, "paid_spend_usd": 0,
                "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.glob("*.json")}}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
