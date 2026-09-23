# Saved-root concentration, support and logging weights

**LEAD-E0-CONC-01: post-result diagnosis of the closed 96-dataset STOP study.** This analysis retains all twelve DR variants, the original estimates and intervals, and every saved dataset. It adds no simulation draws, estimator fits, empirical LLM observations or inference procedure. The purpose is to distinguish observed score concentration, recorded nuisance support and logging-weight exposure, rather than assign undercoverage to any one mechanism from a correlation.

## Quantities and boundaries

For each dataset and method, let x_g be one of the 230 saved root-mean DR scores, d_g=x_g−mean(x), and S=sum_g d_g². The top-one and top-five shares are the largest one or five squared deviations divided by S; the positive share is sum_{d_g>0} d_g²/S. Root-score skewness uses central moments m3/m2^(3/2). These quantities are undefined when S=0. Ranking uses absolute centered contribution, with root-ID tie breaking. The derived file retains top-root IDs, scores and contributions; the pinned journal retains every original root vector. This is concentration of the recorded root-score dispersion, not a count of independent effective observations or an estimate of global target-policy occupancy.

For each archived episode, W_it is the cumulative product of 0.2/B_is over eligible stages through t. Inactive padding contributes no new factor and is not another observation in the stage summary. Each dataset's weights are shared by all twelve methods. Per-stage summaries retain active denominators, maxima and counts strictly above 10 and 100. Root loading L_g is the sum of its eligible cumulative weights divided by its 40 trajectories. Correlations of L_g with root scores and DR-minus-plug-in corrections describe co-occurrence. A large weight may multiply a small residual; weight exposure alone does not establish the cause of an estimator error.

Saved support has two different partitions. Observed versus unseen training cells partition queries by availability. Structural, cell, action-pool, stage-pool and zero sources partition effective predictions. Sum numerators and denominators across folds, separately by stage and STOP/non-STOP; do not add the two partitions together. Structural STOP values do not manufacture observed cells. These queries follow logged active histories and are neither an ESS calculation nor validation of the target-policy history distribution.

Across datasets, grouping by the original below-truth, covering or above-truth intervals is a post-result description. It is not an independent test, new stopping rule, threshold search or basis for discarding a dataset. Shared cross-fitted nuisances may induce score dependence. An absent rare positive contribution cannot appear in that dataset's concentration statistic, so low observed concentration would not by itself refute a rare-event explanation. The target, original intervals and negative findings remain unchanged.

## Results

All twelve methods retain 96 datasets and 230 root scores per dataset. The table reports medians across datasets; it is not an additional coverage experiment.

| Representation | Penalty | STOP mode | Top-one share | Top-five share | Positive share | Root-score skewness |
|---|---:|---|---:|---:|---:|---:|
|compressed|0|original|0.5888|0.9356|0.7058|4.9570|
|compressed|0|evaluation only|0.5857|0.9356|0.7058|4.9570|
|compressed|0|recursive|0.5861|0.9356|0.7058|4.9570|
|compressed|5|original|0.3949|0.9632|0.9643|7.6899|
|compressed|5|evaluation only|0.4004|0.9654|0.9673|7.8159|
|compressed|5|recursive|0.4001|0.9649|0.9673|7.8186|
|history|0|original|0.3789|0.9742|0.9681|7.7661|
|history|0|evaluation only|0.3881|0.9764|0.9763|8.1701|
|history|0|recursive|0.3865|0.9760|0.9762|8.1749|
|history|5|original|0.3767|0.9709|0.9672|7.6583|
|history|5|evaluation only|0.3804|0.9758|0.9758|7.8628|
|history|5|recursive|0.3793|0.9745|0.9752|7.8632|

For full-history penalty-five original, five roots account for a median 97.09% of centered squared deviations; the positive share is 96.72% and within-dataset root-score skewness is 7.658. In the eleven datasets whose original intervals lie below truth, the median top-one share is 86.50% and median SE is 0.06361. In the 85 covering datasets these are 37.44% and 0.15529. These group differences describe the retained data; they do not prove that concentration caused the failures.

The direction is not universal. For compressed unpenalized original, the median top-one share is 19.06% in the thirteen below-truth datasets and 62.29% in the 81 covering datasets. The two above-truth datasets have a median top-one share of 14.47%. A single monotone concentration explanation is therefore not supported across methods. The full derived file retains every variant and group, including empty above-truth groups.

The shared archived weights have the following counts. A stage number here starts at one; the machine record uses zero-based indices.

| Stage | Eligible episode-stage records | Largest cumulative weight | Weight >10 | Weight >100 |
|---|---:|---:|---:|---:|
|1|883,200|9.97384|0|0|
|2|231,457|99.40641|8,651|0|
|3|140,743|990.04822|7,544|600|

These are records from the same 96 datasets, shared across twelve methods; multiplying the counts by twelve would double-count exposure. The uniform target and logging floor permit the loose stage-three bound 1,000, but a possible or observed large weight does not establish a large residual. Differences among methods require their nuisance predictions and residuals as well. The diagnostic holds the logging law and all saved data fixed.


At stage three, the 562,972 logged non-STOP action queries include 13,493 unseen training cells (2.40%) for compressed fits and 206,978 (36.77%) for full-history fits. These are pooled query-count fractions across folds and datasets, not independent-sample proportions or target-history probabilities. Observed support is identical across penalties and STOP modes within each representation; full-history unseen counts are never below compressed counts on the matched queries. Effective prediction-source counts are recorded separately. The median within-dataset correlation of root DR-minus-plug-in correction with shared loading L is 0.239 for compressed unpenalized original, 0.794 for history unpenalized original, and 0.843 for history penalty-five recursive. The complete artifact retains all twelve methods rather than selecting these examples as winners.

The saved-data evidence therefore identifies substantial score concentration, rare large logging weights and sparse full-history queries as co-occurring features. It does not isolate which causes undercoverage, and does not validate weighting, trimming, pooling or interval tuning as a remedy. All 264,960 recorded root corrections satisfy the checked absolute-correction envelope relative to L; this arithmetic check is not a general theorem or inference certificate. A next saved-data discriminator is an auditable stage-wise residual/correction decomposition using the retained nuisance/support records, if those records suffice without refitting. Any proposed inferential change would still require a new declared validation design.

## Validation, provenance and resources

The [compact machine-readable summary](../results/e0_stop_anchor_concentration_summary_20260923.json) retains all 1,152 method–dataset metric records, all 96 shared weight-stage records and all twelve method summaries. The detailed 7,254,501-byte artifact is stored under ignored `work/e0_stop_anchor_concentration_20260923.json`, with its hash recorded in the summary; the pinned raw journal and 96 archives retain all original root means and arrays. This keeps the large derived detail out of Git without dropping a method or dataset from the published metrics.

The reader verifies the exact journal (101,897,293 bytes; SHA256 `980de970926ed17a819eb9c87fbf9db164d39af94fb1b333e6877117630f0928`), every archived dataset byte hash, the saved array/fold fingerprints, complete job/variant order and saved mean/SE arithmetic. The lead's separate stdlib score calculations and independent array-weight calculations agree in **34,752 comparisons**; **7,488 support-invariant checks** also pass. All fifteen original execution-source files remain byte-identical. These checks preserve the previous source/run validation boundary and do not independently observe the old live process or establish root independence.

Independent source and mathematical review accepted the diagnostic and its handwritten fixtures. **22 focused tests pass** in 0.18 seconds of test time (0.418 seconds command wall, 0.286 seconds child CPU). The all-method reader used 3.048 seconds command wall and 2.996 seconds child CPU, within one CPU thread /60 seconds /10 MiB. Separately computed root metrics used 1.441 seconds within Python and weight arithmetic about 2.25 seconds; comparison and preservation checks are timed in the [validation record](../results/e0_stop_anchor_concentration_validation_20260923.json). The latter also records output hashes and the byte-preserving move into `work/` after the reader completed. Zero new datasets, estimator fits, model calls, prompt/completion tokens, benchmark program executions or paid dollars.

Reproduce the full diagnostic at a fresh output path using the existing environment and original saved run:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
.venv/bin/python scripts/diagnose_stop_anchor_concentration.py \
  --run-dir work/e0_stop_anchor_20260923_lead01 \
  --out work/e0_stop_anchor_concentration_review_copy.json
```

The caller must enforce the same 60-second process limit; the command itself is an offline reader, not a study runner. It refuses an existing output, a changed journal/archive, missing or mismatched variants, malformed partitions and output above 10 MiB. Its source is independently reviewed; no estimator or sampler is imported.

## Scientific decision and coordination

**Accept this descriptive diagnosis; the causal explanation of undercoverage remains inconclusive. Hold calibrated-inference claims and new collection.** No original estimate, interval or negative empirical finding changes. Research completion remains **58%, change 0 percentage points** under the fixed rubric: this work refines existing numerical/manuscript credit and adds no independent policy evidence. Efficacy remains unestablished and the full project is not submission-ready.

MRL-24 remains a separate pending source/mock repair request to the existing experimental worker. At the first actual review without its acknowledgement, last-seen and independently reviewed worker source remain `18797b7ab593bd569522ad35a905d640a67b22cb`. Publication of the lead ruling does not establish a worker start or deadline. No new recovery escalation, duplicate collection or empirical permission is added. The primary next project milestone remains the repaired same-prefix E14 package and its independent review before instrument validation, followed eventually by independent frozen-policy evaluation.
