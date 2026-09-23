# Matched fitted-history and regularization diagnostic

> Prepared and independently reviewed on September 22; first published September 23 after a lead-side delay. See [the current decision](e12_lead_judgment_20260923.md) for completed E12 evidence and current authority. The dated plan below does not renew an expired allowance.

22 September 2026. **Prospective specification, not an execution freeze or result.**
This is the next bounded lead-owned component of issue #2 after the
[fitted-prefix source delivery](fitted_history_comparator_20260922.md). It does not
replace the eight-cell prompt/policy proposal, establish ranking performance, or
assign another job to the E12 worker. Implementation, seed audit and source hashes
must be committed and reviewed before any sampled simulation.

## Target and fixed conditions

Estimate the population value of the fixed uniform-five-arm policy, including
absorbing STOP, in the existing synthetic E0 transition law. Root latents are
sampled from the declared population; every root has40 logged trajectories.
Use230 roots, horizon3, effect multiplier1, `gz=mislabel=template_sd=0` throughout.
Only the logging law changes:

| Cell index | Logger | kappa | action floor |
|---|---|---:|---:|
| 0 | Uniform | 0 | .20 |
| 1 | Base | 1 | .10 |
| 2 | Weak overlap | 2.5 | .02 |

All three target the same policy value, reported by the existing exact reference
as .6459770061744536. Recompute and bind that deterministic reference at freeze;
do not estimate truth from the simulated outcomes. Positive .02 support is weak
finite-sample overlap, not zero-support nonidentification. Latent-informed
assignment, mislabeling and changing template mixtures are outside this narrow
study. The original negative diagnostic results remain archived.

Plan200 independent datasets per cell,600 total. Proposed seed table: for cell
c=0,1,2 and replicate r=0,…,199, `data_seed=202609220000+1000*c+r` and
`fold_seed=202609320000+1000*c+r`. Audit these ranges against all existing run
manifests before calling them fresh; pin NumPy and the generator/seed algorithm.
Each dataset has three nonempty root folds shared by all comparisons. No seed or
fold is selected based on outcomes. Process replicates in fixed interleaved order
(r0:c0,c1,c2; r1:c0,c1,c2; …), retaining partial records at any cap.

## Four nuisance variants, eight matched point estimators

Cross compressed `(S_t,t)` versus complete recorded synthetic prefix H_t with
unshrunk versus fixed shrinkage fitting. Each nuisance variant fits once per
training fold and supplies both plug-in and DR scores on its held-out roots. All
variants use exactly the same dataset, folds, target policy and known recorded B.
No oracle Q, latent feature, held-out outcome or truth enters training.

For the shrinkage variants, fix lambda=5 before numerical execution, without a
hyperparameter search. At each backward stage, construct each training trajectory's
pseudo-outcome from its terminal Y if terminal there, otherwise the downstream
V fitted by **that same variant**. Let q_cell be the episode-weighted mean in
(key,action), q_pool the training action/stage mean with the existing stage/zero
fallback, and m the number of distinct training roots represented in that cell.
Use

    q_shrunk = (m * q_cell + 5 * q_pool) / (m + 5).

An unobserved cell uses q_pool. An absent action uses the training-stage mean;
an empty training stage uses0, exactly as the existing fallback. Recompute these
means and downstream values within the variant's own backward recursion; do not
shrink an already fitted unregularized table afterward. The unshrunk variant
retains q_cell when observed and the same fallback when absent.

Counting distinct roots makes the penalty respond to limited root support, but
m is **not** independent effective sample size or a variance estimate. Cell and
pool means remain episode-weighted: under40 trajectories per root, conditioning
on a visited history/action weights roots by their visitation frequency. Replacing
these conditional means with equally weighted observed-cell root means would be
a different estimator. At evaluation, average the40 scores per root, then average
all230 root means equally. The choice lambda5 is a prespecified heuristic, not an
optimality or consistency certificate. Both synthetic representations include S,
whose true-quality categories are not asserted observable to an LLM policy.

## Prespecified comparisons and reports

For each of the eight point estimators report bias, RMSE, empirical standard
deviation, bias Monte Carlo SE and all failures. For DR additionally report mean
and RMS root-level SE, nominal95% interval coverage, average width, below/above
miss counts, coverage MCSE and a binomial interval for coverage. The existing
root-mean normal interval is the procedure being tested, not a guaranteed valid
finite-sample interval. Do not certify a plug-in interval by treating the variance
of fitted root predictions as all of its uncertainty.

For every cell report paired squared-error differences and replicate-level MCSE
for all of: full versus compressed within each shrinkage choice; shrunk versus
raw within each representation; and DR versus plug-in within each fitted Q.
Use common dataset/fold pairs; do not treat paired estimators as independent
replications. These multiple descriptive comparisons do not constitute a
multiplicity-controlled selection procedure or justify promoting the best learner.
Report the full table, including variance penalties and inconclusive differences.

Record training-cell distinct-root/trajectory counts and held-out fallback
frequencies by stage and variant. Keep root support separate from propensity
weights. Missing fits cannot silently leave the denominator: list attempted,
completed, failed and unattempted replicate/variant cells with reasons. For a
failed interval, report returned-interval coverage and failure count separately;
also report successful-covering intervals divided by attempted replicates as an
operational success measure, not standard coverage. Paired comparisons use only
explicitly reported jointly completed pairs, with excluded pairs counted.

With200 completed independent replicates, nominal95% coverage has MCSE about
1.54 percentage points; its worst-case binomial MCSE is3.54 points. This is
diagnostic precision, not final interval validation. Wider uncertainty, a failure
to improve, or a DR variance penalty remains a result. No outcome-driven extension,
new cell, tuning, seed replacement or early efficacy/futility stopping is allowed.
A future final precision study requires its own justified specification.

## Implementation acceptance and resource boundary

Before sampling, commit the exact config/seed table, new regularization/comparison
source, versions, input hashes, output schema and independent review. Deterministic
fixtures must check lambda0 parity with the raw variant, half shrinkage at m=5,
global episode-duplication invariance of m and the penalty, unseen/large-support
behavior, variant-specific backward propagation, training-only fallback, held-out isolation,
intact root folds and identical nuisance use for plug-in and DR. Existing E0 source
and archived outcomes remain immutable. This document alone cannot serve as the
missing source freeze.

Proposed execution ceiling after those conditions: **one CPU worker,600 total
seconds including fitting/truth/reporting,256 MiB output, zero model calls,
benchmark reference/candidate code executions, installations or spend**. An enforceable outer
timeout must retain completed records and charge any failed/incomplete work.
A capped subset is an incomplete diagnostic, not the planned200-replicate study;
report unequal completion if the cap interrupts an interleaved block. Time-based
truncation may affect which datasets finish, so do not claim the partial subset
retains prespecified unconditional coverage precision. No heartbeat renews this
budget.

Do not execute during E12's reserved quiet window or any other active shared-host
lease. Explicit release and fresh resource checks precede any later execution;
light source/design review can continue. Current work is design only. E12 and
then independent prompt-policy validation remain the research priorities. Overall
completion stays55%, change0pp; no efficacy or submission-readiness claim follows.
