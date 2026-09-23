#!/usr/bin/env python3
"""Post-result descriptive calibration diagnostics from two pinned summaries.

This stdlib-only reader never opens the raw run, refits scores, samples data,
imports production statistics helpers, tunes a method or proposes a new CI.
All12 DR methods and all96 prespecified replicates must be present and complete.
The two retrospective constant-width counts reuse these same96 replicates to
estimate width; those widths are unavailable to a real single dataset.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILED = ROOT/"results/e0_stop_anchor_reconciled_20260923.json"
ARITHMETIC = ROOT/"results/e0_stop_anchor_independent_arithmetic_20260923.json"
RECONCILED_SHA256 = "2f5fee670034389e619e2b8a79eb716456ef39ee50b7fb28c94f785c346cdbd8"
ARITHMETIC_SHA256 = "9660c45af75e5915ac664ecd50c39f7586c9b502904724d9e982cc598d749bde"
TRUTH, N = .6459770061744536, 96
MAX_OUTPUT_BYTES = 10*1024*1024
VARIANTS = tuple(f"{r}_lambda{p}_{m}" for r in ("compressed", "history")
                 for p in (0, 5) for m in ("original", "evaluation_only", "recursive"))
ESTIMATORS = tuple(f"{v}:{m}" for v in VARIANTS for m in ("plugin", "dr"))
DR_ESTIMATORS = tuple(f"{v}:dr" for v in VARIANTS)
COUNTS = dict(attempted=0, completed=2304, failed=0, unattempted=0)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("finite numeric value required")
    return float(value)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite JSON constant: "+value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=invalid, parse_float=lambda s: finite(float(s)))


def mean(values):
    if not values:
        raise ValueError("nonempty data required")
    return finite(math.fsum(values)/len(values))


def sample_variance(values):
    if len(values) < 2:
        raise ValueError("sample variance needs at least2 values")
    center = mean(values)
    return finite(math.fsum((v-center)**2 for v in values)/(len(values)-1))


def skewness(values):
    """Empirical moment skewness m3/m2**1.5, m_k=n^-1 sum(x-mean)^k.

    Not a bias-corrected sample-skewness estimator. Constant inputs return None.
    Scaling centered values avoids unnecessary overflow; it cancels in the ratio.
    """
    center = mean(values)
    centered = [finite(v-center) for v in values]
    scale = max(abs(v) for v in centered)
    if scale == 0:
        return None
    scaled = [v/scale for v in centered]
    m2, m3 = mean([v*v for v in scaled]), mean([v*v*v for v in scaled])
    return finite(m3/(m2**1.5))


def pearson(left, right):
    """Centered-sum Pearson r; None if either vector has zero variation."""
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation requires paired vectors of length>=2")
    a, b = mean(left), mean(right)
    x, y = [finite(v-a) for v in left], [finite(v-b) for v in right]
    sx, sy = max(map(abs, x)), max(map(abs, y))
    if not sx or not sy:
        return None
    x, y = [v/sx for v in x], [v/sy for v in y]
    return finite(math.fsum(a*b for a, b in zip(x, y)) /
                  math.sqrt(math.fsum(a*a for a in x)*math.fsum(b*b for b in y)))


def quantile(values, probability):
    """Sorted linear interpolation: h=(n-1)p, between floor(h) and ceil(h)."""
    p = finite(probability)
    if not values or not 0 <= p <= 1:
        raise ValueError("nonempty values and probability in[0,1] required")
    ordered = sorted(finite(v) for v in values)
    h = (len(ordered)-1)*p
    lo, hi = math.floor(h), math.ceil(h)
    return finite(ordered[lo] if lo == hi else ordered[lo]+(h-lo)*(ordered[hi]-ordered[lo]))


def interval_counts(estimates, ses, truth):
    below = above = covered = 0
    for estimate, se in zip(estimates, ses):
        lo, hi = finite(estimate-1.96*se), finite(estimate+1.96*se)
        below += hi < truth
        above += lo > truth
        covered += lo <= truth <= hi
    return dict(total=len(estimates), below_truth=below, above_truth=above, covered=covered)


def product_empirical_counts(errors, ses):
    """All ordered error_i/SE_j pairs, including i=j; not independent trials."""
    below = above = covered = 0
    for error in errors:
        for se in ses:
            half = finite(1.96*se)
            below += error < -half
            above += error > half
            covered += -half <= error <= half
    total = len(errors)*len(ses)
    return dict(total_pairs=total, below_truth=below, above_truth=above, covered=covered,
                covered_fraction=covered/total)


def summarize_pairs(estimates, ses, *, truth=TRUTH):
    """Pure arithmetic fixture seam; production supplies exactly96 paired values."""
    truth = finite(truth)
    if len(estimates) != len(ses) or len(estimates) < 2:
        raise ValueError("at least2 aligned estimate/SE pairs required")
    estimates, ses = [finite(v) for v in estimates], [finite(v) for v in ses]
    if any(se <= 0 for se in ses):
        raise ValueError("strictly positive SE required")
    try:
        errors = [finite(v-truth) for v in estimates]
        z = [finite(error/se) for error, se in zip(errors, ses)]
        variance = sample_variance(errors)
        mse_se = mean([finite(se*se) for se in ses])
        empirical_sd, rms_se = math.sqrt(variance), math.sqrt(mse_se)
        result = dict(n=len(estimates), bias=mean(errors), empirical_sd_error=empirical_sd,
            mean_se=mean(ses), rms_se=rms_se, mean_square_se=mse_se,
            empirical_error_variance=variance,
            mean_square_se_over_empirical_variance=finite(mse_se/variance) if variance else None,
            moment_skewness_error=skewness(errors), moment_skewness_z=skewness(z),
            correlation_error_se=pearson(errors, ses),
            correlation_abs_error_se=pearson([abs(v) for v in errors], ses),
            z_quantiles={name: quantile(z, p) for name, p in
                         (("min", 0), ("q025", .025), ("median", .5), ("q975", .975), ("max", 1))},
            frozen_interval_counts=interval_counts(estimates, ses, truth),
            hindsight_constant_width_counts={
                "same_replicate_rms_se": dict(width_scale=rms_se,
                    **interval_counts(estimates, [rms_se]*len(ses), truth)),
                "same_replicate_empirical_sd": dict(width_scale=empirical_sd,
                    **interval_counts(estimates, [empirical_sd]*len(ses), truth))})
        repaired = product_empirical_counts(errors, ses)
        repaired["original_paired_coverage_fraction"] = result["frozen_interval_counts"]["covered"]/len(errors)
        repaired["fraction_minus_original_pairing"] = repaired["covered_fraction"]-repaired["original_paired_coverage_fraction"]
        result["product_empirical_repairing"] = repaired
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("nonrepresentable diagnostic arithmetic") from exc
    return result


def _close(value, expected):
    if not math.isclose(finite(value), finite(expected), rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("saved arithmetic mismatch")


def analyze(reconciled, arithmetic):
    """Validate the complete fixed study then describe all12 DR methods.

    Pure objects are a test seam. Production must enter diagnose() to verify the
    exact input bytes; this helper alone does not establish artifact provenance.
    """
    audit, summary = reconciled["audit"], reconciled["summary"]
    if (audit.get("schema_version") != "e0-stop-anchor-final-reconciliation-v1"
            or audit.get("input_hashes_stable") is not True
            or audit.get("journal_complete_normal_run") is not True
            or audit.get("child_exit_receipt_verified") is not True
            or audit.get("terminal_jobs") != N or audit.get("all_planned_slots") != 2304
            or summary.get("truth") != TRUTH or summary.get("planned_estimator_slots") != 2304
            or summary.get("status_counts") != COUNTS
            or summary.get("all_planned_results_complete") is not True
            or summary.get("truncated") is not False or summary.get("incomplete") is not False):
        raise ValueError("complete reconciled96-dataset/2304-point study required")
    if (arithmetic.get("schema_version") != "e0-stop-anchor-independent-arithmetic-v1"
            or arithmetic.get("reconciled_sha256") != RECONCILED_SHA256
            or arithmetic.get("truth") != TRUTH or arithmetic.get("raw_hashes_stable") is not True
            or arithmetic.get("completed_points_checked") != 2304
            or arithmetic.get("valid_DR_intervals_checked") != 1152
            or arithmetic.get("failed_DR_intervals_retained") != 0
            or arithmetic.get("truncated") is not False
            or arithmetic.get("all_planned_results_complete") is not True
            or arithmetic.get("raw_snapshot") != audit.get("raw_snapshot")):
        raise ValueError("matching complete independent arithmetic audit required")
    jobs = summary.get("planned_jobs", [])
    if (len(jobs) != N or [j.get("replicate") for j in jobs] != list(range(N))
            or any(type(j["replicate"]) is not int or j.get("cell_id") != "weak_overlap"
                   or not isinstance(j.get("pairing_id"), str) or not j["pairing_id"] for j in jobs)
            or len({j["pairing_id"] for j in jobs}) != N):
        raise ValueError("exact ordered replicate and pairing identities required")
    slots, rows = {}, summary.get("slots", [])
    if len(rows) != 2304:
        raise ValueError("all2304 slots required")
    for row in rows:
        rep, estimator = row.get("replicate"), row.get("estimator")
        if (type(rep) is not int or not 0 <= rep < N or estimator not in ESTIMATORS
                or (rep, estimator) in slots or row.get("status") != "completed"
                or any(row.get(k) != v for k, v in jobs[rep].items())):
            raise ValueError("duplicate, missing or invalid completed slot identity")
        estimate = finite(row.get("estimate"))
        if estimator.endswith(":dr"):
            ci = row.get("interval", {})
            if ci.get("status") != "valid" or finite(ci.get("se")) <= 0:
                raise ValueError("valid strictly positive DR SE required")
            _close(ci.get("lo"), estimate-1.96*ci["se"])
            _close(ci.get("hi"), estimate+1.96*ci["se"])
        elif "interval" in row:
            raise ValueError("plugin interval forbidden")
        slots[rep, estimator] = row
    if set(arithmetic["summary_arithmetic"]["estimators"]) != set(ESTIMATORS):
        raise ValueError("companion estimator set mismatch")
    methods = []
    for estimator in DR_ESTIMATORS:
        selected = [slots[rep, estimator] for rep in range(N)]
        estimates, ses = [r["estimate"] for r in selected], [r["interval"]["se"] for r in selected]
        stats = summarize_pairs(estimates, ses)
        saved = arithmetic["summary_arithmetic"]["estimators"][estimator]
        if saved.get("point_metric_denominator") != N or saved["intervals"].get("returned") != N:
            raise ValueError("companion per-method denominator mismatch")
        for a, b in ((stats["bias"], saved["bias"]), (stats["empirical_sd_error"], saved["empirical_sd"]),
                     (stats["mean_se"], saved["intervals"]["mean_se"]), (stats["rms_se"], saved["intervals"]["rms_se"])):
            _close(a, b)
        for key in ("below_truth", "above_truth", "covered"):
            if stats["frozen_interval_counts"][key] != saved["intervals"][key]:
                raise ValueError("companion frozen interval counts mismatch")
        pairs = [dict(replicate=rep, pairing_id=jobs[rep]["pairing_id"], estimate=finite(estimates[rep]),
                      error=finite(estimates[rep]-TRUTH), se=finite(ses[rep]),
                      z=finite((estimates[rep]-TRUTH)/ses[rep])) for rep in range(N)]
        methods.append(dict(estimator=estimator, pairs=pairs, summary=stats))
    return dict(schema_version="e0-stop-anchor-descriptive-calibration-v1", truth=TRUTH,
        classification="Post-result descriptive diagnostic, not a calibration fix or new CI procedure",
        planned_replicates=N, dr_methods=len(methods), total_pairs=N*len(methods), methods=methods,
        definitions={
            "error": "estimate minus known fixed truth; z=error/SE",
            "empirical_sd_error": "sqrt(sum((error-mean(error))^2)/(96-1))",
            "rms_se": "sqrt(mean(SE^2)) over the same96 replicate-specific SEs",
            "variance_ratio": "mean(SE^2) / sample variance(error), denominator uses n-1",
            "skewness": "m3/m2^1.5, m_k=mean((x-mean(x))^k); no bias correction",
            "correlation": "Pearson centered-sum correlation across matched replicate pairs",
            "quantiles": "Sort96 z values; h=(96-1)*p; linearly interpolate floor(h),ceil(h)",
            "degeneracy": "Zero variance gives null skewness/correlation/variance ratio where undefined",
            "miss_direction": "below_truth: upper bound<truth; above_truth: lower bound>truth; equality is covered",
            "hindsight_counts": "Original estimate +/-1.96 times same-replicate-set RMSSE or empiricalSD; no bias correction or truth-centering",
            "product_empirical_repairing": "All96² ordered error_i/SE_j combinations including i=j; below if error_i < -1.96SE_j, above if error_i > 1.96SE_j, otherwise covered"},
        limitations=[
            "Every one of the12 DR methods and96 replicates is retained; no p-values, tuning or method selection.",
            "Hindsight widths use all96 observed replicate results and are unavailable to a real single dataset.",
            "Hindsight counts do not define valid replacement confidence intervals or demonstrate improved calibration.",
            "Skewness, correlations and z quantiles are descriptive; they do not identify a causal mechanism for undercoverage.",
            "Skewness concerns across-dataset errors/z, not within-dataset root scores; error-SE association can arise because both use the same scores.",
            "Product-empirical re-pairing preserves both empirical marginals; its9216 pairs are not independent trials, a permutation test, a deployable CI or causal attribution.",
            "Source, raw-score, exit and provenance claims are inherited from the two pinned audits, not reverified here.",
            "No raw data are reread, scores regenerated, samplers drawn, estimators fitted, models called or benchmarks executed.",
            "No new claim about independent datasets, cross-fitted-root independence or interval validity is made."],
        resources=dict(raw_run_reads=0, sampled_datasets=0, estimator_fits=0, model_calls=0, benchmark_executions=0, paid_usd=0))


def diagnose(reconciled_path=RECONCILED, arithmetic_path=ARITHMETIC):
    paths = [Path(reconciled_path).resolve(), Path(arithmetic_path).resolve()]
    raws = [path.read_bytes() for path in paths]
    expected = (RECONCILED_SHA256, ARITHMETIC_SHA256)
    if any(sha(raw) != pin for raw, pin in zip(raws, expected)):
        raise ValueError("input bytes differ from published pinned summaries")
    result = analyze(*(strict_json(raw) for raw in raws))
    if any(path.read_bytes() != raw for path, raw in zip(paths, raws)):
        raise ValueError("input changed during diagnosis")
    result.update(checked_utc=datetime.now(timezone.utc).isoformat(),
        utility_sha256=sha(Path(__file__).read_bytes()), input_bytes_stable=True,
        inputs={label: dict(path=str(path), sha256=sha(raw), bytes=len(raw))
                for label, path, raw in zip(("reconciled", "independent_arithmetic"), paths, raws)})
    return result


def write_diagnostic(reconciled_path, arithmetic_path, output):
    inputs = [Path(reconciled_path).resolve(), Path(arithmetic_path).resolve()]
    target = Path(output).resolve()
    if target in inputs:
        raise ValueError("output must differ from immutable inputs")
    if target.exists():
        raise FileExistsError(target)
    result = diagnose(*inputs)
    raw = (json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n").encode()
    if len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError("derived output exceeds10MiB cap")
    if any(sha(path.read_bytes()) != result["inputs"][label]["sha256"]
           for label, path in zip(("reconciled", "independent_arithmetic"), inputs)):
        raise ValueError("input changed before exclusive output creation")
    with target.open("xb") as handle:
        handle.write(raw)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled", type=Path, default=RECONCILED)
    parser.add_argument("--arithmetic", type=Path, default=ARITHMETIC)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_diagnostic(args.reconciled, args.arithmetic, args.output)
