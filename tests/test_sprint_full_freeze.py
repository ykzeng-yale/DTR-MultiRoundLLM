import pytest
from scripts.validate_sprint_freeze import full_commit

def test_full_commit_only(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess,'check_output',lambda *a,**k:'a'*40+'\n')
    assert full_commit()=='a'*40
    monkeypatch.setattr(subprocess,'check_output',lambda *a,**k:'abcdef0\n')
    with pytest.raises(ValueError):full_commit()
