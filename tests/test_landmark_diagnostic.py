"""Mock/source tests for the MRL-08 public diagnostic renderer and v2 release builder.

No candidate, example, reference or diagnostic text is executed; fixtures are byte goldens.
"""
import ast
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect, diagnostic as d
FIX = ROOT / "tests/fixtures/diagnostic_v1"
EXAMPLES = json.loads((ROOT / "docs/public_diagnostic_examples_v1.json").read_text())["cases"]
BY_ROOT = {r["root_id"]: r for r in EXAMPLES}
SHAS = json.loads((FIX / "SHA256SUMS.json").read_text())
A = "a" * 64
BIG = [-(10**18 - 1)] * 16
BASE = [{"role": "system", "content": "S"}, {"role": "user", "content": "T"}]


def res(status, returned=None, kind="none", reason=None):
    return {"status": status, "returned": returned, "value_kind": kind, "reason": reason}


SCENARIOS = {
    "diag_all_pass_mbpp_52": ("mbpp/52", [res("pass", 77, "int"), res("pass", 117, "int"), res("pass", 34, "int")]),
    "diag_first_wrong_value_mbpp_378": ("mbpp/378", [res("wrong_value", [7, -2, 9, 7], "int_list"), res("pass", [3, 8], "int_list"), res("pass", [11], "int_list")]),
    "diag_crash_later_unavailable_mbpp_357": ("mbpp/357", [res("pass", 9, "int"), res("program_exception"), res("unavailable", reason="not_attempted_after_termination")]),
}


def diag_for(name):
    root, results = SCENARIOS[name]
    r = BY_ROOT[root]
    return d.build_diagnostic(root, A, r["entry_point"], r["cases"], results)


def load_builder():
    spec = importlib.util.spec_from_file_location("build_dev_release_v2", ROOT / "scripts/build_dev_release_v2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # builder source only; it executes no benchmark code at import
    return mod


@pytest.mark.parametrize("root", sorted(BY_ROOT))
def test_public_examples_golden_bytes(root):
    r = BY_ROOT[root]
    name = f"public_examples_{root.replace('/', '_')}.txt"
    data = d.render_public_examples(r["entry_point"], r["cases"]).encode("utf-8")
    assert data == (FIX / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == SHAS[name]
    lines = data.decode().split("\n")
    assert lines[0] == d.EXAMPLES_HEADER and len(lines) == 4 and all(" == " in x for x in lines[1:])


def test_render_call_uses_literal_repr():
    assert d.render_call("find_max", "[[(5,), (3,8,-1)]]") == "find_max([(5,), (3, 8, -1)])"
    assert d.render_call("frequency_Of_Largest", "[5,[2,7,7,1,7]]") == "frequency_Of_Largest(5, [2, 7, 7, 1, 7])"


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_diagnostic_golden_bytes_and_sha(name):
    diag = diag_for(name)
    assert d.diagnostic_bytes(diag) == (FIX / f"{name}.json").read_bytes()
    assert hashlib.sha256(d.diagnostic_bytes(diag)).hexdigest() == SHAS[f"{name}.json"]
    msg = d.diagnostic_message(diag)
    assert msg["role"] == "user" and msg["content"].encode() == (FIX / f"{name}.message.txt").read_bytes()
    assert msg["content"].startswith(d.DIAGNOSTIC_HEADER + "\n{")
    assert [c["case_id"] for c in diag["cases"]] == [c["case_id"] for c in BY_ROOT[diag["root_id"]]["cases"]]


def test_s1_precedence():
    assert d.select_s1(diag_for("diag_all_pass_mbpp_52")) == d.S1_STRINGS[2]
    assert d.select_s1(diag_for("diag_first_wrong_value_mbpp_378")) == d.S1_STRINGS[0]
    assert d.select_s1(diag_for("diag_crash_later_unavailable_mbpp_357")) == d.S1_STRINGS[0]
    mk = lambda *s: {"cases": [{"status": x} for x in s]}
    for fail in d.PAYLOAD_FAILURES:  # a payload failure beats any incomplete case, in any position
        for inc in d.INCOMPLETE:
            assert d.select_s1(mk(inc, "pass", fail)) == d.S1_STRINGS[0]
    for inc in d.INCOMPLETE:
        assert d.select_s1(mk("pass", inc, "pass")) == d.S1_STRINGS[1]
    assert d.select_s1(mk("pass", "pass", "pass")) == d.S1_STRINGS[2]
    with pytest.raises(ValueError):
        d.select_s1(mk("pass", "unknown", "pass"))


def test_instruction_strings_verbatim_from_design_doc():
    doc = (ROOT / "docs/public_diagnostic_design_20260921.md").read_text()
    for text in (d.N_INSTRUCTION, *d.S1_STRINGS):
        assert f"> {text}\n" in doc
    assert f"`{d.R1_INSTRUCTION}`" in doc
    assert d.N_INSTRUCTION == collect.GENERIC
    assert f"`{d.DIAGNOSTIC_HEADER}`" in (ROOT / "docs/lead_review_mrl05_08_20260921.md").read_text()


def test_arms_structure_and_shared_diagnostic_bytes():
    diag = diag_for("diag_crash_later_unavailable_mbpp_357")
    answer = "def find_max(t):\n    return max(x for tup in t for x in tup)\n"
    arms = d.render_arms(BASE, answer, diag)
    assert tuple(arms) == d.ARM_IDS == ("N0", "S0", "N1", "S1", "R1")
    enc = lambda m: json.dumps(m, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert enc(arms) == (FIX / "arms_mbpp_357_crash.json").read_bytes()
    prefix = [*BASE, {"role": "assistant", "content": answer}]
    for arm in ("N0", "S0", "N1", "S1"):
        assert arms[arm][:3] == prefix
    assert enc(arms["N1"][3]) == enc(arms["S1"][3]) == enc(arms["R1"][2]) == enc(d.diagnostic_message(diag))
    assert arms["N1"][4]["content"] == arms["N0"][3]["content"] == d.N_INSTRUCTION
    assert arms["S1"][4]["content"] == d.select_s1(diag)
    assert all(m["role"] != "assistant" for m in arms["R1"])
    assert arms["R1"] == [*BASE, d.diagnostic_message(diag), {"role": "user", "content": d.R1_INSTRUCTION}]
    assert all(d.DIAGNOSTIC_HEADER not in m["content"] for arm in ("N0", "S0") for m in arms[arm])


@pytest.mark.parametrize("answer,feature", [("for x in y: pass", "loop"), ("return a / b", "division"), ("return a*b", "fallback")])
def test_s0_uses_collect_targeted_rule(answer, feature):
    arms = d.render_arms(BASE, answer, diag_for("diag_all_pass_mbpp_52"))
    assert collect.branches(BASE, answer)[1] == feature
    assert arms["S0"][-1] == {"role": "user", "content": collect.TARGETED[feature]}
    assert collect.digest(collect.TARGETED) == d.TARGETED_SHA256


def test_renderers_take_only_public_inputs():
    params = lambda f: list(inspect.signature(f).parameters)
    assert params(d.render_arms) == ["base_messages", "initial_output", "diag"]
    assert params(d.render_public_examples) == ["entry_point", "cases"]
    assert params(d.build_diagnostic) == ["root_id", "initial_artifact_sha256", "entry_point", "cases", "results"]
    tree = ast.parse(Path(d.__file__).read_text())
    imported = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert imported <= {"annotations", "ast", "json", "re", "collect"}
    assert not any(isinstance(n, ast.Call) and getattr(n.func, "id", None) in {"exec", "eval", "compile", "open"} for n in ast.walk(tree))
    r = BY_ROOT["mbpp/52"]
    with pytest.raises(ValueError):  # a private field on a case is rejected, not silently dropped
        d.render_public_examples(r["entry_point"], [{**r["cases"][0], "private_assertions": "x"}])


@pytest.mark.parametrize("bad", [
    res("pass", True, "int"), res("pass", 10**18, "int"), res("pass", [1] * 17, "int_list"), res("pass", 7.0, "int"),
    res("pass", 3, "unsupported"), res("unavailable"), res("unavailable", reason="because"), res("program_exception", reason="ZeroDivisionError"),
    res("format_error", 3, "int"), res("bogus"), {**res("pass", 1, "int"), "traceback": "x"},
])
def test_result_validation_rejects(bad):
    r = BY_ROOT["mbpp/52"]
    with pytest.raises(ValueError):
        d.build_diagnostic("mbpp/52", A, r["entry_point"], r["cases"], [bad, res("pass", 117, "int"), res("pass", 34, "int")])


def test_worst_case_size_fits_or_raises_never_truncates():
    budget = json.loads((ROOT / "results/diagnostic_byte_budget_20260921.json").read_text())
    lead = {row["root_id"]: row["bytes"] for row in budget["rows"]}
    longest_reason = max(d.UNAVAILABLE_REASONS, key=len)
    longest_status = max(d.STATUSES, key=len)
    for root, r in BY_ROOT.items():
        # Valid worst case: every case returns the maximal 16-int list; only pass/wrong_value may carry a value,
        # and wrong_value is the longer of the two.
        valid = d.build_diagnostic(root, "f" * 64, r["entry_point"], r["cases"], [res("wrong_value", BIG, "int_list")] * 3)
        # Superset envelope beyond validity: maximal list AND longest status AND longest reason in every case.
        env = {**valid, "cases": [{**c, "status": longest_status, "reason": longest_reason} for c in valid["cases"]]}
        for diag in (valid, env):
            try:
                content = d.diagnostic_message(diag)["content"].encode()
            except d.DiagnosticOverflow:
                continue
            assert len(content) <= d.MAX_DIAGNOSTIC_BYTES and content.endswith(d.diagnostic_bytes(diag))
            json.loads(d.diagnostic_bytes(diag))  # complete JSON, never truncated
        # Our schema differs from the lead's illustrative keys; both are well under the cap.
        assert abs(len(d.diagnostic_message(valid)["content"].encode()) - lead[root]) < 200
    huge = {**valid, "cases": [{**c, "call": "x" * 800} for c in valid["cases"]]}
    with pytest.raises(d.DiagnosticOverflow):
        d.diagnostic_message(huge)
    with pytest.raises(d.DiagnosticOverflow):
        d.diagnostic_bytes({**huge, "cases": huge["cases"] * 2})


def test_rebind_changes_only_public_binding():
    b = load_builder()
    tasks = b.load_jsonl(b.V1C / "tasks.jsonl")
    specs = b.load_jsonl(b.V1C / "private_specs.jsonl")
    new_tasks, new_specs = b.rebind(tasks, specs, EXAMPLES)
    b.check_against_v1c(specs, new_specs)
    for old_t, new_t, old_s, new_s, ex in zip(tasks, new_tasks, specs, new_specs, EXAMPLES):
        rendered = d.render_public_examples(ex["entry_point"], ex["cases"])
        assert new_t["public_context"] == old_t["public_context"] + "\n\n" + rendered
        assert new_t["public_context"].count(d.EXAMPLES_HEADER) == 1
        assert {k: v for k, v in new_t.items() if k != "public_context"} == {k: v for k, v in old_t.items() if k != "public_context"}
        assert new_s["public_task_sha256"] == collect.digest(new_t) != old_s["public_task_sha256"]
        assert b.canon(new_s["private_assertions"]) == b.canon(old_s["private_assertions"])
        assert new_s["reference_code"] == old_s["reference_code"]
        assert {k: v for k, v in new_s.items() if k != "public_task_sha256"} == {k: v for k, v in old_s.items() if k != "public_task_sha256"}
    with pytest.raises(ValueError):  # a second append is refused
        b.rebind(new_tasks, new_specs, EXAMPLES)
    assert b.rebind(tasks, specs, EXAMPLES) == (new_tasks, new_specs)  # deterministic
    assert b.jsonl_bytes(tasks) == (b.V1C / "tasks.jsonl").read_bytes()
    assert b.jsonl_bytes(specs) == (b.V1C / "private_specs.jsonl").read_bytes()
    grade = pytest.importorskip("experiments.landmark.grade")
    assert grade.digest(grade.contract(new_specs)) != grade.digest(grade.contract(specs))


def test_builder_refuses_bad_output(tmp_path):
    b = load_builder()
    with pytest.raises(SystemExit):
        b.build(tmp_path / "outside_work")
    with pytest.raises(SystemExit):
        b.build(b.ROOT / "work")  # exists, and is not strictly under work/


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_built_diagnostics_validate(name):
    d.validate_diagnostic(diag_for(name))  # build_diagnostic output passes the loaded-record validator


def _mutated(fn):
    diag = json.loads(json.dumps(diag_for("diag_all_pass_mbpp_52")))
    fn(diag)
    return diag


@pytest.mark.parametrize("mutate", [
    lambda g: g["cases"][0].update(extra="x"),                                        # extra per-case field
    lambda g: g.update(extra="x"),                                                    # extra top-level field
    lambda g: g["cases"][0].update(reason="protocol_integrity_review"),               # reason on a non-unavailable case
    lambda g: g["cases"][0].update(returned=True),                                    # bool is not an int
    lambda g: g["cases"][0].update(status="unavailable", returned=None, value_kind="none", reason="made_up"),
    lambda g: g.update(initial_artifact_sha256="A" * 64),                             # uppercase hex
    lambda g: g.update(schema_version="public-diagnostic-v0"),
    lambda g: g["cases"][0].update(expected=True),
], ids=["extra_case_field", "extra_top_field", "reason_not_unavailable", "bool_returned", "bad_reason", "upper_sha",
        "schema", "bool_expected"])
def test_validate_refuses(mutate):
    with pytest.raises(ValueError):
        d.validate_diagnostic(_mutated(mutate))


def test_validate_refuses_oversized():
    diag = _mutated(lambda g: g["cases"].extend(
        [{"case_id": f"x{i}", "call": "f()", "expected": BIG, "status": "wrong_value", "returned": BIG,
          "value_kind": "int_list", "reason": None} for i in range(8)]))
    with pytest.raises(d.DiagnosticOverflow):
        d.validate_diagnostic(diag)


def test_validate_binds_case_content_to_the_fixed_public_cases():
    # MRL-08 finding: a shape-valid record carrying a non-public call/expected must be refused when the public cases are known.
    cases = [{"case_id": "c1", "args_literal": "[1]", "expected_literal": "2"}]
    leak = {"schema_version": d.SCHEMA, "root_id": "r1", "initial_artifact_sha256": "a" * 64,
            "cases": [{"case_id": "hidden_7", "call": "assert f(99) == 12345  # PRIVATE HIDDEN TEST / reference: return x*x",
                       "expected": 12345, "status": "pass", "returned": None, "value_kind": "none", "reason": None}]}
    d.validate_diagnostic(leak)  # shape alone passes: this is why the binding is needed
    with pytest.raises(ValueError, match="fixed public cases"):
        d.validate_diagnostic(leak, "f", cases)
    good = d.build_diagnostic("r1", "a" * 64, "f", cases, [res("pass")])
    d.validate_diagnostic(good, "f", cases)
    for bad in ({**good["cases"][0], "expected": 3}, {**good["cases"][0], "call": "f(2)"}, {**good["cases"][0], "case_id": "c2"}):
        with pytest.raises(ValueError, match="fixed public cases"):
            d.validate_diagnostic({**good, "cases": [bad]}, "f", cases)
    with pytest.raises(ValueError, match="fixed public cases"):
        d.validate_diagnostic({**good, "cases": good["cases"] * 2}, "f", cases)
    with pytest.raises(ValueError, match="together"):
        d.validate_diagnostic(good, "f")


# --- MRL-08 round-2 adversarial findings ---

@pytest.mark.parametrize("status", ["program_exception", "timeout", "output_limit"])
def test_status_only_cases_cannot_carry_a_returned_value(status):
    case = [{"case_id": "c0", "args_literal": "[1]", "expected_literal": "2"}]
    with pytest.raises(ValueError, match="cannot carry a returned value"):
        d.build_diagnostic("r", "a" * 64, "f", case, [{"status": status, "returned": 123456789, "value_kind": "int", "reason": None}])


def test_render_arms_refuses_extra_diagnostic_keys():
    case = [{"case_id": "c0", "args_literal": "[1]", "expected_literal": "2"}]
    diag = d.build_diagnostic("r", "a" * 64, "f", case, [{"status": "pass", "returned": 2, "value_kind": "int", "reason": None}])
    diag["private_hidden_assert"] = "assert f(99) == 7"
    base = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
    with pytest.raises(ValueError):
        d.render_arms(base, "```python\ndef f(x): return 2\n```", diag)
