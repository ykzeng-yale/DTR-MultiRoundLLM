"""Synthetic tests for the static public-examples overlap auditor (no execution)."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    'check_public_examples', ROOT / 'scripts' / 'check_public_diagnostic_examples_20260921.py')
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

# Controls/reference text that would raise if ever executed.
BOOM = "def parallelogram_area(b, h):\n    raise SystemExit('EXECUTED')\n"


def _write(tmp_path, public_args, private_asserts, expected='77'):
    ex = tmp_path / 'examples.json'
    ex.write_text(json.dumps({'version': 'synthetic', 'cases': [
        {'root_id': 'mbpp/52', 'entry_point': 'parallelogram_area',
         'cases': [{'case_id': 'p-1', 'args_literal': public_args,
                    'expected_literal': expected}]}]}))
    sp = tmp_path / 'specs.jsonl'
    sp.write_text(json.dumps({'root_id': 'mbpp/52', 'entry_point': 'parallelogram_area',
                              'reference': BOOM, 'negative_controls': [{'code': BOOM}],
                              'private_assertions': private_asserts}) + '\n')
    return ex, sp


@pytest.fixture(autouse=True)
def _no_execution(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('subprocess used'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('subprocess used'))


def test_literal_overlap_holds(tmp_path):
    ex, sp = _write(tmp_path, '[7,11]', ['assert parallelogram_area(7,11)==77', 'assert parallelogram_area(2,3)==6'])
    out = tmp_path / 'out.json'
    assert mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(out), '--expected-case-count', '1']) == 1
    r = json.loads(out.read_text())
    assert r['overlap_gate'] == 'HOLD' and r['cases'][0]['literal_private_input_overlap'] is True
    assert r['candidate_reference_executions'] == 0


def test_no_overlap_passes(tmp_path):
    ex, sp = _write(tmp_path, '[7,11]', ['assert parallelogram_area(10,20)==200'])
    out = tmp_path / 'out.json'
    assert mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(out),
                     '--expected-case-count', '1']) == 0
    r = json.loads(out.read_text())
    assert r['overlap_gate'] == 'PASS' and r['case_count'] == 1


def test_refuses_existing_out(tmp_path, capsys):
    ex, sp = _write(tmp_path, '[7,11]', ['assert parallelogram_area(10,20)==200'])
    out = tmp_path / 'out.json'
    out.write_text('keep')
    assert mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(out), '--expected-case-count', '1']) == 2
    assert out.read_text() == 'keep'
    with pytest.raises(FileExistsError):
        mod.write_new(out, {})


def test_input_hashes_recorded(tmp_path):
    ex, sp = _write(tmp_path, '[7,11]', ['assert parallelogram_area(10,20)==200'])
    out = tmp_path / 'out.json'
    mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(out), '--expected-case-count', '1'])
    r = json.loads(out.read_text())
    eh, sh = hashlib.sha256(ex.read_bytes()).hexdigest(), hashlib.sha256(sp.read_bytes()).hexdigest()
    assert r['examples_sha256'] == eh and r['private_specs_sha256'] == sh
    assert r['input_sha256'] == {str(ex): eh, str(sp): sh}
    assert r['examples_path'] == str(ex) and r['private_specs_path'] == str(sp)


def test_audits_passed_specs_not_hardcoded(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'LEGACY_PRIVATE_SPECS', tmp_path / 'nonexistent.jsonl')
    ex, sp = _write(tmp_path, '[7,11]', ['assert parallelogram_area(10,20)==200'])
    out = tmp_path / 'out.json'
    assert mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(out), '--expected-case-count', '1']) == 0


def test_missing_root_and_case_count_errors(tmp_path):
    ex, sp = _write(tmp_path, '[7,11]', ['assert parallelogram_area(10,20)==200'])
    out = tmp_path / 'out.json'
    assert mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(out),
                     '--expected-case-count', '21']) == 3
    assert not out.exists()
    sp.write_text(json.dumps({'root_id': 'mbpp/999', 'entry_point': 'f', 'private_assertions': []}) + '\n')
    assert mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(out), '--expected-case-count', '1']) == 3
    assert not out.exists()


def test_partial_args_rejected(tmp_path):
    with pytest.raises(SystemExit):
        mod.main(['--examples', 'x.json'])


def test_overlap_normalizes_tuples_and_keeps_bool_distinct():
    # MRL-10 review: a public list-of-lists input equal to a private tuple-list input is an overlap.
    assert mod._norm([[2, 4], [6, 7]]) in [mod._norm([(2, 4), (6, 7)])]
    assert mod._norm([True]) != mod._norm([1])


def test_legacy_mode_refuses_existing_output(tmp_path, monkeypatch):
    out = tmp_path / 'legacy.json'
    out.write_text('PRECIOUS')
    monkeypatch.setattr(mod, 'LEGACY_OUT', out)
    monkeypatch.setattr(mod, 'build_result', lambda *a, **k: {'overlap_gate': 'PASS'})
    monkeypatch.setattr(mod, '_summary', lambda r: None)
    with pytest.raises(FileExistsError):
        mod.legacy_main()
    assert out.read_text() == 'PRECIOUS'


def test_expected_case_count_is_required(tmp_path):
    """MRL-10: the count check can no longer be skipped by omission."""
    ex, sp = _write(tmp_path, '[7,11]', ['assert parallelogram_area(2,3)==6'])
    with pytest.raises(SystemExit):
        mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(tmp_path / 'o.json')])


def test_duplicate_json_key_is_an_audit_error(tmp_path):
    ex, sp = _write(tmp_path, '[7,11]', ['assert parallelogram_area(2,3)==6'])
    sp.write_text(sp.read_text().rstrip('\n')[:-1] + ', "root_id": "mbpp/52"}\n')
    assert mod.main(['--examples', str(ex), '--private-specs', str(sp), '--out', str(tmp_path / 'o.json'),
                     '--expected-case-count', '1']) != 0
    assert not (tmp_path / 'o.json').exists()
