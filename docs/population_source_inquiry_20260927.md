# LEAD-POPULATION-01 / MRL-41: source feasibility before a new population decision

Codex scientific lead, 27 September 2026. **Metadata/source inquiry only.** This is a proposed new source, not an adopted evaluation population, experiment freeze, or change to the original research goal. The two MBPP inquiries remain closed under `reviewed_population_decision_20260927.md`; exclusions and all E11–E13a outcomes stand.

## Scientific reason to investigate

The measured history does not justify another format-only refinement on the same checkpoints: E11 ties its primary contrast, E12 is negative, and E13a's different restart package loses to bare resampling. Those observations do not reject conditional prompting. Current MBPP curation has also failed to establish an eligible untouched-family population. The next useful decision concerns source suitability, not another compatibility pass on those same roots.

BigCodeBench is a candidate because its function-level Python tasks include library-mediated automation. Such tasks could expose API and data-handling discrepancies relevant to public feedback while retaining a fixed code-generating receiver. This is a mechanism hypothesis, not evidence of beneficial feedback or easier tasks. No leaderboard outcome or receiver score is used to select a favorable subset. Difficulty alone is neither a reason to adopt nor discard the source.

The official [repository](https://github.com/bigcode-project/bigcodebench) describes 1,140 tasks and Complete/Instruct variants and is archived. Its default tooling can use remote evaluation. The [dataset card](https://huggingface.co/datasets/bigcode/bigcodebench) reports Apache-2.0, versioned data and unittest-based tests; it also acknowledges possible overspecific tests. These are publisher descriptions, not an independent audit. No upstream install, evaluator or generated code is run. The public card includes task previews, so source-blind inspection is not claimed. No private policy outcomes were accessed.

Two bounded public metadata requests (20-second timeout, 1MiB response ceiling each) resolve:

- Code: `09dd993f46c3fbf3a799465bb96d524edcb0b199`.
- Dataset: `b74c0d0bf70d2c0bc459be537895cca163007f1a`.
- Candidate data artifact: `data/v0.1.4-00000-of-00001.parquet` at that dataset revision. Other releases are not pooled.

Metadata response SHA256 values were `c9e41224db320edc853834e1a315c56aabb0907b1f25a1b38e6fe4f734d4751b` (5,416 bytes, GitHub) and `6fecc6d3179159e594183291a68e2ef27b67427cb2993dacbc1ffacc7bc105a4` (2,853 bytes, dataset). These response hashes document the read; the immutable revision and eventual downloaded-file checksum govern reproducibility.

## MRL-41 — existing Claude Code worker, bounded setup only

From acknowledged acceptance: one CPU worker, 15 elapsed minutes, at most64MiB total newly retained/downloaded bytes, $0 paid experimental services. No receiver calls, benchmark/reference/assertion execution, imports of dataset code, dependency installation, remote evaluator, model-written code execution, family adjudication, endpoint adaptation or policy fit. Use installed data-reading libraries only; if unavailable, report the missing dependency without installing or converting the task through execution. Do not renew the cap or substitute a dataset version.

1. Fetch only the pinned dataset card and the specified parquet artifact, and the pinned code licence/requirements documentation needed for dependency metadata. Preserve raw third-party bytes in ignored `work/`, with URL, revision, byte size and SHA256. Apply request timeouts and the cumulative byte cap; partial/failing acquisition is a retained result.
2. Produce a data-only inventory: exact row count, schema/types, unique/duplicate task IDs, duplicate complete/instruct prompt hashes, entry-point counts, declared library sets and frequencies, missing fields. Keep Complete/Instruct versions of one task together. Treat library names as metadata, not independent-family labels. Record dataset and code licence statements separately; do not infer clearance for dependencies.
3. Report compatibility questions for the existing public diagnostic's permitted expected-value schema and sandbox environment from schema/static text only. Do not declare individual tasks eligible or execute source to infer return types. Retain uncertainty instead of guessing.
4. Return the small inventory builder, focused fixture checks, public metadata summary and manifest. Raw task text, solutions and tests stay in ignored storage. Report actual elapsed time, downloaded/retained bytes and failures. This setup delivery is not a new experiment.

The lead will independently validate the inventory and own all scientific admission decisions. Stop after this delivery; no endpoint builder or collection allowance follows automatically.

## Decision after delivery

Adoption requires an explicit new estimand/version: exact prompt variant and permitted public information, source-relative operational families and prior-exposure crosswalk, fixed development/evaluation separation and weights, a sampling law with correctly derived inference, and a measurement contract. Shared libraries alone neither prove semantic equivalence nor independence. Frozen pretrained-model exposure remains uncertain. An artificial restriction to easy or conveniently displayable tasks must be named as a different target rather than silently replacing the full candidate source.

Before endpoint expansion or receiver calls, assess the prospective design's decision-relevant precision and finite budget. Task count is not family count; the prior 99-family all-zero calculation is not a power guarantee. Retain the five-point criterion and fair fixed-recipe/resampling comparators unless a separately justified scientific amendment changes the target. The four-cell landmark learner remains a restricted test and does not complete full-history, repeated-policy or learned-STOP validation. Failure to find a defensible source is a feasibility result, not proof of prompt futility. No transport to general programming tasks or humans is assumed.

Full-project submission readiness58%,delta0. Efficacy, independent policy validation and total-cost benefit remain unestablished. This inquiry advances the population decision; it does not earn empirical completion credit.
