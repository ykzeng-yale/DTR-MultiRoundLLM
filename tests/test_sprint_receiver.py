import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from experiments.sprint import receiver_v1 as r
from experiments.sprint import worker_v1 as w


def request(i):
    return {'slot':i,'execution_id':'execution-'+str(i),'grading_unit_id':'unit-'+str(i),
        'root':'root','artifact':'sprint-stdio-v1','arm':'INITIAL','replicate':i,'phase':0,
        'payload':{'messages':[{'role':'user','content':'public original task'}],
                   'stream':False,'cache_prompt':False,'temperature':.7,'top_p':.95,
                   'top_k':40,'min_p':.05,'max_tokens':1024,'seed':i}}


def plan(requests):
    return {'max_calls':len(requests),'assignment_cap':20,'max_payload_bytes':1<<20,
            'max_completion_tokens':1024*len(requests),'requests_canonical_sha256':r.sha(requests),
            'request_timeout_seconds':120}


def response():
    return {'choices':[{'finish_reason':'stop','message':{'content':'print(1)'}}],
            'usage':{'prompt_tokens':10,'completion_tokens':5}}


class ReceiverTests(unittest.TestCase):
    def test_exact_decoding_and_assignment_binding(self):
        requests=[request(0),request(1)];r.validate_requests(requests,plan(requests))
        bad=copy.deepcopy(requests);bad[1]['execution_id']=bad[0]['execution_id']
        with self.assertRaisesRegex(ValueError,'identities'):r.validate_requests(bad,plan(bad))
        bad=copy.deepcopy(requests);bad[0]['payload']['cache_prompt']=True
        with self.assertRaisesRegex(ValueError,'decoding'):r.validate_requests(bad,plan(bad))
        wrong=plan(requests);wrong['requests_canonical_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'binding'):r.validate_requests(requests,wrong)

    def test_tokenizer_refuses_no_truncation(self):
        def http(path,body,timeout):
            return {'prompt':'unaltered'} if path=='/apply-template' else {'tokens':[1]*7200}
        with self.assertRaisesRegex(ValueError,'no truncation'):r.preflight(http,request(0))
        actual=response();actual['usage']['prompt_tokens']=40
        with self.assertRaisesRegex(ValueError,'count drift'):r.response_check(actual,10)
        actual=response();actual['usage']['completion_tokens']=1025
        with self.assertRaisesRegex(ValueError,'token accounting'):r.response_check(actual,10)

    def test_four_slot_failures_retained_without_global_abort(self):
        requests=[request(i) for i in range(8)];active=0;maximum=0;lock=threading.Lock();starts=[];journal=[]
        def http(path,body,timeout):
            nonlocal active,maximum
            if path=='/apply-template':return {'prompt':'public'}
            if path=='/tokenize':return {'tokens':[1]*10}
            with lock:active+=1;maximum=max(maximum,active)
            try:
                time.sleep(.005)
                if body['seed']==3:raise RuntimeError('one service failure')
                return response()
            finally:
                with lock:active-=1
        result=r.collect(requests,plan(requests),http,lambda:True,journal.append,lambda:1000,
                         threading.Event(),on_start=lambda rec:starts.append(rec['execution_id']))
        self.assertEqual(maximum,4);self.assertEqual(len(starts),8);self.assertEqual(len(journal),8)
        self.assertEqual(result['unattempted'],0);self.assertEqual(result['calls'][3]['status'],'failed')
        self.assertEqual(result['calls'][4]['status'],'returned')
        self.assertEqual([c['execution_id'] for c in result['calls']],[q['execution_id'] for q in requests])

    def test_prewrite_capacity_stops_without_starting(self):
        requests=[request(0)]
        def http(path,body,timeout):return {'prompt':'p'} if path=='/apply-template' else {'tokens':[1]*10}
        starts=[]
        result=r.collect(requests,plan(requests),http,lambda:True,lambda rec:None,lambda:1000,
                         threading.Event(),on_start=starts.append,can_submit=lambda n:False)
        self.assertEqual(starts,[]);self.assertEqual(result['unattempted'],1)

    def test_two_instances_eight_slots_and_same_seed_routing(self):
        requests=[request(i) for i in range(16)]
        active=[0,0];maximum=[0,0];routes={};lock=threading.Lock();journal=[]
        def transport(q):
            instance=q['payload']['seed']%2
            def http(path,body=None,timeout=3):
                with lock:routes.setdefault(q['execution_id'],[]).append((path,instance))
                if path=='/apply-template':return {'prompt':'public'}
                if path=='/tokenize':return {'tokens':[1]*10}
                with lock:active[instance]+=1;maximum[instance]=max(maximum[instance],active[instance])
                try:time.sleep(.01);return response()
                finally:
                    with lock:active[instance]-=1
            return http
        cfg=plan(requests);cfg.update(workers=8,server_count=2)
        result=r.collect(requests,cfg,None,lambda:True,journal.append,lambda:1000,
                         threading.Event(),transport_factory=transport)
        self.assertEqual(maximum,[4,4]);self.assertEqual(len(result['calls']),16)
        for q in requests:
            self.assertEqual([x[0] for x in routes[q['execution_id']]],['/apply-template','/tokenize','/v1/chat/completions'])
            self.assertEqual({x[1] for x in routes[q['execution_id']]},{q['payload']['seed']%2})
        self.assertEqual(len(w.synthetic_requests(100,2)),18)
        self.assertEqual([sum(q['payload']['seed']%2==i for q in w.synthetic_requests(100,2)) for i in range(2)],[9,9])

    def test_ordered_grading_gate_even_when_stage_file_exists(self):
        self.assertTrue(w.stage_released('dev0',True,set()))
        self.assertFalse(w.stage_released('dev1',True,set()))
        self.assertTrue(w.stage_released('dev1',True,{'dev0_public'}))
        self.assertFalse(w.stage_released('eval0',True,{'tune1_public'}))
        self.assertTrue(w.stage_released('eval0',True,{'tune2_private'}))
        self.assertFalse(w.stage_released('eval0',False,{'tune2_private'}))

    def test_random_routing_imbalance_cannot_queue_eight_on_one_instance(self):
        requests=[request(i) for i in range(8)]
        for q in requests:q['payload']['seed']*=2
        active=0;maximum=0;lock=threading.Lock()
        def http(path,body=None,timeout=3):
            nonlocal active,maximum
            if path=='/apply-template':return {'prompt':'public'}
            if path=='/tokenize':return {'tokens':[1]*10}
            with lock:active+=1;maximum=max(maximum,active)
            try:time.sleep(.01);return response()
            finally:
                with lock:active-=1
        cfg=plan(requests);cfg.update(workers=8,server_count=2)
        result=r.collect(requests,cfg,http,lambda:True,lambda rec:None,lambda:1000,threading.Event(),transport_factory=lambda q:http)
        self.assertEqual(maximum,4);self.assertEqual(len(result['calls']),8)
        self.assertTrue(all(c['server_index']==0 for c in result['calls']))

    def test_stage_spool_freeze_state_and_worker_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            state=root/'state.json';state.write_text('{"phase":0}')
            config={'mode':'development'};config['config_sha256']=r.sha(config)
            cp=root/'config.json';cp.write_bytes(r.canonical(config))
            requests=[request(0)];rp=root/'requests.json';rp.write_bytes(r.canonical(requests))
            sp=plan(requests);sp.update(stage_id='dev0',contract_sha256='a'*64,workers=4,
                receiver_state_sha256=r.STATE_SHA256,model_sha256=r.MODEL_SHA256,build_manifest_sha256='b'*64,
                freeze_commit='c'*40,files={},state_path=str(state),state_sha256=r.file_sha(state),
                study_config_path=str(cp),study_config_file_sha256=r.file_sha(cp),study_config_sha256=config['config_sha256'],
                requests_path=str(rp),requests_file_sha256=r.file_sha(rp),max_requests_bytes=1<<20,model_lock=None)
            spp=root/'plan.json';spp.write_bytes(r.canonical(sp))
            global_plan={'contract_sha256':'a'*64,'build_manifest_sha256':'b'*64,'_actual_worker_plan_sha256':'d'*64}
            release={'stage_id':'dev0','stage_plan_path':str(spp),'stage_plan_file_sha256':r.file_sha(spp),'worker_plan_sha256':'d'*64}
            actual,loaded=w.stage_inputs('dev0',release,global_plan)
            self.assertEqual(loaded,requests)
            bad=dict(release,worker_plan_sha256='e'*64)
            with self.assertRaisesRegex(ValueError,'release'):w.stage_inputs('dev0',bad,global_plan)
            state.write_text('{"phase":1}')
            with self.assertRaisesRegex(ValueError,'state drift'):w.stage_inputs('dev0',release,global_plan)

    def test_relative_qualification_recount_uses_absolute_canary_fixture(self):
        from experiments.measurement_sprint_v3 import execution_v3 as execution
        from experiments.containment import stdio_sprint_qualification_v3 as qualification
        # Pure source/hash recount: no qualifier or fixture payload executes.
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            output=Path(directory);relative=output.relative_to(Path.cwd())
            qp=output/'plan.json';qp.write_text('{"caps":{}}')
            (output/'host-canary').write_text('owned qualification sentinel; not mounted\n')
            def definitions(caps,canary):
                return {name:('trusted-literal:'+str(canary),b'',b'','PASS',None)
                        for name in execution.REQUIRED_FIXTURES}
            known=definitions({},(output/'host-canary').resolve());rows=[]
            for index,name in enumerate(execution.REQUIRED_FIXTURES):
                source,stdin,expected,status,reason=known[name]
                rows.append({'assignment':index,'fixture':name,'source_sha256':w.hashlib.sha256(source.encode()).hexdigest(),
                    'stdin_sha256':w.hashlib.sha256(stdin).hexdigest(),'expected_stdout_sha256':w.hashlib.sha256(expected).hexdigest(),
                    'stdin_bytes':0,'expected_stdout_bytes':0,'receipt':{'status':status,'execution':{'cleanup':True}},'passed':True})
            (output/'journal.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
            att={'plan_sha256':r.file_sha(qp),'job_id':'fixture-job'}
            with patch.dict(w.os.environ,{'SLURM_JOB_ID':'fixture-job'}),patch.object(execution,'verify_attestation',return_value=att),patch.object(qualification,'fixtures',side_effect=definitions):
                self.assertEqual(w.qualification_check(relative,qp),att)

    def test_retained_counter_avoids_per_call_walk_and_counts_external_grader(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ledger=w.RetainedLedger(root,10000,fixed_reserve=100)
            # Every receiver start/journal/control charge is constant-time. A
            # tree walk would fail this test; harmless files only are written.
            with patch.object(Path,'rglob',side_effect=AssertionError('no per-call tree walk')):
                self.assertTrue(ledger.fits(200))
                ledger.append(root/'journal.jsonl',b'call\n',copies=2)
                ledger.append(root/'started.jsonl',b'start\n')
                ledger.publish(root/'control.json',{'ready':True})
                self.assertEqual(ledger.scans,0)
            before=ledger.total()
            (root/'external-grader-audit.json').write_bytes(b'g'*1000)
            actual=ledger.rescan_external()
            self.assertEqual(ledger.scans,1);self.assertGreater(ledger.total(),before)
            self.assertGreaterEqual(ledger.total(),actual+100)
            (root/'external-grader-audit.json').unlink()
            ledger.rescan_external()
            self.assertGreaterEqual(ledger.total(),actual+100)
            with self.assertRaisesRegex(RuntimeError,'pre-write'):ledger.append(root/'refused',b'x'*10000)
            self.assertFalse((root/'refused').exists())


if __name__=='__main__':unittest.main()
