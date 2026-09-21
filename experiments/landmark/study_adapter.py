#!/usr/bin/env python3
"""Adapter from the phased diagnostic-v1 collection (collect_diagnostic.py) to private grading and
analyze_diagnostic.py input. Pure file/arithmetic work: it never executes candidate code itself; the
only execution path is grade.evaluate(spec, code, runner) with a runner the CALLER injects.

Why not grade.grade_collection(view, ...)? It is blocked by grade.py's own integrity checks, which this
module does not hack around (grade.py is inside the grading-contract digest and is not edited):
  1. grade_collection first calls analyze.analyze(run_dir), which requires
     set(row["arms"]) == {"stop", *collect.ARMS} = {"stop","generic_repair","history_specific_repair",
     "independent_restart"}; the study arms STOP,N0,S0,N1,S1,R1 cannot be represented.
  2. It requires manifest["config"]["grading_contract_sha256"] == digest(grade.contract(specs)); the
     diagnostic-v1 collector config does not freeze that field.
  3. analyze.analyze also requires a single run_dir manifest/completion/assignment_table whose rows carry
     every plan key; the study is two phase directories (initial, continue).
So to_grading_view writes the roots.jsonl ROW layout grade.py consumes (root_id, family_id, excluded,
arms -> [{replicate, output, output_sha256, missing_reason}], output_sha256 = collect.digest(output))
plus a view manifest listing these blockers, and grade_study mirrors grade.grade_collection's
per-artifact logic (output-hash binding, reference recheck, negative-control recheck, cache by
(root_id, output_sha256), extract_code, bounded executions) calling grade.evaluate per artifact.
Differences from grade_collection: no containment attestation gate (the caller owns the runner and must
only pass the attested sandbox runner in real use), no collection-contract check (blocker 2), and no
analyze.analyze binding (blocker 1); grade rows carry grader_id "landmark-private-tests-v1:study:<sha12>".
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from experiments.landmark.collect import digest, file_sha  # noqa: E402

STUDY_ARMS = ("STOP", "N0", "S0", "N1", "S1", "R1")
CONTINUATION_ARMS = STUDY_ARMS[1:]
GRADE_PY_BLOCKERS = (
    "analyze.analyze(run_dir): set(row['arms']) must equal {'stop', *collect.ARMS}; STOP,N0,S0,N1,S1,R1 unrepresentable",
    "manifest['config']['grading_contract_sha256'] must equal digest(grade.contract(specs)); diagnostic-v1 config does not freeze it",
    "analyze.analyze(run_dir): single manifest/completion/assignment_table for one run_dir; the study has two phase directories",
)


def _rows(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def _bytes_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _checked(rec):
    out = rec.get("output")
    if rec.get("output_sha256") != (None if out is None else digest(out)):
        raise ValueError("Stored artifact hash does not bind its output bytes")
    return out


def to_grading_view(initial_dir, continue_dir, out_dir):
    """Write out_dir/roots.jsonl (grade.py row layout, arms STOP..R1) and out_dir/view_manifest.json."""
    initial_dir, continue_dir, out_dir = Path(initial_dir), Path(continue_dir), Path(out_dir)
    a_rows = {r["root_id"]: r for r in _rows(initial_dir / "roots.jsonl")}
    c_rows = _rows(continue_dir / "roots.jsonl")
    if len(a_rows) != len(_rows(initial_dir / "roots.jsonl")) or {r["root_id"] for r in c_rows} != set(a_rows) \
            or len(c_rows) != len(a_rows):
        raise ValueError("Initial and continuation phases do not cover the same unique roots")
    view = []
    for c in c_rows:
        a = a_rows[c["root_id"]]
        row = {"root_id": c["root_id"], "family_id": c.get("family_id"), "excluded": bool(c["excluded"]), "arms": {}}
        if c["excluded"] != a["excluded"]:
            raise ValueError(f"Exclusion changed between phases for {c['root_id']}")
        if row["excluded"]:
            view.append(row)
            continue
        init = a["initial"]
        text = _checked(init)
        sha = a.get("artifact_sha256")
        if text is not None:
            stored = (initial_dir / a["artifact"]).read_bytes()
            if hashlib.sha256(stored).hexdigest() != sha or stored != text.encode("utf-8"):
                raise ValueError(f"Initial artifact bytes do not match artifact_sha256 for {c['root_id']}")
            if c.get("initial_artifact_sha256") != sha:
                raise ValueError(f"Continuation bound a different initial artifact for {c['root_id']}")
        elif sha is not None:
            raise ValueError(f"Initial artifact hash without output for {c['root_id']}")
        row["initial_artifact_sha256"] = sha
        row["initial"] = {"calls": int(bool(init.get("attempted"))), "prompt_tokens": init.get("prompt_tokens"),
                          "completion_tokens": init.get("completion_tokens")}
        row["arms"]["STOP"] = [{"replicate": 0, "output": text, "output_sha256": init.get("output_sha256"),
                                "missing_reason": None if text is not None else (init.get("missing_reason") or "initial_output_unavailable"),
                                "calls": 0, "prompt_tokens": 0, "completion_tokens": 0}]
        if set(c["arms"]) != set(CONTINUATION_ARMS):
            raise ValueError(f"Missing assigned continuation arm for {c['root_id']}")
        for arm in CONTINUATION_ARMS:
            recs = []
            for r in c["arms"][arm]:
                out = _checked(r)
                recs.append({"replicate": r["replicate"], "output": out, "output_sha256": r.get("output_sha256"),
                             "missing_reason": None if out is not None else (r.get("missing_reason") or "unavailable_output"),
                             "calls": int(bool(r.get("attempted"))), "prompt_tokens": r.get("prompt_tokens"),
                             "completion_tokens": r.get("completion_tokens")})
            row["arms"][arm] = recs
        view.append(row)
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "roots.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in view))
    manifest = {"arm_set": "diagnostic-v1", "arms": list(STUDY_ARMS), "grade_py_blockers": list(GRADE_PY_BLOCKERS),
                "sources": {"initial_completion_sha256": file_sha(initial_dir / "completion.json"),
                            "initial_roots_sha256": file_sha(initial_dir / "roots.jsonl"),
                            "continue_completion_sha256": file_sha(continue_dir / "completion.json"),
                            "continue_roots_sha256": file_sha(continue_dir / "roots.jsonl")},
                "roots_sha256": file_sha(out_dir / "roots.jsonl")}
    (out_dir / "view_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return view


def load_view(view_dir):
    view_dir = Path(view_dir)
    manifest = json.loads((view_dir / "view_manifest.json").read_text())
    if file_sha(view_dir / "roots.jsonl") != manifest["roots_sha256"]:
        raise ValueError("Grading view checksum mismatch")
    return _rows(view_dir / "roots.jsonl")


def grade_study(view, specs, runner, *, attestation_path=None, fake_runner_for_tests=False, max_executions=200,
                max_seconds=240, clock=time.monotonic):
    """Mirror of grade.grade_collection's per-artifact logic over a study view (list of rows or a view dir).

    `runner` is required and injected (tests pass a fake; never defaulted to sandbox.run_program here). As in
    grade.grade_collection, any real grading requires a passing, current containment attestation; only an
    explicitly declared fake runner (unit tests) may skip it, and that is recorded on every grade row."""
    from experiments.landmark import grade  # local: grade imports the sandbox module (source only)
    if runner is None:
        raise ValueError("An explicit runner is required")
    if not fake_runner_for_tests:
        if attestation_path is None:
            raise ValueError("Containment attestation required")
        grade.verify_attestation(attestation_path)
    if type(max_executions) is not int or not 1 <= max_executions <= 200 or not 0 < max_seconds <= 240:
        raise ValueError("Grading budget exceeds bounded adapter limits")
    rows = load_view(view) if isinstance(view, (str, Path)) else view
    for row in rows:
        for arm, artifacts in row["arms"].items():
            if arm not in STUDY_ARMS:
                raise ValueError(f"Unknown arm {arm!r}")
            for artifact in artifacts:
                _checked(artifact)
    contract_sha = digest(grade.contract(specs))
    by_root = {s["root_id"]: s for s in specs}
    started, count, executions, cache, grades = clock(), 0, [], {}, []

    def bounded_evaluate(spec, code, kind):
        nonlocal count
        if count >= max_executions or clock() - started + 2 > max_seconds:
            return {"outcome": None, "reason": "grading_budget_exhausted", "sandbox_executed": False}
        result = grade.evaluate(spec, code, runner)
        count += int(result["sandbox_executed"])
        executions.append({"root_id": spec["root_id"], "kind": kind, "code_sha256": digest(code), **result})
        return result

    for root in rows:
        if root["excluded"]:
            continue
        spec = by_root.get(root["root_id"])
        reference = controls = None
        if spec is not None:
            reference = bounded_evaluate(spec, spec["reference_code"], "reference")
            if reference["outcome"] == 1:
                controls = [bounded_evaluate(spec, c["code"], "negative_control") for c in spec["negative_controls"]]
        for arm in STUDY_ARMS:
            for artifact in root["arms"].get(arm, []):
                value, reason, cost = None, artifact["missing_reason"], {"executor_starts": 0, "executor_seconds": 0.0}
                if artifact["output"] is not None:
                    if spec is None:
                        reason, cost = "private_spec_missing", {"executor_starts": None, "executor_seconds": None}
                    elif reference["outcome"] != 1:
                        reason = "reference_validation_failed_or_unavailable"
                    elif not all(c["outcome"] == 0 and c["sandbox_executed"] for c in controls):
                        reason = "negative_control_validation_failed_or_unavailable"
                    else:
                        key = (root["root_id"], artifact["output_sha256"])
                        if key not in cache:
                            try:
                                result = bounded_evaluate(spec, grade.extract_code(artifact["output"]), "candidate")
                            except ValueError as exc:
                                result = {"outcome": 0, "reason": "unparseable_output", "details": str(exc), "sandbox_executed": False}
                            cache[key] = result
                            cost = {"executor_starts": int(bool(result.get("sandbox_executed"))),
                                    "executor_seconds": result.get("run", {}).get("seconds", 0.0)}
                        value = cache[key]["outcome"]
                        reason = cache[key]["reason"] if value is None else None
                grades.append({"root_id": root["root_id"], "arm": arm, "replicate": artifact["replicate"],
                               "output_sha256": artifact["output_sha256"], "outcome": value,
                               "missing_reason": reason or ("unavailable_output" if value is None else None),
                               "grader_id": "landmark-private-tests-v1:study:" + contract_sha[:12],
                               "grading_contract_sha256": contract_sha, **cost})
    return {"grades": grades, "executions": executions, "sandbox_executions": count, "model_calls": 0,
            "containment_gate": "fake_runner_for_tests_no_execution" if fake_runner_for_tests else "attestation_verified",
            "missing_grade_rows": sum(g["outcome"] is None for g in grades), "contract_sha256": contract_sha}


def to_analysis_input(view, grades, diagnostics=None, diagnostic_costs=None):
    """analyze_diagnostic.analyze(roots, diagnostics) input. Missing grades stay None with a reason."""
    rows = load_view(view) if isinstance(view, (str, Path)) else view
    diagnostics, diagnostic_costs = dict(diagnostics or {}), diagnostic_costs or {}
    by_key = {}
    for g in grades:
        key = (g["root_id"], g["arm"], g["replicate"])
        if key in by_key:
            raise ValueError(f"Duplicate grade {key}")
        by_key[key] = g
    out, used, missing = [], set(), {}
    for row in rows:
        if row["excluded"]:
            continue
        d = diagnostic_costs.get(row["root_id"], {})
        r = {"root_id": row["root_id"], "family_id": row.get("family_id"),
             "initial_artifact_sha256": row.get("initial_artifact_sha256"), "initial": dict(row["initial"]),
             "diagnostic_cost": {"executor_starts": d.get("executor_starts"), "executor_seconds": d.get("executor_seconds")},
             "arms": {}}
        for arm in STUDY_ARMS:
            recs = []
            for a in row["arms"].get(arm, []):
                key = (row["root_id"], arm, a["replicate"])
                g = by_key.get(key)
                if g is not None:
                    used.add(key)
                    if g["output_sha256"] != a["output_sha256"]:
                        raise ValueError(f"Grade does not match collected artifact {key}")
                grade_value = None if g is None else g["outcome"]
                reason = "grade_row_missing" if g is None else g["missing_reason"]
                if grade_value is not None:
                    reason = None
                else:
                    missing[reason] = missing.get(reason, 0) + 1
                recs.append({"replicate": a["replicate"], "grade": grade_value, "missing_reason": reason,
                             "calls": a.get("calls"), "prompt_tokens": a.get("prompt_tokens"),
                             "completion_tokens": a.get("completion_tokens"),
                             "executor_starts": None if g is None else g.get("executor_starts"),
                             "executor_seconds": None if g is None else g.get("executor_seconds")})
            r["arms"][arm] = recs
        out.append(r)
    if set(by_key) - used:
        raise ValueError("Grade for an unassigned artifact")
    return {"roots": out, "diagnostics": {k: v for k, v in diagnostics.items() if k in {r["root_id"] for r in out}},
            "missing_grades": missing}
