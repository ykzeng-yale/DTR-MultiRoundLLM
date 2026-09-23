#!/usr/bin/env python3
"""Audit E14 seed exposure against immutable Git blobs, not host-specific work/ copies."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_NAMES = {"calls.jsonl", "attempt_ledger.jsonl"}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def numeric_seed(record: dict):
    request = record.get("request") if isinstance(record.get("request"), dict) else {}
    for holder in (request.get("options") or {}, request, record):
        if isinstance(holder, dict) and type(holder.get("seed")) is int:
            return holder["seed"]
    return None


def audit(revision: str, published: dict, published_sha256: str) -> dict:
    revision = git("rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
    config = json.loads(git("show", f"{revision}:experiments/landmark/e14_release_v2/config.json"))
    roots = {f"mbpp/{i}": {"labels": [], "numeric": []} for i in config["e14"]["roster_order"]}
    paths = [p for p in git("ls-tree", "-r", "--name-only", "-z", revision).decode().split("\0")
             if p and Path(p).name in LOG_NAMES]
    sources, positive = [], {"records": 0, "labels": [], "numeric": []}
    for path in paths:
        raw = git("show", f"{revision}:{path}")
        count, malformed = 0, 0
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            count += 1
            root = record.get("root_id")
            label, seed = record.get("seed_key"), numeric_seed(record)
            if root in roots:
                if label is not None:
                    roots[root]["labels"].append(label)
                if seed is not None:
                    roots[root]["numeric"].append(seed)
            if root == "mbpp/842":
                positive["records"] += 1
                if label is not None:
                    positive["labels"].append(label)
                if seed is not None:
                    positive["numeric"].append(seed)
        sources.append({"path": path, "sha256": hashlib.sha256(raw).hexdigest(),
                        "records": count, "unparsed_lines": malformed})
    committed = {s["path"]: s for s in sources}
    reported = {s["path"]: s for s in published["sources"]}
    mismatched = [p for p in committed.keys() & reported.keys()
                  if committed[p]["sha256"] != reported[p]["sha256"]]
    return {
        "audit_version": "e14-seed-committed-lead-v1",
        "evidence_class": "read-only static Git-blob audit; no model or program execution",
        "source_revision": revision,
        "published_inventory_sha256": published_sha256,
        "n_committed_logs": len(sources),
        "n_committed_records": sum(s["records"] for s in sources),
        "n_unparsed_lines": sum(s["unparsed_lines"] for s in sources),
        "sources": sources,
        "roots": roots,
        "any_committed_e14_seed_or_label": any(r["labels"] or r["numeric"] for r in roots.values()),
        "positive_control_842": {"records": positive["records"],
                                 "distinct_labels": len(set(positive["labels"])),
                                 "distinct_numeric_seeds": len(set(positive["numeric"]))},
        "published_source_paths_missing_from_revision": sorted(reported.keys() - committed.keys()),
        "committed_source_paths_missing_from_published": sorted(committed.keys() - reported.keys()),
        "shared_path_hash_mismatches": sorted(mismatched),
        "scope_limit": "Absence in committed logs is not absence from ignored host-local or sibling-project logs; "
                       "it does not establish independent receiver draws or a future frozen seed law.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Refusing to overwrite an audit")
    published_bytes = args.published.read_bytes()
    result = audit(args.revision, json.loads(published_bytes), hashlib.sha256(published_bytes).hexdigest())
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("n_committed_logs", "n_committed_records",
                                             "n_unparsed_lines", "any_committed_e14_seed_or_label")}))


if __name__ == "__main__":
    main()
