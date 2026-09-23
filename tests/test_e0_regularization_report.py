"""Hand-arithmetic report fixtures only: no simulation or estimator fitting."""
import copy
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "e0"))
import regularization_report as r

DR = "history_lambda5:dr"
PLUGIN = "history_lambda5:plugin"


def jobs(n=6, cell="base"):
    return [dict(cell_id=cell, replicate=i, pairing_id=f"dataset+fold:{cell}:{i}") for i in range(n)]


def point(job, estimator, value, se=None):
    row = {**job, "estimator": estimator, "status": "completed", "estimate": value}
    if estimator.endswith(":dr"):
        row["interval"] = ({"status": "failed", "reason": "SE unavailable"} if se is None else
                           dict(status="valid", se=se, lo=value - 1.96 * se, hi=value + 1.96 * se))
    return row


def fixture():
    plan = jobs()
    records = [point(plan[i], DR, x, se) for i, (x, se) in enumerate(zip([.25, .5, 1., .5], [.1, .2, 0., None]))]
    records += [{**plan[4], "estimator": DR, "status": "failed", "reason": "fit failed"}]
    records += [point(plan[i], PLUGIN, x) for i, x in [(0, .5), (1, .75), (3, .25)]]
    return plan, records


def test_hand_calculated_metrics_preserve_point_with_failed_interval():
    plan, records = fixture()
    out = r.summarize_regularization(plan, records, .5)
    d = out["cells"]["base"]["estimators"][DR]
    assert d["planned"] == 6 and d["attempted"] == 5 and d["point_metric_denominator"] == 4
    assert d["status_counts"] == dict(attempted=0, completed=4, failed=1, unattempted=1)
    assert d["bias"] == pytest.approx(1 / 16)
    assert d["rmse"] == pytest.approx(math.sqrt(5 / 64))
    assert d["empirical_sd"] == pytest.approx(math.sqrt(19 / 192))
    assert d["bias_mcse"] == pytest.approx(math.sqrt(19 / 768))
    ci = d["intervals"]
    assert ci["returned"] == 3 and ci["failed_after_completed_point"] == 1
    assert ci["covered"] == ci["below_truth"] == ci["above_truth"] == 1
    assert ci["returned_interval_coverage"] == pytest.approx(1 / 3)
    assert ci["operational_covering_per_attempted"] == .2
    assert ci["operational_denominator"] == 5
    assert ci["mean_se"] == pytest.approx(.1)
    assert ci["rms_se"] == pytest.approx(math.sqrt(1 / 60))
    assert ci["mean_width"] == pytest.approx(.392)
    assert ci["coverage_mcse"] == pytest.approx(math.sqrt(2 / 27))
    # CP inversion for k=1,n=3: lower solves 1-(1-L)^3=.025;
    # upper solves (1-U)^3+3U(1-U)^2=.025.
    lower, upper = ci["coverage_exact_binomial_95"]
    assert 1 - (1 - lower) ** 3 == pytest.approx(.025)
    assert (1 - upper) ** 3 + 3 * upper * (1 - upper) ** 2 == pytest.approx(.025)
    assert len(out["slots"]) == 48 and out["incomplete"]
    assert "intervals" not in out["cells"]["base"]["estimators"][PLUGIN]
    json.dumps(out, allow_nan=False)


def test_paired_squared_errors_use_joint_completion_and_paired_mcse():
    plan, records = fixture()
    out = r.summarize_regularization(plan, records, .5)
    pairs = out["cells"]["base"]["paired_comparisons"]
    assert len(pairs) == 12
    assert {axis: sum(p["axis"] == axis for p in pairs) for axis in
            ["history_minus_compressed", "shrunk_minus_raw", "dr_minus_plugin"]} == {
                "history_minus_compressed": 4, "shrunk_minus_raw": 4, "dr_minus_plugin": 4}
    pair = next(p for p in pairs if p["left"] == DR and p["right"] == PLUGIN)
    assert pair["joint_completed_pairs"] == 3 and pair["excluded_pairs"] == 3
    assert [x["replicate"] for x in pair["included"]] == [0, 1, 3]
    assert [x["squared_error_difference"] for x in pair["included"]] == [1/16, -1/16, -1/16]
    assert pair["mean_squared_error_difference"] == pytest.approx(-1/48)
    assert pair["paired_mcse"] == pytest.approx(1/24)
    assert [x["replicate"] for x in pair["excluded"]] == [2, 4, 5]


def test_no_attempts_and_failed_attempts_have_distinct_denominators():
    plan = jobs(2)
    no_attempt = r.summarize_regularization(plan, [], .5)
    d = no_attempt["cells"]["base"]["estimators"][DR]
    assert d["bias"] is d["rmse"] is d["bias_mcse"] is d["empirical_sd"] is None
    assert d["intervals"]["returned_interval_coverage"] is None
    assert d["intervals"]["operational_covering_per_attempted"] is None
    assert d["intervals"]["coverage_exact_binomial_95"] is None
    records = [{**plan[0], "estimator": DR, "status": "attempted", "reason": "outer timeout during fit"},
               {**plan[1], "estimator": DR, "status": "failed", "reason": "nonfinite point computation"}]
    failed = r.summarize_regularization(plan, records, .5)
    d = failed["cells"]["base"]["estimators"][DR]
    assert d["attempted"] == 2 and d["point_metric_denominator"] == 0
    assert d["intervals"]["returned_interval_coverage"] is None
    assert d["intervals"]["operational_covering_per_attempted"] == 0.
    assert [x["reason"] for x in failed["slots"] if x["estimator"] == DR] == [records[0]["reason"], records[1]["reason"]]


def test_one_point_undefined_sd_mcse_inclusive_coverage_and_cp_boundaries():
    plan = jobs(1)
    out = r.summarize_regularization(plan, [point(plan[0], DR, .5, 0)], .5)
    d = out["cells"]["base"]["estimators"][DR]
    assert d["bias"] == d["rmse"] == 0 and d["empirical_sd"] is d["bias_mcse"] is None
    assert d["intervals"]["returned_interval_coverage"] == 1
    assert d["intervals"]["coverage_mcse"] == 0
    assert d["intervals"]["coverage_exact_binomial_95"] == pytest.approx([.025, 1])
    assert r.exact_binomial_interval(0, 1) == pytest.approx([0, .975])
    assert r.exact_binomial_interval(0, 0) is None


def test_complete_cells_are_separate_and_explicit_truncation_retained():
    plan = jobs(2, "uniform") + jobs(1, "weak")
    records = [point(j, e, .5, .1) for j in plan for e in r.ESTIMATORS]
    out = r.summarize_regularization(plan, records, .5)
    assert out["all_planned_results_complete"] and not out["incomplete"]
    assert [x["planned_jobs"] for x in out["cells"].values()] == [2, 1]
    assert r.summarize_regularization(plan, records[::-1], .5) == out
    truncated = r.summarize_regularization(plan, records, .5, truncated=True)
    assert truncated["all_planned_results_complete"] and truncated["incomplete"] and truncated["truncated"]
    assert "no unconditional precision" in truncated["precision_scope"]


def test_reused_dataset_fold_identity_is_rejected_across_jobs():
    plan = jobs(2)
    plan[1]["pairing_id"] = plan[0]["pairing_id"]
    with pytest.raises(ValueError, match="pairing_id reused"):
        r.summarize_regularization(plan, [], .5)


def test_finite_bounds_with_overflowing_width_are_rejected():
    plan = jobs(1)
    record = point(plan[0], DR, .5, 5e307)
    assert math.isfinite(record["interval"]["lo"]) and math.isfinite(record["interval"]["hi"])
    with pytest.raises(ValueError, match="interval-width"):
        r.summarize_regularization(plan, [record], .5)


def test_unrepresentable_paired_dispersion_raises_not_nonfinite_summary():
    plan = jobs(2)
    records = [point(plan[0], DR, 1.2e154), point(plan[0], PLUGIN, 0.),
               point(plan[1], DR, 0.), point(plan[1], PLUGIN, 1.2e154)]
    # Each error square is finite, but SD of [+1.44e308,-1.44e308] is not.
    with pytest.raises(ValueError, match="aggregate SD"):
        r.summarize_regularization(plan, records, 0.)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "0.5", 1e308])
def test_nonfinite_or_unrepresentable_point_arithmetic_is_not_silently_dropped(value):
    plan = jobs(1)
    with pytest.raises(ValueError):
        r.summarize_regularization(plan, [point(plan[0], PLUGIN, value)], .5)


@pytest.mark.parametrize("defect", ["duplicate_record", "duplicate_plan", "unknown_job", "unknown_estimator", "pairing", "plugin_ci", "invalid_ci", "se_nan", "missing_failure_reason", "nonfinite_truth"])
def test_malformed_binding_status_or_interval_fails_closed(defect):
    plan = jobs(1)
    records = [point(plan[0], DR, .5, .1)]
    truth = .5
    if defect == "duplicate_record": records *= 2
    elif defect == "duplicate_plan": plan *= 2
    elif defect == "unknown_job": records[0]["replicate"] = 99
    elif defect == "unknown_estimator": records[0]["estimator"] = "oracle"
    elif defect == "pairing": records[0]["pairing_id"] = "different-folds"
    elif defect == "plugin_ci": records[0]["estimator"] = PLUGIN
    elif defect == "invalid_ci": records[0]["interval"]["lo"] = 0
    elif defect == "se_nan": records[0]["interval"]["se"] = float("nan")
    elif defect == "missing_failure_reason": records = [{**plan[0], "estimator": DR, "status": "failed"}]
    else: truth = float("nan")
    with pytest.raises(ValueError):
        r.summarize_regularization(plan, records, truth)
