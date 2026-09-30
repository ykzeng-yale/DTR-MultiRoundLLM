"""Bounded Linux stdio execution under bwrap and strict process/network denial.

The threat model is untrusted Python inside fresh namespaces, read-only pinned
runtime/source and pipes. No writable filesystem, home/project, expectations,
network, extra inherited descriptors or descendant creation are provided. This
is not a kernel-exploit proof. No bare or permissive execution fallback exists.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import sys
import tempfile
import time

from experiments.measurement_sprint_v2 import runtime_v2 as runtime

VERSION = 'stdio-sprint-bwrap-strict-v2'
DEFAULT_CAPS = {'stdin_bytes': 16 << 20, 'stdout_bytes': 16 << 20,
                'stderr_bytes': 256 << 10, 'source_bytes': 1 << 20,
                'memory_bytes': 1 << 30, 'cpu_soft_seconds': 4,
                'cpu_hard_seconds': 5, 'wall_seconds': 8.0,
                'file_bytes': 16 << 20, 'open_files': 64}
DENIED_SYSCALLS = (
    'socket', 'socketpair', 'connect', 'bind', 'listen', 'accept', 'accept4',
    'fork', 'vfork', 'clone', 'clone3', 'execve', 'execveat',
    'unshare', 'setns', 'mount', 'umount2', 'mount_setattr', 'pivot_root', 'chroot',
    'ptrace', 'process_vm_readv', 'process_vm_writev', 'pidfd_open', 'pidfd_getfd',
    'open_by_handle_at', 'name_to_handle_at', 'bpf', 'perf_event_open',
    'io_uring_setup', 'io_uring_enter', 'io_uring_register',
    'keyctl', 'add_key', 'request_key', 'init_module', 'finit_module', 'delete_module',
    'kexec_load', 'reboot', 'swapon', 'swapoff', 'setsid', 'setpgid', 'prctl',
)
READY_PREFIX = b'DTR_STDIO_SPRINT_READY:'
REQUIRED_FIXTURES = (
    'preflight_correct', 'wrong_output', 'large_source_input', 'large_source_output',
    'input_cap_inclusive', 'stdout_cap_inclusive', 'socket_denied', 'fork_denied',
    'exec_denied', 'thread_denied', 'home_project_canary_hidden', 'environment_cleared',
    'inherited_fds_closed', 'temporary_write_denied', 'memory_cap', 'cpu_cap',
    'wall_cap_cleanup', 'stdout_over_cap', 'stderr_over_cap', 'syntax_failure',
    'runtime_failure', 'invalid_utf8', 'fake_ready_cannot_override_grade',
)

# This code is trusted, source-pinned bootstrap. The ready prefix is written to
# stderr before compiling/starting the payload and cannot be removed from the
# pipe by a payload. No candidate runs if setup fails; its later output cannot
# create a pre-execution marker. It is not an authenticity claim for stdout.
BOOTSTRAP = r'''
import ctypes,errno,hashlib,json,os,resource,sys
caps=json.loads(sys.argv[1]);nonce=sys.argv[2];source_sha=sys.argv[3]
source=open('/work/program.py','rb').read()
if hashlib.sha256(source).hexdigest()!=source_sha:raise RuntimeError('source binding')
resource.setrlimit(resource.RLIMIT_AS,(caps['memory_bytes'],caps['memory_bytes']))
resource.setrlimit(resource.RLIMIT_CPU,(caps['cpu_soft_seconds'],caps['cpu_hard_seconds']))
resource.setrlimit(resource.RLIMIT_FSIZE,(caps['file_bytes'],caps['file_bytes']))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_NOFILE,(caps['open_files'],caps['open_files']))
resource.setrlimit(resource.RLIMIT_NPROC,(1,1))
for name in os.listdir('/proc/self/fd'):
    fd=int(name)
    if fd>2:
        try:os.close(fd)
        except OSError:pass
lib=ctypes.CDLL('libseccomp.so.2')
lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint];lib.seccomp_rule_add.restype=ctypes.c_int
lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_load.restype=ctypes.c_int
lib.seccomp_release.argtypes=[ctypes.c_void_p]
ctx=lib.seccomp_init(0x7fff0000)
if not ctx:raise RuntimeError('seccomp allocation')
resolved=[]
for name in json.loads(sys.argv[4]):
    number=lib.seccomp_syscall_resolve_name(name.encode())
    if number>=0:
        if lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,number,0)!=0:raise RuntimeError('seccomp rule '+name)
        resolved.append(name)
for mandatory in ('socket','fork','clone','execve','unshare','mount','ptrace'):
    if mandatory not in resolved:raise RuntimeError('missing mandatory syscall '+mandatory)
if lib.seccomp_load(ctx)!=0:raise RuntimeError('seccomp load')
lib.seccomp_release(ctx)
os.write(2,b'DTR_STDIO_SPRINT_READY:'+json.dumps({'nonce':nonce,'source_sha256':source_sha,'denied':resolved},sort_keys=True,separators=(',',':')).encode()+b'\n')
sys.argv=['/work/program.py']
exec(compile(source,'/work/program.py','exec'),{'__name__':'__main__','__file__':'/work/program.py'})
'''


def source_bindings():
    return {'execution': runtime.file_hash(__file__),
            'runtime': runtime.file_hash(runtime.__file__),
            'observer': runtime.file_hash(Path(__file__).resolve().parent / 'stdio_v2.py'),
            'qualification': runtime.file_hash(Path(__file__).resolve().parents[1] /
                'containment/stdio_sprint_qualification_v2.py')}


def validate_caps(caps):
    if type(caps) is not dict or set(caps) != set(DEFAULT_CAPS):
        raise ValueError('exact prospective resource caps required')
    for key, ceiling in DEFAULT_CAPS.items():
        value = caps[key]
        if type(value) not in ((int, float) if key == 'wall_seconds' else (int,)):
            raise ValueError('finite positive resource caps required')
        if not math.isfinite(value) or not 0 < value <= ceiling:
            raise ValueError('resource envelope exceeded')
    if caps['cpu_soft_seconds'] > caps['cpu_hard_seconds'] or caps['open_files'] < 16:
        raise ValueError('invalid resource ordering')
    return caps


def host_binding():
    if sys.platform != 'linux' or not Path('/usr/bin/bwrap').is_file():
        raise RuntimeError('qualified Linux bubblewrap is required; no fallback')
    return {'node': platform.node(), 'kernel': platform.release(),
            'bwrap_sha256': runtime.file_hash('/usr/bin/bwrap'),
            'source_sha256s': source_bindings()}


def command(runtime_directory, manifest, program, caps, nonce):
    """Only dedicated runtime, individual pinned libraries, and source are bound."""
    directory = Path(runtime_directory).resolve(strict=True)
    original = Path(program)
    source_path = original.resolve(strict=True)
    if not source_path.is_file() or original.is_symlink():
        raise ValueError('regular source file required')
    args = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session',
            '--cap-drop', 'ALL', '--ro-bind', str(directory), '/runtime']
    parents = set()
    for dependency in manifest['dependencies']:
        guest = Path(dependency['guest_path'])
        parents.update(str(p) for p in guest.parents if str(p) != '/')
    for parent in sorted(parents, key=lambda p: (p.count('/'), p)):
        args += ['--dir', parent]
    for dependency in manifest['dependencies']:
        args += ['--ro-bind', str(directory / dependency['path']), dependency['guest_path']]
    # The fresh empty directory is read-only: no temporary-file allocation can
    # consume host disk or bypass the stream/AS caps. Contest stdio only.
    empty = source_path.parent / 'empty'
    empty.mkdir(mode=0o500, exist_ok=False)
    args += ['--proc', '/proc', '--dev', '/dev', '--ro-bind', str(empty), '/tmp',
             '--dir', '/work', '--ro-bind', str(source_path), '/work/program.py',
             '--chdir', '/work', '--setenv', 'PATH', '/runtime/bin',
             '--setenv', 'PYTHONIOENCODING', 'utf-8',
             '/runtime/bin/python3', '-I', '-S', '-B', '-u', '-c', BOOTSTRAP,
             runtime.canonical(caps).decode(), nonce, runtime.file_hash(source_path),
             runtime.canonical(list(DENIED_SYSCALLS)).decode()]
    return args


def _kill_owned(process, *, grace=False):
    if grace and process.poll() is None:
        try:
            process.wait(timeout=0.25)
        except subprocess.TimeoutExpired:
            pass
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=5)


def split_ready(stderr, nonce, source_sha256):
    """Inspect only the first exact pre-payload prefix, never later lookalikes."""
    first, separator, rest = stderr.partition(b'\n')
    if not separator or not first.startswith(READY_PREFIX):
        return None, stderr
    try:
        value = json.loads(first[len(READY_PREFIX):])
        if (set(value) != {'nonce', 'source_sha256', 'denied'} or
                value['nonce'] != nonce or value['source_sha256'] != source_sha256 or
                not set(('socket', 'fork', 'clone', 'execve', 'unshare', 'mount', 'ptrace')) <= set(value['denied']) or
                not set(value['denied']) <= set(DENIED_SYSCALLS)):
            return None, stderr
    except (TypeError, ValueError):
        return None, stderr
    return value, rest


def _run_unqualified(source, stdin_bytes, *, runtime_directory,
                     runtime_manifest_sha256, caps, verified_manifest=None,
                     verified_binding=None):
    """Internal trusted qualification path, never a bare execution fallback."""
    validate_caps(caps)
    binding = host_binding() if verified_binding is None else verified_binding
    if type(source) is not str:
        raise ValueError('UTF8 source required')
    source_bytes = source.encode('utf-8', 'strict')
    if len(source_bytes) > caps['source_bytes'] or type(stdin_bytes) is not bytes or len(stdin_bytes) > caps['stdin_bytes']:
        raise ValueError('source/input cap exceeded')
    stdin_bytes.decode('utf-8', 'strict')
    manifest = (runtime.verify_runtime(runtime_directory, runtime_manifest_sha256)
                if verified_manifest is None else verified_manifest)
    started = time.monotonic()
    out, err, overflow, process, cleanup = bytearray(), bytearray(), None, None, False
    source_sha = runtime.sha256(source_bytes)
    nonce = os.urandom(16).hex()
    with tempfile.TemporaryDirectory(prefix='dtr-stdio-source-', dir='/tmp') as name:
        directory = Path(name)
        program = directory / 'program.py'
        program.write_bytes(source_bytes)
        program.chmod(0o400)
        args = command(runtime_directory, manifest, program, caps, nonce)
        (directory / 'stdin').write_bytes(stdin_bytes)
        with (directory / 'stdin').open('rb') as input_file:
            try:
                process = subprocess.Popen(args, stdin=input_file, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, close_fds=True, start_new_session=True,
                    env={'PATH': '/runtime/bin', 'PYTHONIOENCODING': 'utf-8'}, cwd=directory)
                selector = selectors.DefaultSelector()
                for label, stream in (('stdout', process.stdout), ('stderr', process.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, label)
                try:
                    while selector.get_map():
                        if time.monotonic() - started > caps['wall_seconds']:
                            overflow = 'wall_limit'
                            break
                        for key, _ in selector.select(0.025):
                            block = os.read(key.fileobj.fileno(), 65536)
                            if not block:
                                selector.unregister(key.fileobj)
                                continue
                            target = out if key.data == 'stdout' else err
                            # Small trusted marker allowance is separate from
                            # the declared candidate stderr cap.
                            cap = caps['stdout_bytes'] if key.data == 'stdout' else caps['stderr_bytes'] + 8192
                            available = cap + 1 - len(target)
                            target.extend(block[:max(0, available)])
                            if len(target) > cap:
                                overflow = key.data + '_limit'
                                break
                        if overflow:
                            break
                finally:
                    selector.close()
                    _kill_owned(process, grace=overflow is None)
                    process.stdout.close()
                    process.stderr.close()
                    cleanup = process.poll() is not None
            except (OSError, subprocess.SubprocessError) as exc:
                if process is not None:
                    _kill_owned(process)
                return {'version': VERSION, 'payload_started': False,
                        'disposition': 'observer_unavailable', 'failure': type(exc).__name__,
                        'outcome_available': False, 'host_binding': binding,
                        'source_sha256': source_sha, 'stdin_sha256': runtime.sha256(stdin_bytes),
                        'stdin_bytes': len(stdin_bytes), 'seconds': time.monotonic()-started,
                        'cleanup': cleanup, 'caps': caps,
                        'runtime_manifest_sha256': runtime_manifest_sha256}
    ready, candidate_err = split_ready(bytes(err), nonce, source_sha)
    if ready is None:
        disposition, failure = 'observer_unavailable', 'bootstrap_or_namespace_unavailable'
    elif overflow:
        disposition, failure = 'operational_failure', overflow
    elif len(candidate_err) > caps['stderr_bytes']:
        disposition, failure = 'operational_failure', 'stderr_limit'
    elif process.returncode != 0:
        disposition, failure = 'operational_failure', 'payload_nonzero_exit'
    else:
        try:
            bytes(out).decode('utf-8', 'strict')
            disposition, failure = 'completed', None
        except UnicodeDecodeError:
            disposition, failure = 'operational_failure', 'invalid_stdout_utf8'
    return {'version': VERSION, 'payload_started': ready is not None,
            'disposition': disposition, 'failure': failure,
            'outcome_available': ready is not None, 'returncode': process.returncode,
            'stdout': bytes(out), 'stderr': candidate_err,
            'stdout_sha256': runtime.sha256(bytes(out)),
            'stderr_sha256': runtime.sha256(candidate_err),
            'stdout_bytes': len(out), 'stderr_bytes': len(candidate_err),
            'stdin_bytes': len(stdin_bytes), 'stdin_sha256': runtime.sha256(stdin_bytes),
            'source_sha256': source_sha, 'caps': caps, 'cleanup': cleanup,
            'runtime_manifest_sha256': runtime_manifest_sha256,
            'seconds': time.monotonic()-started, 'host_binding': binding,
            'bootstrap_receipt': ready}


def verify_attestation(path):
    raw = Path(path).read_bytes()
    attestation = json.loads(raw)
    if (attestation.get('version') != VERSION or attestation.get('passed') is not True or
            attestation.get('host_binding') != host_binding() or
            attestation.get('planned_fixtures') != list(REQUIRED_FIXTURES) or
            attestation.get('planned_fixtures') != attestation.get('passed_fixtures') or
            attestation.get('unattempted') != 0):
        raise ValueError('fresh complete source/host-bound qualification required')
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(attestation['checked_at'])).total_seconds()
    if not 0 <= age <= 86400:
        raise ValueError('qualification must be from last24hours on this node')
    validate_caps(attestation['caps'])
    runtime.verify_runtime(attestation['runtime_directory'], attestation['runtime_manifest_sha256'])
    return attestation


def run_stdio(source, stdin_bytes, *, attestation_path, caps):
    """Require qualified exact runtime and caps; collection freeze is separate."""
    attestation = verify_attestation(attestation_path)
    if caps != attestation['caps']:
        raise ValueError('resource contract differs from qualified instrument')
    return _run_unqualified(source, stdin_bytes,
        runtime_directory=attestation['runtime_directory'],
        runtime_manifest_sha256=attestation['runtime_manifest_sha256'], caps=caps)


class QualifiedRunner:
    """Verify a sole-owned read-only runtime once for one supervised job.

    Avoid rehashing an entire stdlib for every battery case. The trusted host
    must exclusively control this runtime throughout the bounded job; child
    namespaces cannot mutate it. Cross-job reuse requires a new instance and
    full verification. This is not protection against a hostile host owner.
    """
    def __init__(self, attestation_path):
        self.attestation = verify_attestation(attestation_path)
        self.manifest = runtime.verify_runtime(
            self.attestation['runtime_directory'],
            self.attestation['runtime_manifest_sha256'])

    def __call__(self, source, stdin_bytes, *, caps):
        if caps != self.attestation['caps']:
            raise ValueError('resource contract differs from qualified instrument')
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(self.attestation['checked_at'])).total_seconds()
        if not 0 <= age <= 86400:
            raise ValueError('qualification expired during job')
        return _run_unqualified(source, stdin_bytes,
            runtime_directory=self.attestation['runtime_directory'],
            runtime_manifest_sha256=self.attestation['runtime_manifest_sha256'], caps=caps,
            verified_manifest=self.manifest,
            verified_binding=self.attestation['host_binding'])
