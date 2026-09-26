# E14 proposal: neutral versus diagnostic-directed revision at identical full prefixes

> **Correction, 2026-09-26 (LEAD-FRAME-01, lead `fd2092b`), added by the experiments worker. The original text below is kept unchanged as the historical record.** This document's statements that MRL-15 frame ranks 41–198 (or the 61–198 reserve) were uninspected, protected or untouched are incomplete. Four reserve IDs had already received task-specific manual review on 2026-09-20, with disposition `exclude_specification_pending_repair`: MBPP 159 (rank 69), 386 (91), 112 (146) and 289 (162). The source is `results/landmark_family_audit_20260920/adjudications.json`, sha256 `8ec2b573…`, crossed with `results/frame_review_mrl15_20260922T021718Z/manifest.json`, sha256 `4ffc10f0…`. The worker re-derived the four IDs and ranks independently, and they are the only earlier-adjudicated roots inside the frame. They must stay out of any proposed executable roster unless a versioned same-target specification repair is documented and re-adjudicated. The other 154 later-rank IDs have no targeted manual review in these two recorded sweeps. They are **not** certified untouched, valid, independent or representative.

23 September 2026. Experiment worker, MRL-21 item 3. Source-only document.

## Status: this proposes and releases nothing

> ## AMENDMENT, 2026-09-23 — the 9-root roster below CANNOT answer the primary question. Do not run it as specified.
>
> Building the actual request plan and auditing the roster refuted the design before any collection, which is
> why both were done first. Evidence: `results/e14_request_plan_20260923.json`,
> `results/e14_roster_audit_20260923.json`, and E12's published `analysis_report.json`.
>
> 1. **The endpoint is at the ceiling on every roster root.** The nine roots are exactly E12's nine
>    public-pass roots, and all nine already pass privately: STOP = 1.0 at each, **9/9**. A revision arm can
>    therefore only hold or break a passing answer. There is **no headroom for improvement at all**, so the
>    design cannot measure diagnostic-directed repair — only damage.
> 2. **The DIRECTED arm degenerates to a single constant wording.** `select_s1` is a deterministic function of
>    public statuses, and every roster root's public status is `pass`, so all nine select `S1_STRINGS[2]`
>    ("passes the listed public examples … check whether any change is needed"). No root has a recorded public
>    failure for the instruction to direct attention to, so the contrast is not neutral-versus-directed revision
>    at all; it is two near-equivalent "nothing observed to be wrong" wordings.
> 3. **E12 already observed exactly zero contrast at these prefixes.** On these same nine roots N1 scored 9/9
>    and S1 scored 9/9 with two draws each. Six draws will not make a ceiling informative.
>
> **Decision (experiments workstream).** The primary target — neutral versus diagnostic-directed revision at
> identical full prefixes — requires prefixes carrying a **recorded public failure**. The only development
> prefixes that have one are the five E13a checkpoints, whose reuse for this comparison the lead has excluded.
> So E14 needs **fresh public-fail prefixes**, which means a separately released source-only contract review of
> unreviewed frame ranks (21–60) followed by a fresh Phase A to create prefixes. That is not requested here and
> must not be done unreleased.
>
> What the nine-root roster *could* still measure is a different, secondary question: whether a
> diagnostic-confirming instruction damages already-passing answers. That is worth stating but it is not the
> primary target, it is bounded by the same ceiling, and it does not justify 108 calls on its own.
>
> Sections 1–8 below are retained unchanged as the design of record for the arms, contract, endpoint, seed law
> and caps — all of which survive the amendment. Only the roster is refuted.

- **This document proposes and releases nothing.** It authorizes no collection, no
  receiver start, no model call, no candidate/reference/containment execution and no
  spend. It was written with zero such execution.
- **Execution requires a separate explicit lead release plus a real host window**
  (release bindings, renewed attestation, receiver preflight, a resource agreement and
  an independent design/measurement review), exactly as for E12 and E13a. Unused E13a
  or MRL-20/21 calls, starts or window time authorize nothing here.
- **A new finite development study is not policy validation.** Every root proposed
  below is labeled **development**. No population effect, no independent policy
  evaluation and no submission-ready efficacy claim can follow from it.
- **This is a new intervention/history law, not an E13a repair.** E13a
  (`results/e13a_two_arm_20260923T061500Z/`) remains a valid, immutable negative
  result: R1 9/30 versus FRESH 12/30, equally weighted mean **-0.1000**, all 60
  assigned grades present. Nothing here retroactively repairs, reinterprets or
  re-scores it, and the design below is **not** another format-cue comparison.
- It must **not** be run on the five outcome-inspected E13a checkpoints
  (mbpp/842, 288, 863, 966, 652).

Verified inputs (sha256 of the bytes read while writing this):

| File | sha256 |
|---|---|
| `experiments/landmark/diagnostic.py` | `2a98bccf20cf3fa068790b488be8df4347387ae5ffb1bd7b1bd8b9d49d3a72b2` |
| `scripts/e13_sizing.py` | `e5e3c97dd428d56c030d277ccc56b747f11c8a080401a0102097033facd714eb` |
| `results/frame_review_mrl15_20260922T021718Z/manifest.json` | `4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc` |
| `results/frame_review_mrl15_20260922T021718Z/records.json` | `96dad5032cd9b346e1f4056fba6d8a3ab52533b9a702f0e791d710cd5efa0e74` |
| `results/e13a_two_arm_20260923T061500Z/analysis_report.json` | `b1a5af1393e93055b4efba5f79ddb63476cb77fb403623a1cde7d1a91339d708` |
| `docs/e13a_lead_judgment_20260923.md` | `1ebdda6f8f80948aab1b9bba606ce9c17361eb010ea8c6318d5bb0ea7c64e1a3` |

## 1. Target question and the two arms at an identical full prefix

**Target.** At a fixed development root with a frozen previous answer and a frozen
public diagnostic, does the *wording of the final revision instruction* change the
frozen private-suite-plus-output-validity score: a **neutral** "reconsider" wording
versus a **diagnostic-directed** wording, under the same receiver, the same horizon
(one revision turn) and one common terminal-output contract?

**Both arms share byte-identical messages 0-3.** Only message 4's instruction text
differs. Using `experiments/landmark/diagnostic.py:render_arms` (lines 347-369), the
two arms are exactly the existing **N1** and **S1** arms, plus the shared contract of
section 2:

```
[0] {"role": "system",    "content": collect.SYSTEM}                      # identical
[1] {"role": "user",      "content": "Task:\n...\n\nPublic information:\n..."}  # identical
[2] {"role": "assistant", "content": initial_output}                      # identical: previous answer RETAINED
[3] {"role": "user",      "content": DIAGNOSTIC_HEADER + "\n" + <diagnostic JSON bytes>}  # identical bytes
[4] {"role": "user",      "content": <ARM INSTRUCTION> + "\n\n" + TERMINAL_OUTPUT_CONTRACT}  # the ONLY difference
```

Message 3 is one `diagnostic.diagnostic_message(diag)` object whose bytes are reused
by both arms (as `render_arms` already does for N1/S1/R1), so the public diagnostic is
identical by construction and bounded by `MAX_DIAGNOSTIC_BYTES = 2048`.

**Arm NEUTRAL** reuses the existing `N_INSTRUCTION` (diagnostic.py line 32) verbatim —
no new string is introduced:

> `Reconsider your previous answer against the original task and public information. Return your best complete answer.`

**Arm DIRECTED** reuses the existing `select_s1(diag)` rule (lines 334-344) and the
existing `S1_STRINGS` (lines 33-37) verbatim. The selected string is a deterministic
function of the diagnostic's public statuses only:

- any status in `PAYLOAD_FAILURES` → `S1_STRINGS[0]`:
  > `Review the first public example with a recorded wrong value, format error, interface error, or program exception, in the diagnostic order. Compare the expected result with the recorded behavior, identify the discrepancy in your previous answer, and return a complete corrected answer. Check the remaining public examples and the full stated domain; do not merely hard-code the examples.`
- else any status in `INCOMPLETE` → `S1_STRINGS[1]`:
  > `The public diagnostic is incomplete. Do not interpret an unavailable result as a pass or infer a hidden error. Review your previous answer against the full stated domain and return your best complete answer.`
- else (all public examples pass) → `S1_STRINGS[2]`:
  > `Your previous answer passes the listed public examples, which do not establish correctness on the full stated domain. Check whether any change is needed; preserve correct behavior and return your best complete answer.`

**No new instruction string is invented.** The only new text in the whole design is the
terminal-output contract of section 2, which is appended **identically to both arms**.
The DIRECTED arm's wording varies across roots by the existing `select_s1` rule; that
variation is part of the intervention being tested ("diagnostic-directed wording"), it
is a function of public statuses only, and it must be reported per root so the
comparison is never silently pooled across different DIRECTED strings.

**Why this isolates what E13a could not.** E13a's R1 arm differed from FRESH in three
ways at once: the previous answer was **removed**, the diagnostic was **added**, and the
instruction string changed. So E13a's -0.1000 cannot be attributed to any one of them.
Here messages 0-3 and the terminal contract are byte-identical across arms, so the
**only** varying input is the final instruction wording. That is the whole contrast and
also its whole limit: it identifies nothing beyond the wording it varies.

## 2. Common terminal-output contract (identical in both arms)

> **Superseded, 2026-09-23:** the fence clause below is **withdrawn** — the frozen extractor accepts unfenced
> output, so the clause is unenforceable, and 1 of E13a's 60 saved outputs was fenced (0 of 30 in FRESH, which
> satisfied every other clause). `terminal-output-contract-v2` replaces it in
> [the corrected proposal](e14_corrected_proposal_20260923.md) section 0a, validated by
> `results/e14_output_contract_validation_20260923.json`. The v1 text is retained below as the historical draft.

Proposed text, label **`terminal-output-contract-v1`**:

> `Return the complete solution as one Python code block fenced by triple backticks, containing only the function definition and any imports it needs. Do not include test calls, example output, or any text copied from the diagnostic report.`

- It is **byte-identical in both arms** and **applied to both**, appended to message 4
  after `"\n\n"`. A run in which the two arms' contract bytes differ is invalid.
- Introducing it **changes the measurement relative to E12 and E13a**, which had no such
  contract. It therefore needs its **own version label** (`terminal-output-contract-v1`,
  carried in the stage manifest and in the endpoint label `e14-endpoint-v1`) and its own
  **validation pass** before any primary collection: the extractor/AST/private-suite path
  must be re-validated against the new expected output shape on frozen validation
  artifacts, with the validation record published alongside the run.
- **It does not repair the earlier negative.** E13a's 13 extraction-or-AST failures in
  R1 (one extraction rejection plus 12 Python-AST failures; all six R1 outputs at 966
  failed to produce parseable Python, and the saved failures include diagnostic-report
  echoes) were **not shown** to be correct solutions rejected cosmetically. The contract
  exists so that this new comparison is not a formatting contrast, not to recover latent
  semantic success in E13a, and not to claim any formatting mediation of -0.1000.
- The scorer code itself is unchanged and frozen; changing a scorer would require its own
  version and validation, which this proposal does not request.

## 3. Public-only information timing

At the moment each arm's message list is built, the visible information is exactly:

1. the public task prompt and public context (message 1),
2. the receiver's own previous answer text (message 2),
3. the public diagnostic record, built by `build_diagnostic` from the fixed public
   examples and the recorded per-case public-check statuses only (message 3),
4. the arm's instruction string plus the shared contract (message 4).

`select_s1` reads only `diag["cases"][*]["status"]`, all of which are public-check
statuses. **No private grade, private assertion, hidden test, reference solution or
hidden score is ever in any prompt, in any arm assignment, in any instruction selection,
or in any scheduling decision.** Every private evaluation happens strictly after all
collection is complete and is never fed back into any prompt. `validate_diagnostic`
enforces exact keys, so no non-public text can ride into message 3.

## 4. All-assigned endpoint

- **Primary endpoint:** the frozen private-suite-plus-output-validity score in {0,1}
  per slot (`e14-endpoint-v1`; scorer code unchanged, contract version recorded).
- **Primary estimand:** the equally weighted mean over assigned roots of the within-root
  paired difference (DIRECTED mean over replicates) - (NEUTRAL mean over replicates).
- **Every assigned slot is reported.** Missing outcomes stay **missing**, are listed
  individually with their reason, and are bounded by all-assigned completion bounds
  (substituting 0 and 1 for each missing slot); those bounds are **not** confidence
  intervals.
- **If any assigned primary outcome is missing, no primary point estimate is published**
  — only the completion bounds and the missing-slot list.
- **No parseability-conditioned subgroup** and no conditioning on any post-treatment
  output property. An all-assigned output-state partition (primary success /
  extraction-or-AST failure / extractable-parseable primary failure) may be reported as
  a mutually exclusive, exhaustive **description of where zeros occur**; it identifies no
  mediation, recovers no latent semantic success and quantifies no format-caused share.
- Thin private tests remain the endpoint: a passing score is **not** complete semantic
  correctness (mbpp/863's known public defect, missed by its private assertions, remains
  the standing example).

## 5. Roster construction and the untouched split (no new outcome inspection)

Constructed from `results/frame_review_mrl15_20260922T021718Z/manifest.json` and
`records.json` only. Counts read from those files:

| Quantity | Value |
|---|---|
| `counts.start_frame` | 396 |
| after step i (prior-seen removal) | 384 |
| after step ii near-duplicate-of-prior-seen | 235 |
| after step ii within-frame family collapse = `eligible_ordered_ids` | **198** |
| multi-member families in frame (`n_multi_member_families`) | 26 |
| preregistered source review depth (`preregistered.n_review`) | 20 |
| review decisions | include 18, hold 2, exclude 0 |
| held ids (`records.json` `spec_review.decision == "hold"`) | mbpp/359 (rank 3), mbpp/349 (rank 16) |
| E12 retained roots (`e12_dev_v3_20260922T030255Z/analysis_input.json`) | 14 |
| E13a outcome-inspected checkpoints | 5 (842, 288, 863, 966, 652) |
| prior-seen ids in source (`prior_seen_mbpp_in_source`) | 441 |

Preregistered order key: `sha256(f"mrl15-frame-seed-20260922:{task_id}")`,
`outcome_information_used = "none"` — the rank order is outcome-independent, so the
splits below are declared without inspecting any outcome.

**Proposed development roster (9 roots, available with no new task-frame review).**
The E12 retained roots that are *not* among the five E13a outcome-inspected checkpoints,
all with `spec_review.decision == "include"`, each already carrying a frozen initial
artifact and a built public diagnostic in
`results/e12_dev_v3_20260922T030255Z/B/diagnostics.json`:

| Root | frame rank | provisional family |
|---|---:|---|
| mbpp/918 | 1 | PF-918 |
| mbpp/825 | 2 | PF-825 |
| mbpp/816 | 7 | PF-816 |
| mbpp/895 | 8 | PF-895 |
| mbpp/868 | 9 | PF-813 |
| mbpp/154 | 11 | PF-49 |
| mbpp/651 | 18 | PF-651 |
| mbpp/499 | 19 | PF-499 |
| mbpp/974 | 20 | PF-147 |

All nine provisional families are distinct, and none coincides with a family of the five
E13a checkpoints (PF-29, PF-288, PF-863, PF-361, PF-652). Provisional families are the
MRL-15 union-find labels at threshold 0.5; the manifest states explicitly that it is
**not a family-independence certificate**, so independence across these nine is assumed,
not established.

- **Every eligible assigned root stays in, regardless of public pass or fail.** No root
  is dropped for its E12 outcome, its public-check status or its initial grade. A root
  whose previous answer passes all public examples simply receives `S1_STRINGS[2]` in the
  DIRECTED arm.
- **All nine are labeled development.** Their E12 outcomes have already been seen, so
  this is reuse of development histories, not an independent evaluation set. That is a
  stated limitation, not something the design can undo.
- **Optional extension (requires its own released, source-only step):** the four
  reviewed, include-decision ids not retained by the E12 contract review — mbpp/31,
  847, 907, 963 — plus frame ranks 21-60 (40 ids beginning 911, 211, 701, 960, 667).
  Extending to them needs a separately released source-only contract/frame review and a
  fresh prefix collection; **this proposal does not request it**, and it must not be done
  as part of MRL-21. The two held ids (359, 349) stay held.
- **Untouched future policy-evaluation split:** frame ranks **61-198 (138 ids)** are
  reserved and **must not be touched** by E14 or by any development study — not for
  roster construction, not for piloting, not for source review. They are named only by
  preregistered rank here, and no outcome, text or grade of theirs was read.

## 6. Seed and scheduling law

- **Existing derivation, unchanged:** `collect.seeded(config, root_id, label) =
  int(digest([config["seed"], root_id, label])[:15], 16) % 2**31`
  (`experiments/landmark/collect.py:151`), with `label = "<arm>:<replicate>"` and
  `config["seed"] = 20260921` as in E12 and E13a.
- **Spent labels at each of the nine roots (verified from E12 `calls.jsonl`):**
  `initial`, `N0:0`, `N0:1`, `S0:0`, `S0:1`, `N1:0`, `N1:1`, `S1:0`, `S1:1`, `R1:0`,
  `R1:1` — eleven labels per root. E13a spent `R1:2`-`R1:7` and `FRESH:0`-`FRESH:5` only
  at its five checkpoints, none of which is in this roster.
- **Proposed new labels:** `N1:2`-`N1:7` (NEUTRAL) and `S1:2`-`S1:7` (DIRECTED) at each
  of the nine roots — label-disjoint from every spent label at those roots, following
  E13a's own precedent of continuing the replicate index rather than restarting it. A
  check over the nine roots found **zero** collisions between the 108 proposed derived
  seed values and the spent ones. A preflight must re-run that check and refuse to start
  on any collision.
- **Inclusion probability 1** for every (root, arm, replicate): all 9 x 2 x 6 = 108
  slots are assigned by construction. There is no propensity, no sampling of roots and
  no adaptive assignment; balanced scheduling is **scheduling only** and is not an action
  propensity or a population sampling law.
- **Root-balanced order:** slots are emitted root-balanced (both arms and all replicates
  of a root adjacent, arm order shuffled within root by
  `seeded(config, root_id, "order")`) purely so that a truncated window loses whole roots
  rather than one arm. Order is recorded and carries no inferential role.
- **No retries, no backfill, no outcome-driven stopping.** A failed or timed-out slot is
  recorded as missing with its reason and is never re-drawn; collection stops only on the
  frozen caps of section 7, never on observed scores.

## 7. Proposed numerical caps and precision/feasibility rationale

Roster G = 9 roots, 2 arms, R = 6 replicates → **108 receiver calls**.

Measured unit costs used (all read from files):

- **2.040909 s per call**, `E12_SECONDS_PER_CALL = 314.3 / 154` in
  `scripts/e13_sizing.py` (line 20). The lead's exact recorded A+C collection time is
  **314.258 s** over 154 calls = 2.040636 s per call
  (`docs/e12_lead_judgment_20260923.md`); the committed constant rounds the numerator, a
  0.013% difference that changes no cap below.
- **E13a per-arm usage** (`analysis_report.json` `accounting.usage_by_arm`): R1 30 calls,
  12,804 prompt + 5,018 completion tokens, 108.153781 summed call seconds; FRESH 30
  calls, 6,174 + 1,388, 31.900255 s. Per call: R1 426.8 prompt / 167.3 completion;
  FRESH 205.8 / 46.3.

| Proposed cap | Value | Arithmetic |
|---|---:|---|
| `max_calls` | **108** | 9 roots x 2 arms x 6 replicates |
| Expected collection seconds | **220.4** | 108 x 2.040909 |
| `max_seconds` (collection) | **480** | E13a's frozen cap; 2.18x headroom over 220.4 |
| `max_tokens_per_call` | **512** | unchanged from E12/E13a |
| `max_completion_tokens` (reserved) | **55,296** | 512 x 108 |
| Expected actual completion tokens | **~18,100** | 108 x 167.3 (R1's measured mean) |
| Expected prompt tokens | **~46,100 - 110,600** | lower: 108 x 426.8 (R1 mean, which omits the retained answer); upper planning bound 108 x 1,024 (426.8 + a 512-token retained answer + contract) |
| Isolated starts cap | **153** | 27 validation (3 x 9) + 108 candidate + 18 recheck (2 x 9) |
| Expected candidate starts | **~65** | E13a ran 36 starts for 60 calls (0.60/call) with caching and early rejection |
| Setup wall / grading / analysis / outer caps | **600 / 300 / 300 / 2700 s** | E13a's frozen caps (`docs/e13a_lead_judgment_20260923.md` timing table) |
| Paid spend | **$0** | local receiver only |

**Prefix reuse.** No phase-A initial calls and no new diagnostics are needed: the nine
roots' frozen initial artifacts and public diagnostics already exist in
`results/e12_dev_v3_20260922T030255Z/`. That reuse is valid **only** under the identical
receiver identity recorded for E12/E13a (model `qwen2.5-3b-instruct-q4_k_m.gguf`, digest
`626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d`, server build
`b1-4fea119`, pinned sampler and `num_ctx` 8192). Any receiver or sampler change
invalidates the reuse and forces fresh prefix collection under a new label, with the
call and time caps recomputed. Prompt tokens are not capped by the harness; they are
reported, and the retained previous answer is the reason E14's prompt cost per call
strictly exceeds E13a's R1.

**Precision this size buys** (`scripts/e13_sizing.py:precision`, reused honestly with
`arms_varying = 2` because both arms are sampled at the same root; `WITHIN_VAR = 0.25`
is the Bernoulli upper bound, and the tau2 values are the committed sensitivity
scenarios, not identified variance bounds):

| n roots | R | tau2 | SD of root paired diff | 95% normal half-width | Hoeffding radius (1 contrast) | power at 0.10 | roots for 80% power at 0.10 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 9 | 6 | 0.025 | 0.3291 | 0.2150 | 0.9054 | 0.149 | 86 |
| 9 | 6 | 0.050 | 0.3651 | 0.2386 | 0.9054 | 0.130 | 105 |
| 9 | 6 | 0.100 | 0.4282 | 0.2797 | 0.9054 | 0.108 | 144 |
| 9 | 6 | 0.200 | 0.5323 | 0.3478 | 0.9054 | 0.087 | 223 |
| 9 | 8 | 0.025 | 0.2958 | 0.1933 | 0.9054 | 0.174 | 69 |
| 13 | 6 | 0.025 | 0.3291 | 0.1789 | 0.7533 | 0.195 | 86 |

So, stated plainly:

- **What it buys:** 108 complete assigned slots at nine identical-prefix roots; a
  within-root paired instruction contrast whose nominal 95% normal-approximation
  half-width is about **0.22-0.35** score points depending on the assumed between-root
  variance; a per-root paired description; and a validated `terminal-output-contract-v1`
  measurement path.
- **What it cannot buy:** it does **not** promise usefulness-threshold power. The
  distribution-free radius at n = 9 is **0.9054** on a [-1, 1]-bounded mean, i.e.
  vacuous, and 80% power against a 0.10 conditional difference needs **86-223** roots in
  these scenarios. Going to R = 8 (144 calls, ~294 s) buys only 0.2150 → 0.1933 at
  tau2 = 0.025, because the between-root term dominates; **adding roots, not replicates,
  is the only route to a narrower interval**, and the roots for that must come from a
  separately released source-only frame extension, never from the reserved ranks 61-198.
- **Standing corrections cited:** the lead's five-percentage-point usefulness threshold
  applies to a **full-policy** contrast and is **not addressed** by this development
  instruction contrast; and **no futility claim follows from small draw counts** — a
  null or negative E14 would not establish absence of a useful effect, absence of
  learnable heterogeneity, or any checkpoint's response-mean sign.
- The normal approximation is uncalibrated, roots are assumed independent although the
  family structure is unresolved, and the nine roots are a nonprobability development
  roster. Six draws per cell do not establish any single root's sign; observed 0/6 or 6/6
  cells would be **observed saturation**, never structural floors or ceilings.

## 8. What would make the result informative, and what it still would not establish

**Informative either way, because the prefix and diagnostic are held byte-identical:**

- A **complete all-assigned run** (108/108 graded) is itself the first measurement in
  this project in which instruction wording is the only varying input at a fixed full
  prefix, so the observed difference — of any sign — is attributable to the wording
  rather than to context removal or diagnostic presence.
- A **clearly non-zero observed paired difference** in either direction would be the
  first evidence that the receiver's revision behavior responds to how the revision is
  asked for, at fixed public information, and would justify proposing a sized,
  independently released study on an untouched split.
- A **near-zero observed difference with complete data** would say that, on these nine
  development histories with this contract, directing attention to the recorded public
  failure buys nothing detectable at this precision — which redirects effort away from
  instruction-wording engineering, without licensing a futility claim.
- **Either way**, the run yields a validated `terminal-output-contract-v1` measurement
  path and an all-assigned output-state partition, so a subsequent design need not
  confound wording with output formatting again.

**What it still would not establish, in any outcome:**

- **No population effect.** Nine selected development roots from a nonprobability frame
  identify no population mean, and no confidence statement about MBPP or any wider task
  population follows.
- **No policy validation.** This is not an independent evaluation, not a confirmatory
  trial, and not a test of any gated or history-conditional policy. The reserved
  untouched split (ranks 61-198) remains the only candidate for that, under its own
  release.
- **No mechanism beyond the instruction wording it varies.** It does not identify why a
  difference arises, does not decompose it into attention, formatting or content
  effects, and does not quantify any mediated or format-caused share. It says nothing
  about the E13a restart package, about context removal, or about diagnostic presence
  versus absence, since all of those are held fixed.
- **No completed semantic correctness.** The endpoint remains thin private assertions
  plus output validity; a passing score is not proof that a program is correct on the
  full stated domain.
- **No retroactive change to E13a.** E13a's -0.1000 and all five of its checkpoints
  stand as recorded.

## Pre-execution checklist (all required before any collection)

1. Explicit lead release naming E14, with a real host window and a resource agreement.
2. Frozen stage file and request plan with the arm strings, `terminal-output-contract-v1`
   bytes, the nine roots, the seed labels and every cap in section 7, all hashed.
3. Byte-equality preflight: messages 0-3 identical across arms at every root; contract
   bytes identical across arms; seed non-collision check passes.
4. `terminal-output-contract-v1` measurement validation published before primary
   collection.
5. Independent design and measurement review; receiver preflight, attestation and
   state-drift guards as in E12/E13a.
