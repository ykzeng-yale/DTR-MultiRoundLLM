"""Freeze-archive provenance: recomputes the original Git object id from archived bytes. No execution."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e13a_freeze_archive as fa  # noqa: E402

ARCHIVE = ROOT / "results/e13a_archive_closure_20260923"


@pytest.fixture(scope="module")
def rec():
    return json.loads((ARCHIVE / "freeze_archive.json").read_text())


def test_archived_payload_recomputes_the_recorded_object_id(rec):
    payload = (ARCHIVE / "original_freeze_commit_payload.txt").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == rec["original"]["payload_sha256"]
    # the whole point: the object id is verifiable from these bytes alone
    assert fa.git_object_id(payload) == fa.ORIGINAL == rec["original"]["commit_id"]


def test_original_is_not_in_published_ancestry_and_that_is_recorded(rec):
    assert rec["original"]["is_ancestor_of_origin_main"] is False
    r = subprocess.run(["git", "merge-base", "--is-ancestor", fa.ORIGINAL, "origin/main"], cwd=ROOT)
    assert r.returncode != 0, "the abandoned freeze must not have been merged into main"


def test_whole_tree_identity_is_denied_not_claimed(rec):
    assert rec["replacement"]["whole_tree_identical_to_original"] is False
    assert "NOT claimed" in rec["replacement"]["why_trees_differ"]
    assert any("Whole-tree identity" in x for x in rec["unrecoverable_or_not_claimed"])


def test_every_recorded_path_matches_the_manifest(rec):
    p = rec["recorded_paths"]
    assert p["n"] == 18 and p["n_matching"] == 18
    assert all(v["matches"] for v in p["paths"].values())


def test_bundle_exists_and_declares_its_prerequisite(rec):
    assert (ARCHIVE / rec["bundle"]["file"]).exists()
    assert rec["bundle"]["prerequisite_is_in_published_history"] is True
    assert "Do not merge this ancestry into main" in rec["bundle"]["import_note"]


def test_restored_log_matches_the_delivered_manifest():
    run = ROOT / "results/e13a_two_arm_20260923T061500Z"
    sums = json.loads((run / "ARTIFACT_SHA256SUMS.json").read_text())["files"]
    log = run / "receiver/llama_server.log"
    assert log.exists(), "the manifest lists this log; the bytes must be published"
    assert hashlib.sha256(log.read_bytes()).hexdigest() == sums["receiver/llama_server.log"]
    assert subprocess.run(["git", "ls-files", "--error-unmatch", str(log.relative_to(ROOT))],
                          cwd=ROOT, capture_output=True).returncode == 0, "must be tracked, not ignored"
