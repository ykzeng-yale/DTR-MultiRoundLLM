# Non-oracle STOP qualification: sparse histories can prevent fitting

The frozen synthetic job593fd76 completed all2700assignments in73.500seconds, oneCPU,$0. Every journal row matches its seed/regime/training-size assignment; source and plan hashes verified. All successful null-regime policies have exact value.55; none exceeds the Bayes public-history oracle. These are numerical implementation checks under the specified simulator, not a new theorem or LLM efficacy evidence. Full reconciliation: results/sequential_qualification_reconciliation_20260928.json; raw journal remains immutable in work/sequential_qualification_20260928.

|Regime|Training N|Full-history successful fits /300|Last-observation successful fits|Mean full-history value among successful fits|Mean last-observation value|
|---|---:|---:|---:|---:|---:|
|null|256|115|300|.5500|.5500|
|null|1024|299|300|.5500|.5500|
|null|4096|300|300|.5500|.5500|
|mode_specific|256|138|300|.8128|.8181|
|mode_specific|1024|299|300|.8746|.8374|
|mode_specific|4096|300|300|.9030|.8329|
|noisy_public|256|182|300|.7827|.6957|
|noisy_public|1024|300|300|.8360|.7237|
|noisy_public|4096|300|300|.8523|.7770|

Do not compare the two conditional means as an unconditional gain when fits fail. All-assigned[0,1]bounds, matched successful-fit differences, score refusals and across-seed Monte Carlo SE are saved. AtN256 only18/33/65full-history fits also have sufficient Q support for holdout score computation in the three regimes; these failures are scientific diagnostics, not dropped observations. AtN4096 both representations fit and score in all300replicates per regime. No real-task precision or causal sufficiency follows from a synthetic mean.

Diagnosis: exact full-history tabulation is impractical for general text histories and can fail even in this small finite observation space. Randomization ensures design support, not observed coverage. A deployable learned policy needs explicit function approximation/pooling and validation of extrapolation; borrowing oracle STOP quality is not an acceptable remedy. Next implementation will use a frozen observed-history representation with regularized regression, compare it to the tabular baseline on the SAME already declared regimes/assignments (new code, explicitly development), and preserve all original failures. That is a versioned engineering repair addressing actual support failures, not another search for favorable seeds or a new claim that history must win. Neither version trains on the nine-root LLM strategy outcomes.

Full-project readiness60%,delta0; actual text-controller/DR-training, population/measurement, independent study and final reproduction remain unfinished. Lead numerical validation is not independent mathematical review.
