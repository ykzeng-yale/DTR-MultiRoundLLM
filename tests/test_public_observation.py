import json
import pytest
from experiments.prompt_choice import public_observation_v1 as p
from experiments.prompt_choice import observation_boundary_v1 as ob
from experiments.prompt_choice.status_feedback_v1 import TEXT


def case(scope='public',expected=8):return {'scope':scope,'entry_point':'task_func','args':[7],'expected':expected}

def runner(value):
    def run(source,**kw):return {'execution':{'disposition':'completed_ungraded'},'raw_process':{'stdout':json.dumps({'observation_version':ob.VERSION,'value':value})}}
    return run


def test_private_case_rejected_before_any_execution():
    def no(*a,**kw):raise AssertionError('executed private case')
    with pytest.raises(ValueError,match='scope'):p.public_check('def task_func(x): return x',case('private'),runner=no)


def test_public_status_only_and_private_result_does_not_change_it():
    public=p.public_check('def task_func(x): return x+1',case(),runner=runner(8))
    assert public['feedback_text']==TEXT['PASS']
    for hidden in [8,999999]:
        private=p.private_check('def task_func(x): return x+1',case('private',hidden),runner=runner(8))
        assert 'feedback_text' not in private
        assert public['feedback_text']==TEXT['PASS']


@pytest.mark.parametrize('value,status',[(8,'PASS'),(7,'FAIL'),(True,'FAIL')])
def test_producer_uses_external_comparison(value,status):
    assert p.public_check('def task_func(x): return x',case(),runner=runner(value))['feedback_text']==TEXT[status]


def test_forged_verdict_is_incomplete_and_never_rendered():
    def bad(*a,**kw):return {'execution':{'disposition':'completed_ungraded'},'raw_process':{'stdout':'{"passed":true,"secret":"canary"}'}}
    out=p.public_check('pass',case(),runner=bad)
    assert out['feedback_text']==TEXT['INCOMPLETE'] and 'canary' not in out['feedback_text']


def test_changed_case_and_scope_bindings_distinct():
    assert len({p.case_binding(case('public',8),'public'),p.case_binding(case('public',9),'public'),p.case_binding(case('private',8),'private')})==3
