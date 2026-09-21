# Empty-cell fallback materially affects the weak-overlap result

21 September 2026. **Reused-seed synthetic diagnostic**, frozen before execution
at **3b0666cbe8cfba5c00bf4a5090d5b476cf98d2ba**. This replays the existing 80
weak-overlap replications; it is not 80 additional independent datasets, a practical
estimator competition, or evidence of receiver/prompt efficacy.

## Finding and scientific decision

Replacing only empty training-cell predictions by unavailable population compressed
Q values, while recomputing all upstream pseudo-targets, substantially changes the
finite-sample result. The original plug-in's mean bias falls in magnitude from
5.43 to 0.57 percentage points and its RMSE falls from .07296 to .03251. DR's RMSE
also falls, from .09872 to .05582, while its mean bias is essentially unchanged
in the paired comparison. The original estimates remain preserved.

**Repair the interpretation:** the specified pooled-action fallback and its backward
propagation are a material algorithmic sensitivity in this selected synthetic
condition. The earlier poor result is not solely evidence against history
compression or the longitudinal identification theory. This does not identify a
unique fraction of error caused by empty cells, separate interactions with observed
small cells, or establish that an available repair would achieve the oracle result.
The original negative and weak-overlap uncertainty problems still stand.

**Hold new empirical stage:** this supplies no reason to release model collection
or expand generators. MRL-01–04 remain the experiment worker's queue, with the
same-prefix prompt study and independent policy validation as the priorities.

| Quantity, on identical root folds | Mean bias | Bias MCSE | RMSE |
|---|---:|---:|---:|
| Original plug-in | -.054293 | .005484 | .072961 |
| Oracle empty-cell fill, plug-in | -.005651 | .003602 | .032507 |
| Original DR | +.015802 | .010964 | .098721 |
| Oracle empty-cell fill, DR | +.016533 | .005999 | .055824 |
| Known population-Q initial-value average | -.008501 | .001015 | .012399 |

The last row is a separate known-law reference evaluated on the same initial
states, not a fitted full-history learner. Its mean error is close to the prior
population compression bias -.00872645; empirical composition varies across seeds.
The oracle-filled plug-in mean being closer to zero than that reference does not
show it is superior or remove representation bias: these are finite noisy means.

| Paired change, oracle fill minus original | Mean | Approximate 95% Monte Carlo interval |
|---|---:|---:|
| Plug-in estimate | +.048642 | [.040980, .056303] |
| Plug-in squared error | -.004267 | [-.005689, -.002844] |
| DR estimate | +.000731 | [-.014047, .015509] |
| DR squared error | -.006629 | [-.008984, -.004275] |

These intervals summarize the selected, reused 80-seed diagnostic, with seeds as
Monte Carlo units. They are neither real policy-effect intervals nor a fresh
confirmatory method comparison. Overlapping training folds/cells are not treated
as independent replications. No new coverage claim is made for the oracle variants.

## What was sparse, and why raw empty-cell counts are insufficient

All 80 replications and all 14,400 fold/stage/state/action cells were retained.
There are 318 empty fold cells; 2,372 cells have 1–4 training episodes and 2,403
have 1–4 distinct training roots. Empty-cell fractions across stages are 0%,
0.2292% and 6.3958%. At least one cell is empty in 78 of 80 replications; in the
two with no empty cells the plug-in substitution changes nothing.

The mean target-action mass falling in empty cells is 0%, .1103% and 2.3522%
across the three stages **under logger-generated eligible evaluation histories**,
with equal averaging over folds and seeds. This is not target-policy history
occupancy. In particular, that small descriptive percentage is not a bound on
initial-value distortion: fitting averages under different conditional distributions
and the backward recursion propagates changed continuation predictions. No target-
occupancy or formal error decomposition is claimed here.

The logger's action floor is positive. Empty empirical training cells and weak
finite-sample overlap do not establish a violation of population positivity.
Nonempty cells with few independent roots remain a separate unresolved concern.

## Validation, provenance and resource use

The [committed protocol](sparse_cell_diagnostic_plan_20260921.md) and config pin
all seeds and hashes of the simulator, estimators, original runner and records,
and known population-Q report. The runner verifies its committed script, plan,
tests and config before execution. Folds use the original RNG state immediately
after simulation; instrumentation draws no randomness and keeps roots together.
Reconstructed data and fold hashes are saved. The old study has no archived
array hashes, so exact original-array identity cannot be independently asserted.

All 80 original plug-in/DR means reproduce, maximum discrepancy 3.33e-16. A
separate array implementation has zero discrepancy from the original fitted
predictions and DR scores in this replay. Structural tests check STOP/terminal
recursion, wholly absent states, upstream propagation, absence of held-out outcome
leakage, and no-op substitution when all cells are observed. The full suite passed
233 tests and 8 subtests in 1.48 seconds before metadata/report-label edits;
the four affected tests passed again before the freeze. Test counts are software
checks, not empirical validation. Independent internal source/design review found
no blocker and required the logger-history exposure qualification above. A separate
standard-library audit of the saved records reproduced 51 numerical fields within
6.94e-18, verified all 80 seeds and all 10 pinned sources against the freeze, and
checked invocation/summary consistency. That review took .179 seconds, with no
resimulation or refitting.

[Manifest](../results/empty_cell_diagnosis_20260921/manifest.json),
[all seed/cell records](../results/empty_cell_diagnosis_20260921/replicates.jsonl),
[summary](../results/empty_cell_diagnosis_20260921/summary.json),
[process invocation](../results/empty_cell_diagnosis_20260921/invocation.json), and
[independent review](../results/empty_cell_diagnosis_20260921/independent_review.json)
provide the auditable artifacts. No old result was overwritten.

One CPU worker completed the report in 13.422 seconds internally, 14.273 seconds
including process startup, within the externally enforced 120-second cap. BLAS
thread counts were restricted to one. Artifacts were below the 10 MiB cap.
Receiver calls/tokens, candidate/reference executions, GPU use, installations and
paid spend were zero. There were 240 original fits and 480 array diagnostic fits
on regenerated old-seed data, not fresh independent observations. The overall
research/review wall time is not represented by the report runtime.

Reproduce into an unused output directory with the frozen sources and one-thread
numerical environment:

```bash
.venv/bin/python scripts/diagnose_empty_cells.py --out work/empty_cell_recheck
```

## Remaining discriminating work

The next statistical milestone is a prospectively frozen comparison of an
available adequate-history learner and explicit regularization against the
compressed learner, using identical root folds, target and DR corrections. It
must separate information/representation, finite fitting and overlap, and assess
precision beyond these selected reused seeds. Do not choose an estimator on this
diagnostic and call the same records independent validation. This is a design
requirement, not a newly launched grid or additional worker assignment.

Progress stays **49%, delta 0 points** under the fixed rubric. This narrows a failure
mechanism within existing diagnostic credit; it does not finish the learned-history
or final-precision milestone. Prompt efficacy remains unestablished and the full
project remains not submission-ready.
