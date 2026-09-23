"""Connected adapter tests: handwritten data or mocked sampler, never sampled data."""
import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "e0"))
import regularization_job as j


def plan_job(cell=0):
    plan = json.loads((j.ROOT / "experiments/e0/regularization_comparison_plan_v1.json").read_text())
    job = dict(job_index=cell, cell_index=cell, cell=j.CELLS[cell][1], replicate=0,
               data_seed=202609220000+1000*cell, fold_seed=202609320000+1000*cell)
    return plan, job


def handcrafted(cell=0):
    # Every root seals its initial state with STOP. Half are wrong and half correct.
    # Repetition is deterministic; no random generator is sampled here.
    task = np.repeat(np.arange(230), 40)
    correct = task >= 115
    S = np.full((9200, 3), -1, dtype=int)
    S[:, 0] = np.where(correct, 3, 0)
    elig = np.zeros((9200, 3), dtype=bool)
    elig[:, 0] = True
    A = np.zeros((9200, 3), dtype=int)
    B = np.ones((9200, 3))
    _, _, kappa, floor = j.CELLS[cell]
    beh = j.sim.make_beh(kappa, floor, gz=0)
    B[:, 0] = beh[0, S[:, 0], 0]
    return dict(task=task, S=S, A=A, B=B, elig=elig, Y=correct.astype(float),
                e=np.zeros(9200, dtype=int), z=np.zeros(9200, dtype=int), T=3,
                template=np.full((9200, 3), -1, dtype=int), n_mislabelled=0,
                template_offsets=None)


@pytest.fixture(autouse=True)
def prohibit_real_sampler(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("real simulation is forbidden in deterministic adapter tests")
    monkeypatch.setattr(j.sim, "simulate", forbidden)


def test_preidentity_validates_seed_table_and_is_deterministic_before_sampling():
    plan, job = plan_job()
    a = j.expected_job_identity(plan, job)
    assert a == j.expected_job_identity(copy.deepcopy(plan), copy.deepcopy(job))
    assert a["planned_job"] == dict(cell_id="uniform", replicate=0, pairing_id=a["job_id"])
    changed = dict(job, data_seed=job["data_seed"]+1)
    with pytest.raises(ValueError, match="seeds"):
        j.evaluate_job(plan, changed)
    plan["n_tasks"] = 229
    with pytest.raises(ValueError, match="fixed field"):
        j.evaluate_job(plan, job)


def test_handcrafted_full_shape_connects_all_variants_report_and_callbacks():
    plan, job = plan_job()
    events = []
    out = j.evaluate_job(plan, job, data=handcrafted(), on_event=events.append)
    assert out["resources"]["sampler_attempts"] == 0
    assert out["provenance"]["data_mode"] == "handcrafted_injection"
    assert [e["event"] for e in events] == ["prepared"] + ["variant"]*4
    assert len(out["records"]) == 8 and out["all_points_completed"]
    assert set(out["variants"]) == set(j.fitted.VARIANTS)
    assert len({x["pairing_id"] for x in out["records"]}) == 1
    assert len({v["dataset_sha256"] for v in out["variants"].values()}) == 1
    assert len({v["fold_sha256"] for v in out["variants"].values()}) == 1
    for variant in out["variants"].values():
        assert len(variant["root_means"]["plugin"]) == len(variant["root_means"]["dr"]) == 230
        assert len(variant["support"]) == 3
        for fold in variant["support"]:
            assert len(fold["stages"]) == 3
            assert fold["stages"][1]["training_trajectories"] == 0
            assert fold["stages"][1]["heldout"]["fallback_frequency"] is None
            assert fold["stages"][0]["cell_columns"] == ["key", "action", "roots", "trajectories"]
            assert sum(row[3] for row in fold["stages"][0]["cells"]) == fold["stages"][0]["training_trajectories"]
        for row in variant["records"]:
            means = variant["root_means"][row["estimator"].split(":")[1]]
            assert row["estimate"] == pytest.approx(np.mean(means))
            if row["estimator"].endswith(":dr"):
                se = np.std(means, ddof=1) / math.sqrt(230)
                assert row["interval"]["se"] == pytest.approx(se)
                assert row["interval"]["lo"] == pytest.approx(row["estimate"]-1.96*se)
            else:
                assert "interval" not in row
    report = j.reporting.summarize_regularization([out["planned_job"]], out["records"], plan["deterministic_truth"])
    assert report["all_planned_results_complete"]
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize("cell", [0, 1, 2])
def test_production_boundary_has_exact_law_pcg64_and_separate_fold_seed(monkeypatch, cell):
    plan, job = plan_job(cell)
    seen = []
    def simulated(n_tasks, runs, T, Kk, beh, rng, **kwargs):
        assert (n_tasks, runs, T) == (230, 40, 3)
        assert kwargs == dict(mislabel=0., template_sd=0., cmult=1.)
        assert type(rng.bit_generator) is np.random.PCG64
        expected = np.random.PCG64(np.random.SeedSequence(job["data_seed"]))
        assert rng.bit_generator.state == expected.state  # inspect state; draw nothing
        np.testing.assert_array_equal(Kk, j.sim.kernel(1.))
        np.testing.assert_array_equal(beh, j.sim.make_beh(j.CELLS[cell][2], j.CELLS[cell][3], gz=0.))
        seen.append(True)
        return handcrafted(cell)
    monkeypatch.setattr(j.sim, "simulate", simulated)
    # Stop at prepared to test wiring without repeating all fits in three cells.
    class StopAfterPrepared(Exception): pass
    def event(e):
        assert e["event"] == "prepared"
        expected = j.history.make_task_folds(handcrafted(cell)["task"], 3, job["fold_seed"])
        np.testing.assert_array_equal(e["provenance"]["folds"]["episode_fold_ids"], expected["episode_fold_ids"])
        raise StopAfterPrepared()
    with pytest.raises(StopAfterPrepared):
        j.evaluate_job(plan, job, on_event=event)
    assert seen == [True]


def test_failure_of_one_variant_retains_others_and_identical_folds(monkeypatch):
    plan, job = plan_job()
    original = j.fitted.fit_regularized_q
    indices = {}
    def fit(*args, **kwargs):
        name = (kwargs["representation"], kwargs["shrinkage"])
        indices.setdefault(name, []).append(kwargs["idx"].copy())
        if name == ("history", 0):
            raise RuntimeError("injected nuisance failure")
        return original(*args, **kwargs)
    monkeypatch.setattr(j.fitted, "fit_regularized_q", fit)
    events = []
    out = j.evaluate_job(plan, job, data=handcrafted(), on_event=events.append)
    assert len(out["records"]) == 8
    assert sum(x["status"] == "failed" for x in out["records"]) == 2
    assert sum(x["status"] == "completed" for x in out["records"]) == 6
    assert [x["variant"] for x in events[1:]] == list(j.fitted.VARIANTS)
    for key in [("compressed", 5), ("history", 5)]:
        for a, b in zip(indices[("compressed", 0)], indices[key]):
            np.testing.assert_array_equal(a, b)


def test_callback_budget_failure_propagates_after_completed_variant(monkeypatch):
    plan, job = plan_job()
    events = []
    class BudgetExceeded(Exception): pass
    def event(e):
        events.append(e)
        if e["event"] == "variant":
            raise BudgetExceeded("outer output cap")
    with pytest.raises(BudgetExceeded):
        j.evaluate_job(plan, job, data=handcrafted(), on_event=event)
    assert [x["event"] for x in events] == ["prepared", "variant"]
    assert all(x["status"] == "completed" for x in events[-1]["records"])


def test_sampler_failure_returns_all_attempted_failures(monkeypatch):
    plan, job = plan_job()
    def fail(*args, **kwargs): raise RuntimeError("sampler unavailable")
    monkeypatch.setattr(j.sim, "simulate", fail)
    events = []
    out = j.evaluate_job(plan, job, on_event=events.append)
    assert len(out["records"]) == 8 and all(x["status"] == "failed" for x in out["records"])
    assert out["resources"]["sampler_attempts"] == 1
    assert out["provenance"]["dataset"] is None
    assert events[0]["event"] == "job_failed"
    assert not j.reporting.summarize_regularization([out["planned_job"]], out["records"], .5)["all_planned_results_complete"]


@pytest.mark.parametrize("defect", ["root_count", "stop_outcome", "propensity"])
def test_injected_data_cannot_relax_production_shape_or_law(defect):
    plan, job = plan_job()
    data = handcrafted()
    if defect == "root_count": data["task"][0] = 1
    elif defect == "stop_outcome": data["Y"][0] = 1
    else: data["B"][0, 0] = .3
    out = j.evaluate_job(plan, job, data=data)
    assert all(x["status"] == "failed" for x in out["records"])


def test_root_aggregation_not_episode_average_and_interval_failure_keeps_point(monkeypatch):
    means = j._root_means([0., 1., 1.], np.array([0, 0, 1]))
    np.testing.assert_array_equal(means, [.5, 1.])
    plan, job = plan_job()
    identity = j.expected_job_identity(plan, job)
    row = j._point_record(identity, "history_lambda0:dr", means)
    assert row["estimate"] == .75 and row["interval"]["se"] == .25
    assert row["interval"]["lo"] == pytest.approx(.26)
    def fail(*args, **kwargs): raise ValueError("SE unavailable")
    monkeypatch.setattr(np, "std", fail)
    row = j._point_record(identity, "history_lambda0:dr", means)
    assert row["status"] == "completed" and row["estimate"] == .75
    assert row["interval"]["status"] == "failed"


def test_hashes_bind_array_values_dtype_and_fold_identity_without_sampling():
    data = handcrafted()
    original = j._fingerprint(data)
    assert original == j._fingerprint(copy.deepcopy(data))
    changed = copy.deepcopy(data)
    changed["e"][0] = 1
    assert original["sha256"] != j._fingerprint(changed)["sha256"]
    changed = copy.deepcopy(data)
    changed["S"] = changed["S"].astype(np.int16)
    assert original["sha256"] != j._fingerprint(changed)["sha256"]
