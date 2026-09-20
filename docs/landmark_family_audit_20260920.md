# Fixed-slate landmark family and specification audit

**2026-09-20; source-only development curation.** The fixed 24-task slate contains **seven probable prior-family exclusions, ten material specification exclusions, and seven tasks retained for further contract review**. No replacements were selected. Every selected task remains a development candidate; none is certified ready to run, independent of old families, or suitable for confirmation.

This audit uses the pinned official full MBPP source and canonical 591-root task file from the preceding source audit. Source hashes, all 242 official-test candidate IDs, screening evidence, exact signatures, and all 24 decisions are in `results/landmark_family_audit_20260920/manifest.json`. `adjudications.json` preserves the manual decisions independently of regenerated screening output. `all_candidate_screen.json` preserves screening evidence for the entire 242-ID pool. No benchmark reference body, assertion, expected value, or model outcome is embedded in the screening output.

## Frozen selection and scope

Seed: `landmark-development-20260920-v1`. Rank each of the 242 previously identified official-test candidate IDs by the ascending SHA-256 digest of UTF-8 `seed + ':' + decimal_id`, breaking ties by ID, and take the first 24. This rule avoids random-library/version dependence. The ranked slate was announced before similarity screening and manual adjudication:

`289, 402, 357, 373, 39, 378, 159, 34, 157, 52, 509, 336, 43, 488, 489, 44, 202, 220, 386, 365, 189, 371, 13, 112`.

Task selection and decisions used descriptions, source ASTs, and original benchmark tests, with no candidate/model outcomes and no program execution. Reviewing tests for specification agreement is curator access, not a grant of receiver access. The slate is preserved even though only seven tasks remain plausible for contract development. The exclusion counts describe this fixed development slate; they are not an estimated rate of invalid tasks or a power calculation for a larger population.

## Reproducible screening

`scripts/audit_landmark_families.py` checks the exact source hashes before proceeding. It compares all 242 candidates against **591 old roots and 1,018 public-description variants**: each canonical description plus each used MBPP root's original full-source description. This prevents sanitized rewrites from obscuring earlier task identity.

Lexical screening uses NFKC/case-folded word tokens, a fixed boilerplate stop list, term-frequency times smoothed inverse-document-frequency weights, and cosine similarity. Input-type words such as list, string and number are retained. The IDF corpus contains source descriptions only. The output keeps the top eight unique prior roots, collapsing old-source variants. A cosine of at least 0.60 flags review, without automatically excluding or accepting a task. There are 70 such flags among 242 candidates and nine among the selected 24.

Structural screening parses references as AST data. It reports exact function-shape hashes after erasing identifier names while retaining constants and attribute names, plus AST node-bigram similarity and shared function names. The erasure loses binding distinctions, and node similarity reflects syntax rather than behavior. These are review aids, not semantic equivalence proofs. Twenty-five of 242 candidates have an exact erased-shape or shared-name flag. All 591 canonical references parsed; parsing is not code execution or validation. Best structural evidence can come from a different source variant than the best lexical description.

For the 24 selected tasks, the evidence reviewer read each original description, reference and three tests, reviewed retrieved old-task neighbors, and performed targeted source searches for related operations. The root researcher separately inspected the same slate and provided a cross-review of specification issues. The final evidence decisions incorporate that cross-review; this was not blinded inter-rater validation, and no agreement statistic is claimed. Similarity preprocessing was refined during source-only development to retain input-type words; the seed, candidate pool and selected slate did not change.

## Manual decisions: preserve every selected root

| ID | Decision | Provisional family | Evidence and reasoning |
|---:|---|---|---|
| 13 | Exclude: specification | word frequency ranking | Description says dictionary; reference/tests consume a sequence of words and return top four (word,count) pairs. Four, ordering and tie behavior are absent. Frequency/mode prior tasks share ingredients, but this is not an established identical endpoint. |
| 34 | Exclude: prior family | missing integer search | Sorted missing-number search is close to old 627 and selected 371/189, with a one-based single-gap variant. Missing range/gap assumptions are unspecified. Third original test gives N=5 for six elements; N cannot silently be labeled array length. |
| 39 | Exclude: specification | adjacent distinct rearrangement | Prompt asks whether rearrangement is possible; reference constructs a string and tests demand one exact ordering. Multiple valid rearrangements may be rejected by the literal grader. |
| 43 | Exclude: prior family | regex lowercase underscore | Same lowercase-underscore regex predicate as old 16. Original-source function AST matches after identifier erasure; sanitized old 16 returns Boolean while selected 43 expects two magic strings absent from the prompt. |
| 44 | Exclude: specification | regex word at start | Regex tasks about z share a coding idiom but have different predicates. Selected 44 expects exact magic success/failure strings without specifying them, and word-character convention is unstated. |
| 52 | Retain for contract review | parallelogram area | Rectangle-area prior 458 has the same two-input multiplication shape, but geometry differs. Treat as a potential broad geometry family, not proof of duplicate task identity or independent family. Formula and interface are otherwise conventional. |
| 112 | Exclude: specification | cylinder perimeter | Cylinder perimeter is not a unique geometric quantity. Reference computes twice diameter plus height, compatible with a particular rectangular cross-section, not a defined perimeter of a solid. |
| 157 | Exclude: specification | run length encoding | Run-length encoding is recognizable but prompt does not specify pairs as [count,value], run order, or list versus string handling; tests rely on that representation. |
| 159 | Exclude: specification | calendar season | Month-length classification is a related calendar operation rather than the same task. Season boundaries and hemisphere/convention are unspecified; wording says print while tests expect a return value. |
| 189 | Exclude: prior family | missing integer search | First missing positive in an unsorted array generalizes the same missing-integer family as old 627 and selected 34/371, although algorithm, ordering and zero handling differ. Extra n and input mutation are not explained by prose. |
| 202 | Exclude: prior family | alternating character selection | Selected 202 retains zero-based even indices, exactly the operation old 226 describes; old 437 is the complementary alternating selection. Even characters is ambiguous without indexing convention. |
| 220 | Exclude: prior family | punctuation to colon substitution | Same punctuation substitution as old 732 with a count parameter. Python re.sub count=0 replaces all, conflicting with a literal maximum of zero occurrences unless n is restricted to positive integers. |
| 289 | Exclude: specification | cumulative calendar odd days | Given year suggests one calendar year, whereas source counts excess weekdays accumulated over N years using leap/century corrections. The time interval and origin are absent. |
| 336 | Exclude: prior family | month day count classification | Same month-length classification family with 28 replacing 30/31 and names replacing numbers. Every month contains at least28 days; reference instead selects February, without leap-year semantics. |
| 357 | Retain for contract review | flattened tuple maximum | Tuple-record top-k and word unique-letter maximum are different targets; shared find_max name is not a duplicate. Source casts each item to int, so arbitrary numeric inputs would not implement their true maximum. Tests use integer tuples. |
| 365 | Exclude: specification | integer decimal digit count | Counting decimal digits of an integer differs from counting digit characters in mixed text (old 764). Source returns zero for0 and repeated floor division of negative integers never reaches0. This is a static control-flow finding, not an executed failure. |
| 371 | Exclude: prior family | missing integer search | Both locate first missing nonnegative integer in a sorted sequence by index-based search. Selected left/right arguments and nonnegative zero-origin universe are absent from prose. |
| 373 | Retain for contract review | cuboid volume | Cube and triangular-prism volume tasks are related elementary geometry but have different parameterizations/formulas. No exact task identity established; broad geometry transfer remains possible. |
| 378 | Retain for contract review | right rotate list one | Moving final element to front differs from swapping endpoints (old 625/591). Digit circular-shift HE65 is related but includes integer/string-specific behavior and arbitrary shifts. |
| 386 | Exclude: specification | minimum bracket balance swaps | Minimum swaps depends on adjacent-only versus arbitrary swaps, absent from prose. Source accumulates adjacent distances. Balance recognition and binary-string transformation prior tasks are related, not identical optimization endpoints. |
| 402 | Retain for contract review | binomial modulus | nCr modulo p is recognizable. Other binomial-sum tasks share mathematical ingredients but compute different functions. Source uses dynamic programming and does not require prime p. |
| 488 | Exclude: specification | regular pentagon area | Area is determined from one side only for a regular pentagon, unstated. Original assertions compare floating-point outputs by exact equality; mathematically valid equivalent formulas may round differently. Perimeter prior 171 is related but a different target. |
| 489 | Retain for contract review | frequency of maximum | Counting a supplied target value (old 168) differs from finding maximum then counting its occurrences. This is a related composition, not established semantic duplicate; source extra n must be documented. |
| 509 | Retain for contract review | positive odd prefix mean | Mean of positive odd integers through n is different from filtering/selecting odd list values. Positive-odd domain is conventional but not explicit; negative odd inputs yield zero-count division by static inspection. |

## Family judgment versus shared coding operations

The seven prior-family exclusions are **34,43,189,202,220,336,371**. The missing-integer group contains selected 34/189/371 and old 627. Their order assumptions and positive versus nonnegative universes differ; this is a conservative same-family judgment, not a claim of identical functions. Selected 43 has the same regex predicate as old 16, including an identifier-erased AST match in the original source. Selected 202 implements old 226's alternating-index selection and relates to the complement old 437. Selected 220 adds a count parameter to old 732's substitution. Selected 336 changes the requested month-length class and input representation from old 455/762.

The review deliberately does not label all shared coding operations as duplicate families. Parallelogram area52 and rectangle area458 share a multiplication expression, but geometry differs; the match flags possible broad-family transfer without settling task identity. Cuboid volume373 versus cube volume234 is similar. Rotation378 differs from endpoint swapping625/591. Frequency-of-maximum489 composes selection and counting, differing from supplied-value counting168. Digit count365 versus text digit-count764 remains a high lexical match (0.878) despite different input/target functions. A shared `find_max` name between357 and HumanEval158 is a naming collision. These distinctions are recorded rather than converted into an unsupported independence certificate.

The manifest groups the 24 tasks into 22 provisional named families, including one three-task missing-integer group. **These 22 labels are organizational hypotheses, not 22 independent sampling units.** Semantic equivalence/relatedness is not transitive in all useful senses, and threshold-connected components would not justify family independence. The remaining 218 candidates received mechanical screening only, not manual adjudication.

## Specification and interface disposition

The ten specification exclusions are **13,39,44,112,157,159,289,365,386,488**. Their problems include missing output representation, conflicts between requested and scored behavior, undefined geometric/calendar targets, unstated swap costs, and fragile floating-point grading. Negative-number nontermination in365 is inferred from floor-division control flow; no hanging program was executed. Likewise, multiple valid strings potentially rejected for39 and alternate formula rounding for488 are measurement concerns, not measured false-negative rates.

The retained development candidates are **52,357,373,378,402,489,509**. Each remains conditional on a public contract and validated grading. In particular:52 needs base/perpendicular-height definitions;357 needs nonempty integer tuple records or a repair to its integer coercion;373 needs dimension conventions;378 needs return/empty-list behavior;402 needs integer n,r and positive modulus with 0<=r<=n, without imposing an unnecessary primality restriction;489 needs nonempty input and n semantics;509 needs an explicit positive-odd domain. These proposed domain clarifications do not silently alter the original benchmark. If adopted, record a new task-specification version and preserve the original disposition.

All 24 selected references have a single top-level function with no defaults, annotations or decorators. The script exports **interface metadata only** (function name and arguments), never a body. Defaults, annotations or decorators in other candidates block automatic signature export pending leakage and semantic review. Names and arguments themselves remain part of the declared intervention environment; they must be frozen with the public prompt.

The implementation agent's proposed private grader row has `root_id`, `public_task_sha256`, `entry_point`, `public_assertions`, `private_assertions`, `preamble`, and `reference_code`; the public task hash binds the exact public row. This audit does not instantiate or approve a test split. Original tests and any later repaired tests remain outside collector access unless explicitly assigned to the public partition. No public assertion is counted again in the private score. Semantic leakage, discriminative power, sandbox containment and the receiver contract are separate gates still open.

## Reproduction and checks

```sh
python3 scripts/audit_landmark_families.py \
  --full work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl \
  --canonical /Users/yukang/Documents/Codex/2026-09-18/fur/work/DTR-AgentEvals/work/restoration_reconstruction_13bad73/tasks.json \
  --source-audit results/landmark_task_source_candidates_20260920.json \
  --out work/landmark_family_audit_reproduction_NEW \
  --adjudications results/landmark_family_audit_20260920/adjudications.json
python3 -m unittest discover -s tests -p test_landmark_families.py -v
```

**Seven source-audit tests passed for the original execution.** They check order-independent selection, no duplicate sampling, identifier-renaming flags while retaining constants, blocked export of defaults/annotations, absence of source execution/body leakage, preservation of input-type tokens, and old-variant collapse without automatic exclusion. No reference or candidate was executed; no receiver/model call or Git mutation occurred. The full project test suite was not rerun for this isolated source-audit addition.

The scientific next step is to review/freeze specifications for the retained seven **without replacing excluded roots**, validate the grading contract and sandbox, and use that small slate only for development. A larger confirmatory cohort requires a separate prespecified sampling/curation process, broader prior-use and family review, and no carryover of development outcomes into test selection. Low similarity, different source ID, and a passing reference remain insufficient evidence of semantic independence or verifier reliability.

## Public-only interface review draft

A non-runnable seven-row draft is saved in the ignored `work/landmark_family_audit_20260920/public_interface_review_draft.jsonl`. It preserves original descriptions and adds only the reviewed function signature; proposed domain clarifications remain in separate review notes. Every row uses the shared `unresolved_development_family` placeholder, preventing an accidental claim that IDs establish independent families. This is neither a final family assignment nor an approved study freeze.

File SHA-256: `772f0a3639f04b66de0a1cd494c6fe6a9f888585a21f72a81bc97edfd27521eb`. Exact row hashes use the collector's canonical JSON digest and are also saved in `public_interface_draft_metadata.json`.

| Draft root | Public-task SHA-256 |
|---|---|
| mbpp/52 | `d2f2be6d3be82b1a11dce341dfd18db7f7ed42f8667e38feee5dda3c7ae1089d` |
| mbpp/357 | `0bdb76a526dcf9481341685d7c448fd59fb5868ea4a6dd7025be7d55323f5bdf` |
| mbpp/373 | `2aeef13955c553ff4421722fdb3971d4e414755047b33d378a5c376f6e05a98e` |
| mbpp/378 | `e5fdca1b834b58436304deee0cae897ebfcc08e85db56625fed99f22211462cd` |
| mbpp/402 | `37e5fbd07d7193df28ff55c6d3301c8fece7cb392afb2d9e1cd2c1f5aca41120` |
| mbpp/489 | `c2fc97b373819877bf79ac92b50c11d5cfa59658d0595b7978bf189d24f6147c` |
| mbpp/509 | `d4f18e5dc1449309b8024a84aabd5771467fc1201f5610b6c77829e050d5b1c9` |

## Immutable results correction

The original completed `manifest.json` and `all_candidate_screen.json` are unchanged. The exact script that generated them is archived at `results/landmark_family_audit_20260920/audit_script_at_execution.py`, SHA-256 `e351fa391ba6c028ff83cab1ac055f7535b1f2ea6ac5d075408826af553d553e`, matching the original manifest. The current CLI differs only by a fail-before-write guard: if either completed output already exists, it requires a new output directory. A pre-existing adjudications input in the destination directory is allowed. The reproduction example above deliberately targets `work/landmark_family_audit_reproduction_NEW`; choose another unused directory if that already contains completed outputs.

The new regression test checks each completed output separately, verifies failure before source-input reads, and verifies that existing outputs and adjudications remain byte-identical. Eight tests passed after this repair. No screening rerun was performed, and original result provenance was preserved. The earlier `verification.json` is a historical snapshot; `immutability_guard_verification.json` records the current source/test/document hashes and unchanged result hashes.
