"""MRL-33 pure tests for the endpoint-audit package builder (LEAD-ENDPOINT-01). Committed fixtures are synthetic; the
real pinned MBPP cache is read only if present in gitignored work/. Nothing here runs a reference, control, assertion,
candidate, sandbox or model: programs are parsed with ast and compared as text."""
import ast
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from experiments.prompt_choice import endpoint_audit as ea

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "work/sources/mbpp_full.jsonl"
H = ea.raw_sha256

SYN = {
    877: {"text": "SYNTHETIC FIXTURE: order the letters.", "code": "def sort_String(str) : \r\n    return str ",
          "task_id": 877, "test_setup_code": "",
          "test_list": ['assert sort_String("ba") == "ab"', 'assert sort_String("dc") == "cd"', 'assert sort_String("fe")=="ef"'],
          "challenge_test_list": []},
    345: {"text": "SYNTHETIC FIXTURE: pair differences.", "code": "def diff_consecutivenums(nums):\r\n    return nums",
          "task_id": 345, "test_setup_code": "",
          "test_list": ["assert diff_consecutivenums([1, 2])==[1]", "assert diff_consecutivenums([3, 5, 4]) == [2, -1]",
                        "assert diff_consecutivenums([0, 0])==[0]"],
          "challenge_test_list": []},
}
OTHER = {"text": "SYNTHETIC other", "code": "def f(x):\n    return x", "task_id": 1, "test_setup_code": "",
         "test_list": ["assert f(1) == 1"], "challenge_test_list": []}


def pins_for(records):
    return {r: {"entry_point": ea.RECORD_PINS[r]["entry_point"], "text_sha256": H(records[r]["text"]),
                "reference_sha256": H(records[r]["code"]), "assertion_sha256": tuple(H(t) for t in records[r]["test_list"])}
            for r in ea.ROOTS}


def write_source(path, records, lines=None):
    lines = lines if lines is not None else [json.dumps(OTHER), json.dumps(records[345]), json.dumps(records[877])]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def syn(tmp_path):
    path = tmp_path / "synthetic.jsonl"
    sha = write_source(path, SYN)
    return path, sha, pins_for(SYN)


def build(syn):
    path, sha, pins = syn
    return ea._build_synthetic_for_tests(path, sha, pins)


def test_deterministic_regeneration(syn):
    a, b = build(syn), build(syn)
    assert a == b and ea.canonical_sha256(a) == ea.canonical_sha256(b)
    assert a["manifest"]["public_record_sha256"] == {p["task_id"]: ea.canonical_sha256(p) for p in a["public_records"]}
    assert a["manifest"]["private_record_sha256"] == {p["task_id"]: ea.canonical_sha256(p) for p in a["private_records"]}


def _mutated(tmp_path, change):
    recs = copy.deepcopy(SYN)
    lines = change(recs)
    path = tmp_path / "m.jsonl"
    sha = write_source(path, recs, lines)
    return path, sha, recs


@pytest.mark.parametrize("change,pinned_from", [
    (lambda r: [json.dumps(OTHER), json.dumps(r[345]), json.dumps(r[877]), json.dumps(r[877])], "orig"),   # duplicate root
    (lambda r: [json.dumps(OTHER), json.dumps(OTHER), json.dumps(r[345]), json.dumps(r[877])], "orig"),   # duplicate other id
    (lambda r: [json.dumps(OTHER), json.dumps(r[345])], "orig"),                                           # missing 877
    (lambda r: ['{"task_id": 877, "task_id": 877}', json.dumps(r[345])], "orig"),                         # duplicate JSON key
    (lambda r: r[877].update(extra=1), "mut"),                                                            # changed keys
    (lambda r: r[877]["test_list"].append('assert sort_String("hg") == "gh"'), "mut"),                  # four assertions
    (lambda r: r[345].update(test_setup_code="import math"), "mut"),                                    # nonempty setup
    (lambda r: r[345].update(challenge_test_list=["assert diff_consecutivenums([1]) == []"]), "mut"),  # challenge tests
    (lambda r: r[877].update(code=r[877]["code"] + "\n"), "orig"),                                      # reference byte change
    (lambda r: r[877]["test_list"].__setitem__(1, 'assert sort_String("dc") == "cd" '), "orig"),       # assertion byte change
    (lambda r: r[345].update(text=r[345]["text"] + " "), "orig"),                                       # description change
    (lambda r: r[877]["test_list"].__setitem__(1, 'assert sort_String(x) == "cd"'), "mut"),            # non-literal argument
    (lambda r: r[877]["test_list"].__setitem__(2, 'assert sort_String("a", "b") == "ab"'), "mut"),     # two arguments
    (lambda r: r[877]["test_list"].__setitem__(2, 'assert sort_String("fe") != "ef"'), "mut"),         # not equality
    (lambda r: r[877]["test_list"].__setitem__(2, 'assert other("fe") == "ef"'), "mut"),               # wrong entry point
    (lambda r: r[877]["test_list"].__setitem__(2, 'assert sort_String("fe") == "ef", "m"'), "mut"),    # assert message
    (lambda r: r[877].update(code="def sort_String(s):\n    return s\ndef helper():\n    pass"), "mut"), # extra definition
    (lambda r: r[877].update(code="def sort_String(s, t=1):\n    return s"), "mut"),                  # signature changed
    (lambda r: r[345].update(task_id="345"), "mut"),                                                    # non-integer id
])
def test_fail_closed_on_changed_source(tmp_path, change, pinned_from):
    path, sha, recs = _mutated(tmp_path, lambda r: change(r))
    pins = pins_for(SYN) if pinned_from == "orig" else pins_for(recs) if all(isinstance(recs[k].get("test_list"), list) for k in recs) else pins_for(SYN)
    with pytest.raises(ea.AuditSourceError):
        ea._build_synthetic_for_tests(path, sha, pins)


def test_fail_closed_on_file_pin(tmp_path, syn):
    path, sha, pins = syn
    with pytest.raises(ea.AuditSourceError, match="SHA256"):
        ea._build_synthetic_for_tests(path, "0" * 64, pins)
    with pytest.raises(ea.AuditSourceError, match="unavailable"):
        ea._build_synthetic_for_tests(tmp_path / "absent.jsonl", sha, pins)
    bad = tmp_path / "bad.jsonl"
    bad.write_bytes(b"\xff\n")
    with pytest.raises(ea.AuditSourceError, match="UTF-8"):
        ea._build_synthetic_for_tests(bad, hashlib.sha256(b"\xff\n").hexdigest(), pins)
    with pytest.raises(ea.AuditSourceError):  # default pins: the synthetic file is not the pinned MBPP cache
        ea.build(path)


def test_exact_roots_order_and_945_hold(syn):
    pkg = build(syn)
    assert [p["task_id"] for p in pkg["public_records"]] == [p["task_id"] for p in pkg["private_records"]] == ["mbpp/877", "mbpp/345"]
    assert pkg["manifest"]["roots_in_order"] == ["mbpp/877", "mbpp/345"]
    assert list(pkg["manifest"]["held_roots"]) == ["mbpp/945"] and "not an executable task" in pkg["manifest"]["held_roots"]["mbpp/945"]
    blob = json.dumps(pkg["public_records"] + pkg["private_records"])
    assert "945" not in blob
    assert all(p["public_case"]["case_id"] == "public-0" for p in pkg["public_records"])


def test_public_private_separation_and_binding(syn):
    pkg = build(syn)
    for pub, priv in zip(pkg["public_records"], pkg["private_records"]):
        root = int(pub["task_id"].split("/")[1])
        assert set(pub) == {"record_type", "version", "task_id", "description", "signature", "entry_point", "public_case",
                            "public_assertion", "source_sha256"}
        text = json.dumps(pub, ensure_ascii=False)
        private_texts = [SYN[root]["code"], *SYN[root]["test_list"][1:]]
        private_texts += [c["assertion_text"] for c in priv["batteries"]["supplement_v1"]["cases"]]
        private_texts += [c["code"] for c in priv["controls"]]
        for t in private_texts:
            assert json.dumps(t, ensure_ascii=False)[1:-1] not in text
        for lit in [c["expected_literal"] for b in priv["batteries"].values() for c in b["cases"]]:
            assert lit not in json.dumps(pub["public_case"])
        assert priv["public_record_sha256"] == ea.canonical_sha256(pub)
        assert pub["public_assertion"]["text"] == SYN[root]["test_list"][0] and pub["description"] == SYN[root]["text"]


def test_unchanged_reference_and_assertion_bytes_with_separate_normalized_forms(syn):
    pkg = build(syn)
    for pub, priv in zip(pkg["public_records"], pkg["private_records"]):
        root = int(pub["task_id"].split("/")[1])
        assert priv["reference"]["code"] == SYN[root]["code"] and priv["reference"]["raw_sha256"] == H(SYN[root]["code"])
        cases = priv["batteries"]["original_private"]["cases"]
        assert [c["assertion_index"] for c in cases] == [1, 2]
        assert [c["text"] for c in cases] == SYN[root]["test_list"][1:]  # exact bytes, including original spacing
        for c in cases:
            assert c["raw_sha256"] == H(c["text"])
            assert c["normalized_ast_sha256"] == hashlib.sha256(ast.dump(ast.parse(c["text"]), include_attributes=False).encode()).hexdigest()
    spaced = pkg["private_records"][0]["batteries"]["original_private"]["cases"][1]
    assert spaced["text"] == 'assert sort_String("fe")=="ef"' and spaced["args_literal"] == "['fe']" and spaced["expected_literal"] == "'ef'"


def _contract_supplement():
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "c83555c:docs/policy_endpoint_audit_contract_20260926.md"],
                          capture_output=True, check=True).stdout.decode()
    table = {}
    for root in ("877", "345"):
        row = re.search(rf"^\| {root} \| (.+) \|$", blob, re.M).group(1)
        cells = re.findall(r"`([^`]*)`", row)
        table[int(root)] = [tuple(ast.literal_eval(side.strip()) for side in cell.split("→")) for cell in cells]
    return table


def test_supplement_is_the_exact_lead_table_as_frozen_literals(syn):
    table = _contract_supplement()
    assert {r: [(a[0], e) for a, e in cases] for r, cases in ea.SUPPLEMENT_V1.items()} == table
    assert sum(len(v) for v in ea.SUPPLEMENT_V1.values()) == 8
    tree = ast.parse((ROOT / "experiments/prompt_choice/endpoint_audit.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "SUPPLEMENT_V1")
    assert all(isinstance(v, (ast.Tuple, ast.Constant, ast.List, ast.UnaryOp)) for v in ast.walk(node.value)
               if isinstance(v, ast.expr) and not isinstance(v, ast.Dict)) is True
    ast.literal_eval(node.value.values[0]) and ast.literal_eval(node.value.values[1])  # literal-only expressions
    pkg = build(syn)
    for priv in pkg["private_records"]:
        root = int(priv["task_id"].split("/")[1])
        cases = priv["batteries"]["supplement_v1"]["cases"]
        assert [c["case_id"] for c in cases] == [f"supplement_v1-{j}" for j in range(4)]
        assert [(ast.literal_eval(c["args_literal"])[0], ast.literal_eval(c["expected_literal"])) for c in cases] == table[root]
        for c in cases:
            parsed = ea.parse_assertion(c["assertion_text"], priv["entry_point"])
            assert (parsed["args_literal"], parsed["expected_literal"]) == (c["args_literal"], c["expected_literal"])


def _examples(code):
    tree = ast.parse(code)
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef)  # the table lives inside the function
    fn = tree.body[0]
    assign = fn.body[0]
    assert isinstance(assign, ast.Assign) and assign.targets[0].id == "examples"
    last = fn.body[-1]
    assert isinstance(last, ast.Return) and isinstance(last.value, ast.Constant) and last.value.value is None
    return ast.literal_eval(assign.value)


def test_ten_distinct_labeled_controls(syn):
    pkg = build(syn)
    codes = [c["code"] for p in pkg["private_records"] for c in p["controls"]]
    assert len(codes) == len(set(codes)) == 10
    for priv in pkg["private_records"]:
        root = int(priv["task_id"].split("/")[1])
        assert [c["kind"] for c in priv["controls"]] == list(ea.CONTROL_ORDER[root])
        for c in priv["controls"]:
            tree = ast.parse(c["code"])  # terminal output contract: only the function definition (and imports it needs)
            assert all(isinstance(n, (ast.FunctionDef, ast.Import, ast.ImportFrom)) for n in tree.body)
            fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
            assert [f.name for f in fns] == [priv["entry_point"]] and len(fns[0].args.args) == 1
            assert c["raw_sha256"] == H(c["code"]) and c["rationale"] and c["lead_prediction"]
            assert c["control_id"] == f"{priv['task_id']}/control/{c['kind']}"
            if c["kind"] in ea.FIXED_CONTROLS[root]:
                assert c["code"] == ea.FIXED_CONTROLS[root][c["kind"]] and c["provenance"] == "fixed exact source"
        originals = [ea.parse_assertion(t, priv["entry_point"]) for t in SYN[root]["test_list"]]
        lookup = priv["controls"][4]
        assert _examples(lookup["code"]) == tuple((o["args"][0], o["expected"]) for o in originals)
        const = ast.parse(priv["controls"][3]["code"]).body[0].body[0]
        assert isinstance(const, ast.Return) and ast.literal_eval(const.value) == originals[0]["expected"]
    assert ea.LEAD_PREDICTION["lookup_original_examples"] == "pass original examples; fail supplement_v1"


def test_module_has_no_execution_network_or_dynamic_import_path():
    tree = ast.parse((ROOT / "experiments/prompt_choice/endpoint_audit.py").read_text())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert mods == {"__future__", "argparse", "ast", "hashlib", "json", "pathlib", "sys"}
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    assert not called & {"eval", "exec", "compile", "__import__", "import_module", "system", "Popen", "run", "check_output",
                         "urlopen", "run_program", "evaluate", "grade_collection", "spawn", "fork"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"collect", "diagnostic", "grade", "sandbox", "subprocess", "urllib", "os"}


def test_output_is_new_directory_inside_work_root_and_never_overwritten(tmp_path, syn):
    pkg = build(syn)
    work = tmp_path / "work"
    work.mkdir()
    out = work / "pkg"
    names = ea.write_package(pkg, out, work_root=work)
    assert names == ["manifest.json", "public/mbpp_877.json", "public/mbpp_345.json", "private/mbpp_877.json", "private/mbpp_345.json"]
    assert json.loads((out / "public/mbpp_877.json").read_text()) == pkg["public_records"][0]
    before = {p: p.read_bytes() for p in out.rglob("*.json")}
    with pytest.raises(FileExistsError):
        ea.write_package(pkg, out, work_root=work)
    assert {p: p.read_bytes() for p in out.rglob("*.json")} == before
    with pytest.raises(ea.AuditSourceError):
        ea.write_package(pkg, tmp_path / "outside", work_root=work)
    with pytest.raises(ea.AuditSourceError):
        ea.write_package(pkg, work, work_root=work)


def test_config_mirrors_module_and_pins_contract():
    cfg = json.loads((ROOT / "experiments/prompt_choice/endpoint_audit_source_v1.json").read_text())
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "c83555c:docs/policy_endpoint_audit_contract_20260926.md"],
                          capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == cfg["lead_contract"]["sha256"]
    assert cfg["version"] == ea.VERSION and cfg["status"] == "source_only" and cfg["collection"] == "unreleased"
    assert cfg["execution_authorized"] is False and cfg["experimental_calls_authorized"] == 0 and cfg["runner"] is None
    assert cfg["source"]["sha256"] == ea.SOURCE_SHA256 and cfg["roots_in_order"] == ["mbpp/877", "mbpp/345"]
    for r in ea.ROOTS:
        pin = cfg["record_pins"][f"mbpp/{r}"]
        assert {**pin, "assertion_sha256": tuple(pin["assertion_sha256"])} == ea.RECORD_PINS[r]
        assert cfg["supplement_v1"][f"mbpp/{r}"] == [{"args_literal": repr(list(a)), "expected_literal": repr(e)} for a, e in ea.SUPPLEMENT_V1[r]]
        assert [c["kind"] for c in cfg["controls"][f"mbpp/{r}"]] == list(ea.CONTROL_ORDER[r])
        for c in cfg["controls"][f"mbpp/{r}"]:
            if c["kind"] in ea.FIXED_CONTROLS[r]:
                assert c["code_raw_sha256"] == H(ea.FIXED_CONTROLS[r][c["kind"]])


def _grader_task_and_spec(pub, priv, battery):
    from experiments.landmark.collect import digest
    task = {"root_id": pub["task_id"], "prompt": pub["description"] + "\n" + pub["signature"], "public_context": pub["public_assertion"]["text"]}
    texts = {"original_private": [c["text"] for c in priv["batteries"]["original_private"]["cases"]],
             "supplement_v1": [c["assertion_text"] for c in priv["batteries"]["supplement_v1"]["cases"]]}
    private = texts[battery] if battery != "union" else texts["original_private"] + texts["supplement_v1"]
    spec = {"root_id": pub["task_id"], "public_task_sha256": digest(task), "entry_point": pub["entry_point"],
            "public_assertions": [pub["public_assertion"]["text"]], "private_assertions": private, "preamble": [],
            "reference_code": priv["reference"]["code"],
            "negative_controls": [{"code": c["code"], "rationale": c["rationale"]} for c in priv["controls"]]}
    return task, spec


def _packages(syn):
    pkgs = [build(syn)]
    if REAL.exists() and hashlib.sha256(REAL.read_bytes()).hexdigest() == ea.SOURCE_SHA256:
        pkgs.append(ea.build(REAL))
    return pkgs


@pytest.mark.parametrize("battery", ["original_private", "supplement_v1", "union"])
def test_existing_grader_schema_accepts_each_battery_as_a_separate_pure_spec(syn, battery):
    # Pure validate_specs only (ast parsing and text checks); the grader is unchanged and nothing is executed. Its API takes
    # one private list per spec, so battery-specific outcomes need the separately reviewed adapter in GRADER_ADAPTER_NOTE.
    from experiments.landmark import grade
    from experiments.landmark import diagnostic as dg
    for pkg in _packages(syn):
        for pub, priv in zip(pkg["public_records"], pkg["private_records"]):
            task, spec = _grader_task_and_spec(pub, priv, battery)
            grade.validate_specs([task], [spec])
            dg.public_skeleton(pub["entry_point"], [pub["public_case"]], dg.SCHEMA_V2)  # diagnostic-v2 public display


@pytest.mark.skipif(not REAL.exists(), reason="pinned MBPP cache not present in gitignored work/")
def test_real_pinned_source_builds_with_unchanged_pins():
    pkg = ea.build(REAL)
    assert pkg == ea.build(REAL)
    pub = {p["task_id"]: p for p in pkg["public_records"]}
    assert pub["mbpp/877"]["public_case"] == {"case_id": "public-0", "args_literal": "['cba']", "expected_literal": "'abc'"}
    assert pub["mbpp/345"]["public_case"]["expected_literal"] == "[0, 2, 1, 0, 1, 1, 1]"
    assert pub["mbpp/877"]["signature"] == "sort_String(str)" and pub["mbpp/345"]["signature"] == "diff_consecutivenums(nums)"
    for priv in pkg["private_records"]:
        r = int(priv["task_id"].split("/")[1])
        assert priv["reference"]["raw_sha256"] == ea.RECORD_PINS[r]["reference_sha256"]
        assert [c["raw_sha256"] for c in priv["batteries"]["original_private"]["cases"]] == list(ea.RECORD_PINS[r]["assertion_sha256"][1:])


def test_production_build_has_no_pin_override_and_binds_actual_file_hashes(syn, tmp_path):
    import inspect
    assert list(inspect.signature(ea.build).parameters) == ["source_path"]  # no source/record pin or hash override
    assert list(inspect.signature(ea.main).parameters) == ["argv"]
    path, sha, pins = syn
    with pytest.raises(ea.AuditSourceError):  # a synthetic file can never be built as the real v1 package
        ea.build(path)
    syn_pkg = build(syn)
    assert syn_pkg["manifest"]["designation"] == "synthetic_test_fixture_not_the_v1_package"
    assert syn_pkg["manifest"]["version"] == ea.SYNTHETIC_VERSION != ea.VERSION
    assert all(r["version"] == ea.SYNTHETIC_VERSION for r in syn_pkg["public_records"] + syn_pkg["private_records"])
    builder = hashlib.sha256((ROOT / "experiments/prompt_choice/endpoint_audit.py").read_bytes()).hexdigest()
    config = hashlib.sha256((ROOT / "experiments/prompt_choice/endpoint_audit_source_v1.json").read_bytes()).hexdigest()
    assert (syn_pkg["manifest"]["builder_sha256"], syn_pkg["manifest"]["config_sha256"]) == (builder, config)
    if REAL.exists() and hashlib.sha256(REAL.read_bytes()).hexdigest() == ea.SOURCE_SHA256:
        real = ea.build(REAL)
        assert real["manifest"]["designation"] == "production" and real["manifest"]["version"] == ea.VERSION
        assert all(r["version"] == ea.VERSION for r in real["public_records"] + real["private_records"])
        assert (real["manifest"]["builder_sha256"], real["manifest"]["config_sha256"]) == (builder, config)
        assert None not in (real["manifest"]["builder_sha256"], real["manifest"]["config_sha256"])


def test_cli_refuses_with_a_message_and_writes_nothing(tmp_path, capsys):
    target = ea.WORK_ROOT / "endpoint_audit_cli_refusal_probe_never_created"
    assert ea.main(["--source", str(tmp_path / "absent.jsonl"), "--out", str(target)]) == 2
    assert "refused: AuditSourceError" in capsys.readouterr().err and not target.exists()
