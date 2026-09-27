import ast
import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('adjudication',Path(__file__).resolve().parents[1]/'scripts/adjudicate_bigcodebench_partition_flags_20260927.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def test_decorators_and_signature_prevent_false_duplicate():
    a=ast.parse('@patch("x",return_value=1)\ndef test_a(self,x): pass').body[0]
    b=ast.parse('@patch("x",return_value=2)\ndef test_b(self,x): pass').body[0]
    c=ast.parse('@patch("x",return_value=1)\ndef test_c(self,x): pass').body[0]
    assert m.method_fingerprint(a)!=m.method_fingerprint(b)
    assert m.method_fingerprint(a)==m.method_fingerprint(c)
    assert a.name=='test_a'


def test_shadowing_preserves_later_definition():
    r=m.inspect('class TestCases(unittest.TestCase):\n def test_a(self): return 0\n def test_a(self): return 1\n def test_b(self): return 1\n')
    assert r['declared_test_definitions']==3 and r['distinct_direct_names']==2
    assert len(r['shadowed_definitions'])==1
    assert r['same_full_method_ast_private']==['test_b']


def test_source_not_executed(tmp_path):
    p=tmp_path/'sentinel'
    r=m.inspect(f'open({str(p)!r},"w")\nclass TestCases(unittest.TestCase):\n def test_a(self): pass\n def test_b(self): pass\n')
    assert not p.exists() and r['private_distinct_from_public_count']==0
