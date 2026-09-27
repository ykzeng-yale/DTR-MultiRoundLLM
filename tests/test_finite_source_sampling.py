"""Exact synthetic without-replacement laws, not receiver/power evidence."""
from fractions import Fraction as F
from itertools import combinations, product
from math import comb

import pytest
from experiments.prompt_choice.paired_inference import paired_contrasts

LAWS = (
    ((((-1, 0), F(1, 4)), ((1, 1), F(3, 4))),
     (((0, -1), F(2, 3)), ((1, 0), F(1, 3))),
     (((-1, 1), F(1, 2)), ((0, -1), F(1, 2)))),
    ((((F(-1, 2), F(1, 2)), F(1, 3)), ((F(1, 2), 0), F(2, 3))),
     (((0, F(-1, 2)), F(1, 5)), ((1, F(1, 2)), F(4, 5))),
     (((-1, 1), F(3, 4)), ((F(1, 2), -1), F(1, 4)))),
)


def draws(laws, n):
    for subset in combinations(range(len(laws)), n):
        for outcome in product(*(laws[g] for g in subset)):
            probability = F(1, comb(len(laws), n))
            for _, p in outcome:
                probability *= p
            yield subset, tuple(v for v, _ in outcome), probability


@pytest.mark.parametrize('laws', LAWS)
def test_exact_mgf_for_both_signs_and_all_subset_sizes(laws):
    for n in range(1, len(laws)+1):
        outcomes = list(draws(laws, n))
        assert sum(p for _, _, p in outcomes) == 1
        for j, sign, q in product(range(2), (-1, 1), (F(1,4), F(1,2), F(2), F(4))):
            # exp(t)=q**2 makes half-valued outcomes exact rational powers.
            x = lambda v: max(F(sign)*v[j], F(0))
            mu = sum(sum(p*x(v) for v,p in law) for law in laws)/len(laws)
            mgf = sum(p*q**int(2*sum(x(v) for v in values)) for _,values,p in outcomes)
            mean_mgf = sum(sum(p*q**int(2*x(v)) for v,p in law) for law in laws)/len(laws)
            assert mgf <= mean_mgf**n <= (1-mu+mu*q**2)**n


@pytest.mark.parametrize('laws', LAWS)
def test_exact_simultaneous_coverage_for_specified_finite_laws(laws):
    alpha = F(1,20)
    theta = [sum(sum(p*v[j] for v,p in law) for law in laws)/len(laws) for j in range(2)]
    names = ('d_minus_b1','d_minus_b2')
    for n in range(1,len(laws)+1):
        failure = F(0)
        for subset, values, probability in draws(laws,n):
            rows = [dict(family_id=str(g), bounds={name:(F(v[j]),F(v[j])) for j,name in enumerate(names)})
                    for g,v in zip(subset,values)]
            intervals = paired_contrasts(rows, alpha)['exact']
            if any(not intervals[name]['interval'][0] <= theta[j] <= intervals[name]['interval'][1]
                   for j,name in enumerate(names)):
                failure += probability
            missing = [dict(family_id=str(g), bounds={name:(F(-1),F(1)) for name in names}) for g in subset]
            outer = paired_contrasts(missing,alpha)['exact']
            assert all(outer[name]['interval'] == [F(-1),F(1)] for name in names)
        assert failure <= alpha
