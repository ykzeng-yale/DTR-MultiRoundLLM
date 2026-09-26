#!/usr/bin/env python3
"""Reproduce LEAD-MEASUREMENT-04 source-only rows; never execute benchmark code.

Run from repository root with Python 3.12. Output goes to stdout; compare rows
and counts to results/policy_assertion_separation_audit_20260926.json.
"""
import ast
import hashlib
import json
from pathlib import Path

PINS = {
    'work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl': 'ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f',
    'results/frame_review_mrl15_20260922T021718Z/manifest.json': '4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc',
}


def main():
    sha = lambda b: hashlib.sha256(b).hexdigest()
    for path, digest in PINS.items():
        if sha(Path(path).read_bytes()) != digest:
            raise ValueError(f'source identity mismatch: {path}')
    source, manifest = PINS
    tasks = {r['task_id']: r for r in map(json.loads, Path(source).read_text().splitlines())}
    ids = json.loads(Path(manifest).read_text())['eligible_ordered_ids']
    if len(ids) != 198 or len(set(ids)) != 198:
        raise ValueError('fixed frame must have exactly 198 distinct roots')
    rows = []
    for rank, task_id in enumerate(ids, 1):
        tests = tasks[task_id]['test_list']
        forms, failures = [], []
        for j, text in enumerate(tests):
            try:
                forms.append(ast.dump(ast.parse(text), include_attributes=False))
            except (SyntaxError, ValueError) as exc:
                forms.append(None)
                failures.append({'assertion_index': j, 'error_type': type(exc).__name__})
        rows.append({
            'rank': rank, 'task_id': task_id, 'assertion_count': len(tests),
            'assertion_utf8_sha256': [sha(s.encode()) for s in tests],
            'assertion_ast_sha256': [None if s is None else sha(s.encode()) for s in forms],
            'private_slots_exact_public_repeat': [j for j in range(1, len(tests)) if tests[j] == tests[0]],
            'private_slots_structural_public_repeat': [j for j in range(1, len(forms)) if forms[j] is not None and forms[j] == forms[0]],
            'private_structural_duplicate_pairs': [[j, k] for j in range(1, len(forms)) for k in range(j + 1, len(forms)) if forms[j] is not None and forms[j] == forms[k]],
            'distinct_structural_assertions': len(set(s for s in forms if s is not None)),
            'parse_failures': failures,
        })
    print(json.dumps({'inputs': PINS, 'rows': rows}, indent=2))


if __name__ == '__main__':
    main()
