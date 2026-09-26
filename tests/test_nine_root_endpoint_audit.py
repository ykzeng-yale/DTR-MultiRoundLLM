"""MRL-37 pure tests for the nine-root measurement package builder (LEAD-ENDPOINT-07). Synthetic fixtures plus a read-only
check of the pinned local source when present. Nothing is executed: code and assertions are parsed with ast and compared as text."""
import ast
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from experiments.prompt_choice import nine_root_endpoint_audit as nr

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "work/sources/mbpp_full.jsonl"
HAVE_REAL = REAL.exists() and hashlib.sha256(REAL.read_bytes()).hexdigest() == nr.SOURCE_SHA256
SIG = {356: ("find_angle", ["a", "b"]), 885: ("is_Isomorphic", ["str1", "str2"]), 354: ("tn_ap", ["a", "n", "d"]),
       901: ("smallest_multiple", ["n"]), 654: ("rectangle_perimeter", ["l", "b"]), 703: ("is_key_present", ["d", "x"]),
       700: ("count_range_in_list", ["li", "min", "max"]), 656: ("find_Min_Sum", ["a", "b", "n"]), 36: ("find_Nth_Digit", ["p", "q", "N"])}


def synthetic_records():
    recs = {}
    for r, (entry, params) in SIG.items():
        tests = [f"assert {entry}({', '.join(str(k + i) for k in range(len(params)))}) == {10 + i}" for i in range(3)]
        recs[r] = {"text": f"SYNTHETIC FIXTURE {r}", "code": f"def {entry}({','.join(params)}):\n    return 0\n", "task_id": r,
                   "test_setup_code": "", "test_list": tests, "challenge_test_list": []}
    return recs


def write_jsonl(path, recs, extra=()):
    data = ("\n".join([json.dumps(x) for x in recs.values()] + list(extra)) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def syn(tmp_path):
    path = tmp_path / "syn.jsonl"
    return path, write_jsonl(path, synthetic_records())


@pytest.fixture(scope="module")
def real_pkg():
    if not HAVE_REAL:
        pytest.skip("pinned MBPP cache not present in gitignored work/")
    return nr.build(REAL)


def _contract_text():
    return subprocess.run(["git", "-C", str(ROOT), "show", "b6b7a31:docs/policy_nine_root_measurement_contract_20260926.md"],
                          capture_output=True, check=True).stdout.decode()


def test_supplement_is_the_exact_46_case_lead_table():
    table = {}
    for root in nr.ROOTS:
        row = re.search(rf"^\|{root}\|(`\(.+)\|$", _contract_text(), re.M).group(1)
        cells = re.findall(r"`([^`]*)`", row)
        table[root] = [tuple(ast.literal_eval(side.strip()) for side in c.split("→")) for c in cells]
    ours = {r: [(tuple(a), e) for a, e in cases] for r, cases in nr.SUPPLEMENT_V1.items()}
    assert ours == {r: [(tuple(a) if isinstance(a, tuple) else (a,), e) for a, e in cases] for r, cases in table.items()}
    assert sum(len(v) for v in nr.SUPPLEMENT_V1.values()) == 46
    tree = ast.parse((ROOT / "experiments/prompt_choice/nine_root_endpoint_audit.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "SUPPLEMENT_V1")
    for value in node.value.values:
        ast.literal_eval(value)  # literal-only source: nothing is computed


def test_adapted_public_wording_is_the_lead_text_and_700_keeps_strings():
    text = _contract_text()
    for root, wording in nr.ADAPTED_PUBLIC.items():
        row = re.search(rf"^\|{root}\|([^`|][^|]*)\|$", text, re.M).group(1)
        squash = lambda s: re.sub(r"\s+", "", s)
        assert squash(row) == squash(wording), root
    assert "all integers or all strings" in nr.ADAPTED_PUBLIC[700]


def test_roots_order_and_all_nine_built_deterministically(syn):
    path, sha = syn
    a, b = nr._build_synthetic_for_tests(path, sha), nr._build_synthetic_for_tests(path, sha)
    assert a == b and a["manifest"]["refusals"] == []
    assert [p["task_id"] for p in a["public_records"]] == [f"mbpp/{r}" for r in nr.ROOTS] == a["manifest"]["roots_in_order"]
    assert a["manifest"]["designation"] == "synthetic_test_fixture_not_the_v1_package"
    assert a["manifest"]["planned_inventory"] == {"artifacts": 54, "slots": 162,
                                                  "note": "planning arithmetic only; slots are not independent observations"}


def test_changed_root_is_recorded_as_refusal_not_backfilled(tmp_path):
    recs = synthetic_records()
    recs[901]["test_list"].append("assert smallest_multiple(4) == 12")
    path = tmp_path / "m.jsonl"
    pkg = nr._build_synthetic_for_tests(path, write_jsonl(path, recs))
    assert [r["task_id"] for r in pkg["manifest"]["refusals"]] == ["mbpp/901"]
    assert [p["task_id"] for p in pkg["public_records"]] == [f"mbpp/{r}" for r in nr.ROOTS if r != 901]


@pytest.mark.parametrize("mutate", ["sha", "missing", "duplicate", "dup_key", "not_utf8"])
def test_input_refusals(tmp_path, mutate):
    recs = synthetic_records()
    path = tmp_path / "m.jsonl"
    if mutate == "missing":
        del recs[36]
    extra = [json.dumps(recs[356])] if mutate == "duplicate" else ['{"task_id": 1, "task_id": 1}'] if mutate == "dup_key" else []
    sha = write_jsonl(path, recs, extra)
    if mutate == "not_utf8":
        path.write_bytes(b"\xff\n")
        sha = hashlib.sha256(b"\xff\n").hexdigest()
    with pytest.raises(nr.AuditSourceError):
        nr._build_synthetic_for_tests(path, "0" * 64 if mutate == "sha" else sha)
    with pytest.raises(nr.AuditSourceError):
        nr.build(path)  # the production build never accepts a non-pinned source


def test_no_overwrite_and_work_root_only(syn, tmp_path):
    path, sha = syn
    pkg = nr._build_synthetic_for_tests(path, sha)
    work = tmp_path / "work"
    work.mkdir()
    names = nr.write_package(pkg, work / "pkg", work_root=work)
    assert len(names) == 1 + 9 + 9
    with pytest.raises(FileExistsError):
        nr.write_package(pkg, work / "pkg", work_root=work)
    with pytest.raises(nr.AuditSourceError):
        nr.write_package(pkg, tmp_path / "outside", work_root=work)


def test_real_45_controls_unchanged_bytes_and_separation(real_pkg):
    pkg = real_pkg
    assert pkg["manifest"]["refusals"] == [] and pkg["manifest"]["designation"] == "production"
    src = {}
    for line in REAL.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        src[row["task_id"]] = row
    codes = []
    for pub, priv in zip(pkg["public_records"], pkg["private_records"]):
        r = int(pub["task_id"].split("/")[1])
        assert priv["reference"]["code"] == src[r]["code"] and priv["original_description"] == src[r]["text"]
        assert pub["public_assertion"]["text"] == src[r]["test_list"][0]
        assert [c["text"] for c in priv["batteries"]["original_private"]["cases"]] == src[r]["test_list"][1:]
        assert pub["adapted_public_contract"] == nr.ADAPTED_PUBLIC[r] and priv["public_record_sha256"] == nr.canonical_sha256(pub)
        assert [c["kind"] for c in priv["controls"]] == list(nr.CONTROL_KINDS)
        entry, params = SIG[r]
        originals = [nr.parse_assertion(t, entry, len(params)) for t in src[r]["test_list"]]
        for c in priv["controls"]:
            tree = ast.parse(c["code"])
            assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef) and tree.body[0].name == entry
            assert [p.arg for p in tree.body[0].args.args] == params and c["raw_sha256"] == nr.raw_sha256(c["code"])
            codes.append(c["code"])
        lookup = ast.parse(priv["controls"][4]["code"]).body[0]
        assert ast.literal_eval(lookup.body[0].value) == tuple((o["args"], o["expected"]) for o in originals)
        assert isinstance(lookup.body[-1], ast.Return) and lookup.body[-1].value.value is None
        assert ast.literal_eval(ast.parse(priv["controls"][3]["code"]).body[0].body[0].value) == originals[0]["expected"]
        public_text = json.dumps(pub, ensure_ascii=False)
        secrets_ = [src[r]["code"], *src[r]["test_list"][1:], *[c["code"] for c in priv["controls"]],
                    *[c["assertion_text"] for c in priv["batteries"]["supplement_v1"]["cases"]]]
        for s in secrets_:
            assert json.dumps(s, ensure_ascii=False)[1:-1] not in public_text
    assert len(codes) == 45 and len(set(codes)) == 45


def test_real_package_fits_the_grader_schema_one_spec_per_battery(real_pkg):
    from experiments.landmark import grade
    from experiments.landmark.collect import digest
    for pub, priv in zip(real_pkg["public_records"], real_pkg["private_records"]):
        task = {"root_id": pub["task_id"], "prompt": pub["adapted_public_contract"] + "\n" + pub["signature"],
                "public_context": pub["public_assertion"]["text"]}
        for battery, texts in (("original_private", [c["text"] for c in priv["batteries"]["original_private"]["cases"]]),
                               ("supplement_v1", [c["assertion_text"] for c in priv["batteries"]["supplement_v1"]["cases"]])):
            spec = {"root_id": pub["task_id"], "public_task_sha256": digest(task), "entry_point": pub["entry_point"],
                    "public_assertions": [pub["public_assertion"]["text"]], "private_assertions": texts, "preamble": [],
                    "reference_code": priv["reference"]["code"],
                    "negative_controls": [{"code": c["code"], "rationale": c["rule"]} for c in priv["controls"]]}
            grade.validate_specs([task], [spec])


def test_prediction_table_is_source_reasoned_and_complete():
    for r in nr.ROOTS:
        p = nr.PREDICTIONS[r]
        assert p["reference"] == (True, True) and p["lookup_original_examples"] == (True, False)
        assert all(p[k][1] is False for k in nr.CONTROL_KINDS)  # every control predicted to fail the supplement
    assert nr.PREDICTIONS[901]["wrong_rule_1"] == (True, False) and nr.PREDICTIONS[700]["wrong_rule_2"] == (True, False)
    assert nr.PREDICTIONS[885]["wrong_rule_2"] == (True, False)


def test_module_has_no_execution_or_network_path_and_config_pins_contract():
    tree = ast.parse((ROOT / "experiments/prompt_choice/nine_root_endpoint_audit.py").read_text())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert mods == {"__future__", "argparse", "ast", "hashlib", "json", "pathlib", "experiments.prompt_choice.endpoint_audit"}
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    assert not called & {"eval", "exec", "compile", "__import__", "system", "Popen", "run", "urlopen", "run_program"}
    cfg = json.loads((ROOT / "experiments/prompt_choice/nine_root_endpoint_source_v1.json").read_text())
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "b6b7a31:docs/policy_nine_root_measurement_contract_20260926.md"],
                          capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == cfg["lead_contract"]["sha256"]
    assert cfg["status"] == "source_only" and cfg["execution_authorized"] is False and cfg["runner"] is None
    assert sum(len(v) for v in cfg["supplement_v1"].values()) == 46
