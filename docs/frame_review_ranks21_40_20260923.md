# Semantic measurement-contract review of frame ranks 21-40

23 September 2026. MRL-22 deliverable 2. This is a **source-only** semantic review of
the twenty preregistered candidate-frame records at ranks 21-40, in the shape accepted
for ranks 1-20 (`docs/e12_contract_review_20260922.md`). It is not receiver evidence,
not reference execution, not a release, and not a family-independence certificate. No
model, receiver, sandbox, public check or upstream evaluator was run; no grades file,
analysis report, private execution record or hidden score was opened for any record
reviewed here.

**Disposition:** 10 include, 10 hold, 0 exclude.

- **include (10):** 911, 667, 344, 524, 814, 187, 194, 356, 366, 302
- **hold (10):** 211, 701, 960, 370, 484, 346, 508, 670, 376, 650
- **exclude (0):** none. The mechanical interface/setup exclusions and the prior-seen /
  provisional-duplicate screens were applied upstream by
  `scripts/review_candidate_frame_mrl15.py`; no record in this scope newly fails those
  criteria, and no criterion was loosened or tightened to reach a count.

"Include" means: no source-based defect was found that blocks writing a public contract
whose wording contains no private fixture input, no expected-output list and no
reference code. It does **not** declare the record ready for collection. Each include
still carries the unresolved dependencies listed below, and every adapted public
contract, public example, private bytes and control must be frozen and validated in a
versioned package before any outcome is produced.

## Scope and immutability

Scope is exactly frame ranks 21-40 in the committed order
**911, 211, 701, 960, 667, 344, 370, 484, 524, 814, 346, 187, 508, 194, 356, 366, 302,
670, 376, 650**. No backfill past rank 40, no rank 41-60 expansion, no rerank, no
replacement of an existing hold. Ranks 41-198 were not inspected: no prompt, code or
assertion of any id outside ranks 1-40 was read, and the one consequence of that
protection is recorded as a dependency in the closing notes. The ranks 1-20 holds
(**31, 847, 907, 963**) and the original holds (**359, 349**) stand untouched, as do all
E11/E12/E13a artifacts.

## Sources and verification

| Artifact | Verified fact |
|---|---|
| `results/frame_review_mrl15_20260922T021718Z/manifest.json` | SHA-256 `4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc`, as specified. |
| `results/frame_review_mrl15_20260922T021718Z/records.json` | SHA-256 `96dad5032cd9b346e1f4056fba6d8a3ab52533b9a702f0e791d710cd5efa0e74`, equal to `manifest.records_sha256`. |
| `manifest.eligible_ordered_ids` | 198 ids; `[20:40]` equals the twenty ids of this scope in the order given above. |
| Order key | `sha256("mrl15-frame-seed-20260922:<task_id>")`; re-sorting all 198 ids by that key reproduces `eligible_ordered_ids` exactly. |
| `manifest.preregistered.outcome_information_used` | `"none"`. `manifest.execution` records `model_calls: 0`, `exec_eval_subprocess: false`, static ops `ast.parse` / `compile` only. |
| MBPP source | `manifest.source.mbpp_path` = `work/sources/mbpp_full.jsonl`, SHA-256 `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`, 974 rows. Both that path and the cached official copy `work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl` exist on this host and **both hash to that value**; the twenty records were read from the `work/task_sources/` copy. |
| Builder | `scripts/review_candidate_frame_mrl15.py`: `N_REVIEW = 20`, `review_ids = ordered[:N_REVIEW]`, `SIM_THRESHOLD = 0.5` fixed before any similarity was computed, family rule = union-find over within-frame pairs at that threshold keeping the smallest seeded hash. |
| Already-used rosters | E11 dev roots `[52, 357, 373, 378, 402, 489, 509]` (`manifest.source.e11_dev_roots`); E13a roster `['mbpp/842','mbpp/288','mbpp/863','mbpp/966','mbpp/652']` (`experiments/landmark/e13a_release/release_manifest.json`, `n_roots: 5`); `prior_seen_root_ids` (598 entries, 434 MBPP-mappable) identical in `dev_release_v1c`, `v2`, `v2_1`, `v3` and `e13a_release` configs. |

For each of the twenty ids the review read, from the cached MBPP source only: the prompt
text, the reference function signature, the reference body (as text and AST, never
executed) and all three official assertions. Every record has three official assertions
and an empty `challenge_test_list`. Reference behaviour statements below are derived by
reading code, not by running it.

The proposed endpoint under review is the one used for ranks 1-20: public example =
`test_list[0]`, private = `test_list[1:]`.

## Ten source-based holds

| Root and interface | Concrete source-based defect | Smallest defensible next action |
|---|---|---|
| **211** `count_Num(n)` | The prompt ("count numbers whose oth and nth bits are set") never says over which set of numbers the count runs, and "oth" is an uncorrected typo. The reference returns a closed form for `n > 1` and a special case at `n == 1`; that value is the count over *n-bit* binary numbers, a universe the prose never names. Nothing in the public prose determines the tested values, and `n <= 0` is outside the reference's own domain (it would return a non-integer). | Hold. Either declare the counting universe and the `n >= 1` domain in a versioned public contract and validate a reference against it, or drop the record. Do not infer the universe from the private expected numbers. |
| **701** `equilibrium_index(arr)` | The prose asks for "the equilibrium index" (definite singular) but fixes neither the tie rule nor the no-solution convention. One private input has **two** valid equilibrium indices (the empty suffix sums to zero at the last position, in addition to an interior one); the reference silently returns the smallest by scanning left to right. A second private input has none, and the reference returns a negative sentinel that the prose never mentions. | Hold. Declare "smallest such index, and a stated sentinel when none exists" in a versioned contract, or restrict the domain to inputs with a unique equilibrium index. Do not read the tie rule or the sentinel off the private expected values. |
| **960** `get_noOfways(n)` | "Write a function to solve tiling problem" names no board, no tile set, no meaning for `n` and no return quantity. The reference is a two-term recurrence with `f(0) = 0`, `f(1) = 1`, i.e. an offset Fibonacci; the usual 2-by-n domino tiling count disagrees with the asserted value at the public argument. The tested function is therefore not recoverable from the prose, and the value at `n = 0` corresponds to no tiling convention. | Hold. This needs a fully stated tiling problem (board, tiles, what `n` counts, base cases) as a new versioned task, with a reference validated against that statement. A prompt clarification alone cannot rescue the original wording. |
| **370** `float_sort(price)` | Three separate mismatches: the prose says "sort a tuple" while every assertion passes a **list of pairs** and the reference returns a list; the prose says "float element" while the sorted key is a **numeric string** in the fixtures, so the returned elements keep their original string spellings and output equality is exact-format dependent; and the prose never states the sort **direction**, while the reference sorts descending and all three expected orders depend on that choice. Ties are unspecified. | Hold. Declare the container type, the element shape, the key-conversion rule, the direction and the tie rule in a versioned contract; only then is a public specification possible. Do not infer descending order from the private expected lists. |
| **484** `remove_matching_tuple(test_list1, test_list2)` | The prose says "remove the matching tuples from the given two tuples", but the assertions pass two **lists** of tuples and the reference returns a **list**, so the stated input and output domains are contradicted by the fixtures. The prose also leaves the direction open (filter the first list, or take a symmetric difference); the public example cannot distinguish them, because there the second argument's elements are a subset of the first, whereas a private case does distinguish them. | Hold. Fix the direction, the container types and the order-preservation rule in a versioned public contract, and add a directional control. Then the record becomes a candidate for inclusion; it must not be resolved by reading the private expected lists. |
| **346** `zigzag(n, k)` | The prose delegates the whole specification to a named integer sequence ("entringer number e(n, k)") whose **indexing convention differs between sources**; the prose fixes neither the triangle orientation, nor the domain `0 <= k <= n`, nor the boundary values, and the single public value does not pin the convention. Writing a public specification that does pin it would amount to restating the reference recurrence in the prompt. The reference also recurses without memoisation. | Hold, and report the ambiguity rather than resolving it. The defensible route is a versioned contract that cites an external published definition (sequence identifier and orientation) plus the declared domain, with a reference validated against that citation, and an explicit runtime bound. |
| **508** `same_order(l1, l2)` | Under the proposed split the private set is **partially recoverable from the public example**: official assertions index 0 and index 2 are byte-identical (same two inputs, same expected value), so one of the two private cases is the public case. Independently, the prose speaks only of "order" while the reference compares the filtered sequences for equality, so equal **multiplicities** are also required, and that convention is not stated. | Hold the proposed split: it leaves one private case answered by the public example. A defensible package needs a genuinely additional private case plus a stated duplicate-handling rule, both frozen before outcomes, not a silent re-slicing afterwards. |
| **670** `decreasing_trend(nums)` | The assertions **contradict the stated semantics**. The prose asks whether the sequence has a decreasing trend; the reference returns true exactly when the input is already in non-decreasing order, and the fixtures encode that inversion (an ascending input is asserted true, a descending input false). A correct implementation of the prose fails all three official assertions, including the public example. | Hold. Either publish a corrected, versioned task whose prose states the non-decreasing test (and rename the entry point, since the current name asserts the opposite), or drop the record. Do not grade candidates against prose that the fixtures invert. |
| **376** `remove_replica(test_tup)` | The prose is self-contradictory ("remove ... and replace the duplicates with some custom value") and leaves the custom value unspecified: the tested behaviour depends on one exact literal placeholder string that appears **only inside the assertions' expected outputs**, so the private cases are answerable only by copying that literal out of the public example. Which occurrence is preserved (the first) is also unstated, and the return is a tuple with mixed element types, so grading is exact-format dependent. | Hold. A versioned contract must name the placeholder value and the keep-first rule in the public prose itself, and state the tuple return; with that done the record is a candidate for inclusion. Do not leave the literal discoverable only from expected outputs. |
| **650** `are_Equal(arr1, arr2, n, m)` | The **reference's behaviour is not implied by the prose**: after sorting, its comparison loop stops one position early, so it reports equal arrays for some unequal same-length inputs; the three official assertions do not expose that (their unequal same-length case differs at the first position, and the remaining unequal case differs in length). The reference also **sorts its arguments in place**, mutating caller data, which the prose does not license, and the multiset (order-insensitive) reading of "equal" is revealed only by the public example. | Hold. Repair the reference under a new version (compare every position, do not mutate the inputs), state the multiset semantics and the role of `n` and `m` publicly, and validate the repaired reference plus a control that a one-position-short comparison fails. Do not release the current reference as ground truth. |

These are specification and measurement findings from source text. None of them is an
observed model error, and none was chosen or ranked by expected receiver difficulty.

## Public interface and domain to freeze for the ten includes

The wording below is general, public-only specification: it contains **no private
fixture input, no expected-output list and no reference code**, and is safe to publish
in a prompt. The reviewed signature is included as interface metadata, without its
implementation. These are *adapted* MBPP contracts and must be versioned before any
outcome exists; they are not claims that the original prose already fixed every
convention.

| Root and interface | Public specification to freeze | Source-based qualification |
|---|---|---|
| **911** `maximum_product(nums)` | "nums is a list of at least three integers; values may repeat and may be negative. Return the largest product obtainable from three distinct positions of the list." | The prose adds "using heap queue algorithm", an implementation hint that output equality cannot verify; state it as non-binding or drop it. The reference's two-candidate formula is general for lists of three or more entries and is undefined below that, hence the explicit size floor. |
| **667** `Check_Vow(string, vowels)` | "string is a text string and vowels is a string of characters to be counted. Return how many characters of string are members of vowels; every occurrence counts separately and matching is by exact character identity, not case-folded." | The prose mentions only counting vowels in a string and never mentions the second parameter, so the two-argument interface must be published explicitly. The reference is a generic membership count; the fixtures never vary the second argument, so the parameter's generality is asserted by the specification, not exercised by the endpoint. |
| **344** `count_Odd_Squares(n, m)` | "n and m are integers with 1 <= n <= m. Return how many integers k with n <= k <= m have an odd number of positive divisors; both endpoints are included." | Needed because "elements with odd factors" also reads as "elements having some odd factor", under which every integer qualifies and the tested counts are wrong. The reference uses floating-point square roots, so the contract must also declare the magnitude range in which exact integer results are required. |
| **524** `max_sum_increasing_subsequence(arr, n)` | "arr is a nonempty list of positive integers and n equals its length. Consider subsequences obtained by deleting entries (positions need not be adjacent) whose values are strictly increasing in list order. Return the largest achievable sum of such a nonempty subsequence." | "Maximum increasing subsequence" also reads as "longest"; the sum-versus-length reading is fixed here. The reference's accumulator starts at zero, which is the empty-subsequence convention for all-negative inputs; the positive-integer domain above is declared so that convention is never silently relied on. Same clarification pattern as retained root 895. |
| **814** `rombus_area(p, q)` | "p and q are the lengths of the two diagonals of a rhombus, each nonnegative. Return the area, that is half the product of the diagonals. A numerically equal integer or real result is accepted." | The prose names only "the area of a rombus" and never says the arguments are the diagonals; a base-and-height reading gives a different answer. The reference's true division returns a real value while the fixtures are written as integers, so the numeric-equality allowance must be explicit. The misspelled entry-point name is retained as interface metadata. |
| **187** `longest_common_subsequence(X, Y, m, n)` | "X and Y are sequences (strings in this contract), m equals the length of X and n the length of Y. Return the **length** of a longest common subsequence: the greatest number of positions that can be chosen increasingly in both sequences with equal elements. The subsequence need not be contiguous." | The prose says "find the longest common subsequence" while the tested return is its length; the public example already exposes an integer return, so making it explicit adds no private information. Parameter roles are unstated in the prose. The reference recurses without memoisation, so a runtime bound belongs in the package. |
| **194** `octal_To_Decimal(n)` | "n is a nonnegative integer whose decimal digits are all in the range 0 to 7; those digits are to be read as an octal numeral. Return the integer value of that numeral in base ten." | The prose does not say whether the octal input arrives as a string or as an integer whose digits are octal; the public example already exposes the integer-in-integer convention. The reference accepts digits 8 and 9 and negative inputs and returns meaningless values, so the domain restriction is declared rather than silently repaired. |
| **356** `find_angle(a, b)` | "a and b are two interior angles of a triangle, measured in degrees, with a > 0, b > 0 and a + b < 180. Return the third interior angle in degrees." | The prose names no unit and no validity condition; degrees are exposed by the public example. The reference performs the subtraction unconditionally and would return a nonpositive angle for invalid inputs, so the domain is declared instead of adding validity behaviour the prose does not imply. |
| **366** `adjacent_num_product(list_nums)` | "list_nums is a list of at least two integers. Consider every pair of positions that are neighbours in the given order; the list is not treated as circular. Return the largest product of such a pair." | The prose fixes neither the minimum length nor the absence of wrap-around. The reference pairs each entry with its successor and is undefined for shorter lists. For the present fixtures a wrap-around reading happens to agree, so the convention is untested by the endpoint and must be stated. |
| **302** `set_Bit_Number(n)` | "n is a positive integer. Return the **value** of its most significant set bit, that is the largest power of two that does not exceed n." | "The most significant bit number" reads equally as the bit position; the public example already exposes the value convention. The reference returns zero at n = 0 and a wrong value for negative inputs, so the positive domain is declared rather than inheriting those unstated conventions. |

## Proposed public/private scoring contract split, per record

Endpoint under review: public example = official assertion index 0, private = indices 1
and 2. "Recoverable" means the private expected values follow from the public example
itself (not merely from the published specification, which by design determines every
answer).

| Root | Public | Private | Recoverable from the public example? |
|---|---|---|---|
| 911 | index 0 | 1, 2 | No. Distinct inputs and values. All three inputs are all-positive, so the negative-value branch of the intended semantics is untested. |
| 211 | index 0 | 1, 2 | No, but one private argument is the reference's special-case boundary. Hold stands on the prose defect. |
| 701 | index 0 | 1, 2 | No. One private case is the ambiguous multi-solution input, the other the no-solution sentinel; both are behaviours the prose omits. Hold. |
| 960 | index 0 | 1, 2 | No; the three arguments are consecutive and the recurrence makes the public value a term of the same sequence, so a solver who infers the recurrence gains both private values. Hold regardless. |
| 667 | index 0 | 1, 2 | No for the counted string; the second argument is the **same literal** in all three assertions and is therefore fully exposed by the public example. |
| 344 | index 0 | 1, 2 | No. Three disjoint ranges. |
| 370 | index 0 | 1, 2 | No, but the descending-order convention is recoverable only from the public expected order, which is exactly the unstated convention. Hold. |
| 484 | index 0 | 1, 2 | No. The public case cannot distinguish the direction that a private case tests. Hold. |
| 524 | index 0 | 1, 2 | No. Three distinct arrays. |
| 814 | index 0 | 1, 2 | No; two arguments recur across cases but the products differ. |
| 346 | index 0 | 1, 2 | Partly: the public argument pair and one private pair share the first argument and differ by one in the second, and the reference's recurrence links them; anyone who reconstructs the convention gets both. Hold. |
| 187 | index 0 | 1, 2 | No. Three distinct string pairs. |
| 508 | index 0 | 1, 2 | **Yes** — private index 2 is byte-identical to the public example. Hold. |
| 194 | index 0 | 1, 2 | No. Three distinct numerals. |
| 356 | index 0 | 1, 2 | No; three distinct angle pairs, though the relation is linear, so one example plus the stated formula answers everything. That is a difficulty observation, not a leak. |
| 366 | index 0 | 1, 2 | Partly: the public input's proper prefix is the first private input, so the private answer is obtainable by re-reading the public input under the stated rule. Not a hidden-value leak, but it is not independent coverage either. |
| 302 | index 0 | 1, 2 | No. Three distinct arguments. |
| 670 | index 0 | 1, 2 | No; but the public example already encodes the inverted semantics. Hold. |
| 376 | index 0 | 1, 2 | No for the inputs; the placeholder literal in the expected outputs is fully exposed by the public example, and it is the only thing the prose fails to state. Hold. |
| 650 | index 0 | 1, 2 | No. Three distinct argument sets; none of them exposes the reference's off-by-one. Hold. |

A different assertion index is assigned in every case. As recorded for ranks 1-20, that
fact alone does **not** establish semantically independent data, and here it demonstrably
fails for 508.

## Known overlap with used roots, within this set, and with prior-seen tasks

Overlap was assessed with the committed similarity rule (`score = max(Jaccard(text
tokens), Jaccard(code identifier tokens))`, threshold 0.5), recomputed statically from
source, plus reading of the prompts. Similarity against ranks 41-198 was **not**
computed, because that would require inspecting protected records.

| Basis | Finding |
|---|---|
| Prior-seen roots | None of the twenty is in `prior_seen_root_ids` or in the E11 dev roots; step (i) of the builder removed those before ordering. Nearest prior-seen scores for the twenty range from 0.0 (960) to 0.4444 (524, 376), all below the 0.5 threshold. Highest pairs: 524 vs prior-seen mbpp/468 (0.4444), 376 vs mbpp/394 (0.4444), 667 vs mbpp/238 (0.4286), 194 vs mbpp/99 (0.4286), 356 vs mbpp/397 (0.4286), 911 vs mbpp/4 (0.4167). |
| E12 retained roster (918, 825, 842, 816, 895, 868, 288, 154, 863, 966, 652, 651, 499, 974) and ranks 1-20 holds (31, 847, 907, 963) | No id overlap. Maximum lexical score against any rank 1-20 record is 0.3333 (524 vs 895; 356 vs the held 359). Two semantic relations are worth recording despite low lexical scores: **524** and retained **895** are both "largest sum of a constrained subsequence of one list" tasks, and **484** and retained **966** (0.2857) are both "remove selected tuples from a list of tuples" tasks. A shared solution schema is plausible; the lexical screen does not detect it. |
| E13a roster (842, 288, 863, 966, 652) | No id overlap with this scope. The relation above between 484 and 966 is the only semantic contact with an outcome-inspected root, and it is a prose/schema resemblance only. |
| Within this set | No pair reaches 0.30; the maximum pair is **911 ~ 366 at 0.25**, and those two are semantically the closest pair here (both maximise a product over entries of one list, over triples versus adjacent pairs). **211** and **302** are both single-integer bit-manipulation tasks (0.14 lexically). **814** and **356** are both one-line closed-form geometry tasks. **701, 524, 366, 650** all take a list and return a scalar. These are lexical and schema observations, not independence claims. |
| Prior-seen benchmark exposure generally | The manifest notes that the 164 `humaneval/*` prior-seen ids cannot map to MBPP task ids and are not similarity-screened because no HumanEval source is pinned. That limitation applies unchanged to these twenty; none of them can be certified unexposed to that portion. |
| Provisional family labels | `records.json` carries `provisional_family` and `family_size_in_frame` only for ranks 1-20. For ranks 21-40 those fields are not committed anywhere, and recomputing them would require comparing against protected ranks 41-198. Each of the twenty is, by construction, the smallest-seeded-hash member of its provisional family, so a within-frame sibling may exist for any of them. |

## Unresolved dependencies, per record

Stated as dependencies, not silently resolved.

| Root | A later release still needs |
|---|---|
| 911 | A validated wrong control: a top-three-largest-only implementation passes all three official assertions, because every fixture is all-positive, so the endpoint as proposed does not reject that fault. Either add a fixture with negatives (new version, frozen before outcomes) or record that the negative branch is unmeasured. Also a ruling on whether the "heap queue" hint stays in the prompt. |
| 667 | A decision on whether the second argument is ever varied. If it stays constant, the contract must say the tested behaviour is the fixed-vowel-set count; if it varies, a new fixture and a validated reference are required. Case-sensitivity must be bound explicitly. |
| 344 | An integer-exactness rule for the square-root computation, and a declared upper bound on the range within which the reference is trusted. |
| 524 | A binding of the `n` argument to the list length (mismatched `n` is unspecified and untested), and either the declared positive domain or a stated all-negative convention. A meaningful wrong control (for example non-strict increase) must be validated. |
| 814 | A ruling on real-versus-integer return comparison for the grader, and whether the misspelled entry-point name is kept as-is across the package. |
| 187 | A runtime bound for the unmemoised reference, and a statement of which sequence types are in the domain (the fixtures are strings while the prose says sequences). |
| 194 | Confirmation that inputs with digits 8 or 9 are out of domain rather than silently graded, and a decision on whether a string-input variant is a separate task. |
| 356 | A decision on whether invalid angle pairs are out of domain (current reference returns a nonpositive number) and on the numeric type of the return. |
| 366 | A statement of the non-circular convention in the frozen prose (it is untested by the fixtures) and a minimum-length domain check, plus a validated control for the wrap-around fault. |
| 302 | A ruling on n = 0 and negative inputs: declare them out of domain, or fix the reference under a new version. |
| 211 | A counting universe for the public prose, a declared `n >= 1` domain, and a reference validated against that statement. |
| 701 | A tie rule and a no-solution sentinel in the public prose, or a uniqueness-restricted domain, plus a control for the wrong tie choice. |
| 960 | A complete tiling statement (board, tiles, meaning of `n`, base cases) as a new versioned task, and a reference validated against it. |
| 370 | Container type, element shape, key conversion, sort direction and tie rule, all in the frozen public prose; then a control that a wrongly-ordered result fails. |
| 484 | Direction, container types and order preservation in the frozen prose, plus a directional control, since the public example cannot distinguish direction. |
| 346 | An external published definition to cite (sequence identifier and triangle orientation), a declared domain, a memoised or bounded reference, and a runtime limit. |
| 508 | A genuinely additional private case to replace the duplicate of the public example, plus a stated duplicate-multiplicity rule. |
| 670 | A corrected prose statement and entry-point name under a new version, or removal; and confirmation that no earlier package already used the inverted wording. |
| 376 | The placeholder literal and the keep-first rule in the public prose, an explicit tuple return, and a control for the wrong occurrence being replaced. |
| 650 | A repaired, non-mutating reference validated under a new version, the multiset semantics and the roles of `n` and `m` in public prose, and a control that a one-position-short comparison is rejected. |

## Summary

- **include (10):** 911, 667, 344, 524, 814, 187, 194, 356, 366, 302
- **hold (10):** 211, 701, 960, 370, 484, 346, 508, 670, 376, 650
- **exclude (0):** none.

Hold grounds, grouped: prose does not determine the tested function at all (211, 960);
unspecified tie-break, sentinel or ordering (701, 370, and the direction in 484);
stated input or output domain contradicted by the fixtures (370, 484); semantics
inverted by the fixtures (670); private set recoverable from the public example (508);
exact-format or magic-literal dependence (376, and the string keys in 370); convention
fixed only by an external indexing choice the prose omits (346); reference behaviour not
implied by the prose (650, 211, 960).

**What this review establishes.** That for twenty specific frame records, read from a
hash-verified official source in a preregistered order, ten have a public interface,
domain and semantics that can be written down without using any private fixture or
reference code, and ten have a named, source-visible defect that must be repaired in a
versioned contract first. Every id, hash and path cited above was verified by reading
the file.

**What it does not establish.** It is source-only: no receiver, reference, control,
public check or sandbox was executed, and no outcome, grade, private execution record or
score was consulted or inferred for any of these records. No record was selected,
retained or dropped by expected receiver difficulty. A disposition is **not** a release:
the ten includes are candidates for an adapted, versioned public-contract package whose
prose, public example, private bytes, reference and controls must all still be frozen
and validated. The provisional family labels are lexical artefacts of one token-Jaccard
rule at one threshold, not an independence certificate; twenty distinct ids are not
twenty independent families, HumanEval exposure is unscreened for all of them, and the
within-frame family structure at ranks 21-40 is not recorded anywhere because ranks
41-198 are protected from inspection. Ambiguities above are reported, not resolved by
outcome screening.
