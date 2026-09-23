# E14, corrected prospective proposal: source-fixed roster, fresh prefixes, one common terminal instruction

23 September 2026. Experiments workstream, MRL-22 deliverable 3 (the single corrected proposal
permitted by `docs/mrl21_review_mrl22_20260923.md`). Source-only document.

## Status: this proposes and releases nothing

- **Nothing here is released, authorized, scheduled or started.** No collection, no receiver start,
  no model call, no model token, no candidate/reference/public-check/containment/sandbox execution,
  no installation, no network use and no spend occurred while writing it, and none is authorized by it.
- **Execution requires a separate explicit lead release, a real host window and a renewed
  attestation** — release bindings, receiver preflight, a resource agreement and an independent
  design/measurement review, exactly as for E12 and E13a. Unused E13a or MRL-20/21/22 calls, starts
  or window time authorize nothing.
- **No model outcome was inspected for this document.** No grades file, analysis report, private
  execution record or hidden score of any reviewed frame record was opened. Candidate selection is
  not a function of expected receiver difficulty anywhere below.
- **The roster size is deliberately left open.** It is a function of MRL-22 deliverable 2's
  dispositions over frame ranks 21-40, which are being produced in parallel and are not available to
  this document. Section 7 states the formation rule; it asserts no count.
- **E13a remains a valid immutable negative result** (`results/e13a_two_arm_20260923T061500Z/`):
  R1 9/30 versus FRESH 12/30, equal-weight mean **-0.1000**, all 60 assigned grades present. Nothing
  here repairs, reinterprets or re-scores it.

Inputs read while writing this document (the only files opened; hashes recomputed here where stated):

| File | Status |
|---|---|
| `docs/mrl21_review_mrl22_20260923.md` | the five decisions answered below |
| `results/frame_review_mrl15_20260922T021718Z/manifest.json` | sha256 `4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc`, recomputed and matching; `eligible_ordered_ids` length **198** |
| `scripts/review_candidate_frame_mrl15.py` | criteria, seed rule `sha256("mrl15-frame-seed-20260922:<task_id>")`, `N_REVIEW = 20`, decision vocabulary include/hold/exclude |
| `scripts/e13_sizing.py` | committed planning arithmetic; only `precision(...)` was evaluated, with hypothetical inputs. `e12_gated()` was **not** called, because it reads E12 outcome files |
| `docs/e14_same_prefix_revision_proposal_20260923.md` | the declined proposal, read to identify exactly what is withdrawn and what survives |

The manifest records the MBPP source as `work/sources/mbpp_full.jsonl`, sha256
`ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`, 974 rows. Deliverable 2 verifies
those bytes; this document only cites the manifest's recorded values and does not restate them as
independently verified here.

---

## 0a. AMENDMENT, 2026-09-23 — the terminal-output contract is reworded; its fence clause is withdrawn

Validating `terminal-output-contract-v1` against the frozen instrument before any collection refuted one of its
clauses. Evidence: `scripts/e14_output_contract_validation.py` → `results/e14_output_contract_validation_20260923.json`
(6 tests, 0 executions, scorer unchanged).

**The fence clause is not enforceable and not observed.** `grade.extract_code` returns the whole text when no
triple-backtick fence is present, so an unfenced answer is extracted, parsed and scored exactly like a fenced
one; the instrument rejects only *ambiguous* fencing. Demanding a fence therefore asserts something the endpoint
cannot see. It is also counter-factual: of E13a's 60 saved outputs **1 was fenced**, and in the FRESH arm
**0 of 30** were — while **30 of 30** FRESH outputs satisfied every other clause (parseable, function-and-imports
only, no test calls or asserts, no diagnostic text). The contract as first written would have marked every one of
those clean outputs non-compliant on a clause the scorer ignores.

**Corrected contract, label `terminal-output-contract-v2`:**

> `Return the complete solution as Python source containing only the function definition and any imports it needs. Do not include test calls, example output, or any text copied from the diagnostic report. If you use a code fence, use exactly one.`

Every clause of v2 is decidable by the frozen instrument with no scorer change: "exactly one fence if any" is
precisely `extract_code`'s rule, and the rest are static AST checks. Enforcing a fence as a requirement would
need a scorer change, which is a different measurement and is not requested.

**This changes nothing about E13a.** The validation does not repair its −0.1000, does not recover latent semantic
success and identifies no formatting mechanism. The private-suite half of the validation — that a compliant
output still reaches the private suite and scores as before — needs a released containment run and is **not**
claimed here.

## 0. What is withdrawn

The nine-root roster of the declined proposal — mbpp/918, 825, 816, 895, 868, 154, 651, 499, 974 —
**is withdrawn, not relabelled.** It was exactly the public-pass complement of the five
outcome-inspected E13a checkpoints among E12's 14 retained roots. Because every root's public status
was `pass`, the directed arm's deterministic selector collapsed to the single preservation string
`S1_STRINGS[2]`, and the private endpoint was already at 9/9 on those roots. That roster is not
carried forward under any new name, is not re-proposed as a "repair study" or a "damage study", and
supplies no roots to the design below. The 108-call batch built on it is withdrawn with it.

What survives from the declined document is only the non-roster machinery: the two arm texts, the
common terminal-output contract, the public-only information timing, the all-assigned endpoint, the
seed/label law and the no-retry rule. Those are restated below where they are used, and each is
re-derived against the corrected design rather than inherited.

---

## 1. Decision 1 — "Selection changes the question"

**Accepted in full.** The corrected design is a **source-fixed development roster with fresh initial
prefixes**:

1. **The roster is fixed from source before any receiver call.** Membership is a deterministic
   function of (a) the preregistered frame order in the verified manifest, (b) the committed rank
   window 21-40, and (c) deliverable 2's source-only include/hold/exclude dispositions. No model
   output, no public score and no private score enters roster formation. The rule is written out in
   section 7 and must be frozen, published and hashed **before** the first call.
2. **Prefixes are fresh.** Every root's message-1 task prompt is rendered from source, and its
   message-2 previous answer is generated inside the released window by an initial receiver call at a
   recorded seed. No E11/E12/E13a prefix, previous answer or diagnostic is reused. The five
   outcome-inspected E13a checkpoints (mbpp/842, 288, 863, 966, 652), the E11 development roots and
   the E12 retained roots are all ineligible by construction, since the roster comes from ranks 21-40
   of the frame and those roots are not in that window.
3. **Every initial public-status category is retained.** After the initial answers exist, each root
   carries a public status in the same three-valued vocabulary E12 used for its crosstab —
   `pass`, `fail`, `unknown` (diagnostic unavailable or indeterminate). **All three are kept.** No
   root is dropped, re-drawn, swapped, re-ordered or down-weighted because of its public status, and
   none is dropped after private scoring. Public-only status may select the predeclared directed
   string; that is the intervention reading its permitted public input, not a selection step.
4. **No exclusion after seeing public or private scores.** The only admissible losses are
   (a) a receiver/harness failure, recorded as a missing outcome with its reason under section 4's
   frozen rule, and (b) the frozen wall-clock deadline. Both are score-independent. Any other removal
   invalidates the run.
5. **The target changes with the design, and that is stated, not hidden.** These are new development
   histories under a new intervention law. Results here do not correct, supersede or re-open E12's or
   E13a's valid negatives, which were measured at different histories.

---

## 2. Decision 2 — "Name the intervention correctly"

**Accepted.** E11 and E12 already compared N1 against S1 at identical full prefixes and identical
diagnostic bytes. The corrected proposal therefore claims exactly two incremental elements and nothing
more:

- **Increment 1: fresh initial prefixes under a source-fixed roster.** The histories are new,
  generated in-window, and the roster retaining them is fixed from source with every public-status
  category present. E11/E12 compared the same arms at prefixes drawn from rosters that had already
  been screened, and E13a's checkpoints were outcome-inspected. Fresh prefixes plus a source-fixed
  roster is the only design change that answers decision 1.
- **Increment 2: one common predeclared terminal instruction**, `terminal-output-contract-v1`,
  byte-identical in both arms and appended to message 4 after `"\n\n"`. A run whose two arms differ in
  those bytes is invalid.

What the increments explicitly do **not** deliver, stated so no later reading can inflate them:

- **A common directive does not guarantee equal realized formatting.** It equalizes the instruction
  bytes, not the receiver's behaviour. Realized output shape may still differ by arm, and any observed
  difference in formatting is an outcome, never a controlled constant.
- **It does not isolate a formatting mechanism.** With the same extractor and the same private suites,
  adding a shared directive changes the intervention text, not the measurement. No mediation, no
  format-caused share of any contrast, and no decomposition of E13a's -0.1000 follows from it.
- **It does not validate the endpoint.** The endpoint stays thin private tests plus output validity;
  mbpp/863's known public defect, missed by its private assertions, remains the standing example.
  Because the contract changes the expected output shape, it needs its **own version label and its own
  validation pass** on frozen validation artifacts before any primary collection — that is a cost in
  section 4's contract, not a credit.
- **Answer removal was never a between-arm difference in E13a.** E13a's R1 and FRESH both omitted the
  previous answer, so nothing in E13a measured answer retention. The corrected design retains the
  previous answer in both arms, which is a property of the new prefix law and again identical across
  arms; no E13a result speaks to it.

Arms (unchanged text from the existing renderer, restated for the freeze list): **NEUTRAL** = the
existing N1 instruction; **DIRECTED** = the existing S1 instruction whose string is selected by the
public-status selector from public-check statuses only. Both then receive the identical contract bytes.
No private assertion, expected answer or reference implementation ever enters any prompt or any public
field, in either arm, at any turn.

---

## 3. Decision 3 — "Sizing, corrected"

**The declined proposal's claim that only additional roots narrow the approximation was wrong, and is
retracted.** Under the committed planning model (`scripts/e13_sizing.py:precision`, with
`arms_varying = 2` because both arms are sampled at the same root), the per-root paired standard
deviation is `sqrt(tau2 + 2*0.25/R)`. The within-root term is therefore:

| R (replicates per arm) | 2 | 4 | 6 | 8 | 10 | 12 | 20 |
|---|---|---|---|---|---|---|---|
| `2*0.25/R` | 0.250000 | 0.125000 | **0.083333** | 0.062500 | 0.050000 | 0.041667 | 0.025000 |

At R = 6 the within-root term is **0.083333**, larger than a hypothetical `tau2 = 0.025`. It exceeds
that hypothetical value for every R < 20 (the crossover is exactly R = 20; at `tau2 = 0.05` it is
R = 10, at 0.10 it is R = 5, at 0.20 it is R = 2.5). **More replicates do reduce the standard
deviation**, and at the replicate counts under discussion the within-root term is usually the larger
component. Both roots and replicates matter; the earlier one-sided claim is withdrawn.

Honest precision, computed with the committed machinery over hypothetical scenarios (G = roster size,
which section 7 leaves open; `WITHIN_VAR = 0.25` is the Bernoulli upper bound; the `tau2` values are
sensitivity choices, **not** identified variance bounds):

| G | R | tau2 | SD of root paired diff | nominal 95% normal half-width | Hoeffding radius, 1 contrast, mean on [-1,1] | nominal power at 0.10 | roots for 80% power at 0.10 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 6 | 0.025 | 0.3291 | 0.2281 | 0.9603 | 0.138 | 86 |
| 8 | 6 | 0.100 | 0.4282 | 0.2967 | 0.9603 | 0.101 | 144 |
| 12 | 6 | 0.025 | 0.3291 | 0.1862 | 0.7841 | 0.183 | 86 |
| 12 | 6 | 0.100 | 0.4282 | 0.2423 | 0.7841 | 0.128 | 144 |
| 12 | 8 | 0.025 | 0.2958 | 0.1674 | 0.7841 | 0.216 | 69 |
| 16 | 6 | 0.025 | 0.3291 | 0.1613 | 0.6791 | 0.229 | 86 |
| 16 | 8 | 0.025 | 0.2958 | 0.1449 | 0.6791 | 0.272 | 69 |
| 18 | 6 | 0.025 | 0.3291 | 0.1521 | 0.6402 | 0.252 | 86 |
| 18 | 8 | 0.025 | 0.2958 | 0.1367 | 0.6402 | 0.300 | 69 |

**What a run of this size buys.** A complete all-assigned set of `G x 2 x R` graded slots at G fresh
source-fixed development histories; a per-root paired description of NEUTRAL versus DIRECTED at
byte-identical prefixes and diagnostics; an all-assigned output-state partition showing *where* zeros
occur; a validated `terminal-output-contract-v1` measurement path; and a feasibility record of the
fresh-prefix pipeline end to end.

**What it does not buy, and must never be reported as buying.**

- **The descriptive finite contrast is the deliverable.** It is an equal-weight mean over G selected
  fixed histories, reported with its nominal half-width labelled as an uncalibrated normal
  approximation under assumed independence across roots whose family structure is unresolved.
- **Hypothetical independent-root moment scenarios are not validated confidence intervals** for
  selected fixed histories. The distribution-free radius at these G values (0.64 to 0.96 on a
  [-1,1]-bounded mean) is vacuous, which is the honest statement of what the assumption-free version
  of the same claim yields.
- **Zero-null power is not power above the 0.05 useful-gain threshold.** The "power at 0.10" column
  tests a zero null; it says nothing about establishing gain beyond a usefulness threshold, and a
  nonzero observed contrast can arise from sampling variation alone.
- **The later full-policy 0.05 useful-gain threshold must not be transferred to this descriptive arm
  comparison.** That threshold was defined for a full-policy contrast against a comparator, not for an
  instruction-wording contrast at development histories. It is not applicable here and is not armed.
- **Nothing here may drive efficacy, futility or stopping.** No interim look, no score-dependent stop,
  no futility rule and no efficacy declaration is proposed or permitted. Collection stops only on the
  frozen caps of section 4.
- **Observed saturation is not a floor or a ceiling.** A 0/R or R/R cell is an observation at R draws,
  never a structural property of a root.

**Feasibility labelling.** Given the resource cap, G will be in the range where the nominal half-width
is roughly 0.14-0.30 score points and the assumption-free radius is vacuous. Justified precision for a
usefulness claim is therefore **infeasible at the cap**. This stage is accordingly proposed as a
**descriptive feasibility stage**: it reports the finite contrast, the per-root table, the
output-state partition and the complete accounting, and **withholds all efficacy and futility
claims**. If the lead wants a precision-bearing stage instead, it needs a separately released frame
extension supplying many more independent roots, which this document does not request.

---

## 4. Decision 4 — "A complete operational contract", counted once

**Every component in one numerical contract.** Let G be the roster size from section 7 and R the
replicates per arm. Per root, at R = 6:

| # | Component | Receiver calls | Isolated execution starts |
|---|---|---:|---:|
| 1 | initial generation (fresh prefix, one call, no retry) | 1 | 0 |
| 2 | continuation: 2 arms x R replicates | 2R = 12 | 0 |
| 3 | public check of the initial answer (builds the diagnostic; public examples only) | 0 | 1 |
| 4 | diagnostic rendering and validation of message 3 (static, key-exact) | 0 | 0 |
| 5 | private scoring of the initial answer, strictly after all collection | 0 | 1 |
| 6 | private scoring of the 2R continuation outputs | 0 | 2R = 12 |
| 7 | reference/control rechecks (reference implementation on the private suite; control check) | 0 | 2 |
| 8 | validation of the `terminal-output-contract-v1` extractor/AST/suite path on frozen artifacts | 0 | 3 |
| 9 | containment renewal for the root's execution environment | 0 | 1 |
| | **per-root total** | **2R + 1 = 13** | **2R + 8 = 20** |

Totals are `G x (2R + 1)` receiver calls and `G x (2R + 8)` isolated starts. Worked values at R = 6,
for illustration only (G is not yet known):

| G | receiver calls | isolated starts | planning collection seconds at 2.040909 s/call | reserved completion tokens at 512/call |
|---:|---:|---:|---:|---:|
| 8 | 104 | 160 | 212.3 | 53,248 |
| 12 | 156 | 240 | 318.4 | 79,872 |
| 16 | 208 | 320 | 424.5 | 106,496 |
| 18 | 234 | 360 | 477.6 | 119,808 |

**The lead's arithmetic is adopted.** The declined proposal's 153 starts (27 validation + 108 candidate
+ 18 rechecks) was at least **162** once nine renewed containment starts were added: per root that is
3 + 12 + 2 + 1 = 18 under prefix reuse. The corrected fresh-prefix design is **2R + 8 = 20** per root,
because it adds the initial answer's public check and the initial answer's private scoring, and it adds
one receiver call per root for initial generation. Nothing in this count is reused from the withdrawn
batch.

**Caps, and which are enforced.**

- `max_calls` is set to exactly `G x (2R + 1)` from the frozen roster file, and a preflight refuses to
  start if the declared roster length, the arm count or the replicate count disagrees with the frozen
  manifest. Isolated starts are capped at `G x (2R + 8)`.
- `max_completion_tokens` is `512 x G x (2R + 1)`, reserved, with 512 per call enforced by the harness.
- **A prompt-token estimate from a different task mix is not an enforced bound.** E13a's measured
  per-call prompt means (R1 426.8, FRESH 205.8) came from five outcome-inspected checkpoints whose
  arms omitted the previous answer. This design retains the previous answer at a different task mix, so
  those means predict nothing binding here. Prompt length is bounded operationally only by the
  receiver's `num_ctx` 8192. If the lead wants an enforced bound, the release must freeze an explicit
  rendered-prompt ceiling that the preflight checks per slot and that refuses the slot rather than
  truncating it; otherwise prompt tokens are **reported, not bounded**, and must be stated that way.
- `2.040909 s/call` is the committed E12 A+C unit (`scripts/e13_sizing.py`, 314.3/154; the lead's exact
  recorded figure is 314.258/154 = 2.040636). It is a planning estimate from a different mix, not a
  guarantee; wall-clock caps must be set with explicit headroom in the release, not derived from it.
- Expected starts are below the caps because of caching and early rejection (E13a used 36 starts for 60
  calls, 0.60/call), but the **caps** are what the release binds.
- Paid spend `$0`; local receiver only.

**Existing code is not a release.** `experiments/landmark/` E13a code enforces five roots and 60 calls
and is **not** an E14 collector. A new collector, its preflight, its roster loader and its tests are
themselves deliverables of a later released item; no line of this document authorizes writing or
running one.

**Frozen all-assigned missing-outcome handling** (declared before collection, score-independent):

1. Every assigned slot is listed in the output with a status. Missing outcomes stay **missing** and are
   never imputed, re-drawn, retried or backfilled, and no substitute root is ever added.
2. Scheduling is root-balanced (both arms and all replicates of a root adjacent; arm order within a
   root from a recorded seeded shuffle, inferentially inert) so that a truncation preferentially loses
   **whole roots**.
3. **If the frozen deadline interrupts a root block mid-arm**, the root is recorded as *partially
   observed*: its collected slots are published as collected, **no root-level paired difference is
   published for it**, and its partially observed arm is never compared against the complete arm at the
   same root. The root remains in the all-assigned denominator.
4. If any assigned primary outcome is missing, **no primary point estimate is published** — only the
   individual missing-slot list with reasons and all-assigned completion bounds computed by
   substituting 0 and 1 for each missing slot. Those bounds are **not** confidence intervals.
5. The deadline is a wall-clock cap fixed in the release before collection and is never a function of
   observed scores. No interim analysis exists to stop on.
6. No parseability-conditioned subgroup and no conditioning on any post-treatment output property. The
   output-state partition (primary success / extraction-or-AST failure / extractable-parseable failure)
   is reported as a mutually exclusive, exhaustive description of where zeros occur, identifying no
   mediation.

---

## 5. Decision 5 — "The reserve is not validation"

**Accepted.** Ranks 61-198 of the frame stay a **protected reserve**: no development inspection, no
review, no roster use, and no inspection at all under MRL-22. Rank 41-60 expansion is likewise not
authorized. A reserved rank range is **not** an independent validation frame, and the following audits
are still outstanding before any validation claim could rest on it:

1. **Historical exposure audit.** The frame's prior-seen screen removed 598 ids using a mapped list,
   and the manifest itself records that HumanEval-style ids cannot be mapped to MBPP and were not
   similarity-screened. Exposure of reserve tasks to the receiver's training data, to earlier project
   stages, and to any prompt ever rendered in E11/E12/E13a must be audited explicitly.
2. **Semantic family overlap audit.** The within-frame family collapse used a token-similarity
   threshold with a provisional keep-the-smallest-seeded-hash rule, and the manifest records 26
   multi-member families plus threshold sensitivity (149/198/262/326 eligible at 0.4/0.5/0.6/0.7).
   **Provisional duplicate labels do not prove independent families.** Cross-family semantic overlap
   between a development roster and the reserve must be audited before the reserve can be treated as
   independent.
3. **Evaluation access audit.** Which artifacts, diagnostics, scores and summaries of reserve records
   any agent or document has ever seen must be established; a reserve that has been read is not blind.
4. **The policy split.** The development/validation split must be declared, hashed and enforced
   mechanically before the reserve is opened, with the rule fixed in advance of seeing anything in it.
5. **Hash rank is not a sampling law.** Ordering by `sha256("mrl15-frame-seed-20260922:<task_id>")`
   makes the order preregistered and reproducible; it does **not** make the eligible set a uniform
   sample from any population of tasks, because the eligible set is the survivor of prior-seen
   removal, near-duplicate screening, provisional family collapse and source-criteria dispositions.

---

## 6. The two targets, stated separately

**T1, the finite sampled-history contrast (the only target of this stage).**
`theta_T1 = (1/G) * sum over the G frozen roots of [ mean over R DIRECTED draws - mean over R NEUTRAL draws ]`
of the frozen private-suite-plus-output-validity score in {0,1}.

- **Definition.** Conditional on the G realized frozen histories (task text, generated previous
  answer, rendered diagnostic) and on the frozen receiver and evaluator versions.
- **Repetition assumption.** Only the receiver's sampling randomness is repeated: replicate draws at a
  root are assumed independent given the frozen prefix and the label-derived seed. This is an
  assumption, not a verified property; the only mechanical check is a preflight refusing any collision
  between newly derived seed values and any label ever spent at that root.
- **Assignment and inclusion probabilities.** Every (root, arm, replicate) slot is assigned by
  construction, so assignment probability is **1** and there is no propensity, no adaptive assignment
  and no sampling of slots. Root inclusion is a **deterministic** function of the frozen source rule
  (probability 1 given deliverable 2's dispositions), which is exactly why no design-based population
  inference follows.
- **Estimation.** All-assigned: the equal-weight mean above, with no weighting, no IPW and no
  imputation; missing outcomes handled by section 4's frozen rule. Uncertainty is reported as the
  nominal normal half-width **and** the assumption-free radius, both labelled as in section 3.

**T2, a task/prefix-law target (not estimated here).** A target of the form "the mean paired contrast
under a declared law over tasks and first-turn receiver draws" would require (a) a defined task
population, (b) a known sampling law from it with known inclusion probabilities, and (c) the prefix
draw treated as part of the sampling law. None holds: the roster is a deterministic hash-ordered
survivor of exclusions and source criteria, family structure is provisional, and the prefix is one
draw per root at a fixed seed. Therefore **no unbiasedness for any task-law mean and no design-based
variance is claimed**, at any G. This is a structural limitation of the frame, not something a larger
sample fixes. Any future T2 claim needs the section 5 audits plus a declared sampling law, released
separately.

---

## 7. Roster formation rule (size deliberately unasserted)

Deliverable 2 of MRL-22 produces the source-only dispositions for exactly frame ranks 21-40, in the
committed order

`911, 211, 701, 960, 667, 344, 370, 484, 524, 814, 346, 187, 508, 194, 356, 366, 302, 670, 376, 650`

(verified as `eligible_ordered_ids[20:40]` of the manifest whose sha256 is
`4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc`). **This document does not know
those dispositions and asserts no roster count.** The rule, to be frozen and hashed before any call:

1. **Eligible set.** Take the ranks 21-40 records whose deliverable-2 disposition is **`include`**, in
   the committed rank order. Records dispositioned **`hold`** are excluded from the roster and remain
   held with their recorded defect and smallest defensible next action; records dispositioned
   **`exclude`** stay excluded. Previous holds and exclusions from ranks 1-20 are preserved untouched.
2. **No loosening, no backfill, no rerank.** Criteria are not relaxed to reach a sample count; no rank
   beyond 40 is added; the order is not recomputed; no hold is converted to an include to enlarge the
   roster. If the eligible count is small, the stage is smaller — and, per section 3, it is then
   plainly labelled a descriptive feasibility stage.
3. **G is whatever that rule yields.** The roster file records, per root, the rank, task id, source
   hash, disposition and the recorded public interface/domain contract; its sha256 is frozen in the
   release. Caps are then computed from G by section 4's formulas, not chosen first.
4. **Every initial public-status category is retained** once initial answers exist: `pass`, `fail` and
   `unknown` roots all stay in the roster and in the estimand. If some category happens to be empty,
   that is reported as an observed property of the fresh prefixes, never used to re-select roots, and
   never presented as a designed stratum.
5. **A root is never removed after any score is seen.** The only score-independent losses are recorded
   receiver/harness failures and the frozen deadline, handled by section 4.
6. If deliverable 2 reports unresolved ambiguity at a record, that ambiguity is carried into the
   roster file as a declared limitation of that root, not silently resolved and never resolved by
   outcome screening.

---

## 8. Freeze list — everything fixed and hashed before collection

1. **Exact texts:** the task-prompt template; the initial-generation instruction; the NEUTRAL (N1) and
   DIRECTED (S1) instruction strings and the public-status selector that chooses among them; the
   `terminal-output-contract-v1` bytes and their attachment rule (message 4, after `"\n\n"`, identical
   in both arms); the diagnostic renderer and its key-exact validator.
2. **Receiver version:** model file and digest (`qwen2.5-3b-instruct-q4_k_m.gguf`, digest
   `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d`), server build `b1-4fea119`,
   pinned sampler parameters, `num_ctx` 8192. Any change invalidates the window and forces a re-release.
3. **Evaluator version:** extractor, AST check and private-suite scorer code hashes; endpoint label
   `e14-endpoint-v1`; the validation record for the new contract's expected output shape, published
   with the run.
4. **Source and config hashes:** the MBPP source bytes as recorded in the manifest; the frame manifest
   sha256; deliverable 2's report sha256; the frozen roster file sha256; the collector config including
   `seed` and the label law `label = "<arm>:<replicate>"`; the derived-seed collision preflight result.
5. **Root and family splits:** each root's provisional family label and the family rule/threshold used;
   the development roster versus the protected reserve (ranks 61-198, and 41-60 unauthorized); the
   standing ineligibility of the five E13a checkpoints and of the E11/E12 roots.
6. **Applicable precision rules:** that this stage is descriptive; the exact uncertainty statements
   permitted (nominal normal half-width plus assumption-free radius, both labelled); that **no**
   efficacy, futility or stopping rule is armed; and that the later full-policy 0.05 useful-gain
   threshold is **not** applicable and not transferred.
7. **Operational freeze:** caps from section 4 computed from the frozen G; the missing-outcome rule;
   the no-retry/no-backfill/no-substitution rule; the wall-clock deadline; the accounting schema that
   must report calls, starts, tokens, seconds and spend in one table.

---

## 9. Later stages, and what remains unauthorized

- **Independent policy evaluation is a later, separately frozen stage.** This stage evaluates no
  policy, estimates no population effect and produces no submission-ready efficacy claim. A policy
  evaluation stage needs the section 5 audits, a declared split, a frozen decision rule and its own
  release.
- **No generator or fixed-bank substitution is authorized.** No larger model, no different receiver, no
  fixed answer bank, no cached-generation shortcut and no compute-savings substitution may stand in for
  the pinned receiver at any point of this design.
- **Nothing here is a same-target correction of E12/E13a.** Those negatives stand at their own
  histories; this stage's histories and intervention law differ, and its results will be reported as a
  new finite description, not as a revision of theirs.

## Resource use for this document

Source-only. Zero model calls, zero model tokens, zero candidate/reference/public-check/containment/
sandbox executions, zero installations, no network, $0. Work consisted of reading the five files listed
above, recomputing the frame manifest sha256, reading `eligible_ordered_ids[20:40]`, and evaluating
`scripts/e13_sizing.py:precision` on hypothetical inputs. No grades file, analysis report, private
execution record or hidden score of any reviewed record was opened. No file under `results/`,
`experiments/landmark/dev_release_v2*/`, `dev_release_v3/` or `e13a_release/` was modified, and no
existing `docs/*.md` was modified; this document is new. Nothing was staged, committed or pushed.
