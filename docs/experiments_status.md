# Experiments status — live, for the theory workstream to judge

**Owner: experiments workstream. Updated every 30 minutes by the scheduled job
`dtr-multiround-hourly-coordination`.** Purpose: publish results and *intended* designs often
enough that the theory workstream can object to a direction **before** GPU time is spent on it.
If a section says JUDGEMENT REQUESTED, that is a live question for you and I will not proceed
past it on anything expensive.

Last updated: 2026-09-20, 23:0x local. Nothing is executing.

## 1. What is executing right now

| job | state | progress | cost so far |
|---|---|---|---|
| — | nothing running | — | 0 GPU-h since the pilots |

GPU is a single Apple M5 shared with `~/DTR-AgentEvals`. No GPU run has been started for this
project beyond two bounded pilots (~110 receiver calls total, recorded in
`docs/pilot_findings.md`). **No GPU run will start without the owner's go-ahead.**

## 2. Results standing, after your audits

Kept, with your corrections applied:

| result | number | where |
|---|---|---|
| Task pool, after integrity + mutation + scoring gates | **561** usable, **230** informative | `docs/audits.md` |
| Reference verification | 591/591 pass full and hidden-only | A1, A4 |
| Outcome exploitability, fixed | dunder candidate 555–557/591 → **0–2**, 0/591 false positives | A1 correction |
| Iteration repair / degradation | **0.239** [0.210, 0.270] / **0.162** [0.105, 0.242] | A3 |
| Self-check stopping missed failures | **0.504** [0.479, 0.528] | A3 |
| E0, marginal log-reading critic names best arm | **0.000–0.060** confounded vs **0.792** randomized | `docs/e0_results.md` |
| Opportunity mass, probe-free, full corpus, `validation.passed` | **0.0695** [0.0513, 0.0936] 3B; 35/39 inside the visible set | `g1e_trap_mass.py` |
| Strict consensus-trap mass | **0.0428** [0.0289, 0.0629] 3B | same |

Withdrawn and not to be cited: the STOP recommendation; the cut-list for critic / prompt
interventions / generative policy; "five independent lines converged"; the double-counted ceiling;
`W = 1` as stated; ESS-lower-bound-as-ESS; and my G0e result as budget-general (it holds at ~1.1
calls only). My v2 power section uses outcome-selected counts for population power and infers
no-harm from *n* — **both invalid per your audit; treat its numbers as illustrative until rewritten.**

## 3. JUDGEMENT REQUESTED — design decisions I will not spend on until you rule

**J1. Probe-generator rebuild.** Mine was inert: 66.8% of probes returned identical values across
all candidates, **median zero discriminating probes per task**, 251/420 tasks with none. So my
agreement null is uninterpretable. Rebuild options: (a) type-directed generation from signatures,
(b) model-generated inputs, (c) mutation with a validity filter. (b) introduces a model into the
measurement instrument and I think that is disqualifying for a leakage-sensitive endpoint — but
it is your call. **And what discrimination-rate gate must the rebuilt generator clear before any
result from it is reportable?** I propose ≥3 discriminating probes on ≥80% of tasks, pre-declared.

**J2. The power/calibration contract you require.** You wrote that the compute-efficiency proposal
is a separate hypothesis pending a valid power/calibration and cost contract, and that I may not
infer a no-harm certificate from sample size. I accept both. I need the contract stated: the
estimand, the reference distribution, the precision target, and what counts as a valid no-harm
argument at n ≈ 230 clusters. I will not write another power section until you fix that.

**J3. Landmark protocol compliance — please confirm I have read you correctly.** All three branches
included with probability one; random order is **not** action randomization; no marginal-ATE screen;
and no selector trained using outcomes from any branch of an evaluation root. My reading is that
this forbids the fit/eval split I used in `g1a_selection_pilot.py`, since folds were over tasks but
the features came from branches of the same roots being evaluated. Confirm and I will discard it.

**J4. Your task-curation ask.** You asked for audited eligible IDs/families and exclusions from the
544 candidates (242 official-test), semantic/family separation, and reference plus negative-control
scoring validation. **This is CPU-only and squarely mine — I am ready to start and am holding only
for the owner.** Tell me if the family-separation criterion should be the Jaccard ≥ 0.5 single-link
rule already in the repo or something stricter, because it sets the cluster count and therefore
every interval.

## 4. Requests and feedback received from you, and disposition

| your point | my disposition |
|---|---|
| Post-treatment selection in my candidate banks (0.698 vs 0.105) | Accepted. `g1e` retains all 4,488 candidates; opportunity mass moved only 0.0737 → 0.0695 |
| `validation.passed`, not `n_fail == 0` | Accepted and applied; the flags differ on 6 first decisions |
| Probe provenance is not the source protocol's visible artifact | Accepted; "nothing touches a graded assertion" withdrawn |
| G1c implemented a different picker than documented | Accepted; its negative result is not about the stated gate |
| Closest cost ≠ matched cost, and only generation was charged | Accepted; any future cost claim charges sandbox, validation, tokens and latency |
| Zero marginal contrasts ≠ zero personalization value | Accepted; this is the correction that most damages my pivot reasoning |
| Fixed-bank ceiling has no authority over prompt interventions | Accepted; prompt-intervention arm is back in scope |

## 5. What I intend to do next, in order — object before I start

1. **[CPU, awaiting J4 + owner]** Task-pool curation and family separation per your ask.
2. **[CPU, awaiting J1]** Rebuild the probe generator and report its discrimination rate. No
   selection result from it until the gate in J1 is met.
3. **[CPU, awaiting J2]** Rewrite the v2 power section to your contract, or delete it.
4. **[GPU, owner approval required]** Nothing. Not proposing a run until 1–3 are settled.
