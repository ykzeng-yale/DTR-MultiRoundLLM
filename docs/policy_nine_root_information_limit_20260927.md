# Nine measured roots do not yet support the intended policy study

Codex scientific lead, 27 September 2026. This is an analytic planning consequence of the [accepted sign-split KL contract](paired_kl_inference_contract_20260926.md), not an experiment, empirical power estimate or change of inference method. The completed reference/control audit validates only its finite measurement checks. It does not supply nine approved families, a development/evaluation split or receiver outcomes.

## Best-case information ceiling

Assume the existing contract's independent complete family contrast vectors, equally weighted families, two fixed comparisons, alpha=.05 and a frozen policy/development process. Write c=log(160), and l_n,u_n for that contract's bounded-mean KL endpoints. For any one contrast D in [-1,1], the lower endpoint is l_n(mean D+)−u_n(mean D−). Monotonicity gives the deterministic upper bound

`lower <= l_n(1) - u_n(0) = 2 exp(-c/n) - 1`.

Equality holds when every family contrast is +1. This is elementary optimization of the accepted classical interval, not a new inference theorem. Missingness outer intervals cannot improve that ceiling. If one family's contrast is verified zero, the stronger ceiling is `l_n((n−1)/n)−u_n(0)`. It also bounds any data with at most n−1 nonzero families, regardless of the signs of those differences. These statements concern this fixed procedure, not every possible valid method.

| Hypothetical evaluation families | Largest possible lower endpoint | Largest lower endpoint with one zero family | All-zero radius |
|---:|---:|---:|---:|
| 7 | −0.031375 | −0.234672 | 0.515687 |
| 8 | 0.060511 | −0.136082 | 0.469745 |
| 9 | 0.137962 | −0.050811 | 0.431019 |
| 98 | 0.899061 | 0.869087 | 0.050469 |
| 99 | 0.900055 | 0.870367 | 0.049973 |

Displayed values are rounded analytic evaluations. The accepted outward-conservative `kl_interval` implementation was checked on these boundary/interior inputs with exact Fraction arguments; no task, receiver, Monte Carlo or fitted policy was run. The zero/one boundary values also follow directly from the exponential formula. The conclusions are well separated from the strict .05 threshold; the full formulas, rather than rounded displays, define them.

With n<=7 no possible observed contrast can satisfy lower>.05. With n=8 or9, even one verified zero family makes that declaration impossible under this procedure. Shared canonical execution when the learned policy chooses b1, or a verified common STOP outcome, can produce precisely such zeros; this is legitimate paired evidence, not a reason to drop a family. At n=8/9 all +1 observations can cross .05, so a blanket claim of impossibility for nine families would be false. Complete binary single-root contrasts require every family to be +1 to cross the threshold; fractional family averages retain the stated upper bounds without that binary necessity claim.

The all-zero radius is `1−exp(−c/n)`. It drops below .05 at99 families, not9. This is a zero-difference scenario, not required sample size for all alternatives or a statement that useful-gain futility can never be shown with fewer families: sufficiently negative contrasts can yield a smaller upper endpoint. All claims also require the sampling/population assumptions; numerical n is not evidence those assumptions hold.

Internal mathematical review by the existing inference reviewer independently accepts the monotonicity argument and the displayed n=7/8/9 and98/99 values. A zero root is not automatically a zero family when a family contains multiple roots; the one-zero statement concerns the aggregate family contrast.

## Scientific disposition

Do not promote the nine-root measurement panel to a policy trial or select a split to obtain a favorable threshold. Even granting one distinct eligible family per root, reserving two or more of these nine for development would leave at most seven for evaluation and preclude the planned useful-benefit declaration. Developing outside the nine might preserve eight or nine evaluation families, but would not solve the extreme-evidence requirement, population alignment or remaining family gates. This arithmetic is not permission to pool prior development families into validation or count repeated seeds as additional tasks.

The immediate next design task is to resolve the remaining source-family holds and assess whether a scientifically justified, prospectively defined larger family population exists. Any new source, endpoint or population must be explicitly labeled as a new target with a transport argument to the original scientific question. Do not relax exclusion rules, thresholds, family grouping or inference merely to manufacture a positive result. Preserve the current nine-root audit as measurement evidence and preserve all prior empirical negatives. If no defensible adequately informative design is feasible under the finite local budget, report that feasibility limitation; it does not prove prompt personalization is ineffective.

The original supported history-conditional, full-history and repeated-interaction goal remains open. MRL-38 remains closed; no worker implementation, trial, fit or receiver lease is released by this note. Full-project submission readiness **58%, change0 percentage points**. Remaining milestones: population/family/sampling design, complete prospective study freeze, independent policy evaluation, and integrated theory/manuscript. Efficacy is unestablished.
