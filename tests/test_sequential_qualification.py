import pytest
from experiments.sequential.qualification import initial,exact_value,public_oracle,sample,replicate,REGIMES
from experiments.sequential.finite_history_q import validate

@pytest.mark.parametrize('regime',REGIMES)
def test_exact_probability_and_stop(regime):
 assert sum(x[3] for x in initial(regime))==pytest.approx(1)
 assert exact_value(lambda h,t:(0,False),regime)[0]==pytest.approx(.55)
 assert .55-1e-12<=exact_value(public_oracle(regime),regime)[0]<=1
 validate(sample(100,8,regime,'x'),2)


def test_null_no_strategy_changes_truth():
 for a in range(3):assert exact_value(lambda h,t:(a,False),'null')[0]==pytest.approx(.55)
 assert exact_value(public_oracle('null'),'null')[0]==pytest.approx(.55)


def test_learned_value_cannot_exceed_public_oracle():
 r=replicate(1000,44,'mode_specific',300)
 v=r['variants']['history'];assert not v['fit_error']
 assert v['exact_value']<=exact_value(public_oracle('mode_specific'),'mode_specific')[0]+1e-12
 assert 'dr' in v
