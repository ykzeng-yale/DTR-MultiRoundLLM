# Pilot findings — first real-model measurements, and they are not encouraging

**Status: unfrozen pilot, n = 68 failing states.** These are the first real receiver
calls made for this project, run as design calibration before any pre-registration.
They are not confirmatory results and none of them is powered. They are recorded
because two of them point against the project's premise and one invalidates a cost
claim, and all three change what should be frozen.

Receiver: Qwen2.5-3B-Instruct q4_k_m via `llama-server` at four slots, temperature
0.7, under foreign GPU load from a sibling project's live stage. Tasks drawn from the
audited pool; the repair stratum is the set of states where the first attempt failed
the hidden tests.

## 1. The headline content contrast points the wrong way

| arm | repair rate in the repair stratum |
|---|---|
| **A1** RETRY — content-free, provably zero task information | **0.110** |
| **A3** LOCALIZE — point at where the output goes wrong | **0.066** |

Contrast **A3 − A1 = −0.044**, SE 0.036 (matched, paired within state),
95% CI **[−0.114, +0.026]**.

Not significant at n = 68, and the interval comfortably covers zero. But the point
estimate says that localizing the error did *worse* than a bare "try again", and that
is the direction the literature predicts: Tyen et al. find LLMs cannot reliably find
their own reasoning errors though they can fix them once the location is given, and
UFO (arXiv:2507.14295) shows a content-free retry already elicits multi-turn gains. If
the intervener cannot localize accurately, A3 degenerates into a retry carrying a
misleading hint — which is what the taxonomy's A7 MISDIAGNOSE placebo arm was designed
to measure.

**Consequence.** The project cannot assume a positive content effect. The pilot gate
before the confirmatory experiment must require this contrast to be positive with
adequate precision; if it is not, the honest paper reports that a content-free retry
is not beaten by localization on this task family, which is a publishable negative
result and one the field needs.

## 2. Common random numbers buy 25%, not an order of magnitude

Using the same decoding seed for both arms at the same state, versus different seeds:

| contrast | variance |
|---|---|
| matched (shared seed) | 0.0869 |
| crossed (different seeds) | 0.1166 |

Ratio 0.746, i.e. a **25.4% variance reduction**, equivalent to 1.34× the sample size.
Worth taking, and free. But the branch-tree design claimed this as "the linchpin of
the proposed order-of-magnitude cut" to its cost. It is not: the true factor is 1.34×,
off by roughly an order of magnitude from the claim. **The branch-tree cost estimate
must be recomputed without that saving.**

## 3. The power arithmetic, with the measured variance

States needed to detect a given contrast at 80% power, using the measured matched
variance of 0.0869:

| contrast to detect | states needed |
|---|---|
| 0.03 | **757** |
| 0.05 | **273** |
| 0.10 | 68 |

The audited informative pool is **230 tasks**. So with one decision point per task the
design can detect a contrast of about 0.05 and no smaller — and only just. Anything
subtler requires more decision points per task, more replicates per state, or a
different estimand. This is the single hardest constraint the project faces, and it is
now measured rather than assumed.

## 4. Multi-turn calls are slower than first attempts — the cost model was optimistic

Earlier calibration (`docs/measured_calibration.md`) read 3.2 s per 3B call from a
sibling project's log, but those were mostly *first* attempts with short prompts. These
pilot calls carry real multi-turn context:

| receiver | effective s/call at 4 slots | sustained calls/hour | median prompt | median completion |
|---|---|---|---|---|
| Qwen2.5-3B (8193) | **3.96** | **909** | 276 tok | 176 tok |
| Qwen2.5-7B (8191) | **5.82** | **619** | 270 tok | 131 tok |

So **909 calls/hour is the planning figure for multi-turn 3B work**, not the 2,150
mixed figure. Every design cost in `work/design/` that used the higher figure is
optimistic by roughly 2.4×: a 12,600-call experiment is about 13.9 hours of contended
wall-clock, not 5.9.

## What these three together imply

The content effect may be zero, it can only be detected at about 0.05 or larger with
230 tasks, the variance trick that was supposed to make the branch tree cheap does not,
and every call costs 2.4× what the plan assumed. Taken with
`docs/premise_findings.md` (horizon dominates confounding) and `docs/audits.md`
(oracle stopping is worth +4.6 points while feedback content is held fixed), the
weight of evidence keeps pointing the same way: **the defensible experiment is about
when to intervene and when to stop, with the content contrast reported honestly
including the real possibility that it is null.**
