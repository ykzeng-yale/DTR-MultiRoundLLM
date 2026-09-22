# Evaluating history-dependent prompt choice in multi-round language-model interaction

Working title and manuscript entry point, 22 September 2026. This is an editable synthesis of the current evidence, not a submission-ready paper. It supersedes the empirical framing of the dated PDFs without replacing their historical records. The latest reviewed scientific delivery is `e518cc1`; the subsequent worker acknowledgement `85bc81b` reports no E12 receiver calls.

## Abstract

Choosing a follow-up prompt is a sequential decision: the preceding answer affects both the next instruction and the outcome it may produce. We formulate prompt choice for a fixed receiver as a dynamic treatment regime, targeting supported history- and slate-conditional mean outcomes rather than a realized individual effect. The framework distinguishes candidate generation from selection, local continuation comparisons from whole-policy evaluation, and identification from decision quality. Standard longitudinal identification and estimation results motivate a design that preserves an initial conversation prefix, executes prespecified prompt alternatives, isolates private scoring, and accounts for failures and computation.

Evidence remains developmental. In a reused corpus of 4,488 episodes from 561 coding tasks, the evaluated repair regime trailed adaptive resampling by 4.93 and 1.71 percentage points for the 3B and 7B receivers, respectively; this was not a prospective comparison at exactly matched total cost. A separate 77-call study on seven previously inspected tasks compared diagnostic-directed and neutral continuation instructions given identical public diagnostic information. Six initial answers passed the private suite. The primary observed mean difference was zero on every task; the prespecified context-removal package, which retained the public diagnostic, had a mean task-pass rate one seventh lower than neutral continuation. Two missing grades in a secondary arm were retained and examined separately. These finite results establish neither equivalence nor absence of useful history-dependent effects. They support an auditable evaluation design and preserve negative findings, but do not establish improved personalized prompting. Independent evaluation of a frozen public-history policy remains necessary.

## Scientific contribution and scope

The question is whether information available before the next message can support a prompt choice that improves the fixed receiver's expected final score. A favorable best-of-observed-branches summary would not answer that question: the deployed rule cannot choose using future private scores. Conversely, a null average contrast between two strategies does not exclude opposite conditional benefits. The paper therefore separates the definition of a supported effect, its estimation from an explicit collection design, the predictability of conditional rankings, and independently evaluated policy value.

The methodological contribution is the specification and audit of these distinctions for language-valued interventions. Classical dynamic treatment regime identification, importance weighting and augmentation are foundations, not claimed inventions. Candidate-first randomized selection identifies comparisons within its supported slate law; it does not automatically evaluate a changed prompt generator. Repeated continuations can inform checkpoint response means but do not by themselves identify the history distribution induced by a new multiround policy. These boundaries control both the theory claims and the empirical interpretation.

The empirical contribution currently consists of corrected reused-data diagnostics and fresh, finite development executions. The seven-root E11 result is retained as a negative finding for its frozen strategies and scoring contract. The 14-root E12 package has accepted instrument checks but no delivered prompt outcomes. Its adapted tasks, public information and thin private suites differ from E11, so it is a separate development study. Neither a passing instrument check nor a negative small-sample contrast substitutes for independent policy validation.

## Assembly of the main paper

| Section | Current editable source and required emphasis |
|---|---|
| Introduction and question | Abstract and scope above; define the decision-time information and explain why causal identification alone does not guarantee better prompt choice. |
| Intervention and identification | [Core theory](../docs/theory.md), read with the [reconciliation](../docs/theory_reconciliation_20260920.md) and [landmark theory](../docs/landmark_prompt_theory.md). State supported slate/generator laws, continuation policy and the public-history target. Preserve the boundary between standard results and application-specific formulation. |
| Estimation and inference | Core theory plus [known-assignment inference](../docs/known_assignment_inference_20260921.md). State root/family sampling, nuisance-fitting and variance conditions. Do not use an asymptotic result as a claim that the observed weak-overlap simulations attained coverage. |
| Experimental methods | [Version-specific methods](landmark_methods_20260920.md). Separate the original three-continuation-arm pilot from five-continuation-arm E11/E12. Retain all assigned failures, missingness and separate cost components. |
| Results | [Audited results and discussion](evidence_results_20260921.md). Keep historical repair/resampling, fixed-bank selection, known-truth simulations, E11 and pending E12 in distinct evidence layers. |
| Discussion | Explain what the tested strategies failed to achieve, what is not identified by these designs, and what an untouched policy evaluation must establish. No generic generator-expansion or compute-savings claim follows from the current evidence. |

## Claim-to-evidence check for the abstract

| Claim | Evidence and limit |
|---|---|
| 4,488 episodes and 561 coding roots | [Corpus recheck](../docs/experiment_recheck_20260920.md); reused trajectories, not a new prompt-choice trial. |
| Repair minus adaptive resampling: −4.93 and −1.71 percentage points | [Mechanism diagnosis](../docs/repair_mechanism_diagnosis_20260920.md) and the audited results table; corrected paired-change comparison, not exact total-cost matching. |
| E11: 77 calls, seven inspected roots, primary contrast zero on each root | [Independent E11 judgment](../docs/e11_lead_judgment_20260922.md) and [reconciliation artifact](../results/e11_lead_reconciliation_20260922.json). Two continuations per active arm; descriptive development evidence. |
| Context-removal package: −1/7 mean quality relative to neutral continuation with diagnostics | Same E11 sources. The arm changes the retained context and instruction, retains diagnostics about the old answer, and is not task-only resampling. |
| Two missing grades in a secondary arm | Same E11 judgment; immutable S0 records remain missing, with a separately labeled candidate-format sensitivity. The primary contrast is unaffected. |
| E12 has instrument evidence but no delivered model outcomes | [Accepted validation](../docs/e12_validation_acceptance_20260922.md); 42 reference/control starts are not prompt-efficacy observations. Worker acknowledgement at 03:27 UTC retains the scheduling block. |

The unfinished empirical milestones are the bounded E12 delivery and its independent reconciliation, followed by a scientifically justified, separately frozen policy evaluation if warranted. Manuscript assembly, citation/notation reconciliation and a complete reproducibility package also remain. This draft adds no empirical observation, new mathematical result, collection permission or completion credit.
