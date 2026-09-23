#!/usr/bin/env python3
"""E14 connected SOURCE/MOCK path, repaired under MRL-24 (lead 45f7aa7): criteria 1-3.

Evidence class: source/mock only. Transport, public checker and private scorer are INJECTED fakes in every test;
nothing here calls a receiver, runs a reference, control or candidate program, or starts a container. A passed
mock is not execution evidence and not efficacy evidence.

Repairs relative to scripts/e14_mock_path.py (MRL-23 partial, preserved unchanged at 18797b7):
  1. Collection and quality are separate. Transport completion is reported on its own; private success comes
     only from an injected scorer that consumes the exact bound answer bytes AFTER collection is closed. A
     score of 0 is an observed failure, never missing. Any unavailable primary grade suppresses the point
     contrast; completion bounds are [(S_D-S_N-M_N)/60, (S_D+M_D-S_N)/60] with no missing-at-random assumption.
  2. Failures are retained at the real entry point. All 130 planned slots are persisted before dispatch, and an
     attempt is recorded BEFORE each transport or checker call. Exceptions keep the plan, partial outputs,
     attempted/unknown usage and explicit remaining states. No retry, no silent resume. An integrity,
     receiver-law or environment fault stops every later transport AND public-check call, including
     diagnostics for answers already collected.
  3. One bound release. Tasks, config and public examples are read from the release directory the future
     adapter consumes, with the same public-context bytes and the same seed law; the lead spec is hashed from
     the path actually supplied. The E14 schema is the config's `e14` block, and a conflicting legacy field
     (e.g. an inherited `branch_replicates`) is refused as drift. Seed labels AND numeric seeds are checked
     against a declared historical inventory; an incomplete inventory is reported as an unresolved dependency,
     never read as "no collision". Reproducible, non-colliding seeds do not establish independent draws.
"""
from __future__ import annotations
import hashlib, json, os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect, diagnostic  # noqa: E402

ARMS = ("NEUTRAL", "DIRECTED")
STOPPING_FAULTS = ("IntegrityFault", "ReceiverLawFault", "EnvironmentFault")


class IntegrityFault(RuntimeError): ...
class ReceiverLawFault(RuntimeError): ...
class EnvironmentFault(RuntimeError): ...
class DriftRefused(ValueError): ...


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _jsonl(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


# ---------------------------------------------------------------- criterion 3: one bound release
def load_release(release_dir: Path, spec_path: Path) -> dict:
    release_dir, spec_path = Path(release_dir), Path(spec_path)
    raw = {n: (release_dir / n).read_bytes() for n in ("tasks.jsonl", "config.json", "public_examples_v3.json")}
    spec_bytes = spec_path.read_bytes()
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
        raise DriftRefused(f"legacy branch_replicates={legacy} conflicts with e14.draws_per_arm="
                           f"{e14['draws_per_arm']}; inherited field must be removed, not silently overridden")
    tasks = [json.loads(x) for x in raw["tasks.jsonl"].decode().splitlines() if x.strip()]
    order = [f"mbpp/{i}" for i in e14["roster_order"]]
    if [t["root_id"] for t in tasks] != order:
        raise DriftRefused("tasks.jsonl order differs from e14.roster_order")
    if e14["n_roots"] != len(tasks) or e14["call_slots"] != len(tasks) * (1 + len(ARMS) * e14["draws_per_arm"]):
        raise DriftRefused("slot arithmetic in the e14 block does not match the roster")
    spec = json.loads(spec_bytes)
    term = spec.get("terminal_instruction", {})
    if term.get("label") != e14["terminal_instruction_label"] or not isinstance(term.get("text"), str):
        raise DriftRefused("terminal instruction label/text do not match between spec and release")
    return {"release_dir": str(release_dir), "spec_path": str(spec_path), "config": config, "e14": e14,
            "tasks": tasks, "terminal_text": term["text"],
            "hashes": {**{n: _sha(b) for n, b in raw.items()}, "spec_as_supplied": _sha(spec_bytes)}}


def plan_slots(binding: dict, inventory: dict) -> tuple[list[dict], dict]:
    """All 130 slots, fixed before collection, with seed-collision evidence against a declared inventory."""
    cfg, draws = binding["config"], binding["e14"]["draws_per_arm"]
    slots, collisions, unresolved = [], [], []
    for t in binding["tasks"]:
        rid = t["root_id"]
        labels = ["initial"] + [f"{a}:{r}" for a in ARMS for r in range(draws)]
        spent = inventory.get("roots", {}).get(rid)
        if spent is None:
            unresolved.append(rid)
        for lab in labels:
            seed = collect.seeded(cfg, rid, lab)
            if spent is not None and (lab in spent.get("labels", ()) or seed in spent.get("numeric", ())):
                collisions.append({"root_id": rid, "label": lab, "seed": seed})
            slots.append({"slot": f"{rid}|{lab}", "root_id": rid, "label": lab, "seed": seed,
                          "kind": "initial" if lab == "initial" else "continuation",
                          "arm": None if lab == "initial" else lab.split(":")[0],
                          "state": "planned"})
    if collisions:
        raise DriftRefused(f"seed collision with the declared inventory: {collisions[:3]}")
    return slots, {"inventory_complete": bool(inventory.get("complete")) and not unresolved,
                   "roots_without_inventory": unresolved,
                   "note": ("an incomplete inventory is an unresolved dependency, not evidence of no collision; "
                            "reproducible non-colliding seeds do not establish independent draws")}


# ---------------------------------------------------------------- criterion 2: durable ledger
class Ledger:
    def __init__(self, run_dir: Path, header: dict, slots: list[dict]):
        self.path = Path(run_dir) / "ledger.json"
        self.doc = {"header": header, "slots": {s["slot"]: s for s in slots}, "collection_closed": False,
                    "stopped": None, "events": []}
        self.flush()

    def flush(self):
        fd, tmp = tempfile.mkstemp(dir=self.path.parent)
        with os.fdopen(fd, "w") as f:
            json.dump(self.doc, f, indent=1)
        os.replace(tmp, self.path)        # atomic: an abort never leaves a torn record

    def set(self, slot: str, **fields):
        self.doc["slots"][slot].update(fields)
        self.flush()

    def event(self, **e):
        self.doc["events"].append(e)
        self.flush()


def _fault_name(exc) -> str | None:
    return type(exc).__name__ if type(exc).__name__ in STOPPING_FAULTS else None


def run(release_dir, spec_path, run_dir, *, transport, public_checker, scorer, inventory, max_calls=130):
    """The single entry point. Writes the partial record at every step; refuses to resume."""
    run_dir = Path(run_dir)
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} exists: resume is refused; a new run needs a new directory")
    run_dir.mkdir(parents=True)
    binding = load_release(release_dir, spec_path)
    slots, seed_evidence = plan_slots(binding, inventory)
    led = Ledger(run_dir, {"evidence_type": "mock_transport_only", "hashes": binding["hashes"],
                           "seed_evidence": seed_evidence, "max_calls": max_calls}, slots)
    calls = 0
    draws = binding["e14"]["draws_per_arm"]

    def stop(reason):
        led.doc["stopped"] = reason
        for s in led.doc["slots"].values():
            if s["state"] == "planned":
                s["state"], s["reason"] = "not_attempted", f"stopped:{reason}"
        led.flush()

    def call(slot, messages):
        nonlocal calls
        if calls >= max_calls:
            stop("call_cap_exhausted")
            return None
        led.set(slot, state="attempting")          # recorded BEFORE the boundary
        calls += 1
        try:
            out = transport(messages, led.doc["slots"][slot]["seed"])
        except Exception as exc:  # noqa: BLE001 - every exception is retained, never retried
            led.set(slot, state="failed", reason=type(exc).__name__, usage="unknown")
            if _fault_name(exc):
                stop(_fault_name(exc))
            return None
        led.set(slot, state="completed", output=out["text"], output_sha256=_sha(out["text"].encode()),
                usage=out.get("usage", "unknown"))
        return out["text"]

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
        led.event(kind="public_check_attempt", root_id=rid)          # recorded BEFORE the boundary
        try:
            diag = public_checker(rid, answer)
        except Exception as exc:  # noqa: BLE001
            led.event(kind="public_check_failed", root_id=rid, reason=type(exc).__name__)
            stop(_fault_name(exc) or "EnvironmentFault")               # checker failure is environmental
            break
        shared = diagnostic.diagnostic_message(diag)
        prefix = [*base, {"role": "assistant", "content": answer}, dict(shared)]
        instr = {"NEUTRAL": diagnostic.N_INSTRUCTION, "DIRECTED": diagnostic.select_s1(diag)}
        msgs = {a: [*prefix, {"role": "user", "content": instr[a] + "\n\n" + binding["terminal_text"]}] for a in ARMS}
        if collect.digest(msgs["NEUTRAL"][:4]) != collect.digest(msgs["DIRECTED"][:4]):
            raise DriftRefused(f"shared prefix differs between arms at {rid}")
        led.event(kind="directed_instruction", root_id=rid, index=diagnostic.S1_STRINGS.index(instr["DIRECTED"]))
        for r in range(draws):
            for a in ARMS:
                if led.doc["stopped"]:
                    break
                call(f"{rid}|{a}:{r}", msgs[a])

    led.doc["collection_closed"] = True                          # scoring may start only after this
    led.flush()
    return led


# ---------------------------------------------------------------- criterion 1: private scoring after close
def score_private(led: Ledger, scorer) -> dict:
    if not led.doc["collection_closed"]:
        raise RuntimeError("private scoring may start only after collection is closed")
    for s in led.doc["slots"].values():
        if s["kind"] != "continuation":
            continue
        if s["state"] != "completed":
            s["grade"], s["grade_state"] = None, f"unavailable:{s['state']}"
            continue
        text = s["output"]
        if _sha(text.encode()) != s["output_sha256"]:
            raise DriftRefused(f"bound answer bytes changed for {s['slot']}")
        g = scorer(s["root_id"], text)                            # consumes the exact bound artifact
        if g not in (0, 1, None):
            raise ValueError(f"scorer returned {g!r}; must be 0, 1 or None (unavailable)")
        s["grade"], s["grade_state"] = g, ("unavailable:scorer" if g is None else "graded")
    led.flush()
    return analyse(led)


def analyse(led: Ledger, per_arm: int = 60) -> dict:
    cont = [s for s in led.doc["slots"].values() if s["kind"] == "continuation"]
    S = {a: sum(1 for s in cont if s["arm"] == a and s.get("grade") == 1) for a in ARMS}
    M = {a: sum(1 for s in cont if s["arm"] == a and s.get("grade") is None) for a in ARMS}
    transport = {a: sum(1 for s in cont if s["arm"] == a and s["state"] == "completed") for a in ARMS}
    sd, sn, md, mn = S["DIRECTED"], S["NEUTRAL"], M["DIRECTED"], M["NEUTRAL"]
    complete = md == 0 and mn == 0
    return {
        "successes": S, "unavailable_grades": M, "transport_completed": transport,
        "point_contrast": (sd - sn) / per_arm if complete else None,
        "point_contrast_suppressed": not complete,
        "completion_bounds": [(sd - sn - mn) / per_arm, (sd + md - sn) / per_arm],
        "bounds_kind": "finite all-assigned completion bounds; not a confidence interval for conditional means",
        "note": "a score of 0 is an observed failure, never missing; transport completion is not correctness",
    }
