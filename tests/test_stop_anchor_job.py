"""Handcrafted full-size arrays and mocked fits only; never draw a dataset.

Fold assignments are deterministic fixtures. These tests check the adapter and
event contract; independent handcrafted estimator tests cover fitted arithmetic.
"""
import copy
import csv
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/e0"))
import stop_anchor_job as j


def plan_job():
    plan = json.loads((j.ROOT / j.PLAN_PATH).read_bytes())
    row = next(csv.DictReader((j.ROOT / j.SEED_PATH).read_text().splitlines()))
    row["replicate"] = int(row["replicate"])
    return plan, row


def handcrafted():
    task = np.repeat(np.arange(230), 40)
    correct = task >= 115
    S = np.full((9200, 3), -1, dtype=int)
    S[:, 0] = np.where(correct, 3, 0)
    A = np.zeros((9200, 3), int)
    B = np.ones((9200, 3))
    B[:, 0] = j.sim.make_beh(2.5, .02, gz=0.)[0, S[:, 0], 0]
    elig = np.zeros((9200, 3), bool)
    elig[:, 0] = True
    return dict(task=task, S=S, A=A, B=B, elig=elig, Y=correct.astype(float),
                e=np.zeros(9200, int), z=np.zeros(9200, int))


@pytest.fixture(autouse=True)
def no_draws(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("real sampler invocation forbidden in source fixtures")
    monkeypatch.setattr(j.sim, "simulate", forbidden)
    def folds(tasks, folds, seed):
        assert folds == 3 and type(seed) is int and seed > 2**64
        index = np.asarray(tasks, dtype=int)
        task_folds = np.arange(230) % 3
        return dict(task_labels=np.arange(230), task_index=index,
                    task_fold_ids=task_folds, episode_fold_ids=task_folds[index])
    monkeypatch.setattr(j.core.history, "make_task_folds", folds)


@pytest.fixture
def mocked_fits(monkeypatch):
    """Synthetic score boundaries expose accidental refitting/scalar-STOP use."""
    calls, structural_queries = [], []
    def fit(data, T, policy, *, representation, shrinkage, mode, idx):
        assert T == 3
        calls.append((representation, shrinkage, mode, idx.copy()))
        key = ((lambda i, t: j.core.history.history_key(data, i, t)) if representation == "history"
               else (lambda i, t: (int(data["S"][i, t]), t)))
        Q, fb, stages = [{} for _ in range(3)], [dict.fromkeys(range(5), .5) for _ in range(3)], []
        for t in range(3):
            selected = idx[data["elig"][idx, t]]
            cells = {}
            for state in (0, 3):
                ii = selected[data["S"][selected, t] == state]
                if not len(ii):
                    continue
                h = key(ii[0], t)
                value = float(state == 3) if mode == "recursive" else .4
                Q[t][h] = {0: value}
                cells[h, 0] = dict(root_count=len(set(data["task"][ii])), trajectory_count=len(ii),
                                    q_cell=float(state == 3), q_pool=.5, q_fitted=value)
            actions = {a: dict(root_count=len(set(data["task"][selected])) if a == 0 else 0,
                              trajectory_count=len(selected) if a == 0 else 0) for a in range(5)}
            stages.append(dict(stage=t, trajectory_count=len(selected), root_count=len(set(data["task"][selected])),
                               stage_mean=.5, actions=actions, cells=cells))
        result = dict(representation=representation, shrinkage=shrinkage, mode=mode, Q=Q,
                      fallback=fb, key=key, training_support=stages, backward_fit_reused=False)
        result["query"] = j.core._query(data, result, anchored=mode != "original")
        result["v0"] = (.4 + .2*(data["S"][:, 0] == 3)) if mode == "recursive" else np.full(9200, .48)
        return result
    monkeypatch.setattr(j.core, "fit_stop_anchor_q", fit)
    monkeypatch.setattr(j.core.base, "dr_scores", lambda *args, **kwargs: np.full(9200, .75))
    def structural_score(data, T, policy, query):
        observed = [query(0, 0, 0), query(4600, 0, 0)]
        assert observed == [0., 1.]  # A scalar fallback cannot satisfy this.
        structural_queries.append(observed)
        return np.full(9200, .25)
    monkeypatch.setattr(j.core, "query_dr_scores", structural_score)
    def direct(data, T, policy, query):
        assert query(0, 0, 0) == query(4600, 0, 0) == .4
        return np.full(9200, .02)
    monkeypatch.setattr(j.core, "direct_stop_increment", direct)
    def support(data, T, test, fit):
        return [dict(stage=t, active_heldout_trajectories=int(data["elig"][test, t].sum()),
                     groups={"fixture": "mocked support; actual core tested separately"}) for t in range(T)]
    monkeypatch.setattr(j.core, "heldout_support", support)
    return dict(calls=calls, structural_queries=structural_queries, fit=fit)


@pytest.mark.parametrize("defect", ["scientific", "prose", "pair", "variant_order", "int_seed", "wrong_seed", "leading_zero", "bool_replicate"])
def test_full_plan_or_identity_tamper_rejected_before_sampler(monkeypatch, defect):
    plan, job = plan_job()
    called = []
    monkeypatch.setattr(j.sim, "simulate", lambda *args, **kwargs: called.append(True))
    if defect == "scientific": plan["n_tasks"] = 229
    elif defect == "prose": plan["status"] = "changed declaration"
    elif defect == "pair": plan["primary_pair"]["metric"] = "different metric"
    elif defect == "variant_order": plan["variant_order"].reverse()
    elif defect == "int_seed": job["data_seed"] = int(job["data_seed"])
    elif defect == "wrong_seed": job["fold_seed"] = str(int(job["fold_seed"]) + 1)
    elif defect == "leading_zero": job["data_seed"] = "0" + job["data_seed"]
    else: job["replicate"] = False
    with pytest.raises(ValueError):
        j.evaluate_job(plan, job)
    assert not called


def test_complete_mocked_job_has_ordered_incremental_events_exact_sharing_and_scores(mocked_fits):
    plan, job = plan_job()
    events = []
    out = j.evaluate_job(plan, job, data=handcrafted(), on_event=events.append)
    assert [e["event"] for e in events] == ["prepared"] + [x for _ in range(12) for x in ("variant_started", "variant")]
    assert [e["variant"] for e in events if e["event"] == "variant"] == list(j.core.VARIANTS)
    assert [r["estimator"] for r in out["records"]] == list(j.ESTIMATORS)
    assert out["all_points_completed"] and len(out["records"]) == 24
    assert out["resources"]["sampler_attempts"] == 0
    assert out["resources"]["backward_fit_attempts"] == out["resources"]["backward_fits_completed"] == 24
    assert len(mocked_fits["calls"]) == 24 and len(mocked_fits["structural_queries"]) == 12
    for name, variant in out["variants"].items():
        assert variant["root_labels"] == list(range(230))
        assert variant["dataset_sha256"] == out["provenance"]["dataset"]["sha256"]
        assert variant["fold_sha256"] == out["provenance"]["folds"]["sha256"]
        assert len(variant["support"]) == 3
        assert variant["backward_fit_attempts"] == (0 if "evaluation_only" in name else 3)
        dr_expected = .77 if "evaluation_only" in name else .25 if name.endswith("recursive") else .75
        for row in variant["records"]:
            method = row["estimator"].split(":")[1]
            means = variant["root_means"][method]
            assert len(means) == 230 and row["estimate"] == pytest.approx(np.mean(means))
            if method == "dr":
                assert row["estimate"] == pytest.approx(dr_expected)
                se = float(np.std(means, ddof=1)/math.sqrt(230))
                assert row["interval"]["se"] == pytest.approx(se)
                assert row["interval"]["lo"] == pytest.approx(row["estimate"] - 1.96*se)
            else:
                assert "interval" not in row
    for fold in range(3):
        train = mocked_fits["calls"][fold][3]
        for offset in range(0, 24, 3):
            np.testing.assert_array_equal(train, mocked_fits["calls"][offset + fold][3])
    assert type(out["identity"]["job"]["data_seed"]) is str
    assert type(out["provenance"]["fold_seed"]) is str
    json.dumps(out, allow_nan=False)


def test_arrays_round_trip_hashes_and_seed_constructor_without_draws(monkeypatch):
    plan, job = plan_job()
    seen = []
    def sampler(n_tasks, runs, T, kernel, behavior, rng, **kwargs):
        assert (n_tasks, runs, T) == (230, 40, 3)
        assert kwargs == dict(mislabel=0., template_sd=0., cmult=1.)
        expected = np.random.PCG64(np.random.SeedSequence(int(job["data_seed"])))
        assert rng.bit_generator.state == expected.state  # Inspect, never draw.
        seen.append(True)
        return handcrafted()
    monkeypatch.setattr(j.sim, "simulate", sampler)
    class PreparedStop(Exception): pass
    def stop(event):
        assert event["event"] == "prepared"
        restored = {k: np.asarray(v["values"], dtype=v["dtype"]).reshape(v["shape"])
                    for k, v in event["arrays"].items()}
        assert set(restored) == set(j.ARRAY_NAMES)
        assert j._fingerprint(restored) == event["provenance"]["dataset"]
        assert event["provenance"]["data_seed"] == job["data_seed"]
        folds = event["provenance"]["folds"]
        assert folds["sha256"] == j._digest({k: v for k, v in folds.items() if k != "sha256"})
        assert set(event["provenance"]["source_sha256"]) == set(j.SOURCE_PATHS)
        raise PreparedStop()
    with pytest.raises(PreparedStop):
        j.evaluate_job(plan, job, on_event=stop)
    assert seen == [True]


def test_earlier_terminal_variants_survive_later_recursive_failure(monkeypatch, mocked_fits):
    plan, job = plan_job()
    def fit(*args, **kwargs):
        if (kwargs["representation"], kwargs["shrinkage"], kwargs["mode"]) == ("compressed", 0, "recursive"):
            raise RuntimeError("injected later fit failure")
        return mocked_fits["fit"](*args, **kwargs)
    monkeypatch.setattr(j.core, "fit_stop_anchor_q", fit)
    events = []
    out = j.evaluate_job(plan, job, data=handcrafted(), on_event=events.append)
    assert all(r["status"] == "completed" for r in out["records"][:4])
    assert all(r["status"] == "failed" for r in out["records"][4:6])
    assert all(r["status"] == "completed" for r in out["records"][6:])
    failed = out["variants"]["compressed_lambda0_recursive"]
    assert failed["backward_fit_attempts"] == 1 and failed["backward_fits_completed"] == 0
    assert out["resources"]["backward_fit_attempts"] == 22
    assert out["resources"]["backward_fits_completed"] == 21
    assert [e["variant"] for e in events if e["event"] == "variant"] == list(j.core.VARIANTS)


def test_original_failure_is_explicit_direct_dependency_failure_but_recursive_runs(monkeypatch, mocked_fits):
    plan, job = plan_job()
    def fit(*args, **kwargs):
        if (kwargs["representation"], kwargs["shrinkage"], kwargs["mode"]) == ("compressed", 0, "original"):
            raise RuntimeError("original unavailable")
        return mocked_fits["fit"](*args, **kwargs)
    monkeypatch.setattr(j.core, "fit_stop_anchor_q", fit)
    out = j.evaluate_job(plan, job, data=handcrafted())
    direct = out["variants"]["compressed_lambda0_evaluation_only"]
    assert direct["dependency_failure"] and direct["backward_fit_attempts"] == 0
    assert all("dependency_unavailable" in r["reason"] for r in direct["records"])
    assert all(r["status"] == "completed" for r in out["variants"]["compressed_lambda0_recursive"]["records"])


@pytest.mark.parametrize("boundary", ["prepared", "variant_started", "variant", "job_failed"])
def test_callback_exception_is_never_swallowed(boundary, mocked_fits):
    plan, job = plan_job()
    events = []
    class OutputCap(Exception): pass
    def event(e):
        events.append(e)
        if e["event"] == boundary:
            raise OutputCap("outer journal refuses write")
    data = handcrafted()
    if boundary == "job_failed": data["Y"][0] = 1
    with pytest.raises(OutputCap):
        j.evaluate_job(plan, job, data=data, on_event=event)
    assert events[-1]["event"] == boundary
    if boundary in ("prepared", "variant_started", "job_failed"):
        assert mocked_fits["calls"] == []
    else:
        assert len(mocked_fits["calls"]) == 3
        assert all(r["status"] == "completed" for r in events[-1]["records"])


@pytest.mark.parametrize("defect", ["roots", "stop_outcome", "propensity", "padding", "object_task"])
def test_preparation_failure_preserves_all24_failed_slots_and_no_fit(defect, mocked_fits):
    plan, job = plan_job()
    data = handcrafted()
    if defect == "roots": data["task"][0] = 1
    elif defect == "stop_outcome": data["Y"][0] = 1
    elif defect == "propensity": data["B"][0, 0] = .3
    elif defect == "padding": data["B"][0, 1] = np.nan
    else: data["task"] = data["task"].astype(object)
    events = []
    out = j.evaluate_job(plan, job, data=data, on_event=events.append)
    assert [e["event"] for e in events] == ["job_failed"]
    assert len(out["records"]) == 24 and all(r["status"] == "failed" for r in out["records"])
    assert out["arrays"] is None and not mocked_fits["calls"]
    assert out["resources"]["backward_fit_attempts"] == 0


def test_point_interval_failure_stays_completed_and_equal_root_weighting(monkeypatch):
    plan, job = plan_job()
    identity = j.expected_job_identity(plan, job)
    means = j._root_means([0., 1., 1.], np.array([0, 0, 1]))
    np.testing.assert_array_equal(means, [.5, 1.])
    record = j._point_record(identity, "history_lambda5_recursive:dr", means)
    assert record["estimate"] == .75 and record["interval"]["se"] == .25
    def fail(*args, **kwargs): raise ValueError("injected interval failure")
    monkeypatch.setattr(np, "std", fail)
    record = j._point_record(identity, "history_lambda5_recursive:dr", means)
    assert record["status"] == "completed" and record["estimate"] == .75
    assert record["interval"]["status"] == "failed"
