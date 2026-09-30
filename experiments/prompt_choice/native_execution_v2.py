"""Versioned bounded execution with an exact fresh containment attestation.

The historical runner and releases stay unchanged. This supports future
source-separated instruments only; passing canaries is not an escape proof.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from experiments.prompt_choice import strict_sandbox_v2 as sandbox
from experiments.prompt_choice import native_execution_v1 as previous
from scripts.check_landmark_sandbox import binding

VERSION = 'native-execution-v2-dedicated-runtime'
ROOT = Path(__file__).resolve().parents[2]
REQUIRED_CHECKS = {'own_run_read_write', 'home_read', 'home_write', 'peer_run_read',
                   'outside_home_tmp_write', 'loopback_network', 'system_subprocess',
                   'fork_creation', 'timeout_and_process_cleanup'}


def verify_attestation(path):
    data = json.loads(Path(path).read_text())
    expected = binding(sandbox, sandbox.__file__)
    checker = ROOT/'scripts/check_landmark_sandbox.py'
    if (data.get('schema_version') != 'landmark-containment-v1'
            or data.get('passed') is not True or data.get('binding') != expected
            or data.get('script_sha256') != hashlib.sha256(checker.read_bytes()).hexdigest()):
        raise ValueError('containment does not bind this host/runtime/v2 source/checker')
    checks = data.get('checks', [])
    if (type(checks) is not list or len(checks) != len(REQUIRED_CHECKS)
            or any(type(c) is not dict for c in checks)
            or {c.get('name') for c in checks} != REQUIRED_CHECKS
            or any(c.get('passed') is not True or c.get('payload_started') is not True for c in checks)):
        raise ValueError('incomplete containment checks')
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(data['checked_at'])).total_seconds()
    if not 0 <= age <= 86400:
        raise ValueError('containment must be from the last 24 hours')
    return data


def run(source, *, attestation_path, timeout_s=2.0, cpu_seconds=1,
        output_cap=4096, mem_bytes=256<<20):
    verify_attestation(attestation_path)
    _validate_request(source, timeout_s, cpu_seconds, output_cap, mem_bytes)
    result = sandbox.run_program(source, timeout_s=timeout_s, cpu_seconds=cpu_seconds,
                                 output_cap=output_cap, mem_bytes=mem_bytes)
    classified = previous.classify(result, output_cap)
    classified['version'] = VERSION
    return {'execution': classified, 'raw_process': result}


def _validate_request(source, timeout_s, cpu_seconds, output_cap, mem_bytes):
    if type(source) is not str or len(source.encode()) > 1048576:
        raise ValueError('invalid source size')
    if type(mem_bytes) is not int or not 1 <= mem_bytes <= 2 << 30:
        raise ValueError('invalid requested memory cap')
    if type(output_cap) is not int or not 1024 <= output_cap <= 262144:
        raise ValueError('invalid output cap')
    if type(cpu_seconds) is not int or not 1 <= cpu_seconds <= 5:
        raise ValueError('invalid CPU cap')
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 10:
        raise ValueError('invalid wall cap')


def run_stdin(source, stdin_bytes, *, attestation_path, timeout_s=2.0,
              cpu_seconds=1, output_cap=65536, mem_bytes=256<<20):
    """Attested bounded stdin path; stdout remains an untrusted observation."""
    sandbox.validate_stdin(stdin_bytes)
    verify_attestation(attestation_path)
    _validate_request(source, timeout_s, cpu_seconds, output_cap, mem_bytes)
    result = sandbox.run_program_stdin(source, stdin_bytes, timeout_s=timeout_s,
        cpu_seconds=cpu_seconds, output_cap=output_cap, mem_bytes=mem_bytes)
    classified = previous.classify(result, output_cap)
    classified['version'] = VERSION
    return {'execution': classified, 'raw_process': result}
