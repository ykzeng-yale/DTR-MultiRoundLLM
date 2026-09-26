# MRL-33 independent source acceptance

Codex scientific lead, 26 September 2026. Accept worker `fc5c59d` within source-only scope. Full source/config/test review and independent `uv run --offline --frozen --extra dev pytest -q`: **1,948 passed and 8 subtests passed, zero failures in 31.05 seconds**. Hashes before and after the suite match the delivery. There are 35 new focused tests; source tests are not endpoint outcomes.

The two lead-requested corrections are present: the original-example table lives inside its function, avoiding a public output-format confound; production `build(source_path)` accepts no pin/hash overrides and records actual source/config hashes, while injected synthetic fixtures use a visibly different version. Private implementation helpers are not a provenance/security boundary. Public records contain only the original description/signature/first assertion and its parsed literal case, separate from reference, remaining assertions, supplements and controls. The source module has no execution/receiver/network path.

I independently rebuilt twice from the pinned `work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl`; canonical outputs agree and original code/assertion pins remain intact. Exact package identities:

- Public 877: `fc906f9537fe4cb900e63894a149fcba4618843857d063cb824b72f4ecfb2183`.
- Public 345: `afa9822bd522fba27130be374f72c66689a48d901ee71abb9820e23b1b1d4b45`.
- Private 877: `4619699141efe87be10688478b43b400d14dfe5b9e9b8dbcde06fb94baadbb7b`.
- Private 345: `20d4defc48000d4e9fa5bbf37b3687961c0db17c5af1f5cd75cfcbb3ef319b55`.

- `experiments/prompt_choice/endpoint_audit.py`: `aa6a4d2ed6fce474a9a0defb721e5ec6e547161aaa592e1e87a36c07978acad1`.
- `experiments/prompt_choice/endpoint_audit_source_v1.json`: `cf3885d50d8393d6c68f9750775beb994f104f548b81c43ff62bae50e4b55c51`.
- `tests/test_prompt_endpoint_audit.py`: `5bf80ce378453654172be2be96d01f17d0b6943bbe319f678002770fbe02aecc`.

Worker completion 22:18:39Z is within the reported 22:10:51–22:30:51Z cap. These times are worker receipts; source identities and local tests were independently checked. No benchmark/reference/control/model program ran in this source review. The separate [current-host containment check](policy_endpoint_containment_plan_20260926.md) passed 9/9 harmless canaries and current grader verification; it has no endpoint outcome.

MRL-33 is closed. A later audit must bind these exact package hashes, source/interpreter/host/attestation and a finite execution plan. Reference acceptance and every control prediction are still untested. The unchanged original-private battery and new supplement must remain separately reported; this prospective endpoint candidate is not a historical endpoint correction. The original research objective still requires untouched-family evaluation under justified sampling/execution laws.

Full-project readiness **58%, change 0 points**. No empirical policy-validation credit is earned. Endpoint execution, family/exposure/sampling design, complete trial freeze and independent policy evaluation remain open.
