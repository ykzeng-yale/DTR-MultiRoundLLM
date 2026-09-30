"""Deterministic metadata/interval fixtures only; no RNG, fit or code execution."""
import copy
from fractions import Fraction

import pytest

from experiments.sprint import learner_v1 as learner
from experiments.sprint import pipeline_v1 as pipeline
from experiments.sprint_analysis import inference_v1 as inference


def model(mode):
    coefficients = [[[0]*learner.DIM for _ in range(3)] for _ in range(2)]
    for stage in coefficients:
        stage[1][0] = 1
    return {'version': learner.VERSION, 'mode': mode, 'versions': ['a'*64]*3,
            'training_families': ['train-family'], 'coefficients': coefficients}


@pytest.fixture(scope='module')
def fixture():
    tasks = [{'root': f'root-{i:03d}', 'family_id': f'family-{i:03d}',
        'root_source_sha256': 'a'*64, 'prompt': 'fixed synthetic public task',
        'public_instrument': 'synthetic-sealed-public-reference', 'split': 'eval'}
        for i in range(inference.COMPONENTS)]
    tasks.append(dict(tasks[0], root='root-000b'))
    tasks.extend([dict(tasks[0], root='train-root', family_id='train-family', split='train'),
                  dict(tasks[0], root='tune-root', family_id='tune-family', split='tune')])
    units, _ = pipeline.randomization_roster(tasks, 'evaluation', inference.REPLICATES)
    table = {'version': 'sprint-independent-vector-randomization-v1', 'mode': 'evaluation',
        'component_replicate_nonces': [dict(u, nonce_hex=f'{i:032x}') for i, u in enumerate(units)],
        'development_action_coins': []}
    models = {sid: model(mode) for sid, mode in
              (('FULL_HISTORY_Q', 'full'), ('COMPRESSED_HISTORY_Q', 'compressed'))}
    config = pipeline.make_config(tasks, mode='evaluation', repeats=inference.REPLICATES,
        seed=917, pins={k: 'a'*64 for k in ('receiver', 'generator', 'public_observer',
                    'private_observer', 'source_roster', 'extractor')},
        strategies=list(inference.STRATEGIES),
        model_sha256s={k: learner.artifact_sha256(v) for k, v in models.items()},
        selected_b1='STOP', choice_lock_sha256='b'*64, randomization=table)
    task_map = {t['root']: t for t in tasks}
    rows, labels = [], []
    for assignment in config['ledger']:
        learned = assignment['strategy'] in ('FULL_HISTORY_Q', 'COMPRESSED_HISTORY_Q')
        raw = 'print(1)' if learned else 'print(0)'
        row = dict(assignment, base_messages=pipeline.base_messages(task_map[assignment['root']]),
            final_raw=raw, final_program=raw, disposition='HORIZON' if learned else 'STOP',
            calls=[], fallback_applied=False)
        grade = {'status': 'OBSERVED', 'value': int(learned), 'reason': None,
            'audit_sha256': pipeline.sha([assignment['initial_execution_id'], raw]),
            'primitive_id': pipeline.primitive_id('private', assignment['initial_execution_id'],
                           assignment['root'], pipeline.text_sha(raw), 'a'*64),
            'elapsed_seconds': .001, 'case_starts': 1}
        label = {'assignment_id': row['assignment_id'], 'grading_unit_id': row['initial_execution_id'],
            'root': row['root'], 'family_id': row['family_id'], 'config_sha256': config['config_sha256'],
            'raw_sha256': pipeline.text_sha(raw), 'program_sha256': pipeline.text_sha(raw),
            'extractor': pipeline.EXTRACTOR, 'instrument_sha256': config['pins']['private_observer'],
            'administrative_censoring_reason': None, 'grade': grade}
        rows.append(row); labels.append(label)
    state = {'config_sha256': config['config_sha256'], 'phase': 3, 'requests': [],
             'rows': rows, 'models': models}
    joined = {'config_sha256': config['config_sha256'], 'state_sha256': pipeline.sha(state), 'labels': labels}
    conditioning = {'nonrandom_protocol_sha256': 'c'*64, 'development_info_sha256': 'd'*64,
        'tuning_info_sha256': 'e'*64, 'policies_lock_sha256': inference.policy_lock(config)}
    plan = inference.make_plan(config, tasks, conditioning=conditioning)
    return plan, state, joined, config, tasks


def decode(value):
    return Fraction(value['num'], value['den'])


def test_all_assigned_vectors_and_exact_two_root_component_averages(fixture):
    plan, state, joined, config, tasks = fixture
    result = inference.reconcile(plan, state, joined, config, tasks)
    assert result['components'] == 110 and result['replicates'] == 32
    assert result['vectors'] == 3520 and result['roots'] == 111
    assert result['assigned'] == 111*32*9
    first = result['exact_vectors'][0]
    assert len(first['root_initial_execution_ids']) == 2
    assert first['vector_id'] == 'vector-'+pipeline.sha(first['root_initial_execution_ids'])
    assert all(decode(x) == 1 for x in first['bounds']['d_minus_b1'])
    assert all(decode(x) == 0 for x in result['secondary_descriptive'][0]['full_minus_compressed'])


def test_administrative_fallback_is_observed_actual_but_unknown_intended(fixture):
    plan, original, original_join, config, tasks = fixture
    state, joined = copy.deepcopy(original), copy.deepcopy(original_join)
    index = next(i for i, r in enumerate(state['rows']) if r['root']=='root-000' and
                 r['replicate']==0 and r['strategy']=='FULL_HISTORY_Q')
    state['rows'][index].update(disposition='RESOURCE_TERMINAL', censoring_reason='global_wall_cap', fallback_applied=True)
    joined['labels'][index]['administrative_censoring_reason'] = 'global_wall_cap'
    joined['state_sha256'] = pipeline.sha(state)
    result = inference.reconcile(plan, state, joined, config, tasks)
    first = result['exact_vectors'][0]
    assert list(map(decode, first['bounds']['d_minus_b1'])) == [Fraction(1,2), Fraction(1)]
    assert result['counts']['FULL_HISTORY_Q']['administrative_terminal'] == 1
    assert list(map(decode, result['actual_artifact_quality_envelopes']['FULL_HISTORY_Q'])) == [1,1]
    assert decode(result['intended_quality_envelopes']['FULL_HISTORY_Q'][0]) == 1-Fraction(1,7040)


def test_conflicting_shared_primitive_refused_and_assignment_loss_never_dropped(fixture):
    plan, state, original_join, config, tasks = fixture
    joined = copy.deepcopy(original_join)
    label = next(r for r in joined['labels'] if r['program_sha256']==pipeline.text_sha('print(1)'))
    label['grade']['value'] = 0
    with pytest.raises(ValueError, match='contradiction'):
        inference.reconcile(plan, state, joined, config, tasks)
    joined = dict(original_join, labels=original_join['labels'][:-1])
    with pytest.raises(ValueError, match='every assigned'):
        inference.reconcile(plan, state, joined, config, tasks)


def test_changed_primitive_scope_and_evaluation_family_fit_are_refused(fixture):
    plan, original, original_join, config, tasks = fixture
    joined = copy.deepcopy(original_join)
    joined['labels'][0]['instrument_sha256'] = 'f'*64
    with pytest.raises(ValueError, match='binding drift'):
        inference.reconcile(plan, original, joined, config, tasks)
    state = copy.deepcopy(original)
    state['models']['FULL_HISTORY_Q']['training_families'].append('family-000')
    # Locking an altered artifact after evaluation still cannot make it the
    # original model; neither a changed hash nor metadata grants release.
    joined = dict(original_join, state_sha256=pipeline.sha(state))
    with pytest.raises(ValueError, match='model artifact'):
        inference.reconcile(plan, state, joined, config, tasks)


def test_F_excludes_realized_evaluation_draws_and_hashes(fixture):
    plan, _, _, config, _ = fixture
    changed = copy.deepcopy(config)
    changed['randomization']['component_replicate_nonces'][0]['nonce_hex'] = 'f'*32
    changed['randomization_sha256'] = pipeline.sha(changed['randomization'])
    changed['initials'][0]['seed'] = 123
    changed['ledger'][0]['seeds'] = [456,789]
    changed['config_sha256'] = '0'*64
    assert inference.nonrandom_law(config) == inference.nonrandom_law(changed)
    assert 'evaluation assignment/randomization-table hashes' in plan['conditioning_excludes']


def test_primary_criteria_use_existing_outward_interval_and_are_frozen(fixture):
    plan, state, joined, config, tasks = fixture
    result = inference.analyze(plan, state, joined, config, tasks)
    assert result['decision']['scoped_verdict'] == 'GO_QUALITY'
    assert result['inference']['n_families'] == 110
    assert result['inference']['n_assigned_execution_vectors'] == 3520
    assert result['inference']['alpha'] == {'num':1,'den':20}
    assert result['no_optional_stopping'] and result['no_best_arm_selection']
    changed = copy.deepcopy(plan); changed['census_plan']['alpha'] = {'num':1,'den':10}
    with pytest.raises(ValueError, match='inference/source'):
        inference.reconcile(changed, state, joined, config, tasks)
