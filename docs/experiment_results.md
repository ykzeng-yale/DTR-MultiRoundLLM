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
