#!/usr/bin/env python3
"""Private offline grading; no model interface and no feedback to collection.

Execution requires a successful source/interpreter/host-bound containment check.
Default use validates and emits missing grades. This is not an adversarial judge.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.landmark.collect import digest, file_sha
from experiments.landmark.analyze import analyze
from experiments.landmark import sandbox
from experiments.common.integrity import hack_gate, canary_block

SPEC_KEYS = {"root_id", "public_task_sha256", "entry_point", "public_assertions", "private_assertions", "preamble", "reference_code", "negative_controls"}
REQUIRED_CHECKS = {"own_run_read_write", "home_read", "home_write", "peer_run_read", "outside_home_tmp_write", "loopback_network", "system_subprocess", "fork_creation", "timeout_and_process_cleanup"}
STARTED = "__LANDMARK_GRADER_STARTED__"


def normalize_assertion(source):
    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assert):
        raise ValueError("Each test must be one standalone assert")
    return ast.dump(tree, include_attributes=False)


def validate_specs(tasks, specs):
    by_root = {t["root_id"]: t for t in tasks}
    if len({s.get("root_id") for s in specs}) != len(specs) or {s.get("root_id") for s in specs} != set(by_root):
        raise ValueError("Private spec must bind exactly the declared public roots")
    for spec in specs:
        if set(spec) != SPEC_KEYS or not isinstance(spec["reference_code"], str) or not spec["reference_code"].strip():
            raise ValueError("Invalid private grading spec")
        task = by_root[spec["root_id"]]
        if spec["public_task_sha256"] != digest(task):
            raise ValueError("Private spec does not bind the public task")
        if not isinstance(spec["entry_point"], str) or not spec["entry_point"].isidentifier():
            raise ValueError("Need explicit entry point")
        if not isinstance(spec["private_assertions"], list) or not spec["private_assertions"]:
            raise ValueError("Empty private tests never constitute a passing endpoint")
        if not isinstance(spec["public_assertions"], list) or not isinstance(spec["preamble"], list):
            raise ValueError("Assertion and preamble fields must be lists")
        if not isinstance(spec["negative_controls"], list) or not spec["negative_controls"]:
            raise ValueError("Each task needs frozen known-wrong controls")
        for control in spec["negative_controls"]:
            if set(control) != {"code", "rationale"} or any(not isinstance(v,str) or not v.strip() for v in control.values()):
                raise ValueError("Negative controls require code and a substantive rationale")
        public = [normalize_assertion(x) for x in spec["public_assertions"]]
        private = [normalize_assertion(x) for x in spec["private_assertions"]]
        if len(set(public)) != len(public) or len(set(private)) != len(private) or set(public)&set(private):
            raise ValueError("Duplicate or overlapping public/private assertions")
        public_text = re.sub(r"\s+", "", task["prompt"]+task["public_context"])
        for assertion in spec["private_assertions"]:
            if re.sub(r"\s+", "", assertion) in public_text:
                raise ValueError("Private assertion text is exposed in public information")
            calls = [n for n in ast.walk(ast.parse(assertion)) if isinstance(n, ast.Call)]
            if not any(isinstance(n.func, ast.Name) and n.func.id==spec["entry_point"] for n in calls):
                raise ValueError("Private assertions must exercise the declared entry point")
        for preamble in spec["preamble"]:
            if any(not isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)) for n in ast.parse(preamble).body):
                raise ValueError("Preamble only supports reviewed imports and setup assignments")


def contract(specs):
    return {"version": "landmark-private-tests-v1", "private_spec_sha256": digest(specs),
        "adapter_sha256": file_sha(__file__), "sandbox_sha256": file_sha(Path(sandbox.__file__)),
        "integrity_sha256": file_sha(ROOT/"experiments/common/integrity.py"),
        "endpoint": "private-test quality under reliable frozen receiver law; unavailable outputs/grading and non-parse static integrity flags are unknown pending review, not deployment-reliability zeros",
        "extraction": "one python/untyped code fence or raw source; multiple fences rejected",
        "determinism": "one frozen artifact grade reused within root; deterministic benchmark/code behavior assumed, not proved",
        "timeout_seconds": 2.0, "cpu_seconds": 1, "output_cap_bytes": 65536}


def current_binding():
    info = sandbox.sandbox_info()
    return {"sandbox_sha256": file_sha(Path(sandbox.__file__)), "profile_sha256": info["profile_sha256"],
            "python": info["python"], "python_sha256": file_sha(info["python"]),
            "host_sha256": hashlib.sha256(platform.node().encode()).hexdigest(),
            "platform": platform.platform(), "sandbox_kind": info["kind"]}


def verify_attestation(path):
    data = json.loads(Path(path).read_text())
    if data.get("schema_version") != "landmark-containment-v1" or data.get("passed") is not True:
        raise ValueError("Containment attestation did not pass")
    if data.get("binding") != current_binding() or data.get("script_sha256") != file_sha(ROOT/"scripts/check_landmark_sandbox.py"):
        raise ValueError("Containment attestation does not match current host/source/interpreter")
    checks = data.get("checks", [])
    if {x.get("name") for x in checks} != REQUIRED_CHECKS or len(checks) != len(REQUIRED_CHECKS) or not all(x.get("passed") is True and x.get("payload_started") is True for x in checks):
        raise ValueError("Incomplete containment checks")
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(data["checked_at"])).total_seconds()
    if not 0 <= age <= 86400:
        raise ValueError("Containment attestation must be from the last 24 hours")
    return data


def extract_code(text):
    fences = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.S)
    if "```" in text:
        if len(fences) != 1 or text.count("```") != 2:
            raise ValueError("Ambiguous code fences")
        return fences[0].strip()
    return text.strip()


def prepare_program(spec, code):
    flags = hack_gate(code, spec["entry_point"])
    if flags:
        parse_failure = flags == ["parse-error"]
        return None, None, {"outcome": 0 if parse_failure else None, "reason": "unparseable_output" if parse_failure else "integrity_review_required", "flags": flags}
    tree = ast.parse(code)
    if not tree.body:
        return None, None, {"outcome": 0, "reason": "empty_produced_program"}
    canary = canary_block({}, hidden_asserts=spec["private_assertions"])
    if canary is None:
        return None, None, {"outcome": None, "reason": "integrity_canary_unavailable"}
    futures = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module=="__future__"]
    rest = [n for n in tree.body if n not in futures]
    sentinel = "__LANDMARK_PRIVATE_OK__"+secrets.token_hex(12)
    start_marker = STARTED+secrets.token_hex(12)
    program = "\n".join([*(ast.unparse(n) for n in futures), f"print({start_marker!r},flush=True)", *spec["preamble"],
        *(ast.unparse(n) for n in rest), *spec["private_assertions"], canary, f"print({sentinel!r},flush=True)"])+"\n"
    return program, sentinel, None


def evaluate(spec, code, runner):
    try:
        program, sentinel, rejection = prepare_program(spec, code)
    except (SyntaxError, ValueError) as exc:
        return {"outcome": 0, "reason": "unparseable_output", "details": str(exc), "sandbox_executed": False}
    if rejection is not None:
        return {**rejection, "sandbox_executed": False}
    try:
        result = runner(program, timeout_s=2, cpu_seconds=1, output_cap=65536)
    except Exception as exc:
        return {"outcome": None, "reason": "grader_execution_unavailable", "details": f"{type(exc).__name__}: {exc}", "sandbox_executed": False}
    start_marker = re.search(STARTED+r"[0-9a-f]{24}", program).group(0)
    if not result.get("stdout", "").startswith(start_marker+"\n"):
        outcome, reason = None, "grader_environment_failed_before_payload"
    elif result["timed_out"]:
        # Execution reached its declared bound: this is an observed endpoint failure.
        outcome, reason = 0, "executed_timeout"
    elif result["returncode"] in (70, 71, 72) or result.get("sandbox_kind") != "seatbelt":
        outcome, reason = None, "grader_environment_failure"
    else:
        outcome = int(result["passed"] and result.get("stdout_tail", "").rstrip().endswith(sentinel))
        reason = "private_tests_passed" if outcome else "executed_test_or_integrity_rejection"
    return {"outcome": outcome, "reason": reason, "sandbox_executed": bool(result["executed"]), "run": result}


def grade_collection(run_dir, specs, output, *, execute=False, attestation_path=None, max_executions=200, max_seconds=240, _runner=None):
    if type(max_executions) is not int or not 1 <= max_executions <= 200 or not 0 < max_seconds <= 240:
        raise ValueError("Grading budget exceeds bounded adapter limits")
    # The analyzer checks collection hashes, unique roots and all arm/replicate assignments.
    analyze(run_dir)
    run_dir, output = Path(run_dir), Path(output)
    manifest = json.loads((run_dir/"manifest.json").read_text())
    validate_specs(manifest["tasks"], specs)
    frozen = contract(specs)
    contract_sha = digest(frozen)
    if manifest["config"]["grading_contract_sha256"] != contract_sha:
        raise ValueError("Collection was not frozen to this private grading contract")
    output.mkdir(parents=True, exist_ok=False)
    block_reason = "execution_not_enabled"
    if execute:
        try:
            if attestation_path is None: raise ValueError("Containment attestation required")
            verify_attestation(attestation_path)
            block_reason = None
        except (ValueError, OSError, KeyError) as exc:
            block_reason = "containment_gate: "+str(exc)
    runner = sandbox.run_program if _runner is None else _runner
    started = time.monotonic()
    count = 0
    executions = []
    cache = {}
    references = {}
    controls = {}
    rows = [json.loads(x) for x in (run_dir/"roots.jsonl").read_text().splitlines()]
    for row in rows:
        if row["excluded"]: continue
        for artifacts in row["arms"].values():
            for artifact in artifacts:
                expected = None if artifact["output"] is None else digest(artifact["output"])
                if artifact["output_sha256"] != expected:
                    raise ValueError("Stored artifact hash does not bind its output bytes")
    by_root = {s["root_id"]: s for s in specs}
    grades = []

    def bounded_evaluate(spec, code, kind):
        nonlocal count
        if count >= max_executions or time.monotonic()-started+2 > max_seconds:
            return {"outcome": None, "reason": "grading_budget_exhausted", "sandbox_executed": False}
        result = evaluate(spec, code, runner)
        count += int(result["sandbox_executed"])
        executions.append({"root_id": spec["root_id"], "kind": kind, "code_sha256": digest(code), **result})
        return result

    for root in rows:
        if root["excluded"]:
            continue
        spec = by_root[root["root_id"]]
        if block_reason is None:
            references[root["root_id"]] = bounded_evaluate(spec, spec["reference_code"], "reference")
            if references[root["root_id"]]["outcome"] == 1:
                controls[root["root_id"]] = [bounded_evaluate(spec,c["code"],"negative_control") for c in spec["negative_controls"]]
        for arm, artifacts in root["arms"].items():
            for artifact in artifacts:
                reason = artifact["missing_reason"] if artifact["output"] is None else block_reason
                value = None
                if artifact["output"] is not None and block_reason is None:
                    if references[root["root_id"]]["outcome"] != 1:
                        reason = "reference_validation_failed_or_unavailable"
                    elif not all(c["outcome"] == 0 and c["sandbox_executed"] for c in controls[root["root_id"]]):
                        reason = "negative_control_validation_failed_or_unavailable"
                    else:
                        key = (root["root_id"], artifact["output_sha256"])
                        if key not in cache:
                            try:
                                code = extract_code(artifact["output"])
                                cache[key] = bounded_evaluate(spec, code, "candidate")
                            except ValueError as exc:
                                cache[key] = {"outcome": 0, "reason": "unparseable_output", "details": str(exc)}
                        value = cache[key]["outcome"]
                        reason = cache[key]["reason"] if value is None else None
                grades.append({"root_id": root["root_id"], "arm": arm, "replicate": artifact["replicate"],
                    "output_sha256": artifact["output_sha256"], "outcome": value,
                    "missing_reason": reason or ("unavailable_output" if value is None else None),
                    "grader_id": "landmark-private-tests-v1:"+contract_sha[:12], "grading_contract_sha256": contract_sha})
    (output/"grades.jsonl").write_text("".join(json.dumps(g)+"\n" for g in grades))
    # Private execution diagnostics are never fed to receiver/prompter APIs.
    (output/"private_execution_records.json").write_text(json.dumps(executions, indent=2)+"\n")
    attestation_sha = None
    if attestation_path is not None:
        try: attestation_sha = file_sha(attestation_path)
        except OSError: pass
    summary = {"contract": frozen, "contract_sha256": contract_sha, "collection_manifest_sha256": file_sha(run_dir/"manifest.json"),
        "attestation_sha256": attestation_sha,
        "execution_requested": execute, "blocked_reason": block_reason, "sandbox_executions": count,
        "sandbox_seconds": sum(e.get("run", {}).get("seconds",0) for e in executions), "wall_seconds": time.monotonic()-started,
        "grade_rows": len(grades), "missing_grade_rows": sum(g["outcome"] is None for g in grades), "model_calls":0,
        "checksums": {p.name:file_sha(p) for p in output.glob("*.json*")}}
    (output/"grading_manifest.json").write_text(json.dumps(summary, indent=2)+"\n")
    # Bind every emitted grade with the existing analyzer before declaring completion.
    analyze(run_dir, output/"grades.jsonl")
    return summary


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--private-spec", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--attestation", type=Path)
    p.add_argument("--print-contract", action="store_true")
    a=p.parse_args()
    specs=[json.loads(x) for x in a.private_spec.read_text().splitlines() if x.strip()]
    if a.print_contract:
        manifest=json.loads((a.run/"manifest.json").read_text())
        validate_specs(manifest["tasks"],specs)
        print(json.dumps({"contract":contract(specs),"grading_contract_sha256":digest(contract(specs))},indent=2))
    elif a.output is None:
        p.error("--output required")
    else:
        result=grade_collection(a.run,specs,a.output,execute=a.execute,attestation_path=a.attestation)
        print(json.dumps({k:result[k] for k in ("blocked_reason","sandbox_executions","grade_rows","missing_grade_rows","wall_seconds")},indent=2))
