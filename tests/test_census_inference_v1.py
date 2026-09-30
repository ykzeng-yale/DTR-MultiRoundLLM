"""Exact deterministic cases; no Monte Carlo grid or real outcomes."""
import copy
from fractions import Fraction

import pytest

from experiments.prompt_choice import census_inference_v1 as census
from experiments.prompt_choice import paired_inference as paired


def plan(families=('a', 'b'), repeats=2):
    return dict(version=census.VERSION, scope=census.SCOPE, family_ids=list(families),
                replicates=repeats, alpha={'num': 1, 'den': 20},
                useful_gain={'num': 1, 'den': 20}, **{k: 'a'*64 for k in census.PIN_FIELDS})


def rows(p, bounds=(0, 0)):
    return [dict(family_id=f, replicate=r, initial_execution_id=f'{f}/{r}',
                 bounds={j: bounds for j in paired.CONTRASTS})
            for f in p['family_ids'] for r in range(p['replicates'])]


def exact(value): return Fraction(value['num'], value['den'])


def test_one_repeat_reduces_to_historical_family_arithmetic():
    p = plan(repeats=1); records = rows(p, (Fraction(1, 4), Fraction(1, 2)))
    new = census.analyze(p, records)
    old = paired.paired_contrasts([{'family_id': x['family_id'], 'bounds': x['bounds']}
                                   for x in records], Fraction(1, 20))
    assert new['intervals'] == old['intervals']
    assert new['n_families'] == 2 and new['n_assigned_execution_vectors'] == 2


def test_replication_precision_does_not_inflate_family_count():
    p = plan(repeats=12); res = census.analyze(p, rows(p))
    radius = paired.kl_interval(0, 24, Fraction(1, 20))[1]
    assert [exact(x) for x in res['intervals'][paired.CONTRASTS[0]]] == [-radius, radius]
    assert res['n_families'] == 2 and res['n_assigned_execution_vectors'] == 24
    assert res['scope'] == census.SCOPE and 'no inference beyond' in res['transport']


def test_missingness_retained_and_all_missing_uninformative():
    p = plan(); res = census.analyze(p, rows(p, (-1, 1)))
    assert all([exact(x) for x in v] == [-1, 1] for v in res['intervals'].values())
    records = rows(p)
    records.pop()
    with pytest.raises(ValueError, match='missing assigned'):
        census.analyze(p, records)


def test_duplicate_initial_execution_identity_refused():
    p = plan(); records = rows(p)
    records[1]['initial_execution_id'] = records[0]['initial_execution_id']
    with pytest.raises(ValueError, match='initial execution'):
        census.analyze(p, records)


@pytest.mark.parametrize('change', ['scope', 'hash', 'replicates', 'families', 'threshold', 'alpha'])
def test_target_and_census_pins_cannot_drift(change):
    p = plan(); records = rows(p)
    if change == 'scope': p['scope'] = 'broad-task-families'
    if change == 'hash': p['roster_sha256'] = 'oops'
    if change == 'replicates': p['replicates'] = True
    if change == 'families': p['family_ids'] = ['b', 'a']
    if change == 'threshold': p['useful_gain'] = {'num': 1, 'den': 100}
    if change == 'alpha': p['alpha'] = {'num': True, 'den': 20}
    with pytest.raises(ValueError): census.analyze(p, records)


@pytest.mark.parametrize('change', ['duplicate', 'outside', 'boolean', 'floating_bound'])
def test_assignment_and_exact_bound_guards(change):
    p = plan(); records = rows(p)
    if change == 'duplicate': records.append(copy.deepcopy(records[0]))
    if change == 'outside': records[0]['replicate'] = 99
    if change == 'boolean': records[0]['replicate'] = False
    if change == 'floating_bound': records[0]['bounds'][paired.CONTRASTS[0]] = (0.0, 0.5)
    with pytest.raises(ValueError): census.analyze(p, records)


def test_missing_envelope_contains_complete_data_interval():
    p = plan(); complete = rows(p, (Fraction(1, 3), Fraction(1, 3)))
    wide = copy.deepcopy(complete)
    wide[0]['bounds'] = {j: (-1, 1) for j in paired.CONTRASTS}
    tight = census.analyze(p, complete); outer = census.analyze(p, wide)
    for j in paired.CONTRASTS:
        a, b = map(exact, tight['intervals'][j]); l, u = map(exact, outer['intervals'][j])
        assert l <= a <= b <= u
