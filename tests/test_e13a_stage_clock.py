"""Shared E13a stage clock (scripts/e13a_stage_clock.py).

Bookkeeping only: nothing here contacts a receiver, executes a candidate or writes inside results/.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import e13a_stage_clock as sc  # noqa: E402

START = datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc)


class Fake:
    """Injected time: wall clock for the outer deadline, monotonic for in-flight phase charging."""

    def __init__(self, start=START):
        self.wall, self.mono = start, 1000.0

    def advance(self, seconds):
        self.wall = self.wall + timedelta(seconds=seconds)
        self.mono += seconds

    def now_utc(self):
        return self.wall

    def monotonic(self):
        return self.mono


def clock(fake=None, **kwargs):
    fake = fake or Fake()
    return sc.StageClock.from_start(START, now_utc=fake.now_utc, monotonic=fake.monotonic, **kwargs), fake


def test_lead_fixed_caps_and_outer_total():
    assert sc.PHASE_CAPS == {"setup": 600, "collection": 480, "private_grading": 300, "analysis": 300}
    assert sc.OUTER_TOTAL_SECONDS == 2700
    c, _ = clock()
    assert c.remaining("setup") == 600 and c.remaining("collection") == 480
    assert c.remaining("private_grading") == 300 and c.remaining("analysis") == 300
    assert c.remaining_outer() == 2700
    assert sum(sc.PHASE_CAPS.values()) < sc.OUTER_TOTAL_SECONDS


def test_every_phase_reads_one_shared_outer_deadline():
    c, fake = clock()
    fake.advance(2500)  # 200 s of the outer budget left: no phase may exceed it, whatever its own cap
    assert c.remaining_outer() == 200
    assert all(c.remaining(p) == 200 for p in sc.PHASE_CAPS)
    assert all(c.binding(p) == "outer_deadline" for p in sc.PHASE_CAPS)
    fake.advance(200)
    for phase in sc.PHASE_CAPS:
        with pytest.raises(sc.CapExhausted, match="outer_deadline"):
            c.check(phase)


def test_phase_cap_binds_before_the_outer_deadline():
    c, fake = clock()
    with c.phase("collection"):
        fake.advance(479)
        assert c.remaining("collection") == pytest.approx(1.0)
        assert c.binding("collection") == "phase_cap"
    assert c.spent["collection"] == pytest.approx(479)
    assert c.remaining("collection") == pytest.approx(1.0)
    assert c.remaining("setup") == pytest.approx(600)  # a phase cap is charged to that phase only
    with c.phase("collection"):
        fake.advance(1)
        with pytest.raises(sc.CapExhausted, match="phase_cap"):
            c.check("collection")


def test_in_flight_phase_is_charged_even_when_the_block_raises():
    c, fake = clock()
    with pytest.raises(RuntimeError):
        with c.phase("collection"):
            fake.advance(30)
            raise RuntimeError("abort mid-phase")
    assert c.spent["collection"] == pytest.approx(30)
    assert c.remaining("collection") == pytest.approx(450)


def test_persist_then_load_carries_spend_and_does_not_reset_the_outer_deadline(tmp_path):
    c, fake = clock()
    with c.phase("setup"):
        fake.advance(100)
    path = c.persist(tmp_path)
    assert path == tmp_path / sc.CLOCK_FILE
    fake.advance(400)  # wall time passes between the two commands
    later = Fake(fake.wall)
    reloaded = sc.StageClock.load(path, now_utc=later.now_utc, monotonic=later.monotonic)
    assert reloaded.start_utc == START                      # the anchor, not "now"
    assert reloaded.outer_seconds == sc.OUTER_TOTAL_SECONDS
    assert reloaded.remaining_outer() == pytest.approx(2700 - 500)
    assert reloaded.spent["setup"] == pytest.approx(100)
    assert reloaded.remaining("setup") == pytest.approx(500)
    assert reloaded.remaining("collection") == pytest.approx(480)
    assert reloaded.reloads == 1


def test_a_reload_can_never_extend_the_outer_deadline(tmp_path):
    c, fake = clock()
    fake.advance(2690)
    c.persist(tmp_path)
    for _ in range(3):  # three further commands, each reloading and re-persisting the same clock
        later = Fake(fake.wall)
        c = sc.StageClock.load(tmp_path / sc.CLOCK_FILE, now_utc=later.now_utc, monotonic=later.monotonic)
        assert c.remaining_outer() == pytest.approx(10)
        c.persist(tmp_path)
    fake.advance(10)
    later = Fake(fake.wall)
    c = sc.StageClock.load(tmp_path / sc.CLOCK_FILE, now_utc=later.now_utc, monotonic=later.monotonic)
    assert c.remaining_outer() <= 0
    with pytest.raises(sc.CapExhausted):
        c.check("analysis")


def test_persist_merges_spend_by_maximum_and_never_hands_time_back(tmp_path):
    c, fake = clock()
    with c.phase("collection"):
        fake.advance(200)
    c.persist(tmp_path)
    stale = sc.StageClock.load(tmp_path / sc.CLOCK_FILE)
    stale.spent["collection"] = 5.0  # a stale or tampered in-memory copy
    stale.persist(tmp_path)
    assert json.loads((tmp_path / sc.CLOCK_FILE).read_text())["spent"]["collection"] == pytest.approx(200)


def test_persist_refuses_a_different_anchor_or_caps(tmp_path):
    c, _ = clock()
    c.persist(tmp_path)
    other = sc.StageClock.from_start(START + timedelta(seconds=1))
    with pytest.raises(ValueError, match="different stage clock"):
        other.persist(tmp_path)
    tight = sc.StageClock.from_start(START, {**sc.PHASE_CAPS, "collection": 999})
    with pytest.raises(ValueError, match="persisted phase caps"):
        tight.persist(tmp_path)


def test_unknown_phase_and_malformed_inputs_are_refused(tmp_path):
    c, _ = clock()
    for call in (lambda: c.remaining("grading"), lambda: c.check("grading"), lambda: c.charge("grading", 1)):
        with pytest.raises(ValueError, match="Unknown stage phase"):
            call()
    with pytest.raises(ValueError, match="UTC offset"):
        sc.StageClock.from_start("2026-09-23T12:00:00")
    with pytest.raises(ValueError, match="positive"):
        sc.StageClock.from_start(START, {"collection": 0})
    with pytest.raises(ValueError, match="no cap"):
        sc.StageClock(START, sc.PHASE_CAPS, spent={"nope": 1})
    bad = tmp_path / sc.CLOCK_FILE
    bad.write_text(json.dumps({"schema_version": "other"}))
    with pytest.raises(ValueError, match="stage clock"):
        sc.StageClock.load(bad)
    bad.write_text(json.dumps({"schema_version": sc.SCHEMA}))
    with pytest.raises(ValueError, match="missing stage-clock fields"):
        sc.StageClock.load(bad)


def test_open_clock_reloads_an_existing_run_directory(tmp_path):
    c, fake = clock()
    with c.phase("setup"):
        fake.advance(60)
    c.persist(tmp_path)
    reopened, path = sc.open_clock(tmp_path)
    assert path == tmp_path / sc.CLOCK_FILE
    assert reopened.start_utc == START and reopened.spent["setup"] == pytest.approx(60)
    fresh, _ = sc.open_clock(tmp_path / "other-run")
    assert fresh.spent["setup"] == 0 and fresh.remaining_outer() <= sc.OUTER_TOTAL_SECONDS


def test_cli_init_refuses_to_re_anchor_and_reports_remaining(tmp_path, capsys):
    sc.main(["--run-dir", str(tmp_path), "--init", "--start-utc", START.isoformat()])
    capsys.readouterr()
    with pytest.raises(SystemExit, match="Refusing to re-anchor"):
        sc.main(["--run-dir", str(tmp_path), "--init"])
    report = sc.main(["--run-dir", str(tmp_path), "--phase", "collection"])
    assert report["start_utc"].startswith("2026-09-23T12:00:00")
    assert report["queried_phase"]["phase"] == "collection"
    assert report["reloads"] == 1
    assert json.loads(capsys.readouterr().out)["outer_seconds"] == 2700


def test_nothing_is_written_inside_results(tmp_path):
    before = sorted(p.name for p in (ROOT / "results").iterdir())
    c, _ = clock()
    c.persist(tmp_path)
    assert sorted(p.name for p in (ROOT / "results").iterdir()) == before
