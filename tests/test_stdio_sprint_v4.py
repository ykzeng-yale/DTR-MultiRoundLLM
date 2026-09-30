"""Meaningful deterministic source/mocked transport checks; no code executes."""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from experiments.containment import stdio_sprint_qualification_v4 as qualification
from experiments.measurement_sprint_v4 import execution_v4 as execution
from experiments.measurement_sprint_v4 import runtime_v4 as runtime
from experiments.measurement_sprint_v4 import stdio_v4 as observer

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
    (rt/'lib64/python3.9').mkdir(parents=True)
    manifest={'dependencies':[{'path':'libc','guest_path':'/lib64/libc.so.6'}],
              'stdlib_mounts':[{'path':'lib64/python3.9','guest_path':'/usr/lib64/python3.9'}]}
    cmd=execution.command(rt,manifest,program,execution.DEFAULT_CAPS,'nonce')
    assert '--unshare-all' in cmd and '--die-with-parent' in cmd and '--cap-drop' in cmd
    assert '--bind' not in cmd and '--tmpfs' not in cmd
    pairs=[cmd[j+1:j+3] for j,x in enumerate(cmd) if x=='--ro-bind']
    assert all(source not in ('/usr','/home','/nfs','/lib','/lib64') for source,destination in pairs)
    assert [str(tmp_path/'empty'),'/tmp'] in pairs
    assert [str(rt/'lib64/python3.9'),'/usr/lib64/python3.9'] in pairs
    assert '-I' in cmd and '-S' in cmd and '-B' in cmd
    assert execution.DENIED_SYSCALLS.count('clone')==1 and 'execve' in execution.DENIED_SYSCALLS


def _elf(interpreter='/lib64/ld-linux-x86-64.so.2', bits=64, endian='<'):
    import struct
    header=bytearray(64 if bits==64 else 52)
    header[:7]=b'\x7fELF'+bytes([2 if bits==64 else 1,1 if endian=='<' else 2,1])
    phoff=len(header);entsize=56 if bits==64 else 32
    struct.pack_into(endian+('Q' if bits==64 else 'I'),header,32 if bits==64 else 28,phoff)
    struct.pack_into(endian+'HH',header,54 if bits==64 else 42,entsize,1)
    raw=interpreter.encode()+b'\0';entry=bytearray(entsize)
    struct.pack_into(endian+'I',entry,0,3)
    struct.pack_into(endian+('Q' if bits==64 else 'I'),entry,8 if bits==64 else 4,phoff+entsize)
    struct.pack_into(endian+('Q' if bits==64 else 'I'),entry,32 if bits==64 else 16,len(raw))
    return bytes(header+entry)+raw


def _runtime_fixture(tmp_path):
    rt=tmp_path/'runtime';rt.mkdir();(rt/'bin').mkdir();(rt/'dependencies').mkdir()
    (rt/'lib64/python3.9/encodings').mkdir(parents=True)
    (rt/'lib64/python3.9/lib-dynload').mkdir()
    files=[('bin/python3',_elf(),0o500),('dependencies/loader',b'loader',0o500),('dependencies/library',b'lib',0o400),
           ('lib64/python3.9/encodings/__init__.py',b'# stdlib landmark',0o400)]
    records=[]
    for path,data,mode in files:
        f=rt/path;f.write_bytes(data);f.chmod(mode)
        records.append({'path':path,'bytes':len(data),'sha256':runtime.file_hash(f),'mode':mode})
    interp='/lib64/ld-linux-x86-64.so.2'
    deps=[dict(records[1],guest_path=interp),dict(records[2],guest_path='/lib64/libc.so.6')]
    manifest={'version':runtime.VERSION,'files':records,'dependencies':deps,'elf_interpreter_guest_path':interp,
              'platlibdir':'lib64','minor':'3.9',
              'stdlib_mounts':[{'path':'lib64/python3.9','guest_path':'/usr/lib64/python3.9'}]}
    (rt/'manifest.json').write_bytes(runtime.canonical(manifest))
    return rt,manifest,runtime.file_hash(rt/'manifest.json')


def test_runtime_manifest_rejects_extra_file_links_and_changed_contents(tmp_path):
    rt,manifest,h=_runtime_fixture(tmp_path)
    assert runtime.verify_runtime(rt,h)==manifest
    (rt/'extra').write_text('unexpected')
    with pytest.raises(ValueError):runtime.verify_runtime(rt,h)
    (rt/'extra').unlink();(rt/'dependencies/library').chmod(0o600);(rt/'dependencies/library').write_text('changed')
    with pytest.raises(ValueError):runtime.verify_runtime(rt,h)


def test_elf_loader_mode_is_executable_but_other_libraries_readonly(tmp_path):
    rt,manifest,h=_runtime_fixture(tmp_path)
    interp=runtime.elf_interpreter(rt/'bin/python3')
    assert runtime.staged_mode('dependencies/loader',interp,interp)==0o500
    assert runtime.staged_mode('dependencies/library',interp,'/lib64/libc.so.6')==0o400
    (rt/'dependencies/loader').chmod(0o400)
    with pytest.raises(ValueError,match='mode drift'):runtime.verify_runtime(rt,h)
    (rt/'dependencies/loader').chmod(0o500);(rt/'dependencies/library').chmod(0o500)
    with pytest.raises(ValueError,match='mode drift'):runtime.verify_runtime(rt,h)


@pytest.mark.parametrize('bits,endian',[(64,'<'),(32,'>')])
def test_elf_interpreter_exact_parse_without_execution(tmp_path,bits,endian):
    binary=tmp_path/'python';binary.write_bytes(_elf(bits=bits,endian=endian))
    assert runtime.elf_interpreter(binary)=='/lib64/ld-linux-x86-64.so.2'
    binary.write_bytes(_elf(interpreter='/home/untrusted-loader'))
    with pytest.raises(ValueError):runtime.elf_interpreter(binary)
    binary.write_bytes(b'not an ELF binary')
    with pytest.raises(ValueError):runtime.elf_interpreter(binary)


def test_noexec_selects_dedicated_output_snapshot_without_mount_changes(monkeypatch,tmp_path):
    def flags(path):
        noexec=str(path)=='/tmp'
        return {'f_flag':8 if noexec else 0,'st_noexec_mask':8,'noexec':noexec}
    monkeypatch.setattr(runtime,'filesystem_execution',flags)
    path,binding=qualification.choose_runtime_directory(tmp_path)
    assert path==tmp_path/'runtime' and binding['tmp_filesystem']['noexec']
    assert binding['chosen_location']=='dedicated_owned_output_snapshot'
    monkeypatch.setattr(runtime,'filesystem_execution',lambda path:{'f_flag':8,'st_noexec_mask':8,'noexec':True})
    with pytest.raises(RuntimeError,match='both owned'):qualification.choose_runtime_directory(tmp_path)


def test_trusted_stderr_diagnostic_prefix_is_bounded_hashed_and_explicit(tmp_path):
    raw=b'z'*5000
    d=qualification.retain_trusted_stderr(tmp_path,0,'preflight_correct',raw)
    assert d['full_bytes']==5000 and d['retained_bytes']==4096 and d['truncated']
    assert (tmp_path/d['relative_path']).read_bytes()==raw[:4096]
    assert d['full_sha256']==runtime.sha256(raw)
    with pytest.raises(ValueError):qualification.retain_trusted_stderr(tmp_path,1,'candidate',raw)


def test_v1_stderr_hash_reconstructs_prebootstrap_eacces_only():
    text=b'bwrap: execvp /runtime/bin/python3: Permission denied\n'
    assert len(text)==54 and runtime.sha256(text)=='c86584c97fe7faf6437896c9a00433352a4814a7ae76a3d46b6233591c1023e7'
    assert qualification.PREDECESSOR['job_id']=='27980594'
    assert qualification.PREDECESSOR['freeze_commit']=='78a1ba9c27096990ab0382a0bd4e3a1470fb40fd'


def test_isolated_stdlib_landmarks_and_exact_subtree_cannot_be_broadened(tmp_path):
    rt,manifest,h=_runtime_fixture(tmp_path)
    assert runtime.verify_runtime(rt,h)==manifest
    manifest['stdlib_mounts'][0]['guest_path']='/usr'
    (rt/'manifest.json').write_bytes(runtime.canonical(manifest))
    with pytest.raises(ValueError,match='subtree mapping'):
        runtime.verify_runtime(rt,runtime.file_hash(rt/'manifest.json'))


def test_source_plan_is_finite_all_fixtures_and_drift_refused():
    root=Path(__file__).resolve().parents[1]
    plan=qualification.make_plan(root)
    qualification.validate_plan(plan,root)
    assert plan['model_calls']==plan['task_executions']==0
    assert plan['fixtures']==list(execution.REQUIRED_FIXTURES)
    assert plan['global_wall_seconds']<240
    assert plan['predecessor']==qualification.PREDECESSOR
    assert plan['trusted_fixture_stderr_prefix_bytes']==4096
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


def test_root_and_synthetic_dev_are_readonly_after_mount_construction(tmp_path):
    rt=tmp_path/'runtime';rt.mkdir();program=tmp_path/'program.py';program.write_text('print(1)')
    manifest={'dependencies':[], 'stdlib_mounts':[]}
    cmd=execution.command(rt,manifest,program,execution.DEFAULT_CAPS,'nonce')
    remount=[(i,cmd[i+1]) for i,x in enumerate(cmd) if x=='--remount-ro']
    assert [value for _,value in remount]==['/','/dev']
    assert min(i for i,_ in remount)>max(i for i,x in enumerate(cmd) if x in ('--dir','--ro-bind','--dev','--proc'))
    assert max(i for i,_ in remount)<cmd.index('/runtime/bin/python3')


def test_sealed_stdin_requires_all_four_seals_and_no_file_fallback(monkeypatch,tmp_path):
    import os
    import types
    fd=os.open(tmp_path/'mock-memfd',os.O_RDWR|os.O_CREAT,0o600)
    calls=[]
    monkeypatch.setattr(execution.os,'memfd_create',lambda name,flags:(calls.append(('create',name,flags)) or fd),raising=False)
    monkeypatch.setattr(execution.os,'MFD_CLOEXEC',1,raising=False)
    monkeypatch.setattr(execution.os,'MFD_ALLOW_SEALING',2,raising=False)
    fake=types.SimpleNamespace(F_SEAL_WRITE=8,F_SEAL_GROW=4,F_SEAL_SHRINK=2,F_SEAL_SEAL=1,F_ADD_SEALS=1033,F_GET_SEALS=1034)
    def fcntl(which,op,arg=None):
        calls.append((which,op,arg))
        return 15 if op==1034 else 0
    fake.fcntl=fcntl;monkeypatch.setattr(execution,'fcntl',fake)
    with execution.sealed_stdin(b'input') as stream:
        assert stream.read()==b'input'
    assert calls==[('create','dtr-stdio-input',3),(fd,1033,15),(fd,1034,None)]
    with pytest.raises(OSError):os.fstat(fd)


def test_seal_drift_closes_owned_descriptor_without_yield(monkeypatch,tmp_path):
    import os
    import types
    fd=os.open(tmp_path/'mock-memfd',os.O_RDWR|os.O_CREAT,0o600)
    monkeypatch.setattr(execution.os,'memfd_create',lambda *a:fd,raising=False)
    monkeypatch.setattr(execution.os,'MFD_CLOEXEC',1,raising=False)
    monkeypatch.setattr(execution.os,'MFD_ALLOW_SEALING',2,raising=False)
    fake=types.SimpleNamespace(F_SEAL_WRITE=8,F_SEAL_GROW=4,F_SEAL_SHRINK=2,F_SEAL_SEAL=1,F_ADD_SEALS=1033,F_GET_SEALS=1034,fcntl=lambda *a:0)
    monkeypatch.setattr(execution,'fcntl',fake)
    with pytest.raises(RuntimeError,match='seals'):
        with execution.sealed_stdin(b'input'):pytest.fail('mutable fallback')
    with pytest.raises(OSError):os.fstat(fd)


def test_v3_all_control_definitions_are_preserved_and_ipc_creation_denied():
    from experiments.containment import stdio_sprint_qualification_v3 as old
    definitions=qualification.fixtures(execution.DEFAULT_CAPS,Path('/same-canary'))
    prior=old.fixtures(execution.DEFAULT_CAPS,Path('/same-canary'))
    assert all(definitions[name]==definition for name,definition in prior.items())
    assert len(definitions)==26 and len(execution.REQUIRED_FIXTURES)==26
    assert set(('memfd_create','shmget','semget','msgget','mq_open'))<=set(execution.DENIED_SYSCALLS)
    assert qualification.PREDECESSOR['job_id']=='27980594'
