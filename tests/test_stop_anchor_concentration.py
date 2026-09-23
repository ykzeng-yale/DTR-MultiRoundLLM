"""Handwritten score/archive fixtures only; no draws, estimators or production run."""
import copy
import importlib.util
import io
import json
import math
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[1]/"scripts/diagnose_stop_anchor_concentration.py"
SPEC = importlib.util.spec_from_file_location("stop_concentration", PATH)
diag = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diag)


def test_centered_square_shares_sign_and_translation_invariance():
    got = diag.concentration([0.,0.,0.,4.], [0.]*4, [1.]*4, [0,1,2,3])
    assert got["centered_sum_squares"] == 12
    assert got["sample_root_variance"] == 4
    assert got["top1_square_share"] == .75
    assert got["top5_square_share"] == 1
    assert got["positive_square_share"] == .75
    assert got["root_moment_skewness"] == pytest.approx(2/math.sqrt(3))
    assert [r["root_id"] for r in got["top_roots"]] == [3,0,1,2]
    assert got["top_roots"][0]["centered_dr"] == 3
    assert got["saved_correction_envelope"]["violations"] == 1
    shifted = diag.concentration([10.,10.,10.,14.], [10.]*4, [1.]*4, [0,1,2,3])
    for key in ("centered_sum_squares", "sample_root_variance", "top1_square_share", "top5_square_share",
                "positive_square_share", "root_moment_skewness"):
        assert shifted[key] == pytest.approx(got[key])


def test_zero_variance_is_undefined_and_ties_use_root_id():
    zero = diag.concentration([2.]*6, [1.]*6, [1.]*6, [5,4,3,2,1,0])
    for key in ("top1_square_share", "top5_square_share", "positive_square_share", "root_moment_skewness",
                "correlation_centered_dr_L", "correlation_correction_L"):
        assert zero[key] is None
    assert [r["root_id"] for r in zero["top_roots"]] == [0,1,2,3,4]
    assert all(r["squared_deviation_share"] is None for r in zero["top_roots"])
    tied = diag.concentration([-1.,1.,-1.,1.,-1.,1.], [0.]*6, [1.]*6, [5,4,3,2,1,0])
    assert tied["top1_square_share"] == pytest.approx(1/6)
    assert tied["top5_square_share"] == pytest.approx(5/6)
    assert tied["positive_square_share"] == .5
    assert [r["root_id"] for r in tied["top_roots"]] == [0,1,2,3,4]


def test_root_correlation_sign_and_undefined_pair_accounting():
    got = diag.concentration([0.,1.,2.], [0.,0.,0.], [1.,2.,3.], [0,1,2])
    assert got["correlation_centered_dr_L"] == pytest.approx(1)
    assert got["correlation_correction_L"] == pytest.approx(1)
    assert diag.correlation([None,1.], [0.,2.]) == dict(n=1, excluded=1, r=None)
    assert diag.correlation([1.,2.,3.], [3.,2.,1.])["r"] == pytest.approx(-1)


def test_weights_ignore_inactive_stop_padding_and_cumulate_on_active_steps():
    data = dict(task=np.array([0,0]), B=np.array([[.1,.05,.2],[.2,np.nan,-999.]]),
                elig=np.array([[1,1,1],[1,0,0]], bool))
    got = diag.weight_exposures(data, n_roots=1, runs=2)
    assert got["exposure_L"] == [9.5]  # (2+8+8+1)/2, not including stopped padding.
    assert [s["active_denominator"] for s in got["stages"]] == [2,1,1]
    assert [s["max_weight"] for s in got["stages"]] == [2.,8.,8.]
    changed = copy.deepcopy(data); changed["B"][1,1:] = [.0001, .0001]
    assert diag.weight_exposures(changed, n_roots=1, runs=2) == got


def test_weight_thresholds_are_strict_and_empty_stages_have_no_max():
    all_active = dict(task=np.array([0]), B=np.array([[.02]*3]), elig=np.ones((1,3),bool))
    got = diag.weight_exposures(all_active, n_roots=1, runs=1)
    assert [s["max_weight"] for s in got["stages"]] == [10.,100.,1000.]
    assert [s["count_gt10"] for s in got["stages"]] == [0,1,1]
    assert [s["count_gt100"] for s in got["stages"]] == [0,0,1]
    all_active["elig"][:,1:] = False
    empty = diag.weight_exposures(all_active, n_roots=1, runs=1)
    assert empty["stages"][1] == dict(stage=1, active_denominator=0, max_weight=None, count_gt10=0, count_gt100=0)


@pytest.mark.parametrize("fault", ["zero_b", "nonfinite_b", "reactivate", "wrong_roots"])
def test_invalid_exposure_inputs_refused(fault):
    data = dict(task=np.array([0,0]), B=np.full((2,3), .2), elig=np.ones((2,3),bool))
    if fault == "zero_b": data["B"][0,0] = 0
    elif fault == "nonfinite_b": data["B"][0,0] = np.nan
    elif fault == "reactivate": data["elig"][0,1] = False
    else: data["task"][1] = 1
    with pytest.raises(ValueError): diag.weight_exposures(data, n_roots=1, runs=2)


def support_fixture(active=1):
    stop = dict.fromkeys(diag.PRESENCE+diag.SOURCES, 0)
    stop.update(unseen_training_cell=active, structural=active)
    other = dict.fromkeys(diag.PRESENCE+diag.SOURCES, 0)
    other.update(observed_training_cell=2*active, unseen_training_cell=2*active,
                 cell=2*active, action_pool=active, stage_pool=active)
    held = dict(stage=0, active_heldout_trajectories=active, groups={
        "stop":dict(queries=active, counts=stop, fallback_queries=0, fallback_frequency=0. if active else None),
        "nonstop":dict(queries=4*active, counts=other, fallback_queries=2*active, fallback_frequency=.5 if active else None)})
    return [dict(fold=0, stages=[dict(stage=0, heldout=held)])]


def test_support_partitions_are_separate_and_structural_is_not_observed():
    got = diag.aggregate_support(support_fixture(), horizon=1, folds=1)[0]
    stop, other = got["groups"]["stop"], got["groups"]["nonstop"]
    assert stop["queries"] == 1 and sum(stop["counts"].values()) == 2
    assert stop["unseen_frequency"] == 1 and stop["fallback_frequency"] == 0
    assert other["queries"] == 4 and other["fallback_frequency"] == .5
    empty = diag.aggregate_support(support_fixture(0), horizon=1, folds=1)[0]
    assert empty["groups"]["stop"]["unseen_frequency"] is None
    assert empty["groups"]["nonstop"]["fallback_frequency"] is None


@pytest.mark.parametrize("fault", ["presence", "source", "frequency", "queries", "duplicate_fold"])
def test_support_partition_and_denominator_errors_refused(fault):
    support = support_fixture()
    row = support[0]["stages"][0]["heldout"]["groups"]["stop"]
    if fault == "presence": row["counts"]["observed_training_cell"] = 1
    elif fault == "source": row["counts"]["cell"] = 1
    elif fault == "frequency": row["fallback_frequency"] = 1.
    elif fault == "queries": row["queries"] = 2
    else: support.append(copy.deepcopy(support[0]))
    with pytest.raises(ValueError): diag.aggregate_support(support, horizon=1, folds=1)


def identity():
    job = dict(replicate=0, data_seed="123", fold_seed="456")
    plan_sha = "0"*64
    job_id = diag.digest(dict(schema="e0-stop-anchor-job-identity-v1", plan_sha256=plan_sha, job=job))
    return dict(job=job, plan_sha256=plan_sha, job_id=job_id,
                planned_job=dict(cell_id="weak_overlap", replicate=0, pairing_id=job_id))


def test_identity_decimal_seeds_and_hash_binding():
    ident = identity(); diag.validate_identity(ident, 0)
    for field, value in (("data_seed",123), ("fold_seed","changed"), ("replicate",True)):
        wrong = copy.deepcopy(ident); wrong["job"][field] = value
        with pytest.raises(ValueError): diag.validate_identity(wrong,0)
    wrong = copy.deepcopy(ident); wrong["job_id"] = "wrong"
    with pytest.raises(ValueError): diag.validate_identity(wrong,0)


def test_saved_archive_hash_and_descriptor_binding(tmp_path):
    root = tmp_path; (root/"records").mkdir()
    n = 230*40
    task = np.repeat(np.arange(230), 40)
    arrays = dict(task=task, S=np.full((n,3),3), A=np.zeros((n,3),int), B=np.ones((n,3)),
                  elig=np.column_stack([np.ones(n,bool),np.zeros((n,2),bool)]), Y=np.ones(n))
    folds = dict(task_labels=np.arange(230),task_index=task,task_fold_ids=np.arange(230)%3,
                 episode_fold_ids=(np.arange(230)%3)[task])
    desc = {k:dict(dtype=v.dtype.str,shape=list(v.shape),sha256=diag.sha(np.ascontiguousarray(v).tobytes())) for k,v in arrays.items()}
    fold_payload = {k:v.tolist() for k,v in folds.items()}
    out = io.BytesIO(); np.savez(out,**arrays,**{"fold_"+k:v for k,v in folds.items()})
    raw = out.getvalue(); path=root/"records/dataset_000.npz"; path.write_bytes(raw)
    event = dict(identity=identity(), archive=dict(path=path.name,bytes=len(raw),sha256=diag.sha(raw)),
        provenance=dict(dataset=dict(fields=desc,sha256=diag.digest(desc)),folds=dict(fold_payload,sha256=diag.digest(fold_payload))))
    loaded = diag.read_archive(root,event)
    assert np.array_equal(loaded["task"],task)
    changed=copy.deepcopy(event); changed["provenance"]["dataset"]["sha256"]="wrong"
    with pytest.raises(ValueError,match="descriptor"): diag.read_archive(root,changed)
    path.write_bytes(raw+b"changed")
    with pytest.raises(ValueError,match="hash/length"): diag.read_archive(root,event)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}',b'NaN',b'{"a":1e309}'])
def test_strict_json_refuses_malformed_numerics(raw):
    with pytest.raises(ValueError): diag.strict_json(raw)


def test_wrong_journal_refused_before_any_archive_load(tmp_path,monkeypatch):
    (tmp_path/"records").mkdir(); (tmp_path/"records/events.jsonl").write_bytes(b"{}\n")
    def forbidden(*a): raise AssertionError("archive must not be loaded")
    monkeypatch.setattr(diag,"read_archive",forbidden)
    with pytest.raises(ValueError,match="closed-run pin"): diag.analyze_run(tmp_path)


def test_output_exclusive_outside_raw_and_size_cap(tmp_path,monkeypatch):
    root=tmp_path/"raw";root.mkdir()
    monkeypatch.setattr(diag,"analyze_run",lambda p:dict(fixture_only=True))
    with pytest.raises(ValueError,match="outside"): diag.write_diagnostic(root,root/"result.json")
    out=tmp_path/"result.json";diag.write_diagnostic(root,out)
    assert json.loads(out.read_text())==dict(fixture_only=True)
    with pytest.raises(FileExistsError):diag.write_diagnostic(root,out)
    monkeypatch.setattr(diag,"MAX_OUTPUT_BYTES",1)
    with pytest.raises(ValueError,match="cap"):diag.write_diagnostic(root,tmp_path/"too_big.json")
    assert not (tmp_path/"too_big.json").exists()
