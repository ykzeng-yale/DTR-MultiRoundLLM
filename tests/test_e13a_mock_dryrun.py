"""E13a mock/transport-only dry run (scripts/e13a_mock_dryrun.py).

Mock receiver and STUB private executor only: no model, no llama-server, no sandbox, no candidate, reference
solution or benchmark program is executed, and nothing is written inside results/.
"""
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from experiments.landmark import collect  # noqa: E402
from experiments.landmark import collect_diagnostic as cd  # noqa: E402
import e13a_mock_dryrun as md  # noqa: E402

FIVE = ["mbpp/288", "mbpp/652", "mbpp/842", "mbpp/863", "mbpp/966"]
RUN = md.RUN


def _jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


pytestmark = pytest.mark.skipif(not (RUN / "B/diagnostics.json").exists(), reason="E12 run directory absent")


@pytest.fixture(scope="module")
def plan():
    return md.build_requests()


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("e13a") / "dryrun"
    return out, md.dryrun(out)


# ------------------------------------------------------------------ 1. gating and message bytes
def test_checkpoints_come_from_public_diagnostics_only(plan):
    assert plan["checkpoints"] == FIVE
    diagnostics = md._strict((RUN / "B/diagnostics.json").read_bytes())
    assert md.public_fail_checkpoints(diagnostics) == FIVE
    assert plan["private_inputs_used_for_gating"] == []
    assert "diagnostics.json" in plan["gating_source"] or "case statuses" in plan["gating_source"]


def test_public_fail_gate_is_analyze_diagnostic_public_status():
    """The canonical gate: any_fail only. An unknown public status (timeout/unavailable/output_limit, or no
    case at all) is NOT a checkpoint, so it can never be silently gated in."""
    from experiments.landmark import analyze_diagnostic as ad
    schema = sorted(ad.SCHEMAS)[-1]

    def diag(root_id, *statuses):
        return {"schema_version": schema, "root_id": root_id,
                "cases": [{"status": s} for s in statuses]}

    diagnostics = {"r/1": diag("r/1", "pass", "pass"), "r/2": diag("r/2", "pass", "wrong_value"),
                   "r/3": diag("r/3", "timeout"), "r/4": diag("r/4")}
    assert md.public_fail_checkpoints(diagnostics) == ["r/2"]
    assert [ad.public_status(diagnostics[r], r) for r in sorted(diagnostics)] == \
        ["all_pass", "any_fail", "unknown", "unknown"]
    with pytest.raises(ValueError, match="status"):
        md.public_fail_checkpoints({"r/5": diag("r/5", "not_a_status")})


def test_rendered_messages_are_byte_identical_to_e12_requests(plan):
    """R1 == both E12 R1 requests, FRESH == E12's initial request, previous answer removed from R1."""
    calls = _jsonl(RUN / "C/calls.jsonl")
    a_rows = {r["root_id"]: r for r in _jsonl(RUN / "A/roots.jsonl")}
    assert plan["byte_checks"] and all(all(v is True for k, v in c.items() if k != "root_id")
                                      for c in plan["byte_checks"])
    for root in plan["roots"]:
        e12_r1 = [c["request"]["messages"] for c in calls
                  if c["root_id"] == root["root_id"] and c["arm"] == "R1"]
        assert len(e12_r1) == 2 and all(m == root["messages"]["R1"] for m in e12_r1)
        assert root["messages"]["FRESH"] == a_rows[root["root_id"]]["initial"]["request"]["messages"]
        assert collect.digest(root["messages"]["R1"]) == root["r1_messages_sha256"]
        assert collect.digest(root["messages"]["FRESH"]) == root["base_messages_sha256"]
        assert [m["role"] for m in root["messages"]["R1"]] == ["system", "user", "user", "user"]
        for request in root["requests"]:
            assert request["messages_sha256"] == collect.digest(root["messages"][request["arm"]])


def test_executable_inputs_carry_no_private_grade(plan, run):
    """No private grade value reaches the dispatched plan or the collection manifest (only the "not an input"
    declaration in the stage bindings mentions them at all)."""
    executable = json.dumps({"roots": plan["roots"], "checks": plan["byte_checks"],
                             "inputs": plan["inputs"]}, sort_keys=True)
    assert "grade" not in executable and "outcome" not in executable
    out, _ = run
    manifest = (out / "collect/manifest.json").read_text()
    assert "private_grade" not in manifest and "e12_initial_private_grade" not in manifest
    assert plan["stage"]["gating"]["private_grades_are_an_input"] is False


# ------------------------------------------------------------------ 2. seeds and scheduling
def test_new_seeds_never_collide_with_e12_seeds(plan):
    config, tasks = plan["config"], plan["tasks"]
    e12 = {p["root_id"]: set(p["seeds"].values()) for p in cd.assignments(config, tasks)}
    for root in plan["roots"]:
        new = [q["seed"] for q in root["requests"]]
        assert len(new) == 12 and len(set(new)) == 12
        assert not set(new) & e12[root["root_id"]]
        # The check has teeth: an E12 replicate index reuses an E12 seed and must be refused.
        assert collect.seeded(config, root["root_id"], "R1:0") in e12[root["root_id"]]
    assert {(q["arm"], q["replicate"]) for r in plan["roots"] for q in r["requests"]} == \
        {("R1", r) for r in range(2, 8)} | {("FRESH", r) for r in range(6)}


def test_schedule_is_root_balanced_with_inclusion_probability_one(plan):
    order = md.schedule(plan)
    assert len(order) == 60 and all(o["branch_inclusion_probability"] == 1.0 for o in order)
    assert all(o["order_role"] == "scheduling_not_assignment" for o in order)
    assert len({(o["root_id"], o["arm"], o["replicate"]) for o in order}) == 60
    ids = sorted(r["root_id"] for r in plan["roots"])
    for start in range(0, 60, 5):
        assert sorted(o["root_id"] for o in order[start:start + 5]) == ids
    assert md.schedule(plan) == order  # deterministic


# ------------------------------------------------------------------ 3. mock collection
def test_mock_collection_manifest_completion_and_checksums(run):
    out, result = run
    col = out / "collect"
    manifest = json.loads((col / "manifest.json").read_text())
    completion = json.loads((col / "completion.json").read_text())
    assert result["attempts"] == 60 and completion["attempted_calls"] == 60
    assert len(_jsonl(col / "calls.jsonl")) == 60 and len(_jsonl(col / "roots.jsonl")) == 5
    assert completion["outputs_collected"] + completion["outputs_missing"] == 60
    assert completion["checksums"] and all(
        hashlib.sha256((col / rel).read_bytes()).hexdigest() == sha for rel, sha in completion["checksums"].items())
    assert set(completion["checksums"]) >= {"manifest.json", "calls.jsonl", "roots.jsonl"}
    assert manifest["seed_plan"] and all(len(v) == 12 for v in manifest["seed_plan"].values())
    for row in _jsonl(col / "roots.jsonl"):
        assert set(row["arms"]) == set(md.ARMS)
        assert all(len(row["arms"][a]) == 6 for a in md.ARMS)


def test_mock_run_is_labelled_mock_transport_only(run):
    out, result = run
    manifest = json.loads((out / "collect/manifest.json").read_text())
    completion = json.loads((out / "collect/completion.json").read_text())
    summary = json.loads((out / "grade/summary.json").read_text())
    report = json.loads((out / "grade/mock_report.json").read_text())
    for doc in (manifest, completion, summary, report):
        assert doc["mock_only"] is True and doc["banner"] == md.MOCK_BANNER
    assert manifest["evidence_type"] == "mock_transport_only" and manifest["real_receiver"] is False
    assert manifest["receiver_calls_made"] == 0 and manifest["candidate_executions"] == 0
    assert completion["receiver_verification"]["efficacy_interpretable"] is False
    assert summary["real_candidate_executions"] == 0 and summary["real_sandbox_executions"] == 0
    assert summary["model_calls"] == 0 and result["evidence_class"] == md.EVIDENCE
    for name in ("MOCK_ONLY", "collect/MOCK_ONLY", "grade/MOCK_ONLY"):
        assert md.MOCK_BANNER in (out / name).read_text()


# ------------------------------------------------------------------ 4. mock grading bookkeeping
def test_grading_covers_sixty_artifacts_and_ten_rechecks(run):
    out, result = run
    grades = _jsonl(out / "grade/grades.jsonl")
    summary = result["grading"]
    assert len(grades) == 60 and summary["grade_rows"] == 60
    assert {(g["root_id"], g["arm"], g["replicate"]) for g in grades} == \
        {(r, a, i) for r in FIVE for a, reps in (("R1", range(2, 8)), ("FRESH", range(6))) for i in reps}
    assert summary["planned_max_artifacts"] == 60 and summary["planned_max_rechecks"] == 10
    executions = json.loads((out / "grade/private_execution_records.json").read_text())
    rechecks = [e for e in executions if e["kind"] in ("reference", "negative_control")]
    assert len(rechecks) == 10 and summary["recheck_starts_used"] == 10
    assert all(e["mock_executor"] for e in executions)
    ledger = _jsonl(out / "grade/grading_attempts.jsonl")
    assert ledger[0]["event"] == "reserved" and ledger[-1]["event"] == "complete"
    starts = [x for x in ledger if x["event"] == "start"]
    assert len(starts) == summary["stub_executor_starts"] and all("program_sha256" in x for x in starts)


def test_unavailable_and_format_failures_are_preserved_not_zero_filled(run):
    out, _ = run
    grades = _jsonl(out / "grade/grades.jsonl")
    unavailable = [g for g in grades if g["outcome"] is None]
    assert len(unavailable) >= 2
    assert {g["reason"] for g in unavailable} >= {"mock_incomplete_or_empty_response", "grader_environment_failure"}
    assert all(g["missing_reason"] for g in unavailable)
    extraction = [g for g in grades if g["reason"] == "unparseable_output"]
    assert len(extraction) >= 1 and all(g["outcome"] == 0 for g in extraction)
    assert all(g["reason"] for g in grades)            # no outcome is recorded without a reason
    assert all(g["outcome"] in (0, 1, None) for g in grades)
    assert not any(g["outcome"] == 0 and g["missing_reason"] for g in grades)  # unknown never becomes a zero
    summary = json.loads((out / "grade/summary.json").read_text())
    assert summary["unavailable_rows"] == len(unavailable)
    assert summary["ones"] + summary["zeros"] + summary["unavailable_rows"] == 60


def test_stage_bindings_supply_the_limits(plan, tmp_path):
    stage, limits, sha = md.load_stage(specs=plan["specs"])
    assert limits["artifact_starts"] == 60 and limits["recheck_starts"] == 10 and limits["source"] == "grading_limits"
    assert stage["gating"]["private_grades_are_an_input"] is False and len(stage["roots"]) == 5
    assert sorted(stage["roots"]) == FIVE and stage["arms"]["R1"] == [2, 3, 4, 5, 6, 7]
    bad = tmp_path / "stage.json"
    bad.write_text(json.dumps({k: v for k, v in stage.items() if k != "grading_limits"}))
    with pytest.raises(ValueError, match="grading_limits"):
        md.load_stage(bad, plan["specs"])


# ------------------------------------------------------------------ 5. analysis hand-off and containment
def test_report_is_written_and_states_its_interpretation_limits(run):
    out, result = run
    report = json.loads((out / "grade/mock_report.json").read_text())
    assert report["per_arm"]["R1"]["n"] == 30 and report["per_arm"]["FRESH"]["n"] == 30
    assert set(report["per_root"]) == set(FIVE)
    assert any("tie" in line.lower() for line in report["interpretation"])
    assert any("pooling" in line.lower() for line in report["interpretation"])
    assert report["grades_path"].endswith("grades.jsonl") and Path(report["grades_path"]).exists()
    assert "analysis_dependency" in report  # None once Deliverable A's analyzer accepts the call
    assert result["report"]["evidence_class"] == md.EVIDENCE


def test_refuses_to_write_inside_results_or_over_an_existing_directory(tmp_path):
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        md.dryrun(tmp_path)
    with pytest.raises(ValueError, match="results/"):
        md.mock_collect({"config": {}, "roots": [], "stage_sha256": "", "inputs": {}, "byte_checks": [],
                         "checkpoints": [], "gating_source": "", "private_inputs_used_for_gating": [],
                         "package_config_sha256": ""}, [], md.RESULTS_DIR / "e13a_mock_should_not_exist")
    assert not (md.RESULTS_DIR / "e13a_mock_should_not_exist").exists()


def test_run_leaves_e12_inputs_untouched(plan, run):
    sums = md._strict((RUN / "ARTIFACT_SHA256SUMS.json").read_bytes())
    sums = sums.get("files", sums)
    for rel, sha in plan["inputs"].items():
        assert hashlib.sha256((RUN / rel).read_bytes()).hexdigest() == sha == sums[rel]
    out, _ = run
    assert md.RESULTS_DIR not in out.parents
