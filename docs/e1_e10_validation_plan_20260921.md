# E1–E10 validation plan (MRL-09) — NOT RUN; requires separate lead authorization

## Corrected ordered bundle (MRL-10, experiments workstream) — supersedes the table below

The lead's five repairs and two added acceptance criteria are applied. **E9 and E10 are DONE**, both
non-executing. **E1–E8 are HOLD** until the lead releases this bundle as one ordered job with stop conditions;
**E11 is not authorized**.

\`RUN=work/validation_bundle_v2_<UTC at release>\` is a new, non-existent directory. Every driver refuses to
overwrite, verifies the attestation first, writes an fsynced start/result ledger, never retries, and reports
actual starts separately from the planned maximum.

| order | gate | exact command | frozen inputs (sha256) | planned starts | pass criterion (frozen) | stop condition |
|---|---|---|---|---|---|---|
| 1 | E1 | \`uv run --extra dev python scripts/check_landmark_sandbox.py --runner landmark --output $RUN/attestation/\` (a **directory**; consumers use \`$RUN/attestation/attestation.json\`) | check_landmark_sandbox.py \`8683429158451a82662f618e65b73b3d13c87e4c8e9ca709f1bf61cc0e17f83b\` | 9 | 9/9 canaries started and contained; \`passed: true\` | any canary escapes or fails to start → stop the bundle |
| 2 | E2 | \`uv run --extra dev python -m experiments.landmark.public_instrument_validation --items experiments/landmark/public_instrument_items_v1.json --items-sha256 91dd499bf2799aa4de467d1956f36370631de5abf741f1b92ee73ed0c58bc10e --gate E2 --out $RUN/e2 --attestation $RUN/attestation/attestation.json --real\` | items \`91dd499bf2799aa4de467d1956f36370631de5abf741f1b92ee73ed0c58bc10e\` (canary targets the committed \`dev_release_v2/private_specs.jsonl\` \`b3457f7de452b52bb273ce8b10f49b5db878dc219b8bf3d304389f104598a2c1\`); driver \`97a60c478e1a02b5e0d528b636006ef4546ea961d783d044367be16afcb75503\` | 2 | canary: every case passes with the returned-if-denied value and **no private bytes in stdout**; positive control: permitted read succeeds | a private byte in stdout, or the positive control fails → stop |
| 3 | E3–E5 | \`uv run --extra dev python -m experiments.landmark.validation_canaries --canaries experiments/landmark/validation_canaries_v1.json --out $RUN/e3_e5 --attestation $RUN/attestation/attestation.json --real\` | canaries \`ec6f81e3f254f983bb795ba0420c7b65509ef1b2c21233e2ebc4fbba69190e47\` (18: E3 11, E4 2, E5 5); driver \`5b57f869801157598d198e8a3bc768114804c8009c194b429553b0edd8bdc6ba\` | ≤ 18 (static-gate canaries start nothing; actual reported separately) | each canary's observed statuses in its \`acceptable\` set; never-pass cases never \`pass\` | any never-pass case observed as \`pass\` → stop |
| 4 | E6 | as E2 with \`--gate E6 --out $RUN/e6\` | items as above | 7 | all 21 public cases \`pass\` for the 7 references | any reference fails a public case → stop |
| 5 | E7 | as E2 with \`--gate E7 --out $RUN/e7\` | items as above; predictions bound by control code sha256 | 17 (one per control, root/control identity preserved) | each observed pattern **reported against** the static prediction (16/17 predicted rejected); disagreement reported, not tuned; unexecuted items counted separately | none; this gate reports |
| 6 | E8 | \`uv run --extra dev python -m experiments.landmark.validate_rebound_references --specs experiments/landmark/dev_release_v2/private_specs.jsonl --specs-sha256 b3457f7de452b52bb273ce8b10f49b5db878dc219b8bf3d304389f104598a2c1 --tasks experiments/landmark/dev_release_v2/tasks.jsonl --out $RUN/e8 --attestation $RUN/attestation/attestation.json --real\` | specs \`b3457f7de452b52bb273ce8b10f49b5db878dc219b8bf3d304389f104598a2c1\`; validator \`2a48480605b0c25f86b05d4d41372aabc47ef18eecef6f5289229f6a7a08d69d\` (no 402 special case; historical \`validate_references.py\` preserved unchanged) | 24 | 7/7 references pass, 17/17 controls fail (\`matches_expected\`) | anything else → stop; grading is not releasable |
| — | E9 | **DONE**: \`scripts/receiver_preflight_mrl10.py\` | \`results/receiver_preflight_mrl10_20260921T194506Z\` | 0 (47 loopback requests: GET /slots, /props, /v1/models, POST /apply-template ×42) | state \`1b8bf998…\` unchanged before/after; sampler equals pinned; 42 six-arm renderings verified | — |
| — | E10 | **DONE**: \`scripts/check_public_diagnostic_examples_20260921.py --examples docs/public_diagnostic_examples_v1.json --private-specs experiments/landmark/dev_release_v2/private_specs.jsonl --out <new> --expected-case-count 21\` | \`results/public_diagnostic_examples_audit_v2_20260921T195217Z.json\` | 0 | **PASS**, 21/21, no literal overlap (tuple/list-normalized) | — |

**Planned starts:** 9 + 2 + ≤18 + 7 + 17 + 24 = **≤ 77**, inside the 185-of-200 ledger. Final grading (77 + 24
rechecks) and Phase B diagnostics (≤ 7) belong to E11 and are not released.

---

## Superseded table (MRL-09); kept for the record

Nothing in this document has been executed. Each gate below needs its own lead authorization. Starts match the proposal
ledger (`docs/diagnostic_release_manifest_proposal_20260921.json`, sha256 `ca0164536f50e3d114414e2ee879bfd066ca821a414babec7365e50ed93aae48`):
E1 9 + E2 2 + E3 11 + E4 2 + E5 5 + E6 7 + E7 17 + E8 24 + E9 0 + E10 0 = 77 starts (integrity 24, core 53 of the 161 core). No retries.
Hashes below were recomputed after the MRL-09 review fixes (commit of this file); they are still re-verified at the freeze commit.

| Gate | Command (exact) | Frozen inputs | Starts | Expected | Resolves |
|---|---|---|---|---|---|
| E1 | `python scripts/check_landmark_sandbox.py --runner landmark --output work/mrl09/attestation.json` | scripts/check_landmark_sandbox.py `8683429158451a82662f618e65b73b3d13c87e4c8e9ca709f1bf61cc0e17f83b` | 9 | 9/9 canaries started and contained; `passed: true` | containment_attestation_sha256 (valid 24 h) |
| E2 | `python -m experiments.landmark.public_phase --initial-dir work/mrl09/e2_private_read --examples <public cases> --out work/mrl09/e2 --attestation work/mrl09/attestation.json --real` with the private-read canary artifact | public_check.py `a42fbc9879027598db0378a58884c2181312fbad54cc27ece2632795f7d4d154` | 2 | private spec read fails; public case file read succeeds | public-executor read isolation |
| E3 | `python -m experiments.landmark.validation_canaries --canaries experiments/landmark/validation_canaries_v1.json --out work/mrl09/e3_e5 --attestation work/mrl09/attestation.json --real` (one invocation covers E3–E5) | validation_canaries_v1.json `ec6f81e3f254f983bb795ba0420c7b65509ef1b2c21233e2ebc4fbba69190e47` | 11 | per canary `expected` (acceptable set in `acceptable`); forged/duplicate/extra -> all `unavailable/protocol_integrity_review`; flood -> `output_limit`; alarm reset, CPU exhaustion, wall kill -> `timeout`; sys.exit -> `program_exception` on that case; os._exit -> `program_exception` then `not_attempted_after_termination`; RecursionError -> `program_exception`; oversized -> `wrong_value`; never `pass` on a tampered case | spoof/tamper handling |
| E4 | (same invocation as E3) | same | 2 | missing entry point -> `interface_error` x3; wrong arity -> `interface_error` x3 | runtime interface statuses |
| E5 | (same invocation as E3) | same | 5 | wrong_value x3; program_exception x3; [timeout, pass, pass]; [pass, output_limit, unavailable]; [pass, program_exception, unavailable] | status categories |
| E6 | `python -m experiments.landmark.public_phase --initial-dir <7 reference artifacts> --examples <public cases> --out work/mrl09/e6 --attestation work/mrl09/attestation.json --real` | references from the build output (UNRESOLVED: build sha) | 7 | all 21 public cases `pass` | public instrument on references |
| E7 | as E6 with the 17 control artifacts, `--out work/mrl09/e7` | results/public_checker_static_discrimination_20260921.json (prediction) | 17 | compare with static prediction (16/17 rejected; mbpp/378 predicted all-pass); disagreement reported, not tuned | public instrument on controls |
| E8 | `python -m experiments.landmark.validate_references --specs <rebound private specs> --attestation work/mrl09/attestation.json --out work/mrl09/e8.json` | validate_references.py `feb86670ff8b9b26cfb2816ac780d25ba9a214f4649bef9f8ca4a7b729ae953d`; specs from build (UNRESOLVED) | 24 | 7/7 references pass, 17/17 controls fail | private re-validation under rebound specs |
| E9 | read-only `/props` and `/apply-template` preflight (nongenerating) + completed ownership record, then `python -m experiments.landmark.collect_diagnostic --phase initial --config <resolved config> --tasks <tasks> --output <dry> ` validation only (no `--real`) | experiments/landmark/dev_release_v2_template/*.json | 0 | state digest recorded; sampler equality under `server_defaults_pinned`; ownership window contains now; six-arm render bytes/digests saved | receiver_state_sha256, ownership, template_render_sha256 |
| E10 | `python scripts/build_dev_release_v2.py --output work/dev_release_v2_<date>` then the final literal-overlap audit on the rebound specs | build_dev_release_v2.py `50962cd488ab8d3d8af9ac27e5f54fc72b90f80310353481ce05538b4e7d258e` | 0 (static) | PASS/HOLD only | dataset/grading digests, overlap verdict |

Open item: no standalone literal-overlap audit script exists in `scripts/` or `experiments/` at writing (build_dev_release_v2.py lists
it as pending); E10's audit command is UNRESOLVED until that script is written and frozen.
E11 (77 calls, <=108 starts) is outside this plan and needs the lead's release of the frozen package.
