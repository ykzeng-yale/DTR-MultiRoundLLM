"""Meaningful deterministic source/mocked transport checks; no code executes."""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from experiments.containment import stdio_sprint_qualification_v1 as qualification
from experiments.measurement_sprint import execution_v1 as execution
from experiments.measurement_sprint import runtime_v1 as runtime
from experiments.measurement_sprint import stdio_v1 as observer

RUNTIME_HASH = 'a'*64
CONTRACT_HASH = 'b'*64


def case(identity='0', scope='private', expected='42\n'):
    return {'case_id': identity, 'scope': scope, 'stdin': '20 22\n', 'expected_stdout': expected}


def instrument(cases, normalization='exact'):
    return observer.freeze_instrument(cases, scope=cases[0]['scope'], normalization=normalization,
        runtime_manifest_sha256=RUNTIME_HASH, source_contract_sha256=CONTRACT_HASH)


def mock_runner(stdout=b'42\n', disposition='completed', failure=None):
    def runner(code, stdin, *, caps):
        return {'version': execution.VERSION, 'source_sha256': runtime.sha256(code.encode()),
                'stdin_sha256': runtime.sha256(stdin), 'stdin_bytes': len(stdin),
                'caps': caps, 'runtime_manifest_sha256': RUNTIME_HASH,
                'disposition': disposition, 'failure': failure,
                'payload_started': disposition != 'observer_unavailable',
                'outcome_available': disposition != 'observer_unavailable',
                'returncode': 0 if disposition == 'completed' else 1,
                'stdout': stdout, 'stdout_bytes': len(stdout),
                'stdout_sha256': runtime.sha256(stdout), 'cleanup': True}
    return runner


def evaluate(c, runner=None, normalization='exact'):
    i = instrument([c], normalization)
    return observer.evaluate_case('print(42)', c, instrument=i,
        expected_instrument_sha256=observer.instrument_sha256(i), scope=c['scope'],
        runner=mock_runner() if runner is None else runner)


def test_large_caps_include_measured_source_and_inclusive_boundary():
    caps = execution.DEFAULT_CAPS
    assert caps['stdin_bytes'] >= 12000007 and caps['stdout_bytes'] >= 10924038
    assert len(observer.utf8('x'*caps['stdin_bytes'], caps['stdin_bytes'])) == caps['stdin_bytes']
    with pytest.raises(ValueError):
        observer.utf8('x'*(caps['stdin_bytes']+1), caps['stdin_bytes'])
    c = case(expected='x'*10924038)
    frozen = instrument([c])
    assert frozen['cases'][0]['expected_stdout_bytes'] == 10924038


def test_source_resource_translation_is_exact_and_bounded():
    c = execution.DEFAULT_CAPS
    source = {k: c[k] for k in ('stdin_bytes','stdout_bytes','stderr_bytes','cpu_soft_seconds','cpu_hard_seconds','wall_seconds')}
    source.update(address_space_bytes=c['memory_bytes'], program_bytes=c['source_bytes'])
    assert observer.caps_from_source_contract(source) == c
    with pytest.raises(ValueError):
        observer.caps_from_source_contract(dict(source, wall_seconds=9))
    with pytest.raises(ValueError):
        observer.caps_from_source_contract(dict(source, hidden_budget=1))


@pytest.mark.parametrize('actual,expected,result', [
    (b'42\n', b'42\n', True), (b'42', b'42\n', False),
    (b'42.0', b'42', False), (b'yes', b'YES', False),
])
def test_exact_never_infers_number_case_or_framing_equivalence(actual, expected, result):
    assert observer.compare_stdout(actual, expected, 'exact') is result


def test_token_contract_preserves_order_numbers_and_unicode_whitespace():
    assert observer.compare_stdout(b' 1\t2\r\n', b'1 2', 'ascii_whitespace_tokens_v1')
    assert not observer.compare_stdout(b'2 1', b'1 2', 'ascii_whitespace_tokens_v1')
    assert not observer.compare_stdout(b'1.0 2', b'1 2', 'ascii_whitespace_tokens_v1')
    assert not observer.compare_stdout('1\u00a02'.encode(), b'1 2', 'ascii_whitespace_tokens_v1')


def test_line_contract_preserves_neighbor_rows_and_empty_rows():
    norm = 'line-ascii-tokens-v1'
    assert observer.compare_stdout(b'2\r\n1', b'2\n1\n', norm)
    assert not observer.compare_stdout(b'2 1\n\n', b'2\n1\n', norm)
    assert not observer.compare_stdout(b'', b'\n', norm)
    assert observer.compare_stdout(b'\n\n', b'\r\n\r\n', norm)


def test_source_single_line_contract_preserves_spaces_and_rejects_extra_lines():
    norm = 'single_line_exact_optional_final_newline_v1'
    assert observer.compare_stdout(b'Abe san', b'Abe san\r\n', norm)
    assert not observer.compare_stdout(b'Abe  san\n', b'Abe san', norm)
    assert not observer.compare_stdout(b'Abe san \n', b'Abe san', norm)
    assert not observer.compare_stdout(b'Abe san\n\n', b'Abe san', norm)
    assert not observer.compare_stdout(b'Abe san\r', b'Abe san', norm)
    with pytest.raises(ValueError):
        instrument([case(expected='x\ny')], norm)


@pytest.mark.parametrize('reason', ['payload_nonzero_exit','wall_limit','stdout_limit','stderr_limit','invalid_stdout_utf8'])
def test_completed_operational_failures_are_new_prospective_zero_not_missing(reason):
    row = evaluate(case(), mock_runner(disposition='operational_failure', failure=reason))
    assert row['outcome'] == 0 and row['status'] == 'FAIL' and row['reason'] == reason
    assert row['historical_grades_changed'] is False


def test_observer_unavailability_remains_unknown():
    row = evaluate(case(), mock_runner(disposition='observer_unavailable', failure='bootstrap_or_namespace_unavailable'))
    assert row['outcome'] is None and row['status'] == 'INCOMPLETE'


def test_expectations_never_reach_runner_and_public_feedback_is_only_status():
    c = case(scope='public', expected='secret-expectation')
    i = instrument([c])
    observed = {}
    def runner(code, stdin, *, caps):
        observed.update(code=code, stdin=stdin, caps=caps)
        return mock_runner(stdout=b'wrong')(code, stdin, caps=caps)
    result = observer.public_check('print(42)', c, instrument=i,
        expected_instrument_sha256=observer.instrument_sha256(i), runner=runner)
    assert 'secret-expectation' not in str(observed)
    assert result['feedback_text'] == observer.TEXT['FAIL']
    assert 'secret-expectation' not in result['feedback_text']


def test_case_scope_source_and_execution_identity_cannot_drift():
    c = case();i = instrument([c]);digest = observer.instrument_sha256(i)
    with pytest.raises(ValueError):
        observer.evaluate_case('print(42)', dict(c, expected_stdout='43'), instrument=i,
            expected_instrument_sha256=digest, scope='private', runner=mock_runner())
    with pytest.raises(ValueError):
        observer.evaluate_case('print(42)', c, instrument=i,
            expected_instrument_sha256=digest, scope='public', runner=mock_runner())
    def changed(code, stdin, *, caps):
        return dict(mock_runner()(code,stdin,caps=caps), source_sha256='c'*64)
    with pytest.raises(ValueError):
        evaluate(c, changed)


def test_complete_battery_retains_missing_and_known_failed_conjuncts():
    cases = [case('0'),case('1'),case('2')];i = instrument(cases);seen=[]
    def runner(code, stdin, *, caps):
        index=len(seen);seen.append(index)
        return (mock_runner(disposition='observer_unavailable',failure='infra') if index==1
                else mock_runner(stdout=b'bad' if index==2 else b'42\n'))(code,stdin,caps=caps)
    result = observer.evaluate_battery('print(42)',cases,instrument=i,
        expected_instrument_sha256=observer.instrument_sha256(i),scope='private',runner=runner)
    assert seen==[0,1,2] and result['assigned']==result['accounted']==3
    assert result['outcome']==0 and result['bounds']==[0,0] and result['unavailable_cases']==1
    with pytest.raises(ValueError):
        observer.evaluate_battery('print(42)',cases[:2],instrument=i,
            expected_instrument_sha256=observer.instrument_sha256(i),scope='private',runner=runner)


def test_duplicate_case_payloads_retained_with_distinct_assignments():
    i = instrument([case('0'),case('1')])
    assert len(i['cases'])==2
    with pytest.raises(ValueError):
        instrument([case('0'),case('0')])


def test_prospective_fallback_never_uses_private_success_or_masks_absent_initial():
    result=observer.fallback_artifact('receiver_timeout',last_valid_artifact='wrong-code')
    assert result['artifact']=='wrong-code' and result['STOP'] is False
    absent=observer.fallback_artifact('receiver_failure',last_valid_artifact=None)
    assert absent['artifact'] is None and absent['STOP'] is False
    returned=observer.fallback_artifact('returned',last_valid_artifact='old',returned_artifact='syntax bad')
    assert returned['artifact']=='syntax bad'
    with pytest.raises(ValueError):
        observer.fallback_artifact('missing_log',last_valid_artifact='old')


def test_ready_requires_first_trusted_prefix_and_exact_nonce_source_and_deny_set():
    data={'nonce':'n','source_sha256':'a'*64,'denied':list(execution.DENIED_SYSCALLS)}
    marker=execution.READY_PREFIX+runtime.canonical(data)+b'\n'
    assert execution.split_ready(marker+b'payload stderr','n','a'*64)[1]==b'payload stderr'
    assert execution.split_ready(b'bad\n'+marker,'n','a'*64)[0] is None
    assert execution.split_ready(marker,'other','a'*64)[0] is None
    bad=execution.READY_PREFIX+runtime.canonical(dict(data,denied=[]))+b'\n'
    assert execution.split_ready(bad,'n','a'*64)[0] is None


def test_bwrap_projection_never_mounts_entire_usr_home_project_or_writable_temp(tmp_path):
    rt=tmp_path/'runtime';rt.mkdir();(rt/'libc').write_bytes(b'lib')
    program=tmp_path/'program.py';program.write_text('print(42)')
    manifest={'dependencies':[{'path':'libc','guest_path':'/lib64/libc.so.6'}]}
    cmd=execution.command(rt,manifest,program,execution.DEFAULT_CAPS,'nonce')
    assert '--unshare-all' in cmd and '--die-with-parent' in cmd and '--cap-drop' in cmd
    assert '--bind' not in cmd and '--tmpfs' not in cmd
    pairs=[cmd[j+1:j+3] for j,x in enumerate(cmd) if x=='--ro-bind']
    assert all(source not in ('/usr','/home','/nfs','/lib','/lib64') for source,destination in pairs)
    assert [str(tmp_path/'empty'),'/tmp'] in pairs
    assert execution.DENIED_SYSCALLS.count('clone')==1 and 'execve' in execution.DENIED_SYSCALLS


def test_runtime_manifest_rejects_extra_file_links_and_changed_contents(tmp_path):
    rt=tmp_path/'runtime';rt.mkdir();(rt/'python').write_bytes(b'fake trusted metadata')
    manifest={'version':runtime.VERSION,'files':[{'path':'python','bytes':21,'sha256':runtime.file_hash(rt/'python')}],'dependencies':[]}
    # Use actual size, preserving a deliberately tiny pure fixture.
    manifest['files'][0]['bytes']=(rt/'python').stat().st_size
    (rt/'manifest.json').write_bytes(runtime.canonical(manifest))
    h=runtime.file_hash(rt/'manifest.json');assert runtime.verify_runtime(rt,h)==manifest
    (rt/'extra').write_text('unexpected')
    with pytest.raises(ValueError):runtime.verify_runtime(rt,h)
    (rt/'extra').unlink();(rt/'python').write_text('changed')
    with pytest.raises(ValueError):runtime.verify_runtime(rt,h)


def test_source_plan_is_finite_all_fixtures_and_drift_refused():
    root=Path(__file__).resolve().parents[1]
    plan=qualification.make_plan(root)
    qualification.validate_plan(plan,root)
    assert plan['model_calls']==plan['task_executions']==0
    assert plan['fixtures']==list(execution.REQUIRED_FIXTURES)
    assert plan['global_wall_seconds']<240
    with pytest.raises(ValueError):qualification.validate_plan(dict(plan, fixtures=plan['fixtures'][:-1]),root)


def test_attestation_refuses_incomplete_qualifications_without_running(monkeypatch,tmp_path):
    host={'node':'test','kernel':'test','bwrap_sha256':'a'*64,'source_sha256s':{}}
    monkeypatch.setattr(execution,'host_binding',lambda:host)
    monkeypatch.setattr(runtime,'verify_runtime',lambda *args:{})
    data={'version':execution.VERSION,'passed':True,'host_binding':host,
          'planned_fixtures':list(execution.REQUIRED_FIXTURES),'passed_fixtures':list(execution.REQUIRED_FIXTURES),
          'unattempted':0,'checked_at':datetime.now(timezone.utc).isoformat(),
          'caps':dict(execution.DEFAULT_CAPS),'runtime_directory':'mock','runtime_manifest_sha256':'a'*64}
    p=tmp_path/'attestation.json';p.write_text(json.dumps(data))
    assert execution.verify_attestation(p)==data
    p.write_text(json.dumps(dict(data,passed_fixtures=['preflight_correct'],planned_fixtures=['preflight_correct'])))
    with pytest.raises(ValueError):execution.verify_attestation(p)
