#!/usr/bin/env python3
"""E8 (versioned, generic): validate the frozen REBOUND references and negative controls.

    python -m experiments.landmark.validate_rebound_references --specs S.jsonl --specs-sha256 H \
        --tasks T.jsonl --out DIR --attestation A --real

Supersedes the historical validate_references.py for the rebound release (which is preserved, unedited):
  * reads the builder's JSONL spec format (one spec per line, duplicate keys refused);
  * one job per frozen reference and one per frozen negative control -- NO special-case rewrite of any root
    (in particular no 402 repair job: the rebound reference is already the repaired one) and no extra jobs;
  * exactly 24 planned starts (7 references + 17 controls); expected 7 pass / 17 fail.

Per job this uses grade.evaluate (grade.prepare_program semantics) against the spec's FULL private suite.
A control counts as a demonstrated failure only if the runner actually started it and it returned outcome 0;
a static rejection, environment failure or timeout-before-payload never stands in for a failure.

Refusals (in order, before any start): missing --real; grade.verify_attestation failure (checked FIRST);
specs byte SHA-256 mismatch; grade.validate_specs(tasks, specs) failure; planned job count != 24; existing out dir;
a runner that is neither sandbox.run_program nor an explicitly declared fake (FAKE_RUNNER = True).

Durable accounting: OUT/attempts.jsonl is created exclusively and every record is flushed + fsynced:
  reserved (provenance) -> per job: job_start, program_start (immediately BEFORE the runner is invoked),
  job_result -> complete | INCOMPLETE (on any exception; the ledger is never deleted). No job is retried.
Actual starts are reported separately from the planned maximum.
"""
from __future__ import annotations

import argparse
import os
import hashlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from experiments.landmark import grade, sandbox, diagnostic  # noqa: E402
from experiments.landmark.public_phase import Ledger, runner_identity, attestation_provenance  # noqa: E402

SCHEMA = "landmark-rebound-reference-validation-v1"
PLANNED_STARTS = 24
EXPECTED_REFERENCES = 7
EXPECTED_CONTROLS = 17
LEDGER = "attempts.jsonl"
SUMMARY = "summary.json"
PROVENANCE_SOURCES = {
    "validator": Path(__file__).resolve(),
    "grade": ROOT / "experiments/landmark/grade.py",
    "sandbox": ROOT / "experiments/landmark/sandbox.py",
    "integrity": ROOT / "experiments/common/integrity.py",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jsonl(data: bytes, what: str) -> list[dict]:
    rows = []
    for n, line in enumerate(data.decode("utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{what}: blank line {n} is not allowed in a frozen JSONL file")
        row = diagnostic.strict_json_loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{what}: line {n} is not a JSON object")
        rows.append(row)
    if not rows:
        raise ValueError(f"{what}: empty")
    return rows


def plan_jobs(specs: list[dict]) -> list[dict]:
    """Generic: one reference job + one job per negative control per spec, verbatim code, no rewrites."""
    jobs = []
    for spec in specs:
        jobs.append({"root_id": spec["root_id"], "kind": "reference", "index": 0,
                     "code": spec["reference_code"], "expected_outcome": 1})
        for i, control in enumerate(spec["negative_controls"]):
            jobs.append({"root_id": spec["root_id"], "kind": "control", "index": i,
                         "code": control["code"], "expected_outcome": 0})
    for j in jobs:
        j["code_sha256"] = _sha(j["code"].encode("utf-8"))
    return jobs


def check_plan(jobs: list[dict]) -> None:
    refs = sum(j["kind"] == "reference" for j in jobs)
    ctls = sum(j["kind"] == "control" for j in jobs)
    if len(jobs) != PLANNED_STARTS or refs != EXPECTED_REFERENCES or ctls != EXPECTED_CONTROLS:
        raise ValueError(f"Planned job count must be exactly {PLANNED_STARTS} "
                         f"({EXPECTED_REFERENCES} references + {EXPECTED_CONTROLS} controls); got {len(jobs)} ({refs}+{ctls})")


def provenance() -> dict:
    return {name: _sha(Path(p).read_bytes()) for name, p in PROVENANCE_SOURCES.items()}


def _check_runner(runner) -> dict:
    ident = runner_identity(runner)
    if runner is not sandbox.run_program and getattr(runner, "FAKE_RUNNER", False) is not True:
        raise ValueError("Runner must be sandbox.run_program or an explicitly declared fake (FAKE_RUNNER=True)")
    return ident


def _job_passed(job_row: dict) -> bool:
    return job_row["outcome"] == 1


def _as_expected(job_row: dict) -> bool:
    if job_row["kind"] == "reference":
        return job_row["outcome"] == 1 and job_row["starts"] == 1
    # a control must be demonstrated to fail: actually started, executed, observed outcome 0
    return job_row["outcome"] == 0 and job_row["starts"] == 1 and job_row["sandbox_executed"] is True


def run(specs_path, specs_sha256, tasks_path, out, attestation, real, runner=None) -> dict:
    if real is not True:
        raise PermissionError("Refusing: real execution requires --real")
    verified = grade.verify_attestation(attestation)  # FIRST: raises unless containment passed, fresh and bound
    att = attestation_provenance(attestation, verified)
    runner = sandbox.run_program if runner is None else runner
    ident = _check_runner(runner)

    specs_bytes = Path(specs_path).read_bytes()
    actual_sha = _sha(specs_bytes)
    if actual_sha != specs_sha256:
        raise ValueError(f"Specs SHA-256 mismatch: expected {specs_sha256}, file has {actual_sha}")
    tasks_bytes = Path(tasks_path).read_bytes()
    specs = load_jsonl(specs_bytes, "specs")
    tasks = load_jsonl(tasks_bytes, "tasks")
    grade.validate_specs(tasks, specs)
    jobs = plan_jobs(specs)
    check_plan(jobs)
    by_root = {s["root_id"]: s for s in specs}

    out = Path(out)
    if out.exists():
        raise FileExistsError(f"Output already exists (no uncharged rerun): {out}")
    out.mkdir(parents=True, exist_ok=False)
    ledger = Ledger(out / LEDGER)  # exclusive create + fsync; never deleted
    state = {"starts": 0}
    rows = []
    try:
        ledger.write({"event": "reserved", "schema_version": SCHEMA, "utc": _utc(),
                      "planned_starts": PLANNED_STARTS, "specs_sha256": actual_sha,
                      "tasks_sha256": _sha(tasks_bytes), "source_sha256": provenance(),
                      "runner": ident, "attestation": att,
                      "jobs": [{k: j[k] for k in ("root_id", "kind", "index", "code_sha256", "expected_outcome")} for j in jobs]})
        started = time.monotonic()
        for n, job in enumerate(jobs):
            key = {k: job[k] for k in ("root_id", "kind", "index", "code_sha256")}
            ledger.write({"event": "job_start", "job": n, **key, "utc": _utc()})
            job_starts = {"n": 0}

            def counted(program, _n=n, _key=key, _js=job_starts, **kw):
                if _js["n"] != 0:
                    raise RuntimeError("Refusing a second start for one job (no retries)")
                _js["n"] += 1
                state["starts"] += 1
                ledger.write({"event": "program_start", "job": _n, **_key, "program_sha256": _sha(program.encode("utf-8")),
                              "actual_starts_so_far": state["starts"], "utc": _utc()})
                return runner(program, **kw)

            r = grade.evaluate(by_root[job["root_id"]], job["code"], counted)
            run_info = r.get("run") or {}
            row = {**key, "expected_outcome": job["expected_outcome"], "outcome": r.get("outcome"),
                   "reason": r.get("reason"), "flags": r.get("flags"), "details": r.get("details"),
                   "timed_out": run_info.get("timed_out"), "sandbox_executed": r.get("sandbox_executed"),
                   "starts": job_starts["n"], "stderr_tail": (run_info.get("stderr") or "")[-300:]}
            row["passed"] = _job_passed(row)
            row["as_expected"] = _as_expected(row)
            rows.append(row)
            ledger.write({"event": "job_result", "job": n, **row, "actual_starts_so_far": state["starts"], "utc": _utc()})
        passes = sum(r["passed"] for r in rows)
        summary = {"schema_version": SCHEMA, "planned_starts": PLANNED_STARTS, "actual_starts": state["starts"],
                   "jobs_completed": len(rows), "model_calls": 0,
                   "sandbox_seconds_wall": round(time.monotonic() - started, 2),
                   "passes": passes, "fails": len(rows) - passes,
                   "expected": {"pass": EXPECTED_REFERENCES, "fail": EXPECTED_CONTROLS},
                   "matches_expected": len(rows) == PLANNED_STARTS and all(r["as_expected"] for r in rows),
                   "jobs": [{k: r[k] for k in ("root_id", "kind", "index", "code_sha256", "outcome", "reason",
                                               "timed_out", "starts", "passed", "expected_outcome", "as_expected")}
                            for r in rows],
                   "specs_sha256": actual_sha, "runner": ident, "attestation_sha256": att["sha256"]}
        with open(out / SUMMARY, "x") as f:
            f.write(json.dumps(summary, indent=2, sort_keys=True))
            f.flush()
            os.fsync(f.fileno())
        ledger.write({"event": "complete", "actual_starts": state["starts"], "planned_starts": PLANNED_STARTS,
                      "matches_expected": summary["matches_expected"], "utc": _utc()})
        return summary
    except BaseException as e:
        try:
            ledger.write({"event": "INCOMPLETE", "error": f"{type(e).__name__}: {e}",
                          "traceback_tail": traceback.format_exc()[-2000:], "actual_starts": state["starts"],
                          "planned_starts": PLANNED_STARTS, "jobs_completed": len(rows), "utc": _utc()})
        finally:
            ledger.close()
        raise
    finally:
        if not ledger.f.closed:
            ledger.close()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--specs", type=Path, required=True)
    p.add_argument("--specs-sha256", required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--attestation", type=Path, required=True)
    p.add_argument("--real", action="store_true")
    a = p.parse_args(argv)
    summary = run(a.specs, a.specs_sha256, a.tasks, a.out, a.attestation, a.real)
    print(json.dumps({k: summary[k] for k in ("planned_starts", "actual_starts", "passes", "fails", "matches_expected")}, indent=2))
    return 0 if summary["matches_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
