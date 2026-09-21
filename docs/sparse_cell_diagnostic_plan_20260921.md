# Reused-seed diagnostic of empty-cell fallback

21 September 2026. Commit plan, exact seed/source config and code before running
the report. This follows the [population compression check](history_compression_results_20260921.md).
It is a diagnostic of the existing estimator's finite-data behavior, not a new
independent simulation study, learned prompt policy or real receiver experiment.

Replay all 80 existing FAIL_positivity seeds from the matched-estimator records,
with unchanged simulation sources, parameters and RNG order/root-fold assignment.
First reproduce each recorded plug-in/DR estimate within 1e-10. Preserve the old
records; stop and report if reproducibility fails. Reconstructed arrays receive
hashes, but earlier data-array hashes are unavailable, so matched estimates and
source/seed provenance are not a bytewise comparison to archived trajectory arrays.

At each of three training folds, record all 3 x 4 x 5 stage/state/action training
cell counts and distinct training-root counts. Report empty and low-count cells
descriptively, without excluding roots or changing the policy. The synthetic
logger has positive probabilities; sample-empty cells are not zero population
support. Keep all continuations of a root in one fold.

Compare three quantities on the same held-out initial states:

1. The original compressed-Q plug-in, using pooled-action fallback for absent
   state/action cells. An independently written array implementation must reproduce
   the original `fit_q` predictions before any modification is interpreted.
2. An oracle-fallback diagnostic: replace **only absent training cells** by the
   exact population compressed Q from the frozen prior calculation, at every
   backward step and at prediction. Recompute upstream regression pseudo-targets.
   This is an unavailable known-law repair used to diagnose the algorithm, not a
   proposed deployable method or a data-driven shrinkage choice.
3. The initial value of the fully known population compressed Q, averaged on those
   same evaluation initial states. It separates reference-law compression from
   sampling variation without supplying a learned full-history comparator.

Also report sequential DR scores using the identical Q fits within each of the
original and oracle-fill variants, verifying an independent array-score implementation
against the original score. Record held-out target-action probability mass assigned
to absent cells, among logger-generated eligible held-out histories at each stage,
as an exposure diagnostic. The summary averages folds equally; this is not
exposure under target-policy history occupancy.

Report means, bias against the unchanged uniform-policy truth, RMSE, paired
oracle-fallback minus original changes and squared-error differences, with
approximate Monte Carlo standard errors/intervals across complete seed records.
These intervals describe the selected synthetic condition and reused diagnostic
replications, not a fresh confirmatory method comparison. Do not count them as
80 new independent datasets beyond the earlier study or select a method on them.
If an oracle fill changes the result, attribute it to this defined algorithmic
substitution only; do not claim a unique decomposition of representation,
task composition, sparse observed cells and finite regression error.

Run one CPU worker; total report-process cap 120 seconds, output cap 10 MiB,
zero receiver calls/tokens, candidate/reference executions, installs or paid spend.
Stop collection five seconds before the process cap, retain completed records and
failures, and label partial runs incomplete. Do not report partial preferred seeds
as the complete comparison. Capture source/config/code freeze, software versions,
data/fold hashes and actual runtime. Tests use tiny synthetic fixtures separately.
Independent internal review checks the paired design and interpretation. MRL-01–04
and the primary same-prefix prompt experiment retain their priority and ownership.
