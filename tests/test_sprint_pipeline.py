import copy
import unittest

import numpy as np

from experiments.sprint import pipeline_v1 as p
from experiments.sprint import learner_v1 as learner


def tasks():
    return [{'root':'root-'+str(i),'family_id':'family-'+str(i),'root_source_sha256':'a'*64,
             'prompt':'Read integer n and print n.','public_instrument':'ignored/public.json','split':split}
            for i,split in enumerate(('train','tune','eval'))]


def config(mode='development',repeats=32,strategies=None):
    return p.make_config(tasks(),mode=mode,repeats=repeats,seed=1977,
                         pins={k:'a'*64 for k in ('receiver','generator','public_observer','private_observer','source_roster','extractor')},strategies=strategies,
                         randomization=fixed_randomization(tasks(),mode,repeats))


def fixed_randomization(public,mode,repeats):
    units,coins=p.randomization_roster(public,mode,repeats)
    return {'version':'sprint-independent-vector-randomization-v1','mode':mode,
        'component_replicate_nonces':[dict(u,nonce_hex=p.sha(['fixture',u])[:32]) for u in units],
        'development_action_coins':[dict(c,actions=[p.ACTIONS[c['replicate']%3],p.ACTIONS[(c['replicate']//3)%3]]) for c in coins]}


def receipt(state,raw='print(1)',failed=None):
    calls=[]
    for q in state['requests']:
        c={k:copy.deepcopy(q[k]) for k in ('slot','execution_id','grading_unit_id','root','artifact','arm','replicate','phase')}
        c.update(payload_sha256=p.sha(q['payload']),seconds=.01,status='returned',
                 response={'choices':[{'message':{'content':raw}}],
                           'usage':{'prompt_tokens':10,'completion_tokens':5}})
        if failed is not None and q['slot']==failed:
            c.update(status='failed',error='frozen failure',failure_kind='isolated_service_failure');c.pop('response')
        calls.append(c)
    return {'calls':calls,'unattempted':0,'state_unchanged':True,'error':None}


def observe(unit_id,root,program):
    return {'status':'PASS','elapsed_seconds':.001,'case_starts':1,'audit_sha256':'b'*64,'reason':None,
            'primitive_id':p.primitive_id('public',unit_id,root,p.text_sha(program),'a'*64)}


def grade(unit_id,root,program):
    return {'status':'OBSERVED','value':1,'reason':None,'audit_sha256':'c'*64,'elapsed_seconds':.001,'case_starts':1,
            'primitive_id':p.primitive_id('private',unit_id,root,p.text_sha(program),'a'*64)}


class SprintPipelineTests(unittest.TestCase):
    def test_external_randomization_binding_and_no_validation_resampling(self):
        c=config(repeats=3);p.validate_config(c,tasks())
        changed=copy.deepcopy(c['randomization'])
        changed['component_replicate_nonces'][0]['nonce_hex']='0'*32
        other=p.make_config(tasks(),mode='development',repeats=3,seed=1977,pins=c['pins'],randomization=changed)
        self.assertNotEqual(c['randomization_sha256'],other['randomization_sha256'])
        self.assertNotEqual(c['initials'][0]['seed'],other['initials'][0]['seed'])
        self.assertEqual(c['ledger'][0]['actions'],other['ledger'][0]['actions'])
        bad=copy.deepcopy(c);bad['randomization']['development_action_coins'][0]['actions'][0]='not-supported'
        with self.assertRaises(ValueError):p.validate_config(bad,tasks())
        changed=copy.deepcopy(c['randomization']);changed['component_replicate_nonces'].pop()
        with self.assertRaisesRegex(ValueError,'all vector'):p.make_config(tasks(),mode='development',repeats=3,seed=1977,pins=c['pins'],randomization=changed)

    def test_source_split_refusal_and_determinism(self):
        c=config(); self.assertEqual(c,config())
        bad=tasks();bad[1]['family_id']=bad[0]['family_id']
        with self.assertRaisesRegex(ValueError,'family crosses'):
            p.make_config(bad,mode='development',repeats=2,seed=1,pins=c['pins'])

    def test_extractor_single_no_guess(self):
        self.assertEqual(p.extract_program('```python\nprint(1)\n```'),'print(1)\n')
        self.assertEqual(p.extract_program('print(1)'),'print(1)')
        for raw in ('```python\na\n```\n```python\nb\n```','```javascript\na\n```','```python\na'):
            with self.assertRaises(ValueError):p.extract_program(raw)

    def test_terminal_all_assigned_and_stop(self):
        c=config();s=p.initialize(c,tasks());starts=len(s['requests'])
        checks=[]
        def counted(unit_id,root,program):checks.append((unit_id,root,program));return observe(unit_id,root,program)
        s=p.advance(s,receipt(s),c,tasks(),counted)
        stopped=copy.deepcopy([r for r in s['rows'] if r['disposition']=='STOP'])
        self.assertEqual(len(checks),starts)
        with self.assertRaisesRegex(ValueError,'private observation'):
            p.private_assignments(s)
        for phase in (1,2):s=p.advance(s,receipt(s),c,tasks(),counted)
        self.assertEqual(s['phase'],3);self.assertFalse(s['requests'])
        self.assertEqual(len(s['rows']),len(c['ledger']))
        self.assertEqual(stopped,[r for r in s['rows'] if r['assignment_id'] in {a['assignment_id'] for a in stopped}])
        joined=p.terminal_label_join(s,c,tasks(),grade)
        models=p.fit_models(s,joined,c,tasks())
        self.assertEqual(set(models['models']),{'FULL_HISTORY_Q','COMPRESSED_HISTORY_Q'})
        for model in models['models'].values():
            self.assertTrue(all(min(cell.values())>0 for cell in model['action_counts']))

    def test_service_failure_forced_terminal_all_assigned_fit(self):
        c=config();s=p.initialize(c,tasks());s=p.advance(s,receipt(s),c,tasks(),observe)
        failed_id=s['requests'][0]['execution_id'].split(':')[0]
        s=p.advance(s,receipt(s,failed=0),c,tasks(),observe)
        failed=next(r for r in s['rows'] if r['assignment_id']==failed_id)
        self.assertEqual(failed['disposition'],'SERVICE_TERMINAL')
        self.assertTrue(failed['fallback_applied']);self.assertEqual(failed['final_raw'],failed['initial_raw'])
        s=p.advance(s,receipt(s),c,tasks(),observe)
        joined=p.terminal_label_join(s,c,tasks(),grade)
        models=p.fit_models(s,joined,c,tasks())
        self.assertEqual(models['models']['FULL_HISTORY_Q']['sample_weight_metadata']['episode_count'],len(c['ledger']))
        bad=copy.deepcopy(joined);bad['labels'][0]['grade'].update(status='UNAVAILABLE',value=None,reason='observer unavailable')
        with self.assertRaisesRegex(ValueError,'incomplete assignment'):p.fit_models(s,bad,c,tasks())

    def test_shared_initial_and_critique_not_executed(self):
        c=config('tuning',1,list(p.B1)+['SELF_REFINE_ADAPT','REFLEXION_ADAPT','RESAMPLE_SELECT'])
        s=p.initialize(c,tasks());self.assertEqual(len(s['requests']),1)
        count=[]
        def check(unit_id,root,program):count.append(program);return observe(unit_id,root,program)
        s=p.advance(s,receipt(s),c,tasks(),check);self.assertEqual(len(count),1)
        reqs=p.public_assignments(s,receipt(s,'a critique'))
        self.assertTrue(all(r['scope']=='public' for r in reqs))
        phase1_requests=len(s['requests']);s=p.advance(s,receipt(s,'print(2)'),c,tasks(),check)
        self.assertEqual(len(count),1+phase1_requests-2)
        s=p.advance(s,receipt(s,'print(3)'),c,tasks(),check)
        accounting=p.accounting(s)
        self.assertEqual(accounting['physical_receiver']['calls'],1+phase1_requests+5)
        self.assertGreater(sum(r['calls'] for r in accounting['logical_assignments'].values()),accounting['physical_receiver']['calls'])

    def test_response_bindings_and_drift_refused(self):
        c=config();s=p.initialize(c,tasks());r=receipt(s)
        r['calls'][0]['payload_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'assignment'):p.advance(s,r,c,tasks(),observe)
        r=receipt(s);r['state_unchanged']=False
        with self.assertRaisesRegex(ValueError,'receiver drift'):p.advance(s,r,c,tasks(),observe)

    def test_compressed_ignores_only_earlier_history(self):
        c=config();s=p.initialize(c,tasks());s=p.advance(s,receipt(s),c,tasks(),observe)
        first=s['rows'][0]['decisions'][0]['view']
        self.assertTrue(np.array_equal(learner.features(first,'compressed'),learner.features(first,'full')))
        s=p.advance(s,receipt(s,'print(2)'),c,tasks(),observe)
        row=next(r for r in s['rows'] if len(r['decisions'])==2)
        view=row['decisions'][1]['view'];changed=copy.deepcopy(view)
        changed['messages'][2]['content']='a completely changed previous answer'
        self.assertTrue(np.array_equal(learner.features(view,'compressed'),learner.features(changed,'compressed')))
        self.assertFalse(np.array_equal(learner.features(view,'full'),learner.features(changed,'full')))
        changed=copy.deepcopy(view);changed['messages'][-1]['content']='different current answer'
        self.assertFalse(np.array_equal(learner.features(view,'compressed'),learner.features(changed,'compressed')))

    def test_malformed_completed_artifact_is_fail_zero(self):
        c=config();s=p.initialize(c,tasks())
        malformed='```python\nprint(1)\n```\n```python\nprint(2)\n```'
        def forbidden(*args):raise AssertionError('malformed source must never reach child')
        for phase in range(3):s=p.advance(s,receipt(s,malformed),c,tasks(),forbidden)
        self.assertTrue(all(a['status']=='FAIL' for row in s['rows'] for a in row.get('public_audits',[])))
        joined=p.terminal_label_join(s,c,tasks(),forbidden)
        self.assertTrue(all(l['grade']['value']==0 for l in joined['labels']))
        self.assertIsNotNone(p.fit_models(s,joined,c,tasks()))

    def test_identical_program_two_replicates_distinct_grades(self):
        c=config('tuning',2,['STOP','PATCH2']);s=p.initialize(c,tasks())
        for phase in range(3):s=p.advance(s,receipt(s),c,tasks(),observe)
        events=[]
        def counted(unit_id,root,program):events.append((unit_id,root,p.text_sha(program)));return grade(unit_id,root,program)
        joined=p.terminal_label_join(s,c,tasks(),counted)
        self.assertEqual(len(events),2);self.assertEqual(len({x[0] for x in events}),2)
        self.assertEqual(len(p.private_assignments(s)),2)
        self.assertEqual(len({l['grade']['primitive_id'] for l in joined['labels']}),2)

    def test_resource_terminal_is_not_service_deployment_fit(self):
        c=config();s=p.initialize(c,tasks());s=p.advance(s,receipt(s),c,tasks(),observe)
        missing={'calls':[],'unattempted':len(s['requests']),'state_unchanged':True,'global_cap_reason':'owner_deadline'}
        s=p.advance(s,missing,c,tasks(),observe)
        self.assertTrue(any(r['disposition']=='RESOURCE_TERMINAL' for r in s['rows']))
        s=p.advance(s,receipt(s),c,tasks(),observe)
        joined=p.terminal_label_join(s,c,tasks(),grade)
        with self.assertRaisesRegex(ValueError,'incomplete assignment'):p.fit_models(s,joined,c,tasks())

    def test_tuning_administrative_fallback_and_source_drift_refused(self):
        c=config('tuning',2,list(p.B1));s=p.initialize(c,tasks())
        s=p.advance(s,receipt(s),c,tasks(),observe)
        missing={'calls':[],'unattempted':len(s['requests']),'state_unchanged':True,'global_cap_reason':'owner_deadline'}
        s=p.advance(s,missing,c,tasks(),observe);s=p.advance(s,receipt(s),c,tasks(),observe)
        joined=p.terminal_label_join(s,c,tasks(),grade)
        self.assertTrue(all(l['grade']['status']=='OBSERVED' for l in joined['labels']))
        with self.assertRaisesRegex(ValueError,'incomplete tuning policy'):p.select_b1(s,joined,c)
        s=p.initialize(c,tasks())
        for phase in range(3):s=p.advance(s,receipt(s),c,tasks(),observe)
        joined=p.terminal_label_join(s,c,tasks(),grade)
        self.assertEqual(p.select_b1(s,joined,c)['selected_b1'],'STOP')
        altered=copy.deepcopy(joined);altered['labels'][0]['program_sha256']='d'*64
        with self.assertRaisesRegex(ValueError,'artifact drift'):p.select_b1(s,altered,c)

    def test_evaluation_admin_unknown_and_shared_primitive_conflict(self):
        dev=config();train=p.initialize(dev,tasks())
        for phase in range(3):train=p.advance(train,receipt(train),dev,tasks(),observe)
        models=p.fit_models(train,p.terminal_label_join(train,dev,tasks(),grade),dev,tasks())['models']
        # Frozen fixture policy continues once. Its administrative omission
        # cannot be cancelled against an actually completed STOP comparator.
        full=models['FULL_HISTORY_Q']
        full['coefficients'][0]=np.zeros((3,learner.DIM)).tolist();full['coefficients'][0][1][0]=1
        c=p.make_config(tasks(),mode='evaluation',repeats=2,seed=9,pins=dev['pins'],
            strategies=['FULL_HISTORY_Q','COMPRESSED_HISTORY_Q','B1_LOCKED','RESAMPLE_SELECT'],
            model_sha256s={sid:learner.artifact_sha256(m) for sid,m in models.items()},
            selected_b1='STOP',choice_lock_sha256='d'*64,randomization=fixed_randomization(tasks(),'evaluation',2))
        s=p.initialize(c,tasks(),models=models);s=p.advance(s,receipt(s),c,tasks(),observe)
        missing={'calls':[],'unattempted':len(s['requests']),'state_unchanged':True}
        s=p.advance(s,missing,c,tasks(),observe);s=p.advance(s,receipt(s),c,tasks(),observe)
        joined=p.terminal_label_join(s,c,tasks(),grade);summary=p.analyze(s,joined,c)
        self.assertEqual(summary['contrast_completion_envelopes']['B1_LOCKED'],[-1.,0.])
        self.assertEqual(summary['strategy_counts']['FULL_HISTORY_Q']['intended_policy_unavailable'],2)
        with self.assertRaisesRegex(ValueError,'primary order'):p.analyze(s,joined,c,baseline_ids=('RESAMPLE_SELECT','B1_LOCKED'))
        # A complete matched exact program shares the true primitive; contrary
        # receipts claiming the same primitive must be rejected.
        s=p.initialize(c,tasks(),models=models)
        for phase in range(3):s=p.advance(s,receipt(s),c,tasks(),observe)
        joined=p.terminal_label_join(s,c,tasks(),grade)
        altered=copy.deepcopy(joined)
        next(l for l in altered['labels'] if any(r['assignment_id']==l['assignment_id'] and r['strategy']=='B1_LOCKED' for r in s['rows']))['grade']['audit_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'inconsistent shared primitive'):p.analyze(s,altered,c)


if __name__=='__main__':unittest.main()
