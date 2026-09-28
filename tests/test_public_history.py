import copy
import pytest
from experiments.sequential.public_history import public_view,history_sha256,bind_selection

def fixture():
 return dict(messages=[{'role':'user','content':'task'},{'role':'assistant','content':'answer'}],public_observations=[{'message_index':1,'status':'PASS','observer_sha256':'a'*64}],remaining_calls=2,receiver_sha256='b'*64,generator_sha256='c'*64,slate=[{'id':'stop','kind':'STOP','text':'','calls_required':0},{'id':'p','kind':'PROMPT','text':'Check your answer','calls_required':1}])

def test_private_or_future_fields_refused():
 for key in ('private_outcome','family','next_answer','selected_action'):
  r=fixture();r[key]=1
  with pytest.raises(ValueError):public_view(r)

def test_binding_changes_with_history_and_slate_order():
 a=fixture();b=copy.deepcopy(a);b['messages'][1]['content']='different'
 assert history_sha256(a)!=history_sha256(b)
 b=copy.deepcopy(a);b['slate'].reverse();assert history_sha256(a)!=history_sha256(b)
 assert bind_selection(a,[.3,.7],'p')['selected_probability']==.7

def test_future_observation_or_overbudget_prompt_refused():
 r=fixture();r['public_observations'][0]['message_index']=2
 with pytest.raises(ValueError):public_view(r)
 r=fixture();r['remaining_calls']=0
 with pytest.raises(ValueError):public_view(r)

def test_stop_only_at_zero_budget_and_alias_copy():
 r=fixture();r['remaining_calls']=0;r['slate']=r['slate'][:1]
 v=public_view(r);v['messages'][0]['content']='changed';assert r['messages'][0]['content']=='task'
 assert bind_selection(r,[1.],'stop')['selected_probability']==1
 with pytest.raises(ValueError):bind_selection(fixture(),[1.,0.],'p')

def test_malformed_and_duplicate_candidates_refused():
 for slate in ([None],[{}],[{'id':'x'}]):
  r=fixture();r['slate']=slate
  with pytest.raises(ValueError):public_view(r)
 r=fixture();r['slate'][1]['id']='stop'
 with pytest.raises(ValueError):public_view(r)
