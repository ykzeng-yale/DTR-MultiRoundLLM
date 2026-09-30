import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('prepare_sprint_release_v1',Path(__file__).resolve().parents[1]/'scripts/prepare_sprint_release_v1.py')
release=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(release)


class SprintReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        self.worker={'_file_sha256':'a'*64,'model_sha256':'b'*64,'build_manifest_sha256':'c'*64,
            'receiver_state_sha256':'d'*64,'server_count':2,'workers':8,
            'owner_deadline_iso':'2026-10-01T02:54:40Z','stage_ids':['dev0','dev1'],
            'grading_ids':['dev0_public','dev2_private'],'contract_sha256':'e'*64,'files':{},
            'qualification_plan_path':'qualified.json','qualification_plan_sha256':'f'*64,
            'output_dir':'worker-results'}
        self.ready={k:self.worker[k] for k in ('model_sha256','build_manifest_sha256','receiver_state_sha256','server_count','owner_deadline_iso')}
        self.ready.update(worker_plan_sha256='a'*64,runtime_manifest_sha256='1'*64,
            attestation_file_sha256='2'*64,receiver_qualification_sha256='3'*64)
        self.config={'mode':'development','pins':{'public_observer':'4'*64,'private_observer':'5'*64,'receiver':'d'*64}}
        self.config['config_sha256']=release.receiver.sha(self.config)
        self.state={'phase':0,'config_sha256':self.config['config_sha256'],'requests':[],'rows':[{'disposition':'active'}]}
        self.save('config',self.config);self.save('state',self.state);self.save('requests',[]);self.save('assignments',[]);self.save('manifest',{})

    def save(self,name,value):
        (self.path/name).write_text(json.dumps(value))

    def test_wrong_qualified_allocation_refused_before_release(self):
        bad=copy.deepcopy(self.ready);bad['worker_plan_sha256']='9'*64
        with self.assertRaisesRegex(ValueError,'worker/model/law'):
            release.stage_plan(self.worker,bad,'dev0',self.path/'config',self.path/'state',self.path/'requests','6'*40)

    def test_early_private_and_cross_scope_refused(self):
        with self.assertRaisesRegex(ValueError,'terminal private'):
            release.grading_plan(self.worker,self.ready,'dev2_private',self.path/'config',self.path/'state',self.path/'assignments',self.path/'manifest',self.path)
        self.save('assignments',[{'scope':'private'}])
        with self.assertRaisesRegex(ValueError,'source-separated'):
            release.grading_plan(self.worker,self.ready,'dev0_public',self.path/'config',self.path/'state',self.path/'assignments',self.path/'manifest',self.path)

    def test_order_and_changed_config_refused(self):
        with self.assertRaisesRegex(ValueError,'ordered request'):
            release.stage_plan(self.worker,self.ready,'dev1',self.path/'config',self.path/'state',self.path/'requests','6'*40)
        self.config['mode']='evaluation';self.save('config',self.config)
        with self.assertRaisesRegex(ValueError,'ordered request'):
            release.stage_plan(self.worker,self.ready,'dev0',self.path/'config',self.path/'state',self.path/'requests','6'*40)


if __name__=='__main__':unittest.main()
