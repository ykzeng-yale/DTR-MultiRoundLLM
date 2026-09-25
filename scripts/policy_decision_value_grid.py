"""Exact stylized family-contrast decision probabilities; no model or benchmark calls."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import time
from pathlib import Path

import numpy as np


PLAN = Path("docs/policy_decision_value_grid_plan_20260925.md")
OUTPUT = Path("results/policy_decision_value_grid_20260925.json")
N_VALUES = (198, 544)
Q_VALUES = (0.2, 0.4, 0.6)
DELTA_VALUES = (0.05, 0.10, 0.20)
GAIN = 0.05


def distribution(n: int, q: float, delta: float) -> np.ndarray:
    assert n >= 0 and abs(delta) <= q <= 1
    p_minus, p_zero, p_plus = (q - delta) / 2, 1 - q, (q + delta) / 2
    pmf = np.array([1.0])
    for _ in range(n):
        next_pmf = np.zeros(len(pmf) + 2)
        next_pmf[:-2] += p_minus * pmf
        next_pmf[1:-1] += p_zero * pmf
        next_pmf[2:] += p_plus * pmf
        pmf = next_pmf
    return pmf


def self_check() -> None:
    for n in (0, 1, 2, 3, 4):
        q, delta = 0.4, 0.1
        p = ((q - delta) / 2, 1 - q, (q + delta) / 2)
        brute = np.zeros(2 * n + 1)
        for path in itertools.product(range(3), repeat=n):
            total = sum(x - 1 for x in path)
            brute[total + n] += math.prod(p[x] for x in path)
        assert np.max(np.abs(distribution(n, q, delta) - brute)) < 1e-13


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit(f"Refusing to overwrite {OUTPUT}")
    start = time.perf_counter()
    self_check()
    rows = []
    for n, q, delta in itertools.product(N_VALUES, Q_VALUES, DELTA_VALUES):
        pmf = distribution(n, q, delta)
        sums = np.arange(-n, n + 1)
        radius = math.sqrt(2 * math.log(80) / n)
        benefit = float(pmf[sums / n - radius > GAIN].sum())
        futility = float(pmf[sums / n + radius < GAIN].sum())
        inconclusive = float(pmf.sum() - benefit - futility)
        actual_mean = float(np.dot(sums, pmf))
        actual_var = float(np.dot((sums - n * delta) ** 2, pmf))
        assert abs(pmf.sum() - 1) < 1e-11
        assert abs(actual_mean - n * delta) < 1e-9
        assert abs(actual_var - n * (q - delta * delta)) < 1e-8
        assert abs(benefit + futility + inconclusive - 1) < 1e-11
        assert min(benefit, futility, inconclusive) >= -1e-11
        rows.append({
            "n_hypothetical_families": n,
            "discordance_q": q,
            "true_mean_delta": delta,
            "radius": radius,
            "probability_useful_benefit": benefit,
            "probability_useful_gain_futility": futility,
            "probability_inconclusive": inconclusive,
        })
    elapsed = time.perf_counter() - start
    assert elapsed < 60
    payload = {
        "classification": "exact known-truth stylized numerical planning; not a real policy, receiver result, forecast or trial power guarantee",
        "freeze_commit": args.freeze_commit,
        "plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "elapsed_wall_seconds": elapsed,
        "self_check": "brute force n=0..4 and finite-n probability/moment checks passed",
        "rows": rows,
        "model_calls": 0,
        "tokens": 0,
        "benchmark_program_executions": 0,
        "synthetic_draws": 0,
        "paid_usd": 0,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
