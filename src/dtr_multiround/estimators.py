"""Target-policy OPE scores and independent-task uncertainty summaries.

Functions accept fixed or externally cross-fitted nuisances. This module does
not make a fitted-nuisance claim. Any learned nuisance and policy must be
trained without the evaluation task, including all its branches and replicas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Sequence

import numpy as np

from .simulator import ACTIONS, History, Policy, QFunction, Trajectory, validate_distribution


def action_weights(h: History, target: Policy, propensity: Policy) -> tuple[dict[str, float], dict[str, float]]:
    pi, g = dict(target(h)), dict(propensity(h))
    validate_distribution(pi, h.stopped)
    validate_distribution(g, h.stopped)
    unsupported = [a for a in ACTIONS if pi[a] > 0 and g[a] <= 0]
    if unsupported:
        raise ValueError(f"unsupported target actions at stage {h.t}: {unsupported}")
    return pi, g


def value_from_q(h: History, target: Policy, q: QFunction) -> float:
    pi = target(h)
    validate_distribution(pi, h.stopped)
    return sum(pi[a] * q(h, a) for a in ACTIONS if pi[a] > 0)


def longitudinal_dr_score(trajectory: Trajectory, target: Policy, propensity: Policy, q: QFunction) -> float:
    """Vhat_1 + sum_t W_t (Vhat_{t+1} - Qhat_t), Vhat_{T+1}=U.

    W_t is the cumulative *target numerator* product pi_t/g_t. No stabilized,
    clipped, or self-normalized substitution is silently applied. STOP padding
    contributes ratios one and has exact accepted-answer Q by convention.
    """
    if not trajectory.steps:
        raise ValueError("a trajectory must contain at least one decision")
    score = value_from_q(trajectory.initial_history, target, q)
    weight = 1.0
    for index, step in enumerate(trajectory.steps):
        pi, g = action_weights(step.history, target, propensity)
        if g[step.action] <= 0:
            raise ValueError("observed action has zero supplied propensity")
        weight *= pi[step.action] / g[step.action]
        next_value = (
            trajectory.terminal_utility if index == len(trajectory.steps) - 1
            else value_from_q(step.next_history, target, q)
        )
        score += weight * (next_value - q(step.history, step.action))
    return float(score)


def ipw_score(trajectory: Trajectory, target: Policy, propensity: Policy) -> float:
    weight = 1.0
    for step in trajectory.steps:
        pi, g = action_weights(step.history, target, propensity)
        if g[step.action] <= 0:
            raise ValueError("observed action has zero supplied propensity")
        weight *= pi[step.action] / g[step.action]
    return float(weight * trajectory.terminal_utility)


def trajectory_weight(trajectory: Trajectory, target: Policy, propensity: Policy) -> float:
    weight = 1.0
    for step in trajectory.steps:
        pi, g = action_weights(step.history, target, propensity)
        if g[step.action] <= 0:
            raise ValueError("observed action has zero supplied propensity")
        weight *= pi[step.action] / g[step.action]
    return float(weight)


def continuation_pseudo_outcomes(trajectory: Trajectory, target: Policy, propensity: Policy, q: QFunction) -> tuple[float, ...]:
    """Backward orthogonal recursion; result[t] is Z_{t+1} in one-based time.

    Result length T+1, beginning with the longitudinal DR score and ending in U.
    These labels still need honest regression to estimate history-specific Q.
    """
    z = trajectory.terminal_utility
    results = [z]
    for step in reversed(trajectory.steps):
        pi, g = action_weights(step.history, target, propensity)
        if g[step.action] <= 0:
            raise ValueError("observed action has zero supplied propensity")
        z = value_from_q(step.history, target, q) + pi[step.action] / g[step.action] * (z - q(step.history, step.action))
        results.append(float(z))
    return tuple(reversed(results))


def action_pseudo_outcome(trajectory: Trajectory, stage: int, candidate: str, target: Policy, propensity: Policy, q: QFunction) -> float:
    """Action-specific DR label with the named target continuation (stage 1..T).

    Supports Q_t(h,a) regression and contrasts of such conditional means; it
    does not identify a realized individual's two potential outcomes.
    """
    if candidate not in ACTIONS or not 1 <= stage <= len(trajectory.steps):
        raise ValueError("invalid stage or candidate")
    step = trajectory.steps[stage - 1]
    _, g = action_weights(step.history, target, propensity)
    if g[candidate] <= 0:
        raise ValueError("requested candidate has no behavior support")
    future_z = continuation_pseudo_outcomes(trajectory, target, propensity, q)[stage]
    return float(q(step.history, candidate) + (step.action == candidate) / g[candidate] * (future_z - q(step.history, step.action)))


@dataclass(frozen=True)
class TaskMeanEstimate:
    estimate: float
    standard_error: float
    ci_lower: float
    ci_upper: float
    n_tasks: int
    n_trajectories: int


def estimate_task_mean(scores: Sequence[float], task_ids: Sequence[Hashable]) -> TaskMeanEstimate:
    """Equal-weight independent tasks, averaging replicas within each task.

    This estimates the task-average target; unequal replica counts are not
    allowed to upweight a task. A normal interval is asymptotic in task count.
    This is not valid for adaptive cross-task dependencies or uncorrected
    branch-selection designs. Paired policy contrasts use score differences.
    """
    if len(scores) != len(task_ids) or len(scores) == 0:
        raise ValueError("scores and task_ids must have equal nonzero length")
    grouped: dict[Hashable, list[float]] = {}
    for score, task in zip(scores, task_ids):
        if not np.isfinite(score):
            raise ValueError("scores must be finite")
        grouped.setdefault(task, []).append(float(score))
    if len(grouped) < 2:
        raise ValueError("at least two independent tasks required for uncertainty")
    means = np.array([np.mean(values) for values in grouped.values()])
    estimate = float(means.mean())
    se = float(means.std(ddof=1) / np.sqrt(len(means)))
    return TaskMeanEstimate(estimate, se, estimate - 1.96 * se, estimate + 1.96 * se, len(means), len(scores))


def task_folds(task_ids: Sequence[Hashable], n_folds: int, seed: int = 0) -> np.ndarray:
    """Partition whole tasks; callers refit all learned objects within folds."""
    unique = list(dict.fromkeys(task_ids))
    if n_folds < 2 or n_folds > len(unique):
        raise ValueError("need 2 <= n_folds <= number of unique tasks")
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(unique))
    mapping = {unique[int(index)]: position % n_folds for position, index in enumerate(order)}
    return np.array([mapping[task] for task in task_ids], dtype=int)
