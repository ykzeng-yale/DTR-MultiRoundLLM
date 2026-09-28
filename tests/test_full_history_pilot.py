import copy
import pytest
from experiments.bouchet.full_history_pilot_v1 import assignments, initialize, advance
from experiments.landmark.collect import digest


def fixture():
    public = [{'task_id':str(i),'adapted_public_contract':'identity',
               'signature':'f(x)','entry_point':'f',
               'public_case':{'args_literal':'[1]','expected_literal':'1'},
               'private_trap':'MUST_NOT_ENTER_PROMPT'} for i in range(9)]
    return public, initialize(public, assignments([p['task_id'] for p in public]))


def receipt(state):
    calls = []
    for q in state['requests']:
        c = {k:q[k] for k in ('slot','root','artifact','arm','replicate')}
        c.update(payload_sha256=digest(q['payload']),status='returned',
                 response={'choices':[{'message':{'content':'def f(x): return x'}}]})
        calls.append(c)
    return {'calls':calls,'unattempted':0}


def test_absorbing_stop_full_history_and_no_private_prompt():
    public, state = fixture()
    original = copy.deepcopy(state)
    evaluations = []
    def evaluate(*args):
        evaluations.append(args)
        return {'status':'PASS','stderr':'PRIVATE_AUDIT_NOT_A_MESSAGE'}
    stopped = set()
    for phase in range(3):
        old = copy.deepcopy(state)
        state = advance(state, receipt(state), public, evaluate)
        for r, previous in zip(state['rows'],old['rows']):
            if r['trajectory'] in stopped:
                assert r == previous
            assert r['messages'][:len(previous['messages'])] == previous['messages']
            if r['disposition']=='stopped':
                stopped.add(r['trajectory'])
        for q in state['requests']:
            text = str(q['payload'])
            assert 'MUST_NOT_ENTER_PROMPT' not in text
            assert 'PRIVATE_AUDIT_NOT_A_MESSAGE' not in text
            assert q['slot'] not in stopped
    assert state['requests']==[] and all(r['disposition'] in ('stopped','horizon') for r in state['rows'])
    assert stopped and len(evaluations)<=36
    assert original['phase']==0
    assert all(d['selection_probability']==1/3 and len(d['slate'])==3 for r in state['rows'] for d in r['decisions'])


def test_missing_generation_is_not_stop_or_retried():
    public,state=fixture()
    out=advance(state,{'calls':[],'unattempted':18},public,lambda *x:pytest.fail('must not grade missing output'))
    assert not out['requests']
    assert all(r['disposition']=='generation_unavailable' and not r['decisions'] for r in out['rows'])


def test_receipt_mismatch_fails_before_execution():
    public,state=fixture();r=receipt(state)
    r['calls'][0]['payload_sha256']='wrong'
    with pytest.raises(ValueError,match='assignment'):
        advance(state,r,public,lambda *x:pytest.fail('must not grade mismatched output'))


def test_syntax_unavailable_is_observed_not_dropped():
    public,state=fixture();r=receipt(state)
    for c in r['calls']:
        c['response']['choices'][0]['message']['content']='def broken('
    out=advance(state,r,public,lambda *x:pytest.fail('cannot execute malformed source'))
    assert len(out['rows'])==18
    assert all(row['decisions'][0]['public_status']=='INCOMPLETE' for row in out['rows'])


def test_assignment_determinism_and_nonempty_all_actions():
    a=assignments([str(i) for i in range(9)])
    assert a==assignments([str(i) for i in reversed(range(9))])
    assert {x for r in a for x in r['actions']}=={'STOP','PATCH','RETHINK'}
    assert len({s for r in a for s in r['seeds']})==54
