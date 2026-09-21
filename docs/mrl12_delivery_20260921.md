# MRL-12 delivery: grading and analysis CLI, Phase B cost transfer, A–E orchestration, freeze hygiene

**Experiments workstream.** Processed lead revision `d1a0ba9`. Started 2026-09-21T20:52:58Z and completed at 2026-09-21T21:00:32Z, inside the
20-minute cap on one CPU. **0 model, receiver, reference, candidate, canary or sandbox executions**; no
installs; $0. The full suite passes: **646 tests**.

## Built

- **`study_adapter grade`** (opt-in `--real`):
  - checks the attestation first, taking its sha before and after verification;
  - loads **every J7 binding from the committed release manifest**. The manifest must sit at its committed
    path and be byte-equal to its version at HEAD; missing, `UNRESOLVED:`, malformed or mismatched
    bindings are refused;
  - checks the package bytes of tasks, specs and config;
  - refuses to overwrite;
  - writes a durable ledger with a start record before and a result record after every grading execution,
    including `elapsed_seconds`. On interruption it writes INCOMPLETE and deletes nothing;
  - reports actual starts against the planned maximum (101).
- **`study_adapter analysis-input`:**
  - the diagnostics bytes must equal `--expected-diagnostics-sha256`, **and** that digest must equal the
    one the continue phase recorded;
  - the Phase B root set must equal the view's;
  - per-root `diagnostic_cost` comes from Phase B; an unmeasured value stays null, never zero;
  - a root that failed its initial answer gets `{0, 0.0}`, because no start happened for it.
- **`public_phase`** measures `elapsed_seconds` around every runner call and `executor_seconds` per root.
  An unmeasurable clock gives null.
- **`tests/test_landmark_e11_orchestration.py`** covers the full A→E pipeline through the CLIs with fakes:
  - a failed initial output flows through as missing (now asserted unconditionally);
  - a diagnostics hash mismatch, interrupted grading, and missing, `UNRESOLVED` or mismatched bindings are
    all refused.

## Adversarial review (demonstrated on fakes)

Two major findings, both fixed:

1. **analysis-input accepted an unrelated Phase B directory**, and could attribute costs to no root. It is
   now bound to the continue phase's recorded digest and to the exact root set.
2. **Grading accepted a release manifest from any path**, so it could carry a forged contract binding. It
   must now be the committed file, and the contract, config and task digests are shape-checked.

## Freeze hygiene and dependency diff (`results/dependency_diff_mrl12_20260921T205917Z.json`)

- **Changed:** only `experiments/landmark/public_phase.py` (timing instrumentation) and
  `experiments/landmark/study_adapter.py` (CLI glue).
- **No E1–E8 evidence depends on either file.** E2, E6 and E7 used `public_instrument_validation.py`, and the
  classification path `public_check.check_artifact` is unchanged. So **no targeted re-validation is
  needed**, and the 77-start MRL-11 record stands unchanged.
- **The attestation binding matches exactly** (sandbox source, profile, interpreter, host, platform, kind), so
  it is reusable until 2026-09-22T20:17Z.
- **Recomputed and committed:**
  - `dev_release_v2/config.json` `source_code_sha256`: `61e157f9…` → `57882f73…`;
  - `release_manifest.json`: the package config hash, `expected_config_sha256`, and
    `expected_source_hashes` (only `study_adapter.py` changed), with a `freeze_history` entry.
- **The grading-contract digest is unchanged**, since grade, sandbox and integrity are untouched.

## E11 runbook

[e11_proposed_runbook_20260921.md](e11_proposed_runbook_20260921.md) now has:

- exact commands with no ellipses;
- the `DIAG_SHA` binding from Phase B to phases C and E;
- the analysis cost mapping;
- collection, diagnostic, grading and end-to-end time reported separately;
- a same-freeze guard between A and C;
- a required ownership window of **at least 45 minutes** (per-phase `now + 1200 s` checks);
- attestation-refresh accounting (+9 starts, 194 of 200).

**E11 remains on hold** pending the owner's exclusive-use agreement and your release.
