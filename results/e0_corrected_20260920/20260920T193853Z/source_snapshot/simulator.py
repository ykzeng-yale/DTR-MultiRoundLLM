"""E0 reference simulator: a tabular model of multi-round interaction with EXACT truth.

Purpose. Every estimator this project relies on is validated here first, against a
law whose optimal regime, policy values and turn-level blip effects are computed by
dynamic programming rather than estimated. No model is called; this is CPU-only and
is the work that proceeds while the GPU is held by a sibling run.

Scope, stated because it is easy to overclaim. This is a *reference simulator*, not a
model of LLM behaviour. Its structure and several of its constants are calibrated to
this project's own measured audits (see below), but its intervention effects are
chosen by the analyst. It licenses statements of the form "estimator X recovers /
fails to recover a known truth under condition Y". It licenses no statement about
what any real intervention does to any real model.

State. S_t in {0,1,2,3}: 0 far-wrong, 1 close-wrong, 2 passes the visible assertion
but fails the hidden ones, 3 correct. State 2 exists because the harness's own
visible/hidden split creates it (`experiments/common/scoring.py`): the intervener
sees a passing visible assertion while the graded outcome is still a failure, which
is exactly the configuration that made a self-check stopping rule stop on half of all
failures in audit A3.

Arms. Five, a projection of the frozen taxonomy: STOP (A0), RETRY (A1, the
content-free reference), RESET (A2), LOCAL (A3, localize the error), DIVERT (A6, a
turn aimed away from the task). DIVERT is what separates "another generation pass
happened" from "a pass aimed at the task".

Latents. Ease E in five bins, with bin probabilities taken from the beta-binomial
FITTED TO REAL DATA in audit A2 (alpha 0.348, beta 0.230 for the 3B receiver) --
which is why the ease distribution is U-shaped rather than concentrated. Error type
Z in {0,1} with P(Z=1)=0.35: Z modifies WHICH arm is best (LOCAL when the error is
mechanical, RESET when it is conceptual), so the ordering of arms flips with a latent
the estimator cannot see. That is the structure premise check P3 showed is required
before unmeasured confounding can move a decision at all.

Calibration markers used in the docstrings and the design: (M) measured, (S) set to
match a measured marginal, (D) design choice by the analyst.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import beta as _Beta

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------
EASE_MID = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
#: (M) ease-bin probabilities from audit A2's beta-binomial fit to per-task
#: first-attempt success counts for Qwen2.5-3B (alpha 0.348, beta 0.230).
_edges = _Beta.cdf(np.array([0., .2, .4, .6, .8, 1.]), 0.348, 0.230)
P_E = np.diff(_edges)
P_E = P_E / P_E.sum()

NE = 5                      # ease bins
NS = 4                      # quality states
P_Z = 0.35                  # (D) P(error is conceptual)
ARMS = ('STOP', 'RETRY', 'RESET', 'LOCAL', 'DIVERT')
K = len(ARMS)
UNIF5 = np.full(K, 1.0 / K)

CUT = np.array([-1.0, 0.0, 1.2])   # (D) ordered-logit cutpoints over S'
LAM = 1.4                          # (D) ease loading
OFF = 1.43929                       # (S) chosen so P(S_1 = 3) matches A2's 0.600
MU = np.array([-3.8318, -1.3178, 0.3437, 4.7166])   # (S) per-state baselines

#: (D) severity ordering, used ONLY by the behaviour policy -- it is what makes a
#: severe intervention arrive disproportionately in a bad state.
SEV = {'STOP': 0.0, 'DIVERT': 0.0, 'RETRY': 1.0, 'LOCAL': 2.0, 'RESET': 3.0}
#: (D) how "bad" each state looks to the simulated user.
BAD = np.array([1.0, 0.5, -0.3, -1.0])

# (D) true effects theta(arm, state, Z) on the ordered-logit scale. The two
# load-bearing features: LOCAL beats RESET when Z=0 and loses when Z=1 (effect
# modification by an unobservable), and every arm is HARMFUL in state 3 (iterating
# on a correct answer can destroy it -- audit A3 measured 16.2% degradation).
TH = {}
for _z in (0, 1):
    TH[('RETRY', 0, _z)] = 0.50
    TH[('RETRY', 1, _z)] = 0.60
    TH[('RETRY', 2, _z)] = 0.20
    TH[('RETRY', 3, _z)] = -0.55
    TH[('DIVERT', 0, _z)] = 0.08
    TH[('DIVERT', 1, _z)] = 0.14
    TH[('DIVERT', 2, _z)] = 0.04
    TH[('DIVERT', 3, _z)] = -0.22
    TH[('LOCAL', 2, _z)] = 0.55
    TH[('RESET', 2, _z)] = 0.35
    TH[('LOCAL', 3, _z)] = -1.00
    TH[('RESET', 3, _z)] = -1.80
TH[('LOCAL', 0, 0)] = 0.95
TH[('LOCAL', 1, 0)] = 1.70
TH[('LOCAL', 0, 1)] = 0.40
TH[('LOCAL', 1, 1)] = 0.70
TH[('RESET', 0, 0)] = 1.25
TH[('RESET', 1, 0)] = 1.00
TH[('RESET', 0, 1)] = 1.60
TH[('RESET', 1, 1)] = 1.35


def sig(x):
    return 1.0 / (1.0 + np.exp(-x))


def p_ord(eta):
    """Ordered-logit distribution over the four quality states."""
    c = sig(CUT - eta)
    return np.array([c[0], c[1] - c[0], c[2] - c[1], 1 - c[2]])


def kernel(cmult: float = 1.0) -> np.ndarray:
    """P(S' | E, Z, S, arm), shape (NE, 2, NS, K, NS). STOP rows stay zero: STOP is
    absorbing and is handled separately in the dynamic program."""
    Kk = np.zeros((NE, 2, NS, K, NS))
    for e in range(NE):
        for z in (0, 1):
            for s in range(NS):
                for ai, a in enumerate(ARMS):
                    if ai == 0:
                        continue
                    Kk[e, z, s, ai] = p_ord(MU[s] + cmult * TH[(a, s, z)] + LAM * (EASE_MID[e] - 0.5))
    return Kk


def p_s1(e: int) -> np.ndarray:
    """Initial state law given ease bin e."""
    return p_ord(OFF + LAM * 1.9 * (EASE_MID[e] - 0.5))


# ---------------------------------------------------------------------------
# exact truth by dynamic programming
# ---------------------------------------------------------------------------
def Vtab(Kk: np.ndarray, pol: np.ndarray, T: int) -> np.ndarray:
    """Value table V[t, e, z, s] under a fixed stochastic arm distribution `pol`.

    STOP is absorbing and seals the current artifact, so its value is 1{s == 3}.
    """
    V = np.zeros((T + 2, NE, 2, NS))
    for e in range(NE):
        for z in (0, 1):
            V[T + 1, e, z, :] = (np.arange(NS) == 3)
    for t in range(T, 0, -1):
        for e in range(NE):
            for z in (0, 1):
                for s in range(NS):
                    v = 0.0
                    for ai in range(K):
                        if pol[ai] == 0:
                            continue
                        v += pol[ai] * ((1.0 if s == 3 else 0.0) if ai == 0
                                        else float(Kk[e, z, s, ai] @ V[t + 1, e, z, :]))
                    V[t, e, z, s] = v
    return V


def true_value(Kk: np.ndarray, pol: np.ndarray, T: int) -> float:
    """Exact E[Y] under `pol`, by finite-state dynamic programming."""
    V = Vtab(Kk, pol, T)
    return sum(P_E[e] * (P_Z if z else 1 - P_Z) * float(p_s1(e) @ V[1, e, z, :])
               for e in range(NE) for z in (0, 1))


def true_blips(Kk: np.ndarray, T: int, continuation: np.ndarray = UNIF5) -> dict:
    """Turn-1 blip gamma_1(s, a, STOP) weighting the latents by their PRIOR.

    This is the WRONG object for grading an estimator that conditions on the observed
    state, and is kept only so the two can be compared. An estimator sees S_1 = s, so
    the quantity it targets integrates (E, Z) over their POSTERIOR given s. Use
    :func:`true_blips_posterior`.
    """
    V = Vtab(Kk, continuation, T)
    w = np.array([[P_E[e] * (P_Z if z else 1 - P_Z) for z in (0, 1)] for e in range(NE)])
    w = w / w.sum()
    out = {}
    for s in range(NS):
        q = {}
        for ai, a in enumerate(ARMS):
            q[a] = sum(w[e, z] * ((1.0 if s == 3 else 0.0) if ai == 0
                                  else float(Kk[e, z, s, ai] @ V[2, e, z, :]))
                       for e in range(NE) for z in (0, 1))
        for a in ARMS:
            out[(s, a)] = q[a] - q['STOP']
    return out


def true_blips_posterior(Kk: np.ndarray, T: int, continuation: np.ndarray = UNIF5) -> dict:
    """Turn-1 blip gamma_1(s, a, STOP) weighting the latents by P(E, Z | S_1 = s).

    THE correct truth for grading any estimator that conditions on the observed
    state. Because ease shifts the initial state, observing
    S_1 = s is informative about them, and the prior-weighted blip is a different
    quantity. Ignoring this is a real trap: at s = 1 the prior- and
    posterior-weighted blips differ enough to change which arm looks best.
    """
    V = Vtab(Kk, continuation, T)
    out = {}
    for s in range(NS):
        w = np.array([[P_E[e] * (P_Z if z else 1 - P_Z) * p_s1(e)[s] for z in (0, 1)]
                      for e in range(NE)])
        w = w / w.sum()
        q = {}
        for ai, a in enumerate(ARMS):
            q[a] = sum(w[e, z] * ((1.0 if s == 3 else 0.0) if ai == 0
                                  else float(Kk[e, z, s, ai] @ V[2, e, z, :]))
                       for e in range(NE) for z in (0, 1))
        for a in ARMS:
            out[(s, a)] = q[a] - q['STOP']
    return out


def optimal_rule(Kk: np.ndarray, T: int, observable: str = 'full') -> dict:
    """Exact latent-aware optimum. No state-only optimum is claimed.

    Persistent unobserved latents make the compressed state non-Markov. Optimizing
    state-only rules requires occupancy-aware optimization, not a marginal Bellman
    recursion. Use reference_state_rule for the old, explicitly heuristic baseline.
    """
    if observable != 'full':
        raise ValueError('state-only optimum is not implemented; use reference_state_rule')
    if observable == 'full':
        V = np.zeros((T + 2, NE, 2, NS))
        for e in range(NE):
            for z in (0, 1):
                V[T + 1, e, z, :] = (np.arange(NS) == 3)
        rule = {}
        for t in range(T, 0, -1):
            for e in range(NE):
                for z in (0, 1):
                    for s in range(NS):
                        qs = [(1.0 if s == 3 else 0.0) if ai == 0
                              else float(Kk[e, z, s, ai] @ V[t + 1, e, z, :]) for ai in range(K)]
                        b = int(np.argmax(qs))
                        rule[(t, e, z, s)] = b
                        V[t, e, z, s] = qs[b]
        return rule


def reference_state_rule(Kk: np.ndarray, T: int) -> dict:
    """Heuristic repeating turn-1 uniform-continuation greedy actions, not optimal."""
    rule = {}
    tb = true_blips_posterior(Kk, T)
    for t in range(1, T + 1):
        for s in range(NS):
            best = max(ARMS, key=lambda a: tb[(s, a)])
            rule[(t, s)] = ARMS.index(best)
    return rule


def template_kernel(cmult: float, offsets) -> np.ndarray:
    """Exact class intervention kernel using the same uniform template mixture.

    Template variation changes the target law; it alone does not invalidate a
    class intervention whose within-class randomization is explicitly fixed.
    """
    if offsets is None:
        return kernel(cmult)
    offsets = np.asarray(offsets)
    out = np.zeros((NE, 2, NS, K, NS))
    for e in range(NE):
        for z in (0, 1):
            for s in range(NS):
                for ai, a in enumerate(ARMS[1:], 1):
                    out[e, z, s, ai] = np.mean([
                        p_ord(MU[s] + cmult * (TH[(a, s, z)] + delta)
                              + LAM * (EASE_MID[e] - 0.5))
                        for delta in offsets[ai]], axis=0)
    return out


def true_logging_conditional_blips(Kk, T, beh):
    """Exact associational E[Y|S1=s,A1=a] contrast under logging continuation.

    For gz=0 the first-action assignment is unconfounded given S1, but continuation
    still follows beh, not UNIF5. For gz>0 first-action selection changes P(E,Z).
    """
    V = np.zeros((T + 2, NE, 2, NS))
    V[T + 1] = np.arange(NS) == 3
    for t in range(T, 0, -1):
        for e in range(NE):
            for z in (0, 1):
                for s in range(NS):
                    q = np.r_[float(s == 3), Kk[e, z, s, 1:] @ V[t + 1, e, z]]
                    V[t, e, z, s] = beh[z, s] @ q
    out = {}
    for s in range(NS):
        for ai, a in enumerate(ARMS):
            w = np.array([[P_E[e] * (P_Z if z else 1-P_Z) * p_s1(e)[s]
                           * beh[z, s, ai] for z in (0, 1)] for e in range(NE)])
            w /= w.sum()
            q = np.full((NE, 2), float(s == 3)) if ai == 0 else np.sum(Kk[:, :, s, ai] * V[2], axis=-1)
            out[s, a] = float(np.sum(w*q)) - float(s == 3)
    return out


# ---------------------------------------------------------------------------
# behaviour (logging) policy
# ---------------------------------------------------------------------------
def make_beh(kappa: float, floor: float, gz: float = 0.0) -> np.ndarray:
    """Logging policy table, shape (2, NS, K).

    `kappa` is the confounding strength: with kappa > 0 a severe arm arrives
    disproportionately in a bad state, and STOP arrives disproportionately in a good
    one -- the mechanism that makes an unadjusted comparison of arms invert the true
    ordering. kappa = 0 plus floor = 1/K is exactly uniform randomization, the
    control condition.

    `floor` is the per-arm probability floor. NOTE the feasibility constraint:
    K * floor <= 1, so with K = 5 the largest attainable floor is 0.20, which is
    exactly uniform. A floor cannot be set independently of the arm count -- the
    design's own positivity floor has to respect this.

    `gz` > 0 makes the logging policy track the LATENT error type Z, which is what
    premise check P3 showed is needed before unmeasured confounding can move a
    decision rather than only an estimate.
    """
    if K * floor > 1.0 + 1e-12:
        raise ValueError('infeasible floor: K * floor = %.3f > 1' % (K * floor))
    tab = np.zeros((2, NS, K))
    for z in (0, 1):
        for s in range(NS):
            lg = np.zeros(K)
            for ai, a in enumerate(ARMS):
                lg[ai] = (kappa * 2.0 * (1.0 if s >= 2 else -1.0) if ai == 0
                          else kappa * SEV[a] * BAD[s] * 0.6)
            if gz > 0:
                lg[ARMS.index('LOCAL' if z == 0 else 'RESET')] += gz * 2.0
            p = np.exp(lg - lg.max())
            p = p / p.sum()
            tab[z, s] = (1 - K * floor) * p + floor
    return tab


def simulate(n_tasks: int, runs: int, T: int, Kk: np.ndarray, beh: np.ndarray, rng,
             mislabel: float = 0.0, template_sd: float = 0.0, cmult: float = 1.0) -> dict:
    """Draw `n_tasks` tasks with `runs` episodes each. Latents are drawn PER TASK, so
    episodes of the same task are dependent -- which is why every interval in this
    project resamples whole tasks rather than episodes.

    Two failure mechanisms, off by default. They exist so the grid contains cells in
    which the causal estimators are also supposed to break; a simulation study that
    only shows them winning is an advertisement, not a validation.

    `mislabel` p: with probability p, a LOCAL intervention delivered in a wrong state
    (S_t <= 1) is RECORDED as RETRY, with the recorded propensity taken from the
    recorded label. The transition still follows the arm actually delivered. This is
    measurement error in the treatment, which is what a text-log classifier produces,
    and no amount of correct weighting repairs it: the estimator is answering a
    question about a mislabelled action.

    `template_sd` sigma: each class carries J = 3 paraphrase templates whose true
    effects differ by N(0, sigma) on the ordered-logit scale, drawn once per
    replicate. The analyst observes only the class. The target class intervention explicitly includes this uniform template
    mixture. Class labels alone do not identify a different template mixture.
    This is a transport stress test, not intrinsic failure of class interventions.
    """
    n = n_tasks * runs
    task = np.repeat(np.arange(n_tasks), runs)
    e = np.repeat(rng.choice(NE, size=n_tasks, p=P_E), runs)
    z = np.repeat((rng.random(n_tasks) < P_Z).astype(int), runs)
    cum = np.cumsum([p_s1(i) for i in range(NE)], axis=1)
    u = rng.random(n)
    s = (cum[e] < u[:, None]).sum(1).clip(0, NS - 1)
    elig = np.zeros((n, T), bool)
    A = np.zeros((n, T), int)
    B = np.ones((n, T))
    Sm = np.full((n, T), -1, np.int8)
    alive = np.ones(n, bool)
    Kc = Kk.cumsum(-1)
    J = 3
    # per-replicate template offsets, shape (K, J); index 0 (STOP) unused
    toff = rng.normal(0.0, template_sd, size=(K, J)) if template_sd > 0 else None
    Tm = np.full((n, T), -1, np.int8)
    n_mislabelled = 0
    for t in range(T):
        idx = np.nonzero(alive)[0]
        if not len(idx):
            break
        elig[idx, t] = True
        Sm[idx, t] = s[idx]
        pa = beh[z[idx], s[idx]]
        u = rng.random(len(idx))[:, None]
        ai = (pa.cumsum(1) < u).sum(1).clip(0, K - 1)
        true_ai = ai.copy()
        if mislabel > 0:
            swap = (true_ai == ARMS.index('LOCAL')) & (s[idx] <= 1) & (rng.random(len(idx)) < mislabel)
            ai = np.where(swap, ARMS.index('RETRY'), ai)
            n_mislabelled += int(swap.sum())
        A[idx, t] = ai                                  # RECORDED label
        B[idx, t] = pa[np.arange(len(idx)), ai]         # propensity of the RECORDED label
        alive[idx[true_ai == 0]] = False
        mv = idx[true_ai != 0]
        am = true_ai[true_ai != 0]                      # transition uses the DELIVERED arm
        if len(mv):
            if toff is None:
                u2 = rng.random(len(mv))[:, None]
                s[mv] = (Kc[e[mv], z[mv], s[mv], am] < u2).sum(1).clip(0, NS - 1)
            else:
                tj = rng.integers(0, J, size=len(mv))
                Tm[mv, t] = tj
                u2 = rng.random(len(mv))
                for j2, i2 in enumerate(mv):
                    a2, s2, e2, z2 = am[j2], int(s[i2]), int(e[i2]), int(z[i2])
                    eta = (MU[s2] + cmult * (TH[(ARMS[a2], s2, z2)] + toff[a2, tj[j2]])
                           + LAM * (EASE_MID[e2] - 0.5))
                    s[i2] = int((np.cumsum(p_ord(eta)) < u2[j2]).sum().clip(0, NS - 1))
    return dict(task=task, e=e, z=z, elig=elig, A=A, B=B, S=Sm,
                Y=(s == 3).astype(float), T=T, template=Tm,
                n_mislabelled=n_mislabelled,
                template_offsets=(toff.tolist() if toff is not None else None))
