"""Exact checks for prompt-choice theory, not empirical prompt-effect evidence."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import sys


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_landmark_theory.py"
spec = importlib.util.spec_from_file_location("landmark_theory_check", SCRIPT)
landmark = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = landmark
spec.loader.exec_module(landmark)


def test_zero_ate_can_have_strong_personalization_value():
    result = landmark.ate_and_personalization()
    assert result["ate"] == 0
    assert result["personalization_gain"] == F(1, 5)
    assert result["homogeneous_large_ate_but_no_personalization"]["personalization_gain"] == 0


def test_sample_max_has_noise_and_unavailable_information_gaps():
    result = landmark.oracle_gaps()
    null = result["homogeneous_null"]
    assert null["expected_sample_max"]["1"] - null["public_and_checkpoint_oracle"] == F(91, 400)
    latent = result["unavailable_signal"]
    assert latent["irreducible_information_gap"] == F(1, 5)
    assert latent["expected_sample_max"]["8"] >= latent["checkpoint_oracle"]


def test_new_seeds_do_not_fix_policy_training_on_evaluation_root_labels():
    result = landmark.within_root_label_leakage()
    assert result["use_test_root_labels_then_fresh_evaluation"] == F(17, 25)
    assert result["extra_information_gain"] > 0


def test_known_randomization_identifies_values_despite_history_imbalance():
    result = landmark.randomization_identity()
    assert result["weighted_policy_value"] == result["personalized_truth"]
    assert result["expected_policy_weight"] == 1
    assert result["spurious_unadjusted_arm_difference"] != 0


def test_finite_action_regret_factor_and_gap_condition():
    result = landmark.regret_bound()
    assert result["grid_cases"] == 5832
    assert result["large_gap_cases"] > 0
    assert result["factor_two_attained"]


def test_root_variance_keeps_heterogeneity_and_accounts_for_coupling():
    result = landmark.paired_root_variance()
    assert result["root_contrast_variance_by_repetitions"]["4"] == F(13, 50)
    coupling = result["root_variance_at_r4_by_coupling"]
    assert coupling["common_uniform"] < coupling["independent"] < coupling["antithetic"]
    assert result["n_times_naive_variance_treating_4n_pairs_independent"] == F(7, 50)


def test_shifted_history_distribution_can_reverse_the_landmark_gain():
    result = landmark.distribution_shift()
    assert result["source_history_gain"] > 0
    assert result["target_history_gain"] < 0
    assert result["target_history_gain"] == result["history_reweighted_gain"]
