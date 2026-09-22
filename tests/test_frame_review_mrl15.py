import hashlib
import json
from pathlib import Path

import pytest

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "rcf15", ROOT / "scripts/review_candidate_frame_mrl15.py")
rcf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcf)

pytestmark = pytest.mark.skipif(not rcf.MBPP_PATH.exists(), reason="pinned MBPP source absent")


@pytest.fixture(scope="module")
def built():
    return rcf.build()


def test_determinism(built):
    m2, r2 = rcf.build()
    m1, r1 = built
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    assert m1["eligible_ordered_ids"] == m2["eligible_ordered_ids"]


def test_exclusion_counts_consistent(built):
    m, r = built
    c = m["counts"]
    assert c["start_frame"] == 396
    assert c["start_frame"] >= c["after_i_prior_seen"] >= \
        c["after_ii_prior_seen_near_duplicate"] >= c["after_ii_within_frame_family"]
    steps = [v["step"] for v in m["excluded"].values()]
    assert steps.count("i_prior_seen") == c["start_frame"] - c["after_i_prior_seen"]
    assert steps.count("ii_near_duplicate_of_prior_seen") == \
        c["after_i_prior_seen"] - c["after_ii_prior_seen_near_duplicate"]
    assert steps.count("ii_within_frame_family") == \
        c["after_ii_prior_seen_near_duplicate"] - c["after_ii_within_frame_family"]
    assert len(m["eligible_ordered_ids"]) == c["after_ii_within_frame_family"]
    assert len(r) == min(20, c["after_ii_within_frame_family"])
    prior = set(rcf.E11_DEV_ROOTS)
    assert not prior & set(m["eligible_ordered_ids"])
    fams = [x["provisional_family"] for x in r]
    assert len(fams) == len(set(fams))


def test_seed_ordering_reproducible(built):
    m, r = built
    ids = m["eligible_ordered_ids"]
    keys = [hashlib.sha256(f"mrl15-frame-seed-20260922:{t}".encode()).hexdigest() for t in ids]
    assert keys == sorted(keys)
    assert [x["task_id"] for x in r] == ids[:20]


def test_no_reference_code_or_assertions_in_records(built):
    m, r = built
    mbpp = rcf.load_mbpp()
    blob = json.dumps(r) + json.dumps(m)
    doc = ROOT / "docs/frame_review_mrl15_20260922.md"
    docs = doc.read_text() if doc.exists() else ""
    for x in r:
        row = mbpp[x["task_id"]]
        for t in row["test_list"]:
            assert t not in blob and json.dumps(t)[1:-1] not in blob and t not in docs
        body = row["code"].strip()
        assert body not in blob and json.dumps(body)[1:-1] not in blob and body not in docs
        assert x["reference_code_sha256"] == hashlib.sha256(row["code"].encode()).hexdigest()


def test_threshold_preregistered(built):
    m, _ = built
    assert m["preregistered"]["similarity_threshold"] == 0.5
    assert m["execution"]["model_calls"] == 0
