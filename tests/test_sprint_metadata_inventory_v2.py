import pytest
from scripts.sprint_metadata_inventory_v2 import inventory

def test_complete_counts_nested_and_hardlinked_logical_bytes(tmp_path):
    import os
    (tmp_path/'a').write_bytes(b'abc');(tmp_path/'d').mkdir()
    os.link(tmp_path/'a',tmp_path/'d'/'b')
    assert inventory(tmp_path)=={'complete':True,'files':2,'entries':3,'bytes':6}
    with pytest.raises(ValueError,match='byte cap'):inventory(tmp_path,max_bytes=5)

def test_link_and_incomplete_scan_never_certify_capacity(tmp_path):
    (tmp_path/'a').write_text('a')
    with pytest.raises(TimeoutError):inventory(tmp_path,max_entries=0)
    with pytest.raises(TimeoutError):inventory(tmp_path,seconds=0)
    (tmp_path/'link').symlink_to(tmp_path/'a')
    with pytest.raises(ValueError,match='nonregular'):inventory(tmp_path)

def test_driver_remote_helper_inventory_is_complete_and_link_refusing(tmp_path):
    import json,subprocess,sys
    from scripts.drive_sprint_study_v2 import REMOTE_HELPER
    (tmp_path/'out').mkdir();(tmp_path/'out'/'a').write_bytes(b'abc')
    def run():
        return subprocess.run([sys.executable,'-c',REMOTE_HELPER],input=json.dumps({'root':str(tmp_path),'op':'stats','path':'out'}),text=True,capture_output=True,timeout=5)
    result=run();assert result.returncode==0
    assert json.loads(result.stdout)=={'complete':True,'files':1,'entries':1,'bytes':3}
    (tmp_path/'out'/'link').symlink_to(tmp_path/'out'/'a')
    assert run().returncode!=0
