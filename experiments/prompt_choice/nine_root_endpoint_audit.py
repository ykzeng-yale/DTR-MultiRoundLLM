"""Nine-root measurement package builder: MRL-37 source-only preparation for LEAD-ENDPOINT-07
(prompt-choice-nine-root-measurement-v1; docs/policy_nine_root_measurement_contract_20260926.md).

Builds deterministic public records (adapted public wording, original signature and entry point, public case from original
assertion 0) and separate private records (original_private = original assertions 1-2, supplement_v1 = the lead's 46
literal cases, reference, and five controls per root) for MBPP 356, 885, 354, 901, 654, 703, 700, 656, 36 in that order.
This is a measurement-development panel, not an evaluation roster or certified independent families.

Pure and source-only: standard library plus the accepted MRL-33 helpers (hash conventions, strict JSON). No exec, eval,
compile, dynamic import, subprocess, network, sandbox or runner path; code and assertions are parsed with ast only and
literal values come from ast.literal_eval on single literal nodes. Raw third-party source and the generated private
package stay in the gitignored work/ directory.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

from experiments.prompt_choice.endpoint_audit import (AuditSourceError, _no_duplicate_keys, canonical_sha256,
                                                      normalized_ast_sha256, raw_sha256)

VERSION = "prompt-choice-nine-root-measurement-v1"
DECISION = "LEAD-ENDPOINT-07"
HERE = Path(__file__).resolve().parent
WORK_ROOT = HERE.parents[1] / "work"
CONFIG_PATH = HERE / "nine_root_endpoint_source_v1.json"
SOURCE_SHA256 = "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"
ROOTS = (356, 885, 354, 901, 654, 703, 700, 656, 36)
RECORD_KEYS = frozenset({"text", "code", "task_id", "test_setup_code", "test_list", "challenge_test_list"})
PUBLIC_CASE_ID = "public-0"

ADAPTED_PUBLIC = {  # exact lead-authored adapted public wording (contract table)
    356: "Given two positive interior angles of a triangle in degrees whose sum is below 180, return the third interior angle in degrees. Units and valid domain are explicit.",
    885: "Return whether two strings have equal length and the same equality pattern of characters: a bijective character renaming converts one to the other. The empty strings match.",
    354: "Given first term a, positive one-based index n and common difference d, return the nth arithmetic-progression term. For this adapted contract a, d are integers; zero and negative differences are permitted.",
    901: "For a positive integer n, return the least positive integer divisible by every integer from 1 through n. No arbitrary large-n correctness or runtime guarantee follows from the finite cases.",
    654: "Given nonnegative integer length and width, return the rectangle perimeter; degenerate zero dimensions are permitted in this adapted arithmetic contract. This domain is explicit and is not a claim that every geometric interpretation permits degeneracy.",
    703: "Return whether the supplied hashable key is present in the dictionary; do not test membership among values.",
    700: "Count entries in the inclusive interval between the supplied bounds, including repeated entries. The list entries and bounds are all integers or all strings, with ordinary Python ordering; an empty list or reversed bounds yields zero.",
    656: "For two equal-length integer arrays and their length n, return the minimum sum of absolute differences over bijective pairings. Empty arrays return zero. Only the returned value is scored; no promise of preserving caller inputs is added.",
    36: "For integers 0 <= p < q with q>0 and positive one-based N, return the Nth decimal digit after the point in p/q. Terminating fractions have trailing zeros.",
}

SUPPLEMENT_V1 = {  # lead-authored literal (arguments, expected); never computed by running a reference
    356: (((60, 60), 60), ((1, 1), 178), ((89, 90), 1), ((30, 120), 30)),
    885: ((("", ""), True), (("a", ""), False), (("foo", "bar"), False), (("egg", "add"), True), (("abca", "zbxz"), True),
          (("abc", "xyy"), False), (("aab", "abb"), False)),  # 7th case added by the lead's correction c3a4c29
    354: (((3, 1, 7), 3), ((5, 4, 0), 5), ((10, 4, -3), 1), ((-2, 3, 4), 6)),
    901: (((3,), 6), ((4,), 12), ((5,), 60), ((7,), 420), ((8,), 840)),
    654: (((0, 7), 14), ((3, 3), 12), ((2, 9), 22), ((1, 0), 2)),
    703: ((({}, 1), False), (({"a": 1}, "a"), True), (({"a": 1}, 1), False), (({0: False}, 0), True), (({1: "x"}, 2), False)),
    700: ((([0, 1, 2, 2, 3], 1, 2), 3), ((["aa", "b", "c", "za"], "b", "z"), 2), (([], 0, 1), 0), (([2, 2, 2], 2, 2), 3),
          (([1, 2, 3], 3, 1), 0)),
    656: ((([1, 4], [2, 8], 2), 5), (([-3, 1], [2, -2], 2), 2), (([], [], 0), 0), (([5, 5, 1], [5, 1, 1], 3), 4),
          (([1, 10], [10, 1], 2), 0), (([0, 10], [4, 6], 2), 8)),
    36: (((1, 8, 1), 1), ((1, 8, 2), 2), ((1, 8, 3), 5), ((1, 8, 4), 0), ((2, 7, 3), 5), ((0, 3, 2), 0)),
}

WRONG_RULES = {  # (kind, body using the original parameter names) x3 per root, contract order
    356: (("sum_a_plus_b", "return a + b"), ("three_sixty_minus", "return 360 - a - b"),
          ("one_eighty_minus_abs_diff", "return 180 - abs(a - b)")),
    885: (("equal_lengths_only", "return len(str1) == len(str2)"),
          ("equal_distinct_character_counts_only", "return len(set(str1)) == len(set(str2))"),
          ("many_to_one_map_with_equal_lengths",
           "if len(str1) != len(str2):\n        return False\n    mapping = {}\n    for x, y in zip(str1, str2):\n"
           "        if mapping.setdefault(x, y) != y:\n            return False\n    return True")),
    354: (("a_plus_n_times_d", "return a + n * d"), ("a_plus_n_minus_one", "return a + (n - 1)"),
          ("a_times_n_times_d", "return a * n * d")),
    901: (("return_n", "return n"), ("n_times_n_minus_one", "return n * (n - 1)"), ("return_zero", "return 0")),
    654: (("area", "return l * b"), ("half_perimeter", "return l + b"), ("four_times_length", "return 4 * l")),
    703: (("membership_among_values", "return x in d.values()"), ("dictionary_nonempty", "return len(d) > 0"),
          ("always_false", "return False")),  # corrected by the lead (c3a4c29): Always False
    700: (("strict_bounds", "return sum(1 for x in li if min < x < max)"),
          ("distinct_qualifying_entries", "return len({x for x in li if min <= x <= max})"),
          ("input_length", "return len(li)")),
    656: (("zipped_order_abs_differences", "return sum(abs(x - y) for x, y in zip(a, b))"),
          ("abs_difference_of_sums", "return abs(sum(a) - sum(b))"), ("sum_of_both_arrays", "return sum(a) + sum(b)")),
    36: (("first_digit_regardless_of_n", "return (p * 10 // q) % 10"),
         ("digit_n_plus_one", "return (p * 10 ** (N + 1) // q) % 10"),
         ("integer_quotient_without_last_digit", "return p * 10 ** N // q")),
}
CONTROL_KINDS = ("wrong_rule_1", "wrong_rule_2", "wrong_rule_3", "constant_public_expected", "lookup_original_examples")

# Source-reasoned per-battery predictions (no program was run): True = predicted pass, False = predicted fail.
PREDICTIONS = {  # root -> {artifact: (original_private, supplement_v1)}
    356: {"reference": (True, True), "wrong_rule_1": (False, False), "wrong_rule_2": (False, False),
          "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
    885: {"reference": (True, True), "wrong_rule_1": (False, False), "wrong_rule_2": (True, False),
          "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
    354: {"reference": (True, True), "wrong_rule_1": (False, False), "wrong_rule_2": (False, False),
          "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
    901: {"reference": (True, True), "wrong_rule_1": (True, False), "wrong_rule_2": (False, False),
          "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
    654: {"reference": (True, True), "wrong_rule_1": (False, False), "wrong_rule_2": (False, False),
          "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
    703: {"reference": (True, True), "wrong_rule_1": (False, False), "wrong_rule_2": (False, False),
          "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
    700: {"reference": (True, True), "wrong_rule_1": (False, False), "wrong_rule_2": (True, False),
          "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
    656: {"reference": (True, True), "wrong_rule_1": (False, False), "wrong_rule_2": (False, False),
          "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
    36: {"reference": (True, True), "wrong_rule_1": (False, False), "wrong_rule_2": (False, False),
         "wrong_rule_3": (False, False), "constant_public_expected": (False, False), "lookup_original_examples": (True, False)},
}
PREDICTION_FINDINGS = [
    "Worker source reading before the lead's correction c3a4c29 independently found that 885 wrong_rule_2 passed all six "
    "original supplement cases; the lead's seventh case ('aab','abb') -> False (distinct counts 2 = 2) now rejects it.",
    "885 wrong_rule_2 is predicted to pass original_private (('ab','ba') 2=2 True; ('ab','aa') 2 vs 1 False), beyond the "
    "901/700 original-private weaknesses named in the contract; it fails supplement case 7.",
    "901 wrong_rule_1 (return n) and 700 wrong_rule_2 (distinct count) pass original_private, as the contract states; both "
    "are predicted to fail supplement_v1 ((3,)->3 vs 6; [0,1,2,2,3] distinct 2 vs 3).",
    "Before the correction, 703 constant_public_expected (return True) duplicated wrong_rule_3 (always True); with the "
    "lead's Always False rule the 45 control codes are now pairwise distinct.",
    "Every original case is consistent with its adapted public contract by source reading (no additional contradiction).",
]


def _literal(node, what):
    try:
        return ast.literal_eval(node)  # a single literal node only
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as e:
        raise AuditSourceError(f"{what} is not a literal: {type(e).__name__}") from None


def parse_assertion(text: str, entry_point: str, arity: int) -> dict:
    """`assert <entry_point>(<literal args>) == <literal>`, parsed as text; never run."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        raise AuditSourceError(f"assertion does not parse: {type(e).__name__}") from None
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assert) or tree.body[0].msg is not None:
        raise AuditSourceError("each assertion must be one standalone assert without a message")
    t = tree.body[0].test
    if not (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq) and isinstance(t.left, ast.Call)
            and isinstance(t.left.func, ast.Name) and t.left.func.id == entry_point and not t.left.keywords
            and len(t.left.args) == arity and not any(isinstance(a, ast.Starred) for a in t.left.args)):
        raise AuditSourceError(f"assertion must be `assert {entry_point}(<{arity} literals>) == <literal>`")
    args = tuple(_literal(a, "argument") for a in t.left.args)
    expected = _literal(t.comparators[0], "expected value")
    return {"args": args, "expected": expected, "args_literal": repr(list(args)), "expected_literal": repr(expected)}


def _signature(code: str):
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        raise AuditSourceError(f"reference does not parse: {type(e).__name__}") from None
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(defs) != 1 or len(tree.body) != 1:
        raise AuditSourceError("reference must be exactly one top-level function definition")
    a = defs[0].args
    if a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs or a.defaults:
        raise AuditSourceError("reference signature must be plain positional parameters")
    params = [p.arg for p in a.args]
    return defs[0].name, params


def load_source(source_path, source_sha256=SOURCE_SHA256, roots=ROOTS) -> dict:
    try:
        data = Path(source_path).read_bytes()
    except OSError as e:
        raise AuditSourceError(f"source unavailable: {type(e).__name__}") from None
    if hashlib.sha256(data).hexdigest() != source_sha256:
        raise AuditSourceError("source SHA256 does not match the pin")
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise AuditSourceError("source is not UTF-8") from None
    seen, found = set(), {}
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line, object_pairs_hook=_no_duplicate_keys)
        except ValueError as e:
            raise AuditSourceError(f"line {n} is not a JSON record: {type(e).__name__}") from None
        tid = rec.get("task_id") if isinstance(rec, dict) else None
        if type(tid) is not int:
            raise AuditSourceError(f"line {n} lacks an integer task_id")
        if tid in seen:
            raise AuditSourceError(f"duplicate task_id {tid}")
        seen.add(tid)
        if tid in roots:
            found[tid] = rec
    missing = [r for r in roots if r not in found]
    if missing:
        raise AuditSourceError(f"missing task_id(s) {missing}")
    return found


def _control_code(entry, params, body):
    return f"def {entry}({', '.join(params)}):\n    {body}\n"


def _lookup_code(entry, params, originals):
    table = tuple((o["args"], o["expected"]) for o in originals)
    return (f"def {entry}({', '.join(params)}):\n    examples = {table!r}\n    for arguments, expected in examples:\n"
            f"        if arguments == ({', '.join(params)}{',' if len(params) == 1 else ''}):\n            return expected\n"
            f"    return None\n")


def _assertion_text(entry, args, expected):
    return f"assert {entry}({', '.join(repr(a) for a in args)}) == {expected!r}"


def build_root(root, rec, source_sha256, version) -> tuple:
    """One root's (public record, private record); raises AuditSourceError on any gate failure."""
    if set(rec) != RECORD_KEYS:
        raise AuditSourceError(f"{root}: record keys changed")
    if not isinstance(rec["text"], str) or not isinstance(rec["code"], str) or rec["test_setup_code"] != "" \
            or rec["challenge_test_list"] != [] or not isinstance(rec["test_list"], list) or len(rec["test_list"]) != 3 \
            or not all(isinstance(t, str) for t in rec["test_list"]):
        raise AuditSourceError(f"{root}: record structure changed")
    entry, params = _signature(rec["code"])
    parsed = [parse_assertion(t, entry, len(params)) for t in rec["test_list"]]
    task_id = f"mbpp/{root}"
    public = {"record_type": "public_task", "version": version, "task_id": task_id, "adapted_public_contract": ADAPTED_PUBLIC[root],
              "signature": f"{entry}({', '.join(params)})", "entry_point": entry,
              "public_case": {"case_id": PUBLIC_CASE_ID, "args_literal": parsed[0]["args_literal"],
                              "expected_literal": parsed[0]["expected_literal"]},
              "public_assertion": {"assertion_index": 0, "text": rec["test_list"][0], "raw_sha256": raw_sha256(rec["test_list"][0]),
                                   "normalized_ast_sha256": normalized_ast_sha256(rec["test_list"][0])},
              "source_sha256": source_sha256}
    original = [{"case_id": f"original_private-{i}", "assertion_index": i, "text": rec["test_list"][i],
                 "raw_sha256": raw_sha256(rec["test_list"][i]), "normalized_ast_sha256": normalized_ast_sha256(rec["test_list"][i]),
                 "args_literal": parsed[i]["args_literal"], "expected_literal": parsed[i]["expected_literal"]} for i in (1, 2)]
    supplement = []
    for j, (args, expected) in enumerate(SUPPLEMENT_V1[root]):
        if len(args) != len(params):
            raise AuditSourceError(f"{root}: supplement case {j} arity differs from the signature")
        text = _assertion_text(entry, args, expected)
        supplement.append({"case_id": f"supplement_v1-{j}", "args_literal": repr(list(args)), "expected_literal": repr(expected),
                           "assertion_text": text, "raw_sha256": raw_sha256(text), "normalized_ast_sha256": normalized_ast_sha256(text)})
    codes = [_control_code(entry, params, body) for _, body in WRONG_RULES[root]]
    codes += [_control_code(entry, params, f"return {parsed[0]['expected']!r}"), _lookup_code(entry, params, parsed)]
    controls = []
    for kind, code, rule in zip(CONTROL_KINDS, codes, [*WRONG_RULES[root], ("constant", None), ("lookup", None)]):
        controls.append({"control_id": f"{task_id}/control/{kind}", "kind": kind, "rule": rule[0], "code": code,
                         "raw_sha256": raw_sha256(code),
                         "predicted": {"original_private": PREDICTIONS[root][kind][0], "supplement_v1": PREDICTIONS[root][kind][1]}})
    private = {"record_type": "private_endpoint_package", "version": version, "task_id": task_id,
               "public_record_sha256": canonical_sha256(public), "entry_point": entry,
               "original_description": rec["text"], "original_description_sha256": raw_sha256(rec["text"]),
               "reference": {"code": rec["code"], "raw_sha256": raw_sha256(rec["code"]),
                             "predicted": {"original_private": True, "supplement_v1": True}},
               "batteries": {"original_private": {"label": "unchanged original MBPP assertions 1 and 2", "cases": original},
                             "supplement_v1": {"label": "lead-authored literal cases; not universal correctness or secrecy",
                                               "cases": supplement}},
               "controls": controls,
               "endpoint": "proposed: pass both batteries; each battery reported separately"}
    return public, private


def _file_sha(path) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as e:
        raise AuditSourceError(f"cannot hash {Path(path).name}: {type(e).__name__}") from None


def build(source_path) -> dict:
    """The real v1 package (module pins only). All nine roots are included; a root whose gate fails is recorded as a
    refusal, never backfilled."""
    return _build(source_path, SOURCE_SHA256, VERSION, "production")


def _build_synthetic_for_tests(source_path, source_sha256) -> dict:
    return _build(source_path, source_sha256, VERSION + "-SYNTHETIC-TEST-FIXTURE", "synthetic_test_fixture_not_the_v1_package")


def _build(source_path, source_sha256, version, designation) -> dict:
    recs = load_source(source_path, source_sha256)
    public_records, private_records, refusals = [], [], []
    for root in ROOTS:
        try:
            pub, priv = build_root(root, recs[root], source_sha256, version)
        except AuditSourceError as e:
            refusals.append({"task_id": f"mbpp/{root}", "refusal": str(e)})
            continue
        public_records.append(pub)
        private_records.append(priv)
    manifest = {"version": version, "designation": designation, "decision": DECISION, "status": "source_only",
                "collection": "unreleased", "execution_performed": False, "source_sha256": source_sha256,
                "roots_in_order": [f"mbpp/{r}" for r in ROOTS], "refusals": refusals,
                "public_record_sha256": {p["task_id"]: canonical_sha256(p) for p in public_records},
                "private_record_sha256": {p["task_id"]: canonical_sha256(p) for p in private_records},
                "builder_sha256": _file_sha(__file__), "config_sha256": _file_sha(CONFIG_PATH),
                "hash_conventions": {"raw": "sha256 of the exact UTF-8 bytes of a text",
                                     "canonical": "sha256 of json.dumps(sort_keys=True, ensure_ascii=False, separators=(',', ':')) UTF-8",
                                     "normalized_ast": "sha256 of ast.dump(ast.parse(text), include_attributes=False) UTF-8"},
                "planned_inventory": {"artifacts": 9 * 6, "slots": 9 * 6 * 3,
                                      "note": "planning arithmetic only; slots are not independent observations"},
                "prediction_findings": PREDICTION_FINDINGS,
                "grader_adapter_note": "the unchanged grader validates one private_assertions list per spec; the later audit "
                                       "needs one spec per battery (original_private, supplement_v1) and reports both"}
    return {"manifest": manifest, "public_records": public_records, "private_records": private_records}


def write_package(package: dict, out_dir, *, work_root=WORK_ROOT) -> list:
    out, base = Path(out_dir).resolve(), Path(work_root).resolve()
    if base not in out.parents:
        raise AuditSourceError("output directory must be inside the gitignored work root")
    out.mkdir(parents=False, exist_ok=False)
    (out / "public").mkdir()
    (out / "private").mkdir()
    files = [("manifest.json", package["manifest"])]
    files += [(f"public/{p['task_id'].replace('/', '_')}.json", p) for p in package["public_records"]]
    files += [(f"private/{p['task_id'].replace('/', '_')}.json", p) for p in package["private_records"]]
    for name, value in files:
        with open(out / name, "x", encoding="utf-8") as fh:
            fh.write(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=1) + "\n")
    return [n for n, _ in files]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the MRL-37 nine-root measurement package (source only; executes nothing).")
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        names = write_package(build(a.source), a.out)
    except (AuditSourceError, FileExistsError) as e:
        print(f"refused: {type(e).__name__}: {e}")
        return 2
    print("\n".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
