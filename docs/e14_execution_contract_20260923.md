# E14 execution contract: future commands, resource proposal, frozen limits

> **THIS DOCUMENT GRANTS NOTHING.** It is a source-only planning artifact written under
> MRL-23 item 3 (lead commit `be0507e`, [mrl22_review_mrl23_20260923.md](mrl22_review_mrl23_20260923.md)).
> **No instrument execution and no model collection is released.** Nothing here authorizes a
> receiver call, a candidate execution, a reference or negative-control execution, a public-check
> execution, a containment payload, a download, an installation or any paid service. Authority for
> E14 requires, cumulatively: (i) an independent review of the E14 measurement package,
> (ii) satisfaction of the actual operational gates in section 3 (fresh attestation, agreed shared-host
> window, peer non-contention, reproducible release verification), and (iii) an explicit later lead
> decision naming E14. A published command line is not permission to run it; a numerical allowance is
> a ceiling for a decision that has not been made.
>
> **Evidence class of this document: source/planning only.** It was produced by reading files. Zero
> model calls, zero tokens, zero candidate/reference/public-check/containment starts, $0. No reference
> or control program was executed — not even as a "quick correctness check". Every time estimate below
> is derived from *historical measured* runs and is labelled an estimate, never a bound.

Inputs read for this document, with recorded SHA256 where they are pinned inputs:

| Input | SHA256 / identity |
|---|---|
| `docs/e14_lead_measurement_spec_20260923.json` | pins `source_file_sha256 = ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`, `execution_authorized: false` |
| `work/sources/mbpp_full.jsonl` | `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` (verified, matches spec) |
| `work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl` | `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` (verified, identical bytes) |
| `results/frame_review_mrl15_20260922T021718Z/manifest.json` | contains the same source pin `ccf64cea…b92a9f` (verified) |
| `experiments/landmark/e13a_stage.json`, `experiments/landmark/e13a_release/` | E13a bindings, read-only precedent |
| `results/e13a_two_arm_20260923T061500Z/analysis_report.json` | measured E13a per-arm usage, read-only |
| `docs/e13a_execution_contract_20260923.md` | contract shape imitated here |

The lead JSON is a **scorer-only** document: `added_private_assertions`, `reference_version_requirement`,
`semantic_negative_control_requirement` and `second_negative_control_requirement` must never appear in a
prompt or any public field, and the file is never passed wholesale into a prompt. The public view of a
root is `public_contract` + original entry-point/signature metadata + original assertion index 0 only.

---

## 0. Dependency statement read this first: the E14 executables do not exist yet

Verified by directory listing at the time of writing: there is **no** `experiments/landmark/e14_release/`,
**no** `scripts/build_e14_release.py`, **no** `scripts/e14_collect.py`, `e14_grade.py`, `e14_analyze.py`,
`e14_stage_clock.py`, and **no** `experiments/landmark/e14_stage.json`. MRL-23 items 1 and 2 are to create
the package and the connected source/mock path; this document is item 3 and must not invent their
interfaces. Accordingly every command below is tagged:

* **EXISTS** the script and the flags shown are read out of the current source.
* **DEPENDENCY** the command is the interface the future E14 script **must** accept; the flag does not
  exist today. It is listed as a requirement on items 1/2, not as a runnable line.

Two further facts the lead asked to have stated explicitly:

1. **`scripts/e13a_collect.py` is NOT an E14 path.** It hard-codes `MAX_CALLS = 60` (line 65) and refuses
   any stage descriptor that does not assign exactly 60 cells (`if cells != MAX_CALLS: raise Refusal`,
   lines 125126; again at 392393 and 583584), pins `ARM_SET = "e13a-two-arm"` with `ARMS = ("R1", "FRESH")`
   (lines 6061), and reads E12's five-root checkpoint stage. It cannot express ten roots, 130 slots, an
   initial-generation phase, a public-diagnostic phase or the NEUTRAL/DIRECTED arms. Running it for E14
   is not an option, and widening its constants in place would destroy the E13a binding.
2. **`scripts/build_e14_request_plan.py` (dated 23 Sep 03:19) is bound to the superseded E14 v1 design.**
   It asserts `if n_calls != 108 or set(per_arm.values()) != {54}: raise ValueError` (lines 248249), uses the
   nine-root roster `mbpp/918, 825, 816, 895, 868, 154, 651, 499, 974` (line 3436), appends
   `CONTRACT_LABEL = "terminal-output-contract-v1"` (line 40) and continues E12's frozen prefixes with no
   fresh initial call. The lead's ten-root roster (911, 667, 344, 524, 814, 187, 194, 356, 366, 302),
   `terminal-output-contract-v2`, the fresh initial call and the 130-slot design are all outside it. A new
   builder is required; the existing file must be preserved, not edited.

---

## 1. The exact future command lines, in order

Conventions. Run from the repository root with the worker's existing interpreter
`/Users/yukangzengcmac/DTR-MultiRoundLLM/.venv/bin/python` (shown below as `.venv/bin/python`).
`RUN` is one new `work/e14_<actualUTC>` directory that must not already exist. `RESERVATION` is the
actual committed window/ownership agreement under `docs/`. `OWNERSHIP` is the separate committed
post-launch PID record. `LAUNCHER_SHA` is the `scripts/launch_own_receiver_v31.py` entry in the committed
E14 release's `execution_source_hashes`. Placeholders are not runnable authorization: substituting real
values still does not create authority (see the banner). Every failure stops further dispatch; retain all
records and perform owner-specific cleanup.

### 1.0 Package verification, before any host action (no execution of graded programs)

**DEPENDENCY** the E14 analogue of `scripts/build_e13a_release.py --verify` (which **EXISTS** and takes
`--out --source --stage --plan --run --verify`, rebuilding into a temp dir and diffing the committed bytes):

```sh
# DEPENDENCY (item 1): must rebuild the ten-root package into a temp dir and diff committed bytes.
.venv/bin/python scripts/build_e14_release.py --verify \
    --out experiments/landmark/e14_release \
    --source work/sources/mbpp_full.jsonl \
    --spec docs/e14_lead_measurement_spec_20260923.json \
    --stage experiments/landmark/e14_stage.json \
    --plan results/e14_request_plan_20260923.json
```

```sh
# DEPENDENCY (item 2): the 130-slot plan builder, ten roots, contract v2, fresh initial + diagnostic + 2x6.
.venv/bin/python scripts/build_e14_request_plan.py --out results/e14_request_plan_20260923.json   # flag EXISTS; the 108-slot v1 body does NOT serve E14
```

```sh
# EXISTS: static validators that touch no host and no graded program.
.venv/bin/python scripts/e14_roster_audit.py --out results/e14_roster_audit_<UTC>.json
.venv/bin/python -m pytest tests/ -q
```

**DEPENDENCY on the grading allowlist.** `experiments/landmark/study_adapter.py:389390` fixes
`COMMITTED_RELEASE_MANIFESTS = (dev_release_v2…, dev_release_v3/release_manifest.json,
e13a_release/release_manifest.json)`, and `verify_committed_release` refuses any other path, an untracked
file, or one that differs from its git HEAD blob. An E14 release manifest therefore cannot be verified
until `experiments/landmark/e14_release/release_manifest.json` is added to that tuple **and** committed at
HEAD. That is a source change plus a parent commit; this worker does not commit. Until then E14 grading in
real mode refuses by design. Additionally `GRADING_LIMIT_KEYS` is
`{n_roots, artifact_starts, recheck_starts, max_private_starts, grading_seconds}` with optional
`containment_starts`, and `e13a_grade.py` enforces
`max_private_starts == artifact_starts + recheck_starts + containment_starts` (lines 164187): an E14 stage
must satisfy the same identity (see section 2 for the numbers that do).

### 1.1 Clock initialisation (once, immediately before the first setup action)

```sh
# DEPENDENCY: an E14 clock/stage. See section 3 for why the E13a clock cannot be reused unchanged.
.venv/bin/python scripts/e14_stage_clock.py --run-dir "$RUN" --init --stage experiments/landmark/e14_stage.json
```

The E13a clock **EXISTS** with exactly `--run-dir --init --stage --ownership --owned-receiver-dir
--cleanup-helper-sha256 --start-utc --phase --check --charge --seconds --supervise -- COMMAND` and
`PHASE_CAPS = {"setup": 600, "collection": 480, "private_grading": 300, "analysis": 300}`,
`OUTER_TOTAL_SECONDS = 2700`. It rejects a caps dict whose key set differs from `PHASE_CAPS`
(`set(caps) != set(PHASE_CAPS)` line 91) and any cap above those values (line 94). E14 has **three**
dispatch phases (initial collection, public diagnostics, continuation collection), so either a new phase
schema is added (new clock version, preserving `e13a_stage_clock.py` untouched) or all three run inside the
single 480 s `collection` phase. Which of the two is chosen is a dependency on item 2, not a choice this
document may make silently.

### 1.2 Containment / attestation (setup phase, through the supervisor)

Supervisor form (**EXISTS**, E13a spelling shown; the E14 clock must accept the same shape):

```sh
.venv/bin/python scripts/e14_stage_clock.py --run-dir "$RUN" --stage experiments/landmark/e14_stage.json \
    --ownership "$RESERVATION" --supervise setup -- COMMAND ARGUMENTS
```

```sh
# EXISTS: --runner {common,landmark} and --output DIRECTORY (a directory, not the json filename).
… --supervise setup -- .venv/bin/python scripts/check_landmark_sandbox.py --runner landmark --output "$RUN/attestation"
… --supervise setup -- .venv/bin/python -c 'import sys; from experiments.landmark.grade import verify_attestation; verify_attestation(sys.argv[1])' "$RUN/attestation/attestation.json"
```

A zero exit from the checker does not establish success: `verify_attestation` must pass. Each attestation
epoch is nine containment payload starts (E13a `containment_starts: 9`); two epochs are budgeted in
section 2 (one before dispatch, one at grader-side re-verification).

### 1.3 Receiver launch, preflight, snapshot diff (setup phase)

```sh
# EXISTS: --ownership --out --stop. Launch requires --ownership; the clock adds owner-specific cleanup flags.
.venv/bin/python scripts/e14_stage_clock.py --run-dir "$RUN" --stage experiments/landmark/e14_stage.json \
    --ownership "$RESERVATION" --owned-receiver-dir "$RUN/receiver" --cleanup-helper-sha256 "$LAUNCHER_SHA" \
    --supervise setup -- .venv/bin/python scripts/launch_own_receiver_v31.py --ownership "$RESERVATION" --out "$RUN/receiver"

# EXISTS: --tasks --examples --base-url --out.
… --supervise setup -- .venv/bin/python scripts/receiver_preflight_mrl10.py \
      --tasks experiments/landmark/dev_release_v2/tasks.jsonl \
      --examples docs/public_diagnostic_examples_v1.json \
      --base-url http://127.0.0.1:8193 --out "$RUN/preflight"

# EXISTS: --new-preflight --out. Require passed: true and zero validation errors.
… --supervise setup -- .venv/bin/python scripts/diff_receiver_snapshot_v31.py --new-preflight "$RUN/preflight" --out "$RUN/receiver_diff.json"
```

`--tasks`/`--examples` above are the **historical v2 fixtures the preflight is bound to** (42 renders over
the seven historical public fixtures, loop cues `mbpp/357, 402, 509`, `LOOP_CUE_ROOTS`/`DIAG_PATTERN` in
`receiver_preflight_mrl10.py:2930`). Pointing preflight at the new E14 tasks is **not** a free substitution:
its declared synthetic diagnostics and render count are fixtures of the receiver-identity check, not of the
task roster. Whether E14 keeps the historical fixtures (recommended: the check stays comparable to the
pinned snapshot `results/receiver_props_snapshot_8193.json`) or gains an E14 fixture set with a new pinned
snapshot is a dependency on item 2.

### 1.4 Precollection instrument validation (40 isolated starts, before any model call)

**DEPENDENCY.** No script today validates the ten-root E14 references and both controls per root. The
precedents are `experiments/landmark/validate_references.py`, `validate_rebound_references.py`,
`public_instrument_validation.py`, `public_check.py` and `common/integrity.py:hack_gate`; the required
interface is:

```sh
# DEPENDENCY (item 1/2): 10 public-reference + 10 private-reference + 20 private-control starts = 40.
.venv/bin/python scripts/e14_validate_instrument.py \
    --release experiments/landmark/e14_release \
    --spec docs/e14_lead_measurement_spec_20260923.json \
    --attestation "$RUN/attestation/attestation.json" \
    --out "$RUN/instrument_validation"
```

It must: run each versioned reference against the public view (assertion 0) and against the full private
suite (retained indices 1,2 plus every added assertion); run both controls per root (the specified semantic
fault and the always-`None` control) and require each to **fail** the private suite; and require every
control to pass `hack_gate`. This is the first point in the whole protocol at which a graded program is
executed, and it is gated by the banner.

### 1.5 Initial collection (10 fresh initial calls)

```sh
# DEPENDENCY (item 2): ten fresh initial calls, public prompt only, one per root, no arm instruction.
.venv/bin/python scripts/e14_collect.py --real --phase initial --out "$RUN" \
    --stage experiments/landmark/e14_stage.json \
    --plan results/e14_request_plan_20260923.json \
    --release-dir experiments/landmark/e14_release \
    --ownership "$OWNERSHIP"
```

`--real --out --stage --plan --release-dir --ownership --rebuild-only` are the **EXISTS** spellings from
`e13a_collect.py:722728`; `--phase` is new and is a dependency. `--rebuild-only` (verify the fixed slots and
print the checks, dispatch nothing) must be preserved: it is the only way to check the request law without a
model call, and it should be run for all 130 slots before `--real`.

### 1.6 Public diagnostics (no model call; public statuses only)

```sh
# DEPENDENCY (item 2): frozen public diagnostic over the ten initial answers; public statuses only.
.venv/bin/python scripts/e14_public_diagnostic.py --out "$RUN" \
    --collect "$RUN/collect/initial" \
    --release-dir experiments/landmark/e14_release \
    --stage experiments/landmark/e14_stage.json
```

This stage consumes the ten **initial-public** starts counted in section 2 and produces the single shared
public-diagnostic message (`diagnostic.diagnostic_message(diag)`) and the DIRECTED instruction via
`diagnostic.select_s1(diag)` a deterministic function of public statuses only. `N_INSTRUCTION`,
`select_s1`, `S1_STRINGS`, `render_arms` all **EXIST** in `experiments/landmark/diagnostic.py`. Private
grades are never an input here.

### 1.7 Continuation collection (120 calls, 2 arms x 6 draws x 10 roots)

```sh
# DEPENDENCY (item 2).
.venv/bin/python scripts/e14_collect.py --real --phase continuation --out "$RUN" \
    --stage experiments/landmark/e14_stage.json \
    --plan results/e14_request_plan_20260923.json \
    --release-dir experiments/landmark/e14_release \
    --diagnostics "$RUN/diagnostics" \
    --ownership "$OWNERSHIP"
```

Both arms must share a byte-identical prefix (public task prompt, the model's own previous answer retained,
one shared public-diagnostic message) and both receive the same appended `terminal-output-contract-v2` text
from the lead spec; only the arm instruction differs. The collector must assert prefix byte-equality per
root before dispatch and refuse otherwise.

### 1.8 Private grading (after collection is closed)

```sh
# DEPENDENCY (item 1/2), mirroring EXISTS flags of e13a_grade.py:11301138
#   (--collect --release --out --stage --plan --real --attestation --validate-only).
.venv/bin/python scripts/e14_grade.py --real \
    --collect "$RUN/collect" --release experiments/landmark/e14_release --out "$RUN" \
    --stage experiments/landmark/e14_stage.json --plan results/e14_request_plan_20260923.json \
    --attestation "$RUN/attestation/attestation.json"
```

Run `--validate-only` first (validates the handoff and writes nothing). The primary score stays the
unchanged frozen grader, `GRADER_VERSION = "landmark-grader-v5-parse-and-compile-fault-attribution"`, with
`SPEC_KEYS = {root_id, public_task_sha256, entry_point, public_assertions, private_assertions, preamble,
reference_code, negative_controls}` and `validate_specs`. The terminal instruction is an intervention
instruction only: **no format or fence gate is added to the score.** Candidate private scoring starts only
after collection is closed.

### 1.9 Analysis (through the deadline-enforcing supervisor, not `--check`/`--charge`)

```sh
# DEPENDENCY for the E14 analyzer; the supervisor shape and e13a_analyze flags
#   (--grades --stage --out --treatment-arm --reference-arm) EXIST.
.venv/bin/python scripts/e14_stage_clock.py --run-dir "$RUN" --stage experiments/landmark/e14_stage.json \
    --supervise analysis -- .venv/bin/python scripts/e14_analyze.py \
        --grades "$RUN/grade/grades.jsonl" --stage experiments/landmark/e14_stage.json \
        --treatment-arm DIRECTED --reference-arm NEUTRAL --out "$RUN/analysis_report.json"
```

Output is descriptive only: finite sample contrast, per-root counts, all-assigned completion bounds. No
normal interval, no Hoeffding interval, no efficacy, no futility. Seeds are reproducibility settings, not
proof of independent draws.

### 1.10 Shutdown (immediately after collection and on every failure)

```sh
# EXISTS: terminates ONLY the PID recorded in <out>/launch.json, after comparing process birth/command identity.
.venv/bin/python scripts/launch_own_receiver_v31.py --out "$RUN/receiver" --stop
```

Never signal another project's process; never infer shutdown from a stop-request timestamp. Cleanup
overrun is reported as a deviation, never as renewed allowance.

---

## 2. Numerical resource proposal (a ceiling for a decision not yet made)

### 2.1 Model attempts and reserved tokens

| Quantity | Value | Arithmetic |
|---|---:|---|
| Roots | 10 | lead roster 911, 667, 344, 524, 814, 187, 194, 356, 366, 302 |
| Initial calls | 10 | 1 fresh initial call per root |
| Continuation calls | 120 | 10 roots x 2 arms (NEUTRAL, DIRECTED) x 6 draws |
| **Model attempts** | **130** | 10 + 120 = 130, all slots fixed before collection, no retries |
| Reserved completion tokens per call | 512 | `e13a_collect.TOKENS_PER_CALL = 512` |
| **Reserved completion tokens** | **66,560** | 130 x 512 = 66,560 |

### 2.2 Isolated starts: 228

| Group | Starts | Arithmetic |
|---|---:|---|
| Containment | 18 | 2 nine-check epochs: 2 x 9 = 18 |
| Precollection instrument | 40 | 10 public-reference + 10 private-reference + 20 private-control (2 controls x 10 roots) = 40 |
| Grader-side rechecks | 30 | 10 private-reference + 20 private-control = 30 |
| Candidate | 140 | 10 initial-public + 10 initial-private + 120 continuation-private = 140 |
| **Total isolated starts** | **228** | 18 + 40 = 58; 58 + 30 = 88; 88 + 140 = **228** |

Cross-check against the grader's own limit identity. `e13a_grade.py` requires
`max_private_starts == artifact_starts + recheck_starts + containment_starts`. With the 10 public-check
candidate starts folded into `artifact_starts` (see the dependency below), an E14 stage would declare
`artifact_starts = 140`, `recheck_starts = 30`, `containment_starts = 18`, hence
`max_private_starts = 140 + 30 + 18 = 188`. The 40 precollection instrument starts happen before grading and
outside the grader's ledger: **188 + 40 = 228**, the same total by a second route.

**Every attempted or uncertain start counts.** A start that fails, times out, or whose completion is unknown
is charged. Cache hits and pre-execution format rejection can reduce *actual* starts below these maxima
without dropping any assigned slot they never renew a cap, and they never license an extra start
elsewhere. These are maxima, not expected counts. The historical E12 ledger (333/412) and the E13a allowance
(79 starts, 60 calls, 30,720 tokens) are preserved: this allowance is explicit and borrows no unused capacity.

**Dependency on the public-check counter.** E13a's contract carries "public-check starts: 0" as a separate
line, while `study_adapter.GRADING_LIMIT_KEYS` has no public-check key and the key set is checked exactly. To
represent E14's 10 initial-public starts, item 1/2 must either (a) fold them into `artifact_starts` as above,
or (b) add a new optional limit key, which is a grader schema change and therefore a new grader/adapter
version with `e13a_grade.py` left untouched. This document does not choose; it records that 228 holds under
either representation.

### 2.3 The lead's conditional 198-start alternative: not established, propose 228

198 = 228 - 30, i.e. dropping the grader-side rechecks. Per MRL-23 that lower figure is available **only if
the connected path proves both** of the following:

1. **The 30 rechecks are not run.** The existing grader *does* run them: `e13a_grade.py` classifies a start as
   `"recheck" if kind in ("reference", "negative_control")` (line 690) and budgets `recheck` against
   `limits["recheck_starts"]` (line 672), with `recheck_starts: 10` in the E13a stage and the explicit note
   that they are validation starts, not analysis slots. An E14 grader that does not run them would be a
   different grader with a proof that its private verdicts are unaffected.
2. **Validated reference/control evidence is safely reusable** under all current bindings i.e. the
   precollection validation receipt is bound to the same attested container, the same release bytes, the same
   grader version and the same host state that grading runs under, with that binding checked rather than
   assumed.

**Neither is established today**, because the deliverable-2 path does not exist yet (section 0): there is no
E14 collector, grader or receipt-reuse mechanism whose properties could be inspected. Nothing I can read
demonstrates (1) or (2). **Therefore this document proposes 228, not 198**, and states plainly that the
reduction is unproven rather than declined. If item 2 later lands a grader that imports a bound validation
receipt instead of rerunning references and controls exactly as the nine attestation starts are imported
rather than rerun in E13a then 198 becomes arguable, in a revision reviewed on its own terms. No cache
saving renews a cap in either case.

### 2.4 If this is insufficient for the actual path

If the realised E14 path needs more than 130 attempts, 66,560 reserved tokens or 228 starts, that is a
**dependency to report, not a number to expand**. Concretely, the known pressure points are: a third
containment epoch (would make 27 and 237), any per-call guard sweep that adds metadata attempts, and any
retry policy which this design forbids outright.

---

## 3. Frozen operational limits

### 3.1 Phase and outer wall limits

Currently frozen in `scripts/e13a_stage_clock.py` (read at lines 3233):

| Phase | Cap (s) |
|---|---:|
| `setup` | 600 |
| `collection` | 480 |
| `private_grading` | 300 |
| `analysis` | 300 |
| Contiguous outer limit from clock initialisation | 2,700 |

The clock charges phase time cumulatively and once, including on ordinary exceptions; it rejects a missing,
wrong-run or wrong-stage clock, widened caps, overlapping phases and an unfinished receipt from an
interrupted process; `--check`/`--charge` are bookkeeping and supervise nothing; there is no implicit resume.
**E14 dependency:** E14 needs initial collection, public diagnostics and continuation collection. Either all
three fit inside one 480 s `collection` phase, or a new clock version declares them; the caps key-set check
forbids quietly adding phases to the E13a clock.

### 3.2 Per-request and metadata limits

| Limit | Value | Source |
|---|---:|---|
| Completion tokens reserved per call | 512 | `e13a_collect.TOKENS_PER_CALL`; a stage requesting another value is refused (lines 565566) |
| Collection metadata HTTP attempts | 31 | `e13a_collect.MAX_COLLECTION_METADATA_HTTP`, composed as preflight <= 4 + twelve block guards x 2 + postflight <= 3 |
| Setup metadata/template HTTP attempts | 50, <= 10 s each, no retries | `receiver_preflight_mrl10.py:27` `MAX_REQUESTS, TIMEOUT = 50, 10.0`; allowed endpoints only: `GET /props`, `GET /slots`, `GET /v1/models`, `POST /apply-template` |
| Template renders in preflight | 42 | seven historical public fixtures; not synthetic E14 outcomes |
| Generation smoke calls | 0 | no warm-up call is budgeted |
| Retries | 0 | at every layer |
| Paid services, downloads, installations | $0, none | |

**E14 dependency:** 31 is derived from E13a's twelve five-root blocks. A ten-root, 130-slot schedule has a
different block count, so the metadata cap must be **rederived and frozen in the E14 stage** as
`preflight + 2 x (number of balanced blocks) + postflight`, not copied. Guard frequency follows E13a's
accepted answer: preflight, before each balanced block, and postflight no new per-call metadata sweep.
Guards detect deviation at those checks only, not between them.

### 3.3 Prompt/context and request-law checks

Frozen request shaping is checked field-by-field before dispatch (`e13a_collect.REQUEST_SHAPING`:
`schema_version, model, model_digest, decoding, max_tokens_per_call, sampler, …`). For E14 additionally:
per-root byte-identity of the two arms' shared prefix; exactly one shared public-diagnostic message; the
model's own previous answer retained verbatim; one appended `terminal-output-contract-v2` string identical
across arms; the 130 seed labels disjoint from every seed spent at that root, with a collision check;
context within the launched `-c 32768` window with the prompt length recorded per call. Any
`UNRESOLVED` binding, adapter substitution or bypass is refused in real mode. No private field,
added assertion, reference or control text may appear in any prompt this is checked, not trusted.

### 3.4 Launch and cleanup limits

Receiver identity is pinned: Qwen2.5-3B Q4_K_M, model SHA256
`626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d`, 26 pinned build files, launch shape
`-ngl 99 -np 4 -c 32768 --jinja`, loopback port 8193, ready marker
`listening on http://127.0.0.1:8193`, pinned properties snapshot
`results/receiver_props_snapshot_8193.json`. The launcher requires a committed `--ownership` agreement and at
least 60 minutes remaining at readiness; `--stop` compares recorded process birth/command identity and uses
bounded TERM then KILL with 5 s waits, recording observed disappearance and never inventing an exit code.
The clock's `--owned-receiver-dir` + `--cleanup-helper-sha256` pair permits bounded owner-specific cleanup on
a failed or timed-out launch, with `LAUNCHER_SHA` taken from the committed release's
`execution_source_hashes`. The receiver directory must not already exist.

### 3.5 Live shared-host gates (all three required, none inferable)

1. **Peer non-contention:** a real, current agreement releasing the host; other projects' valid jobs are
   preserved. Silence, an idle port and historical peer reports are not a lease.
2. **Renewed attestation:** fresh `check_landmark_sandbox.py` output plus a passing `verify_attestation`, and
   a `diff_receiver_snapshot_v31.py` result with `passed: true` and zero validation errors. The expired E12/E13a
   windows and the unagreed placeholder date have no standing.
3. **Real agreed window:** a reservation committed under `docs/` with actual UTC start/end, acceptance and
   release references, and the **current** launcher hash; after launch, a separate committed ownership record
   with actual PID/start, receiver URL and accepted window. Setup commits do not re-anchor the clock or renew
   its budget.

### 3.6 Time estimates (estimates, not bounds)

Measured inputs: **E12 collection 314.258 s over 154 calls = 2.040636 s/call**
(`docs/e12_lead_judgment_20260923.md`, `docs/project_status.md`). E13a measured usage over 60 calls
(`results/e13a_two_arm_20260923T061500Z/analysis_report.json`): 18,978 prompt + 6,406 completion tokens
total; per arm, R1 (long prefix, diagnostic + retained answer + instruction) 12,804 prompt / 5,018 completion
over 30 calls = **426.8 prompt and 167.3 completion tokens per call**; FRESH (short prompt) 6,174 / 1,388 over
30 calls = **205.8 prompt and 46.3 completion tokens per call**.

| Estimate | Value | Derivation |
|---|---:|---|
| Initial collection (10 calls) | ~20.4 s | 10 x 2.040636 |
| Continuation collection (120 calls) | ~244.9 s | 120 x 2.040636 |
| All 130 calls | ~265.3 s | 130 x 2.040636 |
| Completion tokens actually used, continuations | ~20,080 | 120 x 167.3 (E13a R1 arm as the nearest measured analogue) |
| Completion tokens actually used, initials | ~460 | 10 x 46.3 (E13a FRESH arm as the nearest analogue) |
| Prompt tokens, continuations | >= ~51,200 | 120 x 426.8, a **lower** estimate: E14 prefixes add the terminal contract and are longer |

Reading of the estimates: ~265 s of dispatch inside a 480 s `collection` cap leaves roughly 215 s of margin
for guards, metadata and per-slot bookkeeping across three sub-phases margin, not proof. Reserved tokens
(66,560) exceed the estimated actual completion usage (~20,540) by design; reservation is a ceiling, and the
measured E13a mix is a different prompt mix at five different roots. These figures are planning estimates from
historical runs, **not bounds and not predictions of E14 outcomes**, and they license nothing.

---

## 4. Stop rules

### 4.1 Stop on integrity or resource failure only never on interim outcomes

Dispatch stops immediately, with all records retained and owner-specific cleanup performed, on any of:
attestation or `verify_attestation` failure; a receiver diff that is not `passed: true` or has validation
errors; a release/stage/plan/source byte mismatch, an unallowlisted or uncommitted release manifest, or an
`UNRESOLVED`/substituted adapter in real mode; a request-law, seed-collision or prefix byte-identity
violation; a prompt that would carry a scorer-only field; a phase cap, outer deadline, token reservation,
start-count or metadata-attempt exhaustion; loss of exclusive host ownership or window expiry; a clock
refusal (wrong run/stage, overlapping phase, unfinished receipt); an unreaped owned child.

**No interim outcome is a stop rule.** No interim efficacy test, no futility test, no score-driven stopping,
no outcome-based roster change, no mid-batch tuning, no favourable-block selection, no alternate extraction,
no replacement seed, no added root, no pooling with E12/E13a. Caps were fixed without inspecting scores;
that prohibits score-driven stopping but does **not** make missingness score-independent runtime and
failures may correlate with potential scores.

### 4.2 Missingness, as operational behaviour

* **Keep every assignment.** All 130 slots stay in the records; a slot never disappears because it failed.
* **Failed initial generation:** its twelve continuation slots are recorded as missing. Do **not** fabricate an
  answer, substitute a task-only intervention, retry, or remove the root.
* **Valid-but-incomplete public diagnostic:** dispatch continues with the predeclared public-only
  incomplete-information instruction. No private information may be consulted to fill the gap.
* **Any missing primary branch grade suppresses the primary point contrast.** Report all-assigned binary
  completion bounds with **no** missing-at-random assumption; available-case summaries are secondary and
  labelled as such. Bounds are not confidence intervals.
* **Mid-root truncation, all-missing arm, environment/containment or receiver-law failure:** the stop rules
  above apply and the partial record is retained as evidence. A failure or interruption is evidence, not an
  invitation to retry.
* **Unknown values are reported explicitly.** Attempted, completed, failed and missing are reported
  separately, with actual prompt/completion usage including unknowns, reserved tokens,
  containment/instrument/recheck/candidate starts, per-phase runtime, metadata requests and $0 spend. No
  silent drops; no parseability-selected success rate.
* **Candidate private scoring starts only after collection is closed.**

---

## 5. What this document is not

Not authority. Not a reservation. Not a receipt. Not evidence about E14's outcome, and not efficacy or
futility evidence about anything. A passed source/mock path is not execution. Publication is not lead
validation, and lead validation of *this* plan would still not be authority to collect: that requires an
independent review of the E14 package plus the section 3 gates plus an explicit later decision. Independent
policy evaluation, matched fitted-history numerical validation and full manuscript integration remain open.
The ten held roots (211, 701, 960, 370, 484, 346, 508, 670, 376, 650) remain untouched; the source-exposure
limitation recorded in MRL-22 (whole-file mechanical processing, twenty-record semantic review, no reported
new model-outcome inspection) is carried forward unchanged.
