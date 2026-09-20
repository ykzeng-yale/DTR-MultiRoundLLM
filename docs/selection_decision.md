# Deciding the selection question end to end

**Executed 2026-09-20, entirely at zero GPU cost.** Scripts
`experiments/audits/g1{b,c}_*.py`; outputs under `results/audits/g1b_agreement/` and
`results/audits/g1c_allocation/`.

`docs/gate1_rescope.md` named one question as deciding the project: **is the
candidate-selection headroom recoverable by anything that cannot see the hidden tests?**
`docs/g1a_selection_pilot.md` showed cheap static features recover none of it and named
the remaining candidate — cross-candidate **execution agreement**, the strongest known
cheap selector for code. This settles it.

## The method, and why it cost nothing

Agreement clustering needs no *expected* outputs, only that candidates be run on **common
inputs**. So probe inputs can be manufactured by mutating the literals of the one visible
assertion (integer increments, sign flips, zeroing, string truncation and doubling,
sequence reversal, halving, extension), and every candidate already in the log can be
executed on them in the sandbox. Median 6 probes per task, 93% task coverage (551 of 591),
870 cells in 105 seconds. Nothing touches a graded assertion: the selector sees only
candidate source, the visible assertion, and outputs on inputs whose correct answers
nobody knows.

## Result 1 — agreement does not recover the selection gap

| receiver | n | visible picker | agreement | agreement + visible | oracle | gap | agree+vis − visible | fraction of gap |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-3B | 420 | 0.7357 | 0.7405 | 0.7452 | 0.8095 | 0.0738 | +0.0095 [−0.0037, +0.0227] | **0.129** |
| Qwen2.5-7B | 450 | 0.7978 | 0.7978 | 0.8022 | 0.8333 | 0.0356 | +0.0044 [−0.0062, +0.0151] | **0.125** |

Both intervals cover zero. A 40-cell pilot had suggested 50% recovery; at n=420 that was
small-sample noise, which is worth recording as a caution.

**The mechanism is visible in the diagnostics.** Only **1.63 clusters per task** (3B) and
**1.28** (7B), with the top cluster holding **83%** and **92%** of candidates. At k ≈ 3.5
a weak model's draws mostly *agree with each other*, so clustering has almost nothing to
discriminate. This is why published agreement methods report large gains at k = 50–1000
and why those gains should not be expected here.

## Result 2 — agreement is a good confidence signal that is nonetheless useless here

Cluster size predicts correctness strongly and consistently: accuracy **0.879** when the
top cluster is large against **0.552** when small (3B), and **0.878** against **0.526**
(7B), correlations +0.44 and +0.40.

That looked like exactly what a stopping rule needs. It is not, and the reason is an
accounting fact: **adaptive best-of-N already spends only 1.036 expected draws**, because
the visible check passes on the first attempt about three-quarters of the time. An
agreement gate must draw at least twice before it can measure agreement, so it spends
more and buys nothing:

| receiver | policy | success | expected draws |
|---|---|---|---|
| 3B | adaptive best-of-4 | **0.7376** | **1.036** |
| 3B | agreement-gated 2→4 | 0.7367 | 2.522 |
| 7B | adaptive best-of-4 | **0.8190** | **1.016** |
| 7B | agreement-gated 2→4 | 0.8212 | 2.236 |

Paired against the closest-cost uniform policy: **−0.0009 [−0.0119, +0.0101]** (3B) and
**+0.0022 [−0.0029, +0.0073]** (7B), for **+1.2 to +1.5 extra draws**. The confidence
signal is real and largely *redundant with the visible check that is already being used*.

## Result 3 — why all five negative results were inevitable, computed exactly

Decomposing every task by how many of its independent draws pass the hidden tests:

| stratum | 3B (n=448) | 7B (n=485) | can a selector help? |
|---|---|---|---|
| all draws correct | 267 (0.596) | 356 (0.734) | no — nothing to choose |
| all draws wrong | 81 (0.181) | 78 (0.161) | no — nothing to find |
| **mixed** | **100 (0.223)** | **51 (0.105)** | only here |
| …of which the visible check already picks a correct one | 67 of 100 | 34 of 51 | already harvested |
| **tasks where any better selector could gain** | **33 of 448** | **17 of 485** | **the entire ceiling** |

**The effective sample for the selection question was never 448 tasks. It was 33.** Every
null above is what 33 tasks look like.

And this was predictable from a measurement made on day one. Audit A2 fitted a
beta-binomial to per-task difficulty and found it strongly **bimodal** (α = 0.348,
β = 0.230, both far below 1): tasks are reliably solved or reliably unsolved. Under that
fitted law the mixed stratum at r = 4 is **0.319**, against **0.223** observed at r ≈ 3–4.
The difficulty distribution measured before any of this work predicted the outcome of all
of it.

## The harvestable-stratum bound — a cheap pre-experiment feasibility test

The ceiling for *any* selection method is `P(0 < S < r)` under the fitted difficulty law,
times the fraction of that stratum the incumbent check does not already harvest. It costs
one beta-binomial fit to existing data and it bounds the whole research direction before a
single GPU hour. The prescription it gives:

| regime | P(mixed) at r = 4 | at r = 8 |
|---|---|---|
| this suite, fitted bimodal (α 0.348, β 0.230) | **0.319** | 0.437 |
| same mean, concentration ×3.5 (α 1.20, β 0.80) | 0.576 | 0.750 |
| same mean, concentration ×8.6 (α 3.01, β 1.99) | **0.713** | 0.890 |

Raising draws per task helps (r = 32 reaches 0.612 even here). **Concentrating difficulty
helps more than doubling the draws**: a suite whose tasks are of similar, moderate
difficulty has roughly 2.2× the harvestable stratum at the same mean success. MBPP plus
HumanEval against a quantized 3B is close to the worst case for this research question.

## Decision

**On this task family with these receivers: STOP.** The selection-and-stopping question is
not answerable here at any sample size that can be afforded, because only 33 of 448 tasks
carry any signal, and the cheapest incumbent check has already taken two-thirds of the
stratum that exists. This is not a power problem to be fixed with more compute; the
ceiling itself is 0.0737, and two-thirds of it is gone before we start.

**What survives, and it is worth more than the original hypothesis:**

1. **The harvestable-stratum bound** as a pre-experiment feasibility test for
   candidate-selection and test-time-scaling research, with the beta-binomial mechanism,
   the exact decomposition, and the regime prescription. Five independent negative results
   here are explained by one computable quantity.
2. **The estimator-validation result** (`docs/e0_results.md`): reading turn-level feedback
   effects off a confounded log inverts the true ordering — 0.000–0.060 versus 0.792 under
   randomization — while a state-conditioned critic beats weighting in 16 of 17 cells.
   That stands independently of anything above.
3. **The baseline-dominance result** (`docs/g0e_kill_criterion.md`): adaptive best-of-N
   beats a real multi-turn feedback loop at lower cost, which the multi-turn literature
   should have to confront.

**What to cut:** the branch tree, the 8-class ladder, the depth-2 factorial, the critic and
the generative policy. All of them price interventions whose effect cannot be resolved in
this regime.

**What a continuation would require, stated so it can be checked:** a task suite and
receiver pairing whose per-task difficulty is *concentrated* near 0.4–0.6 rather than
bimodal, verified by a beta-binomial fit with both parameters above 1, and r ≥ 8 draws.
Run the harvestable-stratum bound on the candidate suite **first**; if the ceiling net of
the incumbent check is under about 0.05, do not run the experiment.

## Honest limits

These are 3–4 draws per task from one routing experiment, not 8 from a purpose-built
design; more draws would widen the mixed stratum to a predicted 0.437 and might move the
agreement result. Probe inputs are literal mutations, weaker than type-directed or
model-generated inputs. And the whole analysis is one benchmark pair and two quantized
small models — the bound is general, but the verdict is specific to this regime. The
literature search running alongside this will say whether published agreement results are
consistent with the large-k, diverse-sample explanation offered here; if they report large
gains at small k on comparable models, this analysis is wrong somewhere and the mechanism
claim needs revisiting.
