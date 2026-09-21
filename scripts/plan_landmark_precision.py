#!/usr/bin/env python3
"""Design arithmetic from the reviewed family bound; no outcomes or model calls.

Uses the current analyzer without changing its inference. Hypothetical singleton
families do not establish independence of any actual benchmark roster.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark.analyze import bounded_family_interval, REPORTED_ENDPOINTS
from experiments.landmark.collect import file_sha


def required_equal_families(half_width, alpha):
    if not math.isfinite(half_width) or not 0 < half_width < 2 or not 0 < alpha < 1:
        raise ValueError("Need a positive contrast half-width below 2 and valid alpha")
    # Contrast support [-1,1]; solve the existing radius for equally weighted families.
    return math.ceil(2 * math.log(2/alpha) / half_width**2)


def scenario(name, family_sizes, alpha, center=0.0):
    if not family_sizes or any(type(n) is not int or n < 1 for n in family_sizes):
        raise ValueError("Need fixed positive family sizes")
    families = [str(g) for g,n in enumerate(family_sizes) for _ in range(n)]
    n = len(families)
    ref = bounded_family_interval([center]*n, [center]*n, families, (-1,1), alpha)
    best = bounded_family_interval([1]*n, [1]*n, families, (-1,1), alpha)
    return {"name": name, "n_roots": n, "family_sizes": family_sizes,
        "alpha": alpha, "family_independence_is_assumed_not_verified": True,
        "effective_families": ref["effective_families"], "radius": ref["radius"],
        "hypothetical_zero_contrast_interval": ref["interval"],
        "hypothetical_all_positive_interval": best["interval"],
        "all_arm_calls_at_two_repeats": 7*n,
        "completion_token_reservation_at_512": 7*n*512}


def report():
    started = time.monotonic()
    scenarios = []
    for alpha in (.05, .05/REPORTED_ENDPOINTS):
        for name, sizes in [("current_seven_shared_unresolved_group", [7]),
                            ("hypothetical_seven_independent_roots", [1]*7),
                            ("hypothetical_24_independent_roots", [1]*24),
                            ("hypothetical_24_roots_six_equal_families", [4]*6),
                            ("hypothetical_24_roots_one_dominant_family", [19,1,1,1,1,1]),
                            ("hypothetical_242_independent_roots", [1]*242),
                            ("hypothetical_544_independent_roots", [1]*544)]:
            scenarios.append(scenario(name, sizes, alpha))
    precision = []
    for alpha in (.05, .05/REPORTED_ENDPOINTS):
        for half_width in (.10,.05,.03):
            n = required_equal_families(half_width, alpha)
            precision.append({"alpha": alpha, "requested_half_width": half_width,
                "sufficient_equal_independent_families_for_this_bound": n,
                "all_arm_calls_if_one_root_per_family_two_repeats": 7*n,
                "meaning": "sufficient radius condition, not a necessary sample size or power guarantee"})
    return {"version": "landmark-precision-planning-v1", "evidence_class": "deterministic design arithmetic",
        "source_sha256": {"planner": file_sha(__file__),
            "analyzer": file_sha(ROOT/"experiments/landmark/analyze.py")},
        "scope": "Existing fixed-weight independent-family expected contrast; complete outcomes; frozen policy and fixed analysis time",
        "limitations": ["No empirical variance or actual outcome supplied", "No family independence certified",
            "No power or infeasibility theorem", "Repeated continuations do not multiply family count",
            "This conservative bound ignores potential variance reduction from seed replication",
            "Displayed call counts describe all-arm development design, not a released policy trial",
            "Requested half-widths are planning scenarios, not chosen useful-benefit thresholds"],
        "scenarios": scenarios, "precision_targets": precision,
        "accounting": {"model_calls":0, "model_tokens":0, "benchmark_executions":0,
            "external_spend_usd":0, "wall_seconds":time.monotonic()-started}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve completed planning reports; choose a new file")
    data = report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as f:
        json.dump(data,f,indent=2)
        f.write("\n")
    print(json.dumps({"scenarios":len(data["scenarios"]), "precision_targets":len(data["precision_targets"]),
                      "wall_seconds":data["accounting"]["wall_seconds"]}))


if __name__ == "__main__":
    main()
