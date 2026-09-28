import copy
import pytest
from experiments.bouchet.full_history_pilot_v1 import assignments, initialize, advance
from experiments.landmark.collect import digest
from experiments.sequential.pilot_public_export import export


def fixture():
    public=[{'task_id':str(i),'adapted_public_contract':'Return one','signature':'f()','entry_point':'f','public_case':{'args_literal':'[]','expected_literal':'1'}} for i in range(9)]
    ledger=assignments([p['task_id'] for p in public]);state=initialize(public,ledger)
    for phase in range(3):
        calls=[]
        for q in state['requests']:
            calls.append({**{k:q[k] for k in ('slot','root','artifact','arm','replicate')},'payload_sha256':digest(q['payload']),'status':'returned','response':{'choices':[{'message':{'content':'def f():\n return 1'}}]}})
        state=advance(state,{'calls':calls,'unattempted':0},public,lambda *args:{'status':'PASS','secret_audit_marker':'EXCLUDED'})
    return state,ledger


def run(state,ledger):return export(state,ledger,'a'*64,'b'*64,'c'*64)


def test_actual_prefixes_and_no_future_or_audit_fields():
    state,ledger=fixture();rows=run(state,ledger)
    assert len(rows)==sum(len(r['decisions']) for r in state['rows'])
    for r in rows:
        turn=r['metadata']['turn'];view=r['view']
        assert len(view['messages'])==2*turn+1
        assert len(view['public_observations'])==turn
        assert 'EXCLUDED' not in str(view)
        assert 'root' not in view and 'outcome' not in view
        assert r['selection']['probabilities']==[1/3]*3
    altered=copy.deepcopy(state)
    for r in altered['rows']:
        r['private_outcome']='SECRET';r['final_raw']='FUTURE_SECRET'
    assert run(altered,ledger)==rows


@pytest.mark.parametrize('kind',['prefix','probability','missing_decision','response','post_stop'])
def test_refuses_corrupted_history_or_law(kind):
    state,ledger=fixture()
    if kind=='prefix':state['rows'][0]['messages'][1]['content']='tampered'
    if kind=='probability':state['rows'][0]['decisions'][0]['selection_probability']=.5
    if kind=='missing_decision':state['rows'][0]['decisions'].pop()
    if kind=='response':state['rows'][0]['messages'][2]['content']='tampered'
    if kind=='post_stop':
        row=next(r for r in state['rows'] if r['disposition']=='stopped');row['messages'].append({'role':'user','content':'after STOP'})
    with pytest.raises(ValueError):run(state,ledger)
