"""Guard/supervisor fixtures only: tiny children, handwritten events, no data draws or fits."""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("stop_runner", ROOT/"scripts/run_stop_anchor_comparison.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def supervise(tmp_path, body, *, seconds=2., cap=32768, started=None):
    code = "\n".join(("import os,sys,time,json", "from pathlib import Path",
        f"sys.path.insert(0, {str(ROOT/'scripts')!r})",
        "from run_stop_anchor_comparison import ByteBudget, OutputCap",
        "root=Path(sys.argv[1]); writer=ByteBudget(root,int(os.environ['E0_STOP_OUTPUT_PAYLOAD_CAP']))",
        "writer.write_json('attempt.json',{'fixture_only':True,'pid':os.getpid()})", body))
    output = tmp_path/"tiny_run"
    result = runner._supervise(output, [sys.executable, "-c", code, "{output}"],
        total_seconds=seconds, output_bytes=cap, manifest={"fixture_only": True},
        started_monotonic=time.monotonic() if started is None else started)
    return output, result


def test_tiny_child_normal_exit_and_exact_total_bytes(tmp_path):
    output, final = supervise(tmp_path, "writer.write_json('done.json',dict(threads={k:os.environ[k] for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']}))")
    assert final["stop_reason"] == "child_complete" and final["child_exit_observed"]
    assert final["child_returncode"] == 0 and final["owned_child_cpu_seconds"] >= 0
    assert set(json.loads((output/"done.json").read_bytes())["threads"].values()) == {"1"}
    assert json.loads((output/"supervisor.json").read_bytes()) == final
    assert final["total_bytes"] == sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
    assert final["within_output_cap"] and final["within_wall_cap"]
    assert "fsync excluded" in final["wall_seconds_scope"]


def test_failed_child_retains_prior_artifacts(tmp_path):
    output, final = supervise(tmp_path, "writer.write_json('prior.json',{'estimate':.5});sys.exit(7)")
    assert final["stop_reason"] == "child_failed" and final["child_returncode"] == 7
    assert final["child_exit_observed"] and (output/"prior.json").exists()


def test_deadline_kills_and_observes_only_owned_child(tmp_path):
    output, final = supervise(tmp_path, "time.sleep(30)", seconds=.8)
    assert final["stop_reason"] == "outer_time_cap"
    assert final["child_exit_observed"] and final["child_returncode"] < 0
    with pytest.raises(ProcessLookupError):
        os.kill(final["child_pid"], 0)
    assert (output/"attempt.json").exists()


def test_expired_start_does_not_spawn_or_invent_child_exit(tmp_path):
    output, final = supervise(tmp_path, "raise AssertionError('must not start')", seconds=.5, started=time.monotonic()-1)
    assert final["stop_reason"] == "startup_deadline" and not final["child_started"]
    assert final["child_pid"] is None and not final["child_exit_observed"]
    assert not (output/"attempt.json").exists()


def test_cooperative_output_cap_includes_root_headers_and_archives(tmp_path):
    output, final = supervise(tmp_path, "\ntry:\n writer.write_json('too_big.json', {'x':'x'*32768})\nexcept OutputCap:\n sys.exit(3)", cap=16384)
    assert final["stop_reason"] == "output_cap_reached"
    assert final["total_bytes"] <= 16384 and not (output/"too_big.json").exists()
    root = tmp_path/"counting"
    root.mkdir(); (root/"records").mkdir()
    (root/"records"/"dataset.npz.tmp").write_bytes(b"x"*1000)
    writer = runner.ByteBudget(root, 1100)
    with pytest.raises(runner.OutputCap): writer.write_bytes("manifest.json", b"x"*51)
    assert writer.used() == 1000


def test_raw_uncooperative_writer_is_detected_not_claimed_contained(tmp_path):
    _, final = supervise(tmp_path, "(root/'uncooperative.bin').write_bytes(b'x'*65536)", cap=16384)
    assert final["stop_reason"] == "output_cap_violation" and not final["within_output_cap"]
    assert final["child_exit_observed"]


def test_no_overwrite_or_alternate_production_path(tmp_path):
    output = tmp_path/"tiny_run"
    output.mkdir(); (output/"old").write_bytes(b"old")
    with pytest.raises(FileExistsError): supervise(tmp_path, "pass")
    assert list(output.iterdir()) == [output/"old"]
    with pytest.raises(ValueError, match="fixed repository"):
        runner.main(["--freeze", "unused", "--resource-receipt", "unused", "--output", str(tmp_path/"alternate")])


def test_spawn_failure_still_records_never_started(tmp_path):
    output = tmp_path/"missing"
    with pytest.raises(FileNotFoundError):
        runner._supervise(output, [str(tmp_path/"no-such-executable")], total_seconds=2, output_bytes=16384,
                          manifest={}, started_monotonic=time.monotonic())
    receipt = json.loads((output/"supervisor.json").read_bytes())
    assert receipt["stop_reason"] == "startup_failure" and not receipt["child_exit_observed"]


@pytest.mark.parametrize("exit_during_wait", [False, True])
def test_signaling_refusal_preserves_receipt_without_inventing_exit(tmp_path, monkeypatch, exit_during_wait):
    """No real process: independently refused signals do not establish exit."""
    class Child:
        pid = 424242
        returncode = None
        def poll(self):
            return self.returncode
        def kill(self):
            raise PermissionError(1, "mock direct-child signal refused")
        def wait(self, timeout):
            assert 0 < timeout <= .05
            if exit_during_wait:
                self.returncode = 0
                return 0
            raise runner.subprocess.TimeoutExpired("mock-child", timeout)
    child = Child()
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **k: child)
    def denied(*args):
        raise PermissionError(1, "mock group signal refused")
    monkeypatch.setattr(runner.os, "killpg", denied)
    output = tmp_path/"signal_refusal"
    result = runner._supervise(output, ["mock-child"], total_seconds=.04, output_bytes=16384,
                              manifest={"fixture_only": True}, started_monotonic=time.monotonic())
    assert json.loads((output/"supervisor.json").read_bytes()) == result
    assert len(result["signaling_errors"]) == 2
    assert all("PermissionError" in error for error in result["signaling_errors"])
    assert result["child_exit_observed"] is exit_during_wait
    assert result["child_returncode"] == (0 if exit_during_wait else None)
    assert result["stop_reason"] == ("outer_time_cap" if exit_during_wait else "cleanup_unconfirmed")
    assert result["total_bytes"] == sum(p.stat().st_size for p in output.rglob("*") if p.is_file())


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e309}', b'[]'])
def test_strict_json_guards(raw):
    with pytest.raises(ValueError): runner.load_json(raw)


@pytest.fixture
def release(tmp_path, monkeypatch):
    """Fake Git blob transport ONLY; real committed-byte/env/receipt logic runs."""
    repo = tmp_path/"repo"
    repo.mkdir()
    blobs, hashes, revision = {}, {}, "a"*40
    for path in runner.REQUIRED_SOURCES:
        raw = (ROOT/path).read_bytes()
        target = repo/path
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        blobs[revision+":"+path] = raw
        hashes[path] = hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(runner, "ROOT", repo)
    freeze = dict(schema_version="e0-stop-anchor-execution-freeze-v1", execution_released=True,
        decision_id="LEAD-E0-STOP-01", planned_run_id=runner.RUN_ID, source_commit=revision,
        source_sha256=hashes, environment=runner._environment(), deterministic_truth=runner.TRUTH,
        caps=dict(runner.CAPS), fixture_only=True)
    fp, rp = repo/"freeze.json", repo/"receipt.json"
    fp.write_bytes(runner.encoded(freeze)); blobs[revision+":freeze.json"] = fp.read_bytes()
    receipt = dict(checked_utc=datetime.now(timezone.utc).isoformat(), planned_run_id=runner.RUN_ID,
        host=platform.node(), freeze_sha256=runner.sha(fp), one_cpu_available=True,
        no_active_conflicting_lease=True, evidence="Handwritten fixture, not actual authority",
        inspection={"fixture_only": True}, lease_scope="fixture only; no production execution")
    rp.write_bytes(runner.encoded(receipt))
    def git(*args):
        if args == ("rev-parse", "HEAD"): return revision.encode()+b"\n"
        if args in (("merge-base", "--is-ancestor", revision, "HEAD"),
                    ("merge-base", "--is-ancestor", revision, revision)): return b""
        if args[0] == "show": return blobs[args[1]]
        raise AssertionError(args)
    monkeypatch.setattr(runner, "_git", git)
    return dict(repo=repo, fp=fp, rp=rp, freeze=freeze, receipt=receipt, blobs=blobs)


def test_exact_release_accepts_mock_git_boundary(release):
    assert runner.validate_release(release["fp"], release["rp"]) == (release["freeze"], release["receipt"])
    assert runner.validate_release(release["fp"], release["rp"], return_binding=True)[2] == {
        "freeze_repository_path": "freeze.json", "freeze_commit": "a"*40}


@pytest.mark.parametrize("fault", ["uncommitted", "source", "caps", "truth", "decision", "run_id", "environment", "source_set", "short_revision"])
def test_release_rejects_material_freeze_drift(release, fault):
    f, fp, blobs = release["freeze"], release["fp"], release["blobs"]
    if fault == "source":
        (release["repo"]/runner.REQUIRED_SOURCES[0]).write_bytes(b"changed")
    else:
        if fault == "uncommitted": f["uncommitted"] = True
        elif fault == "caps": f["caps"]["cpu_workers"] = True  # bool must not equal numeric1.
        elif fault == "truth": f["deterministic_truth"] = .5
        elif fault == "decision": f["decision_id"] = "old-study"
        elif fault == "run_id": f["planned_run_id"] = "other"
        elif fault == "environment": f["environment"]["numpy"] = "wrong"
        elif fault == "source_set": f["source_sha256"].pop(runner.REQUIRED_SOURCES[0])
        else: f["source_commit"] = "abc"
        fp.write_bytes(runner.encoded(f))
        if fault != "uncommitted": blobs["a"*40+":freeze.json"] = fp.read_bytes()
    with pytest.raises(ValueError): runner.validate_release(fp, release["rp"])


@pytest.mark.parametrize("fault", ["stale", "future", "naive", "host", "lease", "inspection", "freeze", "run_id"])
def test_receipt_rejects_invalid_inspection(release, fault):
    r = release["receipt"]
    if fault == "stale": r["checked_utc"] = (datetime.now(timezone.utc)-timedelta(seconds=301)).isoformat()
    elif fault == "future": r["checked_utc"] = (datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat()
    elif fault == "naive": r["checked_utc"] = "2026-09-23T13:55:00"
    elif fault == "host": r["host"] = "other-host"
    elif fault == "lease": r["no_active_conflicting_lease"] = False
    elif fault == "inspection": r["inspection"] = {}
    elif fault == "freeze": r["freeze_sha256"] = "0"*64
    else: r["planned_run_id"] = "other"
    release["rp"].write_bytes(runner.encoded(r))
    with pytest.raises(ValueError): runner.validate_release(release["fp"], release["rp"])


@pytest.fixture
def connected(release, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/"experiments/e0")); monkeypatch.syspath_prepend(str(ROOT/"scripts"))
    adapter = importlib.import_module("stop_anchor_job")
    journal = importlib.import_module("stop_anchor_journal")
    truth = importlib.import_module("check_regularization_truth")
    monkeypatch.setattr(truth, "forward_value", lambda: (runner.TRUTH, None, None))
    def no_sampler(*args, **kwargs): raise AssertionError("real sampler is forbidden")
    monkeypatch.setattr(adapter.sim, "simulate", no_sampler)
    output = release["repo"]/"work"/runner.RUN_ID
    output.mkdir(parents=True)
    start, token = time.monotonic(), "b"*32
    manifest = dict(schema_version="e0-stop-anchor-run-v1", run_id=runner.RUN_ID,
        freeze_commit="a"*40, freeze_repository_path="freeze.json",
        source_commit=release["freeze"]["source_commit"], freeze=release["freeze"],
        resource_receipt=release["receipt"], freeze_sha256=runner.sha(release["fp"]),
        resource_receipt_sha256=runner.sha(release["rp"]), freeze_path="execution_freeze.json",
        resource_receipt_path="resource_receipt.json", output_directory=str(output.resolve()),
        supervisor_pid=os.getppid(), supervisor_token=token, started_monotonic=start,
        deadline_monotonic=start+600, cleanup_seconds=2., output_bytes_cap=runner.CAPS["output_bytes"],
        payload_bytes_cap=runner.CAPS["output_bytes"]-runner.RESERVE)
    for name, raw in (("run_manifest.json", runner.encoded(manifest)),
                      ("execution_freeze.json", release["fp"].read_bytes()),
                      ("resource_receipt.json", release["rp"].read_bytes())):
        (output/name).write_bytes(raw)
    monkeypatch.setenv("E0_STOP_SUPERVISOR_PID", str(os.getppid()))
    monkeypatch.setenv("E0_STOP_SUPERVISOR_TOKEN", token)
    monkeypatch.setenv("E0_STOP_OUTPUT_PAYLOAD_CAP", str(runner.CAPS["output_bytes"]-runner.RESERVE))
    for key, value in runner.THREAD_ENV.items(): monkeypatch.setenv(key, value)
    return release, output, adapter, journal, manifest


def test_full96_job_failed_fixture_through_actual_worker_guards(connected, monkeypatch):
    rel, output, adapter, journal, _ = connected
    calls = []
    def evaluate(plan, job, *, data, on_event):
        assert data is None
        calls.append(job)
        identity = adapter.expected_job_identity(plan, job)
        rows = [dict(identity["planned_job"], estimator=e, status="failed", reason="handwritten preparation failure") for e in adapter.ESTIMATORS]
        on_event(dict(event="job_failed", identity=identity, failure_phase="preparation", records=rows,
                      provenance={"source_sha256": {p:runner.sha(ROOT/p) for p in adapter.SOURCE_PATHS}}))
        return dict(resources=dict(sampler_attempts=0, backward_fit_attempts=0, model_calls=0, paid_usd=0))
    monkeypatch.setattr(adapter, "evaluate_job", evaluate)
    runner._worker(rel["fp"], output, rel["rp"])
    assert [j["replicate"] for j in calls] == list(range(96))
    assert all(type(j["data_seed"]) is str for j in calls)
    summary = json.loads((output/"records"/"summary.json").read_bytes())
    assert summary["planned_estimator_slots"] == 2304
    assert summary["status_counts"]["failed"] == 2304 and summary["incomplete"]
    headers = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
    records_manifest = json.loads((output/"records"/"manifest.json").read_bytes())
    assert records_manifest["output_bytes_cap"] == runner.CAPS["output_bytes"]-runner.RESERVE-headers


def test_interrupted_variant_keeps_two_completed_and_all_remaining_slots(connected, monkeypatch):
    import numpy as np
    rel, output, adapter, journal, _ = connected
    def evaluate(plan, job, *, data, on_event):
        identity = adapter.expected_job_identity(plan, job)
        task = np.repeat(np.arange(230), 40)
        arrays = dict(task=task, S=np.full((9200, 3), 3), A=np.zeros((9200, 3), int),
                      B=np.ones((9200, 3)), Y=np.ones(9200), elig=np.zeros((9200, 3), bool))
        arrays["elig"][:, 0] = True
        arrays["B"][:, 0] = adapter.sim.make_beh(2.5, .02, gz=0.)[0, 3, 0]
        assignment = adapter.anchored._fold_assignment(task, 3, 0, np.repeat(np.arange(230)%3, 40))
        folds = {k:v.tolist() for k,v in assignment.items()}
        prov = dict(source_sha256={p:runner.sha(ROOT/p) for p in adapter.SOURCE_PATHS},
                    dataset=adapter._fingerprint(arrays), folds={**folds,"sha256":adapter._digest(folds)})
        on_event(dict(event="prepared", identity=identity, provenance=prov,
            arrays={k:dict(dtype=v.dtype.str,shape=list(v.shape),values=v.tolist()) for k,v in arrays.items()}))
        variant = list(adapter.anchored.VARIANTS)[0]
        ids = [variant+":"+m for m in ("plugin", "dr")]
        binding = dict(identity=identity,variant=variant,dataset_sha256=prov["dataset"]["sha256"],fold_sha256=prov["folds"]["sha256"])
        on_event(dict(binding,event="variant_started",estimator_ids=ids))
        on_event(dict(binding,event="variant",records=[adapter._point_record(identity,e,np.ones(230)) for e in ids],
                      root_means={m:[1.]*230 for m in ("plugin","dr")},root_labels=list(range(230)),support=[]))
        raise RuntimeError("injected interruption after terminal variant")
    monkeypatch.setattr(adapter, "evaluate_job", evaluate)
    with pytest.raises(RuntimeError, match="after terminal"):
        runner._worker(rel["fp"], output, rel["rp"])
    snapshot = journal.reconcile_recording(output/"records")
    counts = snapshot["summary"]["status_counts"]
    assert counts["completed"] == 2 and counts["attempted"] == 22 and counts["unattempted"] == 2280
    assert (output/"records"/"dataset_000.npz").exists()
    assert not (output/"records"/"summary.json").exists()


@pytest.mark.parametrize("fault", ["parent", "token", "deadline", "archive", "thread", "existing_records",
                                  "freeze_commit", "freeze_path"])
def test_worker_binding_refuses_before_scientific_dispatch(connected, monkeypatch, fault):
    rel, output, adapter, _, manifest = connected
    calls = []
    monkeypatch.setattr(adapter, "evaluate_job", lambda *a, **k: calls.append(True))
    if fault == "parent": manifest["supervisor_pid"] = -1
    elif fault == "token": monkeypatch.setenv("E0_STOP_SUPERVISOR_TOKEN", "wrong")
    elif fault == "deadline": manifest["deadline_monotonic"] = time.monotonic()-1
    elif fault == "archive": (output/"execution_freeze.json").write_bytes(b"changed")
    elif fault == "thread": monkeypatch.setenv("OMP_NUM_THREADS", "2")
    elif fault == "freeze_commit": manifest["freeze_commit"] = "not-a-commit"
    elif fault == "freeze_path": manifest["freeze_repository_path"] = "other.json"
    else: (output/"records").mkdir()
    (output/"run_manifest.json").write_bytes(runner.encoded(manifest))
    with pytest.raises(ValueError): runner._worker(rel["fp"], output, rel["rp"])
    assert not calls and not (output/"worker_receipt.json").exists()
