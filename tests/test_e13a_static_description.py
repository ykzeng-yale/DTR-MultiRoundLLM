"""Static description of E13a outputs: reads immutable records only; nothing is executed or regraded."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e13a_static_description as sd  # noqa: E402


@pytest.fixture(scope="module")
def out():
    return sd.build()


def test_reproduces_the_frozen_contrast_without_regrading(out):
    frozen = json.loads((sd.RUN / "analysis_report.json").read_text())["finite_checkpoint_contrast"]
    assert out["equally_weighted_mean"] == pytest.approx(frozen["contrast"])
    assert out["per_checkpoint_difference"]["mbpp/863"] == pytest.approx(-2 / 3)
    assert out["per_checkpoint_difference"]["mbpp/842"] == pytest.approx(0.5)


def test_instrument_is_not_inert(out):
    d = out["discipline_checks"]
    assert d["instrument_inert"] is False
    assert d["instrument_inertness_evidence"]["distinct_outcomes_observed"] == [0, 1]
    assert d["instrument_inertness_evidence"]["cells_with_more_than_one_distinct_output"] == 10


def test_sign_depends_on_one_checkpoint(out):
    d = out["discipline_checks"]
    assert d["sign_flips_when_one_checkpoint_removed"] == ["mbpp/863"]
    assert d["leave_one_out_mean"]["mbpp/863"] == pytest.approx(1 / 24)   # +0.0417, sign reversed


def test_saturation_and_no_post_treatment_selection(out):
    d = out["discipline_checks"]
    assert d["saturated_cells"]["mbpp/863:FRESH"] == "ceiling"
    assert d["saturated_cells"]["mbpp/652:FRESH"] == "floor" and d["saturated_cells"]["mbpp/652:R1"] == "floor"
    assert d["post_treatment_selection"]["slots_assigned"] == 60 == d["post_treatment_selection"]["slots_graded"]
    assert d["post_treatment_selection"]["slots_dropped_after_continuation"] == 0


def test_format_asymmetry_is_reported_and_conditional_contrast_refused(out):
    f = out["format_under_the_frozen_rule"]
    assert f["by_arm"]["R1"]["static_failures"] == 13 and f["by_arm"]["FRESH"]["static_failures"] == 0
    assert "post-treatment selection" in f["conditional_contrast_refused"]


def test_refuses_to_overwrite(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    with pytest.raises(SystemExit):
        sd.main(["--out", str(p)])
