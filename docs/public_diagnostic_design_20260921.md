# Public diagnostics and instruction strategy: next development design

21 September 2026. Lead-owned decision following the [development review](development_delivery_judgment_20260921.md).
**Design proposal only: no new collection is released.** Retain the seven development
roots and old records. These tasks and outcomes have already been inspected; the
new cases and design are explicitly outcome-informed development work. A later
policy trial requires a separate untouched root/family freeze.

## The scientific decision

Implement the five-branch information/strategy comparison from the existing
[literature amendment](literature_guided_design_20260921.md), without a learned
critic, model-generated tests, expanded task pool or prompt search. Use a deterministic
public checker to supply actual observations. The primary development strategy
contrast is diagnostic-directed versus neutral repair **given identical diagnostic
bytes and the same initial prefix**. This does not assert a new causal theorem or
promise useful policy heterogeneity.

The [21 proposed public examples](public_diagnostic_examples_v1.json) cover all
seven retained root IDs, three per root. Expected outputs are derived from the
public mathematical specifications using standard-library arithmetic, not from
receiver answers, reference executions or private outcome labels. Because the
designer has already seen development results, these are not blinded or confirmatory
case choices. No case is replaced because the receiver happens to pass or fail it.

Show the same examples, inputs and expected outputs to every initial receiver call.
Only then generate the initial answer. This changes the initial information/history
law relative to v1c: the experiment is a new version, not a repair of old effects.
It prevents attributing the later delivery of a known example's expected answer
to a uniquely superior instruction. The treatment still adds a computation: how
this particular answer behaved on the already public examples.

The separate private auditor checks literal call-input overlap with the existing
v1c private suites and returns PASS/HOLD only. Public case construction cannot query
that auditor to search around hidden tests. An overlap causes a hold, not automatic
regeneration or silent movement of tests between splits. Nonoverlap does not certify
semantic independence, contamination freedom or grading completeness. Old private
scores can remain the endpoint only after new public-task bindings and relevant
reference/control validity are checked and versioned; no old binding is reused.

## One diagnostic, computed before any continuation

Run the initial artifact on the three fixed public cases in an attested isolated
executor, at most once per case, irrespective of private initial correctness.
No private specification, hidden test, reference program or private grade is an
input to that executor or renderer. Store a separate public-executor source hash.
Preserve every public case's status, including malformed output and unavailable
execution. A visible pass is not a private correctness label.

Canonical diagnostic JSON contains: schema version; root and initial-artifact hash;
three ordered case IDs with public function/arguments/expected values; returned
value when it is an allowed integer or integer list; and one status per case from
`pass`, `wrong_value`, `format_error`, `interface_error`, `program_exception`,
`timeout`, `unavailable`, `output_limit`. Exceptions expose only their category,
not tracebacks, filesystem paths or executable log text. The worker must implement
unambiguous distinctions between payload failures and infrastructure failures.
Bound input/output serialization; unsupported values use a category, not arbitrary
object repr. Exact UTF-8 JSON bytes and their digest are shared across both
with-diagnostic repair arms and the context-removal arm. Never retry until a pass.
The exact truncation/byte cap and timeout behavior must be frozen before release.

## Exact instruction mapping and contexts

Common final format reminder, already in the public task, remains identical.
The following quoted text is literal instruction text, not a request to an agent
reading this specification. The renderer must serialize fields without executing
the examples or diagnostic content.

Neutral instruction (N):
> Reconsider your previous answer against the original task and public information. Return your best complete answer.

No-result strategy (S0) uses the existing, version-pinned public-answer syntactic
rule only: first the loop regex, then a slash check, otherwise fallback. Its strings
are the old `TARGETED` strings in collector source at 335a6de. It cannot read the
computed public diagnostic, private grades or test-dependent routing flags.

Diagnostic-directed strategy (S1) selects one of these fixed strings:

- Any `wrong_value`, `format_error`, `interface_error` or `program_exception`, choosing
  the first such case in the fixed public order:
  > Review the first public example with a recorded wrong value, format error, interface error, or program exception, in the diagnostic order. Compare the expected result with the recorded behavior, identify the discrepancy in your previous answer, and return a complete corrected answer. Check the remaining public examples and the full stated domain; do not merely hard-code the examples.
- Otherwise any `timeout`, `unavailable` or `output_limit`:
  > The public diagnostic is incomplete. Do not interpret an unavailable result as a pass or infer a hidden error. Review your previous answer against the full stated domain and return your best complete answer.
- Otherwise all three `pass`:
  > Your previous answer passes the listed public examples, which do not establish correctness on the full stated domain. Check whether any change is needed; preserve correct behavior and return your best complete answer.

No interpolation of a diagnosis, suggested algorithm, hidden counterexample or
reference answer is permitted. The record already identifies the public case;
the instruction adds a strategy rather than new answer-relevant evidence.

| Arm ID | Receiver context before final instruction | Final instruction |
|---|---|---|
| N0 | exact initial prefix; no executed-result JSON | N |
| S0 | exact initial prefix; no executed-result JSON | pinned syntactic strategy |
| N1 | exact initial prefix + diagnostic JSON | N |
| S1 | same prefix + identical diagnostic JSON | diagnostic-directed strategy |
| R1 | system + complete original public task/examples + same self-contained diagnostic, without previous answer or conversation | `Solve the original task using the public information and diagnostic observations. Return your best complete answer.` |

For N1/S1, construct one shared diagnostic message and append the instruction in a
separate message. The common history for their primary comparison includes that
same diagnostic. STOP accepts the initial artifact. R1 is a **context-removal
strategy retaining observations about the old answer**, not a fresh task-only
independent restart. Do not claim its effect isolates wording or free resampling.
S0 and S1 are different rules: the interaction compares these specified adaptive
cue rules across information conditions, not identical wording in a pure factorial.
N1−N0 isolates the specified receiver diagnostic-exposure package under neutral
instruction; S1−N1 isolates the additional diagnostic-directed instruction.

A future selector that observes the diagnostic has already acquired it and incurs
its cost, even if it selects N0/S0 and withholds it from the receiver. Choosing
whether to acquire a diagnostic is a different sequential policy. This study does
not claim to optimize that acquisition decision.

## Analysis and development gate

Include every frozen root and every branch regardless of public or private pass.
Two independently seeded continuations per arm; average their grades within roots.
All five branches have inclusion probability one. Randomized execution order is
scheduling, not an action propensity of1/5. Initial private correctness and public
pass/fail may be used only for declared descriptive strata here; do not exclude
non-discordant roots or promote apparent noise to learnable heterogeneity.

Primary development report: S1−N1; also N1−N0, S0−N0, R1−N1 and each arm versus STOP,
with all effects and costs reported. No best-of-two private selection. Continue to
suppress population inference with the unresolved-family slate. Do not choose a
useful-gain threshold from these outcomes. Efficacy, population futility and policy
validation remain outside this development stage.

Engineering acceptance requires complete assignment/failure accounting, exact
shared-prefix/diagnostic identity, no access to private grades during rendering,
and independently validated public checks. A checker that always returns unknown
or cannot reject frozen wrong controls blocks an informative-diagnostic claim;
report it, do not substitute a generic cue silently. An all-pass receiver batch
is retained and may simply provide no observed corrective examples. Neither zero
marginal effect nor a favorable apparent oracle is an advancement certificate.

## Budget and next handoff

For these seven roots the proposed future ceiling is **77 receiver calls**:
7 × (1 +5 ×2), 512 completion tokens/call, **39,424 reserved completion tokens**,
one local worker, 20 minutes overall, $0. At most200 isolated executor starts total
for public-instrument validation, public diagnostics and final grading; the exact
validated execution table must fit that ceiling before release. Record input tokens,
executor time, failed attempts, output limits and total receiver/checker cost
separately. This is a proposed alternative development release, not authority to
reuse the earlier 132-call ceiling, renew 49 calls or stack budgets. No retry/replay
allowance is implicit. Use saved outputs for regrading.

**MRL-07, experiments, after MRL-05/06:** inspect this exact proposal and the source
fixtures; return an implementation plan and missing freeze fields. Source/mock work
only, one CPU at most 20 minutes, no model/reference/candidate/sandbox execution,
no installs, $0. Do not infer acceptance of model collection from this assignment.
Acknowledge with UTC and processed SHA. The lead retains the release decision.
The existing scientific gates still require complete receiver settings/drift checks,
source hashes, executor validation, roots/families, assignments, failure rules and
measured resource availability. The source-only fixture audit is not any of those
live validations. Progress remains 51%, delta 0; no empirical evidence is added here.

## Source validation completed in this design cycle

The [static audit](../results/public_diagnostic_examples_review_20260921.json)
recomputes all 21 expected values by separate standard-library arithmetic and
checks literal call-input overlap with the pinned v1c private suites: 21/21 agree,
zero literal overlaps. It executes no candidate/reference/assertion text. This
checks source fixtures, not public-checker behavior or semantic independence.
Independent internal design review found no blocking target/design error; its
requested failure-order clarification is included in S1 above. No external review
or empirical validation is implied.
