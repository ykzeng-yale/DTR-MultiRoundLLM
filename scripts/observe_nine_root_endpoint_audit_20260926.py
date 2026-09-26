#!/usr/bin/env python3
"""Lead observer for one frozen nine-root reference/control audit; never runs a benchmark directly."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'results/nine_root_endpoint_plan_20260926T2359Z.json'
PLAN_SHA = '2f1c2611c58f7f296d4bece2d213443524b19238b6c01eff42389b35b0259777'
PREDICTIONS = ROOT / 'results/nine_root_measurement_predictions_20260926.json'
PREDICTIONS_SHA = '28f8ea355fb65c09b1b9368a03308703db9092d4070d067208ae0ced22805a7b'
OBSERVER = ROOT / 'work/nine_root_endpoint_observer_20260926T2359Z'
RECEIPT = ROOT / 'results/nine_root_endpoint_observer_20260926T2359Z.json'
PROJECTION = ROOT / 'results/nine_root_endpoint_projection_20260926T2359Z.json'
SUPERVISORS = ROOT / 'work/nine_root_supervisor_runs'
CAP = 8 * 1024 * 1024

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan-commit', required=True)
    args = ap.parse_args()
    if len(args.plan_commit) != 40 or any(c not in '0123456789abcdef' for c in args.plan_commit):
        raise ValueError('full plan commit required')
    if digest(PLAN) != PLAN_SHA or digest(PREDICTIONS) != PREDICTIONS_SHA:
        raise ValueError('frozen input drift')
    plan = json.loads(PLAN.read_text())
    out = ROOT / plan['output_directory']
    if out.exists() or OBSERVER.exists() or RECEIPT.exists() or PROJECTION.exists():
        raise FileExistsError('fresh run, observer and publication paths required')
    before = set(SUPERVISORS.iterdir()) if SUPERVISORS.exists() else set()
    OBSERVER.mkdir()
    cmd = [sys.executable, str(ROOT / 'scripts/run_nine_root_endpoint_audit.py'), 'execute',
           '--source', plan['source']['path'], '--plan', str(PLAN), '--plan-commit', args.plan_commit]
    started = time.monotonic()
    timed_out = False
    with (OBSERVER/'stdout.txt').open('xb') as stdout, (OBSERVER/'stderr.txt').open('xb') as stderr:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = proc.wait(timeout=605)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL)  # only the observer's still-live owned adapter group
            try:
                code = proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                code = None
    elapsed = time.monotonic() - started
    new_sup = sorted(set(SUPERVISORS.iterdir()) - before) if SUPERVISORS.exists() else []
    if (out/'public_projection.json').exists():
        with PROJECTION.open('xb') as f:
            f.write((out/'public_projection.json').read_bytes())
    files = set(OBSERVER.rglob('*'))
    if out.exists(): files.update(out.rglob('*'))
    for p in new_sup: files.update(p.rglob('*'))
    if PROJECTION.exists(): files.add(PROJECTION)
    files = sorted(p for p in files if p.is_file())
    entries = {str(p.relative_to(ROOT)): {'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}
    data = {'kind':'external_observer_not_policy_evidence','plan_commit':args.plan_commit,
            'plan_sha256':PLAN_SHA,'predictions_sha256':PREDICTIONS_SHA,'observer_source_sha256':digest(Path(__file__)),
            'command':cmd,'adapter_pid':proc.pid,'adapter_exit_code':code,'observer_timeout':timed_out,
            'external_elapsed_seconds_before_receipt':elapsed,
            'new_supervisor_directories':[str(p.relative_to(ROOT)) for p in new_sup],
            'files':entries,'model_calls':0,'retained_cap_bytes':CAP,
            'limits_note':'600-second adapter plus at most5 seconds observer bookkeeping; final verdict is printed after receipt write. Timeout cleanup may exceed this and is reported as a violation,never success.',
            'cleanup_note':'Independent payload PID absence and raw-slot reconciliation still required; this observer alone does not certify detached cleanup.'}
    subtotal = sum(v['bytes'] for v in entries.values())
    size = 0
    for _ in range(30):
        data['observer_receipt_bytes'] = size
        data['all_operational_evidence_bytes'] = subtotal + size
        blob = (json.dumps(data,indent=2)+'\n').encode()
        if len(blob) == size: break
        size = len(blob)
    else: raise RuntimeError('byte-accounting fixed point did not converge')
    with RECEIPT.open('xb') as f: f.write(blob)
    final_elapsed = time.monotonic() - started
    actual_bytes = sum(p.stat().st_size for p in files) + RECEIPT.stat().st_size
    ok = code == 0 and not timed_out and final_elapsed <= 605 and actual_bytes <= CAP and actual_bytes == data['all_operational_evidence_bytes']
    print(json.dumps({'receipt':str(RECEIPT),'final_external_elapsed_seconds':final_elapsed,
                      'actual_operational_bytes':actual_bytes,'operational_observer_pass':ok}))
    return 0 if ok else 3

if __name__ == '__main__':
    raise SystemExit(main())
