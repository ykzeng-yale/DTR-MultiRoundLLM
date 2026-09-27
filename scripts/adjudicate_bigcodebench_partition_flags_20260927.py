#!/usr/bin/env python3
"""Refine static flags with method bindings and decorators; never execute task source."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import warnings


def method_fingerprint(node):
    node=copy.deepcopy(node)
    node.name='METHOD'
    return hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()


def inspect(source):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',SyntaxWarning)
        tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='TestCases')
    bindings={};shadowed=[]
    for n in cls.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test'):
            if n.name in bindings:shadowed.append({'name':n.name,'earlier_line':bindings[n.name].lineno,'later_line':n.lineno})
            bindings[n.name]=n
    ordered=sorted(bindings)
    public=bindings[ordered[0]]
    full=method_fingerprint(public)
    same=[name for name in ordered[1:] if method_fingerprint(bindings[name])==full]
    return {'declared_test_definitions':len(bindings)+len(shadowed),'distinct_direct_names':len(bindings),
            'shadowed_definitions':shadowed,'public_candidate':ordered[0],
            'same_full_method_ast_private':same,'public_method_fingerprint':full,
            'private_distinct_from_public_count':len(bindings)-1-len(same),
            'limitation':'Last direct definition recorded; arbitrary class-body mutations, decorators and inherited runtime discovery remain unexecuted.'}


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('refuse overwrite')
    source_hash=hashlib.sha256(a.source.read_bytes()).hexdigest()
    if source_hash!='d9a4965821c9507ebdfb551c288656b2d5fe553234f5183044333ca8a4018267':raise ValueError('source mismatch')
    import pyarrow.parquet as pq
    rows=[{'task_id':r['task_id'],**inspect(r['test'])} for r in pq.read_table(a.source,use_threads=False).to_pylist()]
    result={'source_sha256':source_hash,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'summary':{'rows':len(rows),'direct_distinct_method_names':sum(r['distinct_direct_names'] for r in rows),
            'shadowed_definitions':sum(len(r['shadowed_definitions']) for r in rows),
            'same_full_method_ast_rows':[r['task_id'] for r in rows if r['same_full_method_ast_private']],
            'no_private_method_distinct_from_public':[r['task_id'] for r in rows if r['private_distinct_from_public_count']==0]},'rows':rows}
    with a.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
