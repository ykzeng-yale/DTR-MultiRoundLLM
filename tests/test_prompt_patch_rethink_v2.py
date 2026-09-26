"""MRL-32 deterministic source fixtures for the v2 PATCH/RETHINK renderer (LEAD-MEASUREMENT-03). Synthetic toy histories
only: no benchmark, model, candidate or reference program runs; the public checker is given a runner that records any
call, and none may happen."""
import ast
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from experiments.landmark import diagnostic as dg
from experiments.landmark import public_check as pc
from experiments.prompt_choice import patch_rethink as v1
from experiments.prompt_choice import patch_rethink_v2 as v2

ROOT = Path(__file__).resolve().parents[1]
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def as_v1(inputs):
    return {k: v for k, v in inputs.items() if k != "initial_response_status"}


def refusal(inputs, module=v2):
    with pytest.raises(module.InvalidCheckpoint) as e:
        module.render(inputs)
    return e.value


def empty_checkpoint():
    calls = []
    results = pc.check_artifact("", v2.TOY_ENTRY_POINT, v2.TOY_CASES, lambda *a, **k: calls.append(a) or {}, "0" * 32, display="v2")
    assert calls == []  # the static gate decides an empty artifact before any runner call
    return v2.toy_checkpoint("empty", answer="", results=results)


def test_config_pins_contract_strings_dependency_and_limits():
    cfg = v2.load_config()
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "2e39db7:docs/policy_renderer_v2_contract_20260926.md"],
                          capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == cfg["lead_contract"]["sha256"]
    assert cfg["version"] == v2.VERSION == "patch-rethink-source-v2"
    assert cfg["status"] == "source_only" and cfg["collection"] == "unreleased" and cfg["experimental_calls_authorized"] == 0
    assert cfg["strings"] == v1.load_config()["strings"]
    for name in ("PATCH", "RETHINK", "COMMON_CAVEAT", "TERMINAL_OUTPUT_CONTRACT"):
        assert getattr(v2, name) == getattr(v1, name) and cfg["strings"][name]["sha256"] == v2.sha256_text(getattr(v2, name))
    dep = cfg["pinned_dependency"]
    assert hashlib.sha256((ROOT / dep["path"]).read_bytes()).hexdigest() == dep["sha256"]
    for path, want in cfg["v1_preserved_not_a_dependency"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == want
    assert cfg["invalid_checkpoint_dispositions"] == list(v2.INVALID_DISPOSITIONS) == list(v1.INVALID_DISPOSITIONS)


def test_source_has_no_network_subprocess_execution_dispatch_or_v1_import():
    tree = ast.parse((ROOT / "experiments/prompt_choice/patch_rethink_v2.py").read_text())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert mods == {"__future__", "hashlib", "json", "pathlib", "experiments.landmark"}
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert names == {"annotations", "Path", "diagnostic"}
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, (ast.Name, ast.Attribute))}
    assert not called & {"eval", "exec", "compile", "system", "Popen", "run", "urlopen", "run_program", "check_artifact", "__import__"}
    assert "collect" not in {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def test_completed_empty_artifact_is_an_observed_history_with_both_recipes():
    inputs = empty_checkpoint()
    before = copy.deepcopy(inputs)
    out = v2.render(inputs)
    assert inputs == before and inputs["initial_answer_sha256"] == EMPTY_SHA == v2.sha256_text("")
    assert json.loads(inputs["diagnostic_json"])["initial_artifact_sha256"] == EMPTY_SHA
    for a in v2.ACTIONS:
        assistant = out["arms"][a][2]
        assert assistant == {"role": "assistant", "content": ""}  # exact, not stripped, dropped, STOP or missing
    assert out["support"]["aggregate"] == "PAYLOAD_FAILURE" and out["support"]["has_payload_failure"]
    assert not out["support"]["has_incomplete"] and out["support"]["actions"] == ["PATCH", "RETHINK"]
    assert [s for _, s, _ in out["support"]["case_statuses"]] == ["format_error"] * 3
    assert out["initial_response_status"] == "completed"
    assert refusal(as_v1(inputs), v1).disposition == "initial_receiver_failure_without_artifact"  # the historical conflation


def test_unavailable_transport_is_refused_without_prompt_and_retains_the_record():
    inputs = v2.toy_checkpoint("all_pass")
    inputs.update(initial_response_status="unavailable", initial_answer=None)
    e = refusal(inputs)
    assert e.disposition == "initial_receiver_failure_without_artifact"
    assert e.record["diagnostic_json"] is inputs["diagnostic_json"] and e.record["initial_response_status"] == "unavailable"
    attested = dict(inputs, checkpoint_attestation={"disposition": "initial_receiver_failure_without_artifact",
                                                    "reason": "transport log: connection reset"})
    e = refusal(attested)
    assert e.disposition == "initial_receiver_failure_without_artifact" and e.record["reason"] == "transport log: connection reset"


@pytest.mark.parametrize("status,answer", [
    ("unavailable", ""), ("unavailable", "def f(): pass"),       # unavailable with any string
    ("completed", None), ("completed", 0), ("completed", b""),   # completed without a string
    ("COMPLETED", ""), ("timeout", None), (True, ""), (None, ""), (["completed"], ""),
])
def test_contradictory_or_unknown_transport_statuses_are_input_contract_violations(status, answer):
    inputs = empty_checkpoint()
    inputs.update(initial_response_status=status, initial_answer=answer)
    e = refusal(inputs)
    assert e.disposition == "input_contract_violation" and e.record["diagnostic_json"] is inputs["diagnostic_json"]


def test_missing_transport_status_is_refused():
    inputs = v2.toy_checkpoint("all_pass")
    del inputs["initial_response_status"]
    assert refusal(inputs).disposition == "input_contract_violation"


def v1_schema_checkpoint():
    root, ans = "synthetic/toy-v1-schema", "def toy_increment(x):\n    return x + 1  # é ✓\n"
    results = [{"status": "pass", "returned": int(c["expected_literal"]), "value_kind": "int", "reason": None} for c in v2.TOY_CASES]
    diag = dg.build_diagnostic(root, v2.sha256_text(ans), v2.TOY_ENTRY_POINT, v2.TOY_CASES, results)
    return {"root_id": root, "base_messages": [dict(m) for m in v2.TOY_BASE], "initial_response_status": "completed",
            "initial_answer": ans, "initial_answer_sha256": v2.sha256_text(ans), "diagnostic_json": json.dumps(diag),
            "entry_point": v2.TOY_ENTRY_POINT, "public_cases": [dict(c) for c in v2.TOY_CASES]}


PARITY = [*sorted(v2.TOY_PATTERNS), "v1_schema_unicode"]


@pytest.mark.parametrize("pattern", PARITY)
def test_every_previously_valid_history_renders_byte_identical_to_v1(pattern):
    inputs = v1_schema_checkpoint() if pattern == "v1_schema_unicode" else v2.toy_checkpoint(pattern)
    before = copy.deepcopy(inputs)
    new, old = v2.render(inputs), v1.render(as_v1(inputs))
    assert inputs == before
    for a in v2.ACTIONS:
        enc = lambda ms: json.dumps(ms, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        assert enc(new["arms"][a]) == enc(old["arms"][a])
        assert [m["content"].encode("utf-8") for m in new["arms"][a]] == [m["content"].encode("utf-8") for m in old["arms"][a]]
    assert (new["prefix_sha256"], new["arm_sha256"], new["support"], new["root_id"]) == \
           (old["prefix_sha256"], old["arm_sha256"], old["support"], old["root_id"])
    prefix = new["arms"]["PATCH"][:-1]
    assert prefix == new["arms"]["RETHINK"][:-1]
    assert new["prefix_sha256"] == hashlib.sha256(json.dumps(prefix, sort_keys=True, separators=(",", ":"),
                                                             ensure_ascii=False).encode("utf-8")).hexdigest()
    for a, text in (("PATCH", v1.PATCH), ("RETHINK", v1.RETHINK)):
        assert new["arms"][a][-1] == {"role": "user", "content": text + "\n\n" + v1.TERMINAL_OUTPUT_CONTRACT}
    assert new["arms"]["PATCH"][4] == {"role": "user", "content": v1.COMMON_CAVEAT}


@pytest.mark.parametrize("pattern", sorted(v2.TOY_PATTERNS))
def test_all_eight_statuses_and_mixed_states_keep_the_tri_state_law(pattern):
    statuses = v2.TOY_PATTERNS[pattern]
    sup = v2.render(v2.toy_checkpoint(pattern))["support"]
    assert sup["has_incomplete"] == any(s in v2.INCOMPLETE for s in statuses)
    assert sup["has_payload_failure"] == any(s in v2.PAYLOAD_FAILURES for s in statuses)
    assert sup["aggregate"] == ("PASS" if set(statuses) == {"pass"} else "INCOMPLETE" if sup["has_incomplete"] else "PAYLOAD_FAILURE")
    assert sup["actions"] == ["PATCH", "RETHINK"]
    assert {s for p in v2.TOY_PATTERNS.values() for s in p} == set(dg.STATUSES)


# ---- binding before overflow: six synthetic public cases whose schema-valid wrong_value rows exceed the 2048-byte cap ----
BIG_CASES = [{"case_id": f"big-{i}", "args_literal": f"[{i}]", "expected_literal": str(i + 1)} for i in range(6)]
BIG_RETURN = repr("\U0001d518" * 99)  # 398 UTF-8 bytes: inside the per-value display policy


def oversized_checkpoint():
    root, ans = "synthetic/toy-oversized", "def toy_increment(x):\n    return 'x' * 99\n"
    rows = [{"case_id": cid, "call": call, "expected": exp, "status": "wrong_value", "returned": BIG_RETURN,
             "value_kind": "literal", "reason": None} for cid, call, exp in dg.public_skeleton(v2.TOY_ENTRY_POINT, BIG_CASES, dg.SCHEMA_V2)]
    diag = {"schema_version": dg.SCHEMA_V2, "root_id": root, "initial_artifact_sha256": v2.sha256_text(ans), "cases": rows}
    with pytest.raises(dg.DiagnosticOverflow):  # genuinely bound: schema, skeleton, root and artifact all valid; only the cap fails
        dg.validate_diagnostic(diag, v2.TOY_ENTRY_POINT, BIG_CASES)
    return {"root_id": root, "base_messages": [dict(m) for m in v2.TOY_BASE], "initial_response_status": "completed",
            "initial_answer": ans, "initial_answer_sha256": v2.sha256_text(ans), "diagnostic_json": json.dumps(diag),
            "entry_point": v2.TOY_ENTRY_POINT, "public_cases": [dict(c) for c in BIG_CASES]}


def test_genuinely_bound_overflow_is_refused_without_prompt_fallback_or_stop():
    inputs = oversized_checkpoint()
    e = refusal(inputs)
    assert e.disposition == "oversized_serialization" and e.record["diagnostic_json"] is inputs["diagnostic_json"]
    assert refusal(as_v1(inputs), v1).disposition == "oversized_serialization"


def _wrong_root(d): d["root_id"] = "synthetic/other-root"
def _wrong_hash(d): d["initial_answer"] = "def toy_increment(x):\n    return x + 2\n"; d["initial_answer_sha256"] = v2.sha256_text(d["initial_answer"])
def _wrong_supplied_hash(d): d["initial_answer_sha256"] = EMPTY_SHA
def _wrong_skeleton_value(d): d["public_cases"][0]["expected_literal"] = "99"
def _wrong_skeleton_order(d): d["public_cases"] = d["public_cases"][::-1]
def _wrong_skeleton_count(d): d["public_cases"] = d["public_cases"][:5]
def _wrong_entry_point(d): d["entry_point"] = "other_name"


@pytest.mark.parametrize("mutate,want", [
    (_wrong_root, "public_binding_mismatch"), (_wrong_hash, "artifact_binding_mismatch"),
    (_wrong_supplied_hash, "artifact_binding_mismatch"), (_wrong_skeleton_value, "public_binding_mismatch"),
    (_wrong_skeleton_order, "public_binding_mismatch"), (_wrong_skeleton_count, "public_binding_mismatch"),
    (_wrong_entry_point, "public_binding_mismatch"),
])
def test_mismatched_and_oversized_record_is_a_binding_error_not_trustworthy_overflow(mutate, want):
    inputs = oversized_checkpoint()
    mutate(inputs)
    before = copy.deepcopy(inputs)
    e = refusal(inputs)
    assert e.disposition == want and e.record["diagnostic_json"] is inputs["diagnostic_json"] and inputs == before
    assert refusal(as_v1(inputs), v1).disposition == "oversized_serialization"  # the deliberate versioned change


def test_malformed_and_oversized_record_is_malformed():
    inputs = oversized_checkpoint()
    diag = json.loads(inputs["diagnostic_json"])
    diag["private_note"] = "x"
    inputs["diagnostic_json"] = json.dumps(diag)
    assert refusal(inputs).disposition == "malformed_or_empty_diagnostic"


def _bad_utf8_diag(d): d["diagnostic_json"] = b'{"schema_version": "\xff"}'
def _dup_key_diag(d): d["diagnostic_json"] = d["diagnostic_json"].replace('{"cases"', '{"root_id": "x", "cases"', 1)
def _dup_case(d):
    diag = json.loads(d["diagnostic_json"]); diag["cases"][1]["case_id"] = diag["cases"][0]["case_id"]; d["diagnostic_json"] = json.dumps(diag)
def _extra_field(d): d["extra"] = 1
def _private_field(d): d["private_tests"] = ["assert f(1) == 2"]
def _surrogate_answer(d): d["initial_answer"] = "\ud800"
def _surrogate_root(d): d["root_id"] = "\ud800"
def _bad_base(d): d["base_messages"] = d["base_messages"][:1]
def _empty_diag(d): d["diagnostic_json"] = ""
def _attested_breach(d): d["checkpoint_attestation"] = {"disposition": "integrity_breach", "reason": "sandbox attestation failed"}
def _bad_attestation(d): d["checkpoint_attestation"] = {"disposition": "trusted", "reason": None}


@pytest.mark.parametrize("mutate,want", [
    (_bad_utf8_diag, "malformed_or_empty_diagnostic"), (_dup_key_diag, "malformed_or_empty_diagnostic"),
    (_dup_case, "malformed_or_empty_diagnostic"), (_extra_field, "input_contract_violation"),
    (_private_field, "input_contract_violation"), (_surrogate_answer, "input_contract_violation"),
    (_surrogate_root, "input_contract_violation"), (_bad_base, "input_contract_violation"),
    (_empty_diag, "malformed_or_empty_diagnostic"), (_attested_breach, "integrity_breach"),
    (_bad_attestation, "input_contract_violation"),
])
@pytest.mark.parametrize("source", ["empty", "all_pass"])
def test_strict_refusals_keep_the_original_record(mutate, want, source):
    inputs = empty_checkpoint() if source == "empty" else v2.toy_checkpoint("all_pass")
    mutate(inputs)
    before = copy.deepcopy(inputs)
    e = refusal(inputs)
    assert e.disposition == want and inputs == before
    assert e.record["diagnostic_json"] is inputs.get("diagnostic_json")
    assert e.record["initial_response_status"] == "completed"
    if mutate is _attested_breach:
        assert e.record["reason"] == "sandbox attestation failed"
    if source == "all_pass" and mutate not in (_surrogate_answer,):  # v1 classifies the same non-overflow refusals identically
        assert refusal(as_v1(inputs), v1).disposition == want
