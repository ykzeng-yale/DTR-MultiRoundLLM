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

## STOP — read this before writing any theory (2026-09-19, experiments workstream)

The literature audit is done: 141 citations verified with live lookups, 96 prior-art
items swept down five deliberately different routes, adjudicated, and then attacked
by an agent playing hostile area chair. Results in `docs/literature_audit.md`,
`docs/positioning.md`, and the structured records in `docs/literature/`.

**Good news.** 132 of 141 citations in the originating brief are real and accurately
described. The bibliography was largely sound. (One string is corrupted:
`arcxiv.org/abs/2608.17499` — the arXiv id and title are genuine, but `arcxiv.org`
does not exist as a preprint server.)

**Bad news, and it is load-bearing: the brief's novelty claim does not survive.**
Prior art occupies most of the proposed contribution, including several papers the
brief never mentions. Do not write "we are the first to formulate multi-turn
prompting as a longitudinal causal problem" — it is defeated three times over, twice
by peer-reviewed work. Before drafting, engage these directly:

* **arXiv:2502.17538** — Q-learning for a dynamic treatment regime in a *natural
  language action space*, with embedding-space gradient ascent and decoding back to
  text. Owns our framing and components (ii) and (iii); leaves the entire
  identification layer open. This is the paper to differentiate against.
* **arXiv:2607.03597** — estimands and inference for causal effects in AI-mediated
  conversation. Already plants the flag on our vocabulary.
* **arXiv:2404.00207** (CausalCollab) — user-side text as time-varying treatment, LM
  history as time-varying confounder, sequential g-formula. Same group as 2502.17538.
* **arXiv:2605.07834** (Nakamura & Imai) — marginal structural model over *sequences*
  of text treatment features with a per-feature deconfounder and valid semiparametric
  CIs. The closest existing thing to a DTR over text; its absence from the brief was
  the audit's biggest single gap.
* **arXiv:2410.00903** (Imai & Nakamura) — single-period identification and DML
  asymptotics for text-valued treatments.
* **arXiv:2504.02646** (Kiyohara et al.) — per-context off-policy prompt policy
  learning from logged bandit feedback over a large text action space.
* **arXiv:2605.25998** (KDD 2026) — states prompt-as-treatment plus DR/orthogonal
  policy learning outright, but *explicitly leaves the sequential/agentic case open*,
  which is useful to us.
* **arXiv:2604.09459** — a widely read survey with propositions giving a *negative*
  result on turn-level causal credit in multi-turn LLM trajectories. This is what
  will be thrown at our identification section.
* **arXiv:2603.06859** — argues that with no hidden state in the text history the
  per-decision counterfactual is exactly identified by re-sampling under a frozen
  behaviour policy. A direct rival to a g-formula story, and close to our branching
  design.

**Do not rebuild these** (full list with reasons in `docs/literature_audit.md`):
neural SNMM / blip machinery (DeepBlip, arXiv:2511.14545, ICML 2026 — extend it),
the orthogonal DR Q-learner (arXiv:2509.26429, ICLR 2026 — its gap is the *action*
space, not the estimator), a DML-debiased reward model over prompt and query
embeddings (CPO did it, and doing DML on both jointly is exactly the
treatment/covariate conflation that arXiv:2602.15730 shows induces bias), or
token-level importance weighting for multi-turn OPE (arXiv:2606.05558 did it with
exact log-probs and it still loses to a learned world model).

**What survives is smaller and real, and it converges with the premise checks and
the audits.** The area chair, without seeing either of those, independently landed on:
coarsen the action to a small finite move set and treat *the coarsening as the
identification argument*; **randomize it prospectively and log the propensities** —
nobody has done this in a multi-turn LLM setting, checked as a direct question and
found clean; use the existing orthogonal estimators, cited as such; and use the
estimated effects for the one decision the evidence says they can pay for,
**when to intervene and when to stop**. That is the same conclusion the premise
checks and Audit A3 reached from the other two directions.

Q11 therefore now has a third vote. The experiments workstream's recommendation is
in `docs/positioning.md` under "The claim we should try to earn", together with nine
hard constraints the audit imposes on the design — including a mandatory
zero-information feedback arm (UFO, arXiv:2507.14295), budget-matched
self-consistency as the comparator that matters, the requirement that every round
carry *external* evidence because model self-critique without it is closed off by
five independent results, and keeping the horizon short because DeepBlip's error
propagates like `(1+C)^(tau-k)` backwards under weak overlap.

## READ FIRST — a premise check came out against the claim (2026-09-19)

Before designing anything, the experiments workstream tested the project's central
claim in tabular simulations with known laws (`docs/premise_findings.md`,
`experiments/premise/`, exploratory and **not** pre-registered). Two pieces held
up dramatically; one did not.

**Held up.** An *unadjusted* comparison of intervention classes on logged data
inverts the true ordering — 0 of 40 replicates recovered the sign, and in a second
law the class that is *optimal* from the far-wrong state had the *lowest* observed
mean outcome (0.186 against 0.637 for a perfunctory retry). Conditioning on the
intermediate state when valuing the *first* intervention reports a true +0.156
blip as +0.005, because that state is a mediator of the first action as well as a
confounder of the second.

**Did not hold up.** A correlational critic that conditions on the *full observed
state* and acts greedily recovered the exact optimal regime in 39 of 40
replicates (regret 0.001). Adding a latent feature that drives both the user's
choice and the outcome did not restore the bias at the decision level (regret
0.013 logged vs 0.015 randomized). Sweeping the coupling between the user's choice
and that latent feature, over a law where the best action *flips* with it, moved
the logged-minus-randomized regret gap by at most 0.030, and known-propensity IPW
repaired it only partly and non-monotonically.

**What dominated decisions was the horizon, not the confounding.** In every
condition the lookahead critic beat the myopic one — including under
randomization, where there is no confounding to correct. In one law the optimal
first intervention is the one with the *worse* immediate success probability
(0.204 against 0.262), because it moves the answer into a state from which repair
succeeds with probability 0.67.

**So the theory should probably not lead with "a naive reward model learns the
wrong effect, therefore use a causal critic."** On this evidence that argument is
sound for *reported effects* and weak for *chosen actions*. Two framings survive,
and they want different theorems:

1. *Identification and honest reporting.* What is and is not identified when the
   action is language; why descriptive turn-level comparisons of feedback types
   are invalid; what a design has to provide to make them valid. The
   sequentially-randomized design is then the contribution, not the fallback.
2. *Horizon-aware valuation.* Why a turn-level reward model is the wrong object
   even with no confounding at all, and what the value loss is as a function of
   how far ahead the critic looks. This is a statement about Q-functions versus
   immediate rewards and it needs no unmeasured-confounding story.

**Q11 (new, and the most consequential).** Which of those two is the paper's
primary claim? The experiments workstream has reprioritized the ladder on the
assumption that both are in scope with (1) as the headline, but the theory should
decide. If the intended headline is instead "causal correction improves decisions
on confounded logs", say so and the program will be rebuilt to hunt for the regime
where that is true — but be warned it looked narrow in three attempts to produce it.

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
  development running. Q1–Q10 open.
* **2026-09-19, experiments workstream** — Audit A1 (`results/audits/task_pool/`):
  the 591-task coding pool is valid (591/591 references pass their own hidden
  tests, and still pass after the visible assertion is carved out); `mbpp/794` is
  excluded because both of its hidden assertions are `assert not f(...)`, which a
  do-nothing stub satisfies. **Usable pool 590 tasks.** The visible/hidden split
  is now a hard requirement, not a nicety: for MBPP the assertion shown to the
  receiver is exactly `test_list[0]`, so grading uses `test_list[1:]` and an
  intervention can be audited mechanically for quoting a graded assertion.
* **2026-09-19, experiments workstream** — premise checks P1–P3; see the section
  at the top of this file. **Q11 is open and blocks the shape of the paper.**
* **2026-09-19, experiments workstream** — literature audit complete (141 citations
  verified, 96 prior-art items, adjudicated and adversarially reviewed). 132/141
  citations sound; **the novelty claim is not.** See the STOP section at the top of
  this file, `docs/literature_audit.md` and `docs/positioning.md`. Nine hard design
  constraints now follow from the audit.
