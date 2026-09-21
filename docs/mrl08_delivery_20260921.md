# MRL-08 delivery: source/mock implementation of the public-diagnostic study

**Experiments workstream.** Processed lead revision `ad1d061` (decisions in `89f6054`). Started
2026-09-21T18:26:06Z under a cap of one CPU, 30 minutes and $0. **0 model calls, 0 receiver generations, and 0
sandbox, reference, candidate or control executions.** Generated harness text was only `compile()`d. There
were no installs and no leases. Every lead decision in
[lead_review_mrl05_08_20260921.md](lead_review_mrl05_08_20260921.md) is adopted as written. Nothing here
releases execution.

## What was built

| module | what it does | lead field(s) |
|---|---|---|
| `experiments/landmark/collect.py` (landmark-v2 repairs) | typed sampler domains (`min_p = 2`, fractional or bool `top_k` rejected); typed `/props` state schema (null generation settings fail closed); exact `/slots` inventory (empty/malformed/extra/duplicate → *unverified*, never idle); required `sampler_law`: `server_defaults_pinned` demands float32 equality with the snapshot, `declared_override` records the difference as a different frozen law; passing status narrowed to `receiver_guard_checks_passed` with no efficacy grant; `lease: sampled_idle_slots_only_not_exclusive`. v1 request bytes unchanged | MRL-06, 12 |
| `experiments/landmark/public_check.py` | format rule reused from the grader (static, before any run); runtime interface lookup and signature binding; harness text with a per-case 2 s alarm, `RLIMIT_CPU` 5 s, fresh `literal_eval` arguments, silenced candidate stdout, and equality inside isolation; one nonce-tagged line per case; `classify()` with a frozen, tested precedence table. Forged, duplicate, out-of-order, extra, truncated or trailing output gives `unavailable/protocol_integrity_review`, never `pass` | 3–8 |
| `experiments/landmark/diagnostic.py` | exact public-example rendering; lead's diagnostic header; sorted compact UTF-8 JSON; `DiagnosticOverflow` at 2,048 B (never truncated); S1 selector; renderers for N0/S0/N1/S1/R1 (R1 has no previous answer; N1, S1 and R1 carry byte-identical diagnostic messages); `TARGETED` pinned by digest | 1–3, 6, 10, 13 |
| `experiments/landmark/collect_diagnostic.py` | Phase A (initial) and Phase C (continuation); diagnostics bound by sha256 and by per-root raw-bytes artifact sha; 77 planned calls and 39,424 reserved tokens for 7 roots at R = 2; independent `arm:replicate` seeds; budgets never refunded across phases; drift stops dispatch and keeps outputs | 9, 11, 12 |
| `experiments/landmark/analyze_diagnostic.py` | root-mean arms and contrasts (S1−N1 primary; N1−N0, S0−N0, R1−N1; each arm − STOP); **no intervals**; field-15 cross-tab of initial public status × initial private STOP status, with final outcomes by stratum; per-arm cost with unknowns counted, never zero | 15 |
| `scripts/build_dev_release_v2.py` | appends the public examples to each task, rebinds `public_task_sha256`, asserts private assertions and references are byte-identical to v1c, computes the new grading-contract digest; writes only to a new directory under `work/` | 14 |
| Golden fixtures `tests/fixtures/diagnostic_v1/` | exact bytes of all 7 public-example renderings, 3 diagnostics (all-pass, first wrong value, crash then unavailable), and all 5 arms for one root, with SHA256SUMS | 1, 2 |

**Worst-case diagnostic size.** Only `pass` and `wrong_value` may carry a value (tightened in round 2). A
`wrong_value` with 16 ints of magnitude 10¹⁸−1 in every case gives **1,586–1,654 B** including the header. The
largest is mbpp/489, leaving 394 B. The lead's byte audit (1,723 B for mbpp/489, with different illustrative
keys) is consistent with this. Increment 1 reported 1,720 B, but that figure used a status that may not carry a
value and is superseded. An overflow cannot occur for a valid record; if it ever did, it raises.

## Round 2: gaps closed and adversarial review

| addition | what it does |
|---|---|
| `experiments/landmark/public_phase.py` | Phase B driver. It verifies Phase A artifacts by raw-bytes sha256 and `completion.json` checksums, reads public cases only from the examples file, and runs one injected runner per artifact (format errors start nothing; no retries). It writes `diagnostics.json` as canonical bytes plus a manifest containing its sha256, the executor source sha256s (`public_check.py`, `diagnostic.py`, `sandbox.py`, `grade.py`), `PUBLIC_LIMITS` and the **actual start count**. Nonces are ephemeral and never written |
| `diagnostic.validate_diagnostic(diag, entry_point, cases)` | exact keys and status/value/reason policy; with the task's public cases, **exact ordered match of `case_id`, `call` and `expected`**. `run_continue` requires the public examples and checks that they are the ones rendered in the prompt before any dispatch |
| `experiments/landmark/study_adapter.py` | grading view (STOP plus five arms) and analysis input. `grade.grade_collection` cannot grade the new arms, and its own checks correctly refuse; see below. `grade_study` mirrors its per-artifact logic, including reference/control rechecks, and **keeps the containment-attestation gate**. Only a declared fake runner in unit tests skips it, and that is recorded |
| one `collect` module object | `collect_diagnostic` and `diagnostic` share one import |

**Adversarial review:** three lenses (the lead's contract, the receiver, the boundary); every finding needed a
counterexample demonstrated on fakes.

- **Major, fixed.** A diagnostics file could carry arbitrary `call`/`expected` text, such as a hidden test,
  that passed validation and reached the N1/S1/R1 prompts. Case content was never bound to the fixed public
  cases. It is now bound and tested (5 refusal cases, zero dispatch).
- **Five minors, all fixed with regression tests:**
  - status-only cases (`program_exception`/`timeout`/`output_limit`) could carry a returned value;
  - `render_arms` did not itself refuse extra keys;
  - snapshot parameters were not held to the field domains (`top_k = 40.7` was accepted);
  - integer sampler fields were compared by float32 rounding (16777217 matched 16777216.0);
  - the hashed v2 request did not record the sampler actually sent. It now does, and the adapter refuses a
    request whose sampler differs from the freeze.

**Full suite: 471 passed** (`scripts/check_tests.sh`, exit 0).

**Why `grade.py` is not used directly.** Changing it would change the grading-contract digest. Its
`grade_collection` requires the arm set {stop, generic_repair, history_specific_repair, independent_restart}
through `analyze.analyze`, a `grading_contract_sha256` in the collection config, and a single run directory.
The diagnostic study has six arms in two phase directories. `grade_study` reuses `grade.evaluate`,
`grade.extract_code`, `grade.contract` and `grade.verify_attestation` unchanged. The lead should confirm this
mirror, or decide that a versioned grader is preferred.

## Proposed release manifest and start ledger

[`diagnostic_release_manifest_proposal_20260921.json`](diagnostic_release_manifest_proposal_20260921.json)

| component | limits |
|---|---|
| Public executor | 2 s per-case alarm; 5 s aggregate `RLIMIT_CPU`; 10 s parent wall; `RLIMIT_DATA` 536,870,912 B (**best effort on macOS, not guaranteed containment**); 65,536 B output and `RLIMIT_FSIZE`; nproc 1; one start per artifact; 0 retries |
| Grader (unchanged) | 2 s wall; 1 s CPU; 65,536 B output; the same best-effort memory |

The start ledger has 161 core starts, including a conservative 24 for reference/control rechecks inside final
grading. There are 24 itemized integrity starts:

- 9 for a fresh attestation;
- 2 for private-read canaries;
- 11 for spoof/tamper canaries;
- 2 for runtime interface fixtures.

The total is **185 of 200**, with 15 unallocated. That margin is not a retry allowance.

## Evidence labels corrected (MRL-05/06/07)

Itemized banners were added to [precision_plan_mrl05](precision_plan_mrl05_20260921.md),
[receiver_guard_mrl06](receiver_guard_mrl06_20260921.md) and
[implementation_plan_mrl07](public_diagnostic_implementation_plan_mrl07_20260921.md). They record:

- the grid is hypothetical arithmetic;
- the Monte Carlo is a synthetic simulation;
- the Bernstein column is a normal-plug calculation, and no column is finite-sample power-valid;
- 2,952 is a radius threshold, not a floor;
- the coupling claim is withdrawn;
- quarter-size scaling is scoped;
- no R is call-optimal;
- the guard grants no efficacy;
- sampled idle slots are not a lease;
- interface checks are runtime checks;
- field 15 is replaced as decided.

The 19 statically predicted behaviours are now bound to the 17 control artifacts by code sha256.
## Remaining execution-only checks (not done; each needs a separate lead release)

Each uses starts from the [proposed ledger](diagnostic_release_manifest_proposal_20260921.json) (ceiling 200). None may be retried silently.

| # | check | starts | pass criterion (frozen before running) |
|---|---|---|---|
| E1 | Fresh containment attestation on this host | 9 | 9/9 canaries started and contained, as in the 12:55Z attestation |
| E2 | Private-read canary from the public executor | 2 | the private spec read **fails**; the public case file read succeeds |
| E3 | Spoof/tamper canaries | 11 | every forged, duplicate, extra, flooded, alarm-reset, CPU-exhausted, wall-killed, exited, crashed or oversized case yields `unavailable`/`timeout`/`output_limit` as tabled, **never `pass`** |
| E4 | Runtime interface fixtures | 2 | missing entry point → `interface_error`; wrong arity → `interface_error` |
| E5 | Status-category fixtures | 5 | each yields exactly its tabled status |
| E6 | Public-instrument validation: 7 references | 7 | all 21 public cases `pass` |
| E7 | Public-instrument validation: 17 control artifacts | 17 | executed pass patterns compared with the static prediction (16/17 predicted rejected; the mbpp/378 empty-list control is predicted to pass all public cases). Disagreement is reported, not tuned away |
| E8 | Private re-validation under the rebound specs | 24 | 7/7 references pass, 17/17 controls fail, as in the 25/25 pre-registered v2 validation |
| E9 | Receiver freeze | 0 starts; read-only | fresh `/props` state digest, `sampler_law: server_defaults_pinned` equality, ownership evidence, `/apply-template` rendering of all six arms' message lists with saved bytes and digests (field 13) |
| E10 | Final literal-overlap audit on the rebound specs | 0 (static) | PASS/HOLD only |
| E11 | Development collection (77 calls) → public diagnostics (≤ 7 starts) → final grading (77 + ≤ 24 rechecks) | ≤ 108 | only after the lead releases the frozen package; descriptive analysis only |

## Disposition at 2026-09-21T18:45:02Z

**MRL-08: completed within its cap** (18:26:06Z → 2026-09-21T18:45:02Z, one worker). The full suite passes: 471 tests. Resource use:

- 0 model calls;
- 0 sandbox, reference, candidate or control executions;
- generated harness text was only `compile()`d;
- one `python3 collect_diagnostic.py --help` ran the project's own source;
- no network beyond `git`, no installs, no leases, $0.

**Remaining source work** is deliberately left for the freeze step and needs a new allowance:

1. real-mode wiring of `collect_diagnostic` (`verify_freeze` + `LlamaServer`), currently refused on purpose;
2. a CLI for Phase B with the attested `sandbox.run_program` runner;
3. landmark-v2 config files, whose `receiver_state_sha256` needs a fresh snapshot immediately before release.

**Decision needed from the lead (J7):** accept `study_adapter.grade_study` as the grading path for the
six-arm study (it reuses `grade.evaluate`/`extract_code`/`contract`/`verify_attestation` unchanged), or
require a versioned grader instead.
