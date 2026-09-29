# Frozen synthetic operating-characteristics study for the paired-family intervals

Codex lead, 29 September 2026. This is a source-free Monte Carlo study of the already selected simultaneous inference procedure. It was motivated by the existing design memo's unexecuted proposal to compare declared interval procedures under a fixed $0 local cap. It does not use receiver outcomes, tasks, benchmark code, or candidate/reference programs, and does not alter the population, useful-gain threshold, or primary inference choice.

## Question and estimand

Under explicit finite-support laws for independent task-family-level binary potential outcomes, what are the finite-sample simultaneous-coverage frequencies, interval widths, and strict decision rates of the frozen sign-split KL interval at illustrative family counts? How do those operating characteristics compare with the existing simultaneous Hoeffding sensitivity interval? This addresses uncertainty about the conservatism and informativeness of the fixed procedure under named hypothetical laws; it does not estimate the actual MBPP-family outcome law or feasibility of the still-unselected population.

For each family draw a jointly distributed binary vector `(Y_d, Y_b1, Y_b2)`. The two policy contrasts are `D1 = Y_d - Y_b1` and `D2 = Y_d - Y_b2`, so both are in `[-1,1]` and their dependence is induced by the shared `Y_d`. Families are IID by construction within each scenario. The target in each scenario is the exact pair `(E[D1], E[D2])`. There is no missingness, adaptive sampling, policy fitting, or estimation of a language-model effect.

## Frozen scenario law and assignments

Each row below gives integer mass out of 1,000 on `(Y_d,Y_b1,Y_b2)`. Unlisted mass is assigned to `(0,0,0)`. The scenario table is fixed before generating any Monte Carlo draws.

| Scenario | Nonzero support entries `(outcomes: mass)` | `E[D1]` | `E[D2]` | Purpose |
|---|---|---:|---:|---|
| equal-policies | `(1,1,1):500` | 0 | 0 | Zero contrast with shared outcome variation |
| null-opposed | `(1,0,0):100`, `(0,1,1):100` | 0 | 0 | Null contrasts with 20% disagreement in each |
| gain-005-low | `(1,0,0):100`, `(0,1,1):50` | .05 | .05 | Useful-gain boundary, 15% disagreement |
| gain-005-high | `(1,0,0):200`, `(0,1,1):150` | .05 | .05 | Same boundary, 35% disagreement |
| gain-010 | `(1,0,0):200`, `(0,1,1):100` | .10 | .10 | Gain above threshold, 30% disagreement |
| loss-005 | `(0,1,1):100`, `(1,0,0):50` | −.05 | −.05 | Useful-gain futility region |
| opposed-comparators | `(1,0,0):200`, `(0,1,0):150`, `(0,0,1):250` | .05 | −.05 | Contrasts with opposite signs and dependent outcomes |

Use `n ∈ {8,12,43,67,99,198}` families and 20,000 replicate samples per scenario-size cell: 840,000 samples total. Counts 43, 67, 99, and 198 are illustrative sizes only and do not assert that any MBPP frame or family roster exists. The fixed Python `random.Random` generator uses integer cumulative masses; cell seed is `202609291500 + 10000*scenario_index + n`, with zero-based scenario order as above. No replacement, early stopping, outcome-dependent assignment, or seed substitution is permitted.

## Frozen analyses

1. Primary: use `experiments/prompt_choice/paired_inference.py::paired_contrasts` at alpha `.05` on the complete per-family exact contrasts. For runtime, the runner uses the algebraically identical count form for complete `{-1,0,1}` data; focused tests compare it exactly to the public function. The alpha/8 tail allocation, outward-conservative arithmetic, two contrast identities, and strict thresholds are unchanged.
2. Sensitivity: for each observed contrast mean, use the two-sided Hoeffding interval clipped to `[-1,1]`, radius `sqrt(2*log(80)/n)`. The runner rounds this radius outward using a 100-digit Decimal enclosure. With two contrasts and four tails, this is the simultaneous 95% bounded-difference interval under independent families.
3. For each procedure and cell, report empirical simultaneous coverage of both true contrasts, per-contrast mean width, and the probabilities of the prespecified decisions `L1 > .05`, `U1 < .05`, `L2 > 0`, `U2 < 0`. Equality remains inconclusive. Report Monte Carlo standard errors `sqrt(p*(1-p)/20000)` for all frequencies.
4. Preserve every scenario-size cell. No method is selected, no alpha/threshold is changed, and no interval is described as empirical validation of the theorem. Use the rates only as conditional operating characteristics under the named laws; do not choose a population size from these results.

## Execution and acceptance

One local CPU process; at most 600 seconds wall and CPU, 32 MiB retained output, one fresh output directory, $0 spend. No network, packages/installations, receiver calls, benchmark/reference/task/candidate execution, historical-data access, or training. The script must verify its own frozen source hash and the interval-module hash, write the complete assigned-cell ledger and summary atomically, and fail on a missing/duplicate cell, cap breach, or any plan/source mismatch. Preserve partial outputs as failure evidence; never restart the same assignments automatically. Focused deterministic tests validate the simulator's outcome mapping, exact scenario means, unique seed schedule, sample-size totals and unchanged decision rules before launch. The resulting JSON is lead-generated synthetic evidence only.

## Interpretation limits

The laws are deliberately hypothetical, complete binary family outcomes. They do not model outcome-law uncertainty, related benchmark tasks, weak/absent treatment support, model stochasticity, public/private leakage, endpoint error, missingness, finite-source sampling, within-family trajectory construction, cost or energy. Passing coverage checks cannot certify those assumptions in a real study; simulated decision frequencies are not power guarantees for the unknown target population. The simulation has no efficacy conclusion and releases no real-data fitting or collection.

## Preserved implementation failure and versioned repair

The first frozen runner attempt at `dee975c` failed before the first replicate because Python's `decimal.Context.divide` does not accept a `rounding` keyword. The retained journal is empty; the lead failure receipt is `results/interval_operating_characteristics_v1_failure_20260929.json`. The source-only repair removes that invalid keyword while retaining the context's upward rounding mode, adds a directed-radius check, and changes no law, seed, method or metric. Plan v2 at `experiments/prompt_choice/interval_operating_characteristics_plan_v2_20260929.json` binds the corrected runner hash and parent plan hash. It will use a fresh output directory; no random assignment was consumed by v1.
