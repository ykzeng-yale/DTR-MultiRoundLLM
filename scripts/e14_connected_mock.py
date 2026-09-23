#!/usr/bin/env python3
"""E14 connected SOURCE/MOCK path, version 3 (MRL-25, lead 38942de). Version 2 was reviewed at 1c66f86.

Evidence class: source/mock only. Transport, public checker and private scorer are INJECTED fakes in every test;
nothing here calls a receiver, runs a reference, control or candidate program, or starts a container. A passed
mock is not execution evidence and not efficacy evidence.

v3 repairs, each with a fixture that fails on the reviewed v2 module and passes here:
  1. Exact binding BEFORE any dispatch. The release manifest's sha256 must equal a trusted committed identity
     supplied by the caller; every package file must match its manifest pin; the supplied spec must match the
     manifest's approved spec hash. A changed terminal text under the same label, a changed task prompt, a
     changed manifest, or a relocated copy holding different bytes is refused with zero transport calls. A
     relocated copy holding identical bytes is accepted: identity is by content, not path.
  2. Explicit stop state at every boundary. Malformed transport returns, invalid public diagnostics or renders,
     request-byte violations, prefix drift and preflight receiver faults all leave a classified slot and a named
     stop reason, never an `attempting` slot or `stopped: null`.
  3. Scoring is durable. Each scoring attempt is persisted BEFORE the scorer is called and its result persisted
     before the next call; every attempted private-scoring start is counted in the same bounded start ledger. A
     scorer exception or invalid return stops scoring, keeps prior grades on disk, marks the rest unavailable
     (never zero), and leaves the point contrast suppressed with completion bounds still reported.

v2 behaviour retained: collection and quality separated; 130 slots persisted before dispatch; attempts recorded
before each boundary; no retry; resume refused; seed labels and numeric seeds checked against a declared
inventory, with an incomplete inventory reported as an unresolved dependency.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect, diagnostic  # noqa: E402

VERSION = "e14-connected-mock-v3"
ARMS = ("NEUTRAL", "DIRECTED")
STOPPING_FAULTS = ("IntegrityFault", "ReceiverLawFault", "EnvironmentFault", "MalformedTransportReturn")
RELEASE_MANIFEST_PATH = "experiments/landmark/e14_release_v2/release_manifest.json"
START_INVENTORY = {"containment": 18, "instrument": 40, "grader_rechecks": 30, "candidate": 140}
RECEIVER_FIELDS = ("model", "model_digest", "server_build", "receiver_state_sha256")


class IntegrityFault(RuntimeError): ...
class ReceiverLawFault(RuntimeError): ...
class EnvironmentFault(RuntimeError): ...
class MalformedTransportReturn(RuntimeError): ...
class DriftRefused(ValueError): ...
class StartCapExceeded(RuntimeError): ...


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def committed_manifest_sha256(rev: str = "HEAD", path: str = RELEASE_MANIFEST_PATH) -> str:
    """The trusted identity: the manifest's bytes as COMMITTED at a git revision, not as found on disk."""
    blob = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    return _sha(blob)


# ---------------------------------------------------------------- repair 1: exact binding before dispatch
def load_release(release_dir, spec_path, trusted_manifest_sha256: str) -> dict:
    release_dir, spec_path = Path(release_dir), Path(spec_path)
    if not isinstance(trusted_manifest_sha256, str) or len(trusted_manifest_sha256) != 64:
        raise DriftRefused("a trusted committed manifest sha256 is required; a hash recorded after reading is not a guard")
    manifest_bytes = (release_dir / "release_manifest.json").read_bytes()
    if _sha(manifest_bytes) != trusted_manifest_sha256:
        raise DriftRefused("release manifest differs from the trusted committed identity")
    manifest = json.loads(manifest_bytes)
    for name, pin in manifest["package"].items():
        if _sha((release_dir / name).read_bytes()) != pin:
            raise DriftRefused(f"{name} differs from its manifest pin")
    spec_bytes = spec_path.read_bytes()
    if _sha(spec_bytes) != manifest["lead_specification"]["sha256"]:
        raise DriftRefused("supplied spec differs from the manifest's approved spec hash")
    raw = {n: (release_dir / n).read_bytes() for n in ("tasks.jsonl", "config.json", "public_examples_v3.json")}
    config = json.loads(raw["config.json"])
    e14 = config.get("e14")
    if not isinstance(e14, dict):
        raise DriftRefused("config has no e14 block; the E14 schema is that block")
    need = {"roster_order": list, "n_roots": int, "arms": list, "draws_per_arm": int, "call_slots": int,
            "terminal_instruction_label": str}
    for k, t in need.items():
        if not isinstance(e14.get(k), t):
            raise DriftRefused(f"e14.{k} missing or not {t.__name__}")
    if list(e14["arms"]) != list(ARMS):
        raise DriftRefused(f"e14.arms {e14['arms']} != {list(ARMS)}")
    legacy = config.get("branch_replicates")
    if legacy is not None and legacy != e14["draws_per_arm"]:
        raise DriftRefused(f"legacy branch_replicates={legacy} conflicts with e14.draws_per_arm={e14['draws_per_arm']}")
    tasks = [json.loads(x) for x in raw["tasks.jsonl"].decode().splitlines() if x.strip()]
    if [t["root_id"] for t in tasks] != [f"mbpp/{i}" for i in e14["roster_order"]]:
        raise DriftRefused("tasks.jsonl order differs from e14.roster_order")
    if e14["n_roots"] != len(tasks) or e14["call_slots"] != len(tasks) * (1 + len(ARMS) * e14["draws_per_arm"]):
        raise DriftRefused("slot arithmetic in the e14 block does not match the roster")
    term = json.loads(spec_bytes).get("terminal_instruction", {})
    if term.get("label") != e14["terminal_instruction_label"] or not isinstance(term.get("text"), str):
        raise DriftRefused("terminal instruction label/text do not match between spec and release")
    return {"config": config, "e14": e14, "tasks": tasks, "terminal_text": term["text"],
            "hashes": {"release_manifest": trusted_manifest_sha256, **{n: _sha(b) for n, b in raw.items()},
                       "spec": _sha(spec_bytes)}}


def plan_slots(binding: dict, inventory: dict):
    cfg, draws = binding["config"], binding["e14"]["draws_per_arm"]
    slots, collisions, unresolved = [], [], []
    for t in binding["tasks"]:
        rid = t["root_id"]
        spent = inventory.get("roots", {}).get(rid)
        if spent is None:
            unresolved.append(rid)
        for lab in ["initial"] + [f"{a}:{r}" for a in ARMS for r in range(draws)]:
            seed = collect.seeded(cfg, rid, lab)
            if spent is not None and (lab in spent.get("labels", ()) or seed in spent.get("numeric", ())):
                collisions.append({"root_id": rid, "label": lab, "seed": seed})
            slots.append({"slot": f"{rid}|{lab}", "root_id": rid, "label": lab, "seed": seed,
                          "kind": "initial" if lab == "initial" else "continuation",
                          "arm": None if lab == "initial" else lab.split(":")[0], "state": "planned"})
    if collisions:
        raise DriftRefused(f"seed collision with the declared inventory: {collisions[:3]}")
    return slots, {"inventory_complete": bool(inventory.get("complete")) and not unresolved,
                   "roots_without_inventory": unresolved,
                   "note": ("an incomplete inventory is an unresolved dependency, not evidence of no collision; "
                            "reproducible non-colliding seeds do not establish independent draws")}


class StartLedger:
    """Every attempted or uncertain isolated start counts against its category and the 228 total."""

    def __init__(self, inventory=START_INVENTORY):
        self.caps, self.used, self.events = dict(inventory), {k: 0 for k in inventory}, []

    def record(self, kind, state, note=None):
        if kind not in self.caps:
            raise KeyError(f"undeclared start category {kind!r}")
        if state not in ("attempted", "uncertain"):
            raise ValueError("only attempted or uncertain starts are recorded; both count")
        if self.used[kind] >= self.caps[kind]:
            raise StartCapExceeded(f"{kind} start cap {self.caps[kind]} reached")
        self.used[kind] += 1
        self.events.append({"kind": kind, "state": state, "note": note})

    def summary(self):
        return {"caps": self.caps, "used": self.used, "total_cap": sum(self.caps.values()),
                "total_used": sum(self.used.values()), "actual_program_starts": 0}


def check_receiver(binding, observed, when):
    cfg = binding["config"]
    bad = {k: (cfg.get(k), observed.get(k)) for k in RECEIVER_FIELDS if observed.get(k) != cfg.get(k)}
    if bad:
        raise ReceiverLawFault(f"{when} receiver mismatch: {bad}")


class Ledger:
    def __init__(self, run_dir, header, slots, starts):
        self.path, self.starts = Path(run_dir) / "ledger.json", starts
        self.doc = {"header": header, "slots": {s["slot"]: s for s in slots}, "collection_closed": False,
                    "stopped": None, "scoring_stopped": None, "events": [], "start_ledger": starts.summary()}
        self.flush()

    def flush(self):
        self.doc["start_ledger"] = self.starts.summary()
        fd, tmp = tempfile.mkstemp(dir=self.path.parent)
        with os.fdopen(fd, "w") as f:
            json.dump(self.doc, f, indent=1)
        os.replace(tmp, self.path)

    def set(self, slot, **fields):
        self.doc["slots"][slot].update(fields)
        self.flush()

    def event(self, **e):
        self.doc["events"].append(e)
        self.flush()


def _stop(led, reason):
    led.doc["stopped"] = led.doc["stopped"] or reason
    for s in led.doc["slots"].values():
        if s["state"] in ("planned", "attempting"):
            s["reason"] = s.get("reason") or f"stopped:{reason}"
            s["state"] = "not_attempted" if s["state"] == "planned" else "failed"
    led.flush()


# ---------------------------------------------------------------- repair 2: explicit stop at every boundary
def run(release_dir, spec_path, run_dir, *, transport, public_checker, scorer, inventory,
        trusted_manifest_sha256, max_calls=130, receiver_state=None, clock=None, starts=None):
    run_dir = Path(run_dir)
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} exists: resume is refused; a new run needs a new directory")
    binding = load_release(release_dir, spec_path, trusted_manifest_sha256)     # refuses BEFORE any dispatch
    slots, seed_evidence = plan_slots(binding, inventory)
    run_dir.mkdir(parents=True)
    starts = starts if starts is not None else StartLedger()
    led = Ledger(run_dir, {"version": VERSION, "evidence_type": "mock_transport_only", "hashes": binding["hashes"],
                           "seed_evidence": seed_evidence, "max_calls": max_calls}, slots, starts)
    cfg, draws = binding["config"], binding["e14"]["draws_per_arm"]
    limits = binding["e14"].get("phase_limits_seconds") or {"collection": cfg.get("max_seconds"), "outer": None}
    max_bytes, t0 = cfg.get("max_request_bytes"), (clock() if clock else None)
    calls = 0

    if receiver_state is not None:
        try:
            check_receiver(binding, receiver_state(), "preflight")
        except ReceiverLawFault:
            _stop(led, "ReceiverLawFault:preflight")
            led.doc["collection_closed"] = True
            led.flush()
            raise

    def call(slot, messages):
        nonlocal calls
        if calls >= max_calls:
            _stop(led, "call_cap_exhausted")
            return None
        if clock is not None:
            el = clock() - t0
            if limits.get("outer") is not None and el >= limits["outer"]:
                _stop(led, "outer_limit_exhausted")
                return None
            if limits.get("collection") is not None and el >= limits["collection"]:
                _stop(led, "collection_phase_limit_exhausted")
                return None
        size = len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
        if max_bytes is not None and size > max_bytes:          # request-law violation: stop the batch now
            led.set(slot, state="not_attempted", reason=f"request_bytes_exceeded:{size}>{max_bytes}")
            _stop(led, "RequestByteLimit")
            return None
        led.set(slot, state="attempting")
        calls += 1
        try:
            out = transport(messages, led.doc["slots"][slot]["seed"])
            text = out.get("text") if isinstance(out, dict) else None   # never index: a missing key is malformed
            if not isinstance(text, str):
                raise MalformedTransportReturn(f"transport returned {type(out).__name__} without a str 'text'")
        except Exception as exc:  # noqa: BLE001 - retained, classified, never retried
            name = type(exc).__name__ if type(exc).__name__ in STOPPING_FAULTS else None
            led.set(slot, state="failed", reason=type(exc).__name__, usage="unknown")
            if name:
                _stop(led, name)
            return None
        led.set(slot, state="completed", output=text, output_sha256=_sha(text.encode()),
                usage=out.get("usage", "unknown"))
        return text

    for task in binding["tasks"]:
        if led.doc["stopped"]:
            break
        rid = task["root_id"]
        base = collect.initial_messages(task)
        answer = call(f"{rid}|initial", base)
        if answer is None:
            for a in ARMS:
                for r in range(draws):
                    k = f"{rid}|{a}:{r}"
                    if led.doc["slots"][k]["state"] == "planned":
                        led.set(k, state="not_attempted", reason="initial_failed")
            continue
        if led.doc["stopped"]:
            break
        led.event(kind="public_check_attempt", root_id=rid)
        try:
            starts.record("candidate", "attempted", "initial-public")
        except StartCapExceeded:
            _stop(led, "start_cap_exhausted")
            break
        try:
            diag = public_checker(rid, answer)
        except Exception as exc:  # noqa: BLE001
            led.event(kind="public_check_failed", root_id=rid, reason=type(exc).__name__)
            _stop(led, type(exc).__name__ if type(exc).__name__ in STOPPING_FAULTS else "EnvironmentFault")
            break
        try:                                                    # an invalid diagnostic or render stops the batch
            shared = diagnostic.diagnostic_message(diag)
            directed = diagnostic.select_s1(diag)
        except Exception as exc:  # noqa: BLE001
            led.event(kind="public_diagnostic_invalid", root_id=rid, reason=f"{type(exc).__name__}: {exc}"[:200])
            _stop(led, "InvalidPublicDiagnostic")
            break
        prefix = [*base, {"role": "assistant", "content": answer}, dict(shared)]
        instr = {"NEUTRAL": diagnostic.N_INSTRUCTION, "DIRECTED": directed}
        msgs = {a: [*prefix, {"role": "user", "content": instr[a] + "\n\n" + binding["terminal_text"]}] for a in ARMS}
        if collect.digest(msgs["NEUTRAL"][:4]) != collect.digest(msgs["DIRECTED"][:4]):
            _stop(led, "SharedPrefixDrift")
            break
        led.event(kind="directed_instruction", root_id=rid, index=diagnostic.S1_STRINGS.index(directed))
        for r in range(draws):
            for a in ARMS:
                if led.doc["stopped"]:
                    break
                call(f"{rid}|{a}:{r}", msgs[a])

    if receiver_state is not None and not led.doc["stopped"]:
        try:
            check_receiver(binding, receiver_state(), "postflight")
        except ReceiverLawFault as exc:
            led.doc["postflight_drift"] = str(exc)
    led.doc["collection_closed"] = True
    led.flush()
    return led


# ---------------------------------------------------------------- repair 3: durable, counted scoring
def score_private(led, scorer):
    if not led.doc["collection_closed"]:
        raise RuntimeError("private scoring may start only after collection is closed")
    halted = None
    for s in led.doc["slots"].values():
        if s["kind"] != "continuation":
            continue
        if s["state"] != "completed":
            s["grade"], s["grade_state"] = None, f"unavailable:{s['state']}"
            continue
        if halted:
            s["grade"], s["grade_state"] = None, f"unavailable:not_scored_after_{halted}"
            continue
        if _sha(s["output"].encode()) != s["output_sha256"]:
            halted = "bound_answer_drift"
            s["grade"], s["grade_state"] = None, "unavailable:bound_answer_drift"
            continue
        try:
            led.starts.record("candidate", "attempted", "continuation-private")
        except StartCapExceeded:
            halted = "start_cap_exhausted"
            s["grade"], s["grade_state"] = None, "unavailable:start_cap_exhausted"
            continue
        s["grade_state"] = "scoring_attempt"                      # persisted BEFORE the scorer boundary
        led.flush()
        try:
            g = scorer(s["root_id"], s["output"])
            if g not in (0, 1, None) or isinstance(g, bool):
                raise ValueError(f"invalid scorer return {g!r}")
        except Exception as exc:  # noqa: BLE001 - kept, classified, never converted to zero
            halted = type(exc).__name__
            s["grade"], s["grade_state"] = None, f"unavailable:scorer_{type(exc).__name__}"
            led.flush()
            continue
        s["grade"], s["grade_state"] = g, ("unavailable:scorer" if g is None else "graded")
        led.flush()                                              # persisted BEFORE the next scorer call
    led.doc["scoring_stopped"] = halted
    led.flush()
    return analyse(led)


def analyse(led, per_arm: int = 60):
    cont = [s for s in led.doc["slots"].values() if s["kind"] == "continuation"]
    S = {a: sum(1 for s in cont if s["arm"] == a and s.get("grade") == 1) for a in ARMS}
    M = {a: sum(1 for s in cont if s["arm"] == a and s.get("grade") is None) for a in ARMS}
    transport = {a: sum(1 for s in cont if s["arm"] == a and s["state"] == "completed") for a in ARMS}
    sd, sn, md, mn = S["DIRECTED"], S["NEUTRAL"], M["DIRECTED"], M["NEUTRAL"]
    complete = md == 0 and mn == 0
    return {"successes": S, "unavailable_grades": M, "transport_completed": transport,
            "point_contrast": (sd - sn) / per_arm if complete else None,
            "point_contrast_suppressed": not complete,
            "completion_bounds": [(sd - sn - mn) / per_arm, (sd + md - sn) / per_arm],
            "bounds_kind": "finite all-assigned completion bounds; not a confidence interval for conditional means",
            "note": "a score of 0 is an observed failure, never missing; transport completion is not correctness"}
