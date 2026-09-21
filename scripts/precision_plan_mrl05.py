#!/usr/bin/env python3
"""MRL-05: root/family precision scenarios for the future frozen policy contrast.

Pure arithmetic plus a Monte Carlo check of the variance formula. No model, reference, candidate or
sandbox execution. Every number is CONDITIONAL on stated variance assumptions; none is a certified
sample size, a feasibility verdict or a choice of population. The useful-gain null (Delta <= 0.05),
the planning alternative (0.10), one-sided alpha 0.025 and 80% power are the lead's decision
(docs/worker_issues_resolution_20260921.md); this script chooses none of them.

Hierarchy (equal family weights, G families, m roots per family, R seeded replicates per arm per root):
    D_{r,k} in {-1,0,1}   paired single-replicate difference, policy minus frozen comparator
    tau2   = Var(D_{r,k}) = p_gain + p_harm - Delta^2   (for the SPECIFIED coupling of the two arms)
    tau2   = sB2 + sW2    sB2 = Var(theta_r) between-root, sW2 = E Var(D_{r,k} | r) within-root
    rhoF   = within-family correlation of theta_r
    Var(D_g)       = sB2 * (rhoF + (1 - rhoF)/m) + sW2/(m R)
    Var(Delta_hat) = Var(D_g) / G
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
import random
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
NULL, ALT, ALPHA, POWER = 0.05, 0.10, 0.025, 0.80
Z = NormalDist().inv_cdf(1 - ALPHA) + NormalDist().inv_cdf(POWER)


def var_family(tau2, share_between, rhoF, m, R):
    sB2, sW2 = tau2 * share_between, tau2 * (1 - share_between)
    return sB2 * (rhoF + (1 - rhoF) / m) + sW2 / (m * R)


def g_wald(vg, sep=ALT - NULL):
    """Families for a studentized/Wald lower bound; asymptotic, not finite-sample valid."""
    return math.ceil((Z / sep) ** 2 * vg)


def g_hoeffding(vg, sep=ALT - NULL, a=ALPHA):
    """J2 bound: D_g in [-1,1], radius sqrt(2 log(1/a) / G). Smallest G with P(Delta_hat - r > NULL) >= POWER
    at Delta = ALT under a normal approximation to Delta_hat."""
    zp = NormalDist().inv_cdf(POWER)
    c = math.sqrt(2 * math.log(1 / a)) + zp * math.sqrt(vg)
    return math.ceil((c / sep) ** 2)


def g_empirical_bernstein(vg, sep=ALT - NULL, a=ALPHA):
    """Maurer-Pontil (2009, Thm 4) on X=(D+1)/2 in [0,1], rescaled to D; plugs in the scenario variance for
    the sample variance. radius_D = sqrt(2 vg ln(2/a)/G) + 14 ln(2/a)/(3(G-1))."""
    zp, L = NormalDist().inv_cdf(POWER), math.log(2 / a)
    for G in range(2, 10**6):
        r = math.sqrt(2 * vg * L / G) + 14 * L / (3 * (G - 1))
        if r + zp * math.sqrt(vg / G) <= sep:
            return G
    return None


def simulate(tau_between_levels, m, R, G, reps, seed):
    """Check Var(Delta_hat) formula on binary data. Family effect f_g and root effect e_r are drawn from
    symmetric two-point laws; root-level gain/harm probabilities are then set so theta_r = base + f_g + e_r."""
    rng = random.Random(seed)
    base, sf, se, disc = 0.10, *tau_between_levels
    # per-replicate: gain prob a_r, harm prob b_r with a_r - b_r = theta_r and a_r + b_r = disc (fixed)
    ests, thetas_all, within = [], [], []
    for _ in range(reps):
        tot = 0.0
        for _g in range(G):
            f = sf if rng.random() < 0.5 else -sf
            fam = 0.0
            for _r in range(m):
                e = se if rng.random() < 0.5 else -se
                th = base + f + e
                a, b = (disc + th) / 2, (disc - th) / 2
                assert 0 <= a <= 1 and 0 <= b <= 1 and a + b <= 1
                s = 0
                for _k in range(R):
                    u = rng.random()
                    s += 1 if u < a else -1 if u < a + b else 0
                fam += s / R
            tot += fam / m
        ests.append(tot / G)
    mean = sum(ests) / reps
    emp = sum((x - mean) ** 2 for x in ests) / (reps - 1)
    sB2 = sf**2 + se**2
    rhoF = sf**2 / sB2
    # Var(D | r) = (a+b) - theta_r^2, so sW2 = disc - E[theta^2] = disc - (base^2 + sB2)
    sW2 = disc - (base**2 + sB2)
    theory = (sB2 * (rhoF + (1 - rhoF) / m) + sW2 / (m * R)) / G
    return {"G": G, "m": m, "R": R, "sB2": sB2, "rhoF": rhoF, "sW2": sW2,
            "empirical_var": emp, "formula_var": theory, "ratio": emp / theory, "mean": mean, "reps": reps}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "results/precision_plan_mrl05_20260921.json")
    args = ap.parse_args(argv)
    grid = []
    for tau2, share, rhoF, m, R in itertools.product(
            (0.09, 0.15, 0.25), (0.2, 0.5, 0.8), (0.0, 0.3), (1, 3), (2, 4)):
        vg = var_family(tau2, share, rhoF, m, R)
        gw = g_wald(vg)
        grid.append({"tau2": tau2, "between_root_share": share, "rhoF": rhoF, "m": m, "R": R,
                     "var_family": round(vg, 6), "G_wald": gw, "roots_wald": gw * m,
                     "calls_wald": gw * m * (1 + 2 * R), "G_emp_bernstein": g_empirical_bernstein(vg),
                     "G_hoeffding": g_hoeffding(vg)})
    checks = {
        "z_sum": Z,
        "J2_radius_G230_a025": math.sqrt(2 * (1 / 230) * math.log(1 / 0.025)),  # J2 table: .1791011241
        "hoeffding_floor_G_at_zero_variance": g_hoeffding(0.0),
        "superiority_over_zero_factor": ((Z / ALT) ** 2) / ((Z / (ALT - NULL)) ** 2),
        "pilot_descriptive": {
            "root_mean_sample_variance_primary": 1 / 12,
            "single_pair_moment_primary": 2 / 14,
            "implied_split_if_both_taken_literally": {"sW2": 2 * (2 / 14 - 1 / 12), "sB2": 2 / 14 - 2 * (2 / 14 - 1 / 12)},
            "warning": "two discordant roots, one unresolved family, a different contrast (arm vs arm, not policy vs "
                       "fixed arm): a scenario anchor only, not an estimate to transfer",
        },
    }
    sims = [simulate((0.05, 0.10, 0.40), m=3, R=2, G=40, reps=20000, seed=1),
            simulate((0.0, 0.15, 0.30), m=1, R=4, G=60, reps=20000, seed=2)]
    out = {"version": "mrl05-precision-scenarios-v1", "null": NULL, "alternative": ALT, "alpha_one_sided": ALPHA,
           "power": POWER, "evidence_class": "conditional arithmetic; no model/reference/candidate/sandbox execution",
           "checks": checks, "simulation_checks": sims, "grid": grid}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"checks": checks, "sims": [{k: s[k] for k in ("ratio", "empirical_var", "formula_var")} for s in sims]}, indent=1))


if __name__ == "__main__":
    main()
