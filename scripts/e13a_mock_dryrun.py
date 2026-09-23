#!/usr/bin/env python3
"""MOCK/TRANSPORT-ONLY end-to-end demonstration of the E13a two-arm path. NOT evidence about any arm.

Evidence class: mock_transport_only_no_receiver_no_candidate_execution. Nothing here calls a receiver, a
llama-server, a benchmark program, a candidate answer, a reference solution or a sandbox: the receiver is a
deterministic canned-text adapter and the private executor is a deterministic stub. Every outcome printed is
fabricated by that stub and may never be read as an E13a result.

What it demonstrates, reusing E12's instruments rather than reimplementing them:
  1. request construction  - checkpoints derived from the FROZEN PUBLIC DIAGNOSTICS ONLY (B/diagnostics.json
     case statuses; private grades are never read), messages rebuilt with collect.initial_messages (FRESH) and
     diagnostic.render_arms(...)["R1"] (R1) from E12's checksum-verified initial artifact bytes and frozen
     diagnostic, then checked byte-for-byte against E12's recorded request messages;
  2. root-balanced scheduling with inclusion probability 1 for every root-arm-replicate, and the noncolliding
     seed plan (R1 replicates 2..7, FRESH 0..5, seeds from collect.seeded), asserted against every seed E12
     used at that root;
  3. a mock collection pass (60 attempts) with the real collector's manifest/completion/checksum discipline;
  4. a mock grading pass over 60 artifact starts + 10 recheck starts that exercises the real per-artifact
     bookkeeping (grade.evaluate, grade.extract_code, the output-hash cache, reference and negative-control
     rechecks, study_adapter.ledgered_runner's durable start/result ledger) with the executor stubbed, keeping
     unavailable outcomes and format/extraction failures as unknown/failure with a reason, never zero-filled;
  5. handing the mock grades to the analysis path (scripts/e13a_analyze.py when it exists; otherwise the grades
     file is written and the dependency is recorded in the report).

Stage limits come from experiments/landmark/e13a_stage.json (a NEW file for this stage, read through
study_adapter.load_grading_limits). No frozen package, no E12 result and no release manifest is touched.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect  # noqa: E402
from experiments.landmark import collect_diagnostic as cd  # noqa: E402
from experiments.landmark import grade  # noqa: E402
from experiments.landmark import study_adapter as sa  # noqa: E402

RUN = ROOT / "results/e12_dev_v3_20260922T030255Z"
PKG = ROOT / "experiments/landmark/dev_release_v3"
STAGE = ROOT / "experiments/landmark/e13a_stage.json"
SPECS = PKG / "private_specs.jsonl"
ANALYZER = ROOT / "scripts/e13a_analyze.py"
RESULTS_DIR = ROOT / "results"

ARM_SET = "e13a-two-arm"
ARMS = ("R1", "FRESH")
EVIDENCE = "mock_transport_only_no_receiver_no_candidate_execution"
MOCK_BANNER = "MOCK/TRANSPORT-ONLY: no receiver call, no candidate execution; outcomes are canned, not measured"
ORDER_LABEL = "order:" + ARM_SET
# Canned candidate shapes. The stub executor reads the marker; nothing is ever run.
GOOD, BAD, UNAVAIL = "mock-pass", "mock-fail", "mock-unavailable"


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def _strict(raw):
    return cd.diagnostic_module().strict_json_loads(raw)


# ------------------------------------------------------------------ stage bindings (new file, not a release)
def load_stage(path=STAGE, specs=None):
    """The E13a stage bindings plus its bookkeeping limits, read through study_adapter.load_grading_limits.

    Absent grading_limits are refused rather than silently defaulted to the v2 (77, 24) release numbers."""
    raw = Path(path).read_bytes()
    stage = _strict(raw)
    for key in ("stage", "arm_set", "arms", "roots", "grading_limits", "gating", "evidence_class"):
        if key not in stage:
            raise ValueError(f"E13a stage bindings missing {key}")
    if stage["arm_set"] != ARM_SET or set(stage["arms"]) != set(ARMS):
        raise ValueError(f"E13a stage bindings declare a different arm set: {stage['arm_set']} {sorted(stage['arms'])}")
    if stage["gating"].get("private_grades_are_an_input") is not False:
        raise ValueError("E13a gating must declare that private grades are not an input")
    limits = sa.load_grading_limits(raw, specs)
    if limits["source"] != "grading_limits":
        raise ValueError("E13a stage bindings must declare grading_limits explicitly")
    return stage, limits, hashlib.sha256(raw).hexdigest()


# ------------------------------------------------------------------ 1. request construction
def public_fail_checkpoints(diagnostics):
    """Checkpoints from the FROZEN PUBLIC DIAGNOSTICS ONLY: any public case whose status is not "pass".

    No private grade, private spec or private execution record is read here or anywhere upstream of dispatch."""
    out = []
    for root_id in sorted(diagnostics):
        cases = diagnostics[root_id]["cases"]
        if not cases:
            raise ValueError(f"public diagnostic for {root_id} has no cases")
        if any(c["status"] != "pass" for c in cases):
            out.append(root_id)
    return out


def build_requests(run=RUN, pkg=PKG, stage_path=STAGE):
    """Per-root R1/FRESH message lists, provably the bytes E12 sent, plus the noncolliding seed plan."""
    config = _strict((pkg / "config.json").read_bytes())
    tasks = _jsonl(pkg / "tasks.jsonl")
    plan = cd.assignments(config, tasks)
    initial_dir, _, rows = cd._load_initial(run / "A", config, tasks, plan)  # re-verifies A bytes and bindings
    sums = _strict((run / "ARTIFACT_SHA256SUMS.json").read_bytes())
    sums = sums.get("files", sums)
    raw = (run / "B/diagnostics.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != sums["B/diagnostics.json"]:
        raise ValueError("B/diagnostics.json differs from E12's artifact checksums")
    if hashlib.sha256((run / "C/calls.jsonl").read_bytes()).hexdigest() != sums["C/calls.jsonl"]:
        raise ValueError("C/calls.jsonl differs from E12's artifact checksums")
    dm = cd.diagnostic_module()
    diagnostics = _strict(raw)
    checkpoints = public_fail_checkpoints(diagnostics)
    specs = [s for s in _jsonl(SPECS) if s["root_id"] in set(checkpoints)]
    stage, limits, stage_sha = load_stage(stage_path, specs)
    if checkpoints != sorted(stage["roots"]):
        raise ValueError(f"public-diagnostic checkpoints {checkpoints} differ from the stage bindings {sorted(stage['roots'])}")
    calls = _jsonl(run / "C/calls.jsonl")
    by_task = {t["root_id"]: t for t in tasks}
    seeds_by_root = {p["root_id"]: p["seeds"] for p in plan}
    out_roots, checks = [], []
    for root_id in [p["root_id"] for p in plan if p["root_id"] in set(checkpoints)]:
        row = rows[root_id]
        text = (initial_dir / row["artifact"]).read_bytes()
        if hashlib.sha256(text).hexdigest() != row["artifact_sha256"]:
            raise ValueError(f"initial artifact bytes changed for {root_id}")
        diag = diagnostics[root_id]
        if diag.get("initial_artifact_sha256") != row["artifact_sha256"]:
            raise ValueError(f"diagnostic for {root_id} is bound to a different initial artifact")
        base = collect.initial_messages(by_task[root_id])
        if collect.digest(base) != row["base_messages_sha256"] or base != row["initial"]["request"]["messages"]:
            raise ValueError(f"FRESH messages for {root_id} differ from E12's recorded initial request")
        r1 = dm.render_arms(base, text.decode("utf-8"), diag)["R1"]
        e12_r1 = [c["request"]["messages"] for c in calls if c["root_id"] == root_id and c["arm"] == "R1"]
        if len(e12_r1) != 2 or any(m != r1 for m in e12_r1):
            raise ValueError(f"R1 messages for {root_id} differ from E12's recorded R1 requests")
        if any(m["role"] == "assistant" for m in r1):
            raise ValueError(f"R1 messages for {root_id} still carry the previous answer")
        used = set(seeds_by_root[root_id].values())
        messages = {"R1": r1, "FRESH": base}
        requests = []
        for arm in ARMS:
            for replicate in stage["arms"][arm]:
                seed_key = f"{arm}:{replicate}"
                seed = collect.seeded(config, root_id, seed_key)
                if seed in used:
                    raise ValueError(f"seed for {root_id} {seed_key} repeats a seed E12 used")
                used.add(seed)
                requests.append({"arm": arm, "replicate": replicate, "seed_key": seed_key, "seed": seed,
                                 "messages_sha256": collect.digest(messages[arm]),
                                 "branch_inclusion_probability": 1.0})
        out_roots.append({"root_id": root_id, "family_id": by_task[root_id]["family_id"],
                          "initial_artifact_sha256": row["artifact_sha256"],
                          "base_messages_sha256": row["base_messages_sha256"],
                          "r1_messages_sha256": collect.digest(r1), "messages": messages, "requests": requests})
        checks.append({"root_id": root_id, "fresh_messages_equal_e12_initial_request": True,
                       "r1_messages_equal_both_e12_r1_requests": True, "r1_previous_answer_removed": True,
                       "new_seeds_disjoint_from_e12_seeds": True})
    return {"config": config, "tasks": tasks, "specs": specs, "stage": stage, "limits": limits,
            "stage_sha256": stage_sha, "checkpoints": checkpoints, "roots": out_roots, "byte_checks": checks,
            "inputs": {rel: sums[rel] for rel in ("A/roots.jsonl", "B/diagnostics.json", "C/calls.jsonl") if rel in sums},
            "package_config_sha256": file_sha(pkg / "config.json"), "gating_source": "B/diagnostics.json case statuses",
            "private_inputs_used_for_gating": []}


# ------------------------------------------------------------------ 2. root-balanced scheduling
def schedule(plan):
    """Root-balanced order: each block of len(roots) holds every root exactly once; within a root the 12
    arm-replicate cells are shuffled with a seed derived from collect.seeded. Order is scheduling only."""
    config, roots = plan["config"], plan["roots"]
    per_root = {}
    for r in roots:
        cells = [{"arm": q["arm"], "replicate": q["replicate"]} for q in r["requests"]]
        random.Random(collect.seeded(config, r["root_id"], ORDER_LABEL)).shuffle(cells)
        per_root[r["root_id"]] = cells
    n = len(next(iter(per_root.values())))
    if any(len(v) != n for v in per_root.values()):
        raise ValueError("roots do not carry the same number of cells; the schedule would not be root-balanced")
    order, ids = [], [r["root_id"] for r in roots]
    for slot in range(n):
        block = ids[slot % len(ids):] + ids[:slot % len(ids)]  # rotate so no root is always first
        for root_id in block:
            cell = per_root[root_id][slot]
            order.append({"index": len(order), "block": slot, "root_id": root_id, **cell,
                          "branch_inclusion_probability": 1.0, "order_role": "scheduling_not_assignment"})
    seen = {(o["root_id"], o["arm"], o["replicate"]) for o in order}
    if len(seen) != len(order) or len(order) != len(ids) * n:
        raise ValueError("schedule is not a permutation of the root-arm-replicate cells")
    for start in range(0, len(order), len(ids)):
        if sorted(o["root_id"] for o in order[start:start + len(ids)]) != sorted(ids):
            raise ValueError("schedule block is not root-balanced")
    return order


# ------------------------------------------------------------------ 3. mock collection
def canned_kind(root_id, arm, replicate, roots):
    """Deterministic canned shape per cell, including the two deliberate non-pass paths."""
    if (root_id, arm, replicate) == (roots[0], "R1", 2):
        return "ambiguous_fences"          # format/extraction failure at grading
    if (root_id, arm, replicate) == (roots[1], "FRESH", 0):
        return "empty_response"            # receiver-side missing output
    if (root_id, arm, replicate) == (roots[2], "R1", 3):
        return UNAVAIL                     # executor-unavailable at grading
    return GOOD if (replicate % 2 == 0) == (arm == "R1") else BAD


def canned_text(kind, entry_point):
    # The marker is a string literal, not a comment: grade.prepare_program re-unparses the code and drops comments.
    body = f"def {entry_point}(*args, **kwargs):\n    _mock_outcome = 'MOCKOUTCOME={kind}'\n    return None\n"
    if kind == "ambiguous_fences":
        return "```python\n" + body + "```\nalso:\n```\n" + body + "```\n"
    return "```python\n" + body + "```\n"


class MockAdapter:
    """Deterministic canned-text receiver. No HTTP, no server, no process: never a measurement."""

    def __init__(self, plan):
        self.entry = {s["root_id"]: s["entry_point"] for s in plan["specs"]}
        self.roots = [r["root_id"] for r in plan["roots"]]
        self.calls = 0

    def generate(self, payload, root_id, arm, replicate):
        self.calls += 1
        kind = canned_kind(root_id, arm, replicate, self.roots)
        if kind == "empty_response":
            return {"done": False, "message": {"content": ""}, "mock": True}
        text = canned_text(kind, self.entry[root_id])
        return {"done": True, "message": {"content": text}, "prompt_eval_count": 0, "eval_count": 0, "mock": True}


def mock_collect(plan, order, out_dir, adapter=None, clock=time.monotonic):
    """60 mock artifact records with the real collector's manifest/completion/checksum discipline."""
    out = Path(out_dir)
    if RESULTS_DIR.resolve() in out.resolve().parents or out.resolve() == RESULTS_DIR.resolve():
        raise ValueError("refusing to write a mock run inside results/ (E12 outputs are immutable)")
    out.mkdir(parents=True, exist_ok=False)
    (out / "artifacts").mkdir()
    adapter = adapter if adapter is not None else MockAdapter(plan)
    config = plan["config"]
    manifest = {"schema_version": config["schema_version"], "arm_set": ARM_SET, "stage": "E13a", "phase": "mock_continue",
                "evidence_type": "mock_transport_only", "evidence_class": EVIDENCE, "mock_only": True,
                "banner": MOCK_BANNER, "real_receiver": False, "receiver_calls_made": 0, "candidate_executions": 0,
                "freeze": {"resolved_commit": None, "status": "mock_not_frozen"},
                "config_sha256": collect.digest(config), "stage_sha256": plan["stage_sha256"],
                "inputs": plan["inputs"], "package_config_sha256": plan["package_config_sha256"],
                "gating": {"source": plan["gating_source"], "checkpoints": plan["checkpoints"],
                           "private_inputs_used_for_gating": plan["private_inputs_used_for_gating"]},
                "byte_checks": plan["byte_checks"], "schedule": order, "order_role": "scheduling_not_assignment",
                "design": "Both arms are collected for every root at every replicate; inclusion probability one. "
                          "Randomized execution order is scheduling, not treatment assignment.",
                "bindings": {r["root_id"]: {k: r[k] for k in ("initial_artifact_sha256", "base_messages_sha256",
                                                              "r1_messages_sha256")} for r in plan["roots"]},
                "seed_plan": {r["root_id"]: {q["seed_key"]: q["seed"] for q in r["requests"]} for r in plan["roots"]}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    by_root = {r["root_id"]: r for r in plan["roots"]}
    rows = {r["root_id"]: {"root_id": r["root_id"], "family_id": r["family_id"], "excluded": False,
                           "initial_artifact_sha256": r["initial_artifact_sha256"],
                           "branch_inclusion_probability": 1.0,
                           "arms": {a: [] for a in ARMS}} for r in plan["roots"]}
    started, attempted = clock(), 0
    for cell in order:
        root = by_root[cell["root_id"]]
        req = next(q for q in root["requests"] if (q["arm"], q["replicate"]) == (cell["arm"], cell["replicate"]))
        payload = {"model": config["model"], "messages": root["messages"][cell["arm"]], "stream": False,
                   "options": {**config["decoding"], "num_predict": config["max_tokens_per_call"], "seed": req["seed"]}}
        rec = {"phase": "mock_continue", "root_id": root["root_id"], "arm": cell["arm"], "replicate": cell["replicate"],
               "seed_key": req["seed_key"], "seed": req["seed"], "request_sha256": collect.digest(payload),
               "messages_sha256": collect.digest(payload["messages"]), "attempted": True, "mock": True,
               "output": None, "output_sha256": None, "artifact": None, "artifact_sha256": None,
               "missing_reason": None, "prompt_tokens": None, "completion_tokens": None, "seconds": 0.0}
        if req["messages_sha256"] != rec["messages_sha256"]:
            raise ValueError(f"dispatched messages differ from the checked plan for {root['root_id']} {req['seed_key']}")
        begin = clock()
        attempted += 1
        response = adapter.generate(payload, root["root_id"], cell["arm"], cell["replicate"])
        text = response.get("message", {}).get("content")
        if response.get("done") is not True or not isinstance(text, str) or not text.strip():
            rec["missing_reason"] = "mock_incomplete_or_empty_response"
        else:
            name = f"{root['root_id'].replace('/', '%2F')}__{cell['arm']}__{cell['replicate']}.txt"
            (out / "artifacts" / name).write_bytes(text.encode("utf-8"))
            rec.update(output=text, output_sha256=collect.digest(text), artifact=f"artifacts/{name}",
                       artifact_sha256=cd.text_sha(text), prompt_tokens=response.get("prompt_eval_count"),
                       completion_tokens=response.get("eval_count"))
        rec["seconds"] = clock() - begin
        rows[root["root_id"]]["arms"][cell["arm"]].append(rec)
        with (out / "calls.jsonl").open("a") as f:  # append-only, one line per attempt
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    for row in rows.values():
        for arm in ARMS:
            row["arms"][arm].sort(key=lambda r: r["replicate"])
        row["status"] = "outputs_complete" if all(r["output"] is not None for a in row["arms"].values() for r in a) \
            else "outputs_missing"
        with (out / "roots.jsonl").open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    completion = {"phase": "mock_continue", "arm_set": ARM_SET, "stage": "E13a", "evidence_type": "mock_transport_only",
                  "evidence_class": EVIDENCE, "mock_only": True, "banner": MOCK_BANNER, "real_receiver": False,
                  "receiver_calls_made": 0, "mock_adapter_calls": attempted, "candidate_executions": 0,
                  "paid_api_spend_usd": 0, "attempted_calls": attempted,
                  "planned_calls": len(order), "assigned_roots": len(rows), "excluded_roots": 0,
                  "outputs_collected": sum(r["output"] is not None for row in rows.values()
                                           for a in row["arms"].values() for r in a),
                  "outputs_missing": sum(r["output"] is None for row in rows.values()
                                         for a in row["arms"].values() for r in a),
                  "measured_prompt_tokens": None, "measured_completion_tokens": None,
                  "attempted_calls_with_unknown_usage": sum(r["prompt_tokens"] is None for row in rows.values()
                                                            for a in row["arms"].values() for r in a),
                  "phase_wall_seconds": clock() - started, "preflight_failure": None, "fatal_error": None,
                  "receiver_verification": {"status": "mock_transport_only_not_verified", "efficacy_interpretable": False,
                                            "reasons": ["mock adapter: no receiver was contacted"]}}
    completion["checksums"] = {p.relative_to(out).as_posix(): file_sha(p)
                               for p in sorted([*out.glob("*.json*"), *out.glob("artifacts/*.txt")])}
    (out / "completion.json").write_text(json.dumps(completion, indent=2, ensure_ascii=False) + "\n")
    (out / "MOCK_ONLY").write_text(MOCK_BANNER + "\n")
    return completion


# ------------------------------------------------------------------ 4. mock grading (real bookkeeping, stub executor)
def mock_view(collect_dir):
    """Grading-view rows for the E13a arms, rebuilt from the mock collection directory's bytes."""
    collect_dir = Path(collect_dir)
    completion = _strict((collect_dir / "completion.json").read_bytes())
    for rel, sha in completion["checksums"].items():
        if file_sha(collect_dir / rel) != sha:
            raise ValueError(f"mock collection file changed after completion: {rel}")
    view = []
    for row in _jsonl(collect_dir / "roots.jsonl"):
        out = {"root_id": row["root_id"], "family_id": row["family_id"], "excluded": row["excluded"], "arms": {}}
        for arm in ARMS:
            recs = []
            for r in row["arms"][arm]:
                text = r["output"]
                if text is not None:
                    stored = (collect_dir / r["artifact"]).read_bytes()
                    if hashlib.sha256(stored).hexdigest() != r["artifact_sha256"] or stored != text.encode("utf-8"):
                        raise ValueError(f"mock artifact bytes do not match for {row['root_id']} {arm}:{r['replicate']}")
                recs.append({"replicate": r["replicate"], "output": text, "output_sha256": r["output_sha256"],
                             "missing_reason": None if text is not None else (r["missing_reason"] or "unavailable_output")})
            out["arms"][arm] = sorted(recs, key=lambda x: x["replicate"])
        view.append(out)
    return view


def _canonical(code):
    """ast.unparse of the code, the form grade.prepare_program embeds in a program (static; nothing runs)."""
    return ast.unparse(ast.parse(code))


class StubExecutor:
    """Deterministic canned executor outcomes. Executes NOTHING: it reads the program text and answers.

    Candidate programs carry a MOCKOUTCOME marker; reference and negative-control programs are recognised by
    the frozen spec code they contain, so the reference/control recheck bookkeeping runs unchanged."""

    def __init__(self, specs):
        # grade.prepare_program re-unparses the code it embeds, so match on the same canonical form.
        self.reference = {_canonical(s["reference_code"]) for s in specs}
        self.controls = {_canonical(c["code"]) for s in specs for c in s["negative_controls"]}
        self.programs = []

    def __call__(self, program, **limits):
        self.programs.append(hashlib.sha256(program.encode()).hexdigest())
        start = grade.STARTED + program.split(grade.STARTED, 1)[1][:24] if grade.STARTED in program else ""
        sentinel = "__LANDMARK_PRIVATE_OK__" + program.split("__LANDMARK_PRIVATE_OK__")[-1][:24]
        if f"MOCKOUTCOME={UNAVAIL}" in program:  # grader-side unavailability, never a candidate failure
            return {"stdout": start + "\n", "stdout_tail": "", "timed_out": False, "returncode": 70,
                    "sandbox_kind": None, "passed": False, "executed": True, "seconds": 0.0, "mock": True}
        if f"MOCKOUTCOME={GOOD}" in program:
            ok = True
        elif f"MOCKOUTCOME={BAD}" in program:
            ok = False
        elif any(code in program for code in self.reference):
            ok = True
        elif any(code in program for code in self.controls):
            ok = False
        else:
            return {"stdout": "", "stdout_tail": "", "timed_out": False, "returncode": 71, "sandbox_kind": None,
                    "passed": False, "executed": False, "seconds": 0.0, "mock": True}
        return {"stdout": start + "\n" + (sentinel + "\n" if ok else ""), "stdout_tail": sentinel if ok else "AssertionError",
                "timed_out": False, "returncode": 0 if ok else 1, "sandbox_kind": "seatbelt", "passed": ok,
                "executed": True, "seconds": 0.0, "mock": True}


def mock_grade(plan, collect_dir, out_dir, executor=None, clock=time.monotonic):
    """grade_study's per-artifact bookkeeping over the E13a arms with the executor stubbed.

    Separate budgets: candidate starts <= limits["artifact_starts"], recheck starts <= limits["recheck_starts"].
    An exhausted budget, an unavailable executor and an extraction failure each keep their reason; none is zeroed."""
    out, limits, specs = Path(out_dir), plan["limits"], plan["specs"]
    if RESULTS_DIR.resolve() in out.resolve().parents or out.resolve() == RESULTS_DIR.resolve():
        raise ValueError("refusing to write mock grades inside results/ (E12 outputs are immutable)")
    tasks = [t for t in plan["tasks"] if t["root_id"] in {s["root_id"] for s in specs}]
    grade.validate_specs(tasks, specs)                       # real spec validation
    contract_sha = collect.digest(grade.contract(specs))     # real contract digest
    rows = mock_view(collect_dir)
    out.mkdir(parents=True, exist_ok=False)
    ledger = sa._DurableLedger(out / sa.GRADING_LEDGER)      # real durable start/result ledger
    counter = {"starts": 0, "results": 0}
    runner = sa.ledgered_runner(executor if executor is not None else StubExecutor(specs), ledger, counter, clock=clock)
    by_root = {s["root_id"]: s for s in specs}
    budget = {"candidate": limits["artifact_starts"], "recheck": limits["recheck_starts"]}
    used = {"candidate": 0, "recheck": 0}
    executions, cache, grades = [], {}, []
    ledger.write({"event": "reserved", "stage": "E13a", "arm_set": ARM_SET, "evidence_class": EVIDENCE,
                  "mock_only": True, "stage_sha256": plan["stage_sha256"], "grading_limits": limits,
                  "planned_max_starts": limits["artifact_starts"] + limits["recheck_starts"], "utc": sa._utc()})

    def bounded(spec, code, kind):
        pool = "candidate" if kind == "candidate" else "recheck"
        if used[pool] >= budget[pool]:
            return {"outcome": None, "reason": f"{pool}_start_budget_exhausted", "sandbox_executed": False}
        result = grade.evaluate(spec, code, runner)
        used[pool] += int(result["sandbox_executed"])
        executions.append({"root_id": spec["root_id"], "kind": kind, "code_sha256": collect.digest(code),
                           "outcome": result["outcome"], "reason": result["reason"],
                           "sandbox_executed": result["sandbox_executed"], "mock_executor": True})
        return result

    for row in rows:
        spec = by_root.get(row["root_id"])
        reference = bounded(spec, spec["reference_code"], "reference")
        controls = [bounded(spec, c["code"], "negative_control") for c in spec["negative_controls"]] \
            if reference["outcome"] == 1 else None
        for arm in ARMS:
            for artifact in row["arms"][arm]:
                value, reason, cost = None, artifact["missing_reason"], {"executor_starts": 0, "executor_seconds": 0.0}
                if artifact["output"] is not None:
                    if reference["outcome"] != 1:
                        reason = "reference_validation_failed_or_unavailable"
                    elif not all(c["outcome"] == 0 and c["sandbox_executed"] for c in controls):
                        reason = "negative_control_validation_failed_or_unavailable"
                    else:
                        key = (row["root_id"], artifact["output_sha256"])
                        if key not in cache:
                            try:
                                result = bounded(spec, grade.extract_code(artifact["output"]), "candidate")
                            except ValueError as exc:  # format/extraction failure: a reasoned failure, not a bare 0
                                result = {"outcome": 0, "reason": "unparseable_output", "details": str(exc),
                                          "sandbox_executed": False}
                                executions.append({"root_id": row["root_id"], "kind": "candidate",
                                                   "code_sha256": None, "outcome": 0, "reason": "unparseable_output",
                                                   "sandbox_executed": False, "mock_executor": True})
                            cache[key] = result
                            cost = {"executor_starts": int(bool(result.get("sandbox_executed"))),
                                    "executor_seconds": result.get("run", {}).get("seconds", 0.0)}
                        value = cache[key]["outcome"]
                        reason = cache[key]["reason"] if value is None else cache[key]["reason"]
                grades.append({"root_id": row["root_id"], "arm": arm, "replicate": artifact["replicate"],
                               "arm_set": ARM_SET, "output_sha256": artifact["output_sha256"], "outcome": value,
                               "reason": reason,
                               "missing_reason": (reason if value is None else None) or
                                                 ("unavailable_output" if value is None else None),
                               "grader_id": "landmark-private-tests-v1:e13a-mock:" + contract_sha[:12],
                               "grading_contract_sha256": contract_sha, "mock_executor": True, **cost})
    ledger.write({"event": "complete", "executor_starts": counter["starts"], "mock_only": True, "utc": sa._utc()})
    ledger.close()
    (out / "grades.jsonl").write_text("".join(json.dumps(g) + "\n" for g in grades))
    (out / "private_execution_records.json").write_text(json.dumps(executions, indent=2) + "\n")
    summary = {"stage": "E13a", "arm_set": ARM_SET, "evidence_class": EVIDENCE, "mock_only": True,
               "banner": MOCK_BANNER, "grader_version": grade.GRADER_VERSION, "contract_sha256": contract_sha,
               "stage_sha256": plan["stage_sha256"], "grading_limits": limits,
               "planned_max_artifacts": limits["artifact_starts"], "planned_max_rechecks": limits["recheck_starts"],
               "stub_executor_starts": counter["starts"], "stub_executor_results": counter["results"],
               "candidate_starts_used": used["candidate"], "recheck_starts_used": used["recheck"],
               "real_candidate_executions": 0, "real_sandbox_executions": 0, "model_calls": 0,
               "grade_rows": len(grades), "ones": sum(g["outcome"] == 1 for g in grades),
               "zeros": sum(g["outcome"] == 0 for g in grades),
               "unavailable_rows": sum(g["outcome"] is None for g in grades),
               "unavailable_reasons": sorted({g["reason"] for g in grades if g["outcome"] is None}),
               "failure_reasons": sorted({g["reason"] for g in grades if g["outcome"] == 0}),
               "ledger_sha256": file_sha(out / sa.GRADING_LEDGER)}
    summary["checksums"] = {p: file_sha(out / p) for p in ("grades.jsonl", "private_execution_records.json",
                                                           sa.GRADING_LEDGER)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "MOCK_ONLY").write_text(MOCK_BANNER + "\n")
    return {"summary": summary, "grades": grades, "executions": executions, "view": rows}


# ------------------------------------------------------------------ 5. analysis hand-off
def analysis_descriptor(plan):
    """The stage descriptor shape Deliverable A's analyzer reads: per-root request lists plus the contrast arms."""
    return {"stage": "E13a", "arm_set": ARM_SET, "arms": {a: sorted(plan["stage"]["arms"][a]) for a in ARMS},
            "contrast": {"treatment": "R1", "reference": "FRESH"},
            "roots": [{"root_id": r["root_id"],
                       "requests": [{k: q[k] for k in ("arm", "replicate", "seed_key", "seed", "messages_sha256")}
                                    for q in r["requests"]]} for r in plan["roots"]],
            "decoding": {**plan["config"]["decoding"], "num_predict": plan["config"]["max_tokens_per_call"]}}


def analyse(plan, graded, out_dir):
    """Hand the mock grades to Deliverable A's analyzer when it exists; otherwise report the dependency."""
    report = {"report_version": "e13a-mock-report-v1", "stage": "E13a", "arm_set": ARM_SET,
              "evidence_class": EVIDENCE, "mock_only": True, "banner": MOCK_BANNER,
              "grades_path": str(Path(out_dir) / "grades.jsonl"),
              "grading_contract_sha256": graded["summary"]["contract_sha256"],
              "stage_sha256": plan["stage_sha256"], "checkpoints": plan["checkpoints"],
              "interpretation": [*plan["stage"]["interpretation_rules"],
                                 "Mock/transport-only: these numbers are canned by a stub, not measured."]}
    per_arm = {a: {"n": 0, "ones": 0, "zeros": 0, "unavailable": 0} for a in ARMS}
    per_root = {r["root_id"]: {a: dict(per_arm[a]) for a in ARMS} for r in plan["roots"]}
    for g in graded["grades"]:
        for bucket in (per_arm[g["arm"]], per_root[g["root_id"]][g["arm"]]):
            bucket["n"] += 1
            bucket["ones" if g["outcome"] == 1 else "zeros" if g["outcome"] == 0 else "unavailable"] += 1
    report["per_arm"] = per_arm
    report["per_root"] = per_root
    if ANALYZER.exists():
        spec = importlib.util.spec_from_file_location("e13a_analyze", ANALYZER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        analyze, from_descriptor = getattr(module, "analyze", None), getattr(module, "plan_from_descriptor", None)
        if not callable(analyze) or not callable(from_descriptor):
            report["analysis_dependency"] = (f"{ANALYZER.name} exposes no analyze(grade_rows, plan) plus "
                                             "plan_from_descriptor(descriptor) pair; grades file written for it instead")
        else:
            try:
                report["e13a_analyze_report"] = analyze(graded["grades"], from_descriptor(analysis_descriptor(plan)))
                report["analysis_dependency"] = None
            except Exception as exc:  # the analyzer's input contract is Deliverable A's, not this script's
                report["analysis_dependency"] = (f"{ANALYZER.name}.analyze refused this call "
                                                 f"({type(exc).__name__}: {exc}); grades file written for it instead")
    else:
        report["analysis_dependency"] = (f"{ANALYZER.relative_to(ROOT).as_posix()} does not exist yet (Deliverable A); "
                                         "the mock grades file is written for it and the summary below is a placeholder")
    (Path(out_dir) / "mock_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def dryrun(out_dir, run=RUN, pkg=PKG, stage_path=STAGE, adapter=None, executor=None):
    out = Path(out_dir)
    if out.exists():
        raise SystemExit(f"Refusing to overwrite an existing output directory: {out}")
    plan = build_requests(run, pkg, stage_path)
    order = schedule(plan)
    completion = mock_collect(plan, order, out / "collect", adapter=adapter)
    graded = mock_grade(plan, out / "collect", out / "grade", executor=executor)
    report = analyse(plan, graded, out / "grade")
    (out / "MOCK_ONLY").write_text(MOCK_BANNER + "\n")
    return {"banner": MOCK_BANNER, "evidence_class": EVIDENCE, "checkpoints": plan["checkpoints"],
            "attempts": len(order), "byte_checks": plan["byte_checks"], "schedule_blocks": order[-1]["block"] + 1,
            "collection": completion, "grading": graded["summary"], "report": report}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="new directory for the mock run (never inside results/)")
    ap.add_argument("--run", type=Path, default=RUN)
    ap.add_argument("--package", type=Path, default=PKG)
    ap.add_argument("--stage", type=Path, default=STAGE)
    a = ap.parse_args(argv)
    result = dryrun(a.out, a.run, a.package, a.stage)
    print(MOCK_BANNER)
    print(json.dumps({k: result[k] for k in ("evidence_class", "checkpoints", "attempts", "schedule_blocks")}, indent=1))
    print(json.dumps(result["grading"], indent=1))
    print(json.dumps(result["report"], indent=1))
    return result


if __name__ == "__main__":
    main()
