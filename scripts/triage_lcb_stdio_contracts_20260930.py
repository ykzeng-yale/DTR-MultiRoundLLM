"""Outcome-blind public-source feasibility for the proposed LCB-STDIO-v1 scope.

Only inert JSON public records are read. No source loader, private column, task
code, reference, receiver or generated candidate is executed. Pattern matches
are review candidates, never admission or a prevalence estimate. The limited
source-backed decisions below are tied to one exact public projection.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


VERSION = 'lcb-stdio-source-feasibility-v1'
SOURCE_REVISION = '25d8cb8f0db2efe1b589941eb8c26a219850d4d2'
PROJECTION_SHA256 = '7c68dc8d401c25acbbfcf57e83de4f540107c9623535a515cfc236586c0df1db'
PUBLIC_FIELDS = frozenset(('contest_date', 'contest_id', 'difficulty', 'platform',
                          'public_test_cases', 'question_content', 'question_id',
                          'question_title', 'starter_code'))
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_CASE_JSON_BYTES = 2 * 1024 * 1024
PATTERNS = {
    'interactive_language': r'\binteractiv\w*\b|\binteractor\b|\bflush(?:ing)?\b',
    'multivalued_output_language': (
        r'\b(?:print|output|return|printing)\s+(?:any|one\s+of)\b|'
        r'\bany\s+(?:one\s+)?of\s+them\b|\bany\s+output\b|'
        r'\bother\s+outputs\b|\bin\s+any\s+order\b|'
        r'\b(?:multiple|several)\s+(?:(?:valid|correct)\s+)?'
        r'(?:answers|solutions|ways|reading\s+orders|sequences)\b'),
    'numeric_tolerance_language': (
        r'\b(?:absolute|relative)\s+(?:or\s+(?:absolute|relative)\s+)?error\b|'
        r'\b(?:decimal\s+places|floating[- ]point|precision|tolerance)\b'),
    'case_equivalence_language': r'\bcase[- ]insensitive\b|\bany\s+case\b|\bcase\s+does\s+not\s+matter\b',
    'constructive_output_language': (
        r'\bprint\s+(?:(?:one\s+)?such(?:\s+(?:a|an))?|one|a|an)\s+'
        r'(?:(?:valid|good|integer)\s+)?'
        r'(?:string|solution|construction|placement|way|sequence|permutation|matrix|grid|pair|triple|arrangement)\b'),
}

# These are limited semantic rulings from statement review, not eligibility.
# All other contract axes (cases, bounds, implementation, families) remain open.
INTERACTIVE_HOLDS = {'abc337_e', 'abc355_e'}
MULTIVALUED_HOLDS = {
    'abc311_c', 'abc315_e', 'abc326_d', 'abc333_e', 'abc343_a', 'abc343_e',
    'abc350_c', 'abc362_c', 'abc366_g', 'abc373_g', 'arc181_c', 'arc183_d',
    'arc185_c', 'abc396_e', 'abc397_d', 'arc190_a', 'arc191_c',
    'abc335_d', 'abc363_f', 'arc188_c', 'arc195_c',
}
TOLERANCE_HOLDS = {
    'abc314_e', 'abc315_f', 'abc319_c', 'abc324_f', 'abc327_e', 'abc350_e',
    'abc374_d', 'abc375_b', 'abc385_f', 'abc392_d',
}
CASE_HOLDS = {'1873_A', '1883_B', 'abc395_a', 'arc192_a', 'arc192_b'}
OPERATION_ORDER_CLEARS = {
    '1883_C', 'abc303_d', 'abc323_d', 'abc364_c', 'abc364_e', 'abc369_e',
    'abc377_g', 'arc188_a', 'abc396_g', 'abc399_d', 'abc400_d', 'arc191_d',
    'arc194_e', 'arc195_b', 'arc195_d',
}
FIXED_STRING_CLEARS = {'abc319_b', 'abc341_a', 'abc348_a', 'abc382_b'}
OTHER_CLEARS = {'abc329_c', 'abc327_b', 'abc398_f', 'abc314_a'} | FIXED_STRING_CLEARS


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON member')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('nonfinite JSON constant')


def public_case_structure(blob):
    """Strict data-only JSON parsing; malformed records survive as flags."""
    flags = []
    if type(blob) is not str or len(blob.encode()) > MAX_CASE_JSON_BYTES:
        return {'count': None, 'stdin_cases': 0}, ['malformed_public_case_json']
    try:
        cases = json.loads(blob, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, TypeError, RecursionError):
        return {'count': None, 'stdin_cases': 0}, ['malformed_public_case_json']
    if type(cases) is not list:
        return {'count': None, 'stdin_cases': 0}, ['malformed_public_case_json']
    if not cases:
        flags.append('empty_public_cases')
    stdin = 0
    for case in cases:
        if type(case) is not dict or set(case) != {'input', 'output', 'testtype'}:
            flags.append('malformed_public_case_shape')
            continue
        if type(case['input']) is not str:
            flags.append('non_string_stdin')
        if type(case['output']) is not str:
            flags.append('non_string_expected_output')
        if case['testtype'] != 'stdin':
            flags.append('class_functional_interface_mismatch')
        else:
            stdin += 1
    return {'count': len(cases), 'stdin_cases': stdin}, sorted(set(flags))


def triage_rows(rows):
    """Retain all rows; flags do not confer or revoke task admission."""
    if type(rows) is not list:
        raise ValueError('public row list required')
    result, seen = [], set()
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != PUBLIC_FIELDS:
            raise ValueError('exact public-only schema required; private columns refused')
        if any(type(row[key]) is not str for key in PUBLIC_FIELDS):
            raise ValueError('projected source fields must be strings')
        identity = (row['platform'], row['question_id'])
        if identity in seen:
            raise ValueError('duplicate source identity')
        seen.add(identity)
        empty_starter = not row['starter_code'].strip()
        case_info, flags = public_case_structure(row['public_test_cases'])
        matches = {}
        if empty_starter:
            for name, pattern in PATTERNS.items():
                spans = [[match.start(), match.end()] for match in
                         re.finditer(pattern, row['question_content'], re.IGNORECASE)]
                if spans:
                    flags.append(name)
                    matches[name] = spans
        else:
            flags.append('nonempty_starter_outside_proposed_stdio_interface')
        result.append({
            'source_row': index, 'platform': identity[0], 'question_id': identity[1],
            'empty_starter': empty_starter, 'public_row_sha256': sha256(json_bytes(row)),
            'statement_sha256': sha256(row['question_content'].encode()),
            'public_cases_sha256': sha256(row['public_test_cases'].encode()),
            'starter_sha256': sha256(row['starter_code'].encode()),
            'public_case_structure': case_info, 'review_candidate_flags': sorted(set(flags)),
            'statement_match_character_spans': matches,
            'disposition': 'unreviewed_contract' if empty_starter else 'outside_proposed_stdio_interface',
            'admitted': False,
        })
    return result


def _review(row):
    qid = row['question_id']
    holds, clears = [], []
    if qid in INTERACTIVE_HOLDS:
        holds.append('interactive_judge_dialogue_not_fixed_stdin_output')
    if qid in MULTIVALUED_HOLDS:
        holds.append('valid_constructions_require_semantic_checker_not_one_expected_token_sequence')
    if qid in TOLERANCE_HOLDS:
        holds.append('source_numeric_tolerance_not_exact_token_equality')
    if qid in CASE_HOLDS:
        holds.append('source_case_equivalence_not_case_sensitive_token_equality')
    if qid == 'abc350_c':
        holds.append('public_case_projection_empty_despite_statement_sample_sections')
    if qid in OPERATION_ORDER_CLEARS:
        clears.append('order_phrase_describes_allowed_operations_not_output_equivalence')
    if qid == 'abc329_c':
        clears.append('multiple_ways_phrase_describes_counted_occurrences_not_alternative_output')
    if qid == 'abc314_a':
        clears.append('decimal_places_are_exact_truncation_with_fixed_trailing_digits_not_tolerance')
    if qid == 'abc327_b':
        clears.append('positive_integer_power_a_to_a_is_strictly_increasing_so_answer_is_unique')
    if qid == 'abc398_f':
        clears.append('shortest_palindrome_completion_of_fixed_prefix_is_unique_by_mirror_constraints')
    if qid in FIXED_STRING_CLEARS:
        clears.append('print_string_language_has_explicitly_determined_characters_not_free_construction')
    row['source_backed_limited_review'] = {'holds': holds, 'cleared_flags_only': clears,
                                          'independent_semantic_validation': False}
    if holds:
        row['disposition'] = 'source_backed_comparator_hold'
    return row


def feasibility(raw, inventory_raw):
    """Bind actual bytes and existing inventory before applying fixed reviews."""
    if len(raw) > MAX_SOURCE_BYTES or sha256(raw) != PROJECTION_SHA256:
        raise ValueError('exact bounded public projection required')
    rows = [json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
            for line in raw.decode().splitlines() if line.strip()]
    inventory = json.loads(inventory_raw)
    if len(rows) != 1055 or inventory['actual_rows'] != 1055 or len(inventory['rows']) != 1055:
        raise ValueError('complete 1055-row source/inventory required')
    ledger = triage_rows(rows)
    for actual, frozen in zip(ledger, inventory['rows']):
        if (actual['source_row'], actual['platform'], actual['question_id'], actual['public_row_sha256']) != (
                frozen['source_row'], frozen['platform'], frozen['question_id'], frozen['public_row_sha256']):
            raise ValueError('public source/inventory identity or hash drift')
    for row in ledger:
        if row['empty_starter']:
            _review(row)
    stdio = [row for row in ledger if row['empty_starter']]
    reviewed_ids = (INTERACTIVE_HOLDS | MULTIVALUED_HOLDS | TOLERANCE_HOLDS | CASE_HOLDS |
                    OPERATION_ORDER_CLEARS | OTHER_CLEARS)
    if {row['question_id'] for row in stdio if row['review_candidate_flags']} != reviewed_ids:
        raise ValueError('fixed limited review must reconcile every flagged stdio statement')
    return {
        'version': VERSION, 'scope': 'LCB-STDIO-v1 proposed source feasibility only',
        'source': {'repository': 'livecodebench/code_generation_lite', 'revision': SOURCE_REVISION,
                   'config': 'release_v6', 'public_projection_sha256': sha256(raw),
                   'public_projection_bytes': len(raw),
                   'public_projection_serialization': 'UTF-8 canonical JSONL including newline per row',
                   'canonical_records_sha256': sha256(json_bytes(rows)),
                   'inventory_sha256': sha256(inventory_raw)},
        'counts': {'all_source_rows': len(ledger), 'empty_starter_candidates': len(stdio),
                   'nonempty_starter_outside_scope': len(ledger) - len(stdio),
                   'nonempty_public_stdin_case_rows': sum(row['public_case_structure']['stdin_cases'] > 0 for row in stdio),
                   'empty_public_case_rows': sum(row['public_case_structure']['count'] == 0 for row in stdio),
                   'dispositions': dict(sorted(Counter(row['disposition'] for row in ledger).items())),
                   'stdio_regex_or_structure_review_candidates': sum(bool(row['review_candidate_flags']) for row in stdio),
                   'stdio_review_candidate_flags': dict(sorted(Counter(flag for row in stdio for flag in row['review_candidate_flags']).items())),
                   'admitted': 0, 'verified_semantic_families': 0},
        'scope_decision': {
            'status': 'plausible_narrow_scope_pending_uniform_contract_and_instrument_review',
            'rule': 'deterministic noninteractive stdin tasks with uniquely specified output token sequence and source-faithful comparison; no source semantic rewrite',
            'holds_are_not_dropped': True,
            'unflagged_and_flag_cleared_rows_remain_unreviewed': True,
            'regex_counts_are_not_semantic_prevalence_estimates': True,
            'negative_findings': [
                'empty starter and stdin-labelled sample cases do not imply noninteractive or exact-output semantics',
                'a universal case-sensitive token comparator rejects outputs expressly permitted by some source contracts',
                'one expected sample output cannot grade allowed constructions or tolerance-valued answers',
                'construction tasks can lack any-output wording; full output-section review found additional source-backed holds',
                'empty machine-readable public cases do not prove that the statement has no samples',
                'any-solution wording does not prove multiple outputs when the declared domain mathematically determines a unique result',
            ],
            'cleared_uniqueness_reasoning': {
                'abc327_b': 'For positive integers a<b, a^a <= b^a < b^b; thus at most one positive integer satisfies the source equation.',
                'abc398_f': 'A palindrome extending a length-n prefix exists with length at most2n-1. At any such length every appended position mirrors a fixed prefix position, so the minimum-length completion is unique.',
            },
        },
        'next_release_gates': [
            'Uniformly review all611 candidate contracts and source errata without receiver outcomes; confirm input/output domain and exact tokenization, case and formatting requirements; retain every hold.',
            'Private_test_cases is publisher-declared string storage but its converted-snapshot encoding, contents and alignment were not accessed. Freeze separately bounded inert format acquisition; reject pickle or executable loaders; independently qualify private expected values, cases and invalid/wrong controls.',
            'Qualify stdin byte transport, output cap, tokenizer and exact comparator with independently specified correct/wrong controls in the trusted containment runtime before any task or candidate execution.',
            'Resolve complete semantic duplicate/variant/transferable-structure and historical-exposure crosswalk; contest IDs and dates are provenance only, not independent families or novelty certificates.',
            'Establish source-use provenance and a complete admitted roster, then freeze family-disjoint development/tuning/evaluation, root weights, real learner, two primary comparators, failure fallback, actual costs and finite-census precision before calls.',
        ],
        'execution': {'receiver_calls': 0, 'candidate_reference_task_executions': 0,
                      'private_column_access': False, 'network_requests': 0,
                      'source_loader_execution': False, 'raw_task_content_committed': False},
        'rows': ledger,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('fresh result required; never overwrite a completed disposition')
    if args.source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError('public source byte cap')
    result = feasibility(args.source.read_bytes(), args.inventory.read_bytes())
    result['implementation_sha256'] = sha256(Path(__file__).read_bytes())
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True,
                                   allow_nan=False) + '\n')
    print(json.dumps({'version': VERSION, 'counts': result['counts'],
                      'public_projection_sha256': result['source']['public_projection_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
