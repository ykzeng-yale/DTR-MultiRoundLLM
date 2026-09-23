#!/usr/bin/env python3
"""Where the wall-clock time went, MRL-18..MRL-25, recomputed from git commit timestamps only.

Evidence class: process diagnostics from the repository's own history; no experiment, no model call.
Each round is (lead release, worker acknowledgement, worker delivery, lead review of that delivery).
"""
from __future__ import annotations
import argparse, datetime as dt, json, subprocess
from pathlib import Path

ROUNDS = [
    ("MRL-18", "be417b5", "55a5875", "960ba33", "cb1536a", "source/mock prep; E13 corrections"),
    ("MRL-19", "cb1536a", "9a0da43", "bb89694", "b6bf5e6", "source/mock: E13a real path"),
    ("MRL-20", "5a34153", "ee4edb3", "297749d", "73139fb", "EXECUTION: E13a, 60 receiver calls"),
    ("MRL-21", "73139fb", "5426c6f", "25d1f1c", "c32923c", "source: archive closure + corrections"),
    ("MRL-22", "c32923c", "748c4ae", "3c3066c", "be0507e", "source: frame review ranks 21-40"),
    ("MRL-23", "be0507e", "5da18fb", "18797b7", "45f7aa7", "source/mock: E14 package"),
    ("MRL-24", "45f7aa7", "6486b12", "1c66f86", "38942de", "source/mock: E14 repair"),
]


def t(sha):
    s = subprocess.run(["git", "log", "-1", "--format=%cI", sha], capture_output=True, text=True, check=True).stdout
    return dt.datetime.fromisoformat(s.strip()).astimezone(dt.timezone.utc)


def build(now=None):
    rows = []
    for m, rel, ack, dlv, rev, kind in ROUNDS:
        rows.append({"item": m, "kind": kind,
                     "ack_min": round((t(ack) - t(rel)).total_seconds() / 60, 1),
                     "work_min": round((t(dlv) - t(ack)).total_seconds() / 60, 1),
                     "lead_review_min": round((t(rev) - t(dlv)).total_seconds() / 60, 1),
                     "commits": {"release": rel, "ack": ack, "delivery": dlv, "review": rev}})
    return {"diagnosis_version": "efficiency-diagnosis-v1",
            "source": "git commit timestamps; recompute with scripts/efficiency_diagnosis.py",
            "rounds": rows,
            "e12_delivery_to_lead_review_hours": round((t("be417b5") - t("1f65447")).total_seconds() / 3600, 1),
            "rounds_that_collected_data": [r["item"] for r in rows if r["kind"].startswith("EXECUTION")]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    rec = build()
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("e12_delivery_to_lead_review_hours", "rounds_that_collected_data")}))


if __name__ == "__main__":
    main()
