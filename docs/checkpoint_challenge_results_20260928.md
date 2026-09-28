# Constructed checkpoint intervention results and next decision

Codex lead. Discovery freeze5ed76bf; H100 job27720685 completed162/162 calls in46allocated seconds, no missing generation or state drift. Local frozen source-separated grading completed1314case executions in40.780seconds. All54 assigned checkpoints remain in each arm. Lead receipt/hash reconciliation, not independent reviewer validation.

| Arm | Supplement PASS | FAIL | INCOMPLETE | Mean outcome bounds |
|---|---:|---:|---:|---:|
| STOP |9|45|0|.1667|
| PATCH |37|17|0|.6852|
| RETHINK |39|10|5|.7222–.8148|
| FRESH |44|9|1|.8148–.8333|

These are missing-outcome bounds, not confidence intervals. Each root has six constructed checkpoints, giving equal-root and equal-checkpoint means here. PATCH−FRESH is between−.1481 and−.1296; PATCH−RETHINK between−.1296 and−.0370. No overall superiority of the repair recipes is demonstrated on this panel. STOP's low score is deliberately induced by including five wrong artifacts per root and must not be interpreted as deployment prevalence.

PATCH preserves9/9 reference artifacts. RETHINK yields6passes,1failure and2incomplete from references. For constant-public-expected controls, PATCH repairs4/9 whereas RETHINK repairs9/9. These exploratory strata motivate checking stability, not adopting a rule based on private artifact kind. Private control labels are never policy inputs. Reused nine-root results do not establish independent-family generalization or a fitted policy's benefit.

The six incomplete outcomes include output contaminated with example prints, misplaced top-level returns, missing reduce import and a mixed-domain runtime problem. Preserve the preregistered INCOMPLETE classification and its bounds; do not retrospectively convert these to semantic failures or repair the outputs. The original-example-lookup input intentionally contains original-example answers, so original-private scores are descriptive only. Finite supplemental tests are not complete semantic correctness.

PATCH used1896 completion/12879 prompt tokens; RETHINK2852/12393; FRESH2673/5418. Summed call latencies7.726/10.608/9.712seconds respectively. One H10046seconds=.01278GPU-hours,$0standard-tier charge; energy not measured. Equal1024-token ceilings do not imply equal realized total cost.

## Fixed replication decision before new outcomes

Proceed with exactly10 new seed replicates of every54-checkpoint×3-arm combination,1620calls. Preserve all tasks, adapted contracts, artifact bytes, feedback, prompt recipes, endpoint, model/runtime,1024-token cap and incomplete taxonomy. Do not select only the favorable constant-control contrast or drop the difficult roots. Discovery outcomes are excluded from the replication summary. This tests stochastic stability of the finite constructed panel and safeguards against interpreting single draws as conditional means; it does not increase the number of independent roots or become the original population-level trial.

Seeds are deterministically sampled without replacement from the32-bit seed range, excluding discovery seeds, with seed2026092811; shuffle all1620 assignments with the same frozen generator. Distinct seeds are not proof of independent outputs; no confidence intervals, p-values or causal population generalization are authorized for this stage. Report overall missing-outcome bounds, each of ten replicate panels and all initial-artifact strata, including negative patterns. No policy fitting or outcome-dependent stopping/reselection. One H100/4CPU/16GiB/30minutes,1750-second application timeout,1620calls/max1658880completion tokens,$0; failures remain assigned/unattempted, no retry. Based on discovery35.98s/162 calls, roughly6minutes is a planning extrapolation, not a guarantee.

Grade only on the qualified local sandbox after retrieval: at most13140case starts,2s/1CPU each,3600seconds total,256MiB retained. Existing cap/failure accounting leaves unfinished outcomes unknown. Hash-bind code/config/assignment/analysis before submission. Do not run benchmark code on Bouchet. Raw source and candidate outputs remain ignored; retain remote records until retrieval is checked.

Full-project readiness60%,delta0; population/measurement beyond this development panel, full independent freeze/evaluation and final manuscript/raw reproduction remain outstanding. H100 capacity is operational and no longer the immediate blocker.

Original-private diagnostic counts (not an unseen endpoint): {"FRESH": {"FAIL": 7, "INCOMPLETE": 1, "PASS": 46}, "PATCH": {"FAIL": 13, "PASS": 41}, "RETHINK": {"FAIL": 8, "INCOMPLETE": 6, "PASS": 40}}.
