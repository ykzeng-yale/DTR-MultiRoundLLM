"""Three matched STOP-handling modes for the known E0 binary-quality law.

This core is not an execution release, runner, report or practical LLM learner.
S is observed synthetic true quality. The structural STOP payoff is I(S_t==3):
binary Y, consistent observed STOP outcomes and no early non-STOP termination
are required here, in addition to the unchanged legacy data checks.

Public API: fit_stop_anchor_q(..., mode, representation, shrinkage, idx),
query_dr_scores(..., query), direct_stop_increment(..., original_query), and
crossfit_stop_anchor_scores(..., folds, seed, fold_ids). No externally supplied
fit is accepted: its key/query closures could bind a different dataset or policy.
The cross-fit routine privately reuses each original fit for evaluation_only.
Explicit fold_ids avoid RNG calls; otherwise the existing fold permutation is
used once (fold assignment, not synthetic-data generation). No sampler is called.

Training support always counts actually observed training cells, including in
structural modes. The raw STOP fallback is retained for diagnostics but bypassed
by the state-dependent query. Held-out query sources distinguish structural
answers from observed cells and fallback. Counts are not ESS or target occupancy.
All scores are episode-level; summarize equal root means using task_index.
No interval, finite-sample variance ordering, or calibrated-coverage claim is made.
"""
from __future__ import annotations

import numbers

import numpy as np

import regularized_history_estimators as original

history = original.history
base = original.base
MODES = ("original", "evaluation_only", "recursive")
VARIANTS = {f"{rep}_lambda{penalty}_{mode}": (rep, penalty, mode)
            for rep in ("compressed", "history") for penalty in (0, 5) for mode in MODES}
ESTIMATORS = tuple(f"{name}:{method}" for name in VARIANTS for method in ("plugin", "dr"))


def _validated(d, T, pol):
    data, policy = history._validated_data(d, T, pol)
    if not np.isin(data["Y"], [0., 1.]).all():
        raise ValueError("STOP anchoring requires the binary E0 endpoint")
    for t in range(T):
        stop = data["elig"][:, t] & (data["A"][:, t] == 0)
        if not np.array_equal(data["Y"][stop], (data["S"][stop, t] == 3).astype(float)):
            raise ValueError("observed STOP contradicts the structural E0 payoff")
        if t < T - 1:
            ended = data["elig"][:, t] & ~data["elig"][:, t + 1]
            if np.any(data["A"][ended, t] != 0):
                raise ValueError("early termination must follow STOP")
    return data, policy


def _settings(representation, shrinkage, mode, idx, n):
    if representation not in ("compressed", "history") or mode not in MODES:
        raise ValueError("unknown representation or STOP mode")
    if (isinstance(shrinkage, (bool, np.bool_)) or not isinstance(shrinkage, numbers.Real)
            or not np.isfinite(shrinkage) or shrinkage < 0):
        raise ValueError("shrinkage must be finite and nonnegative")
    train = np.arange(n) if idx is None else np.asarray(idx)
    if (train.ndim != 1 or not np.issubdtype(train.dtype, np.integer)
            or len(np.unique(train)) != len(train) or np.any((train < 0) | (train >= n))):
        raise ValueError("idx must contain unique valid integer episode indices")
    return float(shrinkage), train


def _query(data, fit, anchored):
    def query(i, t, a):
        if not data["elig"][i, t]:
            raise ValueError("Q queries require an active decision; padding is not a history")
        if not 0 <= a < base.K:
            raise ValueError("invalid action query")
        if anchored and a == 0:
            return float(data["S"][i, t] == 3)
        return fit["Q"][t].get(fit["key"](i, t), {}).get(a, fit["fallback"][t][a])
    return query


def _evaluation_view(data, policy, fit):
    # Private and called only immediately beside the original fit on these data.
    view = {**fit, "mode": "evaluation_only", "backward_fit_reused": True}
    view["query"] = _query(data, fit, anchored=True)
    delta = np.array([float(data["S"][i, 0] == 3) - fit["query"](i, 0, 0)
                      for i in range(len(data["Y"]))])
    view["v0"] = fit["v0"] + policy[0] * delta
    return view


def _recursive_fit(data, T, policy, representation, penalty, train):
    """Own backward recursion; frozen original tables are never edited."""
    n = len(data["Y"])
    _, roots = history._task_encoding(data["task"])
    key = ((lambda i, t: history.history_key(data, i, t)) if representation == "history"
           else (lambda i, t: (int(data["S"][i, t]), t)))
    mask = np.zeros(n, dtype=bool)
    mask[train] = True
    last = data["elig"].sum(axis=1) - 1
    fit = dict(representation=representation, shrinkage=penalty, mode="recursive",
               Q=[{} for _ in range(T)], fallback=[{} for _ in range(T)],
               key=key, training_support=[None]*T, backward_fit_reused=False)
    query = _query(data, fit, anchored=True)
    nextv = np.zeros(n)
    for t in range(T - 1, -1, -1):
        active = data["elig"][:, t]
        selected = np.flatnonzero(active & mask)
        y = np.where(last == t, data["Y"], nextv)
        stage_mean = float(y[selected].mean()) if len(selected) else 0.
        cells, action_counts = {}, {}
        for i in selected:
            cells.setdefault((key(i, t), int(data["A"][i, t])), []).append(i)
        for a in range(base.K):
            ai = selected[data["A"][selected, t] == a]
            fit["fallback"][t][a] = float(y[ai].mean()) if len(ai) else stage_mean
            action_counts[a] = dict(trajectory_count=len(ai), root_count=len(set(roots[ai])))
        cell_counts = {}
        for (h, a), ii in cells.items():
            q_cell, m = float(y[ii].mean()), len(set(roots[ii]))
            q_pool = fit["fallback"][t][a]
            unanchored = q_cell if penalty == 0 else (m*q_cell + penalty*q_pool)/(m+penalty)
            value = float(data["S"][ii[0], t] == 3) if a == 0 else unanchored
            fit["Q"][t].setdefault(h, {})[a] = value
            cell_counts[(h, a)] = dict(trajectory_count=len(ii), root_count=m, q_cell=q_cell,
                                       q_pool=q_pool, q_fitted=value, q_unanchored=unanchored,
                                       structural_override=(a == 0))
        fit["training_support"][t] = dict(stage=t, trajectory_count=len(selected),
            root_count=len(set(roots[selected])), stage_mean=stage_mean, actions=action_counts, cells=cell_counts)
        nextv = np.zeros(n)
        for i in np.flatnonzero(active):
            nextv[i] = float(policy @ np.array([query(i, t, a) for a in range(base.K)]))
    fit.update(query=query, v0=nextv)
    return fit


def fit_stop_anchor_q(d, T, pol, *, representation="history", shrinkage=5., mode="recursive", idx=None):
    """Fit one mode under the known STOP payoff, with training-only nuisance means.

Standalone evaluation_only first fits the original once. Cross-fitting uses the
private shared-fit path to avoid refitting. Returned query(i,t,a) is defined only
on active rows. Original/evaluation-only Q tables and support describe the same
original fit; query, not those tables alone, is authoritative for anchored modes.
"""
    data, policy = _validated(d, T, pol)
    penalty, train = _settings(representation, shrinkage, mode, idx, len(data["Y"]))
    if mode == "recursive":
        return _recursive_fit(data, T, policy, representation, penalty, train)
    fit = original.fit_regularized_q(data, T, policy, representation=representation,
                                     shrinkage=penalty, idx=train)
    fit.update(mode="original", backward_fit_reused=False)
    fit["query"] = _query(data, fit, anchored=False)
    return _evaluation_view(data, policy, fit) if mode == "evaluation_only" else fit


def query_dr_scores(d, T, pol, query):
    """Recompute the sequential score directly from a single shared Q query.

This is separate from the STOP-specific Eq(4) calculation. Scores may be outside
[0,1]; no clipping is performed. Only observed-action B enters the weights.
The caller must bind query to these same data, horizon, policy and fitted context;
arbitrary external callables cannot be provenance-checked here. Internal crossfit
construction ensures that binding and uses the same query for plug-in and DR.
"""
    data, policy = _validated(d, T, pol)
    n = len(data["Y"])
    values, chosen = np.zeros((n, T + 1)), np.zeros((n, T))
    for t in range(T):
        for i in np.flatnonzero(data["elig"][:, t]):
            qs = np.array([query(i, t, a) for a in range(base.K)])
            values[i, t] = float(policy @ qs)
            chosen[i, t] = qs[data["A"][i, t]]
    score, weight = values[:, 0].copy(), np.ones(n)
    last = data["elig"].sum(axis=1) - 1
    for t in range(T):
        ii = np.flatnonzero(data["elig"][:, t])
        weight[ii] *= policy[data["A"][ii, t]] / data["B"][ii, t]
        reward = np.where(last[ii] == t, data["Y"][ii], 0.)
        score[ii] += weight[ii] * (reward + values[ii, t + 1] - chosen[ii, t])
    return score


def direct_stop_increment(d, T, pol, original_query):
    """Eq(4), using B only for the observed action, including actual STOP rows.

The original_query callable must be bound to the same data/policy/fitted context;
that caller contract is enforced by construction internally, not for arbitrary
externally supplied callables. No full counterfactual action-probability vector
is inferred from observed-action B.
"""
    data, policy = _validated(d, T, pol)
    change, weight = np.zeros(len(data["Y"])), np.ones(len(data["Y"]))
    for t in range(T):
        ii = np.flatnonzero(data["elig"][:, t])
        ratios = policy[data["A"][ii, t]] / data["B"][ii, t]
        delta = np.array([float(data["S"][i, t] == 3) - original_query(i, t, 0) for i in ii])
        # If STOP was not observed, its propensity is neither accessed nor invented.
        change[ii] += weight[ii] * (policy[0] - ratios * (data["A"][ii, t] == 0)) * delta
        weight[ii] *= ratios
    return change


def heldout_support(data, T, test, fit):
    """Separate actual query source from observed-training support, by action type.

The counts have TWO partitions, each separately summing to queries:
(observed_training_cell, unseen_training_cell), and
(structural, cell, action_pool, stage_pool, zero). Summing all seven double-counts.
"""
    stages = []
    for t in range(T):
        active = test[data["elig"][test, t]]
        groups = {}
        for group, actions in (("stop", (0,)), ("nonstop", range(1, base.K))):
            counts = dict.fromkeys(("observed_training_cell", "unseen_training_cell", "structural",
                                   "cell", "action_pool", "stage_pool", "zero"), 0)
            for i in active:
                cell = fit["Q"][t].get(fit["key"](i, t), {})
                for a in actions:
                    present = a in cell
                    counts["observed_training_cell" if present else "unseen_training_cell"] += 1
                    if a == 0 and fit["mode"] != "original":
                        source = "structural"
                    elif present:
                        source = "cell"
                    elif fit["training_support"][t]["actions"][a]["trajectory_count"]:
                        source = "action_pool"
                    elif fit["training_support"][t]["trajectory_count"]:
                        source = "stage_pool"
                    else:
                        source = "zero"
                    counts[source] += 1
            queries = len(active)*len(actions)
            fallback = counts["action_pool"] + counts["stage_pool"] + counts["zero"]
            groups[group] = dict(queries=queries, counts=counts, fallback_queries=fallback,
                                fallback_frequency=fallback/queries if queries else None)
        stages.append(dict(stage=t, active_heldout_trajectories=len(active), groups=groups))
    return stages


def _fold_assignment(tasks, folds, seed, fold_ids):
    if fold_ids is None:
        return history.make_task_folds(tasks, folds, seed)
    labels, index = history._task_encoding(tasks)
    if (isinstance(folds, (bool, np.bool_)) or not isinstance(folds, (int, np.integer))
            or not 2 <= folds <= len(labels)):
        raise ValueError("require at least two nonempty root folds")
    fa = np.asarray(fold_ids)
    if (fa.shape != index.shape or not np.issubdtype(fa.dtype, np.integer)
            or not np.array_equal(np.unique(fa), np.arange(folds))):
        raise ValueError("fold_ids must cover all requested folds with aligned integers")
    task_folds = np.empty(len(labels), dtype=int)
    for k in range(len(labels)):
        values = np.unique(fa[index == k])
        if len(values) != 1:
            raise ValueError("each root must stay in one fold")
        task_folds[k] = values[0]
    return dict(task_labels=labels, task_index=index, task_fold_ids=task_folds, episode_fold_ids=fa.copy())


def crossfit_stop_anchor_scores(d, T, pol, folds=3, seed=0, fold_ids=None):
    """Twelve Q sequences, eight backward fits per fold, twenty-four point scores.

Evaluation-only DR is original DR plus Eq(4); query_dr_scores supplies the separate
general-score implementation for fixture verification. No runner failure ledger
is implemented here: exceptions propagate to a future failure-preserving adapter.
"""
    data, policy = _validated(d, T, pol)
    assignment = _fold_assignment(data["task"], folds, seed, fold_ids)
    fa, n = assignment["episode_fold_ids"], len(data["Y"])
    variants = {name: dict(representation=rep, shrinkage=penalty, mode=mode,
                plugin_scores=np.empty(n), dr_scores=np.empty(n), fits=[])
                for name, (rep, penalty, mode) in VARIANTS.items()}
    for rep in ("compressed", "history"):
        for penalty in (0, 5):
            for fold in range(folds):
                train, test = np.flatnonzero(fa != fold), np.flatnonzero(fa == fold)
                fit = fit_stop_anchor_q(data, T, policy, representation=rep, shrinkage=penalty,
                                        mode="original", idx=train)
                direct = _evaluation_view(data, policy, fit)
                recursive = fit_stop_anchor_q(data, T, policy, representation=rep, shrinkage=penalty,
                                              mode="recursive", idx=train)
                original_dr = base.dr_scores(data, T, policy, fit["Q"], fit["fallback"], key=fit["key"])
                increment = direct_stop_increment(data, T, policy, fit["query"])
                scores = {"original": original_dr, "evaluation_only": original_dr + increment,
                          "recursive": query_dr_scores(data, T, policy, recursive["query"])}
                for current in (fit, direct, recursive):
                    mode = current["mode"]
                    current.update(fold=fold, train_indices=train, test_indices=test,
                                   heldout_support=heldout_support(data, T, test, current))
                    variant = variants[f"{rep}_lambda{penalty}_{mode}"]
                    variant["plugin_scores"][test] = current["v0"][test]
                    variant["dr_scores"][test] = scores[mode][test]
                    variant["fits"].append(current)
                    if mode == "evaluation_only":
                        variant.setdefault("direct_increment_scores", np.empty(n))[test] = increment[test]
    return {**assignment, "variants": variants,
            "backward_fit_count": 8*folds, "fold_assignment_source": "provided" if fold_ids is not None else "seeded_permutation"}
