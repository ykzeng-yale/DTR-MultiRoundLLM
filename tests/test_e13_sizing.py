"""Scalar checks using committed inputs; no model, benchmark or candidate execution."""
import statistics
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
    assert e["mean_within_sample_var_per_replicate"] == pytest.approx(0.30)


def test_bernoulli_population_cap_is_not_a_sample_variance_cap():
    assert statistics.variance([0, 1]) == 0.5 > s.WITHIN_VAR
    out = s.build()
    assert out["assumptions"]["tau2_scenarios"] == [0.025, 0.05, 0.10, 0.20]
    assert "tau2_moment_consistent_with_cap" not in out["e12_gated"]
    assert "gate_rate_wilson95" not in out["e12_gated"]
    assert "expected_gated_full_at_wilson_bounds" not in out["frame"]
    assert out["frame"]["retained_root_count_scenario"] == 124
    assert "not established lower bounds" in out["e12_gated"]["tau2_note"]


def test_hoeffding_matches_lead_arithmetic():
    # docs/independent_prompt_policy_validation_design_20260922.md: radius at 3,506 families is .04999730
    assert s.precision(3506, 0.0, 1)["hoeffding_radius95_two_contrasts"] == pytest.approx(0.04999730, abs=1e-8)
    assert s.precision(3505, 0.0, 1)["hoeffding_radius95_two_contrasts"] == pytest.approx(0.05000443, abs=1e-8)


def test_cost_formula_reproduces_e12_release_and_v1_proposal():
    e12 = s.cost(14, 14, 2, arms=5)
    assert (e12["receiver_calls"], e12["isolated_starts"], e12["reserved_completion_tokens"]) == (154, 238, 78848)
    v1 = s.cost(30, 11, 2, arms=1, audit_all=True)
    assert (v1["receiver_calls"], v1["isolated_starts"], v1["reserved_completion_tokens"]) == (90, 270, 46080)


def test_two_sampled_arms_add_noise_when_holding_tau2_fixed():
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


def test_threshold_equality_has_tail_probabilities_but_not_80pct_power():
    sd = s.policy_sd(5 / 14, 0.025, 8, 0.14)
    # theta exactly at the threshold: neither rule fires more than the interval's own 2.5% tail
    assert s.power_benefit(0.05, sd, 124) == pytest.approx(0.025, abs=1e-3)
    assert s.power_futility(0.05, sd, 124) == pytest.approx(0.025, abs=1e-3)
    assert s.n_for_80(0.0, sd) is None and s.n_for_80(-0.01, sd) is None


def test_e12_selected_effect_scenario_does_not_attain_80pct_benefit_power():
    u = s.build()["usefulness_full_policy"]
    assert u["threshold"] == 0.05
    assert u["min_delta_cond_for_theta_above_threshold"] == pytest.approx(0.14)
    e12 = [r for r in u["rows"] if r["delta_cond"] == 0.10 and r["replicates"] == 8 and r["tau2"] == 0.025][0]
    assert e12["theta_policy"] == pytest.approx(0.0357, abs=1e-4)
    assert e12["n_roots_for_80pct_benefit"] is None
    assert "80% benefit power" in e12["benefit_80pct_unattainable_reason"]
    assert 0 < e12["power_benefit_at_available_n"] < 0.025
    assert e12["n_roots_for_80pct_futility"] == 861          # futility at the E12 effect needs far more roots
    inert = [r for r in u["rows"] if r["delta_cond"] == 0.0 and r["replicates"] == 8 and r["tau2"] == 0.025][0]
    assert inert["n_roots_for_80pct_futility"] == 64
    larger_gain = next(r for r in u["rows"] if r["delta_cond"] == 0.30 and r["replicates"] == 8 and r["tau2"] == 0.025)
    assert larger_gain["n_roots_for_80pct_benefit"] == 98 < u["n_roots_available"]


def test_demonstrable_effect_and_futility_bound_at_the_available_frame():
    u = s.build()["usefulness_full_policy"]
    assert u["n_roots_available"] == 124
    d80 = u["min_delta_cond_demonstrable_at_available_n"]["tau2=0.025,R=8"]["power_80pct"]
    assert 0.27 < d80 < 0.29                                  # about 3x the E12 point estimate
    assert u["max_theta_declarable_futile_at_available_n"]["tau2=0.025,R=8"] == pytest.approx(0.014, abs=0.002)
    assert u["max_theta_declarable_futile_at_available_n"]["tau2=0.1,R=8"] is None
    assert u["max_theta_declarable_futile_at_available_n"]["tau2=0.2,R=8"] is None


@pytest.mark.parametrize("tau2", s.TAU2_SCENARIOS)
@pytest.mark.parametrize("R", [6, 8])
def test_benefit_inversions_return_the_requested_probability(tau2, R):
    f, n = 5 / 14, 124
    d50 = s._solve_delta(n, s.Z95, f, tau2, R)
    d80 = s._solve_delta(n, s.Z95 + s.Z80, f, tau2, R)
    assert d50 is not None and d80 is not None and d50 < d80
    for d, probability in [(d50, 0.50), (d80, 0.80)]:
        assert s.power_benefit(f * d, s.policy_sd(f, tau2, R, d), n) == pytest.approx(probability)


def test_delta_inversion_keeps_a_feasible_upper_boundary():
    assert s._solve_delta(1, 1.0, 1.0, 0.0, 1, threshold=0.5) == pytest.approx(1.0)
    assert s._solve_delta(1, 2.0, 1.0, 0.0, 1, threshold=0.5) is None


@pytest.mark.parametrize("tau2", s.TAU2_SCENARIOS)
def test_futility_inversion_distinguishes_infeasible_from_zero(tau2):
    f, n, R = 5 / 14, 124, 8
    boundary = s._solve_futile_theta(n, f, tau2, R)
    null_power = s.power_futility(0, s.policy_sd(f, tau2, R, 0), n)
    if boundary is None:
        assert null_power < 0.8
    else:
        assert boundary >= 0 and null_power >= 0.8
        assert s.power_futility(boundary, s.policy_sd(f, tau2, R, boundary / f), n) == pytest.approx(0.8)
        assert s.power_futility(boundary + 1e-5, s.policy_sd(f, tau2, R, (boundary + 1e-5) / f), n) < 0.8


def test_usefulness_states_its_stop_only_scope_limit():
    u = s.build()["usefulness_full_policy"]
    limit = u["scope_limit"]
    assert "ALWAYS-STOP only" in limit and "fixed CONTINUATION" in limit
    assert "NOT done here" in limit          # sizing against b1 must not be claimed
    assert "neither the variance nor the required sample size is ordered" in limit
    assert "simultaneous two-contrast power" in u["power_scope"]
