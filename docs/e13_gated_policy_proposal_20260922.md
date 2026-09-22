# E13 proposal, revision 1: public-diagnostic-gated R1 (NOT RELEASED)

**Experiments workstream, 22 September 2026.** This revision replaces the sizing and comparators of the first
version (`34fb797`), which I checked against the lead's
[validation-design memo](independent_prompt_policy_validation_design_20260922.md) and against E12's own
variance. **The first version's G = 30 design could not have detected the effect it was motivated by**
(details below), so it is withdrawn. Nothing here is released, and nothing was executed: the numbers come
from `scripts/e13_sizing.py` → `results/e13_sizing_20260922.json` (sha `83d0f357…`), which reads only committed
E12 and MRL-15 files.

## Motivation, restated with its limits

On E12's 14 roots, the rule *"if the initial answer fails any public example, issue R1 (task plus
diagnostic, previous answer removed); otherwise STOP"* scored **0.750 against STOP's 0.714**.

- **It was chosen after seeing E12.** It was the best of the gate-then-arm rules on the same 5 public-fail
  roots, so +0.10 per gated root is an optimistic planning value and cannot be treated as evidence.
- **Per gated root, R1 − STOP** was −0.5 (863), +0.5 (842), +0.5 (288), 0 (966) and 0 (652).
  - Of the 0.175 variance across roots, **0.15 is replicate noise** from R = 2.
  - That leaves a moment estimate of between-root variance τ² = 0.025. With 5 roots, τ² is essentially
    unknown, so the scenarios use τ² ∈ {0.025, 0.10, 0.20}.
- **The rule stops selectively.** Under the lead's memo, its comparison is therefore a
  *prompting-and-stopping policy* comparison, not a prompt-choice comparison. R1 also changes the context
  package (the previous answer is removed), not only the wording.

## Why the first version was uninformative

The policy contrast is zero wherever the gate does not fire. All information comes from gated roots, about
36% of roots (Wilson 95% range 16–61%).

| design | gated roots | R | 95% half-width, rule − STOP per gated root | power at +0.10 | power at +0.05 |
|---|---:|---:|---:|---:|---:|
| v1: G = 30, R1 on every root | ≈ 11 | 2 | 0.23 – 0.34 | 0.09 – 0.14 | 0.06 – 0.07 |
| whole remaining MBPP frame | ≈ 44 | 2 | 0.11 – 0.17 | 0.21 – 0.40 | 0.09 – 0.14 |
| whole remaining MBPP frame | ≈ 44 | 8 | 0.07 – 0.14 | 0.28 – 0.80 | 0.11 – 0.29 |

Ranges span τ² from 0.20 to 0.025, using the normal approximation (optimistic at small n).

- **The frame is the binding limit.**
  - The MRL-15 frame has 198 eligible records. 20 have been reviewed, leaving **178 unreviewed**.
  - At E12's 14-of-20 retention, that is about **124 retained roots**, of which about **44 are gated**
    (20–76 across the Wilson range).
  - With R = 8, reaching 80% power at +0.10 needs 45–182 gated roots, depending on τ², and 177–727 at +0.05.
- **Hoeffding radius.** The memo's conservative two-contrast Hoeffding radius at 44 gated roots is
  **0.45**. Its validation target (**3,506 independent families** for radius 0.05) is about **18× the size
  of the entire eligible MBPP frame**. Confirmatory validation of any public-history rule therefore needs a
  task source beyond this frame; more replicates per root do not raise the number of families.

## Revised plan: two stages, each needing a separate release

### E13a: mechanism and variance pilot (cheap; fits the current ledger)

The question E12 cannot answer: **do R1's repairs come from the diagnostic, or simply from drawing a fresh
answer without the old one in context?**

- **FRESH arm:** the original public prompt alone (`base` messages), re-sampled. It is the memo's
  independent-sampling comparator b2 in its simplest form: same gate, one call, no diagnostic.
- **R1 − FRESH** isolates the diagnostic observations plus the R1 instruction, holding "previous answer
  removed" fixed.
- **Roots and checkpoints:** E12's 5 public-fail roots, conditioning on E12's immutable initial artifacts
  and diagnostic bytes. No new Phase A or B. The 42 v3 validation starts transfer only if their bindings are
  unchanged and unexpired, as in MRL-16.
- **Replicates:** R = 6 each of R1 and FRESH.
  - R1 uses replicate indices 2–7, so its `arm:replicate` seeds do not repeat E12's replicates 0–1.
  - FRESH uses a new arm tag.
  - Nothing is pooled with E12; E12's values are shown alongside.
- **Cost:**
  - 60 receiver calls; 30,720 reserved completion tokens; about 2 minutes of collection at E12's measured
    2.04 s per call.
  - 60 private grades plus 10 rechecks = **70 starts, ledger 403 of 412**; no new start budget.
  - It still needs a shared-host window and the full v3.1 receiver checks.
- **What it can show:** descriptive per-root R1 vs FRESH repair counts out of 6, and better within-root
  variance for E13b. Only large per-root gaps are informative: 3/6 against 0/6 on one root is not by itself a
  reliable difference (Fisher two-sided p ≈ 0.18); 5/6 against 0/6 is (p ≈ 0.015).
- **What it cannot show:**
  - it is not a test of the rule (these roots selected it);
  - it gives no population interval (one unresolved family, 5 roots);
  - its τ² is still from 5 roots.
- **Why it comes first:**
  - If FRESH repairs as often as R1, the E12 signal is resampling, not diagnostic-directed prompting. E13b
    should then test the cheaper resample rule, or not run.
  - If R1 clearly beats FRESH, E13b's R1 − FRESH contrast has a concrete prior.

### E13b: prospective test of the frozen rule on the rest of the frame (conditional on E13a)

- **Policy d**, frozen before any new outcome: *public fail → R1, else STOP*.
- **The memo's two contrasts:**
  - d − STOP: the development-selected fixed option, tied with N0 and N1 on E12 and the cheapest;
  - d − b2, where b2 is *public fail → FRESH, else STOP*.
- **Claim label:** prompting-and-stopping, development scale.
- **Roots:** frame ranks 21–198 in their seeded order, with no outcome use.
  - They need the same independent source contract review and wrong-control validation as E12, with no
    backfill.
  - The E11/E12 roots and their inspected variants are excluded, as the memo requires.
- **Two-stage execution:**
  - Phase A and B on every retained root.
  - R1 and FRESH (R = 8 each; final R set from E13a) **only on gated roots**. This is legitimate because the
    gate uses only decision-time public information; the estimand is conditional on it and is reported with
    the gate rate.
  - The first version's audit of R1 on public-pass roots is dropped. E12 already showed R1 lowers
    public-pass roots from 1.0 to 0.889, and the policy never takes that action.
- **Cost:**
  - about 828 calls, 423,936 reserved completion tokens, about 28 minutes of collection;
  - about 1,572 starts, which needs a new start budget, and the A+C cap raised from 1,200 s to about 1,800 s;
  - the dominant cost is source review of about 178 records (E12's review of 20 found 6 holds and one domain
    amendment).
- **Expected precision** (R = 8, about 44 gated roots):
  - 95% half-width about 0.07–0.14 on the gated-root rule − STOP contrast;
  - about 0.09–0.15 on R1 − FRESH, which has twice the replicate noise.
  - This can rule out large effects but is **not powered for +0.05**, and gives no population or validation
    claim.

## Decision requested from the lead

1. Release, amend or decline **E13a**: 60 calls, 70 starts, within the 412 ledger.
2. Say whether **E13b** is worth about 178 source reviews given the precision above. Alternatively, reserve
   the remaining MBPP frame for a later design and move validation to a larger task source, since the
   memo's 3,506-family target cannot be met on MBPP.

Null or negative results remain reportable, and nothing is tuned on outcomes.
