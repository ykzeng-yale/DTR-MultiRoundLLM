# MBPP contract disposition and precision gate

Codex scientific lead, 29 September 2026. This resolves the next decision after the joint-admissibility bound: whether the saved contract proposals can be accepted as one uniform clarification batch, and whether the provisional remainder could support the existing evaluation precision rule. It uses the pinned MBPP source and public examples plus the already accepted inference contract. It does not execute references, assertions, benchmarks or model-written code, and does not inspect private test outcomes.

## Contract ruling

Do not promote the 36 `clarification_required` labels to accepted contracts as a batch. The label records a proposed wording, not evidence that the wording preserves the original objective. A source comparison exposes concrete differences that need row-level decisions:

| Root(s) | Source-level issue | Lead disposition |
|---|---|---|
| 700 | The proposed “integer list” excludes the original public string-list example `['a', …, 'f']` with bounds `'a'` to `'e'`. | Reject this wording; a replacement must preserve both numeric and ordered-string examples or document a new target. |
| 911, 883 | The source prompt explicitly asks for a heap-queue algorithm / lambda, while the proposed contracts specify only output behavior. | Preserve the method clauses in any faithful task statement. The current output-only endpoint cannot verify those clauses, so it cannot certify full prompt compliance. |
| 340 | “Three lowest positive numbers” is turned into “up to three” when fewer than three are present. | This is a new edge-case convention, not settled by the three public examples. Hold pending a declared interpretation. |
| 828, 192 | Python `isalpha`/`isdigit` semantics are selected for natural-language “alphabet/digit/number” terms. | Treat as a versioned character-classification convention requiring explicit adoption; do not imply the prose uniquely entails Unicode behavior. |
| 903 | “Unset bits” is made to mean zeros in minimal binary representations, excluding leading zeros. | This chooses a width convention not stated in the task. Hold until the intended bit-width rule is fixed. |
| 814 | The old claim that the float return requires a diagnostic schema change was withdrawn on 27 September. | Keep that correction: authentic pass/fail with an undisplayed returned float is supported by the current diagnostic. The family exclusion and other domain/measurement checks remain. |
| 344, 194, 302 | The references use floating-point division/square-root operations where exact integer behavior is required at unbounded magnitudes. | Keep the three reference holds; do not shrink their domains to make the references pass. |
| 524, 176, 711, 961 | The earlier source review records, respectively, unresolved empty/all-negative subsequence behavior, an original degenerate triangle example, an empty alternating-digit product convention, and a Roman-numeral grammar conflict with `MMMM`. | Keep all four holds; no silent domain repair. |

The remaining proposed wording is retained as candidate clarification text only. It can help a later task-by-task contract review, but neither the original prompt nor the supplied examples establish the untested input boundaries, return semantics and endpoint behavior needed to freeze those rows. This is a conservative source disposition, not a claim that all 43 tasks are intrinsically unusable. It preserves the original MBPP population and every previous result. In particular, 814's corrected display interpretation must not be counted as a reason for exclusion, and its explicit prior-family relation remains independently sufficient to keep it out of untouched evaluation.

Consequently, the joint admission result remains **0 currently admissible roots**. This review changes the rationale: the 36 clarification labels are heterogeneous proposals, and at least one proposal (700) directly conflicts with a public source example. It does not create a roster. A future contract can be accepted only with a row-specific, source-linked rationale that preserves all public examples and the stated task objective, makes any genuinely new convention explicit, and binds a validated outcome instrument. Method requirements that the outcome instrument cannot observe must be reported separately rather than treated as measured correctness.

## Precision consequence under the existing rule

The accepted primary two-contrast sign-split KL interval spends `alpha/8` per one-sided mean. If every observed paired family contrast is exactly zero, its half-width is `1 - (alpha/8)^(1/n)`. Recomputing this formula through the frozen outward-conservative implementation in `experiments/prompt_choice/paired_inference.py`, with `alpha=0.05`, gives:

| Hypothetical independent families | Zero-contrast half-width |
|---:|---:|
| 8 | 0.469745 |
| 12 | 0.344877 |
| 43 | 0.111329 |
| 67 | 0.072951 |
| 98 | 0.050470 |
| 99 | 0.049973 |

Thus even the optimistic fiction that the eight provisional components were eight valid independent families would be far from the five-point zero-contrast radius. They are not verified families, and this calculation is not a power analysis or a sample-size guarantee. It is the best-case all-zero observation under the accepted interval; heterogeneous signs, missing outcomes, scoring uncertainty, and the actual comparator constraints can widen intervals. The 12-root count is not 12 independent families, and exposure absence is not an unseen certificate. The exact number 99 only crosses the five-point radius in this special all-zero case; it does not mean that 99 families generally suffice.

This resolves the immediate precision question without changing the five-point useful-gain threshold or inference method: the present candidate remainder cannot support a persuasive evaluation merely by assuming its provisional links are valid. There is no scientific basis for a GPU collection job or a policy fit on the current ledger. The next viable route is row-level source adjudication with a defensible measurement contract and global family/exposure resolution; if that cannot produce enough independent, exposure-cleared families, report the original MBPP evaluation as infeasible at the prespecified precision rather than substituting a benchmark or relaxing the rule.

## Evidence and limits

Sources: pinned MBPP `mbpp.jsonl` at commit `4700efb9afa54286b0e04473ba80a13e8461e25f` (local ignored copy documented in `docs/mbpp_source_acquisition_20260925.md`); the 43-row candidate overlay `results/policy_candidate_adjudication_20260926.json`; correction `docs/public_expected_return_display_distinction_20260927.md`; joint screen `results/mbpp_joint_admissibility_20260929.json`; and frozen inference contract `docs/paired_kl_inference_contract_20260926.md`. Source checks are lead review only. There was no independent semantic reviewer, no execution, no new data, no model call and no efficacy estimate.

Full-project paper readiness remains **60%, change 0 percentage points**. No efficacy or independent-policy-evaluation credit is earned. Population/measurement admission, practical policy training, untouched-family evaluation, and manuscript/raw reproduction remain incomplete.
