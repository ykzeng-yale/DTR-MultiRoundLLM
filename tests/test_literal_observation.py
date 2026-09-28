import pytest
from experiments.prompt_choice import literal_observation_v1 as o


def test_integer_keys_preserved_without_expected_in_program():
    s=o.program('def task_func(d,k): return k in d','task_func','[{1: "a"},1]')
    assert "[{1:" in s and 'literal_eval' in s
    assert 'expected' not in s


@pytest.mark.parametrize('x',['[__import__("os").system("false")]','{}','[x for x in []]','[1]*1000000'])
def test_nonliteral_and_nonlist_inputs_refused_before_start(x):
    def never(*a,**kw):raise AssertionError('started')
    with pytest.raises(ValueError):o.evaluate('pass','task_func',x,True,runner=never)


def test_wrong_boolean_vs_integer_still_rejected():
    def mock(*a,**kw):return {'execution':{'disposition':'completed_ungraded'},'raw_process':{'stdout':'{"observation_version":"'+o.VERSION+'","value":1}'}}
    assert o.evaluate('pass','task_func','[]',True,runner=mock)['status']=='FAIL'
