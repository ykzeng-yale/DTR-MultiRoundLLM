"""Versioned default-deny Seatbelt runner with dedicated runtime validation.

This is a bounded benchmark runner, not a general adversarial execution service.
Historical landmark source and manifests remain unchanged. Fresh qualification
must bind this module before a new frozen instrument uses it.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import resource
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def base_interpreter():
    return os.path.realpath(getattr(sys, "_base_executable", None) or sys.executable)


def base_dir():
    path = Path(tempfile.gettempdir()).resolve()/"dtr_landmark_strict"
    path.mkdir(mode=0o700, exist_ok=True)
    return str(path)


def profile(python, run_dir):
    python, prefix = validated_runtime(python)
    if run_dir != "<OWN_RUN_DIRECTORY>":
        directory = Path(run_dir)
        if not directory.is_absolute():
            raise ValueError("Sandbox run directory must be absolute")
        directory = directory.resolve(strict=True)
        if (directory.parent != Path(base_dir()).resolve()
                or not directory.name.startswith("run_") or not directory.is_dir()):
            raise ValueError("Sandbox writes require an owned landmark run directory")
        run_dir = str(directory)
    q = json.dumps
    return "\n".join([
        "(version 1)", "(deny default)", "(deny network*)", "(deny process-fork)",
        "(allow process-exec (literal "+q(python)+"))",
        "(allow file-read-metadata)",
        "(allow file-read* (subpath "+q(prefix)+") (subpath \"/System/Library\") (subpath \"/usr/lib\") (subpath "+q(run_dir)+") (literal \"/dev/urandom\") (literal \"/dev/random\") (literal \"/dev/null\"))",
        "(allow file-write* (subpath "+q(run_dir)+") (literal \"/dev/null\"))",
        "(allow sysctl-read)",
        # Interpreter start-up reads the root directory's own entry (not anything beneath it: `literal`,
        # not `subpath`). Without this single allowance every launch aborts with SIGABRT (-6) before the
        # payload runs, so all nine containment canaries reported started=False. Found by bisection over
        # candidate allowances on 2026-09-21; the dyld shared cache in the Cryptex volume was tested and is
        # NOT required. The canary suite is re-run after this change to confirm it opens no escape.
        "(allow file-read-data (literal \"/\"))",
    ])


def validated_runtime(python):
    """Refuse a shared filesystem tree as the interpreter's readable runtime.

    The profile assumes a dedicated CPython installation with bin/ and lib/.
    In particular /usr/bin/python3 must not infer '/' as its runtime. This
    structural check is not a containment attestation or dependency audit.
    """
    executable = Path(python)
    if not executable.is_absolute():
        raise ValueError("Sandbox interpreter must be an absolute path")
    executable = executable.resolve(strict=True)
    prefix = executable.parent.parent
    forbidden = {Path(p).resolve() for p in (
        '/', '/usr', '/usr/local', '/opt', '/opt/homebrew', '/System',
        '/Library', '/Users', '/private', '/private/tmp', '/tmp', '/var',
        str(Path.home()), str(Path(__file__).resolve().parents[2]),
    )}
    project = Path(__file__).resolve().parents[2]
    if (prefix in forbidden or Path.home().is_relative_to(prefix)
            or project.is_relative_to(prefix) or prefix.is_relative_to(project)):
        raise ValueError("Shared/home/project trees cannot be readable runtimes")
    if (executable.parent.name != 'bin' or not executable.is_file()
            or not os.access(executable, os.X_OK)
            or not re.fullmatch(r'python3(?:\.\d+)?', executable.name)):
        raise ValueError("Dedicated CPython bin layout required")
    libraries = list((prefix/'lib').glob('python3.*'))
    if not any(p.is_dir() and (p/'encodings/__init__.py').is_file()
               and p.resolve().is_relative_to(prefix)
               and (p/'encodings/__init__.py').resolve().is_relative_to(prefix)
               for p in libraries):
        raise ValueError("Dedicated CPython standard library required")
    return str(executable), str(prefix)


def sandbox_info(python=None):
    python, runtime_root = validated_runtime(python or base_interpreter())
    root = base_dir()
    template = profile(python, "<OWN_RUN_DIRECTORY>")
    return {"kind": "seatbelt" if sys.platform=="darwin" and Path("/usr/bin/sandbox-exec").exists() else "none",
            "python": python, "runtime_root": runtime_root, "base_dir": root, "profile": template,
            "profile_sha256": hashlib.sha256(template.encode()).hexdigest()}


def limits(mem_bytes, cpu_seconds, output_cap):
    def apply():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (output_cap, output_cap))
        for limit in (resource.RLIMIT_DATA,):
            try:
                resource.setrlimit(limit, (mem_bytes, mem_bytes))
            except (OSError, ValueError):
                pass  # macOS does not guarantee these memory limits.
    return apply


def run_program(source, timeout_s=2.0, mem_bytes=512 << 20, cpu_seconds=1, output_cap=65536, python=None):
    return _run_program(source, timeout_s=timeout_s, mem_bytes=mem_bytes,
                        cpu_seconds=cpu_seconds, output_cap=output_cap, python=python)


def validate_stdin(stdin_bytes):
    """Bounded UTF-8 invocation bytes; expected output is never an argument."""
    if type(stdin_bytes) is not bytes or len(stdin_bytes) > 65536:
        raise ValueError('bounded UTF-8 stdin bytes required')
    try:
        stdin_bytes.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise ValueError('bounded UTF-8 stdin bytes required') from exc
    return stdin_bytes


def run_program_stdin(source, stdin_bytes, timeout_s=2.0, mem_bytes=512 << 20,
                      cpu_seconds=1, output_cap=65536, python=None):
    """Additive stdin transport; same strict boundary and regular output files.

    The fresh run directory receives only program.py and invocation stdin, never
    expectations or comparison code. The child inherits the input opened rb.
    Passing containment checks does not authenticate an internal computation.
    """
    validate_stdin(stdin_bytes)
    return _run_program(source, timeout_s=timeout_s, mem_bytes=mem_bytes,
                        cpu_seconds=cpu_seconds, output_cap=output_cap,
                        python=python, stdin_bytes=stdin_bytes)


def _decoded(raw):
    try:
        return raw.decode('utf-8', errors='strict'), True
    except UnicodeDecodeError:
        return raw.decode('utf-8', errors='replace'), False


def _run_program(source, timeout_s=2.0, mem_bytes=512 << 20, cpu_seconds=1,
                 output_cap=65536, python=None, stdin_bytes=None):
    info = sandbox_info(python)
    if info["kind"] != "seatbelt":
        raise RuntimeError("Verified Seatbelt isolation is required; no bare fallback")
    if not 0 < timeout_s <= 10 or not 1 <= cpu_seconds <= 5 or not 1024 <= output_cap <= 262144:
        raise ValueError("Landmark execution bounds exceeded")
    run = Path(tempfile.mkdtemp(prefix="run_", dir=info["base_dir"]))
    (run/"program.py").write_text(source)
    rendered = profile(info["python"], str(run))
    start = time.perf_counter()
    timed_out = False
    proc = None
    stdin_stream = None
    try:
        if stdin_bytes is not None:
            # No expectation or instrument digest is staged in the child boundary.
            (run/'stdin').write_bytes(stdin_bytes)
            stdin_stream = (run/'stdin').open('rb')
        with (run/"stdout").open("w+b") as stdout, (run/"stderr").open("w+b") as stderr:
            proc = subprocess.Popen(["/usr/bin/sandbox-exec", "-p", rendered, info["python"], "-I", "-S", str(run/"program.py")],
                cwd=run, env={"PATH": "/usr/bin:/bin", "PYTHONIOENCODING": "utf-8"},
                stdin=stdin_stream if stdin_stream is not None else subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=limits(mem_bytes,cpu_seconds,output_cap))
            try:
                proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                try: os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait(timeout=2)
            stdout.seek(0); out=stdout.read(output_cap)
            stderr.seek(0); err=stderr.read(output_cap)
        out_text, out_valid = _decoded(out)
        err_text, err_valid = _decoded(err)
        return {"passed": proc.returncode==0 and not timed_out, "returncode": proc.returncode,
            "stdout": out_text, "stderr": err_text,
            "stdout_utf8_valid": out_valid, "stderr_utf8_valid": err_valid,
            "stdout_bytes_read": len(out), "stderr_bytes_read": len(err),
            "stdout_sha256": hashlib.sha256(out).hexdigest(),
            "stderr_sha256": hashlib.sha256(err).hexdigest(),
            "stdin_bytes_supplied": 0 if stdin_bytes is None else len(stdin_bytes),
            "stdin_sha256": None if stdin_bytes is None else hashlib.sha256(stdin_bytes).hexdigest(),
            "stdout_tail": out[-512:].decode(errors="replace"), "timed_out": timed_out,
            "seconds": time.perf_counter()-start, "executed": True, "pid": proc.pid,
            "sandbox_kind": info["kind"], "profile_sha256": info["profile_sha256"],
            "rendered_profile_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            "limits_applied": {"cpu_seconds": cpu_seconds,"nproc":1,"file_bytes":output_cap,"memory":"best_effort"}}
    finally:
        if stdin_stream is not None:
            stdin_stream.close()
        if proc is not None and proc.poll() is None:
            try: os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            proc.wait(timeout=2)
        shutil.rmtree(run, ignore_errors=True)
