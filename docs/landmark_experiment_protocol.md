# Landmark prompt-choice experiment: reviewable collection contract

20 September 2026. This implements the next scientific step in the [governing judgment](scientific_judgment_20260920.md). **Status: protocol and harness development; not a frozen real-model trial.** The receiver, fresh task source and evaluator contract must be completed before a real-run manifest can pass. The available benchmark roots are reused development material.

The [21 September literature amendment](literature_guided_design_20260921.md)
adds prospective information/strategy controls, final-answer accounting and
versioned source reuse. It does not mutate the existing seven-root contracts or
release a new collection. The new five-arm extension is a separately frozen target.

## Question and scope

For a fixed receiver and a declared distribution of initial conversation histories, can a policy using public history choose a supported next prompt that improves expected final quality over a competent fixed prompt at the same continuation horizon? This is a conditional mean decision problem, not identification of the realized effect for one conversation. The first experiment ends after one additional receiver response. It cannot establish the value of a long autonomous regime under the different histories that regime would induce.

There are two separate stages. A bounded development batch validates the observation and intervention contract and estimates feasibility/variance. A later locked policy comparison requires an untouched root/family evaluation set. Collecting new responses to already inspected tasks is new interaction data on reused tasks, not fresh out-of-task confirmation.

## Intervention contract and competing explanations

Generate one initial answer from a pinned system message and public task. Preserve that complete prefix, exact messages and hashes. The development harness evaluates each named continuation on independent restored branches, in randomized order with separately recorded seed streams. All three arms are evaluated: branch inclusion probability is one, not a fabricated one-third treatment propensity. Randomized order is a scheduling design and its probability has a different meaning. A later single-action logger must explicitly use and log its actual assignment probabilities.

| Arm | Permitted input and operation | Question it addresses |
|---|---|---|
| Generic repair | Exact initial prefix plus a frozen generic revision instruction | Does another attempt retaining the first answer help? |
| History-specific repair | The same prefix and public information plus a deterministic, frozen instruction derived from it | Does this specified history-dependent wording help beyond generic revision? |
| Independent restart | Same original task/public information and receiver, without the initial assistant answer | Is retained answer/context better than spending the call on an independent draw? |
| STOP | Accept the existing initial answer; no further generation | Is another call worthwhile? |

Restart deliberately changes the receiver context; it is a different continuation strategy, not a clean comparison of wording alone. Both repair arms must have identical answer-relevant public evidence. If a public check is run after the initial answer, both receive the same raw check result before their different instructions. Do not provide a hidden failure trace, reference answer, or selected grading input to any arm. Hidden outcomes enter only the offline grader. A simple format/structure-derived prompt is a limited intervention and must not be described as a trained semantic critic.

Run two independent continuation seeds per arm in the proposed development batch. This gives a first indication of receiver noise; it does not provide accurate pointwise confidence intervals or a new pair of independent tasks. Evaluate all frozen arms irrespective of initial hidden correctness or public-pass status. A checker pass does not terminate the mechanism comparison; public-check absence is recorded as absence, not success. This all-branch design is distinct from a deployment stopping policy.

## Measurement and immutable records

The public task file is strictly separated from a private grading file. Freeze their versions/hashes and root mapping; verify that hidden scores cannot enter requests, prompt rendering, action selection or public logs. A usable scoring contract needs reference acceptance, deliberately wrong/control rejection, split provenance, and sandbox isolation; syntactic nonoverlap alone does not establish semantic isolation. Preserve the old full-benchmark labels as a different endpoint. The bounded-quality target is the score that each prespecified continuation would receive under reliable execution of the frozen receiver/decoding law, including a produced but malformed or empty answer as a graded failure under the frozen parser. It is neither quality conditional on observing an output nor the reliability of the deployed service. Infrastructure loss leaves the intended continuation score unobserved. If that latent complete-data outcome law cannot be defined or the observed executions do not preserve it, the confidence reference does not apply.

Store every assigned root and arm/replicate slot, requests/responses, exact prompts, common-prefix identity, randomized execution order, seeds, model and service identity, decoding/context limits, input/output usage, timing, source hashes, failures and missing grading. No successful-output filtering. The current adapter estimates output quality: unavailable model outputs and absent evaluator results remain missing. It does not implement a deployment-success composite that codes service failures as zero; that alternative requires a separately versioned endpoint and explicit failure mapping. Unattempted budget-limited slots must never become observed failures. The analyzer reports all-assigned completion bounds and suppresses its complete-case confidence interval when required outcomes are missing; never silently interpret incomplete pairs as the full population.

Before actual collection, the environment adapter must show that restored branches do not share mutable conversation, tool or cache state that changes their outcome law. Passing the same client messages is a necessary record, not sufficient proof of server independence. A model digest and server/template version must be independently verified, not merely copied from a user-supplied label. Avoid silent context truncation and record the tokenization/context contract.

## Analysis and advancement

Average repetitions within each root before forming paired arm or policy contrasts. Split training, development and evaluation at the root/family level. A selector is frozen using training/development only and may access only deployment-available inputs. The fixed comparator is selected on training data, never retrospectively on evaluation outcomes. Report both repair contrasts and restart/STOP context; do not pick the favorable contrast after seeing the results.

The current point estimate weights roots equally, so a family with more included roots receives greater weight. This differs from an equal-family target. Freeze the root/family sampling rule and target weights before outcomes; do not let curation or observed performance silently redefine the population. The normal family-cluster interval remains an exploratory approximation, even when its estimated variance is zero. The v2 analyzer additionally exports conservative Hoeffding reference intervals for the expected equal-root mean under **fixed family sizes/weights and independent complete-data families**, with Bonferroni control across its four arm means and six fixed contrasts. These bounds do not establish independence, coverage for a random-size population ratio, repeated-look validity, or transport to other tasks. Missing-outcome completion bounds by themselves concern the realized run; they are not population confidence intervals. See the [independent inference review](landmark_inference_review_20260920.md) and [manuscript methods supplement](../manuscript/landmark_methods_20260920.md).

**A zero marginal prompt effect is not a stopping rule.** Opposite useful effects at different histories can cancel. Conversely, the best observed outcome among noisy branches is not an attainable conditional-mean oracle. Use the [landmark theory](landmark_prompt_theory.md) and [known-truth premise study](landmark_premise_results_20260920.md) to distinguish average effects, predictable conditional differences, learned-policy gain, and post-outcome selection. Merely observing different scores across branches does not prove exploitable heterogeneity.

The development batch's success criterion is valid collection and interpretable uncertainty, not statistical superiority. Before a confirmatory trial, fix one primary policy contrast, an application-justified useful-gain threshold, confidence level, target precision and resource constraint. A lower confidence bound above zero supports superiority; a lower bound above the useful-gain threshold supports that stronger claim. An upper bound below the threshold supports futility for that declared benefit, while a wide interval is inconclusive. Adjust for any multiple primary claims and allow the noncausal-branded, history-adjusted learner to win.

The [precision and decision table](landmark_precision_plan_20260921.md) makes this
limit numerical: even seven hypothetical independent singleton roots all showing
the maximal contrast +1 cannot exclude zero using the conservative single-contrast
reference. The actual shared unresolved-family slate is less informative. This
does not prove that other valid procedures cannot detect an effect. Keep this
batch for engineering, and define a separate affordable evaluation design for the
frozen policy; do not retroactively remove multiplicity or inflate the root count
with continuation repetitions. The current analyzer reports arm summaries, not
an already implemented independent learned-policy comparison.

For an independently sampled paired binary contrast, planning uses `Var(D)=p_gain+p_harm−Delta^2` on all roots, not only oracle opportunities. The usual normal approximation is `n≈(1.96+.84)^2 Var(D)/delta^2`; this is a planning illustration, not a guarantee. At delta=.03 and total discordance .10/.30/.50, the approximation needs about 864/2,606/4,348 roots. Family dependence increases the requirement. Repeated branches can lower conditional seed noise but do not remove between-root variation. Use pilot variance with a justified allowance for its uncertainty and freeze the final design before evaluating the policy.

## Proposed bounded development budget

Use at most 24 explicitly development-only roots × (one initial call + three arms × two repetitions) = **168 calls**, with at most **512 completion tokens per call**, **86,016 reserved completion tokens**, **20 minutes**, and **$0 external spend**. These are ceilings, not authority to launch an incomplete manifest. Record prompt tokens separately; a completion-token reservation is not an exact total-token cap. Require an 8,192-token context contract or revise/freeze it explicitly for the selected receiver. No service startup that disrupts a concurrent job; no new large model download or training.

If a smaller cached receiver is used for engineering feasibility, name it explicitly and do not extend the earlier 3B/7B empirical claims to it. The current absence of a running service is not an efficacy finding. The lack of untouched available roots prevents confirmatory labeling, not CPU development or an honestly labeled reused-task pilot.

## Required before real-run release

The release manifest must pin the exact receiver/digest, server and template, dataset and prior-use exclusions, family split, evaluator/sandbox, initial/prompt renderer, seed/order design, failure endpoint, costs, code/config hashes and numerical ceilings. A clean committed freeze and measured environment preflight must precede calls. The present mock tests and synthetic study validate software/statistical contracts only. They do not substitute for that release or demonstrate prompt improvement.
