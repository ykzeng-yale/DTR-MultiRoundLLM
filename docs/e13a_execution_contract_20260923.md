# E13a prospective execution contract — proposal, execution held

Revised by the coordinating review on 23 September 2026. This is a source-based proposal, **not execution authority**. No model, receiver, reference, candidate or sandbox execution, or live host-availability check, was performed for this revision. The [lead ruling](e12_lead_judgment_20260923.md) permits source/mock preparation only. Real execution requires a reviewed, bound implementation and a separately committed budget and shared-host window.

**Revision 2 (MRL-19 source completion, 23 September 2026).** All corrections of the lead's revision 1 (commit `cb1536a`) are preserved: attestation provenance in section 3, preflight **before** snapshot diff in section 4, the 300-second grading cap, the pre-A ownership record in section 7, and the withdrawal of the September 24 placeholder. Revision 2 adds, under [MRL-19 item 3](mrl18_review_mrl19_20260923.md): the single normative cap table (section 2), the one persisted stage clock shared by every phase (section 2.1), exact runnable command lines with their pins and an explicit dependency list for what does not exist yet (section 5.1), the readiness/window rules with the **verified current** peer host state (section 6), and the separately costed final-public supplement (section 8). Nothing added here releases a start: every number below is a ceiling inside a proposal, and the binding dependency remains the executable path, not owner permission (section 9).

## 1. Scientific scope and implementation status

E13a compares the **diagnostic-plus-R1-instruction restart package** against bare task resampling (`FRESH`) at five fixed E12 public-fail checkpoints: `mbpp/842`, `mbpp/288`, `mbpp/863`, `mbpp/966`, and `mbpp/652`. Each arm receives six new continuations per checkpoint. R1 uses replicate indices 2–7; FRESH uses 0–5 with a distinct arm seed key. Preserve reviewed message bytes and verify that no new seed repeats an E12 seed on the same root. There is no new initial-answer or initial-diagnostic phase.

This is a development follow-up motivated after observing E12. It does not test the selected gated policy or isolate a diagnostic-only effect: R1 and FRESH differ in both diagnostic information and instruction. A tie is inconclusive. Keep E12 separate; do not pool, replace seeds, choose roots using new outcomes, stop for significance, or infer futility from six draws.

The primary comparable endpoint remains the **unchanged private-suite-plus-format score**. Preserve task text and private assertions. Do not select a favorable code block, change formatting instructions, or silently convert missing grades to zeros. Report all five root-specific contrasts and the equally weighted finite-checkpoint mean, failures, missingness and measured costs. No population inference or independent policy-validation claim follows.

**A real E13a collector and grader now exist in source and have never been run.** [The dry-run script](../scripts/e13a_mock_dryrun.py) uses a canned receiver and stub executor; its outputs remain fabricated transport checks, not measured outcomes, and it is superseded as an execution story by [the real collection driver](../scripts/e13a_collect.py) and [the real grader/handoff validator](../scripts/e13a_grade.py), which are reviewed source with mock-injected tests only. [The stage descriptor](../experiments/landmark/e13a_stage.json) is still bookkeeping, not a release; the allowlisted release is now [`e13a_release/release_manifest.json`](../experiments/landmark/e13a_release/release_manifest.json). Existing E12 collector/grader commands still cannot be reused for five roots and the new `FRESH` arm, which is why those two scripts exist.

The frozen 14-root [E12 release](../experiments/landmark/dev_release_v3/release_manifest.json) has ceilings of 154 artifacts, 28 rechecks and 600 grading seconds. Smaller proposed counts neither authorize E13a nor make its root/arm/source contracts compatible. **A new reviewed adapter and release binding are required**, preserving the old package and all E12 artifacts. Binding unchanged assertions to a five-root stage may require a new subset/configuration digest; it does not permit changing their contents.

Exact real collection and grading commands are specified in section 5.1, against the delivered scripts and release (D1–D4 there); the agreed-window ownership record, the analysis-phase clock wiring and the release commit remain open (D5–D8). The real driver must bind every numerical grade to its collected output, assignment, manifest and measurement contract; standalone analyzer slot validation is insufficient. Review and commit the complete path before dispatch. The existing deterministic analysis interface is:

```text
.venv/bin/python scripts/e13a_analyze.py --grades <run>/grade/grades.jsonl --stage experiments/landmark/e13a_stage.json --out <run>/analysis_report.json
```

This is an interface reference, not an instruction to execute; section 5.1 step 7 is the operative form. The stage descriptor still spells this path `<run>/D/grades.jsonl`, an E12 shape the new grader does not write (dependency D7). Bind its inputs and source hash to the reviewed release too.

## 2. Proposed resource allowance — one normative cap table

Every cap for the primary E13a stage, in one place. Each row is a **maximum**, never a target or an expectation.

| # | Cap | Maximum | Derivation / enforcement point |
|---|---|---:|---|
| 1 | Receiver calls | **60** | 5 roots × 2 arms × 6 replicates; `results/e13a_request_plan_20260922.json` → `budget.receiver_calls`; dispatch accounting in `e13a_collect.py` |
| 2 | Reserved completion tokens | **30,720** | 60 × `max_tokens_per_call` 512 (`dev_release_v3/config.json`); a reservation ceiling, not a measured-token forecast |
| 3 | Candidate executions during collection | **0** | collection never grades; no executor is constructed in the collection phase |
| 4 | Private candidate grade starts | **60** | one per assigned slot; `release_manifest.grading_limits.artifact_starts` |
| 5 | Reference/control recheck starts | **10** | one frozen reference + one frozen wrong control per root × 5 roots; `grading_limits.recheck_starts` |
| 6 | Containment-renewal payload starts | **9** | `grade.REQUIRED_CHECKS` has exactly nine names; charged to setup, not to the grading ledger |
| 7 | Primary-stage public-check starts | **0** | gating uses frozen E12 public diagnostics only (section 8 supplement is separate) |
| 8 | **Total isolated executor starts** | **At most 79** | 60 (#4) + 10 (#5) + 9 (#6) |
| 9 | Setup: renewal, launch, preflight, snapshot diff, refreeze | **600 s** | `StageClock` phase `setup`; also the accepted E12 `setup_max_seconds` |
| 10 | Collection | **480 s** | `StageClock` phase `collection` |
| 11 | Private grading, including the 10 rechecks | **300 s** | `StageClock` phase `grading`; `grading_limits.grading_seconds`; `study_adapter.MAX_GRADING_SECONDS` is 600, so 300 is strictly inside the existing guard |
| 12 | Analysis and deterministic final report | **300 s** | `StageClock` phase `analysis` |
| 13 | Sum of the four segment caps | 1,680 s | arithmetic only; **not** the operative limit |
| 14 | **Contiguous outer limit** | **2,700 s / 45 min** | one persisted deadline shared by all phases (section 2.1) |
| 15 | Non-generating receiver metadata/template attempts | **50**, ≤10 s each | inside setup; 42 prompt renders plus props/slots/models; no retries |
| 16 | Generation smoke calls | **0** | launch records `generation_requests: 0` |
| 17 | Paid service spend | **$0** | no paid endpoint is configured or permitted |

Row 8 is **explicitly a maximum, not an expected count**. Private-grade output caching, an absent artifact, or format rejection before execution can each reduce the actual number of starts *without* dropping any assigned grade: a slot whose grade is decided without an execution is still a completed assigned slot, and a slot with no available grade is recorded `missing`, never zero-filled. E12's 2.530702-second grading wall time is the concrete precedent for that reduction. Keep reference/control, containment, candidate and optional public-check starts in separate counters; never net them against each other.

The nine renewal starts correspond one-to-one to `grade.REQUIRED_CHECKS` = {`own_run_read_write`, `home_read`, `home_write`, `peer_run_read`, `outside_home_tmp_write`, `loopback_network`, `system_subprocess`, `fork_creation`, `timeout_and_process_cleanup`}. Successful renewal requires all nine to start *and* pass (`grade.verify_attestation` demands `passed` and `payload_started` both true on exactly nine distinct names). Record launch attempts separately from payload starts if renewal fails. No retry allowance is proposed.

Passing a reference and rejecting one known-wrong control establish only those finite checks; they do not prove general discriminative reliability or program correctness.

**Start-accounting reconciliation, so 70 and 79 are never confused.** Three files carry a start figure and they mean different things:

| Source | Figure | Counts |
|---|---:|---|
| `results/e13a_request_plan_20260922.json` → `budget.isolated_starts` | 70 | grading-ledger starts only: 60 candidate + 10 reference/control |
| `experiments/landmark/e13a_stage.json` → `grading_limits.max_private_starts` | 70 | same grading-ledger scope (stage bookkeeping, no containment field) |
| `experiments/landmark/e13a_release/release_manifest.json` → `grading_limits` | **79** | `{n_roots 5, artifact_starts 60, recheck_starts 10, containment_starts 9, max_private_starts 79, grading_seconds 300}` — the full isolated-start budget of cap row 8 |

`study_adapter.load_grading_limits` was extended **additively** for E13a, not relaxed: it still requires every key of `GRADING_LIMIT_KEYS` = `{n_roots, artifact_starts, recheck_starts, max_private_starts, grading_seconds}`, allows at most the one optional key `OPTIONAL_GRADING_LIMIT_KEYS` = `{containment_starts}`, requires every value to be an `int`, and now enforces `max_private_starts == artifact_starts + recheck_starts + containment_starts` with `containment_starts` defaulting to 0 — so the v3 rule (`70 == 60 + 10`, `182 == 154 + 28`) is unchanged for every existing release, and the 200-start ceiling `MAX_PRIVATE_STARTS` and the 600-second `MAX_GRADING_SECONDS` still bind. `79 == 60 + 10 + 9` is therefore checked arithmetic, not a waiver. The stage descriptor's 70 remains correct for its own narrower scope; whoever next revises it should say so in `limits_note` rather than raise it to 79 and double-count the containment payloads against grading.

The historical ledger is 333/412. Although `333 + 79 = 412`, unused E12 capacity is **not authority for another study**; the request plan's own `budget.ledger_note` says the same. A new allowance must enumerate all components explicitly, which rows 1–17 now do.

The stage descriptor and real runner must use the same **300-second** grading cap; the older 240-second `study_adapter.DEFAULT_GRADING_SECONDS` v2 fallback does not define a separate allowance, and it only applies to a manifest with no `grading_limits` block at all. The outer clock begins with the first setup action and ends with the final report. Scheduling wait before the accepted window is recorded separately. Segment and outer limits apply independently; startup and renewal are included, not charged outside the allowance.

### 2.1 One persisted stage start and deadline, shared by every phase

There is exactly **one** stage start instant and **one** outer deadline for E13a, and every phase reads them from the same file.

- **Owner.** [`scripts/e13a_stage_clock.py`](../scripts/e13a_stage_clock.py) — `class StageClock` with `from_start(start_utc, caps)`, `persist(path)`, `load(path)`, `remaining(phase)` and `check(phase)`, which raises `CapExhausted`.
- **Location.** `<run>/stage_clock.json`, inside the run directory, written once by the first command (setup) and **reloaded, never re-created**, by collection, grading and analysis.
- **Caps it carries.** setup 600 s, collection 480 s, grading 300 s, analysis 300 s, and the outer total 2,700 s (table rows 9–12, 14).
- **Two independent tests per phase.** `check(phase)` fails if either the phase's own segment cap or the shared outer deadline is exhausted. The outer deadline is computed once as `start_utc + 2700 s` and stored; it is never recomputed from "now".

**Separate commands must not reset the outer cap.** This is what makes a four-command stage honest, because each command is a fresh process with a fresh `datetime.now()`. Enforcement:

1. The first command creates `stage_clock.json` with `open(path, "x")` semantics — an existing file is a refusal, not an overwrite, matching the repo-wide refuse-to-overwrite rule.
2. Every later command **must** be given the existing `<run>/stage_clock.json` and calls `StageClock.load`, which takes `start_utc` and the stored deadline from the file rather than from the current clock.
3. A command that finds no clock file refuses rather than starting a new stage; a command whose run directory carries a clock whose `deadline_utc` has passed refuses with `CapExhausted` before dispatching anything.
4. The persisted record binds the run id and the stage-descriptor hash, so a clock cannot be carried from one run directory into another to buy time.
5. Elapsed time is charged from the persisted `start_utc` even across a crash, an operator pause or a re-invocation: there is no "resume with a fresh budget" path, and none is proposed.
6. Consumed per-phase seconds are written back so that a second invocation of the *same* phase continues from the seconds already spent instead of restarting that segment.

The agreed host hard end (section 6) is a **second, independent** limit. Neither bound relaxes the other: collection stops at whichever of the two comes first.

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
3. **Renew containment once.** Use `scripts/check_landmark_sandbox.py --runner landmark --output <run>/attestation/attestation.json` (section 5.1 step 1: `--runner` and `--output` are the script's only flags) with the intended grading interpreter and a new immutable output directory. `grade.verify_attestation` requires schema `landmark-containment-v1`, `passed: true`, the current checker hash, exactly nine distinct required checks with both `passed` and `payload_started` true, and age in `[0,86400]` seconds. Bind `sandbox_sha256`, `profile_sha256`, `python`, `python_sha256`, `host_sha256`, `platform` and `sandbox_kind`. Verify the actual resolved interpreter and host, not merely a virtual-environment path string. Keep the attestation current throughout grading.
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
| [Stage descriptor](../experiments/landmark/e13a_stage.json) | `53a3bddc8fe07bba53b03287ed1f29df3928db6f0f2c0e685766a8df8df9624c` |
| [Repaired analyzer](../scripts/e13a_analyze.py) | `7d969d642fcc7222bd6fa110d09b6ea7cc3c55d87400aec9fd3a39dc50ea2699` |
| [Receiver adapter](../experiments/landmark/collect.py) | `49c94c45f856115925cf20560f0c43ba14348a859a041bc14ad9fd1431e7a83f` |
| [E12 phased collector](../experiments/landmark/collect_diagnostic.py) | `7d7eb0a6641c73b87c0ad1c20a5438b9f251653aed95e47dbb034c6498c6eb79` |
| [Grader v5](../experiments/landmark/grade.py) | `fb1c470fffe988353b36aa1cecc4fa96fa401f929e0182e5f4ae01e995559c4f` |
| [Study adapter](../experiments/landmark/study_adapter.py) | `20ccc6e785d33d4595aa0de393707bed1dc0a88dc23be58efe73391a8da8c0ce` |
| [Arm renderer](../experiments/landmark/diagnostic.py) | `2a98bccf20cf3fa068790b488be8df4347387ae5ffb1bd7b1bd8b9d49d3a72b2` |
| [Public gate function](../experiments/landmark/analyze_diagnostic.py) | `dca7f904b27d615e3f41d2b40e840ccbd0a9d4b88a46a0448a7eb139d5af720a` |
| [Containment checker](../scripts/check_landmark_sandbox.py) | `8683429158451a82662f618e65b73b3d13c87e4c8e9ca709f1bf61cc0e17f83b` |
| MRL-10 preflight fixture `dev_release_v2/tasks.jsonl` (7 roots) | `5eda138d6e71c9fb709134e8ad64b259e2a9047cee2029b65b309981bf307372` |
| [Preflight public fixtures](public_diagnostic_examples_v1.json) | `bf8cf8ed2cc20608d99d782622d9100e319502d57f044a0f0d7dbebd14dfa703` |
| E12 accepted attestation (**expired**, provenance only) | `74389aa74c588bc4f295ff6d695ca0f4dad4caae721b480f00889e0cba1b9b94` |
| [E13a release manifest, committed 77a780e](../experiments/landmark/e13a_release/release_manifest.json) | `702ef40054fbea772851454300b02de0fa5a2d7728d3057955cba600565f6638` |

The E12 paths are under `results/e12_dev_v3_20260922T030255Z/` and remain bound by its unchanged `ARTIFACT_SHA256SUMS.json`. The existing [14-root release manifest](../experiments/landmark/dev_release_v3/release_manifest.json), digest `c9d591ffd4a524992ced28c1cc2f68fc5c299cc14ad8022e587eefc5bb67d3ea`, is provenance for unchanged task/assertion content, **not** the E13a execution release.

The new manifest must also pin the real collector/grader, stage descriptor, analyzer, selected task/specification bindings, extraction/integrity/sandbox code, renewed attestation, actual receiver/ownership records, requests and output paths. Explain and review changed digests; no `UNRESOLVED` or untracked binding may reach dispatch. Retain substantive v5 parse/compile-fault attribution and format rules, with resource faults and unavailable execution recorded as missing.

`study_adapter.verify_committed_release` accepts a manifest only at an **allowlisted relative path** (`COMMITTED_RELEASE_MANIFESTS`, now `dev_release_v2`, `dev_release_v3` and `e13a_release`) that is tracked at `git HEAD` *and* byte-identical to its HEAD blob. The new `experiments/landmark/e13a_release/release_manifest.json` entry therefore gets **exactly the same** strict check through the same code path, with no new looser branch; and until the parent has committed the release, every grading command refuses by construction. That refusal is the intended behaviour, not an obstacle to route around.

**Not yet frozen: the three in-flight drivers.** These are working-tree files at this revision (`git status`: untracked), so this document deliberately records **no digest** for them. Pinning an uncommitted digest would be a number that decays the moment the file is touched; section 4 step 6 is where they get bound, at one clean run HEAD, together with the renewed attestation and the launch/ownership and preflight/diff records.

| Path | Role | Commit state at this revision |
|---|---|---|
| `scripts/e13a_stage_clock.py` | the one shared clock (section 2.1) | untracked working tree |
| `scripts/e13a_collect.py` | real two-arm collection driver (step 5) | untracked working tree |
| `scripts/e13a_grade.py` | handoff validation + private grading (step 6) | untracked working tree |

The E13a release bindings and the additive `study_adapter` limit/allowlist change are committed at `77a780e`, so their digests above are stable.

### 5.1 Exact runnable command lines

All commands below are written for review, **not for execution**. They assume `RUN=work/e13a_dev_<UTC timestamp>Z` (a new, non-existent directory; `results/` stays immutable until a completed run is published) and the same-HEAD guard E12 used: `FREEZE=$(git rev-parse HEAD)` before step 0, re-tested before every later step, with no pulls mid-batch. Interpreter is `/Users/yukangzengcmac/DTR-MultiRoundLLM/.venv/bin/python` throughout. Every flag below was read off the committed script that accepts it; anything still absent is listed in the dependency table at the end of this section rather than invented here.

**Step 0 — create the one stage clock (starts the outer 2,700 s).**

```bash
.venv/bin/python scripts/e13a_stage_clock.py --run-dir "$RUN" --init
# later, read-only, from any phase:
.venv/bin/python scripts/e13a_stage_clock.py --run-dir "$RUN" --phase collection
```

`--init` refuses an existing clock ("Refusing to re-anchor an existing stage clock"), and a phase query without `--init` refuses when no clock exists. `--start-utc` exists for a reviewed explicit anchor; the caps are the module's `PHASE_CAPS`, not command-line input, so no invocation can widen them.

**Step 1 — attestation renewal (9 of the 79 starts; setup segment).**

```bash
.venv/bin/python scripts/check_landmark_sandbox.py --runner landmark \
  --output "$RUN/attestation/attestation.json"
```

`--runner` and `--output` are the script's real flags. `grade.verify_attestation` then requires schema `landmark-containment-v1`, `passed: true`, the current checker hash, exactly the nine `REQUIRED_CHECKS` names with both `passed` and `payload_started` true, and age in `[0, 86400]` s. Renew with the interpreter that will actually grade, and verify the resolved interpreter and host, not a virtual-environment path string.

**Step 2 — verify and launch the receiver once.**

```bash
.venv/bin/python scripts/launch_own_receiver_v31.py \
  --ownership experiments/landmark/e13a_release/ownership.agreed.json \
  --out "results/e13a_receiver_v31_<UTC>Z"
```

Model `qwen2.5-3b-instruct-q4_k_m.gguf`, digest `626b4a66…15c62d`; server build `b1-4fea119`; 26 build-file hashes from `experiments/env/llama_server_manifest.json` (`63d8e03b…922c2b8`); launcher `03bede1d…4d16b5`; launch shape `-ngl 99 -np 4 -c 32768 --jinja`; `generation_requests` must record 0. The ownership file is **(D5)**: a new agreed-window record in the E13a release, in the schema `ready_deadline` already accepts (`start_utc` / `hard_end_utc`, or the `exclusive_window_*` pair — mixing the two with different values is refused as "Conflicting ownership windows").

**Step 3 — preflight, BEFORE the snapshot diff** (the launcher's real order; template equality does not imply output equality).

```bash
.venv/bin/python scripts/receiver_preflight_mrl10.py \
  --tasks experiments/landmark/dev_release_v2/tasks.jsonl \
  --examples docs/public_diagnostic_examples_v1.json \
  --base-url http://127.0.0.1:8193 \
  --out "$RUN/preflight"
```

Seven committed MRL-10 fixture roots (`5eda138d…f307372`), **not** E12/E13a roots; public fixtures `bf8cf8ed…14dfa703`; 42 rendered prompts plus props/slots/models inside the 50 non-generating attempts of cap row 15; zero generation.

**Step 4 — snapshot diff, after preflight.**

```bash
.venv/bin/python scripts/diff_receiver_snapshot_v31.py \
  --new-preflight "$RUN/preflight" \
  --out "$RUN/receiver_diff.json"
```

The frozen side is hardcoded to `results/receiver_props_snapshot_8193.json` (`c0b3aaf2…b76b619e`). Require `n_field_differences: 0`, `state_identical: true`, canonical state `1b8bf998c5dd06a611f692bab9e802b285ae75164b8b389fd8b381c06a83f5c1` on both sides, `rendered_prompts_compared: 42` with `rendered_prompts_identical` true, empty `validation_errors`, `passed: true`. Any unclassified receiver-law difference holds collection.

**Step 5 — collection (60 calls, 480 s, 0 executions).**

```bash
# dry structural check first: verifies the 60 requests and dispatches nothing
.venv/bin/python scripts/e13a_collect.py --out "$RUN" --rebuild-only

.venv/bin/python scripts/e13a_collect.py --real \
  --out "$RUN" \
  --stage experiments/landmark/e13a_stage.json \
  --plan results/e13a_request_plan_20260922.json \
  --release-dir experiments/landmark/e13a_release \
  --ownership experiments/landmark/e13a_release/ownership.agreed.json
```

The stage and plan default to the pinned paths; their digests are recorded by the driver rather than passed as flags, and the shared clock is found at `$RUN/stage_clock.json` (`e13a_stage_clock.CLOCK_FILE`) rather than by flag, so a phase cannot be pointed at a different clock. `--real` builds the receiver through the same path E12 uses (`collect.LlamaServer`, `verify_freeze`, `validate_ownership`, receiver law/slot guards, interim and postflight drift). No `--adapter` exists in real mode: an injected adapter is test-only and its run is labelled transport-only. Decoding stays temperature 0.7, top_p 0.95, `num_ctx` 8192, `num_predict` 512, `cache_prompt=False`, seeds exactly as the plan records them. Outputs `$RUN/collect/{calls.jsonl,manifest.json,completion.json,artifacts/*.txt}` with a durable attempt ledger and all 60 assigned slots present.

**Step 6 — controls plus private grading (60 + 10 starts, 300 s).**

```bash
# handoff validation alone, writing nothing:
.venv/bin/python scripts/e13a_grade.py --collect "$RUN/collect" --out "$RUN" --validate-only

.venv/bin/python scripts/e13a_grade.py --real \
  --collect "$RUN/collect" \
  --release experiments/landmark/e13a_release \
  --stage experiments/landmark/e13a_stage.json \
  --attestation "$RUN/attestation/attestation.json" \
  --out "$RUN"
```

`--plan` defaults to the plan the collection itself pinned, which is stronger than re-passing it by hand. Evaluator pins: grader `landmark-grader-v5-parse-and-compile-fault-attribution`, endpoint contract `landmark-private-tests-v1`, diagnostic schema `public-diagnostic-v2`. Release manifest caps read through `study_adapter.load_grading_limits`: `n_roots 5`, `artifact_starts 60`, `recheck_starts 10`, `containment_starts 9`, `max_private_starts 79`, `grading_seconds 300` — the nine containment payloads being the ones already spent in step 1, so the ledger reaches the 79 of cap row 8 and stops. `validate_handoff` runs first: collection completion/manifest checksums, every artifact's bytes, each root/arm/replicate/output digest, and the frozen release/grading-contract pins. Writes `$RUN/grade/{grades.jsonl,grading_attempts.jsonl,summary.json}`. E13a has **no** initial/continue phase pair, so `study_adapter grade --initial-dir/--continue-dir` (E12's D command) is *not* reusable here; that mismatch is exactly why step 6 exists.

**Step 7 — repaired analysis (300 s, no execution).**

```bash
.venv/bin/python scripts/e13a_analyze.py \
  --grades "$RUN/grade/grades.jsonl" \
  --stage experiments/landmark/e13a_stage.json \
  --out "$RUN/analysis_report.json"
```

These three flags are the analyzer's real, verified interface (`--treatment-arm` / `--reference-arm` exist and stay unset, so the contrast comes from the descriptor: treatment `R1`, reference `FRESH`). The repaired behaviour must be consumed unchanged: **no primary point contrast if any assigned primary grade is missing**, finite all-assigned completion bounds `[s/a, (s+m)/a]` per cell, available-case summaries explicitly secondary, unknown usage reported as unknown and never zero-filled, and refusal on an unexpected or duplicate slot or an existing `--out`.

**Dependencies, stated as dependencies rather than invented flags.**

| ID | Item | Status at this revision |
|---|---|---|
| D1 | `scripts/e13a_stage_clock.py` (`StageClock`, `CapExhausted`, `CLOCK_FILE`, `PHASE_CAPS`, CLI `--run-dir/--init/--start-utc/--phase`) | **delivered this round**; flags above verified against the file |
| D2 | `experiments/landmark/e13a_release/` (`release_manifest.json`, `tasks.jsonl`, `private_specs.jsonl`, `config.json`, `public_examples_v3.json`, `controls_rationale.json`) and its `COMMITTED_RELEASE_MANIFESTS` entry | **delivered this round**; the allowlist entry gets the identical strict HEAD check |
| D3 | `scripts/e13a_collect.py` (`dispatch(stage, plan, out_dir, *, adapter=None, real=False, clock=None, ownership=None)`) | **delivered this round** |
| D4 | `scripts/e13a_grade.py` (`validate_handoff(...)` then `grade(collect_dir, release_dir, out_dir, *, executor=None, real=False, clock=None)`) | **delivered this round** |
| D5 | `experiments/landmark/e13a_release/ownership.agreed.json` — the agreed-window record step 2 requires | **still missing**; it cannot exist before a window is agreed (section 6), and it must not be fabricated to make the launcher pass |
| D6 | Analysis-phase clock enforcement: `scripts/e13a_analyze.py` has **no** `--clock` flag | **open**. Either the launch wrapper calls `StageClock.check("analysis")` immediately before and after the analyzer, or the analyzer gains the flag. Do not weaken any analyzer guard to add it |
| D7 | `e13a_stage.json` `exact_commands.analysis` names `<run>/D/grades.jsonl` while `e13a_grade.py` writes `<run>/grade/grades.jsonl`; `grading_limits.max_private_starts` there is 70, the release manifest's is 79 | **open**, for the descriptor's owner: reconcile the path string and record the scope difference in `limits_note`. Do not raise the stage figure to 79 without saying what it counts |
| D8 | Committing the release: `verify_committed_release` refuses a manifest that is untracked or differs from its `git HEAD` blob, so grading cannot run until the parent commits `e13a_release/` | **open by design**; this is the guard working, not a blocker to route around |

Steps 0, 3–7 are now runnable source; step 2 is blocked on D5 and therefore so is any real dispatch, and nothing at all is authorized to run. This section is a specification of what will be run under a future granted allowance.

## 6. Window, partial completion and stopping

The earlier **September 24 07:10–08:20 placeholder is withdrawn**. It was never a reservation; no scientific or operational requirement forces a wait until that date or time, and treating it as one would be a self-imposed delay with no counterparty. Prefer the **earliest feasible mutually agreed window after source readiness** — that is, after the delivered drivers D1–D4 of section 5.1 are reviewed and committed (D8). This document establishes no current host availability and no reservation.

**Readiness rule, separated from the collection and outer deadlines.** The pinned launcher's `ready_deadline` accepts either ownership schema (`start_utc`/`hard_end_utc`, or `exclusive_window_start_utc`/`exclusive_window_end_utc`) and refuses with "Outside launch window or less than 60 minutes remain for Phase A onward" unless setup/readiness completes by the **shared-window hard end minus 60 minutes**. That is a *launch-time* gate on setup only. The collection cap (480 s), the grading and analysis caps, and the single outer 2,700 s deadline of section 2.1 are enforced **separately and after** readiness, by `StageClock`. Consequently a nominal 45-minute study allowance does not make a 45-minute reservation usable: the window must be long enough that readiness lands 60 minutes before its hard end. A 70-minute shape is convenient for that arithmetic but is neither a reservation nor an exemption from the cutoff; a launcher change to relax the 60-minute margin would be a weakened guard and is not proposed.

**Verified current host state, as published, with paths.** Checked by reading files on 23 September 2026; no live host or peer check was performed.

| Source | What it actually says |
|---|---|
| [`docs/e12_shared_window_20260922T071000Z.json`](e12_shared_window_20260922T071000Z.json) | The most recent accepted window in this repository: start `2026-09-22T07:10:00Z`, hard end `2026-09-22T08:20:00Z`, Phase A latest start `2026-09-22T07:20:00Z`, `setup_max_seconds` 600, `startup_attempts_authorized` 1, `metadata_template_attempts_max` 50, `generation_smoke_calls` 0, `paid_usd_max` 0. **Elapsed.** |
| `/Users/yukangzengcmac/DTR-AgentEvals/results/v2_agent/slot_agreement_20260922_0710.json` | The peer's matching acceptance of that same 07:10–08:20 window, recorded `2026-09-22T05:22:28Z`. It is the peer's **newest** slot artifact; no later `slot_agreement_*` file exists in that repository. |
| `/Users/yukangzengcmac/DTR-AgentEvals/docs/theory_feedback_20260923_completed_pilots.md` | The peer lead's current position (23 September): DTR-REQ-004 is "completed for the two historical DTR blocks"; "The previous MultiRound reservation is expired"; "No new reservation or external scheduler installation is inferred"; before any later authorized host block, obtain **current** peer/ownership/resource evidence and publish actual start/release, without treating old reservations as current or stopping another project's jobs. A host release at 22 September 08:10:09 UTC is recorded as a worker report, not a host inspection. |

**True current state: there is no agreed E13a window anywhere — not on 23 September, not on 24 September, and no pending offer from either side.** The two September 22 records are spent, and the peer has explicitly published that the prior MultiRound reservation is expired. What is required is a *new* mutually agreed slot, sought **after** source readiness, with fresh ownership and resource evidence at that time. Absence of a window is therefore not a reason to delay source work, and the absent September 24 placeholder is not a reason to delay the request for a real one.

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
| Additional paid spend | $0 |
| Outer limit **if** separately granted | 3,000 seconds / 50 minutes |

**This supplement is explicitly NOT part of the primary allowance of section 2.** It is a separate proposal with its own separate cost, requiring its own separate decision. The primary stage's public-check starts remain **0** (cap row 7) whether or not the supplement is ever granted, and the primary caps of 60 calls / 79 starts / 2,700 s do not move. If both were granted, the totals would be **at most 149 starts** and 3,000 s — and that combined figure must be stated as such, never folded back into the 79 or presented as headroom inside it. Bind the public path, controls, missingness and accounting before any release; nothing is authorized here. Keep the supplement separately labelled and outside the primary contrast. It is not retrospective E12 regrading and cannot rescue E12's observed negative primary result.

On `mbpp/863`, E12's initial program mishandles duplicates: the public case returns 2 instead of 3, while two private cases lack duplicates and pass. Private-suite pass is therefore not program correctness. Both S1 outputs were rejected before execution for multiple code blocks; these are frozen format failures, not demonstrated semantic damage after successful public correction.

Attach this limitation to every E13a result for 863. Preserve its assertions and roster membership for this narrow comparison. Before broader policy evaluation, freeze and validate a stronger measurement contract that detects duplicate-handling errors and distinguishes public compliance from private generalization. Independently chosen additional private cases are one possible repair; they change measurement and cannot silently replace the old endpoint.

## 9. What this document does and does not release

Stated plainly, so no later reader can mistake a table of ceilings for an authorization:

1. **Nothing here releases a single start.** Not one of the 60 receiver calls, not one of the 79 isolated executor starts, not one of the nine containment payloads. Every number in section 2 is the maximum a *future* granted allowance would carry, and the stage descriptor still records `receiver_calls_authorized: 0` and `candidate_executions_authorized: 0`.
2. **Nothing here borrows the expired E12 allowance.** E12's accepted attestation (`74389aa7…1b9b94`) was checked at 2026-09-21T20:17:03.055277Z and expired 24 hours later at 2026-09-22T20:17:03.055277Z; its shared window elapsed at 2026-09-22T08:20:00Z. The 333/412 ledger arithmetic in section 2 is accounting, not carry-over capacity: `333 + 79 = 412` is a coincidence of ceilings, not a grant.
3. **The immediate dependency is the executable path, not owner permission.** The executable path now exists in source: the stage clock, the real collection driver, the real grader/handoff validator (D1, D3, D4, working tree) and the committed five-root release bindings (D2, `77a780e`), with mock-injected tests. What blocks dispatch is review and commit of those drivers (D8), the analysis-phase clock wiring (D6), the stage-descriptor reconciliation (D7) and only then an agreed window with its ownership record (D5). A host window and a resource decision are needed *after* that, and the lead has stated one bundled execution decision will follow the actual path, not a per-phase approval cycle.
4. **The supplement of section 8 is a separate proposal with a separate cost**, outside this primary allowance.
5. **No guard was weakened to produce this contract.** The start reconciliation in section 2 was resolved *around* `study_adapter.load_grading_limits`, not by relaxing it; the E13a release manifest inherits the identical `verify_committed_release` HEAD check; the launcher's 60-minute readiness margin, `MAX_PRIVATE_STARTS` 200, `MAX_GRADING_SECONDS` 600, the analyzer's missing-grade refusal and the repo-wide refuse-to-overwrite rule all stand unchanged.

**Disposition:** the source-complete contract is delivered and the real adapter/release exist as reviewed source (D1–D4); the open items are D5–D8 — an agreed window with its ownership record, analysis-phase clock wiring, the stage-descriptor reconciliation and the release commit — plus renewed runtime evidence at execution time. These totals and this scope are concrete review inputs, not execution permission.
