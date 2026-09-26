#!/usr/bin/env python3
"""Frozen harmless real-process supervisor check; no benchmark/model execution."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

PINS = {
    'scripts/run_policy_endpoint_audit.py': 'bd30976a65b1e2728e4038ab5176ebbc63189f3ac8d690c8c95f72aa68ef05a6',
    '/usr/bin/true': 'a73efca930c2adb1f52eef0d1d3b17d375ee40290fc796653c91c33abf381938',
    '/bin/sleep': 'a2be9ba33f4fbf10a4f2702cd9b687ac98274ad28de509109ee86f2f4b0e2beb',
}


def main():
    target = Path('results/policy_supervisor_process_check_20260926.json')
    if target.exists():
        raise FileExistsError(target)
    for path, digest in PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError(f'pin mismatch: {path}')
    spec = importlib.util.spec_from_file_location('adapter', 'scripts/run_policy_endpoint_audit.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    start = time.monotonic()
    rows = []
    for name, cmd in [('normal_exit', ['/usr/bin/true']), ('term_timeout', ['/bin/sleep', '10'])]:
        # Adapter kill reserve is5s: these deadlines leave0.4s before TERM.
        record = adapter.supervise(cmd, time.monotonic() + 5.4)
        try:
            os.killpg(record['child_pid'], 0)
            group_absent = False
        except ProcessLookupError:
            group_absent = True
        record.update(case=name, command=cmd, independently_observed_group_absent=group_absent)
        rows.append(record)
    elapsed = time.monotonic() - start
    ok = (rows[0]['child_exit'] == 0 and not rows[0]['killed_at_deadline']
          and rows[1]['child_exit'] == -15 and rows[1]['killed_at_deadline']
          and all(r['independently_observed_group_absent'] for r in rows) and elapsed < 10)
    result = {'classification': 'harmless real-process operational check, not endpoint or policy evidence',
              'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'pins': PINS,
              'elapsed_seconds': elapsed, 'passed': ok, 'rows': rows,
              'benchmark_reference_control_model_launches': 0,
              'scope_limit': 'normal exit and TERM of owned groups only; watchdog/SIGKILL/detached-sandbox paths untested here'}
    text = json.dumps(result, indent=2) + '\n'
    if len(text.encode()) > 65536:
        raise ValueError('receipt exceeds64KiB')
    with target.open('x') as handle:
        handle.write(text)
    print(json.dumps({'passed': ok, 'elapsed_seconds': elapsed, 'receipt': str(target)}))
    return 0 if ok else 3


if __name__ == '__main__':
    raise SystemExit(main())
