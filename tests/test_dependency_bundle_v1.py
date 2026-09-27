import pytest
from experiments.prompt_choice import dependency_bundle_v1 as b
from experiments.prompt_choice import dependency_sandbox_v1 as s


def test_tree_changes_refused(tmp_path):
    (tmp_path/'module.py').write_text('x=1')
    r=b.inventory(tmp_path);assert b.verify(tmp_path,r['tree_sha256'])==r
    (tmp_path/'module.py').write_text('x=2')
    with pytest.raises(ValueError,match='mismatch'):b.verify(tmp_path,r['tree_sha256'])


def test_hooks_and_links_refused(tmp_path):
    (tmp_path/'x.pth').write_text('import evil')
    with pytest.raises(ValueError,match='hook'):b.inventory(tmp_path)
    (tmp_path/'x.pth').unlink();(tmp_path/'link').symlink_to('/tmp')
    with pytest.raises(ValueError,match='symlink'):b.inventory(tmp_path)


def test_empty_and_size_cap(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='empty'):b.inventory(tmp_path)
    (tmp_path/'x').write_bytes(b'1234');monkeypatch.setattr(b,'MAX_BYTES',3)
    with pytest.raises(ValueError,match='cap'):b.inventory(tmp_path)


def test_profile_only_adds_bundle_read_permission(tmp_path):
    text=s.profile('/p/bin/python','/tmp/run',tmp_path)
    assert '(deny default)' in text and '(deny network*)' in text
    assert '(allow file-read* (subpath '+__import__('json').dumps(str(tmp_path))+'))' in text
    assert '(allow file-write* (subpath '+__import__('json').dumps(str(tmp_path)) not in text


@pytest.mark.parametrize('kw',[{'timeout_s':float('nan')},{'cpu_seconds':True},{'output_cap':0},{'mem_bytes':3<<30}])
def test_limits_before_bundle_read(kw):
    with pytest.raises(ValueError):s.run('pass',bundle='/absent',tree_sha256='0'*64,**kw)


def test_explicit_interpreter_is_forwarded_and_no_bare_fallback(monkeypatch):
    seen=[]
    def info(python):
        seen.append(python);return {'kind':'none'}
    monkeypatch.setattr(s.strict,'sandbox_info',info)
    with pytest.raises(RuntimeError,match='Seatbelt'):
        s.run('pass',bundle='/unused',tree_sha256='0'*64,python='/pinned/python3.9')
    assert seen==['/pinned/python3.9']


def test_framework_root_is_read_only_and_contains_interpreter(tmp_path):
    text=s.profile('/runtime/framework/bin/python','/tmp/run',tmp_path,'/runtime/framework')
    assert '(allow file-read* (subpath "/runtime/framework"))' in text
    assert '(deny process-fork)' in text and '(deny network*)' in text
    assert '(allow file-write* (subpath "/runtime/framework"))' not in text
    for invalid in ['/', '/unrelated']:
        with pytest.raises(ValueError):s.profile('/runtime/framework/bin/python','/tmp/run',tmp_path,invalid)
