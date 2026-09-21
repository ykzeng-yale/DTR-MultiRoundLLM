"""Public-diagnostic rendering for the MRL-08 five-arm development design (source only).

Pure functions over public objects: the fixed public examples, the receiver's initial
answer and the per-case public-check results. Nothing here executes candidate, example
or diagnostic text, and no private spec, hidden test, reference or grade is an input.
Instruction strings are copied verbatim from docs/public_diagnostic_design_20260921.md;
the header and 2,048-byte cap follow the lead's MRL-08 freeze field 2.
"""
from __future__ import annotations

import ast
import json
import re

from experiments.landmark import collect

SCHEMA = "public-diagnostic-v1"
EXAMPLES_HEADER = "Public examples (inputs and required outputs):"
DIAGNOSTIC_HEADER = "Public diagnostic report for the previous answer (execution status is recorded per case):"
MAX_DIAGNOSTIC_BYTES = 2048
STATUSES = ("pass", "wrong_value", "format_error", "interface_error", "program_exception", "timeout", "unavailable", "output_limit")
VALUE_KINDS = ("int", "int_list", "unsupported", "none")
UNAVAILABLE_REASONS = ("not_attempted_after_termination", "infrastructure_not_started", "protocol_integrity_review")
MAX_ABS_INT, MAX_LIST_LEN = 10**18 - 1, 16  # freeze field 3: int (not bool) with |v| < 10**18, lists of <= 16
PAYLOAD_FAILURES = ("wrong_value", "format_error", "interface_error", "program_exception")
INCOMPLETE = ("timeout", "unavailable", "output_limit")
ARM_IDS = ("N0", "S0", "N1", "S1", "R1")

N_INSTRUCTION = "Reconsider your previous answer against the original task and public information. Return your best complete answer."
S1_STRINGS = (
    "Review the first public example with a recorded wrong value, format error, interface error, or program exception, in the diagnostic order. Compare the expected result with the recorded behavior, identify the discrepancy in your previous answer, and return a complete corrected answer. Check the remaining public examples and the full stated domain; do not merely hard-code the examples.",
    "The public diagnostic is incomplete. Do not interpret an unavailable result as a pass or infer a hidden error. Review your previous answer against the full stated domain and return your best complete answer.",
    "Your previous answer passes the listed public examples, which do not establish correctness on the full stated domain. Check whether any change is needed; preserve correct behavior and return your best complete answer.",
)
R1_INSTRUCTION = "Solve the original task using the public information and diagnostic observations. Return your best complete answer."
# Freeze field 10: S0 keeps the pinned syntactic cue. collect.digest(collect.TARGETED) at MRL-08.
TARGETED_SHA256 = "b149db3d503004eb7ba1600d8b83563f6f3d929fbce19de1dfa7a6afea26dd8f"


class DiagnosticOverflow(ValueError):
    """Canonical diagnostic exceeds the frozen byte cap; never truncated."""


def _unique_pairs(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError(f"duplicate JSON key: {k!r}")
        obj[k] = v
    return obj


def strict_json_loads(data):
    """json.loads that raises ValueError on any duplicate object key, at any depth (shared interface).

    Every JSON parse of an untrusted stream or file in the diagnostic path goes through here, so a
    record with two values for one key can never be read as either of them."""
    if not isinstance(data, (str, bytes, bytearray)):
        raise ValueError("strict_json_loads takes str or bytes")
    return json.loads(data, object_pairs_hook=_unique_pairs)


def _is_int(v):
    return type(v) is int and abs(v) <= MAX_ABS_INT  # bool excluded by exact type


def _displayable(v):
    return _is_int(v) or (type(v) is list and len(v) <= MAX_LIST_LEN and all(_is_int(x) for x in v))


def _public_cases(entry_point, cases):
    # Only the three public fields are accepted, so no private field can reach a renderer.
    if not isinstance(entry_point, str) or not entry_point.isidentifier():
        raise ValueError("entry_point must be an identifier")
    if not isinstance(cases, list) or not cases:
        raise ValueError("need a nonempty ordered case list")
    for c in cases:
        if not isinstance(c, dict) or set(c) != {"case_id", "args_literal", "expected_literal"} or not all(isinstance(v, str) for v in c.values()):
            raise ValueError("public case must have exactly case_id, args_literal, expected_literal strings")
        if type(literal(c["args_literal"])) is not list:
            raise ValueError("args_literal must be a list literal of positional arguments")
    return cases


def render_call(entry_point: str, args_literal: str) -> str:
    return f"{entry_point}({', '.join(repr(a) for a in literal(args_literal))})"


def render_public_examples(entry_point: str, cases: list[dict]) -> str:
    _public_cases(entry_point, cases)
    lines = [f"{render_call(entry_point, c['args_literal'])} == {literal(c['expected_literal'])!r}" for c in cases]
    return "\n".join([EXAMPLES_HEADER, *lines])


def _check_result(r):
    if not isinstance(r, dict) or set(r) != {"status", "returned", "value_kind", "reason"}:
        raise ValueError("result must have exactly status, returned, value_kind, reason")
    status, returned, kind, reason = r["status"], r["returned"], r["value_kind"], r["reason"]
    # Exact str before any membership test: a list/dict/None/int is a ValueError, never a TypeError.
    if type(status) is not str or type(kind) is not str or status not in STATUSES or kind not in VALUE_KINDS:
        raise ValueError(f"unknown status/value_kind: {status!r}/{kind!r}")
    if reason is not None and type(reason) is not str:
        raise ValueError("reason must be None or a string")
    ok = {"int": _is_int(returned), "int_list": type(returned) is list and _displayable(returned),
          "unsupported": returned is None, "none": returned is None}[kind]
    if not ok:
        raise ValueError("returned value does not match its bounded value_kind")
    # Freeze field 6: status only. A reason is the explicit cause of an unavailable case, nothing else.
    if (status == "unavailable") != (reason is not None) or (reason is not None and reason not in UNAVAILABLE_REASONS):
        raise ValueError("reason is required for unavailable (one of UNAVAILABLE_REASONS) and forbidden otherwise")
    # Only an observed return (pass / wrong_value) may display a value; every other status is status-only
    # (fields 3 and 6). The executor cannot emit such a line, so the validator must not accept one either.
    if status not in ("pass", "wrong_value") and kind != "none":
        raise ValueError(f"{status} cannot carry a returned value")


def literal(text):
    """ast.literal_eval of a public literal; any malformed literal is a ValueError (never SyntaxError etc.)."""
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError) as exc:
        raise ValueError(f"malformed public literal: {type(exc).__name__}") from None


def check_consistent(status, kind, returned, expected):
    """A bounded primitive return (int / int_list) is the value itself, so its status must equal the private
    assert's Python ==: pass iff returned == expected. value_kind unsupported (returned None) keeps the
    executor's in-isolation equality result, so either pass or wrong_value is allowed."""
    if kind in ("int", "int_list") and status in ("pass", "wrong_value"):
        if (status == "pass") != bool(returned == expected):
            raise ValueError(f"status {status} is inconsistent with the returned value and the public expected value")
    if kind == "none" and status in ("pass", "wrong_value") and (status == "pass") != (expected is None):
        raise ValueError(f"status {status} is inconsistent with a None return and the public expected value")


def build_diagnostic(root_id: str, initial_artifact_sha256: str, entry_point: str, cases: list[dict], results: list[dict]) -> dict:
    _public_cases(entry_point, cases)
    if not isinstance(root_id, str) or not root_id:
        raise ValueError("root_id required")
    if not isinstance(initial_artifact_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", initial_artifact_sha256):
        raise ValueError("initial_artifact_sha256 must be 64 lowercase hex")
    if not isinstance(results, list) or len(results) != len(cases):
        raise ValueError("one result per public case, in the fixed case order")
    rows = []
    for c, r in zip(cases, results):
        _check_result(r)
        expected = literal(c["expected_literal"])
        if not _displayable(expected):
            raise ValueError("public expected value outside the bounded display policy")
        rows.append({"case_id": c["case_id"], "call": render_call(entry_point, c["args_literal"]), "expected": expected,
                     "status": r["status"], "returned": r["returned"], "value_kind": r["value_kind"], "reason": r["reason"]})
    diag = {"schema_version": SCHEMA, "root_id": root_id, "initial_artifact_sha256": initial_artifact_sha256, "cases": rows}
    validate_diagnostic(diag)  # same policy as a loaded record; overflow fails at build time, before any arm is rendered
    return diag


DIAG_KEYS = frozenset({"schema_version", "root_id", "initial_artifact_sha256", "cases"})
CASE_KEYS = frozenset({"case_id", "call", "expected", "status", "returned", "value_kind", "reason"})


def public_skeleton(entry_point: str, cases: list[dict]) -> list[tuple]:
    """(case_id, call, expected) per fixed public case, built exactly as build_diagnostic builds its rows."""
    _public_cases(entry_point, cases)
    return [(c["case_id"], render_call(entry_point, c["args_literal"]), literal(c["expected_literal"])) for c in cases]


def _same(a, b):
    return type(a) is type(b) and (a == b if type(a) is not list else len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b)))


def validate_diagnostic(diag: dict, entry_point: str | None = None, cases: list[dict] | None = None) -> None:
    """Refuse any record build_diagnostic could not have produced: exact keys, bounded values, byte cap.

    With entry_point and cases (the task's fixed public cases), also require the exact ordered
    case_id, call and expected of every row, so no non-public text can ride in a diagnostic.
    """
    if not isinstance(diag, dict) or set(diag) != DIAG_KEYS:
        raise ValueError("diagnostic must have exactly schema_version, root_id, initial_artifact_sha256, cases")
    if diag["schema_version"] != SCHEMA:
        raise ValueError("not a public-diagnostic-v1 record")
    if not isinstance(diag["root_id"], str) or not diag["root_id"]:
        raise ValueError("root_id required")
    sha = diag["initial_artifact_sha256"]
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("initial_artifact_sha256 must be 64 lowercase hex")
    if not isinstance(diag["cases"], list) or not diag["cases"]:
        raise ValueError("need a nonempty ordered case list")
    for c in diag["cases"]:
        if not isinstance(c, dict) or set(c) != CASE_KEYS:
            raise ValueError("diagnostic case must have exactly " + ", ".join(sorted(CASE_KEYS)))
        if not isinstance(c["case_id"], str) or not c["case_id"] or not isinstance(c["call"], str):
            raise ValueError("case_id and call must be strings")
        if not _displayable(c["expected"]):
            raise ValueError("public expected value outside the bounded display policy")
        _check_result({k: c[k] for k in ("status", "returned", "value_kind", "reason")})
        check_consistent(c["status"], c["value_kind"], c["returned"], c["expected"])
    if (entry_point is None) != (cases is None):
        raise ValueError("entry_point and cases are given together")
    if cases is not None:
        skeleton = public_skeleton(entry_point, cases)
        rows = [(c["case_id"], c["call"], c["expected"]) for c in diag["cases"]]
        if len(rows) != len(skeleton) or not all(r[0] == k[0] and r[1] == k[1] and _same(r[2], k[2]) for r, k in zip(rows, skeleton)):
            raise ValueError("diagnostic cases differ from the fixed public cases (case_id, call, expected, count or order)")
    diagnostic_message(diag)  # DiagnosticOverflow (a ValueError) past MAX_DIAGNOSTIC_BYTES


def load_diagnostic(data, entry_point: str | None = None, cases: list[dict] | None = None) -> dict:
    """Parse one serialized diagnostic record (str/bytes) with strict_json_loads, then validate_diagnostic."""
    diag = strict_json_loads(data)
    validate_diagnostic(diag, entry_point, cases)
    return diag


def diagnostic_bytes(diag: dict) -> bytes:
    if not isinstance(diag, dict) or diag.get("schema_version") != SCHEMA:
        raise ValueError("not a public-diagnostic-v1 record")
    data = json.dumps(diag, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_DIAGNOSTIC_BYTES:
        raise DiagnosticOverflow(f"diagnostic JSON is {len(data)} bytes > {MAX_DIAGNOSTIC_BYTES}")
    return data


def diagnostic_message(diag: dict) -> dict:
    content = DIAGNOSTIC_HEADER + "\n" + diagnostic_bytes(diag).decode("utf-8")
    # The lead's cap is on the total message; checking the full content is the stricter reading.
    if len(content.encode("utf-8")) > MAX_DIAGNOSTIC_BYTES:
        raise DiagnosticOverflow(f"diagnostic message is {len(content.encode('utf-8'))} bytes > {MAX_DIAGNOSTIC_BYTES}")
    return {"role": "user", "content": content}


def select_s1(diag: dict) -> str:
    statuses = [c["status"] for c in diag["cases"]]
    if any(type(s) is not str or s not in STATUSES for s in statuses):
        raise ValueError("unknown status")
    if any(s in PAYLOAD_FAILURES for s in statuses):
        return S1_STRINGS[0]
    if any(s in INCOMPLETE for s in statuses):
        return S1_STRINGS[1]
    return S1_STRINGS[2]


def render_arms(base_messages: list, initial_output: str, diag: dict) -> dict[str, list]:
    if collect.digest(collect.TARGETED) != TARGETED_SHA256:
        raise RuntimeError("collect.TARGETED changed; S0 is pinned by digest")
    validate_diagnostic(diag)  # exact keys only: nothing extra can reach the shared diagnostic turn
    if not isinstance(initial_output, str):
        raise ValueError("initial_output must be the receiver's text")
    base = [dict(m) for m in base_messages]
    if any(m.get("role") == "assistant" for m in base):
        raise ValueError("base_messages must be the initial public prompt only")
    # Feature comes from collect's pinned syntactic rule on the public answer only.
    _, feature, _ = collect.branches(base, initial_output)
    prefix = [*base, {"role": "assistant", "content": initial_output}]
    shared = diagnostic_message(diag)  # one object's bytes reused by N1, S1 and R1
    user = lambda text: {"role": "user", "content": text}
    return {
        "N0": [*prefix, user(N_INSTRUCTION)],
        "S0": [*prefix, user(collect.TARGETED[feature])],
        "N1": [*prefix, dict(shared), user(N_INSTRUCTION)],
        "S1": [*prefix, dict(shared), user(select_s1(diag))],
        # Context removal: the old answer is dropped, observations about it are retained.
        "R1": [*base, dict(shared), user(R1_INSTRUCTION)],
    }
