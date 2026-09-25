"""Tests for the E14 ten-root versioned measurement package.

EVIDENCE CLASS: static/source checks on committed bytes. These tests parse, compile and hack_gate the
package's reference and control source; they NEVER execute a reference, control, candidate, public check or
containment program, and they make no model or receiver call. Predicted control failures in
controls_rationale.json are the builder's declared hand traces; these tests check their internal consistency
and that each control is predicted to fail at least one declared private assertion -- not that it does.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common.integrity import hack_gate  # noqa: E402
from experiments.landmark import grade  # noqa: E402
from experiments.landmark.collect import digest, file_sha  # noqa: E402
from scripts import build_e14_release as b  # noqa: E402

RELEASE = ROOT / "experiments/landmark/e14_release"
ROSTER = (911, 667, 344, 524, 814, 187, 194, 356, 366, 302)
ROOT_IDS = tuple(f"mbpp/{t}" for t in ROSTER)
SOURCE_PRESENT = any((ROOT / p).is_file() for p in (b.DEFAULT_SOURCE_FILE, b.ALT_SOURCE_FILE))
needs_source = pytest.mark.skipif(not SOURCE_PRESENT, reason="pinned MBPP source cache absent (work/ is gitignored); acquire and verify it with docs/mbpp_source_acquisition_20260925.md. A skip does NOT reproduce the committed package")


def _lines(name):
    return [json.loads(x) for x in (RELEASE / name).read_text(encoding="utf-8").splitlines() if x.strip()]


@pytest.fixture(scope="module")
def tasks():
    return _lines("tasks.jsonl")


@pytest.fixture(scope="module")
def specs():
    return _lines("private_specs.jsonl")


@pytest.fixture(scope="module")
def manifest():
    return json.loads((RELEASE / "release_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def controls():
    return json.loads((RELEASE / "controls_rationale.json").read_text(encoding="utf-8"))["controls"]


@pytest.fixture(scope="module")
def spec_json():
    return json.loads((ROOT / b.DEFAULT_SPEC).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ package presence and roster order
def test_package_files_present_and_pinned(manifest):
    assert sorted(p.name for p in RELEASE.iterdir()) == sorted(b.PACKAGE_FILES + ("release_manifest.json",))
    for name in b.PACKAGE_FILES:
        assert manifest["package"][name] == file_sha(RELEASE / name), name


def test_roster_order_is_exactly_the_lead_order(tasks, specs, manifest, spec_json):
    assert [t["root_id"] for t in tasks] == list(ROOT_IDS)
    assert [s["root_id"] for s in specs] == list(ROOT_IDS)
    assert manifest["roster_order"] == list(ROSTER) == spec_json["candidate_roster_order"]
    assert manifest["held_ids_unchanged"] == spec_json["held_ids_unchanged"] == list(b.HELD_IDS)


# ------------------------------------------------------------------ determinism against the committed bytes
@needs_source
def test_rebuild_is_deterministic_and_equals_committed_bytes():
    with tempfile.TemporaryDirectory() as tmp:
        one, two = Path(tmp) / "a", Path(tmp) / "bb"
        b.build(one)
        b.build(two)
        names = sorted(p.name for p in one.iterdir())
        assert names == sorted(p.name for p in two.iterdir())
        for name in names:
            fresh = (one / name).read_bytes()
            assert fresh == (two / name).read_bytes(), f"{name} is not deterministic"
            assert fresh == (RELEASE / name).read_bytes(), f"{name} differs from the committed bytes"


@needs_source
def test_verify_entrypoint_passes_on_the_committed_package():
    assert b.verify(RELEASE)["verified"] is True


def test_builder_refuses_to_overwrite():
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        b.build(RELEASE)


# ------------------------------------------------------------------ public/private boundary
def test_public_tasks_carry_only_public_fields(tasks):
    for t in tasks:
        assert set(t) == {"root_id", "prompt", "public_context"}, t["root_id"]
        assert "assert" not in t["prompt"] and "assert" not in t["public_context"]
        assert "Required function interface: def " in t["public_context"]


def test_public_bytes_contain_no_private_assertion_reference_or_control_text(tasks, specs):
    public = re.sub(r"\s+", "", (RELEASE / "tasks.jsonl").read_text(encoding="utf-8")
                    + (RELEASE / "public_examples_v3.json").read_text(encoding="utf-8"))
    for s in specs:
        private = list(s["private_assertions"]) + [s["reference_code"]] \
            + [c["code"] for c in s["negative_controls"]]
        for text in private:
            needle = re.sub(r"\s+", "", text)
            assert needle and needle not in public, f"{s['root_id']} leaked: {text[:70]!r}"


def test_public_example_is_the_single_original_index_zero_case(tasks):
    cases = json.loads((RELEASE / "public_examples_v3.json").read_text(encoding="utf-8"))["cases"]
    assert [c["root_id"] for c in cases] == list(ROOT_IDS)
    for case, task in zip(cases, tasks):
        assert len(case["cases"]) == 1
        rendered = f"{case['entry_point']}({case['cases'][0]['args_literal'][1:-1]}) == " \
                   f"{case['cases'][0]['expected_literal']}"
        assert rendered in task["public_context"], case["root_id"]


def test_lead_spec_is_never_embedded_wholesale(manifest):
    blob = "".join((RELEASE / n).read_text(encoding="utf-8") for n in b.PACKAGE_FILES)
    for field in manifest["lead_specification"]["scorer_only_fields"]:
        assert field not in json.loads((RELEASE / "tasks.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert '"records"' not in blob
    assert manifest["lead_specification"]["never_passed_to_a_prompt"] is True


# ------------------------------------------------------------------ grading contract
def test_validate_specs_passes(tasks, specs):
    grade.validate_specs(tasks, specs)


def test_spec_keys_and_public_task_binding(tasks, specs):
    by_root = {t["root_id"]: t for t in tasks}
    for s in specs:
        assert set(s) == grade.SPEC_KEYS, s["root_id"]
        assert s["public_task_sha256"] == digest(by_root[s["root_id"]])
        assert s["preamble"] == []
        assert len(s["public_assertions"]) == 1
        assert len(s["negative_controls"]) == 2


def test_grading_limits_load_and_authorize_no_execution(manifest, specs):
    from experiments.landmark import study_adapter as sa
    limits = sa.load_grading_limits(json.dumps(manifest).encode("utf-8"), specs)
    assert limits["source"] == "grading_limits"
    assert limits["artifact_starts"] == 140 and limits["recheck_starts"] == 30
    assert limits["containment_starts"] == 18 and limits["max_private_starts"] == 188


# ------------------------------------------------------------------ retained + added assertions
@needs_source
def test_retained_and_added_assertions_match_the_lead_json_exactly(specs, spec_json):
    rows, records = {}, {r["task_id"]: r for r in spec_json["records"]}
    source_sha = spec_json["source_file_sha256"]
    path = next(p for p in (ROOT / b.DEFAULT_SOURCE_FILE, ROOT / b.ALT_SOURCE_FILE) if p.is_file())
    assert file_sha(path) == source_sha
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rec = json.loads(raw)
            if rec.get("task_id") in ROSTER:
                rows[rec["task_id"]] = rec
    for tid, s in zip(ROSTER, specs):
        retained = [rows[tid]["test_list"][i] for i in (1, 2)]
        added = records[tid]["added_private_assertions"]
        assert s["private_assertions"] == retained + added, tid
        assert s["public_assertions"] == [rows[tid]["test_list"][0]], tid


def test_source_hashes_verified_per_record(manifest, spec_json):
    records = {r["task_id"]: r for r in spec_json["records"]}
    per_root = manifest["source_pins"]["per_root"]
    assert manifest["source_pins"]["file_sha256"] == spec_json["source_file_sha256"]
    assert manifest["source_pins"]["verified_before_reading"] is True
    for tid in ROSTER:
        pins = per_root[f"mbpp/{tid}"]
        for key in ("source_text_sha256", "source_reference_sha256", "source_assertions_sha256"):
            assert pins[key] == records[tid][key], (tid, key)


def test_lead_spec_sha256_is_pinned(manifest):
    assert manifest["lead_specification"]["sha256"] == file_sha(ROOT / b.DEFAULT_SPEC)
    assert manifest["lead_specification"]["execution_authorized"] is False


# ------------------------------------------------------------------ static validity of references and controls
@pytest.mark.parametrize("tid", ROSTER)
def test_reference_and_both_controls_parse_compile_and_pass_hack_gate(tid, specs, manifest):
    spec = next(s for s in specs if s["root_id"] == f"mbpp/{tid}")
    entry = spec["entry_point"]
    programs = [("reference", spec["reference_code"])] \
        + [(f"control_{i}", c["code"]) for i, c in enumerate(spec["negative_controls"])]
    assert len(programs) == 3
    for label, code in programs:
        tree = ast.parse(code)
        compile(code, f"<test:{tid}:{label}>", "exec", dont_inherit=True)
        assert entry in [n.name for n in tree.body if isinstance(n, ast.FunctionDef)], (tid, label)
        assert hack_gate(code, entry) == [], (tid, label)
    static = manifest["per_root"][f"mbpp/{tid}"]["static_validation"]
    for key in ("reference", "semantic_control", "none_control"):
        assert static[key]["hack_gate_clean"] is True and static[key]["executed"] is False


@pytest.mark.parametrize("tid", ROSTER)
def test_second_control_is_correctly_interfaced_and_always_none(tid, specs):
    spec = next(s for s in specs if s["root_id"] == f"mbpp/{tid}")
    code = spec["negative_controls"][1]["code"]
    fn = ast.parse(code).body[0]
    assert isinstance(fn, ast.FunctionDef) and fn.name == spec["entry_point"]
    assert len(fn.body) == 1 and isinstance(fn.body[0], ast.Return)
    assert isinstance(fn.body[0].value, ast.Constant) and fn.body[0].value.value is None
    ref_args = ast.unparse(next(n for n in ast.parse(spec["reference_code"]).body
                                if isinstance(n, ast.FunctionDef) and n.name == spec["entry_point"]).args)
    assert ast.unparse(fn.args) == ref_args, tid


@pytest.mark.parametrize("tid", ROSTER)
def test_versioned_reference_honours_the_lead_requirement(tid, specs):
    code = next(s for s in specs if s["root_id"] == f"mbpp/{tid}")["reference_code"]
    if tid == 344:
        assert "math.isqrt(m) - math.isqrt(n - 1)" in code and "0.5" not in code
    elif tid == 187:
        assert "table" in code and "longest_common_subsequence(X, Y" not in code.split("def ", 1)[1][20:]
        assert "for i in range(1, m + 1)" in code
    elif tid == 194:
        assert "temp // 10" in code and "int(temp / 10)" not in code
    elif tid == 302:
        assert code.count("n // 2") == 2 and "int(n / 2)" not in code and "return 1 << msb" in code
    elif tid == 814:
        assert "(p * q) / 2" in code and "//" not in code
    elif tid == 911:
        assert "heapq.nlargest(3, nums)" in code and "heapq.nsmallest(2, nums)" in code
    elif tid == 524:
        assert "arr[i] > arr[j]" in code and ">=" not in code


# ------------------------------------------------------------------ controls rationale
def test_each_root_has_two_controls_with_a_named_fault_and_a_predicted_failing_assertion(controls, specs):
    assert len(controls) == 2 * len(ROSTER)
    by_root = {}
    for c in controls:
        by_root.setdefault(c["root_id"], []).append(c)
    for s in specs:
        got = by_root[s["root_id"]]
        assert [c["control"] for c in got] == ["semantic", "always_none"], s["root_id"]
        n_private = len(s["private_assertions"])
        for c in got:
            assert c["fault"].strip() and c["expected_failure_reasoning"].strip()
            assert c["requirement"].strip()
            assert len(c["private_cases"]) == n_private
            assert [x["assertion"] for x in c["private_cases"]] == s["private_assertions"]
            n_fail = sum(1 for x in c["private_cases"] if x["predicted_fails"])
            assert n_fail == c["predicted_failing_private_assertions"] >= 1, (s["root_id"], c["control"])
            assert "NEVER executed" in c["method"]
        assert got[1]["predicted_failing_private_assertions"] == n_private


def test_predicted_failure_flags_are_internally_consistent(controls):
    for c in controls:
        for case in c["private_cases"]:
            expected = ast.literal_eval(case["expected"])
            predicted = ast.literal_eval(case["predicted_control_return"])
            assert case["predicted_fails"] == (predicted != expected), (c["root_id"], case["assertion"])


# ------------------------------------------------------------------ domain binding
def test_every_assertion_is_bound_to_the_declared_public_domain(manifest, specs):
    for s in specs:
        root = manifest["per_root"][s["root_id"]]
        bound = {x["assertion"] for x in root["assertion_domain_bindings"]}
        assert bound == set(s["public_assertions"]) | set(s["private_assertions"]), s["root_id"]
        for x in root["assertion_domain_bindings"]:
            assert x["in_declared_public_domain"] is True
            assert x["domain_rule"] == root["declared_public_domain"]
            assert x["entry_point"] == s["entry_point"]
        kinds = [x["kind"] for x in root["assertion_domain_bindings"]]
        assert kinds.count("public_source_index_0") == 1
        assert sorted(k for k in kinds if k.startswith("private_retained")) == \
            ["private_retained_source_index_1", "private_retained_source_index_2"]


def test_an_out_of_domain_assertion_is_refused():
    rule, predicate = b.DOMAINS[302]
    assert predicate((16,)) is True
    assert predicate((0,)) is False  # the contract excludes zero
    with pytest.raises(ValueError, match="OUTSIDE the declared public domain"):
        b._bind_domain(302, "assert set_Bit_Number(0) == 0", "private_added_by_lead", "set_Bit_Number")


# ------------------------------------------------------------------ design, authorization, change notes
def test_design_fixes_all_130_slots_before_collection(manifest):
    d = manifest["design"]
    assert d["initial_calls"] == 10 and d["draws_per_arm"] == 6 and d["arms"] == ["NEUTRAL", "DIRECTED"]
    assert d["continuation_slots"] == 120 and d["call_slots"] == 130
    assert d["slots_fixed_before_collection"] is True and d["branch_inclusion_probability"] == 1
    assert any("Suppress the primary point contrast" in r for r in d["missingness_rules"])
    assert any("No normal confidence interval" in r for r in d["reporting_rules"])


def test_package_authorizes_zero_receiver_calls_and_zero_executions(manifest):
    auth = manifest["authorization"]
    for key in ("receiver_calls_authorized", "model_tokens_authorized", "candidate_executions_authorized",
                "reference_executions_authorized", "negative_control_executions_authorized",
                "benchmark_executions_authorized", "public_check_executions_authorized",
                "containment_executions_authorized", "paid_usd_authorized"):
        assert auth[key] == 0, key
    assert "authorizes NO model" in auth["statement"] and "has ever been run" in auth["statement"]
    config = json.loads((RELEASE / "config.json").read_text(encoding="utf-8"))
    assert config["e14"]["receiver_calls_authorized"] == 0
    assert config["e14"]["candidate_executions_authorized"] == 0


def test_terminal_instruction_v2_is_not_a_scoring_rule(manifest, spec_json):
    ti = manifest["terminal_instruction"]
    assert ti["label"] == "terminal-output-contract-v2" == spec_json["terminal_instruction"]["label"]
    assert ti["text"] == spec_json["terminal_instruction"]["text"]
    assert ti["is_a_scoring_rule"] is False
    assert ti["applied_to"] == "both arms, byte-identically appended"
    assert manifest["evaluator"]["grader_version"] == grade.GRADER_VERSION


def test_change_notes_record_the_version_and_the_three_exposure_facts(manifest):
    notes = (RELEASE / "CHANGE_NOTES.md").read_text(encoding="utf-8")
    assert "NEW endpoint version, not a rescoring of E12/E13" in notes
    assert "Whole-source mechanical processing" in notes
    assert "Twenty-record semantic review" in notes
    assert "No reported new model-outcome inspection" in notes
    assert "THREE SEPARATE FACTS" in notes
    for tid in b.HELD_IDS:
        assert str(tid) in notes
    assert len(manifest["source_exposure_limitations"]) == 3
    assert hashlib.sha256(notes.encode("utf-8")).hexdigest() == manifest["package"]["CHANGE_NOTES.md"]


def test_historical_packages_are_not_referenced_as_writable(manifest):
    reuse = manifest["receiver_law_source"]
    assert reuse["dir"] == "experiments/landmark/dev_release_v3"
    assert "read only and was not modified" in reuse["reuse_rule"]
    assert reuse["manifest_sha256"] == file_sha(ROOT / "experiments/landmark/dev_release_v3/release_manifest.json")


def test_build_and_verify_fail_closed_without_the_pinned_source(tmp_path, monkeypatch):
    """LEAD-PORT-01: a missing cache must stop the builder and verify, never degrade to a partial package."""
    monkeypatch.setattr(b, "DEFAULT_SOURCE_FILE", "work/port01_absent_a.jsonl")
    monkeypatch.setattr(b, "ALT_SOURCE_FILE", "work/port01_absent_b.jsonl")
    with pytest.raises(SystemExit, match="cached MBPP source not found"):
        b.build(tmp_path / "out")
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").iterdir())
    with pytest.raises(SystemExit, match="cached MBPP source not found"):
        b.verify(RELEASE)


def test_build_fails_closed_on_a_wrong_source_hash(tmp_path):
    bogus = tmp_path / "mbpp.jsonl"
    bogus.write_text('{"task_id": 1}\n')
    with pytest.raises(ValueError, match="sha256 mismatch"):
        b.build(tmp_path / "out", source_path=bogus)
