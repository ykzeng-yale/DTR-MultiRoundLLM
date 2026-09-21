"""E3/E4/E5 validation-canary CLI (MRL-09). Source only until a separately authorized run.

    python -m experiments.landmark.validation_canaries --canaries experiments/landmark/validation_canaries_v1.json \
        --out O --attestation A --real

Refuses without --real, refuses an existing --out, refuses unless grade.verify_attestation passes, refuses any
"UNRESOLVED:" value. With --real it writes a start ledger BEFORE dispatch, runs each canary exactly once through
public_check.check_artifact with sandbox.run_program (no retries), then writes observed vs expected per canary.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from experiments.landmark import diagnostic, grade, public_check, sandbox

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
    refuse_unresolved(doc, "canaries")
    return doc, hashlib.sha256(raw).hexdigest()


def run(canaries_path, out, attestation, real, runner=None):
    if not real:
        raise SystemExit("validation_canaries executes sandboxed programs; pass --real (separately authorized) to run")
    out = Path(out)
    if out.exists():
        raise SystemExit(f"Refusing to overwrite {out}")
    att = grade.verify_attestation(attestation)  # must pass before anything else is dispatched
    doc, sha = load_canaries(canaries_path)
    runner = runner or sandbox.run_program
    out.mkdir(parents=True)
    ledger = {"schema_version": SCHEMA + "-ledger", "canaries_sha256": sha, "attestation_checked_at": att.get("checked_at"),
              "planned_starts": len(doc["canaries"]), "retries": 0, "written_utc": _now(),
              "planned": [c["id"] for c in doc["canaries"]]}
    (out / "ledger.json").write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")
    rows = []
    for c in doc["canaries"]:
        calls = []
        def counted(program, **kw):
            calls.append(1)
            return runner(program, **kw)
        observed = public_check.check_artifact(c["candidate_code"], c["entry_point"], c["cases"], counted, secrets.token_hex(16))
        obs = [{"status": r["status"], "reason": r["reason"]} for r in observed]
        rows.append({"id": c["id"], "gate": c["gate"], "starts": len(calls), "observed": obs, "expected": c["expected"],
                     "matches_expected": obs == c["expected"], "within_acceptable": obs in c["acceptable"],
                     "passed_forbidden_case": any(obs[i]["status"] == "pass" for i in c["never_pass_cases"])})
    result = {"schema_version": SCHEMA + "-result", "canaries_sha256": sha, "actual_starts": sum(r["starts"] for r in rows),
              "all_within_acceptable": all(r["within_acceptable"] for r in rows),
              "any_forbidden_pass": any(r["passed_forbidden_case"] for r in rows), "rows": rows, "finished_utc": _now()}
    (out / "result.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
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
