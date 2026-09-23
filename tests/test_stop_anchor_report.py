"""Hand-calculated reporting fixtures; no simulation, fitting or RNG calls."""
import copy
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "e0"))
import stop_anchor_report as r

LEFT, RIGHT = r.PRIMARY_PAIR
PLUGIN = "history_lambda5_recursive:plugin"


def jobs():
    return [dict(cell_id="weak_overlap", replicate=i, pairing_id=f"fixed-dataset-and-fold:{i}")
            for i in range(96)]


def point(job, estimator, estimate, se=None):
    record = {**job, "estimator": estimator, "status": "completed", "estimate": estimate}
    if estimator.endswith(":dr"):
        record["interval"] = (dict(status="failed", reason="SE unavailable") if se is None else
                              dict(status="valid", se=se, lo=estimate-1.96*se, hi=estimate+1.96*se))
    return record


def all_records(plan):
    return [point(job, estimator, .5, .1) for job in plan for estimator in r.ESTIMATORS]


def estimator(out, name=LEFT):
    return out["cells"]["weak_overlap"]["estimators"][name]


def primary_pair(out):
    return next(pair for pair in out["cells"]["weak_overlap"]["paired_comparisons"] if pair["is_primary"])


def test_literal_estimators_pairs_and_primary_match_accepted_plan():
    frozen = json.loads((ROOT / "experiments/e0/stop_anchor_comparison_plan_v1.json").read_text())
    assert list(r.ESTIMATORS) == frozen["estimator_order"]
    assert [{"left": left, "right": right} for left, right in r.PAIRS] == frozen["paired_comparisons"]
    assert r.PRIMARY_PAIR == (frozen["primary_pair"]["left"], frozen["primary_pair"]["right"])
    assert len(r.ESTIMATORS) == len(set(r.ESTIMATORS)) == 24
    assert len(r.PAIRS) == len(set(r.PAIRS)) == 24
    assert r.PRECISION_THRESHOLD == frozen["precision"]["primary_paired_mse_mcse_threshold"]


def test_empty_records_preserve_all_2304_slots_and_96_pairs_per_contrast():
    out = r.summarize_stop_anchor(jobs(), [], .5)
    assert out["planned_estimator_slots"] == len(out["slots"]) == 2304
    assert out["status_counts"] == dict(attempted=0, completed=0, failed=0, unattempted=2304)
    assert out["attempted_estimator_slots"] == 0
    assert out["incomplete"] and not out["all_planned_results_complete"]
    assert out["primary_precision"]["status"] == "unassessable"
    assert out["primary_precision"]["numerical_criterion_met"] is None
    d = estimator(out)
    assert d["planned"] == 96 and d["attempted"] == d["point_metric_denominator"] == 0
    assert d["bias"] is d["rmse"] is d["empirical_sd"] is d["bias_mcse"] is None
    assert d["intervals"]["returned_interval_coverage"] is None
    assert d["intervals"]["operational_covering_per_attempted"] is None
    assert d["intervals"]["coverage_exact_binomial_95"] is None
    pairs = out["cells"]["weak_overlap"]["paired_comparisons"]
    assert len(pairs) == len({pair["pair_id"] for pair in pairs}) == 24
    assert all(pair["planned_pairs"] == pair["excluded_pairs"] == 96 for pair in pairs)
    assert all(pair["joint_completed_pairs"] == 0 and pair["paired_mcse"] is None for pair in pairs)
    assert "intervals" not in estimator(out, PLUGIN)
    json.dumps(out, allow_nan=False)


def test_hand_metrics_keep_finite_point_with_failed_interval():
    plan = jobs()
    records = [point(plan[i], LEFT, value, se) for i, (value, se) in
               enumerate(zip([.25, .5, 1., .5], [.1, .2, 0., None]))]
    records.append({**plan[4], "estimator": LEFT, "status": "failed", "reason": "fit failed"})
    out = r.summarize_stop_anchor(plan, records, .5)
    d = estimator(out)
    assert d["status_counts"] == dict(attempted=0, completed=4, failed=1, unattempted=91)
    assert d["attempted"] == 5 and d["point_metric_denominator"] == 4
    assert d["bias"] == pytest.approx(1/16)
    assert d["rmse"] == pytest.approx(math.sqrt(5/64))
    assert d["empirical_sd"] == pytest.approx(math.sqrt(19/192))
    assert d["bias_mcse"] == pytest.approx(math.sqrt(19/768))
    ci = d["intervals"]
    assert ci["returned"] == 3 and ci["failed_after_completed_point"] == 1
    assert ci["no_completed_point"] == 92
    assert ci["covered"] == ci["below_truth"] == ci["above_truth"] == 1
    assert ci["returned_interval_coverage"] == pytest.approx(1/3)
    assert ci["operational_covering_per_attempted"] == pytest.approx(1/5)
    assert ci["operational_denominator"] == 5
    assert ci["coverage_mcse"] == pytest.approx(math.sqrt(2/27))
    assert ci["mean_se"] == pytest.approx(.1)
    assert ci["rms_se"] == pytest.approx(math.sqrt(1/60))
    assert ci["mean_width"] == pytest.approx(.392)
    lower, upper = ci["coverage_exact_binomial_95"]
    assert 1-(1-lower)**3 == pytest.approx(.025)
    assert (1-upper)**3+3*upper*(1-upper)**2 == pytest.approx(.025)


def test_five_of_six_returned_intervals_is_not_five_of_eight_attempts():
    plan = jobs()
    records = [point(plan[i], LEFT, .5 if i < 5 else 1., 0.) for i in range(6)]
    records.append(point(plan[6], LEFT, .5))  # Finite point, failed interval.
    records.append({**plan[7], "estimator": LEFT, "status": "failed", "reason": "point unavailable"})
    out = r.summarize_stop_anchor(plan, records, .5)
    d = estimator(out)
    assert d["attempted"] == 8 and d["point_metric_denominator"] == 7
    assert d["intervals"]["returned"] == 6 and d["intervals"]["covered"] == 5
    assert d["intervals"]["returned_interval_coverage"] == pytest.approx(5/6)
    assert d["intervals"]["operational_covering_per_attempted"] == pytest.approx(5/8)


def test_unfinished_failed_and_unattempted_are_retained_with_distinct_meanings():
    plan = jobs()
    records = [{**plan[0], "estimator": LEFT, "status": "attempted", "reason": "time cap during processing"},
               {**plan[1], "estimator": LEFT, "status": "failed", "reason": "nonfinite point"},
               {**plan[2], "estimator": LEFT, "status": "unattempted", "reason": "job not reached"}]
    out = r.summarize_stop_anchor(plan, records, .5)
    d = estimator(out)
    assert d["status_counts"] == dict(attempted=1, completed=0, failed=1, unattempted=94)
    assert d["attempted"] == 2 and d["point_metric_denominator"] == 0
    assert d["intervals"]["operational_covering_per_attempted"] == 0
    assert d["intervals"]["returned_interval_coverage"] is None
    assert "not a count of actual fits" in out["attempted_slot_definition"]
    assert "complete durable attempt ledger" in out["omitted_slot_contract"]
    retained = [row for row in out["slots"] if row["estimator"] == LEFT][:3]
    assert [row["reason"] for row in retained] == [row["reason"] for row in records]


def test_paired_errors_include_failed_intervals_and_use_joint_points():
    plan = jobs()
    records = [point(plan[i], LEFT, value) for i, value in [(0, .75), (1, .5), (3, .5)]]
    records += [point(plan[i], RIGHT, value, .1) for i, value in [(0, .5), (1, .75), (3, .75)]]
    records.append(point(plan[2], LEFT, .5, .1))  # Its partner is absent.
    out = r.summarize_stop_anchor(plan, records, .5)
    pair = primary_pair(out)
    assert pair["joint_completed_pairs"] == 3 and pair["excluded_pairs"] == 93
    assert [row["replicate"] for row in pair["included"]] == [0, 1, 3]
    assert [row["squared_error_difference"] for row in pair["included"]] == [1/16, -1/16, -1/16]
    assert pair["mean_squared_error_difference"] == pytest.approx(-1/48)
    assert pair["paired_mcse"] == pytest.approx(1/24)
    assert pair["mean_estimate_difference"] == pytest.approx(-1/12)
    assert pair["estimate_difference_mcse"] == pytest.approx(1/6)
    assert pair["excluded"][0]["replicate"] == 2
    assert out["primary_precision"]["status"] == "unassessable"


def test_one_point_mcse_undefined_and_exact_boundary_interval_nonzero():
    plan = jobs()
    out = r.summarize_stop_anchor(plan, [point(plan[0], LEFT, .5, 0.)], .5)
    d = estimator(out)
    assert d["bias"] == d["rmse"] == 0
    assert d["bias_mcse"] is d["empirical_sd"] is None
    assert d["intervals"]["coverage_mcse"] == 0
    assert d["intervals"]["coverage_exact_binomial_95"] == pytest.approx([.025, 1.])
    assert r.exact_binomial_interval(0, 1) == pytest.approx([0., .975])
    assert r.exact_binomial_interval(0, 0) is None


def test_complete_96_primary_precision_is_conditional_not_significance():
    plan = jobs()
    records = all_records(plan)
    out = r.summarize_stop_anchor(plan, records, .5)
    assert out["status_counts"] == dict(attempted=0, completed=2304, failed=0, unattempted=0)
    assert out["all_planned_results_complete"] and not out["incomplete"]
    precision = out["primary_precision"]
    assert precision["arithmetic_assessable"] and precision["numerical_criterion_met"] is True
    assert precision["status"] == "within_threshold_conditional_on_sampling_assumptions"
    assert precision["paired_mcse"] == 0 and precision["threshold"] == .005
    assert precision["independent_datasets_verified"] is False
    assert "not establish independence, significance" in precision["interpretation"]
    assert r.summarize_stop_anchor(plan[::-1], records[::-1], .5) == out
    json.dumps(out, allow_nan=False)


def test_primary_precision_above_threshold_is_not_a_test_of_improvement():
    plan = jobs()
    records = [point(job, name, 1.5 if name == LEFT and job["replicate"] % 2 else .5, .1)
               for job in plan for name in r.ESTIMATORS]
    out = r.summarize_stop_anchor(plan, records, .5)
    precision = out["primary_precision"]
    assert precision["arithmetic_assessable"] and precision["numerical_criterion_met"] is False
    assert precision["status"] == "insufficient_precision_conditional_on_sampling_assumptions"
    assert precision["paired_mcse"] == pytest.approx(math.sqrt(1/380))
    assert primary_pair(out)["mean_squared_error_difference"] == .5


@pytest.mark.parametrize("defect", ["truncated", "missing_primary", "unrelated_interval_failure"])
def test_even_small_primary_mcse_is_unassessable_if_any_dataset_incomplete(defect):
    plan, records = jobs(), all_records(jobs())
    if defect == "missing_primary":
        records = [row for row in records if not (row["replicate"] == 95 and row["estimator"] == LEFT)]
    elif defect == "unrelated_interval_failure":
        records[1]["interval"] = dict(status="failed", reason="SE unavailable")
    out = r.summarize_stop_anchor(plan, records, .5, truncated=defect == "truncated")
    assert out["primary_precision"]["status"] == "unassessable"
    assert out["primary_precision"]["numerical_criterion_met"] is None
    assert out["incomplete"]
    if defect == "truncated":
        assert out["all_planned_results_complete"]


@pytest.mark.parametrize("successes,trials", [(-1, 96), (1, -1), (97, 96), (True, 1), (1, 1.0)])
def test_negative_invalid_binomial_counts_rejected(successes, trials):
    with pytest.raises(ValueError):
        r.exact_binomial_interval(successes, trials)


@pytest.mark.parametrize("defect", ["short_plan", "extra_job", "duplicate_job", "negative_replicate",
    "bool_replicate", "wrong_cell", "empty_pairing", "reused_pairing", "extra_field"])
def test_full_plan_and_identity_contract_fail_closed(defect):
    plan = jobs()
    if defect == "short_plan": plan.pop()
    elif defect == "extra_job": plan.append({**plan[0], "replicate": 96})
    elif defect == "duplicate_job": plan.append(plan[0])
    elif defect == "negative_replicate": plan[0]["replicate"] = -1
    elif defect == "bool_replicate": plan[0]["replicate"] = False
    elif defect == "wrong_cell": plan[0]["cell_id"] = "base"
    elif defect == "empty_pairing": plan[0]["pairing_id"] = " "
    elif defect == "reused_pairing": plan[1]["pairing_id"] = plan[0]["pairing_id"]
    else: plan[0]["counts"] = -1
    with pytest.raises(ValueError):
        r.summarize_stop_anchor(plan, [], .5)


@pytest.mark.parametrize("defect", ["duplicate", "unknown_job", "wrong_pairing", "unknown_estimator",
    "unknown_status", "plugin_ci", "invalid_ci", "negative_se", "no_dr_interval", "no_reason",
    "extra_count", "failed_with_estimate", "nonfinite_truth", "nonboolean_truncated"])
def test_record_schema_and_bindings_fail_closed(defect):
    plan = jobs()
    records, truth, truncated = [point(plan[0], LEFT, .5, .1)], .5, False
    if defect == "duplicate": records *= 2
    elif defect == "unknown_job": records[0]["replicate"] = 96
    elif defect == "wrong_pairing": records[0]["pairing_id"] = "different-data-or-folds"
    elif defect == "unknown_estimator": records[0]["estimator"] = "oracle"
    elif defect == "unknown_status": records[0]["status"] = "dropped"
    elif defect == "plugin_ci": records[0]["estimator"] = PLUGIN
    elif defect == "invalid_ci": records[0]["interval"]["lo"] = 0
    elif defect == "negative_se": records[0]["interval"]["se"] = -.1
    elif defect == "no_dr_interval": records[0].pop("interval")
    elif defect == "no_reason": records = [{**plan[0], "estimator": LEFT, "status": "failed"}]
    elif defect == "extra_count": records[0]["completed"] = -1
    elif defect == "failed_with_estimate":
        records = [{**plan[0], "estimator": LEFT, "status": "failed", "reason": "failure", "estimate": .5}]
    elif defect == "nonfinite_truth": truth = float("nan")
    else: truncated = 1
    with pytest.raises(ValueError):
        r.summarize_stop_anchor(plan, records, truth, truncated=truncated)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "0.5", 1e308])
def test_nonfinite_or_unrepresentable_point_is_not_dropped(value):
    plan = jobs()
    with pytest.raises(ValueError):
        r.summarize_stop_anchor(plan, [point(plan[0], PLUGIN, value)], .5)


def test_interval_width_overflow_rejected():
    plan = jobs()
    record = point(plan[0], LEFT, .5, 5e307)
    assert math.isfinite(record["interval"]["lo"]) and math.isfinite(record["interval"]["hi"])
    with pytest.raises(ValueError, match="interval-width"):
        r.summarize_stop_anchor(plan, [record], .5)


def test_unrepresentable_paired_sd_raises_instead_of_returning_infinity():
    plan = jobs()
    records = [point(plan[0], LEFT, 1.2e154), point(plan[0], RIGHT, 0.),
               point(plan[1], LEFT, 0.), point(plan[1], RIGHT, 1.2e154)]
    with pytest.raises(ValueError, match="aggregate SD"):
        r.summarize_stop_anchor(plan, records, 0.)


def test_inputs_are_not_mutated():
    plan = jobs()
    records = [point(plan[0], LEFT, .5, .1)]
    before = copy.deepcopy((plan, records))
    r.summarize_stop_anchor(plan, records, .5)
    assert (plan, records) == before
