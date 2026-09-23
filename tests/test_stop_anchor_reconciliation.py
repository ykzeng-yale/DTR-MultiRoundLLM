"""Closed-run audit boundary fixtures; Git/import seams are mocked, no draws/fits.

The real journal/archive arithmetic has its separately owned tests. These tests
exercise the final reader's release, closure, strict JSON and immutable-output
checks without claiming a mock run was a production simulation.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load("stop_final_reconciliation_test", ROOT/"scripts/reconcile_stop_anchor_run.py")
reporting = load("stop_final_reporting_test", ROOT/"experiments/e0/stop_anchor_report.py")


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()


def seal(root, supervisor):
    """Handwritten closed receipt with exact total-byte fixed point."""
    payload = sum(path.stat().st_size for path in root.rglob("*")
                  if path.is_file() and path.name != "supervisor.json")
    receipt = dict(supervisor, payload_bytes=payload, total_bytes=0, within_output_cap=True)
    for _ in range(8):
        receipt["total_bytes"] = payload+len(encoded(receipt))
    (root/"supervisor.json").write_bytes(encoded(receipt))
    return receipt


@pytest.fixture
def closed(tmp_path, monkeypatch):
    repo, root = tmp_path/"repo", tmp_path/"raw"
    repo.mkdir(); root.mkdir()
    blobs = {}
    for name in r.REQUIRED_SOURCES:
        raw = (ROOT/name).read_bytes() if name in (r.PLAN, r.SEEDS) else b"# verified test-only source placeholder\n"
        path = repo/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        blobs[name] = raw
    env = dict(python="fixture-python", numpy="fixture-numpy", scipy="fixture-scipy", bit_generator="PCG64")
    freeze = dict(schema_version="e0-stop-anchor-execution-freeze-v1", execution_released=True,
        decision_id="LEAD-E0-STOP-01", planned_run_id=r.RUN_ID, deterministic_truth=r.TRUTH,
        caps=r.CAPS, source_commit="1"*40, source_sha256={name:r.sha(raw) for name,raw in blobs.items()},
        environment=env)
    freeze_raw = encoded(freeze)
    freeze_path, freeze_commit = "results/test_execution_freeze.json", "2"*40
    resource = dict(checked_utc="2026-09-23T12:00:00+00:00", planned_run_id=r.RUN_ID,
        freeze_sha256=r.sha(freeze_raw), host="recorded-host", no_active_conflicting_lease=True,
        one_cpu_available=True, inspection={"process_check":"fixture only"},
        evidence="handwritten unit fixture, not actual resource inspection", lease_scope="unit fixture")
    resource_raw = encoded(resource)
    manifest = dict(schema_version="e0-stop-anchor-run-v1", run_id=r.RUN_ID,
        source_commit=freeze["source_commit"], freeze=freeze, freeze_sha256=r.sha(freeze_raw),
        freeze_path="execution_freeze.json", freeze_repository_path=freeze_path, freeze_commit=freeze_commit,
        resource_receipt=resource, resource_receipt_sha256=r.sha(resource_raw),
        resource_receipt_path="resource_receipt.json", started_utc="2026-09-23T12:01:00+00:00",
        model_calls=0, benchmark_executions=0, prompt_tokens=0, completion_tokens=0, paid_usd=0,
        supervisor_pid=8000, supervisor_token="a"*32, started_monotonic=10., deadline_monotonic=610.,
        cleanup_seconds=2., output_directory=str(root), output_bytes_cap=r.CAPS["output_bytes"],
        payload_bytes_cap=r.CAPS["output_bytes"]-r.RESERVE)
    worker = dict(schema_version="e0-stop-anchor-worker-v1", worker_pid=8001, supervisor_pid=8000,
        imports_verified_utc="2026-09-23T12:01:01+00:00", freeze_sha256=manifest["freeze_sha256"],
        resource_receipt_sha256=manifest["resource_receipt_sha256"], environment=env)
    for name, raw in (("run_manifest.json", encoded(manifest)), ("execution_freeze.json", freeze_raw),
                      ("resource_receipt.json", resource_raw), ("worker_receipt.json", encoded(worker))):
        (root/name).write_bytes(raw)
    plan = r.strict_json(blobs[r.PLAN])
    identities = r.planned_identities(plan, blobs[r.SEEDS])
    sources = {key:freeze["source_sha256"][key] for key in r.JOB_SOURCES}
    recording = dict(schema_version="e0-stop-recording-v1", plan=plan, identities=identities,
                     source_sha256=sources, output_bytes_cap=r.CAPS["output_bytes"]-r.RESERVE,
                     execution_released=False)
    (root/"records").mkdir()
    (root/"records/manifest.json").write_bytes(encoded(recording))
    (root/"records/events.jsonl").write_bytes(b"")
    supervisor = dict(schema_version="e0-stop-anchor-supervisor-v1", stop_reason="outer_time_cap",
        child_started=True, child_pid=8001, child_returncode=-9, child_exit_observed=True,
        wall_seconds=598., outer_seconds_cap=600, owned_child_cpu_seconds=1.,
        output_bytes_cap=r.CAPS["output_bytes"], within_wall_cap=True, completed_artifacts_retained=True,
        error=None, note="mock receipt, not an executed numerical run")
    seal(root, supervisor)
    calls = dict(imports=0, ancestry=[], git=[])
    def git_blob(repo_arg, revision, name):
        assert Path(repo_arg) == repo
        calls["git"].append((revision, name))
        return freeze_raw if (revision, name) == (freeze_commit, freeze_path) else blobs[name]
    monkeypatch.setattr(r, "_git_blob", git_blob)
    monkeypatch.setattr(r, "_git_ancestor", lambda repo_arg,a,b: calls["ancestry"].append((a,b)))
    monkeypatch.setattr(r, "_environment", lambda: env)
    def reconcile(events, ids, source):
        assert ids == identities and source == sources
        if not events:
            return [], {}
        # Outer-reader partial-start fixture only; no fake terminal numerical results.
        assert len(events) == 1 and events[0]["event"] == "job_started"
        assert events[0]["identity"] == ids[0]
        return [dict(ids[0]["planned_job"], estimator=e, status="attempted", reason="fixture interrupted")
                for e in r.ESTIMATORS], {0:dict(complete=False, prepared=None)}
    journal = SimpleNamespace(reporting=reporting, _reconcile=reconcile,
                              ARRAYS=("task","S","A","B","elig","Y"),
                              FOLDS=("task_labels","task_index","task_fold_ids","episode_fold_ids"))
    def loader(repo_arg):
        assert Path(repo_arg) == repo
        calls["imports"] += 1
        return journal
    monkeypatch.setattr(r, "_load_journal", loader)
    return SimpleNamespace(repo=repo, root=root, blobs=blobs, env=env, freeze=freeze, manifest=manifest,
        worker=worker, resource=resource, supervisor=supervisor, identities=identities,
        recording=recording, calls=calls, journal=journal)


def test_closed_incomplete_run_preserves_all_slots_and_binding_order(closed):
    out = r.reconcile_run(closed.root, repo=closed.repo)
    assert out["summary"]["planned_estimator_slots"] == 2304
    assert out["summary"]["status_counts"]["unattempted"] == 2304
    assert out["summary"]["truncated"] and out["summary"]["incomplete"]
    assert out["audit"]["input_hashes_stable"]
    assert out["audit"]["child_exit_receipt_verified"] and not out["audit"]["never_spawned"]
    assert out["audit"]["full_process_wall_verified"] is False
    assert out["audit"]["resource_receipt_age_at_recorded_launch_seconds"] == 60
    assert closed.calls["ancestry"] == [("1"*40,"2"*40), ("2"*40,"HEAD")]
    assert len(closed.calls["git"]) == 16 and closed.calls["imports"] == 1
    assert out["audit"]["resources"]["fits"] == out["audit"]["resources"]["sampler_calls"] == 0


def test_never_spawned_is_honest_and_has_no_exit_claim(closed):
    (closed.root/"worker_receipt.json").unlink()
    (closed.root/"records/events.jsonl").unlink()
    (closed.root/"records/manifest.json").unlink()
    (closed.root/"records").rmdir()
    receipt = dict(closed.supervisor, child_started=False, child_pid=None, child_returncode=None,
                   child_exit_observed=False, owned_child_cpu_seconds=None, stop_reason="startup_deadline")
    seal(closed.root, receipt)
    out = r.reconcile_run(closed.root, repo=closed.repo)
    assert out["audit"]["never_spawned"] and not out["audit"]["child_exit_receipt_verified"]
    assert out["summary"]["status_counts"]["unattempted"] == 2304


def test_never_spawned_rejects_scientific_subtree_even_without_events(closed):
    (closed.root/"worker_receipt.json").unlink()
    receipt = dict(closed.supervisor, child_started=False, child_pid=None, child_returncode=None,
                   child_exit_observed=False, owned_child_cpu_seconds=None, stop_reason="startup_failure")
    seal(closed.root, receipt)
    with pytest.raises(ValueError, match="never-spawned"):
        r.reconcile_run(closed.root, repo=closed.repo)


def test_partial_start_and_torn_tail_keep_exact_hash_and_attempts(closed):
    start = dict(event="job_started", identity=closed.identities[0], estimator_ids=list(r.ESTIMATORS))
    tail = b'{"event":"prepared"}'  # Even valid JSON lacks a durable newline.
    (closed.root/"records/events.jsonl").write_bytes(encoded(start)+tail)
    seal(closed.root, closed.supervisor)
    out = r.reconcile_run(closed.root, repo=closed.repo)
    assert out["audit"]["journal"]["ignored_tail_sha256"] == r.sha(tail)
    assert out["audit"]["journal"]["ignored_trailing_bytes"] == len(tail)
    assert out["summary"]["attempted_estimator_slots"] == 24
    assert out["summary"]["status_counts"]["unattempted"] == 2280
    assert out["audit"]["numerical_accounting"]["additional_sampler_attempts_unknown"]


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                                     b'{"x":1e999}', b'\xff', b'{broken}'])
def test_strict_json_rejects_duplicates_nonfinite_and_invalid_bytes(raw):
    with pytest.raises(ValueError):
        r.strict_json(raw)


def test_complete_bad_journal_line_is_not_discarded_as_tail():
    with pytest.raises(ValueError, match="complete journal line"):
        r.parse_journal(b'{"x":1,"x":2}\n')
    with pytest.raises(ValueError, match="object"):
        r.parse_journal(b'[]\n')


@pytest.mark.parametrize("defect", ["open_child", "unobserved_cleanup", "wall_over", "bytes_wrong", "cap_violation", "invented_pid"])
def test_invalid_supervisor_fails_closed_before_scientific_import(closed, defect):
    receipt = dict(closed.supervisor)
    if defect == "open_child": receipt["child_returncode"] = None
    elif defect == "unobserved_cleanup": receipt["child_exit_observed"] = False
    elif defect == "wall_over": receipt["wall_seconds"] = 600.1
    elif defect == "cap_violation": receipt["stop_reason"] = "output_cap_violation"
    elif defect == "invented_pid": receipt["child_pid"] = True
    sealed = seal(closed.root, receipt)
    if defect == "bytes_wrong":
        sealed["total_bytes"] += 1
        (closed.root/"supervisor.json").write_bytes(encoded(sealed))
    with pytest.raises(ValueError):
        r.reconcile_run(closed.root, repo=closed.repo)
    assert closed.calls["imports"] == 0


def test_temp_and_orphan_files_are_counted_not_treated_as_data(closed):
    (closed.root/"records/dataset_095.npz.tmp").write_bytes(b"unfinished archive")
    (closed.root/"orphan.tmp").write_bytes(b"unreferenced")
    seal(closed.root, closed.supervisor)
    out = r.reconcile_run(closed.root, repo=closed.repo)
    assert out["audit"]["unused_artifacts_counted"] == ["orphan.tmp", "records/dataset_095.npz.tmp"]
    assert out["audit"]["raw_snapshot"]["total_bytes"] == sum(
        p.stat().st_size for p in closed.root.rglob("*") if p.is_file())


def test_oversized_sparse_orphan_is_rejected_before_hashing(closed):
    with (closed.root/"orphan.tmp").open("wb") as handle:
        handle.truncate(r.CAPS["output_bytes"]+1)
    with pytest.raises(ValueError, match="temporaries/orphans exceed"):
        r.reconcile_run(closed.root, repo=closed.repo)
    assert closed.calls["imports"] == 0


def test_symlink_artifact_is_rejected(closed):
    (closed.root/"external-link").symlink_to(closed.repo)
    with pytest.raises(ValueError, match="symlink"):
        r.reconcile_run(closed.root, repo=closed.repo)


@pytest.mark.parametrize("defect", ["raw_freeze", "raw_resource", "local_source", "environment", "committed_freeze", "ancestry"])
def test_source_release_and_environment_verified_before_import(closed, monkeypatch, defect):
    if defect == "raw_freeze":
        (closed.root/"execution_freeze.json").write_bytes(encoded({**closed.freeze,"execution_released":False}))
    elif defect == "raw_resource":
        (closed.root/"resource_receipt.json").write_bytes(encoded({**closed.resource,"host":"changed"}))
    elif defect == "local_source":
        (closed.repo/"experiments/e0/stop_anchor_report.py").write_text("# changed\n")
    elif defect == "environment": monkeypatch.setattr(r,"_environment",lambda: {})
    elif defect == "committed_freeze": monkeypatch.setattr(r,"_git_blob",lambda *args: b"wrong blob")
    else:
        def not_ancestor(*args): raise ValueError("not an ancestor")
        monkeypatch.setattr(r,"_git_ancestor",not_ancestor)
    seal(closed.root,closed.supervisor)
    with pytest.raises(ValueError): r.reconcile_run(closed.root,repo=closed.repo)
    assert closed.calls["imports"] == 0


def test_startup_receipt_age_is_checked_at_launch_not_current_clock(closed):
    out = r.reconcile_run(closed.root,repo=closed.repo)
    assert out["audit"]["resource_receipt_age_at_recorded_launch_seconds"] == 60
    manifest = dict(closed.manifest, started_utc="2026-09-23T12:06:00+00:00")
    (closed.root/"run_manifest.json").write_bytes(encoded(manifest))
    seal(closed.root,closed.supervisor)
    with pytest.raises(ValueError,match="fresh at recorded launch"):
        r.reconcile_run(closed.root,repo=closed.repo)


def test_production_provenance_rejects_handcrafted_and_seed_coercion(closed):
    event = dict(event="prepared",identity=closed.identities[0],provenance=dict(
        source_sha256={k:closed.freeze["source_sha256"][k] for k in r.JOB_SOURCES},
        **{k:closed.env[k] for k in ("python","numpy","scipy")},
        data_mode="production_sampler", data_seed=closed.identities[0]["job"]["data_seed"],
        fold_seed=closed.identities[0]["job"]["fold_seed"], data_rng_initial_state_sha256="b"*64,
        data_rng="numpy.Generator(numpy.PCG64(numpy.SeedSequence(int(data_seed))))",
        fold_rng="history.make_task_folds: numpy.default_rng(int(fold_seed)).permutation"))
    r._production_provenance(event,closed.freeze)
    changed = copy.deepcopy(event); changed["provenance"]["data_mode"] = "handcrafted_injection"
    with pytest.raises(ValueError,match="nonproduction"):
        r._production_provenance(changed,closed.freeze)
    changed = copy.deepcopy(event); changed["provenance"]["data_seed"] = int(changed["provenance"]["data_seed"])
    with pytest.raises(ValueError,match="nonproduction"):
        r._production_provenance(changed,closed.freeze)


def test_archive_hash_and_path_fail_before_numeric_loading(closed):
    (closed.root/"records/dataset_000.npz").write_bytes(b"not a validated array archive")
    snapshot = r._snapshot(closed.root)
    event = dict(event="prepared",identity=closed.identities[0],archive=dict(
        path="dataset_000.npz",bytes=1,sha256="0"*64))
    with pytest.raises(ValueError,match="byte/hash"):
        r._archives(closed.root,snapshot,[event],closed.journal)
    event["archive"]["path"] = "../dataset_000.npz"
    with pytest.raises(ValueError,match="reference/path"):
        r._archives(closed.root,snapshot,[event],closed.journal)


def test_raw_change_during_audit_prevents_output(closed,monkeypatch,tmp_path):
    def changed_loader(repo):
        (closed.root/"orphan_after_start.tmp").write_bytes(b"changed")
        return closed.journal
    monkeypatch.setattr(r,"_load_journal",changed_loader)
    target = tmp_path/"derived.json"
    with pytest.raises(ValueError,match="changed during reconciliation"):
        r.write_derived(closed.root,target,repo=closed.repo)
    assert not target.exists()


def test_derived_output_is_external_exclusive_and_raw_snapshot_unchanged(closed,tmp_path):
    before = r._snapshot(closed.root)
    with pytest.raises(ValueError,match="outside"):
        r.write_derived(closed.root,closed.root/"derived.json",repo=closed.repo)
    target = tmp_path/"derived.json"
    out = r.write_derived(closed.root,target,repo=closed.repo)
    assert json.loads(target.read_text()) == out
    assert r._snapshot(closed.root) == before
    with pytest.raises(FileExistsError):
        r.write_derived(closed.root,target,repo=closed.repo)


def test_normal_exit_cannot_invent_completed_study(closed):
    seal(closed.root,dict(closed.supervisor,stop_reason="child_complete",child_returncode=0))
    with pytest.raises(ValueError,match="normal completion"):
        r.reconcile_run(closed.root,repo=closed.repo)


def test_reported_fit_counters_and_missing_totals_are_honest():
    identity = dict(job=dict(replicate=0))
    start = dict(event="variant_started",identity=identity,variant="history_lambda5_recursive")
    terminal = dict(event="variant",identity=identity,variant=start["variant"],
        backward_fit_attempts=3,backward_fits_completed=3,wall_seconds=1.,cpu_seconds=.8,
        records=[dict(status="completed"),dict(status="completed")])
    states = {0:dict(prepared=("data","fold"),complete=False)}
    unclosed = r._numerical_accounting([start,terminal],states)
    assert unclosed["reported_terminal_variant_fit_attempts"] == 3
    assert unclosed["additional_sampler_attempts_unknown"]
    assert not unclosed["additional_fit_attempts_unknown"]
    unfinished = r._numerical_accounting([start],states)
    assert unfinished["additional_fit_attempts_unknown"]
    resources = dict(backward_fit_attempts=3,backward_fits_completed=3,sampler_attempts=1,
        wall_seconds=2.,cpu_seconds=1.,model_calls=0,benchmark_executions=0,paid_usd=0)
    end = dict(event="job_complete",identity=identity,resources=resources)
    complete = r._numerical_accounting([start,terminal,end],states)
    assert complete["reported_completed_job_sampler_attempts"] == 1
    assert complete["reported_terminal_variant_wall_seconds"] == 1
    assert complete["reported_completed_job_wall_seconds"] == 2
    changed = copy.deepcopy(terminal); changed["backward_fits_completed"] = 4
    with pytest.raises(ValueError,match="fit counters"):
        r._numerical_accounting([start,changed],states)
    changed = copy.deepcopy(end); changed["resources"]["backward_fit_attempts"] = 2
    with pytest.raises(ValueError,match="counters disagree"):
        r._numerical_accounting([start,terminal,changed],states)
    changed = copy.deepcopy(terminal); changed["variant"] = "history_lambda5_evaluation_only"
    with pytest.raises(ValueError,match="fit counters"):
        r._numerical_accounting([changed],states)
