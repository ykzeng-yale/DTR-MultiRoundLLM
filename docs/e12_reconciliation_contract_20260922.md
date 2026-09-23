# E12 independent reconciliation contract

> Prepared and independently reviewed on September 22; first published September 23 after a lead-side delay. See [the current decision](e12_lead_judgment_20260923.md) for completed E12 evidence and current authority. The dated plan below does not renew an expired allowance.

22 September 2026. Preparatory source review of the existing frozen MRL-16 run.
**No new outcome analysis, experiment or change to the running freeze.** Apply
these checks to a completed immutable delivery; an incomplete running snapshot
supports execution-health reporting only. Do not interrupt collection or pull
this documentation into its checkout.

## Assigned observations and executed work are different counts

The fixed roster has 14 roots, each with one initial answer and two continuations
for each of N0, S0, N1, S1 and R1. STOP scores the initial answer. Thus A has
14 initial slots, C has 140 continuation slots, and D has 154 assigned artifact
grade slots. Every slot remains in the analysis even if its call or grade is
unavailable. Missing grades are not failures, and neither is dropped.

The manifest permits at most154 receiver attempts,512 reserved completion tokens
per attempt and78,848 reserved completion tokens in total. B permits14 public
starts. D permits154 artifact starts plus28 reference/control rechecks, for182
private starts. These are ceilings, not required actual counts: invalid outputs,
unavailable responses and cached duplicate artifacts can reduce executed starts.
The accepted42 instrument starts moved the cumulative ledger from174 to216;
B+D can use at most196 additional starts, reaching412.

A+C remains capped at1,200 seconds, private grading at600 seconds, and Phase A
through the final deterministic report at3,540 contiguous seconds. The accepted
07:10–08:20UTC reservation additionally requires A by07:20 and release by08:20.
The separate single startup attempt is capped at600 seconds with47 planned
nongenerating preflight/template requests and a50-attempt ceiling. None of these
allowances is renewed by this review.

## Reconcile cost fields according to their actual scope

`collect_diagnostic.py:333–340` mixes cumulative and phase-local fields by design.
The collector carries A's attempts, reserved tokens and collection time into C.
Consequently:

| Quantity | Correct reconciliation from a completed A/C delivery |
|---|---|
| Receiver attempts | Count `attempted=true` across both raw call logs; match C's cumulative `attempted_calls`. Do not add A's total to C's cumulative total. |
| Reserved completion tokens | Match C's cumulative total to512 times the total attempts and the sum of phase reserved totals. Reserved tokens are not actual output tokens. |
| Measured prompt/completion tokens | Sum the phase-local A and C fields and reconcile against raw usage records. |
| Unknown usage | Sum phase-local unknown-usage attempt counts; do not silently replace a missing usage field with zero. Known token subtotals are not complete totals when unknowns remain. |
| Collection wall time | Use the C cumulative A+C field; reconcile with phase times allowing for their independently sampled timestamp boundaries. Do not require exact floating-point equality. |
| Total research expenditure | Add startup/preflight, instrument/public/private ledger costs separately. Do not infer them from policy-arm cost tables. Report unavailable components as unknown. |

Arm cost comparisons charge the shared initial generation and the public
information the arm uses. Private evaluation overhead is measurement expenditure,
not information the policy may consume. Reference/control rechecks are not new
receiver outputs. Cache hits can be zero additional execution starts without
being ungraded observations. Count actual ledger starts, not the number of
assertions or report rows. No token total is a dollar or energy estimate.

## Immutable evidence to inspect

1. Actual pre-A freeze, ownership/PID record, startup/preflight outputs, accepted
   reservation, receiver-state snapshot/diff and final release. Bind sources to
   the actual freeze while preserving the original instrument lineage.
2. A and C `calls.jsonl`, `roots.jsonl`, `manifest.json`, `completion.json` and
   output artifacts. Verify all assigned keys, seeds, request/output hashes,
   initial-artifact bindings and receiver guards. Calls alone cannot enumerate
   unattempted slots; reconstruct the denominator from the frozen roster.
3. B `attempts.jsonl`, `manifest.json`, `diagnostics.json`: initial-artifact and
   public-example hashes, actual starts and unknown statuses. Confirm that N1
   and S1 consume identical diagnostic bytes.
4. D `grading_attempts.jsonl`, `private_execution_records.json`, `grades.jsonl`,
   `summary.json`, `view/roots.jsonl`, `view/view_manifest.json`: reference/control
   outcomes, cache links, grade hashes, all154 assigned rows and actual ledger
   starts. Source references: `study_adapter.py:280–330,594–675`.
5. Both `analysis_input.json` and `analysis_report.json`. Command E builds the
   former; the already-authorized extra analyzer invocation produces the latter.
   Recompute primary S1−N1, secondary/STOP contrasts, per-root denominators and
   all-assigned missing-outcome bounds after the batch ends. Source references:
   `analyze_diagnostic.py:146–211`, `study_adapter.py:333–379,697–732`.

An optional independent numerical reproduction reads the immutable records only;
it does not regenerate outputs, regrade candidates, change frozen targets or
fill missingness. A reference/control or provenance failure is a measurement
limitation, not an efficacy null.

## Interpretation boundary

The primary contrast changes continuation instruction with diagnostic bytes held
fixed. R1 changes context and instruction jointly. This finite, adaptively
constructed development roster does not provide a validated population/family
sampling design, so no population confidence interval, significance test or
five-point confirmatory decision follows. The analyzer uses one unresolved family label for all14 frozen task rows; the
manifest separately lists14 provisional duplicate-screen labels. Its input label
count is accurate, but neither encoding establishes actual common-family dependence
or independent replication. Preserve the frozen output and qualify that inference
in the scientific report; do not alter the analyzer mid-batch. The descriptive
restriction remains appropriate because population sampling and independence are
unvalidated.

Public/private strata in the frozen report concern the initial answer and its
public diagnostic. They do not measure final-answer public-pass/private-fail
rates without a separately specified final public evaluation. The thin private
suites establish only the declared task-contract score. Preserve nulls, damage,
missingness and costs without converting this development study into independent
learned-policy validation.

Independent read-only source review and lead inspection found no new blocker or
need to change the freeze. Actual calls, grades and costs remain to be delivered
and independently checked. New review model calls/tokens, program executions,
installations and spend: zero.
