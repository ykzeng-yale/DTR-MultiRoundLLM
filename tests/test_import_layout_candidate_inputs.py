"""MRL-40 tests for the import-layout source inquiry. Small synthetic inputs through the explicit synthetic seam
(`reconcile_inputs`), plus an optional read-only check of the pinned real inputs. Nothing is executed: references are parsed
with ast only and never run or imported."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("imp", ROOT / "scripts/prepare_import_layout_candidate_inputs_20260927.py")
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)
H = lambda s: hashlib.sha256(s.encode()).hexdigest()
SECRET = "SECRET_BODY_MARKER"


def row(t, text, code):
    return {"task_id": t, "text": text, "code": code, "test_list": [f"assert f{t}(1) == {SECRET}"], "test_setup_code": "",
            "challenge_test_list": []}


def synthetic():
    mbpp = [row(1, "original words for one", "def one(q):\n    return q\n"),
            row(2, "config only words", "def two(w):\n    return w\n"),
            row(3, "alpha beta gamma", f"import heapq\ndef f3(x):\n    return heapq.nlargest(1, x)  # {SECRET}\n"),
            row(4, "delta epsilon zeta", "from math import gcd as g\ndef f4(a, b):\n    return g(a, b)\n"),
            row(5, "canonical match words", "import re\nimport os\ndef f5(s):\n    return re.sub('a', '', s)\n"),
            row(6, "not selected", "x = 1\ndef f6():\n    return x\n"),
            row(7, "e11 root words", "def seven(z):\n    return z\n"),
            row(8, "alpha beta gamma", "def eight(v):\n    return v\n")]
    by = {r["task_id"]: r for r in mbpp}
    return {
        "expected_n": 3,
        "mbpp": mbpp,
        "canonical_pool": [{"uid": "mbpp/1", "prompt": "canonical match words", "reference": "def one(q):\n    return q\n"},
                           {"uid": "humaneval/0", "prompt": "human eval words", "reference": "def h(a):\n    return a\n"}],
        "interface_audit": {"one_function_imports_only": 3, "records": [
            {"task_id": t, "historical_gate": "G2_interface", "historical_reason": "not_single_function",
             "reference_sha256": H(by[t]["code"]), "one_function_imports_only": t != 6} for t in (3, 4, 5, 6)]},
        "lineage_r1": {"rows": [{"task_id": t, "terminal_category": "mechanical_interface", "flags_from_named_records": {}}
                                for t in (3, 4, 5, 6)]},
        "prior_seen_config": {"prior_seen_root_ids": ["mbpp/1", "humaneval/0", "mbpp/2", "mbpp/4"]},
        "mrl15_manifest": {"source": {"e11_dev_roots": [7]}},
        "reconciliation_198": {"records": [{"task_id": 8, "prior_receiver_development": True},
                                           {"task_id": 7, "prior_receiver_development": False}]},
    }


def build(d=None):
    return imp.reconcile_inputs(d or synthetic())


def rows_by(doc):
    return {r["task_id"]: r for r in doc["rows"]}


def test_selection_order_layout_metadata_and_determinism():
    doc = build()
    assert doc == build() and [r["task_id"] for r in doc["rows"]] == [3, 4, 5]
    rows = rows_by(doc)
    assert rows[3]["layout"]["top_level_imports"] == [{"kind": "import", "module": None, "level": 0, "names": [{"name": "heapq", "alias": None}]}]
    assert rows[4]["layout"]["top_level_imports"][0] == {"kind": "from", "module": "math", "level": 0, "names": [{"name": "gcd", "alias": "g"}]}
    assert rows[5]["layout"]["n_import_statements"] == 2 and rows[4]["layout"]["n_positional_params"] == 2
    assert all(r["approved_for_evaluation"] is False and r["historical_gate"] == "G2_interface" for r in doc["rows"])


def test_e12_only_and_config_only_comparators_are_in_the_prior_universe():
    rows = rows_by(build())
    top3 = rows[3]["prior_neighbors_top6"][0]
    assert top3["uid"] == "mbpp/8" and top3["score"] == 1.0 and top3["provenance_scopes"] == ["e12_recorded_receiver_development"]
    uids = {n["uid"]: n for n in rows[3]["prior_neighbors_top6"]}
    assert uids["mbpp/2"]["provenance_scopes"] == ["prior_seen_config"] and uids["mbpp/2"]["winning_variant"] == "original_mbpp"
    assert uids["mbpp/7"]["provenance_scopes"] == ["e11_dev"]


def test_max_over_variants_dedup_and_winning_variant():
    rows = rows_by(build())
    top5 = rows[5]["prior_neighbors_top6"][0]
    assert top5["uid"] == "mbpp/1" and top5["winning_variant"] == "canonical" and top5["score"] == 1.0
    assert top5["provenance_scopes"] == ["canonical_pool", "prior_seen_config"]
    assert [n["uid"] for n in rows[5]["prior_neighbors_top6"]].count("mbpp/1") == 1


def test_ranking_ties_by_uid_and_within_103_ties_by_numeric_id():
    rows = rows_by(build())
    for r in rows.values():
        keys = [(-n["score"], n["uid"]) for n in r["prior_neighbors_top6"]]
        assert keys == sorted(keys)
        within = [(-n["score"], n["task_id"]) for n in r["within_103_neighbors_top6"]]
        assert within == sorted(within) and r["task_id"] not in [n["task_id"] for n in r["within_103_neighbors_top6"]]


def test_identical_uid_is_excluded_from_neighbours_but_flagged():
    rows = rows_by(build())
    assert "mbpp/4" not in [n["uid"] for n in rows[4]["prior_neighbors_top6"]]
    flags = rows[4]["exposure_flags_from_named_records"]
    assert flags["prior_identity_scopes"] == ["prior_seen_config"] and flags["in_prior_seen_config"] is True


def _extra_assign(d):
    d["mbpp"][2]["code"] = "y = 2\n" + d["mbpp"][2]["code"]
    d["interface_audit"]["records"][0]["reference_sha256"] = H(d["mbpp"][2]["code"])


@pytest.mark.parametrize("fn", [
    lambda d: d["prior_seen_config"]["prior_seen_root_ids"].append("mbpp/999"),      # missing MBPP comparator
    lambda d: d["prior_seen_config"]["prior_seen_root_ids"].append("humaneval/5"),   # missing pool comparator
    lambda d: d["reconciliation_198"]["records"].append({"task_id": 555, "prior_receiver_development": True}),
    _extra_assign,                                                                    # changed source shape
    lambda d: d["interface_audit"].update(one_function_imports_only=4),              # declared count mismatch
    lambda d: d["interface_audit"]["records"][1].update(reference_sha256="0" * 64),   # audit/source hash mismatch
    lambda d: d["lineage_r1"]["rows"][0].update(terminal_category="reviewed_frame"),  # not a historical G2 exclusion
    lambda d: d["mbpp"].append(dict(d["mbpp"][0])),                                   # duplicate source ID
    lambda d: d.update(expected_n=4),
])
def test_refusals(fn):
    d = synthetic()
    fn(d)
    with pytest.raises(imp.InquiryRefused):
        imp.reconcile_inputs(d)


def test_pins_missing_inputs_privacy_and_no_overwrite(tmp_path):
    f = tmp_path / "x.json"
    f.write_text("{}")
    with pytest.raises(imp.InquiryRefused, match="sha256"):
        imp.read_pinned(f, "0" * 64)
    with pytest.raises(imp.InquiryRefused, match="never falls back"):
        imp.load_production(tmp_path)
    text = json.dumps(build())
    assert SECRET not in text and "heapq.nlargest" not in text and "return g(a, b)" not in text
    out = tmp_path / "out.json"
    out.write_text("keep")
    assert imp.main(["--out", str(out)]) == 2 and out.read_text() == "keep"


def test_similarity_definitions_equal_the_pinned_helper_without_importing_it():
    src = (ROOT / "scripts/review_candidate_frame_mrl15.py").read_text()
    assert hashlib.sha256(src.encode()).hexdigest() == imp.INPUTS["similarity_helper"][1]
    tree = ast.parse(src)
    consts = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ("CODE_STOP", "TEXT_STOP"):
            node = n.value.right if isinstance(n.value, ast.BinOp) else n.value
            consts[n.targets[0].id] = ast.literal_eval(node)
    import keyword
    assert set(keyword.kwlist) | consts["CODE_STOP"] == imp.CODE_STOP and consts["TEXT_STOP"] == imp.TEXT_STOP
    assert imp.sim((frozenset("ab"), frozenset()), (frozenset("abc"), frozenset())) == round(2 / 3, 4)


def test_script_is_static_only():
    tree = ast.parse((ROOT / "scripts/prepare_import_layout_candidate_inputs_20260927.py").read_text())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert mods == {"__future__", "argparse", "ast", "hashlib", "json", "keyword", "re", "warnings", "pathlib"}
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    assert not called & {"eval", "exec", "compile", "__import__", "import_module", "run", "Popen", "system", "urlopen"}


REAL = all((ROOT / rel).exists() for rel, _ in imp.INPUTS.values())


@pytest.mark.skipif(not REAL, reason="pinned ignored sources not present")
def test_real_inputs_select_exactly_103_and_verify_the_lead_facts():
    doc = imp.reconcile_inputs(imp.load_production(ROOT))
    assert doc["n_rows"] == 103 and [r["task_id"] for r in doc["rows"]] == sorted(r["task_id"] for r in doc["rows"])
    assert [r["task_id"] for r in doc["rows"] if r["exposure_flags_from_named_records"]["in_prior_seen_config"]] == [43, 220]
    assert [r["task_id"] for r in doc["rows"] if r["challenge_test_count"]] == [43, 44]
    assert all(len(r["prior_neighbors_top6"]) == 6 and len(r["within_103_neighbors_top6"]) == 6 for r in doc["rows"])


# ---------------------------------------------------------------- MRL-40 draft-review regressions (aa05b38): exact shape gate
@pytest.mark.parametrize("code", [
    "import os\ndef f(x: int):\n    return x\n",                 # annotated parameter
    "import os\ndef f(x) -> int:\n    return x\n",                 # return annotation
    "import os\ndef f(x=1):\n    return x\n",                      # default
    "import os\ndef f(*xs):\n    return xs\n",                     # varargs
    "import os\ndef f(**kw):\n    return kw\n",                    # kwargs
    "import os\ndef f(*, x):\n    return x\n",                     # keyword-only
    "import os\ndef f(x, /):\n    return x\n",                     # positional-only
    "import functools\n@functools.cache\ndef f(x):\n    return x\n",  # decorator
    "def f(x):\n    return x\n",                                    # no import
    "import os\ny = 1\ndef f(x):\n    return x\n",                # extra non-import statement
    "import os\ndef f(x):\n    return x\ndef g(y):\n    return y\n",  # two functions
])
def test_layout_gate_refuses_every_non_conforming_shape(code):
    with pytest.raises(imp.InquiryRefused):
        imp.layout(code)


@pytest.mark.parametrize("code,imports", [
    ("import numpy as np\ndef f(x):\n    return np.sum(x)\n", [{"kind": "import", "module": None, "level": 0, "names": [{"name": "numpy", "alias": "np"}]}]),
    ("from collections import Counter, defaultdict as dd\ndef f(x):\n    return Counter(x)\n",
     [{"kind": "from", "module": "collections", "level": 0, "names": [{"name": "Counter", "alias": None}, {"name": "defaultdict", "alias": "dd"}]}]),
])
def test_layout_gate_accepts_alias_and_from_imports(code, imports):
    lay = imp.layout(code)
    assert lay["top_level_imports"] == imports and lay["plain_signature_under_old_rule"] is True


def test_layout_rule_matches_the_old_screen_source():
    src = (ROOT / "scripts/screen_landmark_pool.py").read_text()
    assert "a.posonlyargs or a.kwonlyargs or a.defaults or a.kwarg or a.vararg or fn.decorator_list or fn.returns" in src
    assert "any(x.annotation for x in a.args)" in src
