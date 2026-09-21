# dev_release_v2 templates (MRL-09) — NOT a release

Templates only. Every value not yet frozen is the literal string `UNRESOLVED:<what resolves it>`. Every real-mode
entry point refuses any config/manifest/ownership value starting with `UNRESOLVED:`, and `collect.validate(..., real=True)`
refuses these templates (non-integer seeds/caps, non-hex digests). Nothing here authorizes a run.

Filled from the frozen proposal (`docs/diagnostic_release_manifest_proposal_20260921.json`): model, model_digest,
server_build `b1-4fea119`, base_url `http://127.0.0.1:8193`, decoding (0.7 / 0.95 / 8192), the eleven observed sampler
defaults, sampler_law `server_defaults_pinned`, max_tokens_per_call 512, max_calls 77, max_completion_tokens 39424,
max_seconds 1200, branch_replicates 2, paid budget 0.

| Value | Resolved by | Separately authorized step |
|---|---|---|
| receiver_state_sha256, template_render_sha256 | fresh nongenerating read-only `/props` and `/apply-template` preflight | E9 (lead authorization; 0 starts, no generation) |
| ownership.template.json (all 9 fields) | written exclusive-use agreement, server PID/start from `ps`, window | E9 (recorded by the operator; `collect_diagnostic.validate_ownership` checks window contains now and base_url equality) |
| dataset_sha256, grading_contract_sha256, dataset_source, dataset_license, prior_seen_* | `scripts/build_dev_release_v2.py --output work/...` | release build (lead authorization) |
| source_code_sha256, freeze_commit, protocol_version, seeds, split_fractions, request_timeout_seconds, max_request_bytes | the freeze commit (`collect.source_hashes()` at that commit) | lead-authorized freeze |
| containment_attestation_sha256 | `scripts/check_landmark_sandbox.py --runner landmark --output ...` | E1 |
| overlap_audit_verdict | final literal-overlap audit on rebound specs | E10 |

Order: build (E10 inputs) -> freeze commit -> E1 -> E2..E8 -> E9 immediately before collection -> lead release -> E11.
See `docs/e1_e10_validation_plan_20260921.md`.
