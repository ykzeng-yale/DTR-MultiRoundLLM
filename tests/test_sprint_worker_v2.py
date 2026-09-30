"""Harmless pure file fixtures only; no server, candidate or task execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import signal

from experiments.sprint import receiver_v1 as r
from experiments.sprint import worker_v1 as old_worker
from experiments.sprint import worker_v2 as w


def fixture(root):
    prior=root/'old';prior.mkdir();out=prior/'worker-results';out.mkdir()
    requests=[]
    for i in range(2):
        requests.append(dict(slot=i,execution_id='initial-'+str(i),grading_unit_id='initial-'+str(i),
            root='root',artifact='sprint-stdio-v1',arm='INITIAL',replicate=i,phase=0,
            payload=dict(messages=[dict(role='user',content='source-only fixture')],stream=False,
                cache_prompt=False,temperature=.7,top_p=.95,top_k=40,min_p=.05,max_tokens=1024,seed=i)))
    def write(path,value):
        path.write_bytes(r.canonical(value)+b'\n');return str(path)
    config=dict(mode='development');config['config_sha256']=r.sha(config)
    cp=prior/'config.json';write(cp,config)
    rp=prior/'requests.json';write(rp,requests)
    state=dict(phase=0,config_sha256=config['config_sha256'],requests=requests)
    st=prior/'state.json';write(st,state)
    original=dict(mode='finite-stage-spool-v1',contract_sha256='a'*64,model_sha256=r.MODEL_SHA256,
        receiver_state_sha256=r.STATE_SHA256,build_manifest_sha256='b'*64,workers=8,server_count=2,
        max_calls=10,max_completion_tokens=10240,max_retained_bytes=1<<30,owner_deadline_iso='2026-10-01T02:54:40Z',
        stage_ids=list(w.STAGES),output_dir='worker-results')
    op=prior/'worker-plan.json';write(op,original)
    sp=dict(stage_id='dev0',contract_sha256='a'*64,workers=8,server_count=2,
        receiver_state_sha256=r.STATE_SHA256,model_sha256=r.MODEL_SHA256,build_manifest_sha256='b'*64,
        freeze_commit='c'*40,files={},state_path=str(st),state_sha256=r.file_sha(st),
        study_config_path=str(cp),study_config_file_sha256=r.file_sha(cp),study_config_sha256=config['config_sha256'],
        requests_path=str(rp),requests_file_sha256=r.file_sha(rp),max_requests_bytes=1<<20,model_lock=None,
        max_calls=2,assignment_cap=20,max_payload_bytes=1<<20,max_completion_tokens=2048,
        requests_canonical_sha256=r.sha(requests),request_timeout_seconds=120)
    spp=prior/'stage-plan.json';write(spp,sp)
    calls=[];starts=[];checks=[]
    for q in requests:
        base={k:q[k] for k in r.REQUEST_KEYS-{'payload'}}
        start=dict(base,status='assigned',payload_sha256=r.sha(q['payload']),server_index=q['payload']['seed']%2)
        response={'choices':[{'finish_reason':'stop','message':{'content':'unexecuted fixture'}}],
                  'usage':{'prompt_tokens':10,'completion_tokens':5}}
        calls.append(dict(start,status='returned',response=response,seconds=.01,**r.response_check(response,10)))
        starts.append(start)
        checks.append(dict(execution_id=q['execution_id'],payload_sha256=r.sha(q['payload']),
            tokens=10,context_tokens=8192,completion_reserved=1024,tokenizer_reserve=16,
            template_prompt_sha256='d'*64))
    jp=out/'journal.jsonl';jp.write_bytes(b''.join(r.canonical(c)+b'\n' for c in reversed(calls)))
    ap=out/'started.jsonl';ap.write_bytes(b''.join(r.canonical(c)+b'\n' for c in starts))
    summary=dict(stage_id='dev0',job_id='old-job',config_sha256=r.file_sha(spp),
        study_config_sha256=config['config_sha256'],state_sha256=r.file_sha(st),
        requests_sha256=r.sha(requests),freeze='c'*40,model_lock=None,state_unchanged=True,error=None,
        global_cap_reason=None,unattempted=0,unattempted_execution_ids=[],service_failed_execution_ids=[],
        attempted_without_journal=[],journal_sha256=r.file_sha(jp),started_sha256=r.file_sha(ap),
        tokenizer_preflight=checks,calls=calls)
    sr=out/'summary.json';write(sr,summary)
    entry=dict(stage_id='dev0',original_job_id='old-job',original_worker_plan_path=str(op),
        original_worker_plan_sha256=r.file_sha(op),stage_plan_path=str(spp),stage_plan_file_sha256=r.file_sha(spp),
        summary_path=str(sr),summary_sha256=r.file_sha(sr),journal_path=str(jp),journal_sha256=r.file_sha(jp),
        started_path=str(ap),started_sha256=r.file_sha(ap),prior_output_dir=str(out),retained_files=[])
    plan=dict(original,mode='finite-stage-spool-v2',server_log_cap_bytes=w.LOG_CAP,resume_completed_stages=[entry])
    rebind_retained(plan)
    return plan


def rebind_retained(plan):
    e=plan['resume_completed_stages'][0]
    e['retained_files']=[dict(path=str(p),sha256=r.file_sha(p),bytes=p.stat().st_size)
                         for p in sorted(Path(e['prior_output_dir']).rglob('*')) if p.is_file()]


class WorkerRepairTests(unittest.TestCase):
    def test_explicit_new_log_cap_and_full_resume_no_initial_regeneration(self):
        with tempfile.TemporaryDirectory() as d,patch.object(w,'RESUME_CALLS',2):
            plan=fixture(Path(d));actual=w.verify_resume(plan)
            self.assertEqual(w.LOG_CAP,128<<20);self.assertEqual(r.LOG_CAP,8<<20)
            self.assertEqual(actual['reserved_calls'],2)
            self.assertEqual(w.remaining_stages(actual),w.STAGES[1:])
            sp=json.loads(Path(plan['resume_completed_stages'][0]['stage_plan_path']).read_bytes())
            self.assertEqual(actual['stage_contracts'],{'dev':sp['study_config_sha256']})
            self.assertEqual(actual['retained_bytes'],sum(x['bytes'] for x in plan['resume_completed_stages'][0]['retained_files']))
            self.assertEqual(w.STAGES,old_worker.STAGES);self.assertEqual(w.GRADING,old_worker.GRADING)

    def test_production_requires_5472_not_tiny_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'5472'):w.verify_resume(fixture(Path(d)))

    def test_changed_raw_hash_and_partial_or_drifted_summary_refused(self):
        with tempfile.TemporaryDirectory() as d,patch.object(w,'RESUME_CALLS',2):
            plan=fixture(Path(d));entry=plan['resume_completed_stages'][0]
            with Path(entry['journal_path']).open('ab') as f:f.write(b'{}\n')
            with self.assertRaisesRegex(ValueError,'journal hash'):w.verify_resume(plan)
        for field,value in [('unattempted',1),('error','cap'),('state_unchanged',False),
                            ('global_cap_reason','receiver_lost')]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as d,patch.object(w,'RESUME_CALLS',2):
                plan=fixture(Path(d));entry=plan['resume_completed_stages'][0]
                p=Path(entry['summary_path']);v=json.loads(p.read_bytes());v[field]=value
                p.write_bytes(r.canonical(v)+b'\n');entry['summary_sha256']=r.file_sha(p);rebind_retained(plan)
                with self.assertRaisesRegex(ValueError,'error-free'):w.verify_resume(plan)

    def test_all_started_and_response_payload_bindings_must_match(self):
        with tempfile.TemporaryDirectory() as d,patch.object(w,'RESUME_CALLS',2):
            plan=fixture(Path(d));entry=plan['resume_completed_stages'][0]
            p=Path(entry['started_path']);rows=[json.loads(l) for l in p.read_bytes().splitlines()]
            rows[1]['payload_sha256']='e'*64;p.write_bytes(b''.join(r.canonical(c)+b'\n' for c in rows))
            entry['started_sha256']=r.file_sha(p)
            p=Path(entry['summary_path']);summary=json.loads(p.read_bytes());summary['started_sha256']=entry['started_sha256']
            p.write_bytes(r.canonical(summary)+b'\n');entry['summary_sha256']=r.file_sha(p);rebind_retained(plan)
            with self.assertRaisesRegex(ValueError,'payload binding'):w.verify_resume(plan)

    def test_no_unlisted_retained_file_or_cap_extension(self):
        with tempfile.TemporaryDirectory() as d,patch.object(w,'RESUME_CALLS',2):
            plan=fixture(Path(d));entry=plan['resume_completed_stages'][0]
            (Path(entry['prior_output_dir'])/'old-server.log').write_bytes(b'old log')
            with self.assertRaisesRegex(ValueError,'all prior owned'):w.verify_resume(plan)
            rebind_retained(plan);self.assertGreater(w.verify_resume(plan)['retained_bytes'],0)
            plan['max_calls']+=1
            with self.assertRaisesRegex(ValueError,'budget law changed'):w.verify_resume(plan)

    def test_cumulative_fixed_log_reserve_plus_resumed_bytes(self):
        with tempfile.TemporaryDirectory() as d,patch.object(w,'RESUME_CALLS',2):
            plan=fixture(Path(d));resume=w.verify_resume(plan)
            fresh=Path(d)/'new-output';fresh.mkdir()
            ledger=w.RetainedLedger(fresh,1<<30,
                fixed_reserve=2*w.LOG_CAP+r.FIXED_RESERVE+resume['retained_bytes'])
            self.assertEqual(ledger.total(),2*(128<<20)+r.FIXED_RESERVE+resume['retained_bytes'])
            (fresh/'external-grade').write_bytes(b'x'*1000)
            ledger.rescan_external()
            self.assertEqual(ledger.total(),2*w.LOG_CAP+r.FIXED_RESERVE+resume['retained_bytes']+1000)
            small=copy.deepcopy(plan);small['max_retained_bytes']=2*w.LOG_CAP
            entry=small['resume_completed_stages'][0];op=Path(entry['original_worker_plan_path'])
            old=json.loads(op.read_bytes());old['max_retained_bytes']=small['max_retained_bytes']
            op.write_bytes(r.canonical(old)+b'\n');entry['original_worker_plan_sha256']=r.file_sha(op)
            with self.assertRaisesRegex(ValueError,'cumulative retained'):w.verify_resume(small)

    def test_all_existing_stage_predecessor_gates_remain(self):
        for stage,previous in w.PREDECESSOR_GRADE.items():
            self.assertFalse(w.stage_released(stage,True,set()))
            self.assertTrue(w.stage_released(stage,True,{previous}))
            self.assertFalse(w.stage_released(stage,False,{previous}))

    def test_raw_post_stage_props_retained_before_state_interpretation(self):
        raw=[{'server':'source fixture 0'},{'server':'source fixture 1'}]
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);ledger=w.RetainedLedger(directory,1<<30)
            with patch.object(w,'receiver_state',side_effect=lambda p:p),patch.object(w.receiver,'STATE_SHA256',r.sha(raw[0])):
                result=w.capture_stage_props(directory,lambda:raw,ledger.publish)
            self.assertFalse(result['state_unchanged'])
            path=directory/'props-after.json'
            self.assertEqual(json.loads(path.read_bytes()),raw)
            self.assertEqual(result['props_after_sha256'],r.file_sha(path))
            self.assertGreater(ledger.total(),ledger.fixed_reserve)
            with patch.object(w,'receiver_state',return_value=raw[0]),patch.object(w.receiver,'STATE_SHA256',r.sha(raw[0])):
                # A fresh stage location is required; immutable publication.
                fresh=directory/'next-stage';fresh.mkdir()
                passed=w.capture_stage_props(fresh,lambda:raw,ledger.publish)
            self.assertTrue(passed['state_unchanged'])

    def test_changed_deadline_requires_exact_committed_bounded_owner_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            old={'owner_deadline_iso':'2026-10-01T02:54:40Z'}
            plan=dict(owner_deadline_iso='2026-10-02T18:00:00Z',contract_sha256='a'*64,wall_seconds=14400)
            with self.assertRaisesRegex(ValueError,'requires exact'):w.verify_owner_extension(old,plan)
            receipt=dict(version='sprint-owner-bounded-deadline-extension-v1',original_deadline_iso=old['owner_deadline_iso'],
                extended_deadline_iso=plan['owner_deadline_iso'],lead_recorded_instruction_iso='2026-09-30T23:08:00Z',
                directive='autonomous remaining research with six-hour checks',contract_sha256='a'*64,
                allocation_seconds=14400,max_gpu_hours=24,freeze_commit='b'*40)
            p=Path(d)/'owner.json';p.write_bytes(r.canonical(receipt))
            plan.update(owner_extension_receipt_path=str(p),owner_extension_receipt_sha256=r.file_sha(p))
            self.assertEqual(w.verify_owner_extension(old,plan),r.file_sha(p))
            plan['owner_deadline_iso']='2026-10-03T18:00:00Z'
            with self.assertRaisesRegex(ValueError,'mismatch'):w.verify_owner_extension(old,plan)
            plan['owner_deadline_iso']=receipt['extended_deadline_iso'];plan['wall_seconds']=28800
            with self.assertRaisesRegex(ValueError,'mismatch'):w.verify_owner_extension(old,plan)
            plan['wall_seconds']=14400;receipt['max_gpu_hours']=48;p.write_bytes(r.canonical(receipt))
            plan['owner_extension_receipt_sha256']=r.file_sha(p)
            with self.assertRaisesRegex(ValueError,'mismatch'):w.verify_owner_extension(old,plan)

    def test_data_only_grade_recount_published_outside_batch_and_refusal_stops(self):
        from scripts import audit_sprint_grading_v1 as auditor
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);gp=root/'plan.json';gp.write_text('{}')
            batch=root/'grade';batch.mkdir();summary=batch/'summary.json';summary.write_text('{}')
            report=root/'grading-reconciliation'/'dev0_public.json'
            known=dict(status='RECONCILED_COMPLETE',safe_to_advance=True,plan_file_sha256=r.file_sha(gp),
                summary_file_sha256=r.file_sha(summary),unreconciled_units=0,assigned_units=2,accounted_units=2,
                model_calls=0,candidate_executions=0,private_values_reported=False)
            prior=signal.getsignal(signal.SIGALRM)
            with patch.object(auditor,'audit_batch',return_value=known) as call:
                self.assertEqual(w.audit_grading(gp,batch,report,w.atomic,timeout_seconds=1),known)
                call.assert_called_once_with(gp,batch,root=Path.cwd())
            self.assertEqual(json.loads(report.read_bytes()),known)
            self.assertEqual(summary.read_text(),'{}')
            self.assertEqual(signal.getsignal(signal.SIGALRM),prior)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
            for error in (ValueError('source metadata mismatch'),TimeoutError('cap')):
                with self.subTest(error=type(error).__name__),patch.object(auditor,'audit_batch',side_effect=error):
                    dest=root/('refusal-'+type(error).__name__+'.json')
                    with self.assertRaisesRegex(RuntimeError,'evidence preserved'):
                        w.audit_grading(gp,batch,dest,w.atomic,timeout_seconds=1)
                    self.assertFalse(json.loads(dest.read_bytes())['safe_to_advance'])
            with patch.object(auditor,'audit_batch',return_value=dict(known,safe_to_advance=False)):
                with self.assertRaisesRegex(RuntimeError,'refused'):
                    w.audit_grading(gp,batch,root/'unsafe.json',w.atomic,timeout_seconds=1)


if __name__=='__main__':unittest.main()
