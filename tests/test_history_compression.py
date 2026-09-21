"""Structural controls for the exact E0 representation diagnostic."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('history_compression_check', Path(__file__).resolve().parents[1] / 'scripts/check_history_compression.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize('horizon', [1, 2, 3])
def test_on_policy_aggregation_despite_persistent_latents(horizon):
    law = module.kernel()
    target = np.full(5, .2)
    actual = module.compressed_limit(law, module.make_beh(0, .2), target, horizon)
    assert actual['value'] == pytest.approx(module.true_value(law, target, horizon), abs=1e-12)


def test_one_decision_has_no_omitted_past():
    law, target = module.kernel(), np.full(5, .2)
    for kappa, floor in [(1, .1), (2.5, .02)]:
        value = module.compressed_limit(law, module.make_beh(kappa, floor), target, 1)['value']
        assert value == pytest.approx(module.true_value(law, target, 1), abs=1e-12)


def test_latent_invariant_kernel_removes_history_bias():
    law = module.kernel()
    law[:] = law.mean(axis=(0, 1), keepdims=True)
    target = np.array([.1, .2, .3, .25, .15])
    actual = module.compressed_limit(law, module.make_beh(2.5, .02), target, 3)['value']
    assert actual == pytest.approx(module.true_value(law, target, 3), abs=1e-12)


def test_full_history_posterior_matches_separate_latent_dp():
    law, target = module.kernel(), np.array([.1, .2, .3, .25, .15])
    assert module.history_oracle(law, target, 3)['value'] == pytest.approx(module.true_value(law, target, 3), abs=1e-12)


def test_hidden_assignment_extension_requires_separate_design():
    with pytest.raises(ValueError, match='gz=0'):
        module.compressed_limit(module.kernel(), module.make_beh(1, .1, 1), np.full(5, .2), 3)
