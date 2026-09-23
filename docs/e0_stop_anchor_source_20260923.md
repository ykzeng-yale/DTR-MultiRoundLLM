# STOP mechanism core and seed contract

23 September 2026. **LEAD-E0-STOP-01: source preparation; numerical execution remains held.** This adds the core estimator and a prospective seed/identity plan for the [accepted mechanism design](e0_stop_anchor_design_20260923.md). It is not a connected collector, completed study or model-execution release. The original matched numerical source, raw records, negative results and reserved seeds remain unchanged.

## Delivered source

The new `experiments/e0/stop_anchor_estimators.py` supplies 12 nuisance sequences: compressed/full history, penalties 0/5, and original/evaluation-only/recursive STOP handling. Each supplies matched plug-in and DR episode scores on common root folds, for 24 estimator identities. Evaluation-only variants privately reuse the corresponding original fit. Eight backward fits per fold are required, or 24 per dataset with three folds. All training means remain episode-weighted; the penalty counts distinct training roots. Root means, rather than episodes treated as independent, are the later summary unit.

A shared query answers every active STOP request with the synthetic known payoff in anchored modes, including unseen cells. Recursive fitting uses that query to form its own backward continuation values. Evaluation-only fitting holds the original Q tables and fallback means fixed and applies the direct score adjustment; it does not imitate recursive refitting. The original branch calls the frozen estimator. No frozen estimator file was edited.

The new entry point checks the stronger structural contract: binary outcomes, observed STOP sealing 1{S_t=3}, and early termination only through STOP. Invalid records fail visibly. This validation does not make synthetic true correctness a usable LLM policy feature. The standalone score helpers require a query bound to the intended data and context; the cross-fitting path ensures that internally. Inactive padding never becomes a history or importance factor. Scores may lie outside [0,1] and are not clipped.

Observed/unseen training-cell membership and the source of each held-out prediction are separate partitions. A structural answer does not create a training cell or add a root. STOP and non-STOP support are reported separately. Explicit fold assignments are validated without an RNG call; otherwise the existing seeded root permutation is used once. This is fold assignment, not simulated-data collection.

The core currently returns a complete cross-fit result or raises. It does **not** persist partial fits or promise a failure-preserving 2,304-slot journal. A separate connected job adapter must preserve attempted, returned, failed and unattempted identities before this source can support collection.

## Reserved seed and identity plan

`experiments/e0/stop_anchor_comparison_plan_v1.json` binds the prospective 96-dataset, weak-overlap-only comparison, its 24 estimator identities, all 24 paired contrasts, the primary full-history/lambda5 recursive-versus-original DR contrast and the unchanged resource proposal. Execution is explicitly false. The declared 0.005 paired squared-error MCSE flag is a diagnostic precision rule, not a superiority test. Coverage remains a secondary diagnostic; no plug-in confidence interval is supplied.

`experiments/e0/stop_anchor_seed_plan_v1.csv` contains rows 0–95. Each data/fold input is the unsigned big-endian integer from the first 16 bytes of SHA-256 applied to the exact ASCII namespace/message in the [seed audit](../results/e0_stop_anchor_seed_audit_20260923.json). Preserve exact decimal strings in serialized records and parse using arbitrary-precision Python integers; conversion through floating point or int64 corrupts these 128-bit inputs.

The independent source audit found 192 distinct inputs with no collision against the 1,200 seeds reserved by the previous matched plan, including unused seeds, or against other explicit numeric inputs in its recorded repository scope. The lead separately reproduced all 192 derivations and the complete 1,200-input exclusion. A qualified no-collision result is not proof of independent draws or disjoint RNG streams. Historical dynamic formulas, unrecorded inputs and other hosts remain outside that census; the eventual RNG constructor/environment must still be frozen. No RNG constructor, simulation draw or fit was needed for the reservation audit.

## Validation boundary and next dependency

Independent scientific/source review covers the structural assumptions, direct score identity, recursive propagation, original-mode reuse and honest support accounting. The lead ran all 75 focused deterministic checks (33 new fixtures plus 42 related regression checks): 1.30 seconds test time, 1.641 seconds command wall and 0.920 seconds child CPU, with numerical-library threads fixed at one and a 60-second ceiling. The [execution and integrity record](../results/e0_stop_anchor_source_validation_20260923.json) pins the tested source. A final independent read accepted those exact source/test hashes; the reviewer did not rerun the tests. All 11 old frozen source hashes and six prior saved-run input hashes match. Handcrafted fixture fitting validates implementation behavior; it does not provide new bias, RMSE, coverage or prompting evidence. The previously reviewed algebra and partial numerical findings remain the governing evidence layers.

Before numerical execution, implement and review the separate connected adapter, journal, reporter and reconciliation path with all 2,304 planned slots, immutable actual estimator arrays/folds, source/environment/seed/truth bindings, and enforceable time/output limits. Verify resource feasibility and current host/lease availability, then publish a separate lead release. The former run remains closed; this source delivery does not renew its cap or MRL-23, and no worker is reassigned.

Overall completion remains **58%, change 0 percentage points** under the fixed rubric. E14 delivery and independent prompt-policy validation remain the principal experimental dependencies. Prompt efficacy is unestablished and the full project is not submission-ready.
