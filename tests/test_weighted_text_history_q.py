"""Deterministic fixture fits; no real pilot, candidate or receiver execution."""
import copy
from fractions import Fraction

import numpy as np
import pytest

from experiments.sequential.public_history import bind_selection
from experiments.sequential import text_history_q as original
from experiments.sequential import weighted_text_history_q as weighted


def view(task, turn, prior=None):
    messages = [{'role': 'user', 'content': task},
                {'role': 'assistant', 'content': 'initial answer'}]
    observations = [{'message_index': 1, 'status': 'FAIL', 'observer_sha256': 'c' * 64}]
    if turn == 2:
        messages += [{'role': 'user', 'content': prior.lower() + ' request'},
                     {'role': 'assistant', 'content': 'revised answer'}]
        observations.append({'message_index': 3, 'status': 'PASS', 'observer_sha256': 'c' * 64})
    return {'messages': messages, 'public_observations': observations,
            'remaining_calls': 3 - turn, 'receiver_sha256': 'a' * 64,
            'generator_sha256': 'b' * 64,
            'slate': [{'id': 'STOP', 'kind': 'STOP', 'text': '', 'calls_required': 0},
                      {'id': 'PATCH', 'kind': 'PROMPT', 'text': 'patch request', 'calls_required': 1},
                      {'id': 'RETHINK', 'kind': 'PROMPT', 'text': 'rethink request', 'calls_required': 1}]}


def episode(identity, family, first, second=None, outcome=0):
    first_view = view('task ' + identity, 1)
    steps = [{'view': first_view, 'selection': bind_selection(first_view, [1 / 3] * 3, first)}]
    if first != 'STOP':
        next_view = view('task ' + identity, 2, first)
        steps.append({'view': next_view,
                      'selection': bind_selection(next_view, [1 / 3] * 3, second)})
    return {'episode': identity, 'family': family, 'steps': steps, 'outcome': outcome}


def data():
    return [episode('e0', 'large', 'STOP', outcome=0),
            episode('e1', 'large', 'STOP', outcome=0),
            episode('e2', 'small', 'STOP', outcome=1),
            episode('e3', 'large', 'PATCH', 'STOP', 0),
            episode('e4', 'large', 'PATCH', 'PATCH', 0),
            episode('e5', 'small', 'RETHINK', 'RETHINK', 1),
            episode('e6', 'small', 'RETHINK', 'PATCH', 1)]


def equal_family_weights(episodes):
    return {episode['episode']: Fraction(1, 4 if episode['family'] == 'large' else 3)
            for episode in episodes}


def intercept_only(_):
    x = np.zeros(original.DIM)
    x[0] = 1
    return x


def test_weighted_ridge_matches_scalar_closed_form(monkeypatch):
    monkeypatch.setattr(weighted, 'DIM', 2)
    coefficients = weighted._weighted_ridge([np.array([1., 0.]), np.array([1., 1.])],
                                            [0, 1], [1, 3])
    assert coefficients == pytest.approx([3 / 7, 3 / 7])


def test_unequal_family_intercept_uses_equal_family_episode_masses(monkeypatch):
    monkeypatch.setattr(weighted, 'features', intercept_only)
    episodes = data()
    model = weighted.fit_weighted(episodes, equal_family_weights(episodes))
    assert model['coefficients'][0][0, 0] == pytest.approx(2 / 5)
    assert model['coefficients'][1][1, 0] == pytest.approx(4 / 7)
    metadata = model['sample_weight_metadata']
    assert metadata['episode_count'] == 7 and metadata['family_count'] == 2
    assert metadata['normalized_family_totals'] == {'large': [7, 2], 'small': [7, 2]}
    assert metadata['normalized_weight_sum'] == 7
    assert all(len(metadata[key]) == 64 for key in ('input_weight_sha256', 'normalized_weight_sha256'))
    assert model['version'] == weighted.VERSION


def test_global_weight_scale_invariance():
    episodes = data()
    weights = equal_family_weights(episodes)
    first = weighted.fit_weighted(episodes, weights)
    scaled = weighted.fit_weighted(episodes, {key: value * 17 for key, value in weights.items()})
    for left, right in zip(first['coefficients'], scaled['coefficients']):
        np.testing.assert_allclose(left, right, atol=1e-12)
    assert first['sample_weight_metadata']['normalized_weight_sha256'] == scaled['sample_weight_metadata']['normalized_weight_sha256']
    assert first['sample_weight_metadata']['input_weight_sha256'] != scaled['sample_weight_metadata']['input_weight_sha256']


def test_uniform_weights_match_original_ridge_convention():
    episodes = data()
    first = original.fit(episodes)
    uniform = weighted.fit_weighted(episodes, {episode['episode']: 5 for episode in episodes})
    for left, right in zip(first['coefficients'], uniform['coefficients']):
        np.testing.assert_allclose(left, right, atol=1e-12)
    assert first['action_counts'] == uniform['action_counts']


def test_full_episode_weights_survive_stage_and_action_subsetting(monkeypatch):
    episodes = data()
    weights = equal_family_weights(episodes)
    captured = []
    real = weighted._weighted_ridge
    def traced(xs, ys, stage_weights):
        captured.append(stage_weights)
        return real(xs, ys, stage_weights)
    monkeypatch.setattr(weighted, '_weighted_ridge', traced)
    model = weighted.fit_weighted(episodes, weights)
    large, small = 7 / 8, 7 / 6
    expected = [[large], [large, small], [small],
                [large, large, small], [large, large], [small, small]]
    for observed, declared in zip(captured, expected):
        assert observed == pytest.approx(declared)
    assert model['action_weight_totals'][1] == {'STOP': [7, 8], 'PATCH': [49, 24], 'RETHINK': [7, 6]}


@pytest.mark.parametrize('fault', ['missing', 'extra', 'zero', 'negative', 'nan', 'infinite', 'boolean', 'none'])
def test_invalid_or_unbound_weights_are_refused_before_regression(fault, monkeypatch):
    episodes = data()
    weights = equal_family_weights(episodes)
    if fault == 'missing': weights.pop('e0')
    elif fault == 'extra': weights['new'] = 1
    else: weights['e0'] = {'zero': 0, 'negative': -1, 'nan': float('nan'),
                           'infinite': float('inf'), 'boolean': True, 'none': None}[fault]
    def never(*args, **kwargs): raise AssertionError('reached regression')
    monkeypatch.setattr(weighted, '_weighted_ridge', never)
    with pytest.raises(ValueError): weighted.fit_weighted(episodes, weights)


def test_stage_action_support_and_terminal_labels_required():
    episodes = data()
    missing_action = [episode for episode in episodes if episode['episode'] != 'e3']
    with pytest.raises(ValueError, match='stage-action support'):
        weighted.fit_weighted(missing_action, equal_family_weights(missing_action))
    episodes[0]['outcome'] = None
    with pytest.raises(ValueError, match='outcome'):
        weighted.fit_weighted(episodes, equal_family_weights(episodes))


def test_existing_disjoint_evaluator_refuses_training_family_overlap():
    episodes = data()
    model = weighted.fit_weighted(episodes, equal_family_weights(episodes))
    with pytest.raises(ValueError, match='overlap'):
        original.evaluate_disjoint(model, episodes)
    holdout = copy.deepcopy(episodes)
    for episode in holdout:
        episode['family'] = 'heldout-' + episode['family']
    assert len(original.evaluate_disjoint(model, holdout)) == len(holdout)


def test_weight_identity_hash_is_order_independent_and_fitting_does_not_mutate():
    episodes = data()
    weights = equal_family_weights(episodes)
    before = copy.deepcopy(episodes)
    first = weighted.fit_weighted(episodes, weights)
    reverse = weighted.fit_weighted(episodes, dict(reversed(list(weights.items()))))
    assert first['sample_weight_metadata'] == reverse['sample_weight_metadata']
    assert episodes == before
