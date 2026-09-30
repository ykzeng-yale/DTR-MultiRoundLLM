"""Fresh attestation gating under synthetic trusted receipts; no processes."""
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from experiments.prompt_choice import native_execution_v2 as native


def fixture(tmp_path, monkeypatch):
    expected = {'sandbox_sha256': 'v2', 'profile_sha256': 'profile', 'python': '/dedicated/python'}
    monkeypatch.setattr(native, 'binding', lambda *args: expected)
    data = {'schema_version': 'landmark-containment-v1', 'passed': True,
            'checked_at': datetime.now(timezone.utc).isoformat(), 'binding': expected,
            'script_sha256': hashlib.sha256((native.ROOT/'scripts/check_landmark_sandbox.py').read_bytes()).hexdigest(),
            'checks': [{'name': name, 'passed': True, 'payload_started': True}
                       for name in sorted(native.REQUIRED_CHECKS)]}
    path = tmp_path/'attestation.json'
    return path, data


@pytest.mark.parametrize('drift', ['source', 'stale', 'future', 'checker', 'checks', 'failed'])
def test_bad_attestation_refused_before_program_launch(tmp_path, monkeypatch, drift):
    path, data = fixture(tmp_path, monkeypatch)
    if drift == 'source': data['binding'] = {'sandbox_sha256': 'old-v1'}
    if drift == 'stale': data['checked_at'] = (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    if drift == 'future': data['checked_at'] = (datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
    if drift == 'checker': data['script_sha256'] = 'wrong'
    if drift == 'checks': data['checks'].pop()
    if drift == 'failed': data['checks'][0]['payload_started'] = False
    path.write_text(json.dumps(data))
    def never(*args, **kwargs): raise AssertionError('executed program')
    monkeypatch.setattr(native.sandbox, 'run_program', never)
    with pytest.raises(ValueError): native.run('not executed', attestation_path=path)


def test_passing_receipt_still_only_execution_not_test_success(tmp_path, monkeypatch):
    path, data = fixture(tmp_path, monkeypatch)
    path.write_text(json.dumps(data))
    monkeypatch.setattr(native.sandbox, 'run_program', lambda *a, **k: {
        'sandbox_kind': 'seatbelt', 'executed': True, 'stdout': 'PASS', 'stderr': '',
        'returncode': 0, 'timed_out': False})
    out = native.run('not executed', attestation_path=path)
    assert out['execution']['version'] == native.VERSION
    assert out['execution']['disposition'] == 'completed_ungraded'
    assert out['execution']['test_outcome'] is None
