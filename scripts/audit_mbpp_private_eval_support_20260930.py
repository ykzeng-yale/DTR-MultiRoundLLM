#!/usr/bin/env python3
"""Read-only audit of native MBPP hidden-test support for the residual roots.

This script parses JSONL metadata only. It never imports or executes benchmark,
reference, assertion, or candidate code. The purpose is to test whether the
currently pinned source can provide an independent challenge-test endpoint for
the conservatively retained MBPP candidate roots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PINNED_SOURCE_SHA256 = "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"
PINNED_CANDIDATE_INDEX_SHA256 = "87aa26bd6cc7153b2e2db1ec426424b9dcab9b6202428800291a680f93e610e4"
PINNED_JOINT_LEDGER_SHA256 = "97d29d9baf79c4fea2c73406656881bed82b9df5071f8001c0641dcd624a3081"
PINNED_LINEAGE_SHA256 = "c3e2e63dbc41934eb8ddf02c7fa170b4ed48f09683f4833ac35ead8ae9b516b6"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            task_id = int(row["task_id"])
            if task_id in rows:
                raise ValueError(f"duplicate task_id {task_id} at line {line_number}")
            rows[task_id] = row
    return rows


def audit(
    source_rows: dict[int, dict[str, Any]],
    broad_candidate_ids: list[int],
    residual_ids: list[int],
) -> dict[str, Any]:
    if len(broad_candidate_ids) != len(set(broad_candidate_ids)):
        raise ValueError("broad candidate task IDs must be unique")
    if len(residual_ids) != len(set(residual_ids)):
        raise ValueError("residual task IDs must be unique")
    if not set(residual_ids).issubset(broad_candidate_ids):
        raise ValueError("residual IDs must be contained in the broader candidate frame")
    task_ids = broad_candidate_ids
    missing = sorted(set(task_ids) - source_rows.keys())
    if missing:
        raise ValueError(f"candidate IDs missing from source: {missing}")

    records = []
    for task_id in sorted(task_ids):
        row = source_rows[task_id]
        public_tests = row.get("test_list")
        challenge_tests = row.get("challenge_test_list")
        if not isinstance(public_tests, list) or not isinstance(challenge_tests, list):
            raise ValueError(f"task {task_id} lacks list-valued test fields")
        records.append(
            {
                "task_id": task_id,
                "public_test_count": len(public_tests),
                "challenge_test_count": len(challenge_tests),
            }
        )

    residual = [r for r in records if r["task_id"] in set(residual_ids)]
    from collections import Counter

    challenge_distribution = Counter(str(r["challenge_test_count"]) for r in records)
    public_distribution = Counter(str(r["public_test_count"]) for r in records)
    residual_challenge_distribution = Counter(
        str(r["challenge_test_count"]) for r in residual
    )
    return {
        "record_type": "read_only_source_measurement_inventory",
        "broad_candidate_root_count": len(records),
        "public_test_count_total": sum(r["public_test_count"] for r in records),
        "challenge_test_count_total": sum(r["challenge_test_count"] for r in records),
        "roots_with_challenge_tests": sum(r["challenge_test_count"] > 0 for r in records),
        "challenge_positive_candidate_records": [
            r for r in records if r["challenge_test_count"] > 0
        ],
        "public_test_count_distribution": dict(sorted(public_distribution.items())),
        "challenge_test_count_distribution": dict(sorted(challenge_distribution.items(), key=lambda kv: int(kv[0]))),
        "residual_root_count": len(residual),
        "residual_public_test_count_total": sum(r["public_test_count"] for r in residual),
        "residual_challenge_test_count_total": sum(r["challenge_test_count"] for r in residual),
        "residual_roots_with_challenge_tests": sum(r["challenge_test_count"] > 0 for r in residual),
        "residual_challenge_test_count_distribution": dict(sorted(residual_challenge_distribution.items(), key=lambda kv: int(kv[0]))),
        "residual_records": residual,
        "interpretation": (
            "The pinned source contains no challenge-test partition for these roots. "
            "The remaining public assertions are not an independent hidden endpoint "
            "or evidence of semantic validity; a new outcome instrument requires a "
            "separate specification and validation contract."
        ),
        "execution_counts": {
            "benchmark": 0,
            "reference": 0,
            "candidate": 0,
            "receiver": 0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate-index", type=Path, required=True)
    parser.add_argument("--joint-ledger", type=Path, required=True)
    parser.add_argument("--lineage", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    source_hash = sha256_file(args.source)
    if source_hash != PINNED_SOURCE_SHA256:
        raise SystemExit(f"pinned source hash mismatch: {source_hash}")
    candidate_index_hash = sha256_file(args.candidate_index)
    if candidate_index_hash != PINNED_CANDIDATE_INDEX_SHA256:
        raise SystemExit(f"candidate index hash mismatch: {candidate_index_hash}")
    joint_ledger_hash = sha256_file(args.joint_ledger)
    if joint_ledger_hash != PINNED_JOINT_LEDGER_SHA256:
        raise SystemExit(f"joint ledger hash mismatch: {joint_ledger_hash}")
    lineage_hash = sha256_file(args.lineage)
    if lineage_hash != PINNED_LINEAGE_SHA256:
        raise SystemExit(f"source lineage hash mismatch: {lineage_hash}")
    ledger = json.loads(args.joint_ledger.read_text(encoding="utf-8"))
    candidate_index = json.loads(args.candidate_index.read_text(encoding="utf-8"))
    lineage = json.loads(args.lineage.read_text(encoding="utf-8"))
    broad_ids = candidate_index["after_prior_prompt_duplicate_exclusion_ids"]
    residual_ids = ledger["strict_prior_family_prescreen"]["remaining_roots"]
    result = audit(load_jsonl(args.source), broad_ids, residual_ids)
    lineage_by_id = {int(r["task_id"]): r for r in lineage["rows"]}
    result["challenge_positive_source_roots"] = [
        {
            "task_id": r["task_id"],
            "challenge_test_count": r["challenge_test_count"],
            "historical_gate": lineage_by_id[r["task_id"]]["category_evidence"]["gate"],
            "historical_reason": lineage_by_id[r["task_id"]]["category_evidence"]["reason"],
            "prior_seen_dev_release_v1c": lineage_by_id[r["task_id"]]["flags_from_named_records"]["prior_seen_dev_release_v1c"],
        }
        for r in result["challenge_positive_candidate_records"]
        if r["challenge_test_count"] > 0
    ]
    del result["challenge_positive_candidate_records"]
    result["input_sha256"] = {
        "source": source_hash,
        "candidate_index": candidate_index_hash,
        "joint_ledger": joint_ledger_hash,
        "source_lineage": lineage_hash,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
