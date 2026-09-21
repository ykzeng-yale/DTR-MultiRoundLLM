# MRL-05: root/family precision plan for the future frozen policy contrast

> Lead audit: [MRL-05–08 decisions](lead_review_mrl05_08_20260921.md) supersede conflicting validity, guard and freeze claims below. Implementation acceptance is distinct from execution authorization.

**Experiments workstream, 2026-09-21 (started 14:51Z; source-only, one CPU, 0 model / reference / candidate /
sandbox executions, $0).** Processed lead revision: `e7eb925`. Script
[`scripts/precision_plan_mrl05.py`](../scripts/precision_plan_mrl05.py), output
[`results/precision_plan_mrl05_20260921.json`](../results/precision_plan_mrl05_20260921.json).

This applies the lead's decision in [the consolidated resolution](worker_issues_resolution_20260921.md):
useful-gain null Δ ≤ 0.05, planning alternative Δ = 0.10, one-sided α = 0.025, 80% power, one prespecified final
analysis. **It chooses no threshold, population, screen or uncertainty procedure.** Every number below is
conditional on its stated variance assumptions. None is a certified sample size, and none says a design is
feasible or infeasible.

## The contrast and its sampling structure

The estimand is Δ = Σ_g w_g E[D_g], the frozen public-history policy minus the frozen development-selected
fixed arm. The outcome is whether the final artifact passes its declared private suite. Family weights are
equal. There are G independent families, m roots per family, and R seeded continuation replicates per arm per
root. Every root shares one initial prefix.

| symbol | meaning | why it matters |
|---|---|---|
| D_{r,k} ∈ {−1, 0, 1} | paired single-replicate difference under the **specified coupling** of the two arms | this is the only place the old "discordance − Δ²" formula applies |
| τ² = Var(D_{r,k}) = p_gain + p_harm − Δ² | total single-replicate variance | under the alternative Δ = 0.10, τ² ≥ 0.09 necessarily |
| σ²_B = s·τ² | between-root variance of the root effect θ_r | not reduced by replicates |
| σ²_W = (1 − s)·τ² | within-root replicate variance | divided by R |
| ρ_F | within-family correlation of θ_r | reduces the information in each root |

Var(D_g) = σ²_B·(ρ_F + (1 − ρ_F)/m) + σ²_W/(m·R), and Var(Δ̂) = Var(D_g)/G.

A Monte Carlo check on binary data with non-constant root and family effects gives empirical/formula variance
ratios of **0.992 and 0.997** (20,000 replications each). The formula is exact for that construction, so the
residual is simulation noise.

**Coupling.** Before the freeze, the design should state that the policy and the comparator use the same seed
stream s_{r,k} on each root and replicate. Where the policy selects the comparator's own action, the two
branches are then the same request. The 147 recorded same-seed requests reproduced byte for byte, but that
covers only those requests; it is not a guarantee. Under this coupling those replicates contribute D = 0 by
construction, and τ² is driven by the policy's switch rate. This only reduces variance. It is **not** an
assumption that gains or harms are rare.

## Pilot numbers are a scenario anchor, not an estimate

The v1c primary contrast (syntactic history-derived cue minus generic) gives:

- a root-mean sample variance of 1/12;
- a single-pair moment of 2/14.

Taking both literally would imply σ²_B ≈ 0.024 and σ²_W ≈ 0.119, so s ≈ 0.17. Do not use this as a
transferable estimate:

- only two roots were discordant;
- all seven roots sit in one unresolved family;
- it is an arm-versus-arm contrast, not policy versus fixed arm;
- replicate pairing across arm seeds does not identify a unit-level gain or harm law.

The grid therefore brackets it rather than resting on it.

## Scenario results (grid of 72 cells in the JSON; representative rows)

Calls per root = 1 initial + 2R continuations. This excludes diagnostic executor starts and any extra calls
the policy makes.

| τ² | s (between-root share) | ρ_F | m | R | roots, Wald bound | receiver calls, Wald bound | families, empirical Bernstein | families, J2 Hoeffding |
|---|---|---|---|---|---|---|---|---|
| 0.09 | 0.2 | 0 | 1 | 2 | 170 | 850 | 956 | 3,392 |
| 0.09 | 0.2 | 0 | 1 | 4 | 114 | 1,026 | 824 | 3,309 |
| 0.15 | 0.2 | 0 | 1 | 2 | 283 | 1,415 | 1,200 | 3,526 |
| 0.15 | 0.2 | 0 | 1 | 4 | 189 | 1,701 | 998 | 3,417 |
| 0.15 | 0.5 | 0 | 1 | 2 | 354 | 1,770 | 1,345 | 3,597 |
| 0.15 | 0.5 | 0.3 | 3 | 2 | 495 | 2,475 | 946 | 3,386 |
| 0.15 | 0.8 | 0 | 1 | 2 | 424 | 2,120 | 1,487 | 3,662 |
| 0.25 | 0.5 | 0 | 1 | 2 | 589 | 2,945 | 1,811 | 3,797 |
| 0.25 | 0.8 | 0.3 | 3 | 2 | 1,086 | 5,430 | 1,361 | 3,604 |

- **Wald column:** one-sided studentized/Wald lower bound, G = (2.8016/0.05)²·Var(D_g). It is asymptotic, not
  finite-sample valid.
- **Empirical Bernstein column:** Maurer–Pontil, finite-sample valid for bounded independent families, with the
  scenario variance plugged in.
- **Hoeffding column:** the J2 procedure. Its radius √(2·log 40 / G) reproduces J2's 0.1791011241 at G = 230.

## What the grid says, stated conditionally

1. **The J2 Hoeffding procedure dominates everything else.** Its 2,952 floor exceeds every Wald and
   empirical-Bernstein requirement in the grid. Within a scenario, family-count ratios to Wald are 5.5–83×
   (Hoeffding) and 2.9–16× (empirical Bernstein), against 18.6× variation of the Wald count across variance
   scenarios.
   - The J2 Hoeffding bound uses the full [−1, 1] range of D_g. Even at zero variance, the 0.05-versus-0.10
     test needs **≥ 2,952 independent families**; the bound alone requires √(2·log 40 / G) < 0.05.
   - A variance-adaptive valid bound (empirical Bernstein) needs 617–2,038 families across the grid.
   - A Wald/cluster-robust bound needs 114–1,086 roots.

   This is a property of the procedures, not a feasibility verdict. **Choosing the prespecified uncertainty
   procedure is the lead's decision**; I recommend comparing a variance-adaptive finite-sample bound with a
   family-clustered studentized interval before fixing the population size.
2. **Replicates buy roots, not calls.** In every cell, R = 2 uses fewer receiver calls than R = 4. R = 4 cuts
   the number of roots only when the within-root share is large (s = 0.2: 283 → 189 roots at τ² = 0.15).
   - If curated eligible roots are the scarce resource, R = 4 is worth considering.
   - If receiver calls are scarce, R = 2 is.
   - R = 1 would minimise calls but maximise roots. Either way, the choice belongs in the freeze, not after
     outcomes are seen.
3. **Family structure enters through ρ_F, not the root count.** With ρ_F = 0.3 and m = 3, the required roots
   rise by 19–56% relative to independent roots. Screening family relations before outcomes is therefore
   precision-relevant, not only leakage-relevant.
4. **Superiority over zero is a different, easier question.** It needs one quarter of the families that the
   useful-gain test needs, because the separation is 0.10 rather than 0.05. Under the lead's rule, a study sized
   only for superiority can pass "Δ > 0" while remaining inconclusive about "Δ > 0.05".

## What this plan does not do

- It does not claim any number of the 396 mechanically screened candidates is an eligible independent family.
- It does not transport the 24-slate exclusion fraction to the larger pool.
- It does not remove zero-discordance roots.
- It does not pick a difficulty-screened population.

A difficulty screen on independent seeds would change the target population unless its sampling weights are
kept and the estimand is re-weighted back to the original population. If the eligible family count cannot
support the chosen procedure at 0.05, the lead's rule is to report inconclusive feasibility, not to raise the
threshold.

## Inputs still needed for a full freeze

| input | owner |
|---|---|
| Target population and sampling/weights | lead |
| Uncertainty procedure | lead |
| Eligible family count after semantic/prior-family/specification review | experiments, bounded review job |
| Arm coupling | experiments proposes the same-seed coupling above |
| R | lead, after pricing roots against calls |
| Resource ceiling | lead |

Superseded: every categorical feasibility statement in
[`confirmatory_sizing_20260921.md`](confirmatory_sizing_20260921.md), whose correction banner lists them.
