from experiments.bouchet.checkpoint_requests_v1 import build

def test_same_prefix_no_private_keys_and_fresh_has_no_constructed_answer():
    tasks=[{'task_id':'r','adapted_public_contract':'Task','signature':'f(x)','private_secret':'NEVER_SEND'}]
    artifacts={'r':[{'kind':'reference','code':'def f(x): return x'}]}
    a=build(tasks,artifacts,{('r','reference'):'PASS'});by={x['arm']:x for x in a}
    assert by['PATCH']['payload']['messages'][:3]==by['RETHINK']['payload']['messages'][:3]
    assert len(by['FRESH']['payload']['messages'])==2
    assert 'NEVER_SEND' not in str(a)
    assert len({x['payload']['seed'] for x in a})==3
    assert build(tasks,artifacts,{('r','reference'):'PASS'})==a
