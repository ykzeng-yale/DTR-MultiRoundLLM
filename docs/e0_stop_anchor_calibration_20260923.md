# Saved-error calibration diagnosis — 23 September 2026

**LEAD-E0-CAL-01: accept the descriptive diagnostic; the cause of undercoverage remains inconclusive. Hold calibrated-inference claims and new collection.** This lead-owned analysis reuses the closed 96-dataset STOP study. It changes neither the target, estimator, scoring rule nor original confidence intervals. No new simulated dataset, estimator fit, model call or benchmark execution is involved.

## Question and analysis scope

The [completed STOP study](e0_stop_anchor_results_20260923.md) reports only 81–85 covering intervals out of 96 for nominal 95% DR intervals. The full-history penalty-five original estimator has RMS reported SE 0.150917 and empirical error SD 0.151918. Close marginal second moments do not establish a correct distribution for the studentized error, dataset-specific standard errors or valid normal intervals.

This post-result diagnostic retains all twelve DR variants and all 96 datasets per variant. For each estimate define error e=estimate−0.6459770061744536, reported standard error s, and studentized error z=e/s. The summaries report sample SD with denominator 95, central-moment skewness m3/m2^(3/2), Pearson error–SE and absolute-error–SE correlations, linearly interpolated quantiles and the original lower/upper miss counts. These are descriptive summaries of reused simulation output, without p-values, winner selection, threshold tuning or additional independent observations.

Two further checks keep the estimate centers fixed:

1. Replace each reported s by the RMS(s), or sample SD(e), computed from these same96 datasets. The resulting fixed-width counts are **hindsight diagnostics unavailable in an ordinary single dataset**, not proposed replacement intervals or validated coverage. Widths are not nested: a net increase in covering records need not mean only rescues with no losses.
2. Evaluate all 96×96 ordered pairs of saved errors and standard errors, including the diagonal. The product-empirical covering fraction is (1/9216) sum_ij 1{|e_i|≤1.96s_j}; lower/upper failures use e_i<−1.96s_j and e_i>1.96s_j. This preserves both empirical marginals while removing their observed pairing. It is **not 9,216 independent trials, a randomization test, new simulation data, a deployable interval or a causal intervention**.

## Results and interpretation

| Representation | Penalty | STOP mode | Error–SE r | z skewness | Mean SE² / error variance | Original cover /96 | Re-paired cover % | Hindsight RMS-width cover /96 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| compressed | 0 | original | 0.3568 | -1.7822 | 0.9214 | 81 | 77.75 | 91 |
| compressed | 0 | evaluation only | 0.3716 | -1.7962 | 0.9347 | 81 | 77.54 | 91 |
| compressed | 0 | recursive | 0.3718 | -1.7941 | 0.9349 | 81 | 77.54 | 91 |
| compressed | 5 | original | 0.8963 | -3.9702 | 0.9363 | 82 | 86.78 | 89 |
| compressed | 5 | evaluation only | 0.9082 | -4.2241 | 0.9160 | 82 | 86.49 | 90 |
| compressed | 5 | recursive | 0.9081 | -4.2215 | 0.9176 | 82 | 86.46 | 89 |
| history | 0 | original | 0.9313 | -5.2443 | 0.9569 | 84 | 87.60 | 90 |
| history | 0 | evaluation only | 0.9477 | -4.9088 | 0.9195 | 83 | 86.58 | 90 |
| history | 0 | recursive | 0.9475 | -4.9089 | 0.9205 | 83 | 86.70 | 90 |
| history | 5 | original | 0.9280 | -5.0180 | 0.9869 | 85 | 88.21 | 89 |
| history | 5 | evaluation only | 0.9471 | -4.8319 | 0.9638 | 84 | 87.36 | 90 |
| history | 5 | recursive | 0.9469 | -4.8030 | 0.9634 | 84 | 87.30 | 89 |

For full-history penalty-five original, error–SE correlation is 0.9280, raw-error skewness +0.3516 and studentized-error skewness −5.0180. All 11 original misses lie below truth. For recursive anchoring the correlation is 0.9469 and studentized-error skewness −4.8030, with all 12 misses below truth. The original studentized-error .025 and .975 quantiles are−8.4451 and1.4123. Across-dataset error skewness and within-dataset root-score skewness are different quantities; the latter is not measured here. Neither a nonzero studentized-error mean nor its skewness refutes mean validity of the unstudentized DR estimator.

The exact re-pairing result limits a tempting explanation. Original full-history penalty-five coverage is85/96 (88.54%); re-pairing gives 8129/9216 (88.21%), with 532 lower and 555 upper failures. Recursive coverage is 84/96 (87.50%); re-pairing gives 8046/9216 (87.30%), with 558 lower and 612 upper failures. The directional imbalance changes markedly while the total failure fraction remains similar. Thus removing observed pairing does not restore nominal coverage in this empirical distribution. Strong signed association is not a sufficient explanation of total undercoverage.

For compressed unpenalized fits, re-pairing lowers the covering fraction from 81/96 (84.38%) to 7165/9216 (77.75%) for original and 7146/9216 (77.54%) for recursive. This further cautions against a single explanation for all variants. Hindsight constant RMS widths yield 91/96 for those two methods, versus 89/96 for both full-history penalty-five variants; these counts do not validate any data-dependent interval repair.

## What the implementation can and cannot explain

The estimate and its SE are computed from the same 230 root means. A rare large positive root score can raise both the mean and sample dispersion; a dataset without such scores can have both a lower estimate and a smaller SE. The DR score multiplies residuals by cumulative target/logging ratios. Under this fixed law, the uniform target probability .2 and logging floor .02 imply a loose three-step ratio bound of1000. These source facts provide possible finite-sample mechanisms, not proof of their role in the observed failures; negative extremes are possible too.

Compressed and full-history fits use the same policy, datasets, known assignment probabilities and root folds. History refines state-only cells, increasing the potential number of sparse or unseen queries, while penalty-five pooling and fallback alter predictions and backward targets. Actual support frequencies, extreme weights and root-score concentrations must be examined before assigning the failure to sparsity, nuisance propagation or rare weighted events. Shared nuisance fits also allow cross-fold score dependence. Neither the mean-valid known-assignment argument nor the current covariance identities certify n = 230 normal-interval calibration.

## Validation, cost and provenance

The [machine-readable diagnostic](../results/e0_stop_anchor_calibration_20260923.json) retains all **1,152 matched error/SE/z records** from twelve methods ×96 datasets, with formulas, exact input hashes and every method summary. The re-pairings are derived combinations of these same records, not additional observations. Inputs are the immutable [closed-run reconciliation](../results/e0_stop_anchor_reconciled_20260923.json), SHA256 `2f5fee670034389e619e2b8a79eb716456ef39ee50b7fb28c94f785c346cdbd8`, and [independent root-arithmetic audit](../results/e0_stop_anchor_independent_arithmetic_20260923.json), SHA256 `9660c45af75e5915ac664ecd50c39f7586c9b502904724d9e982cc598d749bde`, published at `1d26e9f96df34f6ee0ba1defe021bd493c17a0da`. Their bytes remained unchanged. Raw-array/source/exit validation is inherited from those audited records; this analysis does not repeat or expand that claim.

A separate stdlib diagnostic imports no estimator or production statistics helpers. Independent mathematical review accepted its formulas and limitations. All **32 handwritten-data tests pass** (.35 seconds test time; .662075 seconds full command wall; .500456 CPU seconds). The single all-method saved-summary analysis took **.135963 seconds full command wall** and .110494 CPU seconds, producing **364,668 bytes**, within one CPU/60 seconds/10 MiB. The parent independently checked four specified original/recursive history-penalty-five and compressed-unpenalized variants using separate formulas and Python statistics functions: **68 comparisons agree** within1e-12. The preliminary independent computations took .042178 and .011660 seconds within Python, and their final comparison .006582 seconds; these timings exclude interpreter startup and are separate from the all-method command time. All fifteen frozen execution-source hashes remain unchanged. [Validation and resource record](../results/e0_stop_anchor_calibration_validation_20260923.json).

Zero sampled datasets, estimator fits, model calls, prompt/completion tokens, benchmark executions and paid dollars. This is post-result reused-data diagnosis, not fresh performance evidence or prospective confirmation. No new interval procedure, collection permission or independent-policy credit is created.

## Next milestone and project boundary

The smallest next numerical discriminator is a bounded read-only inspection of saved root-score concentration, recorded support and archived logging weights, linked by the existing dataset/fold identities. It should preserve every method and failure; no refits, draws, seed replacement, interval tuning or new execution release follow from this memo. Independent future validation would be required for any proposed inference repair.

MRL-23/E14 delivery remains unverified; the original same-prefix prompt-choice and independent-policy questions remain authoritative. The existing recovery is not repeated or renewed. Research completion remains 58%, change 0 percentage points under the fixed rubric. This diagnostic narrows interpretation within existing numerical/manuscript credit; prompt efficacy remains unestablished and the full project is not submission-ready.
