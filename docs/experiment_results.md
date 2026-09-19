# Experiment results ledger

## 2026-09-19 — Codex theory/reference workstream

Executed the finite-state reference study in `results/synthetic_reference_v1`: 400 independent Monte Carlo replicates, 800 root tasks and 2 continuations per root in each replicate, horizon 3, known-truth target utility 0.798750. These are fixed-nuisance diagnostics. DR coverage was .950 (both correct), .9525 (propensity correct/Q wrong), and .950 (Q correct/propensity wrong), with coverage MCSE about .011. Both-wrong exact bias was +.631259. The same code was invoked independently and all numerical/configuration/report files reproduced byte-for-byte, excluding runtime metadata; see `results/reproduction_check.json`.

Separately, `scripts/check_random_slate_remainder.py` enumerated eight random-slate cases, including a changed generator and stagewise mixed nuisance correctness. All algebra assertions passed with maximum remainder discrepancy 2.5e-16. This validates finite-enumerator algebra, not real-conversation assumptions.

The local collector completed a **dry run** of four fixture tasks and 14 mocked requests. Actual receiver calls, tokens, paid spend, and GPU training were zero. No learned critic or prompt generator was trained. The 30-test suite passed after integration.

The experiments workstream's A1 task-pool audits were already committed on main and are preserved. Their latest authoritative run reports 590 usable tasks after visible/hidden-test and degenerate-stub checks; see `results/audits/task_pool/NOTES.md`. This theory workstream read those reports but did not independently re-execute that audit. Do not conflate this reported benchmark audit with completed LLM intervention experiments.

Full-project readiness: theory/reference and experiment design are ready for cross-workstream review; a submission-ready empirical paper still requires fitted-nuisance/critic experiments, randomized generated-prompt trajectories, and locked independent policy trials. The change at this checkpoint is delivery of the theory package and explicit Q1–Q10 design decisions in `COORDINATION.md`.
