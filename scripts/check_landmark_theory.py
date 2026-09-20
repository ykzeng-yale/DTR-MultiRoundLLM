#!/usr/bin/env python3
"""Exact finite-law checks for landmark prompt-choice theory; no model calls.

All probability arithmetic uses Fraction. This is a mathematical audit, not
Monte Carlo evidence, a fitted learner experiment, or a coverage study.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import hashlib
from itertools import product
import json
from math import comb
from pathlib import Path
import platform


def binomial_law(r: int, p: F) -> list[tuple[F, F]]:
    """Distribution of an r-replicate Bernoulli sample mean."""
    return [(F(k, r), comb(r, k) * p**k * (1 - p)**(r - k)) for k in range(r + 1)]


def max_mean_value(p0: F, p1: F, r: int) -> F:
    return sum(max(y0, y1) * w0 * w1
               for y0, w0 in binomial_law(r, p0)
               for y1, w1 in binomial_law(r, p1))


def ate_and_personalization() -> dict:
    q = ((F(4, 5), F(2, 5)), (F(2, 5), F(4, 5)))
    marginal = [sum(row[a] for row in q) / 2 for a in (0, 1)]
    oracle = sum(max(row) for row in q) / 2
    delta = [row[1] - row[0] for row in q]
    identity = (sum(abs(d) for d in delta) / 2 - abs(marginal[1] - marginal[0])) / 2
    assert marginal == [F(3, 5), F(3, 5)]
    assert oracle - max(marginal) == identity == F(1, 5)
    return {"marginal_arm_values": marginal, "ate": marginal[1] - marginal[0],
            "public_oracle": oracle, "personalization_gain": identity,
            "homogeneous_large_ate_but_no_personalization": {
                "ate": F(4, 5) - F(2, 5), "best_fixed_and_oracle": F(4, 5),
                "personalization_gain": F(0)}}


def oracle_gaps() -> dict:
    null = {str(r): max_mean_value(F(13, 20), F(13, 20), r) for r in (1, 2, 4, 8)}
    latent = {str(r): max_mean_value(F(4, 5), F(2, 5), r) for r in (1, 2, 4, 8)}
    assert null["1"] == F(351, 400)  # .8775, not .65.
    assert all(v > F(13, 20) for v in null.values())
    assert latent["1"] == F(22, 25)  # .88, not public .6.
    assert all(v >= F(4, 5) for v in latent.values())
    return {"homogeneous_null": {"public_and_checkpoint_oracle": F(13, 20),
                                 "expected_sample_max": null},
            "unavailable_signal": {"public_oracle": F(3, 5),
                                   "checkpoint_oracle": F(4, 5),
                                   "irreducible_information_gap": F(1, 5),
                                   "expected_sample_max": latent}}


def within_root_label_leakage() -> dict:
    """Fresh evaluation seeds do not remove learning on evaluation-root labels."""
    value = F(0)
    for p0, p1 in ((F(4, 5), F(2, 5)), (F(2, 5), F(4, 5))):
        for y0, w0 in binomial_law(1, p0):
            for y1, w1 in binomial_law(1, p1):
                selected_mean = p1 if y1 > y0 else p0
                value += w0 * w1 * selected_mean / 2
    assert value == F(17, 25)
    assert value > F(3, 5)
    return {"preintervention_public_oracle": F(3, 5),
            "use_test_root_labels_then_fresh_evaluation": value,
            "extra_information_gain": value - F(3, 5),
            "interpretation": "Different information/cost policy; not a valid prefix-only selector."}


def randomization_identity() -> dict:
    q = ((F(4, 5), F(2, 5)), (F(2, 5), F(4, 5)))
    # Assign action one with probability .9 in state zero and .2 in state one.
    e1 = (F(9, 10), F(1, 5))
    # Frozen personalized policy picks action zero in state zero, one in state one.
    selected = (0, 1)
    ipw = F(0)
    policy_mass = F(0)
    action_mass = [F(0), F(0)]
    action_y = [F(0), F(0)]
    ht_action_y = [F(0), F(0)]
    for h, a, y in product((0, 1), repeat=3):
        e = e1[h] if a else 1 - e1[h]
        py = q[h][a] if y else 1 - q[h][a]
        mass = e * py / 2
        action_mass[a] += mass
        action_y[a] += mass * y
        ht_action_y[a] += mass * y / e
        if a == selected[h]:
            ipw += mass * y / e
            policy_mass += mass / e
    naive = [action_y[a] / action_mass[a] for a in (0, 1)]
    assert policy_mass == 1
    assert ipw == F(4, 5)
    assert ht_action_y == [F(3, 5), F(3, 5)]
    assert naive[0] != naive[1]
    return {"personalized_truth": F(4, 5), "weighted_policy_value": ipw,
            "expected_policy_weight": policy_mass,
            "weighted_arm_values": ht_action_y,
            "unadjusted_action_group_values": naive,
            "spurious_unadjusted_arm_difference": naive[1] - naive[0]}


def regret_bound() -> dict:
    """Exhaustive grid includes ties, estimates outside [0,1], and three arms."""
    epsilon = F(1, 5)
    grid = [F(j, 5) for j in range(6)]
    max_regret = F(0)
    checked = 0
    gap_checks = 0
    for q in product(grid, repeat=3):
        for error in product((-epsilon, F(0), epsilon), repeat=3):
            estimate = tuple(q[a] + error[a] for a in range(3))
            chosen = max(range(3), key=estimate.__getitem__)  # First-index tie break.
            best = max(range(3), key=q.__getitem__)
            loss = max(q) - q[chosen]
            actual_error = max(abs(v) for v in error)
            assert 0 <= loss <= 2 * actual_error
            top = sorted(q, reverse=True)
            if top[0] - top[1] > 2 * actual_error:
                assert chosen == best
                gap_checks += 1
            max_regret = max(max_regret, loss)
            checked += 1
    assert max_regret == 2 * epsilon
    return {"grid_cases": checked, "large_gap_cases": gap_checks,
            "error_cap": epsilon, "largest_regret": max_regret,
            "factor_two_attained": max_regret == 2 * epsilon}


def paired_root_variance() -> dict:
    """Enumerate arm means; compare total variance to the root decomposition."""
    checkpoints = ((F(1, 5), F(3, 5)), (F(4, 5), F(2, 5)))
    between = F(4, 25)
    within_one = F(2, 5)
    values = {}
    for r in (1, 2, 4, 8):
        mean = second = F(0)
        for p0, p1 in checkpoints:
            for y0, w0 in binomial_law(r, p0):
                for y1, w1 in binomial_law(r, p1):
                    mass = w0 * w1 / 2
                    d = y1 - y0
                    mean += mass * d
                    second += mass * d**2
        variance = second - mean**2
        assert mean == 0
        assert variance == between + within_one / r
        values[str(r)] = variance

    # For one seed block, give the binary arms their valid joint Bernoulli law.
    # Common-uniform = largest possible positive covariance; antithetic = smallest.
    coupling_variances = {}
    for name in ("independent", "common_uniform", "antithetic"):
        total_conditional_variance = F(0)
        for p0, p1 in checkpoints:
            p11 = p0 * p1 if name == "independent" else (
                min(p0, p1) if name == "common_uniform" else max(F(0), p0 + p1 - 1))
            joint = {(1, 1): p11, (1, 0): p0 - p11,
                     (0, 1): p1 - p11, (0, 0): 1 - p0 - p1 + p11}
            assert min(joint.values()) >= 0 and sum(joint.values()) == 1
            conditional_mean = sum((y1 - y0) * p for (y0, y1), p in joint.items())
            conditional_second = sum((y1 - y0)**2 * p for (y0, y1), p in joint.items())
            assert conditional_mean == p1 - p0
            total_conditional_variance += (conditional_second - conditional_mean**2) / 2
        coupling_variances[name] = between + total_conditional_variance / 4
    assert coupling_variances == {"independent": F(13, 50),
                                  "common_uniform": F(11, 50),
                                  "antithetic": F(8, 25)}
    naive_scaled = values["1"] / 4
    assert naive_scaled == F(7, 50) < values["4"]
    return {"between_root_variance": between, "within_root_variance_one_pair": within_one,
            "root_contrast_variance_by_repetitions": values,
            "n_times_variance_of_root_mean_at_r4": values["4"],
            "n_times_naive_variance_treating_4n_pairs_independent": naive_scaled,
            "root_variance_at_r4_by_coupling": coupling_variances}


def distribution_shift() -> dict:
    gains = (F(1, 5), -F(4, 5))
    source = (F(9, 10), F(1, 10))
    target = tuple(reversed(source))
    source_value = sum(p * d for p, d in zip(source, gains))
    target_value = sum(p * d for p, d in zip(target, gains))
    weighted = sum(p * (pstar / p) * d for p, pstar, d in zip(source, target, gains))
    assert source_value == F(1, 10)
    assert target_value == weighted == -F(7, 10)
    return {"source_history_gain": source_value, "target_history_gain": target_value,
            "history_reweighted_gain": weighted,
            "invariant_conditional_Q_is_assumed": True}


def run_checks() -> dict:
    return {"zero_ate_personalization": ate_and_personalization(),
            "oracle_gaps": oracle_gaps(),
            "within_root_label_leakage": within_root_label_leakage(),
            "randomized_branch_identity": randomization_identity(),
            "finite_action_regret": regret_bound(),
            "paired_root_variance": paired_root_variance(),
            "history_distribution_shift": distribution_shift()}


def to_json(value):
    if isinstance(value, F):
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error(f"Refusing to overwrite {args.output}")
    checks = run_checks()
    result = {"evidence_type": "exact_finite_law_theory_checks",
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "python": platform.python_version(), "check_groups": len(checks),
              "all_assertions_passed": True, "model_calls": 0, "paid_spend_usd": 0,
              "checks": to_json(checks)}
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as f:
            f.write(rendered)
        print(json.dumps({"output": str(args.output), "source_sha256": result["source_sha256"],
                          "check_groups": len(checks), "all_assertions_passed": True}))
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
