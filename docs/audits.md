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

---

## Correction to A1, and what it does and does not do to A2 and A3 (2026-09-19, later the same day)

A design review of the audits found that **A1's discrimination check (S5) was far
too weak**, and the correction is load-bearing enough to record here rather than
quietly amend the table above.

**What was wrong.** A1 tested discrimination with a single `return None` stub and
found one task (`mbpp/794`) satisfied by it. A proper battery of trivial stubs raises
that to **22 tasks**. Worse, a candidate that defines a universal equality dunder —
`__eq__` returning `True`, and five variants of the same idea — passes the hidden
tests of **555–557 of 591 tasks (0.939–0.942)**, reproduced in 59 s. The verifier
inherited from the sibling repository records such code in `hack_flags` but does not
act on it, so as written the outcome was exploitable in principle.

**The fix, measured.** Two independent defences now live in
`experiments/common/integrity.py`:

| defence | effect | false positives on the 591 references |
|---|---|---|
| `canary_block` — one hidden assertion re-issued with a corrupted expected value, which a correct solution must fail | the `__eq__` family drops from 555–557 to **0–2 of 591** | **0 / 591** (all references still pass) |
| `hack_gate` — static AST gate: no dunder redefinition, no module-attribute patching, no module-scope builtin rebinding | stops 9 / 9 attack variants tried, including a dunder-free module-patch route | **0 / 591** |

Neither suffices alone: the canary is not constructible on 27 MBPP tasks whose
assertions use `math.isclose`, and the gate only stops routes that were enumerated.
Both must run on every graded candidate. A naive builtin-rebinding rule was rejected
because it produces 19 false positives — references idiomatically write `sum = 0`
inside a function body — so the rule applies at module scope only, with a carve-out
for a task whose own entry point is named `sum`.

**What this does to A2 and A3 — measured, not assumed.** Those rates were read from
the sibling project's log, graded with the unfixed verifier, so the natural worry is
that they are biased upward. They are not, and this is checkable rather than
arguable: `hack_flags` is present as a list in **all 4,488 episodes** and is
**non-empty in none of them** (0 / 4,488 episodes, 0 / 6,063 decision records), and
the flagger demonstrably fires on a known-bad string. No real model output in that
run attempted any flagged route. **The upper bound on the upward bias in A2's
0.600 / 0.708 first-attempt rates and in A3's 0.239 repair, 0.162 degradation and
+4.6-point stopping headroom is therefore 0.0000.**

**But the gate is still mandatory here, for a reason that does not apply to that
run.** Nothing in the sibling experiment was optimizing against the grader. This
project will train a policy whose objective *is* the graded outcome, and
reward hacking appears precisely under that pressure. An exploit rate of zero under
no optimization pressure is no evidence at all about the rate under optimization.

**Independent confirmation of the effective pool size.** Excluding references that
fail, tasks passed by the trivial-stub battery, and tasks whose mutation kill rate is
0.00 gives **564 tasks**; intersecting with the informative difficulty band gives
**230** (155 MBPP, 75 HumanEval). A2 estimated ~230 by a completely different route
(a beta-binomial fit to per-task success counts). Two independent routes to the same
number is the strongest evidence available that the effective sample is ~230 tasks.

**New: the hidden tests do not always discriminate.** Seven AST mutations of each
reference, 1,965 mutants over 562 tasks, 35 s: overall kill rate **0.8656**,
task-clustered 95% CI [0.8490, 0.8820]. 184 of 562 tasks have a kill rate below 1.0,
**47 are at or below 0.50**, and 2 are at 0.00. Argument-swap mutants survive 30.9% of
the time. This is a property of the benchmark, not of our harness, and it caps how
finely any outcome defined on these tests can resolve a change in behaviour.

Scripts: `experiments/audits/data_evaluator/audit_{reward_hacking,discrimination,
sentinel_evasion,pool_and_psuite}.py`; outputs in
`results/audits/data_evaluator/`. The A1 run directories above are **not** amended —
they record what was measured at the time — and `results/audits/task_pool/NOTES.md`
now points here.

---

## A4 — assertion-level visible/hidden split, and the final pool (2026-09-19)

A harness review found a second defect in the split, and it blocked more of the
design than the stub check did: `verify.split_tests` treated HumanEval's `check`
function as one opaque unit, so **all 164 HumanEval tasks had no
intervener-observable verdict and a hidden-assertion count of 1**. Every design that
conditions on an observed verdict — which is all of them, because an intervention
round with no external evidence is closed off by the self-correction literature —
was therefore undefined on 28% of the pool. Only 76 of 164 prompts carry a `>>>`
doctest from which a verdict could be scavenged, so the obvious remedy was to
exclude the other 88.

**A better fix, measured.** `experiments/common/scoring.py` splits `check` at
assertion level, making the two benchmarks structurally identical instead of
excluding anything: parse the assertions out of `check`, drop any assertion whose
inputs the prompt's own docstring already displays, then hold out the first of the
remainder as visible and grade on the rest — exactly MBPP's arrangement.

Audit A4 (`experiments/audits/audit_scoring_split.py`, CPU only, all rules pass):

| | MBPP | HumanEval |
|---|---|---|
| tasks | 427 | 164 |
| `check` splittable into assertions | n/a | **158** |
| **usable** (one visible assertion **and** ≥ 1 graded assertion) | **427** | **156** |
| hidden assertions per task (mean / median / min / max) | 2.1 / 2 / 2 / 6 | 5.15 / 4 / 1 / 25 |
| tasks with prompt-revealed assertions removed from grading | 0 | **76** |
| assertions removed from grading because the prompt reveals them | 0 | **193** |
| references still passing the hidden-only program | 427 / 427 | 156 / 156 |

So the split recovers **156 of 164** HumanEval tasks rather than the 76 an exclusion
rule would have kept, and it removes 193 assertions that would otherwise have been
graded as hidden while the prompt displayed their inputs. The 8 it cannot use are
`humaneval/{32,34,35,38,44,50,53,129}`: six wrap their assertions in a `for` loop and
are indivisible, and two have nothing left after the revealed assertions are removed.

### The final pool: 230 tasks, by three independent routes

| gate | tasks |
|---|---|
| A1, usable under the (too weak) single-stub check | 590 |
| POOL A — after the trivial-stub battery, the integrity gates and the mutation-kill exclusion | 564 |
| A4 — scoring-usable (visible verdict and ≥ 1 graded assertion) | 583 |
| POOL A ∩ scoring-usable | **561** |
| ∩ informative difficulty band | **230** (155 MBPP, 75 HumanEval) |

The scoring rule costs only 3 tasks beyond POOL A
(`humaneval/{44,53,129}`). And 230 is now the third independent route to the same
number: A2 reached it by fitting a beta-binomial to per-task success counts, the
integrity/mutation route reached it through POOL A, and the scoring route reaches it
again. `results/audits/final_pool.json` holds the list; it is the pool the
experiments use, and any future gate can only shrink it.
