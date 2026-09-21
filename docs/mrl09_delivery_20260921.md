# MRL-09 delivery: grading protections, strict diagnostics, durable Phase B, real-mode wiring, templates

**Experiments workstream.** Processed lead revision `5f02823` (decision in `956cbfd`). Started 2026-09-21T19:08:53Z
and completed at 2026-09-21T19:23:13Z, inside the 30-minute cap on one CPU. Usage:

- **0 model calls, 0 receiver generations, and 0 sandbox, reference, candidate, canary or control executions.**
- Generated harness text and canary text were only `compile()`d.
- The static `hack_gate` was applied to canary text.
- No installs, no leases, $0.

The full suite passes: **578 tests** (`scripts/check_tests.sh`, exit 0).

## Items the lead required, and where they are

| requirement (`mrl08_independent_review_20260921.md`) | implementation |
|---|---|
| **J7 grading protections**: `validate_specs` against the frozen public tasks; expected contract digest; verified phase checksums and exact root/family/arm/replicate coverage; verified source hashes; stale prose removed | `study_adapter.grade_study` refuses before any runner call unless all of these hold: <ul><li>the frozen tasks file bytes match their sha256, parsed strictly;</li><li>`grade.validate_specs` passes;</li><li>`grade.digest(grade.contract(specs))` equals the expected digest;</li><li>every checksum in both phase directories verifies, and the checksum set equals the files present;</li><li>both phase configs hash to the expected config digest;</li><li>the assignment table equals the one derived from the frozen config;</li><li>the (root, family, arm, replicate) coverage is exact (STOP at replicate 0 only; bools refused);</li><li>the view rebuilt from the verified directories equals the given view;</li><li>the expected source-hash mapping (adapter, grade, sandbox, common/integrity, collect, diagnostic, collect_diagnostic, analyze) matches on disk.</li></ul>`grading_source_hashes()` computes the mapping for freezing. The attestation gate stays, and only a declared fake runner skips it. |
| **Strict diagnostics**: no `TypeError`; duplicate keys rejected; pass/wrong_value consistent with the expected value | Non-string status/value_kind/reason raise `ValueError`. Malformed literals raise `ValueError` through `diagnostic.literal()`. `diagnostic.strict_json_loads` rejects duplicate keys at any depth and is used for every untrusted JSON (result lines, diagnostics, manifests, roots, config/tasks/examples in the CLIs). For `int`/`int_list`, pass requires `returned == expected` and wrong_value requires inequality. A `none` return cannot pass an int expected value. `unsupported` keeps the in-isolation equality result |
| **Durable Phase B**: output directory and attempt ledger reserved before dispatch; each start and result persisted; no uncharged rerun | `public_phase.run_phase_b` validates every input first, including every example against the diagnostic policy, so nothing is reserved for a refusable input. It then creates `out_dir` and `attempts.jsonl`, fsyncing each record: `reserved` (with runner and attestation provenance), then per call `start` (a nonce *digest*), `result` and `classified`, then `complete`. On any exception it writes `incomplete` and `INCOMPLETE`; nothing is deleted. An existing `out_dir` is refused |
| **Executor provenance**: `public_phase.py`, `common/integrity.py`, the runner and the attestation | The manifest carries source sha256s for public_phase, public_check, diagnostic, sandbox, grade and common/integrity; the runner's module, qualname and source sha, unwrapping `functools.partial` and `__wrapped__`; and the attestation's sha256, all verified fields and check names. `attestation=None` is allowed only for runners marked `FAKE_RUNNER` |
| **Real mode**: opt-in; refuses an incomplete freeze, attestation or ownership record | `collect_diagnostic --real --ownership OWN` refuses before any request on any of these: <ul><li>a value starting `UNRESOLVED:`, including in raw bytes behind a duplicate key;</li><li>`collect.validate(real=True)` failing, or not landmark-v2;</li><li>an ownership record that is incomplete, uses placeholder text, has a wrong `base_url`, or whose window does not contain now **plus max_seconds**;</li><li>a failed `collect.verify_freeze`;</li><li>an injected adapter.</li></ul>The window end is also a **dispatch guard**: expiry stops future requests and keeps outputs. A real continue phase refuses an initial phase that is mock, from a different freeze commit, or under a different ownership record. It uses `collect.LlamaServer(config)` |
| **Attested Phase B CLI** | `python -m experiments.landmark.public_phase --initial-dir I --examples P --out O --attestation A --real` refuses without `--real`, refuses `UNRESOLVED:` arguments, and runs `grade.verify_attestation` first. The attestation sha is checked before and after. Only then is `sandbox.run_program` used |
| **Templates** with explicit unresolved fields | `experiments/landmark/dev_release_v2_template/`: <ul><li>a config with every landmark-v2 key; known frozen values filled; 15 `UNRESOLVED:` fields, including `receiver_state_sha256` (fresh non-generating `/props` preflight) and the dataset, contract, source and freeze digests;</li><li>an ownership record, all `UNRESOLVED:`;</li><li>a release manifest with the E1–E10 gates, the start ledger, caps and **J7 grading bindings** (frozen tasks, contract, config, source and executor hashes);</li><li>a README saying which authorized step resolves each field.</li></ul>`collect.validate(real=True)` refuses the template as it stands |
| **E1–E10 commands** with frozen canary inputs and expected statuses | [`e1_e10_validation_plan_20260921.md`](e1_e10_validation_plan_20260921.md): the exact commands, frozen-input sha256s (recomputed after the review fixes), starts and expected outcomes, marked **NOT RUN**. `experiments/landmark/validation_canaries_v1.json` (sha256 `ec6f81e3…`) holds 18 frozen canaries (E3 11, E4 2, E5 5) on a synthetic `f(x)=x+1` task, each with expected statuses, an acceptable set and never-pass cases tied to the precedence table. The `validation_canaries` CLI is opt-in and attested, and writes its ledger before dispatch |

## Adversarial review (three lenses; every finding demonstrated on fakes)

There were 12 findings, **all fixed**:

- **Blocker, J7:** the coverage plan was derived from the phase's own config, not the frozen one. Fixed with
  `expected_config_sha256`.
- **Major:**
  - duplicate keys were accepted in `roots.jsonl` and the view manifest;
  - a `pass` with no return was accepted against an int expected value;
  - a malformed example was detected only after runner starts had been charged;
  - the attestation guard could be bypassed by an incomplete record or a wrapped real runner;
  - the ownership window was checked once and not during dispatch;
  - a real continue accepted a mock initial phase.
- **Minor:**
  - a bool replicate passed coverage;
  - an artifact could be read from outside the checksummed phase directory;
  - malformed literals raised `SyntaxError`;
  - the ledger's `reserved` record lacked attestation provenance;
  - the CLI loaded the config with plain `json.loads`.

When I tightened a test's expected message, a **13th defect** surfaced and is fixed. `assert_public_inputs_only`
refused macOS temp paths under `/private/var/…`, which the docstring says are exempt. The earlier test passed
only because it matched any `ValueError`.

**Process caveat:** most regression tests were written alongside their fixes. The pre-fix reproduction for
findings 1–12 is the reviewers' scratch counterexamples.

## Behaviour changes callers must know

- `grade_study` now requires the frozen tasks path and sha, the expected contract, config and source hashes,
  and both phase directories. A partial spec set is refused.
- `run_continue` requires the public examples. In real mode it requires the same freeze and ownership as the
  initial phase.
- Phase B never reruns into an existing directory.
- The source hashes of `collect_diagnostic`, `diagnostic`, `public_check`, `public_phase` and
  `study_adapter` have changed. Nothing was frozen against them yet.

## Still unresolved, by design

All fresh runtime values remain `UNRESOLVED:` until the lead separately authorizes a non-generating preflight
and the freeze:

- the `/props` state digest;
- the ownership record;
- the attestation;
- the dataset, contract, source and config digests at the freeze commit.

E1–E10 (185 of 200 starts in the ledger) and the 77-call collection remain unreleased.
