# G0e — kill criterion K1 has **fired**: adaptive best-of-N beats the multi-turn loop

> **Historical snapshot; conclusions require the 2026-09-20 corrections.** Read [continuation report](continuation_report_20260920.md), [theory reconciliation](theory_reconciliation_20260920.md), [experiment audit](experiment_recheck_20260920.md), and [literature recheck](literature_recheck_20260920.md) before using this document. Earlier universal impossibility, optimality, matched-cost kill, and feature-no-signal claims are superseded. Original text remains for provenance.

**Executed 2026-09-19, zero GPU cost.** `experiments/audits/g0e_adaptive_bon.py`;
output `results/audits/g0e/20260920T003221Z/`.

Best-of-N is the comparator that can kill this project: it turns extra compute into
quality with no multi-turn machinery, no feedback and no causal inference. In its
**adaptive** form — draw candidates one at a time, stop as soon as a cheap visible check
passes — it is stronger still, because it spends fewer calls for the same quality. The
programme pre-registered this as **K1 BASELINE DOMINANCE**, and specified that it be
tested on existing data before any new token is generated.

It has now been tested, and multi-turn loses.

## The comparison

The sibling project's completed 4,488-episode log contains, for each (task, receiver),
several **independent** episodes starting from the same prompt with different seeds.
Their first candidates are i.i.d. draws — exactly what best-of-N needs — and the same log
records what the multi-turn loop achieved. Both arms use the **same** visible check as
their signal, so neither gets a better oracle. Adaptive best-of-N is computed **exactly**
by enumerating ordered samples, not simulated. 624 episodes in which the receiver
switched mid-episode were excluded, since those are not draws from one receiver.

### Qwen2.5-3B, 448 tasks with ≥ 3 independent episodes

| arm | final success | mean calls |
|---|---|---|
| single attempt | 0.7169 (SE 0.0187) | 1.00 |
| **multi-turn loop** | **0.7279** (SE 0.0188) | **1.09** |
| adaptive best-of-2 | **0.7418** (SE 0.0188) | **1.05** |
| adaptive best-of-3 | **0.7461** (SE 0.0189) | **1.07** |
| oracle pass@3 (unachievable ceiling) | 0.8075 | 3.00 |

Paired over the same tasks, **multi-turn minus adaptive best-of-N**:

| k | Δ success | 95% CI | Δ calls |
|---|---|---|---|
| 2 | **−0.0140** | **[−0.0204, −0.0075]** | +0.04 |
| 3 | **−0.0182** | **[−0.0260, −0.0105]** | +0.03 |
| 4 | −0.0121 | [−0.0191, −0.0051] | +0.02 |

Adaptive best-of-N is **better and cheaper**, with the interval excluding zero at every k.

### Qwen2.5-7B, 485 tasks

| arm | final success | mean calls |
|---|---|---|
| multi-turn loop | 0.8057 (SE 0.0168) | 1.05 |
| adaptive best-of-3 | 0.8095 (SE 0.0170) | 1.05 |
| adaptive best-of-4 | 0.8247 (SE 0.0173) | 1.01 |

Paired: k = 3 gives Δ = −0.0038 [−0.0116, +0.0041] — a tie; k = 4 gives
Δ = −0.0032 [−0.0058, −0.0006] — best-of-N significantly ahead, at lower cost.

## K1's verdict

K1 fires when the upper 95% bound on `V(multi-turn) − V(adaptive best-of-N)` at matched
budget falls below +0.01. On the 3B that upper bound is **−0.0075**; on the 7B it is
**−0.0006**. **K1 has fired on both receivers.**

## What this does and does not mean

**It does not mean multi-turn feedback does nothing.** Audit A3 measured that the same
loop repairs 23.9% of failures it acts on. Both facts hold: feedback repairs some
failures, and a fresh independent sample repairs more per unit of compute. The loop's
problem is not that repair fails but that **resampling is a better use of the same call**,
for this receiver on this task family.

**It is consistent with everything else measured here**, which is what makes it
credible rather than a fluke:

* the pilot found a content-free retry (0.110) *beating* structural localization
  (0.066) — feedback content was not buying anything;
* the loop's self-check stopping rule stopped on 50.4% of all failures (A3);
* the self-correction literature finds intrinsic self-correction degrades performance
  without external signal.

**It sharpens where value remains, and the numbers point one way.** The oracle ceiling
`pass@3 = 0.8075` against adaptive best-of-N's achieved `0.7461` is a **6.1-point gap
that is pure selection** — the correct answer was already generated and the visible check
failed to identify it. Audit A3's separate finding was that oracle stopping decisions are
worth **+4.6 points**. Both say the same thing: on this task family the scarce resource is
**knowing which artifact is right and when to stop**, not crafting a better message.

## Consequences

1. **The headline claim cannot be "multi-turn feedback improves outcomes".** On the only
   real data available it does not, relative to the honest baseline.
2. **The defensible object is a selection-and-stopping policy over states with logged
   propensities** — which is what the DTR framing genuinely contributes, and what
   `docs/premise_findings.md`, `docs/audits.md` and `docs/positioning.md` had already
   converged on from three other directions. This is now a fourth.
3. **Every future comparison must include adaptive best-of-N at matched budget**, not
   single-shot, as its primary baseline. A design that beats single-shot and never faces
   adaptive best-of-N is not answering the question a reviewer will ask.
4. **Gate 1 should be re-scoped before it is frozen.** Its core contrast (ρ and β for
   feedback classes) is now measuring a quantity we have evidence is small, while the
   selection/stopping arm is measuring one we have evidence is large.

## Honest limits

This is the *sibling project's* loop, whose intervention is a repair prompt carrying
visible-test output — one real multi-turn policy, not the best conceivable one, and not
this project's frozen taxonomy. A better intervention could in principle beat adaptive
best-of-N; nothing here proves otherwise. What it establishes is that **beating adaptive
best-of-N is a real bar, it is not automatically cleared, and the burden is now on any
multi-turn design to clear it explicitly.** The multi-turn arm also averaged only 1.09
calls, because its stopping rule ended most episodes after one — so this is a comparison
of two cheap policies, and it says nothing about behaviour at large budgets.
