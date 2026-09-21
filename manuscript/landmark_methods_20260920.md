# Supported prompt choice at a fixed conversation history

**Methods supplement, 20 September 2026.** This section supplements the earlier research draft. It describes the developed design and the proposed empirical study; it does not report a completed LLM trial. The full manuscript still requires integration with the longitudinal theory, scientific self-audit and future empirical results.

The current [results and discussion section](evidence_results_20260921.md) preserves
the corrected negative repair findings, selector split sensitivity and matched
estimator diagnostics. Its quantitative summaries were reconciled to stored records;
it does not supply a completed prospective prompt trial.

## Decision problem and identification

We study whether public information available at a conversation checkpoint can guide the choice of a next prompt that improves the receiver's expected final output quality. The receiver model, its decoding and service configuration, the task population, and the subsequent interaction horizon are components of the intervention. In the proposed landmark study, the horizon is one additional receiver response. Let H denote the public task and initial conversation, and let Q_a(H) be the mean final score under supported continuation a. The decision target is the value of a rule d(H), $E[Q_{d(H)}(H)]$, relative to a comparator fixed independently of the evaluation outcomes. A history-conditional mean is distinct from the unobserved realized effect of two prompts on one conversation.

The development design preserves one initial response per root task and evaluates generic repair, a frozen history-dependent repair instruction, and independent restart on separate continuations. STOP retains the initial artifact. The repair arms receive identical answer-relevant public evidence; their instruction wording differs. Restart removes the previous answer and therefore compares continuation strategies with different contexts, rather than isolating wording alone. All three continuation arms are included with probability one. Their randomized execution order balances scheduling conditions; it is not a one-third action-assignment probability.

Identification from these continuations requires a well-defined restored checkpoint, receiver stability, the declared seed law, and no interference between branches. Repeating the same client messages does not establish these conditions if hidden server or tool state changes. The public history may omit root-persistent information that affects outcomes. Repeated continuations can estimate a particular checkpoint's response means without making that omitted information available to a deployable policy. Furthermore, local branch comparisons do not identify the distribution of histories induced by a different multiround policy. Those claims require the separate longitudinal support and transport conditions in the main theory.

## Measurement and task population

The public task file contains only the task, a reviewed interface description and allowed context. A separate private grading contract binds each root to versioned assertions, setup and outcome rules. Reference acceptance is necessary but insufficient: an evaluator can accept the supplied reference while rejecting a different correct implementation or accepting an incorrect one. We therefore require specification review and discriminating controls in addition to reference checks. A test that requires an arbitrary reference-specific arrangement measures agreement with that implementation unless the specification actually requires that arrangement. Specification repairs create a documented task version; they cannot be silently introduced after treatment outcomes are observed.

Benchmark assertions withheld from the current receiver prompt are held-out evaluation material, not necessarily secret or previously unseen model-training material. Their absence from the public payload addresses one leakage route but does not establish freedom from memorization. Likewise, an unused task ID is not an independent family. Development-task selection, related-family screening and exclusions are recorded before receiver outcomes; the entire selected curation slate is retained, including rejected tasks. Any eventual efficacy claim must name the resulting eligible population rather than generalize automatically to the uncurated benchmark.

The source-only development curation illustrates why this review precedes outcome
collection. A fixed 24-task slate retained seven for contract review, without
replacement. A closer review then found that one retained reference returns an
unreduced value when the binomial coefficient's lower index is zero and its
modulus is one. The proposed contract explicitly permits that input. We preserve
the original reference and intended domain, record the discrepancy as a hold, and
require separate versioned validation of any correction. No benchmark execution
or receiver outcome supports this finding; it follows from source control flow.
The [contract proposal](../docs/landmark_task_contracts_20260920.md) clarifies public
definitions and adds private boundaries, defining a new development endpoint.
It does not retroactively alter historical scores or establish that this defect
explains the earlier repair findings. All seven tasks remain unvalidated.

The target endpoint is binary evaluator-defined quality for each prespecified continuation under reliable execution of the fixed receiver/decoding law. A produced malformed or empty answer is a failure under the frozen parser; a substantive test rejection is an observed zero. Infrastructure loss or evaluator failure leaves the intended score missing. The target is not quality conditional on observing an artifact, and the current implementation does not recode service failures as zeros in a deployment-success composite. All assigned slots remain in accounting. The bounded complete-data interpretation requires that this intended receiver outcome law be well-defined and preserved by the observed executions; it does not infer a score for an inherently undefined intervention. This distinction prevents a missing grade, an unattempted call or an empty test set from masquerading as an observed outcome. Passing execution-isolation checks and passing measurement controls are separate requirements: isolation concerns effects on the host, while measurement concerns what a recorded score means.

## Estimation and uncertainty

Repetitions are averaged within each root before constructing paired contrasts. Training, tuning and evaluation splits keep every root's continuations and related task families together. The current estimator assigns equal weight to each root, not each family. With fixed family sizes n_g and N total roots, family g receives weight w_g=n_g/N. The target is the expected weighted mean under this declared sampling design. If family sizes are random and the target is a population ratio, a separate sampling argument is required.

The family-cluster normal interval is an exploratory large-sample approximation. Its width is not reliable merely because all observed contrasts agree. For example, if 24 independent root contrasts equal +1 with probability .9 and −1 otherwise, their population mean is .8. All 24 can equal +1 with probability .9^24, approximately .080, yielding a zero-width normal interval at 1 that misses .8. An estimated zero variance therefore cannot justify a small-sample superiority or no-harm certificate.

For a conservative finite-sample reference, suppose complete-data family means are independent, their weights are fixed before outcomes, and their values lie in [a,b]. A direct application of the classical [Hoeffding inequality](https://doi.org/10.1080/01621459.1963.10500830) gives radius

\[
r_\alpha=(b-a)\sqrt{\frac{\log(2/\alpha)}{2}\sum_g w_g^2}.
\]

Use [0,1] for an arm mean and [−1,1] for a paired contrast. If missing outcomes yield pathwise lower and upper completion means L and U, the clipped interval [L−r_alpha,U+r_alpha] covers the complete-data expected mean under the same assumptions. This follows because L never exceeds the complete-data sample mean and U never falls below it; no missing-at-random assumption is used. The outcome must nevertheless be well-defined and bounded for every assigned slot. The raw completion interval [L,U] alone is about this realized run, not uncertainty about its expected value.

The analyzer uses alpha=.05/10 for each of four arm means and six declared contrasts, giving simultaneous 95% reference coverage by a union bound. This protects only that fixed family of endpoints at a fixed analysis time. It does not cover selecting policies on evaluation labels, unplanned repeated looks, unspecified dependence between families, or a different target population. The bounds will often be wide in a small development batch; that is an honest limit on information rather than evidence of futility. The accompanying [independent review](../docs/landmark_inference_review_20260920.md) checks the derivation and implementation. These are established concentration arguments specialized to the design, not a novel foundational result.

## Scientific advancement

The first bounded batch is intended to validate measurement, collection and variance estimation. It is not powered to establish a modest policy benefit. A later comparison must freeze the learned policy, a competent comparator, one primary contrast, a practically justified benefit threshold, precision and resource limits, and an independent evaluation design. A lower confidence bound above zero supports superiority; exceeding the useful-benefit threshold is a stronger claim. An upper bound below that threshold supports futility for that specified benefit, while a wide interval is inconclusive.

A zero marginal prompt contrast does not terminate personalization: opposite conditional benefits can cancel. Conversely, the best observed branch is a selection using evaluation outcomes and can overstate the value of any deployable rule. The completed known-truth study separates these cases; it supplies no empirical evidence that useful conditional differences are predictable in the proposed natural-language task population. The next scientific test is an independently evaluated, public-history prompt policy under a validated measurement contract. Larger generator development remains conditional on that evidence.
