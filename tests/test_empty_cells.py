"""Structural checks, not empirical validation."""
import importlib.util
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location('empty_cells', Path(__file__).resolve().parents[1]/'scripts/diagnose_empty_cells.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def fixture():
    rng = np.random.default_rng(103)
    return m.simulate(8, 3, 3, m.kernel(1), m.make_beh(0, .05, 0), rng)


def test_array_recursion_and_dr_parity():
    d=fixture(); train=np.flatnonzero(d['task']<5)
    Q,fb,v=m.fit_q(d,3,m.UNIF5,idx=train)
    av,table,_,_=m.array_fit(d,train)
    np.testing.assert_allclose(av,v,atol=1e-14,rtol=0)
    np.testing.assert_allclose(m.table_dr(d,table),m.dr_scores(d,3,m.UNIF5,Q,fb),atol=1e-12,rtol=0)


def test_oracle_fills_wholly_missing_states_and_propagates_backwards():
    d={'elig':np.ones((2,2),bool),'S':np.array([[0,0],[1,1]]),
       'A':np.array([[1,1],[1,1]]),'Y':np.zeros(2),'task':np.array([0,1])}
    pop=np.ones((2,4,5))
    original,_,_,_=m.array_fit(d,np.array([0]))
    value,table,count,roots=m.array_fit(d,np.array([0]),pop)
    assert table[1,1,1]==1 and table[0,1,1]==1
    assert table[1,0,1]==0 and table[0,0,1]==.8
    np.testing.assert_allclose(value,[.96,1])
    assert original[0]==0 and count[0,0,1]==1 and roots[0,0,1]==1


def test_heldout_outcomes_do_not_leak_into_fits():
    d=fixture(); train=np.flatnonzero(d['task']<5)
    pop=np.full((3,4,5),.31)
    before=m.array_fit(d,train,pop)[0]
    d['Y']=d['Y'].copy(); d['Y'][d['task']>=5]=17
    after=m.array_fit(d,train,pop)[0]
    np.testing.assert_array_equal(before,after)


def test_all_cells_observed_oracle_has_no_effect():
    s=np.repeat(np.arange(4),5); a=np.tile(np.arange(5),4)
    d={'elig':np.ones((20,1),bool),'S':s[:,None],'A':a[:,None],
       'Y':s/3,'task':np.arange(20)}
    v,_,count,_=m.array_fit(d,np.arange(20))
    ov,_,_,_=m.array_fit(d,np.arange(20),np.zeros((1,4,5)))
    assert count.min()==1
    np.testing.assert_array_equal(v,ov)
