"""Lead-corrected static description of E13a outputs (v2).

Reads immutable records only: nothing is executed, regraded or modified, and the v1 script/JSON are
untouched. These tests pin the corrections the lead's judgment made binding.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e13a_static_description_v2 as sd2  # noqa: E402


@pytest.fixture(scope="module")
def out():
    return sd2.build()


def test_version_label_and_changelog_name_the_three_v1_overreads(out):
    assert out["analysis_version"] == "e13a-static-description-v2-lead-corrected"
    text = json.dumps(out["changelog_against_v1"]).lower()
    assert "12 python-ast failure" in text
    assert "observed saturation" in text and "structural" in text
    assert "discriminating semantic instrument" in text
    assert len(out["changelog_against_v1"]) == 3


def test_extraction_and_ast_failures_are_separated_one_plus_twelve(out):
    r1 = out["output_validity_by_arm"]["R1"]
    fresh = out["output_validity_by_arm"]["FRESH"]
    assert r1["extraction_rejections"] == 1
    assert r1["ast_failures"] == 12
    assert fresh["extraction_rejections"] == 0
    assert fresh["ast_failures"] == 0
    assert "1 extraction rejection(s) plus 12 Python-AST failure(s)" in out["output_validity_split_statement"]
    # all six R1 outputs at 966 fail to produce parseable Python, and the saved failures echo the report
    cell = out["per_checkpoint"]["mbpp/966"]["R1"]
    assert cell["extraction_rejections"] + cell["ast_failures"] == 6
    assert cell["extractable_and_parseable"] == 0
    assert cell["failures_echoing_diagnostic_report"] >= 1
    assert r1["failures_echoing_diagnostic_report"] >= 1


def test_all_assigned_partition_rows_and_sums(out):
    part = out["all_assigned_partition"]
    rows = {r["joint_recorded_outcome"]: r for r in part["rows"]}
    assert rows["primary-score success"]["R1"] == 9
    assert rows["extraction or AST failure"]["R1"] == 13
    assert rows["extractable, AST-parseable primary-score failure"]["R1"] == 8
    assert rows["primary-score success"]["FRESH"] == 12
    assert rows["extraction or AST failure"]["FRESH"] == 0
    assert rows["extractable, AST-parseable primary-score failure"]["FRESH"] == 18
    for arm in ("R1", "FRESH"):
        assert sum(r[arm] for r in part["rows"]) == 30
    assert part["mutually_exclusive_and_exhaustive"] is True


def test_partition_claims_no_mediation_and_no_format_share(out):
    disclaimer = out["all_assigned_partition"]["disclaimer"].lower()
    assert "identifies no mediation" in disclaimer
    assert "-0.100" in disclaimer and "quantifies no share" in disclaimer
    assert "recovers no latent semantic success" in disclaimer
    assert any("identifies no mediation" in lim.lower() for lim in out["limits"])


def test_saturation_is_observed_with_no_structural_claim(out):
    sat = out["observed_saturation"]
    assert sat["cells"]["mbpp/863:FRESH"] == "all_observed_scores_1"
    assert sat["cells"]["mbpp/652:R1"] == "all_observed_scores_0"
    assert sat["cells"]["mbpp/652:FRESH"] == "all_observed_scores_0"
    statement = sat["statement"]
    assert "OBSERVED saturation" in statement
    assert "No structural floor or ceiling is claimed" in statement
    assert "mbpp/652" in statement and "does not imply it can never express a difference" in statement
    for name, value in sat["cells"].items():
        assert value in ("all_observed_scores_0", "all_observed_scores_1"), name
    blob = json.dumps(out)
    assert '"floor"' not in blob and '"ceiling"' not in blob


def test_instrument_claim_is_narrowed_to_nonconstant_scores(out):
    inst = out["instrument_statement"]
    assert inst["distinct_observed_scores"] == [0, 1]
    assert inst["cells_with_more_than_one_distinct_output_text"] == 10
    assert inst["cells_with_varying_observed_score"] < 10
    assert "not constant on all outputs" in inst["statement"]
    assert "do not imply varying binary-outcome" in inst["statement"]


def test_records_v1_json_hash_and_its_own_input_hashes(out):
    v1_key = "results/e13a_static_description_20260923.json"
    assert v1_key in out["preserved_v1_inputs"]
    expected = sd2._sha256(ROOT / v1_key)
    assert out["preserved_v1_inputs"][v1_key] == expected
    for name in ("collect/calls.jsonl", "grade/grades.jsonl", "analysis_report.json"):
        assert out["inputs"][name] == sd2._sha256(sd2.RUN / name)
    assert out["supersedes"]["analysis_version"] == "e13a-static-description-v1"


def test_frozen_endpoint_is_reproduced_not_regraded(out):
    frozen = json.loads((sd2.RUN / "analysis_report.json").read_text())["finite_checkpoint_contrast"]
    assert out["equally_weighted_mean_observed_difference"] == pytest.approx(frozen["contrast"])
    assert out["equally_weighted_mean_observed_difference"] == pytest.approx(-0.1)
    assert out["per_checkpoint_observed_difference"]["mbpp/863"] == pytest.approx(-2 / 3)
    assert out["per_checkpoint_observed_difference"]["mbpp/652"] == pytest.approx(0.0)


def test_leave_one_out_states_it_changes_the_target(out):
    loo = out["leave_one_out"]
    assert loo["mean_with_one_checkpoint_removed"]["mbpp/863"] == pytest.approx(1 / 24)
    assert loo["sign_differs_from_declared_target"] == ["mbpp/863"]
    assert "CHANGES THE TARGET" in loo["statement"]
    assert "not a corrected estimate" in loo["statement"]


def test_no_parseability_conditioned_contrast_and_all_slots_kept(out):
    pts = out["post_treatment_selection"]
    assert pts["slots_assigned"] == 60 == pts["slots_graded"]
    assert pts["slots_dropped_after_continuation"] == 0
    assert "post-treatment selection" in pts["conditional_contrast_refused"]
    assert len(out["per_checkpoint"]) == 5


def test_refuses_to_overwrite_and_to_touch_v1(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    with pytest.raises(SystemExit):
        sd2.main(["--out", str(p)])
    before = sd2._sha256(sd2.V1_JSON)
    with pytest.raises(SystemExit):
        sd2.main(["--out", str(sd2.V1_JSON)])
    assert sd2._sha256(sd2.V1_JSON) == before
