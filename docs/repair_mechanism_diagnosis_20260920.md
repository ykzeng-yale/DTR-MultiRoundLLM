# Why the repair loop improves answers but loses to resampling

Date: 2026-09-20. Status: executed analysis of the immutable 4,488-episode routing log; no new receiver calls or candidate-code execution. This is our scientific diagnosis of the measured policies, not an attribution of the result to another workstream. It distinguishes genuine negative evidence from earlier analysis defects.

**Judgment:** the tested multi-turn policy does improve on accepting the initial answer. Its main practical weakness is that the public check stops approximately half of initially wrong answers before repair, and the repair process fixes only about one sixth of the wrong answers that it actually tries to repair. Independent resampling produces more repairs at a similar average number of model calls. For the 7B receiver, unnecessary revisions also erase a material share of the repairs. These facts support a strong resampling baseline and a better public-information controller; they do not establish that feedback content is inherently useless, that every prompt policy fails, or that the whole research direction should stop.

## Population, estimand, and independent units

Source: sibling repository `results/code_routing/log/episodes.jsonl`, SHA256 `e643ee44c7ef658fff65efb5e17763ee78c990d21184d060f5823025a100414e`. All 4,488 episodes are retained: **561 root tasks × 4 initial draws × 2 receivers**. There are 407 MBPP and 154 HumanEval roots. No later-routing, success, empty-code, or probe-availability filter is used. Source integrity and randomization were independently checked in [the experiment recheck](experiment_recheck_20260920.md).

The policy holds the initial receiver fixed and uses that same receiver for every subsequent eligible repair call. It retains the executed public-check stopping rule and the source repair prompt. The experiment permits up to three receiver calls: the initial answer and up to two repairs. Initial receiver assignment is blocked, so estimates condition on it. Subsequent logged routing probabilities are known and equal .5.

The baseline accepts the initial artifact. Its recorded verifier outcome is `Y0`; the executed episode's final verifier outcome is `YT`. These are the source benchmark verdicts, not a newly regraded hidden-only outcome or a measure of human satisfaction. The terminal importance weight is

`W = product over subsequent eligible calls {1(receiver equals initial receiver)/b_obs}`.

Switching episodes remain in the average with zero terminal weight. Early-stopped episodes have weight one. At most two subsequent decisions give weights in `{0,1,2,4}`. Each root contributes the mean of its four episode scores, and the 561 root scores are equally averaged. Confidence intervals use root-score standard errors; ratio intervals use the delta method over roots. They are exploratory, unadjusted, benchmark-root repeated-sampling intervals. Related task families may require a larger independence cluster, and the already analyzed corpus is not a new confirmatory holdout.

## Separate changes in the artifact from weighting imbalance

For binary outcomes, the following is an exact finite-sample identity:

`mean(W*YT) - mean(Y0)`

`= mean[W*(1-Y0)*YT] - mean[W*Y0*(1-YT)] + mean[(W-1)*Y0]`.

The first term counts weighted repairs, the second weighted degradation, and the third is baseline-weight imbalance. It is important not to interpret the third term as improvement in an answer.

The first artifact is sometimes graded after the episode. The argument below assumes its grader outcome/distribution is invariant to subsequent routing, with grading randomness independent of later assignments given the initial artifact. Recorded timing alone does not prove that baseline-measurement condition; no new regrading or invariance experiment was executed. This is an explicit consistency assumption, not a detected violation.

Under the recorded sequential randomization and consistent stopping outcomes, the likelihood-ratio martingale gives `E[W | first-artifact information] = 1`. Therefore `W*(YT-Y0)` is an unbiased paired-change/control-variate estimator of the same fixed-receiver policy contrast with accepting the initial answer. Equivalently, `Y0 + W*(YT-Y0)` estimates its final value. This replaces the unnecessarily reweighted initial verdict with its observed value; it does not change the target policy or use the hidden verdict to choose an action. Both versions are reported, since the distinction matters in this finite sample.

| Contribution to population success | 3B | 7B |
|---|---:|---:|
| Initial success | .60027 | .70856 |
| Weighted repairs | +.03209 [.01835, .04582] | +.02317 [.01228, .03406] |
| Weighted degradation | −.00357 [−.00850, +.00137] | −.00713 [−.01410, −.00016] |
| **Paired net repair gain** | **+.02852 [.01387, .04317]** | **+.01604 [.00303, .02906]** |
| Baseline-weight imbalance | −.00045 [−.01090, .01001] | +.00357 [−.00640, .01353] |
| Raw terminal-IPW gain over initial | +.02807 [.01244, .04371] | +.01961 [.00544, .03377] |
| Baseline-augmented final success | .62879 | .72460 |

The degradation row shows its *negative contribution*; the corresponding nonnegative degradation-probability estimate and untruncated normal interval are in the machine-readable output. Near-zero normal intervals may extend outside probability bounds; they are not claims of negative damage probabilities.

There is genuine improvement under this measured regime. Its inferiority to resampling is not explained by a complete absence of repair. For 3B, degradation consumes about 11% of gross repairs by point estimate; for 7B, about 31%. These ratios are descriptive and imprecise where degradation is rare.

## The causal and operational bottlenecks

| Bottleneck or mechanism | 3B | 7B | Interpretation |
|---|---:|---:|---|
| Initially wrong but public check passes | 19.56% of all episodes | 15.24% | The tested policy stops immediately on these failures. |
| Share of initial failures stopped immediately | 48.94% [43.50, 54.39] | 52.29% [45.52, 59.07] | Roughly half of errors never reach its repair process. |
| Initially wrong and public check fails | 20.41% of all episodes | 13.90% | These are the errors reachable by this policy's repair gate. |
| Weighted repair rate among those reachable errors | 15.72% [9.07, 22.37] | 16.67% [9.25, 24.08] | Most attempted wrong artifacts remain wrong. |
| Initially correct but public check fails | 2.54% of all episodes | 2.41% | Correct artifacts are unnecessarily sent for revision. |
| Already-correct share of public-failure cases | 11.07% [6.87, 15.27] | 14.75% [8.41, 21.10] | A failing public check is not a perfect error diagnosis. |
| Degradation rate among unnecessary-repair entries | 14.04% [−4.92, 32.99] | 29.63% [3.82, 55.44] | Damage risk is uncertain for 3B and material for 7B. |

The hidden initial verdict is used only for retrospective diagnostic stratification. It is not an available controller input. These are weighted regime-specific outcome transitions and ratios, not causal effects of changing the public check, intervening on a mediator, or giving a particular feedback phrase. A different check would select different histories and change future execution. Its achievable gain requires a new supported comparison.

In particular, the high false-pass rate does **not** explain the entire difference between repair and resampling: both tested policies use the same initial public stop signal. It explains an important ceiling shared by them. Their difference among histories that do continue is the next question.

If a hypothetical repair process corrected every initially wrong artifact that passes the current continuation gate and never damaged a correct artifact, its same-first-gate ceiling would be .80437 for 3B and .84759 for 7B. These are algebraic upper bounds, not attainable policies or predicted gains. They leave initial false-pass failures unchanged. Nothing in the logs proves that a perfect public check, a new prompt, or a trained critic could realize these bounds.

## Resampling repairs more from the same initial-answer distribution

For each root, enumerate every ordered distinct triple of its four original candidates. Start with the first candidate, accept it if the actual public check passes, otherwise draw again up to three candidates. No hidden verdict is used to stop or select. Because all orderings are averaged, its initial verdict mean is exactly the same root's four-candidate initial mean. Its repair/degradation decomposition therefore has no initial-weight imbalance term.

| Outcome contribution | 3B repair loop | 3B adaptive BoN3 | 7B repair loop | 7B adaptive BoN3 |
|---|---:|---:|---:|---:|
| Repairs | .03209 | .08274 | .02317 | .03565 |
| Degradation | .00357 | .00490 | .00713 | .00253 |
| Net gain over initial | .02852 | .07784 | .01604 | .03313 |
| Final success, baseline-augmented where weighted | .62879 | .67810 | .72460 | .74168 |
| Mean model calls, baseline-augmented where weighted | 1.4198 | 1.3780 | 1.2986 | 1.2879 |

The paired net-gain difference, repair minus resampling, is **−.04932 [−.06597, −.03266]** for 3B and **−.01708 [−.03184, −.00232]** for 7B. These are exploratory control-variate comparisons of the same outcome target as the raw IPW contrasts. The 7B interval differs from the earlier raw-IPW interval because the latter includes baseline-weight noise; it is not a new policy or an independently replicated positive result. Reporting both prevents choosing an estimator solely for its significance.

For 3B, the approximately five-point deficit comes almost entirely from lower repair yield: resampling produces about five additional gross percentage points of repaired initial failures, with slightly more degradation. For 7B, resampling gains about 1.25 additional gross repair points and avoids about .46 degradation points. Thus "revision harms answers" is incomplete as an explanation, especially for 3B. The current repair instruction and continuation process fail to create correct artifacts often enough compared with an independent redraw.

Average calls are close but not exactly matched, and this comparison is not a cost-randomized head-to-head trial. Tokens, latency, and check costs must accompany a deployment decision. The mechanism decomposition does not identify whether the lower repair yield is caused by the wording of feedback, misleading visible-test diagnostics, conditioning on an unproductive previous attempt, receiver limitations, or their interaction. Distinguishing those mechanisms requires randomizing repair versus independent redraw from the same public-failure prefix with the same receiver and declared cost.

## Where selection and stopping headroom remains

The best-of-three hidden oracle over the same candidate triples has success .73218 for 3B and .76649 for 7B. Its excess over adaptive BoN3 is .05407 [.04231, .06583] and .02481 [.01679, .03283]. An oracle is an unavailable ceiling, not a demonstrated learnable policy.

Approximately 81.3% and 79.6% of these residual gaps are cases where the first candidate falsely passes the public check even though another candidate in the hypothetical full triple would be correct. That supports studying a more informative **public** accept/continue signal, but it also exposes the cost problem: finding disagreement or a better candidate may require paying for samples the cheap policy would never generate. A four-candidate-bank selector and a 1.3-call early-stopping policy have different information and cost budgets.

The complete four-draw bank contains a mixture of correct and wrong artifacts on **32.09%** of 3B tasks and **14.62%** of 7B tasks. The former is close to the earlier fitted beta-binomial prediction of .319; the old selected-cohort .223 was substantially reduced by future-switch filtering. Thus the assertion that the suite had almost no informative 3B selection variation was partly an analysis artifact. This does not establish the recoverability of the gap from public features. The all-wrong-bank shares are 24.06% and 22.46%; no selector of those four artifacts can fix such a bank without generating something different.

## Rounds and benchmark differences

For 3B, weighted repairs ending after two calls contribute .01783 and repairs ending after three calls .01426. For 7B those contributions are .01961 and .00357. All observed weighted degradation ends in the three-call group. **This is not evidence that the third call caused every degradation or that stopping after two calls is better.** Intermediate hidden grades were not collected for every prefix, and final call count is selected by earlier public responses. The data do not supply the missing two-call stopping outcome in every three-call episode.

Both benchmarks show positive net repair gain by point estimate. The 3B gains are .03571 on 154 HumanEval roots and .02580 on 407 MBPP roots; 7B gains are .01948 and .01474. The initial false-pass mass is larger in MBPP: .21622 versus .14123 for 3B and .17936 versus .08117 for 7B. These subgroup summaries are exploratory and preserve their own root counts and intervals in the JSON; they do not establish a benchmark-by-policy interaction.

## What experiment this diagnosis warrants

The evidence supports a narrow question rather than immediate large-scale actor training: **given the same initially public-failing artifact, does the existing repair interaction outperform an independent redraw at the same receiver and cost, and can a public-information rule identify histories where each should be used?** Keep initial false-pass cases as a separately declared stopping-calibration target; otherwise the trial would silently exclude approximately half of errors from its scope.

This experiment should carry exact feedback/version definitions, public-only inputs, a common scoring rule, initial-artifact pairing, root/family separation, known randomization, and a fresh evaluation set. A positive result would motivate adaptive routing between repair and redraw. A negative result would reject that tested repair mechanism at that budget, while retaining the honest value-estimation contribution. The present logs do not justify either universal optimism about causal critics or universal pessimism about multi-round interaction.

## Reproducibility

`scripts/diagnose_repair_mechanisms.py` verifies the exact source hash, retains all roots, checks stopping consistency and the gain identity, and writes immutable root-level scores and summaries to `results/mechanism_diagnosis_20260920/`. It completed in under one second, used no model calls, executed no candidate code, and spent $0. The manifest records its source/script hashes and runtime.

```sh
uv run python scripts/diagnose_repair_mechanisms.py --episodes /path/to/DTR-AgentEvals/results/code_routing/log/episodes.jsonl --output results/new_mechanism_diagnosis
```

Conditional rates use the observed initial-state denominator, which is known before subsequent routing; alternative ratios using a weighted denominator are retained as sensitivity diagnostics. All tests and differences refer to the source verifier's recorded outcomes. No intervention on an unobserved mediator, new prompt policy, hidden-only regrading, or prospective confirmation is claimed.
