# Audits A1–A3 — the measured evidence base, before any GPU time is spent

Three audits were run before designing anything, all **CPU-only and at zero GPU
cost**. Two read the task pool directly; one reads a *completed* run from the
sibling project `ykzeng-yale/DTR-AgentEvals`, which used the same machine, the same
inference server and quantizations, and the same task file (identical
`tasks_sha256` — verified, not assumed).

Scripts `experiments/audits/audit_{task_pool,difficulty,iteration_value}.py`;
outputs under `results/audits/`.

## A1 — the task pool can carry the experiment

591 MBPP-sanitized + HumanEval tasks with hidden tests, executed in the Seatbelt
sandbox.

| finding | value |
|---|---|
| references passing their own full assertion set | 591 / 591 |
| references still passing after the visible assertion is carved out | 591 / 591 |
| tasks passed by a do-nothing stub on the hidden-only program | 1 (`mbpp/794`, excluded) |
| median share of the solution body already visible in prompt + visible assertion | 0.12 (MBPP 0.14, HumanEval 0.08) |
| tasks with ≥ 60% of the body already visible | 0 |
| **usable pool** | **590** |

The load-bearing detail: for all 427 MBPP tasks the assertion shown to the receiver
is *exactly* `test_list[0]` (it equals `signature_example`), so it is identifiable
and can be excluded from grading. This project therefore grades MBPP on
`test_list[1:]` and HumanEval on its whole hidden `check`. Without that split,
"more informative feedback works better" would be true by construction, because an
intervention could quote a graded assertion.

`mbpp/794` is instructive rather than incidental: both of its hidden assertions are
`assert not f(...)`, which `return None` satisfies. **Carving out the visible
assertion can destroy a task's discriminating power**, so the stub check has to run
on the hidden-only program for any pool used here.

## A2 — the pool is bimodal, and the effective sample is a fraction of 590

Per-task first-attempt success, read from the sibling's completed 4,488-episode log
(median 4 episodes per task per model). A beta-binomial was fitted to the per-task
success counts, because four draws cannot distinguish a task with true success 1.0
from one at 0.85 (P(4/4 | 0.85) = 0.52), so raw "at ceiling" counts overstate the
true ceiling.

| receiver | mean first-attempt success | implied mass > 0.95 (ceiling) | implied mass < 0.05 (floor) | implied mass 0.1–0.9 (informative) | fitted α, β |
|---|---|---|---|---|---|
| Qwen2.5-3B-Instruct | 0.600 | **0.334** | 0.156 | **0.406** | 0.348, 0.230 |
| Qwen2.5-7B-Instruct | 0.708 | **0.581** | 0.182 | **0.182** | 0.170, 0.071 |

Both fits are strongly U-shaped (α and β well below 1): **tasks are either reliably
solved or reliably unsolved, not concentrated in an informative middle.**

Consequences for design:

1. **The effective sample is about 230 tasks with the 3B and about 100 with the
   7B**, not 590. Every power calculation must use that, and the 7B's informative
   subpool is probably too small to be a primary receiver.
2. **Use Qwen2.5-3B as the primary receiver** — 2.2× more informative tasks.
3. Per-task effects will be highly heterogeneous and concentrated on a minority of
   tasks. That suits a heterogeneous blip-effect story and hurts a marginal average
   effect, which argues for stratifying on the first attempt and for defining the
   primary estimand **conditional on the first attempt failing**, with the
   already-correct stratum analysed separately for *harm*.

Caveats: the source project's prompt format and grading (all assertions) are its
own, so the *level* of these rates is a proxy. The *ranking* of tasks by difficulty
should be far more stable than the level. The real rate must be measured here once
the design is frozen.

## A3 — where the headroom in iteration actually is

Same completed 4,488-episode log. All rates are conditional on the hidden-test
status of the **first** candidate. Wilson 95% intervals, because two of the cells
are small.

| quantity | estimate | counts | 95% CI |
|---|---|---|---|
| episodes taking more than one turn | 0.196 | 881 / 4488 | — |
| **repair**: final correct, given first wrong and another turn taken | **0.239** | 184 / 770 | [0.210, 0.270] |
| **degradation**: final wrong, given first *correct* and another turn taken | **0.162** | 18 / 111 | [0.105, 0.242] |
| failures stopped after one turn by the loop's own self-check | **0.504** | 781 / 1551 | [0.479, 0.528] |

Read together:

* Iteration genuinely repairs about a quarter of failures, so there is something to
  optimize.
* **Iteration also destroys about one in six already-correct answers.** Continuing
  is not free, and a mean-outcome summary hides this. Degradation must be a
  separate reported outcome, not folded into an average.
* A stopping rule based on the system's **own self-check** stopped on half of all
  failures. Self-assessment is not the outcome, and treating it as one costs most
  of the available repair.

**Headroom from stopping decisions alone**, holding the feedback content completely
fixed: observed final success 0.691; with oracle stopping decisions (never stop on a
failure, never disturb a correct answer) 0.737 — an absolute gain of **+4.6
percentage points**. Stated assumptions, which make this an optimistic bound:
prematurely stopped failures are assumed to repair at the same 23.9% rate, and
oracle stopping is not available to any real rule.

## Why these three audits change the program

The premise checks (`docs/premise_findings.md`) found that the decision-level
damage from time-varying confounding is small, while the damage from **not looking
ahead** is large. A3 says the same thing from real data and in units anyone cares
about: on this task family, roughly 4.6 points of final success are sitting in
**when to stop**, not in which words to use. A2 says the experiment that goes after
it must be stratified on the first attempt and sized against ~230 tasks, not 590.
A1 says the outcome it is measured against is sound, provided the visible/hidden
assertion split is enforced and audited.

So the experimental program leads with the **stopping and horizon** question, keeps
**identification and honest effect reporting** as the methodological contribution,
and treats "causal correction of a confounded log improves decisions" as a scoped
secondary claim that the evidence so far does not support strongly.
