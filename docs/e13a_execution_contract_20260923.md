# E13a prospective execution contract — proposal, execution held

Revised by the coordinating review on 23 September 2026. This is a source-based proposal, **not execution authority**. No model, receiver, reference, candidate or sandbox execution, or live host-availability check, was performed for this revision. The [lead ruling](e12_lead_judgment_20260923.md) permits source/mock preparation only. Real execution requires a reviewed, bound implementation and a separately committed budget and shared-host window.

## 1. Scientific scope and implementation status

E13a compares the **diagnostic-plus-R1-instruction restart package** against bare task resampling (`FRESH`) at five fixed E12 public-fail checkpoints: `mbpp/842`, `mbpp/288`, `mbpp/863`, `mbpp/966`, and `mbpp/652`. Each arm receives six new continuations per checkpoint. R1 uses replicate indices 2–7; FRESH uses 0–5 with a distinct arm seed key. Preserve reviewed message bytes and verify that no new seed repeats an E12 seed on the same root. There is no new initial-answer or initial-diagnostic phase.

This is a development follow-up motivated after observing E12. It does not test the selected gated policy or isolate a diagnostic-only effect: R1 and FRESH differ in both diagnostic information and instruction. A tie is inconclusive. Keep E12 separate; do not pool, replace seeds, choose roots using new outcomes, stop for significance, or infer futility from six draws.

The primary comparable endpoint remains the **unchanged private-suite-plus-format score**. Preserve task text and private assertions. Do not select a favorable code block, change formatting instructions, or silently convert missing grades to zeros. Report all five root-specific contrasts and the equally weighted finite-checkpoint mean, failures, missingness and measured costs. No population inference or independent policy-validation claim follows.

**A real E13a collector and grader are not delivered.** [The dry-run script](../scripts/e13a_mock_dryrun.py) uses a canned receiver and stub executor; its outputs are fabricated transport checks, not measured outcomes. [The stage descriptor](../experiments/landmark/e13a_stage.json) is bookkeeping, not an allowlisted release. Existing E12 collector/grader commands cannot simply be reused for five roots and the new `FRESH` arm.

The frozen 14-root [E12 release](../experiments/landmark/dev_release_v3/release_manifest.json) has ceilings of 154 artifacts, 28 rechecks and 600 grading seconds. Smaller proposed counts neither authorize E13a nor make its root/arm/source contracts compatible. **A new reviewed adapter and release binding are required**, preserving the old package and all E12 artifacts. Binding unchanged assertions to a five-root stage may require a new subset/configuration digest; it does not permit changing their contents.

Exact real collection and grading commands, new release path, immutable outputs, failure ledger, runtime checks and source/configuration digests are **pending**. The real driver must bind every numerical grade to its collected output, assignment, manifest and measurement contract; standalone analyzer slot validation is insufficient. Review and commit the complete path before dispatch. The existing deterministic analysis interface is:

```text
python3 scripts/e13a_analyze.py --grades <run>/D/grades.jsonl --stage experiments/landmark/e13a_stage.json --out <run>/analysis_report.json
```

This is an interface reference, not an instruction to execute. Bind its inputs and source hash to the reviewed release too.

## 2. Proposed resource allowance

| Item | Maximum |
|---|---:|
| Receiver attempts | 60: 5 roots × 2 arms × 6 replicates |
| Reserved completion tokens | 30,720: 60 × 512 |
| Paid service spend | $0 |
| Candidate execution during collection | 0 |
| Private candidate starts | 60 |
| Reference/control rechecks | 10: one reference and one frozen wrong control per root |
| Containment-renewal starts | 9 |
| Primary-stage public-check starts | 0 |
| **Total isolated executor starts** | **At most 79** |

These are ceilings, not exact expected usage. Caching, missing output or rejection before execution can reduce actual candidate starts. Keep reference/control, containment, candidate and optional public-check costs separate. Passing a reference and rejecting one known-wrong control establish only those finite checks; they do not prove general discriminative reliability or program correctness.

The nine renewal starts correspond to `grade.REQUIRED_CHECKS`. Successful renewal requires all nine payloads to start and pass their respective checks. Record launch attempts separately from payload starts if renewal fails. No retry allowance is proposed.

The historical ledger is 333/412. Although `333 + 79 = 412`, unused E12 capacity is **not authority for another study**. The request plan's 70-start figure counts grading and rechecks only; this 79-start proposal includes renewal. A new allowance must enumerate all components explicitly.

| Segment | Proposed cap |
|---|---:|
| Renewal, receiver launch, preflight, snapshot comparison and refreeze | 600 seconds |
| Collection | 480 seconds |
| Private grading, including reference/control rechecks | 300 seconds |
| Analysis and deterministic final report | 300 seconds |
| Sum of segment caps | 1,680 seconds |
| **Contiguous outer limit** | **2,700 seconds / 45 minutes** |

The stage descriptor and real runner must use the same **300-second** grading cap; an older 240-second mock setting does not define a separate allowance. The outer clock begins with the first setup action and ends with the final report. Scheduling wait before the accepted window is recorded separately. Segment and outer limits apply independently; startup and renewal are included, not charged outside the allowance.

E12 measured 314.257961 seconds cumulatively for A+C: A took 16.654885 seconds for 14 calls and C took 297.603075 seconds for 140. Applying C's aggregate rate to 60 attempts gives approximately 128 seconds, a planning scenario rather than a conservative bound. E13a selects public-fail checkpoints and mixes initial-shaped FRESH requests with R1 requests, so latency and output-length distributions can differ.

**Per-call durations are available:** every A/C call records `seconds`; observed ranges were approximately 0.402–2.283 seconds in A and 0.392–12.186 in C. Their sums, 14.977224 and 295.594775 seconds, differ from phase wall time because phase overhead is separate. E12's 2.530702-second grading wall time reflects caching and pre-execution rejection; it is not a universal per-artifact execution rate. Private-grade output caching is distinct from receiver KV caching. `collect.py` sets `cache_prompt=False`; no receiver-cache speedup claim is supported by the private grading counts. The proposed caps provide headroom without claiming a demonstrated latency model.

Non-generating receiver metadata/template traffic is separately limited to **50 attempts**, at most 10 seconds each, no retries, inside setup. The fixture workflow uses 42 prompt renders plus metadata requests. Generation smoke calls are zero. Reserved tokens remain a ceiling regardless of forecasts of measured tokens.

## 3. Existing validation and expired runtime evidence

E12's accepted grading attestation is [the validation-bundle attestation](../results/validation_bundle_v2_20260921T201642Z/attestation/attestation.json), SHA256 `74389aa74c588bc4f295ff6d695ca0f4dad4caae721b480f00889e0cba1b9b94`. It was checked at **2026-09-21T20:17:03.055277Z**, passed nine checks with nine payload starts, and expired at **2026-09-22T20:17:03.055277Z** under the 24-hour rule. E12's D summary records this digest. The earlier September 21 12:56 attestation is not the latest accepted record. Both are expired; neither supports current grading. The September 22 07:10–08:20 shared-host window has elapsed too.

The existing 42 E12 validation starts remain historical evidence: 14 private references, 14 wrong controls and 14 public references. They are not fresh runtime containment checks or blanket validation of a new five-root/FRESH adapter. Reusing unchanged assertion content requires reviewed new source/configuration bindings, fresh containment and the proposed ten per-root reference/control checks. If preparation reveals additional execution checks are needed, enumerate them before release; do not hide them within or above the 79-start proposal.

## 4. Required preparation and startup order

All steps describe a prospective released run; none is authorized here.

1. **Finish and review the real adapter/release.** Bind the five-root/two-arm plan, source/configuration, root-balanced schedule, all 60 slots, missing/format rules, exact commands, immutable outputs and cumulative budgets. Dispatch must use public histories and diagnostics only. Private specifications belong to separate grading, and E12 private grades must not enter selection or requests. Inclusion probability is one; scheduling is not treatment assignment.
2. **Obtain an actual shared-host window.** Record peer acceptance and current ownership/resource checks. Do not infer availability from old releases, repository activity or a free port; do not stop another project's process. Respect the launcher timing requirement in section 6.
3. **Renew containment once.** Use `scripts/check_landmark_sandbox.py --runner landmark` with the intended grading interpreter and a new immutable output directory. `grade.verify_attestation` requires schema `landmark-containment-v1`, `passed: true`, the current checker hash, exactly nine distinct required checks with both `passed` and `payload_started` true, and age in `[0,86400]` seconds. Bind `sandbox_sha256`, `profile_sha256`, `python`, `python_sha256`, `host_sha256`, `platform` and `sandbox_kind`. Verify the actual resolved interpreter and host, not merely a virtual-environment path string. Keep the attestation current throughout grading.
4. **Verify and launch the receiver once.** Check all 26 build-file hashes and the model digest below. Use the reviewed committed launcher, loopback endpoint, pinned `LLAMA_MEDIA_MARKER` and unchanged backend. Record command, PID, host, start/ready times, memory observations and zero generation smoke calls. A failure stops setup without an implicit retry.
5. **Run preflight before snapshot comparison.** Use the committed MRL-10 seven-root fixture set, not E12/E13a roots. Save props, slots, models and 42 rendered prompts within 50 non-generating attempts. Then run `diff_receiver_snapshot_v31.py` against those saved outputs and the frozen snapshot. Require zero field differences, identical canonical state, 42 matching renders, empty validation errors and a passing result. Template equality does not imply output equality.
6. **Commit final bindings before collection.** Save renewed attestation, launch/ownership, preflight/diff and reviewed release/configuration bindings at one clean run HEAD. Commands must use these accepted bytes, not whichever revisions are present later. Changed source, prompt, seed, config or measurement bindings require review before use. No mid-batch pulls or silent repinning.
7. **Run only the bound stage, then release the owned receiver.** Preserve all assigned slots on partial completion. At completion or an integrity/resource stop, terminate only this project's process, record observed exit separately from the stop timestamp, and publish an explicit host-release artifact.

The receiver remains Qwen2.5-3B Q4_K_M, model SHA256 `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d`, four 8,192-token slots, and the recorded launch shape `-ngl 99 -np 4 -c 32768 --jinja`. Requests retain temperature 0.7, top_p 0.95 and num_predict 512; other sampler values and order remain pinned. Expected canonical state is `1b8bf998c5dd06a611f692bab9e802b285ae75164b8b389fd8b381c06a83f5c1`. Any unclassified receiver-law difference holds collection.

## 5. Verified source pins and pending release bindings

These are inspected current bytes, not permission to adopt later HEAD contents without reviewing changes.

| Input | Verified SHA256 |
|---|---|
| [Request plan](../results/e13a_request_plan_20260922.json) | `f16d9c1086b30273975421c6b6b805082a77dcb2083570c547e758e23e3398f7` |
| [Plan builder](../scripts/build_e13a_request_plan.py) | `4795b053278e84de31ac45f31b78c6bdcd6dcb46aa6f883d48f3470c173397d5` |
| E12 `A/roots.jsonl` | `5e26bafac75a07b5bd35df01131533d36ba233b5b6eb8802bdf0e9ae9b851947` |
| E12 `B/diagnostics.json` | `e95d50bae632f73a96094673a03aff9401993c5c3d986086f63c5fe3cf8bd94a` |
| E12 `C/calls.jsonl` | `3de109d968098151970a889b4ce8d1b0151413bcdbfc8de566cbb358d0d9223f` |
| [Build manifest](../experiments/env/llama_server_manifest.json) | `63d8e03bcea39031e4d5d4334ccf58e09159a4304f609f2bd320f4538922c2b8` |
| [Receiver snapshot](../results/receiver_props_snapshot_8193.json) | `c0b3aaf2fd07f7aa259041eeb30abd588e6f07362295786c4e43a580b76b619e` |
| [Launcher](../scripts/launch_own_receiver_v31.py) | `03bede1d1de39f376daadcec79c81b2edea9c2c0b56e8e03bb019c321d4a16b5` |
| [Preflight](../scripts/receiver_preflight_mrl10.py) | `15ac29ed1981f44dafbb94ae222d27513c07a638b2cd9b963a6b30b16ace13eb` |
| [Snapshot diff](../scripts/diff_receiver_snapshot_v31.py) | `923871d9f000e75428ddb98099ffb2c9a7fd5b04396b653dea9c74f7f6ddc958` |

The E12 paths are under `results/e12_dev_v3_20260922T030255Z/` and remain bound by its unchanged `ARTIFACT_SHA256SUMS.json`. The existing [14-root release manifest](../experiments/landmark/dev_release_v3/release_manifest.json), digest `c9d591ffd4a524992ced28c1cc2f68fc5c299cc14ad8022e587eefc5bb67d3ea`, is provenance for unchanged task/assertion content, **not** the E13a execution release.

The new manifest must also pin the real collector/grader, stage descriptor, analyzer, selected task/specification bindings, extraction/integrity/sandbox code, renewed attestation, actual receiver/ownership records, requests and output paths. Explain and review changed digests; no `UNRESOLVED` or untracked binding may reach dispatch. Retain substantive v5 parse/compile-fault attribution and format rules, with resource faults and unavailable execution recorded as missing.

## 6. Window, partial completion and stopping

The earlier **September 24 07:10–08:20 placeholder is withdrawn**. It was never reserved; no scientific or operational requirement forces a wait until that date/time. Prefer the **earliest mutually accepted sufficient window after the real source package is ready**. This document establishes no current host availability or reservation.

The pinned launcher's `ready_deadline` requires launch before the window end minus 60 minutes; its ready deadline is also bounded by that point. This constrains launch/readiness, not necessarily the first generation after an earlier successful readiness check. A nominal 45-minute study allowance therefore does not make a 45-minute reservation usable. Choose a sufficient accepted window and setup/launch cutoff leaving that margin, or separately review a launcher change before use. A 70-minute shape may be convenient, but is neither a reservation nor an exemption from the cutoff. The real driver must persist one shared 2,700-second outer deadline across phases; it and the agreed host hard end both remain binding.

Stops are for integrity/resource failures, never interim grades: mismatched source/model/request/seed, failed receiver diff or containment, expired attestation, invalid release binding, ownership conflict, exhausted time/attempt/token/start budgets, forbidden host contention or paid spend above $0. Reaching the last allowed slot completes that budget; dispatch no further attempt.

On interruption, preserve immutable partial call/execution/cost ledgers and all **60 assigned slots**. Distinguish unattempted, unavailable, format-failing and executed outcomes. A stage can finish partially under its caps; do not claim all 60 calls or 70 private starts necessarily occurred. Do not replace missing slots, retry, substitute roots/seeds or reset the budget without a separately reviewed plan. Publish the precise failure and release evidence; retain failed-attempt and setup costs.

## 7. What E12's retained operational evidence establishes

A **pre-A ownership record exists**: [dev_release_v3/ownership.agreed.json](../experiments/landmark/dev_release_v3/ownership.agreed.json), SHA256 `7331d8f6920c2374a0284a4ad76269f6a18b803b039707ef7886c503a8c35ecd`. It records PID 35499, server start, the accepted September 22 07:10–08:20 window, agreement references and recording time 07:10:04Z. Null placeholders in the earlier `docs/e12_shared_window_20260922T071000Z.json` proposal do not negate this later record. **Pre-A ownership differs from a post-run release receipt.**

The [archived server log](../results/e12_receiver_v31_20260922T071000Z/llama_server_log_archive.txt), SHA256 `a4cafa751392a75a6c43235945b4bd5b98dff21c46e8267b0fb7e2129ea2e893`, has 129,491 bytes and 1,121 lines. Its 154 prompt-evaluation timing records have distinct task IDs, corroborating the saved calls. The worker reports a retained byte-for-byte copy; independent local review verifies the committed archive/digest, while the original ignored `.log` is absent from that review checkout.

The final line records shutdown initiation at relative offset 5:28.059208. Adding it to `launch.json.started_utc` gives 07:15:30.232615Z, approximately consistent with recorded stop 07:15:30.254657Z. **This is clock-alignment arithmetic, not independently observed exact shutdown UTC or a verified 22-millisecond interval:** the launcher records UTC before `Popen`, and equivalence to the server log's time origin is unestablished. Read the [additive exit record](../results/e12_receiver_exit_evidence_20260923.json) with this limitation.

`launch.json.exited` remains null. Shutdown initiation and pre-A ownership supply no completed-exit status, post-run peer-release receipt or current host-availability observation. Independent absolute A/C boundaries and a final-report timestamp are absent from those phase artifacts too. Preserve the worker's reported release separately; do not reconstruct missing receipts.

The [MRL-17 annotation](../results/e12_mechanism_exploratory_mrl17_20260922.annotation.json) correctly identifies the metadata error. The original report remains byte-identical, SHA256 `1561bbc7a9b7670916416e7cbbf872386db8b2996748d65e0b834a35cba66a69`; its three input hashes identify E12 with 14 roots and 140 continuation descriptions. Generator fixes apply to future reports only.

## 8. Optional final-public-compliance supplement and root 863

The primary stage performs no new public checks: gating uses frozen initial public diagnostics only. A separately granted supplement could check final public compliance for all 60 continuations after preserving the primary grades/report:

| Supplement item | Additional maximum |
|---|---:|
| Final-artifact public-check starts | 60 |
| Public reference/control rechecks | 10 |
| Total additional starts | 70 |
| Additional time cap | 300 seconds |
| Outer limit if separately granted | 3,000 seconds / 50 minutes |

Together these require **at most 149 starts**, not 79. Bind the public path, controls, missingness and accounting before release; nothing is authorized here. Keep the supplement separately labelled and outside the primary contrast. It is not retrospective E12 regrading and cannot rescue E12's observed negative primary result.

On `mbpp/863`, E12's initial program mishandles duplicates: the public case returns 2 instead of 3, while two private cases lack duplicates and pass. Private-suite pass is therefore not program correctness. Both S1 outputs were rejected before execution for multiple code blocks; these are frozen format failures, not demonstrated semantic damage after successful public correction.

Attach this limitation to every E13a result for 863. Preserve its assertions and roster membership for this narrow comparison. Before broader policy evaluation, freeze and validate a stronger measurement contract that detects duplicate-handling errors and distinguishes public compliance from private generalization. Independently chosen additional private cases are one possible repair; they change measurement and cannot silently replace the old endpoint.

**Disposition:** source/mock preparation delivered; real adapter/release, exact execution commands, renewed runtime evidence and an accepted current window remain pending. These proposed totals and scope are concrete review inputs, not execution permission.
