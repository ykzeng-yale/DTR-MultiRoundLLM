"""MRL-29 deterministic checks for sign-split KL inference (LEAD-INFERENCE-01). Exact synthetic unit checks only:
no Monte Carlo, no receiver grades, no historical reanalysis. The coverage enumerations are finite exact laws. They do
not prove universal coverage and are not empirical validation."""
import ast
import hashlib
import subprocess
from decimal import Context, Decimal, localcontext
from fractions import Fraction as Fr
from itertools import product
from pathlib import Path

import pytest

from experiments.prompt_choice import paired_inference as pi

ROOT = Path(__file__).resolve().parents[1]
ALPHA = Fr(1, 20)
F = lambda d: Fr(d["num"], d["den"])

# ---- independent reference inversion (a separate code path: 150 digits, plain bisection, point values)
_R = Context(prec=150)


def _ref_kl(x, q):
    x, q = Decimal(x.numerator) / Decimal(x.denominator), Decimal(q)
    one = Decimal(1)
    return x * _R.ln(x / q) + (one - x) * _R.ln((one - x) / (one - q))


def _ref_interval(x, n, alpha):
    with localcontext(_R):  # every reference operation at 150 digits, not the global 28-digit context
        return _ref_interval_150(x, n, alpha)


def _ref_interval_150(x, n, alpha):
    c = _R.ln(Decimal(8 * alpha.denominator) / Decimal(alpha.numerator))
    if x == 0:
        return Decimal(0), 1 - _R.exp(-c / n)
    if x == 1:
        return _R.exp(-c / n), Decimal(1)
    xd = Decimal(x.numerator) / Decimal(x.denominator)
    out = []
    for inner, outer in ((xd, Decimal(0)), (xd, Decimal(1))):
        for _ in range(220):
            mid = (inner + outer) / 2
            if n * _ref_kl(x, mid) <= c:
                inner = mid
            else:
                outer = mid
        out.append(inner)
    return out[0], out[1]


GRID_X = [Fr(0), Fr(1, 7), Fr(3, 10), Fr(1, 2), Fr(9, 10), Fr(1)]


@pytest.mark.parametrize("n", [1, 5, 98, 99])
@pytest.mark.parametrize("alpha", [Fr(1, 20), Fr(1, 100)])
def test_endpoints_are_outward_and_close_to_an_independent_high_precision_inversion(n, alpha):
    for x in GRID_X:
        l, u, rep = pi.kl_interval(x, n, alpha)
        rl, ru = _ref_interval(x, n, alpha)
        assert Decimal(l.numerator) / Decimal(l.denominator) <= rl + Decimal("1e-120")  # l never above the true endpoint
        assert Decimal(u.numerator) / Decimal(u.denominator) >= ru - Decimal("1e-120")  # u never below it
        assert rl - Decimal(l.numerator) / Decimal(l.denominator) < Decimal("1e-15")
        assert Decimal(u.numerator) / Decimal(u.denominator) - ru < Decimal("1e-15")
        assert 0 <= l <= x <= u <= 1 and rep["precision_digits"] >= 80 and rep["max_bisections"] == 64


def test_boundary_means_and_the_98_99_zero_difference_radius():
    for n in (98, 99):
        assert pi.kl_interval(0, n, ALPHA)[0] == 0 and pi.kl_interval(1, n, ALPHA)[1] == 1
    u98, u99 = pi.kl_interval(0, 98, ALPHA)[1], pi.kl_interval(0, 99, ALPHA)[1]
    assert u98 > Fr(1, 20) > u99  # the outward u at n=99 still crosses the .05 zero-difference radius
    assert abs(float(u98) - 0.0504693679) < 1e-10 and abs(float(u99) - 0.0499725328) < 1e-10
    zero = [{"family_id": f"f{i}", "bounds": {"d_minus_b1": (0, 0), "d_minus_b2": (0, 0)}} for i in range(99)]
    iv = pi.paired_contrasts(zero, ALPHA)["intervals"]["d_minus_b1"]
    assert F(iv[0]) == -u99 and F(iv[1]) == u99


def test_reflection_and_monotonicity():
    xs = [Fr(k, 40) for k in range(41)]
    for n in (3, 25):
        ends = [pi.kl_interval(x, n, ALPHA) for x in xs]
        for (l1, u1, _), (l2, u2, _) in zip(ends, ends[1:]):
            assert l1 <= l2 and u1 <= u2
        for x, (l, u, _) in zip(xs, ends):
            _, u_ref, _ = pi.kl_interval(1 - x, n, ALPHA)
            assert abs(l - (1 - u_ref)) < Fr(1, 10 ** 15)  # l_n(x) = 1 - u_n(1 - x), up to the outward brackets


# ---- shared-score bounds
def test_shared_missing_grade_cancels_exactly_but_distinct_grades_do_not():
    prims = [("y_shared", 0, 1)]
    assert pi.score_bounds([("y_shared", Fr(1, 3)), ("y_shared", -Fr(1, 3))], prims) == (0, 0)
    two = [("y_draw1", 0, 1), ("y_draw2", 0, 1)]
    assert pi.score_bounds([("y_draw1", Fr(1, 3)), ("y_draw2", -Fr(1, 3))], two) == (-Fr(1, 3), Fr(1, 3))
    assert pi.policy_contrast_bounds([("y_shared", 1)], [("y_shared", 1)], prims) == (0, 0)


def test_fractional_and_zero_policy_weights_and_observed_scores():
    prims = [("p1", 1, 1), ("p2", 0, 1), ("p3", 0, 0), ("r1", Fr(1, 2), Fr(1, 2))]
    lo, hi = pi.policy_contrast_bounds([("p1", Fr(2, 3)), ("p2", Fr(1, 3)), ("p3", 0)], [("r1", 1)], prims)
    assert (lo, hi) == (Fr(2, 3) - Fr(1, 2), Fr(2, 3) + Fr(1, 3) - Fr(1, 2))


@pytest.mark.parametrize("call", [
    lambda: pi.score_bounds([("ghost", 1)], [("y", 0, 1)]),                                  # undeclared reference
    lambda: pi.score_bounds([("y", 1)], [("y", 0, 1), ("orphan", 0, 1)]),                    # unreferenced primitive
    lambda: pi.score_bounds([("y", 1)], [("y", 0, 1), ("y", 0, 1)]),                         # duplicate id
    lambda: pi.score_bounds([("y", 1)], [("y", 0, 2)]),                                      # outside [0,1]
    lambda: pi.score_bounds([("y", 1)], [("y", 1, 0)]),                                      # a > b
    lambda: pi.score_bounds([("y", 0.5)], [("y", 0, 1)]),                                    # float
    lambda: pi.score_bounds([("y", True)], [("y", 0, 1)]),                                   # Boolean
    lambda: pi.score_bounds([("y", 1)], [("y", float("nan"), 1)]),                           # NaN
    lambda: pi.score_bounds([("\ud800", 1)], [("\ud800", 0, 1)]),                            # invalid UTF-8
    lambda: pi.policy_contrast_bounds([("y", Fr(1, 2))], [("y", 1)], [("y", 0, 1)]),         # weights sum != 1
    lambda: pi.policy_contrast_bounds([("y", 2), ("z", -1)], [("y", 1)], [("y", 0, 1), ("z", 0, 1)]),  # negative
])
def test_malformed_score_bookkeeping_is_refused(call):
    with pytest.raises(pi.InferenceInputError):
        call()


# ---- family contrasts
def fam(fid, b1, b2):
    return {"family_id": fid, "bounds": {"d_minus_b1": b1, "d_minus_b2": b2}}


def test_missingness_widens_and_all_missing_gives_minus_one_to_one():
    tight = [fam("a", (Fr(1, 2), Fr(1, 2)), (0, 0)), fam("b", (-Fr(1, 4), -Fr(1, 4)), (1, 1)), fam("c", (0, 0), (0, 0))]
    wide = [fam("a", (0, 1), (0, 0)), fam("b", (-1, 0), (1, 1)), fam("c", (0, 0), (-1, 1))]
    it, iw = pi.paired_contrasts(tight, ALPHA)["exact"], pi.paired_contrasts(wide, ALPHA)["exact"]
    for j in pi.CONTRASTS:
        assert iw[j]["interval"][0] <= it[j]["interval"][0] and it[j]["interval"][1] <= iw[j]["interval"][1]
    allmiss = [fam(f"f{i}", (-1, 1), (-1, 1)) for i in range(5)]
    res = pi.paired_contrasts(allmiss, ALPHA)
    assert all([F(x) for x in res["intervals"][j]] == [-1, 1] for j in pi.CONTRASTS)


def test_empty_input_is_a_labelled_no_data_result_without_evaluating_kl(monkeypatch):
    monkeypatch.setattr(pi, "kl_interval", lambda *a, **k: (_ for _ in ()).throw(AssertionError("KL evaluated at n=0")))
    res = pi.paired_contrasts([], ALPHA)
    assert res["no_data"] is True and res["n_families"] == 0
    assert all([F(x) for x in res["intervals"][j]] == [-1, 1] for j in pi.CONTRASTS)


@pytest.mark.parametrize("families", [
    [fam("a", (0, 0), (0, 0)), fam("a", (0, 0), (0, 0))],             # duplicate family
    [{"family_id": "a", "bounds": {"d_minus_b1": (0, 0)}}],             # missing contrast
    [{"family_id": "a", "bounds": {"d_minus_b1": (0, 0), "d_minus_b2": (0, 0), "d_minus_b3": (0, 0)}}],
    [{"family_id": "a", "bounds": {"d_minus_b1": (0, 0), "d_minus_b2": (0, 0)}, "extra": 1}],
    [fam("a", (Fr(1, 2), 0), (0, 0))],                                  # L > U
    [fam("a", (-2, 0), (0, 0))],                                        # outside [-1, 1]
    [fam("a", (0.0, 0), (0, 0))],                                       # float
    [fam("a", (False, 0), (0, 0))],                                     # Boolean
    [fam("", (0, 0), (0, 0))],                                          # empty id
])
def test_malformed_family_inputs_are_refused(families):
    with pytest.raises(pi.InferenceInputError):
        pi.paired_contrasts(families, ALPHA)


@pytest.mark.parametrize("bad", [0, 1, Fr(3, 2), 0.05, True])
def test_alpha_domain(bad):
    with pytest.raises(pi.InferenceInputError):
        pi.paired_contrasts([fam("a", (0, 0), (0, 0))], bad)


# ---- exact finite-law coverage checks (synthetic, independent, nonidentical, non-Bernoulli)
LAWS = [  # per family: list of ((D1, D2), probability); within-family dependence between the two contrasts is allowed
    [((Fr(1, 2), Fr(-1, 4)), Fr(1, 3)), ((0, 1), Fr(1, 3)), ((-1, Fr(1, 2)), Fr(1, 3))],
    [((1, 0), Fr(1, 2)), ((Fr(-1, 3), Fr(-1, 3)), Fr(1, 2))],
    [((Fr(1, 4), Fr(3, 4)), Fr(3, 4)), ((-1, -1), Fr(1, 4))],
    [((0, Fr(1, 2)), Fr(1, 5)), ((Fr(2, 3), 0), Fr(4, 5))],
]


@pytest.mark.parametrize("alpha", [Fr(1, 2), Fr(9, 10)])
def test_exact_two_contrast_coverage_on_finite_independent_nonidentical_laws(alpha):
    n = len(LAWS)
    theta = [sum(sum(p * d[j] for d, p in law) for law in LAWS) / n for j in (0, 1)]
    covered = Fr(0)
    for combo in product(*LAWS):
        prob = Fr(1)
        for _, p in combo:
            prob *= p
        fams = [fam(f"g{i}", (d[0], d[0]), (d[1], d[1])) for i, (d, _) in enumerate(combo)]
        iv = pi.paired_contrasts(fams, alpha)["exact"]
        if all(iv[c]["interval"][0] <= theta[k] <= iv[c]["interval"][1] for k, c in enumerate(pi.CONTRASTS)):
            covered += prob
    assert sum((Fr(1) for _ in product(*LAWS)), Fr(0)) == 3 * 2 * 2 * 2
    assert covered >= 1 - alpha  # exact synthetic unit check, not universal coverage or empirical validation


# ---- configuration and purity
def test_config_pins_the_contract_and_states_the_allocation():
    import json
    cfg = json.loads((ROOT / "experiments/prompt_choice/paired_inference_source_v1.json").read_text())
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "2ed2abb:docs/paired_kl_inference_contract_20260926.md"],
                          capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == cfg["contract"]["sha256"]
    assert cfg["source_only"] is True and cfg["collection_released"] is False and "alpha/8" in cfg["error_allocation"]
    assert cfg["numerical_policy"]["precision_digits"] == pi.PRECISION >= 80 and cfg["numerical_policy"]["max_bisections"] == 64


def test_module_has_no_discovery_network_or_execution_path():
    tree = ast.parse((ROOT / "experiments/prompt_choice/paired_inference.py").read_text())
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imported <= {"__future__", "decimal", "fractions", "functools"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"open", "glob", "listdir", "exec", "eval", "system", "Popen", "urlopen", "socket", "random", "float"}
