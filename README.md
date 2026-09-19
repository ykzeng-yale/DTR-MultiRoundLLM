# DTR-MultiRoundLLM

**Multi-round human–LLM interaction as a dynamic treatment regime.**

The user-side message at each turn is treated as a time-varying treatment, the
conversation history as the time-varying confounder, and task quality as the
outcome. The programme has three parts: identify and estimate turn-level causal
effects of language-valued interventions; learn an optimal adaptive prompting
regime, including when to stop; and train a generative prompt policy against the
causal critic rather than against a correlational reward model.

> **Status: scaffolding.** This README was seeded by the experiments workstream
> because the repository was empty. The theory workstream owns the framing and
> should replace these sections with its own. See `COORDINATION.md` for the
> ownership map, the open cross-workstream questions (Q1–Q10), and the working
> agreements; `AGENTS.md` for the rules any agent in this repo follows.

## Layout

| Path | Contents | Owner |
|---|---|---|
| `COORDINATION.md` | cross-workstream channel, ownership, open questions | shared |
| `AGENTS.md` | rules for agents working here | shared |
| `docs/theory*.md` | identification, estimands, estimators, guarantees | theory |
| `docs/literature_audit.md` | verified citations, prior art, novelty claim | theory (seeded by experiments) |
| `docs/design_*.md`, `docs/experiment_*.md` | designs, protocols, results, handoff | experiments |
| `experiments/` | harness, pre-registered protocols, runners, estimators | experiments |
| `results/` | immutable run artifacts with manifests | experiments |
| `work/` | gitignored scratch and third-party data | — |

## Sibling projects

* `ykzeng-yale/DTR-AgentEvals` — dynamic treatment regimes for **agent-side**
  decisions (model routing). This repo is the **user-side** counterpart.
* `ykzeng-yale/ICLR-WinRatioAgentEval` — prioritized multi-dimensional outcomes
  for agent evaluation, the natural outcome definition for the regimes studied
  here.
