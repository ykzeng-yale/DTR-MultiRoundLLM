#!/usr/bin/env python3
"""Read-only final reconciliation of a closed, released STOP-anchor run.

No sampling, fitting, resume, repair or raw-run write occurs here. The CLI writes
one exclusively created derived JSON OUTSIDE the raw run. All raw files, including
unused archives and temporaries, are counted and hashed before and after audit.
Only newline-terminated strict-JSON journal records count as durable; an ignored
last fragment has its own hash and makes the run truncated. Missing durable starts
are unknowable, not evidence that no computation occurred.

The frozen journal validates scientific events, root means and actual arrays only
after its Git blobs, local sources and installed versions have been verified.
The supervisor receipt must record an observed child exit, or honestly state that
no child started. Receipt/hash consistency is not independent process surveillance,
proof of independent RNG streams, or validation of confidence interval coverage.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "e0_stop_anchor_20260923_lead01"
TRUTH = .6459770061744536
RESERVE = 4096
CAPS = dict(cpu_workers=1, outer_seconds=600, output_bytes=268435456, paid_usd=0,
            model_calls=0, benchmark_executions=0, prompt_tokens=0, completion_tokens=0)
PLAN = "experiments/e0/stop_anchor_comparison_plan_v1.json"
SEEDS = "experiments/e0/stop_anchor_seed_plan_v1.csv"
JOB_SOURCES = tuple("experiments/e0/" + name + ".py" for name in (
    "stop_anchor_job", "stop_anchor_estimators", "stop_anchor_journal", "stop_anchor_report",
    "regularization_job", "regularization_report", "regularized_history_estimators",
    "history_estimators", "estimators", "simulator")) + (PLAN, SEEDS)
REQUIRED_SOURCES = JOB_SOURCES + ("scripts/run_stop_anchor_comparison.py",
    "scripts/check_regularization_truth.py", "scripts/reconcile_stop_anchor_run.py")
ESTIMATORS = tuple(f"{rep}_lambda{penalty}_{mode}:{method}"
    for rep in ("compressed", "history") for penalty in (0, 5)
    for mode in ("original", "evaluation_only", "recursive") for method in ("plugin", "dr"))
REQUIRED_ROOT_FILES = ("run_manifest.json", "execution_freeze.json", "resource_receipt.json", "supervisor.json")
STOP_REASONS = {"child_complete", "child_failed", "outer_time_cap", "output_cap_reached",
                "output_cap_violation", "startup_failure", "startup_deadline", "supervisor_error"}


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


def strict_json(raw):
    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("nonfinite JSON number")
        return result
    def reject(value):
        raise ValueError("nonfinite JSON constant: " + value)
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_float=number, parse_constant=reject)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("invalid strict JSON bytes") from exc


def parse_journal(raw):
    end = raw.rfind(b"\n") + 1
    events, tail = [], raw[end:]
    for index, line in enumerate(raw[:end].splitlines(), 1):
        try:
            event = strict_json(line)
            if not isinstance(event, dict):
                raise ValueError("event must be an object")
        except ValueError as exc:
            raise ValueError(f"invalid complete journal line {index}: {exc}") from exc
        events.append(event)
    return events, dict(raw_sha256=sha(raw), raw_bytes=len(raw), complete_lines=len(events),
        ignored_trailing_bytes=len(tail), ignored_tail_sha256=sha(tail) if tail else None,
        truncated_final_line=bool(tail))


def _snapshot(root):
    """Count all regular files first, then hash; never follow artifact symlinks."""
    if not root.is_dir():
        raise ValueError("raw run directory is missing")
    files, directories, total = [], [], 0
    for parent, subdirs, names in os.walk(root, followlinks=False):
        for name in subdirs + names:
            path = Path(parent)/name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISDIR(info.st_mode):
                directories.append(relative)
            elif stat.S_ISREG(info.st_mode):
                files.append((relative, info.st_size))
                total += info.st_size
            else:
                raise ValueError("symlink or nonregular raw artifact refused: " + relative)
    if total > CAPS["output_bytes"]:
        raise ValueError("total raw bytes including temporaries/orphans exceed cap")
    result = {}
    for relative, expected_size in sorted(files):
        path, h, count = root/relative, hashlib.sha256(), 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024*1024), b""):
                h.update(chunk)
                count += len(chunk)
        if count != expected_size or path.stat().st_size != expected_size:
            raise ValueError("raw input changed while snapshotting")
        result[relative] = dict(bytes=count, sha256=h.hexdigest())
    return dict(files=result, directories=sorted(directories), total_bytes=total)


def _read(root, snapshot, name):
    if name not in snapshot["files"]:
        raise ValueError("required raw artifact missing: " + name)
    raw = (root/name).read_bytes()
    if dict(bytes=len(raw), sha256=sha(raw)) != snapshot["files"][name]:
        raise ValueError("raw input changed during audit: " + name)
    return raw


def _utc(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if result.tzinfo is None:
        raise ValueError("timestamp must have timezone")
    return result.astimezone(timezone.utc)


def _finite(value, name, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError("invalid nonnegative numeric field: " + name)
    return value


def _environment():
    return dict(python=platform.python_version(), numpy=importlib.metadata.version("numpy"),
                scipy=importlib.metadata.version("scipy"), bit_generator="PCG64")


def _git_blob(repo, revision, path):
    return subprocess.run(["git", "-C", str(repo), "show", f"{revision}:{path}"],
                          capture_output=True, check=True, timeout=5).stdout


def _git_ancestor(repo, ancestor, descendant):
    subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
                   capture_output=True, check=True, timeout=5)


def _verify_committed_freeze(repo, manifest, freeze, archived):
    revision, relative = manifest.get("freeze_commit", ""), manifest.get("freeze_repository_path")
    if (not re.fullmatch(r"[0-9a-f]{40}", revision) or not isinstance(relative, str)
            or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts
            or Path(relative).as_posix() != relative):
        raise ValueError("committed freeze location/revision missing or invalid")
    if _git_blob(repo, revision, relative) != archived:
        raise ValueError("archived freeze differs from recorded committed Git blob")
    source_commit = freeze.get("source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("invalid source revision")
    _git_ancestor(repo, source_commit, revision)
    _git_ancestor(repo, revision, "HEAD")


def _verify_sources(repo, freeze):
    if (freeze.get("schema_version") != "e0-stop-anchor-execution-freeze-v1"
            or freeze.get("execution_released") is not True
            or freeze.get("decision_id") != "LEAD-E0-STOP-01"
            or freeze.get("planned_run_id") != RUN_ID
            or freeze.get("deterministic_truth") != TRUTH
            or digest(freeze.get("caps")) != digest(CAPS)
            or set(freeze.get("source_sha256", {})) != set(REQUIRED_SOURCES)
            or not re.fullmatch(r"[0-9a-f]{40}", freeze.get("source_commit", ""))):
        raise ValueError("invalid complete execution freeze")
    blobs = {}
    for path, expected in freeze["source_sha256"].items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("invalid source hash")
        raw = _git_blob(repo, freeze["source_commit"], path)
        if sha(raw) != expected or (repo/path).read_bytes() != raw:
            raise ValueError("pinned Git/local source mismatch: " + path)
        blobs[path] = raw
    observed = _environment()
    if freeze.get("environment") != observed:
        raise ValueError("current environment differs from frozen versions before import")
    return blobs, observed


def planned_identities(plan, raw_seeds):
    """Reconstruct ordered SHA-derived identities without constructing any RNG."""
    if (plan.get("total_planned_datasets") != 96 or plan.get("dataset_order") != list(range(96))
            or plan.get("estimator_order") != list(ESTIMATORS)
            or plan.get("planned_estimator_slots") != 2304
            or plan.get("deterministic_truth_reference") != TRUTH
            or plan.get("seed_table_path") != SEEDS or plan.get("seed_table_sha256") != sha(raw_seeds)):
        raise ValueError("fixed plan or seed binding differs")
    rows = list(csv.DictReader(raw_seeds.decode("ascii").splitlines()))
    if len(rows) != 96:
        raise ValueError("all96 ordered seed rows required")
    identities, plan_sha = [], digest(plan)
    for rep, row in enumerate(rows):
        seeds = {kind+"_seed": str(int.from_bytes(hashlib.sha256(
            f"DTR-MultiRoundLLM:LEAD-E0-STOP-01:v1:{kind}:{rep}".encode("ascii")).digest()[:16], "big"))
                 for kind in ("data", "fold")}
        if row != dict(replicate=str(rep), **seeds):
            raise ValueError("seed strings/order differ from exact192-seed law")
        job = dict(replicate=rep, **seeds)
        job_id = digest(dict(schema="e0-stop-anchor-job-identity-v1", plan_sha256=plan_sha, job=job))
        identities.append(dict(job_id=job_id, plan_sha256=plan_sha, job=job,
            planned_job=dict(cell_id="weak_overlap", replicate=rep, pairing_id=job_id)))
    return identities


def _headers(root, snapshot):
    raw = {name: _read(root, snapshot, name) for name in REQUIRED_ROOT_FILES}
    manifest, freeze, receipt, supervisor = (strict_json(raw[name]) for name in REQUIRED_ROOT_FILES)
    if any(not isinstance(value, dict) for value in (manifest, freeze, receipt, supervisor)):
        raise ValueError("root metadata must be JSON objects")
    if (manifest.get("schema_version") != "e0-stop-anchor-run-v1" or manifest.get("run_id") != RUN_ID
            or manifest.get("freeze") != freeze or manifest.get("resource_receipt") != receipt
            or manifest.get("source_commit") != freeze.get("source_commit")
            or manifest.get("freeze_path") != "execution_freeze.json"
            or manifest.get("resource_receipt_path") != "resource_receipt.json"
            or manifest.get("freeze_sha256") != sha(raw["execution_freeze.json"])
            or manifest.get("resource_receipt_sha256") != sha(raw["resource_receipt.json"])
            or not isinstance(manifest.get("output_directory"), str)
            or not Path(manifest["output_directory"]).is_absolute()
            or manifest.get("output_bytes_cap") != CAPS["output_bytes"]
            or manifest.get("payload_bytes_cap") != CAPS["output_bytes"]-RESERVE
            or manifest.get("cleanup_seconds") != 2.
            or type(manifest.get("supervisor_pid")) is not int or manifest["supervisor_pid"] <= 0
            or not re.fullmatch(r"[0-9a-f]{32}", manifest.get("supervisor_token", ""))
            or any(type(manifest.get(k)) is not int or manifest[k] != 0 for k in
                   ("model_calls", "benchmark_executions", "prompt_tokens", "completion_tokens", "paid_usd"))):
        raise ValueError("run manifest/raw-header binding mismatch")
    start = _finite(manifest.get("started_monotonic"), "started_monotonic")
    deadline = _finite(manifest.get("deadline_monotonic"), "deadline_monotonic")
    if abs(deadline-start-600) > 1e-6:
        raise ValueError("manifest deadline differs from fixed outer cap")
    launched, checked = _utc(manifest.get("started_utc")), _utc(receipt.get("checked_utc"))
    age = (launched-checked).total_seconds()
    if (not 0 <= age <= 300 or receipt.get("planned_run_id") != RUN_ID
            or receipt.get("freeze_sha256") != manifest["freeze_sha256"]
            or receipt.get("no_active_conflicting_lease") is not True or receipt.get("one_cpu_available") is not True
            or not isinstance(receipt.get("inspection"), dict) or not receipt["inspection"]
            or any(not isinstance(receipt.get(k), str) or not receipt[k].strip()
                   for k in ("host", "evidence", "lease_scope"))):
        raise ValueError("resource receipt not bound/fresh at recorded launch")
    total = snapshot["total_bytes"]
    payload = total-len(raw["supervisor.json"])
    if (supervisor.get("schema_version") != "e0-stop-anchor-supervisor-v1"
            or supervisor.get("stop_reason") not in STOP_REASONS
            or supervisor.get("stop_reason") == "output_cap_violation"
            or supervisor.get("outer_seconds_cap") != 600
            or supervisor.get("output_bytes_cap") != CAPS["output_bytes"]
            or supervisor.get("payload_bytes") != payload or supervisor.get("total_bytes") != total
            or payload > CAPS["output_bytes"]-RESERVE or len(raw["supervisor.json"]) > RESERVE
            or supervisor.get("within_wall_cap") is not True or supervisor.get("within_output_cap") is not True
            or supervisor.get("completed_artifacts_retained") is not True
            or _finite(supervisor.get("wall_seconds"), "wall_seconds") > 600
            or type(supervisor.get("child_started")) is not bool):
        raise ValueError("invalid or exceeded supervisor closure/caps/accounting")
    if supervisor["child_started"]:
        if (type(supervisor.get("child_pid")) is not int or supervisor["child_pid"] <= 0
                or type(supervisor.get("child_returncode")) is not int
                or supervisor.get("child_exit_observed") is not True):
            raise ValueError("started child lacks observed/reaped exit receipt")
        _finite(supervisor.get("owned_child_cpu_seconds"), "owned_child_cpu_seconds")
    elif (supervisor.get("child_pid") is not None or supervisor.get("child_returncode") is not None
          or supervisor.get("child_exit_observed") is not False or supervisor.get("owned_child_cpu_seconds") is not None
          or supervisor["stop_reason"] not in {"startup_failure", "startup_deadline"}):
        raise ValueError("never-spawned receipt must not invent a child exit")
    return manifest, freeze, receipt, supervisor, age


def _load_journal(repo):
    """Import the verified namespace; reject modules originating from another checkout."""
    for relative in JOB_SOURCES:
        if not relative.endswith(".py"):
            continue
        name = Path(relative).stem
        module = sys.modules.get(name)
        if module is not None and Path(getattr(module, "__file__", "")).resolve() != (repo/relative).resolve():
            raise ValueError("already loaded scientific module belongs to another checkout: " + name)
    sys.path.insert(0, str(repo/"experiments/e0"))
    try:
        return importlib.import_module("stop_anchor_journal")
    finally:
        sys.path.pop(0)


def _production_provenance(event, freeze):
    if event.get("event") not in {"prepared", "job_failed"}:
        return
    identity = event.get("identity")
    if not isinstance(identity, dict) or not isinstance(identity.get("job"), dict):
        raise ValueError("scientific event lacks bound job identity")
    p, job = event.get("provenance", {}), identity["job"]
    if not isinstance(p, dict):
        raise ValueError("scientific provenance must be an object")
    if (p.get("source_sha256") != {k: freeze["source_sha256"][k] for k in JOB_SOURCES}
            or any(p.get(k) != freeze["environment"][k] for k in ("python", "numpy", "scipy"))
            or p.get("data_mode") != "production_sampler"
            or any(type(p.get(k)) is not str or p[k] != job[k] for k in ("data_seed", "fold_seed"))
            or p.get("data_rng") != "numpy.Generator(numpy.PCG64(numpy.SeedSequence(int(data_seed))))"
            or p.get("fold_rng") != "history.make_task_folds: numpy.default_rng(int(fold_seed)).permutation"):
        raise ValueError("nonproduction or mismatched scientific provenance")
    if event["event"] == "prepared" and not re.fullmatch(r"[0-9a-f]{64}", p.get("data_rng_initial_state_sha256", "")):
        raise ValueError("prepared production data lacks initial RNG-state binding")


def _archives(root, snapshot, events, journal):
    verified = []
    for event in events:
        if event["event"] != "prepared":
            continue
        ref = event.get("archive")
        expected = f"dataset_{event['identity']['job']['replicate']:03d}.npz"
        if not isinstance(ref, dict) or set(ref) != {"path", "bytes", "sha256"} or ref["path"] != expected:
            raise ValueError("invalid archive reference/path")
        name = "records/"+expected
        raw = _read(root, snapshot, name)
        if type(ref["bytes"]) is not int or ref["bytes"] != len(raw) or ref["sha256"] != sha(raw):
            raise ValueError("archive byte/hash mismatch")
        expected_fields = set(journal.ARRAYS) | {"fold_"+k for k in journal.FOLDS}
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if (len(members) != len(expected_fields)
                    or {m.filename for m in members} != {k+".npy" for k in expected_fields}
                    or any(m.compress_type != zipfile.ZIP_STORED for m in members)
                    or sum(m.file_size for m in members) > 8*1024*1024):
                raise ValueError("archive members/compression/size differ from fixed numeric payload")
        with journal.np.load(io.BytesIO(raw), allow_pickle=False) as arrays:
            if len(arrays.files) != len(expected_fields) or set(arrays.files) != expected_fields:
                raise ValueError("archive field mismatch")
            journal._validate_archive(dict(arrays), event["provenance"])
        verified.append(name)
    return verified


def _numerical_accounting(events, states):
    """Check reported counters; an unfinished event cannot reveal partial work."""
    variants, starts, completed_jobs = {}, set(), {}
    for event in events:
        rep, kind = event["identity"]["job"]["replicate"], event["event"]
        if kind == "variant_started":
            starts.add((rep, event["variant"]))
        elif kind == "variant":
            variant = event["variant"]
            attempted, completed = event.get("backward_fit_attempts"), event.get("backward_fits_completed")
            if (type(attempted) is not int or type(completed) is not int
                    or not 0 <= completed <= attempted <= 3
                    or (variant.endswith("_evaluation_only") and (attempted or completed))):
                raise ValueError("invalid terminal variant fit counters")
            if (not variant.endswith("_evaluation_only") and completed != 3
                    and any(row["status"] == "completed" for row in event["records"])):
                raise ValueError("completed estimator lacks three completed fold fits")
            variants[rep, variant] = dict(attempts=attempted, completed=completed,
                wall=_finite(event.get("wall_seconds"), "variant wall"),
                cpu=_finite(event.get("cpu_seconds"), "variant CPU"))
        elif kind == "job_complete":
            resource = event.get("resources")
            if not isinstance(resource, dict):
                raise ValueError("completed job requires resource counters")
            actual = [value for (job, _), value in variants.items() if job == rep]
            for field, source in (("backward_fit_attempts", "attempts"), ("backward_fits_completed", "completed")):
                if type(resource.get(field)) is not int or resource[field] != sum(row[source] for row in actual):
                    raise ValueError("job/terminal-variant fit counters disagree")
            sampler = resource.get("sampler_attempts")
            if (type(sampler) is not int or sampler not in (0, 1)
                    or (states[rep]["prepared"] is not None and sampler != 1)
                    or any(type(resource.get(k)) is not int or resource[k] != 0
                           for k in ("model_calls", "benchmark_executions", "paid_usd"))):
                raise ValueError("invalid completed production-job resource counters")
            wall = _finite(resource.get("wall_seconds"), "job wall")
            cpu = _finite(resource.get("cpu_seconds"), "job CPU")
            if sum(row["wall"] for row in actual) > wall+1e-8 or sum(row["cpu"] for row in actual) > cpu+1e-8:
                raise ValueError("terminal variant times exceed containing job time")
            completed_jobs[rep] = dict(sampler_attempts=sampler, wall_seconds=wall, cpu_seconds=cpu)
    unfinished = sorted(starts-set(variants))
    unclosed = sorted(set(states)-set(completed_jobs))
    return dict(
        terminal_variants=len(variants), started_variants=len(starts),
        reported_terminal_variant_fit_attempts=sum(row["attempts"] for row in variants.values()),
        reported_terminal_variant_fits_completed=sum(row["completed"] for row in variants.values()),
        reported_terminal_variant_wall_seconds=sum(row["wall"] for row in variants.values()),
        reported_terminal_variant_cpu_seconds=sum(row["cpu"] for row in variants.values()),
        completed_job_resource_records=len(completed_jobs),
        reported_completed_job_sampler_attempts=sum(row["sampler_attempts"] for row in completed_jobs.values()),
        reported_completed_job_wall_seconds=sum(row["wall_seconds"] for row in completed_jobs.values()),
        reported_completed_job_cpu_seconds=sum(row["cpu_seconds"] for row in completed_jobs.values()),
        unfinished_variants=[dict(replicate=rep, variant=variant) for rep, variant in unfinished],
        jobs_without_terminal_resource_counters=unclosed,
        additional_fit_attempts_unknown=bool(unfinished), additional_sampler_attempts_unknown=bool(unclosed),
        scope="reported event counters checked for consistency, not independent process measurements; phase sums are not total runtime; incomplete events may conceal additional work")


def reconcile_run(run_dir, *, repo=ROOT):
    started, cpu = time.perf_counter(), time.process_time()
    root, repo = Path(run_dir).resolve(), Path(repo).resolve()
    before = _snapshot(root)
    manifest, freeze, receipt, supervisor, receipt_age = _headers(root, before)
    _verify_committed_freeze(repo, manifest, freeze, _read(root, before, "execution_freeze.json"))
    blobs, environment = _verify_sources(repo, freeze)  # No scientific imports before this check.
    plan = strict_json(blobs[PLAN])
    identities = planned_identities(plan, blobs[SEEDS])
    parsed = {name: strict_json(_read(root, before, name)) for name in before["files"] if name.endswith(".json")}
    raw_events = _read(root, before, "records/events.jsonl") if "records/events.jsonl" in before["files"] else b""
    events, tail = parse_journal(raw_events)
    worker = parsed.get("worker_receipt.json")
    if not supervisor["child_started"]:
        if (worker is not None or "worker_failure.json" in parsed or events or tail["raw_bytes"]
                or any(name.startswith("records/") for name in before["files"])):
            raise ValueError("never-spawned run contains child/scientific records")
    elif worker is not None:
        if (worker.get("schema_version") != "e0-stop-anchor-worker-v1"
                or worker.get("worker_pid") != supervisor["child_pid"]
                or worker.get("supervisor_pid") != manifest["supervisor_pid"]
                or worker.get("freeze_sha256") != manifest["freeze_sha256"]
                or worker.get("resource_receipt_sha256") != manifest["resource_receipt_sha256"]
                or worker.get("environment") != environment
                or not 0 <= (_utc(worker.get("imports_verified_utc"))-_utc(manifest["started_utc"])).total_seconds() <= supervisor["wall_seconds"]+1):
            raise ValueError("worker receipt binding mismatch")
    if events and worker is None:
        raise ValueError("scientific events lack verified worker receipt")
    sources = {k: freeze["source_sha256"][k] for k in JOB_SOURCES}
    recording = parsed.get("records/manifest.json")
    if recording is not None:
        if (recording.get("schema_version") != "e0-stop-recording-v1" or recording.get("plan") != plan
                or recording.get("identities") != identities or recording.get("source_sha256") != sources
                or type(recording.get("output_bytes_cap")) is not int
                or not 1 <= recording["output_bytes_cap"] <= CAPS["output_bytes"]-RESERVE):
            raise ValueError("recording manifest differs from frozen plan/source/identities")
        record_bytes = sum(v["bytes"] for k, v in before["files"].items() if k.startswith("records/"))
        if record_bytes > recording["output_bytes_cap"]:
            raise ValueError("recording subtree exceeds its allocated ceiling")
    elif events or raw_events:
        raise ValueError("journal lacks recording manifest")
    for event in events:
        _production_provenance(event, freeze)
    journal = _load_journal(repo)
    if list(journal.reporting.ESTIMATORS) != list(ESTIMATORS):
        raise ValueError("pinned reporter identities differ from fixed24")
    records, states = journal._reconcile(events, identities, sources)
    numerical_accounting = _numerical_accounting(events, states)
    verified_archives = _archives(root, before, events, journal)
    terminal = len(states) == 96 and all(state["complete"] for state in states.values())
    normal = (supervisor["child_started"] and supervisor["stop_reason"] == "child_complete"
              and supervisor["child_returncode"] == 0 and supervisor["child_exit_observed"])
    if supervisor["stop_reason"] == "child_complete" and not normal:
        raise ValueError("child_complete receipt does not describe successful observed exit")
    if normal and (not terminal or tail["truncated_final_line"] or "records/summary.json" not in parsed
                   or "worker_failure.json" in parsed):
        raise ValueError("normal completion lacks a complete durable study and summary")
    truncated = not (normal and terminal and not tail["truncated_final_line"])
    summary = journal.reporting.summarize_stop_anchor([i["planned_job"] for i in identities], records,
                                                     freeze["deterministic_truth"], truncated=truncated)
    if summary["planned_estimator_slots"] != 2304:
        raise ValueError("report omitted planned estimator slots")
    if "records/summary.json" in parsed:
        # A final summary may have been saved just before a later cap/cleanup stop.
        completed_summary = journal.reporting.summarize_stop_anchor(
            [i["planned_job"] for i in identities], records, freeze["deterministic_truth"], truncated=False)
        if not terminal or tail["truncated_final_line"] or parsed["records/summary.json"] != completed_summary:
            raise ValueError("saved final summary differs from pinned reconciliation")
    after = _snapshot(root)
    if after != before:
        raise ValueError("raw inputs changed during reconciliation")
    used = set(REQUIRED_ROOT_FILES) | {"worker_receipt.json", "worker_failure.json", "records/manifest.json",
                                      "records/events.jsonl", "records/summary.json"} | set(verified_archives)
    audit = dict(schema_version="e0-stop-anchor-final-reconciliation-v1", run_directory=str(root),
        recorded_run_directory=manifest["output_directory"], run_id=RUN_ID,
        raw_snapshot=before, input_hashes_stable=True,
        unused_artifacts_counted=sorted(set(before["files"])-used),
        source_commit=freeze["source_commit"], verified_source_sha256=freeze["source_sha256"],
        freeze_commit=manifest["freeze_commit"], freeze_repository_path=manifest["freeze_repository_path"],
        utility_sha256=sha(Path(__file__).read_bytes()), environment=environment,
        freeze_raw_sha256=manifest["freeze_sha256"], resource_raw_sha256=manifest["resource_receipt_sha256"],
        resource_receipt_age_at_recorded_launch_seconds=receipt_age,
        supervisor=supervisor, worker_receipt_present=worker is not None,
        full_process_wall_verified=False,
        wall_accounting_scope="supervisor-reported elapsed time excludes final receipt serialization/fsync; external end-to-end command timing is needed for full600-second compliance",
        never_spawned=not supervisor["child_started"], child_exit_receipt_verified=supervisor["child_started"],
        journal=tail, job_states=states, verified_archives=verified_archives,
        numerical_accounting=numerical_accounting,
        durable_started_jobs=len(states), terminal_jobs=sum(state["complete"] for state in states.values()),
        journal_complete_normal_run=normal and terminal and not tail["truncated_final_line"],
        all_planned_slots=2304, production_provenance_required=True,
        limitations=[
            "Closure is verified against the pinned supervisor's observed-exit receipt, not independent process surveillance.",
            "Resource availability/lease inspection remains a recorded operator assertion; no current freshness claim is made.",
            "The supervisor's elapsed-time receipt is not end-to-end process timing; full process wall compliance is not verified here.",
            "A torn tail or interrupted archive can conceal an attempt not durably recorded; unused artifacts are counted but not treated as usable datasets.",
            "Hashes, exact seeds and production markers do not establish independent draws, interval calibration, or unconditional precision for an incomplete run.",
            "Point/interval arithmetic is reconciled with saved root means; no Q refit or replay of sampling is performed."],
        resources=dict(wall_seconds=time.perf_counter()-started, cpu_seconds=time.process_time()-cpu,
                       sampler_calls=0, fits=0, model_calls=0, benchmark_executions=0, paid_usd=0))
    return dict(audit=audit, summary=summary)


def write_derived(run_dir, output, *, repo=ROOT):
    root, destination = Path(run_dir).resolve(), Path(output).resolve()
    if destination == root or root in destination.parents:
        raise ValueError("derived output must be outside immutable raw run")
    if destination.exists():
        raise FileExistsError(destination)
    result = reconcile_run(root, repo=repo)
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    write_derived(args.run_dir, args.output)


if __name__ == "__main__":
    main()
