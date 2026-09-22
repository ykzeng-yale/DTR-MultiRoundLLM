# Scientific judgment: what our negative results mean

**20 September 2026 — coordinating scientific agent.** I led this program's design and own its scientific interpretation. Delegating experiments does not transfer responsibility for the question, assumptions, metrics, comparators or decision to continue. The implementation audits were necessary, but my prior update put too much emphasis on another agent's errors and too little on what our design and actual negative findings teach us.

**Current decision:** keep the original personalized next-prompt question open, but pause generator training and expansion of the autonomous prompting system. The practical premise has not been established. Conduct one affordable, frozen experiment that can distinguish useful prompt choice from extra sampling, stopping and evaluator quality. Do not expand the program merely because its mathematical formulation is valid, and do not change targets until a positive result appears.

**New main reconciliation:** the experiments workstream has retracted its blanket STOP recommendation and proposed a compute-efficiency pivot. [Our adjudication](scientific_judgment_v2_pivot_20260920.md) accepts the retraction but finds that its power and certification arguments do not justify replacing the original question. The fixed-bank evidence remains descriptive; no harm certificate has been issued.

**Status cross-reference (22 September):** This dated judgment's scientific boundaries remain authoritative. Its then-pending threshold and instrument work are historical: the later [threshold ruling](worker_issues_resolution_20260921.md) sets a working five-point useful-gain threshold, and the [current portfolio](experiment_portfolio_review_20260922.md) distinguishes accepted finite instrument checks from the still-incomplete E12 receiver batch and independent policy validation. Preserve the dated findings below; they do not reopen completed validation or release another stage.

## 1. What is wrong, unsupported, or genuinely negative?

| Layer | Scientific diagnosis | Consequence |
|---|---|---|
| Foundational theory | Identification and DR identities are conditional statements. They do not imply positive feedback effects, observable treatment heterogeneity, good rankings, or superior decisions. Some later ESS/stopping/impossibility claims were incorrect and have explicit replacements. | Keep the valid estimand and identification theory; drop a narrative that causal adjustment itself must improve prompting. Additional standard proofs are not the current bottleneck. |
| Scientific sequence | I specified a history encoder, critic, adaptive selector and generator before establishing meaningful and predictable differences among supported prompts. Artifact-based handoff gates did not force that premise to be tested first. | Replace the architecture-first sequence with a bottleneck experiment and a real possibility of futility. This is my design responsibility. |
| Intervention/data | The available corpus randomizes receiver routing inside a largely fixed repair/check process. It is not a randomized comparison of next-prompt candidates under the proposed fixed-receiver continuation. | Reweighting can evaluate a supported fixed-receiver repair regime. It cannot manufacture absent prompt interventions or verify the original personalized-prompt hypothesis. |
| Controller/measurement | On 90 of 561 tasks there were no certified substantive visible assertions. A load-only pass was treated as an acceptance signal. The recorded outcome is full benchmark-test success, not our later hidden-only scoring split. | The current stopping process has a substantial uninformative-check defect. Preserve its measured performance, but do not interpret it as the intrinsic capability of LLM correction or silently rename the endpoint. |
| Statistical estimation | Earlier filtering, targets and truth calculations were wrong. Our corrected first E0 comparison still gave plug-in and DR different training fractions. A new matched-fit diagnostic isolates augmentation. | Repair the original estimand; do not treat a new bank size, population, scorer or cost budget as a statistical correction. |
| Actual repair performance | The repair loop produces real net improvement over the initial answer but less improvement than adaptive resampling at similar mean call counts. | This negative practical result survives the valid corrections. We should not explain it away as only a coding bug. Its exact mechanism and prompt-content generality remain untested. |
| Our positive selector result | The original 7B +2.85-point result was the most favorable of ten diagnostic splits. The median is only +.83 points. All are from reused, overlapping data. | Downgrade it to a modest, split-sensitive development signal; do not use 2.85 points as the expected benefit or evidence for multiround prompting. |

## 2. The repair policy helps, but an independent redraw helps more

The new analysis retains all 561 roots and 4,488 episodes. It evaluates the same fixed-receiver repair/check regime using known subsequent routing probabilities. Accepting the initial artifact is the common baseline.

For binary first/final outcomes and terminal likelihood weight W,

`mean(W*Yfinal)-mean(Yinitial)`

`= weighted repairs − weighted degradation + mean((W−1)*Yinitial)`.

The last term is sampling imbalance, not an answer improvement. Under sequential randomization, `E[W | first-artifact information]=1`. Consequently, `mean[W*(Yfinal−Yinitial)]` estimates the same policy contrast while avoiding needless reweighting of the observed first verdict. Because the initial artifact is sometimes graded after continuation, this also assumes its recorded grade is invariant to later routing and independent grader noise has the declared law. We have not newly tested that invariance. Both estimators are preserved; the analysis does not choose between them based on statistical significance.

| Population contribution | 3B | 7B |
|---|---:|---:|
| Gross repairs | +3.21 percentage points | +2.32 points |
| New errors introduced | −0.36 points | −0.71 points |
| Net gain over initial answer | **+2.85 points** | **+1.60 points** |
| Adaptive best-of-three gain over the same initial distribution | **+7.78 points** | **+3.31 points** |
| Repair minus resampling net gain | −4.93 points | −1.71 points |

The exploratory root intervals for the final row are [−6.60,−3.27] and [−3.18,−.23] percentage points under the paired-change estimator. The previous raw-IPW 7B interval crossed zero because it also includes baseline-weight noise; that result remains reported. This is an estimator sensitivity within one reused corpus, not a new independent trial. Mean calls are close but not identical; no exact matched-cost superiority claim is made.

For 3B, the deficit is mostly low repair yield: the repair process creates fewer correct artifacts than an independent redraw. For 7B, lower repair yield and damage to initially correct answers both contribute. Among initially wrong artifacts that the public check sends for repair, only about 16% are corrected. These are retrospective, regime-specific diagnostic rates; the hidden initial verdict cannot be used as an eligibility rule in deployment.

**What this does not resolve:** whether weak repair yield comes from feedback wording, misleading diagnostics, retaining an unproductive answer in context, insufficient receiver capability, or interactions among them. That distinction needs randomization of repair versus restart and prompt alternatives at the same prefix. The current log does not contain it.

## 3. A large part of the stopping problem is absent information

The measurement audit found 90/561 logged tasks with zero certified visible checks. These account for 720 episodes. Of 714 episodes that passed code-loading and stopped immediately, 424 failed the full benchmark tests. Those 424 cases account for 54.3% of the 781 initial visible-pass/full-test-fail disagreements.

This does not mean all remaining disagreements are software defects, or that a perfect verifier is available. It means our acceptance rule treated “no failing check” as “evidence of correctness” even when there was no substantive check at all. Passing a known correct reference certifies a limited property; it does not establish that a test detects wrong solutions. Zero detected hacks likewise gives no zero upper bound on outcome bias.

Approximately half of all initial failures are accepted by the public checker and never enter repair. The repair and resampling policies share this first acceptance signal, so it is a common performance ceiling, **not the complete explanation for their difference**. Changing the rule for zero-check histories would be a new policy. Because those histories were usually stopped, the log does not identify every outcome from continuing them. That improvement needs fresh execution rather than imputation.

The present outcome remains reproducible full-test pass under the recorded harness. It is a defensible benchmark endpoint with a specific interpretation, not semantic correctness on all inputs or human satisfaction. Our later hidden-only split changes that measurement target and must not be mixed into the old labels.

## 4. I stress-tested the positive result I had emphasized

Before running the new sensitivity analyses, the seed range and feature groups were recorded in `docs/scientific_diagnostic_plan_20260920.md`. Each fit uses the same logistic algorithm, four-candidate bank, 336/225-root split size and recorded full-test endpoint. No candidate programs were executed.

| Receiver | Original split | Median over ten splits | Range | Positive splits |
|---|---:|---:|---:|---:|
| 3B | −0.07 points | −0.76 points | [−2.63,+1.11] | 1/10 |
| 7B | +2.85 points | +0.83 points | [−0.11,+2.85] | 8/10 |

The test sets overlap; ten splits are not ten independent replications. Do not pool them into a confidence interval or a binomial test. The original split was fixed before its first result, but it was the most favorable in this diagnostic set. My earlier emphasis overstated how stable its magnitude was.

On the original split, the 7B public-check-only learner gives +.44 points, while code-structure-only and token-only learners perform worse than visible selection by 5.59 and 5.22 points. The full combination gives +2.85. These ablations show that structural/token proxies do not replace the public check; they do not identify causal contributions of features or prove the full combination will generalize. No feature set is promoted based on this post-hoc table.

All comparisons pay for four initial candidates, while the cheap sequential comparator usually stops around 1.3 calls. Thus even a reproducible fixed-bank gain would leave the practical budget question open and would remain separate from the original next-prompt treatment effect.

## 5. Does doubly robust estimation help when compared fairly?

Our new CPU diagnostic uses exactly the same fitted Q functions, training folds and target policy for plug-in regression and DR. Five conditions × 80 replications = 400 paired diagnostic runs. Seventy-nine base-condition seeds overlap the earlier corrected grid; this is reanalysis of those datasets, not 400 new independent datasets beyond the previous study. No cross-study pooling is used. The Q model is the same compressed (state,time) working model, which may omit consequential history. Recorded logging propensities are known. This does not claim to compare DR with every adequate full-history regression or to recover effects with unavailable confounding information.

| Condition | Plug-in RMSE | DR RMSE | Judgment |
|---|---:|---:|---|
| Base | .01546 | .01517 | Difference unresolved at this Monte Carlo precision |
| Uniform logger | .01219 | .01224 | Difference unresolved |
| Latent-dependent logger, known scores | .01450 | .01481 | Difference unresolved |
| Declared template mixture | .01506 | .01533 | Difference unresolved |
| Weak overlap | .07296 | .09872 | DR has greater estimated MSE despite lower absolute bias |

The paired squared-error difference in the weak-overlap condition is +.00442, with an approximate Monte Carlo interval [.00106,.00778]. DR reduces absolute empirical bias from .0543 to .0158 but increases variance enough to worsen overall error; its Wald coverage is .8125. That is a concrete bias–variance and overlap problem, compatible with the population DR identity. It does not mean the theorem is false, and theoretical consistency does not make this finite-sample estimator adequate.

In the other four conditions, paired MSE-difference intervals cross zero. Those cells provide no clear empirical reason to insist on DR for this task. A lower error in overall policy value would not itself prove better conditional ranking or better deployed prompting. The next learned-policy study must permit adjusted regression to win.

## 6. The scientific decision and the next discriminating experiment

**Stop expanding the generator/critic architecture for now.** There is no demonstrated chain from supported prompt variation to predictable ranking to worthwhile deployed policy gain. Continue only the smallest study that tests the missing link. The theory remains useful for defining and evaluating that study; it is not evidence that the study will succeed.

Use a fresh task/family set and one frozen receiver. From the same initial public history, compare generic repair, a frozen history-specific feedback candidate, and independent restart. Keep future continuation and the maximum number of calls fixed in the mechanism comparison; expose no hidden evaluation outputs. STOP is a separately named baseline so that improved stopping cannot masquerade as better prompt content. The candidate generator, feedback rendering and public information must be the same across the relevant selector comparisons.

First establish whether any supported prompt choice has a useful advantage over competent fixed/heuristic policies. Then test a frozen public-history selector against that comparator on independent roots. Use matched regression and DR learners as a secondary method comparison, not as a requirement that the causal-branded method win. Any later practical claim must also beat a declared independent-sampling controller at an explicit measured generation/checking/selection budget.

Clarification from the subsequent [landmark theory and experiment](landmark_premise_results_20260920.md): this is **not** a prerequisite test for a nonzero marginal arm effect. Opposite useful history-specific effects can cancel on average. The premise is useful, predictable choice, assessed by an independently evaluated frozen selector; sample-max branch outcomes also cannot establish that premise.

Before collection, fix the target population, scoring split, root/family unit, a practically meaningful gain, attainable precision, numerical resource cap, and success/futility/inconclusive rules. A five-point contrast in the original plan was a power illustration, not a retrospectively binding clinical-style threshold. The detailed [theory judgment memo](scientific_judgment_theory_20260920.md) proposes prospective rules; the actual threshold must be justified by the application's benefit and compute cost before launch. If adequate precision is unaffordable, report feasibility and uncertainty rather than changing the endpoint or searching another benchmark until a result wins.

A narrow negative against repair would stop that tested repair mechanism. A narrow negative for history-specific versus fixed prompting would stop personalization in that candidate/receiver/population regime. Similar regression and DR performance would remove the DR-specific superiority claim. A broad confidence interval is inconclusive. A failed measurement or support gate prevents an efficacy conclusion; it is not a license to discard inconvenient outcomes.

## 7. Ownership, status and audit trail

**23:24 UTC measurement follow-up:** The [versioned task-contract review](landmark_task_contracts_20260920.md)
finds a boundary defect in one of the seven previously retained references: MBPP/402
returns 1 when r=0,p=1, conflicting with the proposed positive-modulus contract.
This is source inspection, not an executed benchmark failure. I retain the original
reference, the task's identity and the intended domain; no replacement or silent
domain restriction is justified. Six other retained tasks remain unvalidated too.
Authored boundary tests and wrong controls improve the review proposal, but do not
establish measurement validity until executed in a validated environment. Changes
to public definitions and private suites are explicitly versioned development
targets. They do not invalidate or rescue the original repair results.

The coordinating scientific agent must approve the interpretation and advancement decision against the frozen estimand, irrespective of which agent wrote the code. The next handoff will specify the causal question, expected observation under competing explanations, falsification criterion and exact output needed. Experimental workers should report deviations and negative findings; they should not bear responsibility for defending a hypothesis we failed to formulate precisely.

**Full-project status:** not submission-ready; the original prospective personalized-prompt effect is still untested. This continuation improves diagnosis, not confirmed efficacy. The earlier 48% was a subjective artifact-planning score, not a scientific probability or validated readiness estimate. Proof/test counts should not substitute for the scientific gates above. No new LLM calls, GPU hours, external spending, or candidate-code executions occurred.

Evidence: [repair mechanisms](repair_mechanism_diagnosis_20260920.md), [measurement audit](measurement_judgment_20260920.md), [theory self-audit](scientific_judgment_theory_20260920.md), `results/selection_sensitivity_20260920/`, and `results/matched_estimator_diagnosis_20260920/`. The source data and every prior result remain unchanged. All positive, null and negative diagnostic comparisons are retained. The current automated suite passes 53 tests; independent code review found no blocking error in the matched-estimator diagnostic.
