# Trial scale under nonzero policy disagreement

Codex scientific lead, 27 September 2026. Deterministic hypothetical observed-count arithmetic, not power, a sampled simulation, a policy result, or population adoption. This completes the next precision check requested by the population decision. It does not complete that design.

The accepted two-contrast sign-split KL rule and strict five-percentage-point useful-gain threshold are unchanged. The script enumerates 50 realizable binary paired-count scenarios at 100, 200, 400, 800 and 1,000 families, disagreement fractions .10/.30/.50, and observed differences 0/.05/.10/.15 when compatible with integer counts. Noninteger cells are omitted, not rounded. Each family has one root; all outcomes are complete. The usual conditional independence, equal weighting and target-aligned sampling assumptions remain required. This is a hypothetical scenario grid, not a prediction of the receiver's disagreement law.

At disagreement .30:

| Families | Observed gain | Accepted interval | Five-point decision |
| --- | --- | --- | --- |
| 100 | 0 | [-.22430, .22430] | inconclusive |
| 400 | .10 | [-.01281, .20948] | inconclusive |
| 400 | .15 | [.03932, .25568] | inconclusive |
| 1,000 | 0 | [-.07184, .07184] | inconclusive |
| 1,000 | .10 | [.02890, .16976] | inconclusive |
| 1,000 | .15 | [.08046, .21752] | useful benefit for this contrast |

Decisions use exact outward rational endpoints; displayed decimals are rounded. The other primary comparator and cost contract must also be satisfied. No joint probability of success is calculated. Grading-error sensitivity and missingness can further widen the relevant intervals. The earlier 99-family all-zero observation remains valid, but does not describe zero average gain with offsetting positive and negative outcomes.

## Scientific decision

Do not use "roughly 100 families suffices" to justify population acquisition or launch. Even a hypothetical 1,000-family sample with ten-point observed improvement and .30 disagreement cannot cross the unchanged useful-benefit gate in this scenario. This is neither a universal lower bound nor evidence that the true policy benefit is small. No threshold, inference procedure, split, endpoint or family grouping is changed to obtain a favorable decision.

Keep BigCodeBench as an unadopted source inquiry. Its 1,140 IDs cannot be counted as 1,140 independent eligible held-out families; development allocation, duplicate grouping, exposure and measurement obligations precede any sample-size commitment. At the proposed maximum four research receiver calls per root, the hypothetical evaluation budgets are 400–4,000 calls, excluding development and qualification. These counts are planning arithmetic, not authorization or estimates of runtime, tokens, money or energy. Paid experimental spend remains $0.

The next substantive step is a single integrated population/measurement proposal, followed by a finite development study only if that proposal is defensible. It must distinguish native-test score from semantic correctness, specify family/exposure rules and the actual sampling law, and assess decision probability under explicit joint outcome scenarios before freezing evaluation size. A development study may estimate disagreement but cannot certify untouched-test power or supply grading-error bounds from selected controls. No more task628 controls or automatic compatibility expansion are needed for this decision. Existing negative results remain in the manuscript regardless of whether a new trial becomes feasible.

## Reproduction and current state

Run `.venv/bin/python scripts/plan_policy_precision_20260927.py`; stdout reproduces `results/policy_precision_scenarios_20260927.json` without task discovery, receiver calls or raw benchmark execution. An independent SciPy scalar inversion checks all 50 cells to 1e-11; count realizability and decision checks plus the existing inference tests pass (47 tests). The existing internal inference reviewer independently verified all 50 count configurations and source hash, and confirmed the two 1,000-family gain scenarios with separate 90-digit inversion. This numerical comparison is a check, not the mathematical coverage proof; the accepted inference contract governs.

Full local suite after integration: 2,291 tests and 8 subtests pass in 39.16 seconds, zero failures.

Full-project submission readiness **60%, change 0 percentage points**. No component credit is earned for this calculation. Efficacy remains unestablished; population/measurement, full prospective freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete. Codex implements directly. The continuous goal is active; no running experiment requires a heartbeat.
