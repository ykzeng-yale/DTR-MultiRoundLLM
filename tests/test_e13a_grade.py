"""E13a private grading driver: injected-fake fixtures only.

No receiver call, no model call, no sandbox start, no candidate/reference/containment execution. The private
executor is always a deterministic stub, so every graded row these tests produce is transport-only.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e13a_grade = _load("e13a_grade", "scripts/e13a_grade.py")
e13a_analyze = _load("e13a_analyze", "scripts/e13a_analyze.py")
digest = e13a_grade.digest
HandoffRefusal = e13a_grade.HandoffRefusal

ROOTS = ["mbpp/842", "mbpp/288"]
ARMS = {"R1": [2, 3], "FRESH": [0, 1]}
GOOD = "```python\ndef f(x):\n    return x + 1\n```\n"
BAD = "```python\ndef f(x):\n    return 0\n```\n"
AMBIGUOUS = "```python\ndef f(x):\n    return 1\n```\n```python\ndef f(x):\n    return 2\n```\n"
MODEL_PIN = {"name": "fixture-model", "digest": "sha256:" + "0" * 64}
EVALUATOR_PIN = {"suite": "landmark-private-tests-v1", "version": "fixture"}


def stage_descriptor(roots=ROOTS, arms=ARMS):
    return {
        "stage": "E13a",
        "status": "PROPOSED, NOT RELEASED; fixture",
        "evidence_class": "development_followup_post_hoc_motivated",
        "roots": list(roots),
        "arms": {arm: list(reps) for arm, reps in arms.items()},
        "contrast": {"treatment": "R1", "reference": "FRESH"},
    }


def request_plan(roots=ROOTS, arms=ARMS):
    plan_roots = []
    for root_id in roots:
        requests = []
        for arm, reps in arms.items():
            for rep in reps:
                requests.append({"arm": arm, "replicate": rep, "seed_key": f"{arm}:{rep}",
                                 "seed": 1000 + rep, "messages_sha256": digest([root_id, arm, rep])})
        plan_roots.append({"root_id": root_id, "requests": requests})
    return {"plan_version": "e13a-request-plan-fixture", "roots": plan_roots}


def slots(roots=ROOTS, arms=ARMS):
    return [(root_id, arm, rep) for root_id in roots for arm, reps in arms.items() for rep in reps]


def build_release(tmp_path, roots=ROOTS, n_assigned=None, limits=None, controls_per_root=1,
                  contract_pin=True):
    """An e13a_release-equivalent fixture: same manifest keys, package hashes and grading_limits shape."""
    release = tmp_path / "e13a_release"
    release.mkdir(parents=True)
    tasks = [{"root_id": r, "family_id": f"family-{i}", "prompt": "Implement f(x).",
              "public_context": "The public example is f(0)=1."} for i, r in enumerate(roots)]
    specs = []
    for task in tasks:
        specs.append({
            "root_id": task["root_id"], "public_task_sha256": digest(task), "entry_point": "f",
            "public_assertions": ["assert f(0)==1"], "private_assertions": ["assert f(2)==3"],
            "preamble": [], "reference_code": "def f(x):\n    return x + 1\n",
            "negative_controls": [
                {"code": f"def f(x):\n    return {i}\n",
                 "rationale": f"Constant {i} is wrong for the private input 2 whose specified output is 3."}
                for i in range(controls_per_root)],
        })
    (release / "tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks))
    (release / "private_specs.jsonl").write_text("".join(json.dumps(s) + "\n" for s in specs))
    (release / "config.json").write_text(json.dumps({"release": "e13a-fixture"}, indent=1) + "\n")
    assigned = n_assigned if n_assigned is not None else len(slots(roots))
    limits = limits or {"n_roots": len(roots), "artifact_starts": assigned, "recheck_starts": 10,
                        "containment_starts": 9, "max_private_starts": assigned + 19, "grading_seconds": 300}
    bindings = {}
    if contract_pin:
        bindings = {"expected_contract_sha256": digest(e13a_grade.private_grade.contract(specs))}
    manifest = {"manifest": "e13a-release-fixture", "n_roots": len(roots), "roots": list(roots),
                "model": MODEL_PIN, "evaluator": EVALUATOR_PIN,
                "package": {name: e13a_grade.file_sha(release / name)
                            for name in ("tasks.jsonl", "private_specs.jsonl", "config.json")},
                "grading_limits": limits, "grading_bindings": bindings}
    (release / "release_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return release


def build_collection(tmp_path, release, roots=ROOTS, arms=ARMS, outputs=None, missing=None,
                     name="run", stage=None, plan=None, stage_path=None, plan_path=None):
    """Write a collect/ handoff the driver accepts: artifacts, calls.jsonl, manifest.json, completion.json."""
    run = tmp_path / name
    collect = run / "collect"
    (collect / "artifacts").mkdir(parents=True)
    if stage_path is None:
        stage = stage if stage is not None else stage_descriptor(roots, arms)
        stage_path = run / "stage.json"
        stage_path.write_text(json.dumps(stage, indent=1) + "\n")
    else:
        stage_path = Path(stage_path)
        stage = json.loads(stage_path.read_text())
    if plan_path is None:
        plan = plan if plan is not None else request_plan(roots, arms)
        plan_path = run / "plan.json"
        plan_path.write_text(json.dumps(plan, indent=1) + "\n")
    else:
        plan_path = Path(plan_path)
        plan = json.loads(plan_path.read_text())
    if stage.get("arms") and stage.get("roots"):
        roots, arms = list(stage["roots"]), {a: list(r) for a, r in stage["arms"].items()}
    release_manifest = json.loads((release / "release_manifest.json").read_text())
    requests = {(entry["root_id"], r["arm"], r["replicate"]): r
                for entry in plan["roots"] for r in entry["requests"]}
    outputs = outputs or {}
    missing = missing or {}
    rows = []
    for slot in slots(roots, arms):
        root_id, arm, rep = slot
        request = requests[slot]
        base = {"root_id": root_id, "arm": arm, "replicate": rep, "seed": request["seed"],
                "messages_sha256": request["messages_sha256"], "calls": 1, "prompt_tokens": 11,
                "completion_tokens": 22}
        if slot in missing:
            rows.append({**base, "status": "unavailable", "artifact_path": None, "output_sha256": None,
                         "missing_reason": missing[slot]})
            continue
        text = outputs.get(slot, GOOD)
        relpath = f"artifacts/{root_id.replace('/', '_')}_{arm}_{rep}.txt"
        (collect / relpath).write_text(text)
        rows.append({**base, "status": "completed", "artifact_path": relpath,
                     "output_sha256": digest(text), "missing_reason": None})
    (collect / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    checksums = {str(p.relative_to(collect)): e13a_grade.file_sha(p)
                 for p in sorted(collect.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    manifest = {"stage": stage["stage"], "stage_descriptor_path": str(stage_path),
                "stage_descriptor_sha256": e13a_grade.file_sha(stage_path),
                "request_plan_path": str(plan_path), "request_plan_sha256": e13a_grade.file_sha(plan_path),
                "release_manifest_path": str(release / "release_manifest.json"),
                "release_manifest_sha256": e13a_grade.file_sha(release / "release_manifest.json"),
                "grader_version": e13a_grade.private_grade.GRADER_VERSION,
                "model": release_manifest["model"], "evaluator": release_manifest["evaluator"],
                "transport_only": True,
                "checksums": checksums}
    (collect / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    completion = {"stage": stage["stage"], "manifest_sha256": e13a_grade.file_sha(collect / "manifest.json"),
                  "assigned": len(rows), "dispatched": len(rows),
                  "completed": sum(1 for r in rows if r["artifact_path"] is not None), "status": "complete"}
    (collect / "completion.json").write_text(json.dumps(completion, indent=1) + "\n")
    return {"run": run, "collect": collect, "stage": stage_path, "plan": plan_path, "release": release}


def rewrite(path, mutate):
    data = json.loads(Path(path).read_text())
    mutate(data)
    Path(path).write_text(json.dumps(data, indent=1) + "\n")


def rewrite_calls(path, mutate):
    rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    rows = mutate(rows)
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))


def reseal(collect):
    """Recompute manifest checksums and the completion binding after a deliberate edit to calls.jsonl."""
    manifest = json.loads((collect / "manifest.json").read_text())
    manifest["checksums"] = {str(p.relative_to(collect)): e13a_grade.file_sha(p)
                             for p in sorted(collect.rglob("*"))
                             if p.is_file() and p.name not in ("manifest.json", "completion.json")}
    (collect / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    completion = json.loads((collect / "completion.json").read_text())
    completion["manifest_sha256"] = e13a_grade.file_sha(collect / "manifest.json")
    (collect / "completion.json").write_text(json.dumps(completion, indent=1) + "\n")


@pytest.fixture
def handoff(tmp_path):
    release = build_release(tmp_path)
    return build_collection(tmp_path, release)


def validate(h):
    return e13a_grade.validate_handoff(h["collect"], h["stage"], h["plan"])


def run_grade(h, tmp_path, executor=None, out="out", **kwargs):
    return e13a_grade.grade(h["collect"], h["release"], tmp_path / out,
                            executor=executor if executor is not None else e13a_grade.StubPrivateExecutor(
                                default_candidate=1),
                            real=False, stage=h["stage"], plan=h["plan"], **kwargs)


# ---------------------------------------------------------------- validate_handoff


def test_clean_handoff_validates_every_assigned_slot(handoff):
    result = validate(handoff)
    assert len(result["order"]) == len(slots()) == 8
    assert len(result["artifacts"]) == 8
    assert result["grading_limits"]["containment_starts"] == 9
    assert result["pins"]["grader_version"] == e13a_grade.private_grade.GRADER_VERSION


def test_tampered_artifact_bytes_refused(handoff):
    artifact = next((handoff["collect"] / "artifacts").glob("*.txt"))
    artifact.write_text(BAD)
    with pytest.raises(HandoffRefusal, match="does not match its recorded checksum"):
        validate(handoff)


def test_wrong_recorded_output_digest_refused(handoff):
    rewrite_calls(handoff["collect"] / "calls.jsonl",
                  lambda rows: [{**r, "output_sha256": digest("other")} if i == 0 else r
                                for i, r in enumerate(rows)])
    reseal(handoff["collect"])
    with pytest.raises(HandoffRefusal, match="do not match the output digest recorded"):
        validate(handoff)


def test_absent_assigned_slot_refused(handoff):
    rewrite_calls(handoff["collect"] / "calls.jsonl", lambda rows: rows[1:])
    reseal(handoff["collect"])
    with pytest.raises(HandoffRefusal, match="absent from calls.jsonl"):
        validate(handoff)


def test_duplicate_slot_refused(handoff):
    rewrite_calls(handoff["collect"] / "calls.jsonl", lambda rows: rows + [rows[0]])
    reseal(handoff["collect"])
    with pytest.raises(HandoffRefusal, match="duplicate records for assigned slot"):
        validate(handoff)


def test_unassigned_slot_refused(handoff):
    rewrite_calls(handoff["collect"] / "calls.jsonl",
                  lambda rows: rows + [{**rows[0], "replicate": 99}])
    reseal(handoff["collect"])
    with pytest.raises(HandoffRefusal, match="unassigned slot"):
        validate(handoff)


def test_request_pin_mismatch_refused(handoff):
    rewrite_calls(handoff["collect"] / "calls.jsonl",
                  lambda rows: [{**r, "seed": 7} if i == 0 else r for i, r in enumerate(rows)])
    reseal(handoff["collect"])
    with pytest.raises(HandoffRefusal, match="but the assignment pins"):
        validate(handoff)


def test_stale_stage_pin_refused(handoff):
    rewrite(handoff["stage"], lambda d: d.update(status="EDITED AFTER COLLECTION"))
    with pytest.raises(HandoffRefusal, match="stale or wrong stage pin"):
        validate(handoff)


def test_stale_release_pin_refused(handoff):
    rewrite(handoff["collect"] / "manifest.json",
            lambda d: d.update(release_manifest_sha256="f" * 64))
    reseal(handoff["collect"])
    with pytest.raises(HandoffRefusal, match="stale or wrong release pin"):
        validate(handoff)


def test_wrong_release_directory_refused(tmp_path, handoff):
    other = build_release(tmp_path / "other", roots=ROOTS)
    with pytest.raises(HandoffRefusal, match="does not hold the release manifest the collection pinned"):
        e13a_grade.grade(handoff["collect"], other, tmp_path / "out-wrong-release",
                         executor=e13a_grade.StubPrivateExecutor(), real=False,
                         stage=handoff["stage"], plan=handoff["plan"])
    assert not (tmp_path / "out-wrong-release").exists()


def test_grader_version_pin_mismatch_refused(handoff):
    rewrite(handoff["collect"] / "manifest.json", lambda d: d.update(grader_version="landmark-grader-v4-stale"))
    reseal(handoff["collect"])
    with pytest.raises(HandoffRefusal, match="grader pin mismatch"):
        validate(handoff)


def test_model_pin_mismatch_refused(handoff):
    rewrite(handoff["collect"] / "manifest.json",
            lambda d: d.update(model={"name": "other-model", "digest": "sha256:" + "1" * 64}))
    reseal(handoff["collect"])
    with pytest.raises(HandoffRefusal, match="model pin mismatch"):
        validate(handoff)


def test_unlisted_written_file_refused(handoff):
    (handoff["collect"] / "artifacts" / "sneaked.txt").write_text("not in the checksums")
    with pytest.raises(HandoffRefusal, match="do not cover the written files exactly"):
        validate(handoff)


def test_completion_record_must_bind_the_manifest(handoff):
    rewrite(handoff["collect"] / "manifest.json", lambda d: d.update(transport_only=True, note="late edit"))
    with pytest.raises(HandoffRefusal, match="does not bind the collection manifest bytes"):
        validate(handoff)


def test_completion_counts_must_match_the_ledger(handoff):
    rewrite(handoff["collect"] / "completion.json", lambda d: d.update(completed=1))
    rewrite(handoff["collect"] / "manifest.json", lambda d: d)
    completion = json.loads((handoff["collect"] / "completion.json").read_text())
    completion["manifest_sha256"] = e13a_grade.file_sha(handoff["collect"] / "manifest.json")
    (handoff["collect"] / "completion.json").write_text(json.dumps(completion, indent=1) + "\n")
    with pytest.raises(HandoffRefusal, match="completed slots"):
        validate(handoff)


def test_validate_handoff_writes_nothing_on_refusal(tmp_path, handoff):
    artifact = next((handoff["collect"] / "artifacts").glob("*.txt"))
    artifact.write_text(BAD)
    with pytest.raises(HandoffRefusal):
        e13a_grade.grade(handoff["collect"], handoff["release"], tmp_path / "refused",
                         executor=e13a_grade.StubPrivateExecutor(), real=False,
                         stage=handoff["stage"], plan=handoff["plan"])
    assert not (tmp_path / "refused").exists()


def test_grading_limits_shape_is_strict(tmp_path):
    release = build_release(tmp_path, limits={"n_roots": 2, "artifact_starts": 8, "recheck_starts": 10,
                                              "containment_starts": 9, "max_private_starts": 8 + 19 + 1,
                                              "grading_seconds": 300})
    with pytest.raises(HandoffRefusal, match="max_private_starts must equal"):
        e13a_grade.load_e13a_grading_limits((release / "release_manifest.json").read_bytes())


def test_missing_grading_limits_is_refused_not_defaulted(tmp_path):
    release = build_release(tmp_path)
    rewrite(release / "release_manifest.json", lambda d: d.pop("grading_limits"))
    with pytest.raises(HandoffRefusal, match="must declare grading_limits"):
        e13a_grade.load_e13a_grading_limits((release / "release_manifest.json").read_bytes())


# ---------------------------------------------------------------- grade


def test_refuses_to_overwrite_existing_grade_output(tmp_path, handoff):
    (tmp_path / "out" / "grade").mkdir(parents=True)
    with pytest.raises(HandoffRefusal, match="Refusing to overwrite"):
        run_grade(handoff, tmp_path)


def test_grade_produces_one_row_per_assigned_slot(tmp_path, handoff):
    summary = run_grade(handoff, tmp_path)
    rows = [json.loads(x) for x in (tmp_path / "out/grade/grades.jsonl").read_text().splitlines()]
    assert summary["status"] == "complete"
    assert summary["assigned_slots"] == summary["grade_rows"] == len(rows) == 8
    assert {(r["root_id"], r["arm"], r["replicate"]) for r in rows} == set(slots())
    assert all(r["outcome"] == 1 and r["missing_reason"] is None for r in rows)
    assert all(r["transport_only"] is True for r in rows)
    assert summary["receiver_calls"] == 0 and summary["model_calls"] == 0
    assert (tmp_path / "out/grade/grading_attempts.jsonl").is_file()
    assert summary["checksums"]["grades.jsonl"] == e13a_grade.file_sha(tmp_path / "out/grade/grades.jsonl")


def test_start_ceilings_are_enforced_without_dropping_rows(tmp_path):
    release = build_release(tmp_path, controls_per_root=2,
                            limits={"n_roots": 2, "artifact_starts": 8, "recheck_starts": 2,
                                    "containment_starts": 0, "max_private_starts": 10, "grading_seconds": 300})
    h = build_collection(tmp_path, release)
    summary = run_grade(h, tmp_path)
    rows = [json.loads(x) for x in (tmp_path / "out/grade/grades.jsonl").read_text().splitlines()]
    assert len(rows) == 8, "a reached ceiling must never drop an assigned row"
    used = summary["start_accounting"]["used"]
    assert used["recheck"] <= 2 and used["total"] <= 10
    assert all(r["outcome"] is None and r["missing_reason"] for r in rows)
    reasons = {r["missing_reason"].split(":")[0] for r in rows}
    assert reasons <= {"negative_control_validation_failed_or_unavailable",
                       "reference_validation_failed_or_unavailable"}
    refused = summary["start_accounting"]["refused_starts"]
    assert any(x["reason"].startswith("start_ceiling_reached") for x in refused)


def test_seconds_cap_blocks_starts_and_keeps_every_row(tmp_path, handoff):
    class Clock:
        def check(self, phase):
            assert phase == "private_grading"

        def remaining(self, phase):
            return 0.5

    summary = run_grade(handoff, tmp_path, clock=Clock())
    rows = [json.loads(x) for x in (tmp_path / "out/grade/grades.jsonl").read_text().splitlines()]
    assert len(rows) == 8 and all(r["outcome"] is None for r in rows)
    assert summary["start_accounting"]["used"]["total"] == 0
    assert all(x["reason"] == "grading_seconds_exhausted"
               for x in summary["start_accounting"]["refused_starts"])


def test_cache_hit_reduces_starts_without_dropping_rows(tmp_path, handoff):
    summary = run_grade(handoff, tmp_path)
    rows = [json.loads(x) for x in (tmp_path / "out/grade/grades.jsonl").read_text().splitlines()]
    # Every slot at a root carries identical output bytes in the fixture: one candidate start per root.
    assert summary["start_accounting"]["used"]["candidate"] == len(ROOTS) < len(rows)
    assert summary["cache_hits"] == len(rows) - len(ROOTS)
    assert len(rows) == 8 and all(r["outcome"] == 1 for r in rows)
    assert sum(r["executor_starts"] for r in rows) == len(ROOTS)


def test_format_rejection_scores_without_a_start(tmp_path):
    release = build_release(tmp_path)
    bad_slot = slots()[0]
    h = build_collection(tmp_path, release, outputs={bad_slot: AMBIGUOUS})
    summary = run_grade(h, tmp_path)
    rows = {(r["root_id"], r["arm"], r["replicate"]): r
            for r in map(json.loads, (tmp_path / "out/grade/grades.jsonl").read_text().splitlines())}
    assert rows[bad_slot]["outcome"] == 0 and rows[bad_slot]["missing_reason"] is None
    assert rows[bad_slot]["executor_starts"] == 0
    assert summary["format_rejections"] == 1
    assert len(rows) == 8


def test_missing_collection_outcome_is_preserved_not_zero_filled(tmp_path):
    release = build_release(tmp_path)
    gap = slots()[0]
    h = build_collection(tmp_path, release, missing={gap: "receiver_unavailable"})
    summary = run_grade(h, tmp_path)
    rows = {(r["root_id"], r["arm"], r["replicate"]): r
            for r in map(json.loads, (tmp_path / "out/grade/grades.jsonl").read_text().splitlines())}
    assert rows[gap]["outcome"] is None and rows[gap]["missing_reason"] == "receiver_unavailable"
    assert summary["graded_slots"] == 7 and summary["grade_rows"] == 8
    assert summary["missing_slots"] == [{"root_id": gap[0], "arm": gap[1], "replicate": gap[2],
                                        "missing_reason": "receiver_unavailable"}]


def test_unavailable_executor_outcome_is_not_a_failure(tmp_path):
    release = build_release(tmp_path)
    h = build_collection(tmp_path, release)
    executor = e13a_grade.StubPrivateExecutor(default_candidate="unavailable")
    summary = run_grade(h, tmp_path, executor=executor)
    rows = [json.loads(x) for x in (tmp_path / "out/grade/grades.jsonl").read_text().splitlines()]
    assert len(rows) == 8
    assert all(r["outcome"] is None and r["missing_reason"] == "grader_execution_unavailable" for r in rows)
    assert summary["graded_slots"] == 0


def test_integrity_abort_retains_every_assigned_slot(tmp_path):
    release = build_release(tmp_path)
    h = build_collection(tmp_path, release)

    class Tampering(e13a_grade.StubPrivateExecutor):
        """Test-only fake: mutates an artifact on disk to trip the grade-time digest re-bind."""

        def __init__(self, collect):
            super().__init__(default_candidate=1)
            self.collect = collect
            self.tampered = False

        def set_context(self, root_id, kind, code_sha256):
            super().set_context(root_id, kind, code_sha256)
            if kind == "candidate" and not self.tampered:
                self.tampered = True
                for artifact in sorted((self.collect / "artifacts").glob("*.txt"))[-1:]:
                    artifact.write_text(BAD)

    summary = run_grade(h, tmp_path, executor=Tampering(h["collect"]))
    rows = [json.loads(x) for x in (tmp_path / "out/grade/grades.jsonl").read_text().splitlines()]
    assert summary["status"] == "aborted" and "no longer match the recorded output digest" in summary["abort_reason"]
    assert len(rows) == 8 and {(r["root_id"], r["arm"], r["replicate"]) for r in rows} == set(slots())
    failure = json.loads((tmp_path / "out/grade/failure_report.json").read_text())
    assert failure["retained_slots"] == failure["assigned_slots"] == 8
    aborted = [r for r in rows if r["missing_reason"] and r["missing_reason"].startswith("grading_aborted")]
    assert aborted and all(r["outcome"] is None for r in aborted)


def test_stage_clock_cap_aborts_and_retains_every_slot(tmp_path, handoff):
    class CapExhausted(Exception):
        pass

    class Clock:
        def __init__(self):
            self.checks = 0

        def check(self, phase):
            self.checks += 1
            if self.checks > 3:
                raise CapExhausted("outer deadline reached")

        def remaining(self, phase):
            return 120.0

    summary = run_grade(handoff, tmp_path, clock=Clock())
    rows = [json.loads(x) for x in (tmp_path / "out/grade/grades.jsonl").read_text().splitlines()]
    assert summary["status"] == "aborted" and "CapExhausted" in summary["abort_reason"]
    assert len(rows) == 8 and {(r["root_id"], r["arm"], r["replicate"]) for r in rows} == set(slots())
    assert (tmp_path / "out/grade/failure_report.json").is_file()


def test_executor_must_be_injected(tmp_path, handoff):
    with pytest.raises(HandoffRefusal, match="private executor must be injected"):
        e13a_grade.grade(handoff["collect"], handoff["release"], tmp_path / "out-no-executor",
                         executor=None, real=False, stage=handoff["stage"], plan=handoff["plan"])
    assert not (tmp_path / "out-no-executor").exists()


def test_stub_executor_never_executes_and_reports_transport_only(tmp_path, handoff):
    executor = e13a_grade.StubPrivateExecutor(default_candidate=1)
    summary = run_grade(handoff, tmp_path, executor=executor)
    assert summary["transport_only"] is True
    assert "NOT grades of model behaviour" in summary["transport_only_note"]
    assert {c["kind"] for c in executor.calls} <= {"reference", "negative_control", "candidate"}
    assert summary["containment"]["status"] == "not_started_transport_only"
    assert summary["containment"]["starts_used"] == 0


# ---------------------------------------------------------------- analyzer handoff


def analyze(grades_path, stage_path, out_path):
    e13a_analyze.main(["--grades", str(grades_path), "--stage", str(stage_path), "--out", str(out_path)])
    return json.loads(out_path.read_text())


def test_analyzer_accepts_complete_stub_graded_output(tmp_path, handoff, capsys):
    run_grade(handoff, tmp_path)
    report = analyze(tmp_path / "out/grade/grades.jsonl", handoff["stage"], tmp_path / "analysis.json")
    capsys.readouterr()
    assert report["accounting"]["assigned_slots"] == report["accounting"]["graded_slots"] == 8
    finite = report["finite_checkpoint_contrast"]
    assert finite["contrast"] == 0.0 and finite["contrast_unavailable_reason"] is None
    assert report["accounting"]["usage_totals"]["executor_starts_known_sum"] == len(ROOTS)
    assert report["accounting"]["usage_totals"]["calls_known_sum"] == 8


def test_analyzer_reports_unavailable_primary_contrast_with_bounds(tmp_path, capsys):
    release = build_release(tmp_path)
    gap = slots()[0]
    h = build_collection(tmp_path, release, missing={gap: "receiver_unavailable"})
    run_grade(h, tmp_path)
    report = analyze(tmp_path / "out/grade/grades.jsonl", h["stage"], tmp_path / "analysis.json")
    capsys.readouterr()
    finite = report["finite_checkpoint_contrast"]
    assert finite["contrast"] is None
    assert finite["contrast_unavailable_reason"] == "one or more assigned grades are missing"
    bounds = finite["completion_bounds"]
    assert bounds["is_confidence_interval"] is False and bounds["lower"] <= bounds["upper"]
    assert bounds["lower"] > -1.0 and bounds["upper"] < 1.0, "bounds must be finite and informative"
    assert report["accounting"]["missing_slots"] == [
        {"root_id": gap[0], "arm": gap[1], "replicate": gap[2], "missing_reason": "receiver_unavailable"}]
    assert report["per_root"][gap[0]][gap[1]]["missing"] == 1
    assert report["per_root"][gap[0]][gap[1]]["mean"] is None


def test_cli_validate_only_writes_nothing(tmp_path, handoff, capsys):
    assert e13a_grade.main(["--collect", str(handoff["collect"]), "--stage", str(handoff["stage"]),
                            "--plan", str(handoff["plan"]), "--out", str(tmp_path / "cli-out"),
                            "--validate-only"]) == 0
    assert "validated" in capsys.readouterr().out
    assert not (tmp_path / "cli-out").exists()


def test_cli_refuses_transport_collection_real_execution(tmp_path, handoff):
    with pytest.raises(SystemExit, match="transport-only collection"):
        e13a_grade.main(["--collect", str(handoff["collect"]), "--release", str(handoff["release"]),
                         "--stage", str(handoff["stage"]), "--plan", str(handoff["plan"]),
                         "--out", str(tmp_path / "cli-real"), "--real"])


# ------------------------------------------- integration with the committed E13a release (read-only)

REAL_RELEASE = ROOT / "experiments/landmark/e13a_release"
REAL_STAGE = ROOT / "experiments/landmark/e13a_stage.json"
REAL_PLAN = ROOT / "results/e13a_request_plan_20260922.json"


@pytest.mark.skipif(not (REAL_RELEASE / "release_manifest.json").is_file() or not REAL_PLAN.is_file(),
                    reason="the committed e13a_release / request plan are not present in this tree")
def test_committed_release_binds_all_sixty_assigned_slots(tmp_path, capsys):
    """Read-only integration: the committed release, stage descriptor and request plan, stub executor only."""
    limits = e13a_grade.load_e13a_grading_limits((REAL_RELEASE / "release_manifest.json").read_bytes())
    assert (limits["artifact_starts"], limits["recheck_starts"], limits["containment_starts"],
            limits["max_private_starts"], limits["grading_seconds"]) == (60, 10, 9, 79, 300)
    h = build_collection(tmp_path, REAL_RELEASE, name="real", stage_path=REAL_STAGE, plan_path=REAL_PLAN)
    validated = e13a_grade.validate_handoff(h["collect"], h["stage"], h["plan"])
    assert len(validated["order"]) == 60 and len(validated["artifacts"]) == 60
    summary = e13a_grade.grade(h["collect"], REAL_RELEASE, tmp_path / "real-out",
                              executor=e13a_grade.StubPrivateExecutor(), real=False,
                              stage=h["stage"], plan=h["plan"])
    rows = [json.loads(x) for x in (tmp_path / "real-out/grade/grades.jsonl").read_text().splitlines()]
    assert summary["grade_rows"] == summary["assigned_slots"] == len(rows) == 60
    assert all(r["outcome"] is not None or r["missing_reason"] for r in rows)
    assert summary["start_accounting"]["used"]["candidate"] <= 60
    assert summary["start_accounting"]["used"]["recheck"] <= 10
    assert summary["start_accounting"]["used"]["total"] <= 79
    report = analyze(tmp_path / "real-out/grade/grades.jsonl", REAL_STAGE, tmp_path / "real-analysis.json")
    capsys.readouterr()
    assert report["accounting"]["assigned_slots"] == 60
    assert sorted(report["plan_validated_against"]["root_order"]) == sorted(json.loads(
        REAL_STAGE.read_text())["roots"])


REAL_CLOCK = ROOT / "scripts/e13a_stage_clock.py"


@pytest.mark.skipif(not REAL_CLOCK.is_file(), reason="the shared StageClock is not present in this tree")
def test_shared_stage_clock_composes(tmp_path, handoff):
    """The driver reads the shared clock's private_grading phase: time left grades, exhausted aborts."""
    clock_module = _load("e13a_stage_clock", "scripts/e13a_stage_clock.py")
    assert clock_module.PHASE_CAPS[e13a_grade.PRIVATE_GRADING_PHASE] == 300
    live = clock_module.StageClock.from_start("2026-09-23T00:00:00Z")
    live.now_utc = lambda: live.start_utc  # anchored: the full private-grading cap is available
    summary = run_grade(handoff, tmp_path, clock=live, out="clock-live")
    assert summary["status"] == "complete" and summary["grade_rows"] == 8

    spent = clock_module.StageClock.from_start("2026-09-23T00:00:00Z")
    spent.now_utc = lambda: spent.start_utc
    spent.charge(e13a_grade.PRIVATE_GRADING_PHASE, 300)
    with pytest.raises(clock_module.CapExhausted):
        spent.check(e13a_grade.PRIVATE_GRADING_PHASE)
    summary = run_grade(handoff, tmp_path, clock=spent, out="clock-spent")
    rows = [json.loads(x) for x in (tmp_path / "clock-spent/grade/grades.jsonl").read_text().splitlines()]
    assert summary["status"] == "aborted" and "CapExhausted" in summary["abort_reason"]
    assert len(rows) == 8 and (tmp_path / "clock-spent/grade/failure_report.json").is_file()


@pytest.mark.parametrize("event", ["execution_start", "execution_result"])
def test_durable_write_failure_retains_assignments_without_retry(tmp_path, handoff, monkeypatch, event):
    original = e13a_grade.study_adapter._DurableLedger.write
    fired = {"value": False}
    def fail_once(self, record):
        if record["event"] == event and not fired["value"]:
            fired["value"] = True
            raise OSError("synthetic durable write fault")
        return original(self, record)
    monkeypatch.setattr(e13a_grade.study_adapter._DurableLedger, "write", fail_once)
    executor = e13a_grade.StubPrivateExecutor()
    summary = run_grade(handoff, tmp_path, executor=executor)
    rows = [json.loads(x) for x in (tmp_path / "out/grade/grades.jsonl").read_text().splitlines()]
    assert summary["status"] == "aborted" and len(rows) == len(slots())
    assert all(r["outcome"] is None and r["missing_reason"] for r in rows)
    assert len(executor.calls) == (0 if event == "execution_start" else 1)
    assert summary["start_accounting"]["reserved_execution_attempts"]["total"] == len(executor.calls)
    assert summary["start_accounting"]["unknown_execution_starts"]["total"] == len(executor.calls)
    assert (tmp_path / "out/grade/failure_report.json").is_file()
