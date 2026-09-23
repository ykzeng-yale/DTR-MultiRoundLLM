#!/usr/bin/env python3
"""Planning arithmetic for the (unreleased) E13 proposal, from committed E12 and MRL-15 frame files only.

No receiver, model, reference or candidate is executed. Every scenario below is a planning assumption, not a
result: the E12 inputs come from 5 public-fail roots with unresolved family structure, and the gated R1 rule was
selected on those same roots (best of the gate-then-arm rules), so the +0.10 point estimate is subject to
selection optimism. Precision uses an uncalibrated normal approximation and a bounded-difference Hoeffding radius.
"""
from __future__ import annotations
import argparse, hashlib, json, math, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/e12_dev_v3_20260922T030255Z"
FRAME = ROOT / "results/frame_review_mrl15_20260922T021718Z/manifest.json"
N_REVIEWED = 20            # scripts/review_candidate_frame_mrl15.py N_REVIEW: frame ranks 1-20 were source-reviewed
E12_RETAINED = 14          # docs/e12_contract_review_20260922.md: 14 of the 20 reviewed records retained
E12_SECONDS_PER_CALL = 314.3 / 154   # docs/e12_results_20260922.md: A+C collection time over all calls
TOKENS_PER_CALL = 512
Z95, Z80 = 1.959963984540054, 0.8416212335729143
WITHIN_VAR = 0.25          # Bernoulli maximum for one replicate of (arm grade - fixed STOP grade)
TAU2_SCENARIOS = (0.025, 0.05, 0.10, 0.20)  # sensitivity choices, not identified variance bounds


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def e12_gated(run=RUN):
    """Per public-fail root: replicate differences (arm - STOP) for R1, the rule's action."""
    report = json.loads((run / "analysis_report.json").read_text())
    inp = json.loads((run / "analysis_input.json").read_text())
    fail = report["initial_status"]["crosstab_roots"]["any_fail"]
    gated = fail["pass"] + fail["fail"] + fail["unknown"]
    roots = {r["root_id"]: r for r in inp["roots"]}
    rows = []
    for rid in gated:
        arms = roots[rid]["arms"]
        (stop,) = [x["grade"] for x in arms["STOP"]]
        reps = [x["grade"] for x in sorted(arms["R1"], key=lambda x: x["replicate"])]
        if stop is None or None in reps:
            raise SystemExit(f"missing grade at {rid}; this arithmetic assumes complete E12 grades")
        d = [g - stop for g in reps]
        rows.append({"root_id": rid, "stop": stop, "r1_replicates": reps, "mean_diff": statistics.fmean(d),
                     "within_sample_var": statistics.variance(d)})
    n_roots = report["n_roots"]
    means = [r["mean_diff"] for r in rows]
    R = len(rows[0]["r1_replicates"])
    between = statistics.variance(means)
    within = statistics.fmean(r["within_sample_var"] / R for r in rows)
    return {"n_roots": n_roots, "n_gated": len(rows), "gate_rate": len(rows) / n_roots,
            "replicates": R, "roots": rows,
            "delta_hat": statistics.fmean(means), "var_root_means": between,
            "mean_within_var_of_root_mean": within, "tau2_moment": max(0.0, between - within),
            "mean_within_sample_var_per_replicate": within * R,
            "tau2_note": ("Noisy moment estimate from 5 selected roots, not an identified variance decomposition. "
                          "An unbiased sample variance from two Bernoulli draws can equal 0.5, despite the "
                          "population variance bound of 0.25. The observed average sample variance 0.30 does "
                          "not violate that bound or require replacing tau2=0.025 by 0.05. Both are sensitivity "
                          "scenarios, not established lower bounds on population heterogeneity.")}


def precision(n_g, tau2, R, deltas=(0.05, 0.10), arms_varying=1):
    # Two sampled arms add their within-root variances only under independent seeds conditional on the root.
    # The same tau2 across comparisons is a sensitivity assumption, not an observed variance ordering.
    sd = math.sqrt(tau2 + arms_varying * WITHIN_VAR / R)
    se = sd / math.sqrt(n_g)
    out = {"n_gated": n_g, "tau2": tau2, "replicates": R, "arms_varying": arms_varying, "sd_root_diff": sd,
           "normal_halfwidth95": Z95 * se,
           "hoeffding_radius95_one_contrast": math.sqrt(2 * math.log(2 / 0.05) / n_g),
           "hoeffding_radius95_two_contrasts": math.sqrt(2 * math.log(4 / 0.05) / n_g)}
    for d in deltas:
        out[f"power_at_{d:.2f}"] = phi(d / se - Z95) + phi(-d / se - Z95)
        out[f"n_gated_for_80pct_power_at_{d:.2f}"] = math.ceil(((Z95 + Z80) * sd / d) ** 2)
    return out


USEFULNESS_THRESHOLD = 0.05   # lead's working absolute private-suite gain for "useful benefit" (L > .05)


def policy_sd(f, tau2, R, delta_cond, sw2=WITHIN_VAR):
    """SD of the per-root FULL-POLICY contrast D = g*(Y - S) for the gated rule against always-STOP.

    g is the decision-time public-fail indicator, Y the mean of R replicates of the taken action, S the
    initial artifact's grade (fixed once the artifact is frozen). With sigma2_cond = tau2 + sw2/R,
    E[D] = f*delta_cond and E[D^2] = f*(sigma2_cond + delta_cond^2), so
    Var(D) = f*(sigma2_cond + delta_cond^2) - (f*delta_cond)^2.
    The variance identity assumes independent replicate seeds conditional on the full frozen root.
    sw2 is the average conditional branch variance; its 0.25 default is an upper-bound planning plug-in,
    not evidence that each chosen (tau2, delta_cond, sw2) triple is a jointly attainable Bernoulli law.
    Roots are assumed independent for the subsequent SE; the actual family structure is unresolved.
    """
    return math.sqrt(f * (tau2 + sw2 / R + delta_cond ** 2) - (f * delta_cond) ** 2)


def _se(sd, n):
    return sd / math.sqrt(n)


def power_benefit(theta, sd, n, threshold=USEFULNESS_THRESHOLD):
    """P(L > threshold) with L the lower limit of a two-sided 95% interval: declaring useful benefit."""
    return phi((theta - threshold) / _se(sd, n) - Z95)


def power_futility(theta, sd, n, threshold=USEFULNESS_THRESHOLD):
    """Normal-approximation P(U < threshold); a true effect at threshold gives probability .025."""
    return phi((threshold - theta) / _se(sd, n) - Z95)


def n_for_80(effect_gap, sd):
    """Roots needed for 80% power when the true effect is effect_gap away from the threshold."""
    if effect_gap <= 0:
        return None
    return math.ceil(((Z95 + Z80) * sd / effect_gap) ** 2)


def _solve_delta(n, power_z, f, tau2, R, threshold=USEFULNESS_THRESHOLD):
    """Boundary conditional effect; power_z = Z95 + Phi^{-1}(desired declaration probability)."""
    lo, hi = threshold / f, 1.0
    if hi <= lo:
        return None
    def margin(delta):
        return f * delta - power_z * _se(policy_sd(f, tau2, R, delta), n) - threshold
    if margin(hi) < 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if margin(mid) >= 0:
            hi = mid
        else:
            lo = mid
    return hi


def _solve_futile_theta(n, f, tau2, R, threshold=USEFULNESS_THRESHOLD):
    """Largest nonnegative gain with at least 80% futility power; None if even zero is infeasible."""
    lo, hi = 0.0, threshold
    def margin(theta):
        sd = policy_sd(f, tau2, R, theta / f)
        return threshold - theta - (Z95 + Z80) * _se(sd, n)
    if margin(lo) < 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if margin(mid) >= 0:
            lo = mid
        else:
            hi = mid
    return lo


def usefulness(f, n_roots_available, tau2s, deltas=(0.0, 0.05, 0.10, 0.14, 0.20, 0.30, 0.40), replicates=(6, 8)):
    """The decision-relevant arithmetic: the lead's threshold applies to the FULL-POLICY contrast, not a subset."""
    rows = []
    for tau2 in tau2s:
        for R in replicates:
            for d in deltas:
                theta = f * d
                sd = policy_sd(f, tau2, R, d)
                rows.append({
                    "tau2": tau2, "replicates": R, "delta_cond": d, "theta_policy": theta, "sd_policy": sd,
                    "n_roots_for_80pct_benefit": n_for_80(theta - USEFULNESS_THRESHOLD, sd),
                    "benefit_80pct_unattainable_reason": None if theta > USEFULNESS_THRESHOLD else
                        "theta <= 0.05: no sample size attains 80% benefit power in this Normal model; "
                        "a false-positive declaration remains possible (2.5% at equality)",
                    "n_roots_for_80pct_futility": n_for_80(USEFULNESS_THRESHOLD - theta, sd),
                    "power_benefit_at_available_n": power_benefit(theta, sd, n_roots_available),
                    "power_futility_at_available_n": power_futility(theta, sd, n_roots_available),
                })
    return {
        "threshold": USEFULNESS_THRESHOLD,
        "scope_limit": (
            "This variance and every sample size below apply to the gated rule MINUS ALWAYS-STOP only. They rely on "
            "the contrast being exactly 0 at non-gated roots, which holds because the rule stops there. The lead "
            "memo's primary comparator b1 is a fixed CONTINUATION recipe, not STOP. For that contrast, write "
            "conditional means mu_g, mu_ng and variances v_g, v_ng: the full variance is "
            "f*v_g + (1-f)*v_ng + f*(1-f)*(mu_g-mu_ng)^2. Both strata's contrasts and the target mean may change, "
            "so neither the variance nor the required sample size is ordered relative to STOP. "
            "E12 does not settle those quantities: N1 scored 1.000 on all 9 non-gated roots, "
            "so the observed rule-minus-N1 contrasts there were all 0, while R1 itself drops non-gated roots from "
            "1.000 to 0.889. Sizing against a fixed-continuation comparator is NOT done here."),
        "decision_rule": "useful benefit needs L > 0.05; useful-gain futility needs U < 0.05; an interval endpoint "
                         "equal to 0.05 does not meet its strict rule. When the true effect is 0.05, each "
                         "declaration has probability 0.025 under this Normal approximation.",
        "target": "full-policy equal-weight contrast theta = f * delta_cond, NOT the gated-subset contrast",
        "n_roots_available": n_roots_available,
        "n_roots_available_note": "Hypothetical retained-root count, not a verified independent evaluation frame.",
        "power_scope": "Assumed-variance Normal approximations for one contrast at one final analysis; not "
                       "finite-sample calibration, simultaneous two-contrast power, or evidence of real family independence.",
        "min_delta_cond_for_theta_above_threshold": USEFULNESS_THRESHOLD / f,
        "min_delta_cond_demonstrable_at_available_n": {
            f"tau2={t},R={R}": {"power_50pct": _solve_delta(n_roots_available, Z95, f, t, R),
                                 "power_80pct": _solve_delta(n_roots_available, Z95 + Z80, f, t, R)}
            for t in tau2s for R in replicates},
        "max_theta_declarable_futile_at_available_n": {
            f"tau2={t},R={R}": _solve_futile_theta(n_roots_available, f, t, R) for t in tau2s for R in replicates},
        "futility_null_note": "null means no nonnegative gain reaches 80% futility power under that scenario; "
                              "it does not mean zero is an attainable boundary.",
        "rows": rows,
    }


def cost(G, n_gated, R, arms, validation=True, phase_a=True, audit_all=False):
    cont_roots = G if audit_all else n_gated
    calls = (G if phase_a else 0) + arms * R * cont_roots
    starts = ((3 * G if validation else 0) + (G if phase_a else 0)     # validation; public diagnostic (B)
              + (G if phase_a else 0) + arms * R * cont_roots + 2 * G)  # private initial + continuations; rechecks
    return {"retained_roots": G, "continuation_roots": cont_roots, "replicates": R, "arms": arms,
            "receiver_calls": calls, "reserved_completion_tokens": TOKENS_PER_CALL * calls,
            "isolated_starts": starts, "est_collection_seconds": round(calls * E12_SECONDS_PER_CALL)}


def build(run=RUN, frame=FRAME):
    e12 = e12_gated(run)
    f = e12["gate_rate"]
    eligible = json.loads(frame.read_text())["eligible_ordered_ids"]
    remaining = len(eligible) - N_REVIEWED
    retention = E12_RETAINED / N_REVIEWED
    G_full = math.floor(remaining * retention)
    ng_full = round(G_full * f)
    ng_v1 = round(30 * f)
    # Fixed sensitivity choices; the noisy sample moments identify none of these as a population lower bound.
    tau2s = list(TAU2_SCENARIOS)
    grid = [precision(n, t, R) for n in (e12["n_gated"], ng_v1, ng_full) for t in tau2s for R in (2, 4, 6, 8)]
    # R1 minus FRESH: tau2 here is the between-root variance of that contrast, unmeasured; same scenarios reused.
    mech = [precision(n, t, R, arms_varying=2) for n in (e12["n_gated"], ng_full) for t in tau2s for R in (6, 8)]
    designs = {
        "E13_v1_as_proposed": cost(30, ng_v1, 2, arms=1, audit_all=True),
        "E13a_restart_package_comparison_on_E12_gated_roots": cost(e12["n_gated"], e12["n_gated"], 6, arms=2,
                                                                  validation=False, phase_a=False),
        "E13b_full_remaining_frame": cost(G_full, ng_full, 8, arms=2),
    }
    return {
        "analysis_version": "e13-sizing-v3-usefulness-repaired",
        "evidence_class": "planning arithmetic from committed files; no model/benchmark execution; scenarios are assumptions",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (run / "analysis_report.json", run / "analysis_input.json", frame)},
        "e12_gated": e12,
        "frame": {"eligible": len(eligible), "reviewed": N_REVIEWED, "remaining_unreviewed": remaining,
                  "e12_retention": retention, "retained_root_count_scenario": G_full,
                  "gated_root_count_scenario": ng_full,
                  "interpretation": "Retention and gate-rate extrapolations are planning scenarios, not "
                                    "population estimates or confidence limits for this nonprobability roster."},
        "assumptions": {"within_replicate_var": WITHIN_VAR, "seconds_per_call": E12_SECONDS_PER_CALL,
                        "tau2_scenarios": tau2s, "normal_approximation": True,
                        "within_variance_interpretation": "Upper-bound planning plug-in under conditionally independent "
                            "replicate seeds; scenario moment triples are not asserted to define exact Bernoulli laws."},
        "usefulness_full_policy": usefulness(f, G_full, tau2s),
        "precision_grid_rule_minus_stop": grid,
        "precision_grid_r1_minus_fresh": mech,
        "designs": designs,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    out = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("frame", "designs")}, indent=1))


if __name__ == "__main__":
    main()
