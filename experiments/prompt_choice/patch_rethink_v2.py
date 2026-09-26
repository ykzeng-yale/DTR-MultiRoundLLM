"""PATCH / RETHINK same-prefix renderer v2: MRL-32 source-only correction for LEAD-MEASUREMENT-03.

Self-contained copy of the accepted v1 renderer (patch_rethink.py, preserved byte-identical and not imported), with two
versioned changes (docs/policy_renderer_v2_contract_20260926.md):

1. A required public `initial_response_status`, exactly "completed" or "unavailable" (deployment-visible transport
   metadata, not a private grade). A completed answer is any UTF-8 string, INCLUDING the empty string, kept verbatim as
   the assistant message and bound to its actual raw-byte SHA256. "unavailable" requires a null answer and is refused as
   initial_receiver_failure_without_artifact with no prompt. The flag only checks internal consistency; a future
   collector must bind it to the actual transport receipt and raw artifact.
2. Binding before overflow: `oversized_serialization` is returned only after the diagnostic schema/content, the ordered
   public case skeleton, the root identity and the raw initial-artifact binding have all been checked. The unchanged
   diagnostic validator checks its byte cap last in both modes, so its DiagnosticOverflow is deferred, never
   monkeypatched. Where a binding error and an overflow both occur, v2 reports the binding error (v1 reported overflow).

Pure and source-only: no network, subprocess, code-execution or receiver-dispatch path, no common fallback, no B2
change. The recipe, caveat and terminal strings are byte-identical to v1. Collection is UNRELEASED.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.landmark import diagnostic as dg

VERSION = "patch-rethink-source-v2"
CONFIG_PATH = Path(__file__).with_name("patch_rethink_source_v2.json")

# Exact strings from LEAD-POLICY-16 (docs/lead_resumption_and_action_contract_20260926.md); PATCH/RETHINK copied from LEAD-POLICY-15.
PATCH = ("Review your previous answer against the original task and any failures shown in the public diagnostic. "
         "Preserve its correct behavior; change only what is needed for the full stated task domain. If no public failure "
         "is shown, do not infer that the answer is correct on hidden cases. Do not hard-code the public examples. "
         "Return one complete solution.")
RETHINK = ("Re-derive a solution from the original task. Treat any failures shown in the public diagnostic as evidence "
           "about the previous answer. Do not assume the previous algorithm is correct; use the previous answer only to "
           "avoid witnessed errors. Check the full stated task domain, not only the public examples. Return one complete "
           "solution.")
COMMON_CAVEAT = ("For any check marked timeout, unavailable, or output_limit, the required result was not fully observed; "
                 "do not treat that status as a pass or as proof that the answer is wrong. Completed results retain their "
                 "recorded meaning, including failures when other checks are incomplete. Passing the public examples does "
                 "not establish correctness on the full stated task domain.")
TERMINAL_OUTPUT_CONTRACT = ("Return the complete solution as Python source containing only the function definition and any "
                            "imports it needs. Do not include test calls, example output, or any text copied from the "
                            "diagnostic report. If you use a code fence, use exactly one.")  # terminal-output-contract-v2
RECIPES = {"PATCH": PATCH, "RETHINK": RETHINK}
ACTIONS = ("PATCH", "RETHINK")

INCOMPLETE = ("timeout", "unavailable", "output_limit")
PAYLOAD_FAILURES = ("wrong_value", "format_error", "interface_error", "program_exception")
INVALID_DISPOSITIONS = ("initial_receiver_failure_without_artifact", "malformed_or_empty_diagnostic",
                        "oversized_serialization", "integrity_breach", "public_binding_mismatch",
                        "artifact_binding_mismatch", "input_contract_violation")
RESPONSE_STATUSES = ("completed", "unavailable")
REQUIRED_INPUTS = frozenset({"root_id", "base_messages", "initial_response_status", "initial_answer", "initial_answer_sha256",
                             "diagnostic_json", "entry_point", "public_cases"})
OPTIONAL_INPUTS = frozenset({"checkpoint_attestation"})


class InvalidCheckpoint(ValueError):
    """Every refusal before rendering. `record` retains the original diagnostic, supplied transport status and reason."""

    def __init__(self, disposition, record):
        if disposition not in INVALID_DISPOSITIONS:
            raise ValueError(f"unknown invalid-checkpoint disposition {disposition!r}")
        super().__init__(f"{disposition}: {record.get('detail')}")
        self.disposition, self.record = disposition, record


def sha256_text(text: str) -> str:
    """SHA256 of the raw UTF-8 bytes of a text (not the JSON-encoded collect.digest); "" gives e3b0c442...b855."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def messages_sha256(messages) -> str:
    return hashlib.sha256(json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _support(diag: dict) -> dict:
    """Tri-state aggregate that keeps every per-case status (unchanged from v1). PASS iff all pass; INCOMPLETE if any case
    is incomplete; otherwise PAYLOAD_FAILURE. Witnessed failures in a mixed record are kept in has_payload_failure."""
    cases = diag.get("cases") if isinstance(diag, dict) else None
    if not isinstance(cases, list) or not cases or not all(isinstance(c, dict) for c in cases):
        raise ValueError("support requires a nonempty list of case records")
    statuses = [c.get("status") for c in cases]
    if not all(type(x) is str and x in dg.STATUSES for x in statuses):
        raise ValueError("support requires only known statuses")
    has_incomplete = any(x in INCOMPLETE for x in statuses)
    has_payload_failure = any(x in PAYLOAD_FAILURES for x in statuses)
    aggregate = "PASS" if all(x == "pass" for x in statuses) else "INCOMPLETE" if has_incomplete else "PAYLOAD_FAILURE"
    return {"aggregate": aggregate, "has_payload_failure": has_payload_failure, "has_incomplete": has_incomplete,
            "case_statuses": [(c["case_id"], c["status"], c["reason"]) for c in cases],
            "actions": list(ACTIONS)}  # both recipes on every well-formed history: no forced STOP, drop or retry


def _base(base_messages):
    if (not isinstance(base_messages, list) or len(base_messages) != 2
            or [m.get("role") if isinstance(m, dict) else None for m in base_messages] != ["system", "user"]):
        raise ValueError("base_messages must be exactly the public [system, user] task prefix")
    for m in base_messages:
        if set(m) != {"role", "content"} or not isinstance(m["content"], str) or not m["content"]:
            raise ValueError("base message must have exactly role and nonempty content")
    return [dict(m) for m in base_messages]


def render(inputs: dict) -> dict:
    """Render PATCH and RETHINK at one byte-identical prefix from allowlisted public inputs only.
    Every refusal is an InvalidCheckpoint with a disposition and the original diagnostic and status retained."""
    raw = inputs.get("diagnostic_json") if isinstance(inputs, dict) else None
    status = inputs.get("initial_response_status") if isinstance(inputs, dict) else None

    def refuse(disposition, detail, reason=None):
        raise InvalidCheckpoint(disposition, {"diagnostic_json": raw, "initial_response_status": status,
                                              "reason": reason, "detail": detail})

    if not isinstance(inputs, dict) or not REQUIRED_INPUTS <= set(inputs) <= REQUIRED_INPUTS | OPTIONAL_INPUTS:
        refuse("input_contract_violation", "inputs must be exactly the allowlisted public fields (extra or private fields refused)")
    attestation = inputs.get("checkpoint_attestation")
    if attestation is not None:  # an explicitly attested invalid checkpoint is refused, with the original record kept
        if (not isinstance(attestation, dict) or set(attestation) != {"disposition", "reason"}
                or attestation["disposition"] not in INVALID_DISPOSITIONS):
            refuse("input_contract_violation", "checkpoint_attestation must be {disposition, reason} with a known disposition")
        refuse(attestation["disposition"], "explicitly attested invalid checkpoint", attestation["reason"])
    try:
        base = _base(inputs["base_messages"])
        for m in base:
            m["content"].encode("utf-8")  # strict: a lone surrogate cannot be serialized or hashed
    except (ValueError, TypeError, RecursionError) as e:
        refuse("input_contract_violation", f"base_messages: {type(e).__name__}: {e}")
    answer = inputs["initial_answer"]
    if type(status) is not str or status not in RESPONSE_STATUSES:
        refuse("input_contract_violation", "initial_response_status must be exactly 'completed' or 'unavailable'")
    if status == "unavailable":
        if answer is not None:
            refuse("input_contract_violation", "initial_response_status 'unavailable' requires initial_answer null")
        refuse("initial_receiver_failure_without_artifact", "initial transport unavailable: no saved initial artifact, no prompt")
    if type(answer) is not str:  # completed: any string, including "", is an observed artifact
        refuse("input_contract_violation", "initial_response_status 'completed' requires a string initial_answer")
    try:
        answer.encode("utf-8")
    except UnicodeEncodeError as e:
        refuse("input_contract_violation", f"initial_answer is not valid UTF-8 text: {e}")
    for key in ("root_id", "entry_point", "initial_answer_sha256"):
        if not isinstance(inputs[key], str):
            refuse("input_contract_violation", f"{key} must be a string")
        try:
            inputs[key].encode("utf-8")
        except UnicodeEncodeError as e:
            refuse("input_contract_violation", f"{key} is not valid UTF-8 text: {e}")
    if not isinstance(raw, (str, bytes)) or not raw:
        refuse("malformed_or_empty_diagnostic", "empty or non-text diagnostic")
    try:
        diag = dg.strict_json_loads(raw)  # duplicate keys at any depth are refused
    except (ValueError, RecursionError) as e:  # includes UnicodeDecodeError; excessive nesting is a structured refusal
        refuse("malformed_or_empty_diagnostic", f"{type(e).__name__}: {e}")
    if not isinstance(diag, dict) or not isinstance(diag.get("cases"), list) or not diag["cases"]:
        refuse("malformed_or_empty_diagnostic", "diagnostic must be an object with a nonempty case list")
    ids = [c.get("case_id") if isinstance(c, dict) else None for c in diag["cases"]]
    if not all(type(x) is str and x for x in ids):
        refuse("malformed_or_empty_diagnostic", "every case_id must be a nonempty string")
    if len(ids) != len(set(ids)):
        refuse("malformed_or_empty_diagnostic", "duplicate diagnostic case_id")
    overflow = None  # the validator checks its cap last; an overflow is held until every binding has been checked
    try:
        dg.validate_diagnostic(diag)  # exact keys, bounded values, schema/content
    except dg.DiagnosticOverflow as e:
        overflow = str(e)
    except (ValueError, TypeError, RecursionError) as e:  # includes UnicodeEncodeError from lone surrogates
        refuse("malformed_or_empty_diagnostic", f"{type(e).__name__}: {e}")
    try:
        dg.validate_diagnostic(diag, inputs["entry_point"], inputs["public_cases"])  # fixed ordered public skeleton
    except dg.DiagnosticOverflow as e:
        overflow = str(e)
    except (ValueError, TypeError, RecursionError) as e:
        refuse("public_binding_mismatch", f"{type(e).__name__}: {e}")
    if diag["root_id"] != inputs["root_id"]:
        refuse("public_binding_mismatch", "diagnostic root_id differs from the checkpoint root_id")
    if not (inputs["initial_answer_sha256"] == diag["initial_artifact_sha256"] == sha256_text(answer)):
        refuse("artifact_binding_mismatch", "initial-answer SHA256 (raw UTF-8 bytes) does not match the diagnostic artifact hash")
    if overflow is not None:  # bound but oversized: no prompt, no common outcome, no STOP decision
        refuse("oversized_serialization", overflow)
    prefix = [*base, {"role": "assistant", "content": answer}, dg.diagnostic_message(diag),
              {"role": "user", "content": COMMON_CAVEAT}]
    arms = {a: [*[dict(m) for m in prefix], {"role": "user", "content": RECIPES[a] + "\n\n" + TERMINAL_OUTPUT_CONTRACT}]
            for a in ACTIONS}
    return {"version": VERSION, "root_id": diag["root_id"], "initial_response_status": status, "support": _support(diag),
            "arms": arms, "prefix_sha256": messages_sha256(prefix), "arm_sha256": {a: messages_sha256(m) for a, m in arms.items()}}


def load_config(path=CONFIG_PATH) -> dict:
    cfg = dg.strict_json_loads(Path(path).read_bytes())
    for name, text in (("PATCH", PATCH), ("RETHINK", RETHINK), ("COMMON_CAVEAT", COMMON_CAVEAT),
                       ("TERMINAL_OUTPUT_CONTRACT", TERMINAL_OUTPUT_CONTRACT)):
        entry = cfg["strings"][name]
        if entry["text"] != text or entry["sha256"] != sha256_text(text):
            raise ValueError(f"config string {name} differs from the module constant")
    if cfg["collection"] != "unreleased" or cfg["status"] != "source_only" or cfg["experimental_calls_authorized"] != 0:
        raise ValueError("config must be source_only with collection unreleased and zero authorized experimental calls")
    return cfg


# ---- synthetic-only fixtures (never a real task roster, seed table or assignment) ----

TOY_ENTRY_POINT = "toy_increment"
TOY_CASES = [{"case_id": f"toy-{i}", "args_literal": f"[{a}]", "expected_literal": str(a + 1)} for i, a in enumerate((1, 2, 5), 1)]
TOY_BASE = [{"role": "system", "content": "SYNTHETIC FIXTURE: not a real task."},
            {"role": "user", "content": "Task:\nWrite toy_increment(x) returning x + 1.\n\nPublic information:\nsynthetic"}]
TOY_ANSWER = "def toy_increment(x):\n    return x + 1\n"


def _result(status, case):
    if status in ("pass", "wrong_value"):
        value = int(case["expected_literal"]) + (0 if status == "pass" else 7)
        return {"status": status, "returned": repr(value), "value_kind": "literal", "reason": None}
    return {"status": status, "returned": None, "value_kind": "none",
            "reason": "protocol_integrity_review" if status == "unavailable" else None}


TOY_PATTERNS = {  # every one of the eight statuses, all-pass, and mixed failure/incomplete records (as in v1)
    "all_pass": ("pass", "pass", "pass"), "wrong_value": ("pass", "wrong_value", "pass"),
    "format_error": ("format_error", "pass", "pass"), "interface_error": ("interface_error", "pass", "pass"),
    "program_exception": ("pass", "pass", "program_exception"), "timeout": ("pass", "timeout", "pass"),
    "unavailable": ("unavailable", "pass", "pass"), "output_limit": ("pass", "pass", "output_limit"),
    "mixed_failure_incomplete": ("wrong_value", "timeout", "pass"),
    "mixed_all_nonpass": ("program_exception", "unavailable", "output_limit"),
}


def toy_checkpoint(pattern: str, answer: str = TOY_ANSWER, results=None) -> dict:
    """A completed synthetic checkpoint. `results` may override the per-case results (e.g. the empty-artifact
    format_error record that the public checker's static gate produces without any runner call)."""
    root = f"synthetic/toy-{pattern}"
    if results is None:
        results = [_result(s, c) for s, c in zip(TOY_PATTERNS[pattern], TOY_CASES)]
    diag = dg.build_diagnostic(root, sha256_text(answer), TOY_ENTRY_POINT, TOY_CASES, results, schema=dg.SCHEMA_V2)
    return {"root_id": root, "base_messages": [dict(m) for m in TOY_BASE], "initial_response_status": "completed",
            "initial_answer": answer, "initial_answer_sha256": sha256_text(answer),
            "diagnostic_json": json.dumps(diag, sort_keys=True), "entry_point": TOY_ENTRY_POINT,
            "public_cases": [dict(c) for c in TOY_CASES]}
