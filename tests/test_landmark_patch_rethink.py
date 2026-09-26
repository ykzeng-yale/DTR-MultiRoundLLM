"""MRL-26 source/mock checks for the PATCH/RETHINK renderer. Synthetic fixtures only; no receiver, candidate,
reference or public-check execution. These are source checks, not a model pilot."""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from experiments.landmark import diagnostic as dg
from experiments.prompt_choice import patch_rethink as pr

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "experiments/prompt_choice/patch_rethink.py"
CONTRACT = ROOT / "docs/lead_resumption_and_action_contract_20260926.md"
fsha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _quoted(label):
    """The exact quoted paragraph that follows a label (or the given quote start) in the committed lead contract."""
    lines = CONTRACT.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("> ") and label in line:
            return line[2:]
        if line.strip() == f"**{label}**":
            return next(l[2:] for l in lines[i + 1:] if l.startswith("> "))
    raise AssertionError(label)


def test_exact_constant_strings_match_the_committed_contract_and_config():
    assert pr.PATCH == _quoted("PATCH") and pr.RETHINK == _quoted("RETHINK")
    assert pr.COMMON_CAVEAT == _quoted("For any check marked timeout")
    assert pr.TERMINAL_OUTPUT_CONTRACT == _quoted("Return the complete solution as Python source")
    e14 = json.loads((ROOT / "experiments/landmark/e14_release_v2/release_manifest.json").read_text())
    assert pr.TERMINAL_OUTPUT_CONTRACT in json.dumps(e14)  # the existing terminal-output-contract-v2 text, unchanged
    cfg = pr.load_config()
    assert cfg["status"] == "source_only" and cfg["collection"] == "unreleased" and cfg["receiver_calls_authorized"] == 0
    assert cfg["source_versions"]["experiments/landmark/diagnostic.py"] == fsha(ROOT / "experiments/landmark/diagnostic.py")


@pytest.mark.parametrize("pattern", sorted(pr.TOY_PATTERNS))
def test_both_recipes_on_every_status_with_byte_identical_prefix(pattern):
    out = pr.render(pr.toy_checkpoint(pattern))
    assert list(out["arms"]) == ["PATCH", "RETHINK"] and out["support"]["actions"] == ["PATCH", "RETHINK"]
    p, r = out["arms"]["PATCH"], out["arms"]["RETHINK"]
    assert len(p) == len(r) == 6 and p[:5] == r[:5]  # identical task prefix, answer, diagnostic and caveat
    assert json.dumps(p[:5]).encode() == json.dumps(r[:5]).encode()
    assert [m["role"] for m in p] == ["system", "user", "assistant", "user", "user", "user"]
    assert p[2]["content"] == pr.TOY_ANSWER and p[4]["content"] == pr.COMMON_CAVEAT
    assert p[5]["content"] == pr.PATCH + "\n\n" + pr.TERMINAL_OUTPUT_CONTRACT
    assert r[5]["content"] == pr.RETHINK + "\n\n" + pr.TERMINAL_OUTPUT_CONTRACT
    diag = dg.strict_json_loads(pr.toy_checkpoint(pattern)["diagnostic_json"])
    assert p[3] == dg.diagnostic_message(diag)  # historical canonical serialization, byte for byte


def test_tri_state_support_keeps_mixed_failures_and_reasons():
    got = {k: pr.render(pr.toy_checkpoint(k))["support"] for k in pr.TOY_PATTERNS}
    assert got["all_pass"]["aggregate"] == "PASS" and not got["all_pass"]["has_payload_failure"]
    for k in ("wrong_value", "format_error", "interface_error", "program_exception"):
        assert got[k]["aggregate"] == "PAYLOAD_FAILURE" and got[k]["has_payload_failure"] and not got[k]["has_incomplete"]
    for k in ("timeout", "unavailable", "output_limit"):
        assert got[k]["aggregate"] == "INCOMPLETE" and got[k]["has_incomplete"] and not got[k]["has_payload_failure"]
    for k in ("mixed_failure_incomplete", "mixed_all_nonpass"):
        assert got[k]["aggregate"] == "INCOMPLETE" and got[k]["has_incomplete"] and got[k]["has_payload_failure"]
    assert ("toy-1", "unavailable", "protocol_integrity_review") in got["unavailable"]["case_statuses"]  # verbatim
    seen = {s for v in got.values() for _, s, _ in v["case_statuses"]}
    assert seen == set(dg.STATUSES)  # all eight statuses exercised


def test_support_is_not_select_s1_precedence():
    diag = dg.strict_json_loads(pr.toy_checkpoint("mixed_failure_incomplete")["diagnostic_json"])
    assert dg.select_s1(diag) == dg.S1_STRINGS[0]  # S1 would pick the payload-failure branch
    assert pr._support(diag)["aggregate"] == "INCOMPLETE"  # the new law gives INCOMPLETE precedence and keeps the failure flag


def _bad(mutate):
    inp = pr.toy_checkpoint("wrong_value")
    mutate(inp)
    return inp


def _refused(inp, disposition):
    with pytest.raises(pr.InvalidCheckpoint) as e:
        pr.render(inp)
    assert e.value.disposition == disposition, (e.value.disposition, e.value.record.get("detail"))
    assert e.value.record["diagnostic_json"] == (inp.get("diagnostic_json") if isinstance(inp, dict) else None)
    return e.value


@pytest.mark.parametrize("mutate,disposition", [
    (lambda i: i.update(private_assertions=["assert x"]), "input_contract_violation"),
    (lambda i: i.update(reference="def f(): pass"), "input_contract_violation"),
    (lambda i: i.pop("entry_point"), "input_contract_violation"),
    (lambda i: i.update(base_messages=[*i["base_messages"], {"role": "assistant", "content": "x"}]), "input_contract_violation"),
    (lambda i: i.update(base_messages=[{"role": "system", "content": "s", "private": 1}, i["base_messages"][1]]), "input_contract_violation"),
    (lambda i: i.update(checkpoint_attestation={"disposition": "made_up", "reason": "x"}), "input_contract_violation"),
    (lambda i: i.update(initial_answer_sha256="0" * 64), "artifact_binding_mismatch"),
    (lambda i: i.update(initial_answer_sha256=hashlib.sha256(json.dumps(i["initial_answer"]).encode()).hexdigest()), "artifact_binding_mismatch"),
    (lambda i: i.update(root_id="synthetic/other"), "public_binding_mismatch"),
    (lambda i: i.update(public_cases=i["public_cases"][:2]), "public_binding_mismatch"),
    (lambda i: i.update(public_cases=list(reversed(i["public_cases"]))), "public_binding_mismatch"),
])
def test_contract_violations_are_refused_with_explicit_dispositions(mutate, disposition):
    _refused(_bad(mutate), disposition)


def _with_diag(edit):
    inp = pr.toy_checkpoint("wrong_value")
    d = json.loads(inp["diagnostic_json"])
    edit(d)
    return {**inp, "diagnostic_json": json.dumps(d)}


@pytest.mark.parametrize("edit", [
    lambda d: d["cases"][1].update(case_id=d["cases"][0]["case_id"]),  # duplicate case_id
    lambda d: d["cases"][0].update(case_id=["not", "hashable"]),         # invalid case-ID type: no TypeError leak
    lambda d: d["cases"][0].update(case_id=7),
    lambda d: d["cases"][0].update(private="hidden"),                   # extra/private case field
    lambda d: d["cases"][0].update(status="made_up"),                   # unknown status
    lambda d: d.update(extra="x"),
    lambda d: d.update(cases=[1, 2, 3]),
])
def test_malformed_nonempty_diagnostics_are_explicit_rejections(edit):
    _refused(_with_diag(edit), "malformed_or_empty_diagnostic")


def test_duplicate_json_keys_are_refused_with_the_original_retained():
    inp = pr.toy_checkpoint("wrong_value")
    dup_key = inp["diagnostic_json"].replace('"root_id": ', '"root_id": "synthetic/x", "root_id": ', 1)
    _refused({**inp, "diagnostic_json": dup_key}, "malformed_or_empty_diagnostic")


def test_byte_cap_applies_to_the_canonical_message_not_transport_whitespace():
    inp = pr.toy_checkpoint("all_pass")
    padded = json.dumps(json.loads(inp["diagnostic_json"]), indent=40)  # same record, >2048 raw bytes of whitespace
    assert len(padded.encode()) > 2048
    assert pr.render({**inp, "diagnostic_json": padded})["arms"] == pr.render(inp)["arms"]
    d = json.loads(inp["diagnostic_json"])
    d["root_id"] = "synthetic/" + "r" * 1900  # the canonical message itself overflows
    _refused({**inp, "root_id": d["root_id"], "diagnostic_json": json.dumps(d)}, "oversized_serialization")


@pytest.mark.parametrize("change,disposition", [
    ({"initial_answer": None}, "initial_receiver_failure_without_artifact"),
    ({"initial_answer": ""}, "initial_receiver_failure_without_artifact"),
    ({"diagnostic_json": ""}, "malformed_or_empty_diagnostic"),
    ({"diagnostic_json": "{not json"}, "malformed_or_empty_diagnostic"),
    ({"diagnostic_json": json.dumps({"cases": []})}, "malformed_or_empty_diagnostic"),
    ({"checkpoint_attestation": {"disposition": "integrity_breach", "reason": "attested by reviewer"}}, "integrity_breach"),
])
def test_invalid_checkpoints_are_refused_before_rendering_and_keep_the_original(change, disposition):
    inp = {**pr.toy_checkpoint("unavailable"), **change}
    err = _refused(inp, disposition)
    if "checkpoint_attestation" in change:
        assert err.record["reason"] == "attested by reviewer"


@pytest.mark.parametrize("diag", [{"cases": []}, {"cases": [{"case_id": "a", "status": "made_up", "reason": None}]},
                                  {"cases": "x"}, {}, None])
def test_support_enforces_its_preconditions(diag):
    with pytest.raises(ValueError):
        pr._support(diag)
    assert not hasattr(pr, "support")  # private: only render() reaches it, after validation


def test_integrity_review_reason_alone_is_not_a_breach():
    out = pr.render(pr.toy_checkpoint("unavailable"))  # protocol_integrity_review is recorded, not treated as attested
    assert out["support"]["aggregate"] == "INCOMPLETE"


def test_planning_fixture_is_synthetic_complete_and_deterministic():
    a, b = pr.planning_fixture(3), pr.planning_fixture(3)
    assert a == b and a["synthetic_only"] is True and a["collection_enabled"] is False
    assert a["order_metadata"] == "scheduling_not_assignment" and a["treatment_propensity"] is None
    assert a["order_method"] == "deterministic_sha256_fixture_order_not_sampled_randomization"
    per = {}
    for s in a["slots"]:
        per.setdefault((s["root_id"], s["replicate"]), []).append(s["action"])
        assert s["inclusion_probability"] == 1 and s["root_id"].startswith("synthetic/toy-")
    assert len(per) == len(pr.TOY_PATTERNS) * 3 and all(sorted(v) == ["PATCH", "RETHINK"] for v in per.values())
    assert sorted(a["execution_order"]) == sorted(s["slot_id"] for s in a["slots"]) and len(set(a["execution_order"])) == len(a["slots"])
    ids = a["toy_seed_identities"]
    assert all(k.startswith("toy-seed::") for k in ids) and set(ids.values()) == {"initial", "PATCH", "RETHINK", "B2"}
    assert len(ids) == len(pr.TOY_PATTERNS) * (1 + 3 * 3)  # unique initial / B2 / PATCH / RETHINK identities


def test_module_has_no_network_subprocess_execution_or_dispatch_path():
    tree = ast.parse(MODULE.read_text())
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imported <= {"__future__", "hashlib", "json", "pathlib", "experiments"}
    froms = {(n.module, a.name) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert ("experiments.landmark", "diagnostic") in froms and not any(a == "collect" for _, a in froms)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"collect", "exec", "eval", "compile", "system", "popen", "Popen", "urlopen", "socket", "run_program",
                        "render_arms", "select_s1", "request", "post"}


def test_historical_renderer_and_result_bytes_are_unchanged():
    pins = {"experiments/landmark/diagnostic.py": "2a98bccf20cf3fa068790b488be8df4347387ae5ffb1bd7b1bd8b9d49d3a72b2",
            "results/e12_dev_v3_20260922T030255Z/B/diagnostics.json": "e95d50bae632f73a96094673a03aff9401993c5c3d986086f63c5fe3cf8bd94a",
            "results/e12_dev_v3_20260922T030255Z/analysis_report.json": "ca250a3ea3d5bfe275a202f10b58d3c26a247fba5c63798ee56aa53760eaaf8b",
            "experiments/landmark/e14_release/public_examples_v3.json": "900b97fb2f9ee7faa36920fdd44ea92841a86fbf322d01591115a07f6ce4f727"}
    for path, want in pins.items():
        assert fsha(ROOT / path) == want, path


def test_new_package_is_outside_the_historical_flat_landmark_inventory():
    from experiments.landmark import collect
    assert "patch_rethink.py" not in collect.source_hashes()  # old release identities are not changed by this package
    assert pr.CONFIG_PATH == ROOT / "experiments/prompt_choice/patch_rethink_source_v1.json"
    assert pr.load_config()["future_execution_must_pin"][0] == "experiments/prompt_choice/patch_rethink.py"
