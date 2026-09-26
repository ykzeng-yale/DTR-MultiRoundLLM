# LEAD-MEASUREMENT-01 / MRL-31: unavailable histories are not common outcomes

Codex scientific lead, 26 September 2026. **Prospective measurement clarification and source-only learner extension.** This preserves the reliable-frozen-receiver quality target in `docs/landmark_experiment_protocol.md`, rather than replacing it by a service-reliability endpoint. No real-data fit, model collection, endpoint validation or independent policy result is reported. The original full-history prompt/STOP and repeated-deployment objective remains; the four-cell learner is a baseline within it.

## Quality, observations and common execution

The intended primary outcome is binary private-suite quality under the frozen reliable receiver/decoder and declared bounded evaluator. It is not success conditional on receiving an answer and not a composite coding infrastructure outages as zeros. Existing `grade.py` contract/version remains historical source evidence; task-specific grader discrimination, containment and exposure audits are still release gates.

| Event | Scientific treatment |
|---|---|
| A completed receiver response is saved, including empty or malformed text | An observed artifact. The frozen extractor/endpoint may assign a genuine failure; it is not an infrastructure-missing artifact. |
| A valid, bound public diagnostic includes timeout/unavailable/output_limit | An observed INCOMPLETE history under the one-attempt diagnostic law. Keep both public Boolean flags and witnessed failures; both PATCH/RETHINK remain supported. |
| The initial receiver output or the required history record is lost through infrastructure, or an assigned root is unattempted at the fixed cap | The latent intended history and policy scores are unobserved. Retain the root/family and original weights. Each policy quality is bounded by [0,1]; do not invent an observed status or a shared terminal outcome. |
| A selected continuation or its grader is unavailable, but the history is known | Preserve its assigned action/replicate slot as null, [0,1], under the existing contract. |
| A verified same execution/artifact/scorer is deliberately reused by two policies under the frozen branch law | A genuine shared primitive, consolidated before taking contrast bounds. A common missing score may cancel. |
| Public/private leakage, identity drift, containment breach, invalid source specification, or an undefined intended intervention | Scientific integrity/release hold. A missing-data bound does not establish a valid latent experiment. A reason string is not proof of recoverability or of a breach. |

These rules are assumptions and design requirements, not facts established by accepting a JSON row. The future adapter must reconcile the full planned roster, transport logs, hashes, measurement record and execution identity. The quality law must exist and observed executions must preserve it; arbitrary informative observation loss can be bounded only under that condition.

For the learning inputs, “common” concerns the candidate policies and fixed recipe being fitted. It does not automatically include B2-1R. B2 retains its independently declared controller: STOP on all-public-pass, otherwise one bare-task redraw. Do not alter B2 or charge it a nonexistent continuation to make paths appear equal.

## Scientific defect in the v1 coverage of input types

The accepted v1 learner represents known histories and verified policy-independent common outcomes. It has no distinct unavailable-history root. The latter must not be encoded as `common_outcome: null`: equal marginal score intervals [0,1] do not imply a common realized score. For instance two unknown scores can be 0 and 1, so their difference can be -1 even though their individual intervals match. This is a missing input case for a future all-assigned adapter, not evidence that the accepted toy fixtures or old experiments are wrong.

A separate **v2** source package will support this case while preserving v1 source/config/tests and all historical data. It changes missing-data bookkeeping before any new development fit; it neither changes the task population or outcome nor supplies identification, empirical ranking, improvement or total-cost evidence.

## Exact v2 learning contract

Retain every v1 actionable row and common-outcome row, family/root uniqueness, strict types, UTF-8 validation, planned replicate denominator R, explicit source/config identities, four-cell feature map, exact Fraction arithmetic, PATCH fixed-policy tie and b1 cell tie/unseen fallback. Top-level partition is development only. All families and roots remain in the original weights `w_gi=1/(G*m_g)`.

Add exactly one mutually exclusive root shape:

```
{"root_id": <nonempty UTF-8 string>,
 "state": null,
 "history_unavailable_reason": <one of the three values below>}
```

Allowed reasons: `initial_transport_missing`, `history_record_unavailable`, `collection_cap_unattempted`. These record supplied-data provenance categories, not a certificate that the latent law is valid. Unknown reasons, a non-null state, extra fields, or any common_outcome/outcomes supplied with this shape must be refused. Do not reinterpret an observed INCOMPLETE state as unavailable. Known common outcomes remain a distinct input/report type and require a verified common law outside the fitting API.

For each unavailable-history root, every policy's marginal empirical score interval is [0,1]. Add zero to its lower score and w to its upper score for **every** map; do not choose or impute a state/action. Thus the criterion is the original weighted lower score on known histories plus common-root lower contributions, with zero contributions from unavailable histories. This is a pathwise conservative lower criterion under boundedness and an existing latent law, even if observation loss is informative. Missing roots can change other roots' weights within their family and must never be dropped before calculating weights.

The objective still separates over the four observed cells; therefore the same rule maximizes this lower criterion over all 16 maps, and its criterion is at least b1's. This is exact algebra, not correct ranking or improvement on the latent quality target. The API returns no contrast interval: a missing-history contribution to a paired contrast is generally [-w,w], not [0,0]. That later contrast calculation belongs to the execution ledger plus accepted inference module.

Preserve prediction as a pure two-Boolean operation. `state:null` is missing-data bookkeeping, not a fifth deployable policy state. The v2 artifact must declare version `empirical-policy-source-v2`, its own source/config hashes, four-cell map and b1, and must not carry training labels/IDs or accept a v1 identity silently. Inputs and artifacts must not be mutated. File I/O is allowed only through an explicit identity-loader helper, as in v1; fitting/prediction receive supplied values only.

The v2 report must separately list known-history actionable roots, verified-common input rows, and unavailable-history roots. For every unavailable-history row record family/root ID, original exact weight, reason, planned per-action replicate count R, and marginal policy interval [0,1]. Label it **not a shared outcome**; do not manufacture a primitive ID, cell, action, grade or empirical failure. Keep unavailable-history root count and total exact weight separate from missing continuation slots and missing common scores. Per-cell support counts include known-history cells only; total family/root counts retain all rows. If all histories are unavailable, the tie law gives PATCH everywhere, lower values zero and upper values one, with no observed support and no inference of efficacy.

Complete-policy equality can establish equal expected values, but equality of recipe labels or marginal stochastic laws alone does not make independently drawn realized scores equal. Only a declared shared-execution representation or verified common primitive warrants pathwise cancellation. If the fitted map is constant, report that fact; equality of the complete policies additionally requires matching all continuation/failure/endpoint rules. Do not advance a richer generator on the basis of a constant fitted rule.

The lead and an existing internal mathematical reviewer independently accept this conservative training argument and the distinction between expected-policy equality and realized-score coupling. No new foundational theorem is claimed; the empirical-success and bounded-score methods are classical, as cited in the v1 and paired-inference contracts.

## Remaining measurement gates identified by this review

A completed empty initial response is currently rejected by the v1 renderer's nonempty-string check as `initial_receiver_failure_without_artifact`. That refusal cannot establish infrastructure loss. Before collection, the supported empty-artifact representation and renderer/public-check behavior need a versioned correction and verification; do not force an undocumented common fallback or change B2's rule. Likewise an oversized-serialization refusal occurs before complete binding checks in that renderer, so its disposition alone cannot certify a trustworthy common path. Diagnose trust/identity separately before assigning any score or path. This document does not claim these adapter/renderer gates are implemented.

No common fallback for missing initial history is released. The later full trial must pin the task-specific endpoint and public/private information, extraction and fault attribution, seed and branch-reuse law, independent family/sampling argument, full cap/lease and all collection/analysis source. Actual collection and E14 N1/S1 remain held.

## MRL-31 bounded source assignment

Existing Claude Code worker only. Add `experiments/prompt_choice/empirical_policy_v2.py`, `experiments/prompt_choice/empirical_policy_source_v2.json`, `tests/test_prompt_empirical_policy_v2.py`, plus normal attributed receipts. Do not edit v1, MRL-26 renderer, inference files or historical records. One sequential CPU, **20 elapsed minutes from recorded acceptance, 32 MiB retained output, zero experimental model calls, candidate/reference execution, downloads, paid services, real-data fits or historical reanalysis**. Toy supplied-data fixtures only; no Monte Carlo. Config pins this contract at its issuing commit and any reused source dependency. The explicit artifact identities must cover actual code/config dependencies; avoid a hidden mutable dependency on v1. A self-contained v2 implementation is acceptable.

Verify exact optimization over all 16 maps on mixed known/common/unavailable examples; denominator retention in unequal-sized families including a case where dropping a missing-history root changes b1; all-unavailable behavior; same numerical choices/intervals as v1 when no new input type occurs; distinct missing-history versus common reports; informative-loss toy bookkeeping without a MAR assumption; strict malformed/extra-field/reason/type/duplicate/partition rejection; immutable inputs; label-free prediction and version/identity refusal. Include a counterexample demonstrating that two unknown policy scores need not cancel, without adding a fake outcome/contrast to the fit API. Run affected tests and the documented suite; report actual source hashes, timing and limitations. Codex independently accepts the delivery. No automatic cap renewal or trial release follows.

Full-project submission readiness **58%, change 0 points**. Efficacy is unestablished, independent policy validation absent. Valid family population, endpoint audits and the complete prospective freeze remain the largest remaining milestones.
