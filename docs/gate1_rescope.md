# Gate 1, re-scoped after K1 fired

> **Historical snapshot; conclusions require the 2026-09-20 corrections.** Read [continuation report](continuation_report_20260920.md), [theory reconciliation](theory_reconciliation_20260920.md), [experiment audit](experiment_recheck_20260920.md), and [literature recheck](literature_recheck_20260920.md) before using this document. Earlier universal impossibility, optimality, matched-cost kill, and feature-no-signal claims are superseded. Original text remains for provenance.

**Written by the experiments workstream, 2026-09-19, as a decision memo.** It changes
what Gate 1 spends its first GPU hours on. It does not change any frozen artifact,
because nothing is frozen yet — which is the point of having tested K1 first.

## What changed

Kill criterion K1 fired (`docs/g0e_kill_criterion.md`): on the only completed real data,
adaptive best-of-N beat a real multi-turn feedback loop at **lower** cost, on both
receivers, with the paired interval excluding zero. Alongside it:

| evidence | what it says |
|---|---|
| pilot, n = 68 states | content-free retry 0.110 vs structural localization 0.066 — the content contrast ran the wrong way |
| power, measured variance | 273 states to detect a 0.05 contrast; the informative pool is 230 |
| audit A3 | oracle **stopping** decisions worth **+4.6 points** at fixed feedback content |
| G0e | oracle `pass@3` 0.8075 vs achieved 0.7461 — **6.1 points in selection alone** |
| E0, 17 cells | conditioning beats weighting for *decisions* in 16/17 cells; the log-reading failure is total for *reported effects* |
| repaired theory, R2 | a **stopping-only regime's value is an unweighted mean, `W ≡ 1`** |

Read together: the old Gate-1 core contrast measures a quantity the evidence says is
**small and underpowered**, while the quantity the evidence says is **large** —
which artifact to return, and when to stop — was a secondary arm. That is backwards.

## The re-scoped Gate 1

**New primary question.** Can a learned, policy-observable selection-and-stopping rule
beat adaptive best-of-N at matched budget?

**New primary estimand.** `Δ = V(π̂_φ) − V(adaptive BoN)` at matched expected calls and,
separately, at matched completion tokens, where `π̂_φ` is measurable with respect to the
frozen policy-observable feature map `φ` — which by construction **excludes** the hidden
verdict and everything derived from it.

**The efficiency that makes this cheap: G1a already buys the whole primary.** G1a draws
478 tasks × 8 independent seeds = 3,824 rollouts (**3.07 GPU-h**), recording the visible
and hidden verdicts separately. From that single tree, at no additional generation cost:

* adaptive best-of-N at every `k ≤ 8`, computed **exactly** by enumerating ordered
  samples — the baseline;
* the oracle `pass@k` ceiling — the headroom;
* the joint distribution of (visible verdict, hidden verdict, `φ`) — which is exactly the
  training data for `E[ψ | φ]`, the implementable stop/selection rule;
* the independent-redraw arm that G1b needs.

So **the new primary needs no intervention arms at all**, and it is the statistically
cheapest object in the framework: `W ≡ 1`, unweighted means, no importance weighting, no
positivity floor, no propensity model. The theory's repair (R2) and the measurement (A3,
G0e) point at the same arm from opposite ends.

**Mandatory reporting, per the theory's R3 and E13.** Report the oracle value and the
implementable rule's value **as a pair, never the oracle alone.** The 6.1-point selection
gap and the 4.6-point stopping gap are upper bounds available to something that peeks at
the outcome; how much of either is reachable from `φ` is precisely the empirical question,
and the honest headline is the fraction recovered.

## Revised ordering

| order | arm | GPU-h | why here |
|---|---|---|---|
| 1 | **G1a** — 478 tasks × 8 seeds, visible and hidden graded separately | **3.07** | delivers the entire new primary, the baseline, the ceiling and the variance calibration |
| 2 | **G1a′** (new, CPU) — fit `E[ψ | φ]`, evaluate `π̂_φ` against adaptive BoN on held-out task folds | 0.00 | the primary analysis; cross-fitted over task families, `W ≡ 1` |
| 3 | G1e / G1f — contamination and leakage gates | 2.16 | must precede any confirmatory content claim |
| 4 | **G1c, demoted and re-cut** — the content contrast, on the **repair stratum only**, with A3 redefined as **execution-grounded** rather than structural | ~3.5 | pre-registered as a precision result; the pilot tested the weaker variant |
| 5 | G1d / G1g — perturbation twins and compliance | 1.97 | unchanged |

**Dropped from Gate 1** (not from the project): the depth-2 factorial and the 8-class
ladder move behind the primary, since there is no reason to price a sequential
intervention effect before establishing that any intervention effect clears the baseline.

**Cost.** The new primary is **3.07 GPU-h plus CPU** against the old Gate 1's 12.60, and
it answers the question the evidence says is live. At the measured multi-turn throughput
(909 calls/hour, `docs/pilot_findings.md`), 3,824 rollouts is **4.2 contended hours**.

## What must still be true for the project to work

1. **`φ` must carry signal about the hidden verdict.** If `E[ψ | φ]` is uninformative, no
   selection rule can recover any of the 6.1 points and the programme's remaining claim
   collapses to the reporting result. The visible verdict is one bit and is absent on
   20.8% of the informative pool, so this is a real risk and it is now the project's
   central empirical question rather than a detail.
2. **Beating adaptive best-of-N must remain the bar.** Any later comparison against
   single-shot only is not answering the question.
3. **The content arm stays in, honestly.** Execution-grounded feedback repaired 23.9% of
   failures in A3, against 11.0% for a content-free retry — read with the pilot's 6.6% for
   structural pointing, the ordering says the information that matters is *execution
   output*. That is worth one properly powered contrast, pre-registered as a precision
   result given that 230 tasks cannot resolve below about 0.05.

## What this does to the paper

The object becomes **sequential selection and stopping under known propensities**, with
turn-level interventions as a secondary arm. That is still a dynamic treatment regime: the
action is continue-with-class / stop-and-return-which, the visible verdict is a
time-varying confounder affected by prior actions, the propensities are known by design,
and the outcome is programmatic. It keeps every part of the framing that survived the
literature audit, drops the part the data will not support, and — unlike the original —
has a baseline it has a measured reason to think it can beat.
