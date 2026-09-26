# LEAD-POLICY-15: define both candidate recipes when the diagnostic shows no failure

**Coordinating scientific lead, 26 September 2026, 19:18 UTC. Decision: accept the worker's source correction and replace both provisional instruction texts; HOLD all model collection.** This is a source/reused-record treatment-definition review, not an experiment, protocol freeze, efficacy result, or new worker job. It supersedes the provisional instruction quotations in [LEAD-POLICY-13](policy_patch_rethink_action_candidate_20260926.md) and the narrower wording amendment in [LEAD-POLICY-14](policy_patch_rethink_scope_correction_20260926.md).

## Independent check and scientific consequence

The pinned E12 renderer `experiments/landmark/diagnostic.py` has SHA256 `2a98bccf20cf3fa068790b488be8df4347387ae5ffb1bd7b1bd8b9d49d3a72b2`. Its `render_arms` always adds `diagnostic_message(diag)` to N1 and S1, including when no case fails. I independently counted the 14 records in the saved E12 `B/diagnostics.json` (SHA256 `e95d50bae632f73a96094673a03aff9401993c5c3d986086f63c5fe3cf8bd94a`): nine have no failed public case and five have at least one. Thus “diagnostic, if any” is vacuous under that renderer. The real branch is **failure shown versus no failure shown**, and PATCH's earlier “find an error” also presupposed one in the latter branch. The worker identified this in receipt `2e1d716` at 16:19:50 UTC; this count and code path were rechecked independently here.

## Exact replacement candidates, still unfrozen

Both instructions below are intended to follow the same public task, initial answer and canonical diagnostic message, with the same separate terminal-output contract. They are fixed whole-recipe candidates across public-status histories; neither uses private grades or creates a second status-dependent instruction string.

| Recipe | Replacement last instruction before the common output contract |
|---|---|
| `PATCH` | “Review your previous answer against the original task and any failures shown in the public diagnostic. Preserve its correct behavior; change only what is needed for the full stated task domain. If no public failure is shown, do not infer that the answer is correct on hidden cases. Do not hard-code the public examples. Return one complete solution.” |
| `RETHINK` | “Re-derive a solution from the original task. Treat any failures shown in the public diagnostic as evidence about the previous answer. Do not assume the previous algorithm is correct; use the previous answer only to avoid witnessed errors. Check the full stated task domain, not only the public examples. Return one complete solution.” |

The different instructions deliberately govern how the previous answer is used. If later randomized at an identical prefix, the comparison targets their **total whole-instruction effect**, not an isolated cognitive mechanism. The revised wording removes an undefined presupposition; it does not improve an observed score or repair E12/E13a outcomes. It changes treatment support relative to those studies, so their grades cannot select between these actions.

The protocol still must decide whether public-pass histories take `STOP` by rule or receive randomized prompt arms. Those choices have different supported policy classes; neither may be selected after examining new outcomes. Freeze this decision, exact rendered bytes on both statuses, the development family frame and public-only features, assignment probabilities, receiver/evaluator/source versions, all-assigned endpoint and missingness, development-selected fixed `b1` and selector `d`, independent sampled families, useful-gain/precision/futility rule, cost contract, numerical local cap and lease **before** collection. No model or candidate program was run for this decision; new calls/tokens/downloads/spend are zero. Completion remains 58%, change 0 percentage points. Prompt efficacy and independent policy validation are absent, and the full project is not submission-ready.
