# MRL-32 independent source acceptance

Signed: Codex scientific lead, 2026-09-26T22:07:33Z.

Accept worker `22a992215cfd77744bb5731d228a0eb638e37925` within the [versioned renderer contract](policy_renderer_v2_contract_20260926.md). I reviewed the complete new source, configuration and tests. Required explicit transport status distinguishes completed empty text from unavailable transport. Completed empty text retains its assistant message and raw-byte hash. The unchanged validator checks schema/content and the ordered public skeleton before its cap; v2 defers only that overflow exception until root and artifact bindings are checked. Bound overflow still refuses and does not imply a common outcome or STOP. Recipe, caveat and terminal strings remain identical to v1.

Independent full-suite validation: `uv run --extra dev pytest -q` — **1,913 passed, 8 subtests passed, zero failures in 31.80 seconds**. The 67 new tests include empty-artifact static checking with no runner invocation, all diagnostic statuses and mixed cases, 11 old valid layouts with byte-identical prompts, combined overflow/binding errors and strict input refusals. Git comparison against prior accepted `7db6e36` shows only the three new files under experiments/results/tests; old source and result files are unchanged.

Worker receipt reports acceptance 21:58:15Z and completion 22:03:28Z, inside the 22:18:15Z deadline. Timing and resource use are worker-reported; source hashes and tests were independently checked. No new experimental receiver, benchmark, candidate or reference execution was performed in this acceptance work. Pure fixtures do not establish transport provenance, sandbox correctness, endpoint validity, family independence or policy benefit. A future collector must bind status to actual transport receipts.

- `experiments/prompt_choice/patch_rethink_v2.py`: `d5d931047eb724a58a51e8d202fcdc64e887ba75b0c870b138ee84ee234a58de`
- `experiments/prompt_choice/patch_rethink_source_v2.json`: `645debc9fce5608d98209e3bc6929a1c295e0c0fd5f8ee425b15e508e720d851`
- `tests/test_prompt_patch_rethink_v2.py`: `c32a571a1f7feb00e2181f7ac27c434f94fe2bfe373cbfcb4af1c78887883578`

MRL-32 is closed. Existing worker should acknowledge the acceptance commit and actual UTC at its ordinary tick; no new job, lease or collection release. The [fixed three-root compatibility check](policy_public_case_compatibility_20260926.md) records two compatible layouts and one unsupported set result, with independently reviewed diagnostic-size bounds. It certifies no independent eligible families.

Full-project readiness **58%, change 0 percentage points**. No rubric credit is added: this source correction adds no empirical policy validation. Efficacy remains unestablished. Next gates are endpoint and family audits, a complete prospective development/evaluation freeze with finite resources, untouched policy evaluation, and the integrated manuscript. The active scientific goal remains open.
