# E13 proposal, revision 3: sizing and interpretation repairs (execution NOT RELEASED)

**Revision 3, 23 September 2026, lead-owned mathematical repair under MRL-18.** The original (`34fb797`),
revision 1 (`4817a02`) and revision 2 (`b5bbaf1`) remain dated history in git. This revision corrects sizing
inversions and removes unsupported interpretation claims. E13a source preparation was released under MRL-18;
E13a model/benchmark execution and E13b collection are not released by this document. Only scalar planning
arithmetic and source tests are run for this repair.
Numbers come from `scripts/e13_sizing.py` → `results/e13_sizing_20260922.json`, which reads only committed E12
and frame files.

**What revisions 2–3 withdraw or correct:**

| Earlier statement | Correction |
|---|---|
| E13a would test whether R1's repairs are diagnostic-driven or resampling | It compares a **diagnostic-plus-R1-instruction restart package against bare task resampling** at five fixed checkpoints. A tie is **inconclusive** and does not show a resampling mechanism; the two arms differ in two ways at once. |
| E13b precision was reported as power | Those were powers against a **zero null on the gated subset**, not against the retained **five-point full-policy** useful-gain null. The corrected arithmetic is below. |
| "70 starts, ledger 403 of 412; no new start budget" | **403 is accounting, not authority.** E12 disallows spending its unused starts on another study, and its attestation and shared-host window have expired. E13a needs a separately enumerated allowance, a renewed attestation and a new window. |
| Gate rate given with a Wilson 95% interval | The roster is **not a probability sample**, so that coverage is unsupported. 36%, and the 124-retained / 44-gated figures, are **scenarios**, not estimates with coverage. |
| τ² = 0.025 "between-root variance" | A **noisy moment estimate from five roots**, not an identified variance decomposition. |
| τ² = 0.05 is required for "moment consistency" | The Bernoulli population variance bound does not bound a two-replicate sample variance by 0.25. Both 0.025 and 0.05 are sensitivity choices; neither is a demonstrated lower bound. |
| No sample size can produce useful benefit below the threshold | No sample size attains **80% benefit power** at a true effect at or below the threshold in the stated normal model. A false-positive declaration remains possible. |
| 50% power obtained by setting the normal multiplier to zero | The correct multiplier is **1.96**; a zero multiplier gives a true effect at the threshold, where declaration probability is 2.5%. |
| MBPP frame is "about 18× too small for validation" | The 3,506-family figure belongs to **one conservative Hoeffding procedure**, not a universal minimum for validation. |
| Fisher examples distinguishing per-root counts | They do **not** make an individual root reliable, and multiple comparisons across five roots are not accounted for. |

## Motivation, restated with its limits

On E12's 14 roots, the rule *"if the initial answer fails any public example, issue R1 (task plus
diagnostic, previous answer removed); otherwise STOP"* scored **0.750 against STOP's 0.714**.

**That is +1/28 = +0.036 on the full-policy target, below the 0.05 useful-benefit bar.** At the planning gate
frequency 5/14, a true overall gain strictly above 0.05 requires a conditional gain strictly above 0.14.
Thus the selected pilot point estimate is below the useful planning alternative; it does not establish the
true effect or prove that a future policy cannot meet the bar.

- **It was chosen after seeing E12.** It was the best of the gate-then-arm rules on the same 5 public-fail
  roots, so +0.10 per gated root is subject to selection optimism and is not independent policy validation.
- **Per gated root, R1 − STOP** was −0.5 (863), +0.5 (842), +0.5 (288), 0 (966) and 0 (652).
  - The sample variance of root means is 0.175; the mean within-root sample variance divided by R = 2 is
    0.15. Their difference, 0.025, is a noisy moment calculation, not an identified noise decomposition.
  - The scenarios use τ² ∈ {0.025, 0.05, 0.10, 0.20}; the five selected roots do not determine the future
    population heterogeneity or establish a lower bound on it.
- **The rule stops selectively.** Under the lead's memo, its comparison is therefore a
  *prompting-and-stopping policy* comparison, not a prompt-choice comparison. R1 also changes the context
  package (the previous answer is removed), not only the wording.

## What the first version's sizing does and does not address

The policy-minus-STOP contrast is zero wherever the gate does not fire. Its full-population mean and variance
still depend on the gate frequency. The observed 5/14 frequency is used as a scenario only: the development
roster and unresolved family structure do not justify a population Wilson interval.

| design | gated roots | R | 95% half-width, rule − STOP per gated root | power at +0.10 **per gated root, vs a zero null** | power at +0.05 **per gated root, vs a zero null** |
|---|---:|---:|---:|---:|---:|
| v1: G = 30, R1 on every root | ≈ 11 | 2 | 0.23 – 0.34 | 0.09 – 0.14 | 0.06 – 0.07 |
| whole remaining MBPP frame | ≈ 44 | 2 | 0.11 – 0.17 | 0.21 – 0.40 | 0.09 – 0.14 |
| whole remaining MBPP frame | ≈ 44 | 8 | 0.07 – 0.14 | 0.28 – 0.80 | 0.11 – 0.29 |

Ranges span τ² from 0.20 to 0.025, using an assumed-variance normal approximation with no small-sample
calibration. **These are gated-subset powers against a zero null, not usefulness powers**; +0.05 per gated
root is only +0.018 overall. Adding the 0.05 sensitivity value does not change these ranges.

**τ² scenarios.** An unbiased sample variance from two Bernoulli draws can be 0.5 (observations 0 and 1),
although the population variance is at most 0.25. The observed average sample variance 0.30 therefore does
not violate that population bound or require replacing τ² = 0.025 by 0.05. At the optional τ² = 0.05 scenario
with R = 8, the inert-rule 80% futility requirement is **92 roots**, the largest nonnegative overall gain
with 80% futility power at n = 124 is about **0.007**, and the conditional effect for 80% benefit power is
about **0.30**. These are sensitivity calculations, not estimates of a validated variance model.

- **Frame-count scenarios, not a verified independent sample.**
  - The MRL-15 frame has 198 eligible records. 20 have been reviewed, leaving **178 unreviewed**.
  - Applying E12's 14-of-20 retention and 5-of-14 gate frequency gives **124 retained / 44 gated roots** as
    arithmetic scenarios, not probabilistic projections or confidence limits.
  - With R = 8, the old zero-null calculation at +0.10 needs 45–182 gated roots, depending on τ², and
    177–727 at +0.05; these do not size the full-policy useful-gain test.
- **Hoeffding radius.** The memo's conservative two-contrast Hoeffding radius at 44 gated roots is
  **0.45**, if those units were independent equal-weight families. **3,506 independent families** would
  guarantee radius at most 0.05 under that procedure, larger than the 198-record frame. This is a precision
  guarantee for one conservative procedure, not a power calculation or universal lower sample-size limit.
  The actual independent-family count is unverified; more within-root replicates do not create families.

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
  Phase A or B. **No private grade enters checkpoint selection or receiver-dispatch inputs**; the plan records
  only public case statuses. The final analysis necessarily consumes private grades.
- **Replicates.** R = 6 per arm.
  - R1 uses replicate indices 2–7, so its `arm:replicate` seeds never repeat E12's replicates 0–1.
  - FRESH uses its own arm tag.
  - Inclusion probability is 1 for every root-arm-replicate; order is root-balanced scheduling only.
  - Nothing is pooled with E12; E12's values are only shown alongside.
- **Endpoint.** The frozen private-suite-plus-format score, unchanged. No private assertion changes. A
  final-public-compliance supplement would be separately labelled with its own extra cost, and is not a
  retrospective replacement for E12's endpoint.
- **Cost, as accounting only.** 60 receiver attempts; at most 30,720 reserved completion tokens; 60 artifact
  grading starts plus 10 control/recheck starts. This 70-start grading subtotal excludes the nine containment
  starts in the revised prospective contract, whose total proposed cap is 79. Collection is estimated at about 2 minutes from E12's
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
- **Required to be frozen before dispatch** (in the stage descriptor and the execution contract): root-balanced scheduling,
  inclusion probability 1 per root-arm-replicate, model and evaluator versions, every source and input hash,
  the missing-outcome and format rules, exact real collection/grading/analysis commands and immutable output
  paths. Completing and validating that real two-arm execution path is the pending MRL-19 source assignment.
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

### E13b: HELD as proposed; these scenarios do not constitute a release

**E13b is not released:** no 178-record source review and no 828 calls. Revision 1 tested the wrong null.
The corrected scenarios do not establish an independent evaluation frame, adequately calibrated inference,
or sizing for the required fixed-continuation comparison. They also do not prove that this frame could never
detect useful benefit under a different true effect or justified procedure.

**The decision quantity is the full-policy contrast, not the gated subset.** With STOP behaviour identical
outside the gate, the overall gain is the gate frequency times the conditional gain, θ = f·Δ. The per-root
policy contrast is D = g·(Ȳ − S), where Ȳ averages R fresh continuations at a frozen initial artifact, so

`Var(D) = f(τ² + σ²_w/R + Δ²) − (fΔ)²`, equivalently `f(τ² + σ²_w/R) + f(1 − f)Δ²`
(the two forms agree algebraically). Here τ² is the variance of the conditional mean contrast among gated
roots, and σ²_w is the average conditional branch variance. The identity uses independent continuation seeds
conditional on the full frozen root; the standard error additionally assumes independent roots. Using 0.25
for σ²_w is an upper-bound planning plug-in, not proof that every scenario's moment triple defines an exact
Bernoulli data-generating law.

Under the lead's rule, useful benefit needs the 95% lower limit L > 0.05 and useful-gain futility needs
U < 0.05. An **interval endpoint** equal to 0.05 does not meet its strict rule. Normal-approximation benefit
power is `Φ((θ − 0.05)/SE − 1.96)`; futility power is `Φ((0.05 − θ)/SE − 1.96)`. If the **true effect** equals
0.05, each declaration has probability 0.025. These are one-contrast, one-final-analysis approximations,
not simultaneous two-contrast power or finite-sample guarantees.

| conditional gain Δ per gated root | overall θ at f = 5/14 | roots for 80% power to declare **benefit** | roots for 80% power to declare **futility** |
|---|---|---|---|
| 0 (inert rule) | 0 | 80% unattainable in this model | **64 – 260** (92 at τ² = 0.05) |
| 0.05 | 0.018 | 80% unattainable in this model | 157 – 632 |
| **0.10 (E12's selected estimate)** | **0.036** | **80% unattainable in this model** | 861 – 3,265 |
| 0.14 | 0.050 | 2.5% declaration probability, not 80% | 2.5% declaration probability, not 80% |
| 0.20 | 0.071 | 501 – 1,569 | 80% unattainable in this model |
| 0.30 | 0.107 | 98 – 249 | 80% unattainable in this model |

Ranges span τ² from 0.025 to 0.20 at R = 8; σ²_w is held at the Bernoulli maximum 0.25. Roots are treated as
independent, which the unresolved family structure does not establish.

- **The selected point estimate is below the useful-gain planning target.** At θ = 0.036, no sample size
  attains 80% benefit power in this model; false-positive declarations remain possible. The selected estimate
  does not identify the true future effect.
- **At the hypothetical n = 124, 80% benefit power needs about +0.28 per gated root** at τ² = 0.025,
  or about +0.30 at τ² = 0.05, R = 8. For 50% power the inversion uses 1.96; for 80% it uses 1.96 + 0.842.
- **Futility is also scenario-dependent.** At n = 124 and R = 8, τ² = 0.025 supports 80% futility power
  for nonnegative overall gains up to about 0.014; τ² = 0.05 reduces this to about 0.007. At τ² = 0.10 or
  0.20, even a zero gain does not attain 80% futility power. The machine-readable boundary is therefore
  `null` in these cases, not zero. Conversely, a sufficiently large true benefit can attain 80% benefit
  power within n = 124: Δ = 0.30 needs 98 roots in the τ² = 0.025 scenario. There is no universal
  "futility only" conclusion.
- **Scope limit of this arithmetic (correction to revisions 0–1, which did not state it).** Every number above
  is for the gated rule **minus always-STOP**, and depends on the contrast being exactly zero at non-gated
  roots, which holds only because the rule stops there. The validation memo's primary comparator `b1` is a
  fixed **continuation** recipe. For that contrast, with conditional means μ_g, μ_ng and variances v_g, v_ng,
  the variance is `f·v_g + (1 − f)·v_ng + f(1 − f)(μ_g − μ_ng)²`. The gated contrast and the overall mean
  also change, so neither variance nor required sample size is ordered relative to the STOP comparison.
  E12 does not settle those population quantities: N1 scored 1.000 on all nine non-gated roots, so the
  observed rule-minus-N1 contrasts there were
  all zero, while R1 itself lowers non-gated roots from 1.000 to 0.889. **Sizing against a fixed-continuation
  comparator is not done**, which is consistent with your note that replacing the fixed-continuation
  comparison changes the target rather than silently satisfying it.
- **A later validation design needs its actual comparison, frame and inference frozen.** Whether it can
  resolve useful benefit, futility or neither depends on those choices and explicit effect/variance scenarios.
  Neither this calculation nor the 3,506-family Hoeffding example establishes universal feasibility or
  impossibility for the MBPP frame.

## Current disposition (revision 3)

Both revision-1 decisions are now answered by MRL-18, so what remains is narrower:

1. **E13a source preparation is running under MRL-18** and is delivered with this revision. Execution stays
   held pending a separately enumerated start/token/time allowance, a renewed runtime attestation and an agreed
   shared-host window; the contract proposal is `docs/e13a_execution_contract_20260923.md`.
2. **E13b is held as proposed.** A later validation proposal must address the frozen fixed-continuation
   comparator, independent-family frame, measurement and calibrated inference before collection; this
   arithmetic alone does not require a futility-only design or prove that every valid design needs a larger frame.

Null or negative results remain reportable. E13a is explicitly motivated by observed E12 outcomes; no E13a
outcomes have been collected for this repair, and the follow-up rules must be frozen before its dispatch.
