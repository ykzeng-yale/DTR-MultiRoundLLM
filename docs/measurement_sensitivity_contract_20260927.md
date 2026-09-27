# Benchmark grading and semantic-policy claims

Codex scientific lead,27 September2026. Internally reviewed by the existing inference reviewer. This is classical expectation and confidence-set arithmetic specialized to the project's measurement problem, not a new causal identification result. It does not change historical outcomes or assert that a policy has improved.

## Explicit estimands

For each frozen policy a, let Y_a be binary semantic task quality under a specified correctness contract, and Z_a the binary frozen benchmark grade of that same execution. Use the **same** conditional target law, family/root weights, receiver, continuation and handling of failures/missingness. Conditional on frozen development information F, define unconditional target-weighted error masses:

- u_a = P(Z_a=1,Y_a=0 | F), a false-positive *joint mass*.
- v_a = P(Z_a=0,Y_a=1 | F), a false-negative *joint mass*.

These are not class-conditional false-positive rates, sensitivities or specificities. The identity E[Z_a−Y_a | F]=u_a−v_a implies, for policy d versus b,

`theta_Y = theta_Z − u_d + v_d + u_b − v_b`.

If valid nonnegative upper bounds U_a,V_a hold under the same conditioning, an interval [L,H] covering theta_Z yields the semantic sensitivity interval

`[max(−1, L−U_d−V_b), min(1, H+V_d+U_b)]`.

The rectangle bound is valid but not claimed sharp after all probability constraints or marginal information. For deterministic bounds holding surely conditional on F, coverage inherits the grade interval. If the error bounds are themselves estimated with **simultaneous** coverage1−beta and grade coverage1−alpha, the joint guarantee is at least1−alpha−beta by the union bound; no independence is needed. Conditioning after the fact on the event that estimated bounds happen to hold does not preserve nominal coverage. Across the two policy comparators, allocate coverage jointly rather than silently reusing a per-bound confidence level.

If grades are missing, first use valid interval bounds for the grade target; do not redefine it on complete cases or set missing grades to observed failures. If semantic correctness is not sufficiently specified to define Y, sensitivity arithmetic cannot repair an undefined estimand.

## Implication for the completed audits

The task628 wrong controls, and earlier example-lookup controls, establish finite failures of the tested endpoint to discriminate particular wrong artifacts. Their handpicked distribution is not the deployment policy's artifact distribution. They therefore do **not** estimate U/V, justify setting error to zero, or establish a population defect rate. Passing references also does not bound all false-negative mass. A representative artifact audit under a justified correctness/measurement contract, or another defensible bound, is needed for that purpose.

Policies choosing the identical canonical primitive can share both Y and Z so that the measurement-error term cancels. This requires the same semantic outcome and grade/scoring identity, not merely equal action names or matching text from separate executions. The present helper accepts aggregate bounds and does not manufacture this cancellation.

Consequently a benchmark-success study remains an interpretable endpoint-specific experiment when its sampling/execution/grade contract is valid. It must not be silently advertised as general task correctness. The full original project includes meaningful task quality and cannot be declared complete by relabeling benchmark pass as universal correctness. The weak task628 endpoint is not evidence for or against conditional prompt benefit.

## Implemented and checked

[Exact rational helper](../experiments/prompt_choice/measurement_sensitivity_v1.py) accepts only integers/Fractions, refuses invalid bounds and applies strict five-point benefit/futility thresholds. Seven tests pass, including all136 unordered two-observation empirical distributions over the16 possible binary (Yd,Zd,Yb,Zb) tuples. These check the identity and interval inclusion exactly; they do not simulate receiver performance or validate any assumed error rate.

[Hypothetical scenario table](../results/measurement_sensitivity_scenarios_20260927.json): for a hypothetical graded-benefit interval[.08,.12], assuming each policy has false-positive mass≤.02 and false-negative mass≤.01 widens the semantic interval to[.05,.15]. Equality at.05 is inconclusive under the fixed strict criterion. These numbers are explicitly illustrative assumptions, not measured results or a changed threshold. With no usable error bounds, the helper correctly returns the vacuous[−1,1] possibility in its zero-grade-contrast test.

Internal mathematical review accepted the identity and requested the explicit common-target, unconditional-mass, joint-coverage and identical-Y/Z qualifications above. This review validates the relation under assumptions, not the assumptions themselves.

Full-project readiness **60%, change0 percentage points**. No efficacy or independent-policy credit. Population/measurement, the complete prospective freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete. Goal active; direct Codex implementation, no Claude delegation.
