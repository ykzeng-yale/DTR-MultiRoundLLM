"""Checks for stopping replay assumptions, not empirical LLM validation."""
import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_stopping_identities.py"
spec = importlib.util.spec_from_file_location("stopping_identity_check", SCRIPT)
stop = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = stop
spec.loader.exec_module(stop)


@pytest.mark.parametrize("rule", [stop.stop_visible, stop.stop_cap])
def test_full_rollout_replay_matches_direct_stopping_under_identical_continuation(rule):
    direct = stop.direct_stopped_value(stop.logger_probability, rule)
    replay = stop.replay_value(stop.logger_probability, rule, weighted=False)
    assert replay["value"] == pytest.approx(direct, abs=1e-12)
    assert replay["total_probability"] == pytest.approx(1.0)
    assert replay["complete_path_count"] == 512


@pytest.mark.parametrize("rule", [stop.stop_visible, stop.stop_cap])
def test_changed_continuation_needs_prefix_action_ratio(rule):
    direct = stop.direct_stopped_value(stop.changed_probability, rule)
    naive = stop.replay_value(stop.changed_probability, rule, weighted=False)
    weighted = stop.replay_value(stop.changed_probability, rule, weighted=True)
    assert abs(naive["value"] - direct) > 0.01
    assert weighted["value"] == pytest.approx(direct, abs=1e-12)
    assert weighted["expected_stopped_weight"] == pytest.approx(1.0, abs=1e-12)


def test_privileged_hidden_labels_create_an_unattainable_public_selection_gap():
    result = stop.information_counterexample()
    assert result["best_public_value"] == 0.5
    assert result["privileged_current_grade_rule"] == 0.75
    assert result["future_prophet"] == 0.75


def test_complete_case_deletion_bias_and_valid_observation_weight_correction():
    result = stop.censoring_counterexample()
    assert result["truth"] == pytest.approx(0.5)
    assert result["complete_case_value"] == pytest.approx(0.74)
    assert result["inverse_observation_weighted_value"] == pytest.approx(result["truth"])


def test_overlap_worst_case_bound_is_not_the_actual_population_ess():
    result = stop.ess_counterexample()
    assert result["population_ess_lower_bound"] == 2.75
    assert result["actual_population_ess"] > 175


def test_deleting_diagnostic_branches_can_change_the_task_state_distribution():
    result = stop.diagnostic_counterexample()
    assert result["admissible_target_value"] == 0.5
    assert result["unweighted_filtered_value"] == pytest.approx(0.1)
    assert result["weighted_filtered_value"] == pytest.approx(0.5)


def test_scoped_identity_check_suite_and_failure_counterexamples():
    result = stop.run_checks()
    assert result["stop_side_effect_counterexample"]["actual_stop_rewrite_value"] == 0
    assert result["certificate_impossibility_counterexample"]["null_upper_tail_probability"] < 0.05
