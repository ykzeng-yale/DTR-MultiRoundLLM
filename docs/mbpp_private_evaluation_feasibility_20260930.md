# MBPP candidate frame lacks an admitted independent evaluation endpoint

Codex scientific lead, 30 September 2026. This is a read-only source-measurement audit. It is not a population amendment, benchmark execution, model experiment, task admission, or efficacy result.

## Question and evidence

Can the pinned MBPP source supply a held-out outcome instrument for the existing untouched-family policy evaluation without inventing or silently modifying tests? I audited the source's `test_list` and `challenge_test_list` metadata for all544 literal-description-deduplicated candidate roots, then intersected challenge-positive roots with the existing source-lineage ledger and the current12-root conservative family prescreen. Inputs are hash-bound in [`results/mbpp_private_eval_support_20260930.json`](../results/mbpp_private_eval_support_20260930.json); the reproduction command is:

```sh
python3 scripts/audit_mbpp_private_eval_support_20260930.py \
  --source work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl \
  --candidate-index results/landmark_task_source_candidates_20260920.json \
  --joint-ledger results/mbpp_joint_admissibility_20260929.json \
  --lineage results/source_frame_lineage_20260927_r1.json \
  --out work/mbpp_private_eval_support_20260930.json
```

All544 candidate roots have three original tests. Of these,536 have zero challenge tests, seven have one, and one has three. None of the current12-root residual has a challenge test: the available source supplies36 original assertions total across those roots, with no challenge partition. The eight roots with any challenge tests are23,25,26,28,42,43,44,47. The recorded lineage excludes seven at the setup/challenge gate and one at the single-function interface gate; task43 is also marked in the prior-seen development release. These exclusions remain in force. The source flags do not prove that the eight are semantically invalid, but they do prevent counting them as an admitted untouched evaluation roster.

The broad MBPP candidate source therefore does not provide a challenge-test endpoint on the current conservatively retained roots. Its three original tests per task can define success on those particular published assertions if prospectively withheld from the receiver, but they are not evidence of an independent hidden suite, semantic completeness, or freedom from model pretraining exposure. No challenge tests were created, and no reference, assertion, benchmark, receiver, or candidate code was executed.

## Lead decision

**No-go for a real-task efficacy collection or policy fit on the current MBPP residual.** The immediate blocker is measurement plus admitted untouched families, not GPU, CPU, or memory availability. Under the unchanged source/frame dispositions, eight recorded provisional components are not verified independent clusters and cannot support the five-point evaluation. The fixed sign-split KL rule's hypothetical all-zero half-width at eight independent families is0.469745; this arithmetic is not power and does not certify those components.

Do not reopen the eight challenge-positive exclusions because they are numerically convenient, use the36 public assertions as if they were a validated semantic grader, fit on the exposed nine-root pilots, or replace MBPP with BigCodeBench. The next valid empirical route requires a newly versioned outcome instrument with independently validated task contracts and private cases, a complete family/exposure crosswalk over its sampling frame, and a prospective development/evaluation split. Until those are frozen, extra accelerator capacity cannot make a model call scientifically interpretable.

## Verification and limits

The audit checks only source fields, pinned hashes, and the existing lineage flags; it does not adjudicate all544 task contracts or prove no pretraining exposure. Three focused unit tests pass. Full-project readiness remains **60%, change0 percentage points**: population/measurement admission, practical fitted policy, untouched-family evaluation, and final manuscript/raw-environment reproduction remain incomplete. This earns no efficacy or independent-review credit.
