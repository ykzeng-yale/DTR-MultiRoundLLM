"""Deterministic deployment-accounting fixtures, not actual policy runs."""
import copy
from fractions import Fraction

import pytest

from experiments.prompt_choice import census_inference_v1 as census
from experiments.prompt_choice.paired_inference import CONTRASTS
from experiments.sequential.direct_strategy_evaluation import (
    COMPONENTS, METRICS, census_bundle, make_design, reconcile,
)


def caps(calls=5):
    return {'calls': calls, 'input_tokens': 1000, 'completion_tokens': 1000,
            'elapsed_seconds': 100, 'usd': 0}


def design(shared_initial=True):
    strategies = [{'id': sid, 'kind': kind, 'source_sha256': str(i) * 64,
                   'artifact_sha256': str(i + 3) * 64, 'information_access_sha256': 'a' * 64,
                   'freeze_commit': 'b' * 40, 'development_manifest_sha256': 'c' * 64,
                   'fallback': 'last-valid-initial' if sid == 'DTR' else 'none', 'caps': caps()}
                  for i, (sid, kind) in enumerate((('DTR', 'learned'), ('STOP', 'fixed'), ('RESAMPLE', 'resampling')))]
    return make_design({'A': ['a1', 'a2'], 'B': ['b1']}, {'a1': 'a' * 64, 'a2': 'b' * 64, 'b1': 'c' * 64},
                       replicates=2, strategies=strategies, learned_id='DTR', baseline_ids=['STOP', 'RESAMPLE'],
                       versions={'receiver_sha256': 'd' * 64, 'observer_sha256': 'e' * 64,
                                 'endpoint_sha256': 'f' * 64, 'execution_law_sha256': '0' * 64},
                       choice_lock={'freeze_commit': 'b' * 40, 'development_manifest_sha256': 'c' * 64,
                                    'selected_on': 'development-only'},
                       common_caps=caps(), physical_caps=caps(200),
                       inference={'method': census.VERSION, 'alpha': {'num': 1, 'den': 20},
                                  'useful_gain': {'num': 1, 'den': 20}},
                       shared_initial=shared_initial)


def costs(identity, stages, receiver_stage=None):
    result = []
    for stage in stages:
        for c in COMPONENTS:
            calls = int(c == 'receiver' and stage == receiver_stage)
            result.append({'physical_id': f'{identity}/{stage}/{c}', 'stage': stage, 'component': c,
                           'calls': calls, 'input_tokens': 10 * calls, 'completion_tokens': 5 * calls,
                           'elapsed_seconds': 1 * calls, 'usd': 0, 'energy_joules': 0})
    return result


def data(d, missing=False):
    initials, rows, observations = [], [], []
    for e in d['initial_ledger']:
        initials.append(dict(e, config_sha256=d['config_sha256'], receiver_sha256=d['versions']['receiver_sha256'],
                             status='RETURNED', artifact_sha256='1' * 64,
                             costs=costs(e['initial_execution_id'], ('initial',), 'initial')))
        observations.append({'primitive_id': 'grade-' + e['initial_execution_id'],
                             'family_id': e['family_id'], 'root': e['root'], 'replicate': e['replicate'],
                             'artifact_sha256': '1' * 64, 'root_source_sha256': d['root_source_sha256'][e['root']],
                             'observer_sha256': d['versions']['observer_sha256'],
                             'endpoint_sha256': d['versions']['endpoint_sha256'],
                             'status': 'UNAVAILABLE' if missing else 'OBSERVED',
                             'reason': 'measurement unavailable' if missing else None,
                             'bounds': [0, 1] if missing else [1, 1]})
    by_id = {s['id']: s for s in d['strategies']}
    for e in d['ledger']:
        pid = 'grade-' + e['initial_execution_id']
        rows.append(dict(e, config_sha256=d['config_sha256'],
                         strategy_artifact_sha256=by_id[e['strategy_id']]['artifact_sha256'],
                         execution_status='COMPLETE', raw_artifact_sha256='1' * 64,
                         deployed_artifact_sha256='1' * 64, fallback_applied=False,
                         raw_primitive_id=pid, deployed_primitive_id=pid,
                         terminal_reason='STOP', terminal_stage=0,
                         retained_artifact_sha256='1' * 64, failure_reason=None,
                         costs=costs(e['assignment_id'], ('0', '1', 'final'))))
    return initials, rows, observations


def exact(value):
    return Fraction(value['num'], value['den'])


def replace_root_score(d, rows, obs, *, root, strategy, value):
    for row in rows:
        if row['root'] != root or row['strategy_id'] != strategy:
            continue
        artifact = '2' * 64
        pid = 'new-grade-' + row['assignment_id']
        row.update(terminal_reason='HORIZON', terminal_stage=1, raw_artifact_sha256=artifact,
                   deployed_artifact_sha256=artifact, retained_artifact_sha256=artifact,
                   raw_primitive_id=pid, deployed_primitive_id=pid)
        row['costs'] = costs(row['assignment_id'], ('0', '1', 'final'), '0')
        obs.append({'primitive_id': pid, 'family_id': row['family_id'], 'root': root,
                    'replicate': row['replicate'], 'artifact_sha256': artifact,
                    'root_source_sha256': d['root_source_sha256'][root],
                    'observer_sha256': d['versions']['observer_sha256'],
                    'endpoint_sha256': d['versions']['endpoint_sha256'],
                    'status': 'OBSERVED', 'reason': None, 'bounds': [value, value]})


def test_complete_balanced_family_root_strategy_ledger_and_fresh_starts():
    d = design()
    assert d == design()
    assert d['collection_released'] is False
    assert len(d['initial_ledger']) == 6
    assert len(d['ledger']) == 18
    assert len({e['initial_execution_id'] for e in d['initial_ledger']}) == 6
    for e in d['initial_ledger']:
        branch = [r for r in d['ledger'] if r['initial_execution_id'] == e['initial_execution_id']]
        assert len(branch) == 3
        assert len({(r['family_id'], r['root'], r['replicate']) for r in branch}) == 1
    independent = design(False)
    assert len(independent['initial_ledger']) == 18


def test_shared_missing_primitive_cancels_without_claiming_observed_quality():
    d = design()
    initial, rows, observations = data(d, missing=True)
    result = reconcile(d, initial, rows, observations)
    assert len(result['rows']) == 18
    assert all([exact(x) for x in r['deployed_quality']['bounds']] == [0, 1] for r in result['rows'])
    assert all(all([exact(x) for x in b] == [0, 0] for b in unit['bounds'].values()) for unit in result['census_rows'])
    assert result['n_families'] == 2 and result['replicates_per_family'] == 2


def test_equal_root_weighting_inside_family_not_flat_episode_weighting():
    d = design()
    initial, rows, obs = data(d)
    replace_root_score(d, rows, obs, root='a1', strategy='DTR', value=0)
    result = reconcile(d, initial, rows, obs)
    a_rows = [r for r in result['census_rows'] if r['family_id'] == 'A']
    assert all(all([exact(x) for x in b] == [Fraction(-1, 2)] * 2 for b in r['bounds'].values()) for r in a_rows)
    assert all(all([exact(x) for x in b] == [0, 0] for b in r['bounds'].values())
               for r in result['census_rows'] if r['family_id'] == 'B')


def test_unknown_artifact_has_wide_bounds_and_cannot_alias_shared_initial_grade():
    d = design()
    initial, rows, obs = data(d)
    failed = next(r for r in rows if r['strategy_id'] == 'RESAMPLE')
    failed.update(execution_status='UNATTEMPTED', terminal_reason='UNATTEMPTED', terminal_stage=None,
                  raw_artifact_sha256=None, deployed_artifact_sha256=None, retained_artifact_sha256=None,
                  raw_primitive_id=None, deployed_primitive_id=None, failure_reason='run cap')
    result = reconcile(d, initial, rows, obs)
    unit = next(r for r in result['census_rows'] if r['family_id'] == failed['family_id'] and r['replicate'] == failed['replicate'])
    assert [exact(x) for x in unit['bounds'][CONTRASTS[1]]] == [0, Fraction(1, 2)]
    failed['deployed_primitive_id'] = rows[0]['deployed_primitive_id']
    with pytest.raises(ValueError, match='fallback'):
        reconcile(d, initial, rows, obs)


def test_failure_fallback_is_explicit_preserves_initial_and_raw_missingness():
    d = design()
    initial, rows, obs = data(d)
    failed = next(r for r in rows if r['strategy_id'] == 'DTR')
    failed.update(execution_status='SERVICE_MISSING', terminal_reason='SERVICE_MISSING', terminal_stage=0,
                  raw_artifact_sha256=None, raw_primitive_id=None, fallback_applied=True,
                  failure_reason='receiver timeout')
    failed['costs'] = costs(failed['assignment_id'], ('0', '1', 'final'), '0')
    result = reconcile(d, initial, rows, obs)
    row = next(r for r in result['rows'] if r['assignment_id'] == failed['assignment_id'])
    assert row['fallback_applied']
    assert [exact(x) for x in row['raw_quality']['bounds']] == [0, 1]
    assert [exact(x) for x in row['deployed_quality']['bounds']] == [1, 1]
    failed['deployed_artifact_sha256'] = '2' * 64
    with pytest.raises(ValueError, match='preserve'):
        reconcile(d, initial, rows, obs)


@pytest.mark.parametrize('change', ['artifact', 'source', 'observer', 'endpoint', 'root', 'replicate'])
def test_false_shared_primitive_alias_is_refused(change):
    d = design()
    initial, rows, obs = data(d)
    names = {'artifact': 'artifact_sha256', 'source': 'root_source_sha256',
             'observer': 'observer_sha256', 'endpoint': 'endpoint_sha256',
             'root': 'root', 'replicate': 'replicate'}
    key = names[change]
    obs[0][key] = 999 if change == 'replicate' else 'different-root' if change == 'root' else '9' * 64
    with pytest.raises(ValueError, match='alias'):
        reconcile(d, initial, rows, obs)


def test_all_assignment_rows_and_physical_event_identities_are_required():
    d = design()
    initial, rows, obs = data(d)
    with pytest.raises(ValueError, match='all assigned'):
        reconcile(d, initial, rows[:-1], obs)
    bad = copy.deepcopy(rows)
    bad[-1] = copy.deepcopy(bad[0])
    with pytest.raises(ValueError, match='duplicate'):
        reconcile(d, initial, bad, obs)
    bad = copy.deepcopy(rows)
    bad[1]['costs'][0]['physical_id'] = bad[0]['costs'][0]['physical_id']
    with pytest.raises(ValueError, match='physical operation reused'):
        reconcile(d, initial, bad, obs)


def test_initial_cost_is_logical_for_each_policy_and_physical_once():
    d = design()
    result = reconcile(d, *data(d))
    assert exact(result['physical_costs']['calls']) == 6
    assert sum(exact(r['logical_costs']['calls']) for r in result['rows']) == 18
    assert result['physical_caps_verified'] and result['all_logical_caps_verified']
    assert result['complete_cost_telemetry']
    assert not result['cost_benefit_claim_permitted']


def test_missing_telemetry_is_unknown_not_zero_and_definite_excess_still_refuses():
    d = design()
    initial, rows, obs = data(d)
    initial[0]['costs'][0]['completion_tokens'] = None
    result = reconcile(d, initial, rows, obs)
    assert result['physical_costs']['completion_tokens'] is None
    assert not result['physical_caps_verified']
    assert not result['complete_cost_telemetry']
    rows[0]['costs'][-1]['completion_tokens'] = 1001
    with pytest.raises(ValueError, match='known deployment cost'):
        reconcile(d, initial, rows, obs)


def test_stop_and_terminal_horizon_refuse_later_operations_or_calls():
    d = design()
    initial, rows, obs = data(d)
    event = next(c for c in rows[0]['costs'] if c['stage'] == '1' and c['component'] == 'selection')
    event['elapsed_seconds'] = 1
    with pytest.raises(ValueError, match='absorbing termination'):
        reconcile(d, initial, rows, obs)
    initial, rows, obs = data(d)
    event = next(c for c in rows[0]['costs'] if c['stage'] == '0' and c['component'] == 'receiver')
    event['calls'] = 1
    with pytest.raises(ValueError, match='after STOP'):
        reconcile(d, initial, rows, obs)


def test_baseline_choice_information_and_prospective_lock_cannot_drift():
    d = design()
    initial, rows, obs = data(d)
    d['baseline_ids'].reverse()
    with pytest.raises(ValueError, match='hash drift'):
        reconcile(d, initial, rows, obs)
    d = design()
    d['strategies'][0]['artifact_sha256'] = '9' * 64
    with pytest.raises(ValueError, match='hash drift'):
        reconcile(d, initial, rows, obs)


def test_census_adapter_uses_exact_whole_vector_contrasts_without_inflating_families():
    d = design()
    result = reconcile(d, *data(d, missing=True))
    bundle = census_bundle(d, result, alpha=Fraction(1, 20))
    inference = census.analyze(bundle['plan'], bundle['rows'])
    assert inference['n_families'] == 2
    assert inference['n_assigned_execution_vectors'] == 4
    assert inference['useful_gain'] == {'num': 1, 'den': 20}
    assert inference['scope'] == 'conditional-finite-family-census'
    result['census_rows'][0]['bounds'][CONTRASTS[0]] = [0, 1]
    with pytest.raises(ValueError, match='accounting drift'):
        census_bundle(d, result, alpha=Fraction(1, 20))


def test_float_boolean_grades_and_missing_cost_events_are_refused():
    d = design()
    initial, rows, obs = data(d)
    for bad in ([0., 1.], [False, True]):
        malformed = copy.deepcopy(obs)
        malformed[0]['bounds'] = bad
        with pytest.raises(ValueError, match='exact rational'):
            reconcile(d, initial, rows, malformed)
    rows[0]['costs'].pop()
    with pytest.raises(ValueError, match='missing explicit cost'):
        reconcile(d, initial, rows, obs)


def test_private_grading_is_after_termination_and_never_a_deployment_cost():
    d = design()
    initial, rows, obs = data(d)
    final = next(e for e in rows[0]['costs'] if e['stage'] == 'final' and e['component'] == 'privatecheck')
    final['elapsed_seconds'] = 7
    result = reconcile(d, initial, rows, obs)
    assert exact(result['physical_private_measurement_costs']['elapsed_seconds']) == 7
    assert exact(result['physical_costs']['elapsed_seconds']) == 13
    assert exact(result['rows'][0]['logical_costs']['elapsed_seconds']) == 1
    for missing in (1, None):
        initial, rows, obs = data(d)
        early = next(e for e in initial[0]['costs'] if e['component'] == 'privatecheck')
        early['elapsed_seconds'] = missing
        with pytest.raises(ValueError, match='private grading is forbidden'):
            reconcile(d, initial, rows, obs)


def test_alpha_and_usefulness_are_prospectively_pinned_in_the_direct_design():
    d = design()
    result = reconcile(d, *data(d))
    assert census_bundle(d, result)['plan']['alpha'] == {'num': 1, 'den': 20}
    with pytest.raises(ValueError, match='pinned alpha'):
        census_bundle(d, result, alpha=Fraction(1, 100))
    for name, value in (('alpha', {'num': 1, 'den': 10}), ('useful_gain', {'num': 1, 'den': 100})):
        changed = copy.deepcopy(d)
        changed['inference'][name] = value
        with pytest.raises(ValueError, match='hash drift'):
            reconcile(changed, *data(d))
