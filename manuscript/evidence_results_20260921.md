# Diagnostic evidence and limits of adaptive-prompt claims

**Editable results and discussion section, 21 September 2026.** This section
updates the interpretation of the dated research PDFs and accompanies the
[landmark methods](landmark_methods_20260920.md). It integrates the historical corpus diagnostics and the subsequently collected
seven-task development pilot. No additional receiver data were generated for this
manuscript integration. A complete manuscript and independent prospective policy
validation remain pending.

## Evidence populations and endpoints

The historical real-model evidence includes a reused corpus of 4,488 episodes from 561
root coding tasks, with four initial draws for each of two receivers. Subsequent
receiver routing was randomized within an existing repair/check process. The
recorded endpoint is full benchmark-test success under that process's evaluator.
It is distinct from the later proposed private grading contracts. Task families
remain unresolved; root-level uncertainty below is exploratory and does not
certify generalization to independent families or other task populations.

This corpus supports diagnostics of the recorded repair regime and selection
among already generated candidates. It does not contain the proposed randomized
choice among next-prompt alternatives at a fixed receiver and history. Consequently,
these analyses cannot establish the primary history-conditional prompt-effect
claim. The [source audit](../docs/experiment_recheck_20260920.md) records the raw-log
hash, routing probabilities and corrected cohort definitions. All original
analyses remain available, with superseded interpretations labeled separately.

## Repair improves initial answers but trails the resampling comparator

The corrected analysis retains every root and uses the known routing probabilities
to evaluate the regime that retains the initial receiver on subsequent eligible
repair calls. A paired-change estimate separates weighted repairs from weighted
damage without unnecessarily reweighting the observed initial verdict. The
resampling comparator averages all ordered triples drawn from each root's four
initial candidates, accepting according to the recorded public check and otherwise
continuing up to three candidates. Hidden evaluation outcomes do not determine
its stopping or selection. This is a reused-data comparison, not a prospective
head-to-head trial of exactly matched total cost.

| Diagnostic | 3B receiver | 7B receiver |
|---|---:|---:|
| Repair-regime gain over the initial answer, percentage points | +2.85 | +1.60 |
| Adaptive three-draw resampling gain, percentage points | +7.78 | +3.31 |
| Repair minus resampling, percentage points | -4.93 | -1.71 |
| Exploratory 95% root interval for that contrast, percentage points | [-6.60, -3.27] | [-3.18, -0.23] |
| Estimated mean calls, repair / resampling | 1.4198 / 1.3780 | 1.2986 / 1.2879 |

The [mechanism report](../docs/repair_mechanism_diagnosis_20260920.md) preserves both
the paired-change and earlier raw-IPW estimates. The earlier raw-IPW 7B interval
crossed zero; reducing baseline-weight noise changes the interval without creating
independent evidence. The current comparison does not establish exact cost parity,
and calls alone do not measure tokens, latency or checking overhead.

Lower repair yield accounts for most of the 3B deficit; both lower yield and
damage to initially correct outputs contribute for 7B. The common public stopping
signal also misses many initial failures. Because both policies share that signal,
it cannot by itself explain their performance difference. The data do not isolate
feedback wording, diagnostic quality, retention of an unproductive answer in context
or receiver capability as the cause. The negative result is retained for the
tested regime, while these competing mechanisms motivate a same-prefix comparison.

## The favorable fixed-bank selection result is small and split-sensitive

A corrected logistic selector uses public candidate features to choose among all
four initial artifacts. Training and evaluation contain 336 and 225 roots,
respectively. A diagnostic analysis repeats the fixed learner over ten declared
split seeds; it does not produce ten independent studies because the test sets
overlap and the underlying labels are reused.

| Gain over the public-check selector, percentage points | 3B receiver | 7B receiver |
|---|---:|---:|
| Original split | -0.07 | +2.85 |
| Median over ten overlapping splits | -0.76 | +0.83 |
| Range | [-2.63, +1.11] | [-0.11, +2.85] |
| Number of positive splits, descriptive only | 1/10 | 8/10 |

The original 7B split is the most favorable of these diagnostics. The median is
a descriptive stability summary, not an independently validated effect estimate;
neither positive-split counts nor pooled intervals can turn overlapping splits into
replications. This is at most a development signal for completed-candidate
selection. It is not evidence that a history-specific next prompt works better,
or that a four-candidate selector beats a cheaper stopping policy at equal total
cost. Public features available after generating a bank are admissible at that
selection time; the same future outputs are unavailable at an earlier prompt-choice
decision. See the [selection records](../results/selection_sensitivity_20260920/summary.json)
and [decision-time audit](../docs/experimental_status_rulings_20260921.md).

## A fresh development pilot establishes execution, not personalized benefit

A subsequent development study collected new interactions with a pinned Qwen2.5-3B
receiver on seven previously inspected coding tasks. Each task supplied one initial
answer, two generic-repair continuations, two continuations using a deterministic
syntactic cue, and two independent task-only restarts. Both repair arms retained the
same initial prefix; restart omitted the old answer. STOP accepted the initial answer.
Every continuation arm was included for every task. Randomized execution order did
not constitute randomized single-action assignment. The endpoint was success on a
separately versioned private suite, distinct from the historical corpus endpoint.

The final v1c grading records include seven accepted references and rejection of
17 prespecified wrong-program controls. Review of the initial measurement design
had exposed two suites that failed to distinguish plausible wrong implementations;
the revised suites and the modulus-one reference repair were versioned separately.
These checks support the declared finite instrument, not correctness on every input.
Source and saved-record audits confirmed the recorded collection/grading bindings;
they did not independently repeat live execution or establish a complete receiver-law
freeze. In particular, postflight source checks verified the weight digest but did
not substantiate all claimed build/context/template checks.

| Strategy | Passed artifacts | Mean over the seven roots |
|---|---:|---:|
| STOP | 5/7 | .7143 |
| Generic repair | 9/14 | .6429 |
| Syntactic history-derived cue | 9/14 | .6429 |
| Independent task-only restart | 9/14 | .6429 |

Each continuation mean first averages its two repetitions within a root. The cue
renderer selected a loop instruction on three roots and a general checklist on four.
It received no executed public diagnostic or identified semantic discrepancy. Thus,
its aggregate tie with generic repair concerns these simple instructions; it is not
a test of validated diagnostic feedback. Across the two initially incorrect roots,
repair continuations corrected zero of eight attempts and restart corrected one of
four. Across five initially correct roots, four of 30 continuation attempts failed.
These conditional counts are descriptive and are not independent task observations.
The contrast between cue and generic repair varied across two observed roots, but
neither this variation nor a zero aggregate contrast establishes predictable
conditional-mean heterogeneity or its absence.

All seven tasks retained an unresolved-family label, and population intervals were
suppressed. Fourteen paired branch observations cannot be treated as 14 independent
roots. Their single-pair discordance does not directly supply the variance of a
two-repetition root mean. The resulting earlier assertions that a five-point effect
was infeasible or that a ten-point study would establish absence of that benefit
were not supported. Neither the seven-task pilot nor the separate mechanical screen
of 396 candidate IDs establishes the count of independent eligible evaluation families.

Three collections reused the same seeds and requests and reproduced the same 49
outputs. Together they used 147 receiver calls, 29,892 prompt tokens, 9,486 completion
tokens and 265.153 seconds of recorded collection time, with $0 paid API expenditure.
These are repeated engineering executions, not three independent efficacy studies.
Within the final run, cue, generic and restart arms used 4,920, 3,856 and 2,918 tokens,
respectively, despite equal call counts and per-call caps. Exact total-cost parity
was not established. Regrading and metadata corrections should preserve the outputs
and create linked derived artifacts rather than repeat receiver collection.

The [independent development review](../docs/development_delivery_judgment_20260921.md)
and [record-level audit](../results/development_delivery_lead_audit_20260921.json)
retain the completed observations, source versions and limits. The useful result is
that the observation and grading pipeline operated on these tasks. The scientific
question of beneficial, learnable next-prompt choice remains unresolved.

## Matched estimator diagnostics show no general DR advantage

The synthetic comparison uses identical fitted Q functions, folds and target
policies for plug-in regression and DR. Five conditions each contain 80 paired
replications. These 400 evaluations include 79 base-condition seeds reused from
an earlier corrected grid, so they are not all additional independent datasets.
The working Q model compresses history to state and time; known logging scores
are supplied. This is not a comparison against every adequate full-history
regression and does not validate propensity estimation from unavailable information.

| Synthetic condition | Plug-in RMSE | DR RMSE |
|---|---:|---:|
| Base | .01546 | .01517 |
| Uniform logger | .01219 | .01224 |
| Latent-dependent logger with known scores | .01450 | .01481 |
| Declared template mixture | .01506 | .01533 |
| Weak overlap | .07296 | .09872 |

In the first four conditions, the approximate Monte Carlo intervals for paired
squared-error differences include zero; this does not establish equivalence.
Under weak overlap, DR's paired mean squared-error excess is .00442, with
approximate Monte Carlo interval [.00106, .00778]. Absolute empirical bias falls
from .0543 to .0158, but increased variance worsens RMSE; DR's recorded Wald
coverage is 81.25%. This finite-sample bias–variance problem is compatible with
the population robustness identity. Neither the identity nor value-estimation
accuracy guarantees better conditional rankings or deployed prompting decisions.
The [stored diagnostics](../results/matched_estimator_diagnosis_20260920/summary.json)
retain all conditions; the next empirical study must allow an appropriately
adjusted regression comparator to win.

A subsequent [exact population diagnostic](../docs/history_compression_results_20260921.md)
quantifies one limitation of this working Q model. Its state/time compression
induces bias of -.001387 in the base law and -.008726 under weak overlap; the
oracle full-observed-history value agrees with exact truth. The uniform-logger
aggregate control has zero bias. The weak-overlap population compression error
is smaller than the earlier finite-study bias of -.054293, so compression alone
does not explain that result. Finite-data estimation and sparsity remain unresolved.
This is a known-law reference, not a trained full-history comparator or new
receiver evidence; synthetic observed states also contain correctness information
not automatically available to a deployed coding policy.

A subsequent frozen [empty-cell sensitivity analysis](../docs/sparse_cell_diagnostic_results_20260921.md)
replayed all 80 weak-overlap seeds and recovered every original estimate. Replacing
only absent training cells by known population compressed-Q values, before
recomputing upstream targets, reduced plug-in RMSE from .07296 to .03251 and DR
RMSE from .09872 to .05582. The paired plug-in estimate increased .04864
(approximate Monte Carlo interval [.04098, .05630]); the paired DR mean shift
was .00073 [-.01405, .01551]. This unavailable oracle substitution establishes
material sensitivity to the specified fallback in the reused diagnostic; it does
not identify a unique decomposition of error or demonstrate a practical repair.
Sparse nonempty cells, learned full-history comparisons and valid finite-sample
uncertainty remain unresolved. These are the same replications, not new validation.

The [known-assignment inference clarification](../docs/known_assignment_inference_20260921.md)
separates those observations from a stronger claim about asymptotics. With exact
assignment probabilities, a fixed evaluation policy, independent root folds and
L2 convergence of root scores to a deterministic limit with finite positive
variance, the usual root-score variance is consistent even if the Q limit is
misspecified. This sufficient-condition result does not establish those conditions
or accurate finite-sample coverage in the present study. In particular, the
oracle-fallback RMSE improvement is not a validated confidence-interval repair.

## Interpretation and next empirical test

The current evidence justifies a narrower empirical sequence. Complete receiver-law
verification and validate the public diagnostic instrument, building on the scoped
execution evidence above. Then compare supported continuation strategies
from a common public history, with frozen prompts, continuation, information and
cost rules. Evaluate a frozen public-history selector against competent fixed and
sampling comparators on independent task/family information. The proposed
[literature-guided amendment](../docs/literature_guided_design_20260921.md)
separates diagnostic availability from instruction strategy; its five-arm design
is implemented, and its bounded instrument-validation bundle has passed the declared gates on the worker host. Independent review reconciled 13 saved artifact hashes and records accounting for 77 isolated starts, including seven accepted references and 17 privately rejected controls. This establishes the stated finite validation checks, not general evaluator correctness or prompt efficacy. Grading/analysis command-line integration and receiver ownership remain unresolved; model collection is not released.
The [exact subsequent proposal](../docs/public_diagnostic_design_20260921.md) gives
both repair arms identical public diagnostic bytes, then compares neutral and
diagnostic-directed instructions. Its examples are disclosed before the initial
answer, changing the initial-history law relative to the pilot. It is explicitly
outcome-informed development; a later policy comparison requires untouched roots
and a frozen comparator. Its context-removal arm retains diagnostic observations
about the old answer and is not the task-only restart reported in the table above.

The proposed diagnostic comparison also has a specific measurement limit. The public
examples exercise many of the same error classes as the private suites, although
none repeats a private input literally. Their disclosure is part of the declared
intervention environment for every arm. Thus, a favorable contrast would concern
performance under that shared information; it would not demonstrate transfer to
entirely unseen error classes. We retain the examples and private assertions rather
than selecting a more favorable split after inspecting the pilot. Planned summaries
will cross-tabulate initial public diagnostic status with the initial private
verdict, retaining unavailable diagnostics explicitly. Final private outcomes will
also be described by initial diagnostic status. These summaries do not validate a
learned policy on new tasks, and no final-public-pass rate can be reported without
actually checking the final artifacts on the public instrument. The
[reviewed design decisions](../docs/lead_review_mrl05_08_20260921.md) specify these
limits and the implementation requirements; this study has not yet been executed.

Receiver reproducibility is a separate limitation. The historical requests recorded
only part of the decoding configuration. Later observations make particular server
defaults plausible during collection, but cannot retroactively turn those defaults
into contemporaneous measurements. The proposed successor records explicit request
settings and checks receiver state before, during and after collection. Those checks
provide evidence at observed times; they do not prove absence of intervening changes,
exclusive access to the service or deterministic outputs. The independently identified receiver-guard repairs are implemented and reviewed as
source/mock code. Executed instrument validation and a current receiver ownership
agreement remain required before model collection. Nongenerating preflight observed
the same receiver-state digest at 14:55 and 19:45 UTC and matching request sampler
settings at the later snapshot; these observations do not establish continuous stability.

Future policy validation uses a newly declared working usefulness threshold of five
percentage points in private-suite success, with ten points as a planning alternative.
This is not an estimate from the pilot or a validated user-utility threshold. Existing
sample-size scenarios illustrate sensitivity to family structure and variance; they
do not certify power or establish the number of eligible independent families.
The current variance simulations check a specified synthetic covariance construction,
not confidence-interval coverage. The provisional studentized procedure must be
assessed against the eventual family design before confirmatory collection, with
its asymptotic interpretation kept separate from a prespecified conservative
finite-sample sensitivity analysis. No confirmatory sample size is released.

A zero marginal arm contrast is not a personalization futility criterion, because
conditional differences can cancel. Conversely, selecting the best observed branch
uses evaluation outcomes and does not establish achievable benefit. The completed
[known-truth diagnostic](../docs/landmark_premise_results_20260920.md) illustrates
both distinctions under its specified synthetic laws. It supplies no evidence
that natural-language histories contain a useful, learnable effect-modifying signal
for the proposed receiver and population.

The separate [offline graph component](../docs/graph_offline_validation_20260921.md)
validates data-only grading and provenance. Its complete public verifier and cheap
algorithmic solution make it a controlled measurement extension, not evidence of
practical LLM utility or replacement for the coding population. Neither passing
software checks nor adding standard theory results closes the empirical gap.
The primary prompt-personalization benefit remains unestablished. Larger generator
development awaits that evidence; a compute-efficiency hypothesis requires a
separately declared quality/cost contract and cannot silently replace this target.

## Numerical traceability of this section

The lead independently recomputed the repair table from 1,122 stored root/receiver
records, the split summaries from 4,500 held-out root records across 20 overlapping
fits, and the estimator table from 400 stored paired replications. These are record
counts, not new independent observations. All selected means, intervals, split
summaries, RMSEs, paired MSE comparisons and coverage fractions reconciled to the
published artifacts. The [reconciliation record](../results/manuscript_evidence_reconciliation_20260921.json)
contains exact input/source hashes and scope limits.

Reproduce to an unused path with
`python3 scripts/reconcile_manuscript_evidence.py --output work/new_manuscript_reconciliation.json`.
The script reads stored records without importing the original analysis routines.
It does not repeat raw-log extraction, refit policies, resimulate outcomes, establish
family independence or audit an operational receiver. No model calls, candidate
executions or paid spend occurred. The reported arithmetic check took 0.071 seconds;
this is not a measurement of the entire manuscript-review time. The existing PDFs
remain dated snapshots and were not regenerated by this update.

The development-pilot section was subsequently integrated from the independently
reviewed v1c grades and the three preserved collection logs. Its separate
[manuscript integration record](../results/manuscript_development_integration_20260921.json)
checks the reported conditional counts, arm costs and total usage without executing
receiver or candidate code. This integration adds no observations, repairs no
confidence interval and does not update the dated PDFs.
