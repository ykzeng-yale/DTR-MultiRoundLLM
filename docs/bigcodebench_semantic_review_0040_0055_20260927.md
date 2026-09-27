# BigCodeBench source review: rows 40–55

Codex scientific lead, 27 September 2026. **Source-only development review, not an experiment, failure-rate estimate or population adoption.** Both prompts, canonical solution and full native test source were read for each of these 16 source-ordered tasks. The [ledger](../results/bigcodebench_semantic_review_0040_0055_20260927.json) preserves 64 field hashes and individual judgments; a fresh decode verifies those bindings in the [receipt](../results/bigcodebench_semantic_review_0040_0055_validation_20260927.json). Semantic judgments in this batch are lead-reviewed, not independently validated. No reference, test string or receiver was executed.

## Measurement and specification decisions

Positive evidence must survive an audit of weaknesses. Tasks 43, 44 and 50 contain fixed numerical expectations; 52 and 55 check full count mappings/Series; 53 checks exact extracted records. Tasks 46 and 47 construct expected numerical frames from copies **before** candidate execution. They do not share the post-call mutable-expectation weakness found in 40 and 41. Neither kind of numerical check establishes the unchecked plot content or an unrestricted domain-wide correctness claim.

Several source contracts require adjudication before admission:

- 42 uses `np.cumsum` without a NumPy import in the Complete prefix; native tests supply the name. Its tests do not check PCA values or explained variance.
- 45 uses inconsistent component naming between opening/example and return prose. Tests follow the reference's `Component1/2` convention.
- 46 describes a list of axes but returns/tests a nested axes array.
- 48 checks uniqueness despite sampling timestamps with replacement. This is not guaranteed by its generator; no failure probability or observed failure is claimed.
- 49 promises an Axes object but returns/tests a histogram tuple. Its local-time conversion needs an explicit timezone contract against the fixed UTC-like expected example.
- 51 describes a column-count fallback while reference/tests use row count. The Instruct version also lacks Complete's filter parameter explanations; KMeans randomness/defaults are not frozen.
- 55 lowercases the sentence but not its capitalized `Those` stopword. Existing tests do not exercise that entry; whitespace token boundaries also need specification.

The review records these conflicts without silently rewriting the tasks, changing endpoints, dropping difficult cases or claiming benchmark-wide defect rates. Numerical degeneracies, plotting compatibility and timezone behavior remain unexecuted.

## Provisional family decisions

Conservatively co-split PCA tasks **42/45**, column-standardization tasks **29/38/47**, and sentence-segmentation tasks **54/55** pending the global partition and prior-exposure crosswalk. These are shared computational-task judgments, not claims that the tasks are identical or independent of other groups. The 29/38/47 group extends the earlier 29/38 relationship.

Do not merge 38/40/42 merely because they share a Mean assignment: column scaling, row scaling and PCA have different transformations. Likewise, shared mean-imputation code among 43/44/46/47 is insufficient by itself. Task 46's relation to column standardization remains open, including distinct degenerate-column conventions. The timestamp tasks 48/49/50 also need broader family adjudication. Exact-statement retrieval links 53 to still-unreviewed 56/155/160; these are candidate relations only. Plotting boilerplate is not a family certificate.

## Disposition and next work

Cumulative semantic reading now covers source rows 0–55 plus retrieval-selected 887: **57 distinct source tasks, zero admitted families**. This is a nonrandom development review, not an evaluation roster. Continue with row 56 and the outstanding retrieval relations; complete prior-exposure, global-family and measurement decisions before a sampling freeze. The native runtime remains unqualified; the pending Docker restoration question has no inferred answer. No Claude delegation or experiment-monitor heartbeat is needed.

Full-project submission readiness remains **60%, change 0 percentage points** under the fixed rubric. This source batch earns no additional milestone credit and supplies no efficacy evidence. Population/family/measurement validation, the complete prospective freeze, independent policy evaluation and final manuscript/raw-environment reproduction remain incomplete.
