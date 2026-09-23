"""Actual collector -> real grading guards -> analyzer, with external boundaries mocked.

No HTTP request, receiver/model, containment payload, candidate or reference program executes.
Fixture attestation and Git snapshots exist only in temporary test directories, never evidence artifacts.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_e13a_collect import (ROOT, ec, sc, collect, builder, e12_state, plan,
                               real_bound_fixture)
from test_e13a_grade import e13a_grade as eg, e13a_analyze as ea


@pytest.fixture
def integrated(real_bound_fixture, monkeypatch):
    f = real_bound_fixture
    release = f['stage']['release_dir']
    rel = (release / 'release_manifest.json').relative_to(ROOT).as_posix()
    # Relocate only the path allowlist to the temporary release. All byte/source/contract
    # checks below remain live, including the committed-blob comparison.
    monkeypatch.setattr(eg.study_adapter, 'COMMITTED_RELEASE_MANIFESTS', (rel,))
    def git_run(args, **kwargs):
        assert args[:5] == ['git', '-C', str(ROOT), 'cat-file', 'blob']
        name = args[5].split(':', 1)[1]
        return SimpleNamespace(returncode=0, stdout=f['blobs'][name])
    monkeypatch.setattr(eg.study_adapter.subprocess, 'run', git_run)
    stub = eg.StubPrivateExecutor(default_candidate=1)
    monkeypatch.setattr(eg.private_grade.sandbox, 'run_program', stub)
    monkeypatch.setattr(eg.private_grade.platform, 'platform', lambda: 'synthetic-platform-test-only')
    attestation = f['out'].parent / 'synthetic-attestation.json'
    attestation.write_text(json.dumps({
        'schema_version': 'landmark-containment-v1', 'passed': True,
        'binding': eg.private_grade.current_binding(),
        'script_sha256': eg.file_sha(ROOT / 'scripts/check_landmark_sandbox.py'),
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'checks': [{'name': name, 'passed': True, 'payload_started': True}
                   for name in sorted(eg.private_grade.REQUIRED_CHECKS)],
        'test_only': 'synthetic gate evidence; no containment check ran',
    }))
    return {**f, 'stub': stub, 'attestation': attestation}


def collect_and_grade(f, plan):
    completion = ec.dispatch(f['stage'], plan, f['out'], real=True, ownership=f['ownership'])
    assert eg.main(['--collect', str(f['out'] / 'collect'), '--release', str(f['stage']['release_dir']),
                    '--out', str(f['out']), '--real', '--stage', str(f['stage']['stage_path']),
                    '--plan', str(ec.PLAN), '--attestation', str(f['attestation'])]) == 0
    summary = json.loads((f['out'] / 'grade/summary.json').read_text())
    return completion, summary


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_dispatch_actual_schema_to_real_guarded_grade_and_analyzer(integrated, plan, capsys):
    f = integrated
    completion, summary = collect_and_grade(f, plan)
    assert completion['recorded_slots'] == summary['assigned_slots'] == summary['grade_rows'] == 60
    assert summary['status'] == 'complete' and summary['graded_slots'] == 60
    assert summary['start_accounting']['used'] == {'candidate': 5, 'recheck': 10, 'containment': 9, 'total': 24}
    ledger = rows(f['out'] / 'grade/execution_ledger.jsonl')
    starts = [r for r in ledger if r['event'] == 'execution_start']
    results = [r for r in ledger if r['event'] == 'execution_result']
    assert len(starts) == len(results) == len(f['stub'].calls) == 15
    assert all(a['n'] == b['n'] and a['program_sha256'] == b['program_sha256']
               for a, b in zip(starts, results))
    snapshot = json.loads((f['out'] / sc.CLOCK_FILE).read_text())
    assert snapshot['spent']['collection'] > 0 and snapshot['spent']['private_grading'] > 0
    assert snapshot['active_phase'] is None
    ea.main(['--grades', str(f['out'] / 'grade/grades.jsonl'), '--stage', str(ec.STAGE),
             '--out', str(f['out'] / 'analysis.json')])
    report = json.loads((f['out'] / 'analysis.json').read_text())
    assert report['accounting']['assigned_slots'] == report['accounting']['graded_slots'] == 60
    assert report['accounting']['usage_totals']['calls_known_sum'] == 60
    assert report['accounting']['usage_totals']['prompt_tokens_known_sum'] == 660
    assert report['accounting']['usage_totals']['completion_tokens_known_sum'] == 420
    capsys.readouterr()
    with pytest.raises(eg.HandoffRefusal, match='overwrite'):
        eg.grade(f['out'] / 'collect', f['stage']['release_dir'], f['out'], real=True,
                 stage=ec.STAGE, plan=ec.PLAN, attestation_path=f['attestation'])


def test_actual_handoff_refuses_injected_real_executor(integrated, plan):
    f = integrated
    ec.dispatch(f['stage'], plan, f['out'], real=True, ownership=f['ownership'])
    with pytest.raises(eg.HandoffRefusal, match='injected executors'):
        eg.grade(f['out'] / 'collect', f['stage']['release_dir'], f['out'], real=True,
                 executor=eg.StubPrivateExecutor(), stage=ec.STAGE, plan=ec.PLAN,
                 attestation_path=f['attestation'])
    assert not f['stub'].calls and not (f['out'] / 'grade').exists()


def test_real_grade_rejects_actual_transport_handoff(integrated, plan, e12_state):
    from test_e13a_collect import FakeReceiver
    f = integrated
    adapter = FakeReceiver(e12_state, f['stage']['release']['config']['model_digest'])
    ec.dispatch(f['stage'], plan, f['out'], adapter=adapter, real=False)
    with pytest.raises(eg.HandoffRefusal, match='transport-only collection'):
        eg.grade(f['out'] / 'collect', f['stage']['release_dir'], f['out'], real=True,
                 stage=ec.STAGE, plan=ec.PLAN, attestation_path=f['attestation'])
    assert not f['stub'].calls and not (f['out'] / 'grade').exists()


def test_grade_interruption_preserves_all_slots_and_unknown_starts(integrated, plan, monkeypatch):
    f = integrated
    ec.dispatch(f['stage'], plan, f['out'], real=True, ownership=f['ownership'])
    stub = f['stub']
    class Interrupted:
        def set_context(self, *args):
            stub.set_context(*args)
        def __call__(self, program, **kwargs):
            if stub.context['kind'] == 'candidate':
                raise KeyboardInterrupt('synthetic executor interruption; execution status unknown')
            return stub(program, **kwargs)
    monkeypatch.setattr(eg.private_grade.sandbox, 'run_program', Interrupted())
    summary = eg.grade(f['out'] / 'collect', f['stage']['release_dir'], f['out'], real=True,
                       stage=ec.STAGE, plan=ec.PLAN, attestation_path=f['attestation'])
    graded = rows(f['out'] / 'grade/grades.jsonl')
    assert summary['status'] == 'aborted' and len(graded) == 60
    assert all(r['outcome'] is None and r['missing_reason'] for r in graded)
    assert sum(r['executor_starts'] is None for r in graded) == 1
    assert summary['start_accounting']['unknown_execution_starts']['candidate'] == 1
    assert summary['start_accounting']['reserved_execution_attempts']['total'] == 12
    ledger = rows(f['out'] / 'grade/execution_ledger.jsonl')
    assert len([r for r in ledger if r['event'] == 'execution_start']) == 3
    unknown = [r for r in ledger if r['event'] == 'execution_result' and r['execution_started'] is None]
    assert len(unknown) == 1 and 'KeyboardInterrupt' in unknown[0]['error']
    assert json.loads((f['out'] / sc.CLOCK_FILE).read_text())['spent']['private_grading'] > 0
    assert (f['out'] / 'grade/failure_report.json').is_file()


def test_real_grade_refuses_actual_receiver_drift_keeps_collection(integrated, plan, monkeypatch):
    f = integrated
    original = collect.LlamaServer.request
    def drifting(self, endpoint, payload, timeout):
        answer = original(self, endpoint, payload, timeout)
        if endpoint == "/props":
            if any(name == "/v1/chat/completions" for name, _, _ in f["requests"]):
                answer["total_slots"] += 1
        return answer
    monkeypatch.setattr(collect.LlamaServer, "request", drifting)
    completion = ec.dispatch(f["stage"], plan, f["out"], real=True, ownership=f["ownership"])
    assert 0 < completion["slots_with_output"] < 60
    assert completion["recorded_slots"] == 60
    assert completion["receiver_verification"]["status"] == "receiver_not_verified_outputs_retained"
    original_bytes = (f["out"] / "collect/calls.jsonl").read_bytes()
    with pytest.raises(eg.HandoffRefusal, match="passed receiver guard"):
        eg.grade(f["out"] / "collect", f["stage"]["release_dir"], f["out"], real=True,
                 stage=ec.STAGE, plan=ec.PLAN, attestation_path=f["attestation"])
    assert not f["stub"].calls and not (f["out"] / "grade").exists()
    assert (f["out"] / "collect/calls.jsonl").read_bytes() == original_bytes


def test_real_grade_accepts_ordinary_missing_call_with_passing_receiver_guard(integrated, plan, monkeypatch):
    f = integrated
    original = collect.LlamaServer.request
    generations = {"count": 0}
    def missing_once(self, endpoint, payload, timeout):
        if endpoint == "/v1/chat/completions":
            generations["count"] += 1
            if generations["count"] == 1:
                raise OSError("synthetic isolated transport failure")
        return original(self, endpoint, payload, timeout)
    monkeypatch.setattr(collect.LlamaServer, "request", missing_once)
    completion, summary = collect_and_grade(f, plan)
    assert completion["receiver_verification"]["status"] == "receiver_guard_checks_passed"
    assert completion["fatal_error"] is None
    assert completion["attempted_calls"] == 60 and completion["slots_missing"] == 1
    graded = rows(f["out"] / "grade/grades.jsonl")
    assert summary["grade_rows"] == 60 and summary["graded_slots"] == 59
    missing = [r for r in graded if r["outcome"] is None]
    assert len(missing) == 1 and "transport failure" in missing[0]["missing_reason"]
    assert missing[0]["prompt_tokens"] is None and missing[0]["completion_tokens"] is None
