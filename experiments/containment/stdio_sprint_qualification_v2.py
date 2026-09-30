"""One coherent trusted stdio observer/containment qualification, not task work."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import resource
import tempfile
import time

from experiments.measurement_sprint_v2 import execution_v2 as execution
from experiments.measurement_sprint_v2 import runtime_v2 as runtime
from experiments.measurement_sprint_v2 import stdio_v2 as observer

VERSION = 'stdio-sprint-qualification-v2'
PREDECESSOR = {'version': 'stdio-sprint-qualification-v1', 'job_id': '27976306',
               'freeze_commit': '5057f1c1e3dd0ec8b553658b9e899da4d7180a29',
               'plan_sha256': 'efb8caf9eea1fd304ba6d002702dd50b36b6f1240d93b349b0c40fc4e6574724',
               'first_failure_stderr_sha256': 'c86584c97fe7faf6437896c9a00433352a4814a7ae76a3d46b6233591c1023e7'}
DIAGNOSTIC_PREFIX_BYTES = 4096
FILES = (
    'experiments/measurement_sprint_v2/__init__.py',
    'experiments/measurement_sprint_v2/runtime_v2.py',
    'experiments/measurement_sprint_v2/execution_v2.py',
    'experiments/measurement_sprint_v2/stdio_v2.py',
    'experiments/containment/stdio_sprint_qualification_v2.py',
    'experiments/containment/stdio_sprint_v2.sbatch',
    'scripts/qualify_stdio_sprint_v2.py',
)


def make_plan(root):
    """Pure source freeze only; no subprocess/network/runtime/task execution."""
    root = Path(root)
    return {'version': VERSION, 'classification': 'trusted fixed-fixture qualification, not candidate release',
            'predecessor': dict(PREDECESSOR),
            'repair': 'only CPython ELF interpreter receives execute mode; strict filter/caps unchanged',
            'runtime_location_rule': 'owned node-local tmp when executable; otherwise dedicated owned output snapshot; never mount whole project',
            'trusted_fixture_stderr_prefix_bytes': DIAGNOSTIC_PREFIX_BYTES,
            'caps': dict(execution.DEFAULT_CAPS),
            'fixtures': list(execution.REQUIRED_FIXTURES),
            'runtime_python': '/usr/bin/python3', 'global_wall_seconds': 210,
            'global_supervisor_cpu_seconds': 120, 'max_retained_evidence_bytes': 20 << 20,
            'runtime_bytes_cap': runtime.MAX_RUNTIME_BYTES,
            'dependency_bytes_cap': runtime.MAX_DEPENDENCY_BYTES,
            'measured_source_maxima': {'stdin_bytes': 12000007, 'expected_stdout_bytes': 10924038},
            'files': {name: runtime.file_hash(root / name) for name in FILES},
            'paid_usd': 0, 'model_calls': 0, 'task_executions': 0,
            'candidate_execution_released': False}


def validate_plan(plan, root):
    if plan != make_plan(root):
        raise ValueError('qualification source/assignment/resource freeze drift')


def _emit_code(length, byte='x', fd=1):
    return (f'import os\nn={length}\nblock={byte.encode()!r}*65536\n'
            f'while n:\n k=min(n,len(block));os.write({fd},block[:k]);n-=k\n')


def choose_runtime_directory(output):
    """Use this node's executable filesystem; changing mount flags is forbidden."""
    output = Path(output)
    tmp = runtime.filesystem_execution('/tmp')
    if not tmp['noexec']:
        scratch = Path(tempfile.mkdtemp(prefix='dtr-stdio-runtime-v2-', dir='/tmp'))
        return scratch/'runtime', {'chosen_location': 'owned_node_local_tmp',
            'tmp_filesystem': tmp, 'selected_filesystem': runtime.filesystem_execution(scratch)}
    selected = runtime.filesystem_execution(output)
    if selected['noexec']:
        raise RuntimeError('both owned runtime destinations are noexec; no mount relaxation')
    return output/'runtime', {'chosen_location': 'dedicated_owned_output_snapshot',
        'tmp_filesystem': tmp, 'selected_filesystem': selected}


def retain_trusted_stderr(output, index, fixture, raw):
    """Only fixed trusted fixtures reach this path, never candidate diagnostics."""
    if fixture not in execution.REQUIRED_FIXTURES or type(index) is not int or index < 0 or type(raw) is not bytes:
        raise ValueError('trusted qualification stderr identity')
    relative = f'diagnostics/{index:02d}-{fixture}.stderr'
    path = Path(output)/relative
    path.parent.mkdir(mode=0o700, exist_ok=True)
    prefix = raw[:DIAGNOSTIC_PREFIX_BYTES]
    with path.open('xb') as stream:
        stream.write(prefix)
    return {'relative_path': relative, 'retained_bytes': len(prefix),
            'retained_sha256': runtime.sha256(prefix), 'full_bytes': len(raw),
            'full_sha256': runtime.sha256(raw), 'truncated': len(raw)>len(prefix),
            'scope': 'trusted fixed fixture only, not policy feedback'}


def fixtures(caps, host_canary):
    """All sources are fixed trusted harmless controls, no actual source tasks."""
    correct = 'import sys\na,b=map(int,sys.stdin.read().split());print(a+b)'
    denied = 'DENIED\n'
    definitions = {
        'preflight_correct': (correct, b'20 22\n', b'42\n', 'PASS', None),
        'wrong_output': ('print(41)', b'', b'42\n', 'FAIL', 'external_frozen_stdout_comparison'),
        'large_source_input': ('import sys\nprint(len(sys.stdin.buffer.read()))', b'x'*12000007, b'12000007\n', 'PASS', None),
        'large_source_output': (_emit_code(10924038), b'', b'x'*10924038, 'PASS', None),
        'input_cap_inclusive': ('import sys\nprint(len(sys.stdin.buffer.read()))', b'x'*caps['stdin_bytes'], (str(caps['stdin_bytes'])+'\n').encode(), 'PASS', None),
        'stdout_cap_inclusive': (_emit_code(caps['stdout_bytes']), b'', b'x'*caps['stdout_bytes'], 'PASS', None),
        'socket_denied': ('import socket\ntry:socket.socket()\nexcept PermissionError:print("DENIED")', b'', denied.encode(), 'PASS', None),
        'fork_denied': ('import os\ntry:os.fork()\nexcept PermissionError:print("DENIED")', b'', denied.encode(), 'PASS', None),
        'exec_denied': ('import os\ntry:os.execv("/runtime/bin/python3",["python3","-c","print(1)"])\nexcept PermissionError:print("DENIED")', b'', denied.encode(), 'PASS', None),
        'thread_denied': ('import threading\ntry:threading.Thread(target=lambda:None).start()\nexcept RuntimeError:print("DENIED")', b'', denied.encode(), 'PASS', None),
        'home_project_canary_hidden': ('from pathlib import Path\nprint(all(not Path(p).exists() for p in '+repr(['/home','/root','/nfs',str(host_canary)])+'))', b'', b'True\n', 'PASS', None),
        'environment_cleared': ('import os\nprint("DTR_STDIO_HOST_PRIVATE" not in os.environ)', b'', b'True\n', 'PASS', None),
        'inherited_fds_closed': ('import os\nf=[]\nfor fd in range(3,64):\n try:os.fstat(fd);f.append(fd)\n except OSError:pass\nprint(f)', b'', b'[]\n', 'PASS', None),
        'temporary_write_denied': ('try:open("/tmp/forbidden","w").write("x")\nexcept OSError:print("DENIED")', b'', denied.encode(), 'PASS', None),
        'memory_cap': ('try:x=bytearray(2*1024**3)\nexcept MemoryError:print("DENIED")', b'', denied.encode(), 'PASS', None),
        'cpu_cap': ('while True:pass', b'', b'', 'FAIL', 'payload_nonzero_exit'),
        'wall_cap_cleanup': ('import time\ntime.sleep(30)', b'', b'', 'FAIL', 'wall_limit'),
        'stdout_over_cap': (_emit_code(caps['stdout_bytes']+1), b'', b'', 'FAIL', 'stdout_limit'),
        'stderr_over_cap': (_emit_code(caps['stderr_bytes']+1, fd=2), b'', b'', 'FAIL', 'stderr_limit'),
        'syntax_failure': ('def broken(:\n pass\n', b'', b'', 'FAIL', 'payload_nonzero_exit'),
        'runtime_failure': ('raise ValueError("trusted runtime control")', b'', b'', 'FAIL', 'payload_nonzero_exit'),
        'invalid_utf8': ('import os\nos.write(1,b"\\xff")', b'', b'', 'FAIL', 'invalid_stdout_utf8'),
        'fake_ready_cannot_override_grade': ('import os\nos.write(2,b"DTR_STDIO_SPRINT_READY:{}\\n");print(41)', b'', b'42\n', 'FAIL', 'external_frozen_stdout_comparison'),
    }
    if set(definitions) != set(execution.REQUIRED_FIXTURES):
        raise ValueError('fixture set drift')
    return definitions


def run(plan_path, output, *, root, freeze_path):
    """Lead dispatches this once after source freeze; no install or task code."""
    start = time.monotonic()
    root = Path(root).resolve()
    plan = json.loads(Path(plan_path).read_bytes())
    validate_plan(plan, root)
    out = Path(output).resolve()
    out.mkdir(mode=0o700, exist_ok=False)
    freeze = Path(freeze_path).read_text().strip()
    if len(freeze) != 40 or any(c not in '0123456789abcdef' for c in freeze):
        raise ValueError('exact immutable freeze commit required')
    summary = {'version': execution.VERSION, 'qualification_version': VERSION,
               'classification': plan['classification'], 'plan_sha256': runtime.file_hash(plan_path),
               'freeze': freeze, 'job_id': os.environ.get('SLURM_JOB_ID'),
               'checked_at': datetime.now(timezone.utc).isoformat(),
               'planned_fixtures': list(execution.REQUIRED_FIXTURES),
               'passed_fixtures': [], 'completed': 0, 'failures': 0,
               'unattempted': len(execution.REQUIRED_FIXTURES), 'passed': False,
               'error': None, 'caps': plan['caps'], 'candidate_execution_released': False,
               'model_calls': 0, 'task_executions': 0, 'paid_usd': 0}
    summary['predecessor'] = dict(PREDECESSOR)
    canary = out / 'host-canary'
    canary.write_text('owned qualification sentinel; not mounted\n')
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (plan['global_supervisor_cpu_seconds'],
                                                plan['global_supervisor_cpu_seconds']+5))
        # Node-local small files; old NFS installation latency does not apply.
        # Retain for this allocation's qualification->grading chain only. Every
        # later job stages and qualifies anew on its node; no cross-node reuse.
        staged, location = choose_runtime_directory(out)
        summary['runtime_location'] = location
        runtime.stage_runtime(staged, plan['runtime_python'])
        summary.update(runtime_directory=str(staged),
            runtime_manifest_sha256=runtime.file_hash(staged/'manifest.json'),
            host_binding=execution.host_binding())
        manifest = runtime.verify_runtime(staged, summary['runtime_manifest_sha256'])
        (out/'runtime-manifest.json').write_bytes(runtime.canonical(manifest)+b'\n')
        definitions = fixtures(plan['caps'], canary)
        private_marker_previous = os.environ.get('DTR_STDIO_HOST_PRIVATE')
        os.environ['DTR_STDIO_HOST_PRIVATE'] = 'qualification-only'
        try:
            with canary.open('rb') as inherited, (out/'journal.jsonl').open('xb') as journal:
                os.set_inheritable(inherited.fileno(), True)
                def runner(code, stdin, *, caps):
                    result = execution._run_unqualified(code, stdin,
                        runtime_directory=staged,
                        runtime_manifest_sha256=summary['runtime_manifest_sha256'], caps=caps,
                        verified_manifest=manifest, verified_binding=summary['host_binding'])
                    result['trusted_stderr_diagnostic'] = retain_trusted_stderr(out,index,name,result.get('stderr',b''))
                    return result
                for index, name in enumerate(execution.REQUIRED_FIXTURES):
                    if time.monotonic()-start > plan['global_wall_seconds']-12:
                        raise TimeoutError('global qualification wall cap')
                    code, stdin, expected, expected_status, reason = definitions[name]
                    case = {'case_id': name, 'scope': 'private', 'stdin': stdin.decode(),
                            'expected_stdout': expected.decode()}
                    instrument = observer.freeze_instrument([case], scope='private', normalization='exact',
                        runtime_manifest_sha256=summary['runtime_manifest_sha256'],
                        source_contract_sha256=summary['plan_sha256'], caps=plan['caps'])
                    receipt = observer.evaluate_case(code, case, instrument=instrument,
                        expected_instrument_sha256=observer.instrument_sha256(instrument),
                        scope='private', runner=runner)
                    passed = (receipt['status'] == expected_status and
                              receipt['execution'].get('cleanup') is True and
                              (reason is None or receipt['reason'] == reason))
                    row = {'assignment': index, 'fixture': name, 'passed': passed,
                           'source_sha256': runtime.sha256(code.encode()),
                           'stdin_bytes': len(stdin), 'stdin_sha256': runtime.sha256(stdin),
                           'expected_stdout_bytes': len(expected),
                           'expected_stdout_sha256': runtime.sha256(expected),
                           'expected_status': expected_status, 'expected_reason': reason,
                           'receipt': receipt}
                    raw = runtime.canonical(row)+b'\n'
                    if journal.tell()+len(raw) > 2 << 20:
                        raise RuntimeError('qualification journal cap')
                    journal.write(raw);journal.flush()
                    summary['completed'] += 1
                    summary['failures'] += int(not passed)
                    if passed:
                        summary['passed_fixtures'].append(name)
                    if (index == 0 and not passed) or summary['failures'] >= 2:
                        raise RuntimeError('qualification failed; no automatic repeat or relaxation')
        finally:
            if private_marker_previous is None:
                os.environ.pop('DTR_STDIO_HOST_PRIVATE', None)
            else:
                os.environ['DTR_STDIO_HOST_PRIVATE'] = private_marker_previous
        summary['host_canary_unchanged'] = canary.read_text() == 'owned qualification sentinel; not mounted\n'
        summary['passed'] = (summary['passed_fixtures'] == summary['planned_fixtures']
                             and summary['host_canary_unchanged'])
        if not summary['passed']:
            raise RuntimeError('incomplete qualification')
    except BaseException as exc:
        summary['error'] = repr(exc)
        raise
    finally:
        summary['unattempted'] = len(execution.REQUIRED_FIXTURES)-summary['completed']
        summary['seconds'] = time.monotonic()-start
        summary['python_supervisor'] = platform.python_version()
        summary['runtime_retention'] = 'dedicated owned executable snapshot for this job only; later jobs requalify; manifest retained as evidence'
        (out/'summary.json').write_bytes(runtime.canonical(summary)+b'\n')
        if summary['passed']:
            (out/'attestation.json').write_bytes(runtime.canonical(summary)+b'\n')
