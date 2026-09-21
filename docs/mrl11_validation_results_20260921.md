# MRL-11: E1–E8 instrument-validation bundle results

**Experiments workstream.** Processed lead revision `b2f093c` (release `02bf71a`); frozen sources and inputs at
`0bb2388`. The run went into `work/validation_bundle_v2_20260921T201642Z`, with an immutable copy at [`results/validation_bundle_v2_20260921T201642Z/`](../results/validation_bundle_v2_20260921T201642Z/). The per-file hashes are
in `ARTIFACT_SHA256SUMS.json` (sha256 `73c7424bdcc95c942b810d9c147f49bae32f3ed16036b44041492604c459d38e`).

**The bundle ran from 2026-09-21T20:16:42Z (acknowledged) to 2026-09-21T20:18:12Z (E8 finished): about 1.5 minutes.**

- One CPU; sequential starts; the existing `.venv` interpreter (`cpython-3.12.13`), offline.
- No installs, no downloads, no server changes.
- **0 receiver, model or generation requests.** $0.
- **77 isolated starts of the 77 allowed; no retries.**

**Prechecks before any start.** All 7 bundle inputs are byte-identical to `0bb2388`, and every hash in the
corrected plan matches. The E2 private target exists with sha `b3457f7d…`. The positive-control file
exists under the attested interpreter prefix.

My first precheck script printed PASS while its pattern had matched **zero** file→hash pairs, so that PASS
meant nothing. I caught this and re-ran it properly (7 of 7 matched) before E1. No start happened before
the valid precheck.

| order | gate | starts | mandatory verdict | result |
|---|---|---|---|---|
| 1 | E1 containment attestation | 9 | `passed=true`; 9/9 required checks started and contained | **PASS**: own-run read/write, home read, home write, peer-run read, outside-home tmp write, loopback network, system subprocess, fork creation, timeout and process cleanup, all contained |
| 2 | E2 private-read isolation | 2 | `all_meet_expected`; private read denied; permitted read succeeds; no private output | **PASS**: canary [pass×3] via the denied-read branch; `private_bytes_in_stdout=false`; positive control [pass×3] |
| 3 | E3–E5 canaries | 18 | `all_within_acceptable=true` and `any_forbidden_pass=false` | **PASS**: **18/18 matched their exact expected statuses**, not merely acceptable ones; 0 decided statically; forged, duplicate and extra lines → `protocol_integrity_review`; flood → `output_limit`; alarm reset, CPU exhaustion and wall kill → `timeout`; missing entry point and wrong arity → `interface_error` |
| 4 | E6 references on public cases | 7 | `all_meet_expected`; 21/21 public cases pass | **PASS**: 21/21, including 402's p = 1 case with the repaired reference |
| 5 | E7 controls vs frozen static predictions | 17 | descriptive | **17/17 executed, 0 unexecuted, 0 disagreements.** Every observed public pass pattern equals its frozen prediction; 16/17 controls are rejected by the public cases. The exception is mbpp/378 control2 (the empty-list bug), which passes all public cases as predicted and is caught only by the private suite (E8) |
| 6 | E8 rebound private-suite validation | 24 | `matches_expected=true`; 7 reference and 17 control jobs | **PASS**: 7/7 references pass and 17/17 controls fail; runner `sandbox.run_program` (`ea7eed94…`); attestation `74389aa7…` |

## What this establishes, and what it does not

**Establishes.** On this host, interpreter and sandbox profile, over these finite canaries and suites:

- the isolated executor contains the nine tested behaviours;
- the public executor cannot read the committed private specs;
- tampered or abnormal output streams never yield `pass`;
- the public instrument accepts all references and reproduces the predicted control behaviour exactly;
- the rebound private suites separate all references from all controls.

Every start, result and incomplete state was ledgered; there were no incomplete states. No private assertion
text appears in any artifact (checked).

**Does not establish:**

- containment against adversarial code, on other hosts, or beyond the 24-hour attestation;
- grading completeness beyond these finite suites;
- that the public diagnostic is informative for repair;
- anything about prompt efficacy.

**E11 (the 77-call development collection) is not released.** Receiver ownership remains `UNRESOLVED`,
and I will not invent an agreement.
