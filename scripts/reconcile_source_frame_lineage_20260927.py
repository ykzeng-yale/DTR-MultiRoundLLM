#!/usr/bin/env python3
"""MRL-39: full-source lineage reconciliation of all 974 original MBPP IDs (source only).

Pure JSON/text/hash/set operations over exact, hash-pinned input records (docs/source_frame_lineage_contract_20260927.md).
No benchmark module import, eval/exec/compile, AST execution, subprocess, network or external data discovery. Source text,
references and assertions are read as inert data and emitted only as SHA256 digests. Each ID gets one terminal first
lineage category; the expected stage counts are VERIFIED (a mismatch is a refusal), never forced. Lexical, interface and
provisional-family exclusions are not semantic invalidity, and none is reopened. Every row is approved_for_evaluation=false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

VERSION = "source-frame-lineage-v1-r1"  # R1: exact downstream sets, identity and summary reconciliation
ISSUING_COMMIT = "0580cb9"
INPUTS = {  # name -> (path, sha256 of the raw bytes, pinned at the issuing commit)
    "mbpp": ("work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl", "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"),
    "canonical_pool": ("work/data/tasks.json", "23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce"),
    "acquisition": ("results/landmark_task_source_candidates_20260920.json", "87aa26bd6cc7153b2e2db1ec426424b9dcab9b6202428800291a680f93e610e4"),
    "screen_summary": ("results/pool_screen_20260921T131231Z/summary.json", "e13161e979673d96d8608025e86739caef94152a00d5fe9d263c9b8ab025929b"),
    "screen_per_candidate": ("results/pool_screen_20260921T131231Z/per_candidate.json", "8c7d9ea628035e1f869a45517f86769c4f3911ac002ec7962b057de4c3d9c9c9"),
    "screen_usable": ("results/pool_screen_20260921T131231Z/usable_ids.json", "b2bab50b0999659309f941174aefa1163f09c28c3a62261d5dc5c9aa5bfd0f55"),
    "mrl15_manifest": ("results/frame_review_mrl15_20260922T021718Z/manifest.json", "4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc"),
    "reconciliation_198": ("results/policy_full_frame_reconciliation_20260926.json", "744b0f393ba7b739ed64087d190d406908fe8f8b6063032a6b300cd1f4cbfbff"),
    "adjudication_43": ("results/policy_candidate_adjudication_20260926.json", "3458d582969c9a04922a71ce2818ede91a45ca9c3925e8d78fd5f44307a0b4b4"),
    "refinement_16": ("results/policy_family_refinement_20260927.json", "a0c052a30917f45504356b85cd327318e892756d263d830a6fe3f29d720adf8b"),
    "prior_seen_config": ("experiments/landmark/dev_release_v1c/config.json", "9b22b94cfdabf48ae36e8bdf27d748adc71465ace2b56e0ae5ff30d1a61b062a"),
}
EXPECTED_COUNTS = {"canonical": 427, "prior_literal_duplicate": 3, "mechanical_interface": 142, "mechanical_setup": 6,
                   "mrl15_prior_seen": 12, "mrl15_neighbor": 149, "mrl15_family_member": 37, "reviewed_frame": 198}
CATEGORY_ORDER = tuple(EXPECTED_COUNTS)
MRL15_STEPS = {"i_prior_seen": "mrl15_prior_seen", "ii_near_duplicate_of_prior_seen": "mrl15_neighbor",
               "ii_within_frame_family": "mrl15_family_member"}
ADJ_FIELDS = ("family_axis", "provisional_computational_family", "contract_axis", "public_expected_literal_display",
              "public_actual_display_axis", "measurement_evidence", "approved_evaluation_roster")
REF_FIELDS = ("prior_family_axis", "family_axis", "contract_axis_unchanged", "approved_evaluation_roster")


class LineageRefused(ValueError):
    """An input, stage set or partition check failed; no output is written."""


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_pinned(path, pin) -> bytes:
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        raise LineageRefused(f"{path}: unreadable ({type(e).__name__})") from None
    if hashlib.sha256(data).hexdigest() != pin:
        raise LineageRefused(f"{path}: sha256 differs from the pin")
    return data


def load_production(root=Path(".")) -> dict:
    data = {}
    for name, (rel, pin) in INPUTS.items():
        raw = read_pinned(Path(root) / rel, pin)
        if name == "mbpp":
            rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
            data[name] = rows
        else:
            data[name] = json.loads(raw)
    return data


def _unique(ids, what):
    ids = list(ids)
    if len(ids) != len(set(ids)):
        raise LineageRefused(f"duplicate IDs in {what}")
    return set(ids)


def reconcile(d: dict, expected_counts=EXPECTED_COUNTS) -> dict:
    """Pure reconciliation over already-loaded inputs (the explicit synthetic seam for tests)."""
    mbpp = {}
    for row in d["mbpp"]:
        tid = row.get("task_id")
        if type(tid) is not int or tid in mbpp:
            raise LineageRefused(f"missing, non-integer or duplicate MBPP task_id {tid!r}")
        mbpp[tid] = row
    full = set(mbpp)
    n_full = d["acquisition"]["full_task_count"]
    if len(full) != n_full or full != set(range(1, n_full + 1)):
        raise LineageRefused("MBPP IDs are not the contiguous original frame reported by the acquisition record")
    canon_rows = [r for r in d["canonical_pool"] if r.get("benchmark") == "mbpp"]
    canonical = _unique((int(r["source_task_id"]) for r in canon_rows), "canonical pool")
    canonical_uid = {int(r["source_task_id"]): r["uid"] for r in canon_rows}
    acq = d["acquisition"]
    candidates = _unique(acq["candidate_ids"], "acquisition candidates")
    after_dup = _unique(acq["after_prior_prompt_duplicate_exclusion_ids"], "after-duplicate candidates")
    dup_evidence = {x["candidate_id"]: x["prior_root_ids"] for x in acq["exact_normalized_prior_prompt_duplicates"]}
    per = d["screen_per_candidate"]
    screened = _unique((r["task_id"] for r in per), "screen per-candidate")
    gate = {r["task_id"]: (r["gate"], r.get("reason")) for r in per}
    usable = _unique(d["screen_usable"], "screen usable IDs")
    m = d["mrl15_manifest"]
    frame = list(m["eligible_ordered_ids"])
    frame_set = _unique(frame, "MRL-15 eligible frame")
    excluded = {int(k): v for k, v in m["excluded"].items()}
    recon = d["reconciliation_198"]["records"]
    adj = d["adjudication_43"]["records"]
    ref = d["refinement_16"]["records"]
    checks = {
        "canonical_subset_of_full": canonical <= full,
        "candidates_equal_full_minus_canonical": candidates == full - canonical,
        "after_duplicate_subset_of_candidates": after_dup <= candidates,
        "duplicate_evidence_equals_removed": set(dup_evidence) == candidates - after_dup,
        "screen_input_equals_after_duplicate": screened == after_dup,
        "usable_equals_screen_usable_gate": usable == {t for t, (g, _) in gate.items() if g == "USABLE"},
        "mrl15_start_equals_usable": set(excluded) | frame_set == usable and not set(excluded) & frame_set,
        "mrl15_steps_known": all(v["step"] in MRL15_STEPS for v in excluded.values()),
        "reconciliation_equals_frame_in_rank_order":
            [r["task_id"] for r in sorted(recon, key=lambda r: r["rank"])] == frame and len(recon) == len(frame),
        "adjudication_subset_of_frame": {r["task_id"] for r in adj} <= frame_set and len({r["task_id"] for r in adj}) == len(adj),
        "refinement_subset_of_adjudication": {r["task_id"] for r in ref} <= {r["task_id"] for r in adj}
                                             and len({r["task_id"] for r in ref}) == len(ref),
        "screen_gates_known": {g for g, _ in gate.values()} <= {"USABLE", "G2_interface", "G3_setup"},
    }
    # R1: exact downstream sets (not subsets), with consistent ranks, source identities and contract axes.
    recon_rank = {r["task_id"]: r["rank"] for r in recon}
    by_recon = {r["task_id"]: r for r in recon}
    expected43 = {r["task_id"] for r in recon if r["historical_class"] == "candidate" and r["prior_receiver_development"] is False
                  and r["current_overlay"] == "none"}
    adj_ids = [r["task_id"] for r in adj]
    expected16 = {r["task_id"] for r in adj if r.get("family_axis") == "plausible_shared_family"}
    ref_ids = [r["task_id"] for r in ref]

    def digests(t):
        src = mbpp[t]
        return {"description_sha256": sha256_text(src["text"]), "reference_sha256": sha256_text(src["code"]),
                "assertion_sha256": [sha256_text(a) for a in src["test_list"]]}
    adj_by_id = {r["task_id"]: r for r in adj}
    rd = d["reconciliation_198"]
    checks.update({
        "adjudication_equals_expected_remaining_candidates":
            set(adj_ids) == expected43 and len(adj_ids) == len(set(adj_ids)) == rd.get("remaining_candidate_roots_after_known_receiver_exposure_and_display_hold"),
        "adjudication_ranks_match_frame": all(r.get("rank") == recon_rank.get(r["task_id"]) for r in adj),
        "adjudication_source_hashes_match_mbpp": all(r["task_id"] in mbpp and r.get("source_hashes") == digests(r["task_id"]) for r in adj),
        "adjudication_historical_record_matches_reconciliation": all(
            r.get("historical_record") == {k: by_recon[r["task_id"]][k] for k in r.get("historical_record", {})}
            and bool(r.get("historical_record")) for r in adj if r["task_id"] in by_recon),
        "refinement_equals_plausible_family_rows":
            set(ref_ids) == expected16 and len(ref_ids) == len(set(ref_ids)) and len(expected16) > 0,
        "refinement_ranks_match_frame": all(r.get("rank") == recon_rank.get(r["task_id"]) for r in ref),
        "refinement_source_hashes_match_mbpp": all(r["task_id"] in mbpp and r.get("source_hashes") == digests(r["task_id"]) for r in ref),
        "refinement_contract_axis_unchanged_matches_adjudication": all(
            r["task_id"] in adj_by_id and r.get("contract_axis_unchanged") == adj_by_id[r["task_id"]].get("contract_axis")
            and r.get("prior_family_axis") == adj_by_id[r["task_id"]].get("family_axis") for r in ref),
    })
    # R1: declared summary counts reconciled against the actual sets and counters.
    from collections import Counter
    summ = d["screen_summary"]
    gate_counts = Counter(g for g, _ in gate.values())
    reason_counts = Counter(f"{g}:{reason}" for g, reason in gate.values() if g != "USABLE")
    mc = m.get("counts", {})
    n_i = sum(v["step"] == "i_prior_seen" for v in excluded.values())
    n_ii = sum(v["step"] == "ii_near_duplicate_of_prior_seen" for v in excluded.values())
    classes = Counter(r["historical_class"] for r in recon)
    checks.update({
        "screen_summary_candidates": summ.get("candidates") == len(screened),
        "screen_summary_usable": summ.get("usable_upper_bound") == len(usable),
        "screen_summary_first_failing_gate": summ.get("first_failing_gate") == dict(gate_counts),
        "screen_summary_reasons": summ.get("reasons") == dict(reason_counts),
        "acquisition_declared_counts": (acq.get("full_task_count") == len(full) and acq.get("canonical_mbpp_count") == len(canonical)
                                        and acq.get("candidate_count") == len(candidates)
                                        and acq.get("after_prior_prompt_duplicate_exclusions") == len(after_dup)),
        "mrl15_declared_counts": (mc.get("start_frame") == len(usable) and mc.get("after_i_prior_seen") == len(usable) - n_i
                                  and mc.get("after_ii_prior_seen_near_duplicate") == len(usable) - n_i - n_ii
                                  and mc.get("after_ii_within_frame_family") == len(frame)),
        "reconciliation_declared_class_counts": rd.get("counts") == dict(classes),
        "reconciliation_declared_receiver_counts": (
            rd.get("known_receiver_development_candidates") == sum(r["historical_class"] == "candidate" and r["prior_receiver_development"] for r in recon)
            and rd.get("candidates_without_recorded_receiver_development_in_these_sources")
            == sum(r["historical_class"] == "candidate" and not r["prior_receiver_development"] for r in recon)),
    })
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise LineageRefused(f"stage set checks failed: {failed}")
    category, evidence = {}, {}

    def assign(tid, cat, ev):
        if tid in category:
            raise LineageRefused(f"ID {tid} falls in two categories ({category[tid]}, {cat})")
        category[tid], evidence[tid] = cat, ev
    for t in canonical:
        assign(t, "canonical", {"canonical_uid": canonical_uid[t]})
    for t in candidates - after_dup:
        assign(t, "prior_literal_duplicate", {"prior_root_ids": dup_evidence[t]})
    for t, (g, reason) in gate.items():
        if g == "G2_interface":
            assign(t, "mechanical_interface", {"gate": g, "reason": reason})
        elif g == "G3_setup":
            assign(t, "mechanical_setup", {"gate": g, "reason": reason})
    for t, v in excluded.items():
        assign(t, MRL15_STEPS[v["step"]], {"step": v["step"], "reason": v["reason"]})
    for t in frame:
        assign(t, "reviewed_frame", {"source": "MRL-15 eligible_ordered_ids"})
    if set(category) != full:
        raise LineageRefused(f"categories do not partition the frame: missing {sorted(full - set(category))[:10]}, "
                             f"extra {sorted(set(category) - full)[:10]}")
    counts = {c: sum(v == c for v in category.values()) for c in CATEGORY_ORDER}
    if counts != dict(expected_counts):
        raise LineageRefused(f"stage counts {counts} differ from the expected {dict(expected_counts)}")
    recon_by, adj_by, ref_by = ({r["task_id"]: r for r in recs} for recs in (recon, adj, ref))
    rank = {t: i for i, t in enumerate(frame, 1)}
    prior_seen = {int(s.split("/")[1]) for s in d["prior_seen_config"]["prior_seen_root_ids"] if str(s).startswith("mbpp/")}
    e11 = set(m["source"]["e11_dev_roots"])
    rows = []
    for t in sorted(full):
        src = mbpp[t]
        r = recon_by.get(t)
        rows.append({
            "task_id": t,
            "source_digests": {"text_sha256": sha256_text(src["text"]), "reference_sha256": sha256_text(src["code"]),
                               "assertion_sha256": [sha256_text(a) for a in src["test_list"]]},
            "terminal_category": category[t], "category_evidence": evidence[t],
            "in_reviewed_frame_198": t in frame_set, "frame_rank": rank.get(t),
            "reconciliation_198": None if r is None else {k: r[k] for k in ("historical_class", "source_disposition",
                                                                              "current_overlay", "prior_receiver_development",
                                                                              "measurement_development", "source_record")},
            "adjudication_43": None if t not in adj_by else {k: adj_by[t].get(k) for k in ADJ_FIELDS},
            "refinement_16": None if t not in ref_by else {k: ref_by[t].get(k) for k in REF_FIELDS},
            "canonical_pool_member": t in canonical, "canonical_uid": canonical_uid.get(t),
            "flags_from_named_records": {
                "prior_seen_dev_release_v1c": t in prior_seen,
                "e11_dev_root": t in e11,
                "in_e12_contract_review_record": bool(r and r["source_record"] == "docs/e12_contract_review_20260922.md"),  # review membership, not receiver execution
                "prior_receiver_development_recorded": bool(r and r["prior_receiver_development"]),
            },
            "exposure": "unknown beyond the named records (no claim about model pretraining or cross-workspace use); a false flag means absent from that named record only",
            "approved_for_evaluation": False,
        })
    return {"version": VERSION, "issuing_commit": ISSUING_COMMIT, "record_type": "source_lineage_reconciliation_not_a_decision",
            "n_rows": len(rows), "category_counts": counts, "expected_counts_verified": dict(expected_counts),
            "set_checks": checks,
            "stage_sizes": {"full": len(full), "canonical": len(canonical), "candidates": len(candidates),
                            "after_prior_duplicates": len(after_dup), "screened": len(screened), "usable": len(usable),
                            "mrl15_frame": len(frame), "adjudication_43": len(adj), "refinement_16": len(ref)},
            "limits": ["Lexical-neighbor exclusions are not proven semantic families; interface exclusions are not invalid tasks; "
                       "removed family members are not extra independent families. None is reopened or counted as reserve.",
                       "The 43-root overlay is a later layer and does not replace the 198-root denominator.",
                       "Flags come only from the named records; exposure is otherwise unknown.",
                       "Every row is approved_for_evaluation=false; no family, population or eligibility decision is made."],
            "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        print(f"refused: {out} already exists (never overwritten)")
        return 2
    try:
        doc = reconcile(load_production())
    except LineageRefused as e:
        print(f"refused: {e}")
        return 2
    doc["input_sha256"] = {name: pin for name, (_, pin) in INPUTS.items()}
    doc["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with open(out, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, sort_keys=True, ensure_ascii=False, indent=1) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
