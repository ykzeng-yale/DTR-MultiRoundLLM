"""Deterministic source-contract fixtures; no task/model/candidate execution."""
import copy

import pytest

from experiments.sequential.development_design import (
    PINS, answer_sha256, bind_assignment, evaluation_rows, learner_rows, make_design,
    policy_lock, reconcile, sha256,
    weighted_learner_bundle,
)


def design():
    roots = {'r0': 'f0', 'r1': 'f0', 'r2': 'f1', 'r3': 'f2',
             'r4': 'f3', 'r5': 'f4', 'r6': 'f5'}
    return make_design(roots,
                       {'train': 2, 'tune': 2, 'evaluation': 2},
                       repeats=2, seed=741, pins={k: str(i % 10) * 64 for i, k in enumerate(PINS)},
                       root_prefix_sha256={r: sha256([{'role': 'user', 'content': 'public task'}]) for r in roots})


def cost(stage, component, *, calls=0, energy=None):
    return {'stage': stage, 'component': component, 'calls': calls,
            'input_tokens': 12 if calls else 0, 'completion_tokens': 8 if calls else 0,
            'elapsed_seconds': .125, 'usd': 0., 'energy_joules': energy}


def view(d, messages, observations, t):
    return {'messages': copy.deepcopy(messages), 'public_observations': copy.deepcopy(observations),
            'remaining_calls': 2 - t, 'receiver_sha256': d['pins']['receiver'],
            'generator_sha256': d['pins']['generator'],
            'slate': [{'id': 'STOP', 'kind': 'STOP', 'text': '', 'calls_required': 0},
                      {'id': 'PATCH', 'kind': 'PROMPT', 'text': 'patch', 'calls_required': 1},
                      {'id': 'RETHINK', 'kind': 'PROMPT', 'text': 'rethink', 'calls_required': 1}]}


def receipt(d, row):
    messages = [{'role': 'user', 'content': 'public task'},
                {'role': 'assistant', 'content': 'initial public answer'}]
    observations = [{'message_index': 1, 'status': 'FAIL',
                     'observer_sha256': d['pins']['public_observer']}]
    steps = []
    costs = [cost('initial', 'receiver', calls=1)]
    last = answer_sha256(messages[-1]['content'])
    initial = last
    termination = 'HORIZON'
    for t in range(2):
        v = view(d, messages, observations, t)
        selected = bind_assignment(d, row['episode'], v, t)
        costs += [cost(str(t), c) for c in ('generator', 'critic', 'public_check')]
        if selected['chosen_id'] == 'STOP':
            steps.append({'view': v, 'selection': selected,
                          'response_status': 'STOP', 'response_sha256': None})
            termination = 'STOP'
            break
        answer = f'public revision {t}'
        last = answer_sha256(answer)
        steps.append({'view': v, 'selection': selected,
                      'response_status': 'RETURNED', 'response_sha256': last})
        costs.append(cost(str(t), 'receiver', calls=1))
        prompt = next(a['text'] for a in v['slate'] if a['id'] == selected['chosen_id'])
        messages += [{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': answer}]
        observations.append({'message_index': len(messages) - 1, 'status': 'PASS',
                             'observer_sha256': d['pins']['public_observer']})
    costs.append(cost('final', 'private_check'))
    return {'episode': row['episode'], 'root': row['root'], 'family': row['family'],
            'split': row['split'], 'config_sha256': d['config_sha256'],
            'initial_sha256': initial, 'steps': steps, 'termination': termination,
            'final_sha256': last, 'outcome': {'status': 'OBSERVED', 'value': 1, 'reason': None,
                                             'instrument_sha256': d['pins']['private_observer'],
                                             'artifact_sha256': last,
                                             'grade_receipt_sha256': sha256({'artifact': last, 'grade': 1})},
            'costs': costs}


def receipts(d, splits=('train', 'tune', 'evaluation')):
    return [receipt(d, r) for r in d['ledger'] if r['split'] in splits]


def test_family_split_draws_are_deterministic_and_all_replicates_stay_together():
    d = design()
    assert d == design()
    assert d['collection_released'] is False
    assert len(d['ledger']) == 14
    assert d['max_receiver_calls'] == 42
    assert len({r['split'] for r in d['ledger'] if r['family'] == 'f0'}) == 1
    for split in ('train', 'tune', 'evaluation'):
        assert len({r['family'] for r in d['ledger'] if r['split'] == split}) == 2


def test_every_assigned_row_and_equal_family_root_weights_survive():
    d = design()
    rows = receipts(d)
    result = reconcile(d, rows)
    assert result['assigned'] == 14
    assert result['unavailable'] == 0
    assert result['minimum_logged_probability'] == 1 / 3
    assert result['maximum_two_decision_inverse_probability'] == 9
    for s in ('train', 'tune', 'evaluation'):
        assert sum(c['trajectories'] for c in result['stage_action_support'][s][0].values()) == sum(e['split'] == s for e in rows)
    for s, bounds in result['split_completion_envelopes'].items():
        assert bounds == pytest.approx([1, 1])
        assert sum(r['weight'] for r in result['rows'] if r['split'] == s) == pytest.approx(1)
    f0 = [r for r in result['rows'] if r['family'] == 'f0']
    assert sum(r['weight'] for r in f0) == pytest.approx(.5)
    with pytest.raises(ValueError, match='all assigned'):
        reconcile(d, rows[:-1])
    rows[-1] = copy.deepcopy(rows[0])
    with pytest.raises(ValueError, match='duplicate'):
        reconcile(d, rows)


def test_weighted_bundle_keeps_equal_family_mass_and_locked_source():
    d = design()
    # Exercise the two-root family wherever the prospective split placed it.
    split = d['family_splits']['f0']
    if split == 'evaluation':
        with pytest.raises(ValueError, match='locked policy'):
            weighted_learner_bundle(d, receipts(d, (split,)), split=split)
        split = 'train'
    records = receipts(d, (split,))
    bundle = weighted_learner_bundle(d, records, split=split)
    assert bundle['config_sha256'] == d['config_sha256']
    assert bundle['receipt_sha256'] == sha256(records)
    assert set(bundle['sample_weights']) == {e['episode'] for e in bundle['episodes']}
    masses = {}
    for e in bundle['episodes']:
        masses[e['family']] = masses.get(e['family'], 0) + bundle['sample_weights'][e['episode']]
    assert list(masses.values()) == pytest.approx([.5, .5])
    records[0]['outcome'].update(status='UNAVAILABLE', value=None, reason='observer unavailable')
    with pytest.raises(ValueError, match='complete-case'):
        weighted_learner_bundle(d, records, split=split)


def test_missing_outcome_is_bounded_and_never_silent_complete_case_fit():
    d = design()
    rows = receipts(d, ('train',))
    rows[0]['outcome'].update(status='UNAVAILABLE', value=None, reason='private observer timeout')
    result = reconcile(d, rows, splits=('train',))
    missing_weight = result['rows'][0]['weight']
    assert result['split_completion_envelopes']['train'] == pytest.approx([1 - missing_weight, 1])
    with pytest.raises(ValueError, match='complete-case'):
        learner_rows(d, rows, split='train')


def test_initial_service_failure_retained_distinct_from_stop():
    d = design()
    rows = receipts(d)
    rows[0].update(initial_sha256=None, final_sha256=None, steps=[], termination='SERVICE_MISSING',
                   costs=[cost('initial', 'receiver', calls=1)])
    rows[0]['outcome'].update(status='UNAVAILABLE', value=None, reason='initial service failed',
                              artifact_sha256=None, grade_receipt_sha256=None)
    result = reconcile(d, rows)
    assert result['unavailable'] == 1
    assert result['rows'][0]['costs']['calls'] == 1
    rows[0]['termination'] = 'STOP'
    with pytest.raises(ValueError, match='terminal'):
        reconcile(d, rows)


def test_frozen_slate_draw_probabilities_and_versions_are_not_replaced():
    d = design()
    rows = receipts(d)
    bad = copy.deepcopy(rows)
    bad[0]['steps'][0]['selection']['probabilities'] = [.5, .25, .25]
    with pytest.raises(ValueError, match='selection'):
        reconcile(d, bad)
    bad = copy.deepcopy(rows)
    bad[0]['steps'][0]['view']['receiver_sha256'] = 'a' * 64
    with pytest.raises(ValueError, match='version'):
        reconcile(d, bad)
    d['ledger'][0]['assigned_actions'][0] = 'OTHER'
    with pytest.raises(ValueError, match='hash drift'):
        reconcile(d, rows)


def test_absorbing_stop_has_no_later_call_and_preserves_exact_artifact():
    d = design()
    rows = receipts(d)
    stopped = next(e for e in rows if e['termination'] == 'STOP')
    stopped['costs'].append(cost(str(len(stopped['steps']) - 1), 'receiver', calls=1))
    with pytest.raises(ValueError, match='after STOP'):
        reconcile(d, rows)
    rows = receipts(d)
    stopped = next(e for e in rows if e['termination'] == 'STOP')
    stopped['final_sha256'] = 'a' * 64
    with pytest.raises(ValueError, match='final answer'):
        reconcile(d, rows)


def test_changed_public_prefix_or_private_field_is_refused():
    d = design()
    rows = receipts(d)
    continued = next(e for e in rows if len(e['steps']) == 2)
    continued['steps'][1]['view']['messages'][0]['content'] = 'changed task'
    continued['steps'][1]['selection'] = bind_assignment(
        d, continued['episode'], continued['steps'][1]['view'], 1)
    with pytest.raises(ValueError, match='prefix'):
        reconcile(d, rows)
    rows = receipts(d)
    rows[0]['steps'][0]['view']['private_grade'] = 1
    with pytest.raises(ValueError, match='public-only'):
        reconcile(d, rows)


def test_cost_components_are_explicit_and_energy_unknown_is_not_zero():
    d = design()
    rows = receipts(d)
    result = reconcile(d, rows)
    assert result['rows'][0]['costs']['energy_joules'] is None
    assert result['rows'][0]['costs']['energy_complete'] is False
    assert result['rows'][0]['costs']['known_energy_joules'] == 0
    rows[0]['costs'] = [c for c in rows[0]['costs'] if c['component'] != 'critic']
    with pytest.raises(ValueError, match='explicit predecision'):
        reconcile(d, rows)
    rows = receipts(d)
    rows[0]['costs'][0]['usd'] = -1
    with pytest.raises(ValueError, match='usd'):
        reconcile(d, rows)


def test_exact_development_dataset_and_eval_family_lock_are_required():
    d = design()
    dev = receipts(d, ('train', 'tune'))
    lock = policy_lock(d, dev, policy_sha256='b' * 64, freeze_commit='c' * 40)
    holdout = receipts(d, ('evaluation',))
    result = evaluation_rows(d, holdout, lock)
    assert result['assigned'] == len(holdout)
    with pytest.raises(ValueError, match='all assigned'):
        policy_lock(d, dev[:-1], policy_sha256='b' * 64, freeze_commit='c' * 40)
    bad = copy.deepcopy(lock)
    bad['development_families'].append(holdout[0]['family'])
    with pytest.raises(ValueError, match='family/assignment'):
        evaluation_rows(d, holdout, bad)
    with pytest.raises(ValueError, match='locked policy'):
        learner_rows(d, holdout, split='evaluation')
    with pytest.raises(ValueError, match='committed'):
        policy_lock(d, dev, policy_sha256='b' * 64, freeze_commit='uncommitted')


def test_complete_train_export_matches_existing_public_only_learner_schema():
    d = design()
    rows = receipts(d, ('train',))
    exported = learner_rows(d, rows, split='train')
    assert len(exported) == len(rows)
    assert all(set(e) == {'episode', 'family', 'steps', 'outcome'} for e in exported)
    assert all(set(step) == {'view', 'selection'} for e in exported for step in e['steps'])


def test_observed_quality_cannot_be_assigned_to_no_artifact_or_wrong_grade():
    d = design()
    rows = receipts(d)
    for termination in ('SERVICE_MISSING', 'UNATTEMPTED'):
        bad = copy.deepcopy(rows)
        bad[0].update(initial_sha256=None, final_sha256=None, steps=[], termination=termination,
                      costs=[cost('final', 'private_check')] +
                      ([cost('initial', 'receiver', calls=1)] if termination == 'SERVICE_MISSING' else []))
        bad[0]['outcome']['artifact_sha256'] = None
        with pytest.raises(ValueError, match='artifact-bound grade'):
            reconcile(d, bad)
    bad = copy.deepcopy(rows)
    bad[0]['outcome']['artifact_sha256'] = 'a' * 64
    with pytest.raises(ValueError, match='exact final artifact'):
        reconcile(d, bad)
    bad = copy.deepcopy(rows)
    bad[0]['outcome']['grade_receipt_sha256'] = None
    with pytest.raises(ValueError, match='artifact-bound grade'):
        reconcile(d, bad)
    assert d['incomplete_training_rule'] == 'abort-fit-on-any-incomplete-assignment'


def test_answer_artifact_hash_is_raw_utf8_and_cannot_hide_extraction():
    import hashlib
    content = 'print(3)\n'
    assert answer_sha256(content) == hashlib.sha256(content.encode()).hexdigest()
    assert answer_sha256(content) != sha256(content)
    assert design()['artifact_representation'] == 'raw-utf8-assistant-response-as-program'
