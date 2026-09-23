#!/usr/bin/env python3
"""Source-only family/measurement audit of the proposed E14 roster. Zero executions; no outcome is read.

Every claim in section 5 of docs/e14_same_prefix_revision_proposal_20260923.md is recomputed from committed
source files. The audit deliberately reads NO private grade, private spec, private assertion or hidden score,
and no task outcome: the roster rule is "E12 retained roots minus the five E13a outcome-inspected checkpoints",
and eligibility comes from the preregistered frame review's own decisions.

What this audit can and cannot settle: the MRL-15 provisional families are union-find labels at a lexical
similarity threshold, and that manifest states it is not a family-independence certificate. Distinctness of
labels is therefore verified; independence is NOT established and is recorded as an assumption.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAME = ROOT / "results/frame_review_mrl15_20260922T021718Z"
E12 = ROOT / "results/e12_dev_v3_20260922T030255Z"
PROPOSED = ["mbpp/918", "mbpp/825", "mbpp/816", "mbpp/895", "mbpp/868", "mbpp/154", "mbpp/651", "mbpp/499", "mbpp/974"]
E13A_CHECKPOINTS = ["mbpp/842", "mbpp/288", "mbpp/863", "mbpp/966", "mbpp/652"]
UNTOUCHED_RANKS = (61, 198)
FILES_OPENED = [
    "results/frame_review_mrl15_20260922T021718Z/manifest.json",
    "results/frame_review_mrl15_20260922T021718Z/records.json",
    "results/e12_dev_v3_20260922T030255Z/A/roots.jsonl",
    "results/e12_dev_v3_20260922T030255Z/B/diagnostics.json",
]
NOT_OPENED = ["any private_specs.jsonl", "any grades.jsonl", "any analysis_report.json quality block",
              "any hidden score or private assertion"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def audit():
    manifest = json.loads((FRAME / "manifest.json").read_text())
    records = json.loads((FRAME / "records.json").read_text())
    rows = records["records"] if isinstance(records, dict) and "records" in records else records
    by_id = {}
    for r in rows:
        rid = r.get("root_id") or (f"mbpp/{r['task_id']}" if "task_id" in r else None)
        if rid:
            by_id[rid] = r
    ordered = [f"mbpp/{i}" for i in manifest["eligible_ordered_ids"]]
    rank = {rid: i + 1 for i, rid in enumerate(ordered)}

    # E12's retained roots, taken from phase-A roots (assignment table), not from any outcome file.
    e12_roots = [json.loads(l)["root_id"] for l in (E12 / "A/roots.jsonl").read_text().splitlines() if l.strip()]
    expected = [r for r in e12_roots if r not in E13A_CHECKPOINTS]
    diagnostics = json.loads((E12 / "B/diagnostics.json").read_text())

    checks, per_root = {}, {}
    checks["roster_equals_e12_retained_minus_e13a_checkpoints"] = sorted(PROPOSED) == sorted(expected)
    checks["roster_size_is_9"] = len(PROPOSED) == 9
    checks["no_e13a_checkpoint_in_roster"] = not (set(PROPOSED) & set(E13A_CHECKPOINTS))

    for rid in PROPOSED:
        rec = by_id.get(rid, {})
        review = rec.get("spec_review") or {}
        fam = rec.get("provisional_family")
        per_root[rid] = {
            "frame_rank": rank.get(rid),
            "spec_review_decision": review.get("decision"),
            "provisional_family": fam,
            "family_size_in_frame": rec.get("family_size_in_frame"),
            "has_frozen_initial_artifact": rid in set(e12_roots),
            "has_frozen_public_diagnostic": rid in diagnostics,
            "public_case_statuses": [c.get("status") for c in diagnostics.get(rid, {}).get("cases", [])],
        }
    checks["all_include_decision"] = all(v["spec_review_decision"] == "include" for v in per_root.values())
    checks["all_have_frozen_initial_artifact"] = all(v["has_frozen_initial_artifact"] for v in per_root.values())
    checks["all_have_frozen_public_diagnostic"] = all(v["has_frozen_public_diagnostic"] for v in per_root.values())
    fams = [v["provisional_family"] for v in per_root.values()]
    checks["provisional_family_label_resolved_for_every_root"] = all(f is not None for f in fams)
    checks["provisional_families_distinct"] = len(set(fams)) == len(fams) and all(f is not None for f in fams)
    cp_fams = {rid: by_id.get(rid, {}).get("provisional_family") for rid in E13A_CHECKPOINTS}
    checks["no_family_shared_with_e13a_checkpoints"] = not (set(fams) & {f for f in cp_fams.values() if f})


    lo, hi = UNTOUCHED_RANKS
    untouched = ordered[lo - 1:hi]
    checks["untouched_split_size_138"] = len(untouched) == 138
    checks["untouched_split_disjoint_from_roster"] = not (set(untouched) & set(PROPOSED))
    checks["untouched_split_disjoint_from_e13a"] = not (set(untouched) & set(E13A_CHECKPOINTS))
    checks["roster_ranks_all_below_untouched_split"] = all(per_root[r]["frame_rank"] < lo for r in PROPOSED)
    pre = manifest.get("preregistered", {})
    checks["frame_order_used_no_outcome_information"] = pre.get("outcome_information_used") in (None, "none")

    return {
        "audit_version": "e14-roster-audit-v1",
        "evidence_class": ("source-only family/measurement audit of a PROPOSED roster; zero executions; no "
                           "outcome, private grade, private assertion or hidden score was read"),
        "proposal": {"path": "docs/e14_same_prefix_revision_proposal_20260923.md",
                     "sha256": _sha(ROOT / "docs/e14_same_prefix_revision_proposal_20260923.md")},
        "inputs": {p: _sha(ROOT / p) for p in FILES_OPENED},
        "files_deliberately_not_opened": NOT_OPENED,
        "roster": PROPOSED, "per_root": per_root,
        "untouched_policy_split": {"rank_range": list(UNTOUCHED_RANKS), "n": len(untouched),
                                   "named_by_rank_only": True,
                                   "note": "reserved; no text, outcome or grade of these was read"},
        "family_multiplicity": {
            "note": ("Descriptive, not a pass/fail requirement. The frame collapsed each provisional family to one "
                     "representative, so a roster root whose family had more than one frame member stands in for a "
                     "collapsed sibling. This is where the independence assumption actually rests."),
            "singleton_families": sorted(r for r in PROPOSED if per_root[r]["family_size_in_frame"] == 1),
            "multi_member_families": {r: per_root[r]["family_size_in_frame"] for r in PROPOSED
                                      if (per_root[r]["family_size_in_frame"] or 0) > 1},
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "limitations": [
            "Provisional families are MRL-15 union-find labels at a lexical threshold; the frame manifest states "
            "it is not a family-independence certificate. Distinct labels are verified; independence is assumed.",
            "All nine roots are development histories whose E12 outcomes were already seen; this is reuse, not an "
            "independent evaluation set, and no design choice here undoes that.",
            "Three of the nine roots (868, 154, 974) represent two-member provisional families; their siblings "
            "were removed by the within-frame collapse, so nine roots are not nine independently sampled families.",
            "This audit checks roster construction and measurement bindings only. It is not a release, not a "
            "power calculation and not evidence about any arm.",
        ],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    rec = audit()
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"all_checks_pass": rec["all_checks_pass"], "checks": rec["checks"]}, indent=1))


if __name__ == "__main__":
    main()
