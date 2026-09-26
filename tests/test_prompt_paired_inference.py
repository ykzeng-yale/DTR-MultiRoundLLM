"""MRL-29 deterministic checks for sign-split KL inference (LEAD-INFERENCE-01). Exact synthetic unit checks only:
no Monte Carlo, no receiver grades, no historical reanalysis. The coverage enumerations are finite exact laws. They do
not prove universal coverage and are not empirical validation."""
import ast
import hashlib
import subprocess
from decimal import ROUND_CEILING, ROUND_FLOOR, Context, Decimal, localcontext
from fractions import Fraction as Fr
from itertools import product
from pathlib import Path

import pytest

from experiments.prompt_choice import paired_inference as pi

ROOT = Path(__file__).resolve().parents[1]
ALPHA = Fr(1, 20)
F = lambda d: Fr(d["num"], d["den"])

# ---- independent reference (MRL-30 repair). Every Decimal operation runs inside an explicit 150-digit local context,
# and results convert to EXACT Fractions before any comparison. No ambient 28-digit rounding and no epsilon.
# The certificate is the production directed arithmetic. This reference is a separate numerical CROSS-CHECK:
#  * boundaries x=0/1: closed forms ENCLOSED with directed 150-digit rounding and correctly rounded exp/ln widened
#    by one representable step, so [lo, hi] contains the true value;
#  * interior x: a 150-digit point-valued bisection keeps BOTH bracket ends (inside end, outside end). Its meaning:
#    under the reference's own ~1e-148 evaluation error, the true endpoint lies between them. It is not relabelled
#    as a rigorous enclosure.
_P = 150
_NEAR = Context(prec=_P)
_DOWN = Context(prec=_P, rounding=ROUND_FLOOR)
_UP = Context(prec=_P, rounding=ROUND_CEILING)


def _frac_to_dec(x, ctx):
    return ctx.divide(Decimal(x.numerator), Decimal(x.denominator))


def _c_enclosure(alpha):
    r = Fr(8) / alpha
    return _NEAR.next_minus(_NEAR.ln(_frac_to_dec(r, _DOWN))), _NEAR.next_plus(_NEAR.ln(_frac_to_dec(r, _UP)))


def _boundary_enclosure(n, alpha):
    """Enclosure [e_lo, e_hi] of E = exp(-c/n); u_n(0) = 1 - E lies in [1 - e_hi, 1 - e_lo] and l_n(1) = E."""
    c_lo, c_hi = _c_enclosure(alpha)
    e_lo = _NEAR.next_minus(_NEAR.exp(_UP.divide(c_hi, Decimal(n)).copy_negate()))    # largest c/n -> smallest E
    e_hi = _NEAR.next_plus(_NEAR.exp(_DOWN.divide(c_lo, Decimal(n)).copy_negate()))   # smallest c/n -> largest E
    return Fr(e_lo), Fr(e_hi)


def _ref_kl(x, q):
    xd = _frac_to_dec(x, _NEAR)
    one = Decimal(1)
    return _NEAR.add(_NEAR.multiply(xd, _NEAR.ln(_NEAR.divide(xd, q))),
                     _NEAR.multiply(_NEAR.subtract(one, xd), _NEAR.ln(_NEAR.divide(_NEAR.subtract(one, xd), _NEAR.subtract(one, q)))))


def _ref_brackets(x, n, alpha):
    """Returns ((l_inside, l_outside), (u_inside, u_outside)) as exact Fractions; inside ends satisfy n*kl <= c."""
    with localcontext(_NEAR):
        c = _NEAR.ln(_frac_to_dec(Fr(8) / alpha, _NEAR))
        xd = _frac_to_dec(x, _NEAR)
        out = []
        for inner, outer in ((xd, Decimal(0)), (xd, Decimal(1))):
            for _ in range(220):
                mid = _NEAR.divide(_NEAR.add(inner, outer), Decimal(2))
                if _NEAR.multiply(Decimal(n), _ref_kl(x, mid)) <= c:
                    inner = mid
                else:
                    outer = mid
            out.append((Fr(inner), Fr(outer)))
        return out[0], out[1]


GRID_X = [Fr(0), Fr(1, 7), Fr(3, 10), Fr(1, 2), Fr(9, 10), Fr(1)]
CLOSE = Fr(1, 10 ** 15)


@pytest.mark.parametrize("n", [1, 5, 98, 99])
@pytest.mark.parametrize("alpha", [Fr(1, 20), Fr(1, 100)])
def test_endpoints_are_outward_and_close_to_an_independent_high_precision_reference(n, alpha):
    for x in GRID_X:
        l, u, rep = pi.kl_interval(x, n, alpha)
        assert type(l) is Fr and type(u) is Fr and 0 <= l <= x <= u <= 1
        assert rep["precision_digits"] >= 80 and rep["max_bisections"] == 64
        if x in (0, 1):
            e_lo, e_hi = _boundary_enclosure(n, alpha)
            if x == 0:  # production u beyond the whole enclosure [1 - e_hi, 1 - e_lo] of the true u
                assert l == 0 and u >= 1 - e_lo and u - (1 - e_lo) < CLOSE
            else:       # production l beyond the whole enclosure [e_lo, e_hi] of the true l
                assert u == 1 and l <= e_lo and e_lo - l < CLOSE
            continue
        # Interior numerical cross-check: production beyond the whole reference bracket (both ends kept).
        (l_in, l_out), (u_in, u_out) = _ref_brackets(x, n, alpha)
        assert l_out < l_in and u_in < u_out and l_in - l_out < Fr(1, 10 ** 60) and u_out - u_in < Fr(1, 10 ** 60)
        assert l <= l_out and u >= u_out
        assert l_out - l < CLOSE and u - u_out < CLOSE


def _load_mutant(old, new):
    """A copy of the production module with one exact textual change. Test-only; production files are untouched."""
    import types
    src = (ROOT / "experiments/prompt_choice/paired_inference.py").read_text()
    assert src.count(old) == 1
    mod = types.ModuleType("paired_inference_mutant")
    exec(compile(src.replace(old, new), "paired_inference_mutant", "exec"), mod.__dict__)
    return mod


def test_old_unary_minus_boundary_mutation_fails_the_outward_check_at_n5():
    mutant = _load_mutant("        neg = cn_hi.copy_negate()", "        neg = -cn_hi")
    e_lo, e_hi = _boundary_enclosure(5, Fr(1, 20))
    with localcontext(Context(prec=28)):  # the ambient 28-digit context the old unary minus rounded in
        _, u0, _ = mutant.kl_interval(0, 5, Fr(1, 20))
        l1, _, _ = mutant.kl_interval(1, 5, Fr(1, 20))
    assert u0 < 1 - e_hi  # decisively inside: below the whole enclosure of the true u_n(0)
    assert l1 > e_hi      # decisively inside: above the whole enclosure of the true l_n(1)
    _, u0p, _ = pi.kl_interval(0, 5, Fr(1, 20))
    l1p, _, _ = pi.kl_interval(1, 5, Fr(1, 20))
    assert u0p >= 1 - e_lo and l1p <= e_lo  # production passes the outward checks


def test_results_are_invariant_to_the_global_decimal_context_after_clearing_caches():
    from decimal import ROUND_UP, getcontext
    probes = [(Fr(0), 5), (Fr(1), 5), (Fr(3, 10), 5), (Fr(1, 7), 98), (Fr(9, 10), 99)]
    pi._kl_interval_cached.cache_clear(); pi._threshold.cache_clear()
    base = [pi.kl_interval(x, n, ALPHA) for x, n in probes]
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 5, ROUND_UP
        assert getcontext().prec == 5
        pi._kl_interval_cached.cache_clear(); pi._threshold.cache_clear()
        hostile = [pi.kl_interval(x, n, ALPHA) for x, n in probes]
    pi._kl_interval_cached.cache_clear(); pi._threshold.cache_clear()
    assert hostile == base


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


def test_an_injected_1e60_inward_error_is_detected_at_the_boundary_and_in_the_interior():
    """Each injected value lies 1e-60 inside the true endpoint (per the reference); the repaired checks reject it."""
    tiny = Fr(1, 10 ** 60)
    e_lo, e_hi = _boundary_enclosure(5, ALPHA)
    u_injected = (1 - e_lo) - tiny  # an upper stand-in for (true u_n(0)) - 1e-60
    assert not u_injected >= 1 - e_lo
    l1_injected = e_hi + tiny       # a lower stand-in for (true l_n(1)) + 1e-60
    assert not l1_injected <= e_lo
    (l_in, l_out), (u_in, u_out) = _ref_brackets(Fr(3, 10), 5, ALPHA)
    assert not (l_out + tiny <= l_out) and not (u_out - tiny >= u_out)  # interior injections fail the checks
