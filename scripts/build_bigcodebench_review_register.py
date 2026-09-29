#!/usr/bin/env python3
"""Consolidate source reviews; never certify admission or independent families."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

FIELDS = ('complete_prompt', 'instruct_prompt', 'canonical_solution', 'test')
PIN = 'd9a4965821c9507ebdfb551c288656b2d5fe553234f5183044333ca8a4018267'


def build(inventory, reviews, exposures=()):
    if inventory['source_sha256'] != PIN:
        raise ValueError('inventory source mismatch')
    source = inventory['rows']
    by_id = {r['task_id']: r for r in source}
    if len(by_id) != len(source) or len(source) != inventory['row_count']:
        raise ValueError('inventory count or duplicate ID')
    if [r['row'] for r in source] != list(range(len(source))):
        raise ValueError('inventory row order')
    exposure_by_id = defaultdict(list)
    for exposure in exposures:
        task = exposure['task_id']
        if task not in by_id or exposure['kind'] != 'measurement_development' or not exposure.get('evidence_sha256'):
            raise ValueError('invalid exposure record')
        if any(exposure['field_sha256'].get(k) != by_id[task]['field_sha256'][k] for k in FIELDS):
            raise ValueError('exposure field hash mismatch')
        exposure_by_id[task].append(exposure)
    evidence = defaultdict(list)
    constraints = []
    for name, review in reviews:
        if review['source_sha256'] != PIN:
            raise ValueError('review source mismatch')
        items = review.get('rows', [review] if 'task_id' in review else [])
        if not items:
            raise ValueError('empty review')
        seen = set()
        for item in items:
            task = item['task_id']
            if task not in by_id or task in seen:
                raise ValueError('unknown or duplicate reviewed task')
            seen.add(task)
            if item.get('source_row', by_id[task]['row']) != by_id[task]['row']:
                raise ValueError('review row mismatch')
            if any(item['field_sha256'].get(k) != by_id[task]['field_sha256'][k] for k in FIELDS):
                raise ValueError('review field hash mismatch')
            if item['admission'] != 'unresolved_not_admitted':
                raise ValueError('admission requires a different validated contract')
            evidence[task].append(name)
        groups = review.get('same_family_provisional_groups', [])
        if 'provisional_extended_group' in review:
            groups = [*groups, review['provisional_extended_group']]
        for group in groups:
            ids = [f'BigCodeBench/{n}' for n in group]
            if len(set(ids)) != len(ids) or len(ids) < 2 or any(t not in by_id for t in ids):
                raise ValueError('invalid family constraint')
            constraints.append({'task_ids': ids, 'kind': 'provisional_lead_co_split', 'evidence': name})
    # Exact full-field duplicates are binding split constraints, not inferred
    # from one common statement, one solution body, or library metadata.
    fingerprints = defaultdict(list)
    for row in source:
        fingerprints[tuple(row['field_sha256'][k] for k in FIELDS)].append(row['task_id'])
    for members in fingerprints.values():
        if len(members) > 1:
            constraints.append({'task_ids': members, 'kind': 'exact_four_field_duplicate', 'evidence': 'inventory'})
    # A shared implementation *and* identical preamble can transfer an answer
    # across different prompts/tests. This is a co-split constraint, not a claim
    # that the two specifications or their test outcomes are equivalent.
    answer_fingerprints = defaultdict(list)
    for row in source:
        hashes = row['field_sha256']
        if 'code_prompt' not in hashes:
            continue  # Older toy inventories lacked this field.
        answer_fingerprints[(hashes['code_prompt'], hashes['canonical_solution'])].append(row['task_id'])
    exact_groups = {tuple(c['task_ids']) for c in constraints if c['kind'] == 'exact_four_field_duplicate'}
    for members in answer_fingerprints.values():
        if len(members) > 1 and tuple(members) not in exact_groups:
            constraints.append({'task_ids': members, 'kind': 'exact_code_and_reference_co_split', 'evidence': 'inventory'})
    return {
        'classification': 'source review register; not admission ledger, final families or sampling frame',
        'source_sha256': PIN,
        'summary': {'source_tasks': len(source), 'source_reviewed': len(evidence),
                    'source_review_pending': len(source)-len(evidence), 'admitted_tasks': 0,
                    'final_family_count': None, 'known_measurement_exposed_tasks': len(exposure_by_id)},
        'constraints': constraints,
        'constraints_scope': 'preserve explicit co-split constraints; no automatic transitive family partition; missing edges do not certify independence',
        'rows': [{'task_id': r['task_id'], 'source_row': r['row'],
                  'source_review_evidence': sorted(set(evidence[r['task_id']])),
                  'source_review_status': 'recorded' if evidence[r['task_id']] else 'pending',
                  'known_exposures': exposure_by_id[r['task_id']],
                  'exposure_scope': 'nonexhaustive; empty does not mean untouched',
                  'admission': 'unresolved_not_admitted',
                  'prior_development_crosswalk': 'pending',
                  'global_family_review': 'pending'} for r in source],
        'receiver_calls': 0, 'benchmark_calls': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--reviews', type=Path, nargs='+', required=True)
    parser.add_argument('--exposures', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('refuse overwrite')
    inputs = [args.inventory, *args.reviews, args.exposures]
    if len(set(p.resolve() for p in inputs)) != len(inputs):
        raise ValueError('duplicate input path')
    blobs = {str(p): p.read_bytes() for p in inputs}
    exposures = json.loads(blobs[str(args.exposures)])
    for item in exposures:
        for path, digest in item['evidence_sha256'].items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
                raise ValueError('exposure evidence mismatch')
    result = build(json.loads(blobs[str(args.inventory)]),
                   [(str(p), json.loads(blobs[str(p)])) for p in args.reviews], exposures)
    result['input_sha256'] = {p: hashlib.sha256(b).hexdigest() for p, b in blobs.items()}
    result['builder_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
