#!/usr/bin/env python3
"""Run $0, CPU-only, known-truth fixed-nuisance diagnostics.

Each independent synthetic task draws a task state + initial receiver answer.
Independent continuations share that baseline within task; inference averages
scores within task first. Sampling enumerated conditional paths is exactly
equivalent to sequential simulation, without wasted Python transition calls.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dtr_multiround.estimators import ipw_score, longitudinal_dr_score, trajectory_weight, value_from_q
from dtr_multiround.simulator import (
    ACTIONS, CORRECT, RETRY, STOP, FinitePromptProcess,
    adaptive_policy, behavior_policy, constant_policy, uniform_policy,
)


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def describe_policy(process, name, policy):
    paths = process.enumerate(policy)
    return {
        "policy": name,
        "utility": sum(p * trajectory.terminal_utility for trajectory, p in paths),
        "terminal_quality": sum(p * trajectory.steps[-1].next_history.quality for trajectory, p in paths),
        "mean_feedback_calls": sum(p * sum(s.action != STOP for s in trajectory.steps) for trajectory, p in paths),
        "mean_cost_units": sum(p * trajectory.steps[-1].next_history.cost for trajectory, p in paths),
        "probability_chooses_stop": sum(p * (STOP in trajectory.steps[-1].next_history.actions) for trajectory, p in paths),
    }


def confounding_diagnostic(process, paths):
    rows = []
    for stage in range(1, process.horizon + 1):
        histories, observed_den, observed_num = {}, {RETRY: 0., CORRECT: 0.}, {RETRY: 0., CORRECT: 0.}
        for trajectory, mass in paths:
            step = trajectory.steps[stage - 1]
            if step.history.stopped:
                continue
            histories[step.history] = histories.get(step.history, 0.) + mass
            if step.action in (RETRY, CORRECT):
                observed_den[step.action] += mass
                observed_num[step.action] += mass * step.next_history.quality
        active_mass = sum(histories.values())
        standardized = {
            action: sum(mass * process.success_probability(h, action) for h, mass in histories.items()) / active_mass
            for action in (RETRY, CORRECT)
        }
        observed = {a: observed_num[a] / observed_den[a] for a in (RETRY, CORRECT)}
        rows.append({
            "stage": stage,
            "active_probability_under_behavior": active_mass,
            "observed_correct_minus_retry_next_quality": observed[CORRECT] - observed[RETRY],
            "causal_correct_minus_retry_next_quality": standardized[CORRECT] - standardized[RETRY],
            "observed_correct_quality": observed[CORRECT],
            "observed_retry_quality": observed[RETRY],
            "standardized_correct_quality": standardized[CORRECT],
            "standardized_retry_quality": standardized[RETRY],
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=400)
    parser.add_argument("--tasks", type=int, default=800)
    parser.add_argument("--episodes-per-task", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260919)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--cost-penalty", type=float, default=0.035)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "synthetic_reference_v1")
    args = parser.parse_args()
    if args.replicates < 2 or args.tasks < 2 or args.episodes_per_task < 1:
        parser.error("replicates/tasks >= 2 and episodes-per-task >= 1 required")
    if args.horizon > 5:
        parser.error("exact enumerator is deliberately bounded to horizon <= 5")
    # Preserve previous results: reproducibility checks should use a new path.
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        parser.error("output directory is nonempty; use a new output path to preserve evidence")
    started = time.monotonic()
    process = FinitePromptProcess(args.horizon, args.cost_penalty)
    q_true, _ = process.oracle(adaptive_policy)
    truth = process.policy_value(adaptive_policy)
    paths = process.enumerate(behavior_policy)
    probabilities = np.array([p for _, p in paths])
    methods = {
        "DR_both_correct": lambda tr: longitudinal_dr_score(tr, adaptive_policy, behavior_policy, q_true),
        "DR_propensity_correct_Q_wrong": lambda tr: longitudinal_dr_score(tr, adaptive_policy, behavior_policy, process.wrong_q),
        "DR_Q_correct_propensity_wrong": lambda tr: longitudinal_dr_score(tr, adaptive_policy, uniform_policy, q_true),
        "DR_both_wrong": lambda tr: longitudinal_dr_score(tr, adaptive_policy, uniform_policy, process.wrong_q),
        "IPW_propensity_correct": lambda tr: ipw_score(tr, adaptive_policy, behavior_policy),
        "IPW_propensity_wrong": lambda tr: ipw_score(tr, adaptive_policy, uniform_policy),
        "Direct_Q_correct": lambda tr: value_from_q(tr.initial_history, adaptive_policy, q_true),
        "Direct_Q_wrong": lambda tr: value_from_q(tr.initial_history, adaptive_policy, process.wrong_q),
    }
    method_names = list(methods)
    score_matrix = np.array([[f(tr) for f in methods.values()] for tr, _ in paths])
    exact_means = probabilities @ score_matrix
    initial_distribution = process.initial_distribution()
    initial_probabilities = np.array([p for _, p in initial_distribution])
    grouped_indices, conditional_p, conditional_means, conditional_variances = [], [], [], []
    for initial, initial_p in initial_distribution:
        indices = np.array([index for index, (tr, _) in enumerate(paths) if tr.initial_history == initial])
        conditional = probabilities[indices] / initial_p
        grouped_indices.append(indices)
        conditional_p.append(conditional)
        mean = conditional @ score_matrix[indices]
        conditional_means.append(mean)
        conditional_variances.append(conditional @ (score_matrix[indices] - mean) ** 2)
    conditional_means = np.array(conditional_means)
    conditional_variances = np.array(conditional_variances)
    task_variance = initial_probabilities @ (conditional_variances / args.episodes_per_task + (conditional_means - exact_means) ** 2)

    estimates = np.empty((args.replicates, len(methods)))
    standard_errors = np.empty_like(estimates)
    naive_standard_errors = np.empty_like(estimates)
    replicate_rows = []
    seed_sequence = np.random.SeedSequence(args.seed)
    replicate_sequences = seed_sequence.spawn(args.replicates)
    for replicate, replicate_seed in enumerate(replicate_sequences):
        rng = np.random.default_rng(replicate_seed)
        initial_ids = rng.choice(len(initial_distribution), size=args.tasks, p=initial_probabilities)
        task_scores = np.empty((args.tasks, args.episodes_per_task, len(methods)))
        for baseline_index, (indices, conditional) in enumerate(zip(grouped_indices, conditional_p)):
            positions = np.flatnonzero(initial_ids == baseline_index)
            sampled = rng.choice(indices, size=(len(positions), args.episodes_per_task), p=conditional)
            task_scores[positions] = score_matrix[sampled]
        cluster_means = task_scores.mean(axis=1)
        estimates[replicate] = cluster_means.mean(axis=0)
        standard_errors[replicate] = cluster_means.std(axis=0, ddof=1) / np.sqrt(args.tasks)
        naive_standard_errors[replicate] = task_scores.reshape(-1, len(methods)).std(axis=0, ddof=1) / np.sqrt(args.tasks * args.episodes_per_task)
        for index, name in enumerate(method_names):
            estimate, se = estimates[replicate, index], standard_errors[replicate, index]
            replicate_rows.append({
                "replicate": replicate, "seed_spawn_key": str(replicate_seed.spawn_key), "method": name,
                "estimate": float(estimate), "task_cluster_se": float(se),
                "ci_lower": float(estimate - 1.96 * se), "ci_upper": float(estimate + 1.96 * se),
                "covered_truth": bool(abs(estimate - truth) <= 1.96 * se),
            })

    summary_rows = []
    for index, name in enumerate(method_names):
        errors = estimates[:, index] - truth
        covered = abs(errors) <= 1.96 * standard_errors[:, index]
        naive_covered = abs(errors) <= 1.96 * naive_standard_errors[:, index]
        coverage = float(covered.mean())
        sd = float(estimates[:, index].std(ddof=1))
        summary_rows.append({
            "method": name,
            "truth": truth,
            "exact_score_expectation": float(exact_means[index]),
            "exact_bias": float(exact_means[index] - truth),
            "monte_carlo_bias": float(errors.mean()),
            "bias_mcse": sd / np.sqrt(args.replicates),
            "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "empirical_sd": sd,
            "mean_task_cluster_se": float(standard_errors[:, index].mean()),
            "exact_task_cluster_se": float(np.sqrt(task_variance[index] / args.tasks)),
            "coverage_95": coverage,
            "coverage_mcse": float(np.sqrt(coverage * (1 - coverage) / args.replicates)),
            "naive_episode_coverage_95": float(naive_covered.mean()),
        })

    policy_rows = [describe_policy(process, name, policy) for name, policy in (
        ("adaptive_stochastic", adaptive_policy), ("logging_behavior", behavior_policy),
        ("always_retry", constant_policy(RETRY)), ("always_correct", constant_policy(CORRECT)),
        ("accept_initial", constant_policy(STOP)), ("oracle_optimal", process.optimal_policy()),
    )]
    confounding_rows = confounding_diagnostic(process, paths)
    q_stop, _ = process.oracle(constant_policy(STOP))
    conditional_rows = []
    for initial, mass in initial_distribution:
        conditional_rows.append({
            "difficulty": initial.difficulty, "initial_quality": initial.quality, "population_probability": mass,
            "Q_retry_adaptive_continuation": q_true(initial, RETRY),
            "Q_correct_adaptive_continuation": q_true(initial, CORRECT),
            "Q_stop": q_true(initial, STOP),
            "blip_correct_vs_retry_adaptive_continuation": q_true(initial, CORRECT) - q_true(initial, RETRY),
            "blip_correct_vs_retry_stop_continuation": q_stop(initial, CORRECT) - q_stop(initial, RETRY),
        })
    weights = np.array([trajectory_weight(tr, adaptive_policy, behavior_policy) for tr, _ in paths])
    weight_diagnostics = {
        "exact_mean_terminal_weight": float(probabilities @ weights),
        "exact_second_moment_terminal_weight": float(probabilities @ (weights ** 2)),
        "maximum_terminal_weight_on_enumerated_support": float(weights.max()),
        "iid_trajectory_ess_fraction_diagnostic_only": float(1 / (probabilities @ (weights ** 2))),
        "note": "This weight ESS is not the independent task count and is not used for confidence intervals.",
    }
    config = {
        "study_status": "executed synthetic fixed-nuisance diagnostic; no LLM calls or learned models",
        "horizon": args.horizon, "cost_penalty": args.cost_penalty,
        "replicates": args.replicates, "tasks_per_replicate": args.tasks,
        "episodes_per_task": args.episodes_per_task, "root_seed": args.seed,
        "bit_generator": "numpy.PCG64", "seed_strategy": "SeedSequence(root_seed).spawn(replicates)",
        "target": "adaptive_policy", "behavior": "behavior_policy", "wrong_propensity": "uniform_policy",
        "wrong_q": "FinitePromptProcess.wrong_q", "truth": truth,
        "task_sampling": "iid baseline H1; independent continuations share H1 within task",
        "outcome": "terminal binary answer quality minus cost_penalty * cumulative cost units",
        "costs": {RETRY: 1, CORRECT: 2, STOP: 0},
        "candidate_generator": "fixed slate [RETRY, CORRECT, STOP]",
        "currency_cost_usd": 0, "external_model_calls": 0,
        "confidence_intervals": "normal 1.96 * SE of independent task means; finite-Monte-Carlo coverage is diagnostic",
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "src" / "dtr_multiround").glob("*.py"))},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    write_csv(args.output / "monte_carlo_summary.csv", summary_rows)
    write_csv(args.output / "replicate_estimates.csv", replicate_rows)
    write_csv(args.output / "exact_policy_values.csv", policy_rows)
    write_csv(args.output / "confounding_reversal.csv", confounding_rows)
    write_csv(args.output / "conditional_prompt_values.csv", conditional_rows)
    (args.output / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    (args.output / "overlap_diagnostics.json").write_text(json.dumps(weight_diagnostics, indent=2) + "\n")
    runtime = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - started,
        "python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
        "enumerated_behavior_trajectories": len(paths),
    }
    (args.output / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
    lines = [
        "# Synthetic reference experiment", "",
        "**Executed, CPU-only, $0 external spend. No LLM or neural value model was trained or evaluated.**", "",
        f"The target stochastic feedback policy has exact value **{truth:.6f}**. "
        f"There are {args.replicates} independent Monte Carlo replications, each with {args.tasks} tasks "
        f"and {args.episodes_per_task} continuations per task; horizon {args.horizon}. "
        "Truth is computed by backward recursion and independently checked by complete trajectory enumeration.", "",
        "H1 includes the initial receiver answer. At every active round the same finite candidate slate offers "
        "RETRY, CORRECT, and STOP. STOP freezes quality and incurs no further cost. The logged feedback depends "
        "on current answer quality, which earlier feedback can change. Terminal utility subtracts 0.035 per cost unit "
        "by default (RETRY costs 1, CORRECT costs 2).", "",
        "## Fixed-nuisance robustness and uncertainty", "",
        "`correct` is the known simulator nuisance; `wrong` is a deliberately fixed misspecification. "
        "No nuisance fitting or cross-fitting performance is claimed. The code supplies task-fold assignment "
        "for future fitted experiments. All interval standard errors first average continuations within task.", "",
        "| Estimator | Exact bias | MC bias (MCSE) | RMSE | 95% coverage (MCSE) |", "|---|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(f"| {row['method']} | {row['exact_bias']:.6f} | {row['monte_carlo_bias']:.5f} ({row['bias_mcse']:.5f}) | {row['rmse']:.5f} | {row['coverage_95']:.3f} ({row['coverage_mcse']:.3f}) |")
    lines += [
        "", "The exact expectation calculation, not simulation alone, verifies double robustness. "
        "Coverage is finite-sample evidence for this toy process only. Zero estimated coverage MCSE at observed "
        "coverage 0 or 1 is a plug-in Monte Carlo value, not a certainty claim. "
        "`Direct_Q_correct` uses oracle conditional means and therefore has information unavailable to a fitted model. "
        "Intervals for biased estimators are shown to expose failure; they do not repair misspecification.", "",
        "## Confounding reversal", "",
        "The following compares the next-answer quality after CORRECT versus RETRY. The causal contrast "
        "standardizes both interventions over the same active histories under the logging regime. It uses "
        "immediate quality (equivalently, terminal quality under STOP thereafter), not the main cost-penalized "
        "adaptive-policy outcome.", "",
        "| Stage | Observed contrast | Causal standardized contrast |", "|---|---:|---:|",
    ]
    for row in confounding_rows:
        lines.append(f"| {row['stage']} | {row['observed_correct_minus_retry_next_quality']:.4f} | {row['causal_correct_minus_retry_next_quality']:.4f} |")
    lines += ["", "## Exact policy values", "", "| Policy | Utility | Quality | Feedback calls |", "|---|---:|---:|---:|"]
    for row in policy_rows:
        lines.append(f"| {row['policy']} | {row['utility']:.4f} | {row['terminal_quality']:.4f} | {row['mean_feedback_calls']:.3f} |")
    lines += [
        "", "`oracle_optimal` is known-process dynamic programming, not a learned prompt generator. "
        "The conditional value file illustrates baseline-history-specific mean effects under two named continuation "
        "policies; these are not realized individual treatment effects.", "",
        "## Reproduce and extend", "", "```sh",
        f"uv run --extra dev python scripts/run_synthetic.py --replicates {args.replicates} --tasks {args.tasks} --episodes-per-task {args.episodes_per_task} --seed {args.seed} --horizon {args.horizon} --cost-penalty {args.cost_penalty} --output results/new_reproduction",
        "uv run --extra dev pytest -q", "```", "",
        "Use a fresh output path; the runner refuses to overwrite an existing result. Config records seeds, "
        "source hashes, costs, sampling unit, and estimator definitions. Replicate estimates, exact policy values, "
        "conditional effects, overlap moments, and environment details are separate machine-readable files.", "",
        "Limitations: finite supported candidates, randomized known behavior, four baseline strata, a fixed receiver "
        "transition law, no hidden confounding, no generator shift, no representation loss, no learned policies, "
        "no human users, and no empirical LLM effectiveness claim. Real experiments require frozen checkpoints, "
        "task-level train/calibration/test splits, fresh randomized continuations, terminal scorer isolation, "
        "failure accounting, and predeclared cost/support diagnostics.", "",
    ]
    (args.output / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps({"output": str(args.output), "truth": truth, **runtime}, indent=2))


if __name__ == "__main__":
    main()
