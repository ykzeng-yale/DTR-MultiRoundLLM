"""Phase B driver for the MRL-08 public diagnostic (source/mock only; this module never executes anything itself).

run_phase_b reads Phase A's directory (collect_diagnostic.run_initial: manifest.json, completion.json, roots.jsonl,
artifacts/<artifact_name(root_id)>), re-verifies every file against completion.json's checksums and every artifact's
raw-bytes SHA-256 against roots.jsonl's artifact_sha256 (initial_artifact_sha256 convention), and refuses on any
mismatch. For each collected root, in roots.jsonl order, it calls public_check.check_artifact with the INJECTED runner
and a fresh nonce, then diagnostic.build_diagnostic, then diagnostic.validate_diagnostic when the module defines it.

Input boundary: public cases come ONLY from examples_path, which passes public_check.assert_public_inputs_only. The
initial artifacts are read by this driver as text, outside the executor, and handed to public_check as the candidate
answer; the executor's own inputs are that text plus the public cases, so the work/ rule of the allowlist governs
what enters the executor, not this driver's read of Phase A's directory (which may legitimately live under work/).

Durability (MRL-09): after all inputs are verified and BEFORE any dispatch, out_dir is created (it must not exist) and
an append-only attempt ledger out_dir/attempts.jsonl is opened exclusively; every record is flushed and fsynced. For
each runner call a 'start' record (root_id, artifact SHA-256, SHA-256 of the nonce -- never the nonce --, runner id,
UTC) is written BEFORE the call and a 'result' record (raw returncode, timed_out, stdout SHA-256) right after it, so a
later classifier error or crash cannot erase a start; a 'classified' record then carries the statuses. On any
exception after reservation the ledger is kept and out_dir/INCOMPLETE records the error; nothing is deleted, and a
rerun into the same out_dir is refused (no uncharged rerun).

Real execution is opt-in only via the CLI (--real): grade.verify_attestation(A) runs FIRST, then sandbox.run_program
is the runner. run_phase_b refuses sandbox.run_program without a verified attestation record.

Outputs (out_dir must not exist; nothing is ever overwritten):
  diagnostics.json  exact bytes json.dumps({root_id: diag}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    .encode(); its SHA-256 is what collect_diagnostic.run_continue(expected_diagnostics_sha256=...) binds.
  manifest.json     diagnostics_sha256, executor source SHA-256s, PUBLIC_LIMITS, actual runner invocations. Nonces are
                    ephemeral and never written. There are no retries: each root gets at most one runner invocation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import functools
import inspect
import re
import json
import os
from pathlib import Path
import secrets
import sys
import time

from experiments.landmark import diagnostic, public_check

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXECUTOR_SOURCES = ("experiments/landmark/public_phase.py", "experiments/landmark/public_check.py",
                    "experiments/landmark/diagnostic.py", "experiments/landmark/sandbox.py",
                    "experiments/landmark/grade.py", "experiments/common/integrity.py")
SCHEMA = "public-phase-b-v2"
LEDGER = "attempts.jsonl"
FAKE_ATTESTATION = "fake_runner_for_tests"
ATTESTATION_FIELDS = ("schema_version", "passed", "checked_at", "binding", "script_sha256")


def _loads(data):
    return diagnostic.strict_json_loads(data)  # looked up at call time: duplicate keys refuse everywhere


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _complete_provenance(a) -> bool:
    fields = a.get("verified_fields") if isinstance(a, dict) else None
    return (isinstance(a, dict) and isinstance(a.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", a["sha256"]) is not None
            and isinstance(fields, dict) and set(fields) == set(ATTESTATION_FIELDS) and fields["passed"] is True
            and isinstance(a.get("verified_check_names"), list) and len(a["verified_check_names"]) > 0)


def runner_identity(runner) -> dict:
    """module + qualname of the injected runner; plus its source file SHA-256 when it is sandbox.run_program."""
    while isinstance(runner, functools.partial) or hasattr(runner, "__wrapped__"):
        runner = runner.func if isinstance(runner, functools.partial) else runner.__wrapped__
    target = runner if hasattr(runner, "__qualname__") else type(runner)
    ident = {"module": getattr(target, "__module__", None), "qualname": getattr(target, "__qualname__", None)}
    if ident["module"] == "experiments.landmark.sandbox" and ident["qualname"] == "run_program":
        ident["source_sha256"] = _sha(Path(inspect.getsourcefile(runner)).read_bytes())
    return ident


def attestation_provenance(path, verified: dict) -> dict:
    return {"path": str(path), "sha256": _sha(Path(path).read_bytes()),
            "verified_fields": {k: verified.get(k) for k in ATTESTATION_FIELDS},
            "verified_check_names": sorted(str(c.get("name")) for c in verified.get("checks", []))}


class Ledger:
    """Append-only JSONL opened exclusively; every record is flushed and fsynced before returning."""
    def __init__(self, path: Path):
        self.f = open(path, "xb")
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def write(self, record: dict):
        self.f.write(json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
        self.f.flush()
        os.fsync(self.f.fileno())

    def close(self):
        self.f.close()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact_name(root_id):
    return root_id.replace("/", "%2F") + ".txt"  # collect_diagnostic.artifact_name (kept import-free of that module)


def load_examples(examples_path):
    """root_id -> (entry_point, cases) from a public_diagnostic_examples_v1.json file; refuses duplicates."""
    doc = _loads(Path(examples_path).read_bytes())
    out = {}
    for item in doc["cases"]:
        if item["root_id"] in out:
            raise ValueError(f"Duplicate public examples for {item['root_id']}")
        out[item["root_id"]] = (item["entry_point"], item["cases"])
    return out


PHASE_A_EVIDENCE_TYPES = ("ungraded_real_collection", "mock_transport_only")
PHASE_A_REQUIRED_FILES = ("manifest.json", "roots.jsonl", "calls.jsonl")


def load_initial(initial_dir):
    """Phase A rows with verified artifact text, in roots.jsonl (assignment) order. Refuses on any mismatch.

    MRL-10: all of this runs before any runner start. The completion checksum inventory must be COMPLETE (its key set
    equals exactly the files present apart from completion.json, and includes manifest.json, roots.jsonl, calls.jsonl
    and every artifacts/*.txt); the manifest must be a recorded Phase A manifest (phase initial, arm_set equal to
    completion's, evidence_type recorded); and roots.jsonl must cover the manifest assignment_table exactly (same roots
    in the same order, each once; excluded roots carry no artifact)."""
    initial_dir = Path(initial_dir)
    manifest = _loads((initial_dir / "manifest.json").read_bytes())
    completion = _loads((initial_dir / "completion.json").read_bytes())
    if manifest.get("phase") != "initial" or completion.get("phase") != "initial":
        raise ValueError("Not a diagnostic initial-phase directory")
    if not manifest.get("arm_set") or manifest.get("arm_set") != completion.get("arm_set"):
        raise ValueError("Phase A manifest arm_set missing or differs from completion.json")
    if manifest.get("evidence_type") not in PHASE_A_EVIDENCE_TYPES:
        raise ValueError("Phase A manifest does not record a known evidence_type")
    checksums = completion.get("checksums")
    if not isinstance(checksums, dict):
        raise ValueError("completion.json has no checksum inventory")
    present = {q.relative_to(initial_dir).as_posix() for q in initial_dir.rglob("*") if q.is_file()} - {"completion.json"}
    missing_required = [f for f in PHASE_A_REQUIRED_FILES if f not in checksums]
    if missing_required:
        raise ValueError(f"Incomplete checksum inventory: missing {missing_required}")
    if set(checksums) != present:
        raise ValueError("Incomplete checksum inventory: checksummed files differ from files present "
                         f"(unlisted={sorted(present - set(checksums))}, absent={sorted(set(checksums) - present)})")
    for rel, sha in checksums.items():
        if _sha((initial_dir / rel).read_bytes()) != sha:
            raise ValueError(f"Initial-phase file changed after completion: {rel}")
    rows = [_loads(x) for x in (initial_dir / "roots.jsonl").read_text().splitlines() if x.strip()]
    ids = [r["root_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate root in roots.jsonl")
    table = manifest.get("assignment_table")
    if not isinstance(table, list) or not table:
        raise ValueError("Phase A manifest has no assignment_table")
    if [p["root_id"] for p in table] != ids:
        raise ValueError("roots.jsonl does not cover the manifest assignment_table exactly once, in order")
    for p, r in zip(table, rows):
        if bool(p["excluded"]) != bool(r.get("excluded")):
            raise ValueError(f"Exclusion differs between assignment_table and roots.jsonl for {p['root_id']}")
        if p["excluded"] and (r.get("artifact") or r.get("artifact_sha256")
                              or (initial_dir / "artifacts" / _artifact_name(p["root_id"])).exists()):
            raise ValueError(f"Excluded root has an artifact: {p['root_id']}")
    collected = []
    for p, r in zip(table, rows):
        if p["excluded"]:
            continue
        if not r.get("artifact_sha256"):
            # MRL-10 review: a non-excluded assigned root must be covered, or carry the recorded collection failure.
            initial = r.get("initial")
            if (r.get("status") != "initial_failed" or r.get("artifact") is not None or not isinstance(initial, dict)
                    or initial.get("output") is not None):
                raise ValueError(f"Assigned root neither collected nor recorded as initial_failed: {p['root_id']}")
            continue
        if r.get("artifact") != "artifacts/" + _artifact_name(r["root_id"]):
            raise ValueError(f"Unexpected artifact path for {r['root_id']}")
        data = (initial_dir / r["artifact"]).read_bytes()
        if _sha(data) != r["artifact_sha256"]:
            raise ValueError(f"Initial artifact bytes differ from the recorded SHA-256 for {r['root_id']}")
        collected.append((r["root_id"], r["artifact_sha256"], data.decode("utf-8")))
    expected_artifacts = {"artifacts/" + _artifact_name(root) for root, _, _ in collected}
    if {q for q in checksums if q.startswith("artifacts/")} != expected_artifacts:
        raise ValueError("artifacts/ does not equal the artifacts of collected assigned roots")
    return completion, collected


def run_phase_b(initial_dir: Path, examples_path: Path, out_dir: Path, runner, nonce_factory=secrets.token_hex,
                attestation: dict | None = None) -> dict:
    """attestation: attestation_provenance(...) of a VERIFIED record (CLI --real path); None only for fake runners."""
    out_dir = Path(out_dir)
    if out_dir.exists():
        raise FileExistsError(f"Phase B output already exists (no uncharged rerun): {out_dir}")
    ident = runner_identity(runner)
    if attestation is None:
        # Only an explicitly declared fake may run without attestation: wrappers (partial, lambda) of the real
        # runner are not "not sandbox.run_program" by identity alone.
        if "source_sha256" in ident or getattr(runner, "FAKE_RUNNER", False) is not True:
            raise ValueError("sandbox.run_program requires a verified containment attestation")
        attestation = FAKE_ATTESTATION
    elif not _complete_provenance(attestation):
        raise ValueError("Incomplete attestation provenance")
    public_check.assert_public_inputs_only([examples_path])
    examples = load_examples(examples_path)
    completion, collected = load_initial(initial_dir)
    missing = [root for root, _, _ in collected if root not in examples]
    if missing:
        raise ValueError(f"No public examples for collected roots: {missing}")
    for root, _, _ in collected:  # every example validated against diagnostic's case policy before any charge
        entry_point, cases = examples[root]
        diagnostic.public_skeleton(entry_point, cases)

    out_dir.mkdir(parents=True, exist_ok=False)  # reservation: from here on every attempt is charged
    ledger = Ledger(out_dir / LEDGER)
    try:
        manifest = _dispatch(initial_dir, examples_path, out_dir, runner, nonce_factory, attestation, ident,
                             examples, collected, ledger)
    except BaseException as e:
        try:
            ledger.write({"event": "incomplete", "error": f"{type(e).__name__}: {e}", "utc": _utc()})
        finally:
            ledger.close()
            with (out_dir / "INCOMPLETE").open("x", encoding="utf-8") as f:
                f.write(f"{type(e).__name__}: {e}\n")
        raise
    return manifest


def _monotonic():
    """time.monotonic(), or None when the clock cannot be read (never a fabricated 0)."""
    try:
        t = time.monotonic()
    except Exception:
        return None
    return float(t) if isinstance(t, (int, float)) and not isinstance(t, bool) else None


def _since(t0):
    """Elapsed seconds since t0 by time.monotonic(); None if either reading is unavailable or not finite/non-negative."""
    t1 = _monotonic()
    if t0 is None or t1 is None:
        return None
    d = t1 - t0
    return d if d >= 0 and d != float("inf") and d == d else None


def _dispatch(initial_dir, examples_path, out_dir, runner, nonce_factory, attestation, ident, examples, collected,
              ledger):
    ledger.write({"event": "reserved", "schema_version": SCHEMA, "runner": ident, "attestation": attestation, "utc": _utc(),
                  "initial_completion_sha256": _sha((Path(initial_dir) / "completion.json").read_bytes()),
                  "examples_sha256": _sha(Path(examples_path).read_bytes())})
    invocations = {"n": 0}
    current = {}
    elapsed = []  # per-start time.monotonic() elapsed for the current root; None = could not be measured
    ledger_errors = []

    def counted(*args, **kwargs):  # every runner invocation is an executor start attempt; no retries
        try:  # check_artifact swallows runner exceptions, so ledger failures are re-raised after it returns
            ledger.write({"event": "start", "root_id": current["root"], "initial_artifact_sha256": current["sha"],
                          "nonce_sha256": _sha(current["nonce"].encode()), "runner": ident, "utc": _utc()})
        except BaseException as e:
            ledger_errors.append(e)
            raise
        invocations["n"] += 1
        t0 = _monotonic()
        try:
            run = runner(*args, **kwargs)
        except BaseException as e:
            secs = _since(t0)
            elapsed.append(secs)
            _result({"root_id": current["root"], "runner_error": f"{type(e).__name__}: {e}", "elapsed_seconds": secs})
            raise
        secs = _since(t0)
        elapsed.append(secs)
        stdout = run.get("stdout", "") if isinstance(run, dict) else ""
        _result({"root_id": current["root"], "returncode": run.get("returncode") if isinstance(run, dict) else None,
                 "timed_out": run.get("timed_out") if isinstance(run, dict) else None,
                 "stdout_sha256": _sha(stdout.encode("utf-8", "surrogatepass") if isinstance(stdout, str) else bytes(stdout)),
                 "elapsed_seconds": secs})
        return run

    def _result(rec):
        try:
            ledger.write({"event": "result", "utc": _utc(), **rec})
        except BaseException as e:
            ledger_errors.append(e)
            raise

    diags, per_root = {}, []
    validate = getattr(diagnostic, "validate_diagnostic", None)
    for root, sha, text in collected:
        entry_point, cases = examples[root]
        before = invocations["n"]
        current.update(root=root, sha=sha, nonce=nonce_factory())
        elapsed.clear()
        results = public_check.check_artifact(text, entry_point, cases, counted, current["nonce"])
        if ledger_errors:
            raise ledger_errors[0]
        statuses = [r["status"] for r in results]
        # Sum of measured runner-call time for this root; zero starts measure 0.0; any unmeasured start -> null.
        executor_seconds = None if any(x is None for x in elapsed) else float(sum(elapsed))
        ledger.write({"event": "classified", "root_id": root, "runner_invocations": invocations["n"] - before,
                      "executor_seconds": executor_seconds, "statuses": statuses, "utc": _utc()})
        diag = diagnostic.build_diagnostic(root, sha, entry_point, cases, results)
        if validate is not None:
            validate(diag)
        diagnostic.diagnostic_bytes(diag)  # cap check; raises, never truncates
        diags[root] = diag
        per_root.append({"root_id": root, "initial_artifact_sha256": sha, "runner_invocations": invocations["n"] - before,
                         "executor_seconds": executor_seconds, "statuses": statuses})

    data = json.dumps(diags, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ledger.write({"event": "complete", "diagnostics_sha256": _sha(data), "executor_starts": invocations["n"],
                  "utc": _utc()})
    ledger.close()
    manifest = {
        "schema_version": SCHEMA, "diagnostics_sha256": _sha(data),
        "initial_completion_sha256": _sha((Path(initial_dir) / "completion.json").read_bytes()),
        "examples_sha256": _sha(Path(examples_path).read_bytes()),
        "executor_source_sha256": {name: _sha((REPO / name).read_bytes()) for name in EXECUTOR_SOURCES},
        "runner": ident, "attestation": attestation,
        "attempts_ledger": LEDGER, "attempts_ledger_sha256": _sha((out_dir / LEDGER).read_bytes()),
        "public_limits": dict(public_check.PUBLIC_LIMITS),
        "executor_starts": invocations["n"],  # runner invocations (format errors / integrity flags start nothing)
        "retries": 0, "nonces_recorded": False, "roots": per_root,
    }
    with (out_dir / "diagnostics.json").open("xb") as f:
        f.write(data)
    with (out_dir / "manifest.json").open("x", encoding="utf-8") as f:
        f.write(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return manifest


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(prog="python -m experiments.landmark.public_phase")
    ap.add_argument("--initial-dir", required=True)
    ap.add_argument("--examples", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--attestation", required=True)
    ap.add_argument("--real", action="store_true")
    a = ap.parse_args(argv)
    if not a.real:
        raise SystemExit("refusing: Phase B executes candidate programs; pass --real with a verified --attestation")
    for flag, value in vars(a).items():
        if isinstance(value, str) and value.startswith("UNRESOLVED:"):
            raise SystemExit(f"refusing: --{flag.replace('_', '-')} is unresolved ({value})")
    from experiments.landmark import grade, sandbox  # lazy: nothing real is imported unless --real
    try:
        before = _sha(Path(a.attestation).read_bytes())
        verified = grade.verify_attestation(a.attestation)  # FIRST: before out_dir or any input is touched
        prov = attestation_provenance(a.attestation, verified)
    except Exception as e:
        raise SystemExit(f"refusing: containment attestation not verified: {type(e).__name__}: {e}")
    if prov["sha256"] != before:
        raise SystemExit("refusing: attestation file changed during verification")
    return run_phase_b(Path(a.initial_dir), Path(a.examples), Path(a.out), sandbox.run_program, attestation=prov)


if __name__ == "__main__":
    main(sys.argv[1:])
