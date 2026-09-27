import pytest
from scripts.index_bigcodebench_templates_20260927 import index


def row(name, body, prefix=''):
    return dict(task_id=name, entry_point='task_func', complete_prompt=prefix+'def task_func(xs):\n    """description"""\n', canonical_solution=body)


def test_shared_computation_not_import_semantics():
    body='    values = [transform(x) for x in xs if x > 0]\n    return values\n'
    result=index([row('a',body,'from a import transform\n'),row('b',body,'from b import transform\n')])
    assert result['summary']['candidate_pairs']==1
    assert result['shared_statements'][0]['task_ids']==['a','b']
    assert 'not semantic families' in result['classification']


def test_preserves_constants_and_names():
    a='    values = [x * 2 for x in xs if x > 0]\n'
    b=a.replace('* 2','* 3')
    c=a.replace('values','other')
    assert index([row('a',a),row('b',b),row('c',c)])['shared_statements']==[]


def test_no_execution(tmp_path):
    target=tmp_path/'should-not-exist'
    body=f'    open({str(target)!r}, "w").write("bad")\n'
    index([row('a',body),row('b',body)])
    assert not target.exists()


def test_no_transitive_family_collapse():
    x='    values = [x * 2 for x in xs if x > 0]\n'
    y='    values = [x * 3 for x in xs if x > 0]\n'
    r=index([row('a',x),row('b',x+y),row('c',y)])
    assert sorted(p['task_ids'] for p in r['shared_statements'])==[['a','b'],['b','c']]
    assert r['rule']['transitive_clustering'] is False


def test_duplicate_or_ambiguous_rows_refused():
    r=row('a','    return 1\n')
    with pytest.raises(ValueError,match='duplicate'):index([r,r])
    r['canonical_solution']+='\ndef task_func(xs):\n    return 2\n'
    with pytest.raises(ValueError,match='ambiguous'):index([r])


def test_docstrings_and_small_boilerplate_not_matches():
    assert index([row('a','    return {}\n'),row('b','    return {}\n')])['shared_statements']==[]
