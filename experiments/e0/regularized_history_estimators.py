"""Matched tabular E0 diagnostics, with fixed distinct-root shrinkage.

Four nuisance fits cross compressed S_t versus the complete recorded S/A prefix
with lambda 0 versus 5. Each fit supplies both plug-in and known-B DR scores.
Cell and pool means are episode-weighted; only the shrinkage count uses distinct
training roots. That count is not ESS. S is synthetic full state, not an asserted
observable LLM feature. No oracle fills, tuning, coverage or efficacy claim.

Import with experiments/e0 on sys.path, like the existing E0 modules. Existing
estimators and their validation/fold helpers remain unchanged.
"""
from __future__ import annotations

import numbers

import numpy as np

import history_estimators as history

base = history.base
VARIANTS = {f"{representation}_lambda{penalty}": (representation, penalty)
            for representation in ("compressed", "history") for penalty in (0, 5)}


def fit_regularized_q(d, T, pol, *, representation="history", shrinkage=5.0, idx=None):
    """Return Q, fallback, all-row v0, key callable and training support counts.

An observed key/action uses (m*q_cell + lambda*q_pool)/(m+lambda), with
q_pool the training action/stage pseudo-outcome mean. An absent action uses
the training-stage mean; an empty stage uses zero. All downstream values come
from this fit's own backward recursion. idx denotes unique training episodes.
"""
    data, policy = history._validated_data(d, T, pol)
    if representation not in ("compressed", "history"):
        raise ValueError("representation must be compressed or history")
    if (isinstance(shrinkage, (bool, np.bool_)) or not isinstance(shrinkage, numbers.Real)
            or not np.isfinite(shrinkage) or shrinkage < 0):
        raise ValueError("shrinkage must be finite and nonnegative")
    penalty = float(shrinkage)
    n = len(data["Y"])
    train = np.arange(n) if idx is None else np.asarray(idx)
    if (train.ndim != 1 or not np.issubdtype(train.dtype, np.integer)
            or len(np.unique(train)) != len(train) or np.any((train < 0) | (train >= n))):
        raise ValueError("idx must contain unique valid integer episode indices")
    _, roots = history._task_encoding(data["task"])
    if representation == "history":
        def key(i, t):
            return history.history_key(data, i, t)
    else:
        def key(i, t):
            return int(data["S"][i, t]), t
    mask = np.zeros(n, dtype=bool)
    mask[train] = True
    last = np.full(n, -1)
    for t in range(T):
        last[data["elig"][:, t]] = t
    Q, fallback = [{} for _ in range(T)], [{} for _ in range(T)]
    support = [None] * T
    nextv = np.zeros(n)
    for t in range(T - 1, -1, -1):
        active = data["elig"][:, t]
        selected = np.flatnonzero(active & mask)
        y = np.where(last == t, data["Y"], nextv)
        stage_mean = float(y[selected].mean()) if len(selected) else 0.0
        cells, action_counts = {}, {}
        for i in selected:
            cells.setdefault((key(i, t), int(data["A"][i, t])), []).append(i)
        for a in range(base.K):
            ai = selected[data["A"][selected, t] == a]
            fallback[t][a] = float(y[ai].mean()) if len(ai) else stage_mean
            action_counts[a] = {"trajectory_count": len(ai), "root_count": len(set(roots[ai]))}
        cell_counts = {}
        for (h, a), ii in cells.items():
            q_cell = float(y[ii].mean())
            m = len(set(roots[ii]))
            q_pool = fallback[t][a]
            # Exact lambda-zero parity avoids needless floating-point rescaling.
            value = q_cell if penalty == 0 else (m * q_cell + penalty * q_pool) / (m + penalty)
            Q[t].setdefault(h, {})[a] = value
            cell_counts[(h, a)] = {"trajectory_count": len(ii), "root_count": m,
                                   "q_cell": q_cell, "q_pool": q_pool, "q_fitted": value}
        support[t] = {"stage": t, "trajectory_count": len(selected),
                      "root_count": len(set(roots[selected])), "stage_mean": stage_mean,
                      "actions": action_counts, "cells": cell_counts}
        nextv = np.zeros(n)
        for i in np.flatnonzero(active):
            cell = Q[t].get(key(i, t), {})
            nextv[i] = float(policy @ np.array([cell.get(a, fallback[t][a]) for a in range(base.K)]))
    return {"representation": representation, "shrinkage": penalty,
            "Q": Q, "fallback": fallback, "v0": nextv, "key": key,
            "training_support": support}


def _heldout_support(data, T, policy, test, fit):
    """Counts over active held-out episodes and all K Q queries (no padding)."""
    stages = []
    for t in range(T):
        active = test[data["elig"][test, t]]
        counts = dict.fromkeys(("cell", "action_pool", "stage_pool", "zero"), 0)
        observed_missing = positive_missing = positive_queries = 0
        for i in active:
            cell = fit["Q"][t].get(fit["key"](i, t), {})
            observed_missing += int(int(data["A"][i, t]) not in cell)
            for a in range(base.K):
                present = a in cell
                if present:
                    level = "cell"
                elif fit["training_support"][t]["actions"][a]["trajectory_count"]:
                    level = "action_pool"
                elif fit["training_support"][t]["trajectory_count"]:
                    level = "stage_pool"
                else:
                    level = "zero"
                counts[level] += 1
                if policy[a] > 0:
                    positive_queries += 1
                    positive_missing += int(not present)
        queries = len(active) * base.K
        missing = queries - counts["cell"]
        stages.append({"stage": t, "active_heldout_trajectories": len(active),
                       "q_queries": queries, "queries_by_source": counts,
                       "fallback_queries": missing,
                       "fallback_frequency": missing / queries if queries else None,
                       "positive_target_queries": positive_queries,
                       "positive_target_fallback_queries": positive_missing,
                       "observed_action_fallbacks": observed_missing,
                       "observed_action_fallback_frequency": observed_missing / len(active) if len(active) else None})
    return stages


def crossfit_regularized_history_scores(d, T, pol, folds=3, seed=0, fold_ids=None):
    """Return four matched nuisance variants and the single shared root partition.

result['variants'][name] contains plugin_scores, dr_scores, fits. Each fit exposes
training_support, heldout_support, and train/test indices. Fold validation follows
history.crossfit_history_scores. Summarize episode scores with the returned
task_index and base.task_clustered, keeping roots equally weighted. Plug-in score
dispersion is not a complete uncertainty estimate for fitted plug-in inference.
"""
    data, policy = history._validated_data(d, T, pol)
    assignment = history.make_task_folds(data["task"], folds, seed)
    if fold_ids is not None:
        fa = np.asarray(fold_ids)
        if (fa.shape != data["Y"].shape or not np.issubdtype(fa.dtype, np.integer)
                or not np.array_equal(np.unique(fa), np.arange(folds))):
            raise ValueError("fold_ids must be aligned integers covering all requested folds")
        task_folds = np.empty(len(assignment["task_labels"]), dtype=int)
        for k in range(len(task_folds)):
            values = np.unique(fa[assignment["task_index"] == k])
            if len(values) != 1:
                raise ValueError("each task must belong to exactly one fold")
            task_folds[k] = values[0]
        assignment.update(task_fold_ids=task_folds, episode_fold_ids=fa.copy())
    fa = assignment["episode_fold_ids"]
    variants = {}
    for name, (representation, penalty) in VARIANTS.items():
        plugin, dr, fits = np.empty(len(fa)), np.empty(len(fa)), []
        for fold in range(folds):
            train, test = np.flatnonzero(fa != fold), np.flatnonzero(fa == fold)
            fit = fit_regularized_q(data, T, policy, representation=representation, shrinkage=penalty, idx=train)
            plugin[test] = fit["v0"][test]
            dr[test] = base.dr_scores(data, T, policy, fit["Q"], fit["fallback"], key=fit["key"])[test]
            fit.update(fold=fold, train_indices=train, test_indices=test,
                       heldout_support=_heldout_support(data, T, policy, test, fit))
            fits.append(fit)
        variants[name] = {"representation": representation, "shrinkage": penalty,
                          "plugin_scores": plugin, "dr_scores": dr, "fits": fits}
    return {**assignment, "variants": variants}
