"""Frozen stdio contract checks with mock processes only; no payload executes."""
import hashlib
from pathlib import Path

import pytest

from experiments.prompt_choice import stdio_observation_v1 as observer
from experiments.prompt_choice import native_execution_v2 as execution
from experiments.prompt_choice import strict_sandbox_v2 as sandbox
from experiments.prompt_choice.status_feedback_v1 import TEXT


def case(scope='public', expected='42\n'):
    return {'scope': scope, 'stdin': '20 22\n', 'expected_stdout': expected}


def result(stdout='42\n', disposition='completed_ungraded', valid=True):
    raw = stdout.encode('utf-8')
    return {'execution': {'disposition': disposition},
            'raw_process': {'stdout': stdout, 'stdout_utf8_valid': valid,
                            'stdout_bytes_read': len(raw),
                            'stdout_sha256': hashlib.sha256(raw).hexdigest()}}


def checked(c, *, normalization='exact', response=None, monkeypatch,
            private=False, runner=None):
    scope = 'private' if private else 'public'
    instrument = observer.freeze_instrument([c], scope=scope, normalization=normalization)
    monkeypatch.setattr(execution, 'verify_attestation', lambda path: {})
    if runner is None:
        runner = lambda *args, **kwargs: result() if response is None else response
    function = observer.private_check if private else observer.public_check
    return function('print(20+22)', c, instrument=instrument,
                    expected_instrument_sha256=observer.instrument_sha256(instrument),
                    containment_attestation='mock-fresh-v2', runner=runner)


def test_source_and_input_only_reach_runner_and_feedback_is_status_only(monkeypatch):
    secret = 'private-expectation-canary'
    observed = {}
    def runner(source, stdin_bytes, **kwargs):
        observed.update(source=source, stdin=stdin_bytes, kwargs=kwargs)
        return result('wrong\n')
    c = case(expected=secret)
    output = checked(c, monkeypatch=monkeypatch, runner=runner)
    assert observed['source'] == 'print(20+22)'
    assert observed['stdin'] == b'20 22\n'
    assert secret not in str(observed)
    assert observed['kwargs']['attestation_path'] == 'mock-fresh-v2'
    assert output['feedback_text'] == TEXT['FAIL'] and secret not in output['feedback_text']
    assert output['audit']['receipt']['reason'] == 'external_frozen_stdout_comparison'


@pytest.mark.parametrize('actual,expected,status', [
    ('42\n', '42\n', 'PASS'), ('42', '42\n', 'FAIL'),
    (' 42\n', '42\n', 'FAIL'), ('42.0\n', '42\n', 'FAIL'),
    ('PASS\n', '42\n', 'FAIL'), ('', '', 'PASS'),
])
def test_exact_comparison_infers_no_semantic_equivalence(actual, expected, status, monkeypatch):
    output = checked(case(expected=expected), response=result(actual), monkeypatch=monkeypatch)
    assert output['feedback_text'] == TEXT[status]


def test_crlf_normalization_is_explicit_and_does_not_strip(monkeypatch):
    c = case()
    exact = checked(c, response=result('42\r\n'), monkeypatch=monkeypatch)
    normalized = checked(c, normalization='crlf-to-lf', response=result('42\r\n'), monkeypatch=monkeypatch)
    assert exact['feedback_text'] == TEXT['FAIL']
    assert normalized['feedback_text'] == TEXT['PASS']
    assert observer.canonical_stdout(' 42\r', 'crlf-to-lf') == ' 42\r'
    assert exact['audit']['receipt']['instrument_sha256'] != normalized['audit']['receipt']['instrument_sha256']
    with pytest.raises(ValueError): observer.canonical_stdout('42', 'float-tolerance')


@pytest.mark.parametrize('actual', ['42 7', '  42\t7\r\n', '\v42 \f\t\n7\r '])
def test_explicit_ascii_token_contract_ignores_only_ascii_separators(actual, monkeypatch):
    c = case(expected='42\n7\n')
    exact = checked(c, response=result(actual), monkeypatch=monkeypatch)
    tokens = checked(c, normalization='ascii-whitespace-tokens-v1',
                     response=result(actual), monkeypatch=monkeypatch)
    assert exact['feedback_text'] == TEXT['FAIL']
    assert tokens['feedback_text'] == TEXT['PASS']
    assert exact['audit']['receipt']['instrument_sha256'] != tokens['audit']['receipt']['instrument_sha256']
    assert observer.canonical_stdout(actual, 'ascii-whitespace-tokens-v1') == ('42', '7')


@pytest.mark.parametrize('actual', ['42\u00a07', '42\u20037', '42.0 7', '7 42', '42 seven'])
def test_ascii_token_contract_preserves_unicode_and_internal_token_differences(actual, monkeypatch):
    output = checked(case(expected='42 7'), normalization='ascii-whitespace-tokens-v1',
                     response=result(actual), monkeypatch=monkeypatch)
    assert output['feedback_text'] == TEXT['FAIL']
    assert observer.canonical_stdout('A a', 'ascii-whitespace-tokens-v1') == ('A', 'a')
    assert observer.canonical_stdout('42\u00a07', 'ascii-whitespace-tokens-v1') == ('42\u00a07',)


def test_ascii_token_contract_rejects_invalid_utf8_and_preserves_empty_contract(monkeypatch):
    output = checked(case(), normalization='ascii-whitespace-tokens-v1',
                     response=result(valid=False), monkeypatch=monkeypatch)
    assert output['feedback_text'] == TEXT['INCOMPLETE']
    assert output['audit']['receipt']['reason'] == 'invalid_stdout_utf8'
    assert observer.canonical_stdout(' \t\n\f\v\r', 'ascii-whitespace-tokens-v1') == ()
    with pytest.raises(ValueError):
        observer.canonical_stdout('\ud800', 'ascii-whitespace-tokens-v1')


@pytest.mark.parametrize('disposition', ['timeout', 'output_limit', 'process_error'])
def test_actual_execution_failure_remains_separate(disposition, monkeypatch):
    output = checked(case(), response=result(disposition=disposition), monkeypatch=monkeypatch)
    receipt = output['audit']['receipt']
    assert output['feedback_text'] == TEXT['INCOMPLETE']
    assert receipt['outcome'] is None and receipt['reason'] == disposition


def test_invalid_utf8_and_saturated_stdout_are_incomplete(monkeypatch):
    bad = checked(case(), response=result(valid=False), monkeypatch=monkeypatch)
    assert bad['audit']['receipt']['reason'] == 'invalid_stdout_utf8'
    saturated = checked(case(), response=result('x' * observer.MAX_BYTES), monkeypatch=monkeypatch)
    assert saturated['audit']['receipt']['reason'] == 'invalid_or_saturated_stdout'
    assert saturated['feedback_text'] == TEXT['INCOMPLETE']


def test_private_instrument_never_produces_feedback(monkeypatch):
    output = checked(case('private', 'secret-answer\n'), response=result('42\n'),
                     private=True, monkeypatch=monkeypatch)
    assert 'feedback_text' not in output and output['status'] == 'FAIL'


@pytest.mark.parametrize('fault', ['case', 'scope', 'source', 'normalization', 'digest', 'malformed_hash'])
def test_freeze_or_membership_drift_refused_before_attestation_or_execution(fault, monkeypatch):
    c = case()
    instrument = observer.freeze_instrument([c], scope='public')
    digest = observer.instrument_sha256(instrument)
    if fault == 'case': c['expected_stdout'] = '43\n'
    elif fault == 'scope': c['scope'] = 'private'
    elif fault == 'source': instrument['source_sha256s']['scorer'] = '0' * 64
    elif fault == 'normalization': instrument['normalization'] = 'crlf-to-lf'
    elif fault == 'digest': digest = '0' * 64
    elif fault == 'malformed_hash': instrument['case_sha256s'] = [{}]
    def never(*args, **kwargs): raise AssertionError('reached attestation or execution')
    monkeypatch.setattr(execution, 'verify_attestation', never)
    with pytest.raises(ValueError):
        observer.public_check('print(42)', c, instrument=instrument,
            expected_instrument_sha256=digest, containment_attestation='unused', runner=never)


def test_failed_attestation_prevents_dispatch(monkeypatch):
    c = case()
    instrument = observer.freeze_instrument([c], scope='public')
    def refuse(path): raise ValueError('stale v2 containment')
    def never(*args, **kwargs): raise AssertionError('executed')
    monkeypatch.setattr(execution, 'verify_attestation', refuse)
    with pytest.raises(ValueError, match='stale'):
        observer.public_check('print(42)', c, instrument=instrument,
            expected_instrument_sha256=observer.instrument_sha256(instrument),
            containment_attestation='stale', runner=never)


def test_default_dispatch_selects_attested_stdin_v2(monkeypatch):
    c = case()
    instrument = observer.freeze_instrument([c], scope='public')
    calls = []
    monkeypatch.setattr(execution, 'verify_attestation', lambda path: calls.append(('verify', path)))
    def stdin_runner(source, stdin_bytes, **kwargs):
        calls.append(('stdin', source, stdin_bytes, kwargs['attestation_path']))
        return result()
    monkeypatch.setattr(execution, 'run_stdin', stdin_runner)
    output = observer.public_check('print(42)', c, instrument=instrument,
        expected_instrument_sha256=observer.instrument_sha256(instrument),
        containment_attestation='current-v2')
    assert output['feedback_text'] == TEXT['PASS']
    assert calls == [('verify', 'current-v2'), ('stdin', 'print(42)', b'20 22\n', 'current-v2')]


def test_source_bindings_cover_every_trusted_boundary():
    assert set(observer.source_bindings()) == {'scorer', 'execution', 'classification', 'sandbox',
                                               'containment_checker', 'feedback'}


@pytest.mark.parametrize('bad', [None, b'input', '\ud800', 'x' * (observer.MAX_BYTES + 1)])
def test_invalid_utf8_input_is_refused_at_instrument_freeze(bad):
    c = case(); c['stdin'] = bad
    with pytest.raises(ValueError): observer.freeze_instrument([c], scope='public')


def test_unsupported_expected_output_or_duplicate_instrument_refused():
    c = case(); c['expected_stdout'] = 'x' * observer.MAX_BYTES
    with pytest.raises(ValueError): observer.freeze_instrument([c], scope='public')
    with pytest.raises(ValueError, match='duplicate'):
        observer.freeze_instrument([case(), case()], scope='public')
    assert observer.case_binding(case(), 'public') != observer.case_binding(case('private'), 'private')


def test_native_stdin_validation_precedes_mocked_dispatch(monkeypatch):
    events = []
    monkeypatch.setattr(execution, 'verify_attestation', lambda path: events.append('verify'))
    def sandbox_run(source, stdin_bytes, **kwargs):
        assert events == ['verify'] and stdin_bytes == 'héllo\n'.encode()
        return {'sandbox_kind': 'seatbelt', 'executed': True, 'stdout': '42\n', 'stderr': '',
                'returncode': 0, 'timed_out': False}
    monkeypatch.setattr(sandbox, 'run_program_stdin', sandbox_run)
    response = execution.run_stdin('print(42)', 'héllo\n'.encode(), attestation_path='mock')
    assert response['execution']['disposition'] == 'completed_ungraded'
    events.clear()
    for invalid in (b'\xff', b'x' * 65537, 'text', bytearray(b'x')):
        with pytest.raises(ValueError): execution.run_stdin('print(42)', invalid, attestation_path='mock')
    assert events == []


def test_strict_stdin_uses_rb_file_and_bounded_regular_output_files(tmp_path, monkeypatch):
    """Mock Popen never executes source; inspect trusted transport only."""
    captured = {}
    monkeypatch.setattr(sandbox, 'sandbox_info', lambda python: {
        'kind': 'seatbelt', 'base_dir': str(tmp_path), 'python': '/dedicated/bin/python3.12',
        'profile_sha256': 'a' * 64})
    monkeypatch.setattr(sandbox, 'profile', lambda python, run: '(deny default)')
    class FakeProcess:
        pid = 123
        returncode = 0
        def __init__(self, command, **kwargs):
            stream = kwargs['stdin']
            assert stream.mode == 'rb' and not stream.writable()
            captured.update(stdin=stream.read(), source=Path(command[-1]).read_text(),
                            env=kwargs['env'], stdout=kwargs['stdout'].name,
                            stderr=kwargs['stderr'].name, run=kwargs['cwd'])
            assert kwargs['stdout'] != sandbox.subprocess.PIPE
            assert kwargs['stderr'] != sandbox.subprocess.PIPE
            kwargs['stdout'].write(b'\xff42\n')
        def wait(self, timeout): return 0
        def poll(self): return 0
    monkeypatch.setattr(sandbox.subprocess, 'Popen', FakeProcess)
    response = sandbox.run_program_stdin('print(42)', b'20 22\n')
    assert captured['stdin'] == b'20 22\n' and captured['source'] == 'print(42)'
    assert captured['env'] == {'PATH': '/usr/bin:/bin', 'PYTHONIOENCODING': 'utf-8'}
    assert response['stdout_utf8_valid'] is False and response['stdout_bytes_read'] == 4
    assert response['stdout_sha256'] == hashlib.sha256(b'\xff42\n').hexdigest()
    assert response['stdin_sha256'] == hashlib.sha256(b'20 22\n').hexdigest()
    assert not captured['run'].exists()


def test_old_no_stdin_signature_still_uses_devnull(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, 'sandbox_info', lambda python: {
        'kind': 'seatbelt', 'base_dir': str(tmp_path), 'python': '/dedicated/bin/python3.12',
        'profile_sha256': 'a' * 64})
    monkeypatch.setattr(sandbox, 'profile', lambda python, run: '(deny default)')
    class FakeProcess:
        pid = 124
        returncode = 0
        def __init__(self, command, **kwargs):
            assert kwargs['stdin'] == sandbox.subprocess.DEVNULL
        def wait(self, timeout): return 0
        def poll(self): return 0
    monkeypatch.setattr(sandbox.subprocess, 'Popen', FakeProcess)
    response = sandbox.run_program('pass')
    assert response['stdin_sha256'] is None and response['stdin_bytes_supplied'] == 0
    assert response['stdout_utf8_valid'] is True


def test_stdin_path_retains_no_bare_fallback(monkeypatch):
    monkeypatch.setattr(sandbox, 'sandbox_info', lambda python: {'kind': 'none'})
    def never(*args, **kwargs): raise AssertionError('Popen attempted')
    monkeypatch.setattr(sandbox.subprocess, 'Popen', never)
    with pytest.raises(RuntimeError, match='no bare fallback'):
        sandbox.run_program_stdin('pass', b'input')
