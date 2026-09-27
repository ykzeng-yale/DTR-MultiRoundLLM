# Reuse of bounded strict execution — 27 September2026

Codex direct implementation. The common runner's communicate-then-truncate limitation does not require replacing all execution infrastructure. The existing **landmark strict runner** already writes each stream to a file under RLIMIT_FSIZE and bounds parent reads. It denies by default, refuses a bare-Python fallback and restricts execution to its pinned interpreter. Historical runner source remains unchanged.

## Executed evidence

[Current-host containment](../results/native_strict_containment_20260927/attestation.json):9/9 harmless probes pass, including own-directory access, denied home/peer reads and writes, denied loopback network/fork/system subprocess, and timed-out child cleanup. These are controlled checks, not an escape or denial-of-service proof. No benchmark or receiver code ran.

[Four output probes](../results/native_strict_output_probe_20260927.json): one-million-byte writes to stdout and stderr each return4,096 bytes with exit code0; a dual-stream3,000-byte write returns3,000 bytes per stream; a small print completes. The cap is per file/stream, not a combined4,096-byte quota. The two flood programs demonstrate that partial OS writes can exit successfully, so process exit0 is not a sufficient outcome signal. Candidate-created extra files and total filesystem growth are not bounded by this per-file cap; no overall disk-quota claim follows. Memory limits remain best effort on macOS.

## Adapter decision

[Native execution adapter](../experiments/prompt_choice/native_execution_v1.py) reuses that strict runner without expanding file access. It reports timeout, output_limit, process_error or completed_ungraded. Exact saturation of either stream, or SIGXFSZ, is conservatively output_limit even with exit0; timeout retains a simultaneous saturation flag. Decoded replacement characters can overestimate raw-byte length, another explicitly conservative limit. Neither literal `PASS` printed by a payload nor a clean exit becomes a test pass or public feedback.

Every disposition has `test_outcome=null` and `feedback_status=null`. A trusted, separately audited grading layer remains necessary. The adapter validates source size (at most1MiB), wall cap(0–10s), CPU cap(1–5s), requested memory(positive, at most2GiB), and per-stream cap(1–256KiB) before dispatch. It does not authenticate arbitrary caller-supplied process records; the integrated path must retain trusted parent provenance.

[Final classification receipt](../results/native_output_classification_final_20260927.json) classifies the two flood records as output_limit and the other two as completed_ungraded. The earlier receipt binds the pre-limit-validation source and is retained rather than overwritten. Forty-five affected tests pass, including malformed-record refusal, both-stream saturation, simultaneous timeout/limit retention, no candidate-output grading and invalid-limit refusal before dispatch. No benchmark outcomes are inferred.

## Remaining qualification

The validated path still uses `-I -S`; third-party dependencies remain unavailable. Before a native reference/control audit, define a pinned dependency bundle and minimal read allowance, re-run containment, test trusted result transport and source separation, and freeze the exact endpoints and controls. The first-method-public partition remains unreleased. This work removes the need to invent a second bounded-output runner; it does not release collection or change the receiver.

Full-project readiness **60%, change0 percentage points**. Population/measurement, complete prospective freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete. Goal active; direct Codex implementation, no Claude delegation.
