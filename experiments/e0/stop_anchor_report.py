"""Failure-preserving reports for the fixed 96-dataset STOP-anchor design.

This module reads no files and draws no data, fits no estimators, and authorizes
no execution. The full plan is required: weak_overlap, replicate IDs 0..95, and
unique nonempty dataset/fold pairing IDs. Every job expands to 24 estimator
slots, including when records is empty. Pairing strings check supplied identity,
not the underlying arrays, honest folds, or independence of datasets.

Record schema follows the frozen regularization reporter. A completed point has
a finite estimate; a completed DR point additionally has a valid fixed 1.96-SE
interval or an explicit interval failure. Plugin intervals are forbidden. Other
statuses need a reason and cannot carry estimates. Missing records are marked
unattempted ONLY under the upstream complete durable-attempt-ledger contract.
At shared job_start all 24 operational slots are attempted; this does not mean
24 fits started. Fitting/processing counts need the separate job event ledger.

Point metrics include finite points with failed intervals. Returned-interval
coverage and covering/attempted are distinct. All 24 paired comparisons use only
jointly completed points, retain exclusions, and use paired error differences.
The primary precision flag is conditional arithmetic, never significance: it
requires all 96 dataset result sets complete and no truncation, and still assumes
independent fixed-size datasets, which this reporter cannot establish. The root
Wald intervals themselves remain unvalidated. CP/MCSE calculations do not repair
return selection, dependence or time truncation. No plugin interval is produced.
"""
from __future__ import annotations

import math
import numbers
import statistics

from scipy.stats import beta

CELL_ID = "weak_overlap"
N_DATASETS = 96
PRECISION_THRESHOLD = .005
REPRESENTATIONS = ("compressed", "history")
PENALTIES = (0, 5)
MODES = ("original", "evaluation_only", "recursive")
METHODS = ("plugin", "dr")
VARIANTS = tuple(f"{rep}_lambda{lam}_{mode}"
                 for rep in REPRESENTATIONS for lam in PENALTIES for mode in MODES)
ESTIMATORS = tuple(f"{variant}:{method}" for variant in VARIANTS for method in METHODS)
MODE_PAIRS = (("evaluation_only", "original"), ("recursive", "evaluation_only"),
              ("recursive", "original"))
PAIRS = tuple((f"{rep}_lambda{lam}_{left}:{method}", f"{rep}_lambda{lam}_{right}:{method}")
              for rep in REPRESENTATIONS for lam in PENALTIES for method in METHODS
              for left, right in MODE_PAIRS)
PRIMARY_PAIR = ("history_lambda5_recursive:dr", "history_lambda5_original:dr")
STATUSES = ("attempted", "completed", "failed", "unattempted")
JOB_FIELDS = {"cell_id", "replicate", "pairing_id"}


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    return float(value)


def _reason(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("a nonempty reason is required")
    return value


def _job(row):
    if not JOB_FIELDS <= row.keys():
        raise ValueError("missing job identity fields")
    if row["cell_id"] != CELL_ID:
        raise ValueError("cell_id must be weak_overlap")
    if not isinstance(row["pairing_id"], str) or not row["pairing_id"].strip():
        raise ValueError("pairing_id must be a nonempty string")
    if type(row["replicate"]) is not int or not 0 <= row["replicate"] < N_DATASETS:
        raise ValueError("replicate must be an integer from 0 through 95")
    return row["replicate"]


def exact_binomial_interval(successes, trials):
    """Pointwise equal-tail 95% Clopper-Pearson arithmetic; undefined at n=0."""
    if type(successes) is not int or type(trials) is not int or not 0 <= successes <= trials:
        raise ValueError("require integer 0 <= successes <= trials")
    if not trials:
        return None
    return [0. if successes == 0 else float(beta.ppf(.025, successes, trials-successes+1)),
            1. if successes == trials else float(beta.ppf(.975, successes+1, trials-successes))]


def _mean(values):
    try:
        value = statistics.mean(values) if values else None
    except OverflowError as exc:
        raise ValueError("aggregate mean arithmetic overflow") from exc
    return _number(value, "aggregate mean") if value is not None else None


def _sd(values):
    try:
        value = statistics.stdev(values) if len(values) >= 2 else None
    except OverflowError as exc:
        raise ValueError("aggregate SD arithmetic overflow") from exc
    return _number(value, "aggregate SD") if value is not None else None


def _rms(values):
    if not values:
        return None
    scale = max(abs(v) for v in values)
    return scale * math.sqrt(_mean([(v/scale)**2 for v in values])) if scale else 0.


def _mcse(values):
    return _sd(values)/math.sqrt(len(values)) if len(values) >= 2 else None


def _record(row, plan):
    if not isinstance(row, dict):
        raise ValueError("records must be objects")
    replicate = _job(row)
    estimator, status = row.get("estimator"), row.get("status")
    if row["pairing_id"] != plan[replicate]["pairing_id"]:
        raise ValueError("mismatched dataset/fold pairing_id")
    if estimator not in ESTIMATORS or status not in STATUSES:
        raise ValueError("unknown estimator or status")
    fields = JOB_FIELDS | {"estimator", "status"}
    result = {k: row[k] for k in fields}
    if status == "completed":
        fields |= {"estimate"}
        result["estimate"] = _number(row.get("estimate"), "estimate")
        if estimator.endswith(":dr"):
            fields |= {"interval"}
            interval = row.get("interval")
            if not isinstance(interval, dict):
                raise ValueError("completed DR requires explicit interval status")
            if interval.get("status") == "valid":
                if set(interval) != {"status", "se", "lo", "hi"}:
                    raise ValueError("valid interval requires exactly status/se/lo/hi")
                se, lo, hi = (_number(interval[k], k) for k in ("se", "lo", "hi"))
                estimate = result["estimate"]
                if se < 0 or lo > hi or not lo <= estimate <= hi:
                    raise ValueError("invalid SE or interval order")
                if not math.isfinite(hi-lo):
                    raise ValueError("nonfinite interval-width arithmetic")
                if not (math.isclose(lo, estimate-1.96*se, rel_tol=1e-12, abs_tol=1e-12)
                        and math.isclose(hi, estimate+1.96*se, rel_tol=1e-12, abs_tol=1e-12)):
                    raise ValueError("interval must match the fixed estimate +/-1.96SE procedure")
                result["interval"] = dict(status="valid", se=se, lo=lo, hi=hi)
            elif interval.get("status") == "failed" and set(interval) == {"status", "reason"}:
                result["interval"] = dict(status="failed", reason=_reason(interval["reason"]))
            else:
                raise ValueError("invalid interval status or fields")
    else:
        fields |= {"reason"}
        result["reason"] = _reason(row.get("reason"))
    if set(row) != fields:
        raise ValueError("unexpected or missing record fields (plugin intervals are forbidden)")
    return result


def summarize_stop_anchor(planned_jobs, records, truth, *, truncated=False):
    """Expand the full plan and summarize returned records without silently dropping failures.

Incomplete includes any unfinished/unattempted/failed point, failed DR interval,
or explicit truncation. Precision is unassessable on that incomplete result set;
even a complete-set numeric flag assumes independence and is not significance.
"""
    truth = _number(truth, "truth")
    if type(truncated) is not bool:
        raise ValueError("truncated must be boolean")
    plan, pairing_ids = {}, set()
    for job in planned_jobs:
        if not isinstance(job, dict) or set(job) != JOB_FIELDS:
            raise ValueError("planned jobs must contain exactly the three job fields")
        replicate = _job(job)
        if replicate in plan:
            raise ValueError("duplicate planned job")
        if job["pairing_id"] in pairing_ids:
            raise ValueError("pairing_id reused across distinct planned jobs")
        pairing_ids.add(job["pairing_id"])
        plan[replicate] = dict(job)
    if set(plan) != set(range(N_DATASETS)):
        raise ValueError("the complete 96-job plan (replicates 0..95) is required")
    jobs = [plan[i] for i in range(N_DATASETS)]
    supplied = {}
    for row in records:
        normalized = _record(row, plan)
        key = normalized["replicate"], normalized["estimator"]
        if key in supplied:
            raise ValueError("duplicate estimator record")
        if normalized["status"] == "completed":
            error = normalized["estimate"]-truth
            if not math.isfinite(error) or not math.isfinite(error*error):
                raise ValueError("nonfinite squared-error arithmetic; record an explicit point failure")
        supplied[key] = normalized
    slots = [supplied.get((job["replicate"], estimator),
                         {**job, "estimator": estimator, "status": "unattempted",
                          "reason": "no_record_returned_under_complete_attempt_ledger_contract"})
             for job in jobs for estimator in ESTIMATORS]
    by_key = {(row["replicate"], row["estimator"]): row for row in slots}
    complete = all(row["status"] == "completed" and
                   (not row["estimator"].endswith(":dr") or row["interval"]["status"] == "valid")
                   for row in slots)
    totals = {status: sum(row["status"] == status for row in slots) for status in STATUSES}
    table = {}
    for estimator in ESTIMATORS:
        selected = [by_key[(j["replicate"], estimator)] for j in jobs]
        counts = {status: sum(row["status"] == status for row in selected) for status in STATUSES}
        attempted = N_DATASETS-counts["unattempted"]
        points = [row for row in selected if row["status"] == "completed"]
        estimates = [row["estimate"] for row in points]
        errors = [value-truth for value in estimates]
        result = dict(planned=N_DATASETS, attempted=attempted, status_counts=counts,
                      point_metric_denominator=len(points), point_metric_scope="completed points only",
                      bias=_mean(errors), rmse=_rms(errors), empirical_sd=_sd(estimates),
                      bias_mcse=_mcse(errors))
        if estimator.endswith(":dr"):
            valid = [row["interval"] for row in points if row["interval"]["status"] == "valid"]
            failed = [row for row in points if row["interval"]["status"] == "failed"]
            n = len(valid)
            covered = sum(ci["lo"] <= truth <= ci["hi"] for ci in valid)
            coverage = covered/n if n else None
            result["intervals"] = dict(
                procedure="estimate +/-1.96 root-level SE; finite-sample coverage unvalidated",
                returned=n, failed_after_completed_point=len(failed),
                no_completed_point=N_DATASETS-len(points), se_metric_denominator=n,
                mean_se=_mean([ci["se"] for ci in valid]), rms_se=_rms([ci["se"] for ci in valid]),
                covered=covered, below_truth=sum(ci["hi"] < truth for ci in valid),
                above_truth=sum(ci["lo"] > truth for ci in valid), returned_interval_coverage=coverage,
                coverage_mcse=math.sqrt(coverage*(1-coverage)/n) if n else None,
                coverage_exact_binomial_95=exact_binomial_interval(covered, n),
                mean_width=_mean([ci["hi"]-ci["lo"] for ci in valid]),
                operational_covering_per_attempted=covered/attempted if attempted else None,
                operational_denominator=attempted,
                operational_definition="covered valid intervals / operational attempted estimator slots, including failed/unfinished points and failed intervals; not coverage")
        table[estimator] = result
    comparisons = []
    for left, right in PAIRS:
        squared_differences, point_differences, included, excluded = [], [], [], []
        for job in jobs:
            a, b = (by_key[(job["replicate"], estimator)] for estimator in (left, right))
            if a["status"] == b["status"] == "completed":
                try:
                    square_difference = (a["estimate"]-truth)**2-(b["estimate"]-truth)**2
                except OverflowError as exc:
                    raise ValueError("paired squared-error arithmetic overflow") from exc
                difference = a["estimate"]-b["estimate"]
                if not math.isfinite(square_difference) or not math.isfinite(difference):
                    raise ValueError("paired arithmetic nonfinite")
                squared_differences.append(square_difference)
                point_differences.append(difference)
                included.append({**job, "estimate_difference": difference,
                                 "squared_error_difference": square_difference})
            else:
                excluded.append({**job, "left_status": a["status"], "right_status": b["status"],
                                 "left_reason": a.get("reason"), "right_reason": b.get("reason")})
        comparisons.append(dict(
            pair_id=f"{left}__minus__{right}", left=left, right=right,
            is_primary=(left, right) == PRIMARY_PAIR,
            sign="left squared error minus right squared error; negative favors left",
            estimate_difference_sign="left estimate minus right estimate",
            planned_pairs=N_DATASETS, joint_completed_pairs=len(included), excluded_pairs=len(excluded),
            mean_estimate_difference=_mean(point_differences),
            estimate_difference_mcse=_mcse(point_differences),
            mean_squared_error_difference=_mean(squared_differences), paired_mcse=_mcse(squared_differences),
            included=included, excluded=excluded))
    primary = next(pair for pair in comparisons if pair["is_primary"])
    reasons = []
    if truncated:
        reasons.append("explicitly_truncated")
    if not complete:
        reasons.append("not_all_96_dataset_result_sets_complete")
    if primary["joint_completed_pairs"] != N_DATASETS or primary["paired_mcse"] is None:
        reasons.append("primary_requires_all_96_jointly_completed_points_and_defined_mcse")
    arithmetic_assessable = not reasons
    criterion = primary["paired_mcse"] <= PRECISION_THRESHOLD if arithmetic_assessable else None
    precision = dict(
        pair_id=primary["pair_id"], left=PRIMARY_PAIR[0], right=PRIMARY_PAIR[1],
        metric="paired squared-error difference MCSE", threshold=PRECISION_THRESHOLD,
        units="squared policy-value units", paired_mcse=primary["paired_mcse"],
        arithmetic_assessable=arithmetic_assessable, numerical_criterion_met=criterion,
        status=("unassessable" if not arithmetic_assessable else
                "within_threshold_conditional_on_sampling_assumptions" if criterion else
                "insufficient_precision_conditional_on_sampling_assumptions"),
        unassessable_reasons=reasons, independent_datasets_verified=False,
        required_sampling_assumptions="96 independent fixed-size datasets; no outcome/return/time-based selection; pairing identity and root folds genuinely match",
        interpretation="conditional diagnostic precision flag only; reporter does not establish independence, significance, improvement, interval calibration or efficacy")
    return dict(
        schema_version="e0-stop-anchor-report-v1", truth=truth, planned_jobs=jobs,
        planned_estimator_slots=len(slots), supplied_records=len(supplied),
        status_counts=totals, attempted_estimator_slots=len(slots)-totals["unattempted"],
        attempted_slot_definition="operational processing assignment at durable shared job_start; not a count of actual fits or variant starts",
        omitted_slot_contract="absence means unattempted only after reconciliation with the complete durable attempt ledger",
        all_planned_results_complete=complete, truncated=truncated, incomplete=truncated or not complete,
        primary_precision=precision,
        precision_scope="descriptive completed-record metrics; no unconditional precision or coverage guarantee for incomplete, selected, dependent or time-truncated runs",
        binomial_interval_method="pointwise two-sided equal-tail 95% Clopper-Pearson, conservative iid Bernoulli inversion; not simultaneous or truncation-adjusted",
        coverage_mcse_method="plug-in sqrt(p_hat*(1-p_hat)/n_returned); may be zero at boundaries while exact interval remains nondegenerate",
        comparison_scope="all 24 prespecified comparisons are descriptive; no multiplicity-controlled winner selection",
        slots=slots, cells={CELL_ID: dict(planned_jobs=N_DATASETS, estimators=table,
                                        paired_comparisons=comparisons)})
