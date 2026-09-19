"""Finite state, full-history DTR with an exact, enumerable data-generating law.

H1 contains task difficulty and quality of the frozen receiver's initial answer.
At each of T feedback opportunities the candidate slate is the same three
actions. Costs enter terminal utility, so intermediate rewards are zero.
STOP preserves the accepted answer, is absorbing, and incurs no further cost.
The finite action names represent a synthetic candidate-selector experiment;
they do not assert semantic equivalence of arbitrary natural-language prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Mapping

import numpy as np

RETRY, CORRECT, STOP = "RETRY", "CORRECT", "STOP"
ACTIONS = (RETRY, CORRECT, STOP)
COST = {RETRY: 1.0, CORRECT: 2.0, STOP: 0.0}


@dataclass(frozen=True)
class History:
    difficulty: int
    qualities: tuple[int, ...]
    actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.difficulty not in (0, 1):
            raise ValueError("difficulty must be 0 or 1")
        if len(self.qualities) != len(self.actions) + 1:
            raise ValueError("history must include the initial answer quality")
        if any(q not in (0, 1) for q in self.qualities):
            raise ValueError("qualities must be binary")
        if any(a not in ACTIONS for a in self.actions):
            raise ValueError("unknown action")
        if STOP in self.actions:
            first = self.actions.index(STOP)
            if any(a != STOP for a in self.actions[first:]):
                raise ValueError("STOP is absorbing")
            if any(q != self.qualities[first] for q in self.qualities[first + 1:]):
                raise ValueError("accepted answer cannot change after STOP")

    @property
    def t(self) -> int:
        return len(self.actions) + 1

    @property
    def quality(self) -> int:
        return self.qualities[-1]

    @property
    def stopped(self) -> bool:
        return STOP in self.actions

    @property
    def cost(self) -> float:
        return sum(COST[a] for a in self.actions)

    def advance(self, action: str, quality: int) -> History:
        return History(self.difficulty, self.qualities + (quality,), self.actions + (action,))


Policy = Callable[[History], Mapping[str, float]]
QFunction = Callable[[History, str], float]


def validate_distribution(distribution: Mapping[str, float], stopped: bool = False) -> None:
    if set(distribution) != set(ACTIONS):
        raise ValueError("policy must give probabilities for every action")
    values = np.array(list(distribution.values()), dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("policy probabilities must be finite and nonnegative")
    if abs(float(values.sum()) - 1.0) > 1e-10:
        raise ValueError("policy probabilities must sum to one")
    if stopped and distribution[STOP] != 1.0:
        raise ValueError("only deterministic STOP is admissible after stopping")


def behavior_policy(h: History) -> Mapping[str, float]:
    if h.stopped:
        return {RETRY: 0.0, CORRECT: 0.0, STOP: 1.0}
    if h.quality == 0:
        correction = 0.84 + 0.01 * min(h.t, 3)
        return {RETRY: 0.95 - correction, CORRECT: correction, STOP: 0.05}
    return {RETRY: 0.75, CORRECT: 0.05, STOP: 0.20}


def adaptive_policy(h: History) -> Mapping[str, float]:
    if h.stopped:
        return {RETRY: 0.0, CORRECT: 0.0, STOP: 1.0}
    if h.quality == 0:
        return {RETRY: 0.15, CORRECT: 0.80, STOP: 0.05}
    return {RETRY: 0.10, CORRECT: 0.05, STOP: 0.85}


def uniform_policy(h: History) -> Mapping[str, float]:
    if h.stopped:
        return {RETRY: 0.0, CORRECT: 0.0, STOP: 1.0}
    return dict.fromkeys(ACTIONS, 1.0 / 3.0)


def constant_policy(action: str) -> Policy:
    if action not in ACTIONS:
        raise ValueError("unknown action")

    def policy(h: History) -> Mapping[str, float]:
        chosen = STOP if h.stopped else action
        return {a: float(a == chosen) for a in ACTIONS}

    return policy


@dataclass(frozen=True)
class Step:
    history: History
    action: str
    next_history: History


@dataclass(frozen=True)
class Trajectory:
    steps: tuple[Step, ...]
    terminal_utility: float

    @property
    def initial_history(self) -> History:
        return self.steps[0].history


class FinitePromptProcess:
    def __init__(self, horizon: int = 3, cost_penalty: float = 0.035):
        if horizon < 1 or not isinstance(horizon, int):
            raise ValueError("horizon must be a positive integer")
        if cost_penalty < 0 or not np.isfinite(cost_penalty):
            raise ValueError("cost_penalty must be finite and nonnegative")
        self.horizon = horizon
        self.cost_penalty = cost_penalty

    def initial_distribution(self) -> tuple[tuple[History, float], ...]:
        # Difficulty is randomized 1/2; initial receiver quality is 0.8/0.15.
        return tuple(
            (History(x, (q,)), 0.5 * (p if q else 1.0 - p))
            for x, p in ((0, 0.8), (1, 0.15)) for q in (0, 1)
        )

    def success_probability(self, h: History, action: str) -> float:
        if action not in ACTIONS:
            raise ValueError("unknown action")
        if action == STOP:
            return float(h.quality)
        if h.stopped:
            raise ValueError("receiver cannot be called after STOP")
        if h.quality:
            base = 0.89 - 0.10 * h.difficulty
            benefit = 0.07
        else:
            base = 0.27 - 0.15 * h.difficulty
            benefit = 0.34
        # Previous interventions affect subsequent receiver transitions.
        history_gain = 0.015 * min(h.actions.count(CORRECT), 2)
        return min(0.99, base + history_gain + benefit * (action == CORRECT))

    def transition(self, h: History, action: str) -> tuple[tuple[History, float], ...]:
        if h.t > self.horizon:
            raise ValueError("history is already terminal")
        if h.stopped and action != STOP:
            raise ValueError("STOP is absorbing")
        if action == STOP:
            return ((h.advance(STOP, h.quality), 1.0),)
        p = self.success_probability(h, action)
        return ((h.advance(action, 0), 1 - p), (h.advance(action, 1), p))

    def utility(self, h: History) -> float:
        return float(h.quality) - self.cost_penalty * h.cost

    def oracle(self, target: Policy) -> tuple[QFunction, Callable[[History], float]]:
        @lru_cache(None)
        def value(h: History) -> float:
            if h.t == self.horizon + 1:
                return self.utility(h)
            probabilities = target(h)
            validate_distribution(probabilities, h.stopped)
            return sum(probabilities[a] * q(h, a) for a in ACTIONS if probabilities[a])

        @lru_cache(None)
        def q(h: History, a: str) -> float:
            return sum(p * value(next_h) for next_h, p in self.transition(h, a))

        return q, value

    def policy_value(self, target: Policy) -> float:
        _, value = self.oracle(target)
        return sum(p * value(h) for h, p in self.initial_distribution())

    def optimal_policy(self) -> Policy:
        @lru_cache(None)
        def value(h: History) -> float:
            if h.t == self.horizon + 1:
                return self.utility(h)
            actions = (STOP,) if h.stopped else ACTIONS
            return max(q(h, a) for a in actions)

        @lru_cache(None)
        def q(h: History, a: str) -> float:
            return sum(p * value(next_h) for next_h, p in self.transition(h, a))

        def policy(h: History) -> Mapping[str, float]:
            actions = (STOP,) if h.stopped else ACTIONS
            chosen = max(actions, key=lambda a: q(h, a))
            return {a: float(a == chosen) for a in ACTIONS}

        return policy

    def enumerate(self, policy: Policy, initial: History | None = None) -> list[tuple[Trajectory, float]]:
        """Enumerate probability masses, including padded absorbing transitions."""
        out: list[tuple[Trajectory, float]] = []

        def visit(h: History, mass: float, steps: tuple[Step, ...]) -> None:
            if h.t == self.horizon + 1:
                out.append((Trajectory(steps, self.utility(h)), mass))
                return
            probabilities = policy(h)
            validate_distribution(probabilities, h.stopped)
            for a in ACTIONS:
                if probabilities[a] == 0:
                    continue
                for nh, p in self.transition(h, a):
                    visit(nh, mass * probabilities[a] * p, steps + (Step(h, a, nh),))

        for h, mass in ((initial, 1.0),) if initial is not None else self.initial_distribution():
            visit(h, mass, ())
        return out

    def wrong_q(self, h: History, action: str) -> float:
        """A fixed deliberately wrong nuisance, never presented as a fitted model."""
        if h.stopped or action == STOP:
            return self.utility(h)
        return 0.38 - self.cost_penalty * (h.cost + COST[action])
