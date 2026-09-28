import numpy as np
import pytest
from experiments.sequential import pooled_history_q as q
from experiments.sequential.qualification import sample,exact_value,public_oracle


def test_features_keep_history_and_compression_is_explicit():
 assert not np.array_equal(q.features((0,1,1),'history'),q.features((2,1,1),'history'))
 assert np.array_equal(q.features((0,1,1),'last'),q.features((2,1,1),'last'))


def test_nonoracle_stop_and_family_separation():
 data=sample(256,2026092800,'null','train');m=q.fit(data,2)
 assert 0<q.predict(m,(1,),0)[2][0]<1
 assert exact_value(lambda h,t:q.predict(m,h,t)[:2],'null')[0]==pytest.approx(.55)
 with pytest.raises(ValueError,match='family'):q.evaluate_holdout(m,data)


def test_nonzero_logged_weights_and_oracle_bound():
 data=sample(300,7,'mode_specific','train');m=q.fit(data,2)
 assert exact_value(lambda h,t:q.predict(m,h,t)[:2],'mode_specific')[0]<=exact_value(public_oracle('mode_specific'),'mode_specific')[0]+1e-12
 rows=q.evaluate_holdout(m,sample(100,8,'mode_specific','test'))
 assert len(rows)==100 and all(np.isfinite(x['dr']) for x in rows)


def test_absent_action_is_refused():
 data=[e for e in sample(100,4,'null','train') if e['steps'][0]['action']==0]
 with pytest.raises(ValueError,match='absent'):q.fit(data,1)
