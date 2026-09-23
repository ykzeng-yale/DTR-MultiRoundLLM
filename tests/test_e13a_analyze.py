"""Static JSON fixtures only; no receiver, grader, sandbox or candidate execution."""
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("e13a_analyze", ROOT / "scripts/e13a_analyze.py")
e13a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e13a)

ROOTS = ["mbpp/842", "mbpp/288"]
R1_REPS = [2, 3, 4]
FRESH_REPS = [0, 1, 2]


def descriptor(roots=ROOTS, r1_reps=R1_REPS, fresh_reps=FRESH_REPS):
    return {
        "stage_id": "e13a-test",
        "status": "PROPOSED, NOT RELEASED; no receiver call made",
        "contrast": {"treatment": "R1", "reference": "FRESH"},
        "roots": [{"root_id": r,
                   "requests": [{"arm": "R1", "replicate": i} for i in r1_reps]
                              + [{"arm": "FRESH", "replicate": i} for i in fresh_reps]}
                  for r in roots],
    }


def grade(root, arm, replicate, outcome, missing_reason=None, **extra):
    row = {"root_id": root, "arm": arm, "replicate": replicate, "outcome": outcome,
           "missing_reason": missing_reason}
    row.update(extra)
    return row


def full_grades():
    """R1 2/3 and 3/3; FRESH 1/3 and 0/3 -> differences +1/3 and +1.0."""
    outcomes = {("mbpp/842", "R1"): [1, 1, 0], ("mbpp/842", "FRESH"): [1, 0, 0],
                ("mbpp/288", "R1"): [1, 1, 1], ("mbpp/288", "FRESH"): [0, 0, 0]}
    rows = []
    for root in ROOTS:
        for arm, reps in (("R1", R1_REPS), ("FRESH", FRESH_REPS)):
            for replicate, outcome in zip(reps, outcomes[(root, arm)]):
                rows.append(grade(root, arm, replicate, outcome, calls=1, prompt_tokens=10,
                                  completion_tokens=20, executor_starts=1, executor_seconds=0.5))
    return rows


def write(tmp_path, rows, spec=None, name="grades.jsonl"):
    grades = tmp_path / name
    grades.write_text("".join(json.dumps(r) + "\n" for r in rows))
    stage = tmp_path / "stage.json"
    stage.write_text(json.dumps(spec if spec is not None else descriptor()))
    return grades, stage


def report_for(tmp_path, rows, spec=None):
    grades, stage = write(tmp_path, rows, spec)
    spec = json.loads(stage.read_text())
    plan = e13a.plan_from_descriptor(spec)
    return e13a.build_report(grades, stage, spec, plan, rows)


def test_arithmetic_and_finite_checkpoint_contrast(tmp_path):
    report = report_for(tmp_path, full_grades())
    cell = report["per_root"]["mbpp/842"]["R1"]
    assert (cell["assigned"], cell["graded"], cell["passes"], cell["failures"], cell["missing"]) == (3, 3, 2, 1, 0)
    assert cell["mean"] == pytest.approx(2 / 3)
    diffs = report["finite_checkpoint_contrast"]["per_root_differences"]
    assert diffs["mbpp/842"] == pytest.approx(2 / 3 - 1 / 3)
    assert diffs["mbpp/288"] == pytest.approx(1.0)
    assert report["finite_checkpoint_contrast"]["contrast"] == pytest.approx((1 / 3 + 1.0) / 2)
    bounds = report["finite_checkpoint_contrast"]["completion_bounds"]
    assert bounds["lower"] == bounds["upper"] == report["finite_checkpoint_contrast"]["contrast"]
    assert report["available_case_secondary"]["contrast"] == report["finite_checkpoint_contrast"]["contrast"]
    assert report["finite_checkpoint_contrast"]["n_checkpoints"] == 2
    by_root = {c["root_id"]: c for c in report["per_root_contrasts"]}
    assert by_root["mbpp/842"]["R1_passes"] == 2 and by_root["mbpp/842"]["FRESH_passes"] == 1
    assert len(report["per_root_contrasts"]) == len(ROOTS)
    assert report["accounting"]["assigned_slots"] == 12 and report["accounting"]["graded_slots"] == 12
    usage = report["accounting"]["usage_totals"]
    assert usage["completion_tokens_known_sum"] == 240 and usage["completion_tokens_unknown_count"] == 0
    assert usage["executor_seconds_known_sum"] == pytest.approx(6.0)
    assert report["plan_validated_against"]["assigned_replicates"]["mbpp/842"] == {"FRESH": [0, 1, 2], "R1": [2, 3, 4]}
    assert report["plan_validated_against"]["arms"] == ["FRESH", "R1"]


def test_missing_outcomes_are_preserved_and_not_zero_filled(tmp_path):
    rows = [r for r in full_grades() if not (r["root_id"] == "mbpp/842" and r["arm"] == "R1" and r["replicate"] == 4)]
    rows.append(grade("mbpp/842", "R1", 4, None, "grading_unavailable", calls=1))
    report = report_for(tmp_path, rows)
    cell = report["per_root"]["mbpp/842"]["R1"]
    assert (cell["assigned"], cell["graded"], cell["passes"], cell["failures"], cell["missing"]) == (3, 2, 2, 0, 1)
    assert cell["missing_reasons"] == {"grading_unavailable": 1} and cell["missing_replicates"] == [4]
    assert cell["mean"] is None, "missing assigned outcomes suppress the primary cell point estimate"
    assert cell["available_case_mean"] == pytest.approx(1.0)
    assert cell["completion_bounds"]["lower"] == pytest.approx(2 / 3)
    assert cell["completion_bounds"]["upper"] == 1
    assert report["finite_checkpoint_contrast"]["contrast"] is None
    assert report["available_case_secondary"]["contrast"] == pytest.approx((2 / 3 + 1) / 2)
    assert report["accounting"]["graded_slots"] == 11
    assert report["accounting"]["missing_slots"] == [
        {"root_id": "mbpp/842", "arm": "R1", "replicate": 4, "missing_reason": "grading_unavailable"}]
    usage = report["accounting"]["usage_totals"]
    assert usage["completion_tokens_known_sum"] == 220 and usage["completion_tokens_unknown_count"] == 1


def test_all_missing_cell_leaves_mean_and_contrast_null(tmp_path):
    rows = [r for r in full_grades() if not (r["root_id"] == "mbpp/288" and r["arm"] == "FRESH")]
    rows += [grade("mbpp/288", "FRESH", i, None, "receiver_unavailable") for i in FRESH_REPS]
    report = report_for(tmp_path, rows)
    assert report["per_root"]["mbpp/288"]["FRESH"]["mean"] is None
    assert report["finite_checkpoint_contrast"]["per_root_differences"]["mbpp/288"] is None
    assert report["finite_checkpoint_contrast"]["contrast"] is None
    assert report["finite_checkpoint_contrast"]["contrast_unavailable_reason"]
    assert report["available_case_secondary"]["contrast"] is None
    cell_bounds = report["per_root"]["mbpp/288"]["FRESH"]["completion_bounds"]
    assert (cell_bounds["lower"], cell_bounds["upper"]) == (0, 1)
    root_bounds = report["per_root_contrasts"][1]["completion_bounds"]
    assert (root_bounds["lower"], root_bounds["upper"]) == (0, 1)


def test_directional_counterexample_has_bounds_crossing_zero(tmp_path):
    """One observed treatment success must not assert a positive all-assigned contrast with five missing."""
    root = "synthetic/checkpoint"
    spec = descriptor(roots=[root], r1_reps=list(range(6)), fresh_reps=list(range(6)))
    rows = [grade(root, "R1", i, 1 if i == 0 else None,
                  None if i == 0 else "grading_unavailable") for i in range(6)]
    rows += [grade(root, "FRESH", i, int(i < 3)) for i in range(6)]
    report = report_for(tmp_path, rows, spec)
    finite = report["finite_checkpoint_contrast"]
    assert finite["contrast"] is None
    assert report["available_case_secondary"]["contrast"] == 0.5
    assert finite["completion_bounds"]["lower"] == pytest.approx(-1 / 3)
    assert finite["completion_bounds"]["upper"] == 0.5
    assert finite["completion_bounds"]["kind"] == "finite_completion_bounds"
    assert finite["completion_bounds"]["is_confidence_interval"] is False
    # Both extrema are attainable completions of the five missing binary scores, not sampling intervals.
    for fill, bound in ((0, "lower"), (1, "upper")):
        completed = [{**r, "outcome": fill, "missing_reason": None} if r["outcome"] is None else r for r in rows]
        completed_report = e13a.analyze(completed, e13a.plan_from_descriptor(spec))
        assert completed_report["finite_checkpoint_contrast"]["contrast"] == pytest.approx(
            finite["completion_bounds"][bound])


def test_all_missing_five_checkpoint_bounds_are_minus_one_to_one(tmp_path):
    roots = [f"synthetic/{i}" for i in range(5)]
    spec = descriptor(roots=roots, r1_reps=list(range(6)), fresh_reps=list(range(6)))
    rows = [grade(root, arm, i, None, "budget_unattempted")
            for root in roots for arm in ("R1", "FRESH") for i in range(6)]
    report = report_for(tmp_path, rows, spec)
    assert report["accounting"]["assigned_slots"] == 60
    assert len(report["accounting"]["missing_slots"]) == 60
    assert report["finite_checkpoint_contrast"]["contrast"] is None
    assert report["available_case_secondary"]["contrast"] is None
    for cell in [cell for arms in report["per_root"].values() for cell in arms.values()]:
        assert cell["mean"] is None and cell["available_case_mean"] is None
        assert (cell["completion_bounds"]["lower"], cell["completion_bounds"]["upper"]) == (0, 1)
    bounds = report["finite_checkpoint_contrast"]["completion_bounds"]
    assert (bounds["lower"], bounds["upper"]) == (-1, 1)
    assert bounds["is_confidence_interval"] is False


def test_five_checkpoint_bounds_weight_roots_equally_not_available_counts(tmp_path):
    roots = [f"synthetic/{i}" for i in range(5)]
    spec = descriptor(roots=roots, r1_reps=list(range(6)), fresh_reps=list(range(6)))
    # First root has one observed treatment pass, five missing and reference mean 1/2.
    # The other four root contrasts are complete zero, so bounds average over all five roots.
    rows = []
    for root in roots:
        for arm in ("R1", "FRESH"):
            for i in range(6):
                missing = root == roots[0] and arm == "R1" and i > 0
                outcome = None if missing else (int(i < 3) if root == roots[0] else 0)
                rows.append(grade(root, arm, i, outcome, "receiver_unavailable" if missing else None))
    report = report_for(tmp_path, rows, spec)
    finite = report["finite_checkpoint_contrast"]
    assert finite["contrast"] is None
    assert finite["n_checkpoints"] == 5
    assert finite["completion_bounds"]["lower"] == pytest.approx(-1 / 15)
    assert finite["completion_bounds"]["upper"] == pytest.approx(0.1)
    assert report["available_case_secondary"]["contrast"] == pytest.approx(0.1)


def test_refuses_unexpected_arm_root_replicate_and_duplicate(tmp_path):
    for bad in (grade("mbpp/842", "S1", 2, 1), grade("mbpp/999", "R1", 2, 1), grade("mbpp/842", "R1", 9, 1)):
        with pytest.raises(e13a.RefusalError, match="unexpected"):
            report_for(tmp_path, full_grades() + [bad])
    with pytest.raises(e13a.RefusalError, match="duplicate"):
        report_for(tmp_path, full_grades() + [grade("mbpp/842", "R1", 2, 0)])


def test_refuses_silently_absent_slot_and_outcome_without_reason(tmp_path):
    short = [r for r in full_grades() if not (r["root_id"] == "mbpp/288" and r["arm"] == "FRESH" and r["replicate"] == 1)]
    with pytest.raises(e13a.RefusalError, match="absent from the grades file"):
        report_for(tmp_path, short)
    with pytest.raises(e13a.RefusalError, match="missing_reason"):
        report_for(tmp_path, short + [grade("mbpp/288", "FRESH", 1, None)])
    with pytest.raises(e13a.RefusalError, match="expected 0, 1 or null"):
        report_for(tmp_path, short + [grade("mbpp/288", "FRESH", 1, 0.5)])


def test_refuses_unknown_contrast_arm_and_missing_contrast(tmp_path):
    spec = descriptor()
    spec.pop("contrast")
    with pytest.raises(e13a.RefusalError, match="contrast arms unknown"):
        e13a.plan_from_descriptor(spec)
    with pytest.raises(e13a.RefusalError, match="not assigned"):
        e13a.plan_from_descriptor(spec, treatment_arm="R2", reference_arm="FRESH")
    plan = e13a.plan_from_descriptor(spec, treatment_arm="R1", reference_arm="FRESH")
    assert plan["treatment_arm"] == "R1" and plan["arms"] == ["FRESH", "R1"]


def test_no_e12_arm_or_count_assumptions(tmp_path):
    """Arms, replicate indices and roots come from the descriptor, not from E12's 5-arm 2-replicate layout."""
    spec = descriptor(roots=["mbpp/652"], r1_reps=[7, 8], fresh_reps=[4, 5])
    rows = [grade("mbpp/652", "R1", i, 1) for i in (7, 8)] + [grade("mbpp/652", "FRESH", i, 0) for i in (4, 5)]
    report = report_for(tmp_path, rows, spec)
    assert report["finite_checkpoint_contrast"]["n_checkpoints"] == 1
    assert report["finite_checkpoint_contrast"]["contrast"] == pytest.approx(1.0)
    assert report["accounting"]["assigned_by_arm"] == {"FRESH": 2, "R1": 2}
    source = (ROOT / "scripts/e13a_analyze.py").read_text()
    for token in ("STOP", "N0", "S0", "N1", "S1", "11N", "2N"):
        assert token not in source


def test_statements_and_evidence_class_present(tmp_path):
    report = report_for(tmp_path, full_grades())
    assert "tie" in report["statements"]["tie_inconclusive"].lower()
    assert "inconclusive" in report["statements"]["tie_inconclusive"].lower()
    assert "does not identify a resampling mechanism" in report["statements"]["tie_inconclusive"].lower()
    assert "no hypothesis test" in report["statements"]["no_significance"].lower()
    assert "p-value" in report["statements"]["no_significance"].lower()
    for flag in ("no_population_interval", "no_test", "no_p_value"):
        assert report["finite_checkpoint_contrast"][flag] is True
    assert "finite-checkpoint descriptive" in report["finite_checkpoint_contrast"]["quantity_type"]
    assert "not a test of the selected gated rule" in report["evidence_class"].lower()
    assert "not a test of a diagnostic-only effect" in report["evidence_class"].lower()
    assert "post-hoc-motivated development follow-up" in report["evidence_class"].lower()
    finite_label = report["finite_checkpoint_contrast"]["label"].lower()
    assert "fixed development-selected checkpoints" in finite_label
    assert "no p-value" in report["metric_definitions"]["finite_checkpoint_contrast"].lower()
    assert "no futility claim" in report["metric_definitions"]["finite_checkpoint_contrast"].lower()
    assert report["metric_definitions"]["mean"].startswith("passes / assigned")
    assert report["metric_definitions"]["available_case_mean"].startswith("passes / graded")
    assert "NOT confidence intervals" in report["metric_definitions"]["completion_bounds"]
    assert "never zero-filled" in report["metric_definitions"]["missing"]


def test_cli_writes_report_and_refuses_overwrite(tmp_path):
    grades, stage = write(tmp_path, full_grades())
    out = tmp_path / "sub/e13a_report.json"
    e13a.main(["--grades", str(grades), "--stage", str(stage), "--out", str(out)])
    report = json.loads(out.read_text())
    assert report["analysis_version"] == "e13a-finite-checkpoint-contrast-v2"
    assert report["inputs"]["grades"]["sha256"] and report["inputs"]["stage_descriptor"]["sha256"]
    assert report["inputs"]["grades"]["records"] == 12
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        e13a.main(["--grades", str(grades), "--stage", str(stage), "--out", str(out)])


def test_cli_refusal_exits_without_writing(tmp_path):
    grades, stage = write(tmp_path, full_grades() + [grade("mbpp/842", "S1", 2, 1)])
    out = tmp_path / "report.json"
    with pytest.raises(SystemExit, match="Refusing to analyze"):
        e13a.main(["--grades", str(grades), "--stage", str(stage), "--out", str(out)])
    assert not out.exists()


def test_arm_map_descriptor_shape_with_bare_root_ids(tmp_path):
    """The stage-descriptor shape {"arms": {arm: [reps]}, "roots": [id, ...]} is accepted and root-balanced."""
    spec = {"stage": "E13a", "arms": {"R1": R1_REPS, "FRESH": FRESH_REPS}, "roots": ROOTS,
            "contrast": {"treatment": "R1", "reference": "FRESH"},
            "not_a_test_of": ["the selected gated rule"], "interpretation_rules": ["A tie is inconclusive."]}
    report = report_for(tmp_path, full_grades(), spec)
    assert report["stage_id"] == "E13a"
    assert report["plan_validated_against"]["assigned_replicates"]["mbpp/288"] == {"FRESH": [0, 1, 2], "R1": [2, 3, 4]}
    assert report["finite_checkpoint_contrast"]["contrast"] == pytest.approx((1 / 3 + 1.0) / 2)
    assert report["stage_not_a_test_of_as_recorded"] == ["the selected gated rule"]
    assert report["stage_interpretation_rules_as_recorded"] == ["A tie is inconclusive."]
    bare = {"roots": ROOTS}
    with pytest.raises(e13a.RefusalError, match="no non-empty 'arms' map"):
        e13a.plan_from_descriptor(bare, treatment_arm="R1", reference_arm="FRESH")


def test_real_e13a_stage_descriptor_is_accepted():
    stage_path = ROOT / "experiments/landmark/e13a_stage.json"
    if not stage_path.exists():
        pytest.skip("stage descriptor not present")
    spec = json.loads(stage_path.read_text())
    plan = e13a.plan_from_descriptor(spec, treatment_arm="R1", reference_arm="FRESH")
    assert len(plan["root_order"]) == 5 and plan["arms"] == ["FRESH", "R1"]
    assert sum(len(reps) for r in plan["root_order"] for reps in plan["roots"][r].values()) == 60


def test_real_e13a_request_plan_is_an_acceptable_stage_descriptor():
    plan_path = ROOT / "results/e13a_request_plan_20260922.json"
    if not plan_path.exists():
        pytest.skip("request plan not present")
    plan = e13a.plan_from_descriptor(json.loads(plan_path.read_text()),
                                     treatment_arm="R1", reference_arm="FRESH")
    assert len(plan["root_order"]) == 5 and plan["arms"] == ["FRESH", "R1"]
    assert all(len(plan["roots"][r]["R1"]) == 6 and len(plan["roots"][r]["FRESH"]) == 6 for r in plan["root_order"])
