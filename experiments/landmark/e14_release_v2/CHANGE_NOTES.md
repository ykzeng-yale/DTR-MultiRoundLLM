# E14 release change notes (immutable)

Package: `e14-ten-root-versioned-release`  ·  builder `scripts/build_e14_release.py`
Lead specification: `docs/e14_lead_measurement_spec_20260923.json` (sha256 `fa8687e3024767a3e48137f8a9f784e3d4b73981059446da2fbe69c3bdf9fc23`)
Source file: `official MBPP full cache; identity is the file sha256, local path deliberately not recorded` (sha256 `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`, verified before reading)

## 1. This is a NEW endpoint version, not a rescoring of E12/E13

The private suite of every root gains assertions. A score produced against this suite is therefore NOT
comparable to an E12 or E13 number and is not a re-grading of any historical output. The E11/E12/E13 negative
results stand unchanged, and no historical package is touched: `dev_release_v2*`, `dev_release_v3`,
`e13a_release` and everything under `results/` are read-only inputs here.

The frozen scorer is unchanged (`landmark-grader-v5-parse-and-compile-fault-attribution`). `terminal-output-contract-v2` is a COMMON INTERVENTION INSTRUCTION
shared byte-identically by both arms. It is NOT an added primary-score rule, NOT a format-compliance gate and
NOT a validated semantic-compliance classifier.

## 2. What changed, per the lead's ten binding decisions

Each root retains its original private assertions at source indices 1 and 2 and adds every private assertion
the lead listed. Public prose is the lead's `public_contract`, which states the input domain explicitly and, for
911, drops the original "using heap queue algorithm" algorithm requirement. Reference implementations are
VERSIONED where the lead required it (344 exact integer square roots via `math.isqrt`; 187 iterative length
dynamic programming with a zero boundary row and column, replacing exponential recursion so reference runtime is
not part of the task; 194 integer division `temp // 10`; 302 integer division `n // 2` returning the bit VALUE)
and preserved otherwise. Every root gains two negative controls: the lead's specified semantic fault and a
correctly interfaced always-None control.

Roster order is exactly 911, 667, 344, 524, 814, 187, 194, 356, 366, 302. It is unchanged from the lead's `candidate_roster_order`.

## 3. The ten held ids stay held

211, 701, 960, 370, 484, 346, 508, 670, 376, 650 remain held and untouched. No new source roster was drawn, no reserve record was semantically inspected,
and no outcome was inspected while building this package.

## 4. Source-exposure limitations, carried forward as THREE SEPARATE FACTS

1. **Whole-source mechanical processing.** Reproducing the earlier selection frame loaded the full MBPP file and
   recomputed text/code features and full-frame similarity beyond rank 40. It did not load only the twenty
   selected records. Filename guards are not access logs, and matching a stored frame is a reproducibility check,
   not an attestation about every agent read.
2. **Twenty-record semantic review.** Semantic review covered twenty records. The provisional family labels and
   sizes for all twenty were already recorded; the size-nine group represented by 356 and the size-two group
   represented by 194 are lexical-screen groups, not independent sampling units.
3. **No reported new model-outcome inspection.** No new model outcome was inspected for this package. This is a
   separate claim from (1) and (2) and neither implies nor is implied by them.

## 5. What this package does NOT establish

Nothing here was executed. No reference, control, candidate, public check or containment program was run, not
even as a quick correctness check; the failure predictions in `controls_rationale.json` are declared hand traces.
Static validity (`compile`, `ast.parse`) and a clean `integrity.hack_gate` are not executability, not integrity
clearance and not correctness. The positive references and the negative controls still require later isolated
validation. Finite discriminating fixtures improve coverage of the named faults; they do not establish semantic
completeness or receiver competence. These remain small adapted coding tasks, with no claim of novelty, realism
or independent policy efficacy.

## v2 repairs (MRL-24, lead 45f7aa7) — additive; the v1 package is preserved unchanged

- **Portable reproduction.** The source is identified by its file sha256 only. v1 wrote the locally resolved
  cache path into this file and the manifest, so identical bytes at the two known cache locations produced
  different packages. v2 builds byte-identically from either location.
- **Inherited legacy field removed.** v1 copied `branch_replicates: 2` from the older release config, which
  conflicts with this design's six draws per arm. The authoritative E14 schema is the `e14` block; the E14
  adapter refuses a conflicting legacy field rather than silently overriding it.
- **Phase limits stated once.** v1 carried an inherited 1,560-second `max_seconds` budget. v2 sets
  `max_seconds` to the collection limit and records every governing phase limit in `e14.phase_limits_seconds`:
  setup 600, collection 480, private grading 300, analysis 300, outer 2,700. These remain planning values until
  an explicit later release.
- No task, assertion, reference, control, public contract or endpoint changed.
