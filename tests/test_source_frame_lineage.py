"""MRL-39 tests for the full-source lineage reconciliation. Small synthetic partitions through the explicit synthetic seam
(`reconcile(data, expected_counts)`), plus an optional read-only check of the pinned real inputs. Nothing is executed."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("lineage", ROOT / "scripts/reconcile_source_frame_lineage_20260927.py")
lin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lin)

SYN_COUNTS = {"canonical": 2, "prior_literal_duplicate": 1, "mechanical_interface": 1, "mechanical_setup": 1,
              "mrl15_prior_seen": 1, "mrl15_neighbor": 1, "mrl15_family_member": 1, "reviewed_frame": 4}
SECRET = "def secret_reference_body():"


def synthetic():
    mbpp = [{"task_id": t, "text": f"SYNTHETIC task {t}", "code": f"{SECRET} return {t}",
             "test_list": [f"assert secret_call({t}) == {t}"]} for t in range(1, 13)]
    return {
        "mbpp": mbpp,
        "canonical_pool": [{"uid": "mbpp/1", "benchmark": "mbpp", "source_task_id": "1"},
                           {"uid": "mbpp/2", "benchmark": "mbpp", "source_task_id": "2"},
                           {"uid": "humaneval/0", "benchmark": "humaneval", "source_task_id": "0"}],
        "acquisition": {"full_task_count": 12, "candidate_ids": list(range(3, 13)),
                        "after_prior_prompt_duplicate_exclusion_ids": list(range(4, 13)),
                        "exact_normalized_prior_prompt_duplicates": [{"candidate_id": 3, "prior_root_ids": ["mbpp/1"]}]},
        "screen_summary": {},
        "screen_per_candidate": [{"task_id": 4, "gate": "G2_interface", "reason": "not_single_function"},
                                 {"task_id": 5, "gate": "G3_setup", "reason": "setup_or_challenge_tests_present"}]
                                + [{"task_id": t, "gate": "USABLE", "reason": None} for t in range(6, 13)],
        "screen_usable": list(range(6, 13)),
        "mrl15_manifest": {"eligible_ordered_ids": [9, 11, 10, 12],
                           "excluded": {"6": {"step": "i_prior_seen", "reason": "prior seen"},
                                        "7": {"step": "ii_near_duplicate_of_prior_seen", "reason": "score 0.6 vs prior-seen mbpp/1"},
                                        "8": {"step": "ii_within_frame_family", "reason": "family member of 9"}},
                           "source": {"e11_dev_roots": [7]}},
        "reconciliation_198": {"records": [
            {"rank": i, "task_id": t, "historical_class": "candidate" if t != 10 else "hold", "source_disposition": "syn",
             "current_overlay": "none", "prior_receiver_development": t == 9, "measurement_development": False,
             "source_record": "docs/e12_contract_review_20260922.md" if t == 9 else "syn"} for i, t in enumerate([9, 11, 10, 12], 1)]},
        "adjudication_43": {"records": [{"task_id": t, "family_axis": "no_direct_prior_relation_found", "contract_axis": "ok",
                                         "family_reason": "PRIVATE-ISH NARRATIVE", "approved_evaluation_roster": False} for t in (11, 12)]},
        "refinement_16": {"records": [{"task_id": 12, "prior_family_axis": "plausible_shared_family",
                                       "family_axis": "definite_prior_family", "contract_axis_unchanged": "ok",
                                       "witness": "WITNESS TEXT", "approved_evaluation_roster": False}]},
        "prior_seen_config": {"prior_seen_root_ids": ["mbpp/1", "humaneval/0", "mbpp/6"]},
    }


def test_synthetic_partition_rows_flags_and_order():
    doc = lin.reconcile(synthetic(), SYN_COUNTS)
    assert doc["n_rows"] == 12 and [r["task_id"] for r in doc["rows"]] == list(range(1, 13))
    cat = {r["task_id"]: r["terminal_category"] for r in doc["rows"]}
    assert cat == {1: "canonical", 2: "canonical", 3: "prior_literal_duplicate", 4: "mechanical_interface", 5: "mechanical_setup",
                   6: "mrl15_prior_seen", 7: "mrl15_neighbor", 8: "mrl15_family_member", 9: "reviewed_frame",
                   10: "reviewed_frame", 11: "reviewed_frame", 12: "reviewed_frame"}
    rows = {r["task_id"]: r for r in doc["rows"]}
    assert rows[11]["frame_rank"] == 2 and rows[9]["frame_rank"] == 1 and rows[3]["frame_rank"] is None
    assert rows[9]["flags_from_named_records"]["e12_contract_review_record"] and rows[9]["flags_from_named_records"]["prior_receiver_development_recorded"]
    assert rows[7]["flags_from_named_records"]["e11_dev_root"] and rows[6]["flags_from_named_records"]["prior_seen_dev_release_v1c"]
    assert rows[12]["refinement_16"]["family_axis"] == "definite_prior_family" and rows[11]["refinement_16"] is None
    assert rows[1]["canonical_uid"] == "mbpp/1" and rows[3]["category_evidence"] == {"prior_root_ids": ["mbpp/1"]}
    assert all(r["approved_for_evaluation"] is False and r["exposure"].startswith("unknown") for r in doc["rows"])
    assert lin.reconcile(synthetic(), SYN_COUNTS) == doc  # deterministic


def mutate(fn):
    d = synthetic()
    fn(d)
    return d


@pytest.mark.parametrize("fn", [
    lambda d: d["mbpp"].pop(),                                                                 # missing ID
    lambda d: d["mbpp"].append(dict(d["mbpp"][0])),                                            # duplicate ID
    lambda d: d["canonical_pool"].append({"uid": "mbpp/3", "benchmark": "mbpp", "source_task_id": "3"}),  # canonical/candidate overlap
    lambda d: d["mrl15_manifest"]["excluded"].update({"9": {"step": "i_prior_seen", "reason": "x"}}),    # excluded and in frame
    lambda d: d["screen_usable"].append(4),                                                    # usable set mismatch
    lambda d: d["adjudication_43"]["records"].append({"task_id": 8}),                          # adjudication outside the frame
    lambda d: d["refinement_16"]["records"].append({"task_id": 9}),                            # refinement outside adjudication
    lambda d: d["reconciliation_198"]["records"].reverse() or [r.update(rank=i) for i, r in enumerate(d["reconciliation_198"]["records"], 1)],
    lambda d: d["reconciliation_198"]["records"].pop(),                                        # missing later row
    lambda d: d["mrl15_manifest"]["excluded"].update({"8": {"step": "unknown_step", "reason": "x"}}),
    lambda d: d["acquisition"]["exact_normalized_prior_prompt_duplicates"].clear(),            # unexplained removal
    lambda d: d["screen_per_candidate"].append({"task_id": 3, "gate": "USABLE"}),              # screen input mismatch
])
def test_stage_set_failures_are_refused_not_patched(fn):
    with pytest.raises(lin.LineageRefused):
        lin.reconcile(mutate(fn), SYN_COUNTS)


def test_expected_counts_are_verified_never_forced():
    wrong = dict(SYN_COUNTS, canonical=3, reviewed_frame=3)
    with pytest.raises(lin.LineageRefused, match="differ from the expected"):
        lin.reconcile(synthetic(), wrong)


def test_source_drift_and_missing_inputs_are_refused(tmp_path):
    f = tmp_path / "x.json"
    f.write_text("{}")
    with pytest.raises(lin.LineageRefused, match="pin"):
        lin.read_pinned(f, "0" * 64)
    with pytest.raises(lin.LineageRefused, match="unreadable"):
        lin.read_pinned(tmp_path / "absent.json", "0" * 64)
    with pytest.raises(lin.LineageRefused):
        lin.load_production(tmp_path)  # a directory without the pinned inputs never falls back to anything


def test_output_emits_digests_only_no_code_assertions_or_narratives():
    doc = lin.reconcile(synthetic(), SYN_COUNTS)
    text = json.dumps(doc)
    assert SECRET not in text and "secret_call" not in text and "SYNTHETIC task" not in text
    assert "PRIVATE-ISH NARRATIVE" not in text and "WITNESS TEXT" not in text
    row = doc["rows"][0]
    assert row["source_digests"]["reference_sha256"] == hashlib.sha256(f"{SECRET} return 1".encode()).hexdigest()


def test_existing_output_is_never_overwritten(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("keep")
    assert lin.main(["--out", str(out)]) == 2 and out.read_text() == "keep"


def test_script_is_pure_data_processing():
    tree = ast.parse((ROOT / "scripts/reconcile_source_frame_lineage_20260927.py").read_text())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert mods == {"__future__", "argparse", "hashlib", "json", "pathlib"}
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    assert not called & {"eval", "exec", "compile", "__import__", "run", "Popen", "system", "urlopen", "literal_eval", "parse"}


REAL = all((ROOT / rel).exists() for rel, _ in lin.INPUTS.values())


@pytest.mark.skipif(not REAL, reason="pinned ignored sources not present")
def test_real_inputs_verify_the_expected_partition():
    doc = lin.reconcile(lin.load_production(ROOT))
    assert doc["n_rows"] == 974 and doc["category_counts"] == lin.EXPECTED_COUNTS and all(doc["set_checks"].values())
    assert sum(r["in_reviewed_frame_198"] for r in doc["rows"]) == 198
    assert sum(r["adjudication_43"] is not None for r in doc["rows"]) == 43 and sum(r["refinement_16"] is not None for r in doc["rows"]) == 16
    assert all(r["approved_for_evaluation"] is False for r in doc["rows"])
