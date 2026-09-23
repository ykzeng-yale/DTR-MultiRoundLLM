"""Clock/source tests use injected time and mocked child processes only. No receiver or executor runs."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e13a_stage_clock as sc  # noqa: E402

START = datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc)
HASH = "a" * 64


class Fake:
    def __init__(self, start=START):
        self.wall, self.mono = start, 1000.0

    def advance(self, seconds):
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds

    def now_utc(self):
        return self.wall

    def monotonic(self):
        return self.mono


def clock(fake=None, **kwargs):
    fake = fake or Fake()
    return sc.StageClock.from_start(fake.wall, now_utc=fake.now_utc, monotonic=fake.monotonic, **kwargs), fake


def bound(tmp_path, fake=None, **kwargs):
    c, f = clock(fake, run_dir=tmp_path, stage_sha256=HASH, **kwargs)
    c.persist(tmp_path)
    return c, f, tmp_path / sc.CLOCK_FILE


def test_fixed_caps_and_outer_total():
    c, _ = clock()
    assert c.caps == {"setup": 600, "collection": 480, "private_grading": 300, "analysis": 300}
    assert c.remaining_outer() == 2700
    assert sum(c.caps.values()) < c.outer_seconds


def test_every_phase_reads_shared_outer_deadline():
    c, f = clock()
    f.advance(2500)
    assert all(c.remaining(p) == 200 for p in c.caps if p != "setup")
    assert c.remaining("setup") == -1900  # setup additionally includes the full inter-command wall span
    assert all(c.binding(p) == "outer_deadline" for p in c.caps if p != "setup")
    f.advance(200)
    for p in c.caps:
        with pytest.raises(sc.CapExhausted):
            c.check(p)


def test_phase_time_is_cumulative_and_ordinary_exception_is_charged(tmp_path):
    c, f, p = bound(tmp_path)
    with c.phase("setup"):
        pass
    with c.phase("collection"):
        f.advance(200)
    with pytest.raises(RuntimeError):
        with c.phase("collection"):
            f.advance(20)
            raise RuntimeError("transport abort")
    reloaded = sc.StageClock.load(p, now_utc=f.now_utc, monotonic=f.monotonic)
    assert reloaded.spent["collection"] == 220
    assert reloaded.last_phase["status"] == "failed"
    assert reloaded.last_phase["error"] == "RuntimeError"
    assert json.loads(p.read_text())["active_phase"] is None


def test_persist_during_phase_never_double_charges(tmp_path):
    c, f, p = bound(tmp_path)
    with c.phase("setup"):
        pass
    with c.phase("collection"):
        f.advance(10)
        c.persist(p)
        assert c.remaining("collection") == 470
        c.persist(p)
        assert c.remaining("collection") == 470
        f.advance(5)
        c.persist(p)
    assert c.spent["collection"] == 15
    assert json.loads(p.read_text())["spent"]["collection"] == 15


def test_reload_keeps_anchor_and_prior_phase_spend(tmp_path):
    c, f, p = bound(tmp_path)
    with c.phase("setup"):
        f.advance(100)
    f.advance(400)
    later = sc.StageClock.load(p, now_utc=f.now_utc, monotonic=f.monotonic,
                               run_dir=tmp_path, stage_sha256=HASH, require_bound=True)
    assert later.start_utc == START
    assert later.remaining_outer() == 2200
    assert later.spent["setup"] == 100
    assert later.remaining("setup") == 100  # four hundred seconds between commands still count toward setup


def test_stale_objects_refresh_spend_under_single_worker_lock(tmp_path):
    _, f, p = bound(tmp_path)
    a = sc.StageClock.load(p, now_utc=f.now_utc, monotonic=f.monotonic)
    b = sc.StageClock.load(p, now_utc=f.now_utc, monotonic=f.monotonic)
    with a.phase("setup"):
        f.advance(10)
    with b.phase("setup"):
        f.advance(20)
    assert json.loads(p.read_text())["spent"]["setup"] == 30


def test_overlapping_objects_and_other_phase_are_refused(tmp_path):
    a, f, p = bound(tmp_path)
    b = sc.StageClock.load(p, now_utc=f.now_utc, monotonic=f.monotonic)
    with a.phase("setup"):
        with pytest.raises(sc.ClockRefusal, match="locked"):
            with b.phase("analysis"):
                pytest.fail("overlapping work entered")
        with pytest.raises(sc.ClockRefusal, match="active"):
            with a.phase("analysis"):
                pytest.fail("nested work entered")
        with pytest.raises(sc.ClockRefusal, match="locked"):
            sc.StageClock.load(p)
        assert json.loads(p.read_text())["active_phase"]["phase"] == "setup"


def test_orphan_active_receipt_refuses_restart_even_without_lock(tmp_path):
    _, _, p = bound(tmp_path)
    data = json.loads(p.read_text())
    data["active_phase"] = {"phase": "analysis", "token": "orphan", "pid": 999999}
    p.write_text(json.dumps(data))
    with pytest.raises(sc.ClockRefusal, match="unfinished"):
        sc.StageClock.load(p)
    with pytest.raises(sc.ClockRefusal, match="unfinished"):
        sc.open_clock(tmp_path, require_existing=True, stage_sha256=HASH)


def test_orphan_lock_refuses_restart_without_guessing_pid_liveness(tmp_path):
    _, _, p = bound(tmp_path)
    p.with_suffix(p.suffix + ".lock").write_text('{"pid": 999999}')
    with pytest.raises(sc.ClockRefusal, match="locked"):
        sc.StageClock.load(p)


def test_clock_binding_rejects_missing_changed_moved_and_unbound(tmp_path):
    with pytest.raises(sc.ClockRefusal, match="existing"):
        sc.open_clock(tmp_path / "missing", require_existing=True, stage_sha256=HASH)
    c, f, p = bound(tmp_path)
    c.require_binding(tmp_path, HASH)
    with pytest.raises(sc.ClockRefusal, match="binding"):
        c.require_binding(tmp_path, "b" * 64)
    with pytest.raises(sc.ClockRefusal, match="binding"):
        sc.open_clock(tmp_path, require_existing=True, stage_sha256="b" * 64)
    moved = tmp_path / "other" / sc.CLOCK_FILE
    moved.parent.mkdir()
    moved.write_bytes(p.read_bytes())
    with pytest.raises(sc.ClockRefusal, match="moved"):
        sc.StageClock.load(moved)
    unbound_dir = tmp_path / "unbound"
    unbound_dir.mkdir()
    u, _ = clock(f)
    u.persist(unbound_dir)
    with pytest.raises(sc.ClockRefusal):
        sc.open_clock(unbound_dir, require_existing=True, stage_sha256=HASH)


@pytest.mark.parametrize("caps,outer", [({**sc.PHASE_CAPS, "setup": 601}, 2700),
                                        (sc.PHASE_CAPS, 2701), ({"setup": 600}, 2700)])
def test_fixed_maxima_checked_on_construction_and_load(tmp_path, caps, outer):
    with pytest.raises(ValueError):
        sc.StageClock.from_start(START, caps=caps, outer_seconds=outer)
    _, _, p = bound(tmp_path)
    data = json.loads(p.read_text())
    data.update(caps=caps, outer_seconds=outer)
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        sc.StageClock.load(p)


def test_anchor_caps_and_binding_cannot_change_on_persist(tmp_path):
    _, f, p = bound(tmp_path)
    for kwargs in ({"stage_sha256": "b" * 64}, {"outer_seconds": 2600},
                   {"caps": {**sc.PHASE_CAPS, "setup": 500}}):
        options = {"run_dir": tmp_path, "stage_sha256": HASH, **kwargs}
        other, _ = clock(f, **options)
        with pytest.raises(sc.ClockRefusal):
            other.persist(p)
    other = sc.StageClock.from_start(START + timedelta(seconds=1), run_dir=tmp_path, stage_sha256=HASH)
    with pytest.raises(sc.ClockRefusal):
        other.persist(p)


def test_unknown_phase_and_malformed_clock_refused(tmp_path):
    c, _ = clock()
    with pytest.raises(ValueError, match="Unknown"):
        c.remaining("grading")
    with pytest.raises(ValueError, match="UTC offset"):
        sc.StageClock.from_start("2026-09-23T12:00:00")
    with pytest.raises(ValueError, match="positive"):
        sc.StageClock.from_start(START, {**sc.PHASE_CAPS, "setup": 0})
    with pytest.raises(ValueError, match="no cap"):
        sc.StageClock.from_start(START, spent={"unknown": 1})
    p = tmp_path / sc.CLOCK_FILE
    p.write_text(json.dumps({"schema_version": sc.SCHEMA}))
    with pytest.raises(ValueError, match="missing"):
        sc.StageClock.load(p)


def test_phase_reports_cap_overrun_instead_of_success(tmp_path):
    c, f, p = bound(tmp_path)
    with pytest.raises(sc.CapExhausted):
        with c.phase("analysis"):
            f.advance(301)
    data = json.loads(p.read_text())
    assert data["spent"]["analysis"] == 301
    assert data["last_phase"]["status"] == "failed"
    assert data["active_phase"] is None
    with pytest.raises(sc.CapExhausted):
        c.check("analysis")


class Child:
    pid = 23456
    def __init__(self, fake, *, duration=1, returncode=0, timeout=False):
        self.fake, self.duration, self.returncode, self.timeout = fake, duration, returncode, timeout
        self.waits = []
    def wait(self, timeout=None):
        self.waits.append(timeout)
        if timeout is not None:
            if self.timeout and len(self.waits) == 1:
                self.fake.advance(timeout)
                raise subprocess.TimeoutExpired("mocked owned child", timeout)
            self.fake.advance(self.duration)
        return self.returncode


def test_supervision_uses_remaining_phase_and_cumulative_setup(tmp_path):
    c, f, p = bound(tmp_path)
    seen, killed = [], []
    def spawn(command, **kwargs):
        child = Child(f, duration=25)
        seen.append((command, kwargs, child))
        return child
    sc.supervise(c, "setup", ["MOCK_ONLY"], popen=spawn, killpg=lambda *x: killed.append(x))
    sc.supervise(c, "setup", ["MOCK_ONLY"], popen=spawn, killpg=lambda *x: killed.append(x))
    assert [x[2].waits[0] for x in seen] == [600, 575]
    assert all(x[1] == {"start_new_session": True} for x in seen)
    assert json.loads(p.read_text())["spent"]["setup"] == 50
    assert killed == []


@pytest.mark.parametrize("limit,expected", [("phase", 300), ("outer", 7), ("lease", 4)])
def test_supervision_timeout_kills_and_reaps_only_owned_group(tmp_path, limit, expected):
    c, f, p = bound(tmp_path)
    if limit == "outer":
        f.advance(2693)
    deadline = f.now_utc() + timedelta(seconds=4) if limit == "lease" else None
    child, killed = Child(f, timeout=True), []
    with pytest.raises(sc.CapExhausted):
        sc.supervise(c, "analysis", ["MOCK_ONLY"], deadline_utc=deadline,
                     popen=lambda *a, **k: child, killpg=lambda *a: killed.append(a))
    assert child.waits == [expected, 5]
    assert killed == [(child.pid, signal.SIGKILL)]
    data = json.loads(p.read_text())
    assert data["spent"]["analysis"] == expected + child.duration  # include actual bounded reap time
    assert data["last_phase"]["status"] == "failed" and data["active_phase"] is None


def test_supervision_nonzero_exit_is_failure(tmp_path):
    c, f, p = bound(tmp_path)
    child, killed = Child(f, returncode=3), []
    with pytest.raises(ChildProcessError):
        sc.supervise(c, "analysis", ["MOCK_ONLY"], popen=lambda *a, **k: child,
                     killpg=lambda *a: killed.append(a))
    assert killed == [(child.pid, signal.SIGKILL)]
    assert json.loads(p.read_text())["last_phase"]["status"] == "failed"


def test_supervision_counts_process_start_overhead(tmp_path):
    c, f, _ = bound(tmp_path)
    child = Child(f)
    def spawn(*a, **k):
        f.advance(2)
        return child
    sc.supervise(c, "analysis", ["MOCK_ONLY"], popen=spawn)
    assert child.waits == [298]
    assert c.spent["analysis"] == 3


def test_no_dispatch_after_exhaustion_or_expired_lease(tmp_path):
    c, f, _ = bound(tmp_path)
    def forbidden(*a, **k):
        pytest.fail("must not dispatch")
    with pytest.raises(sc.CapExhausted):
        sc.supervise(c, "analysis", ["MOCK_ONLY"], popen=forbidden, deadline_utc=f.now_utc())
    f.advance(2700)
    with pytest.raises(sc.CapExhausted):
        sc.supervise(c, "analysis", ["MOCK_ONLY"], popen=forbidden)


def test_ownership_guard_checks_setup_before_lease_and_conflicts(tmp_path):
    p = tmp_path / "ownership.json"
    record = {"start_utc": START.isoformat(), "hard_end_utc": (START + timedelta(hours=2)).isoformat()}
    p.write_text(json.dumps(record))
    assert sc.ownership_deadline(p, START) == START + timedelta(hours=2)
    for when in (START - timedelta(seconds=1), START + timedelta(hours=2)):
        with pytest.raises(sc.ClockRefusal, match="outside"):
            sc.ownership_deadline(p, when)
    record.update(exclusive_window_start_utc=START.isoformat(),
                  exclusive_window_end_utc=(START + timedelta(hours=3)).isoformat())
    p.write_text(json.dumps(record))
    with pytest.raises(sc.ClockRefusal, match="conflicting"):
        sc.ownership_deadline(p, START)


def test_cli_requires_bound_init_and_refuses_reanchor(tmp_path, capsys):
    stage = tmp_path / "stage.json"
    stage.write_text('{"stage":"E13a"}')
    run = tmp_path / "run"
    args = ["--run-dir", str(run), "--stage", str(stage), "--init"]
    with pytest.raises(SystemExit):
        sc.main(["--run-dir", str(run), "--init"])
    report = sc.main(args)
    assert report["stage_sha256"] == hashlib.sha256(stage.read_bytes()).hexdigest()
    with pytest.raises(SystemExit, match="re-anchor"):
        sc.main(args)
    assert sc.main(["--run-dir", str(run), "--phase", "collection"])["queried_phase"]["phase"] == "collection"
    capsys.readouterr()


def test_cli_requires_setup_ownership_and_delegates_real_timeout_without_running_child(tmp_path, monkeypatch, capsys):
    stage = tmp_path / "stage.json"
    stage.write_text('{}')
    run = tmp_path / "run"
    sc.main(["--run-dir", str(run), "--stage", str(stage), "--init"])
    with pytest.raises(SystemExit):
        sc.main(["--run-dir", str(run), "--stage", str(stage), "--supervise", "setup", "--", "MOCK_ONLY"])
    calls = []
    monkeypatch.setattr(sc, "supervise", lambda clock, phase, command, **kwargs: calls.append((phase, command, kwargs)))
    sc.main(["--run-dir", str(run), "--stage", str(stage), "--supervise", "analysis", "--", "MOCK_ONLY", "x"])
    assert calls == [("analysis", ["MOCK_ONLY", "x"], {"deadline_utc": None})]
    capsys.readouterr()


def test_cli_overcap_charge_is_retrospective_failure_not_enforcement(tmp_path, capsys):
    stage = tmp_path / "stage.json"
    stage.write_text('{}')
    run = tmp_path / "run"
    sc.main(["--run-dir", str(run), "--stage", str(stage), "--init"])
    sc.main(["--run-dir", str(run), "--check", "analysis"])
    with pytest.raises(SystemExit, match="Already elapsed"):
        sc.main(["--run-dir", str(run), "--charge", "analysis", "--seconds", "320"])
    assert json.loads((run / sc.CLOCK_FILE).read_text())["spent"]["analysis"] == 320
    with pytest.raises(SystemExit, match="cap exhausted"):
        sc.main(["--run-dir", str(run), "--check", "analysis"])
    capsys.readouterr()


def test_nothing_is_written_inside_results(tmp_path):
    before = sorted(p.name for p in (ROOT / "results").iterdir())
    bound(tmp_path)
    assert sorted(p.name for p in (ROOT / "results").iterdir()) == before


def test_setup_wall_gaps_count_and_close_at_first_collection(tmp_path):
    c, f, p = bound(tmp_path)
    with c.phase("setup"):
        f.advance(20)
    f.advance(570)  # inter-command ownership/refreeze work still uses setup's wall allowance
    assert c.remaining("setup") == 10
    with c.phase("collection"):
        f.advance(30)
    assert c.setup_wall_seconds() == 590
    assert c.spent["setup"] == 20  # child work and full setup wall span are explicitly different fields
    reloaded = sc.StageClock.load(p, now_utc=f.now_utc, monotonic=f.monotonic)
    assert reloaded.setup_complete_utc == (START + timedelta(seconds=590)).isoformat()
    with pytest.raises(sc.CapExhausted):
        with reloaded.phase("setup"):
            pytest.fail("setup cannot reopen")


def test_collection_refuses_missing_setup_receipt_or_late_setup(tmp_path):
    c, f, _ = bound(tmp_path)
    with pytest.raises(sc.ClockRefusal, match="setup receipts"):
        with c.phase("collection"):
            pytest.fail("missing setup must refuse")
    with c.phase("setup"):
        f.advance(10)
    f.advance(591)
    with pytest.raises(sc.CapExhausted, match="setup"):
        with c.phase("collection"):
            pytest.fail("late setup must refuse")


def test_failed_setup_cannot_be_retried_or_used_for_collection(tmp_path):
    c, _, _ = bound(tmp_path)
    with pytest.raises(RuntimeError):
        with c.phase("setup"):
            raise RuntimeError("failed startup")
    for name in ("setup", "collection"):
        with pytest.raises(sc.ClockRefusal):
            with c.phase(name):
                pytest.fail("failed setup has no retry allowance")


def test_stale_persist_cannot_erase_setup_close_failure_or_teardown(tmp_path):
    c, f, p = bound(tmp_path)
    stale = sc.StageClock.load(p, now_utc=f.now_utc, monotonic=f.monotonic)
    with c.phase("setup"):
        f.advance(1)
    with c.phase("collection"):
        f.advance(1)
    with pytest.raises(RuntimeError):
        with c.phase("analysis"):
            f.advance(1)
            raise RuntimeError("stop")
    c.last_teardown = {"status": "review_required", "ended_utc": f.now_utc().isoformat()}
    c.persist(p)
    before = json.loads(p.read_text())
    stale.persist(p)
    after = json.loads(p.read_text())
    for key in ("setup_complete_utc", "setup_completed_commands", "failed_phases", "last_teardown", "last_phase"):
        assert after[key] == before[key]


def test_new_phase_receipt_wins_equal_timestamp_tie(tmp_path):
    c, _, p = bound(tmp_path)
    with c.phase("setup"):
        pass
    stale = sc.StageClock.load(p)
    with pytest.raises(RuntimeError):
        with c.phase("analysis"):
            raise RuntimeError("zero-duration mock failure")
    assert json.loads(p.read_text())["last_phase"]["phase"] == "analysis"
    stale.persist(p)
    assert json.loads(p.read_text())["last_phase"]["phase"] == "analysis"


def test_unreaped_owned_child_keeps_active_receipt_and_blocks_reentry(tmp_path):
    c, f, p = bound(tmp_path)
    class NeverExits(Child):
        def wait(self, timeout=None):
            self.waits.append(timeout)
            f.advance(timeout)
            raise subprocess.TimeoutExpired("mocked unexited child", timeout)
    child = NeverExits(f)
    with pytest.raises(sc.UnreapedChild):
        sc.supervise(c, "analysis", ["MOCK_ONLY"], popen=lambda *a, **k: child, killpg=lambda *a: None)
    assert child.waits == [300, 5]
    assert json.loads(p.read_text())["active_phase"]["status"] == "unreaped_child_review_required"
    with pytest.raises(sc.ClockRefusal, match="locked"):
        sc.StageClock.load(p)
    with pytest.raises(sc.ClockRefusal, match="active"):
        with c.phase("setup"):
            pytest.fail("unobserved exit cannot permit more work")


def test_new_launch_cleanup_is_pinned_bounded_and_recorded_separately(tmp_path):
    c, f, p = bound(tmp_path)
    receiver = tmp_path / "new_receiver"
    helper = ROOT / "scripts/launch_own_receiver_v31.py"
    digest = hashlib.sha256(helper.read_bytes()).hexdigest()
    child = Child(f, timeout=True)
    def spawn(*a, **k):
        receiver.mkdir()
        (receiver / "launch.json").write_text(json.dumps({
            "schema": "mrl16-own-receiver-launch-v31", "started_utc": f.now_utc().isoformat(),
            "ownership_sha256": HASH, "process_identity": "mock-only owned identity"}))
        return child
    cleanups = []
    def cleanup(command, **kwargs):
        cleanups.append((command, kwargs))
        f.advance(2)
        record = json.loads((receiver / "launch.json").read_text())
        record["exit_observed"] = True
        (receiver / "launch.json").write_text(json.dumps(record))
        return SimpleNamespace(returncode=0)
    with pytest.raises(sc.CapExhausted):
        sc.supervise(c, "setup", ["python", str(helper), "--out", str(receiver)], popen=spawn,
                     killpg=lambda *a: None, owned_receiver_dir=receiver, cleanup_helper_sha256=digest,
                     ownership_sha256=HASH, cleanup_runner=cleanup)
    assert len(cleanups) == 1 and cleanups[0][1]["timeout"] == 20
    assert cleanups[0][0][-1] == "--stop"
    data = json.loads(p.read_text())
    assert data["last_teardown"]["status"] == "exit_observed"
    assert data["last_teardown"]["elapsed_seconds"] == 2
    assert data["spent"]["setup"] == 601  # 600 work + 1 bounded child reap; separate receiver teardown excluded
    assert c.setup_wall_seconds() == 603


@pytest.mark.parametrize("defect", ["existing_dir", "wrong_hash", "wrong_ownership", "missing_identity", "missing_record"])
def test_cleanup_never_signals_unproved_or_prior_receiver(tmp_path, defect):
    c, f, p = bound(tmp_path)
    receiver = tmp_path / "receiver"
    helper = ROOT / "scripts/launch_own_receiver_v31.py"
    digest = hashlib.sha256(helper.read_bytes()).hexdigest()
    if defect == "existing_dir":
        receiver.mkdir()
    child = Child(f, returncode=1)
    def spawn(*a, **k):
        receiver.mkdir()
        if defect != "missing_record":
            (receiver / "launch.json").write_text(json.dumps({
                "schema": "mrl16-own-receiver-launch-v31", "started_utc": f.now_utc().isoformat(),
                "ownership_sha256": "wrong" if defect == "wrong_ownership" else HASH,
                "process_identity": None if defect == "missing_identity" else "mock owned"}))
        return child
    with pytest.raises((sc.ClockRefusal, ChildProcessError)):
        sc.supervise(c, "setup", ["python", str(helper), "--out", str(receiver)], popen=spawn,
                     killpg=lambda *a: None, owned_receiver_dir=receiver,
                     cleanup_helper_sha256="wrong" if defect == "wrong_hash" else digest,
                     ownership_sha256=HASH, cleanup_runner=lambda *a, **k: pytest.fail("no cleanup may run"))
    if defect not in ("existing_dir", "wrong_hash"):
        assert "manual_reconciliation_required" in json.loads(p.read_text())["last_teardown"]["status"]
