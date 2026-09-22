"""Source-only receiver-restart controls: all process operations are mocked."""
import importlib.util
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launch = load("launch_own_receiver_v31")
diff = load("diff_receiver_snapshot_v31")
AGREEMENT = {"start_utc": "2026-09-22T04:35:00Z", "hard_end_utc": "2026-09-22T05:45:00Z",
             "phase_a_latest_start_utc": "2026-09-22T04:45:00Z"}


@pytest.mark.parametrize("stamp", ["2026-09-22T04:34:59Z", "2026-09-22T04:45:00Z", "2026-09-22T05:45:00Z"])
def test_refuses_outside_window_or_insufficient_remaining(stamp):
    with pytest.raises(SystemExit):
        launch.ready_deadline(AGREEMENT, launch.utc(stamp))


def test_both_agreement_schemas_and_no_deadline_extension():
    current = launch.utc("2026-09-22T04:38:00Z")
    expected = launch.utc("2026-09-22T04:45:00Z")
    assert launch.ready_deadline(AGREEMENT, current) == expected
    worker = {"exclusive_window_start_utc": AGREEMENT["start_utc"], "exclusive_window_end_utc": AGREEMENT["hard_end_utc"]}
    assert launch.ready_deadline(worker, current) == expected


def test_naive_or_conflicting_timestamps_rejected():
    with pytest.raises(SystemExit):
        launch.utc("2026-09-22T04:35:00")
    record = {**AGREEMENT, "exclusive_window_start_utc": "2026-09-22T04:36:00Z", "exclusive_window_end_utc": AGREEMENT["hard_end_utc"]}
    with pytest.raises(SystemExit):
        launch.ready_deadline(record, launch.utc("2026-09-22T04:38:00Z"))


@pytest.mark.parametrize("returncode,saved", [(1, b""), (0, b"{}\n")])
def test_staged_only_or_dirty_agreement_rejected(tmp_path, monkeypatch, returncode, saved):
    monkeypatch.setattr(launch, "ROOT", tmp_path)
    path = tmp_path / "agreement.json"
    path.write_text(json.dumps(AGREEMENT))
    monkeypatch.setattr(launch.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=returncode, stdout=saved))
    with pytest.raises(SystemExit, match="not committed identically"):
        launch.committed_agreement(path)


class FakeChild:
    pid = 12345

    def __init__(self, stubborn=False):
        self.code = None
        self.terminated = self.killed = False
        self.stubborn = stubborn

    def poll(self):
        return self.code

    def terminate(self):
        self.terminated = True
        if not self.stubborn:
            self.code = -15

    def kill(self):
        self.killed = True
        self.code = -9

    def wait(self, timeout):
        if self.code is None:
            raise subprocess.TimeoutExpired("mock", timeout)
        return self.code


def test_owned_child_cleanup_escalates_bounded():
    child = FakeChild(stubborn=True)
    launch.terminate_owned_child(child)
    assert child.terminated and child.killed and child.code == -9


@pytest.mark.parametrize("failure", ["timeout", "interrupt"])
def test_failed_launch_reaps_mock_child_and_preserves_record(tmp_path, monkeypatch, failure):
    agreement = tmp_path / "agreement.json"
    agreement.write_text(json.dumps(AGREEMENT))
    monkeypatch.setattr(launch, "committed_agreement", lambda p: (AGREEMENT, "frozen-hash"))
    monkeypatch.setattr(launch, "launcher_provenance", lambda a: {"source_head": "mock-head", "launcher_sha256": "mock-sha"})
    monkeypatch.setattr(launch, "verify", lambda: ({"media_marker": "pinned"}, "/mock/model", 26))
    monkeypatch.setattr(launch, "sh", lambda cmd: "")

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 22, 4, 35, tzinfo=timezone.utc)

    monkeypatch.setattr(launch, "datetime", Clock)
    ticks = iter([0, 601, 602]) if failure == "timeout" else iter([0, 0, 1])
    monkeypatch.setattr(launch.time, "monotonic", lambda: next(ticks))
    if failure == "interrupt":
        def interrupt(_):
            raise KeyboardInterrupt("mock interruption")
        monkeypatch.setattr(launch.time, "sleep", interrupt)
    child = FakeChild()
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: child)
    out = tmp_path / "run"
    with pytest.raises(SystemExit if failure == "timeout" else KeyboardInterrupt):
        launch.main(["--ownership", str(agreement), "--out", str(out)])
    record = json.loads((out / "launch.json").read_text())
    assert child.terminated and record["exited"] == -15
    assert record["ready_utc"] is None and "stopped_utc" in record


@pytest.fixture
def saved_preflight(tmp_path):
    destination = tmp_path / "preflight"
    shutil.copytree(diff.PRIOR, destination)
    return destination


def test_complete_saved_preflight_passes_without_requests(saved_preflight, tmp_path):
    out = tmp_path / "diff.json"
    diff.main(["--new-preflight", str(saved_preflight), "--out", str(out)])
    assert json.loads(out.read_text())["passed"] is True


@pytest.mark.parametrize("defect", ["error", "missing_requests", "missing_after", "busy", "nonboolean_idle", "drift", "missing_render"])
def test_incomplete_or_failed_preflight_fails_closed(saved_preflight, tmp_path, defect):
    summary_path = saved_preflight / "summary.json"
    summary = json.loads(summary_path.read_text())
    if defect == "error":
        summary["error"] = "recorded preflight failure"
    elif defect == "missing_requests":
        summary["request_log"].pop()
    elif defect == "missing_after":
        (saved_preflight / "props_after.json").unlink()
    elif defect in ("busy", "nonboolean_idle"):
        p = saved_preflight / "slots_after.json"
        slots = json.loads(p.read_text())
        slots[0]["is_processing"] = True if defect == "busy" else 0
        p.write_text(json.dumps(slots))
    elif defect == "drift":
        p = saved_preflight / "props_after.json"
        props = json.loads(p.read_text())
        props["media_marker"] = "changed"
        p.write_text(json.dumps(props))
    else:
        next((saved_preflight / "rendered").glob("*.prompt.txt")).unlink()
    summary_path.write_text(json.dumps(summary))
    out = tmp_path / "diff.json"
    with pytest.raises(SystemExit, match="Preflight failed"):
        diff.main(["--new-preflight", str(saved_preflight), "--out", str(out)])
    report = json.loads(out.read_text())
    assert not report["passed"] and report["validation_errors"]



def test_ready_marker_matches_the_pinned_build_log():
    """Worker-reported excerpt only: the original raw log was not delivered with 544b1e6."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("launch_v31", ROOT / "scripts/launch_own_receiver_v31.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    observed = ("0.14.321143 I srv  llama_server: model loaded\n"
                "0.14.321145 I srv  llama_server: listening on http://127.0.0.1:8193\n")
    assert mod.READY_MARKER in observed
    assert "server is listening" not in observed and "all slots are idle" not in observed


def test_successful_mock_start_records_provenance_and_leaves_child_alive(tmp_path, monkeypatch):
    """Exercise main using a worker-reported excerpt, not an independently archived server log."""
    agreement = tmp_path / "agreement.json"
    agreement.write_text(json.dumps(AGREEMENT))
    provenance = {"source_head": "a" * 40, "launcher_path": "scripts/launch_own_receiver_v31.py", "launcher_sha256": "b" * 64}
    monkeypatch.setattr(launch, "committed_agreement", lambda p: (AGREEMENT, "agreement-hash"))
    monkeypatch.setattr(launch, "launcher_provenance", lambda a: provenance)
    monkeypatch.setattr(launch, "verify", lambda: ({"media_marker": "pinned"}, "/mock/model", 26))
    monkeypatch.setattr(launch, "sh", lambda cmd: "")

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 22, 4, 35, tzinfo=timezone.utc)

    monkeypatch.setattr(launch, "datetime", Clock)
    ticks = iter([0, 0.1, 0.2])
    monkeypatch.setattr(launch.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(launch.time, "sleep", lambda _: pytest.fail("Ready marker should finish without sleeping"))
    child = FakeChild()

    def fake_popen(*args, **kwargs):
        kwargs["stdout"].write("0.14.321143 I srv llama_server: model loaded\n"
                                "0.14.321145 I srv llama_server: listening on http://127.0.0.1:8193\n")
        kwargs["stdout"].flush()
        return child

    monkeypatch.setattr(launch.subprocess, "Popen", fake_popen)
    out = tmp_path / "run"
    launch.main(["--ownership", str(agreement), "--out", str(out)])
    record = json.loads((out / "launch.json").read_text())
    assert all(record[k] == v for k, v in provenance.items())
    assert record["ready_utc"] is not None and record["generation_requests"] == 0
    assert record["ownership_sha256"] == "agreement-hash"
    assert not child.terminated and child.poll() is None


@pytest.mark.parametrize("defect", ["dirty", "missing_from_commit", "reservation_mismatch"])
def test_source_mismatch_refuses_before_spawn(tmp_path, monkeypatch, defect):
    source = tmp_path / "launcher.py"
    source.write_bytes(b"# mock source\n")
    agreement = tmp_path / "agreement.json"
    agreement.write_text(json.dumps(AGREEMENT))
    record = {**AGREEMENT, "launcher_sha256": "wrong"} if defect == "reservation_mismatch" else AGREEMENT
    monkeypatch.setattr(launch, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "__file__", str(source))
    monkeypatch.setattr(launch, "committed_agreement", lambda p: (record, "agreement-hash"))

    def fake_run(args, **kwargs):
        if args[1] == "rev-parse":
            return SimpleNamespace(returncode=0, stdout=b"a" * 40 + b"\n")
        return SimpleNamespace(returncode=1 if defect == "missing_from_commit" else 0,
                               stdout=b"# different\n" if defect == "dirty" else source.read_bytes())

    monkeypatch.setattr(launch.subprocess, "run", fake_run)
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("Must refuse before spawn"))
    with pytest.raises(SystemExit, match="Launcher"):
        launch.main(["--ownership", str(agreement), "--out", str(tmp_path / "run")])


def test_source_provenance_accepts_exact_committed_reservation_pin(tmp_path, monkeypatch):
    import hashlib
    source = tmp_path / "launcher.py"
    source.write_bytes(b"# exact source\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(launch, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "__file__", str(source))
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **k: SimpleNamespace(
        returncode=0, stdout=b"a" * 40 + b"\n" if args[1] == "rev-parse" else source.read_bytes()))
    assert launch.launcher_provenance({"launcher_sha256": digest}) == {
        "source_head": "a" * 40, "launcher_path": "launcher.py", "launcher_sha256": digest}
