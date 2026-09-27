from fractions import Fraction as F
from itertools import product
import pytest
from experiments.prompt_choice.measurement_sensitivity_v1 import semantic_contrast_interval as interval,usefulness


def test_exhaustive_binary_pairs_all_empirical_distributions():
    atoms=list(product([0,1],repeat=4)) # Yd,Zd,Yb,Zb
    for i,a in enumerate(atoms):
        for b in atoms[i:]:
            sample=[a,b];grade=sum(F(x[1]-x[3],2) for x in sample);truth=sum(F(x[0]-x[2],2) for x in sample)
            fp=sum(F(x[1]==1 and x[0]==0,2) for x in sample);fn=sum(F(x[1]==0 and x[0]==1,2) for x in sample)
            bp=sum(F(x[3]==1 and x[2]==0,2) for x in sample);bn=sum(F(x[3]==0 and x[2]==1,2) for x in sample)
            assert truth==grade-fp+fn+bp-bn
            lo,hi=interval(grade,grade,false_positive_policy=fp,false_negative_policy=fn,false_positive_baseline=bp,false_negative_baseline=bn)
            assert lo<=truth<=hi


def test_directional_errors_and_strict_threshold():
    x=interval(F(8,100),F(12,100),false_positive_policy=F(2,100),false_negative_policy=0,false_positive_baseline=0,false_negative_baseline=F(1,100))
    assert x==(F(5,100),F(12,100)) and usefulness(x)=='inconclusive'
    assert usefulness((F(51,1000),F(1,10)))=='benefit'
    assert usefulness((F(-1),F(49,1000)))=='useful_gain_futility'


def test_unknown_errors_are_vacuous():
    assert interval(0,0,false_positive_policy=1,false_negative_policy=1,false_positive_baseline=1,false_negative_baseline=1)==(F(-1),F(1))


@pytest.mark.parametrize('bad',[True,.1,F(-1,10),F(11,10)])
def test_invalid_error_bounds_refused(bad):
    with pytest.raises(ValueError):interval(0,0,false_positive_policy=bad,false_negative_policy=0,false_positive_baseline=0,false_negative_baseline=0)
