"""Deterministic handcrafted tables only: no sampled data or model execution."""
import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "e0"))
import regularized_history_estimators as r

P = r.base.UNIF5


def one_stage(states, outcomes, *, tasks=None, actions=None):
    n = len(states)
    return dict(task=np.arange(n) if tasks is None else tasks,
                S=np.asarray(states, dtype=int)[:, None],
                A=np.ones((n, 1), int) if actions is None else np.asarray(actions, dtype=int)[:, None],
                B=np.full((n, 1), .2), elig=np.ones((n, 1), bool), Y=np.asarray(outcomes, float))


def prefixes():
    # Ten distinct roots: five per prefix, each final action represented once.
    s0 = np.repeat([0, 2], 5)
    a1 = np.tile(np.arange(5), 2)
    return dict(task=np.arange(10), S=np.column_stack((s0, np.zeros(10, int))),
                A=np.column_stack((np.ones(10, int), a1)), B=np.full((10, 2), .2),
                elig=np.ones((10, 2), bool), Y=((s0 == 2) & (a1 != 0)).astype(float))


def two_folds():
    d = prefixes()
    doubled = {k: np.concatenate([v, v]) for k, v in d.items()}
    doubled["task"] = np.array([*range(101, 111), *range(501, 511)])
    return doubled, np.repeat([0, 1], 10)


@pytest.mark.parametrize("representation", ["compressed", "history"])
def test_lambda_zero_matches_existing_raw_fit_and_dr(representation):
    d = prefixes()
    fit = r.fit_regularized_q(d, 2, P, representation=representation, shrinkage=0)
    key = fit["key"]
    q, fb, v0 = r.base.fit_q(d, 2, P, key=key)
    assert fit["Q"] == q and fit["fallback"] == fb
    np.testing.assert_array_equal(fit["v0"], v0)
    np.testing.assert_array_equal(r.base.dr_scores(d, 2, P, q, fb, key=key),
                                  r.base.dr_scores(d, 2, P, fit["Q"], fit["fallback"], key=key))


def test_m_five_is_half_shrinkage_and_large_support_keeps_cell_signal():
    d = one_stage([0] * 5 + [1] * 5, [1] * 5 + [0] * 5)
    fit = r.fit_regularized_q(d, 1, P, representation="compressed")
    cell = fit["training_support"][0]["cells"][((0, 0), 1)]
    assert cell == dict(trajectory_count=5, root_count=5, q_cell=1., q_pool=.5, q_fitted=.75)
    large = one_stage([0] * 100 + [1] * 100, [1] * 100 + [0] * 100)
    fit = r.fit_regularized_q(large, 1, P, representation="compressed")
    assert fit["Q"][0][(0, 0)][1] == pytest.approx(102.5 / 105)


def test_cell_and_pool_means_are_episode_weighted_roots_only_control_penalty():
    d = one_stage([0, 0, 0, 0, 1], [1, 1, 1, 0, 0], tasks=[99, 99, 99, 10, 42])
    fit = r.fit_regularized_q(d, 1, P, representation="compressed")
    cell = fit["training_support"][0]["cells"][((0, 0), 1)]
    assert cell["root_count"] == 2 and cell["trajectory_count"] == 4
    assert cell["q_cell"] == .75 and cell["q_pool"] == .6
    assert cell["q_fitted"] == pytest.approx((2 * .75 + 5 * .6) / 7)


@pytest.mark.parametrize("representation", ["compressed", "history"])
def test_global_episode_duplication_preserves_root_support_and_shrinkage(representation):
    d = prefixes()
    fit = r.fit_regularized_q(d, 2, P, representation=representation)
    duplicated = {k: np.repeat(v, 2, axis=0) for k, v in d.items()}
    dupfit = r.fit_regularized_q(duplicated, 2, P, representation=representation)
    for t in range(2):
        assert fit["fallback"][t] == pytest.approx(dupfit["fallback"][t])
        for key, values in fit["Q"][t].items():
            assert values == pytest.approx(dupfit["Q"][t][key])
        for cell, counts in fit["training_support"][t]["cells"].items():
            doubled = dupfit["training_support"][t]["cells"][cell]
            assert doubled["root_count"] == counts["root_count"]
            assert doubled["trajectory_count"] == 2 * counts["trajectory_count"]


def test_each_variant_backpropagates_its_own_shrunk_values():
    d = prefixes()
    fit = r.fit_regularized_q(d, 2, P)
    low = fit["key"](0, 1)
    high = fit["key"](5, 1)
    assert fit["Q"][1][low][1] == pytest.approx(5 / 12)
    assert fit["Q"][1][high][1] == pytest.approx(7 / 12)
    assert fit["Q"][0][fit["key"](0, 0)][1] == pytest.approx(11 / 30)
    assert fit["Q"][0][fit["key"](5, 0)][1] == pytest.approx(13 / 30)
    # Shrinking the already fitted raw stage-zero table would incorrectly give .2/.6.
    assert fit["Q"][0][fit["key"](0, 0)][1] != pytest.approx(.2)
    compressed = r.fit_regularized_q(d, 2, P, representation="compressed")
    assert compressed["Q"][0][(0, 0)][1] == pytest.approx(.4)
    assert compressed["Q"][0][(2, 0)][1] == pytest.approx(.4)


def test_stop_is_shrunk_without_oracle_exception():
    d = one_stage([0, 3], [0, 1], actions=[0, 0])
    fit = r.fit_regularized_q(d, 1, P, representation="compressed")
    assert fit["Q"][0][(0, 0)][0] == pytest.approx(5 / 12)
    assert fit["Q"][0][(3, 0)][0] == pytest.approx(7 / 12)


def test_training_only_action_stage_zero_fallbacks_and_heldout_frequencies():
    # Fold0 has an unseen first-state and continuing stage; fold1 training stops immediately.
    d = dict(task=[101, 101, 9001, 9001], S=np.array([[0, 1], [0, 1], [3, -1], [3, -1]]),
             A=np.array([[1, 0], [1, 0], [0, 999], [0, -222]]),
             B=np.array([[.2, .2], [.2, .2], [.2, np.nan], [.2, np.nan]]),
             elig=np.array([[True, True], [True, True], [True, False], [True, False]]),
             Y=np.array([0., 0., 1., 1.]))
    result = r.crossfit_regularized_history_scores(d, 2, P, folds=2, fold_ids=[0, 0, 1, 1])
    for variant in result["variants"].values():
        fit = variant["fits"][0]
        assert fit["fallback"] == [dict.fromkeys(range(5), 1.), dict.fromkeys(range(5), 0.)]
        first, second = fit["heldout_support"]
        assert first["queries_by_source"] == dict(cell=0, action_pool=2, stage_pool=8, zero=0)
        assert first["fallback_frequency"] == 1.
        assert second["queries_by_source"] == dict(cell=0, action_pool=0, stage_pool=0, zero=10)
        assert second["observed_action_fallback_frequency"] == 1.
        assert variant["fits"][1]["heldout_support"][1]["fallback_frequency"] is None
        assert np.isfinite(variant["dr_scores"]).all()
    changed = copy.deepcopy(d)
    changed["S"][~d["elig"]] = [123456, -98765]
    changed["A"][~d["elig"]] = [-334, 55555]
    padded = r.crossfit_regularized_history_scores(changed, 2, P, folds=2, fold_ids=[0, 0, 1, 1])
    for name, variant in result["variants"].items():
        for metric in ("plugin_scores", "dr_scores"):
            np.testing.assert_array_equal(variant[metric], padded["variants"][name][metric])


def test_heldout_outcomes_leave_fits_plugin_and_support_unchanged():
    d, fa = two_folds()
    first = r.crossfit_regularized_history_scores(d, 2, P, folds=2, fold_ids=fa)
    changed = copy.deepcopy(d)
    changed["Y"][fa == 0] = 1 - changed["Y"][fa == 0]
    second = r.crossfit_regularized_history_scores(changed, 2, P, folds=2, fold_ids=fa)
    for name, variant in first["variants"].items():
        other = second["variants"][name]
        for field in ("Q", "fallback", "training_support", "heldout_support"):
            assert variant["fits"][0][field] == other["fits"][0][field]
        np.testing.assert_array_equal(variant["plugin_scores"][fa == 0], other["plugin_scores"][fa == 0])
        assert not np.array_equal(variant["dr_scores"][fa == 0], other["dr_scores"][fa == 0])


def test_shared_folds_and_exact_same_nuisance_for_plugin_dr(monkeypatch):
    d, fa = two_folds()
    # Mixed scalar labels survive as distinct roots, including integer1 versus string1.
    d["task"] = [1, "1", *range(2, 20)]
    original_fit, original_dr = r.fit_regularized_q, r.base.dr_scores
    calls = []
    def fit(*args, **kwargs):
        value = original_fit(*args, **kwargs)
        calls.append(value)
        return value
    def dr(data, T, pol, Q, fb, key=None):
        assert Q is calls[-1]["Q"] and fb is calls[-1]["fallback"] and key is calls[-1]["key"]
        return original_dr(data, T, pol, Q, fb, key=key)
    monkeypatch.setattr(r, "fit_regularized_q", fit)
    monkeypatch.setattr(r.base, "dr_scores", dr)
    result = r.crossfit_regularized_history_scores(d, 2, P, folds=2, fold_ids=fa)
    assert len(calls) == 8 and result["task_labels"].tolist()[:2] == [1, "1"]
    np.testing.assert_array_equal(result["episode_fold_ids"], fa)
    for variant in result["variants"].values():
        for f in variant["fits"]:
            np.testing.assert_array_equal(f["train_indices"], np.flatnonzero(fa != f["fold"]))
            np.testing.assert_array_equal(variant["plugin_scores"][f["test_indices"]], f["v0"][f["test_indices"]])
    monkeypatch.setattr(r.base, "dr_scores", original_dr)
    legacy = r.history.crossfit_history_scores(d, 2, P, folds=2, fold_ids=fa)
    for metric in ("plugin_scores", "dr_scores"):
        np.testing.assert_array_equal(result["variants"]["history_lambda0"][metric], legacy[metric])


@pytest.mark.parametrize("penalty", [-1, float("nan"), float("inf"), True, "5"])
def test_invalid_shrinkage_is_rejected(penalty):
    with pytest.raises(ValueError, match="shrinkage"):
        r.fit_regularized_q(prefixes(), 2, P, shrinkage=penalty)


@pytest.mark.parametrize("defect", ["one_fold", "too_many", "split_root", "missing_fold", "float_fold"])
def test_same_root_fold_validation_as_existing_helper(defect):
    d, fa = two_folds()
    folds = 2
    if defect == "one_fold": folds = 1
    elif defect == "too_many": folds = 21
    elif defect == "split_root": d["task"][10] = d["task"][0]
    elif defect == "missing_fold": fa[:] = 0
    else: fa = fa.astype(float)
    with pytest.raises(ValueError, match="fold"):
        r.crossfit_regularized_history_scores(d, 2, P, folds=folds, fold_ids=fa)
