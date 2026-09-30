"""Pure public-data schema/semantic-flag checks; no benchmark execution."""
import json

import pytest

from scripts import triage_lcb_stdio_contracts_20260930 as triage


def row(statement='Print the uniquely specified integer.', *, starter='', cases=None, identity='example'):
    if cases is None:
        cases = [{'input': 'synthetic input', 'output': 'synthetic output', 'testtype': 'stdin'}]
    return dict(contest_date='synthetic date', contest_id='synthetic provenance', difficulty='synthetic',
                platform='synthetic', public_test_cases=json.dumps(cases), question_content=statement,
                question_id=identity, question_title='synthetic title', starter_code=starter)


def test_all_dispositions_retained_without_admission():
    rows = triage.triage_rows([row(), row(starter='class Placeholder: pass', identity='functional')])
    assert len(rows) == 2 and not any(item['admitted'] for item in rows)
    assert rows[0]['disposition'] == 'unreviewed_contract'
    assert rows[1]['disposition'] == 'outside_proposed_stdio_interface'
    assert all('question_content' not in item and 'public_test_cases' not in item for item in rows)


@pytest.mark.parametrize('text,flag', [
    ('An interactive judge supplies the next response.', 'interactive_language'),
    ('Output any valid construction.', 'multivalued_output_language'),
    ('Several solutions are permitted.', 'multivalued_output_language'),
    ('The relative or absolute error must meet the stated limit.', 'numeric_tolerance_language'),
    ('The judge is case-insensitive.', 'case_equivalence_language'),
    ('Print such a placement.', 'constructive_output_language'),
])
def test_uniform_language_flags_are_candidates_only(text, flag):
    item = triage.triage_rows([row(text)])[0]
    assert flag in item['review_candidate_flags']
    assert item['disposition'] == 'unreviewed_contract' and not item['admitted']
    assert item['statement_match_character_spans'][flag]


def test_order_language_does_not_automatically_exclude_task():
    item = triage.triage_rows([row('Operations may be performed in any order; print their minimum count.')])[0]
    assert 'multivalued_output_language' in item['review_candidate_flags']
    assert item['disposition'] == 'unreviewed_contract'


@pytest.mark.parametrize('cases,flag', [
    ([], 'empty_public_cases'),
    ([{'input': 7, 'output': 'x', 'testtype': 'stdin'}], 'non_string_stdin'),
    ([{'input': 'x', 'output': ['x'], 'testtype': 'stdin'}], 'non_string_expected_output'),
    ([{'input': 'x', 'output': 'x', 'testtype': 'functional'}], 'class_functional_interface_mismatch'),
    ([{'input': 'x', 'output': 'x'}], 'malformed_public_case_shape'),
])
def test_case_contract_defects_survive_as_flags(cases, flag):
    item = triage.triage_rows([row(cases=cases)])[0]
    assert flag in item['review_candidate_flags'] and not item['admitted']


@pytest.mark.parametrize('blob', ['not JSON', '{}', '[{"input":"x","input":"y"}]', '[NaN]'])
def test_json_is_strict_inert_and_never_eval(blob):
    info, flags = triage.public_case_structure(blob)
    assert info['count'] is None and flags == ['malformed_public_case_json']


def test_private_field_and_duplicate_identity_refused():
    private = row(); private['private_test_cases'] = 'not accessed'
    with pytest.raises(ValueError, match='public-only'):
        triage.triage_rows([private])
    with pytest.raises(ValueError, match='duplicate'):
        triage.triage_rows([row(), row()])


def test_source_projection_drift_refused_before_review():
    with pytest.raises(ValueError, match='exact bounded public projection'):
        triage.feasibility(b'[]', b'{}')


def test_limited_source_review_never_equals_admission():
    item = triage.triage_rows([row('Output any construction.', identity='abc350_c')])[0]
    triage._review(item)
    assert item['disposition'] == 'source_backed_comparator_hold'
    assert not item['admitted'] and not item['source_backed_limited_review']['independent_semantic_validation']


def test_bound_complete_actual_source_when_available():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    source = root / 'work/lcb_public_inquiry_20260930_v1/public-rows.jsonl'
    inventory = root / 'work/lcb_public_inquiry_20260930_v1/sanitized-inventory.json'
    if not source.exists() or not inventory.exists():
        pytest.skip('ignored public source not present')
    result = triage.feasibility(source.read_bytes(), inventory.read_bytes())
    assert result['source']['canonical_records_sha256'] == '725c558e1b1bbdb91d7a6550d05d019112a626cd25b982924a6436a619811d8c'
    assert result['counts']['dispositions'] == {'outside_proposed_stdio_interface':444, 'source_backed_comparator_hold':38, 'unreviewed_contract':573}
