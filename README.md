# DTR-MultiRoundLLM

**Multi-round human–LLM interaction as a dynamic treatment regime.** The user-side
message at each turn is treated as a time-varying treatment, the conversation history as
the time-varying confounder, and task quality as the outcome.

> **Status, 2026-09-19.** Nothing is frozen and no confirmatory experiment has run. What
> exists is a verified evidence base, a repaired theory draft, a full experimental program,
> and — importantly — **five independent findings that redirected the project away from its
> original hypothesis**. Read `COORDINATION.md` first; it is the cross-workstream channel
> and carries the open questions. This README was seeded by the experiments workstream
> because the repository was empty; the theory workstream owns the framing and should
> replace this section with its own.

## What the evidence says so far

| finding | where |
|---|---|
| Reading feedback effects off a confounded log **inverts** the true ordering — the marginal critic names the true best arm in 0.000–0.060 of replicates, against 0.792 under randomization | [e0_results.md](docs/e0_results.md) |
| A **state-conditioned** critic beats inverse-probability weighting in 16 of 17 cells, and the cell built to break it did not | [e0_results.md](docs/e0_results.md), [premise_findings.md](docs/premise_findings.md) |
| Iterating **destroys** 16.2% of already-correct answers, while repairing 23.9% of failures; a self-check stopping rule stopped on 50.4% of all failures | [audits.md](docs/audits.md) |
| A content-free retry (0.110) **beat** structural localization (0.066) on real states | [pilot_findings.md](docs/pilot_findings.md) |
| **Kill criterion K1 fired**: adaptive best-of-N beats a real multi-turn loop at *lower* cost on both receivers | [g0e_kill_criterion.md](docs/g0e_kill_criterion.md) |
| Cheap policy-observable features recover **none** of the selection headroom | [g1a_selection_pilot.md](docs/g1a_selection_pilot.md) |

Taken together these moved the project from "multi-turn feedback improves outcomes" to
**sequential selection and stopping under known propensities**, and then raised the
question that now decides it: whether the headroom in selection is reachable at all.

## Documents

| path | contents |
|---|---|
| `COORDINATION.md` | cross-workstream channel, ownership, open questions Q1–Q11, working agreements |
| `AGENTS.md` | rules any agent working here follows |
| `docs/positioning.md` | what may and may not be claimed after the literature audit; what we concede and to whom |
| `docs/literature_audit.md` | 141 citations verified, 96 prior-art items, novelty claim, adversarial review |
| `docs/theory_draft_from_experiments.md` | identification and estimation, 22 assumptions, 32 results, ~31 claims withdrawn in place |
| `docs/theory_experiment_requirements.md` | the 31 obligations the theory puts on the harness, plus what only a human theorist can settle |
| `docs/program_draft.md` | the experimental program: 27 arms in four gates, 12 kill criteria, freeze checklist |
| `docs/gate1_rescope.md` | **what to do next**, after K1 fired |
| `docs/audits.md` | audits A1–A4: task-pool validity, difficulty, iteration headroom, assertion-level split |
| `docs/e0_results.md` | the executed simulation study |
| `docs/premise_findings.md` | the premise checks, including the one that came out against the project |
| `docs/pilot_findings.md`, `docs/g0e_kill_criterion.md`, `docs/g1a_selection_pilot.md` | real-model pilots and the two free gates |
| `docs/measured_calibration.md` | every cost figure, with provenance |
| `docs/readiness.md` | the weighted readiness rubric and its checkpoints |

## Code

| path | contents |
|---|---|
| `experiments/common/` | Seatbelt sandbox, hidden-test verifier, integrity gates, assertion-level scoring |
| `experiments/e0/` | reference simulator, estimators, 17-cell grid |
| `experiments/audits/` | A1–A4, the two free gates, the data/evaluator audit suite |
| `experiments/env/` | pinned inference-build manifest (26 hashed files) |
| `results/` | immutable run directories with manifests |

## Reproduce the CPU-only work

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r <(echo -e "numpy\nscipy\nscikit-learn\npandas\nmatplotlib\nrequests\npytest")
.venv/bin/python experiments/audits/audit_task_pool.py
.venv/bin/python experiments/audits/audit_scoring_split.py
.venv/bin/python experiments/e0/run_grid.py --reps 1000 --workers 6
```

## Sibling projects

* `ykzeng-yale/DTR-AgentEvals` — dynamic treatment regimes for **agent-side** decisions
  (model routing). This repo is the **user-side** counterpart, and its completed run
  supplied every zero-cost measurement above.
* `ykzeng-yale/ICLR-WinRatioAgentEval` — prioritized multi-dimensional outcomes for agent
  evaluation.
