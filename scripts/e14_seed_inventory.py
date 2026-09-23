#!/usr/bin/env python3
"""MRL-25 criterion 3: the historical seed-label and numeric-seed inventory for the ten E14 roots.

Evidence class: static scan of this project's immutable receiver call logs; no execution. Every call log in the
repository is enumerated by name, hashed and parsed; each record's root, seed label and numeric request seed are
read. The inventory is declared complete only for the sources actually scanned, and every source it does not
cover is named as an explicit scope limit rather than silently treated as "no collision".
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E14_ROOTS = [f"mbpp/{i}" for i in (911, 667, 344, 524, 814, 187, 194, 356, 366, 302)]
LOG_NAMES = ("calls.jsonl", "attempt_ledger.jsonl")


def _seed(rec):
    req = rec.get("request") if isinstance(rec.get("request"), dict) else {}
    for container in (req.get("options") or {}, req, rec):
        if isinstance(container.get("seed"), int):
            return container["seed"]
    return None


def build():
    sources, roots = [], {r: {"labels": [], "numeric": []} for r in E14_ROOTS}
    logs = sorted(p for name in LOG_NAMES for p in ROOT.rglob(name)
                  if ".git" not in p.parts and ".venv" not in p.parts)
    for p in logs:
        rel = p.relative_to(ROOT).as_posix()
        n, unparsed, found = 0, 0, set()
        for line in p.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                unparsed += 1
                continue
            n += 1
            rid = rec.get("root_id")
            if rid in roots:
                found.add(rid)
                if rec.get("seed_key"):
                    roots[rid]["labels"].append(rec["seed_key"])
                if _seed(rec) is not None:
                    roots[rid]["numeric"].append(_seed(rec))
        sources.append({"path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "records": n,
                        "unparsed_lines": unparsed, "e14_roots_present": sorted(found),
                        "immutable": rel.startswith("results/"),
                        "role": "committed immutable call log" if rel.startswith("results/")
                                else "working-copy duplicate or fixture, scanned for completeness"})
    unparsed_total = sum(s["unparsed_lines"] for s in sources)
    return {
        "inventory_version": "e14-seed-inventory-v1",
        "evidence_class": "static scan of this project's receiver call logs; zero executions",
        "complete": unparsed_total == 0,
        "roots": roots,
        "sources": sources,
        "n_sources": len(sources), "n_records": sum(s["records"] for s in sources),
        "prior_spend_found_for_any_e14_root": any(v["labels"] or v["numeric"] for v in roots.values()),
        "scope_limits": [
            "Covers every file named calls.jsonl or attempt_ledger.jsonl in this repository. Logs of the sibling "
            "project DTR-AgentEvals are NOT scanned: they use a different harness and seed law, so a numeric match "
            "there would not be the same request law. If that exposure matters, it is an unresolved dependency.",
            "Separately, all ten roots lie inside the MRL-15 frame, whose construction removed the 441 prior-seen "
            "MBPP ids; that is a source-exposure fact, not a seed inventory.",
            "An empty inventory for a root means no recorded spend in the scanned logs; it does not establish that "
            "future draws are independent.",
        ],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    rec = build()
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("complete", "n_sources", "n_records", "prior_spend_found_for_any_e14_root")}))


if __name__ == "__main__":
    main()
