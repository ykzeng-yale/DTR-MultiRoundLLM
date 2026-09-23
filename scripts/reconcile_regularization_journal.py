#!/usr/bin/env python3
"""Read-only reconciliation of the fixed E0 regularization attempt journal.

reconcile_run(run_dir, repo=ROOT) returns {audit, summary}; it never samples,
fits, resumes or rewrites a run. CLI --run-dir DIR --output NEW_JSON writes one
exclusive-create derived file OUTSIDE the run. Only newline-terminated JSONL
records count as durable. An unterminated last fragment is ignored and its exact
length/hash retained, even if its bytes happen to form valid JSON.

Pinned Git blobs, seed identities and descriptor/fold hashes are checked. This
does not recover unarchived dataset arrays or prove independent random draws.
The actual pinned reporting module supplies every statistic and all 4,800 slots.
Absent slots mean unattempted only according to the retained durable journal;
the ignored fragment may conceal a just-started attempt. Any partial journal or
non-normal supervisor exit sets truncated=True, including otherwise complete fits.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PLAN = "experiments/e0/regularization_comparison_plan_v1.json"
SEEDS = "experiments/e0/regularization_comparison_seed_plan_v1.csv"
REPORT = "experiments/e0/regularization_report.py"
JOB_SOURCES = tuple("experiments/e0/" + name + ".py" for name in (
    "regularization_job", "simulator", "history_estimators", "estimators",
    "regularized_history_estimators", "regularization_report"))
SOURCES = set(JOB_SOURCES) | {PLAN, SEEDS, "scripts/run_regularization_comparison.py",
    "scripts/check_regularization_truth.py", "docs/fitted_history_numerical_design_20260922.md"}
VARIANTS = tuple(f"{r}_lambda{p}" for r in ("compressed", "history") for p in (0, 5))
ESTIMATORS = tuple(f"{v}:{m}" for v in VARIANTS for m in ("plugin", "dr"))
CAPS = dict(cpu_workers=1, outer_seconds=600, output_bytes=268435456, paid_usd=0, model_calls=0)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode())


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON object key")
        out[key] = value
    return out


def _json(raw):
    def reject(value):
        raise ValueError("nonfinite JSON constant: " + value)
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=reject)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON bytes") from exc


def parse_journal(raw):
    """Return complete records and explicit evidence for any ignored raw tail."""
    end = raw.rfind(b"\n") + 1
    tail = raw[end:]
    records = []
    for index, line in enumerate(raw[:end].splitlines(), 1):
        try:
            value = _json(line)
            if not isinstance(value, dict):
                raise ValueError("event must be an object")
        except ValueError as exc:
            raise ValueError(f"invalid complete journal line {index}: {exc}") from exc
        records.append(value)
    return records, {"raw_sha256": sha(raw), "raw_bytes": len(raw),
                     "complete_lines": len(records), "ignored_trailing_bytes": len(tail),
                     "ignored_tail_sha256": sha(tail) if tail else None,
                     "truncated_final_line": bool(tail)}


def _git_blob(repo, revision, path):
    result = subprocess.run(["git", "-C", str(repo), "show", f"{revision}:{path}"],
                            capture_output=True, check=True)
    return result.stdout


def _pinned_sources(repo, freeze):
    if (freeze.get("schema_version") != "e0-regularization-execution-freeze-v1"
            or freeze.get("execution_released") is not True or freeze.get("caps") != CAPS
            or set(freeze.get("source_sha256", {})) != SOURCES
            or not re.fullmatch(r"[0-9a-f]{40}", freeze.get("source_commit", ""))):
        raise ValueError("invalid execution freeze")
    blobs = {}
    for path, expected in freeze["source_sha256"].items():
        raw = _git_blob(repo, freeze["source_commit"], path)
        if sha(raw) != expected:
            raise ValueError("pinned source blob hash mismatch: " + path)
        blobs[path] = raw
    # Import only the reporter; refuse silently using a different local version.
    if (repo / REPORT).read_bytes() != blobs[REPORT]:
        raise ValueError("local reporter differs from the frozen reporter")
    return blobs


def planned_identities(plan, seed_bytes):
    """Independently reconstruct all declared identities; no RNG or sampler."""
    if (plan.get("total_planned_datasets") != 600 or plan.get("replicates_per_cell") != 200
            or plan.get("n_tasks") != 230 or plan.get("trajectories_per_root") != 40
            or plan.get("folds") != 3 or plan.get("seed_table_path") != SEEDS
            or plan.get("seed_table_sha256") != sha(seed_bytes)):
        raise ValueError("incompatible fixed plan or seed-table hash")
    rows = list(csv.DictReader(seed_bytes.decode().splitlines()))
    identities, plan_hash = [], digest(plan)
    if len(rows) != 600:
        raise ValueError("expected all 600 seed rows")
    for index, row in enumerate(rows):
        rep, cell = divmod(index, 3)
        job = dict(job_index=index, cell_index=cell, cell=("uniform", "base", "weak_overlap")[cell],
                   replicate=rep, data_seed=202609220000 + 1000*cell + rep,
                   fold_seed=202609320000 + 1000*cell + rep)
        if row != {key: str(value) for key, value in job.items()}:
            raise ValueError("seed row/order differs from declared seed law")
        job_id = digest(dict(schema="e0-regularization-job-identity-v1", plan_sha256=plan_hash, job=job))
        identities.append(dict(job_id=job_id, plan_sha256=plan_hash, job=job,
                               planned_job=dict(cell_id=job["cell"], replicate=rep, pairing_id=job_id)))
    return identities


def _provenance(event, freeze, identity, *, prepared):
    p = event.get("provenance", {})
    if (p.get("source_sha256") != {key: freeze["source_sha256"][key] for key in JOB_SOURCES}
            or any(p.get(key) != freeze["environment"][key] for key in ("python", "numpy", "scipy"))
            or p.get("data_mode") != "production_sampler"
            or any(p.get(key) != identity["job"][key] for key in ("data_seed", "fold_seed"))):
        raise ValueError("job source/environment/seed provenance mismatch")
    if not prepared:
        return None
    data, folds = p.get("dataset"), p.get("folds")
    if not isinstance(data, dict) or data.get("sha256") != digest(data.get("fields")):
        raise ValueError("dataset descriptor hash mismatch")
    if not isinstance(folds, dict) or set(folds) != {
            "task_labels", "task_index", "task_fold_ids", "episode_fold_ids", "sha256"}:
        raise ValueError("invalid fold descriptor")
    if folds["sha256"] != digest({k: v for k, v in folds.items() if k != "sha256"}):
        raise ValueError("fold descriptor hash mismatch")
    labels, index, assignments, episodes = (folds[k] for k in
            ("task_labels", "task_index", "task_fold_ids", "episode_fold_ids"))
    root_counts = Counter(index)
    if (len(labels) != 230 or sorted(labels) != list(range(230)) or len(index) != 9200
            or len(assignments) != 230 or len(episodes) != 9200
            or any(type(x) is not int or x not in (0, 1, 2) for x in assignments)
            or any(type(x) is not int or not 0 <= x < 230 for x in index)
            or sorted(assignments.count(f) for f in range(3)) != [76, 77, 77]
            or any(root_counts[r] != 40 for r in range(230))
            or any(type(f) is not int or f != assignments[r] for r, f in zip(index, episodes))):
        raise ValueError("invalid root-preserving fold assignment")
    return data["sha256"], folds["sha256"]


def reconcile_events(events, identities, freeze):
    """State machine; terminal records can only replace durably attempted slots."""
    final, next_job, active, prepared, variants = {}, 0, None, None, set()
    complete, failed_worker = [], False
    for event in events:
        kind = event.get("event")
        if failed_worker:
            raise ValueError("event after worker_failure")
        if kind == "worker_failure":
            if not event.get("reason") or not event.get("error_type"):
                raise ValueError("worker failure requires diagnostic")
            failed_worker = True
            continue
        if kind == "attempted":
            if active is not None or next_job >= len(identities):
                raise ValueError("overlapping/duplicate/excess job attempt")
            expected = identities[next_job]
            if (event.get("identity") != expected or event.get("job") != expected["job"]
                    or event.get("estimator_slots") != list(ESTIMATORS)):
                raise ValueError("attempt identity or slot binding mismatch")
            active, prepared, variants = next_job, None, set()
            next_job += 1
            for estimator in ESTIMATORS:
                final[active, estimator] = dict(expected["planned_job"], estimator=estimator,
                    status="attempted", reason="durable_shared_job_attempt_without_terminal_record")
            continue
        if active is None or event.get("job_index") != active:
            raise ValueError("event without matching active job attempt")
        identity = identities[active]
        if kind == "job_complete":
            if any(final[active, e]["status"] not in ("completed", "failed") for e in ESTIMATORS):
                raise ValueError("job_complete before all eight terminal records")
            complete.append(active)
            active = None
            continue
        if event.get("identity") != identity:
            raise ValueError("terminal/prepared identity mismatch")
        if kind == "prepared":
            if prepared is not None or variants or event.get("records"):
                raise ValueError("duplicate/out-of-order preparation")
            prepared = _provenance(event, freeze, identity, prepared=True)
            continue
        if kind == "job_failed":
            if prepared is not None or variants:
                raise ValueError("job_failed after preparation/terminal event")
            _provenance(event, freeze, identity, prepared=False)
            expected_estimators = set(ESTIMATORS)
            variants.add("job_failed")
        elif kind == "variant":
            variant = event.get("variant")
            if prepared is None or variant not in VARIANTS or variant in variants:
                raise ValueError("unprepared/unknown/duplicate variant")
            if (event.get("dataset_sha256"), event.get("fold_sha256")) != prepared:
                raise ValueError("variant dataset/fold mismatch")
            expected_estimators = {f"{variant}:plugin", f"{variant}:dr"}
            variants.add(variant)
        else:
            raise ValueError("unknown journal event")
        records = event.get("records")
        if (not isinstance(records, list) or len(records) != len(expected_estimators)
                or {r.get("estimator") for r in records} != expected_estimators):
            raise ValueError("incorrect terminal estimator set")
        for row in records:
            estimator = row["estimator"]
            if (any(row.get(k) != v for k, v in identity["planned_job"].items())
                    or row.get("status") not in ("completed", "failed")
                    or final[active, estimator]["status"] != "attempted"
                    or (kind == "job_failed" and row["status"] != "failed")):
                raise ValueError("duplicate/misbound/nonterminal record")
            final[active, estimator] = row
    return list(final.values()), dict(attempted_jobs=next_job, completed_jobs=len(complete),
        active_unfinished_job=active, worker_failure=failed_worker)


def reconcile_run(run_dir, *, repo=ROOT):
    """Require a closed snapshot with all four named inputs.

    Startup failures before planned_jobs/events were written need a separate
    supervisor-only audit; this function refuses rather than inventing that log.
    """
    started, cpu = time.perf_counter(), time.process_time()
    run_dir, repo = Path(run_dir).resolve(), Path(repo).resolve()
    names = ("planned_jobs.json", "events.jsonl", "supervisor.json", "run_manifest.json")
    raw = {name: (run_dir / name).read_bytes() for name in names}
    manifest, supervisor = _json(raw["run_manifest.json"]), _json(raw["supervisor.json"])
    freeze = manifest["freeze"]
    blobs = _pinned_sources(repo, freeze)
    plan = _json(blobs[PLAN])
    identities = planned_identities(plan, blobs[SEEDS])
    planned = [i["planned_job"] for i in identities]
    if _json(raw["planned_jobs.json"]) != planned:
        raise ValueError("planned_jobs differs from all 600 frozen identities")
    if (manifest.get("output_bytes_cap") != CAPS["output_bytes"]
            or manifest.get("model_calls") != 0 or manifest.get("paid_usd") != 0
            or manifest.get("resource_receipt", {}).get("freeze_sha256") != manifest.get("freeze_sha256")
            or not re.fullmatch(r"[0-9a-f]{64}", manifest.get("freeze_sha256", ""))):
        raise ValueError("manifest freeze/resource/cap mismatch")
    allowed_stops = {"child_complete", "outer_time_cap", "output_cap_reached", "output_cap_violation",
                     "child_failed", "startup_failure", "startup_deadline"}
    if (supervisor.get("schema_version") != "e0-supervisor-v1"
            or supervisor.get("stop_reason") not in allowed_stops
            or supervisor.get("outer_seconds_cap") != 600
            or supervisor.get("output_bytes_cap") != CAPS["output_bytes"]
            or supervisor.get("child_exit_observed") is not True):
        raise ValueError("invalid supervisor receipt")
    events, tail = parse_journal(raw["events.jsonl"])
    records, state = reconcile_events(events, identities, freeze)
    normal = (supervisor["stop_reason"] == "child_complete"
              and supervisor.get("child_returncode") == 0 and supervisor.get("child_exit_observed") is True)
    complete = normal and state["completed_jobs"] == 600 and not state["worker_failure"] and not tail["truncated_final_line"]
    spec = importlib.util.spec_from_file_location("_frozen_regularization_report", repo / REPORT)
    reporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reporter)
    summary = reporter.summarize_regularization(planned, records, plan["deterministic_truth"], truncated=not complete)
    audit = dict(schema_version="e0-regularization-journal-reconciliation-v1", run_directory=str(run_dir),
        raw_inputs={name: {"sha256": sha(value), "bytes": len(value)} for name, value in raw.items()},
        source_commit=freeze["source_commit"], verified_source_sha256=freeze["source_sha256"],
        utility_sha256=sha(Path(__file__).read_bytes()), plan_sha256=digest(plan),
        journal=tail, state=state, supervisor=supervisor, normal_child_exit=normal,
        journal_complete_normal_run=complete, all_planned_slots=4800,
        limitations=["Dataset array bytes were not archived: descriptor and cross-event bindings are verified, not raw arrays.",
          "The embedded freeze's raw-file SHA is a recorded binding; the original freeze file bytes are not an input.",
          "Any ignored tail can conceal an attempted slot; unattempted is relative to complete durable journal records.",
          "Source/seed/hash consistency does not prove independence or unconditional precision for a truncated run."],
        resources={"wall_seconds": time.perf_counter()-started, "cpu_seconds": time.process_time()-cpu,
                   "sampler_calls": 0, "fits": 0, "model_calls": 0, "benchmark_executions": 0})
    return {"audit": audit, "summary": summary}


def write_derived(run_dir, output, *, repo=ROOT):
    run_dir, output = Path(run_dir).resolve(), Path(output).resolve()
    if output == run_dir or run_dir in output.parents:
        raise ValueError("derived output must be outside immutable raw run directory")
    if output.exists():
        raise FileExistsError(output)
    result = reconcile_run(run_dir, repo=repo)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_derived(args.run_dir, args.output)


if __name__ == "__main__":
    main()
