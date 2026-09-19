#!/usr/bin/env python3
"""Premise check P1 -- does the project's central claim actually hold?

This is NOT the pre-registered simulation study (that is E0, still being
designed). It is a minimal, fully tabular sanity check of the four claims the
project rests on, in a setting where the truth is computed exactly by
enumeration rather than estimated. If a claim fails here, it fails everywhere,
and the framing has to change before any model is called.

Setting. A frozen receiver has made an attempt; X_1 in {0,1} records whether that
attempt is correct. Two intervention decisions follow (t = 1, 2); the terminal
outcome is Y = X_3, whether the final answer is correct. Baseline difficulty
D in {easy, hard} is observed. Three intervention classes:

  U  unary retry           -- content-free "try again"
  L  locate the error      -- point at what is wrong, add no new information
  V  verification request   -- ask the receiver to check its own work

Transition structure (the point of the example): the best action DEPENDS ON THE
STATE. When the answer is wrong, L repairs it most often. When the answer is
already right, V protects it and L is the most likely to damage it. So no fixed
action is optimal and the optimal rule is a regime, not a choice.

Logging (behaviour) policy -- confounded exactly as the project claims real users
are: a wrong answer provokes L; a right answer gets a perfunctory U. Therefore L
is concentrated on bad states and U on good ones, and a marginal comparison of
outcomes by action must make L look harmful.

Claims tested
  C1  A marginal (unadjusted) comparison of classes reverses the true ordering.
  C2  A regression that conditions on the intermediate state X_2 when valuing the
      FIRST intervention is biased, because X_2 is a mediator of A_1 as well as a
      confounder of A_2. This is the specifically longitudinal error, and it is
      not fixed by "adjusting for everything".
  C3  A correlational critic -- fit E[Y | state, action] on logged data and act
      greedily on it -- is suboptimal, and by how much.
  C4  Per-decision IPW, iterated-Q g-computation and the doubly robust estimator
      recover the true regime value, with intervals that cover.

Everything here is exact or Monte Carlo over a known law; no model calls.
"""
from __future__ import annotations

import argparse, itertools, json, time
from pathlib import Path

import numpy as np

ACTIONS = ('U', 'L', 'V')
AIDX = {a: i for i, a in enumerate(ACTIONS)}
DIFF = ('easy', 'hard')

# ---------------------------------------------------------------------------
# the data-generating process (a known law, so every "truth" below is exact)
# ---------------------------------------------------------------------------
P_HARD = 0.5
# P(X_1 = 1 | D): the receiver's unaided first attempt
P_FIRST = {'easy': 0.70, 'hard': 0.30}
# P(X_{t+1} = 1 | X_t = 0, A_t = a, D): repair a wrong answer
P_REPAIR = {
    ('U', 'easy'): 0.15, ('U', 'hard'): 0.10,
    ('L', 'easy'): 0.45, ('L', 'hard'): 0.30,
    ('V', 'easy'): 0.25, ('V', 'hard'): 0.15,
}
# P(X_{t+1} = 1 | X_t = 1, A_t = a, D): keep an already-correct answer
P_KEEP = {
    ('U', 'easy'): 0.92, ('U', 'hard'): 0.90,
    ('L', 'easy'): 0.86, ('L', 'hard'): 0.84,
    ('V', 'easy'): 0.97, ('V', 'hard'): 0.96,
}
# behaviour policy b(a | X_t): wrong -> locate; right -> perfunctory retry
B = {0: {'U': 0.15, 'L': 0.70, 'V': 0.15},
     1: {'U': 0.70, 'L': 0.15, 'V': 0.15}}


def p_next(x: int, a: str, d: str) -> float:
    """P(X_{t+1} = 1 | X_t = x, A_t = a, D = d)."""
    return P_REPAIR[(a, d)] if x == 0 else P_KEEP[(a, d)]


# ---------------------------------------------------------------------------
# exact truth by enumeration
# ---------------------------------------------------------------------------
def true_value(regime) -> float:
    """E[Y] under a regime d: (t, x, d) -> action. Exact, by enumeration."""
    tot = 0.0
    for d in DIFF:
        pd = P_HARD if d == 'hard' else 1 - P_HARD
        for x1 in (0, 1):
            p1 = P_FIRST[d] if x1 == 1 else 1 - P_FIRST[d]
            a1 = regime(1, x1, d)
            for x2 in (0, 1):
                q = p_next(x1, a1, d)
                p2 = q if x2 == 1 else 1 - q
                a2 = regime(2, x2, d)
                tot += pd * p1 * p2 * p_next(x2, a2, d)
    return tot


def true_blip_t2(x: int, d: str, a: str, a_ref: str) -> float:
    """Exact turn-2 blip: E[Y | X_2 = x, D = d, do(A_2 = a)] - same with a_ref."""
    return p_next(x, a, d) - p_next(x, a_ref, d)


def true_blip_t1(x: int, d: str, a: str, a_ref: str, future) -> float:
    """Exact turn-1 blip with the future fixed to `future`: a regime for t = 2."""
    def v(a1):
        s = 0.0
        for x2 in (0, 1):
            q = p_next(x, a1, d)
            s += (q if x2 == 1 else 1 - q) * p_next(x2, future(x2, d), d)
        return s
    return v(a) - v(a_ref)


def fixed(a: str):
    return lambda t, x, d: a


def optimal_regime():
    """The exact optimal regime, by backward induction on the known law."""
    def d2(x, d):
        return max(ACTIONS, key=lambda a: p_next(x, a, d))
    def reg(t, x, d):
        if t == 2:
            return d2(x, d)
        best, ba = -1.0, None
        for a in ACTIONS:
            q = p_next(x, a, d)
            v = sum((q if x2 == 1 else 1 - q) * p_next(x2, d2(x2, d), d) for x2 in (0, 1))
            if v > best:
                best, ba = v, a
        return ba
    return reg


# ---------------------------------------------------------------------------
# sampling
# ---------------------------------------------------------------------------
def simulate(n: int, rng) -> dict:
    d = np.where(rng.random(n) < P_HARD, 'hard', 'easy')
    pf = np.array([P_FIRST[x] for x in d])
    x1 = (rng.random(n) < pf).astype(int)
    out = {'D': d, 'X1': x1}
    x = x1
    for t in (1, 2):
        pa = np.array([[B[int(xi)][a] for a in ACTIONS] for xi in x])
        u = rng.random(n)[:, None]
        a_i = (pa.cumsum(1) < u).sum(1).clip(0, 2)
        a = np.array([ACTIONS[i] for i in a_i])
        b = pa[np.arange(n), a_i]
        q = np.array([p_next(int(xi), ai, di) for xi, ai, di in zip(x, a, d)])
        xn = (rng.random(n) < q).astype(int)
        out[f'A{t}'] = a
        out[f'B{t}'] = b
        out[f'X{t+1}'] = xn
        x = xn
    out['Y'] = out['X3']
    return out


# ---------------------------------------------------------------------------
# estimators
# ---------------------------------------------------------------------------
def ipw_value(dat, regime) -> float:
    """Hajek per-decision IPW with KNOWN behaviour probabilities."""
    n = len(dat['Y'])
    w = np.ones(n)
    for t in (1, 2):
        tgt = np.array([regime(t, int(x), d) for x, d in zip(dat[f'X{t}'], dat['D'])])
        w *= (dat[f'A{t}'] == tgt) / dat[f'B{t}']
    return float((w * dat['Y']).sum() / w.sum()) if w.sum() > 0 else np.nan


def _tab_q2(dat):
    """Tabular Qhat_2(x, d, a) = mean(Y) in each cell."""
    q = {}
    for x in (0, 1):
        for d in DIFF:
            for a in ACTIONS:
                m = (dat['X2'] == x) & (dat['D'] == d) & (dat['A2'] == a)
                q[(x, d, a)] = float(dat['Y'][m].mean()) if m.sum() else np.nan
    return q


def _tab_q1(dat, v2):
    """Tabular Qhat_1(x, d, a) = mean of the plugged-in V2 in each cell."""
    pseudo = np.array([v2[(int(x2), d)] for x2, d in zip(dat['X2'], dat['D'])])
    q = {}
    for x in (0, 1):
        for d in DIFF:
            for a in ACTIONS:
                m = (dat['X1'] == x) & (dat['D'] == d) & (dat['A1'] == a)
                q[(x, d, a)] = float(pseudo[m].mean()) if m.sum() else np.nan
    return q, pseudo


def gcomp_value(dat, regime) -> float:
    """Iterated-Q g-computation (sequential regression), tabular."""
    q2 = _tab_q2(dat)
    v2 = {(x, d): q2[(x, d, regime(2, x, d))] for x in (0, 1) for d in DIFF}
    q1, _ = _tab_q1(dat, v2)
    vals = [q1[(int(x1), d, regime(1, int(x1), d))] for x1, d in zip(dat['X1'], dat['D'])]
    return float(np.nanmean(vals))


def dr_value(dat, regime, folds: int = 5, seed: int = 0) -> float:
    """Cross-fitted sequential AIPW. With known propensities this is consistent
    for any outcome model; the outcome model only removes variance."""
    n = len(dat['Y'])
    rng = np.random.default_rng(seed)
    fold = rng.integers(0, folds, n)
    scores = np.empty(n)
    for f in range(folds):
        tr, te = fold != f, fold == f
        sub = {k: v[tr] for k, v in dat.items()}
        q2 = _tab_q2(sub)
        v2 = {(x, d): q2[(x, d, regime(2, x, d))] for x in (0, 1) for d in DIFF}
        q1, _ = _tab_q1(sub, v2)
        idx = np.where(te)[0]
        tgt1 = np.array([regime(1, int(dat['X1'][i]), dat['D'][i]) for i in idx])
        tgt2 = np.array([regime(2, int(dat['X2'][i]), dat['D'][i]) for i in idx])
        m1 = (dat['A1'][idx] == tgt1)
        m2 = (dat['A2'][idx] == tgt2)
        w1 = m1 / dat['B1'][idx]
        w2 = w1 * (m2 / dat['B2'][idx])
        q1v = np.array([q1[(int(dat['X1'][i]), dat['D'][i], tgt1[j])] for j, i in enumerate(idx)])
        v2v = np.array([v2[(int(dat['X2'][i]), dat['D'][i])] for i in idx])
        q2v = np.array([q2[(int(dat['X2'][i]), dat['D'][i], tgt2[j])] for j, i in enumerate(idx)])
        q1v = np.nan_to_num(q1v, nan=float(np.nanmean(dat['Y'][tr])))
        v2v = np.nan_to_num(v2v, nan=float(np.nanmean(dat['Y'][tr])))
        q2v = np.nan_to_num(q2v, nan=float(np.nanmean(dat['Y'][tr])))
        scores[idx] = q1v + w1 * (v2v - q1v) + w2 * (dat['Y'][idx] - q2v)
    return float(scores.mean()), float(scores.std(ddof=1) / np.sqrt(n))


# ---- the naive comparators the project claims are wrong --------------------
def naive_marginal_t2(dat) -> dict:
    """C1: mean outcome by turn-2 action, no adjustment at all."""
    return {a: float(dat['Y'][dat['A2'] == a].mean()) for a in ACTIONS}


def naive_conditioned_on_mediator_t1(dat) -> dict:
    """C2: value the FIRST action while conditioning on the intermediate state
    X_2. X_2 is a mediator of A_1, so this blocks the very path being measured."""
    out = {}
    for a in ACTIONS:
        num = den = 0.0
        for x2 in (0, 1):
            for d in DIFF:
                cell = (dat['X2'] == x2) & (dat['D'] == d)
                m = cell & (dat['A1'] == a)
                if m.sum() and cell.sum():
                    num += cell.sum() * dat['Y'][m].mean()
                    den += cell.sum()
        out[a] = float(num / den) if den else np.nan
    return out


def correlational_critic_regime(dat):
    """C3: pool the logged turns, fit Ehat[Y | state, difficulty, action], and act
    greedily on it -- a reward model with no causal correction and no accounting
    for what happens after the action."""
    q = {}
    for x in (0, 1):
        for d in DIFF:
            for a in ACTIONS:
                m1 = (dat['X1'] == x) & (dat['D'] == d) & (dat['A1'] == a)
                m2 = (dat['X2'] == x) & (dat['D'] == d) & (dat['A2'] == a)
                ys = np.concatenate([dat['Y'][m1], dat['Y'][m2]])
                q[(x, d, a)] = float(ys.mean()) if len(ys) else -np.inf
    best = {(x, d): max(ACTIONS, key=lambda a: q[(x, d, a)]) for x in (0, 1) for d in DIFF}
    return (lambda t, x, d: best[(int(x), d)]), q, best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=4000, help='episodes per replicate')
    ap.add_argument('--reps', type=int, default=200)
    ap.add_argument('--seed', type=int, default=20260919)
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[2] / 'results' / 'premise'))
    a = ap.parse_args()

    opt = optimal_regime()
    v_opt = true_value(opt)
    v_fixed = {x: true_value(fixed(x)) for x in ACTIONS}
    v_behav = None  # value of the logging policy itself, by enumeration
    tot = 0.0
    for d in DIFF:
        pd = P_HARD if d == 'hard' else 1 - P_HARD
        for x1 in (0, 1):
            p1 = P_FIRST[d] if x1 == 1 else 1 - P_FIRST[d]
            for a1 in ACTIONS:
                for x2 in (0, 1):
                    q = p_next(x1, a1, d)
                    for a2 in ACTIONS:
                        tot += (pd * p1 * B[x1][a1] * (q if x2 == 1 else 1 - q)
                                * B[x2][a2] * p_next(x2, a2, d))
    v_behav = tot

    truth = {
        'optimal_regime': {f't{t},x{x},{d}': opt(t, x, d) for t in (1, 2) for x in (0, 1) for d in DIFF},
        'V_optimal': v_opt,
        'V_fixed': v_fixed,
        'V_behaviour_policy': v_behav,
        'blip_t2_vs_U': {f'x{x},{d},{a}': true_blip_t2(x, d, a, 'U')
                         for x in (0, 1) for d in DIFF for a in ('L', 'V')},
    }

    rng = np.random.default_rng(a.seed)
    rows = []
    for r in range(a.reps):
        dat = simulate(a.n, rng)
        nm = naive_marginal_t2(dat)
        nc = naive_conditioned_on_mediator_t1(dat)
        crit_reg, _, crit_best = correlational_critic_regime(dat)
        dr, se = dr_value(dat, opt, seed=r)
        rows.append({
            'rep': r,
            'naive_marginal_t2': nm,
            'naive_marginal_says_L_beats_U': nm['L'] > nm['U'],
            'naive_cond_mediator_t1': nc,
            'critic_regime': {f'x{x},{d}': crit_best[(x, d)] for x in (0, 1) for d in DIFF},
            'critic_regime_is_optimal': all(crit_best[(x, d)] == opt(2, x, d) for x in (0, 1) for d in DIFF),
            'V_true_of_critic_regime': true_value(lambda t, x, d, _b=crit_best: _b[(int(x), d)]),
            'ipw_V_opt': ipw_value(dat, opt),
            'gcomp_V_opt': gcomp_value(dat, opt),
            'dr_V_opt': dr,
            'dr_se': se,
            'dr_covers': abs(dr - v_opt) <= 1.96 * se,
        })

    def arr(k):
        return np.array([x[k] for x in rows], dtype=float)

    summary = {
        'n_per_rep': a.n, 'reps': a.reps, 'seed': a.seed,
        'truth': truth,
        'C1_marginal_reverses_ordering': {
            'true_blip_L_vs_U_when_wrong_easy': true_blip_t2(0, 'easy', 'L', 'U'),
            'true_blip_L_vs_U_when_wrong_hard': true_blip_t2(0, 'hard', 'L', 'U'),
            'mean_naive_EY_given_A2': {k: float(np.mean([x['naive_marginal_t2'][k] for x in rows])) for k in ACTIONS},
            'reps_in_which_naive_says_L_beats_U': int(sum(x['naive_marginal_says_L_beats_U'] for x in rows)),
            'verdict': 'REVERSED' if sum(x['naive_marginal_says_L_beats_U'] for x in rows) == 0 else 'not reversed',
        },
        'C2_conditioning_on_mediator': {
            'true_blip_t1_L_vs_U_given_optimal_future_wrong_easy':
                true_blip_t1(0, 'easy', 'L', 'U', lambda x, d: opt(2, x, d)),
            'true_blip_t1_L_vs_U_given_optimal_future_wrong_hard':
                true_blip_t1(0, 'hard', 'L', 'U', lambda x, d: opt(2, x, d)),
            'mean_naive_conditioned_EY_by_A1': {k: float(np.mean([x['naive_cond_mediator_t1'][k] for x in rows])) for k in ACTIONS},
        },
        'C3_correlational_critic': {
            'reps_in_which_critic_regime_equals_optimal': int(sum(x['critic_regime_is_optimal'] for x in rows)),
            'mean_true_value_of_critic_regime': float(arr('V_true_of_critic_regime').mean()),
            'V_optimal': v_opt,
            'mean_regret': float(v_opt - arr('V_true_of_critic_regime').mean()),
            'modal_critic_regime': max({json.dumps(x['critic_regime'], sort_keys=True) for x in rows},
                                       key=lambda s: sum(json.dumps(x['critic_regime'], sort_keys=True) == s for x in rows)),
        },
        'C4_causal_estimators': {
            'V_optimal_truth': v_opt,
            'ipw': {'mean': float(arr('ipw_V_opt').mean()), 'bias': float(arr('ipw_V_opt').mean() - v_opt),
                    'sd': float(arr('ipw_V_opt').std(ddof=1))},
            'gcomp': {'mean': float(arr('gcomp_V_opt').mean()), 'bias': float(arr('gcomp_V_opt').mean() - v_opt),
                      'sd': float(arr('gcomp_V_opt').std(ddof=1))},
            'dr': {'mean': float(arr('dr_V_opt').mean()), 'bias': float(arr('dr_V_opt').mean() - v_opt),
                   'sd': float(arr('dr_V_opt').std(ddof=1)),
                   'mean_se': float(arr('dr_se').mean()),
                   'coverage_95': float(np.mean([x['dr_covers'] for x in rows]))},
        },
    }

    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    outdir = Path(a.out) / stamp
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
