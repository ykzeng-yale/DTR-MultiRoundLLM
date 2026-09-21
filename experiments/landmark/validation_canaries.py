"""E3/E4/E5 validation-canary CLI (MRL-09). Source only until a separately authorized run.

    python -m experiments.landmark.validation_canaries --canaries experiments/landmark/validation_canaries_v1.json \
        --out O --attestation A --real

Refuses without --real, refuses an existing --out, refuses unless grade.verify_attestation passes, refuses any
"UNRESOLVED:" value. With --real it writes a reserved provenance record (attestation sha + verified fields + check
names, runner identity, source SHA-256s, canary sha, per-canary static-gate vs payload path, planned MAXIMUM starts)
BEFORE dispatch, then appends a fsynced ledger.jsonl record per actual START (before the runner) and per RESULT
(after), runs each canary exactly once through public_check.check_artifact (no retries), writes INCOMPLETE on any
exception, never deletes, and reports actual starts separately from the planned maximum.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from experiments.landmark import diagnostic, grade, public_check, public_phase, sandbox

REPO = Path(__file__).resolve().parents[2]
PROVENANCE_SOURCES = ("experiments/landmark/validation_canaries.py", "experiments/landmark/public_check.py",
                      "experiments/landmark/diagnostic.py", "experiments/landmark/public_phase.py", "experiments/landmark/sandbox.py", "experiments/landmark/grade.py",
                      "experiments/common/integrity.py")

SCHEMA = "landmark-validation-canaries-v1"
CANARY_KEYS = {"id", "gate", "entry_point", "cases", "candidate_code", "expected", "acceptable", "static_gate_flags", "never_pass_cases", "note"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def refuse_unresolved(obj, where="value"):
    if isinstance(obj, str) and obj.startswith("UNRESOLVED:"):
        raise ValueError(f"Refusing unresolved {where}: {obj}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            refuse_unresolved(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            refuse_unresolved(v, f"{where}[{i}]")


def load_canaries(path):
    raw = Path(path).read_bytes()
    doc = diagnostic.strict_json_loads(raw)
    if not isinstance(doc, dict) or doc.get("schema_version") != SCHEMA:
        raise ValueError("Not a landmark-validation-canaries-v1 file")
    ids = set()
    for c in doc["canaries"]:
        if set(c) != CANARY_KEYS or c["id"] in ids or c["gate"] not in ("E3", "E4", "E5"):
            raise ValueError(f"Malformed canary: {c.get('id')}")
        ids.add(c["id"])
        for pattern in [c["expected"], *c["acceptable"]]:
            if len(pattern) != len(c["cases"]) or any(r["status"] not in public_check.STATUSES for r in pattern):
                raise ValueError(f"Bad expected pattern: {c['id']}")
            if any((r["status"] == "unavailable") != (r["reason"] in public_check.UNAVAILABLE_REASONS) for r in pattern):
                raise ValueError(f"Unavailable reason mismatch: {c['id']}")
        compile(c["candidate_code"], c["id"], "exec")  # compile only; never executed here
        path, flags = decided_by(c)
        if flags != sorted(c["static_gate_flags"]):
            raise ValueError(f"static_gate_flags differ from hack_gate for {c['id']}: {flags}")
        want = {"static_format_gate": public_check.format_error_results(c["cases"]),
                "static_integrity_gate": public_check.uniform_results(c["cases"], "unavailable", "protocol_integrity_review")}.get(path)
        if want is not None and [p for p in [c["expected"], *c["acceptable"]]
                                 if p != [{"status": r["status"], "reason": r["reason"]} for r in want]]:
            raise ValueError(f"{c['id']} is decided by the {path} (no start) but expects a payload outcome")
    refuse_unresolved(doc, "canaries")
    return doc, hashlib.sha256(raw).hexdigest()


def decided_by(c):
    """Which path of public_check.check_artifact decides this canary: STATIC (format or integrity gate, no runner
    start) or PAYLOAD (exactly one runner start). Static analysis only (extract/parse/hack_gate); nothing executes."""
    code = public_check.static_code(c["candidate_code"])
    if code is None:
        return "static_format_gate", []
    flags = sorted(f for f in public_check.hack_gate(code, c["entry_point"]) if f != "parse-error")
    return ("static_integrity_gate" if flags else "payload"), flags


def _file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runner_provenance(runner):
    ident = public_phase.runner_identity(runner)
    try:
        import inspect
        target = runner if hasattr(runner, "__code__") or hasattr(runner, "__qualname__") else type(runner)
        ident["source_file_sha256"] = _file_sha(inspect.getsourcefile(target))
    except (TypeError, OSError):
        ident["source_file_sha256"] = None
    ident["fake_runner"] = getattr(runner, "FAKE_RUNNER", False) is True
    return ident


def run(canaries_path, out, attestation, real, runner=None):
    if not real:
        raise SystemExit("validation_canaries executes sandboxed programs; pass --real (separately authorized) to run")
    out = Path(out)
    if out.exists():
        raise SystemExit(f"Refusing to overwrite {out}")
    att_before = _file_sha(attestation)
    att = grade.verify_attestation(attestation)  # must pass before anything else is dispatched
    if _file_sha(attestation) != att_before:
        raise SystemExit("Attestation file changed during verification; refusing")
    doc, sha = load_canaries(canaries_path)
    runner = runner or sandbox.run_program
    paths = {c["id"]: decided_by(c)[0] for c in doc["canaries"]}
    planned_max = sum(v == "payload" for v in paths.values())
    reserved = {"schema_version": SCHEMA + "-ledger", "record": "reserved", "canaries_sha256": sha,
                "canaries_path": str(canaries_path), "attestation": public_phase.attestation_provenance(attestation, att),
                "attestation_checked_at": att.get("checked_at"), "runner": runner_provenance(runner),
                "source_sha256": {rel: _file_sha(REPO / rel) for rel in PROVENANCE_SOURCES},
                "planned_max_starts": planned_max, "planned_static_no_start": len(paths) - planned_max, "retries": 0,
                "decided_by": paths, "planned": [c["id"] for c in doc["canaries"]], "written_utc": _now()}
    out.mkdir(parents=True)
    with (out / "ledger.json").open("x") as f:  # reserved snapshot; the durable per-start/result log is ledger.jsonl
        f.write(json.dumps(reserved, indent=1, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    log = public_phase.Ledger(out / "ledger.jsonl")
    log.write(reserved)
    rows, starts = [], [0]
    try:
        for c in doc["canaries"]:
            calls, ledger_errors = [], []
            def counted(program, **kw):
                try:  # durable BEFORE the runner; a start is counted only once its record is durable
                    log.write({"record": "start", "id": c["id"], "start_index": starts[0] + 1, "program_sha256":
                               hashlib.sha256(program.encode("utf-8")).hexdigest(), "utc": _now()})
                except BaseException as exc:
                    ledger_errors.append(exc)
                    raise
                starts[0] += 1
                calls.append(1)
                try:
                    res = runner(program, **kw)
                except BaseException as exc:
                    _raw({"record": "runner_result", "id": c["id"], "start_index": starts[0],
                          "runner_error": f"{type(exc).__name__}: {exc}", "utc": _now()})
                    raise
                out_text = res.get("stdout", "") if isinstance(res, dict) else ""
                _raw({"record": "runner_result", "id": c["id"], "start_index": starts[0],
                      "returncode": res.get("returncode") if isinstance(res, dict) else None,
                      "timed_out": res.get("timed_out") if isinstance(res, dict) else None,
                      "stdout_sha256": hashlib.sha256(str(out_text).encode("utf-8")).hexdigest(), "utc": _now()})
                return res
            def _raw(rec):
                try:
                    log.write(rec)
                except BaseException as exc:
                    ledger_errors.append(exc)
                    raise
            observed = public_check.check_artifact(c["candidate_code"], c["entry_point"], c["cases"], counted, secrets.token_hex(16))
            if ledger_errors:  # check_artifact converts runner-wrapper exceptions; a ledger failure must end INCOMPLETE
                raise ledger_errors[0]
            obs = [{"status": r["status"], "reason": r["reason"]} for r in observed]
            row = {"id": c["id"], "gate": c["gate"], "decided_by": paths[c["id"]], "starts": len(calls),
                   "start_expected": paths[c["id"]] == "payload", "observed": obs, "expected": c["expected"],
                   "matches_expected": obs == c["expected"], "within_acceptable": obs in c["acceptable"],
                   "passed_forbidden_case": any(obs[i]["status"] == "pass" for i in c["never_pass_cases"])}
            rows.append(row)
            log.write({"record": "result", **row, "utc": _now()})
    except BaseException as e:
        log.write({"record": "INCOMPLETE", "error": f"{type(e).__name__}: {e}", "actual_starts": starts[0],
                   "planned_max_starts": planned_max, "results_written": len(rows), "utc": _now()})
        log.close()
        raise
    result = {"schema_version": SCHEMA + "-result", "canaries_sha256": sha, "actual_starts": starts[0],
              "planned_max_starts": planned_max, "static_decided": len(paths) - planned_max,
              "all_within_acceptable": all(r["within_acceptable"] for r in rows),
              "any_forbidden_pass": any(r["passed_forbidden_case"] for r in rows), "rows": rows, "finished_utc": _now()}
    log.write({"record": "complete", "actual_starts": starts[0], "planned_max_starts": planned_max, "utc": _now()})
    log.close()
    with (out / "result.json").open("x") as f:
        f.write(json.dumps(result, indent=1, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--canaries", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--attestation", type=Path, required=True)
    p.add_argument("--real", action="store_true")
    a = p.parse_args(argv)
    result = run(a.canaries, a.out, a.attestation, a.real)
    print(json.dumps({"all_within_acceptable": result["all_within_acceptable"], "any_forbidden_pass": result["any_forbidden_pass"]}))
    return 0 if result["all_within_acceptable"] and not result["any_forbidden_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
