import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("landmark_premise", Path(__file__).parents[1] / "scripts/run_landmark_premise.py")
premise = importlib.util.module_from_spec(spec)
spec.loader.exec_module(premise)


def test_zero_marginal_contrast_does_not_remove_personalization():
    q = premise.public_q("qualitative_interaction")
    assert np.allclose(q.mean(axis=0), [.6, .6])
    assert np.isclose(q.max(axis=1).mean() - q.mean(axis=0).max(), .2)


def test_hidden_signal_is_not_available_to_policy():
    assert np.allclose(premise.public_q("unavailable_signal"), .6)
    rows = premise.replicate("unavailable_signal", 123, n_train=50, n_test=80)
    assert all(np.isclose(r["true_policy_gain"], 0) for r in rows)
    assert all(np.isclose(r["public_oracle_gain"], 0) for r in rows)
    assert {r["branch_repetitions"] for r in rows} == {1, 4}
