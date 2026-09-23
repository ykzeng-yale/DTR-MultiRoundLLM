#!/usr/bin/env python3
"""Independent, stdlib-only arithmetic audit of a CLOSED STOP-anchor run.

Consumes the final reconciler's pinned raw-file hashes, then independently reads
durable newline-terminated events. No estimator, journal, reporter, NumPy, sampler
or fitter is imported. Saved scores are checked, not regenerated. Hash consistency
and descriptive sample identities do not prove independence or valid inference.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat

TRUTH = .6459770061744536
N_DATASETS, N_ROOTS = 96, 230
ATOL = RTOL = 1e-12
VARIANTS = tuple(f"{r}_lambda{p}_{m}" for r in ("compressed", "history")
                 for p in (0, 5) for m in ("original", "evaluation_only", "recursive"))
ESTIMATORS = tuple(f"{v}:{m}" for v in VARIANTS for m in ("plugin", "dr"))
PAIRS = tuple((f"{r}_lambda{p}_{a}:{m}", f"{r}_lambda{p}_{b}:{m}")
              for r in ("compressed", "history") for p in (0, 5) for m in ("plugin", "dr")
              for a, b in (("evaluation_only", "original"), ("recursive", "evaluation_only"),
                           ("recursive", "original")))
PRIMARY = ("history_lambda5_recursive:dr", "history_lambda5_original:dr")
STATUSES = ("attempted", "completed", "failed", "unattempted")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def strict_json(raw):
    def floating(value):
        return finite(float(value))
    def reject(value):
        raise ValueError("nonfinite JSON constant: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                      parse_float=floating, parse_constant=reject)


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("finite numeric value required")
    return float(value)


def close(actual, expected, name):
    if actual is None or expected is None:
        if actual is not expected:
            raise ValueError(name + ": null mismatch")
    elif not math.isclose(finite(actual), finite(expected), rel_tol=RTOL, abs_tol=ATOL):
        raise ValueError(name + ": arithmetic mismatch")


def mean(values):
    return finite(math.fsum(values)/len(values)) if values else None


def variance(values):
    if len(values) < 2:
        return None
    center = mean(values)
    return finite(math.fsum((v-center)**2 for v in values)/(len(values)-1))


def mcse(values):
    return math.sqrt(variance(values)/len(values)) if len(values) >= 2 else None


def rms(values):
    return math.sqrt(finite(math.fsum(v*v for v in values)/len(values))) if values else None


def check_point(row, roots, *, n_roots=N_ROOTS):
    """Pure arithmetic helper; production caller always requires exactly230 roots."""
    if not isinstance(roots, list) or len(roots) != n_roots or n_roots < 2:
        raise ValueError("completed point requires declared root count")
    roots = [finite(value) for value in roots]
    estimate = mean(roots)
    close(row.get("estimate"), estimate, "root-mean estimate")
    result = dict(estimate=estimate, sample_root_variance=variance(roots), roots=n_roots)
    if row["estimator"].endswith(":plugin"):
        if "interval" in row:
            raise ValueError("plugin interval forbidden")
    else:
        interval = row.get("interval", {})
        if interval.get("status") == "valid":
            se = math.sqrt(result["sample_root_variance"]/n_roots)
            for name, expected in (("se", se), ("lo", estimate-1.96*se), ("hi", estimate+1.96*se)):
                close(interval.get(name), expected, "root DR interval " + name)
            result.update(se=se, lo=estimate-1.96*se, hi=estimate+1.96*se)
        elif interval.get("status") != "failed" or not interval.get("reason"):
            raise ValueError("completed DR requires explicit valid/failed interval")
        result["interval_status"] = interval["status"]
    return result


def variance_identity(left, right):
    """Sample covariance identity on aligned roots, not a sampling-variance proof."""
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("aligned root vectors of length>=2 required")
    left, right = [finite(v) for v in left], [finite(v) for v in right]
    delta = [a-b for a, b in zip(left, right)]
    mr, md = mean(right), mean(delta)
    covariance = finite(math.fsum((b-mr)*(d-md) for b, d in zip(right, delta))/(len(left)-1))
    vl, vr, vd = variance(left), variance(right), variance(delta)
    lhs, rhs = vl-vr, 2*covariance+vd
    # Fixed before outcomes: account for cancellation against the scale of every
    # variance/covariance term, rather than the potentially tiny difference.
    scale = finite(math.fsum((vl, vr, 2*abs(covariance), vd)))
    tolerance = ATOL+RTOL*scale
    if abs(lhs-rhs) > tolerance:
        raise ValueError("root variance/covariance identity mismatch")
    return dict(left_root_variance=vl, right_root_variance=vr, difference_root_variance=vd,
                covariance_right_difference=covariance, left_minus_right_variance=lhs,
                twice_covariance_plus_difference_variance=rhs, identity_residual=lhs-rhs,
                root_count=len(left), identity_tolerance=tolerance,
                identity_scale=scale)


def _snapshot(root):
    files, directories = {}, []
    for parent, dirs, names in os.walk(root, followlinks=False):
        for name in dirs+names:
            path = Path(parent)/name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISDIR(info.st_mode):
                directories.append(relative)
            elif stat.S_ISREG(info.st_mode):
                h, size = hashlib.sha256(), 0
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024*1024), b""):
                        h.update(chunk); size += len(chunk)
                if size != info.st_size or path.stat().st_size != size:
                    raise ValueError("raw input changed during hashing")
                files[relative] = dict(bytes=size, sha256=h.hexdigest())
            else:
                raise ValueError("nonregular raw artifact")
    return dict(files=files, directories=sorted(directories),
                total_bytes=sum(item["bytes"] for item in files.values()))


def _read(root, snapshot, name):
    raw = (root/name).read_bytes()
    if dict(bytes=len(raw), sha256=sha(raw)) != snapshot["files"].get(name):
        raise ValueError("raw input changed or was not pinned: " + name)
    return raw


def parse_events(raw):
    end = raw.rfind(b"\n")+1
    events = [strict_json(line) for line in raw[:end].splitlines()]
    if any(not isinstance(event, dict) for event in events):
        raise ValueError("journal event must be an object")
    tail = raw[end:]
    return events, dict(raw_sha256=sha(raw), raw_bytes=len(raw), complete_lines=len(events),
                       ignored_trailing_bytes=len(tail), ignored_tail_sha256=sha(tail) if tail else None,
                       truncated_final_line=bool(tail))


def reconstruct(events, identities, *, n_roots=N_ROOTS):
    """Independent durable status ledger; no production journal implementation used."""
    slots = {(i["job"]["replicate"], e): {**i["planned_job"], "estimator": e,
             "status": "unattempted"} for i in identities for e in ESTIMATORS}
    roots, checked, states = {}, {}, {}
    active, next_rep = None, 0
    for event in events:
        ident, kind = event.get("identity", {}), event.get("event")
        rep = ident.get("job", {}).get("replicate")
        if type(rep) is not int or not 0 <= rep < len(identities) or ident != identities[rep]:
            raise ValueError("event identity mismatch")
        if kind == "job_started":
            if active is not None or rep != next_rep or event.get("estimator_ids") != list(ESTIMATORS):
                raise ValueError("duplicate/out-of-order job start")
            states[rep] = dict(prepared=False, returned=set(), variant=None, complete=False)
            active = rep
            for e in ESTIMATORS:
                slots[rep, e]["status"] = "attempted"
            continue
        if active != rep:
            raise ValueError("event lacks active job")
        state = states[rep]
        if kind == "prepared":
            labels = event.get("provenance", {}).get("folds", {}).get("task_labels")
            if state["prepared"] or state["returned"] or labels != list(range(n_roots)):
                raise ValueError("prepared root labels/order mismatch")
            state.update(prepared=True, labels=labels)
        elif kind == "variant_started":
            variant = event.get("variant")
            expected = [f"{variant}:{m}" for m in ("plugin", "dr")]
            if not state["prepared"] or variant not in VARIANTS or state["variant"] is not None or event.get("estimator_ids") != expected:
                raise ValueError("invalid variant start")
            state["variant"] = variant
        elif kind in {"variant", "job_failed"}:
            variant = event.get("variant")
            expected = ([f"{variant}:{m}" for m in ("plugin", "dr")] if kind == "variant" else list(ESTIMATORS))
            if kind == "variant" and (variant != state["variant"] or event.get("root_labels") != state.get("labels")):
                raise ValueError("unaligned variant roots")
            if kind == "job_failed" and (state["prepared"] or state["returned"]):
                raise ValueError("late preparation failure")
            rows = event.get("records", [])
            if [r.get("estimator") for r in rows] != expected:
                raise ValueError("terminal estimator identities differ")
            for row in rows:
                estimator = row["estimator"]
                if (estimator in state["returned"] or row.get("status") not in {"completed", "failed"}
                        or any(row.get(k) != v for k, v in ident["planned_job"].items())):
                    raise ValueError("duplicate/mismatched terminal record")
                if row["status"] == "completed":
                    if kind != "variant":
                        raise ValueError("preparation failure cannot complete a point")
                    vector = event.get("root_means", {}).get(estimator.split(":")[1])
                    checked[rep, estimator] = check_point(row, vector, n_roots=n_roots)
                    roots[rep, estimator] = vector
                elif not row.get("reason") or "estimate" in row or "interval" in row:
                    raise ValueError("invalid explicit point failure")
                slots[rep, estimator] = row
                state["returned"].add(estimator)
            state["variant"] = None
        elif kind == "job_complete":
            if len(state["returned"]) != len(ESTIMATORS) or state["variant"] is not None:
                raise ValueError("job completion without all terminal estimators")
            state["complete"] = True
            active, next_rep = None, next_rep+1
        else:
            raise ValueError("unknown journal event")
    return slots, roots, checked, states


def summarize(slots, roots, planned_jobs):
    """All arithmetic uses saved scores and fsum; no production summary helper."""
    n, table, pairs = len(planned_jobs), {}, []
    for estimator in ESTIMATORS:
        rows = [slots[j["replicate"], estimator] for j in planned_jobs]
        counts = {s: sum(r["status"] == s for r in rows) for s in STATUSES}
        points = [r for r in rows if r["status"] == "completed"]
        estimates = [mean(roots[r["replicate"], estimator]) for r in points]
        errors = [x-TRUTH for x in estimates]
        table[estimator] = result = dict(planned=n, attempted=n-counts["unattempted"],
            status_counts=counts, point_metric_denominator=len(points), bias=mean(errors),
            rmse=rms(errors), empirical_sd=math.sqrt(variance(estimates)) if len(estimates)>1 else None,
            bias_mcse=mcse(errors))
        if estimator.endswith(":dr"):
            valid = [r["interval"] for r in points if r["interval"]["status"] == "valid"]
            covered = sum(ci["lo"] <= TRUTH <= ci["hi"] for ci in valid)
            proportion = covered/len(valid) if valid else None
            result["intervals"] = dict(returned=len(valid), failed_after_completed_point=len(points)-len(valid),
                no_completed_point=n-len(points), se_metric_denominator=len(valid),
                mean_se=mean([ci["se"] for ci in valid]), rms_se=rms([ci["se"] for ci in valid]),
                covered=covered, below_truth=sum(ci["hi"]<TRUTH for ci in valid),
                above_truth=sum(ci["lo"]>TRUTH for ci in valid), returned_interval_coverage=proportion,
                coverage_mcse=math.sqrt(proportion*(1-proportion)/len(valid)) if valid else None,
                mean_width=mean([ci["hi"]-ci["lo"] for ci in valid]),
                operational_covering_per_attempted=covered/result["attempted"] if result["attempted"] else None,
                operational_denominator=result["attempted"])
    for left, right in PAIRS:
        included, excluded, differences, squares, identities = [], [], [], [], []
        for job in planned_jobs:
            rep = job["replicate"]
            a, b = slots[rep, left], slots[rep, right]
            if a["status"] == b["status"] == "completed":
                av, bv = mean(roots[rep, left]), mean(roots[rep, right])
                d, q = finite(av-bv), finite((av-TRUTH)**2-(bv-TRUTH)**2)
                included.append({**job, "estimate_difference": d, "squared_error_difference": q})
                differences.append(d); squares.append(q)
                identities.append({"replicate": rep, **variance_identity(roots[rep, left], roots[rep, right])})
            else:
                excluded.append({**job, "left_status": a["status"], "right_status": b["status"]})
        pairs.append(dict(pair_id=f"{left}__minus__{right}", left=left, right=right,
            is_primary=(left, right)==PRIMARY, planned_pairs=n, joint_completed_pairs=len(included),
            excluded_pairs=len(excluded), mean_estimate_difference=mean(differences),
            estimate_difference_mcse=mcse(differences), mean_squared_error_difference=mean(squares),
            paired_mcse=mcse(squares), included=included, excluded=excluded,
            within_dataset_variance_identities=identities))
    totals = {s: sum(r["status"]==s for r in slots.values()) for s in STATUSES}
    return dict(planned_estimator_slots=n*len(ESTIMATORS), status_counts=totals,
                attempted_estimator_slots=n*len(ESTIMATORS)-totals["unattempted"],
                estimators=table, paired_comparisons=pairs)


def _compare(actual, expected, path="summary"):
    """Expected is an independently computed subset; all its fields are checked."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise ValueError(path + ": object required")
        for key, value in expected.items():
            if key not in actual:
                raise ValueError(path + ": missing " + key)
            _compare(actual[key], value, path+"."+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(path + ": list length mismatch")
        for index, value in enumerate(expected):
            _compare(actual[index], value, path+f"[{index}]")
    elif type(expected) is float:
        close(actual, expected, path)
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(path + ": value/type mismatch")


def audit_run(run_directory, reconciled_path):
    root, source = Path(run_directory).resolve(), Path(reconciled_path).resolve()
    reconciled_raw = source.read_bytes()
    reconciled = strict_json(reconciled_raw)
    audit, saved = reconciled["audit"], reconciled["summary"]
    if (audit.get("schema_version") != "e0-stop-anchor-final-reconciliation-v1"
            or audit.get("input_hashes_stable") is not True
            or audit.get("production_provenance_required") is not True
            or audit.get("child_exit_receipt_verified") is not True
            or audit.get("never_spawned") is not False):
        raise ValueError("closed observed-child reconciled production artifact required")
    before = _snapshot(root)
    if before != audit.get("raw_snapshot"):
        raise ValueError("raw files differ from reconciled pinned snapshot")
    supervisor = strict_json(_read(root, before, "supervisor.json"))
    if (supervisor != audit.get("supervisor") or supervisor.get("child_started") is not True
            or supervisor.get("child_exit_observed") is not True
            or type(supervisor.get("child_returncode")) is not int):
        raise ValueError("observed exit receipt mismatch")
    freeze_raw = _read(root, before, "execution_freeze.json")
    freeze = strict_json(freeze_raw)
    if freeze.get("deterministic_truth") != TRUTH or sha(freeze_raw) != audit.get("freeze_raw_sha256"):
        raise ValueError("fixed truth/freeze mismatch")
    recording = strict_json(_read(root, before, "records/manifest.json"))
    plan, identities = recording["plan"], recording["identities"]
    expected_pairs = [dict(left=a, right=b) for a, b in PAIRS]
    if (plan.get("deterministic_truth_reference") != TRUTH or plan.get("n_tasks") != N_ROOTS
            or plan.get("total_planned_datasets") != N_DATASETS
            or plan.get("estimator_order") != list(ESTIMATORS)
            or plan.get("paired_comparisons") != expected_pairs or len(identities) != N_DATASETS):
        raise ValueError("fixed96/230/24/pair specification mismatch")
    jobs = [i["planned_job"] for i in identities]
    if ([j.get("replicate") for j in jobs] != list(range(N_DATASETS))
            or any(j.get("cell_id") != "weak_overlap" or not isinstance(j.get("pairing_id"), str)
                   or not j["pairing_id"] for j in jobs)
            or len({j["pairing_id"] for j in jobs}) != N_DATASETS):
        raise ValueError("planned identities differ")
    events, tail = parse_events(_read(root, before, "records/events.jsonl"))
    if tail != audit.get("journal"):
        raise ValueError("journal/torn-tail hash mismatch")
    slots, roots, points, states = reconstruct(events, identities)
    numbers = summarize(slots, roots, jobs)
    _compare(saved, {k: numbers[k] for k in ("planned_estimator_slots", "status_counts", "attempted_estimator_slots")})
    _compare(saved.get("planned_jobs"), jobs, "planned_jobs")
    _compare(saved.get("truth"), TRUTH, "truth")
    for slot in saved.get("slots", []):
        key = slot["replicate"], slot["estimator"]
        if key not in slots:
            raise ValueError("unexpected summary slot")
        _compare(slot, {k: v for k, v in slots[key].items() if k != "reason"}, "slot")
    if (len(saved.get("slots", [])) != 2304
            or len({(r["replicate"], r["estimator"]) for r in saved["slots"]}) != 2304):
        raise ValueError("summary does not contain all2304unique slots")
    cell = saved["cells"]["weak_overlap"]
    _compare(cell["estimators"], numbers["estimators"], "estimators")
    paired = [{k: v for k, v in row.items() if k != "within_dataset_variance_identities"}
              for row in numbers["paired_comparisons"]]
    _compare(cell["paired_comparisons"], paired, "paired_comparisons")
    complete = all(r["status"]=="completed" and (not r["estimator"].endswith(":dr")
                   or r["interval"]["status"]=="valid") for r in slots.values())
    normal = (supervisor.get("stop_reason")=="child_complete" and supervisor["child_returncode"]==0
              and len(states)==N_DATASETS and all(s["complete"] for s in states.values())
              and not tail["truncated_final_line"])
    _compare(saved, dict(all_planned_results_complete=complete, truncated=not normal,
                         incomplete=not normal or not complete))
    primary = next(row for row in paired if row["is_primary"])
    assessable = normal and complete and primary["joint_completed_pairs"]==N_DATASETS
    _compare(saved["primary_precision"], dict(paired_mcse=primary["paired_mcse"],
        arithmetic_assessable=assessable, numerical_criterion_met=(primary["paired_mcse"]<=.005 if assessable else None),
        independent_datasets_verified=False))
    # Serial completed-job reported totals should fit inside the containing child.
    resources = [e["resources"] for e in events if e["event"]=="job_complete"]
    job_wall = math.fsum(finite(r["wall_seconds"]) for r in resources)
    job_cpu = math.fsum(finite(r["cpu_seconds"]) for r in resources)
    if job_wall > finite(supervisor["wall_seconds"])+1e-6 or job_cpu > finite(supervisor["owned_child_cpu_seconds"])+1e-6:
        raise ValueError("reported serial job totals exceed supervisor time")
    if _snapshot(root) != before or source.read_bytes() != reconciled_raw:
        raise ValueError("inputs changed during independent arithmetic audit")
    return dict(schema_version="e0-stop-anchor-independent-arithmetic-v1",
        checked_utc=datetime.now(timezone.utc).isoformat(), utility_sha256=sha(Path(__file__).read_bytes()),
        reconciled_path=str(source), reconciled_sha256=sha(reconciled_raw), raw_directory=str(root),
        raw_snapshot=before, raw_hashes_stable=True, truth=TRUTH,
        tolerance=dict(absolute=ATOL, relative=RTOL,
            variance_identity="abs(residual)<=1e-12+1e-12*(var(left)+var(right)+2*abs(cov(right,L))+var(L))"),
        completed_points_checked=len(points),
        valid_DR_intervals_checked=sum(p.get("interval_status")=="valid" for p in points.values()),
        failed_DR_intervals_retained=sum(p.get("interval_status")=="failed" for p in points.values()),
        within_dataset_variance_identities_checked=sum(len(p["within_dataset_variance_identities"]) for p in numbers["paired_comparisons"]),
        truncated=not normal, all_planned_results_complete=complete, journal=tail,
        summary_arithmetic=numbers, primary_precision_arithmetic_assessable=assessable,
        reported_completed_job_wall_seconds=job_wall, reported_completed_job_cpu_seconds=job_cpu,
        completed_job_totals_within_supervisor=True,
        limitations=["Saved root scores are not refitted or independently regenerated.",
            "Observed-exit and source/provenance validation inherit the pinned reconciler receipt; this is not process surveillance.",
            "Root covariance/variance equality is a descriptive sample identity, not a claim of independent cross-fitted roots or valid SEs.",
            "All24 comparisons and missing pairs are retained; no outcome-based comparison selection is performed.",
            "Monte Carlo SE and coverage proportions are arithmetic only; independence, coverage calibration and time-truncation validity are not established.",
            "Clopper-Pearson interval endpoints are not independently recomputed by this stdlib audit.",
            "Reported job timing consistency does not verify end-to-end wall compliance or independently measure process CPU."],
        sampling_calls=0, estimator_fits=0, model_calls=0, benchmark_executions=0)


def write_audit(run_directory, reconciled_path, output):
    root, source, target = (Path(p).resolve() for p in (run_directory, reconciled_path, output))
    if target==source or target==root or root in target.parents:
        raise ValueError("output must be separate from immutable raw inputs and reconciliation")
    if target.exists():
        raise FileExistsError(target)
    result = audit_run(root, source)
    with target.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--reconciled", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_audit(args.run_dir, args.reconciled, args.output)
