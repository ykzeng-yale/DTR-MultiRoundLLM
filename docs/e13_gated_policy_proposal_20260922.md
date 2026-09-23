# E13 proposal, revision 2: corrected after the lead's MRL-18 ruling (NOT RELEASED)

**Experiments workstream. Revision 2, 23 September 2026, under MRL-18 (lead commit `be417b5`).** Revision 1
(`4817a02`) and the original (`34fb797`) stand as dated history in git; this revision corrects their target,
power and interpretation statements as the ruling requires. Nothing here is released and nothing was executed.
Numbers come from `scripts/e13_sizing.py` → `results/e13_sizing_20260922.json`, which reads only committed E12
and frame files.

**What revision 2 withdraws or corrects:**

| Earlier statement | Correction |
|---|---|
| E13a would test whether R1's repairs are diagnostic-driven or resampling | It compares a **diagnostic-plus-R1-instruction restart package against bare task resampling** at five fixed checkpoints. A tie is **inconclusive** and does not show a resampling mechanism; the two arms differ in two ways at once. |
| E13b precision was reported as power | Those were powers against a **zero null on the gated subset**, not against the retained **five-point full-policy** useful-gain null. The corrected arithmetic is below. |
| "70 starts, ledger 403 of 412; no new start budget" | **403 is accounting, not authority.** E12 disallows spending its unused starts on another study, and its attestation and shared-host window have expired. E13a needs a separately enumerated allowance, a renewed attestation and a new window. |
| Gate rate given with a Wilson 95% interval | The roster is **not a probability sample**, so that coverage is unsupported. 36%, and the 124-retained / 44-gated figures, are **scenarios**, not estimates with coverage. |
| τ² = 0.025 "between-root variance" | A **noisy moment estimate from five roots**, not an identified variance decomposition. |
| MBPP frame is "about 18× too small for validation" | The 3,506-family figure belongs to **one conservative Hoeffding procedure**, not a universal minimum for validation. |
| Fisher examples distinguishing per-root counts | They do **not** make an individual root reliable, and multiple comparisons across five roots are not accounted for. |

## Motivation, restated with its limits

On E12's 14 roots, the rule *"if the initial answer fails any public example, issue R1 (task plus
diagnostic, previous answer removed); otherwise STOP"* scored **0.750 against STOP's 0.714**.

**That is +1/28 = +0.036 on the full-policy target, already below the 0.05 useful-benefit bar it would be
proposed to test.** Clearing 0.05 overall needs +0.14 per gated root, 1.4× this selected estimate. The
motivation and the success criterion are therefore arithmetically incompatible, which revisions 0 and 1 never
said.

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

| design | gated roots | R | 95% half-width, rule − STOP per gated root | power at +0.10 **per gated root, vs a zero null** | power at +0.05 **per gated root, vs a zero null** |
|---|---:|---:|---:|---:|---:|
| v1: G = 30, R1 on every root | ≈ 11 | 2 | 0.23 – 0.34 | 0.09 – 0.14 | 0.06 – 0.07 |
| whole remaining MBPP frame | ≈ 44 | 2 | 0.11 – 0.17 | 0.21 – 0.40 | 0.09 – 0.14 |
| whole remaining MBPP frame | ≈ 44 | 8 | 0.07 – 0.14 | 0.28 – 0.80 | 0.11 – 0.29 |

Ranges span τ² from 0.20 to 0.025, using the normal approximation (optimistic at small n). **These are
gated-subset powers against a zero null, not usefulness powers**; +0.05 per gated root is only +0.018 overall.

**τ² correction.** The 0.025 moment estimate subtracts an observed within-root term of 0.15 per root mean,
which implies 0.30 per replicate — more than the 0.25 Bernoulli maximum the SD then adds back. So (τ² = 0.025,
σ²_w = 0.25) is not moment-consistent; capping the within term gives **τ² = 0.05** as the optimistic end. At
τ² = 0.05 with R = 8, the inert-rule futility requirement rises from 64 to **92 roots**, the overall gain the
full frame can declare futile falls from 0.014 to **0.007**, and the conditional effect needed to demonstrate
usefulness rises from 0.28 to **0.30**. Either way the conclusion is unchanged. τ² remains a noisy five-root
moment estimate, not an identified decomposition.

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

### E13a: restart package versus bare resampling (source preparation released as MRL-18)

**Scientific statement, as the lead framed it:** a descriptive comparison of the
**diagnostic-plus-R1-instruction restart package** against **bare task resampling** at the **five fixed,
development-selected E12 public-fail checkpoints**, six new continuations per arm. It is post-hoc-motivated
development follow-up with fresh seeds. It is **not** a test of the selected gated rule and **not** a
diagnostic-only effect.

- **Arms.**
  - **R1:** `[public task prompt, public diagnostic message, R1 instruction]`, previous answer removed.
  - **FRESH:** the public task prompt alone, re-sampled.
  - The two therefore differ in **two ways at once** — the diagnostic bytes and the instruction — so neither
    arm isolates the diagnostic's own contribution.
- **A tie is inconclusive.** It would not show that E12's repairs came from resampling, and a difference would
  not attribute them to the diagnostic. Identifying the source needs a design that varies one component at a
  time, which this is not.
- **Checkpoints.** The five roots are fixed by E12's **frozen public diagnostics** (`public_status` = `any_fail`:
  842, 288, 863, 966, 652), conditioning on E12's immutable initial artifacts and diagnostic bytes. No new
  Phase A or B. **No private grade enters any executable input**; the plan records only public case statuses.
- **Replicates.** R = 6 per arm.
  - R1 uses replicate indices 2–7, so its `arm:replicate` seeds never repeat E12's replicates 0–1.
  - FRESH uses its own arm tag.
  - Inclusion probability is 1 for every root-arm-replicate; order is root-balanced scheduling only.
  - Nothing is pooled with E12; E12's values are only shown alongside.
- **Endpoint.** The frozen private-suite-plus-format score, unchanged. No private assertion changes. A
  final-public-compliance supplement would be separately labelled with its own extra cost, and is not a
  retrospective replacement for E12's endpoint.
- **Cost, as accounting only.** 60 receiver attempts; at most 30,720 reserved completion tokens; 60 artifact
  grading starts plus 10 control/recheck starts. Collection is estimated at about 2 minutes from E12's
  measured 314.258 s over 154 calls. **This is not authority:** a separately enumerated allowance, a renewed
  runtime attestation and a newly agreed shared-host window are all required first
  (`docs/e13a_execution_contract_20260923.md`).
- **Exact requests prepared, not run:** `results/e13a_request_plan_20260922.json` from
  `scripts/build_e13a_request_plan.py`.
  - It re-verifies E12's A bytes, diagnostics and calls against their checksums.
  - Each R1 prompt is **byte-identical** to both of E12's recorded R1 requests, and each FRESH prompt to
    E12's recorded initial request; only the seed differs.
  - All 60 new seeds differ from every seed E12 used at that root.
- **Formatting instructions are out of scope.** The original public prompt already required one block or raw
  source and no prose. Strengthening or repeating that requirement would be a **new intervention**, not a
  restoration, so no formatting instruction changes in this comparison. Any such change belongs to a separate,
  separately labelled study.
- **Frozen before dispatch** (in the stage descriptor and the execution contract): root-balanced scheduling,
  inclusion probability 1 per root-arm-replicate, model and evaluator versions, every source and input hash,
  the missing-outcome and format rules, the exact A–E commands and the immutable output paths.
- **What it can show:** per-root and equally weighted finite-checkpoint descriptive contrasts over five fixed
  checkpoints, with all assigned failures and actual usage reported.
- **What it cannot show:** it is not a test of the rule (these checkpoints selected it); it gives no
  population interval; no significance, equivalence or futility claim follows from six draws; and per-root
  count comparisons do not make an individual root reliable.
- **Why it is the smaller step:** bare resampling is a serious comparator here — the corrected
  [G0e recheck](experiment_recheck_20260920.md) still finds resampling "a strong comparator, especially for the
  3B receiver" on sibling logs with a different task contract — so a restart package that cannot beat it at
  these checkpoints is weak evidence for pursuing the larger design. That is a reason to measure, not a
  prediction.

### E13b:### E13b: HELD by the lead, and the corrected arithmetic agrees

**E13b is not released, and I am not pursuing it:** no 178-record source review and no 828 calls. My revision-1
power numbers tested the wrong null, and correcting them removes the case for running it on this frame.

**The decision quantity is the full-policy contrast, not the gated subset.** With STOP behaviour identical
outside the gate, the overall gain is the gate frequency times the conditional gain, θ = f·Δ. The per-root
policy contrast is D = g·(Y − S), so

`Var(D) = f(τ² + σ²_w/R + Δ²) − (fΔ)²`, equivalently `f(τ² + σ²_w/R) + f(1 − f)Δ²`
(independently re-derived in this bundle; the two forms agree algebraically)

and under the lead's rule — useful benefit needs the 95% lower limit L > 0.05, futility needs U < 0.05,
equality passes neither — power to declare benefit is `Φ((θ − 0.05)/SE − 1.96)`.

| conditional gain Δ per gated root | overall θ at f = 5/14 | roots for 80% power to declare **benefit** | roots for 80% power to declare **futility** |
|---|---|---|---|
| 0 (inert rule) | 0 | not applicable | **64 – 260** (92 – 260 at moment-consistent τ² ≥ 0.05) |
| 0.05 | 0.018 | impossible: θ < 0.05 | 157 – 632 |
| **0.10 (E12's selected estimate)** | **0.036** | **impossible: θ < 0.05** | 861 – 3,265 |
| 0.14 | 0.050 | equality passes neither rule | equality passes neither rule |
| 0.20 | 0.071 | 501 – 1,569 | not applicable |
| 0.30 | 0.107 | 98 – 249 | not applicable |

Ranges span τ² from 0.025 to 0.20 at R = 8; σ²_w is held at the Bernoulli maximum 0.25. Roots are treated as
independent, which the unresolved family structure does not establish.

- **E12's own point estimate cannot reach the threshold.** A selected +0.10 per gated root is +0.036 overall.
  No sample size makes L > 0.05 when θ < 0.05, so the rule as observed is not a candidate for useful benefit.
- **Reaching the bar needs +0.14 per gated root; demonstrating it on the ~124 remaining roots needs about
  +0.28**, roughly three times E12's selected estimate.
- **The one reachable decisive outcome is futility.** If the rule is inert, 64 roots suffice at τ² = 0.025 and
  R = 8; the whole remaining frame covers true overall gains only up to about 0.014 (and at τ² ≥ 0.1 it cannot
  reach 80% futility power even against an inert rule).
- **Therefore this frame can, at best, rule the rule out — never establish it.** Any future stage of this kind
  should be declared as a futility-oriented design with that stated in advance, or moved to a different task
  source. That is a planning statement, not a result, and it is subject to the lead's remark that the
  3,506-family Hoeffding figure is one conservative procedure rather than a universal minimum.

## Decision requested from the lead (revision 2)

Both revision-1 decisions are now answered by MRL-18, so what remains is narrower:

1. **E13a source preparation is running under MRL-18** and is delivered with this revision. Execution stays
   held pending a separately enumerated start/token/time allowance, a renewed runtime attestation and an agreed
   shared-host window; the contract proposal is `docs/e13a_execution_contract_20260923.md`.
2. **E13b is closed as proposed.** If a prospective stage of this type is ever wanted, it should be declared a
   futility-oriented design, or use a task source larger than this frame.

Null or negative results remain reportable, and nothing is tuned on outcomes.
