#!/usr/bin/env python3
"""E13a two-arm collection driver: the REAL dispatch path, reusing E12's instruments end to end.

Evidence class: ungraded_real_collection with --real (60 receiver calls at five fixed public-fail
checkpoints), and transport_only_injected_adapter otherwise. A transport-only run is NEVER evidence about
either arm: an injected adapter produces no measurement, and its manifest, completion and receiver
verification say so. This module never executes a candidate, a reference solution or a benchmark program.

E13a is NOT authorized to execute. This file is the executable path, not the authorization.

What it does, in order, refusing before it dispatches anything:
  1. Rebuilds all 60 requests through the existing instruments: collect.initial_messages for FRESH and
     diagnostic.render_arms(...)["R1"] for R1, from E12's checksum-verified initial artifact bytes and the
     frozen public diagnostic, with the checkpoint set derived from analyze_diagnostic.public_status only
     (no private grade is read). Every rendered message list is compared byte-for-byte against E12's
     recorded request messages, and every seed against every seed E12 used at that root.
  2. With real=True builds the receiver adapter through the same path E12 uses: collect_diagnostic._real_setup
     (UNRESOLVED refusal, collect.validate(real=True), landmark-v2, validate_ownership plus the window check,
     collect.verify_freeze) returning collect.LlamaServer(config); the receiver law, state, idle-slot, interim
     and postflight drift checks are collect_diagnostic._Phase's, subclassed, not reimplemented.
  3. Preserves every assigned slot. Inclusion probability is 1 for every root-arm-replicate, order is
     root-balanced scheduling only, and there are no retries, no backfill and no outcome-driven stopping: a
     failed or unavailable attempt keeps its slot and records a missing_reason. Calls and reserved completion
     tokens are charged on dispatch and never refunded, under hard ceilings of 60 calls and 30720 tokens.
  4. Keeps a durable attempt ledger (flushed and fsynced per line) so an abort mid-run leaves a readable
     record of every reservation, writes into a fresh output directory it refuses to overwrite, and records
     SHA-256 over every file it wrote plus every input it read.
  5. Charges the run against the shared StageClock: the 480 s collection cap and the ONE 2700 s outer
     deadline, which a reload cannot extend.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from experiments.landmark import collect  # noqa: E402
from experiments.landmark import collect_diagnostic as cd  # noqa: E402
from e13a_stage_clock import CLOCK_FILE, CapExhausted, StageClock, open_clock, parse_utc, utc_now  # noqa: E402

RUN = ROOT / "results/e12_dev_v3_20260922T030255Z"          # E12's immutable run (read only)
PKG = ROOT / "experiments/landmark/dev_release_v3"           # E12's frozen 14-root release (read only)
E13A_RELEASE = ROOT / "experiments/landmark/e13a_release"    # E13a's own bindings, when they exist
STAGE = ROOT / "experiments/landmark/e13a_stage.json"
PLAN = ROOT / "results/e13a_request_plan_20260922.json"
RESULTS_DIR = ROOT / "results"

ARM_SET = "e13a-two-arm"
ARMS = ("R1", "FRESH")
PHASE_NAME = "collection"
ORDER_LABEL = "order:" + ARM_SET
# Hard ceilings for this stage. A caller may tighten them; nothing may raise them.
MAX_CALLS = 60
MAX_RESERVED_COMPLETION_TOKENS = 30720
TOKENS_PER_CALL = 512
LEDGER = "attempt_ledger.jsonl"
# Request-shaping fields that must be identical in E12's frozen package and in E13a's release bindings, or the
# rebuilt requests would not be the bytes E12 sent.
REQUEST_SHAPING = ("schema_version", "model", "model_digest", "decoding", "max_tokens_per_call", "sampler",
                   "sampler_law", "receiver_state_sha256", "base_url", "seed", "request_timeout_seconds",
                   "max_request_bytes", "server_build", "protocol_version")
TRANSPORT_ONLY = "transport_only_injected_adapter_not_a_measurement"
REAL_EVIDENCE = "ungraded_real_collection"


class Refusal(ValueError):
    """An integrity check failed. Raised before dispatch wherever possible; never downgraded to a warning.

    A ValueError, so a caller catching the refusals the reused instruments raise catches these too."""


def _strict(raw):
    return cd.diagnostic_module().strict_json_loads(raw)  # duplicate keys refused, never last-wins


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _jsonl(path):
    return [_strict(line.encode("utf-8")) for line in Path(path).read_text().splitlines() if line.strip()]


def artifact_name(root_id, arm, replicate):
    return f"{root_id.replace('/', '%2F')}__{arm}__{replicate}.txt"


def refuse_results_path(path):
    """results/ holds immutable runs; nothing this driver writes may land inside it."""
    resolved = Path(path).resolve()
    if resolved == RESULTS_DIR.resolve() or RESULTS_DIR.resolve() in resolved.parents:
        raise Refusal(f"Refusing to write inside the immutable results/ tree: {resolved}")
    return resolved


# ------------------------------------------------------------------ stage bindings
def load_stage(path=STAGE, *, release_dir=None, run=RUN, pkg=PKG):
    """The E13a stage descriptor plus the release bindings dispatch uses. Nothing here authorizes a call."""
    path = Path(path)
    raw = path.read_bytes()
    descriptor = _strict(raw)
    for key in ("stage", "arm_set", "arms", "roots", "grading_limits", "gating", "contrast", "evidence_class"):
        if key not in descriptor:
            raise Refusal(f"E13a stage descriptor is missing {key}")
    if descriptor["arm_set"] != ARM_SET or set(descriptor["arms"]) != set(ARMS):
        raise Refusal(f"stage descriptor declares a different arm set: {descriptor['arm_set']} {sorted(descriptor['arms'])}")
    if descriptor["gating"].get("private_grades_are_an_input") is not False:
        raise Refusal("stage gating must declare that private grades are not an input")
    if descriptor.get("branch_inclusion_probability") != 1.0:
        raise Refusal("every root-arm-replicate must carry inclusion probability 1")
    cells = sum(len(descriptor["arms"][a]) for a in ARMS) * len(descriptor["roots"])
    if cells != MAX_CALLS:
        raise Refusal(f"stage descriptor assigns {cells} cells; this stage's ceiling is exactly {MAX_CALLS}")
    if release_dir is None:
        release_dir = E13A_RELEASE if (E13A_RELEASE / "config.json").exists() else pkg
    release_dir = Path(release_dir)
    pkg = Path(pkg)
    package = {"config": _strict((pkg / "config.json").read_bytes()), "tasks": _jsonl(pkg / "tasks.jsonl"),
               "config_path": pkg / "config.json", "tasks_path": pkg / "tasks.jsonl"}
    release = {"config": _strict((release_dir / "config.json").read_bytes()),
               "tasks": _jsonl(release_dir / "tasks.jsonl"),
               "config_path": release_dir / "config.json", "tasks_path": release_dir / "tasks.jsonl"}
    differing = [k for k in REQUEST_SHAPING if release["config"].get(k) != package["config"].get(k)]
    if differing:
        raise Refusal(f"release bindings would change the request bytes E12 sent; differing fields: {differing}")
    return {"descriptor": descriptor, "stage_path": path, "stage_sha256": hashlib.sha256(raw).hexdigest(),
            "run": Path(run), "package": package, "release": release, "release_dir": release_dir,
            "caps": {"max_calls": MAX_CALLS, "max_completion_tokens": MAX_RESERVED_COMPLETION_TOKENS,
                     "phase_seconds": None}}


def load_plan(path=PLAN):
    """The verified E13a request plan (scripts/build_e13a_request_plan.py output)."""
    path = Path(path)
    raw = path.read_bytes()
    plan = _strict(raw)
    if not isinstance(plan.get("roots"), list) or not plan["roots"]:
        raise Refusal("request plan carries no roots")
    if not str(plan.get("plan_version", "")).startswith("e13a-request-plan"):
        raise Refusal(f"not an E13a request plan: {plan.get('plan_version')!r}")
    plan["plan_path"] = str(path)
    plan["plan_sha256"] = hashlib.sha256(raw).hexdigest()
    return plan


def _as_stage(stage):
    return stage if isinstance(stage, dict) and "descriptor" in stage else load_stage(stage)


def _as_plan(plan):
    return plan if isinstance(plan, dict) and "roots" in plan and "plan_sha256" in plan else load_plan(plan)


# ------------------------------------------------------------------ 1. request reconstruction
def checkpoints_from_public_diagnostics(diagnostics):
    """analyze_diagnostic.public_status == "any_fail" only; an unknown public status is never a checkpoint."""
    from experiments.landmark import analyze_diagnostic as ad
    return [rid for rid in sorted(diagnostics) if ad.public_status(diagnostics[rid], rid) == "any_fail"]


def rebuild(stage, plan):
    """Rebuild every assigned request through the existing instruments and verify it against E12's bytes.

    Refuses on: a checkpoint set that differs from the descriptor, an initial artifact whose bytes differ from
    E12's recorded SHA-256, a FRESH or R1 message list that differs from E12's recorded request messages, an R1
    message list that still carries the previous answer, a seed colliding with any seed E12 used at that root,
    a plan seed or message digest that differs from the reconstruction, and any absent or duplicate assignment.
    """
    stage, plan = _as_stage(stage), _as_plan(plan)
    descriptor, run = stage["descriptor"], stage["run"]
    config, tasks = stage["package"]["config"], stage["package"]["tasks"]
    table = cd.assignments(config, tasks)
    initial_dir, _, rows = cd._load_initial(run / "A", config, tasks, table)  # re-verifies A's bytes and bindings
    sums = _strict((run / "ARTIFACT_SHA256SUMS.json").read_bytes())
    sums = sums.get("files", sums)
    raw = (run / "B/diagnostics.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != sums["B/diagnostics.json"]:
        raise Refusal("B/diagnostics.json differs from E12's artifact checksums")
    if hashlib.sha256((run / "C/calls.jsonl").read_bytes()).hexdigest() != sums["C/calls.jsonl"]:
        raise Refusal("C/calls.jsonl differs from E12's artifact checksums")
    diagnostics = _strict(raw)
    checkpoints = checkpoints_from_public_diagnostics(diagnostics)
    if checkpoints != sorted(descriptor["roots"]):
        raise Refusal(f"public-diagnostic checkpoints {checkpoints} differ from the stage roots {sorted(descriptor['roots'])}")
    if sorted({r["root_id"] for r in plan["roots"]}) != checkpoints:
        raise Refusal("request plan roots differ from the public-diagnostic checkpoints")
    dm = cd.diagnostic_module()
    calls = _jsonl(run / "C/calls.jsonl")
    by_task = {t["root_id"]: t for t in tasks}
    seeds_by_root = {p["root_id"]: p["seeds"] for p in table}
    plan_by_root = {}
    for entry in plan["roots"]:
        if entry["root_id"] in plan_by_root:
            raise Refusal(f"request plan lists {entry['root_id']} twice")
        plan_by_root[entry["root_id"]] = entry
    expected_cells = {(a, r) for a in ARMS for r in descriptor["arms"][a]}
    out_roots, checks = [], []
    # Descriptor order is the assignment-table order; ordering is scheduling only.
    for root_id in [p["root_id"] for p in table if p["root_id"] in set(checkpoints)]:
        row, entry = rows[root_id], plan_by_root[root_id]
        text = (initial_dir / row["artifact"]).read_bytes()
        if hashlib.sha256(text).hexdigest() != row["artifact_sha256"]:
            raise Refusal(f"initial artifact bytes changed for {root_id}")
        diag = diagnostics[root_id]
        if diag.get("initial_artifact_sha256") != row["artifact_sha256"]:
            raise Refusal(f"diagnostic for {root_id} is bound to a different initial artifact")
        base = collect.initial_messages(by_task[root_id])
        if collect.digest(base) != row["base_messages_sha256"] or base != row["initial"]["request"]["messages"]:
            raise Refusal(f"FRESH messages for {root_id} differ from E12's recorded initial request")
        r1 = dm.render_arms(base, text.decode("utf-8"), diag)["R1"]
        e12_r1 = [c["request"]["messages"] for c in calls if c["root_id"] == root_id and c["arm"] == "R1"]
        if len(e12_r1) != 2 or any(m != r1 for m in e12_r1):
            raise Refusal(f"R1 messages for {root_id} differ from E12's recorded R1 requests")
        if any(m["role"] == "assistant" for m in r1):
            raise Refusal(f"R1 messages for {root_id} still carry the previous answer")
        messages = {"R1": r1, "FRESH": base}
        digests = {a: collect.digest(messages[a]) for a in ARMS}
        if entry.get("r1_messages_sha256") != digests["R1"] or entry.get("base_messages_sha256") != digests["FRESH"]:
            raise Refusal(f"request plan message digests for {root_id} differ from the reconstruction")
        used = set(seeds_by_root[root_id].values())
        planned = {}
        for req in entry["requests"]:
            cell = (req["arm"], req["replicate"])
            if cell not in expected_cells:
                raise Refusal(f"request plan assigns an unexpected cell for {root_id}: {cell}")
            if cell in planned:
                raise Refusal(f"request plan assigns {root_id} {cell} twice")
            planned[cell] = req
        absent = sorted(expected_cells - set(planned))
        if absent:
            raise Refusal(f"request plan is missing assigned cells for {root_id}: {absent}")
        requests = []
        for arm in ARMS:
            for replicate in descriptor["arms"][arm]:
                seed_key = f"{arm}:{replicate}"
                req = planned[(arm, replicate)]
                seed = collect.seeded(config, root_id, seed_key)
                for candidate, where in ((seed, "reconstructed"), (req.get("seed"), "planned")):
                    if candidate in used:
                        raise Refusal(f"{where} seed for {root_id} {seed_key} repeats a seed E12 used at that root")
                if req.get("seed") != seed:
                    raise Refusal(f"request plan seed for {root_id} {seed_key} differs from collect.seeded")
                if req.get("seed_key") != seed_key or req.get("messages_sha256") != digests[arm]:
                    raise Refusal(f"request plan entry for {root_id} {seed_key} differs from the reconstruction")
                used.add(seed)
                requests.append({"arm": arm, "replicate": replicate, "seed_key": seed_key, "seed": seed,
                                 "messages_sha256": digests[arm], "branch_inclusion_probability": 1.0})
        out_roots.append({"root_id": root_id, "family_id": by_task[root_id]["family_id"], "excluded": False,
                          "initial_artifact_sha256": row["artifact_sha256"], "base_messages_sha256": digests["FRESH"],
                          "r1_messages_sha256": digests["R1"], "messages": messages, "requests": requests,
                          "seeds": {q["seed_key"]: q["seed"] for q in requests}})
        checks.append({"root_id": root_id, "fresh_messages_equal_e12_initial_request": True,
                       "r1_messages_equal_both_e12_r1_requests": True, "r1_previous_answer_removed": True,
                       "new_seeds_disjoint_from_e12_seeds": True,
                       "plan_digests_and_seeds_equal_reconstruction": True})
    total = sum(len(r["requests"]) for r in out_roots)
    if total != MAX_CALLS:
        raise Refusal(f"rebuilt {total} requests; this stage assigns exactly {MAX_CALLS}")
    return {"roots": out_roots, "byte_checks": checks, "checkpoints": checkpoints,
            "inputs": {rel: sums[rel] for rel in ("A/roots.jsonl", "B/diagnostics.json", "C/calls.jsonl") if rel in sums},
            "package_config_sha256": file_sha(stage["package"]["config_path"]),
            "gating": {"source": "results/e12_dev_v3_20260922T030255Z/B/diagnostics.json via analyze_diagnostic.public_status",
                       "checkpoints": checkpoints, "private_inputs_used_for_gating": []}}


# ------------------------------------------------------------------ 2. root-balanced scheduling (not assignment)
def schedule(config, roots):
    """Each block of len(roots) holds every root exactly once; within a root the cells are shuffled from
    collect.seeded. Ordering is scheduling only: inclusion probability is 1 for every cell."""
    per_root, ids = {}, [r["root_id"] for r in roots]
    for r in roots:
        cells = [{"arm": q["arm"], "replicate": q["replicate"]} for q in r["requests"]]
        random.Random(collect.seeded(config, r["root_id"], ORDER_LABEL)).shuffle(cells)
        per_root[r["root_id"]] = cells
    n = len(per_root[ids[0]])
    if any(len(v) != n for v in per_root.values()):
        raise Refusal("roots do not carry the same number of cells; the schedule would not be root-balanced")
    order = []
    for slot in range(n):
        rotation = slot % len(ids)
        for root_id in ids[rotation:] + ids[:rotation]:  # rotate so no root is always first
            order.append({"index": len(order), "block": slot, "root_id": root_id, **per_root[root_id][slot],
                          "branch_inclusion_probability": 1.0, "order_role": "scheduling_not_assignment"})
    unique = len({(o["root_id"], o["arm"], o["replicate"]) for o in order})
    if not unique == len(order) == len(ids) * n:
        raise Refusal("schedule is not a permutation of the root-arm-replicate cells")
    for start in range(0, len(order), len(ids)):
        if sorted(o["root_id"] for o in order[start:start + len(ids)]) != sorted(ids):
            raise Refusal("schedule block is not root-balanced")
    return order


# ------------------------------------------------------------------ durable attempt ledger
class _Ledger:
    """Append-only, flushed and fsynced per line, so an abort mid-run still leaves every reservation readable."""

    def __init__(self, path):
        self.path = Path(path)
        self.lines = 0

    def write(self, record):
        record = {"utc": utc_now().isoformat().replace("+00:00", "Z"), **record}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.lines += 1
        return record


# ------------------------------------------------------------------ dispatch phase (E12's _Phase, subclassed)
class _E13aPhase(cd._Phase):
    """collect_diagnostic._Phase with the shared StageClock folded into its remaining-time budget, plus the
    per-slot artifact write and ledger line. Every receiver guard, accounting rule and missing_reason is
    _Phase's own: nothing is reimplemented or bypassed."""

    def __init__(self, config, output, adapter, clock, carried, *, stage_clock, ledger, phase_name=PHASE_NAME):
        super().__init__(config, output, adapter, clock, carried)
        self.stage_clock, self.ledger, self.phase_name = stage_clock, ledger, phase_name
        self.artifact_index = {}

    def remaining(self):
        """The tightest of the run's own time budget, this phase's cap and the ONE shared outer deadline."""
        return min(super().remaining(), self.stage_clock.remaining(self.phase_name))

    def clock_binding(self):
        own = super().remaining()
        return "config_max_seconds" if own <= self.stage_clock.remaining(self.phase_name) else \
            self.stage_clock.binding(self.phase_name)

    def generate(self, messages, p, phase, arm, replicate=0):
        key = f"{p['root_id']}|{arm}|{replicate}"
        self.ledger.write({"event": "dispatch_start", "slot": key, "seed_key": f"{arm}:{replicate}",
                           "seed": p["seeds"][f"{arm}:{replicate}"], "messages_sha256": collect.digest(messages),
                           "attempted_calls_before": self.attempted, "reserved_completion_tokens_before": self.reserved,
                           "phase_remaining_seconds": self.remaining(), "time_binding": self.clock_binding()})
        rec = super().generate(messages, p, phase, arm, replicate)
        artifact = None
        if rec["output"] is not None:
            name = artifact_name(p["root_id"], arm, replicate)
            (self.output / "artifacts" / name).write_bytes(rec["output"].encode("utf-8"))
            artifact = {"path": f"artifacts/{name}", "sha256": cd.text_sha(rec["output"]),
                        "output_sha256": rec["output_sha256"]}
            self.artifact_index[key] = artifact
        self.ledger.write({"event": "dispatch_result", "slot": key, "attempted": rec["attempted"],
                           "missing_reason": rec["missing_reason"], "request_sha256": rec["request_sha256"],
                           "artifact": artifact, "prompt_tokens": rec["prompt_tokens"],
                           "completion_tokens": rec["completion_tokens"], "seconds": rec["seconds"],
                           "attempted_calls_after": self.attempted, "reserved_completion_tokens_after": self.reserved,
                           "fatal_error": self.fatal})
        return rec


# ------------------------------------------------------------------ attestation (the same instrument E12 uses)
def _attestation(ownership, config, now, budget_seconds):
    """collect_diagnostic.validate_ownership plus _real_setup's window-end check, on the exact bytes."""
    raw = Path(ownership).read_bytes() if not isinstance(ownership, (bytes, bytearray)) else bytes(ownership)
    record = cd.validate_ownership(_strict(raw), config, now)
    window_end = cd._utc(record["exclusive_window_end_utc"], "exclusive_window_end_utc")
    if now + timedelta(seconds=budget_seconds) > window_end:
        raise Refusal("Ownership exclusive window ends before this phase's time budget could elapse")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "record": record}


# ------------------------------------------------------------------ entry point
def dispatch(stage, plan, out_dir, *, adapter=None, real=False, clock=None, ownership=None):
    """Collect both E13a arms at all five checkpoints. The one entry point: tests inject `adapter`.

    real=True builds collect.LlamaServer through collect_diagnostic._real_setup and refuses an injected
    adapter. Any other call is transport-only and is labelled as no measurement. Writes
    out_dir/collect/{calls.jsonl,manifest.json,completion.json,attempt_ledger.jsonl,artifacts/*.txt}.
    """
    stage, plan = _as_stage(stage), _as_plan(plan)
    out_dir = Path(out_dir)
    refuse_results_path(out_dir)
    out = out_dir / "collect"
    if out.exists():
        raise Refusal(f"Refusing to overwrite an existing collection directory: {out}")
    monotonic = time.monotonic
    if clock is None:
        clock, clock_path = open_clock(out_dir)
    else:
        clock_path = out_dir / CLOCK_FILE
    clock.check(PHASE_NAME)  # refuse before any output exists if the shared clock is already exhausted

    release, package = stage["release"], stage["package"]
    caps = dict(stage["caps"])
    if caps["max_calls"] > MAX_CALLS or caps["max_completion_tokens"] > MAX_RESERVED_COMPLETION_TOKENS:
        raise Refusal(f"stage caps exceed this stage's ceilings ({MAX_CALLS} calls, {MAX_RESERVED_COMPLETION_TOKENS} tokens)")
    phase_seconds = min(release["config"]["max_seconds"], clock.caps[PHASE_NAME] if PHASE_NAME in clock.caps else float("inf"))
    dispatch_config = {**release["config"], "max_calls": caps["max_calls"],
                       "max_completion_tokens": caps["max_completion_tokens"], "max_seconds": phase_seconds}
    collect.validate(dispatch_config, release["tasks"])
    if dispatch_config["max_tokens_per_call"] != TOKENS_PER_CALL:
        raise Refusal(f"this stage reserves {TOKENS_PER_CALL} completion tokens per call")

    real_extra, attestation = {}, None
    if real:
        adapter, real_extra = cd._real_setup(release["config"], release["tasks"], release["config_path"],
                                             release["tasks_path"], ownership, utc_now, adapter)
        attestation = real_extra["ownership"]
    else:
        if adapter is None:
            raise Refusal("transport-only collection needs an injected adapter; real dispatch needs real=True")
        if ownership is not None:
            attestation = _attestation(ownership, release["config"], utc_now(), phase_seconds)

    built = rebuild(stage, plan)
    order = schedule(package["config"], built["roots"])
    if len(order) != MAX_CALLS:
        raise Refusal(f"schedule holds {len(order)} cells; this stage assigns exactly {MAX_CALLS}")

    out.mkdir(parents=True, exist_ok=False)  # from here on every reservation is charged and recorded
    (out / "artifacts").mkdir()
    ledger = _Ledger(out / LEDGER)
    evidence = REAL_EVIDENCE if real else TRANSPORT_ONLY
    manifest = {
        "schema_version": dispatch_config["schema_version"], "arm_set": ARM_SET, "stage": "E13a",
        "phase": PHASE_NAME, "evidence_type": evidence,
        "evidence_class": stage["descriptor"]["evidence_class"], "real_receiver": bool(real),
        "transport_only": not real, "candidate_executions": 0, "paid_api_spend_usd": 0,
        "adapter": type(adapter).__name__,
        "measurement_note": None if real else "Injected adapter: this run is transport-only and is NOT evidence about either arm.",
        "authorization_note": "E13a execution is not authorized by this file; --real additionally requires the "
                              "release bindings, a renewed attestation and an enumerated allowance.",
        "stage_path": str(stage["stage_path"]), "stage_sha256": stage["stage_sha256"],
        "plan_path": plan["plan_path"], "plan_sha256": plan["plan_sha256"],
        "release_dir": str(stage["release_dir"]), "release_config_sha256": file_sha(release["config_path"]),
        "release_tasks_sha256": file_sha(release["tasks_path"]),
        "package_config_sha256": built["package_config_sha256"], "inputs": built["inputs"],
        "config": dispatch_config, "config_sha256": collect.digest(dispatch_config),
        "frozen_config_sha256": collect.digest(release["config"]),
        "caps": {"max_calls": dispatch_config["max_calls"], "max_completion_tokens": dispatch_config["max_completion_tokens"],
                 "max_tokens_per_call": dispatch_config["max_tokens_per_call"], "phase_seconds": phase_seconds,
                 "ceilings": {"max_calls": MAX_CALLS, "max_completion_tokens": MAX_RESERVED_COMPLETION_TOKENS}},
        "stage_clock": clock.report(), "stage_clock_path": str(clock_path),
        "gating": built["gating"], "byte_checks": built["byte_checks"],
        "bindings": {r["root_id"]: {k: r[k] for k in ("family_id", "initial_artifact_sha256", "base_messages_sha256",
                                                      "r1_messages_sha256")} for r in built["roots"]},
        "seed_plan": {r["root_id"]: r["seeds"] for r in built["roots"]},
        "schedule": order, "schedule_sha256": collect.digest(order), "order_role": "scheduling_not_assignment",
        "design": "Both arms are dispatched for every root at every assigned replicate; inclusion probability one. "
                  "No retries, no backfill and no outcome-driven stopping: a failed or unavailable attempt keeps "
                  "its slot with a missing_reason. Randomized order is scheduling, not treatment assignment.",
        "contrast": stage["descriptor"]["contrast"],
        "attestation": attestation, **real_extra}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    ledger.write({"event": "reserved", "manifest_sha256": file_sha(out / "manifest.json"),
                  "stage_sha256": stage["stage_sha256"], "plan_sha256": plan["plan_sha256"],
                  "attestation_sha256": (attestation or {}).get("sha256"), "evidence_type": evidence,
                  "planned_calls": len(order), "caps": manifest["caps"],
                  "stage_clock": {"start_utc": clock.report()["start_utc"],
                                  "outer_remaining_seconds": clock.remaining_outer(),
                                  "phase_remaining_seconds": clock.remaining(PHASE_NAME)}})

    by_root = {r["root_id"]: r for r in built["roots"]}
    table = [{"root_id": r["root_id"], "family_id": r["family_id"], "excluded": False} for r in built["roots"]]
    planned = {"total": len(order), **{a: sum(1 for o in order if o["arm"] == a) for a in ARMS}}
    deadline = None
    if attestation is not None:
        deadline = (utc_now, cd._utc(attestation["record"]["exclusive_window_end_utc"], "exclusive_window_end_utc"))
    ph = _E13aPhase(dispatch_config, out, adapter, monotonic,
                    {"attempted_calls": 0, "reserved_completion_tokens": 0, "wall_seconds": 0.0},
                    stage_clock=clock, ledger=ledger)
    ph.deadline = deadline  # checked before every request; expiry stops FUTURE dispatch only
    try:
        with clock.phase(PHASE_NAME):
            ph.preflight()
            last_block = None
            for cell in order:
                if cell["block"] != last_block:  # one receiver state/idle-slot check per root-balanced block
                    ph.interim_check(cell["root_id"])
                    last_block = cell["block"]
                root = by_root[cell["root_id"]]
                ph.generate(root["messages"][cell["arm"]], root, PHASE_NAME, cell["arm"], cell["replicate"])
            ph.postflight()
    except BaseException as exc:
        ledger.write({"event": "aborted", "error": f"{type(exc).__name__}: {exc}",
                      "attempted_calls": ph.attempted, "reserved_completion_tokens": ph.reserved})
        clock.persist(clock_path)
        raise
    if ph.attempted > dispatch_config["max_calls"] or ph.reserved > dispatch_config["max_completion_tokens"]:
        raise Refusal(f"accounting exceeded the caps: {ph.attempted} calls, {ph.reserved} reserved tokens")

    guard = ph.verification()
    verification = guard if real else {"status": "transport_only_not_a_measurement", "efficacy_interpretable": False,
                                       "reason": "injected adapter; no receiver was contacted", "receiver_guard": guard}
    slots = [{"root_id": c["root_id"], "arm": c["arm"], "replicate": c["replicate"],
              "attempted": c["attempted"], "missing_reason": c["missing_reason"],
              "artifact": ph.artifact_index.get(f"{c['root_id']}|{c['arm']}|{c['replicate']}")} for c in ph.calls]
    assigned = {(o["root_id"], o["arm"], o["replicate"]) for o in order}
    recorded = [(s["root_id"], s["arm"], s["replicate"]) for s in slots]
    if sorted(recorded) != sorted(assigned) or len(recorded) != len(assigned):
        raise Refusal("recorded slots are not exactly the assigned slots; no slot may be dropped or duplicated")
    # The ledger's last line is written BEFORE completion.json, so completion's checksums cover its final bytes.
    ledger.write({"event": "complete", "attempted_calls": ph.attempted, "reserved_completion_tokens": ph.reserved,
                  "slots_with_output": sum(s["artifact"] is not None for s in slots),
                  "slots_missing": sum(s["artifact"] is None for s in slots),
                  "fatal_error": ph.fatal, "verification": verification["status"],
                  "manifest_sha256": file_sha(out / "manifest.json")})
    completion = ph.completion(
        PHASE_NAME, table, planned, verification,
        arm_set=ARM_SET, stage="E13a", evidence_type=evidence, transport_only=not real,
        real_receiver=bool(real), adapter=type(adapter).__name__,
        stage_sha256=stage["stage_sha256"], plan_sha256=plan["plan_sha256"],
        manifest_sha256=file_sha(out / "manifest.json"),
        caps=manifest["caps"], stage_clock=clock.report(),
        time_binding=ph.clock_binding(),
        assigned_slots=len(assigned), recorded_slots=len(slots),
        slots_with_output=sum(s["artifact"] is not None for s in slots),
        slots_missing=sum(s["artifact"] is None for s in slots),
        missing_reasons={r: sum(1 for s in slots if s["missing_reason"] == r)
                         for r in sorted({s["missing_reason"] for s in slots if s["missing_reason"]})},
        retries=0, backfilled_slots=0, outcome_driven_stopping=False,
        slot_preservation="every assigned slot is recorded; a failed or unavailable attempt keeps its slot with a "
                          "missing_reason and is never retried or backfilled",
        per_arm={a: {"assigned": planned[a],
                     "with_output": sum(s["artifact"] is not None for s in slots if s["arm"] == a),
                     "missing": sum(s["artifact"] is None for s in slots if s["arm"] == a)} for a in ARMS},
        artifact_index=ph.artifact_index, slots=slots, ledger_file=LEDGER, ledger_lines=ledger.lines,
        byte_checks=built["byte_checks"], gating=built["gating"], inputs=built["inputs"],
        attestation_sha256=(attestation or {}).get("sha256"))
    clock.persist(clock_path)
    return completion


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="run directory; collection is written to <out>/collect")
    ap.add_argument("--stage", type=Path, default=STAGE)
    ap.add_argument("--plan", type=Path, default=PLAN)
    ap.add_argument("--release-dir", type=Path, default=None)
    ap.add_argument("--real", action="store_true", help="opt-in real receiver dispatch (freeze, attestation, guards)")
    ap.add_argument("--ownership", type=Path, help="--real: the receiver ownership/attestation record JSON")
    ap.add_argument("--rebuild-only", action="store_true", help="verify the 60 requests and print the checks; dispatch nothing")
    args = ap.parse_args(argv)
    stage = load_stage(args.stage, release_dir=args.release_dir)
    plan = load_plan(args.plan)
    if args.rebuild_only:
        built = rebuild(stage, plan)
        print(json.dumps({"checkpoints": built["checkpoints"], "byte_checks": built["byte_checks"],
                          "requests": sum(len(r["requests"]) for r in built["roots"]),
                          "dispatched": 0, "receiver_calls": 0}, indent=2))
        return None
    if args.real and args.ownership is None:
        ap.error("--real needs --ownership")
    result = dispatch(stage, plan, args.out, real=args.real, ownership=args.ownership)
    print(json.dumps({k: result[k] for k in ("phase", "evidence_type", "attempted_calls", "reserved_completion_tokens",
                                             "slots_with_output", "slots_missing", "fatal_error")}, indent=2))
    return result


if __name__ == "__main__":
    main()
