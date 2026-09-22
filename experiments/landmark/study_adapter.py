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
grade_study keeps grade_collection's containment gate (grade.verify_attestation; only a declared fake test
runner skips it) and, in place of blockers 1-3, restores the J7 protections on BOTH fake and real paths:
grade.validate_specs against the frozen public tasks file (bytes sha256-verified before use), an expected
frozen grading-contract digest, an expected frozen config digest (the plan is derived only from that config), both phase directories' completion.json checksums recomputed, the view
rebuilt from the phase directories and compared, exact assignment coverage against the frozen plan, and
verified source hashes of this adapter and every grading dependency (grading_source_hashes() freezes them).
Grade rows carry grader_id "landmark-private-tests-v1:study:<sha12>".
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from experiments.landmark.collect import digest, file_sha  # noqa: E402

STUDY_ARMS = ("STOP", "N0", "S0", "N1", "S1", "R1")
MAX_PRIVATE_STARTS, MAX_GRADING_SECONDS, DEFAULT_GRADING_SECONDS = 200, 600, 240
CONTINUATION_ARMS = STUDY_ARMS[1:]
GRADING_SOURCES = ("experiments/landmark/study_adapter.py", "experiments/landmark/grade.py",
                   "experiments/landmark/sandbox.py", "experiments/common/integrity.py",
                   "experiments/landmark/collect.py", "experiments/landmark/diagnostic.py",
                   "experiments/landmark/collect_diagnostic.py", "experiments/landmark/analyze.py")
GRADE_PY_BLOCKERS = (
    "analyze.analyze(run_dir): set(row['arms']) must equal {'stop', *collect.ARMS}; STOP,N0,S0,N1,S1,R1 unrepresentable",
    "manifest['config']['grading_contract_sha256'] must equal digest(grade.contract(specs)); diagnostic-v1 config does not freeze it",
    "analyze.analyze(run_dir): single manifest/completion/assignment_table for one run_dir; the study has two phase directories",
)


def _rows(path):
    return [_strict(x) for x in Path(path).read_bytes().decode("utf-8").splitlines() if x.strip()]


def _bytes_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _checked(rec):
    out = rec.get("output")
    if rec.get("output_sha256") != (None if out is None else digest(out)):
        raise ValueError("Stored artifact hash does not bind its output bytes")
    return out


def _strict(data):
    from experiments.landmark import diagnostic
    return diagnostic.strict_json_loads(data)


def grading_source_hashes():
    """Current {relative_path: sha256} of this adapter and every grading dependency, for freezing."""
    return {rel: file_sha(ROOT / rel) for rel in GRADING_SOURCES}


def verify_source_hashes(expected):
    if not isinstance(expected, dict) or set(expected) != set(GRADING_SOURCES):
        raise ValueError("Expected source hashes must cover exactly the grading sources")
    current = grading_source_hashes()
    bad = sorted(k for k in GRADING_SOURCES if expected[k] != current[k])
    if bad:
        raise ValueError(f"Grading source hash mismatch: {bad}")


def load_frozen_tasks(path, expected_sha256):
    data = Path(path).read_bytes()
    if not isinstance(expected_sha256, str) or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("Frozen public tasks bytes do not match expected sha256")
    return [_strict(x) for x in data.decode("utf-8").splitlines() if x.strip()]


def verify_phase_dir(phase_dir):
    phase_dir = Path(phase_dir)
    completion = _strict((phase_dir / "completion.json").read_bytes())
    sums = completion.get("checksums")
    if not isinstance(sums, dict) or not {"manifest.json", "roots.jsonl"} <= set(sums):
        raise ValueError(f"completion.json checksums incomplete in {phase_dir}")
    listed = set(sums)
    present = {p.relative_to(phase_dir).as_posix() for p in phase_dir.glob("artifacts/*.txt")}
    present |= {p.name for p in phase_dir.glob("*.json*") if p.name != "completion.json"}
    if present != listed:
        raise ValueError(f"completion.json checksums do not list exactly the phase files in {phase_dir}")
    for rel, sha in sums.items():
        if Path(rel).is_absolute() or ".." in Path(rel).parts or not (phase_dir / rel).is_file() \
                or file_sha(phase_dir / rel) != sha:
            raise ValueError(f"completion.json checksum mismatch for {rel} in {phase_dir}")
    return _strict((phase_dir / "manifest.json").read_bytes())


def verify_coverage(rows, initial_dir, continue_dir, frozen_tasks, expected_config_sha256):
    """Exact (root_id, family_id, arm, replicate) coverage of the view against the frozen plan: the plan is
    derived only from a config whose digest equals the frozen expected_config_sha256 (from the freeze record)."""
    from experiments.landmark import collect_diagnostic as cd
    manifests = [verify_phase_dir(initial_dir), verify_phase_dir(continue_dir)]
    if not isinstance(expected_config_sha256, str) \
            or any(digest(m.get("config")) != expected_config_sha256 for m in manifests):
        raise ValueError("Phase manifest config does not match the frozen config digest")
    config = manifests[0]["config"]
    plan = cd.assignments(config, frozen_tasks)
    for m in manifests:
        if m["dataset_sha256"] != digest(frozen_tasks) or m["assignment_table"] != plan:
            raise ValueError("Phase manifest does not bind the frozen tasks and plan")
    reps = config["branch_replicates"]
    expected, observed = set(), []
    for p in plan:
        if not p["excluded"]:
            expected.add((p["root_id"], p["family_id"], "STOP", 0))
            expected |= {(p["root_id"], p["family_id"], a, r) for a in CONTINUATION_ARMS for r in range(reps)}
    view_roots = [r["root_id"] for r in rows]
    if len(view_roots) != len(set(view_roots)) or set(view_roots) != {p["root_id"] for p in plan} \
            or {r["root_id"] for r in rows if r["excluded"]} != {p["root_id"] for p in plan if p["excluded"]}:
        raise ValueError("View roots or exclusions do not match the frozen plan")
    for row in rows:
        if row["excluded"] and row["arms"]:
            raise ValueError(f"Excluded root carries artifacts {row['root_id']}")
        for arm, artifacts in row["arms"].items():
            if any(type(a["replicate"]) is not int for a in artifacts):  # True == 1 must not pass coverage
                raise ValueError(f"Replicate must be an int for {row['root_id']} {arm}")
            observed += [(row["root_id"], row.get("family_id"), arm, a["replicate"]) for a in artifacts]
    if len(observed) != len(set(observed)):
        raise ValueError("Duplicate assignment in view")
    if set(observed) != expected:
        raise ValueError(f"Assignment coverage mismatch: missing={len(expected - set(observed))} "
                         f"extra={len(set(observed) - expected)}")


def to_grading_view(initial_dir, continue_dir, out_dir):
    """Write out_dir/roots.jsonl (grade.py row layout, arms STOP..R1) and out_dir/view_manifest.json."""
    view = build_view(initial_dir, continue_dir)
    _write_view(view, Path(initial_dir), Path(continue_dir), Path(out_dir))
    return view


def build_view(initial_dir, continue_dir):
    """The grading view rows, rebuilt purely from the two phase directories (no writes)."""
    initial_dir, continue_dir = Path(initial_dir), Path(continue_dir)
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
            rel = a.get("artifact")
            sums = _strict((initial_dir / "completion.json").read_bytes()).get("checksums") or {}
            if not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts or rel not in sums:
                raise ValueError(f"Initial artifact path not a checksummed file of the phase dir for {c['root_id']}")
            stored = (initial_dir / rel).read_bytes()
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
    return view


def _write_view(view, initial_dir, continue_dir, out_dir):
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "roots.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in view))
    manifest = {"arm_set": "diagnostic-v1", "arms": list(STUDY_ARMS), "grade_py_blockers": list(GRADE_PY_BLOCKERS),
                "sources": {"initial_completion_sha256": file_sha(initial_dir / "completion.json"),
                            "initial_roots_sha256": file_sha(initial_dir / "roots.jsonl"),
                            "continue_completion_sha256": file_sha(continue_dir / "completion.json"),
                            "continue_roots_sha256": file_sha(continue_dir / "roots.jsonl")},
                "roots_sha256": file_sha(out_dir / "roots.jsonl")}
    cman = continue_dir / "manifest.json"  # the diagnostics digest the continue phase actually bound (MRL-12)
    manifest["continue_diagnostics_sha256"] = _strict(cman.read_bytes()).get("diagnostics_sha256") if cman.exists() else None
    (out_dir / "view_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def load_view(view_dir):
    view_dir = Path(view_dir)
    manifest = _strict((view_dir / "view_manifest.json").read_bytes())
    if file_sha(view_dir / "roots.jsonl") != manifest["roots_sha256"]:
        raise ValueError("Grading view checksum mismatch")
    return _rows(view_dir / "roots.jsonl")


def grade_study(view, specs, runner, *, frozen_tasks_path=None, frozen_tasks_sha256=None,
                expected_contract_sha256=None, initial_dir=None, continue_dir=None, expected_source_hashes=None,
                expected_config_sha256=None,
                attestation_path=None, fake_runner_for_tests=False, max_executions=200,
                max_seconds=240, clock=time.monotonic, max_seconds_cap=240):
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
    # The 240 s cap is raised only when a committed release manifest's grading_limits says so (cmd_grade passes
    # max_seconds_cap=grading_seconds), and never above MAX_GRADING_SECONDS; never more than 200 private starts.
    if type(max_seconds_cap) not in (int, float) or not 0 < max_seconds_cap <= MAX_GRADING_SECONDS:
        raise ValueError("Grading budget exceeds bounded adapter limits")
    if type(max_executions) is not int or not 1 <= max_executions <= MAX_PRIVATE_STARTS \
            or type(max_seconds) not in (int, float) or not 0 < max_seconds <= max_seconds_cap:
        raise ValueError("Grading budget exceeds bounded adapter limits")
    # J7 protections: run on fake and real paths alike (only the attestation above is fake-exempt).
    if None in (frozen_tasks_path, frozen_tasks_sha256, expected_contract_sha256, initial_dir, continue_dir,
                expected_source_hashes, expected_config_sha256):
        raise ValueError("Frozen tasks, contract and config digests, phase directories and source hashes are required")
    verify_source_hashes(expected_source_hashes)
    frozen_tasks = load_frozen_tasks(frozen_tasks_path, frozen_tasks_sha256)
    grade.validate_specs(frozen_tasks, specs)
    contract_sha = digest(grade.contract(specs))
    if contract_sha != expected_contract_sha256:
        raise ValueError("Grading contract digest does not match the frozen digest")
    rows = load_view(view) if isinstance(view, (str, Path)) else view
    for row in rows:
        for arm, artifacts in row["arms"].items():
            if arm not in STUDY_ARMS:
                raise ValueError(f"Unknown arm {arm!r}")
            for artifact in artifacts:
                _checked(artifact)
    verify_coverage(rows, initial_dir, continue_dir, frozen_tasks, expected_config_sha256)
    if rows != build_view(initial_dir, continue_dir):
        raise ValueError("Grading view does not equal the view rebuilt from the verified phase directories")
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
        if diagnostic_costs and row["root_id"] not in diagnostic_costs:
            raise ValueError(f"No diagnostic cost entry for {row['root_id']}")
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


# ---------------------------------------------------------------- MRL-12 CLI (grade / analysis-input / view)
BINDING_KEYS = ("frozen_tasks_path", "frozen_tasks_sha256", "expected_contract_sha256", "expected_config_sha256",
                "expected_source_hashes")
PACKAGE_FILES = ("tasks.jsonl", "private_specs.jsonl", "config.json")
PLANNED_MAX_ARTIFACTS, PLANNED_MAX_RECHECKS = 77, 24  # v2 defaults (no grading_limits in the v2 manifest)
GRADING_LEDGER = "grading_attempts.jsonl"
COMMITTED_RELEASE_MANIFEST = "experiments/landmark/dev_release_v2/release_manifest.json"  # v2 (kept for callers)
COMMITTED_RELEASE_MANIFESTS = (COMMITTED_RELEASE_MANIFEST, "experiments/landmark/dev_release_v3/release_manifest.json")
GRADING_LIMIT_KEYS = frozenset({"n_roots", "artifact_starts", "recheck_starts", "max_private_starts", "grading_seconds"})
HEX64 = re.compile(r"[0-9a-f]{64}")


class GradingInterrupted(BaseException):
    """Raised through grade.evaluate (which swallows Exception) so a runner/ledger failure stops grading: no retries."""


def _unresolved(value):
    if isinstance(value, str):
        return value.startswith("UNRESOLVED:")
    if isinstance(value, dict):
        return any(_unresolved(k) or _unresolved(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_unresolved(v) for v in value)
    return False


def _resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_release_bindings(release_manifest, specs_path, data=None):
    """Every J7 binding from the release manifest's grading_bindings; refuses missing/UNRESOLVED/mismatched.

    `data` = the manifest bytes already verified against the HEAD blob; when given they are parsed instead of
    re-reading the path (no verify-then-reread gap)."""
    release_manifest = Path(release_manifest)
    m = _strict(release_manifest.read_bytes() if data is None else data)
    b = m.get("grading_bindings")
    if not isinstance(b, dict):
        raise ValueError("Release manifest has no grading_bindings")
    for key in BINDING_KEYS:
        if key not in b or b[key] in (None, "", {}):
            raise ValueError(f"Release manifest grading binding missing: {key}")
        if _unresolved(b[key]):
            raise ValueError(f"Release manifest grading binding unresolved: {key}")
    for key in ("frozen_tasks_sha256", "expected_contract_sha256", "expected_config_sha256"):
        if not isinstance(b[key], str) or not HEX64.fullmatch(b[key]):
            raise ValueError(f"Release manifest grading binding is not a sha256 hex digest: {key}")
    pkg = m.get("package")
    if not isinstance(pkg, dict) or any(not isinstance(pkg.get(f), str) or _unresolved(pkg.get(f)) for f in PACKAGE_FILES):
        raise ValueError("Release manifest package hashes missing or unresolved")
    here = release_manifest.parent
    for name in PACKAGE_FILES:
        if file_sha(here / name) != pkg[name]:
            raise ValueError(f"Release package file hash mismatch: {name}")
    tasks_path = _resolve(b["frozen_tasks_path"])
    if file_sha(tasks_path) != b["frozen_tasks_sha256"] or b["frozen_tasks_sha256"] != pkg["tasks.jsonl"]:
        raise ValueError("Frozen tasks binding does not match the release package")
    if file_sha(specs_path) != pkg["private_specs.jsonl"]:
        raise ValueError("Private specs do not match the release package hash")
    if digest(_strict((here / "config.json").read_bytes())) != b["expected_config_sha256"]:
        raise ValueError("Release config does not match expected_config_sha256")
    verify_source_hashes(b["expected_source_hashes"])
    return {**{k: b[k] for k in BINDING_KEYS}, "frozen_tasks_path": tasks_path}


def verify_committed_release(path, data=None):
    """sha256 of a committed release manifest at an ALLOWLISTED path (COMMITTED_RELEASE_MANIFESTS: dev_release_v2,
    dev_release_v3); refuses any other path, an untracked file, or one modified vs its git HEAD blob.

    data: the manifest bytes the caller read once and will parse; they (not a fresh re-read of the path) must
    equal the HEAD blob, so grading limits and the diagnostic schema come from exactly the verified bytes."""
    resolved = Path(path).resolve()
    rel = next((r for r in COMMITTED_RELEASE_MANIFESTS if (ROOT / r).resolve() == resolved), None)
    if rel is None:
        raise ValueError(f"release manifest must be one of the committed {list(COMMITTED_RELEASE_MANIFESTS)}")
    committed = (ROOT / rel).resolve()
    proc = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", f"HEAD:{rel}"],
                          capture_output=True, check=False)
    if proc.returncode != 0:
        raise ValueError("release manifest is not tracked at git HEAD")
    if proc.stdout != (committed.read_bytes() if data is None else bytes(data)):
        raise ValueError("release manifest differs from its git HEAD blob")
    return hashlib.sha256(proc.stdout).hexdigest()


def _int(v):
    return type(v) is int


def _manifest_bytes(release_manifest):
    """Already-verified manifest bytes pass through unchanged; a path is read."""
    if isinstance(release_manifest, (bytes, bytearray)):
        return bytes(release_manifest)
    return Path(release_manifest).read_bytes()


def load_grading_limits(release_manifest, specs=None):
    """(artifact_starts, recheck_starts, grading_seconds, seconds_cap) from the manifest's grading_limits.

    Absent -> the v2 defaults (77, 24, 240 s, cap 240). Present -> strict: exactly GRADING_LIMIT_KEYS, ints,
    max_private_starts == artifact_starts + recheck_starts <= 200, 0 < grading_seconds <= 600, n_roots == len(specs).
    release_manifest: a path, or the exact bytes verify_committed_release checked (no re-read)."""
    m = _strict(_manifest_bytes(release_manifest))
    if "grading_limits" not in m:
        return {"artifact_starts": PLANNED_MAX_ARTIFACTS, "recheck_starts": PLANNED_MAX_RECHECKS,
                "grading_seconds": DEFAULT_GRADING_SECONDS, "seconds_cap": DEFAULT_GRADING_SECONDS, "source": "v2_default"}
    lim = m["grading_limits"]
    if not isinstance(lim, dict) or set(lim) != GRADING_LIMIT_KEYS or not all(_int(lim[k]) for k in GRADING_LIMIT_KEYS):
        raise ValueError(f"grading_limits must carry exactly int {sorted(GRADING_LIMIT_KEYS)}")
    a, r, mx, secs = lim["artifact_starts"], lim["recheck_starts"], lim["max_private_starts"], lim["grading_seconds"]
    if a < 1 or r < 0 or mx != a + r or mx > MAX_PRIVATE_STARTS:
        raise ValueError(f"grading_limits starts invalid: max_private_starts must equal artifact+recheck and be <= {MAX_PRIVATE_STARTS}")
    if not 0 < secs <= MAX_GRADING_SECONDS:
        raise ValueError(f"grading_limits grading_seconds must be in (0, {MAX_GRADING_SECONDS}]")
    if lim["n_roots"] < 1 or (specs is not None and lim["n_roots"] != len(specs)):
        raise ValueError("grading_limits n_roots does not equal the number of private specs")
    return {"artifact_starts": a, "recheck_starts": r, "grading_seconds": secs, "seconds_cap": secs,
            "source": "grading_limits"}


def manifest_diagnostic_schema(release_manifest):
    """The diagnostic schema a release declares (diagnostic_schema); absent -> v1 (the v2 release predates it)."""
    from experiments.landmark import diagnostic
    m = _strict(_manifest_bytes(release_manifest))
    schema = m.get("diagnostic_schema", diagnostic.SCHEMA)
    if schema not in _known_schemas():
        raise ValueError(f"Unknown diagnostic_schema {schema!r}")
    return schema


def _known_schemas():
    from experiments.landmark import diagnostic
    return {diagnostic.SCHEMA} | ({diagnostic.SCHEMA_V2} if isinstance(getattr(diagnostic, "SCHEMA_V2", None), str) else set())


def validate_phase_b_diagnostics(diagnostics, schema=None):
    """Every Phase B diagnostic record validated by diagnostic.validate_diagnostic under ONE schema: the release's
    (schema given) or the records' own schema_version (all records must agree). Returns the schema used."""
    from experiments.landmark import diagnostic
    if not isinstance(diagnostics, dict):
        raise ValueError("Phase B diagnostics must be a root_id -> diagnostic object")
    found = {d.get("schema_version") if isinstance(d, dict) else None for d in diagnostics.values()}
    if schema is None:
        if len(found) > 1:
            raise ValueError(f"Phase B diagnostics mix schemas {sorted(map(str, found))}")
        schema = next(iter(found), diagnostic.SCHEMA)
    if schema not in _known_schemas():
        raise ValueError(f"Unknown diagnostic schema {schema!r}")
    for root_id, d in diagnostics.items():
        if not isinstance(d, dict) or d.get("schema_version") != schema:
            raise ValueError(f"Diagnostic for {root_id} is not schema {schema}")
        if d.get("root_id") != root_id:
            raise ValueError(f"Diagnostic keyed {root_id} carries root_id {d.get('root_id')!r}")
        if schema == diagnostic.SCHEMA:
            diagnostic.validate_diagnostic(d)  # v1: behaviour unchanged
        else:
            diagnostic.validate_diagnostic(d, schema=schema)
    return schema


class _DurableLedger:
    def __init__(self, path):
        self.f = open(path, "x", encoding="utf-8")

    def write(self, rec):
        self.f.write(json.dumps(rec, sort_keys=True) + "\n")
        self.f.flush()
        os.fsync(self.f.fileno())

    def close(self):
        if not self.f.closed:
            self.f.close()


def _utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def ledgered_runner(runner, ledger, counter, clock=time.monotonic):
    """Start record BEFORE and result record (elapsed_seconds) AFTER each execution; failures stop grading."""
    def wrapped(program, **limits):
        try:
            ledger.write({"event": "start", "n": counter["starts"] + 1, "program_sha256": _bytes_sha(program), "utc": _utc()})
        except BaseException as e:
            raise GradingInterrupted(f"ledger start write failed: {type(e).__name__}: {e}") from e
        counter["starts"] += 1
        t0 = clock()
        try:
            run = runner(program, **limits)
        except BaseException as e:
            ledger.write({"event": "result", "n": counter["starts"], "elapsed_seconds": clock() - t0,
                          "runner_error": f"{type(e).__name__}: {e}", "utc": _utc()})
            raise GradingInterrupted(f"runner failed: {type(e).__name__}: {e}") from e
        elapsed = clock() - t0
        try:
            ledger.write({"event": "result", "n": counter["starts"], "elapsed_seconds": elapsed,
                          "returncode": run.get("returncode") if isinstance(run, dict) else None,
                          "timed_out": run.get("timed_out") if isinstance(run, dict) else None, "utc": _utc()})
        except BaseException as e:
            raise GradingInterrupted(f"ledger result write failed: {type(e).__name__}: {e}") from e
        counter["results"] += 1
        return run
    return wrapped


def _refuse(msg):
    raise SystemExit(f"refusing: {msg}")


def cmd_grade(a):
    if not a.real:
        _refuse("grading executes candidate programs; pass --real with a verified --attestation")
    for flag, value in vars(a).items():
        if isinstance(value, str) and value.startswith("UNRESOLVED:"):
            _refuse(f"--{flag.replace('_', '-')} is unresolved ({value})")
    from experiments.landmark import grade, sandbox  # lazy: nothing real is imported unless --real
    try:  # attestation FIRST: before any input or the output directory is touched
        before = file_sha(a.attestation)
        grade.verify_attestation(a.attestation)
    except Exception as e:
        _refuse(f"containment attestation not verified: {type(e).__name__}: {e}")
    if file_sha(a.attestation) != before:
        _refuse("attestation file changed during verification")
    out = Path(a.out)
    if out.exists():
        _refuse(f"output already exists (no uncharged rerun): {out}")
    try:
        release_bytes = Path(a.release_manifest).read_bytes()  # read once: verified, then parsed, from these bytes
        committed_release_sha = verify_committed_release(a.release_manifest, release_bytes)
        bindings = load_release_bindings(a.release_manifest, a.specs, data=release_bytes)
        specs = _rows(a.specs)
        limits = load_grading_limits(release_bytes, specs)
    except (ValueError, OSError, KeyError) as e:
        _refuse(f"release bindings: {type(e).__name__}: {e}")
    out.mkdir(parents=True, exist_ok=False)  # reservation: from here on every start is charged and recorded
    ledger = _DurableLedger(out / GRADING_LEDGER)
    counter = {"starts": 0, "results": 0}
    planned = limits["artifact_starts"] + limits["recheck_starts"]
    if planned > MAX_PRIVATE_STARTS:  # belt and braces: load_grading_limits already refuses this
        _refuse(f"planned private starts {planned} exceed {MAX_PRIVATE_STARTS}")
    try:
        ledger.write({"event": "reserved", "release_manifest_sha256": file_sha(a.release_manifest),
                      "committed_release_manifest_sha256": committed_release_sha,
                      "specs_sha256": file_sha(a.specs), "attestation_sha256": before, "planned_max_starts": planned,
                      "grading_limits": limits, "utc": _utc()})
        to_grading_view(a.initial_dir, a.continue_dir, out / "view")
        runner = ledgered_runner(sandbox.run_program, ledger, counter)
        t0 = time.monotonic()
        result = grade_study(out / "view", specs, runner, initial_dir=a.initial_dir, continue_dir=a.continue_dir,
                             attestation_path=a.attestation, max_executions=planned,
                             max_seconds=limits["grading_seconds"], max_seconds_cap=limits["seconds_cap"], **bindings)
        wall = time.monotonic() - t0
        if file_sha(a.attestation) != before:
            raise ValueError("attestation file changed during grading")
        with (out / "grades.jsonl").open("x", encoding="utf-8") as f:
            f.write("".join(json.dumps(g) + "\n" for g in result["grades"]))
        with (out / "private_execution_records.json").open("x", encoding="utf-8") as f:
            f.write(json.dumps(result["executions"], indent=2) + "\n")
        ledger.write({"event": "complete", "executor_starts": counter["starts"], "utc": _utc()})
        ledger.close()
        summary = {"actual_starts": counter["starts"], "actual_results": counter["results"],
                   "planned_max_starts": planned, "planned_max_artifacts": limits["artifact_starts"],
                   "planned_max_rechecks": limits["recheck_starts"], "grading_seconds": limits["grading_seconds"],
                   "grading_limits_source": limits["source"], "sandbox_executions": result["sandbox_executions"],
                   "grading_wall_seconds": wall, "grade_rows": len(result["grades"]),
                   "missing_grade_rows": result["missing_grade_rows"], "contract_sha256": result["contract_sha256"],
                   "containment_gate": result["containment_gate"], "attestation_sha256": before, "model_calls": 0,
                   "retries": 0, "ledger_sha256": file_sha(out / GRADING_LEDGER),
                   "checksums": {p: file_sha(out / p) for p in ("grades.jsonl", "private_execution_records.json",
                                                                "view/roots.jsonl", "view/view_manifest.json")}}
        with (out / "summary.json").open("x", encoding="utf-8") as f:
            f.write(json.dumps(summary, indent=2) + "\n")
        return summary
    except BaseException as e:
        try:
            ledger.write({"event": "incomplete", "error": f"{type(e).__name__}: {e}", "executor_starts": counter["starts"],
                          "utc": _utc()})
        finally:
            ledger.close()
            with (out / "INCOMPLETE").open("x", encoding="utf-8") as f:
                f.write(f"{type(e).__name__}: {e}\n")
        raise


def phase_b_costs(phase_b_dir, expected_diagnostics_sha256, expected_roots=None):
    """(diagnostics, {root_id: {executor_starts, executor_seconds}}) from a Phase B dir bound to the digest."""
    phase_b_dir = Path(phase_b_dir)
    raw = (phase_b_dir / "diagnostics.json").read_bytes()
    if not isinstance(expected_diagnostics_sha256, str) or hashlib.sha256(raw).hexdigest() != expected_diagnostics_sha256:
        raise ValueError("Phase B diagnostics bytes do not match the expected diagnostics sha256")
    manifest = _strict((phase_b_dir / "manifest.json").read_bytes())
    if manifest.get("diagnostics_sha256") != expected_diagnostics_sha256:
        raise ValueError("Phase B manifest does not bind the expected diagnostics sha256")
    costs = {}
    for r in manifest["roots"]:
        starts, secs = r.get("runner_invocations"), r.get("executor_seconds")
        if type(starts) is not int or starts < 0:
            raise ValueError(f"Invalid runner_invocations for {r.get('root_id')}")
        if secs is not None and (type(secs) not in (int, float) or secs < 0):
            raise ValueError(f"Invalid executor_seconds for {r.get('root_id')}")
        if r["root_id"] in costs:
            raise ValueError(f"Duplicate Phase B root {r['root_id']}")
        costs[r["root_id"]] = {"executor_starts": starts, "executor_seconds": None if secs is None else float(secs)}
    if expected_roots is not None and set(costs) != set(expected_roots):
        raise ValueError("Phase B manifest roots do not equal the view's diagnosed roots")
    return _strict(raw), costs


def cmd_analysis_input(a):
    out = Path(a.out)
    if out.exists():
        _refuse(f"output already exists: {out}")
    schema, release_sha = None, None
    if getattr(a, "release_manifest", None) is not None:  # optional: the release fixes the diagnostic schema
        release_bytes = Path(a.release_manifest).read_bytes()  # read once: verified, then parsed, from these bytes
        release_sha = verify_committed_release(a.release_manifest, release_bytes)
        schema = manifest_diagnostic_schema(release_bytes)
    vman = _strict((Path(a.view) / "view_manifest.json").read_bytes())
    bound = vman.get("continue_diagnostics_sha256")
    if not isinstance(bound, str) or not HEX64.fullmatch(bound) or bound != a.expected_diagnostics_sha256:
        raise ValueError("Expected diagnostics sha256 is not the digest the continue phase bound")
    rows = load_view(a.view)
    live = [r for r in rows if not r["excluded"]]
    diagnosed = {r["root_id"] for r in live if r.get("initial_artifact_sha256") is not None}
    diagnostics, costs = phase_b_costs(a.phase_b_dir, a.expected_diagnostics_sha256, diagnosed)
    schema = validate_phase_b_diagnostics(diagnostics, schema)
    for r in live:  # no initial artifact -> no diagnostic could run: zero starts is known, never None
        if r["root_id"] not in diagnosed:
            costs[r["root_id"]] = {"executor_starts": 0, "executor_seconds": 0.0}
    data = to_analysis_input(a.view, _rows(a.grades), diagnostics, costs)
    data["sources"] = {"grades_sha256": file_sha(a.grades), "phase_b_manifest_sha256": file_sha(Path(a.phase_b_dir) / "manifest.json"),
                       "diagnostics_sha256": a.expected_diagnostics_sha256,
                       "view_roots_sha256": file_sha(Path(a.view) / "roots.jsonl"),
                       "diagnostic_schema": schema, "committed_release_manifest_sha256": release_sha}
    with out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2) + "\n")
    return data


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="python -m experiments.landmark.study_adapter")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grade")
    for flag in ("--release-manifest", "--specs", "--initial-dir", "--continue-dir", "--out", "--attestation"):
        g.add_argument(flag, required=True)
    g.add_argument("--real", action="store_true")
    n = sub.add_parser("analysis-input")
    for flag in ("--view", "--grades", "--phase-b-dir", "--expected-diagnostics-sha256", "--out"):
        n.add_argument(flag, required=True)
    n.add_argument("--release-manifest", default=None, help="optional allowlisted committed release manifest; "
                   "its diagnostic_schema (default v1) is enforced on every Phase B diagnostic")
    v = sub.add_parser("view")
    for flag in ("--initial-dir", "--continue-dir", "--out"):
        v.add_argument(flag, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "grade":
        return cmd_grade(a)
    if a.cmd == "analysis-input":
        return cmd_analysis_input(a)
    if Path(a.out).exists():
        _refuse(f"output already exists: {a.out}")
    return to_grading_view(a.initial_dir, a.continue_dir, a.out)


if __name__ == "__main__":
    main(sys.argv[1:])
