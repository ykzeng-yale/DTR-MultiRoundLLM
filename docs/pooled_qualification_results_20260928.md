# Pooled-history qualification reconciled

Codex lead,28September2026. All2700assigned synthetic replicates completed in263.550seconds, one CPU, no model/GPU/network calls,$0. Plan/source/journal identities match; every assignment and every original tabular counterpart reconciled. Both representations fit and score on all assignments; original tabular support failures are preserved. Full numeric results: results/pooled_qualification_reconciliation_20260928.json. These are paired DEVELOPMENT simulations with reused seeds, not independent confirmation or real LLM efficacy.

|Regime|N|History exact value ± MC SE|Last-observation exact value ± MC SE|History−last, paired ± MC SE|
|---|---:|---:|---:|---:|
|null|256|0.550000 ± 0.000000|0.550000 ± 0.000000|0.000000 ± 0.000000|
|null|1024|0.550000 ± 0.000000|0.550000 ± 0.000000|0.000000 ± 0.000000|
|null|4096|0.550000 ± 0.000000|0.550000 ± 0.000000|0.000000 ± 0.000000|
|mode_specific|256|0.828225 ± 0.002321|0.817125 ± 0.002430|0.011101 ± 0.003031|
|mode_specific|1024|0.876460 ± 0.001303|0.837621 ± 0.000755|0.038839 ± 0.001498|
|mode_specific|4096|0.903153 ± 0.000530|0.832870 ± 0.000412|0.070283 ± 0.000669|
|noisy_public|256|0.798531 ± 0.002250|0.695784 ± 0.003033|0.102747 ± 0.003638|
|noisy_public|1024|0.836520 ± 0.001066|0.723486 ± 0.002902|0.113034 ± 0.003000|
|noisy_public|4096|0.852497 ± 0.000502|0.776799 ± 0.002063|0.075698 ± 0.002058|

MC SE concerns variation across300specified simulation seeds per cell; it is not uncertainty for an LLM policy or task population. Exact value integrates the known simulator law. Holdout IPW/DR errors, stage counts, unseen-history prediction counts and paired pooled-versus-tabular summaries remain visible in the full JSON. All null values equal.55; every learned value is below its public-history Bayes oracle. DR mean errors are reported with their MC SE rather than labeled proven unbiased from this experiment.

Decision: numerical fitting failure is resolved in this finite feature model; STOP remains learned rather than oracle-anchored. Function approximation cannot establish finite-sample overlap or causal sufficiency. Close these synthetic runs: no extra seed, penalty sweep or law change. The next practical component is the public text-history/slate binding API in experiments/sequential/public_history.py. It rejects extra private/outcome/family fields, binds exact chronological public observations and versioned candidate slate, enforces STOP/call budgets and logs actual conditional selector probabilities. It is not a trained controller or semantic leakage detector. Collector provenance and private-answer exclusion still require source audit.

ACT-02 alternative runtime investigation: a bounded compute-node namespace probe checks installed Bouchet isolation tools without benchmark/model execution, downloads or privileged changes. Even success does not release candidate execution. This addresses the unresolved native evaluation path rather than repeating GPU hardware tests.

Full-project60%,delta0: population/measurement, practical trained full-history/DR policy, independent freeze/evaluation and final manuscript/raw reproduction remain incomplete. Lead validation, no independent review claimed.
