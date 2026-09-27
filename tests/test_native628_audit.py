import ast
import importlib.util
from pathlib import Path
S=importlib.util.spec_from_file_location('audit628',Path(__file__).resolve().parents[1]/'scripts/audit_native628_20260927.py');m=importlib.util.module_from_spec(S);S.loader.exec_module(m)


def test_control_sources_parse_without_execution():
    c=m.controls();assert set(c)=={'empty_axes','constant_line'}
    for source in c.values():ast.parse(source)
    assert 'ax.plot' not in c['empty_axes']
    assert 'ax.plot([0,1,2],[0,0,0])' in c['constant_line']


def test_public_private_selection_and_supplement_is_separate():
    source='def task_func(): return None\n';test='class TestCases: pass\n'
    a=m.program(source,'public',test);b=m.program(source,'private',test);c=m.program(source,'supplement',test)
    assert "['test_case_1']" in a and "['test_case_2', 'test_case_3', 'test_case_4', 'test_case_5']" in b
    assert 'class TestCases' not in c and 'max(ys)-min(ys)>1e-6' in c
    for x in [a,b,c]:ast.parse(x)
