# Closed STOP-anchor mechanism diagnostic — 23 September 2026

Decision **LEAD-E0-STOP-01**; scientific review completed 2026-09-23T14:37:20.961223+00:00. Coordinating scientific lead, Yukang Zeng.

**Accept the completed synthetic diagnostic; hold advancement to a new stage.** Recursive STOP anchoring did not demonstrate lower DR error in the prespecified primary comparison. Preserve the adverse plug-in result and unresolved interval calibration. The single numerical allowance is closed: no repeat, resume, replacement seeds or additional collection. This conclusion does not concern prompt efficacy.

## Target and evidence classification

This is a new, post-result synthetic weak-overlap mechanism study motivated by the earlier [time-capped regularization diagnostic](e0_regularization_results_20260923.md). Its protocol and source were committed before these new draws. It is not completion or confirmation of that earlier three-logger study, an empirical LLM experiment, or independent prompt-policy validation.

The fixed uniform-five-arm policy value is **0.6459770061744536** under the declared finite synthetic law. Each of 96 datasets contains 230 roots with 40 trajectories per root and three opportunities; weak logging uses kappa 2.5 and floor .02, with effect 1 and zero gz, mislabel and template-SD parameters. Root-level folds, datasets, assignment probabilities and the target are matched across two representations, penalties 0/5 and three STOP modes. Both representations use true correctness state, which is not established as an available LLM-policy input.

Original fitting, evaluation-only STOP adjustment and recursive anchoring are distinct interventions on nuisance estimation. Evaluation-only adjustment reuses the original Q fits and changes the STOP query; recursive anchoring also changes backward targets and upstream fits. Reuse does not make the evaluation-only method free as a standalone estimator. Plug-in and DR share each variant's Q sequence. Twelve sequences yield 24 point estimators per dataset; no method was selected or tuned on the reported outcomes.

## Complete results

All **96/96 datasets and 2,304/2,304 estimator slots completed**. All 1,152 DR intervals returned; no failed, interrupted, missing or unattempted slots, truncated tail, replacements or retries. All 96 actual data/fold archives are retained locally. Point metrics and coverage each use all 96 datasets. The coverage target is nominal 95%; these empirical proportions do not establish calibrated inference.

| Representation | Penalty | STOP mode | Plug-in RMSE | DR bias | DR RMSE | DR covering intervals | Mean DR interval width |
|---|---:|---|---:|---:|---:|---:|---:|
| compressed | 0 | original | 0.058848 | +0.007550 | 0.081243 | 81/96 | 0.267256 |
| compressed | 0 | evaluation only | 0.058848 | +0.008345 | 0.080448 | 81/96 | 0.265575 |
| compressed | 0 | recursive | 0.059022 | +0.008339 | 0.080437 | 81/96 | 0.265569 |
| compressed | 5 | original | 0.254384 | -0.002820 | 0.126696 | 82/96 | 0.457138 |
| compressed | 5 | evaluation only | 0.263465 | -0.001322 | 0.127480 | 82/96 | 0.454797 |
| compressed | 5 | recursive | 0.281718 | -0.001254 | 0.127525 | 82/96 | 0.455365 |
| history | 0 | original | 0.277540 | -0.013863 | 0.151754 | 84/96 | 0.551595 |
| history | 0 | evaluation only | 0.277540 | -0.013156 | 0.153991 | 83/96 | 0.547880 |
| history | 0 | recursive | 0.311914 | -0.013408 | 0.154207 | 83/96 | 0.548902 |
| history | 5 | original | 0.292711 | -0.009076 | 0.151397 | 85/96 | 0.561245 |
| history | 5 | evaluation only | 0.301818 | -0.008432 | 0.153240 | 84/96 | 0.560466 |
| history | 5 | recursive | 0.357010 | -0.008138 | 0.154046 | 84/96 | 0.563496 |

The prespecified primary contrast is **history, penalty 5, recursive DR minus original DR**, paired within dataset. Its mean squared-error difference is **+0.0008091932**, with Monte Carlo SE **0.0006292854**, from all **96 matched pairs**. Positive differences favor the original estimator. DR RMSE changed from **0.151397 to 0.154046**; covered intervals changed from **85/96 to 84/96**. The result supplies no demonstrated benefit and does not establish harm or equivalence.

The frozen MCSE threshold of .005 is met arithmetically, conditional on treating the simulated datasets as independent. This is a precision diagnostic, not an efficacy, useful-gain, significance or futility criterion; it does not certify power for smaller effects. Completing every planned dataset removes time-truncation from this run, but distinct deterministic PRNG inputs and hashes are not a proof of stochastic independence. All 24 prespecified paired comparisons, including secondary comparisons, are retained in the [reconciliation](../results/e0_stop_anchor_reconciled_20260923.json) and [independent arithmetic audit](../results/e0_stop_anchor_independent_arithmetic_20260923.json). No multiplicity-adjusted winner or simultaneous benefit claim is made.

The matched full-history penalty-five plug-in RMSE increased from **0.292711 to 0.357010** under recursive anchoring. Thus correcting a known deterministic action value does not suffice to improve the complete fitted estimator in this setting. Compensating prediction errors and propagation through sparse non-STOP predictions are hypotheses requiring saved-support/Q analysis, not established causes. Compressed unpenalized DR changed from 0.081243 to 0.080437, a small secondary difference that does not justify selecting a method after inspecting the comparison grid. Neither richer history nor fixed pooling is rescued by STOP anchoring here.

DR coverage ranges from **81/96 to 85/96** across the twelve variants. For history penalty-five original, all 11 misses lie below truth; recursive has 12 below and none above. Original RMS reported SE is **0.150917**, close to the empirical SD **0.151918**, despite undercoverage. A simple scalar SE shortfall is therefore not established as the explanation. Cross-fitted scores need not be independent; sample covariance identities and point consistency do not validate root-score intervals. Pointwise binomial limits in the reporter require their stated iid-replicate assumption and are not simultaneous inference over methods; their endpoints were not separately recomputed by the stdlib auditor.

## Execution, immutable provenance and accounting

- Run: `e0_stop_anchor_20260923_lead01`, **14:23:06.834501–14:28:49.652625 UTC** on 23 September 2026.
- Source commit: `1fa0dbe6fcc2935911d15f391a3397cf3af9f626`. Execution-freeze commit: `031c5db92674bfffe576fc83d4ea1d502614ffa6`. [Committed freeze](e0_stop_anchor_execution_freeze_20260923.json) binds all 15 source/plan/seed files and Python 3.14.4, NumPy 2.5.3, SciPy 1.18.1, PCG64.
- Plan SHA256: `05de997cb4ddb20d8c7a6699ff314dcd8545825a6e5c42be8bcd235bc46c95b5`; exact-input table SHA256: `4585c96be1f3cdaa8c8a7f4d64c5665fc0bba480196e314cfef8976ed7c00e9c`. All 192 decimal input strings were reserved before draws and exclude the 1,200 earlier reserved inputs.
- Fresh resource/lease inspection at **14:22:50.392626 UTC**, 16.544 seconds before launch, on `YukangdeMacBook-Pro.local`; one CPU numerical worker/thread, available local headroom, no conflicting local lease identified. This does not verify a remote worker's scheduler or process state.
- External end-to-end runtime, including final receipt persistence: **342.814138 seconds**, below 600. Saved supervisor runtime: 342.775710 seconds; owned numerical child CPU: 339.357680 seconds. External child-tree CPU, which includes supervisory overhead, is 351.095477 seconds; it is not an additional inference allowance.
- Raw output: **179,658,373 bytes**, below **268,435,456 bytes (256 MiB)**. There were 96 sampler attempts, 1,152 variant sequences and 2,304 completed backward-fit attempts; evaluation-only variants reuse fitting. Reported complete-job totals (332.025852 wall seconds; 329.412799 CPU seconds) fit within the containing process receipts.
- Supervisor observed normal child exit, return code 0, no signaling errors. Health was monitored during collection; outcome analysis began after closure.
- **Zero model calls, prompt/completion tokens, benchmark executions or paid dollars.** These 96 new synthetic datasets and tabular fits are numerical work, not fresh LLM observations.

Immutable raw artifacts remain in gitignored `work/e0_stop_anchor_20260923_lead01/`; this local archive is not a remotely published raw-data bundle. The derived reconciliation publishes every raw path, size and SHA256, plus all planned identities/statuses and comparisons. The journal SHA256 is `980de970926ed17a819eb9c87fbf9db164d39af94fb1b333e6877117630f0928`. Full raw arrays can be rechecked locally without repeating the experiment. The older frozen numerical run remains untouched.

## Independent validation and limits

The frozen closed-run reconciler passed in **4.392041 seconds** (4.026382 CPU seconds), checking exact release provenance, 15 source pins, actual NPZ arrays/folds, all planned status records and saved-root arithmetic. A separate stdlib-only auditor, importing no estimator/journal/reporter arithmetic, passed in **3.157213 seconds** (3.049977 CPU seconds). It independently recomputed all **2,304 root means, 1,152 DR SEs/bounds, 24 paired summaries and 2,304 aligned sample variance/covariance identities**, with explicit tolerances and unchanged before/after raw hashes. Its 25 handwritten-data tests passed in .13 seconds (.363750 command wall, .255103 CPU). Both sets of checks are post-collection analysis, not additional sampled datasets or estimator fits. [Validation and timing receipts](../results/e0_stop_anchor_numerical_validation_20260923.json).

Independent theory and evidence reviewers accepted the auditor's formulas and scientific interpretation. Saved scores were checked rather than independently refitted; the simulator was not replayed, and neither independence nor interval calibration was proved. All 15 execution-source hashes still match after the audit. Source acceptance and arithmetic reproducibility are distinct from scientific efficacy.

## Next discriminating action and project boundary

Use the existing closed records for a bounded studentized-error/tail and SE–error association analysis, then compare saved STOP/non-STOP support and upstream Q changes if needed. This can narrow competing calibration explanations without new draws, refits, seed replacement or tuning. No automatic extension follows the coarse precision pass.

E14 measurement-package delivery remains unverified under the existing MRL-23 recovery; this lead-owned diagnostic neither replaces the same-prefix prompt-choice question nor assigns the worker another job. Independent prompt-policy validation remains unexecuted. Overall research completion stays **58%, change 0 percentage points** under the fixed rubric: this diagnostic refines existing numerical/manuscript credit but does not establish broad calibration, prompt efficacy or full-project submission readiness.
