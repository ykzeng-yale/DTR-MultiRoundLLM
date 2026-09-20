#!/usr/bin/env python3
"""Exact finite-law checks for the 2026-09-20 stopping theory addendum.

No model calls or random draws. Run from the repository root:
    python3 scripts/check_stopping_identities.py --output work/stopping_identities.json
Use a new output path for each preserved run; overwriting requires --overwrite.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import platform
import sys
import time
from typing import Callable

D = 2
TOLERANCE = 1e-12


@dataclass(frozen=True)
class Prefix:
    task: int
    hidden: tuple[int, ...]
    visible: tuple[int, ...]
    actions: tuple[int, ...] = ()

    @property
    def step(self) -> int:
        return len(self.actions)

    @property
    def utility(self) -> float:
        return self.hidden[-1] - 0.03 * self.step - 0.01 * sum(self.actions)


def mass(probability: float, binary: int) -> float:
    if not 0 <= probability <= 1:
        raise AssertionError(f"Probability outside [0,1]: {probability}")
    return probability if binary else 1 - probability


def public_observation_probability(hidden: int) -> float:
    return 0.85 if hidden else 0.35


def logger_probability(prefix: Prefix) -> float:
    return 0.25 + 0.50 * prefix.visible[-1]


def changed_probability(prefix: Prefix) -> float:
    # Deliberately changes continuation; all actions remain supported by logger.
    return 0.9 if prefix.visible[-1] == 0 else 0.8


def stop_visible(prefix: Prefix) -> bool:
    return bool(prefix.visible[-1]) or prefix.step == D


def stop_cap(prefix: Prefix) -> bool:
    return prefix.step == D


def stop_hidden(prefix: Prefix) -> bool:
    # Privileged analyst benchmark, forbidden as a deployed public policy.
    return bool(prefix.hidden[-1]) or prefix.step == D


def initial_states():
    for task, hidden, visible in itertools.product((0, 1), repeat=3):
        probability = mass(0.4, task) * mass(0.2 + 0.5 * task, hidden)
        probability *= mass(public_observation_probability(hidden), visible)
        yield probability, Prefix(task, (hidden,), (visible,))


def next_states(prefix: Prefix, action: int):
    p_hidden = 0.12 + 0.55 * action + 0.18 * prefix.hidden[-1]
    for hidden, visible in itertools.product((0, 1), repeat=2):
        probability = mass(p_hidden, hidden) * mass(public_observation_probability(hidden), visible)
        yield probability, Prefix(
            prefix.task, prefix.hidden + (hidden,), prefix.visible + (visible,), prefix.actions + (action,)
        )


def direct_stopped_value(action_probability: Callable, stop_rule: Callable) -> float:
    """Execute the target stopped process recursively; never generate unused suffixes."""
    def future(prefix: Prefix) -> float:
        if stop_rule(prefix):
            return prefix.utility
        return sum(
            mass(action_probability(prefix), action) * probability * future(following)
            for action in (0, 1)
            for probability, following in next_states(prefix, action)
        )
    return sum(probability * future(prefix) for probability, prefix in initial_states())


def full_paths():
    """Enumerate the complete logger paths, independently of any stopping rule."""
    def expand(probability: float, prefixes: tuple[Prefix, ...]):
        current = prefixes[-1]
        if current.step == D:
            yield probability, prefixes
            return
        for action in (0, 1):
            for transition_probability, following in next_states(current, action):
                yield from expand(
                    probability * mass(logger_probability(current), action) * transition_probability,
                    prefixes + (following,),
                )
    for probability, initial in initial_states():
        yield from expand(probability, (initial,))


def replay_value(action_probability: Callable, stop_rule: Callable, weighted: bool):
    value = 0.0
    expected_stopped_weight = 0.0
    total_probability = 0.0
    count = 0
    for probability, prefixes in full_paths():
        stop_step = next(k for k, prefix in enumerate(prefixes) if stop_rule(prefix))
        weight = 1.0
        for step in range(stop_step):
            prefix = prefixes[step]
            action = prefixes[step + 1].actions[-1]
            weight *= mass(action_probability(prefix), action) / mass(logger_probability(prefix), action)
        value += probability * (weight if weighted else 1.0) * prefixes[stop_step].utility
        expected_stopped_weight += probability * weight
        total_probability += probability
        count += 1
    return {
        "value": value,
        "expected_stopped_weight": expected_stopped_weight,
        "total_probability": total_probability,
        "complete_path_count": count,
    }


def information_counterexample():
    """Two fair binary grades; public observations carry no outcome information."""
    public_value = sum(0.25 * y0 for y0, y1 in itertools.product((0, 1), repeat=2))
    hidden_stop_value = sum(0.25 * (y0 if y0 else y1) for y0, y1 in itertools.product((0, 1), repeat=2))
    prophet_value = sum(0.25 * max(y0, y1) for y0, y1 in itertools.product((0, 1), repeat=2))
    # Every public stopping rule is a mixture of accepting at0 or1: both mean1/2.
    return {"best_public_value": public_value, "privileged_current_grade_rule": hidden_stop_value, "future_prophet": prophet_value}


def censoring_counterexample():
    """Observed baseline predicts censoring and outcome; complete cases are biased."""
    numerator = observed_mass = corrected = truth = 0.0
    for baseline, outcome, observed in itertools.product((0, 1), repeat=3):
        response_probability = 0.1 + 0.8 * baseline
        observation_probability = 0.2 if baseline == 0 else 0.8
        probability = 0.5 * mass(response_probability, outcome) * mass(observation_probability, observed)
        truth += probability * outcome
        numerator += probability * observed * outcome
        observed_mass += probability * observed
        corrected += probability * observed * outcome / observation_probability
    return {"truth": truth, "complete_case_value": numerator / observed_mass, "inverse_observation_weighted_value": corrected}


def ess_counterexample():
    """Both decision laws differ from uniform, but ESS is close to n, not n/64."""
    target = [0.135, 0.115] + [0.125] * 6
    second_moment_one_stage = sum(probability**2 / 0.125 for probability in target)
    second_moment_two_stages = second_moment_one_stage**2
    return {
        "n": 176,
        "overlap_max_bound": 64,
        "population_ess_lower_bound": 176 / 64,
        "actual_second_moment": second_moment_two_stages,
        "actual_population_ess": 176 / second_moment_two_stages,
    }


def diagnostic_counterexample():
    """Conditioning a full trajectory on admissible actions distorts prior states."""
    # At the first state, half the initial histories are s0/1. Logger chance
    # of an admissible action is.9 at0 and.1 at1. Target always admissible;
    # its outcome is baseline s. Dropping diagnostic rows changes the population.
    truth = 0.5
    retained_mass = 0.5 * 0.9 + 0.5 * 0.1
    retained_mean = 0.5 * 0.1 / retained_mass
    weighted_value = sum(0.5 * p * state / p for state, p in ((0, 0.9), (1, 0.1)))
    return {"admissible_target_value": truth, "unweighted_filtered_value": retained_mean, "weighted_filtered_value": weighted_value}


def run_checks():
    results = {}
    for name, policy in (("matching", logger_probability), ("changed", changed_probability)):
        for rule_name, rule in (("visible_stop", stop_visible), ("cap_stop", stop_cap)):
            direct = direct_stopped_value(policy, rule)
            weighted = replay_value(policy, rule, weighted=True)
            naive = replay_value(policy, rule, weighted=False)
            if abs(direct - weighted["value"]) >= TOLERANCE:
                raise AssertionError("Stopped-prefix change of measure failed")
            if abs(weighted["expected_stopped_weight"] - 1.0) >= TOLERANCE:
                raise AssertionError("Stopped likelihood ratio mean is not one")
            if abs(weighted["total_probability"] - 1.0) >= TOLERANCE or weighted["complete_path_count"] != 512:
                raise AssertionError("Complete enumeration missing paths")
            if name == "matching" and abs(direct - naive["value"]) >= TOLERANCE:
                raise AssertionError("Unweighted matching replay failed")
            if name == "changed" and abs(direct - naive["value"]) <= 0.01:
                raise AssertionError("Changed continuation must demonstrate naive replay bias")
            results[f"{name}_{rule_name}"] = {
                "direct_target_value": direct,
                "weighted_replay_value": weighted["value"],
                "unweighted_replay_value": naive["value"],
                "naive_replay_bias": naive["value"] - direct,
                "absolute_identity_error": abs(direct - weighted["value"]),
                **{key: value for key, value in weighted.items() if key != "value"},
            }
    info = information_counterexample()
    assert info == {"best_public_value": 0.5, "privileged_current_grade_rule": 0.75, "future_prophet": 0.75}
    results["hidden_label_information_gap"] = info
    censor = censoring_counterexample()
    assert abs(censor["truth"] - censor["inverse_observation_weighted_value"]) < TOLERANCE
    assert abs(censor["complete_case_value"] - censor["truth"]) > 0.2
    results["censoring"] = censor
    ess = ess_counterexample()
    assert ess["actual_population_ess"] > 175
    assert ess["population_ess_lower_bound"] == 2.75
    results["ess_lower_bound_is_not_actual_ess"] = ess
    diagnostic = diagnostic_counterexample()
    assert abs(diagnostic["weighted_filtered_value"] - diagnostic["admissible_target_value"]) < TOLERANCE
    assert diagnostic["unweighted_filtered_value"] < 0.11
    results["diagnostic_branch_filtering"] = diagnostic
    # STOP-triggered final rewrite destroys a correct prefix: measured-prefix
    # consistency is false even with a perfectly deterministic verifier.
    results["stop_side_effect_counterexample"] = {"recorded_prefix_value": 1.0, "actual_stop_rewrite_value": 0.0}
    # If all paired +/-1 scores are+1, a valid test under E[D]<=0 has tail<=2^-n.
    results["certificate_impossibility_counterexample"] = {"n": 176, "null_upper_tail_probability": 2.0**(-176)}
    assert results["certificate_impossibility_counterexample"]["null_upper_tail_probability"] < 0.05
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output and args.output.exists() and not args.overwrite:
        parser.error("Output exists; choose a new path or use --overwrite")
    start = time.perf_counter()
    results = run_checks()
    report = {
        "schema_version": "1.0",
        "evidence_type": "exact_finite_law_identity_and_counterexample_checks",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_path": "scripts/check_stopping_identities.py",
        "command": "python3 scripts/check_stopping_identities.py --output work/stopping_identities_rerun.json",
        "executed_arguments": sys.argv[1:],
        "python_version": platform.python_version(),
        "configuration": {
            "continuation_decisions": D,
            "tolerance": TOLERANCE,
            "initial_task_p1": 0.4,
            "initial_hidden_p1": "0.2+0.5*task",
            "visible_p1": "0.85 if hidden1 else0.35",
            "logger_action_p1": "0.25+0.50*latest_visible",
            "changed_action_p1": "0.9 if latest_visible0 else0.8",
            "next_hidden_p1": "0.12+0.55*action+0.18*latest_hidden",
            "prefix_utility": "latest_hidden-0.03*step-0.01*sum(actions)",
            "visible_stop_rule": "stop at first visible1 or administrative cap",
            "root_model_calls": 0,
            "paid_spend_usd": 0,
        },
        "results": results,
        "all_assertions_passed": True,
        "runtime_seconds": time.perf_counter() - start,
        "limitations": "Synthetic algebra only; no real-model, neural-learning, independence, or completeness assumption is verified.",
    }
    serialized = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Passed {len(results)} identity/counterexample checks. Results: {args.output}")
        print(f"Source SHA256: {report['source_sha256']}")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
