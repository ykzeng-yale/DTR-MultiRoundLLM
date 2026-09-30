"""Deterministic saved metadata controls; no model/candidate/benchmark runs."""
import copy
import json
from pathlib import Path

import pytest

from scripts import audit_sprint_generation_v1 as a


def fixture(count=3):
    family='family';root='root';messages=[{'role':'user','content':'Frozen public original task'}]
    config={'mode':'development','seed':7,'pins':{'receiver':a.RECEIVER_SHA256},'model_sha256s':{},
            'public_prefix_sha256':{root:a.sha(messages)},'initials':[],'ledger':[],
            'randomization':{'component_replicate_nonces':[]},'strategies':['RANDOMIZED']}
    state={'phase':0,'models':{},'rows':[],'requests':[]}
    for rep in range(count):
        nonce=format(rep,'032x');config['randomization']['component_replicate_nonces'].append({'family_id':family,'replicate':rep,'nonce_hex':nonce})
        iid='initial-'+a.sha(['development',root,rep,7]);aid='assignment-'+a.sha(['development',root,rep,7,'RANDOMIZED'])
        initial={'initial_execution_id':iid,'root':root,'family_id':family,'replicate':rep,'seed':a._seed(nonce,root,'INITIAL',0)}
        ledger={'assignment_id':aid,'initial_execution_id':iid,'root':root,'family_id':family,'replicate':rep,'strategy':'RANDOMIZED','actions':['PATCH','STOP'],
                'seeds':[a._seed(nonce,root,'RANDOMIZED',p) for p in (1,2)]}
        config['initials'].append(initial);config['ledger'].append(ledger);state['rows'].append(dict(ledger,base_messages=messages,disposition='active'))
        state['requests'].append({'slot':rep,'execution_id':iid,'grading_unit_id':iid,'root':root,'artifact':'sprint-stdio-v1','arm':'INITIAL','replicate':rep,'phase':0,
            'payload':{'messages':messages,'stream':False,'cache_prompt':False,'temperature':.7,'top_p':.95,'top_k':40,'min_p':.05,'max_tokens':1024,'seed':initial['seed']}})
    config['randomization_sha256']=a.sha(config['randomization']);config['config_sha256']=a.sha(config);state['config_sha256']=config['config_sha256']
    requests=copy.deepcopy(state['requests']);started=[];journal=[];checks=[]
    for q in requests:
        base={k:q[k] for k in a.IDENTITY_KEYS};base.update(status='assigned',payload_sha256=a.sha(q['payload']),server_index=q['payload']['seed']%2)
        started.append(base)
        text='print(42)';response={'choices':[{'finish_reason':'stop','message':{'content':text}}],'usage':{'prompt_tokens':10,'completion_tokens':4,'total_tokens':14,'prompt_tokens_details':{'cached_tokens':0}}}
        journal.append(dict(base,status='returned',response=response,raw_response_sha256=a.raw_sha(text.encode()),prompt_tokens=10,completion_tokens=4,tokenizer_difference=0,seconds=.2))
        checks.append({'execution_id':q['execution_id'],'payload_sha256':a.sha(q['payload']),'template_prompt_sha256':'a'*64,'tokens':10,'context_tokens':8192,'completion_reserved':1024,'tokenizer_reserve':16})
    plan={'stage_id':'dev0','study_config_sha256':config['config_sha256'],'study_config_file_sha256':a.raw_sha(a.canonical(config)),
          'state_sha256':a.raw_sha(a.canonical(state)),'requests_file_sha256':a.raw_sha(a.canonical(requests)),
          'requests_canonical_sha256':a.sha(requests),'freeze_commit':'b'*40,'model_sha256':a.MODEL_SHA256,'receiver_state_sha256':a.RECEIVER_SHA256,
          'server_count':2,'workers':8,'max_calls':count,'assignment_cap':20,'max_completion_tokens':1024*count,'max_payload_bytes':262144,'model_lock':None,'files':{}}
    summary={'version':a.RECEIVER_VERSION,'stage_id':'dev0','job_id':'27982976','config_sha256':a.raw_sha(a.canonical(plan)),
        'study_config_sha256':config['config_sha256'],'state_sha256':plan['state_sha256'],'requests_sha256':a.sha(requests),
        'freeze':plan['freeze_commit'],'model_lock':None,'state_unchanged':True,'paid_usd':0,'energy_measured':False,'elapsed_seconds':1.2,
        'error':None,'calls':copy.deepcopy(journal),'unattempted':0,'unattempted_execution_ids':[],'tokenizer_preflight':checks}
    obj={'plan':plan,'requests':requests,'state':state,'config':config,'summary':summary,'journal':journal,'started':started}
    rehash(obj)
    return obj


def rehash(obj):
    s=obj['summary'];s['journal_sha256']=a.raw_sha(b''.join(a.canonical(r)+b'\n' for r in obj['journal'])) if obj['journal'] else None
    s['started_sha256']=a.raw_sha(b''.join(a.canonical(r)+b'\n' for r in obj['started'])) if obj['started'] else None
    obj['hashes']={'stage_plan':a.raw_sha(a.canonical(obj['plan'])),'requests':a.raw_sha(a.canonical(obj['requests'])),
                  'state':a.raw_sha(a.canonical(obj['state'])),'config':a.raw_sha(a.canonical(obj['config'])),
                  'summary':a.raw_sha(a.canonical(s)),'journal':s['journal_sha256'],'started':s['started_sha256']}


def audit(o):
    return a.audit_objects(o['plan'],o['requests'],o['state'],o['config'],o['summary'],o['journal'],o['started'],hashes=o['hashes'],expected_job_id='27982976')


def test_complete_generation_all_assignments_hashes_routes_and_costs():
    o=fixture();r=audit(o)
    assert r['assigned']==r['returned']==3 and r['failed']==r['unattempted']==0
    assert r['complete_generation_integrity'] and r['tokenizer_checked']==3
    assert r['reported_prompt_tokens_known']==30 and r['reported_completion_tokens_known']==12
    assert r['attempted_calls_with_unknown_token_cost']==0
    assert all(row['seed']%2==row['server_index'] for row in r['assignment_dispositions'])
    assert 'print(42)' not in json.dumps(r) and 'Frozen public' not in json.dumps(r)


def test_interrupted_start_and_unattempted_are_retained_not_zeros():
    o=fixture();start=o['started'][1]
    recovered=dict(start,status='failed',seconds=None,error='interrupted started request without completed journal',failure_kind='interrupted_inflight_service')
    o['journal']=o['journal'][:1];o['started']=o['started'][:2];o['summary'].update(calls=[o['journal'][0],recovered],unattempted=1,unattempted_execution_ids=[o['requests'][2]['execution_id']],error='global deadline',global_cap_reason='global_wall_or_owner_deadline')
    rehash(o);r=audit(o)
    assert (r['returned'],r['failed'],r['unattempted'])==(1,1,1)
    assert len(r['assignment_dispositions'])==3 and r['recovered_interrupted_rows']==1
    assert r['attempted_calls_with_unknown_token_cost']==r['attempted_calls_with_unknown_latency']==1
    assert r['assignment_dispositions'][1]['completion_tokens'] is None and r['assignment_dispositions'][2]['completion_tokens'] is None
    assert not r['complete_generation_integrity']


def test_fatal_partial_collect_retains_calls_without_invented_preflight():
    o=fixture();o['summary'].pop('tokenizer_preflight');o['summary']['error']='interrupted before collect returned'
    rehash(o);r=audit(o)
    assert r['returned']==3 and len(r['returned_without_saved_tokenizer_evidence'])==3
    assert not r['all_returned_tokenizer_reconciled'] and not r['complete_generation_integrity']


@pytest.mark.parametrize('field,value', [('server_index',9),('grading_unit_id','other'),('raw_response_sha256','f'*64),('prompt_tokens',12),('tokenizer_difference',8)])
def test_corrupted_actual_route_artifact_or_token_metadata_refused(field,value):
    o=fixture();o['journal'][0][field]=value;o['summary']['calls'][0][field]=value;rehash(o)
    with pytest.raises(ValueError):audit(o)


def test_summary_cannot_override_immutable_journal_or_drop_state():
    o=fixture();o['summary']['calls'][0]['seconds']=9;rehash(o)
    with pytest.raises(ValueError,match='immutable'):audit(o)
    o=fixture();o['state']['rows'].pop()
    o['plan']['state_sha256']=a.raw_sha(a.canonical(o['state']));o['summary']['state_sha256']=o['plan']['state_sha256'];o['summary']['config_sha256']=a.raw_sha(a.canonical(o['plan']));rehash(o)
    with pytest.raises(ValueError,match='row loss'):audit(o)


def test_failed_response_preserves_unknown_token_cost_and_failure_kind():
    o=fixture();c=dict(o['started'][0],status='failed',seconds=1.2,error='HTTP failure',failure_kind='isolated_service_failure')
    o['journal'][0]=c;o['summary']['calls'][0]=copy.deepcopy(c);rehash(o);r=audit(o)
    assert r['failure_kind_counts']=={'isolated_service_failure':1} and r['attempted_calls_with_unknown_token_cost']==1
    assert r['reported_completion_tokens_known']==8 and not r['complete_generation_integrity']


def test_exact_source_file_audit_and_no_following_sealed_references(tmp_path):
    o=fixture();o['config']['sealed_reference_not_opened']='/private/never-read';o['config']['config_sha256']=a.sha({k:v for k,v in o['config'].items() if k!='config_sha256'})
    o['state']['config_sha256']=o['config']['config_sha256'];o['plan']['study_config_sha256']=o['summary']['study_config_sha256']=o['config']['config_sha256']
    o['plan']['study_config_file_sha256']=a.raw_sha(a.canonical(o['config']));o['plan']['state_sha256']=o['summary']['state_sha256']=a.raw_sha(a.canonical(o['state']))
    o['summary']['config_sha256']=a.raw_sha(a.canonical(o['plan']));rehash(o)
    paths={}
    for k in ('config','state','requests','summary','plan'):
        path=tmp_path/(k+'.json');path.write_bytes(a.canonical(o[k]));paths[k]=path
    for k in ('journal','started'):
        path=tmp_path/(k+'.jsonl');path.write_bytes(b''.join(a.canonical(row)+b'\n' for row in o[k]));paths[k]=path
    r=a.audit_files(stage_plan=paths['plan'],requests=paths['requests'],state=paths['state'],config=paths['config'],summary=paths['summary'],journal=paths['journal'],started=paths['started'],job_id='27982976',repo_root=tmp_path)
    assert r['complete_generation_integrity'] and r['private_files_read']==0


def test_saved_input_duplicate_keys_and_truncated_journal_are_refused(tmp_path):
    with pytest.raises(ValueError,match='duplicate'):a.strict_json(b'{"x":1,"x":2}')
    with pytest.raises(ValueError,match='nonfinite'):a.strict_json(b'{"x":NaN}')
    p=tmp_path/'journal';p.write_bytes(b'{"execution_id":"e"}')
    with pytest.raises(ValueError,match='trailing'):a.BoundedReader().journal(p)


def test_completed_journal_cannot_silently_drop_latency():
    o=fixture();c=dict(o['started'][0],status='failed',seconds=None,error='failure',failure_kind='isolated_service_failure')
    o['journal'][0]=c;o['summary']['calls'][0]=copy.deepcopy(c);rehash(o)
    with pytest.raises(ValueError,match='measured latency'):audit(o)
