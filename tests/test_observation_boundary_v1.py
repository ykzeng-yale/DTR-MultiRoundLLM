import json
import pytest
from experiments.prompt_choice.observation_boundary_v1 import VERSION, evaluate, parse_observation, program


def reply(value):
    return json.dumps({'observation_version': VERSION, 'value': value})


def runner(stdout, disposition='completed_ungraded'):
    return lambda *a, **k: {'execution': {'disposition': disposition}, 'raw_process': {'stdout': stdout}}


def test_expected_and_comparator_never_sent_to_candidate():
    seen = []
    def stub(source, **kwargs):
        seen.append(source)
        return runner(reply('wrong'))()
    r = evaluate('def task_func(x): return x', 'task_func', ['input'], 'secret-expected', runner=stub)
    assert r['outcome'] == 0
    assert 'secret-expected' not in seen[0] and 'expected_sha256' not in seen[0]
    assert 'input' in seen[0]


@pytest.mark.parametrize('text', ['PASS', '{"passed":true}', reply(2)+'\n'+reply(2),
    '{"observation_version":"'+VERSION+'","value":1,"value":2}',
    '{"observation_version":"'+VERSION+'","value":NaN}',
    '{"observation_version":"'+VERSION+'","value":1e999}', '['*1000+']'*1000])
def test_untrusted_verdict_or_malformed_output_never_passes(text):
    r = evaluate('def task_func(): return 0', 'task_func', [], 2, runner=runner(text))
    assert r['outcome'] is None and r['status'] == 'INCOMPLETE'


@pytest.mark.parametrize('actual,expected,passed', [(True,1,False),(1,1.0,False),([1,2],[1],False),
    ({'x':1},{'x':1},True),({'x':[1,2]},{'x':[1,2]},True),(None,None,True)])
def test_exact_external_observation_comparison(actual,expected,passed):
    r=evaluate('def f(): return 0','f',[],expected,runner=runner(reply(actual)))
    assert r['outcome']==int(passed)


@pytest.mark.parametrize('disposition',['timeout','output_limit','process_error'])
def test_valid_claim_with_bad_process_cannot_pass(disposition):
    r=evaluate('def f(): return 1','f',[],1,runner=runner(reply(1),disposition))
    assert r['outcome'] is None


def test_invalid_expected_prevents_dispatch():
    def forbidden(*a,**k):raise AssertionError('dispatched')
    with pytest.raises(ValueError):evaluate('def f(): return 1','f',[],float('nan'),runner=forbidden)


def test_source_is_only_constructed_not_executed(tmp_path):
    p=tmp_path/'not-created'
    program(f'open({str(p)!r},"w").write("bad")','f',[])
    assert not p.exists()
