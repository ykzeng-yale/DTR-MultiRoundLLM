# Corrected fixed-bank selection pilot, 2026-09-20

**Executed on existing data: zero model calls and zero GPU hours.** All 4,488 initial candidates are retained, regardless of later routing: 561 tasks × two receivers × four draws. A frozen seeded split uses 336 task roots for fitting and 225 for evaluation, shared across receivers. This reuses a previously analysed corpus, including its former confirmatory labels, and is explicitly exploratory.

Each policy receives the same bank of four completed initial answers and public validation results. All four generation calls are charged to every selector. The visible comparator chooses uniformly among visible-passing candidates, or uniformly among all four if none passes. This equals averaging the first-visible-pass rule over random bank order. Learned policies maximize their fitted score with uniform tie-breaking. The endpoint is recorded **full-test success**, not independently rescored hidden-only performance.

| Receiver | Selector | Visible success | Learned success | Difference (percentage points) | Exploratory task 95% interval (pp) |
|---|---|---:|---:|---:|---|
| qwen2.5-3b-instruct | gbm | 0.6674 | 0.6700 | +0.26 | [-1.92, +2.44] |
| qwen2.5-3b-instruct | logit | 0.6674 | 0.6667 | -0.07 | [-2.48, +2.34] |
| qwen2.5-7b-instruct | gbm | 0.7093 | 0.7122 | +0.30 | [-1.59, +2.19] |
| qwen2.5-7b-instruct | logit | 0.7093 | 0.7378 | +2.85 | [+1.19, +4.52] |

The 7B logistic selector is a promising signal: +2.85 percentage points for this frozen-bank task split. This is not a confirmed effect after adaptive project-level selection or multiplicity correction. It does not establish a cheaper policy, multi-round feedback benefit, causal next-prompt value, or a learned dynamic regime. The other three fits provide little evidence of improvement. We retain all four comparisons rather than reporting only the positive one.

## Integrity and limits

An independent internal agent reconstructed all 900 per-task rows from the raw source and checked source/script hashes, split membership, labels, exact tie expectations, generation-token totals, paired means, standard errors and intervals; they matched. No direct hidden-label feature leakage was found. This is an internal audit, not external replication or proof of data validity.

Intervals condition on the frozen training data and assume independent task roots. Benchmark families remain unresolved, all project-level analyses have already inspected the corpus, and full-test labels can overlap prompt-visible material. Standardization fits training data only. Generation prompt/completion costs match by construction; checker and selector CPU time were not measured. There is no comparison at the lower adaptive-BoN stopping cost.

Inherited failure-class features name `assert` while the source emits `assertion`; that intended one-hot is therefore absent. The public visible-pass and fraction-failed features still record failure. Preserve this run as executed; fix the schema prospectively before a new frozen experiment. Do not silently refit around the positive result.

An initial run aborted before fitting because a strict validator expected a Boolean but the recorded outcome is binary integer. The corrected run accepts only Boolean or integer 0/1 outcomes; the failure record is retained. Source logs were not edited.

## Reproduction

`uv run python scripts/recheck_selection.py --episodes /path/to/DTR-AgentEvals/results/code_routing/log/episodes.jsonl --out results/new_selection_recheck`

Use the source SHA256 in `results/selection_corrected_20260920_v2/manifest.json`. The complete manifest, task split, hyperparameters, predicted scores, per-task outcomes and summaries are retained. The source corpus is not bundled into this repository.

## Next falsifiable experiment

Freeze logistic selection, visible selection and adaptive-BoN baselines on a new root/family-separated task set. First compare fixed banks at identical generation budgets; separately compare a prespecified sequential policy at a matched expected-call/token budget, measuring selector/checker costs too. Audit visible versus hidden test separation and invalid-test rates before generation. Preserve failures. Do not relabel this candidate-selection follow-up as evidence for prompt treatment effects; that requires its own randomized feedback experiment.
