# Continuation report: theory and experiment audit

**20 September 2026.** The work continued with a fresh repository audit, corrections, proofs and additional CPU experiments. The project remains **not submission-ready**. Its supported goal is history-conditional next-prompt value and policy evaluation; an individual conversation's unobserved causal effect is not identified.

## What was completed

- Added ten scoped theory results/propositions with proofs for full-rollout stopping, changed-policy weights, public-information optimal stopping, regret, censoring, candidate selection, finite-class evaluation, ESS and hidden state. Ten finite-law identity/counterexample checks pass.
- Repaired the E0 first-action weight, continuation-target comparison, template-mixture truth, false optimality label and replication accounting. Ran all **17 cells × 80 = 1,360 corrected replications**. A separate internal auditor ran 72 fitted-Q replications. Original 400-replication fixed-nuisance reference results remain a separate study.
- Independently reanalysed **4,488 existing real-model episodes / 561 tasks**. Retained first candidates from conversations that later switched receiver; evaluated the fixed-receiver repair regime with recorded routing weights. The earlier blanket “K1 fired on both models at lower cost” conclusion is withdrawn.
- Fit two public-feature selectors on 336 roots and evaluated on 225 roots, using four initial candidates per receiver/task. The 7B logistic fit improved recorded full-test success by **2.85 percentage points**, with an exploratory task interval **[1.19, 4.52]**. All four model/learner comparisons are reported; this reused corpus is not confirmatory.
- Rechecked ten load-bearing literature records. All identifiers were real, but several descriptions and novelty/possibility claims were wrong. CausalCollab and language-action DTR learning are direct predecessors. No “first causal conversation” or “first randomized LLM system” claim is made.
- **51 tests pass.** Newly added checks concern actual estimator, cohort, propensity, stopping and inference failures. All new work used local CPU, **zero new model calls, zero GPU hours and $0 external spend**.

## Findings that change the interpretation

The original routing comparison selected easier candidates by discarding conversations that later switched receivers. It also mixed different task denominators. After correction, resampling remains strong for 3B; the 7B result depends on sample count and cost. These are exploratory sibling routing-policy results, not randomized user-prompt effects.

The old E0 conditional-regression and IPW estimates did not always target the same continuation. Its state-only “optimum” was a heuristic, and its template-heterogeneity coverage used the wrong truth. In the repaired grid, weak overlap still yields poor Wald coverage (.8125 at 80 replications). Template variation alone does not break identification of an explicitly fixed template mixture. Fitted propensity robustness and precise final coverage calibration remain untested.

Full-rollout stopping evaluation has weight one only when the target uses the same continuation mechanism before stopping and the stop outcome is the recorded prefix utility. Complete prefix grades do not identify effects of untaken prompts. Naturally stopped routing logs cannot reveal missing suffixes. An ESS lower bound of 2.75 is not the actual effective sample size; a conservative certificate's failure is not a general impossibility theorem.

The new positive selection result concerns choosing among four already-generated answers. It supplies a reason to test that specific selector afresh, but does not establish multi-round feedback gains, a causal critic, prompt optimization, or an advantage over a cheaper early-stopping baseline. The exact feature schema and training procedure are frozen in the run manifest; the discovered unused assertion-category feature will be fixed prospectively, without quietly changing this result.

A further experiment-workstream update (`0ee7666`) arrived during this audit. Its new execution-agreement/allocation studies retain the same future-switch exclusions and add probe-usability selection; their proposed stop decision therefore needs the [latest audit](latest_selection_decision_audit_20260920.md). The oracle opportunity bound is valid for the same bank, but does not make only 33 roots the independent sample size or prove a research-wide impossibility. Its near-one-call allocation target also differs from the new four-call selector pilot.

## Remaining work, in order

1. **Accept the corrections and freeze one intervention design.** Reconcile candidate-first randomized selection with class-first generation; these have different laws and weights. Adopt the stopping assumptions and Q11 scope in the new theory reconciliation.
2. **Finish simulation precision and fair baselines.** Prespecify Monte Carlo precision; expand the corrected grid as needed and include correctly history-adjusted sequential regression for the same target. Fit propensities only if an observational-estimation claim is retained.
3. **Validate the selection lead on new tasks.** Audit family structure and visible/hidden separation, freeze the logistic/visible/BoN comparisons, and measure total generation/checking/selector cost. Compare four-candidate banks first; prespecify a separate matched-budget adaptive comparison.
4. **Collect actual prompt-intervention evidence.** With one pinned receiver, freeze a small exact candidate slate, randomize supported next prompts at restorable histories, and name the continuation policy. Record failures and assignment probabilities; use independent roots for evaluation. This is the missing experiment for the original personalized-prompt question.
5. **Only then train and evaluate broader regimes/generators.** Assess conditional calibration and supported policy improvement. A changed generator needs fresh data or a valid full generator likelihood ratio. Do not use local branches as a substitute for whole-policy target-history validation.

No paid service or additional model inference was launched: the informative next action was to repair and independently audit existing evidence. The prospective collection remains genuinely outstanding; it is not being presented as completed by this CPU continuation.

## Evidence map

| Artifact | Role |
|---|---|
| [Original theory](theory.md) and [new addendum](theory_addendum_20260920.md) | General prompt estimand and scoped stopping/selection proofs |
| [Theory reconciliation](theory_reconciliation_20260920.md) | Fourteen findings, replacements and Q11 resolution |
| [Corrected E0](e0_corrected_results_20260920.md) | Fitted-Q simulation results, MCSE and reproducibility |
| [Independent experiment audit](experiment_recheck_20260920.md) | Raw-log integrity, corrected routing values/costs and E0 audit |
| [Selection pilot](selection_corrected_results_20260920.md) | All four frozen-split fits and limitations |
| [Literature recheck](literature_recheck_20260920.md) | Primary-source links and corrected interpretation |
| [Execution handoff](experiment_handoff.md) | Ordered work packages and GitHub issue links |

This report and the updated PR are reviewable outputs, not evidence that another agent has accepted the handoff or that the manuscript is submission-ready.
