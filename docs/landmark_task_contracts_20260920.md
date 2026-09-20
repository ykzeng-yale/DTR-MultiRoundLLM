# Versioned development task contracts and a reference boundary defect

20 September 2026, 23:24 UTC continuation; scientific lead's source-only review.

The seven retained tasks now have explicit public definitions and separate private
grading proposals. **None is cleared for collection.** Six await isolated reference
and negative-control validation; MBPP/402 additionally has a known reference
boundary defect. This refines the earlier seven-task contract-review status. It
does not revise the fixed 24-task selection, replace an excluded root, or establish
any new receiver result. Full-project status remains not submission-ready.

## What changed, and what target this defines

`experiments/landmark/task_contracts_v1.json` defines
`landmark-curated-development-contracts-v1`. It rewrites ambiguous public wording,
states the function interface and permitted input domain, and discloses the output
parser convention before any collection. All arms would receive the same public
definition. The separate grader uses Python equality on returned values; numeric
type identity, list identity/mutation and efficiency are not endpoint claims.

| Root | Proposed public domain and target | Added private boundary cases | Current disposition |
|---|---|---:|---|
| 52 | Positive integer base and perpendicular height; parallelogram area | 3 | Execution validation pending |
| 357 | Nonempty list of nonempty integer tuples, including negative values; maximum over every tuple | 3 | Execution validation pending |
| 373 | Three positive integer perpendicular lengths; cuboid volume | 3 | Execution validation pending |
| 378 | Integer list, including empty/singleton/repeated values; return a one-position right rotation | 3 | Execution validation pending |
| 402 | Integers 0 ≤ r ≤ n and p ≥ 1, without requiring prime p; binomial coefficient modulo p | 4 | Original reference conflicts with this domain |
| 489 | Nonempty integer list, n equal to its length; frequency of the maximum | 3 | Execution validation pending |
| 509 | Positive odd n; exact mean of positive odd integers through n | 3 | Execution validation pending |

Each private proposal retains all three original assertions, then adds the authored
boundary cases: **21 original plus 22 authored assertions, and 14 deliberately
wrong control programs**. No assertions are public in this proposal. A root's
quality endpoint would require passing its entire private suite, not the average
of 43 assertion scores or 43 independent observations. This is a new development
measurement contract, neither the old generated-public-check/full-test contract
nor the later one-visible-assertion/private-rest split. It must not be pooled with
those results as the same endpoint.

Making a domain explicit may make a task easier and changes the receiver's public
information. Adding boundary tests changes what is measured. Both changes are
declared prospectively; neither repairs old results retroactively. The seven-root
slate is too small and its family status too unresolved to validate a personalized
policy. Some tasks are elementary and may have little room for improvement; that
possibility is not measured yet and is not a reason to replace them after seeing
outcomes. They can support engineering development once all gates pass.

## Static defect in the original reference for 402

The exact pinned source initializes `C[0] = 1` and returns `C[r]`. If `r=0`, the
inner descending loop has no iterations, so `C[0]` remains 1. With `p=1`, every
integer reduced modulo p is 0. Thus inputs `(0,0,1)` and `(4,0,1)` have expected
value 0 but the reference's control flow returns 1. This is a direct source
inspection, **not an executed failure**. The original three tests do not exercise
this boundary. Original reference digest (canonical JSON string digest):
`60c271e5bbdf2f739a783bc54ce4371959c8b164daf3c8d9b92d7cd44ecb91a9`.

The prior family audit proposed positive modulus and zero-permitted r; I did not
previously notice this mismatch and retain responsibility for that incomplete
review. Restricting p to at least 2 merely to preserve the reference would change
the proposed domain without scientific justification. The builder therefore
preserves the original reference, adds the discriminating boundary assertions,
and retains a machine-readable hold. A minimal candidate repair is a final modulo
reduction of the return value, but it is **not adopted or validated here**. Any
repair needs a separate reference version, original-versus-repaired hashes and
isolated reference/control evidence before clearing the hold. The task remains in
the audit trail regardless of whether it eventually enters a development run.

This defect concerns a proposed expanded development contract. It does not show
that the old three-test endpoint was miscomputed, that previous repair negatives
were caused by this root, or that the DTR identification arguments are false.

## Separation, provenance and limits

The builder verifies the full official source's SHA-256, the exact seven IDs and
interfaces, empty original setup/challenge fields, and the unresolved shared
family marker. It preserves each reference and original test list as data, parses
but never executes source/control code, and accepts only literal authored boundary
arguments. The existing grader checks exact public-task binding, private/public
separation and duplicate assertions. Controls with static integrity flags block
export rather than being mistaken for observed failures.

The original full source is pinned to Google Research commit
`4700efb9afa54286b0e04473ba80a13e8461e25f`, file SHA-256
`ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`.
The [source dataset](https://github.com/google-research/google-research/blob/4700efb9afa54286b0e04473ba80a13e8461e25f/mbpp/mbpp.jsonl)
is attributed to Google Research MBPP under CC-BY-4.0; the earlier source audit
separately records the repository code's Apache license. Raw reference bodies and
original assertions stay in ignored `work/`. The committed configuration contains
newly authored definitions, cases and controls, not copied reference bodies.

The generated package is named `REVIEW_ONLY` and its manifest explicitly states
`ready_for_collection: false`. That field is a review disposition, **not an added
runtime interlock in the collector**. The existing pre-call freeze process remains
mandatory; do not pass these files into a live collector. No new receiver config
or assignment freeze is supplied. Private scorer data must not become prompt or
policy inputs; repository access alone is not proof of experimental blinding.

All seven retain `unresolved_development_family`. This prevents manufactured
independent family labels; it does not certify a true family partition. None is
assigned to an independent policy test cohort. The 24 original curation decisions
and hashes remain intact. Passing a small set of boundary/control tests later
would establish finite-suite discrimination, not general program correctness,
semantic independence or freedom from pretraining contamination.

## Reproduction and validation

Run only the source-only builder with the existing pinned local source:

```sh
uv run python scripts/build_landmark_task_contracts.py \
  --source work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl \
  --out work/landmark_task_contracts_reproduction_NEW
uv run --extra dev pytest -q
```

The output directory must be unused and under ignored `work/`; the builder refuses
to overwrite completed packages. It emits public rows, separate private specs,
the source-bound grading contract, and a hash-only manifest. The actual package
is at `work/landmark_task_contracts_20260920_v1/`; its manifest is copied unchanged
to `results/landmark_task_contracts_20260920/manifest.json`. Configuration, builder,
public rows, private specs and grading source bindings are all recorded there.
Runtime is expected to differ in a reproduction; substantive hashes should match
only under unchanged inputs and grading sources.

The full suite passed **131 tests and two subtests in 1.42 seconds**, including ten
new export/guard tests and the existing deterministic simulator checks. New tests
use authored fixtures whose bodies would raise if called; they check separation,
source refusal, preserved holds, literal-only cases, interface/setup rejection,
duplicate assertions, integrity flags, immutable output and artifact bindings.
These are software tests, not execution validation of the seven tasks. The real
source-only build took **0.010368 seconds** of instrumented builder wall time.
Calls, model tokens, sandbox launches, reference/control/candidate executions,
GPU work and external spending were all zero in this continuation. No unchanged
sandbox retry or additional synthetic efficacy study was warranted.

## Concrete next decision

Experiments workstream: establish controlled containment on a supported existing
environment and return its exact interpreter/profile/source-bound evidence. Then
validate these proposed task definitions and controls, with a separately versioned
repair for 402 if retained. Report failures rather than dropping tasks or narrowing
domains. Any next receiver freeze must explicitly state the accepted subset and
all exclusions, keep the shared-family limitation, and reduce the call cap to the
actual accepted slate (49 calls only if all seven become eligible). It remains an
engineering development batch. Independent policy validation on untouched
root/family information is still the missing scientific milestone; generator
expansion remains premature.
