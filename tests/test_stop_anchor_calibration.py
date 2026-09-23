"""Handwritten arithmetic/identity fixtures; no draws, fits or raw-run access."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import statistics

import pytest

PATH = Path(__file__).resolve().parents[1]/"scripts/diagnose_stop_anchor_calibration.py"
SPEC = importlib.util.spec_from_file_location("stop_calibration", PATH)
cal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cal)


def test_handwritten_error_se_z_summary():
    out = cal.summarize_pairs([-1., 0., 1.], [1., 2., 3.], truth=0.)
    assert out["bias"] == 0
    assert out["empirical_sd_error"] == 1
    assert out["mean_se"] == 2
    assert out["rms_se"] == pytest.approx(math.sqrt(14/3))
    assert out["mean_square_se_over_empirical_variance"] == pytest.approx(14/3)
    assert out["moment_skewness_error"] == 0
    assert out["moment_skewness_z"] == pytest.approx(-70/(26**1.5))
    assert out["correlation_error_se"] == pytest.approx(1)
    assert out["correlation_abs_error_se"] == pytest.approx(0)
    assert out["z_quantiles"] == pytest.approx(dict(min=-1, q025=-.95, median=0, q975=19/60, max=1/3))
    assert out["frozen_interval_counts"] == dict(total=3, below_truth=0, above_truth=0, covered=3)


def test_quantile_interpolation_and_moment_convention():
    assert cal.quantile([3., 0., 1., 2.], .025) == pytest.approx(.075)
    assert cal.quantile([3., 0., 1., 2.], .975) == pytest.approx(2.925)
    assert cal.skewness([0., 0., 3.]) == pytest.approx(1/math.sqrt(2))
    assert cal.pearson([1., 2., 3.], [6., 4., 2.]) == pytest.approx(-1.)


def test_degenerate_statistics_are_null_not_fabricated_z():
    out = cal.summarize_pairs([1., 1., 1.], [1., 1., 1.], truth=0.)
    assert out["empirical_sd_error"] == 0
    assert out["mean_square_se_over_empirical_variance"] is None
    assert out["moment_skewness_error"] is out["moment_skewness_z"] is None
    assert out["correlation_error_se"] is out["correlation_abs_error_se"] is None
    assert out["z_quantiles"]["median"] == 1
    assert out["hindsight_constant_width_counts"]["same_replicate_empirical_sd"]["above_truth"] == 3
    for estimates in ([0., 0.], [1., 1.]):
        with pytest.raises(ValueError, match="positive"):
            cal.summarize_pairs(estimates, [0., 1.], truth=0.)


def test_hindsight_counts_keep_original_center_and_can_lose_coverage():
    # One covered wide-SE observation is lost when empiricalSD becomes zero.
    out = cal.summarize_pairs([2., 2.], [.1, 2.], truth=0.)
    assert out["frozen_interval_counts"]["covered"] == 1
    assert out["hindsight_constant_width_counts"]["same_replicate_empirical_sd"]["covered"] == 0
    assert out["hindsight_constant_width_counts"]["same_replicate_rms_se"]["covered"] == 2


def test_all_ordered_product_pairs_and_directional_boundaries():
    counts = cal.product_empirical_counts([-2., 2.], [.5, 2.])
    assert counts == dict(total_pairs=4, below_truth=1, above_truth=1, covered=2, covered_fraction=.5)
    out = cal.summarize_pairs([0., 2.], [.1, 2.], truth=0.)
    re = out["product_empirical_repairing"]
    assert re["total_pairs"] == 4 and re["covered"] == 3
    assert re["original_paired_coverage_fraction"] == 1
    assert re["fraction_minus_original_pairing"] == -.25
    boundary = cal.product_empirical_counts([-1.96, 1.96], [1.])
    assert boundary["covered"] == 2 and boundary["above_truth"] == boundary["below_truth"] == 0


@pytest.fixture
def objects():
    jobs = [dict(cell_id="weak_overlap", replicate=i, pairing_id=f"handwritten-{i}") for i in range(96)]
    # Deterministically repeated symmetric triples, never a sampled dataset.
    estimates = [cal.TRUTH+(-1+i%3)*.125 for i in range(96)]
    ses = [.1+.01*(i%2) for i in range(96)]
    slots = []
    for job in jobs:
        i = job["replicate"]
        for estimator in cal.ESTIMATORS:
            row = dict(job, estimator=estimator, status="completed", estimate=estimates[i])
            if estimator.endswith(":dr"):
                row["interval"] = dict(status="valid", se=ses[i], lo=estimates[i]-1.96*ses[i], hi=estimates[i]+1.96*ses[i])
            slots.append(row)
    snapshot = dict(fixture_only=True)
    recon = dict(audit=dict(schema_version="e0-stop-anchor-final-reconciliation-v1", input_hashes_stable=True,
        journal_complete_normal_run=True, child_exit_receipt_verified=True, terminal_jobs=96,
        all_planned_slots=2304, raw_snapshot=snapshot), summary=dict(truth=cal.TRUTH,
        planned_estimator_slots=2304, status_counts=dict(cal.COUNTS), all_planned_results_complete=True,
        truncated=False, incomplete=False, planned_jobs=jobs, slots=slots))
    companion = dict(schema_version="e0-stop-anchor-independent-arithmetic-v1", reconciled_sha256=cal.RECONCILED_SHA256,
        truth=cal.TRUTH, raw_hashes_stable=True, completed_points_checked=2304, valid_DR_intervals_checked=1152,
        failed_DR_intervals_retained=0, truncated=False, all_planned_results_complete=True,
        raw_snapshot=snapshot, summary_arithmetic=dict(estimators={}))
    for estimator in cal.ESTIMATORS:
        companion["summary_arithmetic"]["estimators"][estimator] = dict(point_metric_denominator=96,
            bias=statistics.mean([x-cal.TRUTH for x in estimates]), empirical_sd=statistics.stdev(estimates),
            intervals=dict(returned=96, mean_se=statistics.mean(ses),
                rms_se=math.sqrt(sum(s*s for s in ses)/96), below_truth=0, above_truth=0, covered=96))
    return recon, companion


def test_all12_methods_and96_identified_pairs_are_retained(objects):
    result = cal.analyze(*objects)
    assert [r["estimator"] for r in result["methods"]] == list(cal.DR_ESTIMATORS)
    assert result["total_pairs"] == 1152
    for method in result["methods"]:
        assert [p["replicate"] for p in method["pairs"]] == list(range(96))
        assert method["summary"]["product_empirical_repairing"]["total_pairs"] == 9216
    assert "unavailable" in " ".join(result["limitations"])
    assert "not independent" in " ".join(result["limitations"])


@pytest.mark.parametrize("fault", ["missing", "duplicate", "unknown_estimator", "wrong_replicate", "bool_replicate",
    "pairing", "job_order", "duplicate_job", "point_failed", "nonfinite", "se_zero", "se_negative",
    "se_nonfinite", "ci_failed", "ci_bound", "plugin_interval", "companion_reference", "snapshot", "truncated"])
def test_invalid_assignment_or_completed_slot_is_rejected(objects, fault):
    recon, companion = copy.deepcopy(objects)
    rows, jobs = recon["summary"]["slots"], recon["summary"]["planned_jobs"]
    dr = rows[1]
    if fault == "missing": rows.pop()
    elif fault == "duplicate": rows[-1] = copy.deepcopy(rows[1])
    elif fault == "unknown_estimator": dr["estimator"] = "chosen:dr"
    elif fault == "wrong_replicate": dr["replicate"] = 96
    elif fault == "bool_replicate": dr["replicate"] = False
    elif fault == "pairing": dr["pairing_id"] = "wrong"
    elif fault == "job_order": jobs.reverse()
    elif fault == "duplicate_job": jobs[1]["pairing_id"] = jobs[0]["pairing_id"]
    elif fault == "point_failed": dr["status"] = "failed"
    elif fault == "nonfinite": dr["estimate"] = float("inf")
    elif fault == "se_zero": dr["interval"]["se"] = 0
    elif fault == "se_negative": dr["interval"]["se"] = -.1
    elif fault == "se_nonfinite": dr["interval"]["se"] = float("nan")
    elif fault == "ci_failed": dr["interval"]["status"] = "failed"
    elif fault == "ci_bound": dr["interval"]["hi"] += .1
    elif fault == "plugin_interval": rows[0]["interval"] = copy.deepcopy(dr["interval"])
    elif fault == "companion_reference": companion["reconciled_sha256"] = "wrong"
    elif fault == "snapshot": companion["raw_snapshot"] = dict(other=True)
    else: recon["summary"]["truncated"] = True
    with pytest.raises(ValueError): cal.analyze(recon, companion)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'NaN', b'{"x":1e309}', b'Infinity'])
def test_strict_json(raw):
    with pytest.raises(ValueError): cal.strict_json(raw)


def test_hash_guard_fails_before_object_analysis(tmp_path, monkeypatch):
    first, second = tmp_path/"a.json", tmp_path/"b.json"
    first.write_text("{}"); second.write_text("{}")
    def forbidden(*a): raise AssertionError("must not analyze unmatched bytes")
    monkeypatch.setattr(cal, "analyze", forbidden)
    with pytest.raises(ValueError, match="pinned"):
        cal.diagnose(first, second)


def test_exclusive_output_stable_inputs_and_output_cap(tmp_path, monkeypatch, objects):
    recon, companion = copy.deepcopy(objects)
    first, second, output = tmp_path/"a.json", tmp_path/"b.json", tmp_path/"derived.json"
    first.write_text(json.dumps(recon))
    fixture_sha = cal.sha(first.read_bytes())
    monkeypatch.setattr(cal, "RECONCILED_SHA256", fixture_sha)
    companion["reconciled_sha256"] = fixture_sha
    second.write_text(json.dumps(companion))
    monkeypatch.setattr(cal, "ARITHMETIC_SHA256", cal.sha(second.read_bytes()))
    before = (first.read_bytes(), second.read_bytes())
    result = cal.write_diagnostic(first, second, output)
    assert result["input_bytes_stable"] and result["dr_methods"] == 12
    assert (first.read_bytes(), second.read_bytes()) == before
    with pytest.raises(FileExistsError): cal.write_diagnostic(first, second, output)
    with pytest.raises(ValueError, match="differ"): cal.write_diagnostic(first, second, first)
    monkeypatch.setattr(cal, "MAX_OUTPUT_BYTES", 1)
    with pytest.raises(ValueError, match="cap"): cal.write_diagnostic(first, second, tmp_path/"too_big.json")
    assert not (tmp_path/"too_big.json").exists()


def test_mid_analysis_input_change_refuses_output(tmp_path, monkeypatch, objects):
    recon, companion = copy.deepcopy(objects)
    first, second = tmp_path/"a.json", tmp_path/"b.json"
    first.write_text(json.dumps(recon)); monkeypatch.setattr(cal, "RECONCILED_SHA256", cal.sha(first.read_bytes()))
    companion["reconciled_sha256"] = cal.RECONCILED_SHA256
    second.write_text(json.dumps(companion)); monkeypatch.setattr(cal, "ARITHMETIC_SHA256", cal.sha(second.read_bytes()))
    original = cal.analyze
    def changed(*args):
        result = original(*args)
        first.write_text("changed fixture")
        return result
    monkeypatch.setattr(cal, "analyze", changed)
    with pytest.raises(ValueError, match="changed"):
        cal.write_diagnostic(first, second, tmp_path/"refused.json")
    assert not (tmp_path/"refused.json").exists()
