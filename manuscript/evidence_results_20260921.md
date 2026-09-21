# Diagnostic evidence and limits of adaptive-prompt claims

**Editable results and discussion section, 21 September 2026.** This section
updates the interpretation of the dated research PDFs and accompanies the
[landmark methods](landmark_methods_20260920.md). It integrates previously reported
diagnostics; it does not report a new receiver experiment. Integration into a
complete manuscript and independent prospective policy validation remain pending.

## Evidence populations and endpoints

The available real-model evidence is a reused corpus of 4,488 episodes from 561
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

## Interpretation and next empirical test

The current evidence justifies a narrower empirical sequence. First validate the
measurement contract and receiver. Then compare supported continuation strategies
from a common public history, with frozen prompts, continuation, information and
cost rules. Evaluate a frozen public-history selector against competent fixed and
sampling comparators on independent task/family information. The proposed
[literature-guided amendment](../docs/literature_guided_design_20260921.md)
separates diagnostic availability from instruction strategy; its five-arm design
is not yet implemented by the existing three-arm collector or released for use.

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
