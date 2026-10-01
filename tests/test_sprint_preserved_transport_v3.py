import json,subprocess,sys
import pytest
from scripts import drive_sprint_study_v3 as d

def test_preserved_inputs_are_verified_without_crossing_write_boundary(tmp_path):
    p=tmp_path/'f';p.write_bytes(b'original')
    t=d.Transport({'spec':{'output_dir':'work/new'},'caps':{'file_bytes':1024}});t.worker={'spool_dir':'spool'}
    calls=[];t.rpc=lambda op,**k:calls.append((op,k))
    t.upload('work/old/locked.json',p);t.upload('work/new/next.json',p)
    assert [op for op,_ in calls]==['verify','write']
    assert 'raw' not in calls[0][1] and calls[0][1]['sha256']==d.digest(p)

def test_readonly_verification_refuses_changed_or_missing_preserved_bytes(tmp_path):
    p=tmp_path/'locked';p.write_bytes(b'original')
    payload={'root':str(tmp_path),'op':'verify','path':'locked','sha256':d.digest(p),'cap':1024}
    def run():return subprocess.run([sys.executable,'-c',d.REMOTE_HELPER],input=json.dumps(payload),text=True,capture_output=True,timeout=5)
    r=run();assert r.returncode==0 and json.loads(r.stdout)['read_only']
    p.write_bytes(b'changed');assert run().returncode!=0
    p.unlink();assert run().returncode!=0

def test_three_epoch_inventory_counts_and_requires_latest_failure_diagnostics(tmp_path):
    from experiments.sprint.recovery_v2 import verify_manifest
    import hashlib
    roots=[tmp_path/str(i) for i in range(3)]
    for p in roots:p.mkdir()
    f=roots[2]/'failed-summary';f.write_bytes(b'failure')
    m={'roots':[str(p) for p in roots],'files':[{'path':str(f),'bytes':7,'sha256':hashlib.sha256(b'failure').hexdigest()}]}
    assert verify_manifest(m)==7
    m['files']=[]
    with pytest.raises(ValueError,match='omissions'):verify_manifest(m)
