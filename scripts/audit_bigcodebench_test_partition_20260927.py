#!/usr/bin/env python3
"""Static measurement feasibility only. No dataset-source execution."""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import warnings

PIN = 'd9a4965821c9507ebdfb551c288656b2d5fe553234f5183044333ca8a4018267'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def partition(source):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)
        tree = ast.parse(source)
    classes = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'TestCases']
    if len(classes) != 1:
        return {'status': 'hold', 'reasons': ['nonunique_or_missing_TestCases']}
    cls = classes[0]
    methods = [x for x in cls.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name.startswith('test')]
    names = [x.name for x in methods]
    reasons = []
    if len(set(names)) != len(names): reasons.append('duplicate_method_names')
    if len(methods) < 2: reasons.append('fewer_than_two_methods')
    if [ast.unparse(b) for b in cls.bases] != ['unittest.TestCase']: reasons.append('nonstandard_inheritance')
    if cls.decorator_list: reasons.append('class_decorators')
    if any(isinstance(x, ast.AsyncFunctionDef) for x in methods): reasons.append('async_test')
    if any(x.name == 'load_tests' for x in tree.body if isinstance(x, ast.FunctionDef)): reasons.append('module_load_tests')
    if any(isinstance(x, (ast.Assign, ast.AnnAssign, ast.AugAssign)) for x in cls.body): reasons.append('class_assignments_review')
    methods = sorted(methods, key=lambda x: x.name)
    entries=[]
    for method in methods:
        body = ast.Module(body=method.body, type_ignores=[])
        assertions = [n for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr.startswith('assert')]
        entries.append({'name': method.name, 'body_ast_sha256': digest(ast.dump(body, include_attributes=False)),
                        'assertion_ast_sha256': sorted(set(digest(ast.dump(n, include_attributes=False)) for n in assertions)),
                        'decorator_ast_sha256': [digest(ast.dump(n, include_attributes=False)) for n in method.decorator_list],
                        'subtest_calls': sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='subTest' for n in ast.walk(method))})
    public = entries[0] if entries else None
    private = entries[1:]
    overlap = []
    if public:
        for entry in private:
            shared = sorted(set(public['assertion_ast_sha256']) & set(entry['assertion_ast_sha256']))
            if shared or public['body_ast_sha256']==entry['body_ast_sha256']:
                overlap.append({'private_method': entry['name'], 'shared_assertion_hashes': shared,
                                'identical_body': public['body_ast_sha256']==entry['body_ast_sha256']})
    return {'status': 'hold' if reasons else 'structurally_partitionable', 'reasons': reasons,
            'method_count': len(entries), 'public_candidate': public, 'private_candidates': private,
            'syntactic_public_private_overlap': overlap,
            'fixtures': [x.name for x in cls.body if isinstance(x,ast.FunctionDef) and x.name in ['setUp','tearDown','setUpClass','tearDownClass']],
            'additional_classes': [x.name for x in tree.body if isinstance(x,ast.ClassDef) and x is not cls],
            'module_executable_node_types': [type(x).__name__ for x in tree.body if not isinstance(x,(ast.Import,ast.ImportFrom,ast.ClassDef,ast.FunctionDef))]}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists(): raise ValueError('refuse overwrite')
    if hashlib.sha256(a.source.read_bytes()).hexdigest()!=PIN:raise ValueError('source mismatch')
    import pyarrow.parquet as pq
    rows=pq.read_table(a.source,use_threads=False).to_pylist()
    results=[{'task_id':r['task_id'],'test_sha256':digest(r['test']),**partition(r['test'])} for r in rows]
    summary={'rows':len(results),'statuses':dict(Counter(r['status'] for r in results)),
             'method_count':sum(r.get('method_count',0) for r in results),
             'overlap_rows':[r['task_id'] for r in results if r.get('syntactic_public_private_overlap')],
             'additional_class_rows':[r['task_id'] for r in results if r.get('additional_classes')],
             'module_executable_rows':[r['task_id'] for r in results if r.get('module_executable_node_types')],
             'hold_reasons':dict(Counter(reason for r in results for reason in r['reasons']))}
    output={'source_sha256':PIN,'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'candidate_rule':'lexicographically first TestCases method beginning test; remainder private; source-only proposal',
            'summary':summary,'rows':results,'limitations':['No source execution, runtime discovery, task admission or reference validation.',
            'Identical assertion ASTs can use different fixture/local bindings; a flag is not proof of equivalent cases.',
            'No syntactic overlap does not imply semantic separation or informative tests.']}
    with a.out.open('x') as f:json.dump(output,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in summary.items()},indent=2))


if __name__=='__main__':main()
