#!/usr/bin/env python3
"""Premise check P3 -- WHEN does causal correction change the decision, not just
the estimate?

P1 and P2 established:
  * an unadjusted comparison of intervention classes on logged data is badly
    wrong -- in P2's logged condition the class that is optimal from the
    far-wrong state (restructure) had the LOWEST observed mean outcome, 0.186
    against 0.637 for a perfunctory retry;
  * but a critic that conditions on the full observed state and acts greedily was
    barely harmed (regret 0.013 logged vs 0.015 randomized), so "there is
    time-varying confounding" does not by itself justify causal machinery for
    DECISIONS.

The missing ingredient is effect modification by something the critic cannot see.
If the best intervention depends on a latent feature of the error, and the user's
choice of intervention tracks that same latent feature, then within any observed
state the logged data over-represents each class exactly where that class works.
A critic conditioning on the observed state alone then learns each class's
performance *on the subpopulation where it was chosen*, not on the population --
and can invert the ranking.

This script sweeps the one parameter that controls that coupling, gamma: the
probability that the user recognises the latent error type and sends the matching
intervention (otherwise it falls back on its habit, locating the error). gamma = 0
means assignment ignores the latent feature; gamma = 1 means it tracks it exactly.
Under sequential randomization assignment ignores it by construction, whatever the
user would have done.

Latent Z: the error is conceptual (Z = 1) rather than mechanical (Z = 0).
  mechanical error  -> locating it (L) repairs it best
  conceptual error  -> restructuring (S) repairs it best
P(Z = 1) = 0.35, so the best rule for a decision maker who cannot see Z is L.
"""
from __future__ import annotations

import argparse, itertools, json, time
from pathlib import Path

import numpy as np

ACTIONS = ('U', 'L', 'V', 'S')
NA, NX = 4, 3
P_Z = 0.35
P_X1 = {0: (0.45, 0.30, 0.25), 1: (0.50, 0.30, 0.20)}

# P(X' | X, a, Z) over X' = (wrong-far, wrong-close, right).
# The ordering of L and S flips with Z: that is the effect modification.
T = {
    # mechanical error (Z = 0): locating works, restructuring is wasted motion
    (0, 'U', 0): (0.62, 0.23, 0.15), (0, 'L', 0): (0.38, 0.27, 0.35),
    (0, 'V', 0): (0.70, 0.22, 0.08), (0, 'S', 0): (0.55, 0.33, 0.12),
    (1, 'U', 0): (0.10, 0.62, 0.28), (1, 'L', 0): (0.05, 0.28, 0.67),
    (1, 'V', 0): (0.08, 0.57, 0.35), (1, 'S', 0): (0.15, 0.55, 0.30),
    # conceptual error (Z = 1): locating the symptom does not help, restructuring does
    (0, 'U', 1): (0.72, 0.20, 0.08), (0, 'L', 1): (0.66, 0.24, 0.10),
    (0, 'V', 1): (0.76, 0.18, 0.06), (0, 'S', 1): (0.34, 0.30, 0.36),
    (1, 'U', 1): (0.18, 0.66, 0.16), (1, 'L', 1): (0.16, 0.66, 0.18),
    (1, 'V', 1): (0.16, 0.66, 0.18), (1, 'S', 1): (0.08, 0.30, 0.62),
    # already correct: verification protects it, the others can damage it
    (2, 'U', 0): (0.02, 0.06, 0.92), (2, 'L', 0): (0.04, 0.10, 0.86),
    (2, 'V', 0): (0.01, 0.02, 0.97), (2, 'S', 0): (0.06, 0.16, 0.78),
    (2, 'U', 1): (0.03, 0.07, 0.90), (2, 'L', 1): (0.05, 0.11, 0.84),
    (2, 'V', 1): (0.01, 0.03, 0.96), (2, 'S', 1): (0.07, 0.17, 0.76),
}


def trans(x, a, z):
    p = np.array(T[(x, a, z)], float)
    return p / p.sum()


def value_of(rule1, rule2) -> float:
    """Exact E[Y] for an X-only regime given as two length-3 tuples of actions."""
    tot = 0.0
    for z in (0, 1):
        pz = P_Z if z == 1 else 1 - P_Z
        for x1 in range(NX):
            t1 = trans(x1, rule1[x1], z)
            for x2 in range(NX):
                tot += pz * P_X1[z][x1] * t1[x2] * trans(x2, rule2[x2], z)[2]
    return tot


def best_x_only():
    best, bv = None, -1.0
    for r2 in itertools.product(ACTIONS, repeat=NX):
        for r1 in itertools.product(ACTIONS, repeat=NX):
            v = value_of(r1, r2)
            if v > bv:
                bv, best = v, (r1, r2)
    return best, bv


def b_obs(x, z, gamma):
    """With probability gamma the user recognises the latent error type and sends
    the matching intervention; otherwise it falls back on its habit (locate).
    A floor of 0.05 keeps every class on support so the comparison is about bias,
    not about an unsupported target."""
    match = 'S' if z == 1 else 'L'
    p = {a: 0.05 for a in ACTIONS}
    if x == 2:
        p = {'U': 0.60, 'L': 0.12, 'V': 0.18, 'S': 0.10}
        return np.array([p[a] for a in ACTIONS])
    rest = 1.0 - 4 * 0.05
    p[match] += rest * gamma
    p['L'] += rest * (1 - gamma)
    v = np.array([p[a] for a in ACTIONS])
    return v / v.sum()


def b_rct(x, z, gamma):
    return np.full(NA, 0.25)


def simulate(n, rng, beh, gamma):
    z = (rng.random(n) < P_Z).astype(int)
    x1 = np.array([rng.choice(NX, p=P_X1[zi]) for zi in z])
    d = {'Z': z, 'X1': x1}
    x = x1
    for t in (1, 2):
        pa = np.array([beh(int(xi), int(zi), gamma) for xi, zi in zip(x, z)])
        u = rng.random(n)[:, None]
        ai = (pa.cumsum(1) < u).sum(1).clip(0, NA - 1)
        d[f'A{t}'] = ai
        d[f'B{t}'] = pa[np.arange(n), ai]
        xn = np.array([rng.choice(NX, p=trans(int(xi), ACTIONS[int(aa)], int(zi)))
                       for xi, aa, zi in zip(x, ai, z)])
        d[f'X{t+1}'] = xn
        x = xn
    d['Y'] = (d['X3'] == 2).astype(int)
    return d


def learn_terminal(d):
    """Correlational critic: Ehat[Y | X, A] pooled over turns, greedy. No use of
    the known assignment probabilities."""
    acc = {}
    for t in (1, 2):
        for i in range(len(d['Y'])):
            acc.setdefault((int(d[f'X{t}'][i]), int(d[f'A{t}'][i])), []).append(d['Y'][i])
    q = {k: float(np.mean(v)) for k, v in acc.items()}
    rule = tuple(ACTIONS[max([(q.get((x, ai), -np.inf), ai) for ai in range(NA)])[1]] for x in range(NX))
    return rule, rule, q


def learn_ipw_greedy(d):
    """Same conditioning set, but each turn's contribution is inverse-weighted by
    the KNOWN assignment probability, and the value is the terminal outcome under
    the target action followed by the data's own continuation -- a per-decision
    IPW estimate of the class ranking at each observed state."""
    num = {}
    den = {}
    for t in (1, 2):
        w = 1.0 / d[f'B{t}']
        for i in range(len(d['Y'])):
            k = (int(d[f'X{t}'][i]), int(d[f'A{t}'][i]))
            num[k] = num.get(k, 0.0) + w[i] * d['Y'][i]
            den[k] = den.get(k, 0.0) + w[i]
    q = {k: num[k] / den[k] for k in num if den[k] > 0}
    rule = tuple(ACTIONS[max([(q.get((x, ai), -np.inf), ai) for ai in range(NA)])[1]] for x in range(NX))
    return rule, rule, q


def learn_qlearn(d):
    """Backward-induction Q-learning on the observed state (the DTR critic)."""
    a2 = {}
    for i in range(len(d['Y'])):
        a2.setdefault((int(d['X2'][i]), int(d['A2'][i])), []).append(d['Y'][i])
    q2 = {k: float(np.mean(v)) for k, v in a2.items()}
    r2, v2 = [], {}
    for x in range(NX):
        c = max([(q2.get((x, ai), -np.inf), ai) for ai in range(NA)])
        r2.append(ACTIONS[c[1]])
        v2[x] = c[0] if np.isfinite(c[0]) else float(d['Y'].mean())
    a1 = {}
    for i in range(len(d['Y'])):
        a1.setdefault((int(d['X1'][i]), int(d['A1'][i])), []).append(v2[int(d['X2'][i])])
    q1 = {k: float(np.mean(v)) for k, v in a1.items()}
    r1 = tuple(ACTIONS[max([(q1.get((x, ai), -np.inf), ai) for ai in range(NA)])[1]] for x in range(NX))
    return r1, tuple(r2), (q1, q2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=8000)
    ap.add_argument('--reps', type=int, default=30)
    ap.add_argument('--seed', type=int, default=20260919)
    ap.add_argument('--gammas', default='0.0,0.25,0.5,0.75,1.0')
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[2] / 'results' / 'premise'))
    a = ap.parse_args()

    (opt1, opt2), vopt = best_x_only()
    truth = {
        'optimal_X_only_rule': {'t1': list(opt1), 't2': list(opt2)},
        'V_optimal_X_only': vopt,
        'V_fixed_class': {c: value_of((c,) * NX, (c,) * NX) for c in ACTIONS},
        'true_P_right_next_step': {f'x{x},{c},Z={z}': round(float(trans(x, c, z)[2]), 3)
                                   for x in (0, 1) for c in ACTIONS for z in (0, 1)},
        'population_avg_P_right_from_x0': {c: round(float((1 - P_Z) * trans(0, c, 0)[2] + P_Z * trans(0, c, 1)[2]), 4)
                                           for c in ACTIONS},
    }

    rng = np.random.default_rng(a.seed)
    rows = []
    for gamma in [float(g) for g in a.gammas.split(',')]:
        for cond, beh in (('OBS', b_obs), ('RCT', b_rct)):
            acc = {k: [] for k in ('terminal', 'ipw', 'qlearn')}
            rules = {k: [] for k in ('terminal', 'ipw', 'qlearn')}
            for r in range(a.reps):
                d = simulate(a.n, rng, beh, gamma)
                for nm, fn in (('terminal', learn_terminal), ('ipw', learn_ipw_greedy), ('qlearn', learn_qlearn)):
                    r1, r2, _ = fn(d)
                    acc[nm].append(value_of(r1, r2))
                    rules[nm].append((r1, r2))
            row = {'gamma': gamma, 'condition': cond}
            for nm in acc:
                v = float(np.mean(acc[nm]))
                modal = max(set(rules[nm]), key=rules[nm].count)
                row[nm] = {'mean_value': v, 'regret': vopt - v,
                           'modal_rule_t1': list(modal[0]), 'modal_rule_t2': list(modal[1]),
                           'frac_reps_recovering_optimal': float(np.mean([x == (opt1, opt2) for x in rules[nm]]))}
            rows.append(row)
            print('gamma=%.2f %s  regret: terminal %.4f  ipw %.4f  qlearn %.4f   modal terminal t1=%s'
                  % (gamma, cond, row['terminal']['regret'], row['ipw']['regret'],
                     row['qlearn']['regret'], ''.join(row['terminal']['modal_rule_t1'])))

    obs = [r for r in rows if r['condition'] == 'OBS']
    rct = [r for r in rows if r['condition'] == 'RCT']
    flip = [r['gamma'] for r in obs if r['terminal']['frac_reps_recovering_optimal'] < 0.5]
    summary = {
        'n_per_rep': a.n, 'reps': a.reps, 'seed': a.seed, 'truth': truth, 'rows': rows,
        'findings': {
            'gammas_where_logged_correlational_critic_fails_to_recover_optimum': flip,
            'randomized_critic_always_recovers_optimum': all(
                r['terminal']['frac_reps_recovering_optimal'] >= 0.9 for r in rct),
            'max_regret_gap_obs_minus_rct_for_terminal': max(
                (o['terminal']['regret'] - c['terminal']['regret']) for o, c in zip(obs, rct)),
            'does_known_propensity_ipw_repair_the_logged_case': {
                str(o['gamma']): {'terminal_regret': o['terminal']['regret'], 'ipw_regret': o['ipw']['regret']}
                for o in obs},
        },
    }
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    outdir = Path(a.out) / ('P3_' + stamp)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))
    print('\n--- findings ---')
    print(json.dumps(summary['findings'], indent=2, default=str))
    print('\noptimal X-only rule:', truth['optimal_X_only_rule'], 'V =', round(vopt, 4))
    print('population-average P(right) from the far-wrong state:', truth['population_avg_P_right_from_x0'])
    print('wrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
