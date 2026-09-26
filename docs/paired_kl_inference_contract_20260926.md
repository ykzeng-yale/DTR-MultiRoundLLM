# LEAD-INFERENCE-01: sign-split bounded-mean inference

Codex scientific lead, 26 September 2026. **Prospective inference contract and MRL-29 source-only assignment.** This improves the route to an original-target paired-family policy evaluation without replacing the target by an easier finite-roster claim. No policy outcome, sampled coverage experiment or collection release is reported here. Mathematical review by the lead and an independent internal reviewer accepts the argument below. Implementation still needs independent validation before use.

## Established inequality and target

Use the classical Chernoff/Hoeffding bounded-mean inequality, not a new concentration theorem: [Hoeffding (1963), JASA 58, 13–30](https://doi.org/10.1080/01621459.1963.10500830), [primary-paper copy](https://www.cs.rpi.edu/academics/courses/spring06/random/hoefding.pdf). For independent X_i in [0,1], with mu = n^-1 sum E X_i, convexity bounds each exponential moment by that of a Bernoulli variable with the same mean. Concavity of log then bounds the product by `(1-mu+mu exp(t))^n`. Chernoff optimization gives each tail `exp(-n kl(x||mu))`. Negative t supplies the lower tail. Identical distributions and Bernoulli observations are not required.

Condition on frozen development data, policies and experiment. Let `(D_g1,D_g2)` be **independent across families**, fixed n >= 1, equally weighted bounded paired family contrasts in [-1,1]. Within-family aggregation weights/counts are fixed by the protocol; arbitrary dependence within a family or between the two contrasts is allowed. The target is theta_j = n^-1 sum E D_gj. Representative IID family sampling identifies the intended population expectation; nonidentical independent families identify only this average-expectation target unless a separate sampling argument aligns it. Family identifiers, semantic screening and randomized scheduling do not establish independence or population transport.

For x,q in [0,1], use binary relative entropy `kl(x||q)=x log(x/q)+(1-x) log((1-x)/(1-q))`, with 0 log 0 = 0 and infinite divergence at an incompatible boundary. For delta=alpha/8 and c=log(1/delta), let l_n(x),u_n(x) be the endpoints of `{q: n kl(x||q) <= c}`. At boundaries:

`l_n(0)=0; u_n(0)=1-exp(-c/n); l_n(1)=exp(-c/n); u_n(1)=1`.

For each bounded mean, tail inversion gives each one-sided error at most delta. The inversion event follows because kl(x||mu) is monotone as x moves away from mu on either side; no union over possible observed means is needed. The endpoints l_n and u_n are nondecreasing functions of x.

## Two simultaneous policy contrasts

Set `X_gj^+=max(D_gj,0)` and `X_gj^-=max(-D_gj,0)`. Both are bounded in [0,1], and theta_j = mean E X_gj^+ - mean E X_gj^-. Let bars denote empirical family averages. Define

`I_j = [l_n(bar X_j^+) - u_n(bar X_j^-), u_n(bar X_j^+) - l_n(bar X_j^-)]`.

There are two tails for each of four means (two signs, two contrasts). The union bound gives simultaneous coverage of both I_j at least 1-alpha. Intersect with [-1,1] if needed. This is a specialization of established bounded-mean inference, not evidence of learned-policy usefulness. Full-history causal sufficiency of a learner's features is not required for direct value evaluation; consistent interventions, receiver/scorer stability, isolation, valid measurement and the declared sampling law still are.

The eight-tail allocation is fixed even if the observed data are zero or one contrast looks uninteresting. No optional stopping, random completer denominator, outcome-chosen learner, split, subgroup or endpoint is covered. A fixed roster with cap-truncated missing outcomes can be handled only under the latent-law and containment conditions below.

## Missingness and shared outcomes

Assume the complete latent family vectors exist under the frozen experiment and meet the independence/boundedness conditions. Suppose deterministic valid bounds satisfy `-1 <= L_gj <= D_gj <= U_gj <= 1` for every planned family, including unattempted slots. Then monotonicity gives the simultaneous outer intervals

`[l_n(mean max(L_j,0)) - u_n(mean max(-L_j,0)),`

` u_n(mean max(U_j,0)) - l_n(mean max(-U_j,0))]`.

The first negative term uses **-L** (the upper bound on the negative part); the last uses **-U** (its lower bound). These intervals contain the complete-data I_j pathwise. Missingness may depend on outcomes, but neither a nonexistent endpoint nor corrupted provenance is repaired by assigning an interval. Uncertain or breached first-stage identity cannot be treated as a verified common branch. If containment is only probabilistic its error must receive a separate allocation.

For valid shared outcomes, construct bounds **before** subtracting marginal intervals. Write a paired score as `D=sum_k c_k Y_k`, with each unique, truly shared primitive score Y_k in [a_k,b_k]. First consolidate every occurrence of the same verified primitive identity to one coefficient c_k. Its sharp rectangular bounds are

`L=sum_{c>=0} c*a + sum_{c<0} c*b; U=sum_{c>=0} c*b + sum_{c<0} c*a`.

This follows directly by minimizing/maximizing a linear expression over the score box. The same missing grade with coefficient +w and -w cancels exactly. Two distinct draws of the same recipe do **not** share a primitive merely because their action names or output hashes match. Shared identity requires the predeclared branch-reuse law, same saved artifact/execution, endpoint and score version; a caller-provided string cannot certify those facts. Family averaging follows consolidation with the frozen root/replicate weights.

For pre-choice nonactionable roots, a verified shared fallback can cancel from a contrast even if its absolute score is missing. An integrity breach or an unverified common execution law cannot. Such units retain unconstrained contrast bounds or invalidate the scientific analysis as appropriate to the documented breach; they are never dropped or converted to public pass. This settles a mathematical bookkeeping rule, **not** the still-open deployment endpoint/failure contract.

## Precision consequence and prospective choice

If all complete family contrasts equal zero, the displayed two-contrast intervals have radius `1-(alpha/8)^(1/n)`. At alpha=.05, an independent scalar check gives radius .0504693679 at n=98 and .0499725328 at n=99. Thus 99 can cross the **.05 zero-difference radius** threshold. This is conditional arithmetic, not a universal sample-size guarantee, power calculation, prediction of observed agreement, or a certificate that 99 independent eligible families exist. Contrasts with substantial positive and negative parts can have much wider intervals.

The earlier 3,506-family calculation remains correct for its stated Hoeffding fixed-radius method. The empirical-Bernstein note remains valid too. Neither is a lower bound on the sample size of every valid procedure. This option makes an audited smaller family frame worth assessing again; it does not certify the existing 198-ID MBPP convenience frame.

**Prospective decision:** after source/numerical acceptance, use this sign-split procedure as the proposed primary two-contrast uncertainty rule for the new PATCH/RETHINK policy design. This is decided before new development or evaluation outcomes. The prior Hoeffding and empirical-Bernstein procedures may be labeled sensitivity analyses; do not select the narrowest interval or combine conclusions at unadjusted .05. The useful-gain threshold remains .05, with strict lower-bound >.05 for useful benefit and strict upper-bound <.05 for useful-gain futility; equality is inconclusive. Practical superiority still needs the separate B2 and cost contract. No old result is reanalyzed or relabeled by this choice.

## MRL-29 bounded source assignment

Existing Claude Code worker only, one CPU, **20 elapsed minutes from acceptance, 32 MiB new retained output**, zero experimental model calls, historical-data fitting/reanalysis, candidate/reference execution, downloads/installations or paid experimental services. No Monte Carlo sampling. Publish factual partial work at the cap. Direct main integration with configured owner identity, fetch/inspect main before pushing and ordinary merges only. Codex owns mathematical interpretation and independent review.

Add `experiments/prompt_choice/paired_inference.py`, `experiments/prompt_choice/paired_inference_source_v1.json`, `tests/test_prompt_paired_inference.py` and ordinary attributed receipts. Do not modify prior source/results. Config must pin this contract at its issuing commit, mark source-only/collection-unreleased, state the alpha/8 allocation and assumption boundaries. The module must have no data discovery, network, dispatch or code-execution path.

Provide pure functions for (a) shared-primitive linear score bounds, (b) one bounded-mean KL interval, and (c) the exactly two named family contrasts `d_minus_b1`, `d_minus_b2` using the missingness envelope above. Accept exact integers/Fractions, rejecting Boolean, float, NaN and malformed/nonfinite domains rather than silently rounding them. A serialization helper may emit rational numerator/denominator pairs. Validate nonnegative policy weights summing exactly to one on each side of a contrast, score intervals inside [0,1], nonempty unique UTF-8 IDs and exact reference completeness. The shared-score function validates internal bookkeeping only, not execution identity. Family input includes exactly one bounds pair per named contrast per unique family, with -1<=L<=U<=1. Never silently discard or regroup rows. Empty family input returns a clearly labeled no-data [-1,1] result, without evaluating a KL expression at n=0.

Numerical endpoints must be **outward conservative**, not merely point estimates of roots. Use exact Fraction brackets and a fixed maximum of 64 bisections. Evaluate KL and c/n with outward interval arithmetic at at least 80 decimal digits: rational conversion and arithmetic round outward; a correctly rounded Decimal logarithm may be enclosed by its adjacent representable values. If intervals do not determine the comparison, retain the current bracket and stop. Return the lower exterior endpoint for l and upper exterior endpoint for u. Handle x=0/1 without 0*log(0); a formula-based shortcut also needs outward bounds. Report precision/iteration policy. Do not use an arbitrary added epsilon as a numerical certificate. A private point-valued math function may serve as a diagnostic but not replace conservative output.

Tests must independently cover exact cancellation of shared missing grades versus distinct grades, fractional/zero weights, malformed references, all-zero/all-one means, reflection, monotonicity, missingness widening and all-missing [-1,1]. Compare to a separate high-precision numerical inversion on fixed grids, including n=98/99 and alpha=.05. Enumerate small fixed independent and nonidentical finite-support joint family laws to verify the two-contrast coverage calculation against known expectations; label these exact synthetic unit checks, not proof of universal coverage or empirical validation. Include non-Bernoulli fractional differences. No sampled simulation or existing receiver-grade access. Run focused tests and report hashes, limits and exact UTC/deadline; Codex will independently check before adopting the component.

Full-project readiness remains **58%, change 0 percentage points**. Efficacy and independent policy validation remain unestablished. Source/family/measurement validity and the full finite execution freeze are still required; E14 N1/S1 remains NO-GO.
