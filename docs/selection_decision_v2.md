# The selection question, decided end to end (supersedes the retracted v1)

**2026-09-20.** Replaces `docs/selection_decision.md`, whose STOP conclusion is retracted
(`docs/selection_decision_RETRACTED.md`). This version rests on three things v1 lacked: a
literature search with adversarial verification of the papers the decision turns on, a
probe-free measurement on the **complete, correctly-flagged** corpus, and the power
arithmetic.

**Verdict: PIVOT.** Not STOP, and not GO on selection accuracy. The target becomes
**compute efficiency with a certified do-no-harm guarantee**, because that is the estimand
this sample size can carry. Selection accuracy becomes a secondary descriptive arm.

## 1. The literature conflicts, and the conflict is informative

| paper | regime | agreement's share of the oracle gap |
|---|---|---|
| DOCE (arXiv:2408.13745) | k = 50, DeepSeekCoder-6.7B, full public test suites as the filter | **73–83%** |
| İşcan (arXiv:2606.16999) | **k = 8**, 0.5–1.5B | **14%, null**, 0 of 6 cells significant |
| Semantic Voting (arXiv:2605.08680) | N = 50, MBPP+ | **−13%** — worse than "first syntactically valid" |
| CodeT / AlphaCode-C (arXiv:2207.10397) | k = 10–100 | 4.2–18% at k=100, negative on one model |

These are not contradictory once the reconciling variables are named: **the strength of the
visible filter, and k.** With full public test suites the filter drains the trap — agreement
has little left to fix but the residual gap is also concentrated where it helps. At small k
clustering is close to vacuous: Semantic Voting *measures* 1.2–1.5 clusters per problem at
N = 50, and AlphaCode needed ~100,000 draws with >99% filtered.

**Our regime is none of these three.** Weakest filter in the literature (a *single* visible
assertion), smallest k (3–4 now, 8 planned), and the only quantized receiver anywhere in
this literature. **So the literature does not settle our case, in either direction.**

## 2. Corroboration that is genuinely independent of my broken instrument

My static-feature null was *not* an artifact. İşcan's "capability scissors" reproduces it
with different features on a different model: a learned probe scores **AUC 0.479 for hidden
correctness** while the same features reach **0.985 for visible-pass**. And trained reward
models go *negative* in four separate papers — CodeRM −0.80 on MBPP+, AceCoder −0.6 below
greedy on **Qwen2.5-Coder-7B-Instruct** (our own receiver family), CodeScore below random.

So of my two nulls, the **static-feature** one replicates in the literature; the
**agreement** one was confounded by my inert probes and remains untested by me.

## 3. The measurement that decides it, and it is probe-free

`experiments/audits/g1e_trap_mass.py`. A selector that cannot see hidden tests can only
net-gain where the incumbent's pick is hidden-wrong **and** a hidden-correct candidate is in
the same bank. Counting those tasks bounds every such selector, needs no probes, and is
computed on the complete corpus with both of the audit's corrections applied: **all 4,488
candidates retained** (the 624 later-switching episodes are kept, not dropped) and the
incumbent flag is `validation.passed`, the flag the source loop actually used.

| quantity | 3B (n=561) | 7B (n=561) |
|---|---|---|
| everything correct and passing | 0.4135 | 0.6025 |
| no correct candidate anywhere | 0.2406 | 0.2246 |
| **opportunity** (incumbent wrong, a correct candidate exists) | **0.0695** [0.0513, 0.0936] | **0.0357** [0.0232, 0.0544] |
| …reachable *within* the visible-passing set | 0.0624 (35 of 39) | 0.0303 (17 of 20) |
| …correct candidate only *outside* it | 0.0071 (4) | 0.0053 (3) |
| **strict consensus trap** | **0.0428** [0.0289, 0.0629] | **0.0125** [0.0061, 0.0255] |

Three things follow.

**The literature's kill-switch does not fire.** İşcan found trap mass near zero and
concluded the arm was dead. Ours is **0.0428** on the 3B — small but real, and 3.4× the 7B's.
İşcan *predicted* exactly this: "a weaker visible-test filter would refill the consensus
trap." Our one-assertion split **is** that weaker filter. He predicted it; we have now
measured it. That is a genuine, citable contribution regardless of what else happens.

**A filter-respecting selector is not structurally blocked.** 35 of 39 opportunities sit
*inside* the visible-passing set, so a rule that reorders within the filter has almost all of
the available mass; only 0.7% of tasks require overriding the filter, which is the move the
literature measures as harmful.

**Two corrections mattered less than feared, and I should say so plainly rather than
defensively.** The post-treatment selection flaw was real and large for absolute rates
(0.698 vs 0.105), but the *opportunity mass* barely moved: 0.0737 on the flawed corpus
against 0.0695 here, because the excluded episodes were mostly hidden-failures that land in
"no correct candidate anywhere" rather than in the opportunity stratum. And the checker-flag
error touched **6** first decisions. Both criticisms were correct; neither overturns this
particular statistic.

## 4. Why the selection arm still cannot be confirmed here — power, not impossibility

| n (opportunity tasks) | MDE for a paired binary contrast, 80% power |
|---|---|
| **39** (3B, measured) | **0.317** |
| 20 (7B) | 0.443 |
| 67 (if k = 8 doubles the mixed stratum) | 0.242 |
| 89 (what we would need) | 0.210 |

Conversion of opportunities is **0.14** (İşcan, measured at our k) to **0.29** (CodeT's best
cell at k=100, an upper bound). My own conditional estimate was 0.19–0.29, though it is
outcome-selected and not an effect estimate. **To detect a conversion of 0.21 we need ~89
opportunity tasks; at a 7% opportunity rate that is ~1,281 tasks, or ~742 at k = 8. We have
561.** So the arm is short by roughly 1.3–2.3× in tasks — **underpowered, not impossible**,
and that is a different claim from the one I made in v1.

Unconditionally, the whole effect is 0.010–0.020 on the 3B (5–11 tasks of 561) against an
unconditional MDE of 0.084. It was never going to show up in a marginal mean.

## 5. Why the pivot target is the right one

Two independent 2026 papers converge on execution agreement being worth a **16–19% compute
saving at approximately zero accuracy change** (İşcan's ACE with a Hoeffding–Bentkus
Learn-then-Test certificate; CoTT, arXiv:2609.12489, at $0.065 against $0.077). That is a
*large* effect relative to our noise, where a 1-point accuracy difference is not.

And the estimand matches the sample size. İşcan's Proposition 1: a distribution-free
do-no-harm certificate cannot bound population harm at 5% even at zero observed harm unless
n ≥ 45. **We have 230–561.** So we can certify do-no-harm and measure a compute saving; we
cannot establish a small positive accuracy effect. The design should target what the data can
support.

This also lands where four other lines already pointed — the premise checks (horizon
dominates confounding), audit A3 (stopping headroom at fixed feedback content), the hostile
literature review (spend the effects on when to intervene), and G0e — **with the correction
that G0e's result holds only at ~1.1 calls**, because that loop's stopping rule rarely took a
second turn.

## 6. The decision

**Primary arm — compute efficiency with certified no harm.** A stopping/allocation rule over
policy-observable state, evaluated against adaptive best-of-N at matched *total* cost
(generation, sandbox, validation, tokens and latency — v1 charged only generation calls).
Primary estimands: compute saved at a certified do-no-harm operating point, with the
certificate constructed distribution-free. Pre-register the harm bound before looking.

**Secondary arm — selection, reported descriptively and honestly.** Trap mass, the
within/outside-filter decomposition, and the conversion rate, pre-declared as
*conditional-on-opportunity* quantities with the conditioning stated in advance so it is not
outcome-selected after the fact. This is publishable as the first quantized-receiver
measurement in this literature and the first measurement of İşcan's predicted
weak-filter boundary condition — a null or a small positive are both informative.

**Not cut, and v1 was wrong to cut them.** The critic, the prompt interventions and the
generative policy. A fixed-bank ceiling bounds fixed-bank selection; a prompt intervention
changes the candidate distribution and is not bounded by the max over an existing bank. **The
original hypothesis remains untested and requires its own randomized feedback experiment.**

**Before any of it:** rebuild the probe generator with type-directed or model-generated
inputs and report its discrimination rate. Mine was inert on 60% of tasks, and no selector
built on it can be believed.

## 7. What would change this verdict

If the rebuilt probe generator reaches a high discrimination rate and the conversion rate on
the opportunity stratum comes in above ~0.32, the selection arm becomes detectable at n = 39
and should be promoted. If trap mass on a new, harder task pool exceeds ~0.15, the arm
becomes detectable without any increase in conversion. Both are cheap to check first.
