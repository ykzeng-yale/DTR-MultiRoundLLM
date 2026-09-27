# Native status-only feedback: prospective measurement contract v1

Codex scientific lead,27 September2026. This is a new measurement version for a possible library-mediated task study, not a change to historical MBPP diagnostics or a release of BigCodeBench collection. Source-only implementation: [serializer](../experiments/prompt_choice/status_feedback_v1.py), [hash-bound contract](../results/status_feedback_contract_20260927.json).

## Decision-time information

The receiver already sees the frozen task and its own initial artifact. The proposed additional public feedback is exactly one of three fixed strings: PASS, FAIL or INCOMPLETE with a fixed explanatory sentence. No test source/name, expected/actual value, exception, output, timing, path, artifact hash, private verdict or count is rendered. Both supported prompt recipes must receive exactly the same status string and saved initial prefix. A future recipe adaptation must be versioned because the existing renderer assumes literal-case diagnostic records and its common caveat references that schema.

The internal record has exactly four fields: version, artifact SHA256, public-test SHA256 and status. The trusted collector must compare the two bindings with the frozen test and saved initial artifact. The serializer checks their equality and syntax; it cannot authenticate the collector, prove the check occurred or establish that a supplied status is true. Private/raw logs are stored separately and never accepted as serializer input. Unknown fields, status values, versions or mismatched bindings cause a constant, content-free error. They do not become INCOMPLETE or a retry and must stop receiver dispatch.

Conditional on the task, initial artifact and frozen selection rule, this serializer's output alphabet has exactly three elements. Its entropy is at most log2(3) bits per successful emission. This is an elementary finite-alphabet bound, not zero answer transfer, adequate diagnostic usefulness or a guarantee for the complete system. Outcome-dependent retries, exposed latency, number of checks, changing test selection and other channels require separate accounting. Invalid-record termination is a separate operational event; conditioning on successfully rendered histories cannot silently replace the assigned population.

## Required producer semantics before execution

A future trusted supervisor, outside the candidate's sandbox, must produce the record and private audit receipt. PASS requires an observed completed public check with every declared assertion satisfied, no unexpected skip/expected-failure/zero-test success, no lost output and no integrity failure. FAIL requires an observed terminal failure assigned to the candidate by the frozen failure taxonomy (including declared extraction/syntax/interface failures). INCOMPLETE means the planned public outcome was unavailable under the declared infrastructure/limit law. The classification of candidate timeouts and service failures must be fixed before outcomes and reflected in the endpoint/missingness contract; this serializer intentionally does not infer it from arbitrary exception text.

Do not trust a candidate-written marker or stdout as supervisor truth. Do not expose private assertions to public execution. A fresh process and filesystem per public/private primitive, hash-bound code, an audited containment profile and trusted outcome transport are required operational work, not consequences of these source tests. Candidate inspection of test internals remains a threat even in a no-network sandbox; no secrecy or adversarial integrity claim is made here.

## Measurement and target boundaries

The first-method-public split is still unreleased after its source audit. The serializer does not repair duplicate methods, weak private suites, specification conflicts, unsupported dependencies or semantic-family separation. The complete1,140-row inquiry remains intact and no convenient subset is adopted. Distinct task-family sampling, complete prospective freeze, untouched policy fitting/evaluation separation and an informative precision/budget design remain prerequisites for efficacy collection.

This contract permits nonliteral library outputs by withholding values from the feedback channel. That changes the information intervention relative to the historical literal diagnostic. Any resulting policy value must name this measurement version and its task population; it cannot be pooled with E11/E12 or treated as a correction of their negative findings. The research objective remains supported history-conditional prompt/STOP policy evaluation; this component alone tests neither learned STOP nor repeated policy deployment.

## Executed validation

Twenty-six focused tests pass: every valid status, forbidden answer/output/timing fields, malformed statuses, missing/version errors, binding mismatches, malformed hashes, constant error messages and the exact three-string alphabet over27 binding/status combinations. No receiver, subprocess, grader or benchmark code is invoked. The tests establish the serializer boundary only, not operational noninterference or measurement validity. Old renderer and results remain unchanged.

Full-project readiness **60%, change0 percentage points**. No efficacy or independent-policy credit. Codex continues implementation directly; goal active. Next operational work is a source-isolated public/private execution design and trusted supervisor validation under synthetic controls before any frozen benchmark measurement audit.
