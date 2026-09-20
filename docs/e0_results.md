# E0 results — estimator validation against exact truth

> **Historical snapshot; conclusions require the 2026-09-20 corrections.** Read [continuation report](continuation_report_20260920.md), [theory reconciliation](theory_reconciliation_20260920.md), [experiment audit](experiment_recheck_20260920.md), and [literature recheck](literature_recheck_20260920.md) before using this document. Earlier universal impossibility, optimality, matched-cost kill, and feature-no-signal claims are superseded. Original text remains for provenance.

**Executed 2026-09-19.** 17 cells × 996 replicates, CPU only, ~30 minutes on 6 workers.
Run directory `results/e0/20260919T234422Z/`; code in `experiments/e0/`; every cell's
truth recomputed by dynamic programming from that cell's own parameters and graded
against the **posterior-weighted** blip.

Abort condition A1 passed before the grid ran: the exact dynamic program matches a
2,000,000-episode Monte Carlo of `V(uniform-5)` to **0.00 MC SE** (0.645977 both), and
every conditional blip matches its brute-force Monte Carlo within about one MC SE.

All quantities are for the turn-1 blip in the close-wrong state `s = 1`, where the true
ordering is LOCALIZE (0.326) > RESET (0.289) > RETRY (0.221) > DIVERT (0.172).
τ is mean Kendall τ against that exact ordering; `P(top)` is the probability of naming
the true best arm; regret is against the exact state-only optimum.

| cell | marginal τ | marginal P(top) | conditional τ | mediator τ | IPW τ | IPW P(top) | DR bias | DR coverage | regret |
|---|---|---|---|---|---|---|---|---|---|
| `base` | -0.624 | 0.000 | +0.875 | -0.132 | +0.817 | 0.755 | -0.0007 | 0.943 | 0.0055 |
| `kappa0` | +0.279 | 0.792 | +0.863 | -0.137 | +0.863 | 0.771 | +0.0006 | 0.945 | 0.0043 |
| `kappa0.5` | -0.527 | 0.023 | +0.869 | -0.108 | +0.850 | 0.783 | -0.0001 | 0.934 | 0.0047 |
| `kappa2` | -0.610 | 0.001 | +0.861 | -0.081 | +0.757 | 0.715 | +0.0001 | 0.945 | 0.0067 |
| `floor0.05` | -0.665 | 0.000 | +0.878 | -0.124 | +0.723 | 0.689 | -0.0001 | 0.960 | 0.0064 |
| `floor0.02` | -0.667 | 0.000 | +0.870 | -0.120 | +0.613 | 0.576 | +0.0008 | 0.935 | 0.0072 |
| `T2` | -0.629 | 0.000 | +0.887 | -0.100 | +0.870 | 0.811 | -0.0005 | 0.935 | 0.0042 |
| `T5` | -0.620 | 0.001 | +0.829 | -0.137 | +0.694 | 0.631 | -0.0002 | 0.950 | 0.0072 |
| `n590` | -0.660 | 0.000 | +0.962 | -0.183 | +0.926 | 0.870 | -0.0004 | 0.944 | 0.0023 |
| `runs10` | -0.529 | 0.023 | +0.634 | +0.232 | +0.560 | 0.548 | -0.0001 | 0.935 | 0.0137 |
| `runs160` | -0.663 | 0.000 | +0.980 | -0.231 | +0.961 | 0.911 | -0.0003 | 0.945 | 0.0013 |
| `half_effect` | -0.658 | 0.000 | +0.629 | -0.056 | +0.538 | 0.567 | -0.0004 | 0.942 | 0.0067 |
| `latent_track` | -0.626 | 0.000 | +0.900 | -0.119 | +0.850 | 0.867 | -0.0000 | 0.955 | 0.0041 |
| `FAIL_positivity` | -0.666 | 0.000 | +0.824 | +0.012 | +0.426 | 0.387 | -0.0000 | **0.840** | 0.0136 |
| `FAIL_latent` | -0.414 | 0.060 | +0.894 | -0.073 | +0.824 | 0.857 | +0.0006 | 0.942 | 0.0032 |
| `FAIL_mislabel` | -0.388 | 0.015 | +0.873 | -0.097 | +0.818 | 0.733 | +0.0016 | 0.933 | 0.0057 |
| `FAIL_coarsening` | -0.587 | 0.002 | +0.819 | -0.108 | +0.777 | 0.712 | -0.0011 | **0.886** | 0.0088 |

## What replicated, and what did not

**1. Reading feedback effects off a confounded log fails totally.** The marginal
critic — no conditioning, which is how turn-level feedback comparisons are routinely
made — has τ between −0.39 and −0.67 and names the true best arm in **0.000–0.060** of
replicates in every confounded cell. Under randomization (`kappa0`) the identical
estimator recovers τ = +0.279 and P(top) = 0.792. So the failure is caused by the
confounding, not by noise, and randomization repairs it. This is the project's
strongest and most robust claim.

**2. Conditioning on the observed state beats inverse-probability weighting in 16 of
17 cells** (tied in the 17th, which is exactly uniform by construction). Weighting only
adds variance, and the penalty grows as the positivity floor shrinks: at floor 0.02 the
conditional critic holds τ = 0.870 while IPW falls to 0.613, and in the severe
positivity cell IPW collapses to 0.426 against the conditional critic's 0.824.

**3. The purpose-built unmeasured-confounding cell did not break the conditional
critic.** `FAIL_latent` makes the logging policy track, at strength 2.0, the latent
error type that determines *which arm is best* — the structure most hostile to a
state-conditioned estimator. Its conditional τ is 0.894, among the highest in the grid,
and its regret 0.0032 is the second lowest. Premise check P1's refutation of the
project's original decision-level claim therefore **replicates at R = 996 against an
adversarially designed cell**, and is now a result rather than a suspicion.

**4. Conditioning on the intermediate state to value the first intervention is not
just biased — it gets worse with more data.** The mediator-adjusted critic's τ goes
**+0.232 → −0.132 → −0.231** as replicates per task go 10 → 40 → 160. It is converging,
accurately, to the wrong number. This is the cleanest available demonstration that
"adjust for everything observed" is not a safe default in a longitudinal setting.

**5. The failure cells fail, and only they.** Cross-fitted DR coverage lies in
[0.933, 0.960] in 15 of 17 cells and falls outside nominal in exactly the two cells
designed to break it: **0.840** under a severe positivity violation and **0.886** under
violated coarsening sufficiency (paraphrases within a class having genuinely different
effects). Nothing else in the grid loses coverage.

**6. Precision, not bias, is the binding constraint.** DR bias never exceeds 0.0016 in
absolute value anywhere. But halving the effect size drops the conditional critic from
τ = 0.875 to 0.629, and cutting replicates per task from 40 to 10 drops it to 0.634
with regret rising 2.5×. Going the other way, 160 replicates per task reaches τ = 0.980
and regret 0.0013. The estimators are correct; what limits us is how much data 230
informative tasks can carry.

## What this licenses, and what it does not

It licenses: the estimator implementations are correct; the log-reading failure is real,
large and caused by confounding; randomization repairs it; the mediator adjustment is
actively harmful; and the boundary at which each estimator breaks is now mapped.

It does not license any claim about what a real intervention does to a real model. E0 is
a reference simulator whose intervention effects were chosen by the analyst; only its
difficulty law, its effective sample size, its degradation-in-the-correct-state sign and
its state space were calibrated to measurement.

## Consequence for the program

The causal machinery's value is established for **reporting effects** and is *not*
established for **choosing actions** — conditioning wins there, in every cell, including
the one built to make it lose. The program should therefore spend its confirmatory
budget on the design (randomization with logged propensities, which repairs the one
failure that is real and total) and on horizon and stopping, and should present the
weighting machinery as what it is: necessary for honest effect estimation, and not
demonstrated to improve decisions.
