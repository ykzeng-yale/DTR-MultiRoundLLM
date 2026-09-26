#!/usr/bin/env python3
"""MRL-34 thin adapter for the fixed 36-slot endpoint reference/control audit (LEAD-ENDPOINT-03).

Source/mock preparation only; running the real audit needs a separate explicit lead release of a committed exact plan
(docs/policy_endpoint_execution_contract_20260926.md). The default `plan` mode parses and hashes, never executes.
The `execute` mode refuses unless: the plan file equals the Git blob at a full commit SHA that is an ancestor of HEAD;
every bound source, the builder/config/package identities, the interpreter/host/profile binding and the slot plan still
match; the attestation file hash matches and the unchanged grade.verify_attestation passes now; the source exists; and
the output directory is new. All of that is checked before any runner call.

Slots: roots 877 then 345; per root the reference then the five MRL-33 controls in builder order; per artifact the
public check, original_private, supplement_v1 (36 slots, kept in every outcome). Checks use the unchanged
public_check.check_artifact (display v2) and grade.evaluate, with one grader spec per battery. There are no
retries, replacements, outcome-based stopping or repairs. A launch is counted and persisted before the runner is called.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from experiments.prompt_choice import endpoint_audit as ea  # noqa: E402
from experiments.landmark import grade, public_check as pc  # noqa: E402
from experiments.landmark.collect import digest, file_sha  # noqa: E402

VERSION = "prompt-choice-endpoint-execution-v1"
MOCK_DESIGNATION = "mock_runner_not_an_audit_result"
CONFIG_PATH = ROOT / "experiments/prompt_choice/endpoint_execution_source_v1.json"
ATTESTATION_PATH = ROOT / "results/policy_endpoint_containment_20260926T2217Z/attestation.json"
ATTESTATION_SCRIPT = ROOT / "scripts/check_landmark_sandbox.py"
CHECKS = ("public", "original_private", "supplement_v1")
LIMITS = {"max_sandbox_starts": 36, "total_elapsed_seconds": 180, "retained_output_bytes": 8 * 1024 * 1024,
          "model_calls": 0, "downloads": 0, "paid_spend": 0}
SLOT_BOUND_SECONDS = {"public": pc.PUBLIC_LIMITS["parent_wall_seconds"], "original_private": 2, "supplement_v1": 2}
# External owned-child supervisor (MRL-34-R1): the parent kills the child's process group at total - kill_reserve; the
# child stops starting slots at slot_budget, leaving time inside the 180 s total for finalization and cleanup.
SUPERVISOR = {"total_seconds": 180, "kill_reserve_seconds": 5, "term_grace_seconds": 2, "slot_budget_seconds": 160}
# Worst case retained bytes for one more slot: stdout and stderr up to 65,536 bytes each, JSON-escaped up to 6x, plus
# record overhead; finalization (summary receipt and projection, no raw duplication) is reserved separately.
WORST_SLOT_BYTES = 6 * 2 * 65536 + 16384
FINALIZATION_RESERVE_BYTES = 256 * 1024
RAW_FIELDS = ("private_results", "private_run", "private_runner_calls", "public_nonce", "public_reasons")
# Exact MRL-33 production identities independently reproduced by the lead (docs/policy_endpoint_source_review_20260926.md).
PACKAGE_IDENTITIES = {
    "public_record_sha256": {"mbpp/877": "fc906f9537fe4cb900e63894a149fcba4618843857d063cb824b72f4ecfb2183",
                             "mbpp/345": "afa9822bd522fba27130be374f72c66689a48d901ee71abb9820e23b1b1d4b45"},
    "private_record_sha256": {"mbpp/877": "4619699141efe87be10688478b43b400d14dfe5b9e9b8dbcde06fb94baadbb7b",
                              "mbpp/345": "20d4defc48000d4e9fa5bbf37b3687961c0db17c5af1f5cd75cfcbb3ef319b55"},
    "builder_sha256": "aa6a4d2ed6fce474a9a0defb721e5ec6e547161aaa592e1e87a36c07978acad1",
    "config_sha256": "cf3885d50d8393d6c68f9750775beb994f104f548b81c43ff62bae50e4b55c51",
}
EVALUATE_REASONS = frozenset({"unparseable_output", "empty_produced_program", "candidate_compile_error",
                              "grader_compile_resource_fault", "integrity_review_required", "integrity_canary_unavailable",
                              "grader_execution_unavailable", "grader_environment_failed_before_payload", "executed_timeout",
                              "grader_environment_failure", "private_tests_passed", "executed_test_or_integrity_rejection"})
ADAPTER_STATUSES = ("launched", "static_decision", "cap_unattempted", "output_cap_unattempted",
                    "interrupted_result_unknown", "interrupted_unattempted")
PUBLIC_FAIL = ("wrong_value", "format_error", "interface_error", "program_exception")
PUBLIC_UNKNOWN = ("timeout", "unavailable", "output_limit")


class ReleaseRefused(RuntimeError):
    """A plan, binding, attestation, source or output check failed; nothing was launched."""


# ---------------------------------------------------------------- slots, specs, identities (pure)
def slot_plan(package: dict) -> list:
    slots = []
    for pub, priv in zip(package["public_records"], package["private_records"]):
        artifacts = [("reference", "reference", priv["reference"]["code"])]
        artifacts += [(c["control_id"], c["kind"], c["code"]) for c in priv["controls"]]
        for artifact_id, kind, code in artifacts:
            for check in CHECKS:
                slots.append({"slot_index": len(slots), "slot_id": f"{pub['task_id']}|{artifact_id}|{check}",
                              "task_id": pub["task_id"], "artifact_id": artifact_id, "artifact_kind": kind, "check": check,
                              "code_sha256": ea.raw_sha256(code)})
    return slots


def task_and_specs(pub: dict, priv: dict) -> tuple:
    """The grader's validate_specs schema, one spec per battery (overlap checks unchanged)."""
    task = {"root_id": pub["task_id"], "prompt": pub["description"] + "\n" + pub["signature"],
            "public_context": pub["public_assertion"]["text"]}
    texts = {"original_private": [c["text"] for c in priv["batteries"]["original_private"]["cases"]],
             "supplement_v1": [c["assertion_text"] for c in priv["batteries"]["supplement_v1"]["cases"]]}
    specs = {}
    for battery, private in texts.items():
        spec = {"root_id": pub["task_id"], "public_task_sha256": digest(task), "entry_point": pub["entry_point"],
                "public_assertions": [pub["public_assertion"]["text"]], "private_assertions": private, "preamble": [],
                "reference_code": priv["reference"]["code"],
                "negative_controls": [{"code": c["code"], "rationale": c["rationale"]} for c in priv["controls"]]}
        grade.validate_specs([task], [spec])
        specs[battery] = spec
    return task, specs


def repo_import_closure(start: Path) -> list:
    """Repo-relative paths of every experiments/* module statically imported from `start`, transitively (AST only)."""
    seen, todo = set(), [Path(start).resolve()]
    while todo:
        path = todo.pop()
        rel = path.relative_to(ROOT).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        names = []
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or "").startswith("experiments"):
                names += [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                names += [a.name for a in node.names if a.name.startswith("experiments")]
        for name in names:
            parts = name.split(".")
            for i in range(1, len(parts) + 1):
                base = ROOT.joinpath(*parts[:i])
                for cand in (base.with_suffix(".py"), base / "__init__.py"):
                    if cand.is_file() and cand.relative_to(ROOT).as_posix() not in seen:
                        todo.append(cand.resolve())
    return sorted(seen)


def bound_sources() -> dict:
    paths = set(repo_import_closure(Path(__file__)))
    paths |= {"experiments/prompt_choice/endpoint_audit_source_v1.json", CONFIG_PATH.relative_to(ROOT).as_posix(),
              ATTESTATION_SCRIPT.relative_to(ROOT).as_posix()}
    return {p: file_sha(ROOT / p) for p in sorted(paths)}


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False)


# ---------------------------------------------------------------- plan (parse and hash only)
def make_plan(source_path, out_dir, *, package=None, binding=None) -> dict:
    """The exact execution plan: hashes and metadata only (no reference, assertion or control body)."""
    package = ea.build(source_path) if package is None else package
    out = Path(out_dir)
    plan = {"version": VERSION, "decision": "LEAD-ENDPOINT-03", "status": "prepared_not_released",
            "package_designation": package["manifest"]["designation"],
            "source": {"path": Path(source_path).as_posix(), "sha256": package["manifest"]["source_sha256"]},
            "package": {"public_record_sha256": package["manifest"]["public_record_sha256"],
                        "private_record_sha256": package["manifest"]["private_record_sha256"],
                        "builder_sha256": package["manifest"]["builder_sha256"],
                        "config_sha256": package["manifest"]["config_sha256"]},
            "bound_sources": bound_sources(),
            "binding": grade.current_binding() if binding is None else binding,
            "attestation": {"path": ATTESTATION_PATH.relative_to(ROOT).as_posix(), "sha256": file_sha(ATTESTATION_PATH)
                            if ATTESTATION_PATH.exists() else None},
            "slots": slot_plan(package), "output_directory": out.as_posix(),
            "limits": LIMITS, "per_call_bound_seconds": SLOT_BOUND_SECONDS, "supervisor": SUPERVISOR,
            "retained_bytes_rule": {"worst_slot_bytes": WORST_SLOT_BYTES, "finalization_reserve_bytes": FINALIZATION_RESERVE_BYTES},
            "predictions": PREDICTIONS}
    return json.loads(json.dumps(plan))  # detached JSON copy: editing a plan never aliases module constants or the package


PREDICTIONS = {"reference": "public pass; original_private pass; supplement_v1 pass",
               "nonlookup_control": "original_private fail (at least one original-private assertion fails)",
               "lookup_original_examples": "public pass; original_private pass; supplement_v1 fail"}


def verify_release(plan_path, plan_commit, source_path, *, git=_git, binding=None, attest=grade.verify_attestation,
                   package=None, allow_synthetic=False) -> dict:
    """Every gate before any launch; raises ReleaseRefused naming the first failure."""
    plan_path = Path(plan_path)
    try:
        data = plan_path.read_bytes()
        plan = json.loads(data)
    except (OSError, ValueError) as e:
        raise ReleaseRefused(f"plan unreadable: {type(e).__name__}") from None
    if not (isinstance(plan_commit, str) and len(plan_commit) == 40 and all(c in "0123456789abcdef" for c in plan_commit)):
        raise ReleaseRefused("plan commit must be a full 40-hex SHA")
    try:
        rel = plan_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        raise ReleaseRefused("plan must be a file inside the repository") from None
    blob = git("rev-parse", f"{plan_commit}:{rel}")
    if blob.returncode != 0 or blob.stdout.strip() != git_blob_sha1(data):
        raise ReleaseRefused("plan file is not the committed blob at the given commit")
    if git("merge-base", "--is-ancestor", plan_commit, "HEAD").returncode != 0:
        raise ReleaseRefused("plan commit is not an ancestor of HEAD")
    if plan.get("version") != VERSION:
        raise ReleaseRefused("plan version mismatch")
    if plan.get("bound_sources") != bound_sources():
        raise ReleaseRefused("bound source drift")
    try:
        package = ea.build(source_path) if package is None else package
    except ea.AuditSourceError as e:
        raise ReleaseRefused(f"source/package refused: {e}") from None
    ident = {"public_record_sha256": package["manifest"]["public_record_sha256"],
             "private_record_sha256": package["manifest"]["private_record_sha256"],
             "builder_sha256": package["manifest"]["builder_sha256"], "config_sha256": package["manifest"]["config_sha256"]}
    if plan.get("package") != ident or (package["manifest"]["designation"] == "production" and ident != PACKAGE_IDENTITIES):
        raise ReleaseRefused("package identity drift")
    if plan.get("slots") != slot_plan(package) or len(plan["slots"]) != 36:
        raise ReleaseRefused("slot plan incomplete or changed")
    if plan.get("binding") != (grade.current_binding() if binding is None else binding):
        raise ReleaseRefused("interpreter/host/profile binding drift")
    if plan.get("limits") != LIMITS:
        raise ReleaseRefused("limit drift")
    att = ROOT / plan["attestation"]["path"]
    if not att.exists() or file_sha(att) != plan["attestation"]["sha256"]:
        raise ReleaseRefused("attestation file absent or changed")
    try:
        attest(att)
    except (ValueError, OSError, KeyError) as e:
        raise ReleaseRefused(f"attestation invalid now: {e}") from None
    if Path(plan["output_directory"]).exists():
        raise ReleaseRefused("output directory already exists")
    out = Path(plan["output_directory"]).resolve()
    if (ROOT / "work").resolve() not in out.parents:
        raise ReleaseRefused("output directory must be inside work/")
    if package["manifest"]["designation"] != "production" and not allow_synthetic:
        raise ReleaseRefused("only the production package can be released")
    expected = make_plan(source_path, Path(plan["output_directory"]), package=package,
                         binding=grade.current_binding() if binding is None else binding)
    if plan != expected:  # the whole canonical plan, exact field set included
        raise ReleaseRefused("plan differs from the reconstructed canonical plan")
    return plan


# ---------------------------------------------------------------- outcomes (pure)
def public_outcome(results: list):
    statuses = [r["status"] for r in results]
    if any(s in PUBLIC_FAIL for s in statuses):
        return 0
    if statuses and all(s == "pass" for s in statuses):
        return 1
    return None  # incomplete or unavailable: unknown, never pass or fail


def classify(slot_records: list) -> dict:
    """Per artifact: confirmed / contradicted / unknown against the lead's predictions. Contradiction needs an observed
    outcome; any unobserved component that could decide the prediction leaves it unknown."""
    by_artifact = {}
    for r in slot_records:
        by_artifact.setdefault((r["task_id"], r["artifact_id"], r["artifact_kind"]), {})[r["check"]] = r["outcome"]
    out = {}
    for (task, artifact, kind), o in by_artifact.items():
        if kind == "reference":
            want = {"public": 1, "original_private": 1, "supplement_v1": 1}
        elif kind == "lookup_original_examples":
            want = {"public": 1, "original_private": 1, "supplement_v1": 0}
        else:
            want = {"original_private": 0}
        seen = {k: o.get(k) for k in want}
        if any(v is not None and v != want[k] for k, v in seen.items()):
            verdict = "contradicted"
        elif any(v is None for v in seen.values()):
            verdict = "unknown"
        else:
            verdict = "confirmed"
        out[f"{task}|{artifact}"] = {"kind": kind, "prediction": PREDICTIONS.get(kind, PREDICTIONS["nonlookup_control"]),
                                     "observed": dict(o), "verdict": verdict}
    return out


def public_projection(receipt: dict) -> dict:
    """Compact public result: identities, statuses, reason codes and totals only (no bodies, expected values or output)."""
    rows = []
    for r in receipt["slots"]:
        reason = r.get("reason")
        if reason is not None and reason not in EVALUATE_REASONS and reason not in pc.UNAVAILABLE_REASONS \
                and reason not in ADAPTER_STATUSES and reason != "public_check":
            reason = "other_recorded_privately"
        rows.append({k: r.get(k) for k in ("slot_index", "slot_id", "task_id", "artifact_kind", "check", "code_sha256",
                                           "status", "launched", "outcome", "seconds", "returncode")}
                    | {"reason": reason, "public_statuses": r.get("public_statuses")})
    return {"version": VERSION, "designation": receipt["designation"], "run_status": receipt["run_status"],
            "plan_sha256": receipt.get("plan_sha256"), "totals": receipt["totals"], "slots": rows,
            "predictions": {k: {"kind": v["kind"], "verdict": v["verdict"], "observed": v["observed"]}
                            for k, v in receipt["classification"].items()},
            "note": "reference/control measurement only; not policy efficacy or a memorization prevalence estimate"}


# ---------------------------------------------------------------- execution loop
def run_audit(package, slots, out_dir, runner, *, designation, plan_sha256=None, clock=time.monotonic, limits=LIMITS) -> dict:
    """Run the 36 slots once each in order with the given runner, persisting a start manifest and one flushed record per
    slot. Caps convert remaining slots to recorded unattempted slots; an interrupt records the run as interrupted."""
    out = Path(out_dir)
    out.mkdir(parents=False, exist_ok=False)
    by_task = {p["task_id"]: (p, q) for p, q in zip(package["public_records"], package["private_records"])}
    codes = {}
    specs = {}
    for task, (pub, priv) in by_task.items():
        codes[(task, "reference")] = priv["reference"]["code"]
        codes.update({(task, c["control_id"]): c["code"] for c in priv["controls"]})
        specs[task] = task_and_specs(pub, priv)[1]
    started, launches, written, records = clock(), 0, 0, []
    start_manifest = {"version": VERSION, "designation": designation, "plan_sha256": plan_sha256, "limits": limits,
                      "started_at": datetime.now(timezone.utc).isoformat(), "slots": slots}
    with open(out / "start_manifest.json", "x", encoding="utf-8") as fh:
        text = json.dumps(start_manifest, sort_keys=True) + "\n"
        fh.write(text)
    written += len(text.encode("utf-8"))
    log = open(out / "slots_private.jsonl", "x", encoding="utf-8")

    def persist(obj):
        nonlocal written
        line = json.dumps(obj, sort_keys=True, default=str) + "\n"
        log.write(line)
        log.flush()
        os.fsync(log.fileno())
        written += len(line.encode("utf-8"))

    stop_reason, current, run_status = None, None, "completed"
    try:
        for slot in slots:
            current = slot
            rec = dict(slot)
            elapsed = clock() - started
            if stop_reason is None and (launches >= limits["max_sandbox_starts"]
                                        or elapsed + SLOT_BOUND_SECONDS[slot["check"]] > SUPERVISOR["slot_budget_seconds"]):
                stop_reason = "cap_unattempted"
            if stop_reason is None and written + WORST_SLOT_BYTES + FINALIZATION_RESERVE_BYTES > limits["retained_output_bytes"]:
                stop_reason = "output_cap_unattempted"
            if stop_reason is not None:
                rec.update(status=stop_reason, launched=False, outcome=None, reason=stop_reason)
                persist({"event": "slot", **rec})
                records.append(rec)
                continue
            launched, raw_calls = [], []

            def counted(program, **kw):
                nonlocal launches
                launches += 1  # counted and persisted before the runner is invoked
                launched.append(True)
                call = {"program_sha256": hashlib.sha256(program.encode("utf-8")).hexdigest(), "bounds": kw}
                persist({"event": "launch_attempt", "slot_id": slot["slot_id"], "launch_number": launches,
                         "program_sha256": call["program_sha256"]})
                try:
                    result = runner(program, **kw)
                except BaseException as e:
                    call["exception"] = f"{type(e).__name__}: {e}"
                    raw_calls.append(call)
                    raise
                call["result"] = result  # raw runner result (stdout, stderr, return code) kept privately
                raw_calls.append(call)
                return result

            code, t0 = codes[(slot["task_id"], slot["artifact_id"])], clock()
            pub = by_task[slot["task_id"]][0]
            if slot["check"] == "public":
                nonce = secrets.token_hex(16)
                results = pc.check_artifact(code, pub["entry_point"], [dict(pub["public_case"])], counted, nonce, display="v2")
                rec.update(outcome=public_outcome(results), reason="public_check", public_nonce=nonce,
                           public_statuses=[r["status"] for r in results],
                           public_reasons=[r["reason"] for r in results], private_results=results)
            else:
                res = grade.evaluate(specs[slot["task_id"]][slot["check"]], code, counted)
                run = res.get("run") or {}
                rec.update(outcome=res["outcome"], reason=res["reason"], returncode=run.get("returncode"),
                           private_results={k: v for k, v in res.items() if k != "run"}, private_run=run)
            rec.update(status="launched" if launched else "static_decision", launched=bool(launched),
                       seconds=round(clock() - t0, 6), private_runner_calls=raw_calls)
            persist({"event": "slot", **rec})
            records.append(rec)
            current = None
    except BaseException as exc:  # interrupt, supervisor deadline or adapter fault: never declared complete
        run_status = f"interrupted:{type(exc).__name__}"
        done = {r["slot_id"] for r in records}
        for slot in slots:
            if slot["slot_id"] in done:
                continue
            in_flight = current is not None and slot["slot_id"] == current["slot_id"]
            rec = dict(slot, status="interrupted_result_unknown" if in_flight else "interrupted_unattempted",
                       launched=None if in_flight else False, outcome=None,
                       reason="interrupted_result_unknown" if in_flight else "interrupted_unattempted")
            try:
                persist({"event": "slot", **rec})
            except Exception:
                pass
            records.append(rec)
        _finish(out, log, records, designation, plan_sha256, run_status, launches, clock() - started, written)
        raise
    return _finish(out, log, records, designation, plan_sha256, run_status, launches, clock() - started, written)


def _finish(out, log, records, designation, plan_sha256, run_status, launches, elapsed, written):
    log.close()
    summaries = [{k: v for k, v in r.items() if k not in RAW_FIELDS} for r in records]  # raw results stay only in the JSONL
    receipt = {"version": VERSION, "designation": designation, "plan_sha256": plan_sha256, "run_status": run_status,
               "totals": {"slots": len(records), "sandbox_launch_attempts": launches, "elapsed_seconds": round(elapsed, 6),
                          "retained_bytes_before_finalization": written, "model_calls": 0,
                          "by_status": {s: sum(r["status"] == s for r in records) for s in ADAPTER_STATUSES}},
               "slots": summaries, "classification": classify(records),
               "raw_records": "slots_private.jsonl (runner results, program hashes, public nonces)"}
    with open(out / "receipt_private.json", "x", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, sort_keys=True, default=str, indent=1) + "\n")
    projection = public_projection(receipt)
    with open(out / "public_projection.json", "x", encoding="utf-8") as fh:
        fh.write(json.dumps(projection, sort_keys=True, indent=1) + "\n")
    receipt["totals"]["retained_bytes_total"] = sum(f.stat().st_size for f in out.iterdir() if f.is_file())
    return receipt


def supervise(cmd, *, popen=subprocess.Popen, killpg=os.killpg, clock=time.monotonic) -> dict:
    """External owned-child supervisor: start the audit child in its own session, kill only that owned process group at
    total - kill_reserve, and record the observed exit and whether the group is gone (never assumed)."""
    t0 = clock()
    child = popen(cmd, start_new_session=True)
    killed, rc = False, None
    try:
        rc = child.wait(timeout=SUPERVISOR["total_seconds"] - SUPERVISOR["kill_reserve_seconds"])
    except subprocess.TimeoutExpired:
        killed = True
        for sig, wait in ((signal.SIGTERM, SUPERVISOR["term_grace_seconds"]), (signal.SIGKILL, 1)):
            try:
                killpg(child.pid, sig)
            except ProcessLookupError:
                pass
            try:
                rc = child.wait(timeout=wait)
                break
            except subprocess.TimeoutExpired:
                continue
    try:
        killpg(child.pid, 0)
        cleanup = "unresolved: owned process group still present"
    except ProcessLookupError:
        cleanup = "confirmed: owned process group gone"
    except PermissionError:
        cleanup = "unresolved: cannot signal owned process group"
    return {"child_pid": child.pid, "child_exit": rc, "killed_at_deadline": killed, "cleanup": cleanup,
            "elapsed_seconds": round(clock() - t0, 6), "total_seconds": SUPERVISOR["total_seconds"]}


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("plan", help="write the exact plan (parse and hash only; executes nothing)")
    p.add_argument("--source", required=True)
    p.add_argument("--out-dir", required=True, help="future audit output directory inside work/ (must not exist)")
    p.add_argument("--plan", required=True, help="new plan file to write (never overwritten)")
    x = sub.add_parser("execute", help="run a released committed plan (requires a separate explicit lead release)")
    x.add_argument("--source", required=True)
    x.add_argument("--plan", required=True)
    x.add_argument("--plan-commit", required=True)
    c = sub.add_parser("_child", help=argparse.SUPPRESS)
    c.add_argument("--source", required=True)
    c.add_argument("--plan", required=True)
    c.add_argument("--plan-commit", required=True)
    a = ap.parse_args(argv)
    if a.mode == "plan":
        out = Path(a.out_dir).resolve()
        if (ROOT / "work").resolve() not in out.parents or out.exists():
            print("refused: output directory must be new and inside work/", file=sys.stderr)
            return 2
        try:
            plan = make_plan(a.source, Path(a.out_dir))
            with open(a.plan, "x", encoding="utf-8") as fh:
                fh.write(json.dumps(plan, sort_keys=True, indent=1) + "\n")
        except (ea.AuditSourceError, FileExistsError) as e:
            print(f"refused: {type(e).__name__}: {e}", file=sys.stderr)
            return 2
        print(a.plan)
        return 0
    try:
        plan = verify_release(a.plan, a.plan_commit, a.source)
    except ReleaseRefused as e:
        print(f"refused before any launch: {e}", file=sys.stderr)
        return 2
    if a.mode == "execute":  # parent: supervise the owned child and record its observed exit and cleanup
        record = supervise([sys.executable, str(Path(__file__).resolve()), "_child", "--source", a.source, "--plan", a.plan,
                            "--plan-commit", a.plan_commit])
        out = Path(plan["output_directory"])
        target = out / "supervisor.json" if out.is_dir() else out.with_name(out.name + ".supervisor.json")
        with open(target, "x", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True))
        return 0 if record["child_exit"] == 0 and not record["killed_at_deadline"] else 3
    from experiments.landmark import sandbox  # child only, imported after every gate has passed
    receipt = run_audit(ea.build(a.source), plan["slots"], plan["output_directory"], sandbox.run_program,
                        designation="released_audit", plan_sha256=file_sha(a.plan))
    print(json.dumps(receipt["totals"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
