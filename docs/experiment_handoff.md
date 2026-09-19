# Handoff to the experimental agent

The user authorized development of the theory and experiment package and communication through this GitHub repository. The next agent should claim the corresponding issue, implement on a branch, and return a reviewable PR. Posting the issue is not evidence that any agent has accepted or executed it.

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
