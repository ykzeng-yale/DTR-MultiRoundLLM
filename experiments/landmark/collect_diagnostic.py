#!/usr/bin/env python3
"""Phased collector for the public-diagnostic development study (arm set diagnostic-v1); mock only.

Phase A ("initial"): one receiver call per root, seed key "initial"; writes the initial artifact bytes and
their SHA-256. Phase B (public executor, public_check.py) is NOT run here: this module never executes
candidate code. Phase C ("continue"): reads phase A's directory plus a diagnostics JSON file bound by the
SHA-256 of its exact bytes, renders N0/S0/N1/S1/R1 with diagnostic.render_arms, and dispatches
5 arms x branch_replicates with independent "<arm>:<replicate>" seeds.

Accounting mirrors collect.run: calls/completion tokens are reserved on dispatch and never refunded (the
continue phase inherits phase A's counts, so max_calls/max_completion_tokens/max_seconds bound the whole
study), every skipped call records a missing_reason, calls.jsonl is append-only, and a receiver drift,
contention or unverifiable check (before a phase, before a root, or between phases) stops FUTURE dispatch
only: outputs already collected are kept and the study is marked not interpretable for efficacy.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import random
import re
import time

try:
    from . import collect
except ImportError:  # run as a script or imported with experiments/landmark on sys.path (as the tests do)
    import collect

ARM_SET = "diagnostic-v1"
DIAG_ARMS = ("N0", "S0", "N1", "S1", "R1")
PHASES = ("initial", "continue")
# Real roots are "mbpp/52": "/" is allowed in the id and encoded as "%2F" in the artifact file name ("%" is not
# allowed in an id, so the encoding is injective and the file name never contains a path separator).
SAFE_ROOT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,127}")
HEX64 = re.compile(r"[0-9a-f]{64}")


def diagnostic_module():
    """Lazy: diagnostic.py is written concurrently and is needed only to render the continue phase."""
    try:
        return importlib.import_module(__package__ + ".diagnostic") if __package__ else importlib.import_module("diagnostic")
    except ImportError:
        return importlib.import_module("diagnostic")


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact_name(root_id):
    return root_id.replace("/", "%2F") + ".txt"


def text_sha(text):
    # Artifact identity = SHA-256 of the exact UTF-8 bytes written to artifacts/<artifact_name(root_id)> (what phase B
    # reads). Distinct from collect.digest(text), the JSON-encoded digest kept as output_sha256 in calls.jsonl.
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assignments(config, tasks):
    """Exclusions as collect.assignments; order is scheduling only (all 5 arms have inclusion probability 1)."""
    seen_roots = set(config["prior_seen_root_ids"])
    seen_families = set(config["prior_seen_family_ids"]) | {t["family_id"] for t in tasks if t["root_id"] in seen_roots}
    labels = ("initial", *(f"{a}:{r}" for a in DIAG_ARMS for r in range(config["branch_replicates"])))
    plan = []
    for task in tasks:
        if not SAFE_ROOT.fullmatch(task["root_id"]):
            raise ValueError(f"root_id is not a safe artifact file name: {task['root_id']!r}")
        order = [{"arm": a, "replicate": r} for a in DIAG_ARMS for r in range(config["branch_replicates"])]
        random.Random(collect.seeded(config, task["root_id"], "order:" + ARM_SET)).shuffle(order)
        excluded = task["root_id"] in seen_roots or task["family_id"] in seen_families
        plan.append({"root_id": task["root_id"], "family_id": task["family_id"], "excluded": excluded,
                     "exclusion_reason": "previously_seen_root_or_family" if excluded else None,
                     "branch_order": order, "order_role": "scheduling_not_assignment", "branch_inclusion_probability": 1.0,
                     "seeds": {s: collect.seeded(config, task["root_id"], s) for s in labels}})
    return plan


def planned_calls(config, plan):
    n = sum(not p["excluded"] for p in plan)
    per_root = len(DIAG_ARMS) * config["branch_replicates"]
    return {"initial": n, "continue": n * per_root, "total": n * (1 + per_root)}


class _Phase:
    """One phase's receiver guard and dispatch accounting (collect.run's closures, made reusable)."""

    def __init__(self, config, output, adapter, clock, carried):
        self.config, self.output, self.adapter, self.clock = config, output, adapter, clock
        self.attempted, self.reserved = carried["attempted_calls"], carried["reserved_completion_tokens"]
        self.carried = dict(carried)
        self.elapsed_before = carried["wall_seconds"]  # the time budget is study-wide, like the call budget
        self.started = clock()
        self.fatal = None
        self.preflight_failure = None
        self.metadata = {"interim_checks": []}
        self.calls = []
        self.guarded = config["schema_version"] == "landmark-v2" and not isinstance(adapter, collect.Mock)

    def remaining(self):
        return self.config["max_seconds"] - self.elapsed_before - (self.clock() - self.started)

    def metadata_call(self, method):
        if self.remaining() <= 0:
            raise TimeoutError("Run deadline reached before metadata request")
        return method(min(self.config["request_timeout_seconds"], self.remaining()))

    def preflight(self, previous_state=None):
        """collect.run's preflight, plus the A/C boundary: phase C's state must equal phase A's state."""
        a, md = self.adapter, self.metadata
        if self.guarded:
            md.update(sampler_law=self.config["sampler_law"], lease=collect.LEASE, receiver_guard_limits=list(collect.GUARD_LIMITS))
        try:
            md["before"] = self.metadata_call(a.metadata)
            md["version"] = self.metadata_call(a.version)
            md["definition"] = self.metadata_call(a.definition)
            if self.guarded:
                if not hasattr(a, "receiver_state") or not hasattr(a, "busy_slots"):
                    raise ValueError("landmark-v2 needs a receiver that exposes its /props state and slots")
                md["state_before"] = self.metadata_call(a.receiver_state)
                md["state_before_sha256"] = collect.digest(md["state_before"])
                if previous_state is not None:
                    md["between_phase_drift_fields"] = collect.state_drift(previous_state, md["state_before"])
                    if md["between_phase_drift_fields"]:
                        raise ValueError(f"receiver_drift_between_phases: {md['between_phase_drift_fields']}")
                if md["state_before_sha256"] != self.config["receiver_state_sha256"]:
                    raise ValueError("Receiver state (build/template/context/sampler defaults) differs from freeze")
                # collect.py's sampler-law binding (MRL-06 repair), exactly as collect.run applies it.
                overrides = collect.sampler_differences(self.config["sampler"], md["state_before"]["default_generation_settings"]["params"])
                if self.config["sampler_law"] == "server_defaults_pinned" and overrides:
                    raise ValueError(f"Request sampler differs from the frozen server defaults under server_defaults_pinned: {overrides}")
                md["sampler_overrides"] = overrides
                busy = self.metadata_call(a.busy_slots)
                if busy != 0:
                    raise ValueError(f"Receiver lease check failed: busy slots = {busy}")
        except Exception as exc:
            self.fatal = f"preflight: {type(exc).__name__}: {exc}"
        self.preflight_failure = self.fatal

    def interim_check(self, root_id):
        if not self.guarded or self.fatal is not None:
            return
        check = {"root_id": root_id}
        try:
            state = self.metadata_call(self.adapter.receiver_state)
            check.update(state_sha256=collect.digest(state), drift_fields=collect.state_drift(self.metadata["state_before"], state),
                         busy_slots=self.metadata_call(self.adapter.busy_slots))
        except Exception as exc:
            check["error"] = f"{type(exc).__name__}: {exc}"
        self.metadata["interim_checks"].append(check)
        if check.get("error"):
            self.fatal = f"receiver_unverifiable_before_{root_id}: {check['error']}"
        elif check["drift_fields"]:
            self.fatal = f"receiver_drift_before_{root_id}: {check['drift_fields']}"
        elif check["busy_slots"] != 0:
            self.fatal = f"receiver_contention_before_{root_id}: busy slots = {check['busy_slots']}"

    def generate(self, messages, p, phase, arm, replicate=0):
        config = self.config
        seed_key = "initial" if arm == "initial" else f"{arm}:{replicate}"
        payload = {"model": config["model"], "messages": messages, "stream": False,
                   "options": {**config["decoding"], "num_predict": config["max_tokens_per_call"], "seed": p["seeds"][seed_key]}}
        rec = {"phase": phase, "root_id": p["root_id"], "arm": arm, "replicate": replicate, "seed_key": seed_key,
               "request": payload, "request_sha256": collect.digest(payload), "attempted": False, "output": None,
               "output_sha256": None, "missing_reason": None, "prompt_tokens": None, "completion_tokens": None, "seconds": 0.0}
        reason = self.fatal
        if reason is None and self.remaining() <= 0: reason = "time_budget_exhausted"
        if reason is None and self.attempted >= config["max_calls"]: reason = "call_budget_exhausted"
        if reason is None and self.reserved + config["max_tokens_per_call"] > config["max_completion_tokens"]: reason = "completion_token_budget_exhausted"
        if reason is None and len(json.dumps(payload, ensure_ascii=False).encode()) > config["max_request_bytes"]: reason = "request_byte_cap"
        begin = self.clock()
        if reason is None:
            self.attempted += 1
            self.reserved += config["max_tokens_per_call"]  # Never refund: includes timed-out/uncertain work.
            rec["attempted"] = True
            try:
                response = self.adapter.generate(payload, min(config["request_timeout_seconds"], self.remaining()))
                rec["response"] = response
                text = response.get("message", {}).get("content")
                if response.get("done") is not True or not isinstance(text, str) or not text.strip():
                    raise ValueError("Incomplete or empty response")
                for name, key in (("prompt_tokens", "prompt_eval_count"), ("completion_tokens", "eval_count")):
                    value = response.get(key)
                    if type(value) is not int or value < 0:
                        raise ValueError("Missing or invalid token accounting")
                    rec[name] = value
                if rec["completion_tokens"] > config["max_tokens_per_call"]:
                    self.fatal = "server_violated_completion_token_cap"
                    raise ValueError("Server violated completion-token cap")
                rec["output"], rec["output_sha256"] = text, collect.digest(text)
            except Exception as exc:
                reason = f"generation: {type(exc).__name__}: {exc}"
        rec["seconds"] = self.clock() - begin
        rec["missing_reason"] = reason
        self.calls.append(rec)
        with (self.output / "calls.jsonl").open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def postflight(self):
        md = self.metadata
        try:
            md["after"] = self.metadata_call(self.adapter.metadata)
            md["digest_unchanged"] = md["after"].get("digest") == md.get("before", {}).get("digest")
            if self.guarded and "state_before" in md:
                after = self.metadata_call(self.adapter.receiver_state)
                md["state_after"], md["state_after_sha256"] = after, collect.digest(after)
                md["postflight_drift_fields"] = collect.state_drift(md["state_before"], after)
        except Exception as exc:
            md["postflight_error"] = f"{type(exc).__name__}: {exc}"
            md["digest_unchanged"] = None

    def verification(self, inherited_problems=()):
        """collect.receiver_verification's statuses (MRL-06: a passing guard is "receiver_guard_checks_passed" and
        never grants efficacy interpretation), plus problems inherited from an earlier phase."""
        v = collect.receiver_verification(self.config, self.adapter, self.metadata, self.preflight_failure, self.fatal, self.guarded)
        if v["status"] == "preflight_failed_no_dispatch":
            return {**v, "inherited": list(inherited_problems)}
        if inherited_problems and v["status"] in ("receiver_not_verified_outputs_retained", "receiver_guard_checks_passed"):
            return {"status": "receiver_not_verified_outputs_retained", "efficacy_interpretable": False,
                    "reasons": [*inherited_problems, *v.get("reasons", [])]}
        return v

    def completion(self, phase, plan, planned, verification, **extra):
        phase_calls = self.attempted - self.carried["attempted_calls"]
        completion = {"phase": phase, "arm_set": ARM_SET, "attempted_calls": self.attempted, "reserved_completion_tokens": self.reserved,
            "phase_attempted_calls": phase_calls, "phase_reserved_completion_tokens": self.reserved - self.carried["reserved_completion_tokens"],
            "planned_calls": planned, "measured_prompt_tokens": sum(c["prompt_tokens"] or 0 for c in self.calls),
            "measured_completion_tokens": sum(c["completion_tokens"] or 0 for c in self.calls),
            "attempted_calls_with_unknown_usage": sum(c["attempted"] and (c["prompt_tokens"] is None or c["completion_tokens"] is None) for c in self.calls),
            "phase_wall_seconds": self.clock() - self.started, "wall_seconds": self.elapsed_before + self.clock() - self.started,
            "model_metadata": self.metadata, "preflight_failure": self.preflight_failure, "fatal_error": self.fatal,
            "assigned_roots": sum(not p["excluded"] for p in plan), "excluded_roots": sum(p["excluded"] for p in plan),
            "paid_api_spend_usd": 0, "candidate_executions": 0, "receiver_verification": verification, **extra}
        completion["checksums"] = {p.relative_to(self.output).as_posix(): file_sha(p)
                                   for p in sorted([*self.output.glob("*.json*"), *self.output.glob("artifacts/*.txt")])}
        (self.output / "completion.json").write_text(json.dumps(completion, indent=2, ensure_ascii=False) + "\n")
        return completion


def _start(config, tasks, output, real):
    if real:
        # Fail closed: freeze verification (collect.verify_freeze) and release are not wired under MRL-08.
        raise ValueError("Real diagnostic collection is not released; this collector is source/mock only")
    collect.validate(config, tasks, real)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    plan = assignments(config, tasks)
    return output, plan, planned_calls(config, plan)


def _manifest(config, tasks, plan, planned, phase, **extra):
    return {"schema_version": config["schema_version"], "arm_set": ARM_SET, "phase": phase, "evidence_type": "mock_transport_only",
            "config": config, "config_sha256": collect.digest(config), "dataset_sha256": collect.digest(tasks), "tasks": tasks,
            "assignment_table": plan, "assignment_table_sha256": collect.digest(plan), "planned_calls": planned,
            "system": collect.SYSTEM, "design": "All five continuation arms are collected for every root; inclusion probability one. "
            "Randomized execution order is scheduling, not treatment assignment.", **extra}


def run_initial(config, tasks, output, *, adapter=None, clock=time.monotonic, real=False):
    output, plan, planned = _start(config, tasks, output, real)
    (output / "artifacts").mkdir()
    (output / "manifest.json").write_text(json.dumps(_manifest(config, tasks, plan, planned, "initial"), indent=2, ensure_ascii=False) + "\n")
    ph = _Phase(config, output, adapter if adapter is not None else collect.Mock(), clock,
                {"attempted_calls": 0, "reserved_completion_tokens": 0, "wall_seconds": 0.0})
    ph.preflight()
    for task, p in zip(tasks, plan):
        row = {"root_id": p["root_id"], "family_id": p["family_id"], "excluded": p["excluded"]}
        if p["excluded"]:
            row["status"] = "excluded_before_collection"
        else:
            ph.interim_check(p["root_id"])
            base = collect.initial_messages(task)
            rec = ph.generate(base, p, "initial", "initial")
            row.update(base_messages_sha256=collect.digest(base), initial=rec, artifact=None, artifact_sha256=None)
            if rec["output"] is None:
                row["status"] = "initial_failed"
            else:
                path = output / "artifacts" / artifact_name(p["root_id"])
                path.write_bytes(rec["output"].encode("utf-8"))
                row.update(artifact=path.relative_to(output).as_posix(), artifact_sha256=text_sha(rec["output"]), status="initial_collected")
        with (output / "roots.jsonl").open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    ph.postflight()
    return ph.completion("initial", plan, planned, ph.verification())


def _load_initial(initial_dir, config, tasks, plan):
    """Everything phase C trusts from phase A, re-verified from bytes (checksums, config, dataset, plan)."""
    initial_dir = Path(initial_dir)
    manifest = json.loads((initial_dir / "manifest.json").read_text())
    completion = json.loads((initial_dir / "completion.json").read_text())
    if manifest.get("phase") != "initial" or manifest.get("arm_set") != ARM_SET or completion.get("phase") != "initial":
        raise ValueError("Initial directory is not a diagnostic-v1 initial phase")
    if (manifest["config_sha256"], manifest["dataset_sha256"], manifest["assignment_table_sha256"]) != (
            collect.digest(config), collect.digest(tasks), collect.digest(plan)):
        raise ValueError("Initial phase used a different config, dataset or assignment table")
    for rel, sha in completion["checksums"].items():
        if file_sha(initial_dir / rel) != sha:
            raise ValueError(f"Initial-phase file changed after completion: {rel}")
    if set(completion["checksums"]) != {p.relative_to(initial_dir).as_posix()
                                        for p in [*initial_dir.glob("*.json*"), *initial_dir.glob("artifacts/*.txt")]} - {"completion.json"}:
        raise ValueError("Initial-phase directory contents differ from its completion checksums")
    rows = {r["root_id"]: r for r in (json.loads(x) for x in (initial_dir / "roots.jsonl").read_text().splitlines() if x.strip())}
    if list(rows) != [p["root_id"] for p in plan]:
        raise ValueError("Initial roots differ from the assignment table")
    return initial_dir, completion, rows


def run_continue(config, tasks, initial_dir, diagnostics_path, output, *, expected_diagnostics_sha256,
                 adapter=None, clock=time.monotonic, real=False):
    if real:
        raise ValueError("Real diagnostic collection is not released; this collector is source/mock only")
    collect.validate(config, tasks, real)
    if not isinstance(expected_diagnostics_sha256, str) or not HEX64.fullmatch(expected_diagnostics_sha256):
        raise ValueError("Continue phase requires the expected SHA-256 of the diagnostics file")
    raw = Path(diagnostics_path).read_bytes()
    diagnostics_sha256 = hashlib.sha256(raw).hexdigest()
    if diagnostics_sha256 != expected_diagnostics_sha256:
        raise ValueError("Diagnostics file differs from its bound SHA-256")
    plan = assignments(config, tasks)
    planned = planned_calls(config, plan)
    initial_dir, initial_completion, initial_rows = _load_initial(initial_dir, config, tasks, plan)
    diagnostics = json.loads(raw.decode("utf-8"))
    collected = [r for r in initial_rows.values() if r.get("artifact_sha256")]
    if not isinstance(diagnostics, dict) or set(diagnostics) != {r["root_id"] for r in collected}:
        raise ValueError("Diagnostics must map exactly the roots with an initial artifact")
    dm = diagnostic_module()
    # Bind and render everything before any dispatch: a refusal never leaves a partial continuation.
    bound = {}
    for task, p in zip(tasks, plan):
        row = initial_rows[p["root_id"]]
        if not row.get("artifact_sha256"):
            continue
        data = (initial_dir / row["artifact"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != row["artifact_sha256"]:
            raise ValueError(f"Initial artifact bytes differ from the recorded SHA-256 for {p['root_id']}")
        diag = diagnostics[p["root_id"]]
        if not isinstance(diag, dict) or diag.get("schema_version") != dm.SCHEMA or diag.get("root_id") != p["root_id"]:
            raise ValueError(f"Diagnostic for {p['root_id']} has the wrong schema or root")
        if diag.get("initial_artifact_sha256") != row["artifact_sha256"]:
            raise ValueError(f"Diagnostic for {p['root_id']} is bound to a different initial artifact")
        base = collect.initial_messages(task)
        if collect.digest(base) != row["base_messages_sha256"]:
            raise ValueError(f"Public prefix for {p['root_id']} differs from the initial phase")
        message_bytes = dm.diagnostic_bytes(diag)  # raises on overflow; never truncates
        arms = dm.render_arms(base, data.decode("utf-8"), diag)
        if set(arms) != set(DIAG_ARMS):
            raise ValueError(f"render_arms returned {sorted(arms)}, expected {DIAG_ARMS}")
        bound[p["root_id"]] = {"messages": arms, "diagnostic_sha256": collect.digest(diag),
                               "diagnostic_bytes_sha256": hashlib.sha256(message_bytes).hexdigest(),
                               "rendered_sha256": {a: collect.digest(arms[a]) for a in DIAG_ARMS}}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    renderers = {"n_instruction": dm.N_INSTRUCTION, "r1_instruction": dm.R1_INSTRUCTION, "s1_strings": list(dm.S1_STRINGS),
                 "diagnostic_header": dm.DIAGNOSTIC_HEADER, "targeted_renderer": collect.TARGETED}
    (output / "manifest.json").write_text(json.dumps(_manifest(
        config, tasks, plan, planned, "continue", initial_dir=str(initial_dir), initial_completion_sha256=file_sha(initial_dir / "completion.json"),
        diagnostics_sha256=diagnostics_sha256, renderers=renderers, renderers_sha256=collect.digest(renderers),
        bindings={k: {x: v[x] for x in v if x != "messages"} for k, v in bound.items()}), indent=2, ensure_ascii=False) + "\n")
    carried = {k: initial_completion[k] for k in ("attempted_calls", "reserved_completion_tokens", "wall_seconds")}
    ph = _Phase(config, output, adapter if adapter is not None else collect.Mock(), clock, carried)
    ph.preflight(previous_state=initial_completion["model_metadata"].get("state_before") if ph.guarded else None)
    inherited = []
    if initial_completion.get("fatal_error"):
        inherited.append("initial_phase: " + initial_completion["fatal_error"])
        ph.fatal = ph.fatal or f"initial_phase_fatal: {initial_completion['fatal_error']}"
    elif initial_completion["receiver_verification"].get("status") != "receiver_guard_checks_passed":
        inherited.append("initial_phase_guard_not_passed: " + initial_completion["receiver_verification"]["status"])
    for task, p in zip(tasks, plan):
        row = {"root_id": p["root_id"], "family_id": p["family_id"], "excluded": p["excluded"], "arms": {}}
        if p["excluded"]:
            row["status"] = "excluded_before_collection"
        elif p["root_id"] not in bound:
            row["arms"] = {a: [{"replicate": r, "output": None, "output_sha256": None, "missing_reason": "initial_output_unavailable",
                                "attempted": False, "prompt_tokens": 0, "completion_tokens": 0, "seconds": 0.0}
                               for r in range(config["branch_replicates"])] for a in DIAG_ARMS}
            row["status"] = "initial_failed"
        else:
            b = bound[p["root_id"]]
            row.update({k: b[k] for k in ("diagnostic_sha256", "diagnostic_bytes_sha256", "rendered_sha256")},
                       initial_artifact_sha256=initial_rows[p["root_id"]]["artifact_sha256"], branch_order=p["branch_order"],
                       branch_inclusion_probability=1.0)
            ph.interim_check(p["root_id"])
            row["arms"] = {a: [] for a in DIAG_ARMS}
            for entry in p["branch_order"]:
                row["arms"][entry["arm"]].append(ph.generate(b["messages"][entry["arm"]], p, "continue", entry["arm"], entry["replicate"]))
            for a in DIAG_ARMS:
                row["arms"][a].sort(key=lambda r: r["replicate"])
            row["status"] = "outputs_complete" if all(r["output"] is not None for a in row["arms"].values() for r in a) else "outputs_missing"
        with (output / "roots.jsonl").open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    ph.postflight()
    return ph.completion("continue", plan, planned, ph.verification(inherited), diagnostics_sha256=diagnostics_sha256)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=PHASES, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--initial", type=Path, help="continue: the initial-phase output directory")
    p.add_argument("--diagnostics", type=Path, help="continue: root_id -> diagnostic JSON file")
    p.add_argument("--diagnostics-sha256", help="continue: required SHA-256 of the diagnostics file bytes")
    args = p.parse_args()
    config = json.loads(args.config.read_text())
    tasks = [json.loads(line) for line in args.tasks.read_text().splitlines() if line.strip()]
    if args.phase == "initial":
        result = run_initial(config, tasks, args.output)
    else:
        if args.initial is None or args.diagnostics is None or args.diagnostics_sha256 is None:
            p.error("--phase continue needs --initial, --diagnostics and --diagnostics-sha256")
        result = run_continue(config, tasks, args.initial, args.diagnostics, args.output,
                              expected_diagnostics_sha256=args.diagnostics_sha256)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
