"""Mechanical driver controls; no live SSH, model, task or candidate execution."""
import copy
import json
from pathlib import Path
import shlex

import pytest

from scripts import drive_sprint_study_v1 as d


def test_nested_ssh_keeps_final_command_one_argument_without_local_shell():
    route={'outer':['ssh','-T','-o','BatchMode=yes','mac-aux'],
           'inner':['ssh','-T','-o','BatchMode=yes','bouchet']}
    command="/usr/bin/python3 -c 'print(42)'"
    argv=d.ssh_command(route,command)
    assert argv[:-1]==route['outer'] and shlex.split(argv[-1])==route['inner']+[command]
    assert d.ssh_command({'outer':[],'inner':route['inner']},command)==route['inner']+[command]
    with pytest.raises(ValueError):d.ssh_command({'outer':[],'inner':['sh','-c']},command)


def test_owned_paths_and_immutable_write_refuse_traversal_or_mutation(tmp_path):
    for p in ('/private/answer','work/../private','../outside','.git/config',''):
        with pytest.raises(ValueError):d.relative(p)
    assert d.relative('work/frozen/state.json')=='work/frozen/state.json'
    p=tmp_path/'state.json';d.write(p,{'all_assigned':7});d.write(p,{'all_assigned':7})
    with pytest.raises(ValueError,match='immutable'):d.write(p,{'all_assigned':8})
    (tmp_path/'link').symlink_to(p)
    with pytest.raises(ValueError,match='symlink'):d.owned_bytes(tmp_path,100000)


def test_local_retained_is_global_and_fails_before_another_batch(tmp_path):
    (tmp_path/'batch1').write_bytes(b'x'*40);(tmp_path/'batch2').write_bytes(b'y'*50)
    assert d.owned_bytes(tmp_path,90)==90
    with pytest.raises(ValueError,match='global local retained'):d.owned_bytes(tmp_path,89)


def test_all_failed_generation_kinds_retained_but_only_isolated_service_can_advance():
    report={'unattempted':0,'terminal_error':None,'global_cap_reason':None,
        'receiver_state_unchanged':True,'all_returned_tokenizer_reconciled':True,
        'nonzero_cached_token_execution_ids':[],'failure_kind_counts':{'isolated_service_failure':1}}
    assert d.generation_go(report)
    for key,value in [('unattempted',1),('terminal_error','fatal'),('global_cap_reason','deadline'),
                      ('receiver_state_unchanged',False),('all_returned_tokenizer_reconciled',False),
                      ('nonzero_cached_token_execution_ids',['x']),('failure_kind_counts',{'receiver_lost':1})]:
        bad=copy.deepcopy(report);bad[key]=value
        with pytest.raises(ValueError,match='preserve and stop'):d.generation_go(bad)


def test_grading_caps_reserve_prior_actual_costs_and600_second_audit():
    w={'grading_reconciliation_seconds':600,'server_log_cap_bytes':128<<20,'max_case_starts':4000000,
       'max_grading_cpu_seconds':57000,'max_retained_bytes':100<<30}
    used=[{'case_starts':500000,'cpu_seconds':12000}]
    c=d.grade_caps(w,used,2000,3<<30,28560852)
    assert c['max_case_starts']==3500000 and c['max_cpu_seconds']==14000 and c['max_wall_seconds']==1250
    assert c['max_retained_bytes']==20<<30
    with pytest.raises(ValueError,match='exhausted'):d.grade_caps(w,used,700,3<<30,28560852)
    with pytest.raises(ValueError,match='exhausted'):d.grade_caps(w,used,2000,50<<30,28560852)


def test_actual_job_identity_account_directory_and_nontruncated_name():
    spec={'job_id':'27989272','job_name':'dtr-scientific-sprint-h100-v2','account':'pi_gt353',
          'partition':'gpu_h100','user':'yz2324','remote_dir':'/nfs/owned/study'}
    raw={'accounting':'27989272|dtr-scientific-sprint-h100-v2|pi_gt353|gpu_h100|yz2324|PENDING|0:0|0|240|Unknown|Unknown|\n',
         'queue':'27989272|dtr-scientific-sprint-h100-v2|pi_gt353|gpu_h100|yz2324|PENDING|0:00|4:00:00|Priority|/nfs/owned/study\n',
         'observed_unix':1}
    assert d.parse_job(raw,spec)['state']=='PENDING'
    for key,new in [('queue',raw['queue'].replace('/nfs/owned/study','/nfs/peer')),('accounting',raw['accounting'].replace('pi_gt353','peer'))]:
        bad=copy.deepcopy(raw);bad[key]=new
        with pytest.raises(ValueError):d.parse_job(bad,spec)


def test_receiver_metadata_gate_requires_token_usage_hash_seed_template_and_no_cache():
    request={'execution_id':'x','payload':{'messages':[],'seed':7}}
    check={'execution_id':'x','payload_sha256':d.sha(request['payload']),'template_prompt_sha256':'a'*64,
           'tokens':5,'context_tokens':8192,'completion_reserved':1024,'tokenizer_reserve':16}
    call={'response':{'choices':[{'finish_reason':'stop','message':{'content':'42'}}],
                     'usage':{'prompt_tokens':5,'completion_tokens':2,'total_tokens':7,'prompt_tokens_details':{'cached_tokens':0}}},
          'raw_response_sha256':d.hashlib.sha256(b'42').hexdigest(),'prompt_tokens':5,'completion_tokens':2,
          'tokenizer_difference':0,'seconds':.1}
    d.audit_receiver_record(call,request,check)
    for field,value in [('raw_response_sha256','f'*64),('tokenizer_difference',2),('seconds',None),('seconds',float('inf'))]:
        bad=copy.deepcopy(call);bad[field]=value
        with pytest.raises(ValueError):d.audit_receiver_record(bad,request,check)
    bad=copy.deepcopy(call);bad['response']['usage']['prompt_tokens_details']['cached_tokens']=1
    with pytest.raises(ValueError):d.audit_receiver_record(bad,request,check)


def test_pending_queue_duration_does_not_consume_running_handoff_window(monkeypatch):
    # A long queue wait must not make the first running file handoff time out.
    class Transport:
        count=0
        def exists(self,path):self.count+=1;return self.count==4
    driver=object.__new__(d.Driver);driver.transport=Transport();driver.worker={'stage_wait_seconds':3600,'owner_deadline_iso':'2099-01-01T00:00:00Z'}
    driver.plan={'caps':{'poll_seconds':30}};driver.verify=lambda:None
    states=iter(['PENDING','PENDING','RUNNING']);driver.owned_job=lambda:{'state':next(states)}
    clock=iter([50000,50001]);monkeypatch.setattr(d.time,'monotonic',lambda:next(clock))
    monkeypatch.setattr(d.time,'sleep',lambda _:None)
    driver.wait('worker-results/ready.json')


def test_no_replay_and_all_nine_stage_order_with_actual_fit_and_locked_eval(monkeypatch,tmp_path):
    """Wire-level whole workflow with pure deterministic helper substitutes."""
    spec={'output_dir':'work/driver','development_config':'dev.json','development0_state':'dev0.json',
          'tuning_config':'tune.json','tuning0_state':'tune0.json','evaluation_randomization':'rng.json','evaluation_namespace_seed':2026093000}
    for name,obj in {'dev.json':{'pins':{'public_observer':'a'*64},'mode':'development'},'tune.json':{'mode':'tuning'},
                     'dev0.json':{'phase':0,'mode':'development'},'tune0.json':{'phase':0,'mode':'tuning'},'rng.json':{'already_drawn':True}}.items():d.write(tmp_path/name,obj)
    driver=object.__new__(d.Driver);driver.repo=tmp_path;driver.spec=spec;driver.public=['whole frozen roster'];driver.worker={'contract_sha256':'f'*64}
    driver.state={'done':{}};log=[]
    def data(name,value):path='work/driver/'+name+'.json';d.write(tmp_path/path,value);return path
    driver.data=data
    driver.metadata_freeze=lambda name,paths,extra=None:(log.append(('freeze',name)), 'b'*40)[1]
    def once(k,fn):
        if k not in driver.state['done']:driver.state['done'][k]=fn()
        return driver.state['done'][k]
    driver.once=once
    driver.resume_dev0=lambda:(log.append(('preserve','dev0')),'original-terminal.json')[1]
    driver.generate=lambda stage,config,state,lock=None:(log.append(('generation',stage,lock)),stage+'-receipt.json')[1]
    def phase(stage,config,state,receipt,lock=None):
        log.append(('public_advance',stage));return data(stage[:-1]+str(int(stage[-1])+1)+'-state',{'phase':int(stage[-1])+1,'mode':stage[:-1]})
    driver.phase=phase
    def terminal(prefix,config,state):
        assert d.read(tmp_path/state)['phase']==3;log.append(('terminal_private',prefix));return data(prefix+'-labels',{'labels':[prefix]})
    driver.terminal=terminal
    def fit(state,labels,config,tasks):
        assert log[-1]==('terminal_private','dev');log.append(('fit_real_dev',True))
        return {'models':{'FULL_HISTORY_Q':{},'COMPRESSED_HISTORY_Q':{}},'model_sha256s':{'FULL_HISTORY_Q':'1'*64,'COMPRESSED_HISTORY_Q':'2'*64}}
    def select(state,labels,config):
        assert log[-1]==('terminal_private','tune');log.append(('tune_choice',True));return {'selected_b1':'PATCH2'}
    def config(tasks,**kw):
        assert kw['randomization']=={'already_drawn':True} and kw['repeats']==32 and kw['model_sha256s']['FULL_HISTORY_Q']=='1'*64
        log.append(('initialize_existing_eval_draws',True));return kw
    monkeypatch.setattr(d.pipeline,'fit_models',fit);monkeypatch.setattr(d.pipeline,'select_b1',select);monkeypatch.setattr(d.pipeline,'make_config',config)
    monkeypatch.setattr(d.pipeline,'initialize',lambda config,tasks,models:{'phase':0,'mode':'eval'})
    monkeypatch.setattr(d.inference,'policy_lock',lambda config:'c'*64)
    monkeypatch.setattr(d.inference,'make_plan',lambda config,tasks,conditioning:{'plan_sha256':'d'*64,'conditioning':conditioning})
    monkeypatch.setattr(d.inference,'analyze',lambda *a:{'decision':{'scoped_verdict':'INCONCLUSIVE'}})
    monkeypatch.setattr(d.pipeline,'accounting',lambda s:{'unknown_energy':True})
    monkeypatch.setattr(d.pipeline,'analyze',lambda *a:{'secondary_only':True})
    result=driver.modes()
    assert [x[1] for x in log if x[0]=='generation']==list(d.STAGES[1:])
    assert sum(x==('preserve','dev0') for x in log)==1
    assert [x[1] for x in log if x[0]=='terminal_private']==['dev','tune','eval']
    evstart=next(i for i,x in enumerate(log) if x[:2]==('generation','eval0'))
    assert any(x[:2]==('freeze','evaluation_before_calls') for x in log[:evstart])
    assert all(x[2]['freeze_commit']=='b'*40 and x[2]['selected_b1']=='PATCH2' for x in log if x[0]=='generation' and x[1].startswith('eval'))
    # A process checkpoint recovery never fits, chooses, draws or generates twice.
    before=len(log);assert driver.modes()==result;assert len(log)==before
    assert not any(x[:2]==('generation','dev0') for x in log)


def test_reported_trusted_pass_cannot_override_actual_output_or_bootstrap():
    source='print(42)';stdin=b'';expected=b'42\n';definition=(source,stdin,expected,'PASS',None)
    h=lambda raw:d.hashlib.sha256(raw).hexdigest();host={'node':'fresh-actual-node'}
    row={'assignment':0,'fixture':'preflight_correct','source_sha256':h(source.encode()),'stdin_sha256':h(stdin),
         'expected_stdout_sha256':h(expected),'stdin_bytes':0,'expected_stdout_bytes':3,'passed':True,
         'receipt':{'status':'PASS','reason':None,'execution':{'cleanup':True,'payload_started':True,
             'runtime_manifest_sha256':'a'*64,'caps':d.execution.DEFAULT_CAPS,'source_sha256':h(source.encode()),'stdin_sha256':h(stdin),
             'host_binding':host,'bootstrap_receipt':{'nonce':'1'*32,'source_sha256':h(source.encode()),
                 'denied':['socket','fork','clone','execve','unshare','mount','ptrace','memfd_create']},
             'disposition':'completed','returncode':0,'outcome_available':True,'stdout_sha256':h(expected),'stdout_bytes':3,'seconds':.1}}}
    ready={'runtime_manifest_sha256':'a'*64};att={'host_binding':host}
    d.audit_qualification_fixture(row,0,'preflight_correct',definition,ready,att,d.execution.DEFAULT_CAPS)
    for key,value in [('stdout_sha256','f'*64),('stdout_bytes',4),('payload_started',False),('cleanup',False)]:
        bad=copy.deepcopy(row);bad['receipt']['execution'][key]=value
        with pytest.raises(ValueError):d.audit_qualification_fixture(bad,0,'preflight_correct',definition,ready,att,d.execution.DEFAULT_CAPS)
    bad=copy.deepcopy(row);bad['receipt']['execution']['bootstrap_receipt']['denied'].remove('memfd_create')
    with pytest.raises(ValueError):d.audit_qualification_fixture(bad,0,'preflight_correct',definition,ready,att,d.execution.DEFAULT_CAPS)


def test_trusted_remote_writer_is_exclusive_idempotent_and_never_overwrites_original_inputs(tmp_path):
    import subprocess
    import sys
    root=tmp_path/'owned';root.mkdir();raw=b'{"frozen":true}\n'
    payload={'root':str(root),'op':'write','path':'work/driver/prepared/state.json','write_prefix':'work/driver',
             'spool_prefix':'spool','raw':d.base64.b64encode(raw).decode(),'sha256':d.hashlib.sha256(raw).hexdigest(),'cap':4096}
    def run(value):return subprocess.run([sys.executable,'-c',d.REMOTE_HELPER],input=d.canonical(value),capture_output=True)
    assert run(payload).returncode==0 and run(payload).returncode==0
    assert (root/payload['path']).read_bytes()==raw
    changed=dict(payload,raw=d.base64.b64encode(b'changed').decode(),sha256=d.hashlib.sha256(b'changed').hexdigest())
    assert run(changed).returncode!=0 and (root/payload['path']).read_bytes()==raw
    outside=dict(payload,path='work/sprint_preparation/original-config.json')
    assert run(outside).returncode!=0 and not (root/outside['path']).exists()
    release=dict(payload,path='spool/dev1.ready.json')
    assert run(release).returncode==run(release).returncode==0
    assert run(dict(changed,path=release['path'])).returncode!=0


def test_unsafe_source_spec_key_is_refused_before_file_reads(tmp_path):
    with pytest.raises(ValueError,match='specification'):d.make_plan({'choose_new_population':True},tmp_path)


def test_stream_retrieval_refuses_symlink_and_global_retained_overrun(monkeypatch,tmp_path):
    import io
    import tarfile
    def archive(link=False):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w') as t:
            item=tarfile.TarInfo('worker-results/batch.json');item.size=20
            if link:item.type=tarfile.SYMTYPE;item.linkname='/private/answer';t.addfile(item)
            else:t.addfile(item,io.BytesIO(b'x'*20))
        return stream.getvalue()
    class Process:
        def __init__(self,*a,**kw):self.stdout=io.BytesIO(archive());self.code=None
        def poll(self):return self.code
        def wait(self,timeout=None):self.code=0;return 0
        def kill(self):self.code=-1
    plan={'spec':{'remote_dir':'/nfs/owned','ssh_route':{'outer':[],'inner':['ssh','bouchet']}},
          'caps':{**d.LOCAL_CAPS,'retained_bytes':30,'file_bytes':100}}
    tr=d.Transport(plan);tr.local_output=tmp_path;monkeypatch.setattr(d.subprocess,'Popen',Process)
    (tmp_path/'old').write_bytes(b'z'*20)
    with pytest.raises(ValueError,match='global local retained'):tr.fetch(['worker-results'],tmp_path/'raw')
    assert not (tmp_path/'raw'/'worker-results'/'batch.json').exists()
    (tmp_path/'old').unlink()
    class Link(Process):
        def __init__(self,*a,**kw):self.stdout=io.BytesIO(archive(True));self.code=None
    monkeypatch.setattr(d.subprocess,'Popen',Link)
    with pytest.raises(ValueError,match='regular evidence'):tr.fetch(['worker-results'],tmp_path/'raw2')
