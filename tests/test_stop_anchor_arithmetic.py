"""Tiny handwritten arithmetic fixtures; no sampler, fitter or run generator."""
import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1]/"scripts/audit_stop_anchor_arithmetic.py"
SPEC = importlib.util.spec_from_file_location("independent_stop_arithmetic", PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def identity(rep):
    return dict(job=dict(replicate=rep), planned_job=dict(cell_id="weak_overlap", replicate=rep,
                                                       pairing_id=f"handwritten-{rep}"))


def point(ident, estimator, values, *, failed_interval=False):
    # Hand fixtures use symmetric triples, so the middle entry is the exact mean.
    center = values[1]
    row = {**ident["planned_job"], "estimator": estimator, "status": "completed", "estimate": center}
    if estimator.endswith(":dr"):
        if failed_interval:
            row["interval"] = dict(status="failed", reason="handwritten interval failure")
        else:
            se = abs(values[2]-center)/math.sqrt(3)
            row["interval"] = dict(status="valid", se=se, lo=center-1.96*se, hi=center+1.96*se)
    return row


def events_for_two_variants():
    ident = identity(0)
    events = [dict(event="job_started", identity=ident, estimator_ids=list(audit.ESTIMATORS)),
              dict(event="prepared", identity=ident, provenance=dict(folds=dict(task_labels=[0,1,2])))]
    for mode, values in (("original", [0.,1.,2.]), ("evaluation_only", [1.,2.,3.])):
        variant = "compressed_lambda0_"+mode
        events.append(dict(event="variant_started", identity=ident, variant=variant,
                           estimator_ids=[variant+":plugin", variant+":dr"]))
        events.append(dict(event="variant", identity=ident, variant=variant, root_labels=[0,1,2],
                           root_means={"plugin": values, "dr": values},
                           records=[point(ident, variant+":plugin", values),
                                    point(ident, variant+":dr", values, failed_interval=mode=="evaluation_only")]))
    return events


def test_hand_root_mean_variance_and_dr_interval():
    row = point(identity(0), audit.ESTIMATORS[1], [0.,1.,2.])
    got = audit.check_point(row, [0.,1.,2.], n_roots=3)
    assert got["estimate"] == 1.
    assert got["sample_root_variance"] == 1.
    assert got["se"] == pytest.approx(1/math.sqrt(3))
    with pytest.raises(ValueError, match="root count"):
        audit.check_point(row, [0.,1.,2.])  # production requires230


@pytest.mark.parametrize("field", ["estimate", "se", "lo", "hi"])
def test_reject_incorrect_saved_arithmetic(field):
    row = point(identity(0), audit.ESTIMATORS[1], [0.,1.,2.])
    if field == "estimate":
        row[field] += .001
    else:
        row["interval"][field] += .001
    with pytest.raises(ValueError, match="arithmetic mismatch"):
        audit.check_point(row, [0.,1.,2.], n_roots=3)


def test_failed_interval_preserved_not_repaired_and_plugin_ci_forbidden():
    row = point(identity(0), audit.ESTIMATORS[1], [0.,1.,2.], failed_interval=True)
    assert audit.check_point(row, [0.,1.,2.], n_roots=3)["interval_status"] == "failed"
    row["estimator"] = audit.ESTIMATORS[0]
    with pytest.raises(ValueError, match="plugin interval"):
        audit.check_point(row, [0.,1.,2.], n_roots=3)


def test_fsum_retains_small_mean_between_opposite_large_scores():
    row = dict(estimator=audit.ESTIMATORS[0], estimate=1/3)
    assert audit.check_point(row, [1e16,1.,-1e16], n_roots=3)["estimate"] == 1/3


def test_variance_identity_exact_covariance_and_shift_cases():
    result = audit.variance_identity([0.,2.,4.], [0.,1.,2.])
    assert result["left_root_variance"] == 4.
    assert result["right_root_variance"] == 1.
    assert result["difference_root_variance"] == 1.
    assert result["covariance_right_difference"] == 1.
    assert result["left_minus_right_variance"] == 3.
    assert result["identity_residual"] == 0.
    assert result["identity_scale"] == 8.
    assert result["identity_tolerance"] == pytest.approx(9e-12)
    shifted = audit.variance_identity([1.,2.,3.], [0.,1.,2.])
    assert shifted["difference_root_variance"] == shifted["identity_residual"] == 0.


def test_variance_identity_cancellation_uses_all_term_scale():
    result = audit.variance_identity([1e8, 2., -1e8], [1e8, 0., -1e8])
    assert result["identity_tolerance"] > 10000
    assert abs(result["identity_residual"]) <= result["identity_tolerance"]


def test_partial_job_all_slots_and_failed_interval_denominators():
    identities = [identity(0), identity(1)]
    slots, roots, checked, states = audit.reconstruct(events_for_two_variants(), identities, n_roots=3)
    out = audit.summarize(slots, roots, [i["planned_job"] for i in identities])
    assert len(slots) == 48
    assert len(checked) == 4
    assert out["status_counts"] == dict(attempted=20, completed=4, failed=0, unattempted=24)
    assert out["attempted_estimator_slots"] == 24
    assert not states[0]["complete"]
    original = out["estimators"]["compressed_lambda0_original:dr"]
    direct = out["estimators"]["compressed_lambda0_evaluation_only:dr"]
    assert original["intervals"]["returned"] == 1
    assert original["intervals"]["covered"] == 1
    assert original["intervals"]["operational_denominator"] == 1
    assert direct["point_metric_denominator"] == 1
    assert direct["intervals"]["returned"] == 0
    assert direct["intervals"]["failed_after_completed_point"] == 1
    assert direct["intervals"]["no_completed_point"] == 1
    assert len(out["paired_comparisons"]) == 24
    pair = out["paired_comparisons"][0]
    assert pair["joint_completed_pairs"] == pair["excluded_pairs"] == 1
    assert pair["mean_estimate_difference"] == 1.
    assert pair["mean_squared_error_difference"] == pytest.approx(3-2*audit.TRUTH)
    assert pair["paired_mcse"] is None
    assert pair["excluded"][0]["left_status"] == "unattempted"
    assert len(pair["within_dataset_variance_identities"]) == 1


def test_two_dataset_hand_paired_mcse_uses_square_differences():
    jobs = [identity(0)["planned_job"], identity(1)["planned_job"]]
    slots = {(j["replicate"], e): {**j,"estimator":e,"status":"unattempted"} for j in jobs for e in audit.ESTIMATORS}
    roots = {}
    left, right = audit.PAIRS[0]
    for rep, (a,b) in enumerate(((1.,0.), (2.,0.))):
        for estimator, value in ((left,a), (right,b)):
            slots[rep, estimator] = dict(jobs[rep], estimator=estimator, status="completed", estimate=value)
            roots[rep, estimator] = [value]*3
    pair = audit.summarize(slots, roots, jobs)["paired_comparisons"][0]
    q0, q1 = 1-2*audit.TRUTH, 4-4*audit.TRUTH
    assert pair["mean_squared_error_difference"] == pytest.approx((q0+q1)/2)
    assert pair["paired_mcse"] == pytest.approx(abs(q1-q0)/2)
    assert pair["estimate_difference_mcse"] == .5


def test_preparation_failure_retains_all_failed_points():
    ident = identity(0)
    events = [dict(event="job_started", identity=ident, estimator_ids=list(audit.ESTIMATORS)),
              dict(event="job_failed", identity=ident, records=[dict(ident["planned_job"], estimator=e,
                   status="failed", reason="prepared fixture failure") for e in audit.ESTIMATORS]),
              dict(event="job_complete", identity=ident)]
    slots, roots, checked, states = audit.reconstruct(events, [ident], n_roots=3)
    result = audit.summarize(slots, roots, [ident["planned_job"]])
    assert result["status_counts"]["failed"] == 24
    assert not roots and not checked and states[0]["complete"]
    assert all(p["joint_completed_pairs"] == 0 and p["excluded_pairs"] == 1 for p in result["paired_comparisons"])


@pytest.mark.parametrize("bad", ["root_labels", "pairing", "duplicate", "nonfinite"])
def test_event_and_root_alignment_fail_closed(bad):
    events = events_for_two_variants()
    if bad == "root_labels":
        events[-1]["root_labels"] = [1,0,2]
    elif bad == "pairing":
        events[-1]["records"][0]["pairing_id"] = "wrong"
    elif bad == "duplicate":
        events.append(copy.deepcopy(events[-1]))
    else:
        events[-1]["root_means"]["plugin"][0] = float("nan")
    with pytest.raises(ValueError):
        audit.reconstruct(events, [identity(0)], n_roots=3)


def test_torn_tail_is_hashed_but_not_a_durable_event():
    first, tail = b'{"event":"a"}\n', b'{"event":"not_durable"}'
    events, metadata = audit.parse_events(first+tail)
    assert events == [dict(event="a")]
    assert metadata["ignored_tail_sha256"] == audit.sha(tail)
    with pytest.raises(ValueError):
        audit.parse_events(b'{broken}\n')


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'NaN', b'1e999', b'Infinity'])
def test_strict_json_rejects_nonfinite_and_duplicate(raw):
    with pytest.raises(ValueError):
        audit.strict_json(raw)


def test_snapshot_and_bound_read_detect_changed_or_added_inputs(tmp_path):
    (tmp_path/"receipt.json").write_bytes(b"{}")
    snap = audit._snapshot(tmp_path)
    assert audit._read(tmp_path, snap, "receipt.json") == b"{}"
    (tmp_path/"receipt.json").write_bytes(b'{"changed":true}')
    with pytest.raises(ValueError, match="changed"):
        audit._read(tmp_path, snap, "receipt.json")
    assert audit._snapshot(tmp_path) != snap


def test_production_requires_observed_child_before_reading_any_events(tmp_path):
    root = tmp_path/"raw"; root.mkdir()
    source = tmp_path/"reconciled.json"
    source.write_text(json.dumps(dict(audit=dict(schema_version="e0-stop-anchor-final-reconciliation-v1",
        input_hashes_stable=True, production_provenance_required=True,
        child_exit_receipt_verified=False, never_spawned=True), summary={})))
    with pytest.raises(ValueError, match="observed-child"):
        audit.audit_run(root, source)


def test_summary_comparison_fails_wrong_counts_or_pair_arithmetic():
    with pytest.raises(ValueError, match="value/type"):
        audit._compare(dict(returned=2), dict(returned=1))
    with pytest.raises(ValueError, match="arithmetic"):
        audit._compare(dict(paired_mcse=.1), dict(paired_mcse=.2))
    with pytest.raises(ValueError, match="value/type"):
        audit._compare(True, 1)


def test_output_must_be_external_exclusive_and_not_overwrite_reconciliation(tmp_path, monkeypatch):
    root = tmp_path/"raw"; root.mkdir()
    source = tmp_path/"reconciled.json"; source.write_text("{}")
    monkeypatch.setattr(audit, "audit_run", lambda *a: dict(source_fixture=True))
    with pytest.raises(ValueError):
        audit.write_audit(root, source, root/"output.json")
    with pytest.raises(ValueError):
        audit.write_audit(root, source, source)
    target = tmp_path/"derived.json"
    audit.write_audit(root, source, target)
    assert json.loads(target.read_text()) == dict(source_fixture=True)
    with pytest.raises(FileExistsError):
        audit.write_audit(root, source, target)
