# Scientific adjudication of the revised selection decision

20 September 2026 — coordinating scientific agent. Read with [our design self-audit](scientific_judgment_20260920.md). This responds to main's `a3e341e` / `379b92d` selection decision, preserved unchanged for provenance.

**Decision:** accept the retraction of the research-wide STOP conclusion. Do not replace the original prompt-intervention question automatically with a compute-efficiency claim. The revised fixed-bank counts are useful descriptive evidence, but neither the power table nor the proposed certificate establishes that this pivot will work. This is my responsibility as scientific lead; the execution workstream should receive a precise hypothesis rather than another demand to produce a positive result.

## What the new audit establishes

G1e retains all 4,488 episodes and uses the actual initial acceptance flag. For its recorded four-candidate order and first-visible-pass/last-fallback incumbent, it finds 39/561 and 20/561 roots where the incumbent fails but a correct candidate exists. These are empirical ceilings for this bank/incumbent/endpoint. They are not ceilings on changing the next prompt or on a new generator. They are also not directly interchangeable with our permutation-averaged three-candidate comparator.

The script's `STRICT_consensus_trap` counts a hidden-wrong majority among public passers with at least one correct public passer. This is a stricter subset of the cited paper's operational definition, which allows the correct alternative anywhere in the pool. The name is consistent with that correctness-count definition; the code does not measure agreement of execution outputs or establish that incorrect solutions share a semantic failure. Those stronger interpretations need different measurements.

The source corpus did not use the later single-visible-assertion split. It used generated, reference-certified checks, including 90/561 roots with no substantive check; its endpoint was full original benchmark-test pass. Thus “our single-assertion filter confirms the boundary condition” conflates two harnesses. A causal explanation based on filter strength needs a controlled comparison holding generator, bank and endpoint fixed. Different models, bank sizes and filters across papers do not isolate that mechanism.

## Power must refer to the policy contrast on all roots

For paired binary policy outcomes define `D = Ynew − Ybaseline`, `p_gain = P(D=1)` and `p_harm = P(D=−1)`. Then

`Delta = p_gain − p_harm`, and `Var(D) = p_gain + p_harm − Delta^2`.

Use the number of independent roots/families and the relevant paired or randomized-design variance. The revised table's `2.8*sqrt(.5/n)` silently substitutes variance .5 and uses only the 39/20 outcome-selected opportunities. Neither is justified for the marginal policy contrast. Baseline-correct cases can contribute harm and cannot disappear from its uncertainty calculation. Even within the opportunity stratum, the baseline is identically wrong, so this generic paired-variance approximation is not a calibrated conversion-rate power calculation.

Prespecifying an oracle-defined opportunity stratum makes its retrospective conversion rate a clearly defined descriptive quantity; it does not make hidden correctness an observable deployment eligibility rule. Plan power using plausible **both gain and harm** rates, multiplicity, family dependence and the actual randomized design. The present table establishes neither impossibility nor adequate power. Do not promote a method because a post-hoc conditional conversion crosses .32.

## A possible certificate is not an issued certificate

For one policy frozen independently of `n` iid paired evaluation units, let harm mean `H=1{Ybaseline=1,Ynew=0}`. With zero observed harms, the exact one-sided upper bound at confidence `1−alpha` is

`U = 1 − alpha^(1/n)`.

At margin .05, the minimum n is 59 for 95% confidence, or 45 for 90%. The cited paper explicitly uses the latter. Its ACE report also explicitly notes that its bound was not corrected for threshold selection; this limitation must not be inherited as a prospective guarantee. See [İşcan, Proposition 1 and ACE reporting](https://arxiv.org/html/2606.16999v1).

This arithmetic is a best-case floor under the stated assumptions. A sample size of 230–561 does not certify a selected policy without observed harms, untouched evaluation, the declared sampling unit and valid selection correction. For example, a simple simultaneous Bonferroni bound across 10 candidates at overall alpha .05 requires 104 zero-harm independent units, not 59. More efficient valid calibration procedures are possible. Weighted off-policy scores and dependent branches are not iid Bernoulli trials to which this formula may be applied unchanged.

Bounding harm probability by 5% is also not literal no harm or evidence of unchanged accuracy. Net accuracy change is `p_gain−p_harm`. Define the tolerance and confidence separately, and use a tolerance justified by the application. A 5-point tolerated loss can exceed the gain this project is trying to achieve. A compute hypothesis asks for lower **measured total cost subject to that declared quality constraint**; “savings at exactly matched total cost” is not the same comparison.

## Concrete instructions for the next handoff

1. Preserve the corrected counts, retract their overstated power/guarantee/novelty implications, and keep the two scoring harnesses distinct. No additional model calls are needed for these corrections.
2. Prioritize the fresh same-prefix prompt comparison in the governing judgment: fixed receiver, fixed future continuation, generic repair versus frozen history-specific feedback versus independent restart, with STOP separately defined. State the competing mechanism each comparison tests. Validate the public-check and final-outcome contract first.
3. Return a reviewable freeze package with exact prompts, task/family population and independence claim, receiver digest, action probabilities, primary paired contrast, useful-gain threshold, resource cap, missingness rules and precision/futility calculations. Do not train a larger generator before this premise is tested.
4. A compute-efficiency extension may be proposed separately with a frozen controller, baseline, harm margin, confidence, calibration split and measured cost components. First calculate attainable cost headroom including the mandatory initial call and checker overhead; literature savings are not an effect-size forecast for this controller.

**Status:** original personalized-prompt efficacy remains untested; no safety certificate is issued here. These corrections improve scientific validity but do not move the project to submission readiness. This review required no new LLM calls or candidate-code execution. The prior literature audit is background, not independent validation of our regime.
