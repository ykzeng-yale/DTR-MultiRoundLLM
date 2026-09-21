# What the development batch can establish

21 September 2026, 00:25 UTC continuation. Evidence: deterministic planning
arithmetic using the already reviewed analyzer, not a simulation or receiver
experiment. The scientific lead retains responsibility for the design decision.

**Decision:** preserve the seven-root slate for engineering development only.
It cannot support a superiority or useful-gain claim under our current conservative
confidence procedure, even in an extremely favorable hypothetical outcome. Do not
increase repeat counts, relabel families, or promote a noisy branch maximum to
make that evidence appear stronger. This is a limitation of this design and bound,
not an impossibility theorem for prompt personalization or all valid inference.

## Reproduced precision calculations

`scripts/plan_landmark_precision.py` calls the current
`bounded_family_interval` without changing it. For a contrast in [-1,1], its
radius is `sqrt(2 log(2/alpha) sum_g w_g^2)`. It assumes fixed weights, independent
complete-data families, a frozen policy and a fixed analysis time. Actual family
independence and valid measurement remain unestablished. The reviewed derivation
is in [the inference audit](landmark_inference_review_20260920.md).

| Hypothetical design | Effective family count | Single 95% contrast radius | Current ten-endpoint radius |
|---|---:|---:|---:|
| Seven roots kept as one unresolved group | 1 | 2.716 | 3.462 |
| Seven independent singleton families | 7 | 1.027 | 1.308 |
| 24 independent singleton families | 24 | .554 | .707 |
| 24 roots in six equal independent families | 6 | 1.109 | 1.413 |
| 24 roots, family sizes 19/1/1/1/1/1 | 1.574 | 2.165 | 2.759 |
| 242 independent singleton families | 242 | .175 | .223 |
| 544 independent singleton families | 544 | .116 | .148 |

The last two rows use source-pool counts only as numerical scenarios. They do not
certify those IDs as eligible, independent, untouched, or available for a trial.
The effective count is `1/sum_g w_g^2`, a weight concentration diagnostic, not a
discovered number of independent tasks. Grouping all seven together avoids an
unsupported independence claim but yields the full contrast interval [-1,1].

Even granting seven genuinely independent roots and a hypothetical observed
contrast of +1 for every root, the single-contrast interval is approximately
[-.0266,1]; with the current ten-endpoint adjustment it is [-.3084,1]. These
calculations use complete outcomes and favorable centering. Missing outcomes do
not improve precision. Twenty-four singleton roots could establish only a very
large effect with this bound, not a modest effect near a few percentage points.

The one-primary-contrast column is a prospective alternative for an independently
frozen policy comparison. It is **not** permission to remove the existing
ten-endpoint adjustment after inspecting the development results. The analyzer
itself remains unchanged and does not yet implement a selected-policy endpoint.

## Resource implications, not a recommended sample size

For equal-weight independent families, inverting this particular radius gives
the following sufficient counts for the requested untruncated half-width:

| Requested half-width | One primary contrast, alpha=.05 | Ten endpoints, alpha=.005 each |
|---|---:|---:|
| .10 | 738 | 1,199 |
| .05 | 2,952 | 4,794 |
| .03 | 8,198 | 13,315 |

These are **sufficient counts for this conservative bound**, not necessary sample
sizes, power calculations or a proof that a cheaper valid experiment cannot work.
They do not choose the application's useful-gain threshold. Nor does a small
confidence radius alone guarantee a positive conclusion: the underlying effect
and observed center matter. Variance-sensitive inference might improve precision
under a separately validated, frozen procedure. We do not replace the current
procedure on the basis of an attractive hypothetical result.

The seven-root all-arm development design reserves 49 calls and at most 25,088
completion tokens at two repetitions and 512 tokens per call. Those are planned
ceilings, not actual usage or authorization to bypass the freeze. The .03-radius
single-primary scenario would use 57,386 calls if one inefficiently retained the
same seven-calls-per-root all-arm design; this is far beyond the current 168-call
ceiling. An eventual policy-versus-comparator design has its own budget and need
not collect every arm. No such large run is proposed or authorized here.

Additional within-root seeds can reduce conditional receiver noise, but this
particular bounded-family reference does not exploit that reduction. They do not
turn seven roots into more independent families. The planning calculation should
not be read as saying repeated seeds are universally useless.

## Independent policy validation: exact scientific decisions

The next small batch validates transport, measurement and runtime accounting.
It does not select a final test cohort by favorability or establish efficacy.
Before a later policy trial, independently freeze the public-history rule d(H),
its permissible information, a competent comparator c(H), receiver and continuation
law, new-root/family sampling and splits, primary contrast, benefit threshold,
precision method, missingness handling and a numerical affordable cap.

On a held-out root, evaluate the two rules selected from its public initial history.
If collecting all arms, compute policy outcomes using decisions made without that
root's branch grades. Do not choose the winning arm from those grades or use them
to train the rule. Distinct receiver seeds alone do not make a reused root a new
policy-evaluation task. Comparator selection also belongs to development; selecting
the best comparator on test outcomes changes the inference problem.

| Observation or gate | Scientific interpretation and action |
|---|---|
| Invalid task, reference or measurement before collection | Resolve and version the contract or keep the task held; preserve its selection record. This is not a receiver loss. |
| Missing outputs or grading after assignment | Preserve every assignment and use the prespecified missing-outcome procedure. Do not silently remove failed pairs or extend recruitment until significance. |
| Marginal arm means are similar | Continue evaluating the frozen selector; cancellation can coexist with useful conditional choices. |
| Prespecified policy interval lies above useful-gain threshold | Supports that stronger policy claim for the declared population, cost and information contract. |
| Interval lies above zero but overlaps useful-gain threshold | Supports positive gain, not demonstrated practically useful gain. |
| Interval's upper end is below useful-gain threshold | Futility for that declared useful benefit; can coexist with a small positive effect. Preserve the negative conclusion. |
| Interval overlaps zero and the useful-gain threshold | Inconclusive; do not portray this as equivalence, proof of no personalization, or success. |
| New endpoint, broader input domain, generator or evaluation population is proposed after inspection | Declare a new target/version and prospective plan. It cannot rescue the original hypothesis retroactively. |

A robust negative trial can complete a milestone. Successful prompting is not
required to earn completion credit. Conversely, completed theory or data plumbing
does not earn the independent-policy milestone. If suitable measurement, sampling
and affordable precision cannot be obtained, the lead must explicitly narrow the
paper's claims to what can be supported, rather than declaring a full empirical
paper ready based on infrastructure work.

## Reproduction and evidence

```sh
uv run python scripts/plan_landmark_precision.py \
  --output work/landmark_precision_reproduction_NEW.json
uv run --extra dev pytest -q tests/test_landmark_precision_plan.py
```

The immutable report is `results/landmark_precision_planning_20260921/report.json`.
It contains 14 design scenarios, six inverted thresholds, exact source hashes and
the planning/runtime distinction. The source-only calculation took .001424 seconds.
Five focused tests with six parameter subtests verify the inversion against the
existing analyzer, the seven-root limit, grouping invariance and family imbalance.
Zero model calls/tokens, benchmark executions, sandbox attempts or external spend.
No new underlying proof is claimed. An independent internal reviewer recomputed
all 14 scenarios and six thresholds, checked source hashes, reran the five tests
and six subtests, and found no blockers. The review explicitly distinguishes the
current ten arm/contrast endpoints from a later policy endpoint needing its own
frozen evaluation/multiplicity rule. Full project remains not submission-ready.
