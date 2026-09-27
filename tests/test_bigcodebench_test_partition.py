import importlib.util
from pathlib import Path
S=importlib.util.spec_from_file_location('partition',Path(__file__).resolve().parents[1]/'scripts/audit_bigcodebench_test_partition_20260927.py')
m=importlib.util.module_from_spec(S);S.loader.exec_module(m)


def test_sorted_partition_and_fixture():
    r=m.partition('import unittest\nclass TestCases(unittest.TestCase):\n def setUp(self): pass\n def test_z(self): self.assertEqual(2,2)\n def test_a(self): self.assertEqual(1,1)\n')
    assert r['status']=='structurally_partitionable'
    assert r['public_candidate']['name']=='test_a'
    assert [x['name'] for x in r['private_candidates']]==['test_z']
    assert r['fixtures']==['setUp']
    assert not r['syntactic_public_private_overlap']


def test_duplicate_body_and_assertion_flagged():
    r=m.partition('class TestCases(unittest.TestCase):\n def test_a(self): self.assertTrue(f())\n def test_b(self): self.assertTrue(f())\n')
    assert r['syntactic_public_private_overlap'][0]['identical_body']


def test_duplicate_names_do_not_silently_disappear():
    r=m.partition('class TestCases(unittest.TestCase):\n def test_a(self): pass\n def test_a(self): pass\n')
    assert 'duplicate_method_names' in r['reasons']


def test_other_class_not_scored_and_source_not_executed(tmp_path):
    target=tmp_path/'sentinel'
    r=m.partition(f"open({str(target)!r},'w')\nclass TestCases(unittest.TestCase):\n def test_a(self): pass\n def test_b(self): pass\nclass Extra(unittest.TestCase):\n def test_c(self): pass\n")
    assert not target.exists()
    assert r['method_count']==2 and r['additional_classes']==['Extra']
    assert r['module_executable_node_types']==['Expr']


def test_custom_inheritance_and_async_held():
    r=m.partition('class TestCases(Custom):\n async def test_a(self): pass\n def test_b(self): pass\n')
    assert set(r['reasons'])=={'nonstandard_inheritance','async_test'}


def test_absent_class_held():
    assert m.partition('x=1')['status']=='hold'
