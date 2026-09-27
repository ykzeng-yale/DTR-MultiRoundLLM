from copy import deepcopy
import pytest
from scripts.build_bigcodebench_review_register import build, FIELDS, PIN


def fixture():
    rows = [{'row': i, 'task_id': f'BigCodeBench/{i}',
             'field_sha256': {k: f'{i}-{k}' for k in FIELDS}} for i in range(4)]
    inv = {'source_sha256': PIN, 'rows': rows, 'row_count': 4}
    item = {'task_id': rows[0]['task_id'], 'source_row': 0,
            'field_sha256': rows[0]['field_sha256'].copy(), 'admission': 'unresolved_not_admitted'}
    review = {'source_sha256': PIN, 'rows': [item], 'same_family_provisional_groups': [[0, 1], [1, 2]]}
    return inv, review


def test_missing_review_never_means_eligible_or_independent():
    inv, review = fixture()
    result = build(inv, [('review.json', review)])
    assert result['summary'] == dict(source_tasks=4, source_reviewed=1, source_review_pending=3,
                                     admitted_tasks=0, final_family_count=None, known_measurement_exposed_tasks=0)
    assert [c['task_ids'] for c in result['constraints']] == [['BigCodeBench/0','BigCodeBench/1'], ['BigCodeBench/1','BigCodeBench/2']]
    assert all(r['admission'] == 'unresolved_not_admitted' for r in result['rows'])


@pytest.mark.parametrize('change', ['source', 'hash', 'row', 'unknown', 'duplicate', 'admit'])
def test_stale_or_invalid_review_refused(change):
    inv, review = fixture()
    item = review['rows'][0]
    if change == 'source': review['source_sha256'] = 'wrong'
    elif change == 'hash': item['field_sha256']['test'] = 'wrong'
    elif change == 'row': item['source_row'] = 2
    elif change == 'unknown': item['task_id'] = 'BigCodeBench/99'
    elif change == 'duplicate': review['rows'].append(deepcopy(item))
    else: item['admission'] = 'admitted'
    with pytest.raises(ValueError): build(inv, [('bad', review)])


def test_only_full_four_field_duplicate_creates_exact_constraint():
    inv, _ = fixture()
    inv['rows'][1]['field_sha256']['canonical_solution'] = inv['rows'][0]['field_sha256']['canonical_solution']
    inv['rows'][3]['field_sha256'] = inv['rows'][2]['field_sha256'].copy()
    result = build(inv, [])
    assert result['constraints'] == [dict(task_ids=['BigCodeBench/2','BigCodeBench/3'],kind='exact_four_field_duplicate',evidence='inventory')]


def test_repeated_and_single_task_reviews_keep_provenance_without_double_count():
    inv, review = fixture()
    relation = dict(review['rows'][0], source_sha256=PIN, provisional_extended_group=[0,2])
    result = build(inv, [('batch', review), ('relation', relation)])
    assert result['summary']['source_reviewed'] == 1
    assert result['rows'][0]['source_review_evidence'] == ['batch','relation']
    assert result['constraints'][-1]['task_ids'] == ['BigCodeBench/0','BigCodeBench/2']


@pytest.mark.parametrize('members', [[0,99],[0,0],[0]])
def test_bad_family_constraints_refused(members):
    inv, review = fixture(); review['same_family_provisional_groups'] = [members]
    with pytest.raises(ValueError): build(inv, [('bad', review)])


def test_exposure_is_explicit_not_an_untouched_certificate():
    inv, review = fixture()
    exposure = dict(task_id='BigCodeBench/2', kind='measurement_development',
                    field_sha256=inv['rows'][2]['field_sha256'].copy(), evidence_sha256={'receipt':'hash'})
    result = build(inv, [('review', review)], [exposure])
    assert result['summary']['known_measurement_exposed_tasks'] == 1
    assert result['rows'][2]['known_exposures'] == [exposure]
    assert all(r['prior_development_crosswalk'] == 'pending' for r in result['rows'])
    exposure['field_sha256']['test'] = 'wrong'
    with pytest.raises(ValueError): build(inv, [], [exposure])


def test_cli_refuses_overwrite_and_changed_exposure_evidence(tmp_path, monkeypatch):
    import json
    from scripts.build_bigcodebench_review_register import main
    inv, review = fixture()
    paths = {name: tmp_path/name for name in ('inventory', 'review', 'exposures', 'out', 'receipt')}
    paths['inventory'].write_text(json.dumps(inv)); paths['review'].write_text(json.dumps(review))
    exposure = dict(task_id='BigCodeBench/2', kind='measurement_development',
                    field_sha256=inv['rows'][2]['field_sha256'],
                    evidence_sha256={str(paths['receipt']): 'wrong'})
    paths['exposures'].write_text(json.dumps([exposure])); paths['receipt'].write_text('changed')
    argv = ['register', '--inventory', str(paths['inventory']), '--reviews', str(paths['review']),
            '--exposures', str(paths['exposures']), '--out', str(paths['out'])]
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(ValueError, match='evidence mismatch'): main()
    assert not paths['out'].exists()
    paths['out'].write_text('preserve')
    with pytest.raises(ValueError, match='overwrite'): main()
    assert paths['out'].read_text() == 'preserve'
