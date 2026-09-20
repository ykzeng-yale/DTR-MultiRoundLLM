# Handoff to the experimental agent

## Governing scientific decision after self-audit

The coordinating agent owns scientific judgment, including defects in the design it handed off. Read [scientific_judgment_20260920.md](scientific_judgment_20260920.md) before expanding the system. The immediate priority is endpoint/public-check integrity followed by one fresh, fixed-continuation prompt-choice test. Generator training and architecture expansion are paused as a scientific recommendation pending that gate; this is not a claim that all prompt optimization is futile.

Each assignment must name the estimand, competing explanations, observations that would distinguish them, same-target comparators, cost/precision limits, and prospective success/futility/inconclusive rules. Return valid negative findings without changing the population, scorer or budget to make them positive. The scientific lead must decide which hypothesis survives before issuing the next experiment.

The [revised selection-pivot adjudication](scientific_judgment_v2_pivot_20260920.md) accepts the STOP retraction, but the compute-efficiency proposal is a separate hypothesis pending a valid power/calibration and cost contract. Do not infer a no-harm certificate from the available sample size or use outcome-selected opportunity counts as the sample size for marginal policy improvement.

New evidence in this continuation: decomposition of 4,488 existing episodes; static endpoint/public-check audit; ten overlapping split sensitivities and feature diagnostics of our own selector; 400 diagnostic simulations with identical Q fits (79 base seeds reuse the prior grid) for regression and DR. All are diagnostic reuse or synthetic experiments, not fresh prompt-efficacy evidence. The original +2.85pp selector split is preserved but is not the expected benefit; 7B split median is +.83pp. Known behavior probabilities remain distinct from fitted propensities.

The user authorized development of the theory and experiment package and communication through this GitHub repository. The next agent should claim the corresponding issue, implement on a branch, and return a reviewable PR. Posting the issue is not evidence that any agent has accepted or executed it.

## September 20 continuation: required order

Read the [current report](continuation_report_20260920.md) and the three independent audits before following historical gate decisions. P0 has new fitted-Q evidence and source repairs, but the same-target history-adjusted baseline and final Monte Carlo precision remain open. Acknowledge Q11 and the stopping addendum in issue #2. No missing suffixes from naturally stopped logs can be used as full-rollout stopping outcomes.

For issue #4, the new fixed-bank 7B logistic result is a **fresh-validation hypothesis**, not a confirmatory success. Freeze its feature schema (including the assertion-category correction), model, four-call bank baseline and separate adaptive-cost protocol before new data. Keep visible validation and hidden-only evaluation auditable; use fresh root/family splits and measure checker/selector cost.

For issue #3, retain the original prompt-intervention goal: pinned receiver, exact candidate text/slate, pre-action history, named continuation, logged randomization and complete failures. Resolve candidate-first versus class-first generation explicitly. Begin with a bounded local feasibility protocol after committing all required freeze artifacts; this continuation did not run that new collection. Issue #5 remains dependent on the critic/data gates.

## Read first

`AGENTS.md`, `docs/research_proposal.md`, `docs/theory.md`, `docs/training_and_serving.md`, `docs/experiment_protocol.md`, `docs/data_contract.md`, and `docs/literature_audit.md` define the scientific contract. Start by independently reproducing the reference suite and inspecting failures. Do not transplant numerical results from DTR-AgentEvals: that is a different intervention study.

## Work packages

| Priority | Package | Deliverable | Completion criterion |
|---|---|---|---|
| P0 | Independent theory/code audit and fitted-nuisance simulation | Proof-review notes; exact-truth checks; task-cross-fitted nuisance learner; complete robustness grid | No unresolved identification/score mismatch; actual fitted-model bias/coverage reported with MCSE |
| P1 | Randomized generated-feedback dataset | Open-weight collector; restored-state branches; immutable logs; manifests; failure report | Exact slates/probabilities; no answer leakage; budget adherence; valid split/cluster structure |
| P2 | Critic, ranking, and STOP | Matched regression and DR critics; conditional-mean calibration; ranking regret | Held-out tasks; named continuation; unsupported predictions flagged; all costs counted |
| P3 | Learned generator and locked prospective trial | Generator/selector ablations; frozen policy comparison; uncertainty and compute ledger | Fresh evaluation after generator changes; independent test; all prespecified comparisons reported |

P0 can begin on CPU. P1 can run a small feasibility batch with an available local receiver after its manifest is pinned. P2 depends on an adequate dataset, and P3 depends on a successful leakage/identification audit. If hardware is unavailable, complete CPU work and report the exact pending resource need; do not label a dry run as an LLM experiment.

## Reply format on the issue

State the claim and scope, branch and commit, files changed, commands, test status, dataset/model digests, actual calls/tokens/runtime/spend, failures and missing outcomes, statistical results with uncertainty, and which claims remain unsupported. Attach tables/raw-result paths and explain any protocol deviation before selecting a final policy. Request review of a concrete PR rather than silently merging changes into the baseline.

## Non-negotiable comparisons

The causal critic must compete with a correctly history-conditioned sequential-regression critic using the same encoder and tuning budget. Include a simple iterative-feedback baseline and account for generator cost. A confounded marginal comparison is a diagnostic, not the strongest baseline. Finite-action simulations validate statistical identities; they do not validate a neural treatment embedding or a free-form generative policy.

## Ownership and acceptance

The initial package owns the theory specification and reference code. The experimental agent owns implementation and experiment execution on its branch after claiming a work package. Reviewer acceptance is distinct from execution completion. Keep issue/PR links in `docs/project_status.md`; never imply another agent has started solely because an issue exists.

## GitHub execution queue

Review [PR #1](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/pull/1) and acknowledge the Q1–Q10 decisions through [P0 / issue #2](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/2). The remaining packages are [P1 / data #3](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/3), [P2 / critic #4](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/4), and [P3 / generator and trial #5](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/5). These issues are concrete handoffs; execution/acceptance requires an agent reply and resulting artifacts.
