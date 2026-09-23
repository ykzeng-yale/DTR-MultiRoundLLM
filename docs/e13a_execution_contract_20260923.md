# E13a prospective execution contract (PROPOSAL)

**Evidence class: source/static contract proposal. No model, receiver, benchmark program, candidate answer or sandbox
was executed to produce this document. It grants nothing.** Execution of E13a remains **held** until the coordinating
lead commits a separately enumerated budget and window. This document is the thing to be reviewed, not an authorization,
and nothing in it may be read as self-authorization: per the lead's ruling, "New execution remains held until this one
complete bundle is reviewed and a separately enumerated budget and window are committed"
([docs/e12_lead_judgment_20260923.md](e12_lead_judgment_20260923.md), section "E13 ruling and next discriminating action",
item 4).

Scientific scope is fixed by that ruling and is not reopened here: E13a compares the diagnostic-plus-R1-instruction
restart package (arm `R1`) against bare task resampling (arm `FRESH`) on the five fixed E12 public-fail checkpoints
`mbpp/842`, `mbpp/288`, `mbpp/863`, `mbpp/966`, `mbpp/652`
([results/e13a_request_plan_20260922.json](../results/e13a_request_plan_20260922.json), `roots[].root_id`). It is a
**post-hoc-motivated development follow-up**. It is not a test of the selected gated rule, not a test of a
diagnostic-only effect, and a tie is inconclusive rather than proof of a resampling mechanism. No pooling with E12, no
significance-driven escalation, and no futility claim from six draws.

---

## 1. Receiver, token and time limits

### 1.1 Attempts and tokens

| Quantity | Contracted limit | Source |
|---|---|---|
| Receiver attempts | **60** (2 arms x 6 replicates x 5 roots) | `budget.receiver_calls` = 60 in [results/e13a_request_plan_20260922.json](../results/e13a_request_plan_20260922.json) |
| Reserved completion tokens | **at most 30,720** (512 per attempt x 60) | `budget.reserved_completion_tokens` = 30720, same file; 512/attempt matches `decoding.num_predict` = 512 |
| Decoding | temperature 0.7, top_p 0.95, num_ctx 8192, num_predict 512 | `decoding` block, same file |
| Paid service spend | **$0** | no paid endpoint is bound; E12 recorded `paid_api_spend_usd` = 0 in [results/e12_dev_v3_20260922T030255Z/C/completion.json](../results/e12_dev_v3_20260922T030255Z/C/completion.json) |
| Candidate executions during collection | **0** | E12 recorded `candidate_executions` = 0 in the same file; E13a keeps collection and grading separate |

A 61st receiver attempt, or a reservation above 30,720, is a contract breach and aborts the stage. Reserved tokens are a
ceiling, not a forecast: E12 reserved 78,848 and measured 12,198 completion tokens over 154 attempts
([docs/e12_lead_judgment_20260923.md](e12_lead_judgment_20260923.md); A measured 592 and C measured 11,606 in the two
`completion.json` files), so the same ratio would predict roughly 4,800 measured completion tokens here. That prediction
is **not** a limit and must not be used to shrink the reservation.

### 1.2 Collection wall time — estimate and cap

E12's measured cumulative A+C collection time is **314.25796104222536 s over 154 attempted calls**
(`wall_seconds` and `attempted_calls` in
[results/e12_dev_v3_20260922T030255Z/C/completion.json](../results/e12_dev_v3_20260922T030255Z/C/completion.json); the
lead states the same 314.258 s figure and warns it is cumulative, not additive on top of A). Phase detail from the same
artifacts: A was 14 calls in 16.654884959571064 s, and the C phase alone was 140 calls in 297.6030753329396 s.

Derived per-call rates:

| Basis | Calls | Seconds | s/call |
|---|---:|---:|---:|
| A (initial) | 14 | 16.654885 | 1.190 |
| C phase (continuations) | 140 | 297.603075 | 2.126 |
| A+C cumulative | 154 | 314.257961 | 2.041 |

**Estimate for E13a: 60 x 2.126 = approximately 128 s** (the continuation rate is the right basis; all 60 E13a attempts
are single-turn requests of continuation shape, and the slower of the two measured rates is the conservative choice).
This is an **estimate**, not a commitment.

**Contracted collection cap: 480 s.** Reasoning for the 3.8x headroom over the 128 s estimate: (i) the per-call time
recorded in E12 is an aggregate — no per-call durations are stored in the phase artifacts — so the variance is unmeasured
and cannot be bounded from the record; (ii) E13a starts with a cold KV cache and a freshly launched server, while much of
E12's C phase benefited from prefix reuse across arms on the same root (the lead attributes E12's smaller execution count
partly to caching); (iii) the host is shared, so contention can stretch wall time without any integrity fault; (iv) a cap
must never be so tight that ordinary slowness forces an abort mid-batch, because an aborted batch wastes the whole
window. The cap is still far below E12's 1,200 s A+C allowance
([docs/e12_receiver_restart_amendment_20260922.md](e12_receiver_restart_amendment_20260922.md), "Unchanged collection and
reporting limits"), which is the right direction for a stage with 60 attempts instead of 154.

### 1.3 Grading wall time — estimate and cap

E12's private grading measured **2.5307021252810955 s** for 154 artifacts (`grading_wall_seconds` in
[results/e12_dev_v3_20260922T030255Z/D/summary.json](../results/e12_dev_v3_20260922T030255Z/D/summary.json); the lead
reports 2.531 s), i.e. 0.01643 s/artifact. **Estimate for 60 artifacts: approximately 1.0 s.**

**Contracted grading cap: 300 s.** Reasoning: the estimate is ~1 s, but each grading start runs an isolated executor with
its own process setup and per-case timeouts, and a single pathological candidate (an infinite loop caught by the
per-case timeout) dominates the total. 300 s absorbs several such candidates and is **below** the 600 s
`grading_limits.grading_seconds` already frozen in
[experiments/landmark/dev_release_v3/release_manifest.json](../experiments/landmark/dev_release_v3/release_manifest.json)
(sha256 `c9d591ffd4a524992ced28c1cc2f68fc5c299cc14ad8022e587eefc5bb67d3ea`). That frozen 600 s is a **limit**, not
authority to spend 600 s.

### 1.4 Outer end-to-end limit

| Segment | Cap |
|---|---:|
| Attestation renewal, launch, preflight, snapshot diff, refreeze (section 3) | 600 s |
| Collection (section 1.2) | 480 s |
| Private grading (section 1.3) | 300 s |
| Analysis, contrast computation and deterministic final report | 300 s |
| Sum of segments | 1,680 s |
| **Outer end-to-end limit, contiguous** | **2,700 s (45 minutes)** |

The outer limit is a single contiguous wall-clock window from the first setup action to the published final report, with
1,020 s of slack over the segment sum for handoffs between phases. It is below E12's 59 contiguous minutes. Segment caps
and the outer cap are independent: exhausting either one stops the stage. Scheduling wait before the window is not
charged against any of these caps and must be recorded separately, as MRL-16 required for setup time.

---

## 2. Full enumeration of isolated executor starts

**E12's unused start ledger is NOT authority for this stage.** The lead is explicit:
"**333+70=403 is accounting, not authority:** E12 explicitly disallows spending unused starts on another study"
([docs/e12_lead_judgment_20260923.md](e12_lead_judgment_20260923.md), item 4). The request plan itself carries the same
caveat (`budget.ledger_note` in [results/e13a_request_plan_20260922.json](../results/e13a_request_plan_20260922.json)).
A **separately enumerated allowance** is required for every line below; none of them may be drawn from the 79 starts
remaining under the 412 ceiling by arithmetic alone.

| # | Line item | Starts | What each start is |
|---|---|---:|---|
| 1 | Artifact grading | **60** | one isolated private-suite execution per graded continuation artifact (1 per receiver attempt) |
| 2 | Control / reference rechecks | **10** | 2 per root x 5 roots, the frozen reference-solution recheck that proves the private suite still discriminates |
| 3 | Containment attestation renewal payloads | **9** | one payload start per required check in `grade.REQUIRED_CHECKS`: `own_run_read_write`, `home_read`, `home_write`, `peer_run_read`, `outside_home_tmp_write`, `loopback_network`, `system_subprocess`, `fork_creation`, `timeout_and_process_cleanup` ([experiments/landmark/grade.py](../experiments/landmark/grade.py) line 28; `verify_attestation` requires `passed is True` **and** `payload_started is True` for each) |
| 4 | Public-check starts | **0 in the primary stage** | the primary endpoint needs no public execution; gating is read from frozen public diagnostics (section 4). The optional supplement in section 7(b) would add 70 and is **not** included here |
| | **Total requested isolated executor starts** | **79** | |

Non-start executions, itemized separately because they are receiver metadata/template traffic rather than isolated
executor starts, and they generate no tokens:

| Line item | Count | Bound |
|---|---:|---|
| Non-generating metadata/template attempts (props, slots, models, render) | **at most 50** | the MRL-16 cap, at most 10 s each, no retries, inside the 600 s setup segment |
| Rendered prompt-byte comparisons (MRL-10 seven-root fixture set) | **42** | comparison of already-rendered bytes; `rendered_prompts_compared` = 42 in [results/receiver_diff_v31_20260922T071000Z.json](../results/receiver_diff_v31_20260922T071000Z.json) |
| Receiver generation smoke calls | **0** | forbidden by MRL-16 condition 3 |

Ledger arithmetic, offered only as accounting: the cumulative ledger stands at **333/412**
([docs/e12_lead_judgment_20260923.md](e12_lead_judgment_20260923.md)), so 79 remain and 333 + 79 = 412 would consume the
ceiling exactly. That coincidence is a reason for caution, not a reason to proceed: it shows the old ledger has no
headroom for a second stage and reinforces that E13a needs its own enumerated allowance rather than the remainder of
E12's.

---

## 3. Runtime-attestation renewal procedure

**Both the containment attestation and the shared-host window have EXPIRED.** Evidence:

- The most recent passing attestation is
  [results/landmark_containment_20260921T125641Z/attestation.json](../results/landmark_containment_20260921T125641Z/attestation.json),
  `schema_version` `landmark-containment-v1`, `passed` true, `checked_at` **2026-09-21T12:56:41.648906+00:00**. The
  immediately preceding one,
  [results/landmark_containment_20260921T125535Z/attestation.json](../results/landmark_containment_20260921T125535Z/attestation.json),
  records `passed` **false** and must not be used.
- `grade.verify_attestation` rejects any attestation whose age is outside `0 <= age <= 86400` seconds
  ([experiments/landmark/grade.py](../experiments/landmark/grade.py) lines 106-118). As of 23 September 2026 the
  2026-09-21 attestation is more than 24 h old, so **every real grading path is currently closed**:
  `study_adapter.grade_study` raises `ValueError("Containment attestation required")` when no path is given and otherwise
  calls `grade.verify_attestation` ([experiments/landmark/study_adapter.py](../experiments/landmark/study_adapter.py)
  lines 239-253); only a declared fake, non-executing test runner is exempt.
- The shared-host window ran 2026-09-22T07:10:00Z to 08:20:00Z
  ([docs/e12_shared_window_20260922T071000Z.json](e12_shared_window_20260922T071000Z.json), and the peer's copy at
  `/Users/yukangzengcmac/DTR-AgentEvals/results/v2_agent/slot_agreement_20260922_0710.json`). It has elapsed.

### 3.1 Renewal steps, in order

1. **Renew containment attestation.** Run `scripts/check_landmark_sandbox.py` on the dispatch host and write a fresh
   `attestation.json` to a new immutable path. It must satisfy, per `grade.verify_attestation`:
   `schema_version == "landmark-containment-v1"`; `passed is True`; `script_sha256` equal to the sha256 of
   `scripts/check_landmark_sandbox.py` at dispatch HEAD; `binding` equal to `grade.current_binding()`, i.e. the seven
   fields `sandbox_sha256`, `profile_sha256`, `python`, `python_sha256`, `host_sha256`, `platform`, `sandbox_kind`
   ([experiments/landmark/grade.py](../experiments/landmark/grade.py) lines 98-103); exactly the 9 `REQUIRED_CHECKS`
   present, each with `passed is True` and `payload_started is True`; and `checked_at` inside 24 h of **every** grading
   call, not merely of dispatch. Because the interpreter path and its hash are part of the binding, the attestation must
   be produced with the same `/Users/yukangzengcmac/DTR-MultiRoundLLM/.venv/bin/python` that will grade.
   Cost: the 9 payload starts itemized in section 2, line 3.
2. **Verify the 26 pinned binary/library hashes** against
   [experiments/env/llama_server_manifest.json](../experiments/env/llama_server_manifest.json)
   (sha256 `63d8e03bcea39031e4d5d4334ccf58e09159a4304f609f2bd320f4538922c2b8`; its `files` array has exactly **26**
   entries). E12's launcher recorded `pinned_build_files_verified` = 26
   ([results/e12_receiver_v31_20260922T071000Z/launch.json](../results/e12_receiver_v31_20260922T071000Z/launch.json)).
   Any mismatch holds dispatch.
3. **Verify the exact model digest**
   `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d` for
   `qwen2.5-3b-instruct-q4_k_m.gguf` (recorded as `model_sha256` in the same `launch.json`, and required by
   [docs/e12_receiver_restart_amendment_20260922.md](e12_receiver_restart_amendment_20260922.md) condition 1). No model
   substitution and no change of numerical backend is covered by this contract.
4. **One launch attempt only**, with the committed launcher
   [scripts/launch_own_receiver_v31.py](../scripts/launch_own_receiver_v31.py)
   (sha256 `03bede1d1de39f376daadcec79c81b2edea9c2c0b56e8e03bb019c321d4a16b5`, matching `launcher_sha256` in both the
   07:10 `launch.json` and the ownership record), reusing the recorded shape `-ngl 99 -np 4 -c 32768 --jinja` on
   loopback port 8193 with 8,192 tokens per slot, and the pinned `LLAMA_MEDIA_MARKER`. Record PID, exact command, host,
   start/ready/stop times, memory pressure before and at ready, and `generation_requests` = 0. Confirm the port is free
   **without** signalling another project's process.
5. **Receiver-snapshot field-by-field diff.** Run [scripts/diff_receiver_snapshot_v31.py](../scripts/diff_receiver_snapshot_v31.py)
   (sha256 `923871d9f000e75428ddb98099ffb2c9a7fd5b04396b653dea9c74f7f6ddc958`) against the frozen snapshot
   [results/receiver_props_snapshot_8193.json](../results/receiver_props_snapshot_8193.json)
   (sha256 `c0b3aaf2fd07f7aa259041eeb30abd588e6f07362295786c4e43a580b76b619e`, which is exactly the
   `frozen_snapshot_sha256` recorded by E12's diff). Dispatch requires, as E12's diff achieved
   ([results/receiver_diff_v31_20260922T071000Z.json](../results/receiver_diff_v31_20260922T071000Z.json)):
   `n_field_differences` = 0, `state_identical` true, `receiver_state_sha256_new` ==
   `receiver_state_sha256_frozen` == `1b8bf998c5dd06a611f692bab9e802b285ae75164b8b389fd8b381c06a83f5c1`,
   empty `render_mismatches` and `validation_errors`, `passed` true. Model/build (`build_info` `b1-4fea119`), chat
   template, capabilities, `bos_token` `<|endoftext|>` / `eos_token` `<|im_end|>`, context/slots (`total_slots` 4),
   sampler values **and order**, modalities, endpoint settings and request/seed/cache behaviour must all match. The
   canonical-state function excludes only `is_sleeping`; `media_marker` stays inside the hash and may be reclassified as
   launch-only text-irrelevant **only** with recorded source/usage evidence plus unchanged render checks. The frozen
   server default temperature (~0.8) and the intentional per-request override 0.7 both stay as they are; neither is
   edited to mimic the other. Any other unclassified or outcome-relevant difference **holds collection and reports the
   exact difference** rather than triggering a redesign.
6. **Non-generating render checks.** Run [scripts/receiver_preflight_mrl10.py](../scripts/receiver_preflight_mrl10.py)
   (sha256 `15ac29ed1981f44dafbb94ae222d27513c07a638b2cd9b963a6b30b16ace13eb`) over the committed MRL-10 seven-root
   fixture set and compare **42** rendered prompt bytes to the prior snapshot, producing the same artifact shape as
   [results/receiver_preflight_v31_20260922T071000Z/](../results/receiver_preflight_v31_20260922T071000Z)
   (`props_before.json`, `props_after.json`, `slots_before.json`, `slots_after.json`, `models.json`, `rendered/`,
   `summary.json`). Hard limits: at most 50 non-generating metadata/template attempts, at most 10 s each, no retries, no
   model smoke calls, and **do not** pass the 14 E12 roots or the 5 E13a roots into this preflight — it is specific to
   those fixtures. Template equality does not claim output equality.
7. **Refreeze and commit before collection.** Commit the renewed attestation path, the new launch/ownership record, the
   new snapshot diff and every dependent configuration/manifest binding **before** the first receiver call, keeping the
   accepted `dev_release_v3` paths so the strict grading-path check stays intact, and keeping one clean HEAD for the
   whole stage with no mid-batch pulls.
8. **Release.** Terminate only this project's own process at completion or on an integrity/resource failure, record the
   stop **and** the observed exit, and publish an explicit release artifact to the peer. Section 7(a) shows precisely
   which of these records E12 did and did not leave behind; the gap there is the reason step 8 is written this way.

---

## 4. Source bindings

Every input the stage reads, its role, and whether it must be hash-pinned before dispatch. "Pin" means the sha256 is
recorded in the dispatch manifest and re-verified at read time; a mismatch holds dispatch.

| Input path | Role | Pin before dispatch |
|---|---|---|
| [results/e13a_request_plan_20260922.json](../results/e13a_request_plan_20260922.json) | the 60 requests: `roots[].root_id`, `roots[].requests[].{arm,replicate,seed_key,seed,messages_sha256}`, top-level `decoding` | **Yes.** Current bytes hash to `f16d9c1086b30273975421c6b6b805082a77dcb2083570c547e758e23e3398f7`; the parent is revising this file, so the pin is whatever HEAD carries at dispatch, recorded then |
| [scripts/build_e13a_request_plan.py](../scripts/build_e13a_request_plan.py) | generator of the plan; establishes that R1/FRESH strings and seeds were derived, not typed | **Yes** (`4795b053278e84de31ac45f31b78c6bdcd6dcb46aa6f883d48f3470c173397d5` at time of writing) |
| results/e12_dev_v3_20260922T030255Z/A/roots.jsonl | E12 initial artifacts and base messages; source of the byte-identical FRESH prompt | **Yes** — `5e26bafac75a07b5bd35df01131533d36ba233b5b6eb8802bdf0e9ae9b851947` per the plan's `inputs` |
| results/e12_dev_v3_20260922T030255Z/B/diagnostics.json | **frozen public diagnostics**; the only permitted source of checkpoint selection | **Yes** — `e95d50bae632f73a96094673a03aff9401993c5c3d986086f63c5fe3cf8bd94a` per the plan's `inputs` |
| results/e12_dev_v3_20260922T030255Z/C/calls.jsonl | E12's recorded R1 requests; source of the byte-identical R1 message list | **Yes** — `3de109d968098151970a889b4ce8d1b0151413bcdbfc8de566cbb358d0d9223f` per the plan's `inputs` |
| results/e12_dev_v3_20260922T030255Z/ARTIFACT_SHA256SUMS.json | index the three inputs above are checked against | **Yes** (read-only; E12 is immutable) |
| [experiments/landmark/dev_release_v3/release_manifest.json](../experiments/landmark/dev_release_v3/release_manifest.json) | grading bindings and `grading_limits`; allowlisted release | **Yes** — `c9d591ffd4a524992ced28c1cc2f68fc5c299cc14ad8022e587eefc5bb67d3ea`; `study_adapter.verify_committed_release` additionally requires the file to be tracked at git HEAD and byte-identical to its HEAD blob ([experiments/landmark/study_adapter.py](../experiments/landmark/study_adapter.py) lines 449-467) |
| dev_release_v3 private specs / tasks / public examples (per the manifest's `grading_bindings`) | private suite, task text, public example | **Yes** — `load_release_bindings` refuses missing, `UNRESOLVED` or mismatched bindings and non-hex digests (same file, lines 413-447) |
| [experiments/env/llama_server_manifest.json](../experiments/env/llama_server_manifest.json) | the 26 pinned build files | **Yes** — `63d8e03bcea39031e4d5d4334ccf58e09159a4304f609f2bd320f4538922c2b8` |
| the GGUF model file | the receiver weights | **Yes** — digest `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d` |
| [results/receiver_props_snapshot_8193.json](../results/receiver_props_snapshot_8193.json) | frozen receiver snapshot for the field-by-field diff | **Yes** — `c0b3aaf2fd07f7aa259041eeb30abd588e6f07362295786c4e43a580b76b619e` |
| the renewed `attestation.json` (new path, section 3.1 step 1) | containment gate for all grading | **Yes**, plus the freshness check: within 24 h of every grading call |
| [experiments/landmark/collect.py](../experiments/landmark/collect.py), [collect_diagnostic.py](../experiments/landmark/collect_diagnostic.py), [diagnostic.py](../experiments/landmark/diagnostic.py), [grade.py](../experiments/landmark/grade.py), [study_adapter.py](../experiments/landmark/study_adapter.py), [analyze_diagnostic.py](../experiments/landmark/analyze_diagnostic.py) | the instruments (`seeded`, `initial_messages`, `digest`, phased collector, `render_arms`/`diagnostic_message`/`R1_INSTRUCTION`, grader v5, grading/analysis CLIs) | **Yes** — instrument source bytes are pinned by the frozen-HEAD requirement; grader identity is `landmark-grader-v5-parse-and-compile-fault-attribution` ([experiments/landmark/grade.py](../experiments/landmark/grade.py) line 40) |
| [scripts/launch_own_receiver_v31.py](../scripts/launch_own_receiver_v31.py), [scripts/diff_receiver_snapshot_v31.py](../scripts/diff_receiver_snapshot_v31.py), [scripts/receiver_preflight_mrl10.py](../scripts/receiver_preflight_mrl10.py), `scripts/check_landmark_sandbox.py` | launch, diff, render preflight, containment check | **Yes** — hashes in section 3.1; `check_landmark_sandbox.py`'s hash is additionally re-verified by `verify_attestation` |

Two bindings deserve explicit notice.

- **`grading_limits` in `dev_release_v3` is frozen for 14 roots.** It reads `n_roots` 14, `artifact_starts` 154,
  `recheck_starts` 28, `max_private_starts` 182, `grading_seconds` 600. E13a's 60 artifact starts and 10 recheck starts
  fit **numerically** inside those frozen ceilings, so no new release package is required and the frozen package must not
  be edited. But fitting inside a frozen ceiling is not authorization to spend, and the E13a runner must carry its own
  explicit 60/10/300 caps rather than inheriting 154/28/600 as defaults. E12's hard-coded arm and count assumptions are
  not reused.
- **No private grade may appear in any executable input.** Checkpoint selection is derived from
  `B/diagnostics.json` through the frozen public-status path, which is exactly what the plan's `checks` list records
  ("checkpoints derived from frozen public diagnostics via `analyze_diagnostic.public_status`; no private grade is
  read"). The primary endpoint remains the frozen private-suite-plus-format score, computed only after collection.
  Inclusion probability is 1 for every root-arm; ordering is root-balanced scheduling only and carries no information.

---

## 5. Shared-host availability and proposed reservation

### 5.1 What the sibling project's published state actually says

Read-only inspection of `/Users/yukangzengcmac/DTR-AgentEvals` (its git HEAD is `4927adc`):

- `/Users/yukangzengcmac/DTR-AgentEvals/results/v2_agent/slot_agreement_20260922_0710.json` records the **expired**
  window: `holder` "DTR-MultiRoundLLM MRL-16", `start_utc` 2026-09-22T07:10:00Z, `end_utc` 2026-09-22T08:20:00Z,
  `recorded_utc` 2026-09-22T05:22:28Z, with `execution_status` "Reservation accepted by coordinating lead; DTR worker
  acknowledgement, actual DTR release and peer launch are not observed." Its `launch_condition` requires "Explicit actual
  DTR release plus peer live ownership/resource checks", and its `conflict_rule` forbids interrupting an existing job or
  silently extending a slot. This is the peer-side mirror of
  [docs/e12_shared_window_20260922T071000Z.json](e12_shared_window_20260922T071000Z.json). **It grants nothing for
  E13a.**
- `/Users/yukangzengcmac/DTR-AgentEvals/docs/theory_feedback_20260922_pilot_release.md` line 44 records DTR-REQ-004 as
  "P0 **PROCEED**" with the peer's next-slot claim explicitly declined and the worker required to record actual start and
  end, recheck ownership and resources, publish PIDs, use at most one server, and release at the cap. That deferral was
  scoped to that block and has elapsed with it.
- `/Users/yukangzengcmac/DTR-AgentEvals/AGENTS.md` line 42 states the sibling's current phase instruction: while GPU
  capacity is limited the theory workstream **defers new model inference, GPU jobs and Monte Carlo sweeps**, with
  deterministic CPU analysis and manuscript work in scope. That lowers the expected contention but is a **statement of
  the sibling's own priorities, not an agreement to yield the host**.
- The sibling's most recent published work is consistent with that: `results/v2_agent/analysis_20260922/` (written
  2026-09-22, e.g. `SUMMARY.md`, `cross_cohort_diagnostic.json`) is a descriptive synthesis of **already-completed**
  episodes and states that none of it measures model capability. Its newest commits (`4927adc`, `e8a3d39`, `f8252c9`)
  describe diagnostics of completed episodes and an idle state awaiting lead review. No artifact under
  `/Users/yukangzengcmac/DTR-AgentEvals/results/` dated after 2026-09-22 claims an active accelerator block, and there
  is **no published sibling reservation covering 23 or 24 September**.

**No current host reservation exists for either project, and none of the above is an availability guarantee.**

### 5.2 Proposed reservation (contingent)

| Field | Proposal |
|---|---|
| Window | **2026-09-24T07:10:00Z to 2026-09-24T08:20:00Z** (70 minutes) |
| Rationale for shape | reuses the time-of-day and 70-minute shape the peer already negotiated once, so the request is familiar and needs no new protocol; 70 minutes covers the 45-minute outer limit plus handoff |
| Latest collection start | 2026-09-24T07:25:00Z; if setup and the renewal checks are not complete by then, the stage does not start |
| Holder | DTR-MultiRoundLLM, E13a |
| Quiet requirement | no competing accelerator or CPU/memory/IO-heavy work from either project inside the window; light source/status work may continue |
| Release | explicit published release artifact at or before 08:20:00Z, naming the PID and the observed exit |

This window is **contingent on peer agreement** and on the lead committing a separately enumerated budget. Availability
must be **re-agreed at dispatch** and **cannot be inferred from idleness**: not from an empty results directory, not from
a free port 8193, not from reduced swap usage, not from the sibling's deferral of GPU work in `AGENTS.md`, and not from a
previous window's clock having run out. The peer's own record makes the same point about the mirror case — its
`required_before_launch` note says a reported hard end "is not release evidence"
([docs/e12_shared_window_20260922T071000Z.json](e12_shared_window_20260922T071000Z.json)). No existing job may be
interrupted to obtain capacity.

---

## 6. Stop and abort rules

A stop is triggered **only** by an integrity failure or a resource failure. Interim outcomes never stop, extend, shrink
or redirect this stage.

**Integrity stops:** any of the 26 build-file hashes mismatching; the model digest mismatching; a non-empty
`field_differences` or `state_identical` false in the snapshot diff; any render mismatch among the 42 compared prompts;
an attestation that fails `verify_attestation` for any reason, including age; a release-manifest binding that is missing,
`UNRESOLVED`, mismatched or untracked at HEAD; any request whose `messages_sha256` does not equal the plan's value for
that root and arm; any new seed colliding with a seed E12 used on the same root; a private grade appearing in any
executable input; a HEAD change mid-stage.

**Resource stops:** the collection cap (480 s), grading cap (300 s) or outer cap (2,700 s) being reached; the 60-attempt
or 30,720-token ceiling being reached; the window hard end; a memory-pressure or host-contention condition that would
degrade the peer's work; any paid spend above $0.

**Explicitly not stopping conditions.** The following are forbidden as triggers for stopping, continuing, extending or
resizing: an early R1-versus-FRESH split in either direction; a run of zeros or ones; a per-root pattern; any p-value or
interval computed mid-stage; any futility impression from six draws. There is no interim analysis, no optional stopping
and no escalation path in this contract. All 60 attempts and all 70 grading/recheck starts either run under the
committed allowance or the stage does not start. On any stop, the rule is to publish the exact failing condition and the
immutable partial records, and to release the host — not to retry, not to substitute, and not to reconstruct.

---

## 7. Evidence checks

### 7(a) Retained original exit/release evidence for E12's owned server

Searched: the whole repository tree and `/Users/yukangzengcmac/DTR-MultiRoundLLM/work` for archived server logs,
stop/exit records, launcher PID records and any ownership-release artifact. Nothing was reconstructed, re-run or
re-derived; hashes below are of the files as they sit on disk.

**EXISTS — the 07:10 collection run (the run that produced E12's data):**

| Artifact | sha256 | What it evidences |
|---|---|---|
| [results/e12_receiver_v31_20260922T071000Z/launch.json](../results/e12_receiver_v31_20260922T071000Z/launch.json) (tracked at git HEAD) | `697557d8e01c4055593898546ecf8506a78a29bf4a06ac8d0afdb88d6c7d67e2` | `pid` 35499; exact command; host `Yukangs-MacBook-Pro.local`; `source_head` `2bc8546aff8747ee4a6e73bee84bf7f391d3b30f`; `launcher_sha256` `03bede1d…`; `started_utc` 2026-09-22T07:10:02.173407+00:00; `ready_utc` 07:10:03.180766+00:00; `ready_seconds` 1.0284066256135702; `pinned_build_files_verified` 26; `model_sha256` `626b4a66…`; `generation_requests` 0; memory before and at ready; `setup_deadline_utc` 07:20:00Z; `shared_window_hard_end_utc` 08:20:00Z; **`stopped_utc` 2026-09-22T07:15:30.254657+00:00**; **`exited` null** |
| results/e12_receiver_v31_20260922T071000Z/llama_server.log (**present on disk, NOT tracked at git HEAD**) | `a4cafa751392a75a6c43235945b4bd5b98dff21c46e8267b0fb7e2129ea2e893` | 1,121 lines. Its final line is `5.28.059.208 I srv operator(): operator(): cleaning up before exit...` — a shutdown **initiation** at ~5 min 28 s after start, consistent with the recorded `stopped_utc` of 07:15:30.254657. No later line exists |
| [docs/e12_shared_window_20260922T071000Z.json](e12_shared_window_20260922T071000Z.json) (tracked) | referenced as `ownership_sha256` `e198e01a9db858605bb8a79f4869df06137de148c738be19ad52cb1b67f26714` by `launch.json` | the ownership/reservation record: window 07:10:00Z-08:20:00Z, `setup_max_seconds` 600, `startup_attempts_authorized` 1, `metadata_template_attempts_max` 50, `generation_smoke_calls` 0, `paid_usd_max` 0, `run_id` `e12_dev_v3_20260922T030255Z`. Its `actual_prior_release_reference`, `actual_server_pid` and `actual_execution_start_utc` are all **null** |
| [results/receiver_diff_v31_20260922T071000Z.json](../results/receiver_diff_v31_20260922T071000Z.json) (tracked) | `6cbc0d0b68ae0b55520e2daf908b9b2d3eafdf642479c2d977365b8b0372c5b4` | the passing pre-collection refreeze: 0 field differences, identical state hash, 42/42 identical rendered prompts |
| [results/receiver_preflight_v31_20260922T071000Z/](../results/receiver_preflight_v31_20260922T071000Z) (tracked) | per-file | `props_before/after`, `slots_before/after`, `models.json`, `rendered/`, `summary.json` from the non-generating checks |

**EXISTS — the earlier 04:35 attempt (no E12 data came from it):**

| Artifact | sha256 | What it evidences |
|---|---|---|
| results/e12_receiver_v31_20260922T043512Z/launch.json (tracked) | `3ca84f1f2dd4c48ffd21171bfc9f3b015850da1aaceed1fe7feddbd5a08d32f9` | `pid` 8458; `started_utc` 04:35:13.456780+00:00; `ready_utc` **null** with `ready_seconds` 600.2079093744978; `stopped_utc` 04:46:01.466225+00:00; `exited` **null**; `generation_requests` 0; a `post_hoc_note` stating the server was actually listening ~1 s after start, that the launcher's readiness strings never occur in this build, and that no preflight, diff, refreeze or receiver request followed |
| results/e12_receiver_v31_20260922T043512Z/llama_server_log_archive.txt (**tracked at git HEAD** — this is the committed archived-log text artifact) | `d3620da69140de0910b2d12b851e1d20a78e7bc478e35a9e06c3509cf4be892f` | byte-identical to that run's `llama_server.log` (same digest). Ends `10.47.961.652 I srv operator(): operator(): cleaning up before exit...`, consistent with the 04:46:01 stop |

**UNAVAILABLE — marked explicitly, not reconstructed:**

1. **A completed-exit receipt for either run.** `exited` is **null** in both `launch.json` records. There is no exit
   status, return code, wait-result or post-stop process-table observation anywhere on disk. What is evidenced is that a
   stop was **issued and recorded at 07:15:30.254657** and that the server logged `cleaning up before exit...`; what is
   **not** evidenced is that the process finished exiting, when it finished, or with what status. The lead states the
   same limit: the lead "verifies that report and timestamp, not a completed-exit receipt or current host availability".
2. ~~**A committed archive of the 07:10 run's server log.**~~ **RESOLVED by the parent in this same bundle**
   (commit `77add2d`): the 129,491-byte log is now committed as
   [results/e12_receiver_v31_20260922T071000Z/llama_server_log_archive.txt](../results/e12_receiver_v31_20260922T071000Z/llama_server_log_archive.txt),
   byte-identical to the on-disk log (`a4cafa751392a75a6c43235945b4bd5b98dff21c46e8267b0fb7e2129ea2e893`), with
   [results/e12_receiver_exit_evidence_20260923.json](../results/e12_receiver_exit_evidence_20260923.json) recording
   what it does and does not evidence. It was copied, never regenerated, and contains no assertion or candidate text
   (0 occurrences of `assert`, no request or response bodies). It adds two facts: its 154 `prompt eval time` lines
   corroborate the 154 recorded receiver calls from the server's own side, and its final line places shutdown
   initiation at 07:15:30.232615, **22.0 ms before** the recorded `stopped_utc`. Item 1 above still stands: a
   completed-exit receipt does not exist.

3. **An ownership-release artifact.** No file records the release of the 07:10:00Z-08:20:00Z window back to the peer.
   The ownership record's `actual_prior_release_reference`, `actual_server_pid` and `actual_execution_start_utc` are
   null; the peer's `slot_agreement_20260922_0710.json` likewise records "actual DTR release and peer launch are not
   observed". The 04:46:01 stop of the earlier attempt carries a worker note saying "window released", but that concerns
   the superseded reservation `docs/e12_shared_window_20260922.json`, not the collection window.
4. **Independent A and C absolute phase boundaries and a final-report timestamp** in their own artifacts. Only the
   cumulative `wall_seconds` and phase durations are recorded. The lead records the same gap.
5. **A post-stop host-availability observation.** None exists; current host availability is therefore unevidenced, which
   is precisely why section 5 requires re-agreement at dispatch.

### 7(b) The final-public-compliance supplement — SEPARATELY LABELLED AND OPTIONAL

**This supplement is optional, separately labelled, and NOT part of the primary endpoint. It is not free.** The primary
comparable endpoint stays the frozen private-suite-plus-format score for all 60 artifacts.

What it would measure: whether each of the 60 **final** continuation answers satisfies the public example it was shown,
i.e. final public compliance — a quantity E12 never measured. The lead is explicit that E12's public/private cross-tab
"concerns initial answers only; final public compliance was not measured by this run"
([docs/e12_lead_judgment_20260923.md](e12_lead_judgment_20260923.md)).

Additional execution cost, over and above section 2's 79 starts:

| Line item | Additional starts | Additional time |
|---|---:|---:|
| Public-example execution of each of the 60 final artifacts | **60** | ~1.0 s estimated at E12's measured 0.01643 s/artifact; **cap 300 s** |
| Public-example control rechecks, 2 per root x 5 roots | **10** | inside the same 300 s cap |
| **Supplement total** | **70** | **+300 s**, raising the outer end-to-end limit to 3,000 s (50 minutes) if granted |

Conditions if it is granted: it runs **after** the primary grading is complete and published, it is reported under its own
label and never merged into the primary contrast, and it requires its own line in the enumerated allowance. It is **not a
retrospective replacement for E12's endpoint**: it cannot be applied to E12's artifacts to create a comparable historical
series, and a favourable supplement result cannot rescue or reinterpret E12's observed negative primary contrast. For
this narrow follow-up **no private assertion may change** — the private suites, the grader
(`landmark-grader-v5-parse-and-compile-fault-attribution`) and the format rule stay exactly as frozen.

#### The `mbpp/863` limitation

Root `mbpp/863` carries a defect the lead described and that must be stated wherever this root appears. Its initial
program **resets the run length at duplicate values, returning 2 for the public example whose correct answer is 3**. Its
**private suite nonetheless passes, because the two private cases lack duplicates**. Therefore, on this root,
**"private pass" is not program correctness**: the public diagnostic detected a real stated-domain defect that the private
endpoint cannot see ([docs/e12_lead_judgment_20260923.md](e12_lead_judgment_20260923.md), "Measurement and mechanism
corrections"). Relatedly, both E12 S1 continuations on 863 scored zero under the frozen multi-block extraction rule with
**zero candidate execution starts**, which is a formatting/extraction outcome and not demonstrated semantic damage on
private inputs.

**This limitation must be resolved before any broader policy study** — a private suite that cannot distinguish a correct
program from one that mishandles duplicates is not an adequate endpoint for a policy claim, and the fix is a private-case
addition, which is a change of measurement. **For this narrow follow-up, that fix is forbidden:** no private assertion
may change, `mbpp/863` stays in the roster exactly as frozen, and every 863 result in E13a is reported with this
limitation attached rather than read as evidence about program correctness.

---

## 8. What this document does and does not do

It specifies 60 receiver attempts, at most 30,720 reserved completion tokens, a 480 s collection cap against a ~128 s
estimate, a 300 s grading cap against a ~1.0 s estimate, a 2,700 s outer contiguous limit, 79 enumerated isolated
executor starts (60 grading + 10 control/recheck + 9 attestation payloads) with 0 public-check starts in the primary
stage, the full attestation-renewal procedure for an expired attestation and an expired window, every source binding and
its pin, the actual sibling-project host state with paths, a contingent 70-minute reservation proposal, and
integrity/resource-only stop rules.

It does **not** authorize any of it. No model, receiver, benchmark program, candidate answer or sandbox was executed to
write it; no E12 result and no frozen release package was modified; nothing was committed by its author. Execution stays
held pending the lead's separately enumerated budget and window.
