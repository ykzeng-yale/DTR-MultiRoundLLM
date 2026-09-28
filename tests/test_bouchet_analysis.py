import copy
import pytest
from experiments.bouchet.analyze_calibration_v1 import analyze,digest


def fixture():
    plan={'requests':[{'slot':i,'length_label':'short','payload':{'seed':i}} for i in range(9)]}
    calls=[{'slot':i,'payload_sha256':digest({'seed':i}),'status':'returned','seconds':1.0,'response':{'usage':{'prompt_tokens':100,'completion_tokens':91},'choices':[{'message':{'content':'1. ready\n2. ready'}}]}} for i in range(9)]
    return plan,{'calls':calls,'unattempted':0,'elapsed_seconds':12,'error':None,'state_unchanged':True,'guard_failures':[]}


def test_short_output_not_full_instruction_success():
    p,r=fixture();a=analyze(p,r)
    assert a['returned']==9 and a['completion_tokens']==819
    assert a['exact_instruction_compliance']==0
    assert a['all_nine_returned_without_recorded_error']


def test_failed_and_unattempted_stay_accounted():
    p,r=fixture();r['calls']=r['calls'][:2];r['calls'][1]={'slot':1,'payload_sha256':digest({'seed':1}),'status':'failed'};r['unattempted']=7;r['error']='timeout'
    a=analyze(p,r);assert (a['returned'],a['assigned'],a['unattempted'])==(1,2,7)
    assert not a['all_nine_returned_without_recorded_error']


@pytest.mark.parametrize('change',[{'slot':3},{'payload_sha256':'wrong'},{'seconds':float('nan')}])
def test_mismatched_or_invalid_records_refused(change):
    p,r=fixture();r['calls'][0].update(change)
    with pytest.raises(ValueError):analyze(p,r)
