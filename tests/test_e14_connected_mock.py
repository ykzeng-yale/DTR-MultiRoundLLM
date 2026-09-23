"""MRL-24 criteria 1-3 through the real entry point, with injected fakes only. No program or model execution."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import e14_connected_mock as cm  # noqa: E402
from experiments.landmark import collect, diagnostic  # noqa: E402

RELEASE = ROOT / "experiments/landmark/e14_release"
SPEC = ROOT / "docs/e14_lead_measurement_spec_20260923.json"
SCHEMA = "public-diagnostic-v2"
FULL_INV = {"complete": True, "roots": {}}


@pytest.fixture
def release(tmp_path):
    """The MRL-23 package with ONLY the inherited legacy replicate field removed (the v2 correction)."""
    d = tmp_path / "rel"
    shutil.copytree(RELEASE, d)
    cfg = json.loads((d / "config.json").read_text())
    cfg.pop("branch_replicates")
    (d / "config.json").write_text(json.dumps(cfg))
    return d


@pytest.fixture
def full_inventory(release):
    tasks = [json.loads(x) for x in (release / "tasks.jsonl").read_text().splitlines() if x.strip()]
    return {"complete": True, "roots": {t["root_id"]: {"labels": [], "numeric": []} for t in tasks}}


def diag(rid, status="wrong_value"):
    assert SCHEMA in diagnostic.SCHEMAS
    return {"schema_version": SCHEMA, "root_id": rid, "cases": [{"case_id": "public-1", "status": status}]}


class Fakes:
    def __init__(self, raise_on=None, checker_raises=None, status="wrong_value"):
        self.raise_on, self.checker_raises, self.status = raise_on or {}, checker_raises, status
        self.transport_calls, self.checker_calls, self.messages = [], [], {}

    def transport(self, messages, seed):
        slot = None
        for s, m in self.messages.items():
            if m is messages:
                slot = s
        self.transport_calls.append(seed)
        exc = self.raise_on.get(len(self.transport_calls))
        if exc:
            raise exc
        return {"text": f"def f():\n    return {seed}\n", "usage": {"completion_tokens": 5}}

    def checker(self, rid, answer):
        self.checker_calls.append(rid)
        if self.checker_raises and len(self.checker_calls) == self.checker_raises[0]:
            raise self.checker_raises[1]
        return diag(rid, self.status)


def grade_by_seed(led, plan):
    """scorer factory: plan maps (arm, index-within-arm) -> 1/0/None using the ledger's stable slot order."""
    order = {}
    for arm in cm.ARMS:
        arm_slots = [s for s in led.doc["slots"].values() if s["arm"] == arm]
        for i, s in enumerate(arm_slots):
            order[str(s["seed"])] = plan(arm, i)
    return lambda rid, text: order[text.split("return ")[1].strip()]


def run(release, tmp_path, fakes, inv, **kw):
    return cm.run(release, SPEC, tmp_path / "run", transport=fakes.transport,
                  public_checker=fakes.checker, scorer=None, inventory=inv, **kw)


# ---------------- criterion 3
def test_actual_mrl23_package_is_refused_for_inherited_replicate_drift(tmp_path):
    with pytest.raises(cm.DriftRefused, match="branch_replicates=2 conflicts with e14.draws_per_arm=6"):
        cm.run(RELEASE, SPEC, tmp_path / "r", transport=None, public_checker=None, scorer=None,
               inventory=FULL_INV)


def test_binds_release_prompt_bytes_and_seed_law(release, tmp_path, full_inventory):
    f = Fakes()
    led = run(release, tmp_path, f, full_inventory)
    cfg = json.loads((release / "config.json").read_text())
    first = json.loads((release / "tasks.jsonl").read_text().splitlines()[0])
    s0 = led.doc["slots"][f"{first['root_id']}|initial"]
    assert s0["seed"] == collect.seeded(cfg, first["root_id"], "initial") == f.transport_calls[0]
    assert led.doc["header"]["hashes"]["spec_as_supplied"]


def test_spec_drift_and_seed_collision_are_refused(release, tmp_path, full_inventory):
    bad = tmp_path / "spec.json"
    s = json.loads(SPEC.read_text()); s["terminal_instruction"]["label"] = "other"
    bad.write_text(json.dumps(s))
    with pytest.raises(cm.DriftRefused, match="terminal instruction"):
        cm.run(release, bad, tmp_path / "a", transport=None, public_checker=None, scorer=None,
               inventory=full_inventory)
    rid = next(iter(full_inventory["roots"]))
    full_inventory["roots"][rid]["labels"] = ["NEUTRAL:0"]
    with pytest.raises(cm.DriftRefused, match="seed collision"):
        cm.run(release, SPEC, tmp_path / "b", transport=None, public_checker=None, scorer=None,
               inventory=full_inventory)


def test_incomplete_inventory_is_an_unresolved_dependency_not_no_collision(release, tmp_path):
    led = run(release, tmp_path, Fakes(), {"complete": False, "roots": {}})
    ev = led.doc["header"]["seed_evidence"]
    assert ev["inventory_complete"] is False and len(ev["roots_without_inventory"]) == 10


# ---------------- criterion 2
def test_all_130_slots_persisted_before_dispatch_and_attempt_recorded_before_boundary(release, tmp_path, full_inventory):
    seen = {}

    class Probe(Fakes):
        def transport(self, messages, seed):
            doc = json.loads((tmp_path / "run" / "ledger.json").read_text())
            if not seen:
                seen["n"] = len(doc["slots"])
            seen.setdefault("attempting", []).append(
                sum(1 for s in doc["slots"].values() if s["state"] == "attempting"))
            return super().transport(messages, seed)

    run(release, tmp_path, Probe(), full_inventory)
    assert seen["n"] == 130
    assert all(n == 1 for n in seen["attempting"])      # the current slot is marked before every call


def test_failed_initial_leaves_its_twelve_branches_missing_and_run_continues(release, tmp_path, full_inventory):
    f = Fakes(raise_on={1: RuntimeError("transport error")})
    led = run(release, tmp_path, f, full_inventory)
    first = next(iter(led.doc["slots"].values()))["root_id"]
    branches = [s for s in led.doc["slots"].values() if s["root_id"] == first and s["kind"] == "continuation"]
    assert len(branches) == 12 and all(s["state"] == "not_attempted" and s["reason"] == "initial_failed" for s in branches)
    assert led.doc["slots"][f"{first}|initial"]["state"] == "failed"
    assert led.doc["stopped"] is None and len(f.transport_calls) == 1 + 9 * 13   # no retry, others ran


def test_thrown_continuation_is_retained_not_retried(release, tmp_path, full_inventory):
    f = Fakes(raise_on={2: RuntimeError("timeout")})           # first continuation of root 1
    led = run(release, tmp_path, f, full_inventory)
    failed = [s for s in led.doc["slots"].values() if s["state"] == "failed"]
    assert len(failed) == 1 and failed[0]["usage"] == "unknown" and failed[0]["kind"] == "continuation"
    assert len(f.transport_calls) == 130                       # attempted once, never re-drawn


def test_integrity_fault_after_one_successful_initial_stops_transport_and_checks(release, tmp_path, full_inventory):
    f = Fakes(raise_on={14: cm.IntegrityFault("receiver changed")})   # root 2's initial
    led = run(release, tmp_path, f, full_inventory)
    assert led.doc["stopped"] == "IntegrityFault"
    assert f.checker_calls == [next(iter(led.doc["slots"].values()))["root_id"]]   # only root 1's, before the fault
    assert len(f.transport_calls) == 14
    rest = [s for s in led.doc["slots"].values() if s["state"] == "not_attempted"]
    assert len(rest) == 116 and all(s["reason"] == "stopped:IntegrityFault" for s in rest)


def test_thrown_checker_stops_everything_after_it(release, tmp_path, full_inventory):
    f = Fakes(checker_raises=(1, OSError("sandbox unavailable")))
    led = run(release, tmp_path, f, full_inventory)
    assert led.doc["stopped"] == "EnvironmentFault"
    assert len(f.transport_calls) == 1 and f.checker_calls == [f.checker_calls[0]]
    assert sum(1 for s in led.doc["slots"].values() if s["state"] == "not_attempted") == 129


def test_incomplete_diagnostic_uses_the_predeclared_public_only_instruction(release, tmp_path, full_inventory):
    led = run(release, tmp_path, Fakes(status="unavailable"), full_inventory)
    idx = {e["index"] for e in led.doc["events"] if e["kind"] == "directed_instruction"}
    assert idx == {diagnostic.S1_STRINGS.index(diagnostic.S1_STRINGS[1])}


def test_mid_root_cap_exhaustion_keeps_every_slot_with_a_reason(release, tmp_path, full_inventory):
    led = run(release, tmp_path, Fakes(), full_inventory, max_calls=20)   # cuts inside root 2
    states = [s["state"] for s in led.doc["slots"].values()]
    assert states.count("completed") == 20 and states.count("not_attempted") == 110
    assert led.doc["stopped"] == "call_cap_exhausted"


def test_resume_is_refused_and_the_first_record_is_untouched(release, tmp_path, full_inventory):
    run(release, tmp_path, Fakes(), full_inventory)
    before = (tmp_path / "run" / "ledger.json").read_bytes()
    with pytest.raises(FileExistsError, match="resume is refused"):
        run(release, tmp_path, Fakes(), full_inventory)
    assert (tmp_path / "run" / "ledger.json").read_bytes() == before


# ---------------- criterion 1
def _scored(release, tmp_path, inv, plan):
    led = run(release, tmp_path, Fakes(), inv)
    return cm.score_private(led, grade_by_seed(led, plan))


def test_complete_fixture_gives_point_02(release, tmp_path, full_inventory):
    r = _scored(release, tmp_path, full_inventory,
                lambda a, i: 1 if (a == "DIRECTED" and i < 30) or (a == "NEUTRAL" and i < 18) else 0)
    assert r["point_contrast"] == pytest.approx(0.2) and r["point_contrast_suppressed"] is False


def test_missing_grades_suppress_point_and_give_exact_bounds(release, tmp_path, full_inventory):
    def plan(a, i):
        if a == "DIRECTED":
            return 1 if i < 30 else (None if i < 32 else 0)
        return 1 if i < 18 else (None if i < 21 else 0)
    r = _scored(release, tmp_path, full_inventory, plan)
    assert r["point_contrast"] is None and r["point_contrast_suppressed"] is True
    assert r["completion_bounds"] == pytest.approx([0.15, 14 / 60])
    assert r["transport_completed"] == {"NEUTRAL": 60, "DIRECTED": 60}   # delivered, yet grades missing


def test_all_missing_directed_arm(release, tmp_path, full_inventory):
    r = _scored(release, tmp_path, full_inventory, lambda a, i: None if a == "DIRECTED" else (1 if i < 18 else 0))
    assert r["completion_bounds"] == pytest.approx([-0.3, 0.7]) and r["point_contrast"] is None


def test_zero_is_observed_failure_not_missing(release, tmp_path, full_inventory):
    r = _scored(release, tmp_path, full_inventory, lambda a, i: 0)
    assert r["unavailable_grades"] == {"NEUTRAL": 0, "DIRECTED": 0} and r["point_contrast"] == 0.0


def test_scoring_before_close_is_refused(release, tmp_path, full_inventory):
    led = run(release, tmp_path, Fakes(), full_inventory)
    led.doc["collection_closed"] = False
    with pytest.raises(RuntimeError, match="only after collection is closed"):
        cm.score_private(led, lambda r, t: 1)


# ---------------- criterion 4: guards must REJECT, limits must bind, every start counts
V2 = ROOT / "experiments/landmark/e14_release_v2"


def _v2_inventory():
    tasks = [json.loads(x) for x in (V2 / "tasks.jsonl").read_text().splitlines() if x.strip()]
    return {"complete": True, "roots": {t["root_id"]: {"labels": [], "numeric": []} for t in tasks}}


def _good_state():
    cfg = json.loads((V2 / "config.json").read_text())
    return {k: cfg[k] for k in cm.RECEIVER_FIELDS}


def _run_v2(tmp_path, fakes, **kw):
    return cm.run(V2, SPEC, tmp_path / "run", transport=fakes.transport, public_checker=fakes.checker,
                  scorer=None, inventory=_v2_inventory(), **kw)


def test_preflight_receiver_mismatch_is_refused_before_any_dispatch(tmp_path):
    f = Fakes()
    bad = {**_good_state(), "model_digest": "0" * 64}
    with pytest.raises(cm.ReceiverLawFault, match="preflight receiver mismatch"):
        _run_v2(tmp_path, f, receiver_state=lambda: bad)
    assert f.transport_calls == [] and f.checker_calls == []
    doc = json.loads((tmp_path / "run" / "ledger.json").read_text())
    assert sum(1 for s in doc["slots"].values() if s["state"] == "planned") == 130   # plan kept, nothing sent


def test_postflight_drift_is_recorded_not_hidden(tmp_path):
    states = iter([_good_state(), {**_good_state(), "server_build": "b2-changed"}])
    led = _run_v2(tmp_path, Fakes(), receiver_state=lambda: next(states))
    assert "postflight receiver mismatch" in led.doc["postflight_drift"]


def test_per_request_byte_limit_blocks_the_request_without_calling_transport(tmp_path):
    rel = tmp_path / "rel"
    shutil.copytree(V2, rel)
    cfg = json.loads((rel / "config.json").read_text()); cfg["max_request_bytes"] = 50
    (rel / "config.json").write_text(json.dumps(cfg))
    f = Fakes()
    led = cm.run(rel, SPEC, tmp_path / "run", transport=f.transport, public_checker=f.checker, scorer=None,
                 inventory=_v2_inventory())
    assert f.transport_calls == []
    reasons = {s.get("reason", "").split(":")[0] for s in led.doc["slots"].values() if s["kind"] == "initial"}
    assert reasons == {"request_bytes_exceeded"}


def test_collection_phase_limit_binds_through_the_clock(tmp_path):
    t = {"now": 0.0}

    def clock():
        t["now"] += 10.0          # every guard check advances 10 s
        return t["now"]
    led = _run_v2(tmp_path, Fakes(), clock=clock)
    assert led.doc["stopped"] == "collection_phase_limit_exhausted"
    assert 0 < sum(1 for s in led.doc["slots"].values() if s["state"] == "completed") < 130


def test_outer_limit_binds(tmp_path):
    t = iter([0.0] + [5000.0] * 500)
    led = _run_v2(tmp_path, Fakes(), clock=lambda: next(t))
    assert led.doc["stopped"] == "outer_limit_exhausted"


def test_start_ledger_inventory_is_228_and_uncertain_starts_count():
    sl = cm.StartLedger()
    assert sl.summary()["total_cap"] == 228 == 18 + 40 + 30 + 140
    sl.record("candidate", "uncertain")
    assert sl.summary()["used"]["candidate"] == 1 and sl.summary()["actual_program_starts"] == 0
    with pytest.raises(KeyError):
        sl.record("public_score", "attempted")
    small = cm.StartLedger({"containment": 1, "instrument": 0, "grader_rechecks": 0, "candidate": 0})
    small.record("containment", "attempted")
    with pytest.raises(cm.StartCapExceeded):
        small.record("containment", "uncertain")


def test_start_cap_stops_the_connected_run(tmp_path):
    sl = cm.StartLedger({"containment": 18, "instrument": 40, "grader_rechecks": 30, "candidate": 3})
    f = Fakes()
    led = _run_v2(tmp_path, f, starts=sl)
    assert led.doc["stopped"] == "start_cap_exhausted" and len(f.checker_calls) == 3
    assert led.doc["start_ledger"]["used"]["candidate"] == 3
