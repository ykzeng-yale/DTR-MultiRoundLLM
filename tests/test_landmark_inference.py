"""Meaningful failure cases for bounded small-family inference; no model calls."""
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.landmark.analyze import bounded_family_interval, paired_summary


def test_identical_observations_do_not_imply_population_certainty():
    # D=+1 with probability .9, -1 otherwise. True mean .8; all +1 has >5% mass.
    values = [1.] * 24
    families = list(range(24))
    assert .9**24 > .05
    assert paired_summary(values, families)["ci95"] == [1., 1.]
    interval = bounded_family_interval(values, values, families, (-1, 1))["interval"]
    assert interval[0] < .8 < interval[1]


def test_exact_small_binomial_coverage_with_outcome_selected_missingness():
    # Missingness is fully outcome-dependent. Lower/upper remain pathwise valid.
    n = 8
    for p in (.01, .1, .5, .9, .99):
        coverage = 0.
        for k in range(n+1):
            values = [1.] * k + [-1.] * (n-k)
            lower = values[:]
            upper = [1.] * n  # Every negative is withheld; every positive seen.
            ci = bounded_family_interval(lower, upper, list(range(n)), (-1, 1))["interval"]
            mass = math.comb(n, k) * p**k * (1-p)**(n-k)
            coverage += mass * (ci[0] <= 2*p-1 <= ci[1])
        assert coverage >= .95-1e-12


def test_repeating_roots_within_one_family_does_not_create_information():
    a = bounded_family_interval([.2, .6], [.2, .6], ["a", "b"], (0, 1))
    b = bounded_family_interval([.2]*10+[.6]*10, [.2]*10+[.6]*10, ["a"]*10+["b"]*10, (0, 1))
    assert a["radius"] == b["radius"]
    assert a["effective_families"] == b["effective_families"] == 2
    c = bounded_family_interval([.2]*9+[.6], [.2]*9+[.6], ["a"]*9+["b"], (0, 1))
    assert c["effective_families"] < 2 and c["radius"] > a["radius"]


def test_no_observations_or_failed_identity_cannot_yield_interval():
    assert bounded_family_interval([], [], [], (-1, 1))["interval"] is None
    assert bounded_family_interval([0], [1], ["a"], (0, 1), allow=False)["interval"] is None
    assert bounded_family_interval([-1]*24, [1]*24, list(range(24)), (-1, 1))["interval"] == [-1, 1]


@pytest.mark.parametrize("lower,upper,families,alpha", [([0], [1], [], .05), ([1], [0], ["a"], .05), ([float("nan")], [1], ["a"], .05), ([0], [1], ["a"], 0)])
def test_invalid_completion_bounds_are_rejected(lower, upper, families, alpha):
    with pytest.raises(ValueError):
        bounded_family_interval(lower, upper, families, (0, 1), alpha)
