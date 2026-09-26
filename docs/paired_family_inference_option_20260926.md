# A variance-sensitive option for the paired-family trial

Codex scientific lead, 26 September 2026. **Prospective theory/design option; no simulated or receiver outcomes, no adoption in an existing analysis, and no collection release.** This addresses the precision bottleneck in the [independent policy design](independent_prompt_policy_validation_design_20260922.md). It does not establish policy benefit, certify the family frame, replace old intervals or change their negative conclusions.

## Established bound and project specialization

Maurer and Pontil (2009), [Theorem 11](https://www.learningtheory.org/colt2009/papers/012.pdf), provide an empirical Bernstein inequality for independent bounded variables, including nonidentical distributions. This is established concentration theory, not a new estimator or foundational result here.

Condition on a frozen development/training package. For two prespecified contrasts, let the vector `(D_g1,D_g2)` contain each family's bounded paired quality differences, with `D_gj` in `[-1,1]`. Assume independent family vectors, fixed `n >= 2`, fixed family-aggregation weights/counts, valid measurement, and policies fixed without evaluation outcomes. Define

\[
\theta_j=n^{-1}\sum_{g=1}^n E[D_{gj}],\quad
\bar D_j=n^{-1}\sum_gD_{gj},\quad
s_j^2=(n-1)^{-1}\sum_g(D_{gj}-\bar D_j)^2.
\]

Then simultaneous two-sided coverage of both contrasts is at least `1-alpha` for

\[
I_{Ej}= [\bar D_j-r_{Ej},\bar D_j+r_{Ej}]\cap[-1,1],\qquad
r_{Ej}=\sqrt{\frac{2s_j^2\log(8/\alpha)}{n}}
 +\frac{14\log(8/\alpha)}{3(n-1)}.
\]

To check the specialization, set `X=(D+1)/2`, whose sample variance is `s²/4`. Apply Theorem 11 to `X` and `1-X` at failure probability `alpha/4` each; rescale by two and union-bound four tails. The two contrasts need not be independent.

## Assumptions are not created by the formula

IID sampling of the declared target families identifies the intended population contrast. Independent nonidentical families also satisfy the bound, but its average-expectation target equals the intended population only with a valid sampling/weighting argument. Arbitrary dependence within a family is allowed after its prespecified bounded aggregation; treating multiple branches as independent families is not allowed. Finite-frame sampling without replacement needs its own argument rather than this independence assumption.

Fixed policies, endpoint and sample size can be set by design. Valid family independence, receiver/scorer stability, lack of interference and representative sampling still require justification. An adaptive cap or outcome-dependent inclusion must not select the observed rows used for inference. These are fixed-sample intervals, not confidence sequences. Outcome-dependent termination can still be handled as missingness if the full prespecified roster/denominator and latent execution law stay fixed and all unobserved slots receive valid bounds below; using a random completer count is invalid. With fewer than two families use the prespecified trivial range. Zero empirical variance retains a positive radius.

## Missing outcomes without complete-case selection

Suppose a latent complete-data vector under the fixed experiment exists and meets the above assumptions. Let valid intervals `[L_gj,U_gj]` contain every unobserved complete contrast, including failures and unattempted planned slots where the endpoint is genuinely unknown. If interval containment is itself probabilistic, its failure probability needs an additional allocation; the argument below assumes deterministic valid bounds. Never rename a missing score STOP or discard its family.

For one contrast write `m_g=(L_g+U_g)/2`, `h_g=(U_g-L_g)/2` and

\[
S_{\max}=\min\left\{\sqrt{\frac n{n-1}},\;
s(m)+\sqrt{\frac{\sum_g h_g^2}{n-1}}\right\}.
\]

Every compatible completion has `s(D) <= S_max`: center the vector, apply the Euclidean triangle inequality and the contraction of orthogonal centering, and use `|D_g-m_g| <= h_g`. The other term is the maximal sample standard deviation for `[-1,1]` data. Therefore

\[
[\bar L-r_E(S_{\max}^2),\ \bar U+r_E(S_{\max}^2)]\cap[-1,1]
\]

contains the complete-data interval for every compatible completion and inherits its coverage. Missingness can depend on outcomes; the independent latent vectors and fixed total family count still must exist. This outer envelope may be uninformative. It does not resolve nonexistence of a counterfactual endpoint, corrupted provenance or outcome-adaptive choice of the target family population. This is an elementary application-specific envelope argument, not a claim of novel missing-data methodology.

## Prospective arithmetic, not power or evidence

The following entries evaluate formulas at *stipulated observed variances*, with `alpha=.05`. They do not predict the eventual variance or probability of a useful-benefit decision. The current two-contrast Hoeffding radius is `sqrt(2 log(4/alpha)/n)`.

| Families n | Stipulated s² | Empirical Bernstein radius | Hoeffding radius |
|---:|---:|---:|---:|
| 198 | 0 | .120224 | .210387 |
| 198 | .10 | .191823 | .210387 |
| 198 | .20 | .221481 | .210387 |
| 544 | 0 | .043617 | .126927 |
| 544 | .01 | .057277 | .126927 |
| 544 | .05 | .074161 | .126927 |
| 544 | .10 | .086813 | .126927 |
| 544 | .20 | .104705 | .126927 |
| 544 | .40 | .130009 | .126927 |

At 544 families, a .05 radius requires `s² <= .00218343`; at 198 even zero variance cannot reach .05. Neither count is a certified current independent-family sample. The option can improve precision but does not remove the feasibility gap or demonstrate a useful effect.

## No favorable-interval selection

Taking the narrower of two separately 95% procedures has no automatic 95% guarantee, even if that selection rule is preregistered. Either freeze one primary procedure and report the other as sensitivity without changing the primary conclusion, or reserve error budgets `alpha_E + alpha_H <= .05` for a jointly valid intersection. In the latter case use the respective levels in both displayed radius formulas. With equal `.025/.025` allocations, the logarithms become `log320` and `log160`. At `n=544,s²=.10`, the two radii are `.095625` and `.136597`. Dependence between the procedures is harmless for the union-bound guarantee. With this equal split at 544 families, the empirical Bernstein zero-variance floor is .049574 and a .05 radius requires s² <= 0.000008547; splitting can materially reduce the apparent precision gain.

A proposed implementation still needs a separately frozen known-truth validation grid, exact missingness/weight handling, deterministic edge cases, independent review and a bounded execution plan before any sampled study. Do not fit the variance scenario, sample size, interval choice or useful-gain threshold to held-out outcomes. No worker simulation is assigned by this note.

Independent mathematical review checked Theorem 11 against the primary paper, the rescaling and four-tail union bound, the centering proof for the missingness envelope and the error allocation for intersection. A second reader separately checked the same formulas and clarified termination versus a random completer denominator. Formula values were independently recomputed with elementary arithmetic. This is proof/design review, not sampled coverage validation.

Full-project readiness remains **58%, change 0 percentage points**. This design option earns no empirical or independent-policy credit. Source/family validity, supported development learning, independent policy evaluation and the manuscript/reproducibility package remain the largest milestones.
