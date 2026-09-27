import signal
import pytest
from experiments.prompt_choice import native_execution_v1 as n


def rec(**kw):
    return {'sandbox_kind':'seatbelt','executed':True,'stdout':'','stderr':'','returncode':0,'timed_out':False,**kw}


@pytest.mark.parametrize('stream',['stdout','stderr'])
def test_clean_exit_at_cap_is_not_pass(stream):
    r=n.classify(rec(**{stream:'x'*1024}),1024)
    assert r['disposition']=='output_limit' and r['test_outcome'] is None and r['feedback_status'] is None


def test_completion_is_ungraded():
    r=n.classify(rec(stdout='PASS'),1024)
    assert r['disposition']=='completed_ungraded' and r['test_outcome'] is None


def test_timeout_and_cap_flags_both_retained():
    r=n.classify(rec(stdout='x'*1024,timed_out=True,returncode=-9),1024)
    assert r['disposition']=='timeout' and r['output_saturated']


@pytest.mark.parametrize('code,expected',[(-signal.SIGXFSZ,'output_limit'),(1,'process_error'),(-9,'process_error')])
def test_exit_status(code,expected):
    assert n.classify(rec(returncode=code),1024)['disposition']==expected


@pytest.mark.parametrize('kw',[{'sandbox_kind':'none'},{'executed':False},{'stdout':None},{'timed_out':None},{'returncode':True}])
def test_invalid_records_fail_closed(kw):
    with pytest.raises(ValueError):n.classify(rec(**kw),1024)


def test_exact_cap_is_conservative_even_if_legitimate():
    assert n.classify(rec(stdout='x'*1023),1024)['disposition']=='completed_ungraded'
    assert n.classify(rec(stdout='x'*1024),1024)['disposition']=='output_limit'


@pytest.mark.parametrize('kw',[{'mem_bytes':0},{'mem_bytes':3<<30},{'timeout_s':float('nan')},{'timeout_s':11},{'cpu_seconds':True},{'output_cap':True}])
def test_invalid_limits_before_dispatch(monkeypatch,kw):
    monkeypatch.setattr(n.sandbox,'run_program',lambda *a,**k:pytest.fail('must not dispatch'))
    with pytest.raises(ValueError):n.run('pass',**kw)
