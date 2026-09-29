"""Small deterministic contract checks, not model efficacy simulations."""
import copy
import math

import pytest

from experiments.sequential.public_history import bind_selection
from experiments.sequential.text_history_q import fit, evaluate_disjoint, validate, features


def view(task, turn, prior=None):
    messages = [{'role': 'user', 'content': task},
                {'role': 'assistant', 'content': 'initial answer'}]
    observations = [{'message_index': 1, 'status': 'FAIL', 'observer_sha256': 'c'*64}]
    if turn == 2:
        prompt = 'patch request' if prior == 'PATCH' else 'rethink request'
        messages += [{'role': 'user', 'content': prompt},
                     {'role': 'assistant', 'content': 'revised answer'}]
        observations.append({'message_index': 3, 'status': 'PASS', 'observer_sha256': 'c'*64})
    return {'messages': messages, 'public_observations': observations,
            'remaining_calls': 3-turn, 'receiver_sha256': 'a'*64,
            'generator_sha256': 'b'*64,
            'slate': [{'id': 'STOP', 'kind': 'STOP', 'text': '', 'calls_required': 0},
                      {'id': 'PATCH', 'kind': 'PROMPT', 'text': 'patch request', 'calls_required': 1},
                      {'id': 'RETHINK', 'kind': 'PROMPT', 'text': 'rethink request', 'calls_required': 1}]}


def episode(i, family, first, second=None, outcome=0):
    first_view = view('task '+str(i), 1)
    steps = [{'view': first_view,
              'selection': bind_selection(first_view, [1/3]*3, first)}]
    if first != 'STOP':
        second_view = view('task '+str(i), 2, first)
        steps.append({'view': second_view,
                      'selection': bind_selection(second_view, [1/3]*3, second)})
    return {'episode': str(i), 'family': family, 'steps': steps, 'outcome': outcome}


def assignments(prefix):
    return [episode(0, prefix+'0', 'STOP', outcome=0),
            episode(1, prefix+'1', 'STOP', outcome=1),
            episode(2, prefix+'2', 'PATCH', 'STOP', 0),
            episode(3, prefix+'3', 'PATCH', 'PATCH', 1),
            episode(4, prefix+'4', 'RETHINK', 'RETHINK', 1),
            episode(5, prefix+'5', 'RETHINK', 'PATCH', 0)]


def test_full_history_controller_and_disjoint_scores():
    train = assignments('train')
    model = fit(train)
    assert model['action_counts'] == [{'STOP': 2, 'PATCH': 2, 'RETHINK': 2},
                                      {'STOP': 1, 'PATCH': 2, 'RETHINK': 1}]
    holdout = assignments('holdout')
    scores = evaluate_disjoint(model, holdout)
    assert len(scores) == len(holdout)
    assert all(math.isfinite(s[k]) for s in scores for k in ('ipw', 'dr'))
    with pytest.raises(ValueError, match='overlap'):
        evaluate_disjoint(model, train)


def test_training_requires_stage_action_support_and_complete_labels():
    data = assignments('train')
    with pytest.raises(ValueError, match='support'):
        fit([e for e in data if e['steps'][-1]['selection']['chosen_id'] != 'STOP'])
    data[0]['outcome'] = None
    with pytest.raises(ValueError, match='outcome'):
        validate(data)


def test_future_or_private_field_and_post_stop_refused():
    data = assignments('train')
    bad = copy.deepcopy(data)
    bad[0]['steps'][0]['view']['private_outcome'] = 1
    with pytest.raises(ValueError):validate(bad)
    bad = copy.deepcopy(data)
    bad[0]['steps'].append(copy.deepcopy(bad[1]['steps'][0]))
    with pytest.raises(ValueError):validate(bad)
    bad = copy.deepcopy(data)
    bad[2]['steps'][1]['view']['messages'][2]['content'] = 'different prompt'
    with pytest.raises(ValueError):validate(bad)
    bad = copy.deepcopy(data)
    bad[2]['steps'][1]['view']['public_observations'][0]['status'] = 'PASS'
    bad[2]['steps'][1]['selection'] = bind_selection(
        bad[2]['steps'][1]['view'], [1/3]*3, 'STOP')
    with pytest.raises(ValueError, match='observation history'):
        validate(bad)
    bad = copy.deepcopy(data)
    bad[2]['steps'][0]['selection']['probabilities'] = [.5,.25,.25]
    with pytest.raises(ValueError):validate(bad)


def test_representation_sees_prior_response_but_not_metadata():
    a = view('task', 1)
    b = copy.deepcopy(a)
    b['messages'][1]['content'] = 'different answer'
    assert (features(a) != features(b)).any()


def test_receiver_version_drift_refused_across_fit_and_evaluation():
    train = assignments('train')
    changed = copy.deepcopy(train)
    changed[0]['steps'][0]['view']['receiver_sha256'] = 'd'*64
    changed[0]['steps'][0]['selection'] = bind_selection(
        changed[0]['steps'][0]['view'], [1/3]*3, 'STOP')
    with pytest.raises(ValueError, match='version drift'):
        fit(changed)
    model = fit(train)
    holdout = assignments('holdout')
    for e in holdout:
        for step in e['steps']:
            step['view']['receiver_sha256'] = 'd'*64
            step['selection'] = bind_selection(step['view'], [1/3]*3,
                                               step['selection']['chosen_id'])
    with pytest.raises(ValueError, match='version drift'):
        evaluate_disjoint(model, holdout)
