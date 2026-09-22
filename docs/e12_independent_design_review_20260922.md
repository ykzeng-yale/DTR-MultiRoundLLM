# Independent internal design review of E12

Reviewed source: `25e65151029fc66c68629e3d56ec78cda2f83c7a`. Scope: E12 proposal, MRL-15 frame review, revised sampling proposal, the frame-selection source, and relevant grading-adapter accounting. This review ran no simulations, models, references, candidates or sandbox jobs. It is a design review, not execution validation.

**Decision:** E12 can proceed as a bounded, prospective, descriptive development study after one bundled, outcome-blind package preflight. Retain the proposed roster rather than start another sampling/review cycle, but withdraw the uniform-family and smallest-informative-study claims. The current package is not executable as proposed; the bindings and budget require repair before dispatch.

## Sampling and target

`review_candidate_frame_mrl15.py` first retains the minimum-hash root in each provisional family (line 332), then ranks those same minimum hashes to select the first 20 (lines 354–355). This is not uniform family sampling. Even if root hashes are ideal independent uniform priorities, a family with two members beats a singleton with probability two-thirds, not one-half. The fixed hash ordering itself is reproducible, not an independently verified probability-sampling mechanism.

The practical repair is to retain the 18 proposed roots as a **prespecified hash-priority development roster**, subject only to logged, pre-collection specification/instrument holds, with no backfill. Its unweighted descriptive mean is a roster summary; it is not a uniform-family or representative full-MBPP estimate. If a later study requires uniform family sampling, it needs a separately defined family-level draw and within-family selection rule before its outcomes. This study need not be delayed for that separate design.

The counts 396, 384, 235 and 198 describe successive mechanical/prior-use/similarity filters. The 198 representatives have not all passed the final specification review: only 20 were reviewed and 18 received static `include` decisions. Those decisions remain provisional until the task specifications and instruments are checked. The 0.5 similarity rule and one-per-provisional-family selection do not establish independence; HumanEval prior use was not similarity-screened. Report new receiver outcomes on previously uncollected roster IDs, without asserting untouched semantic families or absence of benchmark contamination.

## Primary comparison and interpretation

Keep S1 minus N1 primary: the average within-root difference between two final private-suite grades per arm, using the same frozen initial prefix and identical public-diagnostic bytes. Use the independent arm/replicate streams actually proposed for E12; remove the older proposal's conflicting reference to coupled continuations. Initial histories and diagnostic execution belong to the versioned intervention contract. This is a specified instruction comparison, not evaluation of a learned selector or proof of long-horizon policy benefit.

Report the primary contrast over every assigned roster root. Initial private STOP correctness may define secondary descriptive repair and damage strata, but must not select roots or enter prompts. Missing outcomes remain missing, with all-assigned descriptive completion bounds; do not silently replace the target by complete cases. Retain the other prespecified contrasts and costs. No population interval, usefulness claim or null-based stopping is released for E12; align the older sampling note with this descriptive scope.

Replace the following wording in `e12_proposal_20260922.md`:

- “E11 answered nothing” is incorrect. Its complete primary contrast was a valid observed null on seven reused development roots; format failures and damage were also informative. That scope does not establish population equivalence.
- “The smallest study that can observe repair” is unsupported. A smaller study can observe repair, and 18 roots do not guarantee any failing initial answer.
- “Informative only if some roots fail at STOP” is incorrect. Initially correct roots inform damage avoidance, including a possible S1–N1 difference. The historical 0.6 success rate is an illustrative planning assumption, not a calibrated prediction for this newly filtered, differently prompted roster.

## Public/private measurement contract

Taking `test_list[0]` as public and `test_list[1:]` as private establishes distinct list positions, not distinct call inputs or semantic independence. Before any receiver call, check the actual partition and public-task/specification agreement. Show the public example and expected value before the initial answer for every arm; keep the private suffix inaccessible to collection and rendering. Freeze the one-example diagnostic schema and exact renderer behavior rather than inherit an assumption of three public examples.

The retained private suffix, generally two assertions here, defines a thin **suite-passing endpoint**, not complete program correctness. A stub that failed the old full suite is not thereby known to fail the new private suffix. Reference and negative-control checks must use that exact suffix. A do-nothing control alone provides limited discrimination evidence; do not describe it as comprehensive validation of repair. Preserve any pre-collection semantic holds without replacement, and do not modify cases in response to receiver outcomes. This endpoint and history law differ from E11 and must not be pooled with it.

## One bundled release, with corrected accounting

The new-package validation and final grading are distinct operations. `study_adapter.py` rechecks references and negative controls inside final grading (lines 290–304). With one control per root and no caching, 18 roots require:

- 36 initial private reference/control starts;
- 18 public diagnostic starts;
- 198 artifact-grading starts;
- 36 reference/control rechecks inside final grading.

That is **288 starts**, not 252. Adding one public-reference validation per root gives **306 starts**. The receiver ceiling remains **198 calls and 101,376 reserved completion tokens**. Any further controls, canaries or retries require explicit ledger entries. A new 306-start allowance would be separate from the old 200-start cap; carried forward from 174, the cumulative ceiling would be 480. The final grading phase alone can require 234 starts, above the adapter's current 200 maximum.

The adapter also binds the older `dev_release_v2` manifest and 77-artifact/24-recheck plan (lines 380–382). Repair these release-specific bindings and ceilings explicitly; do not bypass verification or rely on an implicit larger frame. The seven-minute extrapolation is not a worst-case runtime guarantee.

To avoid serial permission cycles, the lead can issue one conditional package authorization covering preparation, validation and collection, with all of the following checked together before receiver dispatch:

1. Publish one immutable roster/specification/partition/source/renderer/seed/analysis manifest. Apply only declared outcome-blind holds, publish the retained count and reasons, and do not backfill.
2. Bind the adapter and grader to that package and complete its focused source checks and exact reference/control/public-reference validation under the stated start ledger. A shared integrity or containment failure stops dispatch; failed checks are retained.
3. Verify the current receiver/owner window, pinned settings, attestation and resource availability. Freeze the new allowance, one-CPU limit, collection time limit and outer wall-clock cap together. A smaller retained roster uses a smaller corresponding maximum; unused capacity does not authorize retries or extra roots.
4. Once these conditions pass, proceed within the same authorization, retaining every assigned failure and publishing complete or partial artifacts at the cap. No further threshold, outcome-screening, favorable-interval or renderer decision is made after collection begins.

This is a practical release contract for exploratory evidence. It does not certify independent families, sample-size adequacy, useful gain, semantic prompt personalization or readiness for a confirmatory policy trial.
