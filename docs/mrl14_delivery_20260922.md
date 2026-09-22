# MRL-14 delivery: candidate compile-validity gates, fault attribution, targeted-validation proposal

**Experiments workstream.** Processed lead revision `b5168d6`. Started 2026-09-22T01:37:17Z and completed at 2026-09-22T01:43:07Z, inside the
20-minute cap on one CPU. Work was source, mock and **static `compile()` only**: 0 model, receiver, sandbox,
reference, candidate, control or canary executions; no installs; $0. The full suite passes: **673 tests**.
E11 files and original grades are untouched.

## Repair

- **Private gate** (`experiments/landmark/grade.py`, `GRADER_VERSION = landmark-grader-v3-candidate-compile-as-written`).
  After the unchanged `hack_gate` and `ast.parse` checks, the candidate must pass
  `compile(code, "<candidate>", "exec", dont_inherit=True)` **exactly as written**. A failure is outcome 0 with
  `candidate_compile_error` (exception class and line, no traceback), and there are **zero sandbox starts**.
  `grader_environment_failed_before_payload` now means only a harness, compiler or runtime fault on a
  candidate that compiles.
- **Public gate** (`public_check.py`). `static_code` requires the same compile. A compile failure is
  `format_error` with no runner call. `infrastructure_not_started` is kept only for compiling candidates.
- **Adversarial review:** one major finding, fixed. The private gate originally compiled a
  future-import-reordered rewrite, so a late `from __future__` import was accepted privately and rejected
  publicly. It now compiles as written, and a test forces the two gates to agree on five edge cases.
- **Tests:**
  - module-level `return`, `break`, `continue` and `await`;
  - valid `from __future__ import annotations`, and a docstring followed by a future import;
  - ordinary functions;
  - null bytes;
  - a compiling candidate with no start marker, which is still an infrastructure fault;
  - **both saved E11 S0 outputs** (378 and 489, replicate 1), whose hashes are verified against their saved
    records. Both are now static `candidate_compile_error` / `format_error` with zero runner calls.
- **Historical freeze tests are re-bound, not waived.** Each stored v1/v1c contract digest is recomputed
  statically from the grade, sandbox and integrity blobs at its freeze commit. Both match exactly, and both
  differ from the current contract.

## Versioned hashes

| item | before | after |
|---|---|---|
| `grade.py` | frozen at `0bb2388` | `0602926a…` |
| `public_check.py` | `a42fbc98…` | `956a74b6…` |
| grading contract for the v2 specs | `0b49177c…` (bound in `dev_release_v2` and used by E11) | `21b4c0cb…` |
| collector source hash | `57882f73…` (in the v2 config) | `536923f2…` |

**Not rebound.** `dev_release_v2` and the E11 run remain bound to the old contract and source hashes. A
future collection needs a new package version (v2.1) frozen against the new hashes. Old validation is not
presented as if the new grader had run.

## Dependency impact (`results/dependency_diff_mrl14_20260922T014228Z.json`)

**Changed against the E1–E8 freeze `0bb2388`:** `grade.py` (E8 evidence), `public_check.py` (E2–E7 evidence),
and the MRL-12 files `public_phase.py` and `study_adapter.py` (no gate evidence).

**The sandbox, profile, interpreter, host and platform binding is unchanged**, so E1 is unaffected and the
attestation (valid until 2026-09-22T20:17Z) is reusable on this host.

**Static evidence** (compile only, 0 starts):

- all **24/24** frozen references and controls compile;
- all **18/18** validation canaries compile;
- all **26/26** public-instrument items compile.

So the new gates change the execution path for **none** of the artifacts E2–E8 measured; the only change is
for non-compiling candidates. This is reasoning from source and compile results, not executed validation.

## Minimal targeted validation proposal (not run)

| gate | what | planned starts | pass criterion |
|---|---|---|---|
| E8′ | `validate_rebound_references` with grader v3 on the frozen v2 specs | 24 | 7/7 references pass, 17/17 controls fail (unchanged expectation) |
| E6′ | `public_instrument_validation --gate E6` with the new public checker | 7 | 21/21 public reference cases pass |
| *(optional)* E3–E5′ | the frozen canaries through the new public checker | 18 | the same frozen expectations; none compile-fail, so none should change |

- **Minimal:** 31 starts, bringing the ledger to 143 + 31 = **174 of 200**.
- **With the optional canaries:** 49 starts, bringing it to **192 of 200**.
- **No E1 refresh** is needed while the attestation is valid.
- **A full E2–E8 rerun** (68 starts) would exceed the ceiling (211), and the static evidence above makes it
  unnecessary.

## Next sampling design (proposal)

[next_sampling_design_proposal_20260922.md](next_sampling_design_proposal_20260922.md) sets out a
prospectively sampled frame from the 396 mechanically screened fresh candidates:

- exclusions are fixed and hashed before any call, including the seven E11 roots;
- there is a family cap;
- an optional initial-failure screen uses a frozen **public** decision-time rule, from a separately seeded
  screening draw;
- **an unscreened stratum and all inclusion probabilities are kept**, so the whole-frame and failure-enriched
  targets are stated separately;
- private grades never select roots.

**Budget arithmetic from E11 per-root costs** (11 calls and about 9.4 grading starts per root; planning
arithmetic, not power):

| roots | receiver calls | grading starts |
|---|---|---|
| 30 | 330 | about 283 |
| 60 | 660 | — |
| 115 | 1,265 | about 1,084 |

The frame cannot certify Δ > 0.05. It supports a development-scale discriminating test on roots with room to
improve. **Precondition:** this compile repair is validated and frozen first.
