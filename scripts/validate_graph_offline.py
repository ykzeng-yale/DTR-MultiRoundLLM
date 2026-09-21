#!/usr/bin/env python3
"""Validate frozen data-only graph fixtures; never call a model or execute answers."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark.graph_adapter import (
    build_public_task, generate_root, grade_response, validate_puzzle,
)

DESIGN_FREEZE = "58847236039b84f561bcc94c2ad53bd7e72e0fa1"
CONFIG_PATH = "experiments/landmark/graph_fixture_config_v1.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args]).decode().strip()


def peak_rss_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


class BudgetExceeded(RuntimeError):
    pass


def independent_validity(puzzle, reference):
    """Small direct check separate from the adopted verifier."""
    return (
        set(reference) == set(puzzle["vertices"])
        and all(type(c) is int and c in puzzle["color_options"] for c in reference.values())
        and all(reference[u] != reference[v] for u, v in puzzle["edges"])
    )


def _verify_sources(implementation_commit):
    paths = [Path(__file__).resolve(), ROOT/"experiments/landmark/graph_adapter.py",
             ROOT/"experiments/landmark/__init__.py"]
    paths += sorted(p for p in (ROOT/"experiments/landmark/vendor").iterdir() if p.is_file())
    sources = {}
    for path in paths:
        relative = str(path.relative_to(ROOT))
        content = path.read_bytes()
        committed = subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{implementation_commit}:{relative}"], timeout=5)
        if content != committed:
            raise ValueError(f"Uncommitted execution source: {relative}")
        sources[relative] = sha(content)
    return sources


def _accept_record(records, record):
    """One acceptance point; derive both exports and ledger counts afterward."""
    records.append(record)


def _write_artifacts(output, files, max_bytes):
    """Write completion manifest last/atomically; retain evidence of failed writes."""
    try:
        existing = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        if existing + sum(map(len, files.values())) + 4096 > max_bytes:
            raise BudgetExceeded("artifact_bytes (including reserved failure-record space)")
        for name, data in files.items():
            if name == "manifest.json":
                continue
            with (output/name).open("xb") as stream:
                stream.write(data)
        temporary = output/".manifest.json.tmp"
        with temporary.open("xb") as stream:
            stream.write(files["manifest.json"])
        temporary.replace(output/"manifest.json")
    except Exception as exc:
        # If the device itself cannot be written, the preexisting RUN_STARTED
        # marker still identifies an incomplete run; no successful manifest exists.
        failure = encoded({"status": "artifact_write_failed", "error_type": type(exc).__name__})
        try:
            occupied = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
            if occupied + len(failure) <= max_bytes:
                with (output/"FAILURE.json").open("xb") as stream:
                    stream.write(failure)
        except OSError:
            pass
        raise
    return sum(p.stat().st_size for p in output.iterdir() if p.is_file())


def run(config_path, output):
    started = time.perf_counter()
    config_bytes = config_path.read_bytes()
    frozen_bytes = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{DESIGN_FREEZE}:{CONFIG_PATH}"]
    )
    if config_bytes != frozen_bytes:
        raise ValueError("This runner requires the exact committed offline fixture design")
    config = json.loads(config_bytes)
    implementation_commit = git("rev-parse", "HEAD")
    subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
                    DESIGN_FREEZE, implementation_commit], check=True)
    sources = _verify_sources(implementation_commit)
    if output.exists():
        raise FileExistsError("Use a new output directory; completed or failed runs are immutable")
    output.mkdir(parents=True)
    started_record = encoded({"status": "started", "design_freeze_commit": DESIGN_FREEZE,
                              "implementation_commit": implementation_commit,
                              "config_sha256": sha(config_bytes)})
    with (output/"RUN_STARTED.json").open("xb") as stream:
        stream.write(started_record)
    ledger = [{"root_index": i, "root_id": f"rg-graph/v1/{config['first_seed']+i}",
               "seed": config["first_seed"]+i, "status": "not_attempted"}
              for i in range(config["root_count"])]
    accepted_records, controls = [], []
    all_public_keys = {"root_id", "family_id", "prompt", "public_context"}

    def check_budget():
        if time.perf_counter()-started > config["max_wall_seconds"]:
            raise BudgetExceeded("wall_time")
        if peak_rss_bytes() > config["max_memory_mib"]*1024**2:
            raise BudgetExceeded("resident_memory")

    def alarm_handler(signum, frame):
        raise BudgetExceeded("wall_time_alarm")

    previous = signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, config["max_wall_seconds"])
    status, failure = "complete", None
    try:
        check_budget()
        validate_puzzle(config["fixed_control_puzzle"])
        for control in config["fixed_controls"]:
            result = grade_response(config["fixed_control_puzzle"], control["response"],
                                    max_response_bytes=config["max_response_bytes"])
            matched = result["score"] == control["expected_score"]
            expected_status = "missing" if control["response"] is None else "observed"
            matched = matched and result["status"] == expected_status
            controls.append({"name": control["name"], "expected_score": control["expected_score"],
                             "expected_status": expected_status, "actual": result, "matches": matched})
            if not matched:
                raise ValueError(f"Frozen control mismatch: {control['name']}")
        for i, row in enumerate(ledger):
            check_budget()
            row.update(num_vertices=config["vertex_schedule"][i % len(config["vertex_schedule"])],
                       edge_probability=config["edge_probability_schedule"][i % len(config["edge_probability_schedule"])])
            row["status"] = "generation_started"
            generated = generate_root(row["seed"], row["num_vertices"], row["edge_probability"],
                                      config["num_colors"], config["max_attempts_per_root"])
            row.update(status=("generated_pending_validation" if generated["status"] == "generated"
                               else generated["status"]), attempts=generated["attempts"])
            check_budget()
            if generated["status"] != "generated":
                continue
            puzzle, reference = generated["puzzle"], generated["reference"]
            validate_puzzle(puzzle)
            if not independent_validity(puzzle, reference):
                raise ValueError("Generated reference fails independent edge/domain check")
            response = json.dumps(reference, sort_keys=True)
            reference_grade = grade_response(puzzle, response, max_response_bytes=config["max_response_bytes"])
            if reference_grade["score"] != 1:
                raise ValueError("Valid reference rejected by response adapter")
            task = build_public_task(row["root_id"], config["family_id"], puzzle)
            if set(task) != all_public_keys or not all(isinstance(v, str) for v in task.values()):
                raise ValueError("Public task schema violates whitelist")
            row.update(puzzle_sha256=sha(encoded(puzzle)), public_task_sha256=sha(encoded(task)),
                       reference_accepted=True, independent_reference_valid=True)
            _accept_record(accepted_records, {"task": task, "private": {
                "root_id": row["root_id"], "puzzle": puzzle, "reference": reference,
                "public_task_sha256": row["public_task_sha256"],
                "puzzle_sha256": row["puzzle_sha256"]}})
    except Exception as exc:
        status, failure = "failed", f"{type(exc).__name__}: {exc}"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)

    accepted_ids = {record["task"]["root_id"] for record in accepted_records}
    public = [record["task"] for record in accepted_records]
    private = [record["private"] for record in accepted_records]
    graph_roots = defaultdict(list)
    for row in ledger:
        if row["root_id"] in accepted_ids:
            row["status"] = "accepted"
            graph_roots[row["puzzle_sha256"]].append(row["root_id"])
        elif row["status"] == "not_attempted":
            row["status"] = "not_attempted_run_failure"
        elif row["status"] == "generation_started":
            row["status"] = "generation_interrupted_attempt_count_unknown"
        elif row["status"] == "generated_pending_validation":
            row["status"] = "validation_interrupted"
    # All arrays are bounded by the frozen 32-root/15-control plan.
    files = {
        "public_tasks.jsonl": b"".join(encoded(x) for x in public),
        "private_references.jsonl": b"".join(encoded(x) for x in private),
        "root_ledger.jsonl": b"".join(encoded(x) for x in ledger),
        "fixed_controls.json": encoded(controls),
    }
    manifest = {
        "schema_version": "graph-offline-validation-v1", "status": status, "failure": failure,
        "design_freeze_commit": DESIGN_FREEZE, "implementation_commit": implementation_commit,
        "python_version": sys.version, "platform": sys.platform, "interpreter": sys.executable,
        "config_sha256": sha(config_bytes), "source_sha256": sources,
        "ready_for_collection": False, "family_id": config["family_id"], "split": config["split"],
        "receiver_calls": 0, "receiver_input_tokens": 0, "receiver_output_tokens": 0,
        "receiver_runtime_seconds": 0, "paid_spend_usd": 0, "generated_programs_executed": 0,
        "assigned_roots": len(ledger), "accepted_roots": len(public),
        "generation_failed_roots": sum(r["status"] == "generation_failed" for r in ledger),
        "not_attempted_roots": sum(r["status"].startswith("not_attempted") for r in ledger),
        "recorded_generation_attempts": sum(r.get("attempts", 0) for r in ledger),
        "generation_attempt_count_unknown_roots": sum(
            r["status"] == "generation_interrupted_attempt_count_unknown" for r in ledger),
        "root_status_counts": {status: sum(r["status"] == status for r in ledger)
                               for status in sorted({r["status"] for r in ledger})},
        "fixed_controls_checked": len(controls), "fixed_controls_matched": sum(c["matches"] for c in controls),
        "exact_duplicate_groups": [ids for ids in graph_roots.values() if len(ids) > 1],
        "isomorphism_or_family_independence_certified": False,
        "elapsed_through_validation_seconds": time.perf_counter()-started,
        "peak_resident_bytes": peak_rss_bytes(),
        "resource_enforcement": "Validation-loop wall alarm; RSS checks between bounded roots; byte cap before writing; one process. Git setup and final writes are outside the alarm; total elapsed is measured.",
        "run_started_sha256": sha(started_record),
        "files": {name: {"sha256": sha(data), "bytes": len(data)} for name, data in files.items()},
    }
    files["manifest.json"] = encoded(manifest)
    total_bytes = _write_artifacts(output, files, config["max_artifact_bytes"])
    summary = {k: manifest[k] for k in ("status", "failure", "assigned_roots", "accepted_roots",
               "generation_failed_roots", "not_attempted_roots", "recorded_generation_attempts",
               "generation_attempt_count_unknown_roots",
               "fixed_controls_checked", "fixed_controls_matched", "peak_resident_bytes")}
    summary.update(artifact_bytes=total_bytes, elapsed_total_seconds=time.perf_counter()-started,
                   manifest_sha256=sha(files["manifest.json"]), output=str(output), receiver_calls=0,
                   receiver_tokens=0, paid_spend_usd=0)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT/CONFIG_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.config, args.output)
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
