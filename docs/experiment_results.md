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

## 20 September 2026, 23:24 UTC — Source-only contract preparation (scientific lead)

The [versioned contract report](landmark_task_contracts_20260920.md) records an explicit public/private proposal for the same seven retained tasks: 21 original private assertions, 22 authored boundary assertions and 14 wrong controls. None was executed. Static source inspection finds a boundary defect in the original MBPP/402 reference at r=0,p=1; it remains an explicit hold without narrowing the proposed positive-modulus domain or backfilling the original slate. All seven are unvalidated, and the task/endpoint revisions are distinct development targets.

The real source-only builder took 0.010368 seconds and produced a review-only package with hashes in `results/landmark_task_contracts_20260920/manifest.json`. The coordinating agent ran the complete suite: 131 tests and two subtests passed in 1.42 seconds. These are static export, mock and deterministic software checks, not evidence that benchmark references or controls pass. New model calls/tokens, sandbox launches, benchmark/control executions, GPU work and external spend were zero. Existing failed-host evidence and prior simulation/empirical artifacts are unchanged. Full-project status remains not submission-ready; validated execution, receiver freeze and independent prompt-policy validation are still required.

## 21 September 2026, 00:25 UTC — Precision/resource planning (scientific lead)

The [planning report](landmark_precision_plan_20260921.md) contains 14 deterministic design scenarios and six inversions of the existing fixed-family confidence radius. An independent internal reviewer recomputed them and verified source hashes without blockers. Under the conservative procedure, even seven independent roots all with contrast +1 have lower bound −.0266 for one prespecified 95% interval; the unresolved shared-group design yields [-1,1]. These are hypothetical calculations, not observed outcomes, power estimates, empirical failures or an impossibility theorem for other methods.

The source-bound artifact is `results/landmark_precision_planning_20260921/report.json`; planning wall time was .001424 seconds. The full software suite passed 136 tests and 8 subtests in 1.47 seconds, including existing deterministic simulator checks. Zero model calls/tokens, benchmark executions, sandbox attempts, GPU work or spend. Earlier source results are unchanged. Milestone completion is approximately 49%, unchanged under the newly documented retrospective baseline. Full project remains not submission-ready; fresh supported prompt data and independent policy validation remain absent.

## 21 September, 01:36 UTC heartbeat — Offline graph component completed

The coordinating agent implemented the bounded source-adoption handoff, with an
exact fixture/protocol commit 5884723 before implementation and code commit 61136c3
before execution. See [the validation report](graph_offline_validation_20260921.md).
Three pure Reasoning Gym functions are narrowly reused with license/provenance;
strict JSON/public-feedback handling and interruption-safe immutable records are
validated. The 32-root batch made 42 generator attempts and matched 15/15 controls,
including missing output. Independent artifact review checked source hashes,
all 32 direct reference constraints and public/private/ledger consistency. These
are trusted data-only fixtures, not LLM outputs or code-candidate execution.

The full suite passes 222 tests and 8 subtests in 1.52 seconds. Whole batch process
0.233 seconds, 24.92 MiB peak RSS, 58,262 artifact bytes; zero model calls/tokens,
spend, sandbox launches, installations or downloads. A pre-execution interruption
bug was found and fixed. The historical novelty audit no longer controls current
README/theory claims; current source links were corrected without rewriting history.

Keep the original seven coding roots and all holds. The controlled graph target
has a complete public verifier and a cheap algorithmic solution; it cannot prove
practical LLM utility or prompt efficacy. The current collector is still three-arm
v1, not the five-arm amendment. No collection is released. Next return the exact
receiver/environment/resource window and finish the selected renderer/measurement
freeze, then fresh data and independent policy validation. Resource clarification
was requested from the owner; no answer or paid approval has been inferred.

Progress remains 49%, Δ=0 points; full project not submission-ready. Continue on
current main under Yukang Zeng's identity. Do not repeat the unchanged offline
batch merely to create activity, and do not expand generator training.
