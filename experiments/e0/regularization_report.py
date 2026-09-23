"""Failure-preserving summaries; this module generates no data or fits.

API: summarize_regularization(planned_jobs, records, truth, truncated=False).
Each planned job is exactly {cell_id: str, replicate: int>=0, pairing_id: str}.
pairing_id identifies the frozen dataset AND root-fold assignment; every supplied
record must match it. This checks the supplied binding, not the underlying data.
Each job expands to all eight ESTIMATORS. A record has the three job fields plus
estimator and status. Status completed requires finite estimate. Completed DR
also requires interval={status:'valid', se, lo, hi} matching estimate +/-1.96*se,
or {status:'failed', reason}. Plugin records cannot carry intervals. Other point
statuses (attempted=unfinished, failed, unattempted) require a nonempty reason and
cannot carry estimates/intervals. Omitted slots become unattempted with a reason.
This interpretation requires a complete durable attempt ledger upstream: an absent
result alone does not prove that computation never started. Pairing IDs must be
unique across planned jobs, without thereby proving independent draws.
Duplicate/unknown slots, invalid numeric values and inconsistent bindings raise;
they are never silently omitted. Record nonfinite point computations as failed,
and finite points with failed intervals as completed plus interval failure.

Point metrics use completed points, including interval failures. DR uncertainty
metrics use returned valid intervals; operational covering/attempted-estimator
slots is separately named. Every planned slot and reason is returned. Twelve
paired comparisons cover the three prespecified axes across eight estimators.
CP intervals and plug-in MCSEs are descriptive binomial calculations, not a
certificate for selected/truncated/dependent runs. No plugin CI is produced.
"""
from __future__ import annotations

import math
import numbers
import statistics

from scipy.stats import beta

VARIANTS = tuple(f"{rep}_lambda{lam}" for rep in ("compressed", "history") for lam in (0, 5))
ESTIMATORS = tuple(f"{v}:{method}" for v in VARIANTS for method in ("plugin", "dr"))
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
    if any(not isinstance(row[k], str) or not row[k].strip() for k in ("cell_id", "pairing_id")):
        raise ValueError("cell_id and pairing_id must be nonempty strings")
    if type(row["replicate"]) is not int or row["replicate"] < 0:
        raise ValueError("replicate must be a nonnegative integer")
    return row["cell_id"], row["replicate"]


def exact_binomial_interval(successes, trials):
    """Equal-tail pointwise 95% Clopper-Pearson; no trials means undefined."""
    if type(successes) is not int or type(trials) is not int or not 0 <= successes <= trials:
        raise ValueError("require integer 0 <= successes <= trials")
    if not trials:
        return None
    return [0.0 if successes == 0 else float(beta.ppf(.025, successes, trials - successes + 1)),
            1.0 if successes == trials else float(beta.ppf(.975, successes + 1, trials - successes))]


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
    return scale * math.sqrt(_mean([(v / scale) ** 2 for v in values])) if scale else 0.0


def _mcse(values):
    return _sd(values) / math.sqrt(len(values)) if len(values) >= 2 else None


def _comparisons():
    pairs = []
    for lam in (0, 5):
        for method in ("plugin", "dr"):
            pairs.append(("history_minus_compressed", f"history_lambda{lam}:{method}", f"compressed_lambda{lam}:{method}"))
    for rep in ("compressed", "history"):
        for method in ("plugin", "dr"):
            pairs.append(("shrunk_minus_raw", f"{rep}_lambda5:{method}", f"{rep}_lambda0:{method}"))
    pairs.extend(("dr_minus_plugin", f"{v}:dr", f"{v}:plugin") for v in VARIANTS)
    return pairs


def summarize_regularization(planned_jobs, records, truth, *, truncated=False):
    """Return per-cell tables, all planned slots, denominators and paired errors.

Incomplete includes unattempted/unfinished/failed points or failed DR intervals,
as well as explicit time/output truncation even if all supplied slots completed.
Unavailable SD/MCSE/coverage values are None, never fabricated zero precision.
"""
    truth = _number(truth, "truth")
    if type(truncated) is not bool:
        raise ValueError("truncated must be boolean")
    plan, pairing_ids = {}, set()
    for job in planned_jobs:
        if not isinstance(job, dict) or set(job) != JOB_FIELDS:
            raise ValueError("planned jobs must contain exactly the three job fields")
        key = _job(job)
        if key in plan:
            raise ValueError("duplicate planned job")
        if job["pairing_id"] in pairing_ids:
            raise ValueError("pairing_id reused across distinct planned jobs")
        pairing_ids.add(job["pairing_id"])
        plan[key] = dict(job)
    if not plan:
        raise ValueError("planned_jobs must not be empty")
    supplied = {}
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("records must be objects")
        job = _job(row)
        estimator, status = row.get("estimator"), row.get("status")
        if job not in plan or row["pairing_id"] != plan[job]["pairing_id"]:
            raise ValueError("unknown job or mismatched dataset/fold pairing_id")
        if estimator not in ESTIMATORS or status not in STATUSES:
            raise ValueError("unknown estimator or status")
        key = (*job, estimator)
        if key in supplied:
            raise ValueError("duplicate estimator record")
        fields = JOB_FIELDS | {"estimator", "status"}
        normalized = {k: row[k] for k in fields}
        if status == "completed":
            fields |= {"estimate"}
            estimate = _number(row.get("estimate"), "estimate")
            error = estimate - truth
            if not math.isfinite(error) or not math.isfinite(error * error):
                raise ValueError("nonfinite squared-error arithmetic; record an explicit point failure")
            normalized["estimate"] = estimate
            if estimator.endswith(":dr"):
                fields |= {"interval"}
                interval = row.get("interval")
                if not isinstance(interval, dict):
                    raise ValueError("completed DR requires explicit interval status")
                if interval.get("status") == "valid":
                    if set(interval) != {"status", "se", "lo", "hi"}:
                        raise ValueError("valid interval requires exactly status/se/lo/hi")
                    se, lo, hi = (_number(interval[k], k) for k in ("se", "lo", "hi"))
                    if se < 0 or lo > hi or not lo <= estimate <= hi:
                        raise ValueError("invalid SE or interval order")
                    if not math.isfinite(hi - lo):
                        raise ValueError("nonfinite interval-width arithmetic")
                    if not (math.isclose(lo, estimate - 1.96 * se, rel_tol=1e-12, abs_tol=1e-12)
                            and math.isclose(hi, estimate + 1.96 * se, rel_tol=1e-12, abs_tol=1e-12)):
                        raise ValueError("interval must match the fixed estimate +/-1.96SE procedure")
                    normalized["interval"] = dict(status="valid", se=se, lo=lo, hi=hi)
                elif interval.get("status") == "failed" and set(interval) == {"status", "reason"}:
                    normalized["interval"] = dict(status="failed", reason=_reason(interval["reason"]))
                else:
                    raise ValueError("invalid interval status or fields")
        else:
            fields |= {"reason"}
            normalized["reason"] = _reason(row.get("reason"))
        if set(row) != fields:
            raise ValueError("unexpected or missing record fields (plugin intervals are forbidden)")
        supplied[key] = normalized
    slots = []
    for job in plan.values():
        for estimator in ESTIMATORS:
            key = (job["cell_id"], job["replicate"], estimator)
            slots.append(supplied.get(key, {**job, "estimator": estimator, "status": "unattempted",
                                             "reason": "no_record_returned"}))
    complete = all(x["status"] == "completed" and (not x["estimator"].endswith(":dr")
                   or x["interval"]["status"] == "valid") for x in slots)
    by_key = {(s["cell_id"], s["replicate"], s["estimator"]): s for s in slots}
    cells = {}
    for cell in dict.fromkeys(k[0] for k in plan):
        jobs = [job for key, job in plan.items() if key[0] == cell]
        table = {}
        for estimator in ESTIMATORS:
            selected = [by_key[(cell, j["replicate"], estimator)] for j in jobs]
            counts = {s: sum(x["status"] == s for x in selected) for s in STATUSES}
            attempted = len(selected) - counts["unattempted"]
            points = [x for x in selected if x["status"] == "completed"]
            estimates = [x["estimate"] for x in points]
            errors = [v - truth for v in estimates]
            result = {"planned": len(jobs), "attempted": attempted, "status_counts": counts,
                      "point_metric_denominator": len(points), "point_metric_scope": "completed points only",
                      "bias": _mean(errors), "rmse": _rms(errors),
                      "empirical_sd": _sd(estimates), "bias_mcse": _mcse(errors)}
            if estimator.endswith(":dr"):
                valid = [x["interval"] for x in points if x["interval"]["status"] == "valid"]
                failed = [x for x in points if x["interval"]["status"] == "failed"]
                n = len(valid)
                covered = sum(x["lo"] <= truth <= x["hi"] for x in valid)
                coverage = covered / n if n else None
                result["intervals"] = {"procedure": "estimate +/-1.96 root-level SE", "returned": n,
                    "failed_after_completed_point": len(failed), "no_completed_point": len(jobs) - len(points),
                    "mean_se": _mean([x["se"] for x in valid]),
                    "rms_se": _rms([x["se"] for x in valid]),
                    "se_metric_denominator": n, "covered": covered,
                    "below_truth": sum(x["hi"] < truth for x in valid),
                    "above_truth": sum(x["lo"] > truth for x in valid),
                    "returned_interval_coverage": coverage,
                    "coverage_mcse": math.sqrt(coverage * (1 - coverage) / n) if n else None,
                    "coverage_exact_binomial_95": exact_binomial_interval(covered, n),
                    "mean_width": _mean([x["hi"] - x["lo"] for x in valid]),
                    "operational_covering_per_attempted": covered / attempted if attempted else None,
                    "operational_denominator": attempted,
                    "operational_definition": "covered valid intervals / attempted estimator slots, including failed/unfinished points and failed intervals; not coverage"}
            table[estimator] = result
        pairs = []
        for axis, left, right in _comparisons():
            differences, included, excluded = [], [], []
            for job in jobs:
                a, b = (by_key[(cell, job["replicate"], name)] for name in (left, right))
                if a["status"] == b["status"] == "completed":
                    try:
                        difference = (a["estimate"] - truth) ** 2 - (b["estimate"] - truth) ** 2
                    except OverflowError as exc:
                        raise ValueError("paired squared-error arithmetic overflow") from exc
                    if not math.isfinite(difference):
                        raise ValueError("paired squared-error arithmetic nonfinite")
                    differences.append(difference)
                    included.append({**job, "squared_error_difference": difference})
                else:
                    excluded.append({**job, "left_status": a["status"], "right_status": b["status"],
                                     "left_reason": a.get("reason"), "right_reason": b.get("reason")})
            pairs.append({"axis": axis, "left": left, "right": right,
                          "sign": "left squared error minus right squared error; negative favors left",
                          "planned_pairs": len(jobs), "joint_completed_pairs": len(differences),
                          "excluded_pairs": len(excluded), "mean_squared_error_difference": _mean(differences),
                          "paired_mcse": _mcse(differences), "included": included, "excluded": excluded})
        cells[cell] = {"planned_jobs": len(jobs), "estimators": table, "paired_comparisons": pairs}
    return {"schema_version": "e0-regularization-report-v1", "truth": truth,
            "planned_jobs": list(plan.values()), "planned_estimator_slots": len(slots),
            "supplied_records": len(supplied), "all_planned_results_complete": complete,
            "truncated": truncated, "incomplete": truncated or not complete,
            "precision_scope": "descriptive completed-record metrics; no unconditional precision or coverage guarantee for incomplete, selected, dependent or time-truncated runs",
            "binomial_interval_method": "pointwise two-sided equal-tail 95% Clopper-Pearson, conservative iid Bernoulli inversion; not simultaneous or truncation-adjusted",
            "coverage_mcse_method": "plug-in sqrt(p_hat*(1-p_hat)/n_returned); may be zero at boundaries while exact interval remains nondegenerate",
            "slots": slots, "cells": cells}
