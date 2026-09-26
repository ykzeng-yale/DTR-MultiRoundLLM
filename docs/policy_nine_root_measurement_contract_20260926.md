# LEAD-ENDPOINT-07 / MRL-37: nine-root measurement package

Codex scientific lead,26 September2026. Prepare a new versioned measurement candidate,`prompt-choice-nine-root-measurement-v1`,for exactly **356,885,354,901,654,703,700,656,36**,in that order. They are the ten roots with no direct prior relation found in LEAD-FRAME-11 minus176's unresolved specification conflict. This is a deterministic source-based measurement panel,not an evaluation roster or nine certified independent families. Keep15 definite-family exclusions,16 plausible-family holds,the679/833 family pair and176's hold; no backfill. The actual family partition,exposure assessment and sampling/execution law remain open.

This panel does not replace the original population,research question,receiver or independent-policy objective. Its adapted public contracts and separately versioned supplemental endpoint are new measurement targets,not silently equivalent to original MBPP or historical E12. A successful measurement audit cannot authorize receiver collection or establish policy efficacy.

## Source and public contracts

Pin the cached original MBPP JSONL SHA256 `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`. Preserve every original description,signature,reference and assertion byte separately.

Use these public contract drafts as the explicit adapted wording,with the original entry point and signature. The sole public case is original assertion0; original assertions1–2 remain a distinct `original_private` battery. No supplemental case or expected value goes into public records or prompts.

| Root | Adapted public wording and material convention |
|---|---|
|356|Given two positive interior angles of a triangle in degrees whose sum is below180,return the third interior angle in degrees. Units and valid domain are explicit.|
|885|Return whether two strings have equal length and the same equality pattern of characters: a bijective character renaming converts one to the other. The empty strings match.|
|354|Given first term a,positive one-based index n and common difference d,return the nth arithmetic-progression term. For this adapted contract a,d are integers; zero and negative differences are permitted.|
|901|For a positive integer n,return the least positive integer divisible by every integer from1 through n. No arbitrary large-n correctness or runtime guarantee follows from the finite cases.|
|654|Given nonnegative integer length and width,return the rectangle perimeter; degenerate zero dimensions are permitted in this adapted arithmetic contract. This domain is explicit and is not a claim that every geometric interpretation permits degeneracy.|
|703|Return whether the supplied hashable key is present in the dictionary; do not test membership among values.|
|700|Count entries in the inclusive interval between the supplied bounds,including repeated entries. The list entries and bounds are all integers or all strings,with ordinary Python ordering; an empty list or reversed bounds yields zero.|
|656|For two equal-length integer arrays and their length n,return the minimum sum of absolute differences over bijective pairings. Empty arrays return zero. Only the returned value is scored; no promise of preserving caller inputs is added.|
|36|For integers0 <= p < q with q>0 and positive one-based N,return the Nth decimal digit after the point in p/q. Terminating fractions have trailing zeros.|

**Correction to the unadopted LEAD-FRAME-11 draft:**700's original second assertion uses strings. Integer-only wording would exclude an original case. The above explicitly supports both homogeneous integer and string domains; do not rewrite that assertion or infer a numeric-only scope. No receiver outcomes informed this correction. Every original case must remain valid under its proposed adapted contract; report any additional contradiction before building a release.

## Frozen supplemental cases

Arguments below are positional literal tuples. Expected values are lead-authored arithmetic/logical expectations,not values computed by executing the references. Preserve this battery as `supplement_v1`,separate from the unchanged original-private battery. The proposed new quality endpoint is passing both batteries; an audit must report them separately as well. This finite suite is neither universal correctness nor proof of secrecy from model training.

|Root|Supplement arguments → expected|
|---|---|
|356|`(60,60) → 60`;`(1,1) → 178`;`(89,90) → 1`;`(30,120) → 30`|
|885|`("","") → True`;`("a","") → False`;`("foo","bar") → False`;`("egg","add") → True`;`("abca","zbxz") → True`;`("abc","xyy") → False`;`("aab","abb") → False`|
|354|`(3,1,7) → 3`;`(5,4,0) → 5`;`(10,4,-3) → 1`;`(-2,3,4) → 6`|
|901|`(3,) → 6`;`(4,) → 12`;`(5,) → 60`;`(7,) → 420`;`(8,) → 840`|
|654|`(0,7) → 14`;`(3,3) → 12`;`(2,9) → 22`;`(1,0) → 2`|
|703|`({},1) → False`;`({"a":1},"a") → True`;`({"a":1},1) → False`;`({0:False},0) → True`;`({1:"x"},2) → False`|
|700|`([0,1,2,2,3],1,2) → 3`;`(["aa","b","c","za"],"b","z") → 2`;`([],0,1) → 0`;`([2,2,2],2,2) → 3`;`([1,2,3],3,1) → 0`|
|656|`([1,4],[2,8],2) → 5`;`([-3,1],[2,-2],2) → 2`;`([],[],0) → 0`;`([5,5,1],[5,1,1],3) → 4`;`([1,10],[10,1],2) → 0`;`([0,10],[4,6],2) → 8`|
|36|`(1,8,1) → 1`;`(1,8,2) → 2`;`(1,8,3) → 5`;`(1,8,4) → 0`;`(2,7,3) → 5`;`(0,3,2) → 0`|

Total46 supplemental cases. No runtime-generated cases or post-result edits under this version.

## Fixed controls

For each root prepare the original reference plus exactly five controls in this order: the three root-specific wrong rules below,constant original public expected output,and lookup of all three original examples with `None` for any other arguments. Lookup compares exact literal argument tuples,including dictionary/list arguments by equality rather than hashability; do not execute source assertions to obtain the examples. Never let the lookup use supplemental cases.

|Root|Wrong rule1|Wrong rule2|Wrong rule3|
|---|---|---|---|
|356|a+b|360-a-b|180-abs(a-b)|
|885|Equal lengths only|Equal counts of distinct characters only|A consistent map from first-string characters to second-string characters,checking equal lengths but permitting many-to-one mappings|
|354|a+n*d|a+(n-1)|a*n*d|
|901|n|n*(n-1)|0|
|654|length*width|length+width|4*length|
|703|Membership among dictionary values|Whether dictionary is nonempty|Always False|
|700|Strict rather than inclusive bounds|Count distinct qualifying entries|Length of the input list|
|656|Sum of absolute differences in original zipped order|Absolute difference of the two array sums|Sum of both arrays|
|36|First decimal digit regardless of N|Digit at N+1 rather than N|Integer quotient of p*10**N by q without taking the last decimal digit|

Source prediction: all nine references pass both private batteries. Every wrong control must fail the supplemental battery,while lookup passes the original examples and fails the supplement. **Original-private rejection is not assumed for every wrong control**:901's return-n rule passes its two original-private cases;700's distinct-count rule also passes its original-private cases. These weaknesses are part of the audit,not permission to replace them. Produce a source-reasoned per-battery prediction table for lead review,retaining any uncertainty. Do not run any control/reference to generate predictions.

## MRL-37 assignment: preparation only

Existing Claude Code experiment worker: acknowledge actual UTC and issuing SHA before starting. One CPU,20 elapsed minutes from acceptance,32MiB new retained output,$0. Zero model calls,receiver/server startup,benchmark/reference/control/assertion execution,sandbox starts,downloads or fits. Ordinary pure builder tests and AST/literal parsing are permitted. Stop with a precise partial handoff at cap; no renewal by implication.

Add `experiments/prompt_choice/nine_root_endpoint_audit.py`,`experiments/prompt_choice/nine_root_endpoint_source_v1.json`,`tests/test_nine_root_endpoint_audit.py`,and ordinary receipts only. Preserve all old builders/configs/results. Use reusable trusted parsing/validation helpers where compatible; do not change the old two-root package to masquerade as this new target. The source builder takes an explicit hash-pinned MBPP path and a fresh output directory,refuses overwrite,mismatch,duplicate/missing IDs or changed assertion structure,and never executes supplied code. Preserve original bytes and bind adapted public prose,public case,original-private,supplement,controls,config and builder with exact canonical hash conventions. Raw third-party source/private packages stay in ignored work. Include all nine roots even if a build gate fails; record the refusal rather than backfill.

Output must fit the existing private grading schema through pure validation; explain any adapter changes required. Do not implement or launch an execution runner in this assignment. Expected later inventory is54 artifacts(reference plus five controls per root),with public,original-private and supplemental checks separately:162 slots,not162 independent observations. That arithmetic is planning only. A later lead-owned audit needs an exact plan,host containment/provenance check,finite runtime/output cap and explicit release.

Tests must cover exact roots/order,all46 literal supplemental cases,all45 control identities,unchanged original bytes,adapted700 string-domain wording,public/private separation,deterministic reproduction,input refusal and no overwrite. No tests may execute benchmark/reference/control source. Report actual affected/full test commands,count,runtime and any unfinished checks. Commit directly to main under repository identity rules; fetch/inspect before push,preserve concurrent work and the existing lock-file deletion. Codex independently reviews and owns all scientific/release decisions.

Full-project submission readiness58%,change0 percentage points. No efficacy or independent-policy credit. Measurement validity,remaining family/sampling decisions and a complete prospective development/evaluation/resource freeze remain the largest milestones. E14 N1/S1 stays NO-GO; the full history-conditional learned-prompt research goal remains active.


## Pre-execution source correction and discrimination witnesses

The worker accepted the original source-only draft `f418699` at23:40:01Z (`1cc93f9`),before the46-case correction `c3a4c29`. Its original deadline remains2026-09-27T00:00:01Z; this correction does not reset or extend the cap. The earlier sentence claiming it had not been dispatched was incorrect: the worker watches commits directly. No benchmark/control/reference or model execution was authorized by either version. Static lead review found that its six885 supplemental cases did not reject the equal-distinct-count control. This revision adds the seventh885 case(aab,abb),which has equal distinct counts but different equality patterns,and changes703's third control to Always False to avoid duplicating its constant-public-True control. The exact total is46 supplemental cases;54 artifacts/162 planned slots are unchanged. This is a disclosed source correction before any payload or model execution,not an outcome-selected amendment.

For each root,the following are source-reasoned failure witnesses for wrong rules1–3,constant-public and original-example lookup,in that order. Case numbers are one-based within the frozen supplement table. Values are predictions,not observed executions.

|Root|Rule1|Rule2|Rule3|Constant|Lookup|
|---|---|---|---|---|---|
|356|case1:120≠60|case1:240≠60|case1:180≠60|case1:44≠60|case1:None≠60|
|885|case3:True≠False|case7:True≠False|case6:True≠False|case2:True≠False|case1:None≠True|
|354|case1:10≠3|case2:8≠5|case1:21≠3|case1:9≠3|case1:None≠3|
|901|case1:3≠6|case3:20≠60|case1:0≠6|case1:360360≠6|case1:None≠6|
|654|case1:0≠14|case1:7≠14|case1:0≠14|case1:60≠14|case1:None≠14|
|703|case2:False≠True|case3:True≠False|case2:False≠True|case1:True≠False|case1:None≠False|
|700|case1:0≠3|case1:2≠3|case1:5≠3|case1:6≠3|case1:None≠3|
|656|case2:8≠2|case6:0≠8|case1:15≠5|case1:0≠5|case1:None≠5|
|36|case2:1≠2|case1:2≠1|case2:12≠2|case1:5≠1|case1:None≠1|
