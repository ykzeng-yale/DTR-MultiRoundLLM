import copy
import pytest
from experiments.bouchet.strategy_comparison_v1 import *
from scripts.grade_strategy_comparison_20260928 import describe

def inputs(status='FAIL'):
    return [{'trajectory':i,'root':str(i//2),'replicate':i%2,
             'base_messages':[{'role':'system','content':'system'},{'role':'user','content':'task'}],
             'raw':'def f(x): return x','public_status':status,
             'private_label':'DO_NOT_SEND'} for i in range(18)]

def receipt(state):
    return {'calls':[{**{k:q[k] for k in ('slot','root','artifact','arm','replicate')},
                     'status':'returned','payload_sha256':digest(q['payload']),
                     'response':{'choices':[{'message':{'content':'def f(x): return x'}}]}}
                    for q in state['requests']], 'unattempted':0}

def test_complete_all_assigned_no_private_and_critique_not_executed():
    state=initialize(inputs(),assignment_table());assert len(state['rows'])==162
    observed=[]
    def obs(root,raw):observed.append(root);return 'FAIL',{'private_trace':'KEEP_OUT'}
    state=advance(state,receipt(state),obs)
    assert len(observed)==18*6 # eight continuing policies minus two critique types
    for q in state['requests']:
        assert 'KEEP_OUT' not in str(q) and 'DO_NOT_SEND' not in str(q)
    state=advance(state,receipt(state),obs)
    assert not state['requests'] and len(state['rows'])==162
    assert all(len(r['calls'])==0 if r['policy']=='STOP' else len(r['calls'])==2 for r in state['rows'])

def test_pass_gate_stops_without_new_checks_but_fixed_policies_continue():
    state=initialize(inputs('PASS'),assignment_table());stopped=[copy.deepcopy(r) for r in state['rows'] if r['disposition']=='stopped']
    assert len(stopped)==72
    state=advance(state,receipt(state),lambda *x:('PASS',{}))
    state=advance(state,receipt(state),lambda *x:('PASS',{}))
    assert [r for r in state['rows'] if r['disposition']=='stopped']==stopped

def test_reflection_adaptations_have_distinct_declared_contexts():
    state=initialize(inputs(),assignment_table());state=advance(state,receipt(state),lambda *x:('FAIL',{}))
    q={x['arm']:x for x in state['requests']}
    assert len(q['SELF_REFINE_ADAPT']['payload']['messages'])==6
    assert len(q['REFLEXION_ADAPT']['payload']['messages'])==3
    assert len(q['RESAMPLE_SELECT']['payload']['messages'])==2

def test_resample_earliest_pass_selected_not_private_best():
    state=initialize(inputs('PASS'),assignment_table());state=advance(state,receipt(state),lambda *x:('PASS',{}));state=advance(state,receipt(state),lambda *x:('PASS',{}))
    assert all(r['selected_candidate']==0 for r in state['rows'] if r['policy']=='RESAMPLE_SELECT')

def test_missingness_does_not_become_stop_or_cancel_in_contrast():
    state=initialize(inputs(),assignment_table());state=advance(state,{'calls':[],'unattempted':len(state['requests'])},lambda *x:pytest.fail())
    assert all(r['disposition']=='generation_unavailable' for r in state['rows'] if r['policy']!='STOP')
    d=describe([]);assert d['contrasts_vs_resample']['PATCH2']==[-1,1]

def test_assignment_guard_and_deterministic_seeds():
    assert assignment_table()==assignment_table()
    assert len({s for r in assignment_table() for s in r['seeds']})==324
    state=initialize(inputs(),assignment_table());r=receipt(state);r['calls'][0]['root']='wrong'
    with pytest.raises(ValueError,match='assignment'):advance(state,r,lambda *x:pytest.fail())

def test_public_switch_is_explicit_untrained_rule():
    assert [action('PUBLIC_SWITCH',s) for s in ('PASS','FAIL','INCOMPLETE')]==['STOP','RETHINK','PATCH']
