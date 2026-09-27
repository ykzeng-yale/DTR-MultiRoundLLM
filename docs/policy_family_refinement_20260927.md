# Source-based refinement of sixteen family holds

Signed: Codex scientific lead, 27 September 2026. This source-only adjudication refines the sixteen plausible relationships in `results/policy_candidate_adjudication_20260926.json`. No task/reference/assertion or receiver program was executed, no policy outcomes were inspected, and no new split or roster was selected. The [new hash-bound record](../results/policy_family_refinement_20260927.json) preserves all sixteen rows, original source hashes, prior classifications and contract holds. All sixteen descriptions, references and original assertion hashes were independently matched to the pinned MBPP source. Prior canonical-pool and E11 provenance are distinguished.

## What the decisions mean

The existing conservative separation convention treats reuse of an exposed task's substantive output or computational kernel, followed by an explicit domain bridge or aggregation, as evidence against claiming an untouched family. This continues the prior per-row intersection and selected-column-sum judgments. It does not require exact task equality, and does not assert statistical dependence. Shared Python syntax, list types, an elementary operator, or general computability alone is insufficient. Arbitrary Turing reductions would connect nearly every task and are not the rule used here. Each decision below gives the concrete limited relation and states its domain; these remain disclosed scientific grouping judgments, not a universal semantic equivalence relation.

| Candidate | Exposed task | Concrete relationship |
|---|---|---|
| 911 | MBPP4 top-k largest | Top three original entries plus bottom two obtained from top-k of negated entries determine maximum triple product. |
| 366 | MBPP766 consecutive pairs | Maximum of products of the returned pairs, for length at least two. |
| 345 | MBPP766 consecutive pairs | Ordered next-minus-previous map of each returned pair. |
| 200 | HumanEval35 maximum | Return every position equal to the exposed maximum, for nonempty input. |
| 883 | MBPP75 divisible tuples | Wrap scalars as singleton tuples; apply the prior filter successively with the two nonzero divisors; unwrap. |
| 340 | MBPP4 top-k largest | Negate positive entries, take up to three largest, and negate their sum. |
| 506 | E11 MBPP402 modular binomial | With p=2^n+1, the residue is the exact binomial coefficient; multiply by k! for 0<=k<=n. |
| 547 | MBPP224 population count | Sum bit counts of (k−1) XOR k over k=1,...,n, for nonnegative n. |
| 811 | MBPP142 aligned equality count | Check equal lengths, then count_samepair(A,B,B)=len(A), for lists of ordinary literal tuples. |

The prior witnesses use the pinned canonical pool `work/data/tasks.json` (SHA256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`), except E11 root402, whose exact original MBPP source is identified separately. In particular, canonical MBPP75 returns a list; the original MBPP variant returns its string representation and would require literal decoding between calls. The displayed883 composition concerns the canonical exposed variant. HumanEval35 is likewise verified from the canonical pool; this is not a claim of a newly pinned external HumanEval release.

These nine become definite prior-family relations for prospective separation. All output differences remain documented. Root366 does not need the stronger and unjustified claim that a maximum-product-subarray routine is equivalent. Root340's up-to-three domain is still a proposed adaptation. Root506's relationship follows from choose(n,k)<=sum_j choose(n,j)=2^n; this is elementary combinatorics and not a practical runtime claim. Root811 requires the length check to prevent zip truncation and ordinary reflexive structural equality; it does not cover custom comparison objects or NaN. None of these witnesses repairs an endpoint or changes a benchmark reference.

For911, a maximum product of three integer positions is attained either by the three largest entries or by the largest and the two smallest. The two-smallest case captures two negative factors; the all-negative and zero cases are also included. Top-k preserves repeated positions, so duplicate values do not invalidate the construction. For883, sequential filters preserve both order and multiplicity; a potentially different set-intersection operation is unnecessary. For547, the aggregate prior bit-count construction is distinct from the more efficient floor-sum identity, but both represent the same declared nonnegative target.

## Remaining holds and resulting frame

Seven plausible relations remain unresolved: **667,194,711,828,192,961,921**. Vowel/character predicates, positional-base conversion direction, digit-position versus digit-value selection, Unicode classes, Roman grammar/range and contiguous versus strided partitioning require explicit decisions. We do not remove those holds merely because no exact prior function identity was established. Keep828/192 together if later considered; the latter is a Boolean consequence of character counts under compatible character conventions. Reference hold194 and specification holds711/961 remain unchanged.

The43-root family overlay is now **24 definite prior relations,7 plausible holds,10 roots with no direct prior relation found,and2 related candidate roots**. These categories count roots, not independent families. The ten still include176's specification hold. The pair679/833 cannot count as two untouched families. The nine-root measurement panel remains nine measurement-audited roots, not an approved roster; its completed audit is unchanged. This refinement adds zero eligible evaluation families. Historical adjudications are retained rather than overwritten.

Even if every remaining hold among these43 roots were resolved favorably, the24 prior-family exclusions leave19 roots. Keeping679/833 together gives at most18 prospective families within this particular overlay, before any further grouping, contract failures or development allocation. This is an optimistic inventory ceiling, not18 eligible families and not a ceiling on all MBPP or the entire198-root frame. At n=18 the accepted all-zero sign-split interval has radius `1−exp(−log(160)/18)=0.2456916941`; it cannot resolve the five-point zero-difference scenario. Stronger observed effects can still be informative, so this is not a universal impossibility or power claim.

Internal mathematical/source review by the existing inference reviewer accepts all nine identities with their domains and independently verifies the pinned canonical pool, including75 and HumanEval35. The initial original-source75 string-return caveat was resolved by distinguishing the actual canonical exposed variant; no source or outcome was altered.

The outcome reinforces the need for a defensible population and sampling design; it does not authorize a favorable split, relaxed exclusions, a new source, more receiver calls or a change of inference method. The next source work must resolve the remaining holds or explicitly document why the existing population cannot support the intended validation. A new population remains a new scientific target, requiring a prospective definition and an argument connecting it to the original question. All earlier negative experiments remain valid for their stated scope.

Full-project submission readiness **58%,change0 percentage points**. This curation result earns no efficacy or independent-policy credit. Major remaining milestones are family/population/sampling design, complete prospective trial and resource freeze, independent policy validation, and manuscript integration. MRL-38 is closed; no new experiment worker job or lease is assigned.
