#!/usr/bin/env python3
"""Enumerate a two-stage random-slate DGP and verify the exact DR remainder.

No fitted nuisance models, random draws, external libraries, or LLM calls are
used. This is an algebra check, not a simulation of real language-model efficacy.

Run from the repository root:
    python3 scripts/check_random_slate_remainder.py \
        --output results/random_slate_remainder.json

Use a new output path when rerunning; --overwrite explicitly replaces an output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import platform
import sys
import time

HORIZON = 2
TOLERANCE = 1e-12
History = tuple[int, ...]
ACTIONS = tuple(itertools.product((0, 1), repeat=2))


def bernoulli_mass(probability: float, value: int) -> float:
    if not 0.0 < probability < 1.0:
        raise AssertionError(f"Invalid nondegenerate probability: {probability}")
    return probability if value else 1.0 - probability


def generator_probability(history: History, changed: bool) -> float:
    if changed:
        return 0.48 if history[-1] else 0.58
    return 0.65 if history[-1] else 0.35


def logger_probability(history: History, slate: int, wrong: bool = False) -> float:
    if wrong:
        return 0.70 - 0.20 * slate
    return 0.25 + 0.20 * slate + 0.15 * history[-1]


def selector_probability(history: History, slate: int) -> float:
    return 0.70 - 0.25 * slate + 0.05 * history[-1]


def transition_probability(history: History, slate: int, index: int) -> float:
    return 0.12 + 0.38 * index + 0.18 * slate + 0.13 * history[-1]


def reward(slate: int, index: int) -> float:
    return -0.06 * index - 0.02 * slate


def logging_mass(history: History, slate: int, index: int, wrong: bool = False) -> float:
    return bernoulli_mass(generator_probability(history, False), slate) * bernoulli_mass(
        logger_probability(history, slate, wrong), index
    )


def target_mass(history: History, slate: int, index: int, changed: bool) -> float:
    return bernoulli_mass(generator_probability(history, changed), slate) * bernoulli_mass(
        selector_probability(history, slate), index
    )


def next_history(history: History, slate: int, index: int, state: int) -> History:
    return history + (slate, index, state)


@lru_cache(maxsize=None)
def true_q(stage: int, history: History, slate: int, index: int, changed: bool) -> float:
    probability = transition_probability(history, slate, index)
    return reward(slate, index) + sum(
        bernoulli_mass(probability, state)
        * true_v(stage + 1, next_history(history, slate, index, state), changed)
        for state in (0, 1)
    )


@lru_cache(maxsize=None)
def true_v(stage: int, history: History, changed: bool) -> float:
    if stage > HORIZON:
        return float(history[-1])
    return sum(
        target_mass(history, slate, index, changed)
        * true_q(stage, history, slate, index, changed)
        for slate, index in ACTIONS
    )


def fitted_q(
    stage: int,
    history: History,
    slate: int,
    index: int,
    changed: bool,
    q_correct: frozenset[int],
) -> float:
    if stage in q_correct:
        return true_q(stage, history, slate, index, changed)
    return 0.39 + 0.14 * slate - 0.07 * index + 0.08 * history[-1]


def fitted_v(
    stage: int, history: History, changed: bool, q_correct: frozenset[int]
) -> float:
    if stage > HORIZON:
        return float(history[-1])
    return sum(
        target_mass(history, slate, index, changed)
        * fitted_q(stage, history, slate, index, changed, q_correct)
        for slate, index in ACTIONS
    )


def check_case(
    changed: bool, label: str, assignment_correct: frozenset[int], q_correct: frozenset[int]
) -> dict:
    expected_score = 0.0
    exact_remainder = 0.0
    leaf_probability = 0.0
    leaves = 0

    def enumerate_paths(stage: int, history: History, probability: float, weight: float, score: float):
        nonlocal expected_score, exact_remainder, leaf_probability, leaves
        if stage > HORIZON:
            expected_score += probability * score
            leaf_probability += probability
            leaves += 1
            return
        if abs(sum(logging_mass(history, c, j) for c, j in ACTIONS) - 1) > TOLERANCE:
            raise AssertionError("Logging action mass does not sum to one")
        if abs(sum(target_mass(history, c, j, changed) for c, j in ACTIONS) - 1) > TOLERANCE:
            raise AssertionError("Target action mass does not sum to one")
        local_remainder = 0.0
        for slate, index in ACTIONS:
            true_e = logging_mass(history, slate, index)
            fitted_e = logging_mass(history, slate, index, wrong=stage not in assignment_correct)
            target_d = target_mass(history, slate, index, changed)
            q_estimate = fitted_q(stage, history, slate, index, changed, q_correct)
            q_error = q_estimate - true_q(stage, history, slate, index, changed)
            local_remainder += target_d * (1 - true_e / fitted_e) * q_error
            next_weight = weight * target_d / fitted_e
            for state in (0, 1):
                following_history = next_history(history, slate, index, state)
                following_score = score + next_weight * (
                    reward(slate, index)
                    + fitted_v(stage + 1, following_history, changed, q_correct)
                    - q_estimate
                )
                enumerate_paths(
                    stage + 1,
                    following_history,
                    probability * true_e * bernoulli_mass(transition_probability(history, slate, index), state),
                    next_weight,
                    following_score,
                )
        exact_remainder += probability * weight * local_remainder

    oracle = 0.0
    for initial_state in (0, 1):
        probability = bernoulli_mass(0.4, initial_state)
        history = (initial_state,)
        oracle += probability * true_v(1, history, changed)
        enumerate_paths(1, history, probability, 1.0, fitted_v(1, history, changed, q_correct))
    bias = expected_score - oracle
    identity_error = bias - exact_remainder
    robust = all(stage in assignment_correct or stage in q_correct for stage in range(1, HORIZON + 1))
    if abs(identity_error) >= TOLERANCE:
        raise AssertionError(f"Exact remainder failed for {label}: {identity_error}")
    if robust and abs(bias) >= TOLERANCE:
        raise AssertionError(f"Stagewise robustness failed for {label}: {bias}")
    if not robust and abs(bias) <= 1e-3:
        raise AssertionError("Both-wrong case should demonstrate substantial product bias")
    if abs(leaf_probability - 1.0) >= TOLERANCE or leaves != 128:
        raise AssertionError(f"Incomplete trajectory enumeration: mass={leaf_probability}, leaves={leaves}")
    return {
        "generator": "changed_generator" if changed else "same_generator",
        "nuisance_case": label,
        "assignment_correct_stages": sorted(assignment_correct),
        "q_correct_stages": sorted(q_correct),
        "stagewise_robustness_condition_holds": robust,
        "oracle_value": oracle,
        "expected_dr_score": expected_score,
        "bias": bias,
        "exact_remainder": exact_remainder,
        "identity_error": identity_error,
        "absolute_identity_error": abs(identity_error),
        "enumerated_trajectories": leaves,
        "enumerated_logging_probability": leaf_probability,
        "all_assertions_passed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write machine-readable result; omit for stdout")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace an existing output")
    args = parser.parse_args()
    if args.output and args.output.exists() and not args.overwrite:
        parser.error(f"Output exists: {args.output}; use a new path or explicitly supply --overwrite")
    started = time.perf_counter()
    cases = [
        ("all_assignment_correct", frozenset({1, 2}), frozenset()),
        ("all_q_correct", frozenset(), frozenset({1, 2})),
        ("mixed_stage_correct", frozenset({1}), frozenset({2})),
        ("both_wrong", frozenset(), frozenset()),
    ]
    rows = [check_case(changed, label, e_stages, q_stages) for changed in (False, True) for label, e_stages, q_stages in cases]
    source_path = Path(__file__).resolve()
    result = {
        "schema_version": "1.0",
        "check_name": "random_slate_exact_longitudinal_dr_remainder",
        "evidence_type": "exact_finite_state_enumeration",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": "scripts/check_random_slate_remainder.py",
            "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "reproduction_command": "python3 scripts/check_random_slate_remainder.py --output results/random_slate_remainder_rerun.json",
            "executed_arguments": sys.argv[1:],
            "python_version": platform.python_version(),
        },
        "configuration": {
            "horizon": HORIZON,
            "tolerance": TOLERANCE,
            "initial_state_probability": 0.4,
            "logging_generator_p_c1": "0.65 if s=1 else 0.35",
            "changed_target_generator_p_c1": "0.48 if s=1 else 0.58",
            "logging_selector_p_j1": "0.25 + 0.20*c + 0.15*s",
            "target_selector_p_j1": "0.70 - 0.25*c + 0.05*s",
            "receiver_p_next_state1": "0.12 + 0.38*j + 0.18*c + 0.13*s",
            "turn_reward": "-0.06*j - 0.02*c",
            "terminal_reward": "final binary receiver state",
            "wrong_selector_p_j1": "0.70 - 0.20*c",
            "wrong_q": "0.39 + 0.14*c - 0.07*j + 0.08*s",
            "target_generator_density_included_in_numerator": True,
            "logging_generator_density_included_in_denominator": True,
            "q_truth_method": "exact_backward_recursion",
            "monte_carlo_sampling": False,
        },
        "results": rows,
        "summary": {
            "all_assertions_passed": True,
            "case_count": len(rows),
            "maximum_absolute_identity_error": max(row["absolute_identity_error"] for row in rows),
            "elapsed_seconds": time.perf_counter() - started,
            "model_calls": 0,
            "model_tokens": 0,
            "paid_api_cost_usd": 0,
        },
        "limitations": [
            "No real receiver or language data were used.",
            "Nuisances are fixed correct or misspecified functions, not fitted neural models.",
            "Numerical enumeration checks an algebra identity, not real-data identification assumptions.",
            "No conditional confidence-interval coverage or neural convergence rate is established.",
        ],
    }
    serialized = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Passed {len(rows)} exact-enumeration cases; max identity error {result['summary']['maximum_absolute_identity_error']:.3g}")
        print(f"Source SHA-256: {result['source']['sha256']}")
        print(f"Result: {args.output}")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
