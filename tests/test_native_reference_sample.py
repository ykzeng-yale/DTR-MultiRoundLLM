import json
from scripts.audit_native_reference_sample_20260927 import render, extract, MARKER


def test_source_preserved_and_named_class_only():
    row={'complete_prompt':'def task_func():\n','canonical_solution':'    return 1\n','test':'class TestCases: pass\n'}
    text=render(row)
    assert row['complete_prompt']+row['canonical_solution']+'\n'+row['test'] in text
    assert 'loadTestsFromTestCase(TestCases)' in text


def test_report_requires_completed_process_unique_marker_and_typed_counts():
    report={'tests_run':5,'failures':0,'errors':0,'skips':0,'expected_failures':0,'unexpected_successes':0,'was_successful':True}
    raw={'execution':{'disposition':'completed_ungraded'},'raw_process':{'stdout':MARKER+json.dumps(report)}}
    assert extract(raw)==report
    raw['raw_process']['stdout']+='\n'+raw['raw_process']['stdout'];assert extract(raw) is None
    report['tests_run']=True;raw['raw_process']['stdout']=MARKER+json.dumps(report);assert extract(raw) is None
    raw['execution']['disposition']='timeout';assert extract(raw) is None
