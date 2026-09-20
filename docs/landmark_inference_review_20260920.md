# Independent review of landmark inference

**20 September 2026. Reviewed baseline:** commit `1e544e4`, specifically `experiments/landmark/analyze.py` and `docs/landmark_experiment_protocol.md`, with read-only checks of collection and tests. This memo does not change the analyzer, prior outputs, endpoint, or protocol. Its exact numerical counterexamples use no model calls. The conclusions concern statistical scope and pre-run contract gaps, not a new efficacy result.

**Baseline judgment:** the analysis at `1e544e4` is suitable for a clearly labeled development description. It preserves the assigned-root denominator in missing-outcome bounds, averages branches before analysis, and uses family-cluster rather than branch-level standard errors. It does **not** supply finite-sample population confidence bounds or a confirmatory decision procedure. The protocol mostly states that distinction correctly. The changes needed before confirmatory use are precise: declare the weighted target, separate realized-sample completion bounds from population uncertainty, freeze the failure endpoint, and implement the selected primary/multiplicity rule. No defect was found in the existing cluster-sandwich algebra itself. **The subsequent candidate patch was independently reviewed and fixes the bound-export scope and multiplicity issues; see §9.**

## 1. What is already correct

* Branches are averaged within root; six named arm contrasts are paired on the same roots. Repetition does not artificially increase the root count.
* Family membership controls both collection splits and the cluster sum used for uncertainty. One-family data do not receive a normal interval.
* A contrast interval is withheld if any selected root lacks a required grade or the receiver identity gate fails. Complete-pair means are explicitly described as selected-population summaries when incomplete.
* Missing grades are bounded in `[0,1]`; contrast bounds subtract the other arm's upper/lower bound. All selected, nonexcluded roots remain in the denominator. Precollection exclusions concern prior exposure, not observed quality.
* The protocol does not gate personalization on an average arm effect. Its development-stage criterion is valid collection, not efficacy. It distinguishes significance against zero from benefit beyond a meaningful threshold, and labels the existing power formula as approximate.

These are substantive protections. They should be retained when adding an inferential export.

## 2. Equal-root and equal-family targets differ

At baseline, `paired_summary` (lines 26–39) estimates

$$
\bar D=\frac1N\sum_{g=1}^G\sum_{i=1}^{n_g}D_{gi}
=\sum_g w_g\bar D_g,\qquad w_g=n_g/N.
\tag{R1}
$$

It uses the cluster scores `S_g=w_g(bar D_g-bar D)` and variance estimate `G/(G-1) sum_g S_g^2`. This is the usual intercept-only cluster sandwich. It is an asymptotic approximation under suitable independent-cluster sampling, moments and absence of a dominant cluster. Counting at least two family IDs is not enough to establish those conditions.

The mean gives every root equal weight and large families more weight. It does not give families equal weight. For nine roots with contrast `+1` in family A and one root with contrast `-1` in family B, the code returns `.8`; the equal-family mean is `0`. Neither weighting is intrinsically correct. The scientific population determines which is wanted.

Three targets should not be merged:

1. **The realized roster:** its complete-outcome average is a descriptive finite-sample quantity. Unknown grades cause completion uncertainty; no random-sampling interpretation is automatic.
2. **Expected performance on this fixed roster/design:** average over the declared receiver/initial-answer/measurement randomness for the frozen tasks, weights and policy. A valid bounded independent-family argument can cover this expectation, conditional on the design and any separately learned policy.
3. **A new-root population:** requires an explicit root/family sampling law. For iid sampled families with random sizes `N_g`, pooling all roots generally approaches `E[sum_i D_gi]/E[N_g]`; giving each family equal weight approaches `E[bar D_g]`. A fixed-weight confidence theorem does not automatically cover the former ratio target under arbitrary informative cluster sizes.

**Action before collection:** put `equal_root` or a different declared weighting rule in the inferential contract, name its target population/roster, and retain family sizes. Report `max_g w_g` and `1/sum_g w_g^2` as weight-concentration diagnostics; the latter is not a substitute for a valid family definition or independent sampling. Hash-based splitting preserves supplied family labels but cannot discover missing dependencies.

## 3. The existing normal interval is not a finite-sample certificate

The code explicitly calls its interval an "Unadjusted normal family-cluster approximation" and warns about small-cluster coverage. That warning is justified. It is not a proved 95% interval simply because the exported field is named `ci95`.

**Executable counterexample using the current function.** Take 24 independent one-root families and a contrast `D` equal to `+1` with probability `.9` and `-1` otherwise. Its true expected contrast is `.8`. On the event that all 24 observations equal `+1`, `paired_summary` returns mean `1`, standard error `0`, and interval `[1,1]`, which excludes `.8`. That event alone has probability

$$
0.9^{24}=0.0797664431.
$$

Consequently coverage is at most `.920233557` in this finite example, even with no missingness, correct families and complete assignment. Other failure events can lower it further. The demonstration is not an estimate of coverage in the actual study, whose outcome law remains unknown.

The direct read-only invocation was `paired_summary([1.0]*24, [str(i) for i in range(24)])`; it returned exactly the values above. The separate unequal-family example from §2 returned SE `.36` and approximate interval `[.0944,1.5056]`. That does not justify a conclusion about the equal-family target of zero: it is a different estimand. Merely clipping a normal interval to `[-1,1]` or changing 1.96 to a small-sample t multiplier does not fix the zero-estimated-variance counterexample.

**Action:** retain the normal interval only under an explicit exploratory/asymptotic label. If a finite-sample statement is desired, export a separately named bound with its actual sampling assumptions; a concrete conservative choice follows. A mock interval validates arithmetic, not empirical inference.

## 4. A valid bounded-family alternative with a fixed target

This is an elementary Hoeffding specialization, not a new statistical contribution. It deliberately makes weaker precision promises than the normal approximation.

Condition on the frozen design, fixed positive family sizes, fixed weights `w_g>=0` summing to one, and any separately trained policy. Suppose family-level random vectors are independent; dependence within each family is unrestricted. Let `X_g` be the family-average paired contrast, with `-1<=X_g<=1`. Define the specific target

$$
\theta_w=\sum_g w_gE[X_g\mid\text{frozen design/training}],\qquad
\widehat\theta_w=\sum_gw_gX_g.
\tag{R2}
$$

Neither identical distributions nor independent roots within a family are required. The independence, boundedness, weighting and conditioning statements are required. Use `w_g=n_g/N` only when that is the declared target; do not quietly interpret (R2) as an unconditional superpopulation ratio.

For `0<alpha<1`, write

$$
r_\alpha=\sqrt{2\log(2/\alpha)\sum_gw_g^2}.
\tag{R3}
$$

Then

$$
P\left\{\theta_w\in
 [\max(-1,\widehat\theta_w-r_\alpha),
  \min(1,\widehat\theta_w+r_\alpha)]\right\}\ge1-\alpha.
\tag{R4}
$$

**Proof.** The independent summand `w_gX_g` lies in `[-w_g,w_g]`, an interval of width `2w_g`. Hoeffding gives each tail probability at most `exp{-2t^2/sum_g(2w_g)^2}=exp{-t^2/(2 sum_g w_g^2)}`. At (R3), each tail is at most `alpha/2`; union bound proves the untruncated interval. Intersecting with the known parameter range `[-1,1]` preserves coverage. ∎

For 24 equal-size independent families and `alpha=.05`, `r_alpha=.5544426221`. In the all-ones counterexample the bound is `[.4455573779,1]`, not `[1,1]`. With weights `(.9,.1)` the radius is `2.4596264563`, so truncation gives the entire parameter range. These values were directly computed, not inferred from the model logs. The bound's likely lack of precision at the proposed development size is a reason to label that stage feasibility; it is not evidence of an effect or of impossibility for all inferential methods.

For an arm **quality mean** rather than a contrast, family means lie in `[0,1]`; the sharper radius is `sqrt{log(2/alpha) sum_g w_g^2/2}`, with clipping to `[0,1]`. Reusing the contrast radius is conservative but should not be advertised as the sharper mean bound.

## 5. Missing outcomes: completion bounds first, confidence bounds separately

The current `all_assigned_mean_bounds` (lines 118–121 and 149–159) are valid **bounds over completions of the realized assigned data**. For an arm with `R` prescribed replicates, known-success total `s`, and `m` missing outcomes, `[s/R,(s+m)/R]` contains every possible complete replicate mean. For a contrast, `[L_a-U_b,U_a-L_b]` contains every completion. Averaging those endpoints with the declared fixed weights preserves containment.

These are not population confidence intervals. With no missing grades they reduce to `[bar D,bar D]`, which still has sampling uncertainty. With missing grades the code does not assume missing-at-random; this is appropriate. The completion bound may be conservative rather than sharp when deterministic identical-artifact labels or other known constraints tie missing scores together.

There is also a limit to the completion interpretation: a numeric bound presupposes a well-defined bounded endpoint for every assigned slot under the declared intervention. If a "quality" outcome is undefined when no artifact exists, first define a deployment-failure composite or a missing potential continuation outcome. Mathematical bounding cannot itself choose that endpoint.

### Conservative confidence envelope for a declared complete-outcome target

For each family let `L_g<=X_g<=U_g` be its completion bounds, with all three in `[-1,1]`. Preserve the same independent **complete-data** family outcomes and fixed-weight conditioning as in §4, and let

`bar L=sum_g w_g L_g`, `bar U=sum_g w_g U_g`.

No ignorability or independence of the missingness mechanism is needed. The following interval covers `theta_w` with probability at least `1-alpha`:

$$
 [\max(-1,\bar L-r_\alpha),\min(1,\bar U+r_\alpha)].
\tag{R5}
$$

**Proof.** Write the latent complete-data mean as `bar X=sum_g w_g X_g`. Pathwise, `bar L<=bar X<=bar U`, irrespective of how grades become missing. Hence `[bar L-r_alpha,bar U+r_alpha]` contains `[bar X-r_alpha,bar X+r_alpha]`. The latter contains `theta_w` with probability at least `1-alpha` by (R4), so the larger interval does too. Intersection with the known parameter range preserves coverage. Equivalently, failure at the lower endpoint implies `bar X-theta_w>r_alpha`, and failure at the upper endpoint implies `theta_w-bar X>r_alpha`; each tail costs at most `alpha/2`. ∎

Thus the same radius as (R3) suffices for both endpoints. It is not necessary to use two two-sided bounds and pay an extra factor of two. Even a global research budget or outcome-adaptive grading schedule may induce arbitrary dependence in **missingness** across families without invalidating this pathwise argument. The preassigned complete-data outcomes must nevertheless be well defined and independent across families under the target execution law. Shared mutable environment state or resource contention that changes the outcomes themselves, rather than only whether they are observed, is a distinct threat. Adding or dropping assigned roots adaptively would also change the fixed weights/design assumption. This proof is stronger than concentrating the random lower and upper endpoints separately, which would unnecessarily require their independence across families.

**Action:** label existing exports `realized_assignment_completion_bounds`; export (R5) separately with alpha, family weights, target, complete-data independence assumptions and limitations. Do not convert the midpoint of a completion interval into an efficacy estimate. Do not label an interval as certified merely because its formula is conservative under assumptions that the collection design does not satisfy.

## 6. A concrete endpoint mismatch to resolve before a real run

At baseline line 91, the analyzer rejects any numeric outcome when `artifact['output'] is None`, even if the offline grade is a declared failure zero. The protocol says a service failure **can** be zero under a declared deployment-success endpoint. That optional composite endpoint is therefore not implemented by the current analyzer; it currently treats missing artifacts as ungraded outcomes and bounds them.

This is a pre-run contract gap, not evidence that old results should be retrospectively relabeled. Choose and freeze one contract:

* Keep the current behavior and explicitly state that unavailable outputs remain unknown in the reported bounded-quality target; or
* Define a composite endpoint with an audited set of actual service-failure reasons assigned zero, distinguish attempted failures from budget-unattempted slots and absent grading, and implement/test that exact rule.

An unattempted branch caused by a research collection cap is not automatically a deployed policy failure. A missing evaluator result is not a receiver failure. No indiscriminate `None -> 0` conversion is acceptable. Likewise, the current `receiver_identity_gate` only checks model identity/fatal status; it is not itself certification of grading validity or family independence.

## 7. Thresholds, power, futility and multiplicity

The supplied paired-binary planning numbers are arithmetically correct for a superiority-against-zero illustration: with `delta=.03`, variance `discordance-delta^2` and multiplier `(1.96+.84)^2`, sample sizes are `863.271`, `2605.493`, `4347.716`, rounding upward to `864`, `2606`, `4348`. They are not a guarantee under 24 development roots or a family-dependent design. With averaged replicate outcomes the root contrast need not be binary; use its paired-root variance, not the one-draw discordance identity without adjustment.

Power to show `theta>delta_star` at alternative `theta=delta_alt` depends on the separation `delta_alt-delta_star`, not `delta_alt` alone. The current `.03` calculation is not power for a lower bound exceeding a `.03` useful-gain threshold. No new sample-size threshold is proposed here; freeze the actual target claim and attainable precision before collection.

The protocol's distinctions are sound: a lower bound above zero supports superiority; a lower bound above `delta_star` supports a stronger useful-benefit claim; an upper bound below `delta_star` supports futility for that magnitude; a wide interval is inconclusive. A small positive effect can simultaneously be statistically superior and too small to be useful. That is not a contradiction. These conclusions require the selected interval to have the stated coverage for the declared target.

The analyzer currently exports six **unadjusted** contrasts and does not implement primary-contrast selection, thresholds, multiplicity or a release decision. This is acceptable for its declared development scope. It cannot support a post-hoc "at least one prompt wins" claim at 5% error merely because one unadjusted interval excludes zero. For `m` predeclared primary contrasts, the bounded-family alternative can use `alpha/m` for each contrast; equivalently use radius `sqrt{2 log(2m/alpha) sum w_g^2}` for simultaneous coverage. No independence across contrasts is needed. This controls error under the underlying family assumptions; multiplicity correction cannot repair invalid marginal intervals or test-set policy selection.

If one frozen contrast is the sole confirmatory claim, other contrasts can remain clearly labeled exploratory. Define whether success requires all conditions or any of several claims: that determines whether a union correction is needed. Reusing the test set to choose the comparator or policy still violates the frozen-policy premise even if six displayed intervals have been adjusted.

## 8. Minimal actionable resolution

1. Preserve existing results and their exploratory normal-interval labels.
2. Freeze equal-root versus equal-family weighting and the specific expectation/population target.
3. Distinguish completion bounds from uncertainty for the expectation; a new bound export should state its complete-data family independence and fixed-weight assumptions. Arbitrary missingness is allowed by the pathwise bound, but shared state that changes complete-data outcomes needs a separate argument.
4. Resolve the service-failure endpoint before real grading; preserve missing evaluation and unattempted slots distinctly.
5. Keep development decisions descriptive. Implement the one declared primary target, appropriate multiplicity and prospective thresholds only when the confirmatory contract is complete.

This audit finds no new efficacy evidence and changes no full-project readiness claim. Prospective measurement validation, defensible family/sampling construction, fresh-root policy evaluation and practical cost comparison remain outstanding.

## 9. Independent review of the candidate inference patch

After reporting the baseline findings, reviewed the coordinating agent's uncommitted patch to `experiments/landmark/analyze.py` with SHA256 `f05c786b01ab8b92e8a4bfb0fb166171272977858ccb89875545723104f10719` and `tests/test_landmark_inference.py` with SHA256 `6c2bef1cc4d88d71dbffb8d702e69478491c282eb4f55c50c50529a2aa0224db`. The review is of these bytes; later changes need their own check.

**No blocking mathematical or target-weighting defect found.** The new `bounded_family_interval` implements radius `(hi-lo)*sqrt{.5*sum_g w_g^2*log(2/alpha)}`. This agrees with (R3) for contrast range `[-1,1]` and the sharper arm-quality radius for `[0,1]`. It uses all assigned roots, keeps the equal-root weights fixed, expands the completion endpoints, clips to the known support, and suppresses the exported interval if the receiver/collection gate fails. The stated target is the expected equal-root mean for the prespecified family sizes, conditional on design/training; the function explicitly disclaims an arbitrary random-size population-ratio or transport interpretation.

The analyzer predefines four quality endpoints and six contrasts and allocates `.05/10=.005` to each. Union bound supplies at least 95% simultaneous coverage for these ten intervals under their assumptions; no cross-endpoint independence is needed. This allocation is distinct from the retained unadjusted exploratory normal intervals. Repeated looks, chosen policies, changed endpoints, and searches over different splits are explicitly outside the reference family. For 24 equally weighted independent families, the exported simultaneous reference radii are `.7066036458` for contrasts and `.3533018229` for quality. No precision or release claim is inferred from those large radii.

The new tests are meaningful checks of: the zero-estimated-SE counterexample; exact small-binomial coverage when all negative outcomes are withheld; invariance to multiplying the number of perfectly dependent roots within each family; worsening weight concentration under unequal family sizes; full missingness; gate suppression; and invalid input rejection. The outcome-selected-missingness test uses `[-1,1]` for each hidden negative and `[1,1]` for each observed positive, so it tests valid completion bounds. It is a finite example, not a proof for every missingness mechanism; the pathwise proof above supplies that generality. Independently ran `uv run --extra dev pytest -q tests/test_landmark_inference.py`: **8 tests passed**.

Remaining pre-run requirements are substantive design/measurement matters: true family independence, a declared sampled population, valid bounded complete outcomes and evaluator, fixed weights, and the failure-endpoint choice from §6. A hash or a valid concentration formula cannot establish them. This patch improves inferential honesty without issuing an empirical harm/superiority certificate or changing historical mock results.

## 10. Exact diagnostic and manuscript consistency check

Created and executed `scripts/check_landmark_inference.py` with immutable output `results/landmark_inference_20260920/exact_checks.json`. The command was:

```bash
python3 scripts/check_landmark_inference.py --output results/landmark_inference_20260920/exact_checks.json
```

The script refuses overwrite. It hashes the executed script, analyzer and collector before importing the analyzer and verifies that those bytes have not changed when checks finish. It records Python version and the contextual Git revision, while explicitly recording that working-tree hashes, not merely the commit identifier, identify the executed implementation. Script SHA256 is `b3edaecaf13b1df042e8c5c3ec1595157ac6c3ff9be0dfc2b04307f5f6050723`.

The audit enumerates all 25 binomial counts for the §3 example with exact rational probabilities; interval endpoints use the actual analyzer's floating-point implementation. Probability mass sums exactly to one. The exact-law coverage values are:

| Procedure | Coverage in this law |
|---|---:|
| Exploratory normal interval, nominal .95 | .912777410 |
| Bounded single-endpoint interval, nominal .95 | .999947938 |
| Bounded endpoint using .05/10 error | .999992806 |
| Bounded .95 interval with a globally dependent outcome-selected missingness rule | 1.000000000 |

The last rule reveals every observation only when all complete outcomes are positive, otherwise withholds them all. Its observed missingness pattern is dependent across families. The complete outcomes remain independent, so the pathwise containment proof still applies. The script also checks unequal-family weights, complete missingness, identity-gate suppression and unchanged radius after fivefold duplication within families. All assertions passed. The high bounded coverage values are specific to this deliberately small finite law, not a claim of empirical precision or a new universal coverage estimate. The ten-endpoint guarantee comes from the union argument; the diagnostic does not pretend that one endpoint's enumeration independently verifies ten actual LLM endpoints.

Also read the new `manuscript/landmark_methods_20260920.md` and revised landmark protocol. Their statistical paragraphs correctly state the fixed-weight target, .9^24 event, pathwise missingness argument, ten-endpoint allocation and prohibition of an ATE-based personalization futility gate. The protocol now explicitly chooses the current implementation's treatment of unavailable artifacts as missing, resolving the optional composite-endpoint wording mismatch. The remaining condition is clearly stated in the supplement: confidence for an all-assigned complete-data expectation requires a well-defined latent bounded outcome for every slot. "Quality of an available artifact" does not by itself define the score of a genuine no-artifact failure; that substantive measurement assumption still needs justification before using the reference interval for such a run.
