"""Endpoint-audit package builder: MRL-33 source-only preparation for LEAD-ENDPOINT-01 (prompt-choice-endpoint-audit-v1).

Builds deterministic public task records and separate private battery/control records for the fixed measurement-
development panel MBPP 877 then 345 (docs/policy_endpoint_audit_contract_20260926.md). Root 945 keeps its
unsupported-set hold and never appears as an executable task. The two roots are not independent evaluation families.

Pure and source-only. Standard library only; the module never imports collect/diagnostic/grade (collect imports urllib and
subprocess). It has no exec, eval, compile, dynamic import, subprocess, network, sandbox or runner path: reference code,
assertions and controls are handled as text and parsed with ast only. Literal values come from ast.literal_eval on
single literal nodes, never from running a test expression. Raw third-party source and the generated private package
stay in the gitignored work/ directory.

Hash conventions: `raw` = SHA256 of the exact UTF-8 bytes of a text; `canonical` = SHA256 of
json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) encoded as UTF-8 (the collect.digest rule);
`normalized_ast` = SHA256 of ast.dump(ast.parse(text), include_attributes=False) (the grader's normalize_assertion form).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

VERSION = "prompt-choice-endpoint-audit-v1"
DECISION = "LEAD-ENDPOINT-01"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORK_ROOT = REPO / "work"
CONFIG_PATH = HERE / "endpoint_audit_source_v1.json"
SOURCE_SHA256 = "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"
ROOTS = (877, 345)  # exact order
HELD_ROOTS = {945: "unsupported_set_public_display_hold (LEAD-FRAME-03): not an executable task; no replacement"}
PUBLIC_CASE_ID = "public-0"
RECORD_KEYS = frozenset({"text", "code", "task_id", "test_setup_code", "test_list", "challenge_test_list"})

# Per-record pins (raw SHA256 of the exact source strings); a changed record fails closed even under a matching file hash.
RECORD_PINS = {
    877: {"entry_point": "sort_String",
          "text_sha256": "2a1082a4f144e9d2ec98564974fcbb29c0133574450ea2d4644c432ee2049839",
          "reference_sha256": "ce8de2c84a0fee936257bfe9330221be20a61130561da95ae24b43514bb9f1d5",
          "assertion_sha256": ("e53a2ba7fef43c1024cca1c41d31ab3d3483a37f74d4da9fe7bd52795c8b0db5",
                               "eaf729dd6b9f534449bb2931103e066ea1a2cd2d414c59609eb92dafdcf912f4",
                               "0025a59973d620dc2c45749c5ca9080b40123d1e2edd9c7424772ad1faf148d3")},
    345: {"entry_point": "diff_consecutivenums",
          "text_sha256": "cbf0e9e214fe1c5c6ba1547e9d76c41093c8138d68d2be9775c03c64a02c3915",
          "reference_sha256": "bb61aa52406b2b73495090e3cbd215297218c4c1f3b3952f5f3d2bb233756825",
          "assertion_sha256": ("c08474c9010d01f807e5dc8583e82fc48c5c06a446be0d93f85f98b4bb00268b",
                               "74351d019afc273394e2d60f456376fe2483d84ddf73d24a1679adfb9f93906f",
                               "d57814e9734ac0652f97abf43d3b725ecc15460973213dde0efbddcc353f73c9")},
}

# Exact lead-authored supplement_v1 (contract table), frozen as literals: (positional args, expected value).
# Never computed with the reference or copied from a model answer.
SUPPLEMENT_V1 = {
    877: ((("",), ""), (("q",), "q"), (("bbaca",), "aabbc"), (("fedcab",), "abcdef")),
    345: ((([],), []), (([8],), []), (([5, 2, -2, 4],), [-3, -4, 6]), (([-3, -3, 0, -5],), [0, 3, -5])),
}

# Five frozen wrong controls per root. Fixed ones are exact source; `constant_public_expected` and
# `lookup_original_examples` are generated from parsed literals of the original assertions (never by running them).
FIXED_CONTROLS = {
    877: {"return_input_unchanged": "def sort_String(s):\n    return s\n",
          "reverse_input": "def sort_String(s):\n    return s[::-1]\n",
          "sorted_unique_characters": "def sort_String(s):\n    return ''.join(sorted(set(s)))\n"},
    345: {"return_input_unchanged": "def diff_consecutivenums(nums):\n    return nums\n",
          "absolute_adjacent_differences": "def diff_consecutivenums(nums):\n    return [abs(b - a) for a, b in zip(nums[:-1], nums[1:])]\n",
          "previous_minus_next": "def diff_consecutivenums(nums):\n    return [a - b for a, b in zip(nums[:-1], nums[1:])]\n"},
}
CONTROL_ORDER = {877: ("return_input_unchanged", "reverse_input", "sorted_unique_characters", "constant_public_expected",
                       "lookup_original_examples"),
                 345: ("return_input_unchanged", "absolute_adjacent_differences", "previous_minus_next",
                       "constant_public_expected", "lookup_original_examples")}
CONTROL_RATIONALE = {
    "return_input_unchanged": "identity: returns the input, ignoring the stated transformation",
    "reverse_input": "reverses the string instead of sorting it",
    "sorted_unique_characters": "sorts but drops repeated characters",
    "absolute_adjacent_differences": "loses the sign of next minus previous",
    "previous_minus_next": "reverses the difference direction (previous minus next)",
    "constant_public_expected": "returns the original public expected result for every input",
    "lookup_original_examples": ("returns the expected value of the three original examples and None on unseen input; "
                                 "predicted by the lead to pass the original examples and fail the supplement, an explicit "
                                 "measurement limitation of the old finite suite, not observed memorization"),
}
LEAD_PREDICTION = {k: ("pass original examples; fail supplement_v1" if k == "lookup_original_examples"
                       else "rejected by at least one original_private case") for k in CONTROL_RATIONALE}
BATTERY_LABELS = {
    "original_private": "unchanged original MBPP assertions 2 and 3 (indices 1 and 2); historical meaning kept separate",
    "supplement_v1": "exact lead-authored diagnostic coverage; not proof of correctness or of benchmark secrecy",
}
ENDPOINT = ("proposed prompt-choice-endpoint-audit-v1: acceptance of the union of original_private and supplement_v1, "
            "with each battery outcome reported separately; finite-suite acceptance, not full-domain correctness")
GRADER_ADAPTER_NOTE = ("The existing landmark grader validates one private_assertions list per root and returns one outcome. "
                       "It does not produce battery-specific results. A later reviewed adapter must grade original_private "
                       "and supplement_v1 as separately labeled batteries (for example two frozen specs per root, or a "
                       "battery-aware grader version) and report both; this module adds no runner.")


class AuditSourceError(ValueError):
    """Fail-closed refusal of a source file or record that does not match the frozen expectations."""


def raw_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_sha256(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def normalized_ast_sha256(text: str) -> str:
    return hashlib.sha256(ast.dump(ast.parse(text), include_attributes=False).encode("utf-8")).hexdigest()


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise AuditSourceError("duplicate JSON key in a source record")
    return dict(pairs)


def _literal(node, what):
    try:
        return ast.literal_eval(node)  # a single literal node only; no name lookup, call or evaluation
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as e:
        raise AuditSourceError(f"{what} is not a literal: {type(e).__name__}") from None


def parse_assertion(text: str, entry_point: str) -> dict:
    """`assert <entry_point>(<one literal>) == <literal>` parsed as text; the expression is never run."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        raise AuditSourceError(f"assertion does not parse: {type(e).__name__}") from None
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assert) or tree.body[0].msg is not None:
        raise AuditSourceError("each assertion must be one standalone assert without a message")
    test = tree.body[0].test
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
            and isinstance(test.left, ast.Call) and isinstance(test.left.func, ast.Name) and test.left.func.id == entry_point
            and not test.left.keywords and len(test.left.args) == 1 and not isinstance(test.left.args[0], ast.Starred)):
        raise AuditSourceError(f"assertion must be `assert {entry_point}(<one literal>) == <literal>`")
    args = [_literal(a, "argument") for a in test.left.args]
    expected = _literal(test.comparators[0], "expected value")
    return {"args": args, "expected": expected, "args_literal": repr(args), "expected_literal": repr(expected)}


def _signature(code: str, entry_point: str) -> str:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        raise AuditSourceError(f"reference does not parse: {type(e).__name__}") from None
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(defs) != 1 or defs[0].name != entry_point or len(tree.body) != 1:
        raise AuditSourceError("reference must be exactly one top-level definition of the entry point")
    a = defs[0].args
    if a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs or a.defaults or len(a.args) != 1:
        raise AuditSourceError("reference signature must take exactly one positional parameter")
    return f"{entry_point}({a.args[0].arg})"


def load_source(source_path, source_sha256=SOURCE_SHA256, roots=ROOTS) -> dict:
    """Read the explicitly given pinned JSONL; fail closed on missing file, hash mismatch, bad UTF-8/JSON, duplicate IDs
    anywhere or a missing root. Returns {root: record} for the requested roots only."""
    path = Path(source_path)
    try:
        data = path.read_bytes()
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


def _check_record(root, rec, pins):
    pin = pins[root]
    if set(rec) != RECORD_KEYS:
        raise AuditSourceError(f"{root}: record keys changed")
    if not isinstance(rec["text"], str) or not isinstance(rec["code"], str) or rec["test_setup_code"] != "" \
            or rec["challenge_test_list"] != [] or not isinstance(rec["test_list"], list) or len(rec["test_list"]) != 3 \
            or not all(isinstance(t, str) for t in rec["test_list"]):
        raise AuditSourceError(f"{root}: record structure changed (text, code, empty setup/challenge, three assertion strings)")
    if raw_sha256(rec["text"]) != pin["text_sha256"] or raw_sha256(rec["code"]) != pin["reference_sha256"] \
            or tuple(raw_sha256(t) for t in rec["test_list"]) != tuple(pin["assertion_sha256"]):
        raise AuditSourceError(f"{root}: description, reference or assertion bytes differ from the pins")


def _lookup_control(entry_point, param, examples):
    """One function definition only (the table lives inside it), so the control meets the terminal output contract and a
    later rejection measures test coverage rather than a format mismatch."""
    table = tuple((ex["args"][0], ex["expected"]) for ex in examples)
    return (f"def {entry_point}({param}):\n    examples = {table!r}\n    for argument, expected in examples:\n"
            f"        if argument == {param}:\n            return expected\n    return None\n")


def _assertion_text(entry_point, args, expected):
    return f"assert {entry_point}({', '.join(repr(a) for a in args)}) == {expected!r}"


SYNTHETIC_VERSION = VERSION + "-SYNTHETIC-TEST-FIXTURE"


def _file_sha256(path) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as e:
        raise AuditSourceError(f"cannot hash {Path(path).name}: {type(e).__name__}") from None


def build(source_path) -> dict:
    """The real v1 package: module pins only (no override), actual builder/config file hashes. Nothing is executed."""
    return _build(source_path, SOURCE_SHA256, RECORD_PINS, VERSION, "production")


def _build_synthetic_for_tests(source_path, source_sha256, pins) -> dict:
    """Private test helper: caller-supplied pins, and every record and the manifest are labeled synthetic, never v1."""
    return _build(source_path, source_sha256, pins, SYNTHETIC_VERSION, "synthetic_test_fixture_not_the_v1_package")


def _build(source_path, source_sha256, pins, version, designation) -> dict:
    """Deterministic package: {'manifest', 'public_records', 'private_records'}."""
    builder_sha256, config_sha256 = _file_sha256(__file__), _file_sha256(CONFIG_PATH)
    recs = load_source(source_path, source_sha256)
    public_records, private_records = [], []
    for root in ROOTS:
        rec = recs[root]
        _check_record(root, rec, pins)
        entry = pins[root]["entry_point"]
        signature = _signature(rec["code"], entry)
        param = "s" if root == 877 else "nums"
        parsed = [parse_assertion(t, entry) for t in rec["test_list"]]
        task_id = f"mbpp/{root}"
        public = {"record_type": "public_task", "version": version, "task_id": task_id, "description": rec["text"],
                  "signature": signature, "entry_point": entry,
                  "public_case": {"case_id": PUBLIC_CASE_ID, "args_literal": parsed[0]["args_literal"],
                                  "expected_literal": parsed[0]["expected_literal"]},
                  "public_assertion": {"assertion_index": 0, "text": rec["test_list"][0], "raw_sha256": raw_sha256(rec["test_list"][0]),
                                       "normalized_ast_sha256": normalized_ast_sha256(rec["test_list"][0])},
                  "source_sha256": source_sha256}
        public_sha = canonical_sha256(public)
        original = [{"case_id": f"original_private-{i}", "assertion_index": i, "text": rec["test_list"][i],
                     "raw_sha256": raw_sha256(rec["test_list"][i]), "normalized_ast_sha256": normalized_ast_sha256(rec["test_list"][i]),
                     "args_literal": parsed[i]["args_literal"], "expected_literal": parsed[i]["expected_literal"]} for i in (1, 2)]
        supplement = []
        for j, (args, expected) in enumerate(SUPPLEMENT_V1[root]):
            text = _assertion_text(entry, args, expected)
            supplement.append({"case_id": f"supplement_v1-{j}", "args_literal": repr(list(args)), "expected_literal": repr(expected),
                               "assertion_text": text, "raw_sha256": raw_sha256(text), "normalized_ast_sha256": normalized_ast_sha256(text)})
        generated = {"constant_public_expected": f"def {entry}({param}):\n    return {parsed[0]['expected']!r}\n",
                     "lookup_original_examples": _lookup_control(entry, param, parsed)}
        controls = []
        for kind in CONTROL_ORDER[root]:
            code = FIXED_CONTROLS[root].get(kind) or generated[kind]
            controls.append({"control_id": f"{task_id}/control/{kind}", "kind": kind, "rationale": CONTROL_RATIONALE[kind],
                             "lead_prediction": LEAD_PREDICTION[kind], "code": code, "raw_sha256": raw_sha256(code),
                             "provenance": "generated from parsed original literals" if kind in generated else "fixed exact source"})
        private = {"record_type": "private_endpoint_package", "version": version, "task_id": task_id,
                   "public_record_sha256": public_sha, "entry_point": entry,
                   "reference": {"code": rec["code"], "raw_sha256": raw_sha256(rec["code"]),
                                 "expectation": "must be accepted on both batteries in a later contained audit (not yet checked)"},
                   "batteries": {"original_private": {"label": BATTERY_LABELS["original_private"], "cases": original},
                                 "supplement_v1": {"label": BATTERY_LABELS["supplement_v1"], "cases": supplement}},
                   "controls": controls, "endpoint": ENDPOINT}
        public_records.append(public)
        private_records.append(private)
    manifest = {"version": version, "designation": designation, "decision": DECISION, "status": "source_only", "collection": "unreleased",
                "execution_performed": False, "source_sha256": source_sha256, "roots_in_order": [f"mbpp/{r}" for r in ROOTS],
                "held_roots": {f"mbpp/{k}": v for k, v in HELD_ROOTS.items()}, "public_case_id": PUBLIC_CASE_ID,
                "public_record_sha256": {p["task_id"]: canonical_sha256(p) for p in public_records},
                "private_record_sha256": {p["task_id"]: canonical_sha256(p) for p in private_records},
                "builder_sha256": builder_sha256, "config_sha256": config_sha256,
                "hash_conventions": {"raw": "sha256 of the exact UTF-8 bytes of a text",
                                     "canonical": "sha256 of json.dumps(sort_keys=True, ensure_ascii=False, separators=(',', ':')) UTF-8",
                                     "normalized_ast": "sha256 of ast.dump(ast.parse(text), include_attributes=False) UTF-8"},
                "batteries": BATTERY_LABELS, "endpoint": ENDPOINT, "grader_adapter_note": GRADER_ADAPTER_NOTE,
                "measurement_panel_note": "measurement-development panel selected by source compatibility; not independent evaluation families"}
    return {"manifest": manifest, "public_records": public_records, "private_records": private_records}


def write_package(package: dict, out_dir, *, work_root=WORK_ROOT) -> list:
    """Create a NEW directory inside the gitignored work root (never overwrite) and write the package files exclusively."""
    out, base = Path(out_dir).resolve(), Path(work_root).resolve()
    if base not in out.parents:
        raise AuditSourceError("output directory must be inside the gitignored work root")
    out.mkdir(parents=False, exist_ok=False)  # FileExistsError for an existing directory: nothing is overwritten
    (out / "public").mkdir()
    (out / "private").mkdir()
    files = [("manifest.json", package["manifest"])]
    files += [(f"public/{p['task_id'].replace('/', '_')}.json", p) for p in package["public_records"]]
    files += [(f"private/{p['task_id'].replace('/', '_')}.json", p) for p in package["private_records"]]
    written = []
    for name, value in files:
        with open(out / name, "x", encoding="utf-8") as fh:
            fh.write(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=1) + "\n")
        written.append(name)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the MRL-33 endpoint-audit package (source only; executes nothing).")
    ap.add_argument("--source", required=True, help="explicit path to the pinned MBPP JSONL")
    ap.add_argument("--out", required=True, help="new directory inside work/ (must not exist)")
    a = ap.parse_args(argv)
    try:
        names = write_package(build(a.source), a.out)
    except (AuditSourceError, FileExistsError) as e:  # fail closed with a message; nothing is overwritten
        print(f"refused: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    for name in names:
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
