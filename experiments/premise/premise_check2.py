#!/usr/bin/env python3
"""Premise check P2 -- where the "naive critic is biased" claim actually holds.

P1 (premise_check.py) confirmed two claims and REFUTED a third:
  C1 confirmed  an unadjusted comparison of intervention classes reverses the
                true ordering (E[Y|A=locate] = 0.47 vs E[Y|A=retry] = 0.81 while
                the true blip of locate over retry in the wrong state is +0.30).
  C2 confirmed  conditioning on the intermediate state when valuing the FIRST
                intervention collapses a true +0.156 blip to +0.005, because that
                state is a mediator of the first action as well as a confounder of
                the second.
  C3 REFUTED    a correlational critic that conditions on the FULL state and acts
                greedily recovered the optimal regime in 39/40 replicates
                (regret 0.001). With a fully observed, low-dimensional state and
                an action whose myopically best choice is also its long-run best
                choice, there is no bias left for causal machinery to remove.

C3's refutation matters: "use a causal critic instead of a reward model" is not
justified by the mere existence of time-varying confounding. It is justified by
two specific failures, which P2 isolates and measures:

  F1 STATE INSUFFICIENCY. The state here is a natural-language conversation, so
     any critic conditions on a compression of it. If the user reacts to something
     the compression drops (how close the answer is, which error it made) and that
     something also moves the outcome, the C1 reversal returns and no estimator
     using only the compression can remove it. What removes it is the DESIGN:
     when the action is assigned by a known randomization that ignores the latent
     feature, the confounding is broken by construction.
  F2 MYOPIA. A reward model scoring immediate improvement is not a Q-function.
     When an intervention lowers immediate correctness but sets up a state from
     which repair is easy -- restructuring a wrong answer, for example -- the
     myopic choice and the optimal choice differ.

Setting. Three-level state X: 0 wrong and far from correct, 1 wrong but close,
2 correct. Y = 1{X_3 = 2}. Two intervention decisions. Four classes: U retry,
L locate the error, V request verification, S restructure/decompose. A latent
binary Z (the task has a subtle specification issue) shifts the transitions and
also drives what a real user sends -- it is exactly the kind of thing a text
feature set may fail to capture.

Two data conditions:
  OBS  logged interaction: the user's class depends on X and on the latent Z.
  RCT  sequentially randomized: each class with probability 1/4, ignoring Z.

Both are analysed by critics that see X only (the realistic case) and, for
reference, by critics that see (X, Z).
"""
from __future__ import annotations

import argparse, json, time
from pathlib import Path

import numpy as np

ACTIONS = ('U', 'L', 'V', 'S')
NA, NX = len(ACTIONS), 3

# P(X' | X, a, Z=0) rows over X' = (far, close, right)
T0 = {
    (0, 'U'): (0.60, 0.25, 0.15), (0, 'L'): (0.45, 0.30, 0.25),
    (0, 'V'): (0.70, 0.22, 0.08), (0, 'S'): (0.20, 0.75, 0.05),
    (1, 'U'): (0.10, 0.62, 0.28), (1, 'L'): (0.05, 0.35, 0.60),
    (1, 'V'): (0.08, 0.57, 0.35), (1, 'S'): (0.10, 0.65, 0.25),
    (2, 'U'): (0.02, 0.06, 0.92), (2, 'L'): (0.04, 0.10, 0.86),
    (2, 'V'): (0.01, 0.02, 0.97), (2, 'S'): (0.05, 0.15, 0.80),
}
Z_PENALTY = 0.55   # a subtle spec issue multiplies the chance of reaching `right`
P_Z = 0.45
P_X1 = {0: (0.40, 0.30, 0.30), 1: (0.55, 0.30, 0.15)}   # P(X_1 | Z)


def trans(x: int, a: str, z: int) -> np.ndarray:
    p = np.array(T0[(x, a)], dtype=float)
    if z == 1:
        p = p.copy()
        moved = p[2] * (1 - Z_PENALTY)
        p[2] -= moved
        p[0] += moved * 0.5
        p[1] += moved * 0.5
    return p / p.sum()


# ---------------------------------------------------------------------------
# exact truth
# ---------------------------------------------------------------------------
def value_of(regime, sees_z: bool) -> float:
    """E[Y] under a regime. regime(t, x, z) -> action; if not sees_z it must
    ignore z. Exact, by enumeration over (Z, X_1, X_2, X_3)."""
    tot = 0.0
    for z in (0, 1):
        pz = P_Z if z == 1 else 1 - P_Z
        for x1 in range(NX):
            p1 = P_X1[z][x1]
            a1 = regime(1, x1, z if sees_z else None)
            t1 = trans(x1, a1, z)
            for x2 in range(NX):
                a2 = regime(2, x2, z if sees_z else None)
                tot += pz * p1 * t1[x2] * trans(x2, a2, z)[2]
    return tot


def optimal_full():
    """Optimal regime for a decision maker who sees (X, Z)."""
    def d2(x, z):
        return max(ACTIONS, key=lambda a: trans(x, a, z)[2])
    def reg(t, x, z):
        if t == 2:
            return d2(x, z)
        return max(ACTIONS, key=lambda a: sum(trans(x, a, z)[x2] * trans(x2, d2(x2, z), z)[2]
                                              for x2 in range(NX)))
    return reg


def optimal_x_only():
    """Best regime among those that see X only. Enumerated over all 4^3 x 4^3
    (t=1, t=2) rules -- 4096 combinations, exact."""
    best, bestv = None, -1.0
    import itertools
    for r2 in itertools.product(ACTIONS, repeat=NX):
        for r1 in itertools.product(ACTIONS, repeat=NX):
            reg = (lambda t, x, z, _r1=r1, _r2=r2: _r1[x] if t == 1 else _r2[x])
            v = value_of(reg, sees_z=False)
            if v > bestv:
                bestv, best = v, (r1, r2)
    r1, r2 = best
    return (lambda t, x, z, _r1=r1, _r2=r2: _r1[x] if t == 1 else _r2[x]), bestv, best


def myopic_x_only():
    """The class with the highest immediate P(X_{t+1} = right), marginalising Z
    over its prior -- what a reward model trained on immediate improvement learns."""
    tab = {}
    for x in range(NX):
        tab[x] = max(ACTIONS, key=lambda a: (1 - P_Z) * trans(x, a, 0)[2] + P_Z * trans(x, a, 1)[2])
    return (lambda t, x, z, _t=tab: _t[x]), tab


# ---------------------------------------------------------------------------
# logging policies
# ---------------------------------------------------------------------------
def b_obs(x: int, z: int) -> np.ndarray:
    """A plausible real user: locates the error when the answer is clearly wrong,
    restructures when it is subtly wrong (z = 1), and is perfunctory when it looks
    right. Depends on the LATENT z, which no text feature set is guaranteed to
    recover."""
    if x == 2:
        p = {'U': 0.62, 'L': 0.13, 'V': 0.15, 'S': 0.10}
    elif z == 1:
        p = {'U': 0.12, 'L': 0.25, 'V': 0.13, 'S': 0.50}
    else:
        p = {'U': 0.15, 'L': 0.55, 'V': 0.15, 'S': 0.15}
    return np.array([p[a] for a in ACTIONS])


def b_rct(x: int, z: int) -> np.ndarray:
    return np.full(NA, 1.0 / NA)


def simulate(n: int, rng, behaviour) -> dict:
    z = (rng.random(n) < P_Z).astype(int)
    x1 = np.array([rng.choice(NX, p=P_X1[zi]) for zi in z])
    out = {'Z': z, 'X1': x1}
    x = x1
    for t in (1, 2):
        pa = np.array([behaviour(int(xi), int(zi)) for xi, zi in zip(x, z)])
        u = rng.random(n)[:, None]
        ai = (pa.cumsum(1) < u).sum(1).clip(0, NA - 1)
        out[f'A{t}'] = ai
        out[f'B{t}'] = pa[np.arange(n), ai]
        xn = np.array([rng.choice(NX, p=trans(int(xi), ACTIONS[int(a)], int(zi)))
                       for xi, a, zi in zip(x, ai, z)])
        out[f'X{t+1}'] = xn
        x = xn
    out['Y'] = (out['X3'] == 2).astype(int)
    return out


# ---------------------------------------------------------------------------
# critics learned from data
# ---------------------------------------------------------------------------
def critic_terminal(dat, use_z: bool):
    """Correlational critic: Ehat[Y | state, action], pooled over turns, greedy.
    This is the reward-model analogue."""
    keys = (lambda t, i: (int(dat[f'X{t}'][i]), int(dat['Z'][i]) if use_z else 0))
    acc = {}
    for t in (1, 2):
        for i in range(len(dat['Y'])):
            k = keys(t, i) + (int(dat[f'A{t}'][i]),)
            acc.setdefault(k, []).append(dat['Y'][i])
    q = {k: float(np.mean(v)) for k, v in acc.items()}
    tab = {}
    for x in range(NX):
        for zz in ((0, 1) if use_z else (0,)):
            cand = [(q.get((x, zz, ai), -np.inf), ai) for ai in range(NA)]
            tab[(x, zz)] = ACTIONS[max(cand)[1]]
    return (lambda t, x, z, _t=tab, _uz=use_z: _t[(int(x), int(z) if _uz else 0)]), tab


def critic_myopic(dat, use_z: bool):
    """Reward model on IMMEDIATE improvement: Ehat[1{X_{t+1} = right} | state, action]."""
    acc = {}
    for t in (1, 2):
        for i in range(len(dat['Y'])):
            k = (int(dat[f'X{t}'][i]), int(dat['Z'][i]) if use_z else 0, int(dat[f'A{t}'][i]))
            acc.setdefault(k, []).append(1 if dat[f'X{t+1}'][i] == 2 else 0)
    q = {k: float(np.mean(v)) for k, v in acc.items()}
    tab = {}
    for x in range(NX):
        for zz in ((0, 1) if use_z else (0,)):
            tab[(x, zz)] = ACTIONS[max([(q.get((x, zz, ai), -np.inf), ai) for ai in range(NA)])[1]]
    return (lambda t, x, z, _t=tab, _uz=use_z: _t[(int(x), int(z) if _uz else 0)]), tab


def critic_qlearning(dat, use_z: bool):
    """Backward-induction Q-learning on the same data -- the causal/DTR critic.
    Tabular, so correctly specified given the conditioning set it is allowed."""
    def key(t, i):
        return (int(dat[f'X{t}'][i]), int(dat['Z'][i]) if use_z else 0)
    n = len(dat['Y'])
    acc2 = {}
    for i in range(n):
        acc2.setdefault(key(2, i) + (int(dat['A2'][i]),), []).append(dat['Y'][i])
    q2 = {k: float(np.mean(v)) for k, v in acc2.items()}
    tab2, v2 = {}, {}
    for x in range(NX):
        for zz in ((0, 1) if use_z else (0,)):
            cand = [(q2.get((x, zz, ai), -np.inf), ai) for ai in range(NA)]
            best = max(cand)
            tab2[(x, zz)] = ACTIONS[best[1]]
            v2[(x, zz)] = best[0] if np.isfinite(best[0]) else float(dat['Y'].mean())
    acc1 = {}
    for i in range(n):
        acc1.setdefault(key(1, i) + (int(dat['A1'][i]),), []).append(v2[key(2, i)])
    q1 = {k: float(np.mean(v)) for k, v in acc1.items()}
    tab1 = {}
    for x in range(NX):
        for zz in ((0, 1) if use_z else (0,)):
            cand = [(q1.get((x, zz, ai), -np.inf), ai) for ai in range(NA)]
            tab1[(x, zz)] = ACTIONS[max(cand)[1]]
    reg = (lambda t, x, z, _t1=tab1, _t2=tab2, _uz=use_z:
           (_t1 if t == 1 else _t2)[(int(x), int(z) if _uz else 0)])
    return reg, (tab1, tab2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=6000)
    ap.add_argument('--reps', type=int, default=60)
    ap.add_argument('--seed', type=int, default=20260919)
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[2] / 'results' / 'premise'))
    a = ap.parse_args()

    opt_full = optimal_full()
    v_full = value_of(opt_full, sees_z=True)
    opt_x, v_x, opt_x_tab = optimal_x_only()
    myo, myo_tab = myopic_x_only()
    v_myo = value_of(myo, sees_z=False)

    truth = {
        'V_optimal_seeing_latent_Z': v_full,
        'V_optimal_X_only': v_x,
        'ceiling_cost_of_not_seeing_Z': v_full - v_x,
        'optimal_X_only_rule': {'t1': list(opt_x_tab[0]), 't2': list(opt_x_tab[1])},
        'myopic_X_only_rule': {int(k): v for k, v in myo_tab.items()},
        'V_of_myopic_rule': v_myo,
        'F2_myopia_gap': v_x - v_myo,
        'F2_myopic_differs_from_optimal': [k for k in range(NX)
                                          if myo_tab[k] != opt_x_tab[0][k]],
        'V_fixed_class': {c: value_of(lambda t, x, z, _c=c: _c, sees_z=False) for c in ACTIONS},
    }

    rng = np.random.default_rng(a.seed)
    res = {}
    for cond, beh in (('OBS', b_obs), ('RCT', b_rct)):
        rows = []
        for r in range(a.reps):
            dat = simulate(a.n, rng, beh)
            out = {}
            for nm, fn, uz in (('terminal_Xonly', critic_terminal, False),
                               ('terminal_XZ', critic_terminal, True),
                               ('myopic_Xonly', critic_myopic, False),
                               ('qlearn_Xonly', critic_qlearning, False),
                               ('qlearn_XZ', critic_qlearning, True)):
                reg, _ = fn(dat, uz)
                out[nm] = value_of(reg, sees_z=uz)
            # marginal, unadjusted comparison of turn-2 classes (the C1 reversal)
            out['marginal_EY_by_A2'] = {ACTIONS[k]: float(dat['Y'][dat['A2'] == k].mean())
                                        for k in range(NA)}
            rows.append(out)
        def m(k):
            return float(np.mean([x[k] for x in rows]))
        res[cond] = {
            'value': {k: m(k) for k in ('terminal_Xonly', 'terminal_XZ', 'myopic_Xonly',
                                        'qlearn_Xonly', 'qlearn_XZ')},
            'regret_vs_X_only_ceiling': {k: v_x - m(k) for k in ('terminal_Xonly', 'myopic_Xonly', 'qlearn_Xonly')},
            'regret_vs_full_ceiling': {k: v_full - m(k) for k in ('terminal_XZ', 'qlearn_XZ')},
            'mean_marginal_EY_by_A2': {c: float(np.mean([x['marginal_EY_by_A2'][c] for x in rows]))
                                       for c in ACTIONS},
        }

    summary = {'n_per_rep': a.n, 'reps': a.reps, 'seed': a.seed, 'truth': truth, 'conditions': res}
    summary['findings'] = {
        'F1_state_insufficiency': (
            'regret of the X-only terminal critic: OBS %.4f vs RCT %.4f'
            % (res['OBS']['regret_vs_X_only_ceiling']['terminal_Xonly'],
               res['RCT']['regret_vs_X_only_ceiling']['terminal_Xonly'])),
        'F1_randomization_repairs_it': (
            'under RCT the same X-only critic reaches within %.4f of the X-only ceiling'
            % res['RCT']['regret_vs_X_only_ceiling']['terminal_Xonly']),
        'F2_myopia': 'myopic rule loses %.4f against the X-only optimum; it differs at states %s'
                     % (truth['F2_myopia_gap'], truth['F2_myopic_differs_from_optimal']),
    }

    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    outdir = Path(a.out) / ('P2_' + stamp)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
