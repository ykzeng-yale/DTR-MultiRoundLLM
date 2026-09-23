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

def test_policy_contrast_sd_matches_hand_derivation():
    f, tau2, R, d = 5 / 14, 0.025, 8, 0.20
    sigma2_cond = tau2 + 0.25 / R
    expected = ((f * (sigma2_cond + d * d) - (f * d) ** 2)) ** 0.5
    assert s.policy_sd(f, tau2, R, d) == pytest.approx(expected)
    # Delta = 0 collapses to f * sigma2_cond
    assert s.policy_sd(f, tau2, R, 0.0) == pytest.approx((f * sigma2_cond) ** 0.5)


def test_threshold_rules_are_symmetric_at_equality_and_unreachable_below_it():
    sd = s.policy_sd(5 / 14, 0.025, 8, 0.14)
    # theta exactly at the threshold: neither rule fires more than the interval's own 2.5% tail
    assert s.power_benefit(0.05, sd, 124) == pytest.approx(0.025, abs=1e-3)
    assert s.power_futility(0.05, sd, 124) == pytest.approx(0.025, abs=1e-3)
    assert s.n_for_80(0.0, sd) is None and s.n_for_80(-0.01, sd) is None


def test_e12_effect_cannot_reach_the_usefulness_threshold():
    u = s.build()["usefulness_full_policy"]
    assert u["threshold"] == 0.05
    assert u["min_delta_cond_for_theta_above_threshold"] == pytest.approx(0.14)
    e12 = [r for r in u["rows"] if r["delta_cond"] == 0.10 and r["replicates"] == 8 and r["tau2"] == 0.025][0]
    assert e12["theta_policy"] == pytest.approx(0.0357, abs=1e-4)
    assert e12["n_roots_for_80pct_benefit"] is None and "no sample size" in e12["benefit_unreachable_reason"]
    assert e12["n_roots_for_80pct_futility"] == 861          # futility at the E12 effect needs far more roots
    inert = [r for r in u["rows"] if r["delta_cond"] == 0.0 and r["replicates"] == 8 and r["tau2"] == 0.025][0]
    assert inert["n_roots_for_80pct_futility"] == 64          # an inert rule is the one decisive reachable case


def test_demonstrable_effect_and_futility_bound_at_the_available_frame():
    u = s.build()["usefulness_full_policy"]
    assert u["n_roots_available"] == 124
    d80 = u["min_delta_cond_demonstrable_at_available_n"]["tau2=0.025,R=8"]["power_80pct"]
    assert 0.27 < d80 < 0.29                                  # about 3x the E12 point estimate
    assert u["max_theta_declarable_futile_at_available_n"]["tau2=0.025,R=8"] == pytest.approx(0.014, abs=0.002)
    assert u["max_theta_declarable_futile_at_available_n"]["tau2=0.1,R=8"] == 0.0


def test_usefulness_states_its_stop_only_scope_limit():
    u = s.build()["usefulness_full_policy"]
    limit = u["scope_limit"]
    assert "ALWAYS-STOP only" in limit and "fixed CONTINUATION" in limit
    assert "NOT done here" in limit          # sizing against b1 must not be claimed
