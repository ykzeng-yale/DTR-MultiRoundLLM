# Independent source review of the proposed E12 contracts

22 September 2026. Independent evidence reviewer for the coordinating scientific
agent. This is a source-only review of all 18 mechanically included records, not
receiver evidence, reference execution, or a family-independence certificate.

**Disposition:** retain the fixed order and hold **31, 847, 907, 963**. The remaining
**14 roots are eligible for a new, explicitly adapted public-contract package and
subsequent reference/control validation**, subject to the clarifications below:

**918, 825, 842, 816, 895, 868, 288, 154, 863, 966, 652, 651, 499, 974.**

No replacement roots are proposed. The original holds 359 and 349 remain holds.
This does not declare any of the 14 ready for receiver collection. Root 288 needs
an explicit domain amendment; it must remain held if the package retains the
original prime-only wording. Other retained roots also need their exact public
contract, tests and controls bound to the new package, rather than treating the
mechanical `include` label as semantic clearance.

## Sources and verification

Reviewed repository head: `25e65151029fc66c68629e3d56ec78cda2f83c7a`.
The source is the cached official MBPP file
`work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl`, SHA-256
`ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`.
It matches the source hash in
`results/frame_review_mrl15_20260922T021718Z/manifest.json`; the worker's recorded
`work/sources/mbpp_full.jsonl` path need not exist on this host. All 18 prompt and
reference-code hashes match `records.json`. The official pinned source is
[google-research MBPP](https://github.com/google-research/google-research/blob/4700efb9afa54286b0e04473ba80a13e8461e25f/mbpp/mbpp.jsonl).

The review read the actual prompt, function signature, reference body and all
three source assertions for each root. Reference source was parsed as text/AST
only. No candidate, reference, model or upstream evaluator was executed. The
proposed endpoint was read from `docs/e12_proposal_20260922.md`: public assertion
`test_list[0]`, private assertions `test_list[1:]`, and a do-nothing control.

## Four source-based holds

| Root | Concrete defect | Smallest defensible next action |
|---|---|---|
| **31** | The prompt requests the top-k most frequent integers, but does not specify tie selection or output order. All three assertions use the same input matrix with different k. The reference retains/replaces tied elements through insertion/heap behavior and returns a particular ordered list; an equally valid top-k set or conventional descending order can fail. The public k=3 case does not define a general tie rule. The algorithm requirement itself is not verified by output equality. | Hold this version. Either declare a complete tie/order rule and validate a corresponding reference, or use a semantic top-k validator that accepts all permitted ties/orders. Both require a versioned contract; do not infer an arbitrary rule from private expected lists. |
| **847** | The text asks to copy a list from a singleton tuple, whereas all assertions call the function with a bare list. The reference returns `xs[:]`; equality-only assertions accept returning `xs` itself, so they do not distinguish a copy from an alias. | Hold. Choose and state the input type and shallow-copy semantics, then add identity/mutation-sensitive controls under a separate version. Merely passing the current reference and a `None` stub does not validate copying. |
| **907** | The public example requests ten lucky numbers; both private cases request shorter prefixes of that same revealed sequence. Their complete expected outputs are recoverable by slicing the public example. The text also says print, while all assertions require a returned list. | Hold the proposed split. Define the lucky-number sieve and return interface publicly, and freeze genuinely additional cases that are not already answered by the exposed prefix. This requires a new measurement version and validation, not a silent rearrangement after outcomes. |
| **963** | The prompt asks only for a discriminant value, but assertions require a tuple containing an exact message and the number. The public case exposes only one message category; the private cases require other exact strings/capitalization. The final private input has both quadratic and linear coefficients zero and a nonzero constant, but the reference labels it as one solution solely because the discriminant is zero. That is not a valid classification of the equation. The heuristic missed strings nested in tuple returns. | Hold. A clean alternative is a numeric-discriminant-only contract or a fully specified equation-classification contract with an appropriate coefficient domain and tests. Do not repair this by copying private message strings into the public prompt or by calling the original private case a valid quadratic. |

These are specification/measurement findings, not observed model errors. Literal
assertion strings differ for every public/private pair in the 18 roots; that fact
does **not** imply distinct underlying data, semantic nonoverlap, or answer secrecy.

## Exact public clarifications for the 14 retained candidates

The following text supplies general interfaces, domains and semantics. It contains
no private fixture inputs or private expected output lists. These are **adapted
MBPP contracts**, and must be versioned before outcomes. They are not assertions
that the original prose already specified every convention. Include the reviewed
function signature as interface metadata, without its implementation.

| Root and interface | Public specification to freeze | Source-based qualification |
|---|---|---|
| **918** `coin_change(S, m, n)` | “S is a nonempty list of distinct positive integer coin denominations, m equals its length, and n is a nonnegative integer amount. Return the number of unordered combinations totaling n when each denomination may be used any number of times; permutations of the same coins count once.” | Original “count coin change” leaves amount/count/ordering and parameter roles unspecified. This states the usual unbounded-combination problem implemented by the source. |
| **825** `access_elements(nums, list_index)` | “Return a list containing the elements of nums at the supplied indices, preserving the order and repetitions in list_index. Use Python list indexing; each supplied index is valid.” | Public example supplies a reasonable interface; clarify index-list order and indexing explicitly. No tested source contradiction found. |
| **842** `get_odd_occurence(arr, arr_size)` | “arr is a nonempty integer list, arr_size equals its length, and exactly one distinct value occurs an odd number of times. Return that value.” | The source returns the first odd-frequency value if several exist and a sentinel if none exists. Those cases are not specified by the original singular task or exercised by its assertions; the declared unique-odd domain avoids silently imposing an arbitrary tie/sentinel rule. |
| **816** `clear_tuple(test_tup)` | “Given a tuple, return the empty tuple obtained by clearing all its elements. No in-place mutation is requested.” | The correct function is constant. Every source assertion checks the same output. Retain transparently as a simple task; do not label a constant empty-tuple implementation a wrong control or infer generalization from distinct inputs. Do not exclude it based on anticipated ceiling. |
| **895** `max_sum_subseq(A)` | “A is a nonempty list of integers. Return the largest sum of a nonempty subsequence whose chosen positions are never adjacent in the original list.” | The empty-subsequence convention matters for all-negative inputs; an empty input crashes the source. The source implements the declared nonempty version. This clarification is needed before adding boundary checks. |
| **868** `length_Of_Last_Word(a)` | “Words are separated by ordinary spaces. Ignore leading/trailing spaces and return the length of the last word; when no word exists, treat the last word as the empty string. Inputs use spaces rather than other internal whitespace separators.” | The source resets on ASCII space, not arbitrary internal whitespace. The private suite includes an empty-string boundary. State the general no-word convention publicly instead of assuming the first example explains it. |
| **288** `modular_inverse(arr, N, P)` | “P is an integer modulus at least two, N equals the length of the integer list arr, and duplicate entries count separately. Count entries whose residue is invertible modulo P and equal to its own multiplicative inverse.” | **Explicit domain amendment:** the original says prime, but a private assertion uses a composite modulus. The source checks the correct self-inverse congruence for general P. Either adopt this broadened, versioned modulus contract or hold 288; do not grade an originally prime-only task on an undisclosed composite case. |
| **154** `specified_element(nums, N)` | “Return the element at zero-based column N from each row of nums, preserving row order. N is nonnegative and every row contains that position.” | All source assertions reuse one matrix while varying the column. This is limited within-instance coverage, not unseen-matrix validation. |
| **863** `find_longest_conseq_subseq(arr, n)` | “arr is a nonempty integer list and n equals its length. Ignore the original order and repeated copies of a value. Return the length of the longest run of consecutive integer values present in the list.” | Original “subsequence” may imply order preservation. The public example does not resolve this, while private cases require ignoring order. The reference sorts/deduplicates. Clarify semantics rather than penalizing a legitimate order-preserving interpretation. |
| **966** `remove_empty(tuple1)` | “The input is a list whose elements are tuples or nonempty strings. Remove the empty tuples and preserve every other element and its order.” | Source fixtures contain bare strings written with parentheses, not only tuples. The reference removes all false-valued objects; on this declared input domain that agrees with removing empty tuples. A broader domain containing other false-valued objects needs a reference repair and new controls. |
| **652** `matrix_to_list(test_list)` | “The input is a list of rows containing equal-length tuples. Visit those tuples in row-major order, collect each tuple-component position into a tuple, and form a list of those component tuples. Return the standard Python string representation of that list.” | The prose requests a tuple list, but the reference returns its string representation. The public assertion already exposes that representation convention; make it explicit. Exact string formatting is part of this adapted endpoint. |
| **651** `check_subset(test_tup1, test_tup2)` | “Return whether every distinct element of the second tuple occurs in the first tuple. Element order and multiplicity do not matter.” | Clarifies direction and set rather than multiset containment, consistent with reference and public example. |
| **499** `diameter_circle(r)` | “r is the nonnegative radius of a circle. Return its diameter.” | Clarifies the input quantity. Source assertions use integers; no numerical-tolerance issue is demonstrated by these cases. |
| **974** `min_sum_path(A)` | “A is a nonempty triangular list of integer rows, with row i containing i+1 entries. Starting at the top, move from position j to position j or j+1 in the next row until reaching the bottom. Return the smallest sum including both endpoints.” | Original text omits allowed moves. This states the standard adjacency rule implemented by the source; no tested source contradiction found. |

## Measurement conditions for the next package

1. Preserve this source-selected reduced roster and all four new holds; no backfill.
   Freeze the adapted public prose, signatures, public example and private bytes
   before receiver outcomes. Validate the **new** package's references and controls;
   prior seven-root validation does not cover these roots.
2. Replace “public and private cases do not overlap by construction” with the
   narrower fact that different source assertion indices are assigned. Root 907
   disproves semantic nonoverlap; 31 and 154 reuse their full underlying input data
   while varying a parameter. Record these distinctions rather than assuming a
   hidden-only file establishes independent generalization.
3. Two private assertions and a failing do-nothing stub demonstrate little
   discrimination. They do not establish rejection of plausible wrong programs.
   Use a source-based meaningful wrong control for each retained contract, whose
   fault concerns the intended operation and whose rejection is actually validated;
   retain the stub separately if useful. For 816, the constant empty-tuple solution
   is correct and must be accepted. Do not select new controls using receiver outputs.
4. These 18 source tasks use integer-valued/count outputs, lists/tuples, booleans
   or strings, not approximate real-valued targets. The exact-format problems in
   31/652/963 are not fixed by a floating-point tolerance. Future noninteger-radius
   or other numerical extensions require an explicit domain and comparison rule;
   do not invent a precision failure in the present integer fixtures.
5. The family screen is provisional and omitted HumanEval semantic comparisons.
   Fourteen retained IDs are not fourteen established independent families. The
   prospective source selection is useful development discipline; it does not
   retrospectively make the benchmark unexposed or make this a confirmatory study.

The eligible roster is concrete. Remaining release decisions concern its declared
adapted target, package validation, runtime and budget; this review supplies no
new execution authority or efficacy claim.
