# Prospective task-source candidates: full official MBPP

**Audit date:** 2026-09-20. **Status:** source acquisition and static comparison only; no model calls, candidate/reference execution, new outcome collection, or Git mutations. This report corrects an overly broad reading of “the old pool is exhausted”: the inspected 591-root pool is exhausted, but the official full MBPP source supplies additional candidate IDs.

## Result and source pin

The full source has **974 unique, contiguous task IDs, 1–974**. The canonical pool has 427 MBPP roots and 164 HumanEval roots. Its 427 MBPP IDs exactly equal the official sanitized subset, and all 427 normalized canonical descriptions match that subset. Full MBPP therefore supplies **547 IDs outside the canonical pool and all seven inspected prior episode files**. These are candidate IDs, not established fresh confirmatory roots.

The acquisition pins Google Research repository commit `4700efb9afa54286b0e04473ba80a13e8461e25f` (2026-09-16). GitHub's path-specific commit query reports the last change to `mbpp/mbpp.jsonl` as `f82046ba5aabbbb427dbfd38a254d26bff08b533` (2022-03-31). The pinned [full source](https://raw.githubusercontent.com/google-research/google-research/4700efb9afa54286b0e04473ba80a13e8461e25f/mbpp/mbpp.jsonl), [sanitized source](https://raw.githubusercontent.com/google-research/google-research/4700efb9afa54286b0e04473ba80a13e8461e25f/mbpp/sanitized-mbpp.json), source README, root README, and repository LICENSE are saved under the Git-ignored `work/task_sources/mbpp_full_20260920_4700efb9/` directory. No benchmark solutions are added to tracked artifacts.

| Artifact | SHA-256 |
|---|---|
| Official full MBPP | `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` |
| Official sanitized MBPP | `ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9` |
| Canonical 591-root task file | `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce` |

## Duplicate audit and official splits

Description normalization is Unicode NFKC, case folding, and whitespace collapse. We compare candidates against all 591 canonical public descriptions **and** the original full-source descriptions of the 427 previously used MBPP IDs. This second comparison matters: 237 of those 427 descriptions differ after sanitization. A second normalization additionally removes punctuation; it finds the same prior-root duplicate set.

| Candidate ID | Prior MBPP root with the same normalized description |
|---|---|
| 217 | 602 |
| 704 | 248 |
| 928 | 427 |

Excluding these three leaves **544 candidate IDs**, comprising **542 distinct normalized descriptions**. Two duplicate pairs remain within this set: **76/347** and **216/872**. These counts concern literal description equivalence, not semantic equivalence. Distinct wording or IDs does not establish a distinct task family; no family assignments were manufactured.

The official source defines the following splits and identifies the sanitized file as a hand-verified subset. The edited subset inherits the original groupings. [Official MBPP README](https://raw.githubusercontent.com/google-research/google-research/4700efb9afa54286b0e04473ba80a13e8461e25f/mbpp/README.md)

| Official split / ID range | Full pool | Previously used IDs | Candidate IDs | After prior-description exclusions | Distinct descriptions in that row |
|---|---:|---:|---:|---:|---:|
| Few-shot prompting / 1–10 | 10 | 7 | 3 | 3 | 3 |
| Test / 11–510 | 500 | 257 | 243 | 242 | 241 |
| Validation / 511–600 | 90 | 43 | 47 | 47 | 47 |
| Train / 601–974 | 374 | 120 | 254 | 252 | 252 |
| Total | 974 | 427 | 547 | 544 | 542 overall |

The distinct-description column does not sum to the overall total because 216/872 crosses official splits. All ID lists and duplicate mappings are in `results/landmark_task_source_candidates_20260920.json`. For a bounded first curation batch, the **242 official-test candidate IDs, with 241 literal descriptions**, provide a clear starting pool before semantic and measurement exclusions. Calling a task an official test task does not establish that the receiver never encountered it during training.

## Prior-use evidence and its scope

The canonical file is the restored `DTR-AgentEvals/work/restoration_reconstruction_13bad73/tasks.json`. Its 591-root design includes the 30 pilot roots separately from 231 training and 330 confirmation roots. The prior-use scan read every row of these sibling raw episode files; their hashes and MBPP IDs are recorded in the JSON.

| Prior file under `DTR-AgentEvals/results/` | Rows | Unique task IDs | Unique MBPP IDs |
|---|---:|---:|---:|
| `code_routing/log/episodes.jsonl` | 4,488 | 561 | 407 |
| `code_routing/pilot/episodes.jsonl` | 120 | 30 | 20 |
| `code_routing/live/episodes.jsonl` | 3,960 | 330 | 239 |
| `code_routing/branch/episodes.jsonl` | 800 | 103 | 73 |
| `local_pilot/episodes.jsonl` | 80 | 44 | 0 |
| `local_pilot_calibration/episodes.jsonl` | 160 | 88 | 0 |
| `local_pilot_reasoning/episodes.jsonl` | 80 | 44 | 0 |

Their union contains exactly the same 427 MBPP IDs as the canonical pool; none adds a full-source candidate ID to the exclusion set. The three local-pilot task files contain arithmetic tasks. This is a bounded local evidence statement: other workspaces, remote runs, unpublished pilot use, semantic relatives, and model pretraining are not exhausted by this scan. The new full-source task descriptions have now been inspected for acquisition/curation; their candidate outcomes have not been generated or examined in this audit.

## Source quality and scoring gates

All 547 ID-level candidates are outside the hand-verified subset. Every candidate has three original tests; 539 have no challenge tests, seven have one, and one has three. Two have nonempty test setup code. No empty description, reference source, or test list was found. Python AST parsing found no syntax errors in candidate source, setup, or original tests, but emitted some regex escape warnings. **No reference or candidate program was run.** Parseability establishes neither reference correctness nor an adequate verifier.

A coding landmark collector must still freeze a public task contract, entry-point/signature construction, permissible imports/setup, a visible-feedback contract, and an outcome evaluator. The source's original tests are public benchmark assets. Tests withheld from a receiver prompt may be an evaluation partition; they are not genuinely secret benchmark tests. Reusing all tests in feedback would invalidate a claim that the terminal endpoint tests unseen requirements. With just three original tests, withholding some also creates an explicit trade-off in verifier coverage that must be measured.

Before treating any subset as confirmatory, complete semantic duplicate and prior-use review; curate task/specification consistency without looking at treatment effects; validate the frozen evaluator on correct references **and discriminating incorrect programs** in the approved sandbox; preserve public-versus-evaluation separation; and lock task/family exclusions and analysis rules before generating treatment outcomes. The earlier zero-check and reference-only certification failures make this a measurement gate, not optional polish. A new ID or new seed alone does not satisfy it.

The Git-ignored `public_description_candidates.json` contains the 544 remaining IDs and public descriptions only, without reference code or test contents. It is an acquisition index, not an approved prompt payload or executable study configuration. The immediate inexpensive next step is semantic/specification curation of a fixed batch from the official-test candidates, followed by sandboxed scoring validation. This acquisition does not repair the absent receiver service or complete the landmark collector described in the feasibility report.

## Licensing

The pinned Google Research root README assigns **CC BY 4.0 International to datasets** and **Apache 2.0 to source files**. Preserve dataset attribution and provenance for any redistributed derivative; do not label the MBPP dataset Apache-only. The root README and Apache LICENSE were downloaded. A direct fetch of the linked Creative Commons legal-code page returned HTTP 403, recorded in the manifest; the repository's dataset-license declaration remains available. [Pinned license declaration](https://raw.githubusercontent.com/google-research/google-research/4700efb9afa54286b0e04473ba80a13e8461e25f/README.md), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode)

**Disposition:** a real additional source is available at zero API cost: 547 ID-level candidates, 544 after prior literal-description exclusions, 542 distinct normalized descriptions. Genuine prospective confirmation remains conditional on the named duplicate, prior-use, measurement, and execution gates. No new empirical result is claimed.
