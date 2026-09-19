# Coordination — DTR for multi-round LLM interaction

Two Claude agents work this repository in parallel, at the owner's direction
(`ykzeng-yale`, yukang.zeng@yale.edu). This file is the shared channel: read it
before your first commit, append to it rather than rewriting it, and sign your
sections.

## Who is here

| Workstream | Role | Owns |
|---|---|---|
| **Theory** | literature, idea framing, full theory + manuscript | `docs/theory*.md`, `manuscript/`, framing sections of `README.md` |
| **Experiments** (this session, opened 2026-09-19) | designs, harness, pre-registration, execution, results | `experiments/`, `results/`, `docs/experiment_*.md`, `docs/design_*.md` |

The owner used the same split in the sibling repos
`ykzeng-yale/DTR-AgentEvals` and `ykzeng-yale/ICLR-WinRatioAgentEval`.
This repo was empty when the experiments workstream arrived, so the experiments
workstream seeded the scaffold below. **The theory workstream should overwrite
the framing in `README.md` with its own** — that is its territory, not a
conflict.

## The idea, as the experiments workstream understands it

Freeze a receiver model/agent `M`. A user submits task `X`; the receiver
answers `O_1`; the user sends a further instruction `A_2`; the receiver answers
`O_2`; and so on. Treat

* `A_t` — the user-side message at turn `t` — as a **time-varying treatment**,
* `H_t = (X, A_1, O_1, ..., A_{t-1}, O_{t-1})` — the conversation — as the
  **time-varying covariate**, and
* terminal task quality `Y` as the **outcome**.

The confounding structure that makes this longitudinal rather than single-shot:
`A_{t-1} -> O_{t-1} -> A_t` while `O_{t-1} -> Y`. Prior output quality is a
time-varying confounder *affected by prior treatment*, so a naive reward model
fit on logs will mis-order feedback types (severe corrections co-occur with bad
states, and so look harmful even when they help).

Targets: turn-level blip/advantage effects of language-valued interventions,
`Q`-functions over (history × candidate next message), the value of an adaptive
prompting regime including a **STOP** action, and a generative prompt policy
trained against the causal critic.

## What the experiments workstream needs from the theory workstream

These are the decisions that change the harness. Each one blocks a freeze, not
the design work, so the experiments workstream is proceeding with the stated
default and will revise on your answer. Answer inline under each question,
signed, or open an issue.

**Q1 — Headline estimand.** Turn-level blip effect `gamma_t(H_t, a, a_ref)`
(SNMM-style), or regime value `V(pi)`, or both with one as primary?
*Experiments default:* blip is primary (it is what the critic must learn), with
`V(pi)` as the confirmatory quantity.

**Q2 — Treatment space.** Do we randomize/target a **finite coarsened prompt
class** (identification by construction, positivity holds by design), or
free-form text with stochastic-intervention semantics, or both in a ladder?
*Experiments default:* a ladder. The anchor design randomizes over a frozen
finite taxonomy; free-form generator prompts come in as a second design where
the propensity is computable from generator log-probabilities. The taxonomy is
the single most expensive artifact to change after a freeze, so this is the
question we most need answered.

**Q3 — Reference action for the blip.** `a_ref = STOP` (accept current output),
or a content-free `"try again"`, or no-message? These give different effects and
different baselines.
*Experiments default:* two reference contrasts reported — vs `STOP` (is another
turn worth it at all) and vs unary `"try again"` (does the *content* of the
feedback matter beyond the fact of a retry).

**Q4 — Horizon and stopping.** Is `STOP` an action inside the regime (so the
regime chooses its own horizon), or is the horizon fixed at `T`? If regimes stop
at different times, the comparison must fix either a turn budget or a
measurement point — which?
*Experiments default:* fixed `T_max` with `STOP` available, outcome measured at
the absorbing state, and every regime additionally compared at a matched turn
budget. Abandonment by a real user is informative censoring and is out of scope
for the first design.

**Q5 — Outcome.** Scalar (`pass@final` on hidden tests) or a prioritized
multivariate outcome (correctness, then tokens, then turns) in the style of the
sibling win-ratio project? Cost as a penalty `lambda C` or as a constraint?
*Experiments default:* record all components per episode so either can be
computed post hoc; report scalar primary + cost-adjusted secondary.

**Q6 — Inference unit and variance.** Task instance as the unit, clustered by
task family? We need the variance form you intend to use to size the
experiment — please state it (or confirm that a cluster-robust sandwich over
task families is acceptable).

**Q7 — Positivity floor.** What randomization floor do you want per arm
(sibling routing project used `>= 0.2`)? This sets the number of prompt classes
we can afford per decision point.

**Q8 — Who is the user?** The intervener in every feasible design is an LLM or
a scripted policy, not a human. The paper must scope this honestly: we estimate
effects of *interventions deliverable by an automated intervener*, which is also
the deployment target. Do you want a small human-in-the-loop validation slice,
and if so, does the owner have IRB/consent cover for it?

**Q9 — Known propensities.** Should the harness log generator token
log-probabilities so sequence propensities are exactly computable? Cheap to add
before a freeze, impossible to add after.
*Experiments default:* yes, log them.

**Q10 — Pre-registration contents.** Confirm what must be frozen and committed
before the first model call: protocol, config, taxonomy with exemplars, seeded
assignment table, estimator code, analysis script, and the primary/secondary
outcome list. The sibling repos froze exactly this and recorded the freeze
commit id.

## Working agreements (carried over from the sibling repos)

* `git pull --rebase origin main` before every push. **Never force-push.**
* Never overwrite a completed run; new run directory, new manifest.
* Pre-register before any model call: protocol + config + seeded design frozen
  and committed, freeze commit id recorded, every episode stamped with the
  config hash.
* Distinguish, always: synthetic simulation / pilot / confirmatory result /
  planned-but-not-run. A proposed extension is not an experiment.
* Do not call known DTR, OPE or semiparametric results novel. Attach
  assumptions and primary citations to every mathematical claim.
* Report null and negative results plainly.
* Keep tokens, latency, money and energy distinct; do not let one stand in for
  another.
* Raw third-party data stays in gitignored `work/`. No credentials, ever.
* `gh` is not installed on the owner's machine. Read issues over the public
  REST API; **write coordination as files in this repo.**

## Machine constraints (experiments workstream, 2026-09-19)

One Apple M5, 32 GB, 10 cores, ~258 GB free. The GPU is **shared with two
sibling projects**; at the time of writing `DTR-AgentEvals` is running a
4,488-episode routing log stage with `llama-server` on ports 8191 (Qwen2.5-7B)
and 8193 (Qwen2.5-3B). Cached open-weight models: Qwen2.5-3B/7B-Instruct GGUF,
Qwen2.5-Coder-7B-Instruct GGUF, Qwen3-4B-Instruct, granite-3.3-8b GGUF. No
`torch` installed in either sibling venv; `mlx_lm` is available.
Consequence: design, pre-registration, CPU simulation and analysis proceed now;
GPU work is scheduled around the sibling runs and recorded per episode.

## Log

* **2026-09-19, experiments workstream** — repo was empty; seeded scaffold,
  this file, and the ownership map. Literature audit and identification-theory
  development running. Q1–Q10 above are open.
