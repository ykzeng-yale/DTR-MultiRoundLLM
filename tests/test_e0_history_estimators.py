"""Handcrafted finite tables only: no Monte Carlo, model or candidate execution."""
import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "e0"))
import history_estimators as h


def fixture():
    # Both folds contain both prefixes; each final arm appears once per task.
    # STOP seals the common wrong S1=1, so its outcome is zero in both prefixes.
    prefix = np.repeat([0, 2, 0, 2], 5)
    actions = np.tile(np.arange(5), 4)
    return dict(task=np.repeat([101, 999, -42, 7001], 5),
                S=np.column_stack((prefix, np.ones(20, int))),
                A=np.column_stack((np.ones(20, int), actions)),
                B=np.full((20, 2), .2), elig=np.ones((20, 2), bool),
                Y=((prefix == 2) & (actions != 0)).astype(float),
                e=np.arange(20), z=np.arange(20) % 2), np.repeat([0, 0, 1, 1], 5)


def test_same_current_state_different_prefix_backpropagates_distinct_values():
    d, folds = fixture()
    result = h.crossfit_history_scores(d, 2, h.base.UNIF5, folds=2, fold_ids=folds)
    Q = result["fits"][0]["Q"]
    low, high = h.history_key(d, 0, 1), h.history_key(d, 5, 1)
    assert low != high and d["S"][0, 1] == d["S"][5, 1]
    assert Q[1][low] == dict.fromkeys(range(5), 0.0)
    assert Q[1][high] == {0: 0.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}
    assert Q[0][h.history_key(d, 0, 0)][1] == 0.0
    assert Q[0][h.history_key(d, 5, 0)][1] == pytest.approx(.8)
    compressed, _, _ = h.base.fit_q(d, 2, h.base.UNIF5, idx=np.flatnonzero(folds == 1))
    assert compressed[0][(0, 0)][1] == pytest.approx(.4)
    assert compressed[0][(2, 0)][1] == pytest.approx(.4)


def test_key_uses_prior_actions_but_never_current_or_future_information():
    d = dict(S=np.array([[0, 1, 3]]), A=np.array([[1, 3, 0]]), Y=np.array([1.]),
             B=np.array([[.2, .2, .2]]), e=[3], z=[1], task=[999], template=[4])
    key = h.history_key(d, 0, 1)
    assert key == ((0, 1), (1,))
    changed = copy.deepcopy(d)
    changed["S"][0, 2] = 0
    changed["A"][0, 1:] = [0, 4]
    for name in ("Y", "B", "e", "z", "task", "template"):
        changed[name] = None  # Must not even be read by the key.
    assert h.history_key(changed, 0, 1) == key
    changed["A"][0, 0] = 2
    assert h.history_key(changed, 0, 1) != key


def test_heldout_outcomes_cannot_change_its_fold_fit_or_plugin():
    d, folds = fixture()
    first = h.crossfit_history_scores(d, 2, h.base.UNIF5, folds=2, fold_ids=folds)
    changed = copy.deepcopy(d)
    changed["Y"][folds == 0] = 1 - changed["Y"][folds == 0]
    second = h.crossfit_history_scores(changed, 2, h.base.UNIF5, folds=2, fold_ids=folds)
    for key in ("Q", "fallback"):
        assert first["fits"][0][key] == second["fits"][0][key]
    np.testing.assert_array_equal(first["plugin_scores"][folds == 0], second["plugin_scores"][folds == 0])
    assert not np.array_equal(first["dr_scores"][folds == 0], second["dr_scores"][folds == 0])


def test_plugin_and_dr_reuse_exact_same_fit_and_key(monkeypatch):
    d, folds = fixture()
    original_fit, original_dr = h.base.fit_q, h.base.dr_scores
    calls = []

    def fit(*args, **kwargs):
        output = original_fit(*args, **kwargs)
        calls.append((output, kwargs["key"], kwargs["idx"].copy()))
        return output

    def dr(data, T, policy, Q, fallback, key=None):
        output, fitted_key, _ = calls[-1]
        assert Q is output[0] and fallback is output[1] and key is fitted_key
        return original_dr(data, T, policy, Q, fallback, key=key)

    monkeypatch.setattr(h.base, "fit_q", fit)
    monkeypatch.setattr(h.base, "dr_scores", dr)
    result = h.crossfit_history_scores(d, 2, h.base.UNIF5, folds=2, fold_ids=folds)
    assert len(calls) == 2
    for fold, (output, key, train) in enumerate(calls):
        np.testing.assert_array_equal(train, np.flatnonzero(folds != fold))
        np.testing.assert_array_equal(result["plugin_scores"][folds == fold], output[2][folds == fold])
        np.testing.assert_array_equal(result["dr_scores"][folds == fold], original_dr(d, 2, h.base.UNIF5, *output[:2], key=key)[folds == fold])


def test_unseen_cells_use_training_fallback_not_heldout_or_oracle():
    # One decision: training has only RETRY with Y=1, held-out has only STOP Y=0.
    d = dict(task=np.array([100, 100, 999, 999]), S=np.array([[0], [0], [1], [1]]),
             A=np.array([[0], [0], [1], [1]]), B=np.full((4, 1), .2),
             elig=np.ones((4, 1), bool), Y=np.array([0., 0., 1., 1.]))
    result = h.crossfit_history_scores(d, 1, h.base.UNIF5, folds=2, fold_ids=[0, 0, 1, 1])
    assert result["fits"][0]["fallback"] == [dict.fromkeys(range(5), 1.0)]
    assert result["plugin_scores"][:2].tolist() == [1., 1.]
    # The wrapper does not fill the unseen STOP cell with known simulator truth 0.
    assert result["dr_scores"][:2].tolist() == [0., 0.]


def test_valid_early_stop_ignores_inactive_state_action_and_propensity_padding():
    # Each task has a correct initial artifact sealed by STOP and a distinct
    # continuing wrong artifact sealed at turn 2. Inactive turn 2 is not data.
    d = dict(task=np.array([101, 101, 9001, 9001]),
             S=np.array([[3, -1], [0, 1], [3, -1], [0, 1]]),
             A=np.array([[0, 0], [1, 0], [0, 0], [1, 0]]),
             B=np.array([[.4, 1.], [.2, .3], [.4, 1.], [.2, .3]]),
             elig=np.array([[True, False], [True, True], [True, False], [True, True]]),
             Y=np.array([1., 0., 1., 0.]))
    folds = [0, 0, 1, 1]
    initial = h.crossfit_history_scores(d, 2, h.base.UNIF5, folds=2, fold_ids=folds)
    changed = copy.deepcopy(d)
    changed["S"][~d["elig"]] = [987654, -4321]
    changed["A"][~d["elig"]] = [987654, -4321]
    changed["B"][~d["elig"]] = np.nan
    padded = h.crossfit_history_scores(changed, 2, h.base.UNIF5, folds=2, fold_ids=folds)
    for name in ("plugin_scores", "dr_scores"):
        assert np.isfinite(padded[name]).all()
        np.testing.assert_array_equal(initial[name], padded[name])
    for original_fit, padded_fit in zip(initial["fits"], padded["fits"]):
        assert original_fit["Q"] == padded_fit["Q"]
        assert original_fit["fallback"] == padded_fit["fallback"]


@pytest.mark.parametrize("labels", [[101, -77, 99999, 4], ["task-z", "task-a", "task-d", "task-b"], [101, "task-a", -4, "task-b"]])
def test_arbitrary_noncontiguous_task_labels_keep_repeats_together(labels):
    task = np.repeat(np.array(labels, dtype=object), [1, 3, 2, 4])
    first = h.make_task_folds(task, folds=2, seed=19)
    second = h.make_task_folds(task, folds=2, seed=19)
    for name in first:
        np.testing.assert_array_equal(first[name], second[name])
    for k in range(4):
        assert len(np.unique(first["episode_fold_ids"][first["task_index"] == k])) == 1
    assert sorted(np.unique(first["episode_fold_ids"])) == [0, 1]
    # Scores are summarized equally across tasks, not equally across episodes.
    score = first["task_index"].astype(float)
    assert h.base.task_clustered(first["task_index"], score)[0] == pytest.approx(1.5)
    assert score.mean() != pytest.approx(1.5)


def test_crossfit_preserves_mixed_label_types_in_input_lists():
    d, folds = fixture()
    d["task"] = [label for label in [1, "1", 300, "300"] for _ in range(5)]
    result = h.crossfit_history_scores(d, 2, h.base.UNIF5, folds=2, fold_ids=folds)
    assert result["task_labels"].tolist() == [1, "1", 300, "300"]
    assert len(result["task_fold_ids"]) == 4
    np.testing.assert_array_equal(result["episode_fold_ids"], folds)


@pytest.mark.parametrize("folds,task", [(1, [1, 2]), (3, [1, 2]), (2, [7, 7]), (True, [1, 2]), (2.0, [1, 2])])
def test_requires_at_least_two_tasks_and_two_nonempty_folds(folds, task):
    with pytest.raises(ValueError, match="fold"):
        h.make_task_folds(task, folds=folds)


@pytest.mark.parametrize("defect", ["split_task", "missing_fold", "float_folds", "zero_propensity", "invalid_policy", "reactivation"])
def test_invalid_assignments_and_estimating_inputs_fail_closed(defect):
    d, folds = fixture()
    policy = h.base.UNIF5.copy()
    if defect == "split_task":
        folds[0] = 1
    elif defect == "missing_fold":
        folds[:] = 0
    elif defect == "float_folds":
        folds = folds.astype(float)
    elif defect == "zero_propensity":
        d["B"][0, 0] = 0
    elif defect == "invalid_policy":
        policy[0] = -.1
    else:
        d["A"][0, 0] = 0
    with pytest.raises(ValueError):
        h.crossfit_history_scores(d, 2, policy, folds=2, fold_ids=folds)
