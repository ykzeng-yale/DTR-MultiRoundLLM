"""Profile construction only: no sandbox, candidate or reference is launched."""
import json
from pathlib import Path

import pytest

from experiments.prompt_choice import strict_sandbox_v2 as sandbox


def runtime(tmp_path):
    root = tmp_path/'dedicated-cpython'
    binary = root/'bin/python3.12'
    binary.parent.mkdir(parents=True)
    binary.write_text('fixture, never executed')
    binary.chmod(0o700)
    encodings = root/'lib/python3.12/encodings'
    encodings.mkdir(parents=True)
    (encodings/'__init__.py').write_text('')
    return binary, root


def test_dedicated_runtime_is_canonical_and_other_files_are_not_allowed(tmp_path):
    binary, root = runtime(tmp_path)
    alias = tmp_path/'python-alias'
    alias.symlink_to(binary)
    text = sandbox.profile(str(alias), '<OWN_RUN_DIRECTORY>')
    assert '(subpath '+json.dumps(str(root))+')' in text
    assert '(literal '+json.dumps(str(binary))+')' in text
    assert '(subpath "/")' not in text
    assert '(subpath '+json.dumps(str(tmp_path))+')' not in text
    assert '(deny process-fork)' in text and '(deny network*)' in text


@pytest.mark.parametrize('path', ['/usr/bin/python3', 'python3', '/usr/local/bin/python3'])
def test_shared_or_relative_interpreter_refused_before_profile(path):
    with pytest.raises((ValueError, FileNotFoundError)):
        sandbox.profile(path, '<OWN_RUN_DIRECTORY>')


def test_link_to_shared_system_interpreter_is_refused(tmp_path):
    link = tmp_path/'python'
    link.symlink_to('/usr/bin/python3')
    with pytest.raises((ValueError, FileNotFoundError)):
        sandbox.profile(str(link), '<OWN_RUN_DIRECTORY>')


def test_runtime_cannot_cover_project_or_home(tmp_path, monkeypatch):
    binary, root = runtime(tmp_path)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: root))
    with pytest.raises(ValueError, match='Shared/home/project'):
        sandbox.profile(str(binary), '<OWN_RUN_DIRECTORY>')


def test_missing_stdlib_or_nonexecutable_runtime_refused(tmp_path):
    binary, root = runtime(tmp_path)
    binary.chmod(0o600)
    with pytest.raises(ValueError, match='bin layout'):
        sandbox.validated_runtime(str(binary))
    binary.chmod(0o700)
    (root/'lib/python3.12/encodings/__init__.py').unlink()
    with pytest.raises(ValueError, match='standard library'):
        sandbox.validated_runtime(str(binary))


def test_run_directory_cannot_grant_shared_writes(tmp_path, monkeypatch):
    binary, root = runtime(tmp_path)
    owned = tmp_path/'runs'
    owned.mkdir()
    monkeypatch.setattr(sandbox, 'base_dir', lambda: str(owned))
    run = owned/'run_fixture'
    run.mkdir()
    text = sandbox.profile(str(binary), str(run))
    assert '(allow file-write* (subpath '+json.dumps(str(run))+')' in text
    for bad in ('/', str(tmp_path), str(owned), 'relative'):
        with pytest.raises(ValueError):
            sandbox.profile(str(binary), bad)
    escaped = owned/'run_link'
    escaped.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        sandbox.profile(str(binary), str(escaped))


def test_template_binding_reports_runtime_root(tmp_path, monkeypatch):
    binary, root = runtime(tmp_path)
    monkeypatch.setattr(sandbox, 'base_dir', lambda: str(tmp_path/'runs'))
    info = sandbox.sandbox_info(str(binary))
    assert info['python'] == str(binary) and info['runtime_root'] == str(root)
    assert info['profile'] == sandbox.profile(str(binary), '<OWN_RUN_DIRECTORY>')
