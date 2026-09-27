"""Independent scalar inversion and realizability checks for planning arithmetic."""
from fractions import Fraction
import math
from scipy.optimize import brentq
from scripts.plan_policy_precision_20260927 import build


def reference(x, n):
    c = math.log(160)/n
    if x == 0:
        return 0.0, -math.expm1(-c)
    def f(q):
        return x*math.log(x/q)+(1-x)*math.log((1-x)/(1-q))-c
    return brentq(f, 1e-15, x, xtol=1e-14), brentq(f, x, 1-1e-15, xtol=1e-14)


def test_all_scenarios_against_independent_inversion():
    rows = build()['scenarios']
    assert len(rows) == 50
    for row in rows:
        n = row['n_families']
        p, m, z = (row[k] for k in ('positive_count','negative_count','zero_count'))
        assert p+m+z == n and min(p,m,z) >= 0
        d = row['observed_difference']
        assert Fraction(p-m,n) == Fraction(d['num'],d['den'])
        lp, up = reference(p/n,n)
        lm, um = reference(m/n,n)
        lo, hi = row['display_interval']
        assert abs(lo-(lp-um)) < 1e-11
        assert abs(hi-(up-lm)) < 1e-11
        decision = 'useful_benefit' if lo > .05 else 'useful_gain_futility' if hi < .05 else 'inconclusive'
        assert row['decision'] == decision
