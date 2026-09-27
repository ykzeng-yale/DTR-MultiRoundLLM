import importlib.util
from pathlib import Path
import pytest

P = Path(__file__).resolve().parents[1] / 'scripts/inventory_bigcodebench_rows_20260927.py'
S = importlib.util.spec_from_file_location('row_inventory', P)
m = importlib.util.module_from_spec(S)
S.loader.exec_module(m)


def row(**kw):
    r = {k: '' for k in m.FIELDS}
    r.update(task_id='synthetic/0', complete_prompt='def f():\n', canonical_solution='    return 1\n',
             instruct_prompt='return one', test='import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(f(), 1)\n',
             entry_point='f', doc_struct='{"examples": []}', libs="['os', 'os', 'json']")
    r.update(kw)
    return r


def test_duplicates_counts_and_ast():
    r=m.summarize([row(),row(task_id='synthetic/1')])
    assert r['row_count']==2
    assert r['declared_library_task_counts']=={'json':2,'os':2}
    assert not r['duplicate_exact_bytes']['task_id']
    assert len(r['duplicate_exact_bytes']['complete_prompt'])==1
    assert r['rows'][0]['test_static']['test_method_count']==1
    assert r['rows'][0]['reference_static']['parseable']


def test_malicious_libs_are_not_executed(tmp_path):
    sentinel=tmp_path/'should_not_exist'
    d=m.summarize([row(libs=f"__import__('pathlib').Path({str(sentinel)!r}).touch()")])
    assert d['rows'][0]['libs_error']=='ValueError'
    assert not sentinel.exists()


def test_source_is_parsed_not_run(tmp_path):
    sentinel=tmp_path/'should_not_exist'
    d=m.summarize([row(test=f"open({str(sentinel)!r}, 'w').write('bad')")])
    assert d['rows'][0]['test_static']['parseable']
    assert not sentinel.exists()


def test_missing_malformed_and_duplicate_ids_preserved():
    d=m.summarize([row(libs=None,doc_struct='bad',test='def:'),row()])
    assert d['missing_or_blank']['libs']==1
    assert len(d['duplicate_exact_bytes']['task_id'])==1
    assert d['rows'][0]['doc_error']
    assert not d['rows'][0]['test_static']['parseable']


def test_schema_refused():
    with pytest.raises(ValueError):m.summarize([{'task_id':'x'}])
    with pytest.raises(ValueError):m.summarize([row(libs=[])])


def test_cli_refuses_overwrite_before_opening_input(tmp_path, monkeypatch):
    out=tmp_path/'saved.json';out.write_text('preserve')
    monkeypatch.setattr(m.sys,'argv',['inventory','--source',str(tmp_path/'absent'),'--out',str(out)])
    with pytest.raises(ValueError,match='overwrite'):m.main()
    assert out.read_text()=='preserve'


def test_cli_refuses_changed_source_before_reader_import(tmp_path, monkeypatch):
    source=tmp_path/'source';source.write_bytes(b'wrong pinned input')
    out=tmp_path/'out'
    monkeypatch.setattr(m.sys,'argv',['inventory','--source',str(source),'--out',str(out)])
    with pytest.raises(ValueError,match='hash mismatch'):m.main()
    assert not out.exists()
