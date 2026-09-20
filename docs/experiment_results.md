# Experiment results ledger

## 2026-09-19 — Codex theory/reference workstream

Executed the finite-state reference study in `results/synthetic_reference_v1`: 400 independent Monte Carlo replicates, 800 root tasks and 2 continuations per root in each replicate, horizon 3, known-truth target utility 0.798750. These are fixed-nuisance diagnostics. DR coverage was .950 (both correct), .9525 (propensity correct/Q wrong), and .950 (Q correct/propensity wrong), with coverage MCSE about .011. Both-wrong exact bias was +.631259. The same code was invoked independently and all numerical/configuration/report files reproduced byte-for-byte, excluding runtime metadata; see `results/reproduction_check.json`.

Separately, `scripts/check_random_slate_remainder.py` enumerated eight random-slate cases, including a changed generator and stagewise mixed nuisance correctness. All algebra assertions passed with maximum remainder discrepancy 2.5e-16. This validates finite-enumerator algebra, not real-conversation assumptions.

The local collector completed a **dry run** of four fixture tasks and 14 mocked requests. Actual receiver calls, tokens, paid spend, and GPU training were zero. No learned critic or prompt generator was trained. The 30-test suite passed after integration.

The experiments workstream's A1 task-pool audits were already committed on main and are preserved. Their latest authoritative run reports 590 usable tasks after visible/hidden-test and degenerate-stub checks; see `results/audits/task_pool/NOTES.md`. This theory workstream read those reports but did not independently re-execute that audit. Do not conflate this reported benchmark audit with completed LLM intervention experiments.

Full-project readiness: theory/reference and experiment design are ready for cross-workstream review; a submission-ready empirical paper still requires fitted-nuisance/critic experiments, randomized generated-prompt trajectories, and locked independent policy trials. The change at this checkpoint is delivery of the theory package and explicit Q1–Q10 design decisions in `COORDINATION.md`.


## 2026-09-20: continuation audit and corrected experiments (Codex coordinating agent)

Ran 1,360 corrected E0 replications plus 72 independently audited fitted-Q replications; ten exact stopping checks; 51 tests pass. Audited 4,488 sibling episodes and ran a fixed 336/225-root selection fit/evaluation without new inference. See [continuation report](continuation_report_20260920.md), [E0](e0_corrected_results_20260920.md), [raw-log recheck](experiment_recheck_20260920.md), and [selector](selection_corrected_results_20260920.md). Original artifacts remain unchanged. Source, estimator, population, cost and validation boundaries in those documents are part of every reported result. External spend $0; new model calls 0; GPU hours 0.


## 2026-09-20: scientific self-audit and mechanism diagnosis

The coordinating agent owns the original design and interpretation. See [scientific judgment](scientific_judgment_20260920.md) for the decision. New diagnostic work retained all 4,488 episodes, identified 90 roots without substantive public checks, decomposed repair gains/losses, tested selector sensitivity across ten overlapping splits, and ran 400 matched-fit regression/DR diagnostic runs (79 base seeds overlap the prior grid; no cross-study pooling). No new model calls, candidate-code executions, GPU hours or external spend. This evidence strengthens the diagnosis and narrows the program; it does not establish personalized prompt efficacy.


## 20 September 2026 — Landmark theory and personalization premise (scientific lead)

The [new report](landmark_premise_results_20260920.md) records 1,200 simulated train/test datasets (four conditions ×300) and two nested replication analyses per dataset. Marginal arm effects are zero in all four declared laws; useful history-based selection is recovered only where its information is available. Seven exact theory-check groups include the information/noise oracle distinction, root-label leakage, regret and clustered variance. This is synthetic evidence for interpretation and implementation, not LLM efficacy.

The new collector/analyzer executes a two-root mock run (14 mocked requests, zero receiver calls) and preserves absent grades as missing bounds. The full project suite passes 82 tests. The prospective source audit finds 544 additional MBPP candidate IDs after known description exclusions, not 544 validated fresh tasks. Current receiver/evaluator/family gates remain open. No candidate-code execution, GPU/model calls or external spending occurred in this continuation.

## 20 September 2026, 22:24 UTC hourly continuation — Measurement and inference (scientific lead)

A fixed 24-task source-only curation retained seven for contract review, identified seven probable old-family variants, and held ten for material specification problems. No replacements or model outcomes informed the selection. All 242 candidate IDs were mechanically screened; only the 24 selected tasks were manually reviewed. The [family audit](landmark_family_audit_20260920.md) distinguishes detected relationships from unverified independence. No reference/test agreement was established by execution.

Exact enumeration of 25 binomial counts in a declared 24-independent-root law gives **0.912777410** coverage for the exploratory nominal 95% normal interval. The conservative fixed-weight family alternative gives **0.999947938** in that same law, illustrating conservatism rather than general empirical precision. Its Bonferroni endpoint allocation across ten fixed outputs is separately implemented. The [inference review](landmark_inference_review_20260920.md) supplies the argument, weighting/endpoint restrictions and source-bound internal review; `results/landmark_inference_20260920/exact_checks.json` retains every count and coverage contribution. This is exact finite-law analysis, not a Monte Carlo or LLM experiment. No old simulation or result was overwritten.

The new offline private grader is tested with mocked execution and fails closed on this host. The [execution report](landmark_grading_validation_20260920.md) records failed containment startup checks separately from benchmark outcomes. Reference/control discrimination and sandbox isolation must pass before actual grading; broad static code flags are held for review rather than automatically labeled incorrect. No new receiver calls, evaluation-model tokens, benchmark reference/candidate executions, GPU work or external spend occurred. Source-curation and exact-enumeration aggregate CPU time was not instrumented; controlled-launch timings are retained in their report. Full-project readiness remains below submission: this continuation repairs our measurement/inference design and prepares software, while real prompt efficacy remains untested.

The coordinating agent independently ran the final integrated suite: **121 tests and two subtests passed in 1.53 seconds**. Controlled host-check accounting is 31 launch attempts, zero observed Python payload starts, and 0.420941 seconds summed runner wall time. The final blocked mock grading run retains all four outcomes as missing and makes zero grading executions. These checks validate the refusal/missingness behavior; they do not turn a failed host startup into an executed reference or negative-control test.
