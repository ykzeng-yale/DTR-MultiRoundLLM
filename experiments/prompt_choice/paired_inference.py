"""Sign-split bounded-mean KL inference with shared-score bounds: MRL-29 source-only implementation of LEAD-INFERENCE-01.

Pure functions only. There is no data discovery, network, dispatch or code-execution path. Inputs are exact integers or
Fractions; Boolean, float, NaN and other types are refused, never rounded.

Numerical policy. Every endpoint is OUTWARD CONSERVATIVE. Rationals convert to Decimal at PRECISION significant digits
with directed rounding (floor for lower, ceiling for upper). Interval arithmetic rounds outward. Decimal ln and exp are
correctly rounded (ROUND_HALF_EVEN), and each result is enclosed by its adjacent representable values (next_minus,
next_plus). The KL inversion uses at most MAX_BISECTIONS exact-Fraction bisections. When the enclosures cannot decide a
comparison, bisection stops and the current bracket is kept. The function returns the LOWER exterior endpoint for l and
the UPPER exterior endpoint for u. No added epsilon is used as a certificate.

Scope. This is a mathematical component under stated assumptions (family independence, boundedness, a fixed n, the
frozen protocol, and valid pathwise bounds). It is not evidence of policy usefulness, sampled coverage or independence.
"""
from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Context, Decimal
from fractions import Fraction
from functools import lru_cache

VERSION = "paired-inference-source-v1"
PRECISION = 100
MAX_BISECTIONS = 64
CONTRASTS = ("d_minus_b1", "d_minus_b2")
TAILS = 8  # two tails x two signs x two contrasts: delta = alpha / 8

_FLOOR = Context(prec=PRECISION, rounding=ROUND_FLOOR)
_CEIL = Context(prec=PRECISION, rounding=ROUND_CEILING)
_NEAR = Context(prec=PRECISION, rounding=ROUND_HALF_EVEN)


class InferenceInputError(ValueError):
    """Explicit refusal of a malformed or out-of-domain input."""


# ---------------------------------------------------------------- exact inputs
def exact(v, what="value") -> Fraction:
    if type(v) is int:
        return Fraction(v)
    if type(v) is Fraction:
        return v
    raise InferenceInputError(f"{what}: only exact int or Fraction is accepted (Boolean, float, NaN and others refused)")


def _text(v, what):
    if type(v) is not str or not v:
        raise InferenceInputError(f"{what} must be a nonempty string")
    try:
        v.encode("utf-8")
    except UnicodeEncodeError:
        raise InferenceInputError(f"{what} is not valid UTF-8 text") from None
    return v


def serialize(x: Fraction) -> dict:
    return {"num": x.numerator, "den": x.denominator}


# ---------------------------------------------------------------- (a) shared-primitive linear score bounds
def score_bounds(terms, primitives):
    """Sharp rectangular bounds of D = sum_k c_k Y_k over the box Y_k in [a_k, b_k], after consolidating every
    occurrence of the same primitive ID into one coefficient. `terms` is a list of (primitive_id, coefficient) and
    `primitives` a list of (primitive_id, a, b). This checks internal bookkeeping only: an ID string does not certify
    execution identity, a branch-reuse law, the saved artifact, the endpoint or the score version."""
    if type(primitives) is not list or type(terms) is not list:
        raise InferenceInputError("terms and primitives must be lists")
    box = {}
    for p in primitives:
        if type(p) is not tuple or len(p) != 3:
            raise InferenceInputError("primitive must be (id, a, b)")
        pid = _text(p[0], "primitive id")
        if pid in box:
            raise InferenceInputError(f"duplicate primitive id {pid!r}")
        a, b = exact(p[1], f"{pid}.a"), exact(p[2], f"{pid}.b")
        if not (0 <= a <= b <= 1):
            raise InferenceInputError(f"{pid}: score interval must satisfy 0 <= a <= b <= 1")
        box[pid] = (a, b)
    coef = {}
    for t in terms:
        if type(t) is not tuple or len(t) != 2:
            raise InferenceInputError("term must be (primitive_id, coefficient)")
        pid = _text(t[0], "term primitive id")
        if pid not in box:
            raise InferenceInputError(f"term references undeclared primitive {pid!r}")
        coef[pid] = coef.get(pid, Fraction(0)) + exact(t[1], f"{pid} coefficient")
    if set(coef) != set(box):
        raise InferenceInputError("every declared primitive must be referenced (exact reference completeness)")
    lo = sum((c * box[k][0] if c >= 0 else c * box[k][1] for k, c in coef.items()), Fraction(0))
    hi = sum((c * box[k][1] if c >= 0 else c * box[k][0] for k, c in coef.items()), Fraction(0))
    return lo, hi


def policy_contrast_bounds(plus, minus, primitives):
    """Bounds of (policy-weighted score of `plus`) minus (policy-weighted score of `minus`). Each side is a list of
    (primitive_id, weight) with nonnegative exact weights summing to exactly one. Shared primitives cancel exactly."""
    for side, name in ((plus, "plus"), (minus, "minus")):
        if type(side) is not list or not side:
            raise InferenceInputError(f"{name} side must be a nonempty list of (primitive_id, weight)")
        ws = []
        for t in side:
            if type(t) is not tuple or len(t) != 2:
                raise InferenceInputError(f"{name} side entries must be (primitive_id, weight)")
            w = exact(t[1], f"{name} weight")
            if w < 0:
                raise InferenceInputError(f"{name} weights must be nonnegative")
            ws.append(w)
        if sum(ws, Fraction(0)) != 1:
            raise InferenceInputError(f"{name} weights must sum to exactly one")
    terms = [(pid, exact(w)) for pid, w in plus] + [(pid, -exact(w)) for pid, w in minus]
    return score_bounds(terms, primitives)


# ---------------------------------------------------------------- outward Decimal interval arithmetic
def _dec_lo(x: Fraction) -> Decimal:
    return _FLOOR.divide(Decimal(x.numerator), Decimal(x.denominator))


def _dec_hi(x: Fraction) -> Decimal:
    return _CEIL.divide(Decimal(x.numerator), Decimal(x.denominator))


def _ln_bounds(lo: Decimal, hi: Decimal):
    """Enclosure of ln over [lo, hi] (lo > 0): monotone, correctly rounded, then widened by one representable step."""
    return _NEAR.next_minus(_NEAR.ln(lo)), _NEAR.next_plus(_NEAR.ln(hi))


def _exp_bounds(lo: Decimal, hi: Decimal):
    return _NEAR.next_minus(_NEAR.exp(lo)), _NEAR.next_plus(_NEAR.exp(hi))


def _mul(a, b):
    """Outward product of intervals a=(a0,a1), b=(b0,b1)."""
    lows = [_FLOOR.multiply(x, y) for x in a for y in b]
    highs = [_CEIL.multiply(x, y) for x in a for y in b]
    return min(lows), max(highs)


def _add(a, b):
    return _FLOOR.add(a[0], b[0]), _CEIL.add(a[1], b[1])


@lru_cache(maxsize=None)
def _threshold(alpha: Fraction):
    """Enclosure of c = log(1/delta) = log(TAILS/alpha)."""
    r = Fraction(TAILS) / alpha
    return _ln_bounds(_dec_lo(r), _dec_hi(r))


def _kl_enclosure(x: Fraction, q: Fraction):
    """Outward enclosure of kl(x||q) for x in (0,1) and q in (0,1)."""
    total = (Decimal(0), Decimal(0))
    for coef, ratio in ((x, x / q), (1 - x, (1 - x) / (1 - q))):
        term = _mul((_dec_lo(coef), _dec_hi(coef)), _ln_bounds(_dec_lo(ratio), _dec_hi(ratio)))
        total = _add(total, term)
    return total


# ---------------------------------------------------------------- (b) one bounded-mean KL interval
@lru_cache(maxsize=None)
def _kl_interval_cached(x: Fraction, n: int, alpha: Fraction):
    c_lo, c_hi = _threshold(alpha)
    report = {"precision_digits": PRECISION, "max_bisections": MAX_BISECTIONS}
    if x == 0 or x == 1:  # formula shortcut with outward bounds: exp(-c/n)
        cn_hi = _CEIL.divide(c_hi, Decimal(n))
        neg = cn_hi.copy_negate()  # exact negation (unary minus would round in the global 28-digit context)
        e_lo = _exp_bounds(neg, neg)[0]  # lower bound of exp(-c/n)
        if x == 0:
            u = min(Fraction(_CEIL.subtract(Decimal(1), e_lo)), Fraction(1))
            return Fraction(0), u, {**report, "method": "boundary formula u=1-exp(-c/n)", "bisections": [0, 0]}
        return max(Fraction(e_lo), Fraction(0)), Fraction(1), {**report, "method": "boundary formula l=exp(-c/n)",
                                                                 "bisections": [0, 0]}

    def inside(q):  # True: certainly n*kl <= c; False: certainly > c; None: undetermined
        k_lo, k_hi = _kl_enclosure(x, q)
        nk_lo, nk_hi = _FLOOR.multiply(k_lo, Decimal(n)), _CEIL.multiply(k_hi, Decimal(n))
        if nk_hi <= c_lo:
            return True
        if nk_lo > c_hi:
            return False
        return None

    def invert(inner, outer):  # inner is inside, outer is outside (kl infinite at the boundary)
        steps = 0
        while steps < MAX_BISECTIONS:
            mid = (inner + outer) / 2
            verdict = inside(mid)
            if verdict is None:
                break
            steps += 1
            inner, outer = (mid, outer) if verdict else (inner, mid)
        return outer, steps  # the exterior end of the retained bracket

    l, sl = invert(x, Fraction(0))
    u, su = invert(x, Fraction(1))
    return l, u, {**report, "method": "outward bisection", "bisections": [sl, su]}


def kl_interval(xbar, n, alpha):
    """Outward-conservative endpoints (l_n(x), u_n(x)) of {q: n kl(x||q) <= log(TAILS/alpha)}."""
    x, a = exact(xbar, "xbar"), exact(alpha, "alpha")
    if type(n) is not int or n < 1:
        raise InferenceInputError("n must be a positive integer (Boolean refused)")
    if not 0 <= x <= 1:
        raise InferenceInputError("xbar must lie in [0, 1]")
    if not 0 < a < 1:
        raise InferenceInputError("alpha must lie in (0, 1)")
    return _kl_interval_cached(x, n, a)


# ---------------------------------------------------------------- (c) two named sign-split family contrasts
def paired_contrasts(families, alpha) -> dict:
    """Simultaneous outer intervals for d_minus_b1 and d_minus_b2 from per-family pathwise bounds [L, U].
    `families` is a list of {"family_id": str, "bounds": {"d_minus_b1": (L, U), "d_minus_b2": (L, U)}}."""
    a = exact(alpha, "alpha")
    if not 0 < a < 1:
        raise InferenceInputError("alpha must lie in (0, 1)")
    if type(families) is not list:
        raise InferenceInputError("families must be a list")
    seen, rows = set(), []
    for f in families:
        if type(f) is not dict or set(f) != {"family_id", "bounds"}:
            raise InferenceInputError("each family must be exactly {family_id, bounds}")
        fid = _text(f["family_id"], "family_id")
        if fid in seen:
            raise InferenceInputError(f"duplicate family_id {fid!r}")
        seen.add(fid)
        b = f["bounds"]
        if type(b) is not dict or set(b) != set(CONTRASTS):
            raise InferenceInputError(f"{fid}: bounds must have exactly {CONTRASTS}")
        row = {}
        for j in CONTRASTS:
            if type(b[j]) not in (tuple, list) or len(b[j]) != 2:
                raise InferenceInputError(f"{fid}/{j}: bounds must be a (L, U) pair")
            L, U = exact(b[j][0], f"{fid}/{j}/L"), exact(b[j][1], f"{fid}/{j}/U")
            if not -1 <= L <= U <= 1:
                raise InferenceInputError(f"{fid}/{j}: need -1 <= L <= U <= 1")
            row[j] = (L, U)
        rows.append(row)
    n = len(rows)
    base = {"version": VERSION, "alpha": serialize(a), "delta": serialize(a / TAILS), "tails": TAILS, "n_families": n,
            "precision_digits": PRECISION, "max_bisections": MAX_BISECTIONS}
    if n == 0:  # no KL expression is evaluated at n = 0
        return {**base, "no_data": True,
                "intervals": {j: [serialize(Fraction(-1)), serialize(Fraction(1))] for j in CONTRASTS},
                "note": "no families: the uninformative interval [-1, 1], not an inference"}
    out = {}
    for j in CONTRASTS:
        mean = lambda f: sum((f(r[j]) for r in rows), Fraction(0)) / n
        pos_lo, neg_hi = mean(lambda b: max(b[0], 0)), mean(lambda b: max(-b[0], 0))
        pos_hi, neg_lo = mean(lambda b: max(b[1], 0)), mean(lambda b: max(-b[1], 0))
        l_pl, _, r1 = kl_interval(pos_lo, n, a)
        _, u_nh, r2 = kl_interval(neg_hi, n, a)
        _, u_ph, r3 = kl_interval(pos_hi, n, a)
        l_nl, _, r4 = kl_interval(neg_lo, n, a)
        lower, upper = max(l_pl - u_nh, Fraction(-1)), min(u_ph - l_nl, Fraction(1))
        out[j] = {"interval": [lower, upper],
                  "means": {"pos_of_L": pos_lo, "neg_of_L": neg_hi, "pos_of_U": pos_hi, "neg_of_U": neg_lo},
                  "bisections": {"l(pos_of_L)": r1["bisections"], "u(neg_of_L)": r2["bisections"],
                                 "u(pos_of_U)": r3["bisections"], "l(neg_of_U)": r4["bisections"]}}
    return {**base, "no_data": False,
            "intervals": {j: [serialize(out[j]["interval"][0]), serialize(out[j]["interval"][1])] for j in CONTRASTS},
            "exact": out}
