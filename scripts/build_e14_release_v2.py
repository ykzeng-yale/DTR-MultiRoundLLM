#!/usr/bin/env python3
"""E14 release builder, VERSION 2 (MRL-24 criterion 5): portable content identity, no inherited legacy
replicate field, explicit phase limits. The v1 builder, scripts/build_e14_release.py, is preserved byte-for-byte
so the MRL-23 package still reproduces from it.

E14 ten-root versioned measurement package builder.

EVIDENCE CLASS: source-bound prospective measurement package (bindings + static validity only). This script
produces NO measurement. It performs zero model/receiver calls and zero candidate, reference, negative-control,
public-check or containment EXECUTIONS. It parses source, calls compile()/ast.parse for static validity, and
calls integrity.hack_gate (a static AST gate). It never runs a reference or a control -- not even "as a quick
correctness check". Control failure predictions in controls_rationale.json are HAND TRACES declared in this
file's PREDICTED_SEMANTIC table, not observed outputs. The release manifest it writes authorizes none of those
executions either (authorization.receiver_calls_authorized == 0,
authorization.candidate_executions_authorized == 0).

Inputs, every one sha256-verified before use:
  * docs/e14_lead_measurement_spec_20260923.json -- the coordinating lead's binding specification. Its
    added_private_assertions, reference_version_requirement and negative-control requirements are SCORER-ONLY.
  * the cached official MBPP file, whose sha256 must equal the spec's source_file_sha256, and whose per-record
    text / code / test_list sha256s must equal the spec's source_text_sha256 / source_reference_sha256 /
    source_assertions_sha256 (the last derived as sha256(json.dumps(test_list))).
  * experiments/landmark/dev_release_v3/ -- the frozen receiver request law reused by config.json, gated on
    that release's own manifest hashes. dev_release_v3 is read only and never modified.

PUBLIC/PRIVATE BOUNDARY (the spec's public_private_boundary, enforced here):
  * tasks.jsonl and public_examples_v3.json carry ONLY root_id, the lead's public_contract prose, the original
    entry point and signature as interface metadata, and the rendered original assertion index 0.
  * private_specs.jsonl and controls_rationale.json carry the retained original private assertions (source
    indices 1 and 2), the lead's added_private_assertions, the versioned reference and both negative controls.
    They are scorer-only. The lead JSON is never emitted wholesale and never reaches a prompt.
  * _assert_public_carries_no_private() scans the public bytes against every private string before writing.

Unknown or unresolved values are refusals, never zero-fills. Refuses to overwrite an existing output directory;
--verify rebuilds into a temporary directory and diffs the committed bytes.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.landmark.collect import digest, file_sha, source_hashes  # noqa: E402
from experiments.common.integrity import hack_gate  # noqa: E402

MANIFEST_ID = "e14-ten-root-versioned-release"
RELEASE_DIRNAME = "e14_release"
DEFAULT_OUT = "experiments/landmark/e14_release"
DEFAULT_OUT_V2 = "experiments/landmark/e14_release_v2"
# MRL-24 criterion 5: v2 records the source by CONTENT identity only. v1 serialized the locally resolved cache
# path, so identical bytes at the two known cache locations produced different packages (non-portable). v1 is
# preserved unchanged as the historical MRL-23 package.
SOURCE_IDENTITY_V2 = "official MBPP full cache; identity is the file sha256, local path deliberately not recorded"
LEGACY_FIELDS_REMOVED_V2 = ("branch_replicates",)
PHASE_LIMITS_V2 = {"setup": 600, "collection": 480, "private_grading": 300, "analysis": 300, "outer": 2700}
V2_CHANGE_NOTES = """
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
"""
DEFAULT_SPEC = "docs/e14_lead_measurement_spec_20260923.json"
DEFAULT_SOURCE_FILE = "work/sources/mbpp_full.jsonl"
ALT_SOURCE_FILE = "work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl"
DEFAULT_LAW_RELEASE = "experiments/landmark/dev_release_v3"

ROSTER = (911, 667, 344, 524, 814, 187, 194, 356, 366, 302)
HELD_IDS = (211, 701, 960, 370, 484, 346, 508, 670, 376, 650)
PUBLIC_ASSERTION_INDICES = (0,)
RETAINED_PRIVATE_INDICES = (1, 2)

PACKAGE_FILES = ("tasks.jsonl", "public_examples_v3.json", "private_specs.jsonl", "controls_rationale.json",
                 "config.json", "CHANGE_NOTES.md")
LAW_PACKAGE_FILES = ("tasks.jsonl", "private_specs.jsonl", "public_examples_v3.json", "controls_rationale.json",
                     "config.json")
EXECUTION_SOURCES = ("scripts/build_e14_release.py", "experiments/landmark/grade.py",
                     "experiments/landmark/sandbox.py", "experiments/landmark/diagnostic.py",
                     "experiments/landmark/study_adapter.py", "experiments/common/integrity.py")

DIAGNOSTIC_SCHEMA = "public-diagnostic-v2"

# E14 design: 10 roots x (1 fresh initial + 2 arms x 6 draws) = 10 + 120 = 130 fixed call slots.
N_ROOTS = 10
N_ARMS = 2
DRAWS_PER_ARM = 6
INITIAL_SLOTS = N_ROOTS
CONTINUATION_SLOTS = N_ROOTS * N_ARMS * DRAWS_PER_ARM
CALL_SLOTS = INITIAL_SLOTS + CONTINUATION_SLOTS

# grading_limits keys are exactly study_adapter.GRADING_LIMIT_KEYS plus the optional containment_starts, so
# study_adapter.load_grading_limits accepts them. artifact_starts = the lead's 140 candidate starts
# (10 initial-public + 10 initial-private + 120 continuation-private); recheck_starts = the grader-side 30
# reference/control rechecks (10 + 20); containment_starts = 18 for two nine-check epochs.
GRADING_LIMITS = {"n_roots": N_ROOTS, "artifact_starts": 140, "recheck_starts": 30, "containment_starts": 18,
                  "max_private_starts": 188, "grading_seconds": 600}
# The lead's explicit planning inventory (MRL-23 item 3). Recorded separately because load_grading_limits is
# strict about grading_limits' key set; precollection instrument starts are not grading-plan slots.
PLANNING_INVENTORY = {
    "model_attempts": CALL_SLOTS,
    "reserved_completion_tokens": 66560,
    "total_isolated_starts": 228,
    "containment_starts": 18,
    "precollection_instrument_starts": 40,
    "grader_side_recheck_starts": 30,
    "candidate_starts": 140,
    "note": ("Upper planning allowance only, NOT execution authority. 18 + 40 + 30 + 140 = 228. Every attempted "
             "or uncertain start counts; no cache saving renews a cap. A lower 198-start figure is possible only "
             "if the connected path proves the 30 grader-side rechecks are not run and validated reference/"
             "control evidence is safely reusable under all current bindings."),
}

AUTHORIZATION_STATEMENT = (
    "This package binds inputs, identities, static validity and bookkeeping limits only. It authorizes NO model "
    "or receiver call and NO candidate, reference, negative-control, public-check or containment EXECUTION. No "
    "reference or control in this package has ever been run, including for a quick correctness check; every "
    "control failure prediction is a declared hand trace. E14 instrument validation and model collection remain "
    "held pending independent review of this package and satisfaction of its operational gates."
)

MISSINGNESS_RULES = [
    "Keep every assignment; never drop, retry or replace a slot.",
    "Suppress the primary point contrast if ANY primary branch grade is missing.",
    "Report binary completion bounds with NO missing-at-random assumption.",
    "A failed initial generation leaves its twelve continuation slots missing: do not fabricate an answer, "
    "substitute a task-only intervention, retry, or remove the root.",
    "A valid-but-incomplete public diagnostic uses the predeclared public-only incomplete-information "
    "instruction.",
    "Environment/containment and receiver-law failures keep their existing stop rules.",
    "Candidate private scoring starts only after collection is closed.",
    "No outcome-based roster change or tuning mid-batch.",
]
REPORTING_RULES = [
    "Report the finite-sample contrast, per-root counts and all-assigned completion bounds DESCRIPTIVELY.",
    "No normal confidence interval, no Hoeffding interval, no efficacy declaration, no futility declaration.",
    "Seeds are reproducibility settings, not proof of independent draws.",
    "Inclusion probability is 1 for every one of the 130 slots; balanced order is scheduling only and is not a "
    "binary treatment propensity requiring inverse-propensity weighting.",
]

# ------------------------------------------------------------------ per-root versioned references (TEXT ONLY)
# Each honours the lead's reference_version_requirement for that root. NEVER EXECUTED by this builder.
REFERENCES = {
    911: "def maximum_product(nums):\n"
         "    import heapq\n"
         "    a, b = heapq.nlargest(3, nums), heapq.nsmallest(2, nums)\n"
         "    return max(a[0] * a[1] * a[2], a[0] * b[0] * b[1])\n",
    667: "def Check_Vow(string, vowels):\n"
         "    final = [each for each in string if each in vowels]\n"
         "    return len(final)\n",
    344: "import math\n"
         "\n"
         "\n"
         "def count_Odd_Squares(n, m):\n"
         "    return math.isqrt(m) - math.isqrt(n - 1)\n",
    524: "def max_sum_increasing_subsequence(arr, n):\n"
         "    max = 0\n"
         "    msis = [0 for x in range(n)]\n"
         "    for i in range(n):\n"
         "        msis[i] = arr[i]\n"
         "    for i in range(1, n):\n"
         "        for j in range(i):\n"
         "            if arr[i] > arr[j] and msis[i] < msis[j] + arr[i]:\n"
         "                msis[i] = msis[j] + arr[i]\n"
         "    for i in range(n):\n"
         "        if max < msis[i]:\n"
         "            max = msis[i]\n"
         "    return max\n",
    814: "def rombus_area(p, q):\n"
         "    area = (p * q) / 2\n"
         "    return area\n",
    187: "def longest_common_subsequence(X, Y, m, n):\n"
         "    table = [[0] * (n + 1) for _ in range(m + 1)]\n"
         "    for i in range(1, m + 1):\n"
         "        for j in range(1, n + 1):\n"
         "            if X[i - 1] == Y[j - 1]:\n"
         "                table[i][j] = table[i - 1][j - 1] + 1\n"
         "            else:\n"
         "                table[i][j] = max(table[i - 1][j], table[i][j - 1])\n"
         "    return table[m][n]\n",
    194: "def octal_To_Decimal(n):\n"
         "    dec_value = 0\n"
         "    base = 1\n"
         "    temp = n\n"
         "    while temp:\n"
         "        last_digit = temp % 10\n"
         "        temp = temp // 10\n"
         "        dec_value += last_digit * base\n"
         "        base = base * 8\n"
         "    return dec_value\n",
    356: "def find_angle(a, b):\n"
         "    c = 180 - (a + b)\n"
         "    return c\n",
    366: "def adjacent_num_product(list_nums):\n"
         "    return max(a * b for a, b in zip(list_nums, list_nums[1:]))\n",
    302: "def set_Bit_Number(n):\n"
         "    if n == 0:\n"
         "        return 0\n"
         "    msb = 0\n"
         "    n = n // 2\n"
         "    while n > 0:\n"
         "        n = n // 2\n"
         "        msb += 1\n"
         "    return 1 << msb\n",
}

REFERENCE_VERSION_NOTE = {
    911: "Original heap-based reference preserved verbatim modulo line-ending/whitespace normalization.",
    667: "Original membership-count reference preserved (parenthesized return normalized to return len(final)).",
    344: "Versioned: math.isqrt(m) - math.isqrt(n - 1) replaces int(m**0.5) - int((n-1)**0.5). No floating roots.",
    524: "Original dynamic-programming reference preserved; strict arr[i] > arr[j] kept; positive domain declared.",
    814: "Original half-product reference preserved; true division kept so 3,5 -> 7.5.",
    187: "Versioned: standard iterative LCS length DP with a zero boundary row and column replaces the exponential "
         "recursion. Signature (X, Y, m, n) preserved, so reference runtime is not part of the task.",
    194: "Versioned: temp // 10 replaces int(temp / 10); digit accumulation retained. No float rounding.",
    356: "Original subtraction reference preserved.",
    366: "Original adjacent-pair reference preserved.",
    302: "Versioned: integer division n // 2 in both locations; algorithm and returned bit VALUE preserved.",
}

# ------------------------------------------------------------------ per-root semantic negative controls (TEXT)
SEMANTIC_CONTROLS = {
    911: ("def maximum_product(nums):\n"
          "    import heapq\n"
          "    a = heapq.nlargest(3, nums)\n"
          "    return a[0] * a[1] * a[2]\n",
          "Multiplies only the three largest values, ignoring the two-negative-factor product."),
    667: ("def Check_Vow(string, vowels):\n"
          "    fixed = 'AaEeIiOoUu'\n"
          "    final = [each for each in string if each in fixed]\n"
          "    return len(final)\n",
          "Ignores the vowels parameter and always uses the fixed set AaEeIiOoUu."),
    344: ("import math\n"
          "\n"
          "\n"
          "def count_Odd_Squares(n, m):\n"
          "    return math.isqrt(m - 1) - math.isqrt(n - 1)\n",
          "Counts square integers in the half-open interval [n, m), excluding the upper endpoint."),
    524: ("def max_sum_increasing_subsequence(arr, n):\n"
          "    max = 0\n"
          "    msis = [0 for x in range(n)]\n"
          "    for i in range(n):\n"
          "        msis[i] = arr[i]\n"
          "    for i in range(1, n):\n"
          "        for j in range(i):\n"
          "            if arr[i] >= arr[j] and msis[i] < msis[j] + arr[i]:\n"
          "                msis[i] = msis[j] + arr[i]\n"
          "    for i in range(n):\n"
          "        if max < msis[i]:\n"
          "            max = msis[i]\n"
          "    return max\n",
          "Uses nondecreasing (arr[i] >= arr[j]) rather than strictly increasing subsequences."),
    814: ("def rombus_area(p, q):\n"
          "    area = (p * q) // 2\n"
          "    return area\n",
          "Uses integer floor division for half the product, so an odd product loses the .5."),
    187: ("def longest_common_subsequence(X, Y, m, n):\n"
          "    table = [[0] * (n + 1) for _ in range(m + 1)]\n"
          "    best = 0\n"
          "    for i in range(1, m + 1):\n"
          "        for j in range(1, n + 1):\n"
          "            if X[i - 1] == Y[j - 1]:\n"
          "                table[i][j] = table[i - 1][j - 1] + 1\n"
          "                if table[i][j] > best:\n"
          "                    best = table[i][j]\n"
          "    return best\n",
          "Computes the longest common CONTIGUOUS substring length instead of the subsequence length."),
    194: ("def octal_To_Decimal(n):\n"
          "    return n\n",
          "Treats the input as an ordinary base-ten integer and returns it unchanged."),
    356: ("def find_angle(a, b):\n"
          "    c = a + b\n"
          "    return c\n",
          "Returns a + b rather than 180 - a - b."),
    366: ("def adjacent_num_product(list_nums):\n"
          "    pairs = list(zip(list_nums, list_nums[1:])) + [(list_nums[-1], list_nums[0])]\n"
          "    return max(a * b for a, b in pairs)\n",
          "Also compares the last and first positions as a circular pair, although the list is not circular."),
    302: ("def set_Bit_Number(n):\n"
          "    if n == 0:\n"
          "        return 0\n"
          "    msb = 0\n"
          "    n = n // 2\n"
          "    while n > 0:\n"
          "        n = n // 2\n"
          "        msb += 1\n"
          "    return msb\n",
          "Returns the highest set bit's POSITION rather than its value."),
}

NONE_CONTROL_FAULT = ("Correctly interfaced but always returns None. Every declared primary expected output for "
                      "this root is numerical, so None can equal no expected value and the control must fail "
                      "every private assertion.")

# Declared HAND TRACES of each control's return value, aligned with the ordered private assertions
# (retained source indices 1 and 2, then the lead's added_private_assertions in spec order). These are
# predictions written by static reasoning; NOTHING here was executed. Literals only.
PREDICTED_SEMANTIC = {
    911: ("414375", "2520", "6"),
    667: ("2", "2", "3", "3", "1"),
    344: ("6", "1", "0", "0"),
    524: ("22", "10", "4"),
    814: ("25", "4", "7", "0"),
    187: ("1", "1", "1", "0"),
    194: ("30", "40", "0", "107"),
    356: ("140", "90", "179"),
    366: ("20", "6", "72"),
    302: ("3", "4", "0", "4"),
}
SEMANTIC_TRACE = {
    911: "nlargest(3) products: [25,35,22,85,14,65,75,25,58] -> 85*75*65 = 414375 (matches); "
         "[18,14,10,...] -> 18*14*10 = 2520 (matches); [-10,-10,1,2,3] -> 3*2*1 = 6, expected 300 (fails).",
    667: "Fixed set AaEeIiOoUu: 'valid' -> 2 (matches); 'true' -> 2 (matches); 'aAbE' -> a,A,E = 3, expected 2 "
         "(fails); 'aaa' -> 3 (matches); 'A' -> 1, expected 0 (fails).",
    344: "isqrt(m-1)-isqrt(n-1): (8,65) -> 8-2 = 6 (matches, 65 is not square); (2,5) -> 2-1 = 1 (matches); "
         "(1,1) -> 0-0 = 0, expected 1 (fails); (9,9) -> isqrt(8)-isqrt(8) = 0, expected 1 (fails).",
    524: "Nondecreasing: [3,4,5,10] -> 22 (matches); [10,5,4,3] -> 10 (matches); [2,2] -> msis[1] = 2+2 = 4, "
         "expected 2 (fails).",
    814: "Floor division: (10,5) -> 25 (matches); (4,2) -> 4 (matches); (3,5) -> 15//2 = 7, expected 7.5 (fails); "
         "(0,5) -> 0 (matches).",
    187: "Longest common contiguous substring: ('ABCDGH','AEDFHR') -> 1, expected 3 (fails); ('AXYT','AYZX') -> 1, "
         "expected 2 (fails); ('abc','ac') -> 1, expected 2 (fails); ('','x') -> 0 (matches).",
    194: "Identity on base ten: 30 -> 30, expected 24 (fails); 40 -> 40, expected 32 (fails); 0 -> 0 (matches); "
         "107 -> 107, expected 71 (fails).",
    356: "a+b: (45,95) -> 140, expected 40 (fails); (50,40) -> 90, expected 90 (matches, since 50+40 = 180-90); "
         "(1,178) -> 179, expected 1 (fails).",
    366: "Circular pair added: [1,2,3,4,5] -> max(20, 5*1) = 20 (matches); [2,3] -> max(6, 6) = 6 (matches); "
         "[9,1,1,8] -> max(9,1,8, 8*9=72) = 72, expected 9 (fails).",
    302: "Bit position: 10 -> 3, expected 8 (fails); 18 -> 4, expected 16 (fails); 1 -> 0, expected 1 (fails); "
         "16 -> 4, expected 16 (fails).",
}

# ------------------------------------------------------------------ declared public domains (machine-checked)
# Each predicate receives the tuple of literal call arguments from one assertion and returns True only when
# every argument lies inside the lead's public_contract domain for that root. Literals are read with
# ast.literal_eval, which evaluates literal nodes only and runs no program.
_INT = (int,)


def _ints(seq, lo, hi):
    return all(type(x) is int and lo <= x <= hi for x in seq)


def _ascii(s, maxlen):
    return isinstance(s, str) and len(s) <= maxlen and all(ord(c) < 128 for c in s)


DOMAINS = {
    911: ("len(nums) in [3,100]; every element an int in [-1000000, 1000000]",
          lambda a: len(a) == 1 and isinstance(a[0], list) and 3 <= len(a[0]) <= 100
          and _ints(a[0], -1000000, 1000000)),
    667: ("len(string) <= 100 ASCII; len(vowels) <= 52 ASCII",
          lambda a: len(a) == 2 and _ascii(a[0], 100) and _ascii(a[1], 52)),
    344: ("1 <= n <= m <= 1000000, both int",
          lambda a: len(a) == 2 and _ints(a, 1, 1000000) and a[0] <= a[1]),
    524: ("len(arr) in [1,100]; every element a positive int <= 1000000; n == len(arr)",
          lambda a: len(a) == 2 and isinstance(a[0], list) and 1 <= len(a[0]) <= 100
          and _ints(a[0], 1, 1000000) and type(a[1]) is int and a[1] == len(a[0])),
    814: ("p and q int in [0, 1000000]",
          lambda a: len(a) == 2 and _ints(a, 0, 1000000)),
    187: ("X and Y ASCII strings of length <= 12; m == len(X); n == len(Y)",
          lambda a: len(a) == 4 and _ascii(a[0], 12) and _ascii(a[1], 12)
          and type(a[2]) is int and a[2] == len(a[0]) and type(a[3]) is int and a[3] == len(a[1])),
    194: ("n a nonnegative int of at most 8 decimal digits, every digit in 0..7",
          lambda a: len(a) == 1 and type(a[0]) is int and 0 <= a[0] and len(str(a[0])) <= 8
          and all(c in "01234567" for c in str(a[0]))),
    356: ("a and b positive ints in degrees with a + b < 180",
          lambda a: len(a) == 2 and _ints(a, 1, 179) and a[0] + a[1] < 180),
    366: ("len(list_nums) in [2,100]; every element an int in [-1000000, 1000000]",
          lambda a: len(a) == 1 and isinstance(a[0], list) and 2 <= len(a[0]) <= 100
          and _ints(a[0], -1000000, 1000000)),
    302: ("n an int with 1 <= n <= 2147483647",
          lambda a: len(a) == 1 and _ints(a, 1, 2147483647)),
}

CHANGE_NOTES = """# E14 release change notes (immutable)

Package: `{manifest_id}`  ·  builder `scripts/build_e14_release.py`
Lead specification: `{spec_rel}` (sha256 `{spec_sha}`)
Source file: `{source_rel}` (sha256 `{source_sha}`, verified before reading)

## 1. This is a NEW endpoint version, not a rescoring of E12/E13

The private suite of every root gains assertions. A score produced against this suite is therefore NOT
comparable to an E12 or E13 number and is not a re-grading of any historical output. The E11/E12/E13 negative
results stand unchanged, and no historical package is touched: `dev_release_v2*`, `dev_release_v3`,
`e13a_release` and everything under `results/` are read-only inputs here.

The frozen scorer is unchanged (`{grader_version}`). `{terminal_label}` is a COMMON INTERVENTION INSTRUCTION
shared byte-identically by both arms. It is NOT an added primary-score rule, NOT a format-compliance gate and
NOT a validated semantic-compliance classifier.

## 2. What changed, per the lead's ten binding decisions

Each root retains its original private assertions at source indices {retained} and adds every private assertion
the lead listed. Public prose is the lead's `public_contract`, which states the input domain explicitly and, for
911, drops the original "using heap queue algorithm" algorithm requirement. Reference implementations are
VERSIONED where the lead required it (344 exact integer square roots via `math.isqrt`; 187 iterative length
dynamic programming with a zero boundary row and column, replacing exponential recursion so reference runtime is
not part of the task; 194 integer division `temp // 10`; 302 integer division `n // 2` returning the bit VALUE)
and preserved otherwise. Every root gains two negative controls: the lead's specified semantic fault and a
correctly interfaced always-None control.

Roster order is exactly {roster}. It is unchanged from the lead's `candidate_roster_order`.

## 3. The ten held ids stay held

{held} remain held and untouched. No new source roster was drawn, no reserve record was semantically inspected,
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
"""


def _dump(obj):
    return json.dumps(obj, indent=1) + "\n"


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_spec(spec_path):
    spec_path = Path(spec_path)
    spec = _read_json(spec_path)
    if spec.get("schema_version") != "e14-lead-measurement-spec-v1":
        raise ValueError(f"unexpected lead spec schema_version {spec.get('schema_version')!r}")
    if tuple(spec["candidate_roster_order"]) != ROSTER:
        raise ValueError(f"lead roster {spec['candidate_roster_order']} is not the builder roster {list(ROSTER)}")
    if tuple(spec["held_ids_unchanged"]) != HELD_IDS:
        raise ValueError("lead held_ids_unchanged does not match the carried-forward holds")
    if spec.get("execution_authorized") is not False:
        raise ValueError("lead spec must declare execution_authorized false")
    records = {r["task_id"]: r for r in spec["records"]}
    if tuple(sorted(records)) != tuple(sorted(ROSTER)) or len(spec["records"]) != N_ROOTS:
        raise ValueError("lead spec records do not cover exactly the ten roster roots")
    for tid, rec in records.items():
        if tuple(rec["public_assertion_indices"]) != PUBLIC_ASSERTION_INDICES:
            raise ValueError(f"{tid}: public_assertion_indices is not {list(PUBLIC_ASSERTION_INDICES)}")
        if tuple(rec["retained_private_assertion_indices"]) != RETAINED_PRIVATE_INDICES:
            raise ValueError(f"{tid}: retained_private_assertion_indices is not {list(RETAINED_PRIVATE_INDICES)}")
    return spec, records, file_sha(spec_path)


def _load_source(source_path, expected_sha):
    source_path = Path(source_path)
    actual = file_sha(source_path)
    if actual != expected_sha:
        raise ValueError(f"source file sha256 mismatch for {source_path}: {actual} != {expected_sha}")
    rows = {}
    for raw in source_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        rec = json.loads(raw)
        tid = rec.get("task_id")
        if tid in ROSTER:
            if tid in rows:
                raise ValueError(f"duplicate source row for task_id {tid}")
            rows[tid] = rec
    missing = [t for t in ROSTER if t not in rows]
    if missing:
        raise ValueError(f"source file does not carry roster tasks {missing}")
    return rows, actual


def _verify_record_hashes(tid, row, rec):
    """The lead's three per-record source pins, recomputed from the verified source bytes."""
    got = {"source_text_sha256": _sha_text(row["text"]),
           "source_reference_sha256": _sha_text(row["code"]),
           # derivation: sha256 of json.dumps(test_list) with default separators
           "source_assertions_sha256": _sha_text(json.dumps(row["test_list"]))}
    for key, value in got.items():
        if rec[key] != value:
            raise ValueError(f"{tid}: {key} mismatch: recomputed {value} != lead {rec[key]}")
    return got


def _entry_point_and_signature(tid, code):
    tree = ast.parse(code)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(fns) != 1:
        raise ValueError(f"{tid}: original source does not define exactly one top-level function")
    fn = fns[0]
    if not fn.name.isidentifier():
        raise ValueError(f"{tid}: entry point {fn.name!r} is not an identifier")
    return fn.name, f"def {fn.name}({ast.unparse(fn.args)}):"


def _assertion_parts(tid, assertion, entry_point):
    """(rendered_call_eq_expected, args_literal, expected_literal, literal_args) for one standalone assert."""
    tree = ast.parse(assertion)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assert):
        raise ValueError(f"{tid}: not a single standalone assert: {assertion!r}")
    test = tree.body[0].test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        raise ValueError(f"{tid}: assertion is not a single top-level == comparison: {assertion!r}")
    call = test.left
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != entry_point:
        raise ValueError(f"{tid}: assertion does not call the declared entry point {entry_point}: {assertion!r}")
    if call.keywords:
        raise ValueError(f"{tid}: keyword arguments are outside the declared interface: {assertion!r}")
    try:
        literal_args = tuple(ast.literal_eval(a) for a in call.args)
        expected_value = ast.literal_eval(test.comparators[0])
    except ValueError as exc:
        raise ValueError(f"{tid}: assertion arguments/expected value are not literals: {assertion!r}") from exc
    return (ast.unparse(test), "[" + ", ".join(ast.unparse(a) for a in call.args) + "]",
            ast.unparse(test.comparators[0]), literal_args, expected_value)


def _bind_domain(tid, assertion, kind, entry_point):
    rule, predicate = DOMAINS[tid]
    rendered, args_literal, expected_literal, literal_args, expected_value = _assertion_parts(
        tid, assertion, entry_point)
    if not predicate(literal_args):
        raise ValueError(f"{tid}: assertion arguments fall OUTSIDE the declared public domain "
                         f"({rule}): {assertion!r}")
    return {"assertion": assertion, "kind": kind, "entry_point": entry_point, "args_literal": args_literal,
            "expected_literal": expected_literal, "domain_rule": rule, "in_declared_public_domain": True}, \
        rendered, expected_literal, expected_value


def _static_check(tid, label, code, entry_point):
    """Static validity only: ast.parse + compile + integrity.hack_gate. The program is NEVER run."""
    tree = ast.parse(code)  # raises SyntaxError on invalid source
    compile(code, f"<e14:{tid}:{label}>", "exec", dont_inherit=True)  # compile only; no exec()
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    if entry_point not in names:
        raise ValueError(f"{tid}: {label} does not define the declared entry point {entry_point} at module level")
    hits = hack_gate(code, entry_point)
    if hits:
        raise ValueError(f"{tid}: {label} fails integrity.hack_gate: {hits}")
    return {"sha256": _sha_text(code), "ast_parsed": True, "compiled": True, "hack_gate_hits": [],
            "hack_gate_clean": True, "executed": False}


def _none_control(signature):
    header = signature[:-1] if signature.endswith(":") else signature
    return f"{header}:\n    return None\n"


def _assert_public_carries_no_private(public_blobs, private_strings):
    """No private assertion, reference or control text may appear in any public byte stream."""
    joined = {name: re.sub(r"\s+", "", blob) for name, blob in public_blobs.items()}
    for text in private_strings:
        needle = re.sub(r"\s+", "", text)
        if not needle:
            continue
        for name, blob in joined.items():
            if needle in blob:
                raise ValueError(f"private text leaked into public file {name}: {text[:90]!r}")


def _verify_law_release(law_dir):
    law_dir = Path(law_dir)
    manifest = _read_json(law_dir / "release_manifest.json")
    pkg = manifest.get("package")
    if not isinstance(pkg, dict):
        raise ValueError("dev_release_v3 manifest has no package hashes")
    for name in LAW_PACKAGE_FILES:
        if name not in pkg:
            raise ValueError(f"dev_release_v3 manifest does not pin {name}")
        actual = file_sha(law_dir / name)
        if actual != pkg[name]:
            raise ValueError(f"frozen receiver-law source changed on disk: {name} ({actual} != {pkg[name]})")
    return manifest


def build(out_dir, spec_path=None, source_path=None, law_dir=None, version="v2"):
    """Write the ten-root E14 package into out_dir (which must not exist). Returns the manifest dict."""
    out_dir = Path(out_dir)
    spec_path = Path(spec_path or ROOT / DEFAULT_SPEC)
    law_dir = Path(law_dir or ROOT / DEFAULT_LAW_RELEASE)
    if out_dir.exists():
        raise SystemExit(f"refusing to overwrite existing output: {out_dir}")

    spec, records, spec_sha = _load_spec(spec_path)
    if source_path is None:
        candidates = [ROOT / DEFAULT_SOURCE_FILE, ROOT / ALT_SOURCE_FILE]
        source_path = next((p for p in candidates if p.is_file()), None)
        if source_path is None:
            raise SystemExit(f"cached MBPP source not found at any of {[str(p) for p in candidates]}")
    rows, source_sha = _load_source(source_path, spec["source_file_sha256"])
    if version != "v2":
        raise SystemExit(f"unknown package version {version!r}")
    v2 = version == "v2"
    source_label = SOURCE_IDENTITY_V2 if v2 else str(Path(source_path).relative_to(ROOT))
    law_manifest = _verify_law_release(law_dir)

    tasks, cases, specs, controls, bindings, per_root = [], [], [], [], {}, {}
    private_strings = []
    for tid in ROSTER:
        row, rec = rows[tid], records[tid]
        root_id = rec["root_id"]
        if root_id != f"mbpp/{tid}":
            raise ValueError(f"{tid}: lead root_id {root_id!r} does not match the source task id")
        source_pins = _verify_record_hashes(tid, row, rec)
        entry_point, signature = _entry_point_and_signature(tid, row["code"])
        test_list = row["test_list"]
        if len(test_list) < max(RETAINED_PRIVATE_INDICES) + 1:
            raise ValueError(f"{tid}: source has too few assertions for the declared indices")

        public_assertions = [test_list[i] for i in PUBLIC_ASSERTION_INDICES]
        retained = [test_list[i] for i in RETAINED_PRIVATE_INDICES]
        added = list(rec["added_private_assertions"])
        if added != records[tid]["added_private_assertions"]:
            raise ValueError(f"{tid}: added assertions diverge from the lead JSON")
        private_assertions = retained + added

        # ---- bind every original and added assertion to the declared public domain
        root_bindings, public_rendered, expected_literals, expected_values = [], [], [], []
        for a in public_assertions:
            b, rendered, _lit, _val = _bind_domain(tid, a, "public_source_index_0", entry_point)
            root_bindings.append(b)
            public_rendered.append(rendered)
        for idx, a in zip(RETAINED_PRIVATE_INDICES, retained):
            b, _r, lit, val = _bind_domain(tid, a, f"private_retained_source_index_{idx}", entry_point)
            root_bindings.append(b)
            expected_literals.append(lit)
            expected_values.append(val)
        for a in added:
            b, _r, lit, val = _bind_domain(tid, a, "private_added_by_lead", entry_point)
            root_bindings.append(b)
            expected_literals.append(lit)
            expected_values.append(val)
        bindings[root_id] = root_bindings

        # ---- public files: contract prose + interface metadata + rendered assertion index 0 ONLY
        public_context = (f"Required function interface: {signature}\n\n"
                          "Public example (input and required output):\n" + "\n".join(public_rendered))
        tasks.append({"root_id": root_id, "prompt": rec["public_contract"], "public_context": public_context})
        cases.append({"root_id": root_id, "entry_point": entry_point,
                      "cases": [{"case_id": f"public-{tid}-{n + 1}",
                                 "args_literal": root_bindings[n]["args_literal"],
                                 "expected_literal": root_bindings[n]["expected_literal"]}
                                for n in range(len(public_assertions))]})

        # ---- scorer-only: versioned reference + two negative controls, statically validated
        reference = REFERENCES[tid]
        semantic_code, semantic_fault = SEMANTIC_CONTROLS[tid]
        none_code = _none_control(signature)
        static = {"reference": _static_check(tid, "reference", reference, entry_point),
                  "semantic_control": _static_check(tid, "semantic_control", semantic_code, entry_point),
                  "none_control": _static_check(tid, "none_control", none_code, entry_point)}

        predicted = PREDICTED_SEMANTIC[tid]
        if len(predicted) != len(private_assertions):
            raise ValueError(f"{tid}: {len(predicted)} predicted returns for {len(private_assertions)} "
                             "private assertions")
        control_records = []
        for label, code, fault, preds, trace in (
                ("semantic", semantic_code, semantic_fault, predicted, SEMANTIC_TRACE[tid]),
                ("always_none", none_code, NONE_CONTROL_FAULT, ("None",) * len(private_assertions),
                 "Returns None for every input; every declared expected output is numerical.")):
            private_cases, n_fail = [], 0
            for a, lit, val, pred in zip(private_assertions, expected_literals, expected_values, preds):
                predicted_value = ast.literal_eval(pred)  # literal only; the control is never run
                fails = predicted_value != val
                n_fail += int(fails)
                private_cases.append({"assertion": a, "expected": lit, "predicted_control_return": pred,
                                      "predicted_fails": fails})
            if n_fail < 1:
                raise ValueError(f"{tid}: {label} control is predicted to fail no declared private assertion")
            control_records.append({
                "root_id": root_id, "control": label, "entry_point": entry_point,
                "fault": fault,
                "requirement": rec["semantic_negative_control_requirement"] if label == "semantic"
                else rec["second_negative_control_requirement"],
                "expected_failure_reasoning": trace,
                "method": ("hand trace of the control's logic on the declared private inputs; the control text "
                           "was statically parsed, compiled and hack_gate-checked but NEVER executed"),
                "static_trace": trace,
                "predicted_failing_private_assertions": n_fail,
                "private_cases": private_cases,
                "code_sha256": static["semantic_control" if label == "semantic" else "none_control"]["sha256"],
            })
        controls.extend(control_records)

        spec_row = {
            "root_id": root_id, "entry_point": entry_point, "public_task_sha256": digest(tasks[-1]),
            "public_assertions": public_assertions, "private_assertions": private_assertions,
            "preamble": [], "reference_code": reference,
            "negative_controls": [
                {"code": semantic_code,
                 "rationale": f"{semantic_fault} Predicted to fail "
                              f"{control_records[0]['predicted_failing_private_assertions']} of "
                              f"{len(private_assertions)} declared private assertions by hand trace; never run."},
                {"code": none_code,
                 "rationale": f"{NONE_CONTROL_FAULT} Predicted to fail all {len(private_assertions)} declared "
                              "private assertions by hand trace; never run."},
            ],
        }
        specs.append(spec_row)
        private_strings.extend(private_assertions + [reference, semantic_code, none_code])

        per_root[root_id] = {
            "task_id": tid, "entry_point": entry_point, "signature": signature,
            "source_pins": source_pins,
            "reference_version_requirement": rec["reference_version_requirement"],
            "reference_version_note": REFERENCE_VERSION_NOTE[tid],
            "public_assertion_indices": list(PUBLIC_ASSERTION_INDICES),
            "retained_private_assertion_indices": list(RETAINED_PRIVATE_INDICES),
            "n_added_private_assertions": len(added),
            "n_private_assertions": len(private_assertions),
            "declared_public_domain": DOMAINS[tid][0],
            "assertion_domain_bindings": root_bindings,
            "static_validation": static,
            "tasks_row_sha256": digest(tasks[-1]),
            "private_spec_row_sha256": digest(spec_row),
            "call_slots": 1 + N_ARMS * DRAWS_PER_ARM,
        }

    from experiments.landmark import grade  # lazy import: source/static use only, nothing is executed
    grade.validate_specs(tasks, specs)

    public_examples = {"version": "public-examples-v3", "cases": cases}
    controls_rationale = {"version": "e14-release-controls", "controls": controls,
                          "execution_note": ("No control was executed. Every predicted_control_return is a hand "
                                             "trace declared in scripts/build_e14_release.py.")}
    _assert_public_carries_no_private(
        {"tasks.jsonl": "\n".join(json.dumps(t, sort_keys=True, ensure_ascii=False) for t in tasks),
         "public_examples_v3.json": _dump(public_examples)},
        private_strings)

    contract = grade.contract(specs)
    config = _read_json(law_dir / "config.json")
    config.update(dataset_sha256=digest(tasks), source_code_sha256=digest(source_hashes()),
                  grading_contract_sha256=digest(contract), max_calls=CALL_SLOTS,
                  max_completion_tokens=PLANNING_INVENTORY["reserved_completion_tokens"],
                  max_seconds=PHASE_LIMITS_V2["collection"] if v2 else 1560)
    if v2:
        for k in LEGACY_FIELDS_REMOVED_V2:
            config.pop(k, None)
    config["e14"] = {
        "manifest": MANIFEST_ID, "roster_order": list(ROSTER), "n_roots": N_ROOTS,
        "initial_slots": INITIAL_SLOTS, "arms": ["NEUTRAL", "DIRECTED"], "draws_per_arm": DRAWS_PER_ARM,
        "continuation_slots": CONTINUATION_SLOTS, "call_slots": CALL_SLOTS,
        "arm_instructions": {"NEUTRAL": "diagnostic.N_INSTRUCTION",
                             "DIRECTED": "diagnostic.select_s1(diag), a deterministic function of PUBLIC "
                                         "diagnostic statuses only"},
        "shared_prefix": ("byte-identical across arms: public task prompt, the model's own retained previous "
                          "answer, one shared public-diagnostic message"),
        "terminal_instruction_label": spec["terminal_instruction"]["label"],
        "branch_inclusion_probability": 1,
        "order_role": "balanced order is scheduling only, not a treatment propensity",
        "grader_version": grade.GRADER_VERSION,
        "diagnostic_schema": DIAGNOSTIC_SCHEMA,
        "receiver_calls_authorized": 0, "candidate_executions_authorized": 0,
    }
    if v2:
        config["e14"]["manifest"] = MANIFEST_ID + "-v2"
        config["e14"]["package_version"] = "v2"
        config["e14"]["legacy_fields_removed"] = list(LEGACY_FIELDS_REMOVED_V2)
        config["e14"]["phase_limits_seconds"] = dict(PHASE_LIMITS_V2)
        config["e14"]["phase_limits_status"] = "planning values until an explicit later release; not authority"

    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "tasks.jsonl").write_text(
        "".join(json.dumps(t, sort_keys=True, ensure_ascii=False) + "\n" for t in tasks), encoding="utf-8")
    (out_dir / "public_examples_v3.json").write_text(_dump(public_examples), encoding="utf-8")
    (out_dir / "private_specs.jsonl").write_text(
        "".join(json.dumps(s, sort_keys=True, ensure_ascii=False) + "\n" for s in specs), encoding="utf-8")
    (out_dir / "controls_rationale.json").write_text(_dump(controls_rationale), encoding="utf-8")
    (out_dir / "config.json").write_text(_dump(config), encoding="utf-8")
    (out_dir / "CHANGE_NOTES.md").write_text(CHANGE_NOTES.format(
        manifest_id=MANIFEST_ID, spec_rel=spec_path.relative_to(ROOT), spec_sha=spec_sha,
        source_rel=source_label, source_sha=source_sha,
        grader_version=grade.GRADER_VERSION, terminal_label=spec["terminal_instruction"]["label"],
        retained=" and ".join(str(i) for i in RETAINED_PRIVATE_INDICES),
        roster=", ".join(str(t) for t in ROSTER), held=", ".join(str(t) for t in HELD_IDS))
        + (V2_CHANGE_NOTES if v2 else ""), encoding="utf-8")

    from experiments.landmark import study_adapter as sa  # lazy: source hashes / strict json only
    manifest = {
        "manifest": MANIFEST_ID + ("-v2" if v2 else ""),
        "status": ("PROPOSED BINDINGS for E14. Not a release decision and not an execution authorization; "
                   "MRL-23 item 1 source/static work only."),
        "evidence_class": ("source-bound prospective measurement package: bindings, hand-traced control "
                           "predictions and static validity (ast.parse, compile, integrity.hack_gate). NOT "
                           "executed reference/control validation and NOT new model data."),
        "endpoint": spec["endpoint"],
        "roots": [r["root_id"] for r in specs],
        "n_roots": N_ROOTS,
        "roster_order": list(ROSTER),
        "roster_order_note": ("exactly the lead's candidate_roster_order; no outcome-based reordering and no "
                              "new source roster"),
        "held_ids_unchanged": list(HELD_IDS),
        "public_private_boundary": spec["public_private_boundary"],
        "design": {
            "initial_calls": INITIAL_SLOTS, "arms": ["NEUTRAL", "DIRECTED"], "draws_per_arm": DRAWS_PER_ARM,
            "continuation_slots": CONTINUATION_SLOTS, "call_slots": CALL_SLOTS,
            "slots_fixed_before_collection": True, "branch_inclusion_probability": 1,
            "arm_difference": "only the arm instruction differs; both arms share a byte-identical prefix and the "
                              "same terminal instruction v2",
            "missingness_rules": MISSINGNESS_RULES,
            "reporting_rules": REPORTING_RULES,
        },
        "authorization": {"receiver_calls_authorized": 0, "model_tokens_authorized": 0,
                          "candidate_executions_authorized": 0, "reference_executions_authorized": 0,
                          "negative_control_executions_authorized": 0, "benchmark_executions_authorized": 0,
                          "public_check_executions_authorized": 0, "containment_executions_authorized": 0,
                          "paid_usd_authorized": 0, "statement": AUTHORIZATION_STATEMENT},
        "grading_limits": dict(GRADING_LIMITS),
        "limits_note": ("artifact_starts = the lead's 140 candidate starts (10 initial-public + 10 "
                        "initial-private + 120 continuation-private); recheck_starts = 30 grader-side "
                        "reference/control rechecks (10 + 20); containment_starts = 18 for two nine-check "
                        "epochs; max_private_starts = artifact + recheck + containment. Read with "
                        "study_adapter.load_grading_limits. These are BOOKKEEPING CAPS, not authorization."),
        "planning_inventory": dict(PLANNING_INVENTORY),
        "package": {name: file_sha(out_dir / name) for name in PACKAGE_FILES},
        "lead_specification": {"path": str(spec_path.relative_to(ROOT)), "sha256": spec_sha,
                               "schema_version": spec["schema_version"], "created_utc": spec["created_utc"],
                               "evidence_class": spec["evidence_class"],
                               "execution_authorized": spec["execution_authorized"],
                               "scorer_only_fields": ["added_private_assertions", "reference_version_requirement",
                                                      "semantic_negative_control_requirement",
                                                      "second_negative_control_requirement"],
                               "never_passed_to_a_prompt": True},
        "source_pins": {"path": source_label, "file_sha256": source_sha,
                        "expected_file_sha256": spec["source_file_sha256"], "verified_before_reading": True,
                        "assertions_sha256_derivation": "sha256(json.dumps(test_list)) with default separators",
                        "per_root": {r: per_root[r]["source_pins"] for r in per_root}},
        "terminal_instruction": {**spec["terminal_instruction"],
                                 "applied_to": "both arms, byte-identically appended",
                                 "is_a_scoring_rule": False},
        "model": law_manifest["model"],
        "evaluator": {"grader_version": grade.GRADER_VERSION, "endpoint": contract["version"],
                      "diagnostic_schema": DIAGNOSTIC_SCHEMA,
                      "scorer_change": "none; the frozen scorer is unchanged and applied to the new suite"},
        "diagnostic_schema": DIAGNOSTIC_SCHEMA,
        "grading_bindings": {
            "frozen_tasks_path": f"experiments/landmark/{RELEASE_DIRNAME}/tasks.jsonl",
            "frozen_tasks_sha256": file_sha(out_dir / "tasks.jsonl"),
            "expected_contract_sha256": digest(contract),
            "expected_config_sha256": digest(sa._strict((out_dir / "config.json").read_bytes())),
            "expected_source_hashes": sa.grading_source_hashes(),
        },
        "execution_source_hashes": {name: file_sha(ROOT / name) for name in EXECUTION_SOURCES},
        "receiver_law_source": {
            "dir": str(law_dir.relative_to(ROOT)), "manifest": law_manifest["manifest"],
            "manifest_sha256": file_sha(law_dir / "release_manifest.json"),
            "files": {name: file_sha(law_dir / name) for name in LAW_PACKAGE_FILES},
            "reuse_rule": ("config.json inherits dev_release_v3's frozen receiver request law and rebinds only "
                           "the dataset, grading contract, source hashes and E14 caps. dev_release_v3 is read "
                           "only and was not modified."),
        },
        "per_root": per_root,
        "version_note": ("NEW ENDPOINT VERSION, not a rescoring of E12 or E13. Scores against this suite are not "
                         "comparable to E12/E13 numbers. The E11/E12/E13 negatives stand unchanged."),
        "source_exposure_limitations": [
            "whole-source mechanical processing during frame reproduction (full file loaded, features and "
            "similarity recomputed beyond rank 40)",
            "twenty-record semantic review, with all twenty provisional family labels and sizes already recorded; "
            "the size-nine and size-two groups are lexical-screen groups, not independent sampling units",
            "no reported new model-outcome inspection",
        ],
        "source_exposure_note": "These are three separate facts; none implies another.",
        "not_established": ("Nothing in this package was executed. Static validity and a clean hack_gate are not "
                           "executability, integrity clearance or correctness. The references and controls still "
                           "require later isolated validation."),
        "builder": {"script": "scripts/build_e14_release_v2.py", "script_sha256": file_sha(__file__),
                    "deterministic": True,
                    "rebuild_command": ".venv/bin/python scripts/build_e14_release.py --verify"},
    }
    (out_dir / "release_manifest.json").write_text(_dump(manifest), encoding="utf-8")
    return manifest


def verify(out_dir, **kw):
    """Rebuild into a temporary directory and compare every byte with the committed package."""
    out_dir = Path(out_dir)
    if not out_dir.is_dir():
        raise SystemExit(f"nothing to verify: {out_dir} does not exist")
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / RELEASE_DIRNAME
        build(fresh, **kw)
        names = sorted(p.name for p in fresh.iterdir())
        committed = sorted(p.name for p in out_dir.iterdir())
        if names != committed:
            raise SystemExit(f"rebuild file set differs: rebuilt {names} vs committed {committed}")
        bad = [n for n in names if (fresh / n).read_bytes() != (out_dir / n).read_bytes()]
        if bad:
            raise SystemExit(f"rebuild differs from the committed bytes: {bad}")
    return {"verified": True, "dir": str(out_dir), "files": names}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default=None)
    p.add_argument("--version", choices=("v2",), default="v2")  # v1 lives in build_e14_release.py, unchanged
    p.add_argument("--spec", default=str(ROOT / DEFAULT_SPEC))
    p.add_argument("--source", default=None, help="cached MBPP jsonl; default resolves the two known paths")
    p.add_argument("--law-release", default=str(ROOT / DEFAULT_LAW_RELEASE))
    p.add_argument("--verify", action="store_true", help="rebuild into a temp dir and diff the committed bytes")
    a = p.parse_args(argv)
    if a.out is None:
        a.out = str(ROOT / (DEFAULT_OUT_V2 if a.version == "v2" else DEFAULT_OUT))
    kw = dict(spec_path=a.spec, source_path=a.source, law_dir=a.law_release, version=a.version)
    if a.verify:
        result = verify(a.out, **kw)
    else:
        m = build(a.out, **kw)
        result = {"built": str(a.out), "roots": m["roots"], "call_slots": m["design"]["call_slots"],
                  "receiver_calls_authorized": m["authorization"]["receiver_calls_authorized"]}
    print(json.dumps(result, indent=1))
    return result


if __name__ == "__main__":
    main()
