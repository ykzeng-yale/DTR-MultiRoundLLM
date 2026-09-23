"""Handcrafted deterministic fixtures; no sampler or fold-RNG calls are needed."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/e0"))
import stop_anchor_estimators as s

P = np.full(5, .2)


@pytest.fixture(autouse=True)
def forbid_sampling_and_fold_rng(monkeypatch):
    import simulator
    def prohibited(*args, **kwargs):
        raise AssertionError("this fixture must not sample data or randomize folds")
    monkeypatch.setattr(simulator, "simulate", prohibited)
    monkeypatch.setattr(s.history, "make_task_folds", prohibited)


def two_stage():
    # Same prefix, separate training/evaluation roots. Only terminal non-STOP Y differs.
    return dict(task=np.array([101, 501]), S=np.zeros((2, 2), int), A=np.ones((2, 2), int),
                B=np.full((2, 2), .2), elig=np.ones((2, 2), bool), Y=np.array([1., 0.]))


def observed_and_unseen():
    return dict(task=np.array([10, 20, 30, 40]), S=np.array([[0], [3], [1], [2]]),
                A=np.array([[0], [0], [1], [1]]), B=np.full((4, 1), .2),
                elig=np.ones((4, 1), bool), Y=np.array([0., 1., 0., 1.]))


def absorbing():
    d = dict(task=np.array([1, 2, 3, 4]), S=np.array([[0, 0], [3, -999], [1, 3], [3, 1]]),
             A=np.array([[1, 1], [0, 999], [2, 0], [1, 1]]),
             B=np.array([[.3, .5], [.1, np.nan], [.25, .4], [.6, .7]]),
             elig=np.array([[True, True], [True, False], [True, True], [True, True]]),
             Y=np.array([1., 1., 1., 0.]))
    return d


@pytest.mark.parametrize("representation", ["compressed", "history"])
@pytest.mark.parametrize("penalty", [0, 5])
def test_original_is_frozen_fitter_and_scorer_parity(representation, penalty):
    d = absorbing()
    expected = s.original.fit_regularized_q(d, 2, P, representation=representation, shrinkage=penalty, idx=[0, 1])
    fit = s.fit_stop_anchor_q(d, 2, P, representation=representation, shrinkage=penalty, mode="original", idx=[0, 1])
    assert fit["Q"] == expected["Q"] and fit["fallback"] == expected["fallback"]
    assert fit["training_support"] == expected["training_support"]
    np.testing.assert_array_equal(fit["v0"], expected["v0"])
    frozen = s.base.dr_scores(d, 2, P, expected["Q"], expected["fallback"], key=expected["key"])
    np.testing.assert_allclose(s.query_dr_scores(d, 2, P, fit["query"]), frozen, atol=1e-14, rtol=0)


@pytest.mark.parametrize("representation", ["compressed", "history"])
@pytest.mark.parametrize("penalty", [0, 5])
def test_exact_direct_adjustment_differs_from_own_backward_recursion(representation, penalty):
    d = two_stage()
    fits = {m: s.fit_stop_anchor_q(d, 2, P, representation=representation, shrinkage=penalty,
                                  mode=m, idx=[0]) for m in s.MODES}
    assert fits["original"]["v0"][1] == pytest.approx(1.)
    assert fits["evaluation_only"]["v0"][1] == pytest.approx(4/5)
    assert fits["recursive"]["v0"][1] == pytest.approx(16/25)
    scores = {m: s.query_dr_scores(d, 2, P, f["query"]) for m, f in fits.items()}
    assert scores["original"][1] == pytest.approx(0.)
    assert scores["evaluation_only"][1] == pytest.approx(-2/5)
    assert scores["recursive"][1] == pytest.approx(-9/25)
    increment = s.direct_stop_increment(d, 2, P, fits["original"]["query"])
    np.testing.assert_allclose(increment, [-2/5, -2/5], rtol=0, atol=1e-14)
    np.testing.assert_allclose(scores["original"] + increment, scores["evaluation_only"], atol=1e-14)
    # Direct mode leaves non-STOP tables fixed; recursive mode changes upstream Q.
    assert fits["evaluation_only"]["Q"] == fits["original"]["Q"]
    assert fits["evaluation_only"]["query"](1, 0, 1) == pytest.approx(1.)
    assert fits["recursive"]["query"](1, 0, 1) == pytest.approx(4/5)
    assert fits["recursive"]["query"](1, 1, 1) == pytest.approx(1.)


@pytest.mark.parametrize("mode", ["evaluation_only", "recursive"])
@pytest.mark.parametrize("penalty", [0, 5])
def test_observed_and_unseen_stop_and_honest_support(mode, penalty):
    d = observed_and_unseen()
    fit = s.fit_stop_anchor_q(d, 1, P, shrinkage=penalty, mode=mode, idx=[0, 1])
    assert [fit["query"](i, 0, 0) for i in range(4)] == [0., 1., 0., 0.]
    assert len(fit["training_support"][0]["cells"]) == 2
    assert len(fit["Q"][0]) == 2  # No held-out key is materialized as a trained cell.
    support = s.heldout_support(d, 1, np.array([2, 3]), fit)[0]["groups"]
    assert support["stop"]["counts"]["unseen_training_cell"] == 2
    assert support["stop"]["counts"]["structural"] == 2
    assert support["stop"]["counts"]["cell"] == 0
    assert support["stop"]["fallback_queries"] == 0
    assert support["nonstop"]["fallback_queries"] == 8
    for group in support.values():
        counts = group["counts"]
        assert counts["observed_training_cell"] + counts["unseen_training_cell"] == group["queries"]
        assert sum(counts[k] for k in ("structural", "cell", "action_pool", "stage_pool", "zero")) == group["queries"]
    raw = s.fit_stop_anchor_q(d, 1, P, shrinkage=penalty, mode="original", idx=[0, 1])
    assert raw["query"](2, 0, 0) == pytest.approx(.5)
    if penalty == 0:
        assert raw["query"](0, 0, 0) == 0 and raw["query"](1, 0, 0) == 1
    else:
        assert raw["query"](0, 0, 0) == pytest.approx(5/12)
        assert raw["query"](1, 0, 0) == pytest.approx(7/12)


def test_eq4_with_nonuniform_policy_observed_stop_and_absorbing_padding():
    d, policy = absorbing(), np.array([.1, .35, .2, .25, .1])
    for representation in ("compressed", "history"):
        fit = s.fit_stop_anchor_q(d, 2, policy, mode="original", representation=representation, idx=[0, 1, 3])
        direct = s.fit_stop_anchor_q(d, 2, policy, mode="evaluation_only", representation=representation, idx=[0, 1, 3])
        old = s.query_dr_scores(d, 2, policy, fit["query"])
        recomputed = s.query_dr_scores(d, 2, policy, direct["query"])
        np.testing.assert_allclose(old + s.direct_stop_increment(d, 2, policy, fit["query"]), recomputed, rtol=0, atol=1e-13)
        with pytest.raises(ValueError, match="active"):
            direct["query"](1, 1, 0)
    no_stop_policy = np.array([0., .25, .25, .25, .25])
    fit = s.fit_stop_anchor_q(d, 2, no_stop_policy, mode="original", idx=[0, 1])
    np.testing.assert_array_equal(s.direct_stop_increment(d, 2, no_stop_policy, fit["query"]), np.zeros(4))


def test_crossfit_shared_fits_folds_scores_and_variant_order(monkeypatch):
    d = absorbing()
    d = {k: np.repeat(v, 2, axis=0) for k, v in d.items()}
    d["task"] = [1, 1, "1", "1", 99, 99, 501, 501]
    fa = np.repeat([0, 1, 0, 1], 2)
    original_fitter, recursive_fitter = s.original.fit_regularized_q, s._recursive_fit
    calls = {"original": 0, "recursive": 0}
    def old(*args, **kwargs):
        calls["original"] += 1
        return original_fitter(*args, **kwargs)
    def rec(*args, **kwargs):
        calls["recursive"] += 1
        return recursive_fitter(*args, **kwargs)
    monkeypatch.setattr(s.original, "fit_regularized_q", old)
    monkeypatch.setattr(s, "_recursive_fit", rec)
    result = s.crossfit_stop_anchor_scores(d, 2, P, folds=2, fold_ids=fa)
    assert calls == {"original": 8, "recursive": 8}
    assert result["backward_fit_count"] == 16 and result["fold_assignment_source"] == "provided"
    assert result["task_labels"].tolist() == [1, "1", 99, 501]
    assert list(result["variants"]) == list(s.VARIANTS) and len(s.ESTIMATORS) == 24
    np.testing.assert_array_equal(result["episode_fold_ids"], fa)
    for prefix in s.original.VARIANTS:
        original_variant = result["variants"][prefix + "_original"]
        direct_variant = result["variants"][prefix + "_evaluation_only"]
        np.testing.assert_allclose(direct_variant["dr_scores"], original_variant["dr_scores"] + direct_variant["direct_increment_scores"])
        for ofit, dfit in zip(original_variant["fits"], direct_variant["fits"]):
            assert dfit["Q"] is ofit["Q"] and dfit["fallback"] is ofit["fallback"]
            assert dfit["training_support"] is ofit["training_support"]
            assert dfit["backward_fit_reused"] is True
    for variant in result["variants"].values():
        for fit in variant["fits"]:
            test = fit["test_indices"]
            np.testing.assert_array_equal(test, np.flatnonzero(fa == fit["fold"]))
            np.testing.assert_array_equal(variant["plugin_scores"][test], fit["v0"][test])
            np.testing.assert_allclose(variant["dr_scores"][test], s.query_dr_scores(d, 2, P, fit["query"])[test], rtol=0, atol=1e-13)


def test_heldout_nonstop_outcomes_private_fields_and_padding_cannot_change_fit():
    d = absorbing()
    altered = copy.deepcopy(d)
    altered["Y"][[0, 3]] = 1 - altered["Y"][[0, 3]]  # Only held-out non-STOP endpoints.
    altered["S"][1, 1], altered["A"][1, 1] = 123456, -98765
    altered["B"][1, 1] = -np.inf
    altered.update(e=np.array([99]*4), z=np.array([-100]*4), hidden="ignored")
    for mode in s.MODES:
        fit = s.fit_stop_anchor_q(d, 2, P, mode=mode, idx=[1, 2])
        other = s.fit_stop_anchor_q(altered, 2, P, mode=mode, idx=[1, 2])
        assert fit["Q"] == other["Q"] and fit["fallback"] == other["fallback"]
        assert fit["training_support"] == other["training_support"]
        np.testing.assert_array_equal(fit["v0"], other["v0"])
        assert not np.array_equal(s.query_dr_scores(d, 2, P, fit["query"])[[0, 3]],
                                  s.query_dr_scores(altered, 2, P, other["query"])[[0, 3]])


@pytest.mark.parametrize("mode", s.MODES)
def test_empty_training_later_stage_retains_structural_not_fake_support(mode):
    d = absorbing()
    fit = s.fit_stop_anchor_q(d, 2, P, mode=mode, idx=[1])  # Training root stops immediately.
    assert fit["training_support"][1]["trajectory_count"] == 0
    assert fit["training_support"][1]["cells"] == {}
    assert fit["Q"][1] == {}
    assert fit["query"](2, 1, 0) == (0. if mode == "original" else 1.)
    assert np.isfinite(s.query_dr_scores(d, 2, P, fit["query"])).all()


@pytest.mark.parametrize("defect", ["nonbinary", "contradictory_stop", "early_nonstop", "reactivated_stop"])
def test_structural_endpoint_contract_rejects_invalid_data(defect):
    d = absorbing()
    if defect == "nonbinary": d["Y"][0] = .5
    elif defect == "contradictory_stop": d["Y"][1] = 0
    elif defect == "early_nonstop": d["A"][1, 0] = 1
    else: d["A"][0, 0] = 0
    with pytest.raises(ValueError):
        s.fit_stop_anchor_q(d, 2, P)


@pytest.mark.parametrize("kwargs", [dict(mode="other"), dict(representation="oracle"),
    dict(shrinkage=-1), dict(shrinkage=True), dict(shrinkage=np.nan), dict(idx=[0, 0])])
def test_invalid_settings(kwargs):
    with pytest.raises(ValueError):
        s.fit_stop_anchor_q(two_stage(), 2, P, **kwargs)


@pytest.mark.parametrize("defect", ["one_fold", "split_root", "missing_fold", "float_fold"])
def test_invalid_shared_folds(defect):
    d, fa, folds = absorbing(), np.array([0, 1, 0, 1]), 2
    if defect == "one_fold": folds = 1
    elif defect == "split_root": d["task"][1] = d["task"][0]
    elif defect == "missing_fold": fa[:] = 0
    else: fa = fa.astype(float)
    with pytest.raises(ValueError, match="fold"):
        s.crossfit_stop_anchor_scores(d, 2, P, folds=folds, fold_ids=fa)


def test_external_fit_reuse_is_not_a_public_argument():
    with pytest.raises(TypeError, match="original_fit"):
        s.fit_stop_anchor_q(two_stage(), 2, P, original_fit={})
