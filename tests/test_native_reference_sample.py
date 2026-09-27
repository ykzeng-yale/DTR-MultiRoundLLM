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


def test_explicit_runtime_requires_successful_matching_qualification(tmp_path):
    import hashlib
    import pytest
    from scripts.audit_native_reference_sample_20260927 import validate_qualification
    path=tmp_path/'receipt.json'
    receipt={'passed':True,'error':None,'python':'/pinned/python','python_sha256':'binary','bundle_sha256':'tree'}
    plan={'python':'/pinned/python','tree_sha256':'tree','qualification_summary':str(path),'input_sha256':{'/pinned/python':'binary'}}
    def save():
        path.write_text(json.dumps(receipt));plan['input_sha256'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    save();validate_qualification(plan)
    for key,value in [('passed',False),('python','/other/python'),('bundle_sha256','other'),('error','failed')]:
        old=receipt[key];receipt[key]=value;save()
        with pytest.raises(ValueError):validate_qualification(plan)
        receipt[key]=old
    save();path.write_text('{}')
    with pytest.raises(ValueError):validate_qualification(plan)
