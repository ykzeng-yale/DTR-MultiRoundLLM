"""Cross-fitted tabular Q and DR using complete recorded synthetic S/A prefixes.

Import with experiments/e0 on sys.path, as for the existing E0 modules. This
wrapper leaves the pinned estimators unchanged and fits each fold's Q once for
both plug-in and DR scores. S is the simulator's full recorded quality state:
this is NOT a claim that real LLM histories expose that state. Neither the key
nor the regression uses latent ease/type, recorded propensities, or task IDs as
features; known B is used only by the existing DR correction.

The existing unsmoothed, training-only action/stage fallback is retained,
including its zero fallback when a training stage is empty. No oracle fills,
practical regularization, finite-sample coverage, or history-sufficiency claim
is supplied here. Exact B alone does not make the plain Q regression causal
when assignment depends on hidden variables. Cross-fitting also does not by
itself validate the existing task-mean normal interval.
"""
from __future__ import annotations

import numpy as np

import estimators as base


def history_key(d, i: int, t: int):
    """Pre-action key H_t on an active row: S_0:t and A_0:t-1 only."""
    return tuple(d["S"][i, :t + 1]), tuple(d["A"][i, :t])


def _task_encoding(task):
    values = np.asarray(task, dtype=object)
    if values.ndim != 1 or not len(values):
        raise ValueError("task must be a nonempty one-dimensional label array")
    mapping, labels = {}, []
    index = np.empty(len(values), dtype=int)
    for i, label in enumerate(values):
        try:
            if label is None or not bool(label == label):
                raise ValueError("task labels must be nonmissing")
            if label not in mapping:
                mapping[label] = len(labels)
                labels.append(label)
            index[i] = mapping[label]
        except (TypeError, ValueError) as exc:
            raise ValueError("task labels must be nonmissing hashable scalars") from exc
    out = np.empty(len(labels), dtype=object)
    out[:] = labels
    return out, index


def make_task_folds(task, folds: int = 3, seed: int = 0):
    """Deterministic balanced task folds, independent of outcomes and label magnitudes.

    Task order is first occurrence. task_index is a contiguous encoding usable
    with existing base.task_clustered even when original labels cannot be sorted.
    """
    labels, index = _task_encoding(task)
    if isinstance(folds, (bool, np.bool_)) or not isinstance(folds, (int, np.integer)) or not 2 <= folds <= len(labels):
        raise ValueError("require at least two folds, no more folds than distinct tasks")
    task_folds = np.random.default_rng(seed).permutation(np.arange(len(labels)) % folds)
    return {"task_labels": labels, "task_index": index,
            "task_fold_ids": task_folds, "episode_fold_ids": task_folds[index]}


def _validated_data(d, T, pol):
    if isinstance(T, (bool, np.bool_)) or not isinstance(T, (int, np.integer)) or T < 1:
        raise ValueError("T must be a positive integer")
    data = {k: np.asarray(d[k], dtype=object if k == "task" else None)
            for k in ("task", "S", "A", "B", "Y", "elig")}
    n = len(data["Y"])
    if data["Y"].shape != (n,) or data["task"].shape != (n,):
        raise ValueError("task and Y must be aligned one-dimensional arrays")
    if any(data[k].shape != (n, T) for k in ("S", "A", "B", "elig")):
        raise ValueError("S, A, B, elig must have shape (episodes, T)")
    eligible = data["elig"]
    if eligible.dtype != np.dtype(bool) or not eligible[:, 0].all() or np.any(eligible[:, 1:] & ~eligible[:, :-1]):
        raise ValueError("elig must be boolean with an active initial decision and contiguous active prefixes")
    for name, upper in (("S", base.NS), ("A", base.K)):
        array = data[name]
        if not np.issubdtype(array.dtype, np.integer) or np.any((array[eligible] < 0) | (array[eligible] >= upper)):
            raise ValueError(f"active {name} entries must be valid integer categories")
    if np.any((data["A"][:, :-1] == 0) & eligible[:, 1:]):
        raise ValueError("STOP cannot be followed by another active decision")
    if not np.isfinite(data["Y"]).all() or not np.isfinite(data["B"][eligible]).all() or np.any((data["B"][eligible] <= 0) | (data["B"][eligible] > 1)):
        raise ValueError("Y must be finite and observed-action B must lie in (0, 1]")
    policy = np.asarray(pol, dtype=float)
    if policy.shape != (base.K,) or not np.isfinite(policy).all() or np.any(policy < 0) or not np.isclose(policy.sum(), 1, rtol=0, atol=1e-12):
        raise ValueError("pol must be a probability vector over the existing arms")
    return data, policy


def crossfit_history_scores(d, T: int, pol, folds: int = 3, seed: int = 0, fold_ids=None):
    """Return matched out-of-fold plug-in/DR episode scores and their fixed folds.

    Optional fold_ids supplies one integer per episode in 0..folds-1. Every task
    must stay within one fold and every fold must be nonempty. Returned fits
    expose Q/fallback and train/test indices for auditing; neither estimator
    refits or tunes its own Q. Apply base.task_clustered(result['task_index'],
    result['plugin_scores'] or result['dr_scores']) for equal-task summaries.
    Propensities are recorded/known; this wrapper does not fit them or establish
    positivity for unobserved alternative actions.
    """
    data, policy = _validated_data(d, T, pol)
    assignment = make_task_folds(data["task"], folds, seed)
    if fold_ids is not None:
        fa = np.asarray(fold_ids)
        if fa.shape != data["Y"].shape or not np.issubdtype(fa.dtype, np.integer) or not np.array_equal(np.unique(fa), np.arange(folds)):
            raise ValueError("fold_ids must be aligned integers covering all requested folds")
        task_folds = np.empty(len(assignment["task_labels"]), dtype=int)
        for k in range(len(task_folds)):
            values = np.unique(fa[assignment["task_index"] == k])
            if len(values) != 1:
                raise ValueError("each task must belong to exactly one fold")
            task_folds[k] = values[0]
        assignment.update(task_fold_ids=task_folds, episode_fold_ids=fa.copy())
    fa = assignment["episode_fold_ids"]
    plugin, dr = np.empty(len(fa)), np.empty(len(fa))
    fitted = []

    def key(i, t):
        return history_key(data, i, t)

    for fold in range(folds):
        train, test = np.flatnonzero(fa != fold), np.flatnonzero(fa == fold)
        Q, fallback, v0 = base.fit_q(data, T, policy, idx=train, key=key)
        plugin[test] = v0[test]
        dr[test] = base.dr_scores(data, T, policy, Q, fallback, key=key)[test]
        fitted.append({"fold": fold, "train_indices": train, "test_indices": test,
                       "Q": Q, "fallback": fallback})
    return {**assignment, "plugin_scores": plugin, "dr_scores": dr, "fits": fitted}
