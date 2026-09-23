# Diagnostic evidence and limits of adaptive-prompt claims

**Editable results and discussion section, 21 September 2026; E11/E12/E13a status updated 23 September.** This section
updates the interpretation of the dated research PDFs and accompanies the
[landmark methods](landmark_methods_20260920.md). It integrates the historical corpus diagnostics, the subsequently collected
seven-task development studies, completed E12 and the fixed-checkpoint E13a follow-up. No additional receiver data were generated for this
manuscript integration. A complete manuscript and independent prospective policy
validation remain pending.

## Evidence populations and endpoints

The historical real-model evidence includes a reused corpus of 4,488 episodes from 561
root coding tasks, with four initial draws for each of two receivers. Subsequent
receiver routing was randomized within an existing repair/check process. The
recorded endpoint is full benchmark-test success under that process's evaluator.
It is distinct from the later private grading contracts. Task families
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
is implemented, and its bounded instrument-validation bundle has passed the declared gates on the worker host. Independent review reconciled 13 saved artifact hashes and records accounting for 77 isolated starts, including seven accepted references and 17 privately rejected controls. This establishes the stated finite validation checks, not general evaluator correctness or prompt efficacy. Grading/analysis command-line integration has passed independent source and mock review. The E11 development run subsequently completed under a committed receiver-use agreement. Its independently reconciled results are reported below. E12 subsequently completed under its separate release; its changed contract, instrument records and independently reconciled outcomes are distinguished below.
The [E11 design](../docs/public_diagnostic_design_20260921.md) gave
both repair arms identical public diagnostic bytes and compared neutral and
diagnostic-directed instructions. Its examples were disclosed before the initial
answer, changing the initial-history law relative to the pilot. It is explicitly
outcome-informed development; a later policy comparison requires untouched roots
and a frozen comparator. Its context-removal arm retains diagnostic observations
about the old answer and is not the task-only restart reported in the table above.

The E11 diagnostic comparison also has a specific measurement limit. The public
examples exercise many of the same error classes as the private suites, although
none repeats a private input literally. Their disclosure is part of the declared
intervention environment for every arm. Thus, a favorable contrast would concern
performance under that shared information; it would not demonstrate transfer to
entirely unseen error classes. We retain the examples and private assertions rather
than selecting a more favorable split after inspecting the pilot. Its reporting
contract compares initial public diagnostic status with the initial private
verdict, retaining unavailable diagnostics explicitly, and describes final private
outcomes by initial diagnostic status. These summaries do not validate a
learned policy on new tasks, and no final-public-pass rate can be reported without
actually checking the final artifacts on the public instrument. The
[reviewed design decisions](../docs/lead_review_mrl05_08_20260921.md) specify these
limits and the implementation requirements; the completed E11 findings appear below.

Receiver reproducibility is a separate limitation. The historical requests recorded
only part of the decoding configuration. Later observations make particular server
defaults plausible during collection, but cannot retroactively turn those defaults
into contemporaneous measurements. The successor harness records explicit request
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

The [precollection interpretation guide](../docs/e11_precollection_interpretation_20260921.md) preserves the primary information-matched contrast and specifies how positive, negative, heterogeneous and incomplete development results will be reported without treating them as independent policy validation.

## Subsequent public-diagnostic development run

The [E11 review](../docs/e11_lead_judgment_20260922.md) reconciled 77 fresh receiver calls on the same seven inspected development roots. STOP passed on six of seven roots. The primary information-matched S1–N1 contrast was zero on every root; neither arm repaired the one initially failing root. Both S1 outputs on that root violated the single-code-block format. This is a negative descriptive finding for the frozen strategy and endpoint, not population equivalence or a refutation of history-conditional effects.

The R1 context-and-instruction package had mean quality 1/7 lower than N1, with two failures among 12 initially correct continuations. Because both context and instructions differ, this contrast does not isolate the effect of removing context. The S0 arm had ten passes, two failures and two missing grades. Static compilation and saved worker stderr identify those missing grades as candidate module-level return statements misclassified as environment failures. The immutable analysis retains them as missing; scoring them zero in a labeled sensitivity gives S0 10/14 and a −1/7 contrast against N0. The defect does not affect the primary comparison. No arm repaired the initially failing root across its ten continuation attempts.

The run consumed 31,800 prompt and 4,859 completion tokens, seven public-check starts and 59 private-grading starts, at $0 paid service cost. Two continuations per arm and one unresolved task family provide no independent policy validation. The six-of-seven initial success ceiling limits repair opportunity and reflects our development design; it does not justify selecting a favorable replacement cohort after observing outcomes. A new cohort requires a prospective sampling and screening target, and any grader change requires versioned validation.

A later [post-hoc static output review](../docs/e11_mechanism_lead_review_20260922.md) found that the two S1 continuations on each of the six public-all-pass roots retained the initial function-definition AST; the other two S1 outputs were unassessable under the frozen extraction rule. R1 had six matching function-definition ASTs, seven different assessable ASTs and one unparseable output. These structural descriptors do not measure semantic equivalence or identify why an intervention helped or harmed. Both displayed S1 implementations on root402 also retain a visible error at the already-public modulus-one example, so format rejection is not evidence of a correct repair obscured by parsing. No candidate was re-executed or regraded. All six public-all-pass roots were privately correct; the hypothesis that a preservation instruction suppresses repair in a public-pass/private-fail stratum therefore remains untested by E11.

## Completed prospective E12 development batch

The [conditional E12 release](../docs/e12_bundled_release_20260922.md) specifies
14 adapted MBPP roots retained after source-based contract review, without backfill.
This is a finite, prospective hash-priority development roster. Selecting each
provisional family's minimum member hash and ranking those minima was not uniform
family sampling; neither representative-population nor independent-family inference
is claimed. Each adapted public task discloses the first original assertion's
example before the initial answer; its two remaining original assertions form the
private suite. This thin suite-passing endpoint and information package differ
from E11 and are not pooled with it or equated with complete program correctness.
The primary contrast remains S1 minus N1 at the same initial prefix with identical
public-diagnostic bytes and two independently seeded continuations per arm. All
assigned roots, failures and unavailable outcomes remain in descriptive reporting.

At worker delivery `e518cc1`, the [instrument records](../results/e12_dev_v3_20260922T030255Z_validation/ARTIFACT_SHA256SUMS.json)
reported 42 checks: 14 private references passing, 14 wrong controls rejected by
the private suffix, and 14 public references passing. [Independent review](../docs/e12_v3_measurement_review_20260922.md)
subsequently reconciled all four artifact hashes and all 42 recorded starts, including
assertion-level rejection of each control. The subsequent E12 delivery completed all 154 receiver calls and all assigned grades. STOP passed on 10/14 roots; N0 and N1 each passed on 20/28 continuations, while S0, S1 and R1 each passed on 19/28. The primary S1 minus N1 mean was −1/28 (−3.57 percentage points), consisting of +0.5 on root 842, −1 on root 863 and twelve ties. No fixed arm improved on STOP. S1 had one fail-to-pass transition among eight continuations of initially private-failing answers and two pass-to-fail transitions among twenty initially private-passing continuations; R1 had two and three, respectively. These are frozen-score transitions, not complete semantic-correctness assessments.

Root 863 illustrates the distinction. The initial program failed a valid public duplicate-value example but passed two private assertions without duplicates. Both S1 outputs were then rejected for multiple code blocks without candidate execution. The saved outputs do not establish a successful public repair that damaged private behavior. The public diagnostic detected a real domain error; the private pass was incomplete evidence of correctness. All original grades and format penalties remain unchanged. A post-hoc static review reproduced seven unassessable S1 outputs, all on public-fail roots; the association does not identify a causal mechanism, and the base prompt already required a single complete answer.

The batch used 53,670 prompt and 12,198 completion tokens, with zero unknown usage, 314.258 seconds of collection, and 117 public/private execution starts. The [independent review](../docs/e12_lead_judgment_20260923.md) and [record-level reconciliation](../results/e12_outcome_lead_reconciliation_20260923.json) verify the saved evidence without new model execution or regrading. Neither the unresolved family label nor the provisional duplicate screen supports population inference. The negative observed primary contrast is not equivalence or proof that predictable conditional effects are absent. E11's null remains intact; the future five-point usefulness criterion was not an E12 stopping threshold.

A public-fail-gated R1 rule was selected after inspecting E12 and has apparent in-sample value 0.750 versus STOP's 0.714. This is development selection on the same outcomes, not policy validation. The subsequent E13a follow-up compared diagnostic-plus-instruction restart with bare resampling at the five E12 histories with a public failure. Its fixed-checkpoint findings are reported next; this does not evaluate the selected rule on independent histories.

## Fixed-checkpoint E13a restart-package follow-up

E13a collected six fresh continuations per arm at five already inspected E12
checkpoints under the separately frozen MRL-20 contract. R1 retained the original
task and public diagnostics but removed the previous answer; FRESH retained only
the task and its public information. The instructions also differed. Thus the
contrast concerns these complete restart packages, not the diagnostic alone or
information-matched instruction choice. Both arms were executed at every checkpoint;
the balanced randomized order is scheduling, not an action-selection propensity.
These development-selected histories are not an untouched policy-evaluation set.

All 60 assigned outputs had frozen grades. R1 passed on 9/30 and FRESH on 12/30,
for an equally weighted five-checkpoint difference of −0.100. The checkpoint counts
were 5/6 versus 2/6 (842), 2/6 versus 3/6 (288), 2/6 versus 6/6 (863), 0/6 versus
1/6 (966), and 0/6 versus 0/6 (652). These are observed finite-draw contrasts;
no population interval, conditional-mean sign, equivalence, or useful-gain futility
claim follows. Removing 863 changes the mean to +1/24, but also changes the target;
all five checkpoints remain in the primary result. Observed 0/6 and 6/6 cells do
not establish structural response floors or ceilings.

The saved outputs support the following descriptive partition. Every denominator
is all 30 assigned outputs in that arm, so this table does not condition the
success contrast on a post-treatment parse result.

| Joint recorded state | R1 | FRESH |
|---|---:|---:|
| Primary-score success | 9/30 | 12/30 |
| Extraction or Python syntax failure | 13/30 | 0/30 |
| Extractable, parseable output with primary-score failure | 8/30 | 18/30 |

The 13 static failures are not 13 extractor rejections: the grader records one
extraction rejection, and the broader static check also includes Python parsing.
All six R1 outputs at 966 failed to produce parseable Python; diagnostic-report
echoes are among the saved failures. They are not established to be semantically
correct solutions rejected by a cosmetic convention. This partition neither
identifies mediation nor estimates how the score would change after repairing
formatting. The original extraction rule and all zero grades remain unchanged.
Textual diversity and a nonconstant score do not establish the sensitivity or
semantic completeness of the thin private suites.

R1 used 12,804 prompt and 5,018 completion tokens; FRESH used 6,174 and 1,388,
respectively. Both received a 512-completion-token ceiling per call, but actual
costs were unequal. The study used 60 calls, 30,720 reserved completion tokens,
55 isolated starts (9 containment, 10 reference/control, 36 candidate), and $0;
unknown token/start counts were zero. The setup wall interval including gaps was
64.737 seconds; the 4.539-second active-command sum is a distinct quantity.
Collection took 142.074 seconds, grading 1.617 seconds, and supervised analysis
0.042 seconds. The saved shutdown record observes the owned PID absent; the lead
did not independently observe the live host.

[Independent review](../docs/e13a_lead_judgment_20260923.md) checks the saved outcomes,
request bindings, accounting and interpretation without regrading. Complete
archive acceptance remains pending: 164 delivered file hashes match, but the
165-file manifest names a missing receiver log; the recorded execution commit
was rebased after dispatch and requires an additive object archive. Matching
recorded source hashes to the published replacement does not establish identity
of the entire original commit/tree. These provenance limitations accompany the
finite result; they are not repaired by editing its immutable manifest.

The next substantive empirical question remains whether public history supports
useful prompt choice. Any follow-up with a common terminal-output instruction
must be frozen as a new intervention law, preserving E13a rather than relabeling
it as corrected data. An information-matched same-prefix comparison on a new
predeclared development roster would address that question more directly than
repeatedly tuning these five checkpoints. Independent evaluation of a locked
public-history policy remains a separate unfinished milestone.

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
