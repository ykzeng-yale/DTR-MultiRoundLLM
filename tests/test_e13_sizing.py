"""Arithmetic checks for the E13 planning script (reads committed files only; nothing is executed)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e13_sizing as s  # noqa: E402


def test_e12_gated_decomposition():
    e = s.e12_gated()
    assert [r["root_id"] for r in e["roots"]] == ["mbpp/863", "mbpp/842", "mbpp/288", "mbpp/966", "mbpp/652"]
    assert (e["n_roots"], e["n_gated"], e["replicates"]) == (14, 5, 2)
    assert e["delta_hat"] == pytest.approx(0.1)
    assert e["var_root_means"] == pytest.approx(0.175)
    assert e["mean_within_var_of_root_mean"] == pytest.approx(0.15)
    assert e["tau2_moment"] == pytest.approx(0.025)


def test_hoeffding_matches_lead_arithmetic():
    # docs/independent_prompt_policy_validation_design_20260922.md: radius at 3,506 families is .04999730
    assert s.precision(3506, 0.0, 1)["hoeffding_radius95_two_contrasts"] == pytest.approx(0.04999730, abs=1e-8)
    assert s.precision(3505, 0.0, 1)["hoeffding_radius95_two_contrasts"] == pytest.approx(0.05000443, abs=1e-8)


def test_cost_formula_reproduces_e12_release_and_v1_proposal():
    e12 = s.cost(14, 14, 2, arms=5)
    assert (e12["receiver_calls"], e12["isolated_starts"], e12["reserved_completion_tokens"]) == (154, 238, 78848)
    v1 = s.cost(30, 11, 2, arms=1, audit_all=True)
    assert (v1["receiver_calls"], v1["isolated_starts"], v1["reserved_completion_tokens"]) == (90, 270, 46080)


def test_power_is_monotone_and_mechanism_contrast_is_noisier():
    a = s.precision(44, 0.025, 8)
    b = s.precision(44, 0.025, 8, arms_varying=2)
    assert b["sd_root_diff"] > a["sd_root_diff"] and b["power_at_0.10"] < a["power_at_0.10"]
    assert s.precision(44, 0.1, 8)["power_at_0.10"] < a["power_at_0.10"]


def test_refuses_to_overwrite(tmp_path):
    out = tmp_path / "x.json"
    out.write_text("{}")
    with pytest.raises(SystemExit):
        s.main(["--out", str(out)])
