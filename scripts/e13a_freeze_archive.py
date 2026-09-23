#!/usr/bin/env python3
"""Archive the E13a dispatch-freeze Git object additively and emit a deterministic verification recipe.

MRL-21 item 1 (lead 73139fb). Evidence class: provenance archive; no execution of any kind.

The run manifest names dispatch freeze 76d958eb... . A post-dispatch `git pull --rebase` replayed that commit
as d7382cc..., so the original is not an ancestor of origin/main. This script exports the ORIGINAL object
itself, additively, so its Git object ID and recorded paths can be verified without importing abandoned
ancestry into main and without inventing a reconstructed commit.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = "76d958eb1fd26624d2d384a2a26743a8d2e157d2"
REPLACEMENT = "d7382ccee9b9ab3294b33ac700c7593d9171837d"
RUN = ROOT / "results/e13a_two_arm_20260923T061500Z"


def git(*args, binary=False):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode()


def git_object_id(payload: bytes, kind: str = "commit") -> str:
    """Recompute the object ID from its payload: sha1(b"<kind> <len>\\0" + payload)."""
    return hashlib.sha1(f"{kind} {len(payload)}".encode() + b"\0" + payload).hexdigest()


def build(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = git("cat-file", "commit", ORIGINAL, binary=True)
    recomputed = git_object_id(payload)
    if recomputed != ORIGINAL:
        raise SystemExit(f"payload does not hash to the recorded object id: {recomputed}")
    (out_dir / "original_freeze_commit_payload.txt").write_bytes(payload)

    header = {ln.split(" ", 1)[0]: ln.split(" ", 1)[1]
              for ln in payload.decode().split("\n\n", 1)[0].splitlines()}
    manifest = json.loads((RUN / "collect/manifest.json").read_text())
    tracked = manifest["freeze"]["tracked_file_hashes"]

    # Each recorded path, resolved in the ORIGINAL tree, with its blob id and content hash.
    paths = {}
    for rel, sha256 in tracked.items():
        blob = git("rev-parse", f"{ORIGINAL}:{rel}").strip()
        content = git("cat-file", "blob", blob, binary=True)
        paths[rel] = {"blob_id_in_original": blob,
                      "sha256_in_original": hashlib.sha256(content).hexdigest(),
                      "sha256_recorded_in_manifest": sha256,
                      "matches": hashlib.sha256(content).hexdigest() == sha256}

    repl_tree = git("cat-file", "commit", REPLACEMENT).split("\n", 1)[0].split()[1]
    return {
        "record_version": "e13a-freeze-archive-v1",
        "authority": "MRL-21 item 1, lead commit 73139fb",
        "why": ("The run manifest names the dispatch freeze; a post-dispatch rebase replayed it, so the original "
                "commit is not an ancestor of origin/main. The object is archived additively here."),
        "original": {
            "commit_id": ORIGINAL, "tree_id": header["tree"], "parent_id": header["parent"],
            "payload_file": "original_freeze_commit_payload.txt",
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "payload_bytes": len(payload),
            "object_id_recomputed_from_payload": recomputed,
            "is_ancestor_of_origin_main": False,
        },
        "replacement": {
            "commit_id": REPLACEMENT, "tree_id": repl_tree,
            "whole_tree_identical_to_original": repl_tree == header["tree"],
            "why_trees_differ": ("The rebase replayed the ownership commit onto the lead's 4ca2741, so the "
                                 "replacement tree additionally contains the lead's files. Whole-tree identity "
                                 "is therefore NOT claimed; only the recorded paths are shown to match."),
        },
        "recorded_paths": {"n": len(paths), "n_matching": sum(p["matches"] for p in paths.values()),
                           "paths": paths},
        "bundle": {"file": "original_freeze.bundle",
                   "contents": f"the single commit {ORIGINAL[:12]} with prerequisite {header['parent'][:12]}",
                   "prerequisite_is_in_published_history": True,
                   "import_note": ("Import into a SCRATCH clone only. Do not merge this ancestry into main: "
                                   "published history stays as it is.")},
        "verification_recipe": [
            "1. sha256 of original_freeze_commit_payload.txt equals payload_sha256 below.",
            "2. Recompute the Git object id: sha1(b'commit ' + str(len(payload)) + b'\\0' + payload) == "
            f"{ORIGINAL}. scripts/e13a_freeze_archive.py:git_object_id does exactly this.",
            "3. git bundle verify original_freeze.bundle  (needs the prerequisite parent, which is in main).",
            "4. In a scratch clone: git fetch <path>/original_freeze.bundle e13a-original-freeze, then "
            f"git cat-file commit {ORIGINAL[:12]} and compare the tree id to tree_id below.",
            "5. Each recorded path's sha256 in the original tree equals the manifest's tracked_file_hashes.",
        ],
        "unrecoverable_or_not_claimed": [
            "Whole-tree identity between the original and replacement commits: the trees genuinely differ.",
            "Commit identity: the replacement has a different parent and therefore a different object id.",
            "Nothing was reconstructed or invented; if the original object is ever garbage-collected from this "
            "working repository, the archived payload and bundle here remain the only copies.",
        ],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "results/e13a_archive_closure_20260923")
    a = ap.parse_args(argv)
    rec = build(a.out_dir)
    (a.out_dir / "freeze_archive.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"original": rec["original"], "recorded_paths": {k: v for k, v in rec["recorded_paths"].items() if k != "paths"},
                      "whole_tree_identical": rec["replacement"]["whole_tree_identical_to_original"]}, indent=1))


if __name__ == "__main__":
    main()
