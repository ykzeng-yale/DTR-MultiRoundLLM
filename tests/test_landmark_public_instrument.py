"""Fake-runner tests for the public-instrument validation driver; sandbox.run_program is never reached."""
import json
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

from experiments.landmark import grade, public_check, sandbox
from experiments.landmark import public_instrument_validation as piv

ITEMS = piv.ITEMS_PATH
SHA = piv.sha256_bytes(ITEMS.read_bytes())


@pytest.fixture(autouse=True)
def no_real_sandbox(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("sandbox.run_program must never be reached in tests")
    monkeypatch.setattr(sandbox, "run_program", boom)
    monkeypatch.setattr(grade, "verify_attestation", lambda p: {"checked_at": "2026-09-21T00:00:00+00:00"})


@pytest.fixture
def att(tmp_path):
    p = tmp_path / "attestation.json"
    p.write_text("{}")
    return p


class FakeRunner:
    FAKE_RUNNER = True

    def __init__(self, fail_at=None):
        self.calls, self.fail_at = 0, fail_at

    def __call__(self, program, **kw):
        self.calls += 1
        if self.fail_at is not None and self.calls == self.fail_at:
            raise KeyboardInterrupt("simulated interruption")
        return {"stdout": "", "returncode": 1, "timed_out": False}  # classified infrastructure_not_started


def ledger(out):
    return [json.loads(l) for l in (out / "ledger.jsonl").read_text().splitlines()]


def test_fixture_is_deterministic_and_counts():
    assert piv.items_bytes(piv.build_items(permitted_path=json.loads(ITEMS.read_bytes())["gates"]["E2"][1]["permitted_path"])) == ITEMS.read_bytes()
    doc = json.loads(ITEMS.read_bytes())
    assert {g: len(v) for g, v in doc["gates"].items()} == {"E2": 2, "E6": 7, "E7": 17}
    e7 = doc["gates"]["E7"]
    assert len({(i["root_id"], i["control_index"]) for i in e7}) == 17
    assert len({i["root_id"] for i in e7}) == 7 and len({i["root_id"] for i in doc["gates"]["E6"]}) == 7
    specs = [json.loads(l) for l in piv.V1C_SPECS.read_text().splitlines() if l.strip()]
    want = {(s["root_id"], ci, piv.sha256_bytes(c["code"].encode())) for s in specs for ci, c in enumerate(s["negative_controls"])}
    assert {(i["root_id"], i["control_index"], i["code_sha256"]) for i in e7} == want
    for gate in doc["gates"].values():
        for it in gate:
            assert public_check.static_code(piv._fence(it["code"])) is not None  # parse only
    canary = doc["gates"]["E2"][0]
    assert str(piv.REBOUND_SPECS) in canary["code"] and canary["private_path"] == str(piv.REBOUND_SPECS)


@pytest.mark.parametrize("gate,n", [("E2", 2), ("E6", 7), ("E7", 17)])
def test_exact_starts_and_preserved_identities(tmp_path, att, gate, n):
    out, fake = tmp_path / "out", FakeRunner()
    res = piv.run(ITEMS, SHA, gate, out, att, True, runner=fake)
    assert fake.calls == n and res["actual_starts"] == n and res["planned_max_starts"] == n
    recs = ledger(out)
    assert recs[0]["event"] == "reserved" and recs[0]["fake_runner"] is True and recs[-1]["event"] == "complete"
    assert set(recs[0]["source_sha256"]) == set(piv.PROVENANCE_SOURCES)
    assert [r["event"] for r in recs[1:-1]] == ["start", "result"] * n
    items = json.loads(ITEMS.read_bytes())["gates"][gate]
    assert [(r["item_id"], r["root_id"], r["control_index"], r["code_sha256"]) for r in res["rows"]] == \
        [(i["item_id"], i["root_id"], i.get("control_index"), i["code_sha256"]) for i in items]
    if gate == "E7":  # fake gives unavailable everywhere; disagreement is reported, not tuned
        assert all("predicted_pass_pattern" in r for r in res["rows"])
    else:
        assert res["all_meet_expected"] is False


def test_refusals(tmp_path, att, monkeypatch):
    with pytest.raises(SystemExit, match="--real"):
        piv.run(ITEMS, SHA, "E6", tmp_path / "a", att, False, runner=FakeRunner())
    (tmp_path / "exists").mkdir()
    with pytest.raises(SystemExit, match="overwrite"):
        piv.run(ITEMS, SHA, "E6", tmp_path / "exists", att, True, runner=FakeRunner())
    with pytest.raises(SystemExit, match="sha256 mismatch"):
        piv.run(ITEMS, "0" * 64, "E6", tmp_path / "b", att, True, runner=FakeRunner())
    assert not (tmp_path / "b").exists()
    def bad_att(p):
        raise ValueError("Containment attestation did not pass")
    monkeypatch.setattr(grade, "verify_attestation", bad_att)
    fake = FakeRunner()
    with pytest.raises(ValueError, match="attestation"):
        piv.run(ITEMS, SHA, "E6", tmp_path / "c", att, True, runner=fake)
    assert fake.calls == 0 and not (tmp_path / "c").exists()


def test_refuses_unresolved_and_unmarked_runner(tmp_path, att):
    doc = json.loads(ITEMS.read_bytes())
    doc["gates"]["E6"][0]["criterion"] = "UNRESOLVED: pending"
    bad = tmp_path / "items.json"
    bad.write_bytes(piv.items_bytes(doc))
    with pytest.raises(ValueError, match="unresolved"):
        piv.run(bad, piv.sha256_bytes(bad.read_bytes()), "E6", tmp_path / "o", att, True, runner=FakeRunner())
    with pytest.raises(SystemExit, match="FAKE_RUNNER"):
        piv.run(ITEMS, SHA, "E6", tmp_path / "p", att, True, runner=lambda program, **kw: {})


def test_durable_incomplete_when_runner_raises(tmp_path, att):
    out, fake = tmp_path / "out", FakeRunner(fail_at=3)
    with pytest.raises(KeyboardInterrupt):
        piv.run(ITEMS, SHA, "E7", out, att, True, runner=fake)
    recs = ledger(out)
    assert [r["event"] for r in recs] == ["reserved", "start", "result", "start", "result", "start", "INCOMPLETE"]
    assert recs[-1]["actual_starts"] == 3 and recs[-1]["planned_max_starts"] == 17 and not (out / "result.json").exists()


def test_e2_leak_check_and_pass_path(tmp_path, att):
    doc = json.loads(ITEMS.read_bytes())
    canary = doc["gates"]["E2"][0]
    obs = [{"status": "pass", "reason": None}] * 3
    assert piv.evaluate(canary, obs, [""])["meets_expected"] is (Path(canary["private_path"]).exists())
    if Path(canary["private_path"]).exists():
        leak = piv._private_markers(canary["private_path"])[0]
        row = piv.evaluate(canary, obs, [leak])
        assert row["private_bytes_in_stdout"] is True and row["meets_expected"] is False


class RaisingRunner:
    FAKE_RUNNER = True

    def __init__(self):
        self.calls = 0

    def __call__(self, program, **kw):
        self.calls += 1
        raise OSError("simulated infrastructure failure")


def test_e7_infrastructure_failure_is_not_agreement(tmp_path, att):
    # MRL-10 review finding: an all-False observed pattern from a runner that never ran must not "agree".
    out = tmp_path / "e7"
    res = piv.run(ITEMS, SHA, "E7", out, att, real=True, runner=RaisingRunner())
    assert all(r["agrees_with_prediction"] is None and r["execution"] == "not_executed" for r in res["rows"])
    assert res["disagreements_with_prediction"] == [] and res["not_executed_count"] == 17
    # per-item starts match the ledgered start events and actual_starts
    recs = ledger(out)
    assert sum(r["event"] == "start" for r in recs) == res["actual_starts"] == 17
    assert all(r["starts"] == 1 for r in recs if r["event"] == "result")
