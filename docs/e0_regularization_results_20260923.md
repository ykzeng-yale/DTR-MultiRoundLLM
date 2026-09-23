# Bounded matched numerical diagnostic — 23 September 2026

**Decision: accept the preserved numerical accounting; retain the negative finite-sample diagnostic; the planned study remains incomplete. No automatic extension, tuning or new model stage.** This is fresh known-truth synthetic data under the [prespecified design](fitted_history_numerical_design_20260922.md), not a prompting or independent-policy experiment. Original empirical negatives remain unchanged.

## Frozen execution and independent checks

`LEAD-E0-REG-01`, run `e0_regularization_20260923_lead01`, used source commit `dfd462419df3824d7fff47fd44ad187fba6079b2` and committed execution freeze `b7bf51db4900e038affeaa999d5f9f6c1ab28103`. Python 3.14.4, NumPy 2.5.3, SciPy 1.18.1 and PCG64 and all 11 source pins were verified. Fresh local process/load/memory and documented-lease inspection preceded launch; it did not establish the separate experimental worker's host state. The fixed policy truth is 0.6459770061744536.

The one worker started at 10:46:47.820503 UTC and stopped by the predetermined time cap after 598.008174 seconds, reserving cleanup inside the 600-second ceiling. Saved supervisor evidence records SIGKILL/return code −9 with exit observed; the lead independently checked that both owned PIDs 2621/2645 were absent after completion. Exactly 117,307,339 bytes, including the 394-byte supervisor receipt, were retained under 268,435,456 bytes. No sampled job was resumed or replaced. All receiver/model calls, prompt/completion tokens, benchmark/reference/candidate executions and paid cost are zero. These zero model counts do not mean zero simulation: 433 datasets were generated from the predeclared sequence.

There are 432 complete datasets (144 per logging condition) plus uniform job 432 with three of four variants complete. All 4,800 planned estimator slots remain: **3,462 completed, 2 interrupted attempts, 1,336 unattempted**; there are no recorded terminal point or interval failures. The last two interrupted slots belong to uniform history/λ5. Thus uniform estimators have 145 completed datasets except history/λ5, which has 144 completed out of 145 attempts; base and weak-overlap each have 144 completed. There is no incomplete final JSONL fragment.

Independent saved-root arithmetic reproduces all 3,462 point estimates, 1,731 DR intervals, 24 estimator summaries and 36 paired comparisons; all 11 source pins and the original committed freeze bytes match. The [independent audit](../results/e0_regularization_independent_audit_20260923.json) passes with zero discrepancies beyond floating arithmetic tolerance. Its 73,746 checks establish saved-record consistency, not efficacy or inferential validity. The separate immutable [reconciler](../scripts/reconcile_regularization_journal.py) passed 22 handwritten-record tests (1.05s test time). Later read-only reconciliation took 4.648 s wall/4.154 s CPU, independent arithmetic 3.028 s/2.803 s, and support aggregation 2.498 s/2.454 s. These post-run analyses are reported separately from the bounded sampled run; no further draws or fits occurred.

## All eight point estimators

RMSE and bias below describe the returned time-truncated prefix. Weak-overlap coverage counts refer only to returned DR intervals. Every paired comparison and its actual denominator is retained in the [complete derived record](../results/e0_regularization_reconciled_20260923.json); the [compact table](../results/e0_regularization_metrics_20260923.csv) includes all 24 condition/estimator rows.

| Representation, penalty, method | Uniform RMSE | Base RMSE | Weak-overlap RMSE | Weak-overlap bias | Weak-overlap interval coverage |
|---|---:|---:|---:|---:|---:|
| compressed, λ=0, plug-in | 0.0131 | 0.0139 | 0.0631 | -0.0440 | — |
| compressed, λ=0, DR | 0.0131 | 0.0135 | 0.0715 | -0.0076 | 118/144 (81.9%) |
| compressed, λ=5, plug-in | 0.0169 | 0.0142 | 0.2526 | -0.2518 | — |
| compressed, λ=5, DR | 0.0130 | 0.0135 | 0.1110 | -0.0128 | 130/144 (90.3%) |
| history, λ=0, plug-in | 0.0334 | 0.0171 | 0.2760 | -0.2757 | — |
| history, λ=0, DR | 0.0130 | 0.0138 | 0.1378 | -0.0154 | 130/144 (90.3%) |
| history, λ=5, plug-in | 0.0838 | 0.0242 | 0.2902 | -0.2900 | — |
| history, λ=5, DR | 0.0130 | 0.0140 | 0.1376 | -0.0147 | 130/144 (90.3%) |

The negative finding is about our finite-sample design: a richer sufficient history representation and the fixed pooling rule did not automatically deliver better estimation. Under weak overlap, full-history raw plug-in bias was −0.2757, versus −0.0440 for compressed/raw. Pooling also worsened compressed plug-in bias to −0.2518. Under uniform logging, history plug-in bias was +0.0305 without pooling and +0.0827 with pooling. These are observed diagnostics, not a reason to erase negative runs or select a winner from the same data.

DR corrected much of these variants' observed plug-in bias but carried a variance penalty. Weak-overlap raw full-history DR RMSE was 0.1378 versus 0.0715 for compressed/raw; their paired mean squared-error difference was +0.013867 on 144 matched datasets. Compressed pooling increased DR RMSE to 0.1110 (paired squared-error difference +0.007201). Full-history pooling left DR RMSE similar (0.1376 versus 0.1378), which does not establish equivalence. The 12 prespecified paired comparisons per condition are descriptive and do not support multiplicity-controlled winner selection.

Weak-overlap returned-interval coverage was 118/144 for compressed/raw DR and 130/144 for the other three DR variants. Higher coverage accompanied wider intervals and greater error; it establishes neither calibrated 95% inference nor efficiency. For the partial uniform history/λ5 row, returned coverage 142/144 differs from operational covering/attempted 142/145. All planned, attempted, point-returned and interval-returned denominators remain separate.

## Support and an independently checked mechanism

The [saved support aggregation](../results/e0_regularization_support_20260923.json) makes sparse-history estimation a concrete concern. In weak overlap at the third turn, full-history/raw fallback occurred for 38.67% of held-out action queries versus 2.28% for compressed/raw, averaging the recorded fold-level frequencies. Observed full-history cells averaged 3.00 distinct training roots and 89.83% had at most 5 roots; compressed cells averaged 25.55 roots with 41.50% at most 5. These are pooled training-cell descriptors, not independent effective sample sizes. They support a sparsity/fallback explanation but do not isolate its causal contribution to total error.

Before reading outcomes, independent source review also checked the following exact STOP identity. In this synthetic law STOP seals Y=I{S_t=3}, and both representations retain S_t. For an observed training STOP cell, the recursion therefore gives q_cell=I{S_t=3}. Writing b for the effective fallback and m for distinct training roots, the fixed rule gives

    fitted_STOP_Q − I{S_t=3} = 5/(m+5) × (b − I{S_t=3}).

The same identity holds for an unseen cell, m=0. If training STOP rows are absent, b is the stage pseudo-outcome mean, or 0 for an empty stage; otherwise it is the action/stage STOP mean. Backward convex averaging keeps b in [0,1], so pooling weakly raises unsuccessful-state STOP values and weakly lowers successful-state values, with absolute error at most 5/(m+5). Under independent-root sampling and positive visitation of each fixed cell, m grows and this distortion vanishes; adding Monte Carlo replicates alone does not increase m. This is fitted-Q error, not automatically policy-value bias or DR bias, and it cannot by itself explain the raw-history failure.

## Scientific limits and next discriminating step

The planned 200 datasets per condition were not reached. A fixed time cap prevents outcome-based continuation but can still select a runtime-dependent prefix. The reported MCSE and pointwise binomial arithmetic do not establish the planned unconditional precision or population coverage for this incomplete run. Root-score interval validity, optimal regularization and practical LLM benefit remain unestablished. Both synthetic representations contain true quality state S, not a demonstrated observable LLM policy feature.

The first useful follow-up is a separately frozen design that distinguishes support/fallback effects from pooling of deterministic STOP, with a realistic computation/precision contract. Do not silently change the current estimator, rerun these seeds or expand the allowance. Same-target estimator corrections must remain distinct from changing the target or claiming prompt-policy improvement. E14 measurement delivery and untouched independent policy validation remain the primary experimental dependencies.

Large raw files are preserved locally in `work/e0_regularization_20260923_lead01`; published input hashes, derived slots, metrics and audits permit saved-summary checking, but raw dataset arrays were not archived and have not been regenerated. A portable full raw archive is not claimed. To reproduce reconciliation from that preserved directory, run the committed reconciliation utility with a NEW derived output path; its input files remain immutable.

Overall research completion stays **58%, change 0 percentage points** under the fixed rubric. This incomplete diagnostic advances the investigation within existing credit; it does not complete the planned numerical precision milestone. Prompt efficacy is unestablished and the full project is not submission-ready.
