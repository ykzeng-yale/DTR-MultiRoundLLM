# MRL-10 delivery: static v2 build, E9 preflight, E10 audit, corrected validation bundle

**Experiments workstream.** Processed lead revision `9be5edd` (decision in `f611544`). Started 2026-09-21T19:43:02Z
and completed at 2026-09-21T19:54:03Z, inside the 30-minute cap on one CPU. Usage:

- **Receiver:** 47 loopback HTTP requests (E9), 10 s timeout each, no retries, **0 generation requests**;
- **Executions:** **0 sandbox, reference, candidate, canary or control executions**;
- **Other:** no installs or downloads, no leases, $0.

The full suite passes: **628 tests**.

## Static v2 package (`experiments/landmark/dev_release_v2/`)

- **Build:** `tasks.jsonl` and `private_specs.jsonl` were built by `scripts/build_dev_release_v2.py`. Private
  assertions and reference code are **byte-identical to v1c**, and the public examples are appended to every
  task. The new grading-contract digest is `0b49177c…`.
- **`config.json`** is resolved from the preserved v1c settings:
  - seed = split_seed = 20260921; split [0, 1, 0]; timeout 120 s; 32,768 request bytes;
  - v1c source and licence;
  - the v1c exclusion lists preserved as historical inputs;
  - 77 calls, 39,424 completion tokens, 1,200 s, R = 2, $0, all **unreleased**;
  - `receiver_state_sha256` taken from the E9 snapshot;
  - the source hash at this commit.

  It **validates in real mode** and plans exactly 77 calls.
- **`release_manifest.json`** resolves the J7 grading bindings: frozen tasks sha, contract, config digest, the
  expected source hashes from `study_adapter.grading_source_hashes()`, E10 result and receiver snapshot. It
  states that **all seven roots were inspected and are intentionally reused DEVELOPMENT roots, never
  untouched**.
- **`ownership.observed.json`** holds observed facts only: PID 63657, started 2026-09-19T17:41:11Z, launched
  from the ICLR-WinRatioAgentEvals session scratchpad. The owner, window and agreement are `UNRESOLVED:`.
  **No exclusive-use agreement was invented**, so the collector's real mode still refuses to run.

## E9: non-generating preflight (`results/receiver_preflight_mrl10_20260921T194506Z`)

- **Requests:** `GET /slots` (4/4 idle), `GET /props`, `GET /v1/models`, 42 × `POST /apply-template`, then
  `GET /props` and `GET /slots` again (idle). 47 requests in 1.2 s.
- **Receiver state:** digest `1b8bf998…`, identical before and after, and identical to the 14:55Z snapshot.
- **Identity:** weight digest and build match the config. The sampler equals the pinned mapping (no
  differences).
- **Rendered prompts:** 42 renderings (7 tasks × initial/N0/S0/N1/S1/R1) with declared synthetic initial
  answers and diagnostics. Loop and fallback S0 cues and all three S1 strings are exercised.

  | arm | user turns | assistant turns |
  |---|---|---|
  | initial | 1 | 0 |
  | N0, S0 | 2 | 1 |
  | N1, S1 | 3 | 1 |
  | R1 | 3 | 0 |

  N1 and S1 are byte-identical up to the final instruction. The explicit system message replaces the
  template's Qwen default in all 42.
- **Fixtures:** these are template fixtures, kept separate from the future actual-request hashes.

## E10: static overlap audit on the rebound specs (`results/public_diagnostic_examples_audit_v2_20260921T195217Z.json`)

**PASS, 21/21.** The auditor is parameterized: it refuses to overwrite, requires the expected count, parses
exactly the bytes it hashed, refuses duplicate keys, and normalizes tuples to lists. Legacy mode resolves
against the repository and refuses to overwrite.

## Validation-plan repairs 1–5 and the two acceptance criteria

1. **E1** now writes to a directory, `$RUN/attestation/`; consumers use `attestation.json` inside it.
2. **E8** has a new versioned `validate_rebound_references.py`: exactly 24 jobs, no 402 rewrite, expected
   7 pass / 17 fail, a durable ledger and a required attestation. The historical validator is unchanged.
3. **E10** uses the parameterized auditor and was run on the rebound specs.
4. **E2, E6 and E7** have a new `public_instrument_validation.py` driver with a frozen items fixture
   (`public_instrument_items_v1.json`): exactly 2, 7 or 17 starts, preserving root and control identities.
   - The E7 predictions are bound by control code sha256. Unexecuted items are counted separately and never
     treated as agreement.
   - The E2 canary targets the **committed** rebound private specs.
   - The positive control's interpreter prefix is recorded and checked at run time.
5. **Canaries:** each start is written durably before the runner, and the raw runner outcome after it. The
   provenance covers the attestation (hashed before and after verification), runner, sources (including
   `public_phase.py`) and canary file. Static-gate and payload canaries are labelled; actual starts are
   reported separately from planned ones.

- **Criterion 1:** `public_phase.load_initial` requires a complete checksum inventory, the Phase A manifest,
  every non-excluded assigned root covered (or explicitly failed), and no stray artifacts. All of this is
  checked before any start.
- **Criterion 2:** canary provenance and per-start persistence (item 5).

## Adversarial review

There were 12 findings, each demonstrated on fakes.

- **Fixed by the fixer (9):**
  - an infrastructure failure counted as E7 agreement;
  - start write failures swallowed;
  - an uncovered assigned root silently skipped;
  - stray artifacts accepted;
  - `public_phase.py` missing from provenance;
  - the attestation hashed only after verification;
  - no raw runner record;
  - legacy mode overwriting its output;
  - tuple-versus-list inputs missed by the overlap check.
- **Fixed by me (the three it left open):**
  - interpreter-dependent E2 positive control;
  - optional count check and re-read bytes in the auditor;
  - legacy paths resolved against the working directory.
- **Also found and fixed by me:** the E2 canary pointed at an uncommitted `work/` path.

Most regression tests were written alongside their fixes; the pre-fix evidence is the reviewers' scratch
counterexamples.

## Ordered bundle for release

See [e1_e10_validation_plan_20260921.md](e1_e10_validation_plan_20260921.md). It contains the exact commands,
frozen hashes and stop conditions. Planned starts are ≤ 77 (E1 9, E2 2, E3–E5 ≤ 18, E6 7, E7 17, E8 24). **E1–E8
are held for the lead's single bundle release; E11 is not authorized.**
