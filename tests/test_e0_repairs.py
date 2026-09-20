"""Regression tests for the Sept 20 scientific audit repairs."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments' / 'e0'))
from estimators import blip_ipw
from simulator import (ARMS, kernel, template_kernel, make_beh, true_blips_posterior,
                       true_logging_conditional_blips, optimal_rule)
from run_grid import seed_jobs


def test_first_assignment_confounding_requires_initial_inverse_weight():
    # Equal latent strata: treatment rates .2 and .8, treatment outcomes 1 and 0.
    # Naive treated mean=.2; intervention mean=.5. STOP always yields 0.
    A = np.array([1]*2+[0]*8+[1]*8+[0]*2)
    B = np.array([.2]*2+[.8]*8+[.8]*8+[.2]*2)
    Y = np.array([1]*2+[0]*18)
    d = dict(elig=np.ones((20, 1), bool), S=np.ones((20, 1), int),
             A=A[:, None], B=B[:, None], Y=Y)
    assert Y[A == 1].mean() == pytest.approx(.2)
    assert blip_ipw(d, 1, 1)['RETRY'] == pytest.approx(.5)


def test_continuation_target_agreement_only_under_uniform_logging():
    k = kernel()
    uniform = true_blips_posterior(k, 3)
    assoc_uniform = true_logging_conditional_blips(k, 3, make_beh(0, .2))
    assert max(abs(uniform[key]-assoc_uniform[key]) for key in uniform) < 1e-14
    assoc = true_logging_conditional_blips(k, 3, make_beh(1, .1))
    assert max(abs(uniform[key]-assoc[key]) for key in uniform) > .01


def test_template_truth_changes_with_mixture():
    assert np.allclose(template_kernel(1, np.zeros((5, 3))), kernel())
    offsets = np.ones((5, 3)) * .4
    changed = template_kernel(1, offsets)
    assert not np.allclose(changed, kernel())
    assert np.allclose(changed[:, :, :, 1:].sum(-1), 1)
    assert (changed[:, :, :, 1:, 3] > kernel()[:, :, :, 1:, 3]).all()


def test_no_false_state_optimality_claim():
    with pytest.raises(ValueError, match='not implemented'):
        optimal_rule(kernel(), 3, 'state')
    assert len(optimal_rule(kernel(), 3, 'full')) == 3*5*2*4


@pytest.mark.parametrize('reps,workers', [(1000, 12), (7, 3), (2, 8)])
def test_exact_distinct_replicate_count(reps, workers):
    got = np.concatenate(seed_jobs(reps, workers, 122))
    assert np.array_equal(got, np.arange(122, 122+reps))


def test_saved_replicates_can_be_reanalysed_after_json_roundtrip():
    import json
    from run_grid import one_rep, metrics, BASE
    cfg=dict(BASE, n_tasks=20, runs=20, T=2)
    reps=[one_rep((s,cfg)) for s in (19,20)]
    original=metrics(reps,cfg)
    restored=metrics(json.loads(json.dumps(reps)),cfg)
    assert original == restored
