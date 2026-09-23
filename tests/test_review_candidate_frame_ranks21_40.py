"""Tests for the MRL-22 mechanical screen of candidate-frame ranks 21-40.

Source-only: nothing here executes a candidate, a reference, a model or a sandbox.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _load("rcf2140", "scripts/review_candidate_frame_ranks21_40.py")
M15 = _load("rcf15_for_2140", "scripts/review_candidate_frame_mrl15.py")

OUT_DIR = ROOT / "results/frame_review_ranks21_40_20260923"
COMMITTED_IDS = [911, 211, 701, 960, 667, 344, 370, 484, 524, 814,
                 346, 187, 508, 194, 356, 366, 302, 670, 376, 650]

_frame_ok = (R.FRAME_DIR / "manifest.json").exists()
_source_ok = any((ROOT / c).exists() for c in R.SOURCE_FALLBACKS)
pytestmark = pytest.mark.skipif(not (_frame_ok and _source_ok),
                                reason="pinned MRL-15 frame or MBPP source absent")


@pytest.fixture(scope="module")
def built():
    return R.build()


@pytest.fixture(scope="module")
def source_path():
    fm, _ = R.load_frame_manifest()
    path, _, _ = R.resolve_source(fm)
    return path


# --- scope: the exact 20 ids, in the committed order --------------------------------

def test_expected_ids_pinned_in_script():
    assert R.EXPECTED_IDS == COMMITTED_IDS
    assert (R.RANK_LO, R.RANK_HI) == (21, 40)
    assert len(COMMITTED_IDS) == len(set(COMMITTED_IDS)) == 20


def test_ids_match_frame_manifest_slice():
    fm, sha = R.load_frame_manifest()
    assert sha == R.FRAME_MANIFEST_SHA256
    ordered = fm["eligible_ordered_ids"]
    assert len(ordered) == 198
    assert ordered[20:40] == COMMITTED_IDS


def test_records_are_exactly_ranks_21_40_in_order(built):
    manifest, records = built
    assert [r["task_id"] for r in records] == COMMITTED_IDS
    assert [r["rank"] for r in records] == list(range(21, 41))
    assert manifest["scope"]["task_ids_in_committed_order"] == COMMITTED_IDS
    assert manifest["scope"]["ranks"] == [21, 40]
    assert manifest["scope"]["ranks_41_198_inspected"] is False
    assert manifest["scope"]["no_backfill_beyond_rank_40"] is True
    assert manifest["scope"]["no_rerank"] is True


def test_no_overlap_with_already_reviewed_ranks_1_20(built):
    manifest, records = built
    fm, _ = R.load_frame_manifest()
    assert not set(fm["review_ids"]) & {r["task_id"] for r in records}
    assert manifest["carried_forward"]["ranks_1_20_ids"] == fm["review_ids"]


def test_refuses_when_slice_is_not_the_committed_list(monkeypatch, source_path):
    fm, _ = R.load_frame_manifest()
    tampered = json.loads(json.dumps(fm))
    o = tampered["eligible_ordered_ids"]
    o[20], o[21] = o[21], o[20]
    monkeypatch.setattr(R, "load_frame_manifest",
                        lambda path=None: (tampered, R.FRAME_MANIFEST_SHA256))
    with pytest.raises(SystemExit) as e:
        R.build(source_path=source_path)
    assert "not the MRL-22 list" in str(e.value)


# --- criteria identity against the MRL-15 module ------------------------------------

def test_criteria_are_the_imported_mrl15_objects():
    assert R.M.SEED == M15.SEED == "mrl15-frame-seed-20260922"
    assert R.M.SIM_THRESHOLD == M15.SIM_THRESHOLD == 0.5
    assert R.M.SIM_RULE == M15.SIM_RULE
    assert R.M.N_REVIEW == M15.N_REVIEW == 20
    assert R.M.CODE_STOP == M15.CODE_STOP
    assert R.M.TEXT_STOP == M15.TEXT_STOP
    assert R.M.E11_DEV_ROOTS == M15.E11_DEV_ROOTS
    assert R.M.MBPP_SHA256 == M15.MBPP_SHA256
    assert R.M.spec_review is R.M.spec_review
    # No threshold or stop list is re-declared in the ranks 21-40 script.
    text = (ROOT / "scripts/review_candidate_frame_ranks21_40.py").read_text()
    for banned in ("SIM_THRESHOLD =", "SIM_RULE =", "CODE_STOP =", "TEXT_STOP =",
                   "SEED =", "N_REVIEW =", "def spec_review", "def sim(", "def jac("):
        assert banned not in text


def test_manifest_criteria_identity_block(built):
    manifest, _ = built
    fm, _ = R.load_frame_manifest()
    ident = manifest["criteria_identity"]
    assert ident["similarity_threshold"] == fm["preregistered"]["similarity_threshold"]
    assert ident["source_module"] == "scripts/review_candidate_frame_mrl15.py"
    assert ident["source_module_sha256"] == hashlib.sha256(
        (ROOT / "scripts/review_candidate_frame_mrl15.py").read_bytes()).hexdigest()
    assert manifest["preregistered"] == fm["preregistered"]
    assert manifest["preregistered"]["outcome_information_used"] == "none"
    for key in ("seed", "order_key", "similarity_rule", "family_rule",
                "similarity_threshold", "mbpp_sha256", "e11_dev_roots"):
        assert key in ident["checked_against_preregistered"]
    assert manifest["criteria_reproduction"]["eligible_ordered_ids_reproduced"] is True
    assert manifest["criteria_reproduction"]["excluded_map_reproduced"] is True


def test_criteria_identity_refuses_on_changed_preregistration():
    fm, _ = R.load_frame_manifest()
    bad = json.loads(json.dumps(fm))
    bad["preregistered"]["similarity_threshold"] = 0.6
    with pytest.raises(SystemExit) as e:
        R.criteria_identity(bad)
    assert "criteria identity failed" in str(e.value)


def test_selection_reproduces_the_committed_frame(source_path):
    fm, _ = R.load_frame_manifest()
    _, mbpp, _ = R.resolve_source(fm, source_path)
    fr = R.rebuild_frame(mbpp)
    assert fr["ordered"] == fm["eligible_ordered_ids"]
    assert {str(k): v for k, v in sorted(fr["excluded"].items())} == fm["excluded"]


# --- source hash verification -------------------------------------------------------

def test_source_hash_verified_and_recorded(built, source_path):
    manifest, _ = built
    fm, _ = R.load_frame_manifest()
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert digest == fm["source"]["mbpp_sha256"] == M15.MBPP_SHA256
    assert manifest["source"]["mbpp_sha256"] == digest
    assert manifest["source"]["sha256_verified_before_read"] is True
    assert manifest["source"]["mbpp_rows"] == fm["source"]["mbpp_rows"] == 974
    assert (ROOT / manifest["source"]["mbpp_path"]).exists()


def test_refuses_tampered_source(tmp_path, source_path):
    raw = source_path.read_bytes()
    bad = tmp_path / "mbpp_tampered.jsonl"
    bad.write_bytes(raw.replace(b"Write a function", b"Write a  function", 1))
    assert hashlib.sha256(bad.read_bytes()).hexdigest() != M15.MBPP_SHA256
    with pytest.raises(SystemExit) as e:
        R.build(source_path=bad)
    assert "sha256 mismatch" in str(e.value)


def test_refuses_tampered_frame_manifest(tmp_path):
    fm_bytes = (R.FRAME_DIR / "manifest.json").read_bytes()
    bad = tmp_path / "manifest.json"
    bad.write_bytes(fm_bytes + b"\n")
    with pytest.raises(SystemExit) as e:
        R.load_frame_manifest(bad)
    assert "frame manifest sha256 mismatch" in str(e.value)


# --- determinism and committed bytes -----------------------------------------------

def test_determinism_matches_committed_bytes(built):
    manifest, records = built
    man_bytes, rec_bytes = R.serialize(manifest, records)
    m2, r2 = R.build()
    man2, rec2 = R.serialize(m2, r2)
    assert (man_bytes, rec_bytes) == (man2, rec2)
    if OUT_DIR.exists():
        assert (OUT_DIR / "records.json").read_bytes() == rec_bytes
        assert (OUT_DIR / "manifest.json").read_bytes() == man_bytes
        committed = json.loads((OUT_DIR / "manifest.json").read_text())
        assert committed["records_sha256"] == hashlib.sha256(rec_bytes).hexdigest()


def test_refuses_to_overwrite(tmp_path):
    out = tmp_path / "out"
    assert R.main(["--out-dir", str(out)]) == 0
    assert (out / "records.json").exists() and (out / "manifest.json").exists()
    with pytest.raises(SystemExit) as e:
        R.main(["--out-dir", str(out)])
    assert "refusing to overwrite" in str(e.value)


def test_refuses_to_write_into_the_immutable_frame_dir():
    with pytest.raises(SystemExit) as e:
        R.main(["--out-dir", str(R.FRAME_DIR)])
    assert "refusing to overwrite" in str(e.value) or "immutable" in str(e.value)
    assert sorted(p.name for p in R.FRAME_DIR.iterdir() if p.is_file()) == \
        ["manifest.json", "records.json"]


# --- no outcome information anywhere ------------------------------------------------

def test_no_outcome_or_grade_or_private_paths_opened(built):
    manifest, _ = built
    opened = manifest["outcome_inspection"]["inputs_opened"]
    assert opened
    for p in opened:
        low = p.lower()
        for marker in R.FORBIDDEN_INPUT_MARKERS:
            assert marker not in low, f"{p} looks outcome-bearing"
        assert (ROOT / p).exists()
    assert set(opened) <= {
        "results/frame_review_mrl15_20260922T021718Z/manifest.json",
        "results/frame_review_mrl15_20260922T021718Z/records.json",
        "scripts/review_candidate_frame_mrl15.py",
        "work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl",
        "work/sources/mbpp_full.jsonl",
        "results/pool_screen_20260921T131231Z/usable_ids.json",
        "results/pool_screen_20260921T131231Z/summary.json",
        "results/pool_screen_20260921T131231Z/per_candidate.json",
        "experiments/landmark/dev_release_v1c/config.json",
        "docs/e12_contract_review_20260922.md",
    }


def test_outcome_inspection_declared(built):
    manifest, records = built
    oi = manifest["outcome_inspection"]
    assert oi["model_outcomes_inspected"] is False
    assert oi["outcome_fields_read"] == []
    assert oi["decision_function_reads_no_outcome_field"] is True
    assert set(oi["source_fields_read"]) == set(R.SOURCE_FIELDS_READ)
    assert manifest["execution"] == {
        "exec_eval_subprocess": False, "model_calls": 0, "model_tokens": 0,
        "network": False, "installs": 0,
        "static_ops": ["ast.parse", "compile", "hashlib.sha256", "json.loads"]}
    def keys(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k
                yield from keys(v)
        elif isinstance(o, list):
            for v in o:
                yield from keys(v)

    all_keys = set(keys(manifest)) | set(keys(records))
    for k in all_keys:
        low = k.lower()
        for bad in ("pass_rate", "public_score", "private_score", "grade", "reward",
                    "receiver", "completion", "hidden_score"):
            assert bad not in low, f"outcome-shaped field {k}"
    assert "outcome_information_used" in all_keys  # declared as "none"
    for r in records:
        assert r["outcome_information_used"] == "none"
        assert r["mechanical_decision"] == r["spec_review"]["decision"]
        assert r["mechanical_decision"] in ("include", "hold", "exclude")


def test_decision_function_is_a_pure_source_function(source_path):
    """spec_review's arguments are derived only from the pinned MBPP row."""
    fm, _ = R.load_frame_manifest()
    _, mbpp, _ = R.resolve_source(fm, source_path)
    row = mbpp[COMMITTED_IDS[0]]
    ep, arity, info = R.M.entry_point(row["code"])
    a = R.M.spec_review(row, ep, arity, info)
    b = R.M.spec_review(dict(row), ep, arity, dict(info))
    assert a == b
    assert set(a) == {"flags", "decision", "uncertainty", "note"}


# --- required per-record fields and carried-forward holds ---------------------------

def test_record_fields_and_hashes(built, source_path):
    _, records = built
    fm, _ = R.load_frame_manifest()
    _, mbpp, _ = R.resolve_source(fm, source_path)
    required = {"rank", "task_id", "seed_hash", "text", "text_sha256",
                "reference_code_sha256", "test_list_sha256", "entry_point", "arity",
                "n_official_tests", "n_challenge_tests", "provisional_family",
                "family_size_in_frame", "nearest_prior_seen", "nearest_in_frame",
                "spec_review", "mechanical_decision", "outcome_information_used"}
    prior_keys = set(json.loads((R.FRAME_DIR / "records.json").read_text())[0])
    for r in records:
        assert required <= set(r)
        assert prior_keys <= set(r), "shape must match the MRL-15 records"
        row = mbpp[r["task_id"]]
        assert r["text"] == row["text"]
        assert r["text_sha256"] == hashlib.sha256(row["text"].encode()).hexdigest()
        assert r["reference_code_sha256"] == hashlib.sha256(row["code"].encode()).hexdigest()
        assert r["seed_hash"] == R.M.seed_key(r["task_id"])
        assert r["entry_point"] and isinstance(r["arity"], int)
        assert r["n_official_tests"] == len(row["test_list"])
        assert r["family_size_in_frame"] >= 1
        assert 0.0 <= r["nearest_prior_seen"]["score"] < R.M.SIM_THRESHOLD


def test_no_reference_code_or_assertion_text_leaks(built, source_path):
    manifest, records = built
    fm, _ = R.load_frame_manifest()
    _, mbpp, _ = R.resolve_source(fm, source_path)
    blob = json.dumps(records) + json.dumps(manifest)
    for r in records:
        row = mbpp[r["task_id"]]
        for t in row["test_list"]:
            assert t not in blob and json.dumps(t)[1:-1] not in blob
        body = row["code"].strip()
        assert body not in blob and json.dumps(body)[1:-1] not in blob


def test_carried_forward_holds_preserved(built):
    manifest, records = built
    cf = manifest["carried_forward"]
    fm, _ = R.load_frame_manifest()
    held = {h["task_id"]: h for h in cf["mechanical_holds_ranks_1_20"]}
    assert set(held) == {359, 349}
    assert held[359]["rank"] == 3 and held[349]["rank"] == 16
    for h in held.values():
        assert h["status"] == "hold" and h["revisited"] is False
    assert cf["semantic_holds_ranks_1_20"]["ids"] == [31, 847, 907, 963]
    assert cf["semantic_holds_ranks_1_20"]["revisited"] is False
    reviewed = {r["task_id"] for r in records}
    assert not reviewed & ({359, 349} | {31, 847, 907, 963})
    assert cf["mechanical_exclusions_preserved"] == len(fm["excluded"])
    assert cf["mechanical_exclusions_sha256"] == hashlib.sha256(
        json.dumps(fm["excluded"], sort_keys=True).encode()).hexdigest()


def test_carried_forward_refuses_if_a_prior_hold_changed(monkeypatch):
    fm, _ = R.load_frame_manifest()
    monkeypatch.setattr(R, "CARRIED_MECHANICAL_HOLDS", (359, 349, 918))
    with pytest.raises(SystemExit) as e:
        R.carried_forward(fm)
    assert "hold" in str(e.value)
