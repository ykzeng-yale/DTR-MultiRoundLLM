import copy
import pytest
from experiments.sequential.finite_history_q import fit,predict,evaluate_holdout,validate


def panel(prefix='train'):
    return [{'episode':f'{prefix}-{x}-{a}','family':f'{prefix}-{x}-{a}', 'steps':[{'history':(x,), 'action':a,'probabilities':(1/3,)*3}], 'outcome':float(a==(1 if x==0 else 2))} for x in (0,1) for a in range(3)]


def test_learns_stop_instead_of_public_oracle():
    data=panel();m=fit(data,1)
    assert predict(m,(1,),0)[0]==2
    assert predict(m,(1,),0)[2][0]==0
    assert predict(m,(0,),0)[0]==1


def test_exact_balanced_scores_and_family_guard():
    data=panel();m=fit(data,1);scores=evaluate_holdout(m,panel('test'))
    assert sum(x['ipw'] for x in scores)/6==1
    assert all(x['dr']==1 for x in scores)
    with pytest.raises(ValueError,match='family'):evaluate_holdout(m,data)


def test_no_label_or_latent_input_and_missing_refused():
    data=panel();data[0]['latent_quality']=1
    with pytest.raises(ValueError):fit(data,1)
    data=panel();data[0]['outcome']=None
    with pytest.raises(ValueError):fit(data,1)


def test_stop_absorbs_and_history_cannot_change():
    data=panel();data[0]['steps'].append({'history':(0,0,1),'action':1,'probabilities':(1/3,)*3})
    with pytest.raises(ValueError,match='post STOP'):validate(data,2)
    data=panel();data[1]['steps'].append({'history':(1,1,0),'action':0,'probabilities':(1/3,)*3})
    with pytest.raises(ValueError):validate(data,2)


def test_support_is_not_filled_by_oracle():
    m=fit(panel()[:-1],1);a,fallback,q=predict(m,(1,),0)
    assert a==0 and fallback and 2 not in q
    with pytest.raises(ValueError,match='support'):evaluate_holdout(m,panel('test'))


def test_full_probability_vector_required():
    data=panel();data[0]['steps'][0]['probabilities']=(.5,.5,0)
    with pytest.raises(ValueError):fit(data,1)


def test_two_stage_bellman_and_stop_outcomes():
    data=[]
    for a in range(3):
        if a==0:
            data.append({'episode':'s','family':'s','steps':[{'history':(0,), 'action':0,'probabilities':(1/3,)*3}], 'outcome':.4})
        else:
            for b in range(3):
                data.append({'episode':f'{a}{b}','family':f'{a}{b}','steps':[{'history':(0,), 'action':a,'probabilities':(1/3,)*3},{'history':(0,a,1),'action':b,'probabilities':(1/3,)*3}], 'outcome':float(a==2 and b==1)})
    m=fit(data,2);assert predict(m,(0,),0)[0]==2
    assert predict(m,(0,),0)[2][0]==.4
    assert predict(m,(0,2,1),1)[0]==1
    test=copy.deepcopy(data)
    for e in test:e['family']='test'+e['family']
    assert all(s['dr']==1 for s in evaluate_holdout(m,test))
