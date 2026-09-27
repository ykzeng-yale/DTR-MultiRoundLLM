#!/usr/bin/env python3
"""Pinned data-only row inventory. Never import or execute dataset source."""
from __future__ import annotations
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

PIN = 'd9a4965821c9507ebdfb551c288656b2d5fe553234f5183044333ca8a4018267'
FIELDS = ('task_id', 'complete_prompt', 'instruct_prompt', 'canonical_solution', 'code_prompt', 'test', 'entry_point', 'doc_struct', 'libs')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def syntax(text):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return {'parseable': False}
    imports, methods = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split('.')[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
            methods.append(node.name)
    return {'parseable': True, 'import_roots': sorted(imports), 'test_method_count': len(methods)}


def summarize(rows):
    groups = {k: defaultdict(list) for k in ('task_id', 'complete_prompt', 'instruct_prompt', 'test', 'canonical_solution')}
    missing = Counter({k: 0 for k in FIELDS})
    libs, entries, imports, output = Counter(), Counter(), Counter(), []
    for index, r in enumerate(rows):
        if set(r) != set(FIELDS):
            raise ValueError('unexpected fields')
        if any(v is not None and not isinstance(v, str) for v in r.values()):
            raise ValueError('non-string field')
        for k in FIELDS:
            missing[k] += r[k] is None or not r[k].strip()
        ident = r['task_id']
        for k, g in groups.items():
            if r[k] is not None:
                g[sha(r[k].encode())].append({'row': index, 'task_id': ident})
        parsed_libs, lib_error = [], None
        try:
            if r['libs'] is None or len(r['libs']) > 65536:
                raise ValueError('missing or oversized libs')
            value = ast.literal_eval(r['libs'])
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ValueError('libs must be a list of strings')
            parsed_libs = sorted(set(value))
        except (ValueError, SyntaxError, TypeError, RecursionError) as e:
            lib_error = type(e).__name__
        libs.update(parsed_libs)
        entries.update([r['entry_point']])
        test_info = syntax(r['test'] or '')
        source_info = syntax((r['complete_prompt'] or '') + (r['canonical_solution'] or ''))
        imports.update(set(test_info.get('import_roots', [])) | set(source_info.get('import_roots', [])))
        doc_error, examples = None, None
        try:
            doc = json.loads(r['doc_struct'])
            if not isinstance(doc, dict) or not isinstance(doc.get('examples'), list):
                raise ValueError('invalid doc structure')
            examples = len(doc['examples'])
        except (ValueError, TypeError) as e:
            doc_error = type(e).__name__
        output.append({'row': index, 'task_id': ident, 'entry_point': r['entry_point'],
                       'field_sha256': {k: sha(v.encode()) if v is not None else None for k, v in r.items()},
                       'libs': parsed_libs, 'libs_error': lib_error, 'test_static': test_info,
                       'reference_static': source_info, 'doc_error': doc_error, 'doc_example_line_count': examples})
    return {'row_count': len(rows), 'missing_or_blank': dict(missing),
            'entry_point_counts': dict(entries), 'declared_library_task_counts': dict(sorted(libs.items())),
            'static_import_task_counts': dict(sorted(imports.items())),
            'duplicate_exact_bytes': {k: [v for v in g.values() if len(v)>1] for k,g in groups.items()},
            'rows': output,
            'limits': ['AST parsing is not execution, dependency resolution or semantic validation.',
                       'Exact-byte duplicates are not a semantic family partition.',
                       'Library names are metadata, not independent families or network-use findings.',
                       'No row is admitted to evaluation; no receiver or benchmark outcome is produced.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('refuse overwrite')
    data = a.source.read_bytes()
    if sha(data) != PIN:
        raise ValueError('source hash mismatch')
    import pyarrow
    import pyarrow.parquet as pq
    pyarrow.set_cpu_count(1)
    table = pq.read_table(a.source, use_threads=False)
    if table.column_names != list(FIELDS) or any(str(f.type) != 'string' for f in table.schema):
        raise ValueError('unexpected schema')
    result = summarize(table.to_pylist())
    result.update({'request': 'LEAD-SOURCE-02', 'source_sha256': PIN,
                   'reader': {'pyarrow': pyarrow.__version__, 'python': sys.version},
                   'builder_sha256': sha(Path(__file__).read_bytes()),
                   'schema': [{'name': f.name, 'type': str(f.type)} for f in table.schema]})
    with a.out.open('x') as f:
        json.dump(result, f, sort_keys=True, indent=2)
        f.write('\n')
    print(json.dumps({'rows': result['row_count'], 'output': str(a.out), 'sha256': sha(a.out.read_bytes())}))


if __name__ == '__main__':
    main()
