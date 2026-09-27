#!/usr/bin/env python3
"""Exact source-template retrieval, never task execution or family adjudication."""
import argparse
import ast
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import warnings

PIN = 'd9a4965821c9507ebdfb551c288656b2d5fe553234f5183044333ca8a4018267'
MIN_NODES = 12


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def index(rows):
    ids = [r['task_id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate task IDs')
    groups = defaultdict(set)
    details = {}
    counts = {}
    for row in rows:
        source = row['complete_prompt'] + row['canonical_solution']
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', SyntaxWarning)
            tree = ast.parse(source)
        funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == row['entry_point']]
        if len(funcs) != 1:
            raise ValueError('ambiguous entry point')
        seen = set()
        for node in funcs[0].body:
            if isinstance(node, (ast.Import, ast.ImportFrom)) or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
                continue
            size = sum(1 for _ in ast.walk(node))
            if size < MIN_NODES:
                continue
            fingerprint = sha(ast.dump(node, include_attributes=False))
            groups[fingerprint].add(row['task_id'])
            details[fingerprint] = {'ast_node_count': size, 'statement_kind': type(node).__name__}
            seen.add(fingerprint)
        counts[row['task_id']] = len(seen)
    shared = []
    pairs = defaultdict(list)
    for fingerprint, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        members = sorted(members)
        shared.append({'statement_sha256': fingerprint, **details[fingerprint], 'task_ids': members})
        for i, left in enumerate(members):
            for right in members[i+1:]:
                pairs[(left,right)].append(fingerprint)
    pair_rows = [{'task_ids': list(pair), 'shared_statement_count': len(fps),
                  'shared_ast_nodes': sum(details[h]['ast_node_count'] for h in fps),
                  'statement_sha256': sorted(fps)} for pair,fps in sorted(pairs.items())]
    return {'classification': 'exact top-level statement retrieval; not semantic families or eligibility',
            'rule': {'minimum_ast_nodes': MIN_NODES, 'names_and_constants_preserved': True,
                     'ignores_source_locations': True, 'transitive_clustering': False},
            'limitations': ['renamed/reordered/rewritten relatives may be missed',
                           'identical statement may mean different things under different imports or surrounding state',
                           'large common boilerplate can match; semantic review remains required',
                           'no prior-development crosswalk, runtime or endpoint validation'],
            'summary': {'rows': len(rows), 'shared_statement_groups': len(shared), 'candidate_pairs': len(pair_rows),
                        'rows_with_candidates': len(set(t for p in pairs for t in p))},
            'task_statement_counts': counts, 'shared_statements': shared,
            'pair_storage': 'all candidate pairs recoverable as unions of within-group pairs; not expanded'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('refuse overwrite')
    source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if source_hash != PIN:
        raise ValueError('source mismatch')
    import pyarrow.parquet as pq
    result = index(pq.read_table(args.source, use_threads=False).to_pylist())
    result.update(source_sha256=source_hash, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
