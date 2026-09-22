# Independent measurement review of E12 v3

22 September 2026. Independent evidence reviewer for the coordinating scientific
agent. Reviewed delivery `e518cc146c40e7a1c55c7c20b9f190576a656aff` and source
package commit `9d4a1f26524339ba4922496c79e3f2315edf94db`.

**Disposition: accept the v3 task/measurement package and its saved validation
evidence for the existing MRL-16 bundled development release. No additional
measurement gate or rerun is requested.** The existing fresh receiver-window and
execution conditions remain in force; this review does not create another
approval round or claim that receiver collection has happened.

## Contract and source correspondence

The package is `experiments/landmark/dev_release_v3/`. Its 14 roots preserve the
approved order exactly:

918, 825, 842, 816, 895, 868, 288, 154, 863, 966, 652, 651, 499, 974.

All 14 public prompt strings match the exact clarification table in
[the contract review](e12_contract_review_20260922.md). In particular, 288 uses
the explicitly approved general-modulus domain, 863 ignores original array order,
652 specifies a string representation, and 966 declares its mixed tuple/string
domain. Holds 31, 847, 907, 963, 359 and 349 are preserved without backfill.

Each reference is byte-identical to its pinned MBPP source. Each private suite is
exactly source `test_list[1:]` (two assertions), while its single public example
has the source `test_list[0]` entry point, literal arguments and expected value.
The public context renders that same example and the required interface. Private
specs have empty `public_assertions` and empty preambles, so the public example
is not counted again in the private endpoint. Public task hashes match all 14
private-spec bindings. The public row schema contains only root, family, prompt
and public context; no private assertion was inserted into that text.

The source file used for comparison was the cached official MBPP file
`work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl`, with the matching pinned
SHA-256 `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`.
Seven package-file hashes match the release manifest and their bytes at the
source package commit. The release manifest itself also matches that commit.
All eight listed grading-source hashes match current files and that source commit;
the private/public validators' recorded source bindings also match the inspected
files.

## Saved validation reconciles

Reviewed bundle:
`results/e12_dev_v3_20260922T030255Z_validation/`.
All four artifact hashes in `ARTIFACT_SHA256SUMS.json` match their files. Its
own SHA-256 is
`fce1b642b55d3208d9672765e8cd5bcb6c47cb9f184dc9ee2d937ae4c5cdbb76`.
The package release-manifest SHA-256 is
`c9d591ffd4a524992ced28c1cc2f68fc5c299cc14ad8022e587eefc5bb67d3ea`.

| Saved evidence | Independently reconciled finding |
|---|---|
| Private `attempts.jsonl` and `summary.json` | 28 job starts, 28 program starts and 28 results: one reference and one control for each root. All 14 references score 1; all 14 controls score 0; every result has one start, no timeout and `as_expected=true`. |
| Private control rejection | Each saved stderr ends in an `AssertionError` at a private assertion. Controls were executed and rejected on a graded assertion, rather than merely failing parsing, being unavailable, or receiving an infrastructure zero. No integrity flags are recorded. |
| Public `ledger.jsonl` and `result.json` | 14 starts and 14 results, one reference per root; each public example passes with no observed error reason under display v2. The recorded runner is real, with zero retries. |
| Code and data identity | All reference/control code hashes match the exact package bodies. Public and private records bind the package/spec/example hashes; summary rows match the detailed ledgers. |
| Attestation binding | Both validation paths bind the same saved attestation hash, `74389aa74c588bc4f295ff6d695ca0f4dad4caae721b480f00889e0cba1b9b94`, and the inspected sandbox source. This review did not rerun containment or inspect the worker host live. |
| Start accounting | 28 private + 14 public = **42 starts**. The stated prior ledger 174 therefore becomes **216**, leaving 196 starts under the existing 412 ceiling. |

The saved private summary reports 0.7 seconds of sandbox wall time. Public ledger
reservation-to-completion timestamps span approximately 0.631446 seconds. These
are producer-recorded timings, not a fresh execution measurement by this reviewer.

## Controls and overlap

The source-designed wrong controls target the intended operations: ordered rather
than unordered coin counting; shifted indices; first-element selection; retaining
the uncleared tuple; ignoring nonadjacency; counting words rather than word length;
omitting the modulus; taking a row instead of a column; using original-order runs;
removing nonempty tuples; omitting the transpose; reversing subset direction;
squaring rather than doubling the radius; and maximizing rather than minimizing
the path sum. Their recorded private rejections support these concrete controls.
Root 816 correctly retains the constant empty-tuple function as valid behavior;
its wrong control returns the original nonempty tuple.

Independent parsing of the literal call arguments reproduces the saved overlap
audit: **no full public/private call-input repeats**; shared argument positions
occur for 918, 288 and 154; repeated public/private expected outputs occur for
842, 816 and 651. Root 154 retains the same matrix with different requested
columns, and 816 has the same correct output for all inputs. These limitations
are disclosed and do not reinstate the rejected claim of semantic independence
“by construction.” None requires changing this already scoped finite-roster
development run.

The public context explicitly declares Python equality, without numeric type
identity or resource-efficiency scoring. This agrees with the source assertions.
The string-output contract for 652 is explicit; it is not a numerical tolerance
problem. The private suffix remains only two assertions per root. One rejected
wrong program per root establishes the specified discrimination check, not a
general correctness guarantee or a false-pass rate across all incorrect programs.

## Scope of this review

There were **293 passing read-only correspondence, hash, ledger and count checks**
with no detected discrepancy. The automated reading/parsing/hash portion took
approximately 0.315 seconds, excluding manual semantic review and this report.
Those checks are not 293 benchmark executions or a rerun of the project tests.
No candidate, reference, control, sandbox, model or upstream evaluator was executed
by this reviewer; no task was regenerated.

All task rows retain the shared `unresolved_development_family` label. The separate
provisional family screen is not proof of independence or uniform family sampling.
The accepted evidence concerns the adapted task contracts and the worker's saved
validation results. It is not prompt-efficacy evidence, broad benchmark validity,
or independent-policy confirmation. Proceed within the existing bundled release
when its already specified receiver-window and runtime conditions hold.
