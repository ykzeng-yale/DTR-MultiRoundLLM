"""Operational fixtures only: no simulator, estimator fit, or benchmark program.

Children below write handcrafted records, sleep, or fail. Connected worker tests
replace evaluate_job completely: the real plan, truth, journal and reporter run,
but no sampling, fold permutation, nuisance fitting or scientific job executes.
"""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "regularization_runner_for_tests", ROOT / "scripts/run_regularization_comparison.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


CHILD_PREFIX = """
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'scripts'))
from run_regularization_comparison import ByteBudget
output = Path(sys.argv[1])
writer = ByteBudget(output, int(os.environ['E0_OUTPUT_PAYLOAD_CAP']))
writer.append_jsonl('events.jsonl', {'event': 'attempted', 'job_index': 0,
                                  'fixture_only': True, 'pid': os.getpid()})
"""


def supervise(tmp_path, body, *, seconds=3.0, byte_cap=32768, started=None):
    output = tmp_path / "run"
    result = runner._supervise(
        output, [sys.executable, "-c", CHILD_PREFIX + body, "{output}"],
        total_seconds=seconds, output_bytes=byte_cap,
        manifest={"fixture_only": True, "sampled_datasets": 0},
        started_monotonic=time.monotonic() if started is None else started)
    return output, result


def test_byte_budget_rejects_before_changing_completed_bytes(tmp_path):
    event = {"event": "attempted"}
    payload = runner.encoded(event)
    writer = runner.ByteBudget(tmp_path, len(payload))
    writer.append_jsonl("events.jsonl", event)
    before = (tmp_path / "events.jsonl").read_bytes()
    with pytest.raises(runner.OutputCap):
        writer.append_jsonl("events.jsonl", {"event": "completed"})
    assert (tmp_path / "events.jsonl").read_bytes() == before
    assert writer.used() == len(payload)


def test_temporary_bytes_are_included_in_budget(tmp_path):
    (tmp_path / "unfinished.tmp").write_bytes(b"x" * 15)
    value = {"fixture_only": True}
    writer = runner.ByteBudget(tmp_path, len(runner.encoded(value)) + 14)
    with pytest.raises(runner.OutputCap):
        writer.write_json("result.json", value)
    assert not (tmp_path / "result.json").exists()
    assert not (tmp_path / "result.json.tmp").exists()
    assert (tmp_path / "unfinished.tmp").read_bytes() == b"x" * 15


def test_artifact_writer_does_not_overwrite_or_escape(tmp_path):
    writer = runner.ByteBudget(tmp_path, 8192)
    writer.write_json("result.json", {"kept": True})
    before = (tmp_path / "result.json").read_bytes()
    with pytest.raises(FileExistsError):
        writer.write_json("result.json", {"kept": False})
    for name in ("../outside.json", "nested/file.json", "supervisor.json"):
        with pytest.raises(ValueError):
            writer.write_json(name, {})
    (tmp_path / "symlink.json").symlink_to(tmp_path / "result.json")
    with pytest.raises(ValueError):
        writer.append_jsonl("symlink.json", {})
    assert (tmp_path / "result.json").read_bytes() == before


def test_handcrafted_child_completes_and_gets_one_thread_environment(tmp_path):
    output, result = supervise(tmp_path, """
writer.write_json('handcrafted.json', {'fixture_only': True,
    'thread_env': {k: os.environ[k] for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
        'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')}})
writer.append_jsonl('events.jsonl', {'event': 'completed', 'job_index': 0,
                                  'fixture_only': True})
""")
    assert result["stop_reason"] == "child_complete"
    assert result["child_returncode"] == 0
    assert result["child_exit_observed"]
    artifact = json.loads((output / "handcrafted.json").read_text())
    assert set(artifact["thread_env"].values()) == {"1"}
    assert [json.loads(x)["event"] for x in (output / "events.jsonl").read_text().splitlines()] == ["attempted", "completed"]
    persisted = json.loads((output / "supervisor.json").read_text())
    assert persisted == result
    assert sum(p.stat().st_size for p in output.iterdir()) <= result["output_bytes_cap"]
    assert result["wall_seconds"] < result["outer_seconds_cap"]


def test_failed_child_retains_attempt_and_completed_prior_artifact(tmp_path):
    output, result = supervise(tmp_path, """
writer.write_json('prior_variant.json', {'fixture_only': True, 'estimate': 0.5})
sys.exit(7)
""")
    assert result["stop_reason"] == "child_failed"
    assert result["child_returncode"] == 7
    assert result["child_exit_observed"]
    assert json.loads((output / "prior_variant.json").read_text())["estimate"] == .5
    events = [json.loads(x) for x in (output / "events.jsonl").read_text().splitlines()]
    assert [x["event"] for x in events] == ["attempted"]
    assert not (output / "summary.json").exists()


def test_hanging_child_is_killed_and_no_completion_is_invented(tmp_path):
    output, result = supervise(tmp_path, "time.sleep(30)\n", seconds=.8)
    assert result["stop_reason"] == "outer_time_cap"
    assert result["child_returncode"] < 0
    assert result["child_exit_observed"]
    event = json.loads((output / "events.jsonl").read_text())
    assert event["event"] == "attempted"
    with pytest.raises(ProcessLookupError):
        os.kill(event["pid"], 0)
    assert not (output / "summary.json").exists()
    # Small scheduling allowance only for the mock test; production cap stays600.
    assert result["wall_seconds"] < 1.0


def test_group_signal_permission_race_preserves_final_receipt(tmp_path, monkeypatch):
    def raced_killpg(pid, sig):
        raise PermissionError(1, "group leader exited between poll and signal")

    monkeypatch.setattr(runner.os, "killpg", raced_killpg)
    output, result = supervise(tmp_path, "time.sleep(30)\n", seconds=.8)
    assert result["stop_reason"] == "outer_time_cap"
    assert result["child_returncode"] < 0
    assert result["child_exit_observed"]
    assert json.loads((output / "supervisor.json").read_text()) == result


def test_group_leader_exit_between_poll_and_kill_is_reaped(monkeypatch):
    class ExitedChild:
        pid = 12345
        killed = False
        polled = 0
        waited = False

        def poll(self):
            self.polled += 1
            return None if self.polled == 1 else 0

        def kill(self):
            self.killed = True

        def wait(self, timeout):
            self.waited = True
            return 0

    def raced_killpg(pid, sig):
        raise PermissionError(1, "already exited")

    monkeypatch.setattr(runner.os, "killpg", raced_killpg)
    child = ExitedChild()
    runner._stop_child_group(child, time.monotonic() + 1)
    assert child.waited
    assert not child.killed


def test_fast_raw_writer_cannot_be_reported_complete_above_cap(tmp_path):
    # Deliberately bypass the cooperative writer to test the post-exit monitor.
    # This tests detection, not hard containment of arbitrary malicious writers.
    output, result = supervise(tmp_path, """
(output / 'uncooperative.bin').write_bytes(b'x' * 65536)
""", byte_cap=16384)
    assert result["stop_reason"] == "output_cap_violation"
    assert result["payload_bytes"] > 16384 - runner.RESERVE
    assert result["child_exit_observed"]
    assert (output / "events.jsonl").exists()


def test_existing_output_is_immutable_and_child_is_not_started(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    marker = output / "completed.json"
    marker.write_bytes(b"immutable old run")
    with pytest.raises(FileExistsError):
        supervise(tmp_path, "writer.write_json('should_not_exist.json', {})\n")
    assert marker.read_bytes() == b"immutable old run"
    assert sorted(p.name for p in output.iterdir()) == ["completed.json"]


def test_expired_outer_budget_does_not_start_child(tmp_path):
    output, result = supervise(tmp_path, "writer.write_json('should_not_exist.json', {})\n",
                               seconds=.5, started=time.monotonic() - 1)
    assert result["stop_reason"] == "startup_deadline"
    assert result["child_returncode"] is None
    assert not (output / "events.jsonl").exists()
    assert not (output / "should_not_exist.json").exists()


def test_spawn_failure_preserves_supervisor_receipt(tmp_path):
    output = tmp_path / "run"
    with pytest.raises(FileNotFoundError):
        runner._supervise(output, [str(tmp_path / "nonexistent-program")],
                          total_seconds=2, output_bytes=16384, manifest={"fixture_only": True},
                          started_monotonic=time.monotonic())
    result = json.loads((output / "supervisor.json").read_text())
    assert result["stop_reason"] == "startup_failure"
    assert result["child_returncode"] is None
    assert not (output / "events.jsonl").exists()


def test_oversized_manifest_is_rejected_before_output_reservation(tmp_path):
    output = tmp_path / "run"
    with pytest.raises(runner.OutputCap):
        runner._supervise(output, ["should-not-start"], total_seconds=2,
                          output_bytes=8192, manifest={"oversized": "x" * 8192},
                          started_monotonic=time.monotonic())
    assert not output.exists()


def test_cooperative_cap_stop_preserves_receipt_without_exceeding_total(tmp_path):
    output, result = supervise(tmp_path, """
from run_regularization_comparison import OutputCap
try:
    writer.write_json('too_large.json', {'value': 'x' * 65536})
except OutputCap:
    sys.exit(3)
""", byte_cap=16384)
    assert result["stop_reason"] == "output_cap_reached"
    assert result["child_returncode"] == 3
    assert not (output / "too_large.json").exists()
    assert not (output / "too_large.json.tmp").exists()
    assert (output / "events.jsonl").exists()
    assert sum(p.stat().st_size for p in output.iterdir()) <= 16384


@pytest.fixture
def bound_release(tmp_path, monkeypatch):
    """Mock only Git object retrieval; exercise actual release/receipt guards."""
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    revision = "fixture-source-revision"
    blobs = {}
    source_hashes = {}
    for name in runner.REQUIRED_SOURCES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = ("source bytes for fixture: " + name).encode()
        path.write_bytes(data)
        blobs[revision + ":" + name] = data
        source_hashes[name] = hashlib.sha256(data).hexdigest()
    freeze = {
        "schema_version": "e0-regularization-execution-freeze-v1",
        "execution_released": True,
        "caps": {"cpu_workers": 1, "outer_seconds": 600,
                 "output_bytes": 268435456, "paid_usd": 0, "model_calls": 0},
        "source_sha256": source_hashes, "source_commit": revision,
    }
    freeze_path = tmp_path / "fixture-freeze.json"
    freeze_path.write_bytes(runner.encoded(freeze))
    blobs["HEAD:fixture-freeze.json"] = freeze_path.read_bytes()
    receipt = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "no_active_conflicting_lease": True, "one_cpu_available": True,
        "host": platform.node(), "freeze_sha256": runner.sha(freeze_path),
        "evidence": "Synthetic receipt for guard tests only; no execution authority.",
    }
    receipt_path = tmp_path / "fixture-receipt.json"
    receipt_path.write_bytes(runner.encoded(receipt))

    def fake_git(*args):
        if args == ("merge-base", "--is-ancestor", revision, "HEAD"):
            return b""
        if args[0] == "show":
            return blobs[args[1]]
        raise AssertionError(args)

    monkeypatch.setattr(runner, "_git", fake_git)
    return freeze_path, receipt_path, freeze, receipt, blobs


def test_release_guard_accepts_exact_committed_source_fixture(bound_release):
    freeze_path, receipt_path, freeze, receipt, _ = bound_release
    assert runner.validate_release(freeze_path, receipt_path) == (freeze, receipt)


def test_release_guard_rejects_local_source_drift(bound_release):
    freeze_path, receipt_path, _, _, _ = bound_release
    source = freeze_path.parent / runner.REQUIRED_SOURCES[0]
    source.write_bytes(source.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Source differs"):
        runner.validate_release(freeze_path, receipt_path)


def test_release_guard_rejects_uncommitted_freeze(bound_release):
    freeze_path, receipt_path, freeze, _, _ = bound_release
    freeze["new_uncommitted_field"] = True
    freeze_path.write_bytes(runner.encoded(freeze))
    with pytest.raises(ValueError, match="committed and unchanged"):
        runner.validate_release(freeze_path, receipt_path)


@pytest.mark.parametrize("mutation", ["stale", "future", "wrong_host", "wrong_freeze", "conflicting_lease"])
def test_release_guard_rejects_invalid_resource_receipt(bound_release, mutation):
    freeze_path, receipt_path, _, receipt, _ = bound_release
    if mutation == "stale":
        receipt["checked_utc"] = (datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat()
    elif mutation == "future":
        receipt["checked_utc"] = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    elif mutation == "wrong_host":
        receipt["host"] += "-different"
    elif mutation == "wrong_freeze":
        receipt["freeze_sha256"] = "0" * 64
    else:
        receipt["no_active_conflicting_lease"] = False
    receipt_path.write_bytes(runner.encoded(receipt))
    with pytest.raises(ValueError):
        runner.validate_release(freeze_path, receipt_path)


@pytest.fixture
def connected_worker(tmp_path, monkeypatch):
    """Bind a mock authority/parent environment; retain the actual scientific plan."""
    import numpy as np
    import scipy

    monkeypatch.syspath_prepend(str(ROOT / "experiments/e0"))
    job_module = importlib.import_module("regularization_job")
    report_module = importlib.import_module("regularization_report")
    output = tmp_path / "connected-fixture"
    output.mkdir()
    freeze = {
        "caps": {"cpu_workers": 1, "outer_seconds": 600, "output_bytes": 268435456,
                 "paid_usd": 0, "model_calls": 0},
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "scipy": scipy.__version__, "bit_generator": "PCG64"},
        "source_sha256": {name: runner.sha(ROOT / name) for name in runner.REQUIRED_SOURCES},
        "fixture_only": True,
    }
    freeze_path = tmp_path / "mock-authority.json"
    freeze_path.write_bytes(runner.encoded(freeze))
    receipt_path = tmp_path / "mock-receipt.json"
    receipt_path.write_bytes(runner.encoded({"fixture_only": True}))
    monkeypatch.setattr(runner, "validate_release", lambda f, r: (freeze, {"fixture_only": True}))
    monkeypatch.setenv("E0_SUPERVISOR_PID", str(os.getppid()))
    monkeypatch.setenv("E0_OUTPUT_PAYLOAD_CAP", str(freeze["caps"]["output_bytes"] - runner.RESERVE))
    manifest = {
        "supervisor_pid": os.getppid(), "freeze_sha256": runner.sha(freeze_path),
        "output_bytes_cap": freeze["caps"]["output_bytes"],
        "deadline_monotonic": time.monotonic() + 120,
        "fixture_only": True,
    }
    (output / "run_manifest.json").write_bytes(runner.encoded(manifest))
    return output, freeze_path, receipt_path, freeze, job_module, report_module


def fixture_job_evaluator(job_module, freeze, calls, *, stop_after_variant=False,
                          wrong_identity=False, wrong_source=False):
    """A full replacement, not a wrapper around the real evaluate_job function."""
    def evaluate(plan, job, *, on_event):
        calls.append(dict(job))
        identity = job_module.expected_job_identity(plan, job)
        callback_identity = dict(identity)
        if wrong_identity:
            callback_identity["job_id"] = "wrong-fixture-identity"
        sources = {p: freeze["source_sha256"][p] for p in job_module.SOURCE_PATHS}
        if wrong_source:
            sources[job_module.SOURCE_PATHS[0]] = "0" * 64
        provenance = {
            "source_sha256": sources, "data_mode": "handcrafted_callback_fixture_no_computation",
            "data_seed": job["data_seed"], "fold_seed": job["fold_seed"],
            "dataset": {"sha256": "a" * 64, "fields": {}, "fixture_only": True},
            "folds": {"sha256": "b" * 64, "fixture_only": True},
        }
        on_event({"event": "prepared", "identity": callback_identity, "provenance": provenance})
        records = []
        variants = {}
        for variant in ("compressed_lambda0", "compressed_lambda5", "history_lambda0", "history_lambda5"):
            pair = []
            for method in ("plugin", "dr"):
                record = {**identity["planned_job"], "estimator": variant + ":" + method,
                          "status": "completed", "estimate": .5}
                if method == "dr":
                    record["interval"] = {"status": "valid", "se": 0., "lo": .5, "hi": .5}
                pair.append(record)
            event = {
                "event": "variant", "identity": identity, "variant": variant,
                "records": pair, "root_means": {"plugin": [.5] * 230, "dr": [.5] * 230},
                "root_labels": list(range(230)),
                "support": [{"fold": fold, "stages": []} for fold in range(3)],
                "dataset_sha256": "a" * 64, "fold_sha256": "b" * 64, "wall_seconds": 0.,
            }
            on_event(event)
            records.extend(pair)
            variants[variant] = event
            if stop_after_variant:
                raise RuntimeError("injected failure after a durably returned variant")
        return {
            "schema_version": "e0-regularization-job-v1", "identity": identity,
            "planned_job": identity["planned_job"], "provenance": provenance,
            "records": records, "variants": variants, "all_points_completed": True,
            "resources": {"sampler_attempts": 0, "model_calls": 0, "benchmark_executions": 0,
                          "paid_usd": 0, "wall_seconds": 0., "cpu_seconds": 0.},
        }
    return evaluate


def test_connected_worker_completes_exact_600_handcrafted_jobs(connected_worker, monkeypatch):
    output, freeze_path, receipt_path, freeze, job_module, _ = connected_worker
    calls = []
    monkeypatch.setattr(job_module, "evaluate_job", fixture_job_evaluator(job_module, freeze, calls))
    runner._worker(freeze_path, output, receipt_path)
    assert len(calls) == 600
    assert [j["job_index"] for j in calls] == list(range(600))
    for i, job in enumerate(calls):
        assert job["cell_index"] == i % 3
        assert job["replicate"] == i // 3
        assert job["data_seed"] == 202609220000 + 1000 * (i % 3) + i // 3
        assert job["fold_seed"] == 202609320000 + 1000 * (i % 3) + i // 3
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    assert len(events) == 4200
    assert [e["job_index"] for e in events if e["event"] == "job_complete"] == list(range(600))
    assert sum(e["event"] == "attempted" for e in events) == 600
    assert sum(e["event"] == "variant" for e in events) == 2400
    assert all(e["resources"]["sampler_attempts"] == 0 for e in events if e["event"] == "job_complete")
    planned = json.loads((output / "planned_jobs.json").read_text())
    assert len(planned) == len({j["pairing_id"] for j in planned}) == 600
    summary = json.loads((output / "summary.json").read_text())
    assert summary["truth"] == .6459770061744536
    assert summary["planned_estimator_slots"] == summary["supplied_records"] == 4800
    assert summary["all_planned_results_complete"]
    assert not summary["incomplete"]
    assert all(s["status"] == "completed" for s in summary["slots"])
    for cell in summary["cells"].values():
        assert cell["planned_jobs"] == 200
        for estimator in cell["estimators"].values():
            assert estimator["point_metric_denominator"] == estimator["attempted"] == 200
            assert estimator["bias"] == .5 - .6459770061744536
            assert estimator["empirical_sd"] == 0
        assert all(pair["joint_completed_pairs"] == 200 for pair in cell["paired_comparisons"])
    assert sum(p.stat().st_size for p in output.iterdir()) < freeze["caps"]["output_bytes"]


def test_connected_partial_variant_preserves_all_planned_states(connected_worker, monkeypatch):
    output, freeze_path, receipt_path, freeze, job_module, reporter = connected_worker
    calls = []
    monkeypatch.setattr(job_module, "evaluate_job",
                        fixture_job_evaluator(job_module, freeze, calls, stop_after_variant=True))
    with pytest.raises(RuntimeError, match="after a durably returned variant"):
        runner._worker(freeze_path, output, receipt_path)
    assert len(calls) == 1
    assert not (output / "summary.json").exists()
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    assert [e["event"] for e in events] == ["attempted", "prepared", "variant"]
    planned = json.loads((output / "planned_jobs.json").read_text())
    # Independent source-only reconciliation from durable receipts, not absence
    # of output alone. This deliberately does not manufacture a completed run.
    recovered = {}
    for event in events:
        if event["event"] == "attempted":
            identity = event["identity"]["planned_job"]
            for name in event["estimator_slots"]:
                recovered[(identity["cell_id"], identity["replicate"], name)] = {
                    **identity, "estimator": name, "status": "attempted",
                    "reason": "attempt receipt exists without terminal variant record"}
        for record in event.get("records", []):
            recovered[(record["cell_id"], record["replicate"], record["estimator"])] = record
    summary = reporter.summarize_regularization(planned, list(recovered.values()),
                                                .6459770061744536, truncated=True)
    statuses = [slot["status"] for slot in summary["slots"]]
    assert len(statuses) == 4800
    assert statuses.count("completed") == 2
    assert statuses.count("attempted") == 6
    assert statuses.count("unattempted") == 4792
    assert summary["incomplete"]
    assert not summary["all_planned_results_complete"]


@pytest.mark.parametrize("fault", ["identity", "source"])
def test_connected_invalid_event_is_rejected_before_journaling(connected_worker, monkeypatch, fault):
    output, freeze_path, receipt_path, freeze, job_module, _ = connected_worker
    calls = []
    monkeypatch.setattr(job_module, "evaluate_job", fixture_job_evaluator(
        job_module, freeze, calls, wrong_identity=fault == "identity", wrong_source=fault == "source"))
    with pytest.raises(ValueError):
        runner._worker(freeze_path, output, receipt_path)
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    assert [e["event"] for e in events] == ["attempted"]
    assert not (output / "summary.json").exists()
