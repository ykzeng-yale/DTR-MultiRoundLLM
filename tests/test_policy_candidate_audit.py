"""MRL-36 tests for the candidate-audit input preparation. Small synthetic fixtures only (plus an optional read-only check of
the pinned local sources when present); nothing is executed: assertions and code are parsed, never evaluated."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("prepare_policy_candidate_audit", ROOT / "scripts/prepare_policy_candidate_audit.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)
HELPER = pc.load_helper(ROOT / "scripts/review_candidate_frame_mrl15.py", pc.PINS["helper"])
OTHER_IDS = [i for i in range(1000, 1200)][:198 - len(pc.EXPECTED_IDS)]


def mbpp_row(t, text, code, first="assert f(1) == 2"):
    return {"task_id": t, "text": text, "code": code, "test_list": [first, "assert f(2) == 3", "assert f(3) == 4"]}


def fixture():
    records, mbpp = [], {}
    order = list(pc.EXPECTED_IDS) + OTHER_IDS
    for rank, t in enumerate(order, 1):
        cand = t in pc.EXPECTED_IDS
        records.append({"rank": rank, "task_id": t, "source_record": "synthetic", "source_disposition": "synthetic",
                        "source_review_basis": "synthetic", "historical_class": "candidate" if cand else "hold",
                        "prior_receiver_development": False, "current_overlay": "none", "measurement_development": False,
                        "approved_evaluation_roster": False})
        mbpp[t] = mbpp_row(t, f"Write a function to do task{t} alpha{t}.", f"def f{t}(x):\n    return x + {t}\n")
    for t in pc.E11_ROOTS:
        mbpp[t] = mbpp_row(t, f"E11 prior task{t}.", f"def e{t}(y):\n    return y\n")
    pool = [{"uid": "mbpp/7", "benchmark": "mbpp", "source_task_id": "7", "prompt": "canonical words zeta", "reference": "def z(q):\n    return q\n"},
            {"uid": "humaneval/0", "benchmark": "humaneval", "source_task_id": "0", "prompt": "Human eval words", "reference": "def h(a):\n    return a\n"}]
    mbpp[7] = mbpp_row(7, "original words eta", "def o(w):\n    return w\n")
    return {"records": records}, mbpp, pool


def build(recon=None, mbpp=None, pool=None):
    r, m, p = fixture()
    return pc.build(recon or r, mbpp or m, pool if pool is not None else p, HELPER, {"synthetic": True})


def test_deterministic_and_complete_with_pending_unapproved_records():
    a, b = build(), build()
    assert a == b and [r["task_id"] for r in a["records"]] == list(pc.EXPECTED_IDS)
    assert all(r["family_adjudication"] == "pending" and r["approved"] is False for r in a["records"])
    assert all(len(r["prior_neighbors_top6"]) == 6 and len(r["frame_neighbors_top6"]) == 6 for r in a["records"])
    rec877 = next(r for r in a["records"] if r["task_id"] == 877)
    assert rec877["exposure_tags"]["measurement_development"].startswith("measurement_development")


def test_prior_retrieval_dedups_uids_picks_the_winning_variant_and_breaks_ties_by_uid_then_scope():
    recon, mbpp, pool = fixture()
    root = pc.EXPECTED_IDS[0]
    pool[0]["prompt"] = mbpp[root]["text"]  # canonical variant of mbpp/7 matches the root exactly
    rec = build(recon, mbpp, pool)["records"][0]
    top = rec["prior_neighbors_top6"]
    assert top[0]["uid"] == "mbpp/7" and top[0]["winning_variant"] == "canonical" and top[0]["score"] == 1.0
    assert [n["uid"] for n in top].count("mbpp/7") == 1  # one entry per UID (max over variants)
    mbpp[7]["text"] = mbpp[root]["text"]
    pool[0]["prompt"] = "unrelated"
    top = build(recon, mbpp, pool)["records"][0]["prior_neighbors_top6"]
    assert top[0]["uid"] == "mbpp/7" and top[0]["winning_variant"] == "original_mbpp"
    rest = top[1:]
    keys = [(-n["score"], n["uid"], n["scope"]) for n in rest]
    assert keys == sorted(keys)
    assert {n["scope"] for n in build()["records"][0]["prior_neighbors_top6"]} >= {"e11_dev"}  # E11 included as prior comparator


def test_self_exclusion_in_prior_and_frame_retrieval():
    recon, mbpp, pool = fixture()
    root = pc.EXPECTED_IDS[3]
    pool.append({"uid": f"mbpp/{root}", "benchmark": "mbpp", "source_task_id": str(root), "prompt": mbpp[root]["text"],
                 "reference": mbpp[root]["code"]})
    rec = build(recon, mbpp, pool)["records"][3]
    assert f"mbpp/{root}" not in [n["uid"] for n in rec["prior_neighbors_top6"]]
    assert root not in [n["task_id"] for n in rec["frame_neighbors_top6"]]
    assert rec["exposure_tags"]["in_canonical_prior_pool"] is True
    frame = rec["frame_neighbors_top6"]
    assert [(-n["score"], n["task_id"]) for n in frame] == sorted((-n["score"], n["task_id"]) for n in frame)
    assert all({"source_rank", "historical_class", "source_disposition"} <= set(n) for n in frame)


def test_input_mismatches_are_refused(tmp_path):
    recon, mbpp, pool = fixture()
    bad = copy.deepcopy(recon)
    bad["records"][0]["historical_class"] = "hold"
    with pytest.raises(pc.InputRefused):
        pc.build(bad, mbpp, pool, HELPER, {})
    with pytest.raises(pc.InputRefused):
        pc.build({"records": recon["records"][:-1]}, mbpp, pool, HELPER, {})
    with pytest.raises(pc.InputRefused):
        pc.build(recon, mbpp, pool + [dict(pool[0])], HELPER, {})  # duplicate pool UID
    missing = dict(mbpp)
    del missing[pc.E11_ROOTS[0]]
    with pytest.raises(pc.InputRefused):
        pc.build(recon, missing, pool, HELPER, {})
    f = tmp_path / "x.json"
    f.write_text("{}")
    with pytest.raises(pc.InputRefused, match="pin"):
        pc.read_pinned(f, "0" * 64)
    with pytest.raises(pc.InputRefused, match="unreadable"):
        pc.read_pinned(tmp_path / "absent", None)
    with pytest.raises(pc.InputRefused):
        pc.load_helper(f, pc.PINS["helper"])


@pytest.mark.parametrize("text,args_literal,expected_literal", [
    ("assert f(x) == 2", False, True), ("assert f(1) == g(2)", True, False), ("assert f(undefined_name + 1) == open('p')", False, False),
    ("assert f([1, 2], 'a') == (3, {'k': 1})", True, True),
])
def test_nonliteral_expressions_are_flagged_unsupported_never_evaluated(text, args_literal, expected_literal):
    shape = pc.first_assertion_shape(text, "f")
    assert shape["all_call_arguments_literal"] is args_literal and shape["expected_literal"] is expected_literal
    for info in shape["args"] + shape["comparators"]:
        if not info["literal"]:
            assert info["status"] == "nonliteral_unsupported" and "value_type" not in info
        else:
            assert set(info) <= {"literal", "node_type", "value_type", "value_repr_sha256", "container_size"}
    assert "1, 2" not in json.dumps(shape) and "'a'" not in json.dumps(shape)  # values are hashed, not retained


def test_non_assert_and_non_call_shapes_are_reported_not_repaired():
    assert pc.first_assertion_shape("x = 1", "f")["parse"] == "not a single assert"
    assert pc.first_assertion_shape("assert (", "f")["parse"].startswith("unparseable")
    shape = pc.first_assertion_shape("assert set(f(1)) == set([1])", "f")
    assert shape["call_name_is_entry_point"] is False and shape["all_call_arguments_literal"] is False


def test_existing_output_is_never_overwritten(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("keep")
    assert pc.main(["--out", str(out)]) == 2 and out.read_text() == "keep"


def test_script_never_executes_benchmark_code():
    tree = ast.parse((ROOT / "scripts/prepare_policy_candidate_audit.py").read_text())
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    assert not called & {"eval", "exec", "compile", "__import__", "system", "Popen", "run", "urlopen"}


REAL = all((ROOT / p).exists() for p in pc.DEFAULT_PATHS.values())


@pytest.mark.skipif(not REAL, reason="pinned local sources not present (gitignored work/)")
def test_real_pinned_sources_give_43_pending_records_without_raw_material():
    recon, mbpp, pool, helper, prov = pc.load_inputs({k: ROOT / v for k, v in pc.DEFAULT_PATHS.items()}, pc.PINS)
    doc = pc.build(recon, mbpp, pool, helper, prov)
    assert doc["root_order"] == list(pc.EXPECTED_IDS) and doc["n_roots"] == 43
    text = json.dumps(doc, ensure_ascii=False)
    for t in [*(r["task_id"] for r in recon["records"]), *pc.E11_ROOTS]:
        for a in mbpp[t]["test_list"]:
            assert json.dumps(a, ensure_ascii=False)[1:-1] not in text
        assert json.dumps(mbpp[t]["code"], ensure_ascii=False)[1:-1] not in text
