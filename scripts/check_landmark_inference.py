#!/usr/bin/env python3
"""Exact finite-law audit of landmark interval exports; no model calls.

Enumerates all binomial counts, using rational probability masses. Interval
endpoints use the actual analyzer's floating-point implementation. This is not
a Monte Carlo experiment or validation of empirical family independence.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def rational(value: Fraction) -> dict:
    return {"fraction": str(value), "decimal": float(value)}


def contains(interval, target) -> bool:
    return interval[0] <= float(target) <= interval[1]


def binomial_audit() -> dict:
    n, p = 24, Fraction(9, 10)
    truth = 2*p - 1
    families = list(range(n))
    coverage = {name: Fraction(0) for name in (
        "exploratory_normal_95", "bounded_single_endpoint_95",
        "bounded_endpoint_bonferroni_10", "bounded_globally_dependent_missingness_95")}
    total = Fraction(0)
    rows = []
    for k in range(n+1):
        mass = math.comb(n, k) * p**k * (1-p)**(n-k)
        total += mass
        values = [1.] * k + [-1.] * (n-k)
        intervals = {
            "exploratory_normal_95": paired_summary(values, families)["ci95"],
            "bounded_single_endpoint_95": bounded_family_interval(
                values, values, families, (-1, 1), alpha=.05)["interval"],
            "bounded_endpoint_bonferroni_10": bounded_family_interval(
                values, values, families, (-1, 1), alpha=.05/REPORTED_ENDPOINTS)["interval"],
        }
        # A global outcome-selected observation rule: reveal everything only
        # when all outcomes are +1; otherwise withhold every outcome. Missingness
        # is dependent across families, but complete-data outcomes remain iid.
        lower, upper = (values, values) if k == n else ([-1.]*n, [1.]*n)
        intervals["bounded_globally_dependent_missingness_95"] = bounded_family_interval(
            lower, upper, families, (-1, 1), alpha=.05)["interval"]
        covered = {name: contains(ci, truth) for name, ci in intervals.items()}
        for name, ok in covered.items():
            coverage[name] += mass * ok
        rows.append({"number_of_positive_contrasts": k, "probability": rational(mass),
                     "intervals": intervals, "covers_truth": covered})
    assert total == 1
    assert coverage["exploratory_normal_95"] < Fraction(95, 100)
    assert coverage["bounded_single_endpoint_95"] >= Fraction(95, 100)
    assert coverage["bounded_endpoint_bonferroni_10"] >= Fraction(995, 1000)
    assert coverage["bounded_globally_dependent_missingness_95"] >= Fraction(95, 100)
    assert rows[-1]["intervals"]["exploratory_normal_95"] == [1., 1.]
    assert p**n > Fraction(5, 100)
    return {"independent_families": n, "positive_contrast_probability": rational(p),
            "true_expected_contrast": rational(truth), "complete_count_enumeration": n+1,
            "total_probability": rational(total),
            "all_positive_failure_event_probability": rational(p**n),
            "coverage": {k: rational(v) for k, v in coverage.items()},
            "multiplicity_note": "The .005 endpoint calculation checks its marginal coverage; simultaneous ten-endpoint validity follows by union bound, not from assuming endpoint independence.",
            "count_results": rows}


def weights_and_missingness_audit() -> dict:
    values = [1.]*9 + [-1.]
    unequal = bounded_family_interval(values, values, ["large"]*9 + ["small"], (-1, 1))
    assert math.isclose(unequal["effective_families"], 1/(.9**2+.1**2))
    assert math.isclose(unequal["radius"], math.sqrt(2*math.log(40)*(.9**2+.1**2)))
    assert unequal["interval"] == [-1, 1]

    base = bounded_family_interval([.5]*24, [.5]*24, list(range(24)), (0, 1))
    repeated = bounded_family_interval([.5]*120, [.5]*120,
                                       [g for g in range(24) for _ in range(5)], (0, 1))
    assert base["radius"] == repeated["radius"]
    contrast = bounded_family_interval([.5]*24, [.5]*24, list(range(24)), (-1, 1))
    assert math.isclose(contrast["radius"], 2*base["radius"])

    full_missing = bounded_family_interval([-1.]*24, [1.]*24, list(range(24)), (-1, 1))
    no_roots = bounded_family_interval([], [], [], (-1, 1))
    failed_gate = bounded_family_interval([0.], [1.], ["a"], (0, 1), allow=False)
    assert full_missing["interval"] == [-1, 1]
    assert no_roots["interval"] is None and failed_gate["interval"] is None
    return {"unequal_family_sizes": [9, 1], "equal_root_observed_mean": .8,
            "equal_family_observed_mean": 0., "unequal_weight_reference": unequal,
            "equal_24_family_quality_radius": base["radius"],
            "equal_24_family_contrast_radius": contrast["radius"],
            "duplicating_all_roots_five_times_within_family_preserves_radius": True,
            "all_missing_reference": full_missing,
            "no_roots_reference": no_roots, "failed_identity_reference": failed_gate}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    global REPORTED_ENDPOINTS, bounded_family_interval, paired_summary
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Refusing to overwrite {args.output}")
    sources = [Path(__file__).resolve(), ROOT / "experiments/landmark/analyze.py",
               ROOT / "experiments/landmark/collect.py"]
    before = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    # Hash before loading the implementation, then verify unchanged afterward.
    from experiments.landmark.analyze import (
        REPORTED_ENDPOINTS, bounded_family_interval, paired_summary,
    )
    checks = {"binomial_coverage": binomial_audit(),
              "weights_and_missingness": weights_and_missingness_audit()}
    after = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    if before != after:
        raise RuntimeError("Audited source changed during execution; output not written")
    result = {"evidence_type": "exact_finite_law_inference_checks",
              "all_assertions_passed": True,
              "source_sha256": after,
              "source_state": "Executed working-tree sources; recorded hashes are authoritative even when files are not committed.",
              "git_head_for_context": subprocess.check_output(
                  ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "python": platform.python_version(), "dependencies": "Python standard library only",
              "model_calls": 0, "paid_spend_usd": 0,
              "checks": checks}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"output": str(args.output), "all_assertions_passed": True,
                      "coverage": checks["binomial_coverage"]["coverage"],
                      "source_sha256": after}, indent=2))


if __name__ == "__main__":
    main()
