# RETRACTION of the STOP decision in `selection_decision.md`

**Written 2026-09-20 by the experiments workstream, which produced the retracted
document.** `docs/selection_decision.md` concluded STOP: that the selection-and-stopping
question was unanswerable in this regime and that the critic, the prompt interventions and
the generative policy should be cut. **That conclusion is withdrawn.** It was not supported
by the evidence I offered for it, and two independent lines of checking now agree on why.

The prompt for this came from the owner, who pointed out that the theory workstream has
largely been following my experimental lead, that I therefore carry most of the scientific
judgment, and that when experiments fail the first duty is to establish whether the
*design*, the *metric* or the *hypothesis* failed. I had not done that. Doing it overturns
the conclusion.

**Short answer: the design was wrong and the metric was wrong. The hypothesis was never
tested.**

## Part 1 — what I found when I interrogated my own instrument

`experiments/audits/g1d_instrument_check.py`, output in `results/audits/g1d_instrument/`.

### The probe generator was mostly inert

I manufactured probe inputs by mutating the literals of the visible assertion. Measured
over 2,568 probe slots on the 3B:

| probe outcome | count | share |
|---|---|---|
| every candidate raised the same error | 97 | 0.038 |
| every candidate returned an identical value (no signal) | **1,715** | **0.668** |
| **discriminating** | 756 | 0.294 |

**Median discriminating probes per task: 0.0.** For **251 of 420 tasks** there was *no*
discriminating probe at all, so "agreement" was trivially perfect and the picker silently
fell through to its tie-break. On the 7B it is worse: 13.5% discriminating, 356 of 450
tasks with none.

So the headline diagnostic I offered as the mechanism — "1.63 clusters per task, so a weak
model's draws mostly agree" — was substantially **a property of my probe generator, not of
the model.** Literal mutation does not keep an input inside a function's valid domain, and
when it leaves it every candidate fails identically.

### Restricted to where the instrument works, and where selection is even possible, the sign reverses

| subset | n | agreement + visible − visible picker |
|---|---|---|
| all tasks (what I reported) | 420 | +0.0095 [−0.0037, +0.0227] |
| probes actually discriminate (≥2) | 141 | +0.0213 [−0.0155, +0.0580] |
| opportunity exists (mixed bank, incumbent wrong) | 31 | **+0.1935 [+0.0522, +0.3349]** |
| both | 24 | **+0.2083 [+0.0424, +0.3743]** |

7B: +0.2500 [+0.0309, +0.4691] and +0.2857 [+0.0401, +0.5313].

**Read this carefully, because it is easy to over-claim in the other direction.** The
"opportunity exists" subset is defined *using the hidden outcome*, so these intervals are
conditional on opportunity and are **not** unconditional effect estimates — that is the
same error I am retracting, run in reverse. What they legitimately establish is a
**conversion rate**: given that a better selector *could* have gained, agreement took the
opportunity roughly 13–29% of the time. The small unconditional number and the large
conditional one are the same fact: **opportunities are rare, not the method inert.** My
document asserted the second and had only shown the first.

### The experiment could not have detected a perfect selector

| quantity | 3B | 7B |
|---|---|---|
| minimum detectable unconditional effect, 80% power | 0.0852 | 0.0750 |
| the **entire ceiling** for any selector | 0.0737 | 0.0356 |

**The MDE exceeds the ceiling.** An unconditional test over all tasks on this corpus was
structurally incapable of detecting even a perfect selector — the implied within-opportunity
effect needed is 1.16 and 2.11, i.e. above 100%. I reported nulls from an experiment with
no power and treated them as evidence of absence. That is the central error.

## Part 2 — what the theory workstream's audit found, independently

`docs/latest_selection_decision_audit_20260920.md`. Its blocking findings, all of which I
accept:

1. **Post-treatment selection in my candidate banks.** I dropped episodes whose receiver
   switched later — but the routing decision is *downstream* of the first candidate's
   quality, so this conditions on the outcome. They measured the magnitude: first-candidate
   success **0.698 for retained versus 0.105 for excluded** 3B episodes. My "i.i.d. draws"
   were a heavily selected easy subset, and every absolute rate I quoted inherits that.
2. **Wrong checker flag.** I used `n_fail == 0`; the source loop stops on
   `validation.passed`. So my "the same cheap check" claim is inaccurate.
3. **Probe provenance.** My probes derive from `scoring.split_assertions`, a visibility
   convention *I invented later*, not the source experiment's frozen visible-test artifact —
   and the stored `success_first_candidate` outcome was graded including those assertions.
   "Nothing touches a graded assertion" is therefore unsupported.
4. **G1c implemented a different policy than it documented** — clustering over all
   candidates with visible pass only as a tie-break, rather than the declared
   restrict-then-cluster rule. So its negative result is not a result about the stated gate.
5. **Closest cost is not matched cost.** 1.2–1.5 draws apart, and only generation calls were
   charged — not sandbox, validation, tokens or latency.

And three overinterpretations, all correct:

* **The ceiling was double-counted.** The 0.0737 oracle-minus-visible gap *already is* the
  residual after the incumbent's successes. Saying "the ceiling is 0.0737 and two-thirds of
  it is already taken" subtracts the incumbent twice.
* **"The effective sample was 33"** is rhetoric, not statistics: 33 is a count of
  outcome-selected opportunity events. The other 415 tasks still inform rates, harm and
  calibration.
* **The bound does not license what I used it for.** `E[max_j Y_j] − Y_visible` bounds
  *selection within a fixed candidate bank*. A prompt intervention **changes the candidate
  distribution**, so it is not bounded by the max over an existing bank. Cutting the critic,
  the prompt interventions and the generative policy on the strength of this bound was
  unjustified.

They also corrected E0: grading template heterogeneity against the replicate-specific
mixture kernel rather than the zero-offset kernel raises `FAIL_coarsening` coverage from my
0.886 to **0.9625**. My "violated coarsening breaks coverage" reading was an artifact of
grading against the wrong truth. And my "regret" was measured against a heuristic reference,
not an optimal policy.

## Part 3 — the corrected state of the question

Their `docs/selection_corrected_results_20260920.md` redoes it properly: all 4,488 initial
candidates retained regardless of later routing, a frozen 336/225 root split, a fixed
four-call bank, all four calls charged to every selector.

| receiver | selector | visible | learned | difference |
|---|---|---|---|---|
| 3B | gbm | 0.6674 | 0.6700 | +0.26 pp [−1.92, +2.44] |
| 3B | logit | 0.6674 | 0.6667 | −0.07 pp |
| 7B | gbm | 0.7093 | 0.7122 | +0.30 pp |
| **7B** | **logit** | 0.7093 | **0.7378** | **+2.85 pp [+1.19, +4.52]** |

One of four comparisons is positive with an interval excluding zero, uncorrected for
multiplicity, on a corpus already inspected — exploratory, as they say, and not a cheaper
policy, not a feedback effect. But it is direct evidence against my blanket claim that no
cheap public-feature selector can beat the incumbent.

## What actually holds now

* **Selection opportunities are rare in this regime** at a four-draw bank. That survives as
  a *descriptive* fact about this corpus, with the corrections above, and it is
  bank-size-dependent: the predicted mixed stratum rises from 0.319 at r = 4 to 0.437 at
  r = 8 and 0.612 at r = 32.
* **Agreement clustering converts a substantial share of the opportunities that exist**, and
  its apparent inertness in my run was largely my probe generator.
* **A learned selector can beat the visible picker on a fixed bank** (7B, +2.85 pp,
  exploratory).
* **Nothing here bears on prompt interventions or multi-round feedback at all.** That was
  the original hypothesis and it remains untested.

## What the design must do differently — the real lesson

1. **Never select the analysis cohort on anything downstream of the first candidate.** Use
   all draws; handle receiver switching by design, not by exclusion.
2. **Analyse on the stratum where the effect can live, pre-registered.** An unconditional
   mean over a population where 93% of units have no opportunity cannot detect the effect.
   Stratify on the opportunity-bearing stratum, or oversample it, and declare the
   conditional estimand in advance so conditioning is not outcome-selected after the fact.
3. **Build the probe generator properly and measure it before trusting it.** Type-directed
   or model-generated inputs, with a reported discrimination rate. A selector whose feature
   is inert on 60% of tasks has no chance, and I should have measured that first.
4. **Charge every cost**, and construct genuinely matched-cost mixtures rather than nearest
   neighbours.
5. **Keep the ceiling in its lane.** A fixed-bank ceiling bounds fixed-bank selection. It
   says nothing about interventions that change the bank.

## Status of the retracted document

`docs/selection_decision.md` is retained unaltered — it is what was concluded and how — with
a pointer to this retraction at its head. Its STOP recommendation, its cut-list, and its
claim that five independent lines converged are all withdrawn. The harvestable-stratum bound
survives **only** as a fixed-bank feasibility heuristic, with the double-count removed and
its scope restricted.
