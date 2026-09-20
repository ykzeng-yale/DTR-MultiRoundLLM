"""Fitted estimators for the corrected E0 diagnostic grid.

Naive conditional regression estimates logging-continuation association, not the
uniform-continuation intervention blip. IPW includes the initial inverse assignment
factor and subsequent target/logging ratios. Sequential Q is fitted on compressed
(state,time); known recorded logging probabilities supply the DR correction.
Persistent latents can invalidate a Markov interpretation of that Q. Intervals are
calculated from equal task means, not treated as independent episodes. Read the
2026-09-20 corrected report for estimand and precision limits.
"""
from __future__ import annotations

import numpy as np

from simulator import ARMS, K, NS, UNIF5


def task_clustered(task: np.ndarray, score: np.ndarray):
    """Mean and 95% interval over task means. Returns (est, se, lo, hi)."""
    lab, inv, cnt = np.unique(task, return_inverse=True, return_counts=True)
    cm = np.bincount(inv, weights=score) / cnt
    est = float(cm.mean())
    se = float(cm.std(ddof=1) / np.sqrt(len(cm)))
    return est, se, est - 1.96 * se, est + 1.96 * se


def blip_naive_marginal(d) -> dict:
    """Mean outcome by first-turn arm, no conditioning at all."""
    out = {}
    for i, a in enumerate(ARMS):
        m = d['elig'][:, 0] & (d['A'][:, 0] == i)
        out[a] = float(d['Y'][m].mean()) if m.sum() > 5 else np.nan
    return out


def blip_naive_conditional(d, s: int) -> dict:
    m0 = d['elig'][:, 0] & (d['S'][:, 0] == s)
    q = {}
    for i, a in enumerate(ARMS):
        m = m0 & (d['A'][:, 0] == i)
        q[a] = float(d['Y'][m].mean()) if m.sum() > 5 else np.nan
    return {a: q[a] - q['STOP'] for a in ARMS}


def blip_mediator(d, s: int) -> dict:
    """The C2 failure: condition on the intermediate state to value the first arm."""
    m0 = d['elig'][:, 0] & (d['S'][:, 0] == s)
    cell = {}
    for i in np.nonzero(m0)[0]:
        s2 = int(d['S'][i, 1]) if d['T'] > 1 and d['elig'][i, 1] else -1
        cell.setdefault((s2, int(d['A'][i, 0])), []).append(d['Y'][i])
    q = {k: float(np.mean(v)) for k, v in cell.items() if len(v) > 3}
    s2s = sorted({k[0] for k in q})
    out = {}
    for i, a in enumerate(ARMS):
        vs = [q[(s2, i)] for s2 in s2s if (s2, i) in q]
        out[a] = float(np.mean(vs)) if vs else np.nan
    return {a: out[a] - out['STOP'] for a in ARMS}


def blip_ipw(d, s: int, T: int, continuation: np.ndarray = UNIF5) -> dict:
    """Hajek per-decision IPW for gamma_1(s, a, STOP) with a fixed continuation."""
    m0 = d['elig'][:, 0] & (d['S'][:, 0] == s)
    # Within (S_1, A_1), inverse first-action propensity restores P(E,Z|S_1).
    # Omitting this factor is valid only when b_1 is constant in that stratum.
    W = 1.0 / d['B'][:, 0]
    for t in range(1, T):
        el = d['elig'][:, t]
        W[el] *= continuation[d['A'][el, t]] / d['B'][el, t]
    out = {}
    for i, a in enumerate(ARMS):
        m = m0 & (d['A'][:, 0] == i)
        if m.sum() < 5:
            out[a] = np.nan
            continue
        w = W[m]
        out[a] = float((w * d['Y'][m]).sum() / w.sum()) if w.sum() > 0 else np.nan
    return {a: out[a] - out['STOP'] for a in ARMS}


def fit_q(d, T: int, pol: np.ndarray, optimal: bool = False, idx=None, key=None):
    """Iterated-Q (sequential regression) g-computation, tabular.

    The pseudo-outcome at turn t is the realized Y for episodes that ended at t and
    the plugged-in continuation value otherwise, which is what makes this the
    g-formula rather than a pooled regression.
    """
    n = len(d['Y'])
    if idx is None:
        idx = np.arange(n)
    mask = np.zeros(n, bool)
    mask[idx] = True
    if key is None:
        def key(i, t):
            return (int(d['S'][i, t]), t)
    last = np.full(n, -1)
    for t in range(T):
        last[d['elig'][:, t]] = t
    Q = [{} for _ in range(T)]
    fb = [{} for _ in range(T)]
    nextv = np.zeros(n)
    for t in range(T - 1, -1, -1):
        m = d['elig'][:, t] & mask
        y = np.where(last == t, d['Y'], nextv)
        cells = {}
        for i in np.nonzero(m)[0]:
            cells.setdefault((key(i, t), int(d['A'][i, t])), []).append(y[i])
        for (kk, aa), v in cells.items():
            Q[t].setdefault(kk, {})[aa] = float(np.mean(v))
        for aa in range(K):
            ma = m & (d['A'][:, t] == aa)
            fb[t][aa] = float(y[ma].mean()) if ma.any() else (float(y[m].mean()) if m.any() else 0.0)
        v_t = np.zeros(n)
        for i in np.nonzero(d['elig'][:, t])[0]:
            c = Q[t].get(key(i, t), {})
            qs = np.array([c.get(aa, fb[t][aa]) for aa in range(K)])
            v_t[i] = qs.max() if optimal else float(pol @ qs)
        nextv = v_t
    return Q, fb, nextv


def dr_scores(d, T: int, pol: np.ndarray, Q, fb, key=None) -> np.ndarray:
    """Sequential AIPW influence-function scores for V(pol)."""
    n = len(d['Y'])
    if key is None:
        def key(i, t):
            return (int(d['S'][i, t]), t)
    last = np.full(n, -1)
    for t in range(T):
        last[d['elig'][:, t]] = t
    Vv = np.zeros((n, T + 1))
    Qa = np.zeros((n, T))
    R = np.zeros((n, T))
    W = np.ones((n, T))
    for t in range(T):
        prev = W[:, t - 1] if t > 0 else np.ones(n)
        rt = np.ones(n)
        for i in np.nonzero(d['elig'][:, t])[0]:
            c = Q[t].get(key(i, t), {})
            qs = np.array([c.get(aa, fb[t][aa]) for aa in range(K)])
            Vv[i, t] = float(pol @ qs)
            Qa[i, t] = qs[d['A'][i, t]]
            if last[i] == t:
                R[i, t] = d['Y'][i]
            rt[i] = pol[d['A'][i, t]] / d['B'][i, t]
        W[:, t] = prev * rt
    return Vv[:, 0] + np.sum(W * d['elig'] * (R + Vv[:, 1:] - Qa), axis=1)


def value_ipw(d, T: int, pol: np.ndarray = UNIF5):
    """Sequential IPW value with task-clustered interval."""
    ratio = np.where(d['elig'], pol[d['A']] / np.where(d['B'] > 0, d['B'], 1), 1.0)
    w = np.cumprod(ratio, axis=1)[:, -1]
    return task_clustered(d['task'], w * d['Y'])


def value_gcomp(d, T: int, pol: np.ndarray = UNIF5) -> float:
    _, _, v0 = fit_q(d, T, pol)
    return float(v0.mean())


def value_dr(d, T: int, pol: np.ndarray = UNIF5, folds: int = 3, rng=None):
    """Cross-fitted sequential DR value, folds drawn over TASKS."""
    n_tasks = len(np.unique(d['task']))
    if rng is None:
        rng = np.random.default_rng(0)
    assign = rng.permutation(np.arange(n_tasks) % folds)
    fa = assign[d['task']]
    sc = np.zeros(len(d['Y']))
    for k in range(folds):
        tr = np.nonzero(fa != k)[0]
        Qk, fbk, _ = fit_q(d, T, pol, idx=tr)
        sc = np.where(fa == k, dr_scores(d, T, pol, Qk, fbk), sc)
    return task_clustered(d['task'], sc)


def learned_rule(d, T: int) -> dict:
    """Backward-induction optimal rule learned from the data (the DTR critic)."""
    Qo, fbo, _ = fit_q(d, T, UNIF5, optimal=True)
    rule = {}
    for t in range(T):
        for s in range(NS):
            c = Qo[t].get((s, t), {})
            rule[(t, s)] = int(np.argmax([c.get(aa, fbo[t][aa]) for aa in range(K)]))
    return rule
