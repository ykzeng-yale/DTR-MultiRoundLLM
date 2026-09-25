#!/usr/bin/env python3
"""Bounded E0 runner. Real sampling requires a committed released freeze.

The parent imports only the standard library and supervises one child process.
The child uses cooperative, byte-counted writes; completed variant events survive
timeout. No resume, retry, extra seeds, model calls, or benchmark execution.
"""
from __future__ import annotations

import time
STARTED = time.monotonic()
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RESERVE = 4096
THREAD_ENV = {k: "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}
REQUIRED_SOURCES = (
    "experiments/e0/simulator.py", "experiments/e0/estimators.py",
    "experiments/e0/history_estimators.py", "experiments/e0/regularized_history_estimators.py",
    "experiments/e0/regularization_report.py", "experiments/e0/regularization_job.py",
    "scripts/run_regularization_comparison.py", "scripts/check_regularization_truth.py",
    "experiments/e0/regularization_comparison_plan_v1.json",
    "experiments/e0/regularization_comparison_seed_plan_v1.csv",
    "docs/fitted_history_numerical_design_20260922.md",
)


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OutputCap(RuntimeError):
    pass


class ByteBudget:
    """Count every file byte, including incomplete temporary writes, before writing."""
    def __init__(self, root, limit):
        self.root, self.limit = Path(root), limit

    def used(self):
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())

    def _path(self, relative):
        p = self.root / relative
        if p.parent != self.root or p.name in {"supervisor.json", "", ".", ".."}:
            raise ValueError("Only direct child artifact names are allowed")
        if p.is_symlink():
            raise ValueError("Symlink artifact refused")
        return p

    def _reserve(self, size):
        if self.used() + size > self.limit:
            raise OutputCap("output byte budget exhausted")

    def append_jsonl(self, relative, value):
        raw, p = encoded(value), self._path(relative)
        self._reserve(len(raw))
        with p.open("ab") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())

    def write_json(self, relative, value):
        raw, p = encoded(value), self._path(relative)
        if p.exists():
            raise FileExistsError(p)
        temporary = self._path(relative + ".tmp")
        self._reserve(len(raw))
        with temporary.open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, p)


def _git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=5)


def validate_release(freeze_path, receipt_path):
    """Validate published-source bindings and a fresh factual local-resource receipt.

    A receipt is an auditable operator assertion, not an automatic lease detector.
    Its factual accuracy remains a scientific release responsibility.
    """
    freeze_path = Path(freeze_path).resolve()
    relative = freeze_path.relative_to(ROOT).as_posix()
    freeze_bytes = freeze_path.read_bytes()
    if _git("show", "HEAD:" + relative) != freeze_bytes:
        raise ValueError("Freeze must be committed and unchanged")
    freeze = json.loads(freeze_bytes)
    if freeze.get("schema_version") != "e0-regularization-execution-freeze-v1" or freeze.get("execution_released") is not True:
        raise ValueError("No committed execution release")
    if freeze.get("caps") != {"cpu_workers": 1, "outer_seconds": 600, "output_bytes": 268435456, "paid_usd": 0, "model_calls": 0}:
        raise ValueError("Unexpected resource contract")
    sources = freeze.get("source_sha256", {})
    if set(sources) != set(REQUIRED_SOURCES):
        raise ValueError("Incomplete or changed source binding set")
    revision = freeze["source_commit"]
    _git("merge-base", "--is-ancestor", revision, "HEAD")
    for path, expected in sources.items():
        if sha(ROOT / path) != expected or hashlib.sha256(_git("show", revision + ":" + path)).hexdigest() != expected:
            raise ValueError("Source differs from freeze: " + path)
    receipt_bytes = Path(receipt_path).read_bytes()
    receipt = json.loads(receipt_bytes)
    checked = datetime.fromisoformat(receipt["checked_utc"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - checked).total_seconds()
    if not 0 <= age <= 300 or receipt.get("no_active_conflicting_lease") is not True or receipt.get("one_cpu_available") is not True:
        raise ValueError("Fresh availability and lease receipt required")
    if receipt.get("host") != platform.node() or receipt.get("freeze_sha256") != hashlib.sha256(freeze_bytes).hexdigest():
        raise ValueError("Receipt host/freeze mismatch")
    if not receipt.get("evidence") or not isinstance(receipt["evidence"], str):
        raise ValueError("Resource receipt needs concrete inspection evidence")
    return freeze, receipt


def _stop_child_group(child, deadline):
    """Reap an owned child even if it exits between poll and group signaling."""
    if child.poll() is not None:
        return
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except OSError:
        # On macOS an already-exited, unreaped group leader may yield EPERM.
        # If the child is still live, signal it directly as a fallback.
        if child.poll() is None:
            try:
                child.kill()
            except OSError:
                pass
    try:
        child.wait(timeout=max(.001, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        pass


def _supervise(output, command, *, total_seconds, output_bytes, manifest, started_monotonic=None):
    """One owned process group; cleanup time and final receipt are within the cap.

    Smaller limits support deterministic tests. Production caps are fixed above.
    The command's {output} placeholder expands to the new output directory.
    Child writes must use ByteBudget; the supervisor also detects output drift.
    """
    started = STARTED if started_monotonic is None else started_monotonic
    if total_seconds <= 0 or output_bytes <= RESERVE:
        raise ValueError("Invalid supervisor limits")
    output = Path(output).resolve()
    deadline = started + total_seconds
    cleanup = min(2.0, total_seconds / 4)
    bound_manifest = {**manifest, "supervisor_pid": os.getpid(),
                      "deadline_monotonic": deadline, "output_bytes_cap": output_bytes}
    if len(encoded(bound_manifest)) > output_bytes - RESERVE:
        raise OutputCap("run manifest exceeds payload budget")
    output.mkdir(parents=True, exist_ok=False)
    budget = ByteBudget(output, output_bytes - RESERVE)
    budget.write_json("run_manifest.json", bound_manifest)
    env = os.environ.copy(); env.update(THREAD_ENV)
    env["E0_OUTPUT_PAYLOAD_CAP"] = str(output_bytes - RESERVE)
    env["E0_SUPERVISOR_PID"] = str(os.getpid())
    child = None; reason = "startup_failure"; returncode = None
    try:
        if time.monotonic() >= deadline - cleanup:
            reason = "startup_deadline"
        else:
            argv = [str(x).replace("{output}", str(output)) for x in command]
            child = subprocess.Popen(argv, cwd=ROOT, env=env, start_new_session=True,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            while child.poll() is None:
                if budget.used() > budget.limit:
                    reason = "output_cap_violation"; break
                if time.monotonic() >= deadline - cleanup:
                    reason = "outer_time_cap"; break
                time.sleep(min(.02, max(0, deadline - cleanup - time.monotonic())))
            else:
                reason = ("child_complete" if child.returncode == 0 else
                          "output_cap_reached" if child.returncode == 3 else "child_failed")
            if child.poll() is None:
                _stop_child_group(child, deadline)
            returncode = child.poll()
            if budget.used() > budget.limit:
                reason = "output_cap_violation"
    finally:
        if child is not None and child.poll() is None:
            _stop_child_group(child, deadline)
        if child is not None:
            returncode = child.poll()
        final = {"schema_version": "e0-supervisor-v1", "stop_reason": reason,
                 "child_returncode": returncode, "child_exit_observed": child is None or child.poll() is not None,
                 "wall_seconds": time.monotonic() - started, "outer_seconds_cap": total_seconds,
                 "payload_bytes": budget.used(), "output_bytes_cap": output_bytes,
                 "completed_artifacts_retained": True,
                 "note": "No resume. An absent final report is incomplete; use the attempt/variant journal for later source-only reconciliation."}
        raw = encoded(final)
        if len(raw) > RESERVE:
            raise OutputCap("supervisor receipt exceeds reserve")
        with (output / "supervisor.json").open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
    return final


def _worker(freeze_path, output, receipt_path):
    """Pinned numeric path; source integration tests replace evaluate_job only."""
    freeze, _ = validate_release(freeze_path, receipt_path)
    manifest = json.loads((Path(output) / "run_manifest.json").read_bytes())
    if (int(os.environ.get("E0_SUPERVISOR_PID", "-1")) != os.getppid()
            or manifest.get("supervisor_pid") != os.getppid()
            or manifest.get("freeze_sha256") != sha(freeze_path)
            or manifest.get("output_bytes_cap") != freeze["caps"]["output_bytes"]
            or int(os.environ.get("E0_OUTPUT_PAYLOAD_CAP", "-1")) != freeze["caps"]["output_bytes"] - RESERVE
            or time.monotonic() >= manifest.get("deadline_monotonic", 0)):
        raise ValueError("Worker lacks matching live supervisor binding")
    # All scientific imports/truth/collection/reporting occur inside supervision.
    import numpy as np
    import scipy
    if freeze.get("environment") != {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "bit_generator": "PCG64"}:
        raise ValueError("Environment differs from frozen versions")
    sys.path.insert(0, str(ROOT / "experiments/e0"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from regularization_job import evaluate_job, expected_job_identity, SOURCE_PATHS
    from regularization_report import summarize_regularization, ESTIMATORS
    from check_regularization_truth import forward_value, EXPECTED
    plan = json.loads((ROOT / "experiments/e0/regularization_comparison_plan_v1.json").read_bytes())
    with (ROOT / plan["seed_table_path"]).open() as f:
        jobs = list(csv.DictReader(f))
    if len(jobs) != 600 or sha(ROOT / plan["seed_table_path"]) != plan["seed_table_sha256"]:
        raise ValueError("Seed-table binding/count mismatch")
    for job in jobs:
        for key in ("job_index", "cell_index", "replicate", "data_seed", "fold_seed"):
            job[key] = int(job[key])
    identities = [expected_job_identity(plan, job) for job in jobs]
    planned = [{"cell_id": job["cell"], "replicate": job["replicate"], "pairing_id": ident["job_id"]}
               for job, ident in zip(jobs, identities)]
    if [j["job_index"] for j in jobs] != list(range(600)):
        raise ValueError("Planned order mismatch")
    writer = ByteBudget(output, int(os.environ["E0_OUTPUT_PAYLOAD_CAP"]))
    writer.write_json("planned_jobs.json", planned)
    truth, _, _ = forward_value()
    if abs(truth - EXPECTED) > 1e-12 or truth != plan["deterministic_truth"]:
        raise ValueError("Truth binding mismatch")
    records = {}
    for job, identity, planned_job in zip(jobs, identities, planned):
        writer.append_jsonl("events.jsonl", {"event": "attempted", "job": job, "identity": identity,
            "utc": datetime.now(timezone.utc).isoformat(), "estimator_slots": list(ESTIMATORS),
            "convention": "All eight estimator slots attempted when their shared dataset job begins"})
        for name in ESTIMATORS:
            records[(planned_job["cell_id"], planned_job["replicate"], name)] = {**planned_job, "estimator": name,
                "status": "attempted", "reason": "shared_job_started_no_terminal_record"}
        prepared = None
        returned = set()
        def retain(event):
            nonlocal prepared
            if event.get("identity") != identity:
                raise ValueError("Adapter event identity mismatch")
            kind = event.get("event")
            if kind not in {"prepared", "variant", "job_failed"}:
                raise ValueError("Unknown adapter event")
            if kind == "prepared" and event.get("records"):
                raise ValueError("Preparation cannot carry terminal records")
            if kind in {"prepared", "job_failed"}:
                provenance = event["provenance"]
                if provenance["source_sha256"] != {p: freeze["source_sha256"][p] for p in SOURCE_PATHS}:
                    raise ValueError("Adapter source binding mismatch")
                if prepared is not None or returned:
                    raise ValueError("Duplicate or out-of-order preparation")
                if kind == "prepared":
                    prepared = (provenance["dataset"]["sha256"], provenance["folds"]["sha256"])
            elif prepared is None or (event["dataset_sha256"], event["fold_sha256"]) != prepared:
                raise ValueError("Variant data/fold binding mismatch")
            pending_names = set()
            for record in event.get("records", []):
                if {k: record[k] for k in ("cell_id", "replicate", "pairing_id")} != planned_job or record["estimator"] not in ESTIMATORS:
                    raise ValueError("Adapter record binding mismatch")
                if record.get("status") not in {"completed", "failed"}:
                    raise ValueError("Adapter record is not terminal")
                if record["estimator"] in returned | pending_names:
                    raise ValueError("Duplicate terminal estimator record")
                pending_names.add(record["estimator"])
            writer.append_jsonl("events.jsonl", {**event, "job_index": job["job_index"]})
            returned.update(pending_names)
            for record in event.get("records", []):
                records[(record["cell_id"], record["replicate"], record["estimator"])] = record
        artifact = evaluate_job(plan, job, on_event=retain)
        if returned != set(ESTIMATORS):
            raise ValueError("Adapter returned without all eight terminal records")
        writer.append_jsonl("events.jsonl", {"event": "job_complete", "job_index": job["job_index"],
                                              "resources": artifact["resources"]})
    summary = summarize_regularization(planned, list(records.values()), truth)
    writer.write_json("summary.json", summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resource-receipt", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if "E0_OUTPUT_PAYLOAD_CAP" not in os.environ or args.resource_receipt is None:
            raise ValueError("Worker requires supervising process")
        try:
            _worker(args.freeze.resolve(), args.output.resolve(), args.resource_receipt.resolve())
        except OutputCap:
            return 3
        except Exception as exc:
            try:
                ByteBudget(args.output, int(os.environ["E0_OUTPUT_PAYLOAD_CAP"])).append_jsonl(
                    "events.jsonl", {"event": "worker_failure", "error_type": type(exc).__name__,
                                     "reason": str(exc)[:1000], "utc": datetime.now(timezone.utc).isoformat()})
            except Exception:
                pass  # Supervisor retains the nonzero exit and existing bytes.
            return 2
        return 0
    if args.resource_receipt is None:
        raise ValueError("Resource receipt is required")
    freeze, receipt = validate_release(args.freeze, args.resource_receipt)
    caps = freeze["caps"]
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--freeze", str(args.freeze.resolve()),
               "--resource-receipt", str(args.resource_receipt.resolve()), "--output", "{output}"]
    manifest = {"freeze": freeze, "freeze_sha256": sha(args.freeze), "resource_receipt": receipt,
                "started_utc": datetime.now(timezone.utc).isoformat(), "model_calls": 0, "paid_usd": 0}
    final = _supervise(args.output, command, total_seconds=caps["outer_seconds"], output_bytes=caps["output_bytes"], manifest=manifest)
    return 0 if final["stop_reason"] == "child_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
