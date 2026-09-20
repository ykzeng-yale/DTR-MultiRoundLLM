#!/usr/bin/env python3
"""Harmless host-containment canaries only; never benchmark/model programs."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_runner(path):
    spec = importlib.util.spec_from_file_location("audited_sandbox", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def binding(module, source):
    info = module.sandbox_info()
    return {"sandbox_sha256": sha(source), "profile_sha256": info["profile_sha256"],
            "python": info["python"], "python_sha256": sha(info["python"]),
            "host_sha256": hashlib.sha256(platform.node().encode()).hexdigest(),
            "platform": platform.platform(), "sandbox_kind": info["kind"]}


def check(runner_path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    module = load_runner(runner_path)
    report = {"schema_version": "landmark-containment-v1", "checked_at": datetime.now(timezone.utc).isoformat(),
              "binding": binding(module, runner_path), "checks": [], "passed": False,
              "script_sha256": sha(__file__), "benchmark_executions": 0, "model_calls": 0}
    if report["binding"]["sandbox_kind"] != "seatbelt":
        report["blocked_reason"] = "Seatbelt isolation unavailable; no canary program executed"
        (output/"attestation.json").write_text(json.dumps(report, indent=2)+"\n")
        return report
    begin = time.monotonic()
    home_dir = Path(tempfile.mkdtemp(prefix="landmark_canary_", dir=ROOT/"work"))
    peer = Path(tempfile.mkdtemp(prefix="audit_peer_", dir=module.sandbox_info()["base_dir"]))
    shared = None
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    try:
        (home_dir/"read_fixture").write_text("controlled non-sensitive canary")
        (peer/"read_fixture").write_text("controlled peer canary")
        def denied(operation):
            return "try:\n    "+operation+"\nexcept OSError:\n    print('BLOCKED', flush=True)\nelse:\n    print('ALLOWED', flush=True)\n"
        cases = [
            ("own_run_read_write", "from pathlib import Path\np=Path('owned');p.write_text('ok');assert p.read_text()=='ok'\nprint('OK',flush=True)\n", "OK", 2),
            ("home_read", denied(f"open({str(home_dir/'read_fixture')!r}).read()"), "BLOCKED", 2),
            ("home_write", denied(f"open({str(home_dir/'write_marker')!r}, 'w').write('controlled marker')"), "BLOCKED", 2),
            ("peer_run_read", denied(f"open({str(peer/'read_fixture')!r}).read()"), "BLOCKED", 2),
        ]
        try:
            shared = Path(tempfile.mkdtemp(prefix="landmark_canary_", dir="/Users/Shared"))
            cases.append(("outside_home_tmp_write", denied(f"open({str(shared/'write_marker')!r}, 'w').write('controlled marker')"), "BLOCKED", 2))
        except OSError as exc:
            report["checks"].append({"name": "outside_home_tmp_write", "passed": False, "executed": False, "reason": str(exc)})
        port = listener.getsockname()[1]
        cases += [
            ("loopback_network", "import socket\ns=socket.socket();s.settimeout(0.2)\n"+denied(f"s.connect(('127.0.0.1',{port}))"), "BLOCKED", 2),
            ("system_subprocess", "import subprocess\n"+denied("subprocess.run(['/bin/echo','controlled'],check=True)"), "BLOCKED", 2),
            ("fork_creation", "import os\ntry:\n    pid=os.fork()\nexcept OSError:\n    print('BLOCKED',flush=True)\nelse:\n    if pid==0: os._exit(0)\n    os.waitpid(pid,0)\n    print('ALLOWED',flush=True)\n", "BLOCKED", 2),
            ("timeout_and_process_cleanup", "import os,time\nprint('PID',os.getpid(),flush=True)\ntime.sleep(3)\n", None, .3),
        ]
        for name, program, expected, timeout in cases:
            program = "print('__LANDMARK_CANARY_STARTED__',flush=True)\n"+program
            result = module.run_program(program, timeout_s=timeout, cpu_seconds=1, output_cap=4096)
            payload_started = result["stdout"].startswith("__LANDMARK_CANARY_STARTED__\n")
            observed = result["stdout"].removeprefix("__LANDMARK_CANARY_STARTED__\n")
            passed = bool(payload_started and result["passed"] and observed.strip() == expected)
            details = {}
            if expected is None:
                tokens = observed.strip().split()
                child_pid = int(tokens[1]) if len(tokens)==2 and tokens[0]=="PID" else None
                alive = None
                if child_pid is not None:
                    try:
                        os.kill(child_pid, 0)
                        alive = True
                    except ProcessLookupError:
                        alive = False
                passed = result["timed_out"] and alive is False
                details = {"executed_process_pid": child_pid, "alive_after_runner_return": alive}
            report["checks"].append({"name": name, "passed": passed, "executed": result["executed"], "payload_started": payload_started,
                                      "program": program, "result": result, **details})
        report["passed"] = all(c["passed"] for c in report["checks"])
        report["sandbox_executions"] = sum(bool(c["executed"]) for c in report["checks"])
        report["sandbox_launch_attempts"] = report["sandbox_executions"]
        report["payload_executions"] = sum(bool(c.get("payload_started")) for c in report["checks"])
        report["sandbox_seconds"] = sum(c.get("result", {}).get("seconds", 0) for c in report["checks"])
        report["wall_seconds"] = time.monotonic()-begin
        report["limitations"] = ["Controlled containment checks, not an adversarial escape proof", "Only fork/subprocess attempts tested; descendants were not permitted in the passing configuration", "Timeout check verifies launched process reaped; no independently created descendant was available to test cleanup", "No general denial-of-service, kernel isolation, or grade-integrity guarantee"]
    finally:
        listener.close()
        for directory in (home_dir, peer, shared):
            if directory is not None:
                shutil.rmtree(directory, ignore_errors=True)
    (output/"attestation.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runner", choices=("common", "landmark"), required=True)
    p.add_argument("--output", type=Path, required=True)
    a=p.parse_args()
    runner=ROOT/"experiments"/a.runner/"sandbox.py"
    result=check(runner,a.output)
    print(json.dumps({k:result.get(k) for k in ("passed","sandbox_executions","sandbox_seconds","wall_seconds","blocked_reason")},indent=2))
