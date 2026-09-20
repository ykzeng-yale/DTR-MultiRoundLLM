# Independent recheck of E0, G0e, and G1a evidence

Date: 2026-09-20. Status: executed CPU-only audit; $0 external spend; no new model calls. This is a separate internal review of another workstream's experiments, not external peer review. Authoritative recheck artifacts are in `results/independent_audit_20260920/verified/`. The original results remain preserved.

## Main conclusion

The archived G0e arithmetic is internally consistent **within each selected cohort**, but its narrative combines different cohorts and its exclusion rule conditions on later routing outcomes. The original selected candidates are therefore not ordinary independent draws from the initial receiver. The corrected analysis still gives evidence that resampling is a strong comparator, especially for the 3B receiver, but does not support the unqualified statement that K1 has been prospectively established on both receivers at matched cost. E0 contains genuine fitted tabular Q functions, but several comparisons and failure-cell interpretations used mismatched targets. The old statement that the study licenses correctness of every estimator and maps every failure boundary is too strong.

## Raw source and integrity

Read the sibling project's local `results/code_routing/log/episodes.jsonl` at `/Users/yukang/Documents/Codex/2026-09-18/fur/work/DTR-AgentEvals/`. SHA256:

`e643ee44c7ef658fff65efb5e17763ee78c990d21184d060f5823025a100414e`

It contains 4,488 unique episodes: 561 root tasks, four initial draws per task per receiver. There are 1,122 task/receiver cells. Every cell has one initial-input transcript hash and distinct episode seeds. All 6,063 recorded routing decisions have `b_obs=.5`, source `design_u`, and are marked eligible and completed. There are no recorded episode errors or mock episodes. One configuration, source-code, task-pool, and visible-test hash covers the source. Source metadata hashes are saved in the audit JSON.

The sibling `experiments/code_routing/run.py:chooser` reads a presampled routing uniform for the current stage, chooses the receiver with probability .5, and checks the blocked initial assignment. `agent.py` records the probability before invocation and uses `validation.passed` to stop. This supports use of the recorded randomization probabilities conditional on the frozen design. It does not prove server invariance or absence of benchmark-family dependence.

The source includes 1,848 episodes marked `train` and 2,640 marked `confirm`. G0e and G1a consumed both. These analyses are exploratory reuse; those labels cannot subsequently be called an untouched confirmatory holdout for a method selected using these findings. Cross-fitting by task in G1a prevents direct same-task fitting but does not restore a sequestered holdout or account automatically for dependence from shared fitted models in its simple paired standard error.

## G0e: denominator mismatch and post-outcome selection

`experiments/audits/g0e_adaptive_bon.py:load` discards episodes containing a later receiver switch before collecting their first candidates. `g1a_selection_pilot.py:load` repeats this rule. Whether an episode continues or switches depends on earlier receiver outcomes. Keeping only episodes that never switched selects the first-candidate distribution.

| Receiver | Retained episodes | First success retained | Switched episodes | First success excluded |
|---|---:|---:|---:|---:|
| Qwen2.5-3B | 1,873 | .6983 | 371 | .1051 |
| Qwen2.5-7B | 1,991 | .7820 | 253 | .1304 |

Requiring at least three or four *retained* episodes then selects task cohorts too. These exclusions are not a legitimate way to manufacture fixed-receiver trajectories without propensity correction.

The reported 7B values .8057 and .8247 use 485 and 444 tasks respectively. Within the 444-task k=4 cohort, the multi-turn mean is **.821509**, versus **.824700** for BoN; their paired difference is correctly **−.003191**. Thus the subtraction discrepancy comes from the prose/table denominators, not the stored paired-difference calculation. The corresponding multi-turn calls are 1.018581, not the all-485-task 1.05. For 3B k=4, the matched cohort has 378 tasks and multi-turn mean .729497. All matched component means are saved in `routing_audit.json`.

There is also a checker mismatch: both archived loaders use `n_fail==0`, while the executed loop uses `validation.passed`. In this corpus 720 episodes have zero visible assertions; a zero-check loading failure can have `n_fail=0` but `passed=False`. Six first decisions, and ten decisions overall, disagree. The corrected comparator uses the actual `passed` flag. No hidden success flag is used for stopping or choosing an achievable comparator; it is only the evaluation outcome. The oracle ceiling remains explicitly unavailable to the deployed picker. The historical variable name “hidden” does not itself certify that the logged benchmark outcome excludes every prompt-revealed test; the existing grading definition must remain attached to these results.

## Corrected exploratory comparison on all 561 tasks

The target is the sibling repair-and-stopping policy with the initial receiver fixed to model m and all subsequent eligible calls also using m. The analysis conditions on the blocked initial receiver assignment, so its first probability is not reweighted. At later eligible decisions use

`W = product_t>=1 {1(model_t=m) / b_obs,t}`.

An episode that switches remains in its task's four-episode average with zero terminal weight. An episode that stops after its initial call has weight one. Terminal success, total model calls, and total completion tokens are multiplied by W. The equal mean of the four scores is calculated within each task, then tasks are equally averaged. This identifies the fixed-receiver target under the recorded randomization, consistency, and stable-environment assumptions; it is not the raw mean among never-switchers.

Adaptive BoN uses **all four first candidates** per task and receiver. For each k, enumerate every ordered distinct k-sample, stop at the first actual visible pass, otherwise return the last. The sample statistic is unbiased for k independent initial generations when the original draws are conditionally iid. Its calls and completion tokens are charged through the actual stopping position. Distinct seeds and identical initial transcript hashes are checked, but iid server behavior is still a design assumption. No candidate program is re-executed by this audit.

All rows below compare the same 561 tasks. Intervals are paired 1.96-standard-error intervals over root-task score differences. They are exploratory benchmark-root repeated-sampling summaries, not multiplicity-adjusted prospective certificates; task-family clustering remains unresolved.

| Receiver | k | Fixed-receiver MT IPW success | Adaptive BoN success | MT − BoN, 95% CI | MT calls | BoN calls |
|---|---:|---:|---:|---|---:|---:|
| 3B | 2 | .628342 | .654337 | −.025995 [−.041979, −.010012] | 1.4158 | 1.2295 |
| 3B | 3 | .628342 | .678105 | −.049762 [−.067695, −.031830] | 1.4158 | 1.3780 |
| 3B | 4 | .628342 | .692068 | −.063725 [−.083967, −.043484] | 1.4158 | 1.4908 |
| 7B | 2 | .728164 | .732323 | −.004159 [−.018749, +.010430] | 1.3021 | 1.1631 |
| 7B | 3 | .728164 | .741682 | −.013518 [−.029351, +.002316] | 1.3021 | 1.2879 |
| 7B | 4 | .728164 | .746881 | −.018717 [−.035792, −.001641] | 1.3021 | 1.3971 |

At k=3, mean completion tokens are 116.482 versus 107.470 for 3B and 108.961 versus 104.165 for 7B. Every paired call/token interval is retained in the JSON, including cost uncertainty. BoN4 improves the 7B estimated outcome while using **more calls** than the fixed-receiver target. BoN2's 7B upper success-difference bound is +.010430, above the stated +.01 K1 threshold. BoN3's interval includes zero and its cost difference is uncertain. These facts rule out using “better and cheaper on both receivers at every k” as the revised conclusion. No exact common-cost interpolation policy or cost-matched fresh head-to-head experiment is estimated here.

Maximum terminal weight is four for both receivers. Mean weights are .995989 and 1.003565. The episode-weight ESS diagnostics are 1,382.57 and 1,575.98, respectively; the independent root-task count is **561**, not those ESS values. The observed weight distribution and full per-task scores are saved. There are no propensity zeros in this source. This maximum overlap of four is specific to two subsequent randomized routing decisions and says nothing about support for arbitrary prompt messages.

## E0 target and implementation audit

1. **Fitted versus known nuisance:** `fit_q` estimates tabular sequential outcome regressions and `value_dr` cross-fits by root task. The logging propensity B is supplied by the simulator, never fitted. In latent-dependent cells it contains information from the true latent-dependent assignment law. These cells do not validate learned propensities or robustness to genuinely unavailable assignment information. The compressed `(state,time)` Q is not automatically the full-history true Q when persistent task latents remain.
2. **Continuation mismatch:** archived `blip_naive_conditional` averages observed Y given the first state and action, so its future continuation follows the logger. The grading truth instead fixes uniform continuation. In the base cell and state 1, the exact LOCAL uniform-continuation blip is **.326173**, while the raw conditional regression converges to **.318174**. RESET is .289314 versus .280419. Similar rankings do not make the estimands identical. Comparing their ranking variance can be descriptive but does not prove that a fair conditional estimator beats an IPW estimator of the same target.
3. **Missing first-action adjustment:** archived `blip_ipw` starts weighting at the second decision. In `FAIL_latent`, the first treatment selection tilts the latent distribution. For LOCAL its exact large-sample limit is **.364842**, rather than the uniform-continuation target **.326173**. RESET converges to .306346 instead of .289314. Correct continuation ratios alone cannot repair this initial bias.
4. **Misnamed optimum:** archived `optimal_rule(observable='state')` repeated the turn-1 uniform-continuation greedy action at every stage. Its own source described that shortcut. It was not a state-only optimal-control solver, so its value could be a heuristic reference but could not establish “regret to the exact optimum.” Exact evaluation of a rule does not establish optimality of that rule.
5. **Wrong coarsening truth:** `FAIL_coarsening` draws a new template-offset array for each replication and then samples uniformly among templates in each class. The archived metrics used the zero-offset kernel for every replication. The relevant class-intervention kernel is the exact average of that replicate's template kernels. Treatment-version heterogeneity does not by itself invalidate the value of an explicitly fixed within-class mixture. The old coverage .886 is not interpretable as pure failure of DR under version heterogeneity.
6. **Weak versus absent overlap:** `FAIL_positivity` retains a positive .02 floor. Its Wald coverage failure is evidence about finite-sample overlap/precision, not a literal violation of positivity identification. “Only the failure cells fail” and “all estimators are correct” should not be inferred from a single 996-replication grid.
7. **Replication accounting:** the historical driver allocates `floor(requested/workers)` to every worker, producing 996 rather than the manifest's 1000. The report disclosed 996, but the manifest remained inconsistent. Per-replication raw output was not preserved in that archived grid, limiting reconstruction.

The integrating agent repaired initial treatment weighting, per-replicate mixture truth, logging-association truth, heuristic-reference labeling, seed allocation, and raw replicate preservation. I inspected the repaired functions and found them consistent with these requested changes. I did not treat that inspection as an independent complete proof of all estimator properties. The legacy E0 README/docstrings still need interpretation through the corrected reports when they make broader claims.

## Bounded fitted-Q reproduction

Independently ran 24 replications each of base, latent-dependent assignment, and template heterogeneity, with 230 tasks × 40 episodes and three decisions per replication. Seeds, exact template offsets, fitted-DR estimates, intervals, and actual/nominal truths are saved. The runner snapshots the three E0 sources before importing them, so source edits by another agent cannot change the recorded reproduction. The snapshot's hash is in `e0_recheck.json`. The script computes its own exact template-mixture kernel for comparison.

| Cell | DR bias against actual truth | Coverage | Coverage MCSE | Actual truth range |
|---|---:|---:|---:|---|
| base | +.000046 | .8750 | .0675 | .645977 |
| latent-dependent assignment | −.003987 | .9583 | .0408 | .645977 |
| template heterogeneity | +.000406 | .9583 | .0408 | [.630971, .665461] |

These small-R results verify executable fitted-Q operation and expose the changing coarsening truth; they are too imprecise to establish nominal coverage or replace the larger corrected study. For this particular 24-seed template sample, nominal and actual coverage happen to agree. That coincidence does not repair the archived target mismatch. Exact blip limits, rather than Monte Carlo rankings alone, establish the continuation and initial-weight discrepancies.

## G1a interpretation

No direct hidden verdict was found in the candidate-feature construction. Hidden outcomes are training labels, which is appropriate when evaluation tasks are excluded from fitting. However, the shared post-routing selection bias, variable bank sizes/order, use of `n_fail==0`, reuse of confirmatory labels, and missing family-level split remain material. The source code names failure classes `assert/timeout/syntax`, whereas the sibling validator reports `assertion` and many errors as `exception` with an additional `err` field; some declared features therefore do not represent their intended categories. The pilot's two fitted procedures failing to improve is **not proof that the feature set contains no usable signal or that no learner can recover the gap**. Its bank selector also consumes all candidates, so its value cannot inherit the early-stopping cost of adaptive BoN. The parent agent is running a separately scoped corrected fixed-bank selection diagnostic; this audit does not duplicate it.

## Reproduction and boundaries

```sh
uv run python scripts/audit_existing_evidence.py --episodes /path/to/DTR-AgentEvals/results/code_routing/log/episodes.jsonl --e0-reps 24 --output results/new_independent_audit
uv run --extra dev pytest -q tests/test_evidence_audit.py
```

Four meaningful audit tests pass: paired components share one cohort, visible-only stopping cannot consult hidden success, switchers retain zero-weight scores, and routing probabilities cannot be missing. The source log is external to this repository and must match the recorded hash to reproduce these numbers. Existing output directories are never overwritten. Earlier `independent_audit_20260920/` and `completed/` artifacts are preserved preliminary runs; only `verified/` uses the actual checker flag, full diagnostics, and immutable E0 source snapshots. A preliminary serialization failure was corrected before the successful verified run.

No fresh LLM interaction, trained generative prompt policy, newly sequestered holdout, hidden-only regrading, family-independent benchmark study, or matched-budget superiority claim was established by this audit. Those remain separate research tasks.
