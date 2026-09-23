"""Handwritten journal fixtures only: no sampling, fitting or subprocess jobs."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reconciliation", ROOT / "scripts/reconcile_regularization_journal.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def enc(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    # Actual frozen sources are read, never executed (except the reporting module).
    freeze = json.loads((ROOT / "docs/e0_regularization_execution_freeze_20260923.json").read_bytes())
    blobs = {path: (ROOT / path).read_bytes() for path in r.SOURCES}
    freeze["source_sha256"] = {path: r.sha(raw) for path, raw in blobs.items()}
    monkeypatch.setattr(r, "_git_blob", lambda repo, rev, path: blobs[path])
    identities = r.planned_identities(json.loads(blobs[r.PLAN]), blobs[r.SEEDS])
    run = tmp_path / "raw"
    run.mkdir()
    manifest = dict(freeze=freeze, freeze_sha256="a"*64,
                    resource_receipt={"freeze_sha256": "a"*64},
                    output_bytes_cap=268435456, model_calls=0, paid_usd=0)
    supervisor = dict(schema_version="e0-supervisor-v1", stop_reason="outer_time_cap",
                      child_returncode=-15, child_exit_observed=True,
                      outer_seconds_cap=600, output_bytes_cap=268435456)
    for name, obj in (("run_manifest.json", manifest), ("supervisor.json", supervisor),
                      ("planned_jobs.json", [i["planned_job"] for i in identities])):
        (run / name).write_bytes(enc(obj))
    (run / "events.jsonl").write_bytes(b"")
    return run, identities, freeze, blobs


def attempt(identity):
    return dict(event="attempted", identity=identity, job=identity["job"], estimator_slots=list(r.ESTIMATORS))


def provenance(identity, freeze):
    fields = {"fixture": {"json_value": "handwritten descriptor; no dataset generated"}}
    labels = list(range(230))
    indices = [i for i in labels for _ in range(40)]
    assignments = [i % 3 for i in labels]
    folds = dict(task_labels=labels, task_index=indices, task_fold_ids=assignments,
                 episode_fold_ids=[assignments[i] for i in indices])
    return dict(source_sha256={k: freeze["source_sha256"][k] for k in r.JOB_SOURCES},
                **{k: freeze["environment"][k] for k in ("python", "numpy", "scipy")},
                data_mode="production_sampler", data_seed=identity["job"]["data_seed"],
                fold_seed=identity["job"]["fold_seed"],
                dataset=dict(fields=fields, sha256=r.digest(fields)),
                folds={**folds, "sha256": r.digest(folds)})


def prepare(identity, freeze):
    return dict(event="prepared", identity=identity, job_index=identity["job"]["job_index"],
                provenance=provenance(identity, freeze))


def variant(identity, preparation, name="compressed_lambda0"):
    records = [dict(identity["planned_job"], estimator=f"{name}:{m}", status="completed", estimate=.5)
               for m in ("plugin", "dr")]
    records[1]["interval"] = dict(status="failed", reason="handwritten interval failure")
    p = preparation["provenance"]
    return dict(event="variant", identity=identity, job_index=identity["job"]["job_index"], variant=name,
                records=records, dataset_sha256=p["dataset"]["sha256"], fold_sha256=p["folds"]["sha256"])


def save(run, events, tail=b""):
    raw = b"".join(enc(event) + b"\n" for event in events) + tail
    (run / "events.jsonl").write_bytes(raw)
    return raw


def test_empty_run_preserves_4800_slots(bundle):
    run, _, _, _ = bundle
    result = r.reconcile_run(run)
    assert len(result["summary"]["slots"]) == 4800
    assert all(s["status"] == "unattempted" for s in result["summary"]["slots"])
    assert result["summary"]["incomplete"] is True
    assert result["audit"]["state"]["attempted_jobs"] == 0


def test_partial_variant_and_tail_preserve_attempts_and_raw_bytes(bundle):
    run, ids, freeze, _ = bundle
    p = prepare(ids[0], freeze)
    raw = save(run, [attempt(ids[0]), p, variant(ids[0], p)], b'{"event":"var')
    result = r.reconcile_run(run)
    statuses = [s["status"] for s in result["summary"]["slots"]]
    assert statuses.count("completed") == 2
    assert statuses.count("attempted") == 6
    assert statuses.count("unattempted") == 4792
    assert result["summary"]["incomplete"]
    assert result["audit"]["journal"]["ignored_trailing_bytes"] == 13
    assert result["audit"]["raw_inputs"]["events.jsonl"]["sha256"] == r.sha(raw)
    assert (run / "events.jsonl").read_bytes() == raw


@pytest.mark.parametrize("raw", [b'{bad}\n', b'\n', b'[]\n', b'{"a":1,"a":2}\n', b'{"a":NaN}\n'])
def test_malformed_complete_lines_rejected(raw):
    with pytest.raises(ValueError):
        r.parse_journal(raw)


def test_valid_but_unterminated_json_is_explicitly_ignored():
    events, audit = r.parse_journal(b'{"event":"attempted"}')
    assert events == [] and audit["truncated_final_line"]
    assert audit["ignored_trailing_bytes"] == 21


@pytest.mark.parametrize("fault", ["duplicate_attempt", "unprepared", "duplicate_variant", "bad_data", "bad_fold",
                                  "bad_identity", "premature_complete", "next_job_early", "after_worker_failure"])
def test_transition_and_binding_rejections(bundle, fault):
    run, ids, freeze, _ = bundle
    p = prepare(ids[0], freeze)
    v = variant(ids[0], p)
    events = [attempt(ids[0]), p, v]
    if fault == "duplicate_attempt": events = [attempt(ids[0]), attempt(ids[0])]
    elif fault == "unprepared": events = [attempt(ids[0]), v]
    elif fault == "duplicate_variant": events.append(copy.deepcopy(v))
    elif fault == "bad_data": v["dataset_sha256"] = "0"*64
    elif fault == "bad_fold": p["provenance"]["folds"]["task_fold_ids"][0] = 2
    elif fault == "bad_identity": v["records"][0]["pairing_id"] = "wrong"
    elif fault == "premature_complete": events.append(dict(event="job_complete", job_index=0))
    elif fault == "next_job_early": events.append(attempt(ids[1]))
    elif fault == "after_worker_failure": events = [dict(event="worker_failure", reason="x", error_type="RuntimeError"), attempt(ids[0])]
    save(run, events)
    with pytest.raises(ValueError):
        r.reconcile_run(run)


def test_job_failure_is_eight_terminal_attempts_and_complete_marker(bundle):
    run, ids, freeze, _ = bundle
    records = [dict(ids[0]["planned_job"], estimator=e, status="failed", reason="fixture failure") for e in r.ESTIMATORS]
    failed = dict(event="job_failed", identity=ids[0], job_index=0,
                  provenance=provenance(ids[0], freeze), records=records)
    save(run, [attempt(ids[0]), failed, dict(event="job_complete", job_index=0)])
    result = r.reconcile_run(run)
    assert result["audit"]["state"]["completed_jobs"] == 1
    assert sum(s["status"] == "failed" for s in result["summary"]["slots"]) == 8
    assert result["summary"]["incomplete"]


def test_false_normal_exit_does_not_make_incomplete_journal_complete(bundle):
    run, _, _, _ = bundle
    s = json.loads((run / "supervisor.json").read_bytes())
    s.update(stop_reason="child_complete", child_returncode=0)
    (run / "supervisor.json").write_bytes(enc(s))
    result = r.reconcile_run(run)
    assert result["audit"]["normal_child_exit"]
    assert not result["audit"]["journal_complete_normal_run"]
    assert result["summary"]["incomplete"]


def test_unconfirmed_child_exit_cannot_supply_closed_snapshot(bundle):
    run, _, _, _ = bundle
    s = json.loads((run / "supervisor.json").read_bytes())
    s["child_exit_observed"] = False
    (run / "supervisor.json").write_bytes(enc(s))
    with pytest.raises(ValueError, match="supervisor"):
        r.reconcile_run(run)


def test_changed_pinned_source_and_plan_refused(bundle):
    run, _, _, blobs = bundle
    original = blobs[r.PLAN]
    blobs[r.PLAN] = original + b" "
    with pytest.raises(ValueError, match="source blob hash"):
        r.reconcile_run(run)
    blobs[r.PLAN] = original
    planned = json.loads((run / "planned_jobs.json").read_bytes())
    planned[0]["pairing_id"] = "wrong"
    (run / "planned_jobs.json").write_bytes(enc(planned))
    with pytest.raises(ValueError, match="planned_jobs"):
        r.reconcile_run(run)


def test_derived_output_exclusive_and_outside_raw(bundle):
    run, _, _, _ = bundle
    with pytest.raises(ValueError, match="outside"):
        r.write_derived(run, run / "derived.json")
    output = run.parent / "derived.json"
    r.write_derived(run, output)
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        r.write_derived(run, output)
    assert output.read_bytes() == original
