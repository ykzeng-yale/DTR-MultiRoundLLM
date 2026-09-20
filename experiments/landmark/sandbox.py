"""Landmark-only default-deny Seatbelt runner; never falls back to bare Python.

This is a bounded benchmark runner, not a general adversarial execution service.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import resource
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
    prefix = str(Path(python).parent.parent)
    q = json.dumps
    return "\n".join([
        "(version 1)", "(deny default)", "(deny network*)", "(deny process-fork)",
        "(allow process-exec (literal "+q(python)+"))",
        "(allow file-read-metadata)",
        "(allow file-read* (subpath "+q(prefix)+") (subpath \"/System/Library\") (subpath \"/usr/lib\") (subpath "+q(run_dir)+") (literal \"/dev/urandom\") (literal \"/dev/random\") (literal \"/dev/null\"))",
        "(allow file-write* (subpath "+q(run_dir)+") (literal \"/dev/null\"))",
        "(allow sysctl-read)",
    ])


def sandbox_info(python=None):
    python = python or base_interpreter()
    root = base_dir()
    template = profile(python, "<OWN_RUN_DIRECTORY>")
    return {"kind": "seatbelt" if sys.platform=="darwin" and Path("/usr/bin/sandbox-exec").exists() else "none",
            "python": python, "base_dir": root, "profile": template,
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
    try:
        with (run/"stdout").open("w+b") as stdout, (run/"stderr").open("w+b") as stderr:
            proc = subprocess.Popen(["/usr/bin/sandbox-exec", "-p", rendered, info["python"], "-I", "-S", str(run/"program.py")],
                cwd=run, env={"PATH": "/usr/bin:/bin", "PYTHONIOENCODING": "utf-8"}, stdin=subprocess.DEVNULL,
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
        return {"passed": proc.returncode==0 and not timed_out, "returncode": proc.returncode,
            "stdout": out.decode(errors="replace"), "stderr": err.decode(errors="replace"),
            "stdout_tail": out[-512:].decode(errors="replace"), "timed_out": timed_out,
            "seconds": time.perf_counter()-start, "executed": True, "pid": proc.pid,
            "sandbox_kind": info["kind"], "profile_sha256": info["profile_sha256"],
            "rendered_profile_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            "limits_applied": {"cpu_seconds": cpu_seconds,"nproc":1,"file_bytes":output_cap,"memory":"best_effort"}}
    finally:
        if proc is not None and proc.poll() is None:
            try: os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            proc.wait(timeout=2)
        shutil.rmtree(run, ignore_errors=True)
