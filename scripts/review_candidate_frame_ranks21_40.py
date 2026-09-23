#!/usr/bin/env python3
"""MRL-22 mechanical screen of candidate-frame ranks 21-40 (source-only, static).

Scope is EXACTLY ranks 21-40 of the preregistered MRL-15 candidate frame
(`results/frame_review_mrl15_20260922T021718Z/manifest.json`, sha256 pinned below).
Nothing is reranked, no criterion is loosened, no rank outside 21-40 is reviewed and
ranks 41-198 are never read from the ordered list beyond the slice bound.

Criteria identity: every threshold, stop list, similarity metric, seed/order key,
family rule and the decision function itself are IMPORTED from
`scripts/review_candidate_frame_mrl15.py` (never re-typed). The selection pipeline is
re-executed with those imported functions and the result is asserted to reproduce the
committed frame exactly (same `excluded` map, same `eligible_ordered_ids`), which is
the machine-checked proof that the criteria are unchanged.

No model, receiver, sandbox, subprocess or network is used; reference code is only
parsed with ast.parse / compile() inside the imported MRL-15 helpers. No grades file,
analysis report, private execution record or hidden score is opened, and the decision
function reads no outcome field.

Reproduce:
  .venv/bin/python scripts/review_candidate_frame_ranks21_40.py \
      --out-dir results/frame_review_ranks21_40_20260923
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MRL15_SCRIPT = ROOT / "scripts/review_candidate_frame_mrl15.py"
FRAME_DIR = ROOT / "results/frame_review_mrl15_20260922T021718Z"
FRAME_MANIFEST_SHA256 = "4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc"

RANK_LO, RANK_HI = 21, 40
# Committed order handed down with MRL-22; asserted against the frame manifest slice.
EXPECTED_IDS = [911, 211, 701, 960, 667, 344, 370, 484, 524, 814,
                346, 187, 508, 194, 356, 366, 302, 670, 376, 650]

# The manifest records the worker's path; the same sha-pinned bytes may live under
# work/task_sources/ on another host. Resolution order: manifest path, then these.
SOURCE_FALLBACKS = ("work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl",
                    "work/sources/mbpp_full.jsonl")
# Only these MBPP row fields are ever read. None of them is a model outcome.
SOURCE_FIELDS_READ = ("task_id", "text", "code", "test_list", "challenge_test_list")

# Carried-forward dispositions from ranks 1-20. These stay held and are NOT revisited.
CARRIED_MECHANICAL_HOLDS = (359, 349)           # records.json ranks 3 and 16
CARRIED_SEMANTIC_HOLDS = (31, 847, 907, 963)    # docs/e12_contract_review_20260922.md
E12_DOC = ROOT / "docs/e12_contract_review_20260922.md"

FORBIDDEN_INPUT_MARKERS = ("grade", "outcome", "private", "score", "hidden",
                           "analysis", "transcript", "generation", "completion")


def _load_mrl15():
    spec = importlib.util.spec_from_file_location("rcf_mrl15", MRL15_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = _load_mrl15()
sha256_bytes = M.sha256_bytes
sha256_text = M.sha256_text


def rel(p: Path) -> str:
    p = Path(p)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def load_frame_manifest(path: Path | None = None) -> tuple[dict, str]:
    path = Path(path) if path else FRAME_DIR / "manifest.json"
    raw = path.read_bytes()
    got = sha256_bytes(raw)
    if got != FRAME_MANIFEST_SHA256:
        raise SystemExit(f"frame manifest sha256 mismatch: {got}")
    return json.loads(raw.decode("utf-8")), got


def criteria_identity(frame_manifest: dict) -> dict:
    """Assert the imported MRL-15 criteria equal the preregistered ones."""
    pre = frame_manifest["preregistered"]
    src = frame_manifest["source"]
    checks = {
        "seed": (M.SEED, pre["seed"]),
        "order_key": (f'sha256(f"{M.SEED}:{{task_id}}")', pre["order_key"]),
        "n_review": (M.N_REVIEW, pre["n_review"]),
        "similarity_threshold": (M.SIM_THRESHOLD, pre["similarity_threshold"]),
        "similarity_rule": (M.SIM_RULE, pre["similarity_rule"]),
        "family_rule": ("union-find over within-frame pairs with score >= threshold; "
                        "keep member with smallest seeded hash", pre["family_rule"]),
        "outcome_information_used": ("none", pre["outcome_information_used"]),
        "mbpp_sha256": (M.MBPP_SHA256, src["mbpp_sha256"]),
        "e11_dev_roots": (list(M.E11_DEV_ROOTS), list(src["e11_dev_roots"])),
        "screen_dir": (rel(M.SCREEN_DIR), src["screen_dir"]),
    }
    bad = {k: {"imported": a, "preregistered": b} for k, (a, b) in checks.items() if a != b}
    if bad:
        raise SystemExit("criteria identity failed: " + json.dumps(bad, sort_keys=True))
    return {
        "source_module": rel(MRL15_SCRIPT),
        "source_module_sha256": sha256_bytes(MRL15_SCRIPT.read_bytes()),
        "imported_not_retyped": sorted([
            "SEED", "N_REVIEW", "SIM_THRESHOLD", "SIM_RULE", "CODE_STOP", "TEXT_STOP",
            "E11_DEV_ROOTS", "MBPP_SHA256", "SCREEN_DIR", "PRIOR_CONFIG", "seed_key",
            "text_tokens", "code_tokens", "jac", "sim", "entry_point", "test_features",
            "spec_review", "UF", "verify_screen", "map_prior_seen",
        ]),
        "checked_against_preregistered": sorted(checks),
        "similarity_threshold": M.SIM_THRESHOLD,
        "n_code_stop_tokens": len(M.CODE_STOP),
        "n_text_stop_tokens": len(M.TEXT_STOP),
        "code_stop_sha256": sha256_text(json.dumps(sorted(M.CODE_STOP))),
        "text_stop_sha256": sha256_text(json.dumps(sorted(M.TEXT_STOP))),
        "decision_function": "review_candidate_frame_mrl15.spec_review (imported verbatim)",
    }


def resolve_source(frame_manifest: dict, path: Path | None = None) -> tuple[Path, dict, dict]:
    """Resolve the MBPP source from the manifest and verify its sha256 before reading."""
    expected = frame_manifest["source"]["mbpp_sha256"]
    tried = []
    cands = [Path(path)] if path else \
        [Path(frame_manifest["source"]["mbpp_path"])] + [ROOT / c for c in SOURCE_FALLBACKS]
    for cand in cands:
        tried.append(str(cand))
        if not cand.exists():
            continue
        raw = cand.read_bytes()
        got = sha256_bytes(raw)
        if got != expected:
            raise SystemExit(f"MBPP source sha256 mismatch at {cand}: {got} != {expected}")
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        if len(rows) != frame_manifest["source"]["mbpp_rows"]:
            raise SystemExit(f"MBPP row count {len(rows)} != manifest "
                             f"{frame_manifest['source']['mbpp_rows']}")
        mbpp = {int(r["task_id"]): r for r in rows}
        info = {"mbpp_path": rel(cand), "mbpp_path_as_recorded":
                frame_manifest["source"]["mbpp_path"], "mbpp_sha256": got,
                "sha256_verified_before_read": True, "mbpp_rows": len(rows),
                "paths_tried": [rel(Path(t)) for t in tried],
                "fields_read": list(SOURCE_FIELDS_READ)}
        return cand, mbpp, info
    raise SystemExit("MBPP source not found; tried: " + "; ".join(tried))


def rebuild_frame(mbpp: dict) -> dict:
    """Re-run the MRL-15 selection with the imported criteria (no re-typed thresholds)."""
    frame, screen_info = M.verify_screen()
    prior_mbpp, prior_info = M.map_prior_seen()
    missing = [t for t in frame if t not in mbpp]
    if missing:
        raise SystemExit(f"frame ids missing from MBPP source: {missing}")
    prior_all = set(prior_mbpp) | set(M.E11_DEV_ROOTS)
    prior_in_source = sorted(t for t in prior_all if t in mbpp)
    excluded: dict[int, dict] = {}

    step1 = []
    for t in frame:
        if t in prior_all:
            src = []
            if t in prior_mbpp:
                src.append("dev_release_v1c.prior_seen_root_ids")
            if t in M.E11_DEV_ROOTS:
                src.append("E11/dev inspected root")
            excluded[t] = {"step": "i_prior_seen", "reason": " + ".join(src)}
        else:
            step1.append(t)

    feats = {t: (M.text_tokens(mbpp[t]["text"]), M.code_tokens(mbpp[t]["code"]))
             for t in set(frame) | set(prior_in_source)}

    nearest_prior = {}
    for t in frame:
        best = (-1.0, None)
        for p in prior_in_source:
            if p == t:
                continue
            s = M.sim(feats[t], feats[p])
            if s > best[0] or (s == best[0] and p < (best[1] or 10**9)):
                best = (s, p)
        nearest_prior[t] = {"task_id": best[1], "score": best[0]}
    step2 = []
    for t in step1:
        if nearest_prior[t]["score"] >= M.SIM_THRESHOLD:
            excluded[t] = {"step": "ii_near_duplicate_of_prior_seen",
                           "reason": f"score {nearest_prior[t]['score']} >= {M.SIM_THRESHOLD} "
                                     f"vs prior-seen mbpp/{nearest_prior[t]['task_id']}"}
        else:
            step2.append(t)

    uf = M.UF(step2)
    nearest_frame = {}
    for a in step2:
        best = (-1.0, None)
        for b in step2:
            if a == b:
                continue
            s = M.sim(feats[a], feats[b])
            if s > best[0] or (s == best[0] and b < (best[1] or 10**9)):
                best = (s, b)
            if s >= M.SIM_THRESHOLD and a < b:
                uf.union(a, b)
        nearest_frame[a] = {"task_id": best[1], "score": best[0]}
    fams: dict[int, list[int]] = {}
    for t in step2:
        fams.setdefault(uf.find(t), []).append(t)
    fam_label, fam_size = {}, {}
    for root, members in fams.items():
        for m in members:
            fam_label[m] = f"PF-{min(members)}" if len(members) > 1 else f"PF-{m}"
            fam_size[m] = len(members)
    step3 = []
    for root, members in sorted(fams.items()):
        keep = min(members, key=M.seed_key)
        step3.append(keep)
        for m in members:
            if m != keep:
                excluded[m] = {"step": "ii_within_frame_family",
                               "reason": f"provisional family {fam_label[m]}; kept "
                                         f"{keep} (smallest seeded hash)"}
    ordered = sorted(step3, key=lambda t: (M.seed_key(t), t))
    return {"ordered": ordered, "excluded": excluded, "fam_label": fam_label,
            "fam_size": fam_size, "nearest_prior": nearest_prior,
            "nearest_frame": nearest_frame, "screen_info": screen_info,
            "prior_info": prior_info, "n_prior_in_source": len(prior_in_source)}


def carried_forward(frame_manifest: dict) -> dict:
    """Preserve ranks 1-20 dispositions and all mechanical exclusions; do not revisit."""
    prior_records = json.loads((FRAME_DIR / "records.json").read_bytes())
    ranks_1_20 = {r["task_id"]: r for r in prior_records}
    mech = sorted(t for t, r in ranks_1_20.items()
                  if r["spec_review"]["decision"] in ("hold", "exclude"))
    for t in CARRIED_MECHANICAL_HOLDS:
        if t not in ranks_1_20 or ranks_1_20[t]["spec_review"]["decision"] != "hold":
            raise SystemExit(f"expected carried-forward hold mbpp/{t} not found at ranks 1-20")
    if sorted(mech) != sorted(CARRIED_MECHANICAL_HOLDS):
        raise SystemExit(f"ranks 1-20 mechanical holds changed: {mech}")
    for t in CARRIED_SEMANTIC_HOLDS:
        if t not in ranks_1_20:
            raise SystemExit(f"semantic hold mbpp/{t} is not a rank 1-20 record")
    return {
        "ranks_1_20_ids": [r["task_id"] for r in prior_records],
        "mechanical_holds_ranks_1_20": [
            {"task_id": t, "rank": ranks_1_20[t]["rank"], "status": "hold",
             "revisited": False} for t in CARRIED_MECHANICAL_HOLDS],
        "semantic_holds_ranks_1_20": {
            "ids": list(CARRIED_SEMANTIC_HOLDS), "status": "hold", "revisited": False,
            "source": rel(E12_DOC),
            "source_sha256": sha256_bytes(E12_DOC.read_bytes()) if E12_DOC.exists() else None},
        "mechanical_exclusions_preserved": len(frame_manifest["excluded"]),
        "mechanical_exclusions_sha256": sha256_text(
            json.dumps(frame_manifest["excluded"], sort_keys=True)),
        "policy": "no hold is replaced, reopened or re-decided; no backfill beyond rank 40; "
                  "ranks 41-198 are not inspected",
    }


def build(source_path: Path | None = None, frame_manifest_path: Path | None = None):
    fm, fm_sha = load_frame_manifest(frame_manifest_path)
    ident = criteria_identity(fm)
    src_path, mbpp, src_info = resolve_source(fm, source_path)

    committed = fm["eligible_ordered_ids"]
    if len(committed) != 198:
        raise SystemExit(f"frame has {len(committed)} eligible ids, expected 198")
    slice_ids = committed[RANK_LO - 1:RANK_HI]
    if slice_ids != EXPECTED_IDS:
        raise SystemExit(f"ranks {RANK_LO}-{RANK_HI} of the committed frame are {slice_ids}, "
                         f"not the MRL-22 list {EXPECTED_IDS}")
    reviewed_before = set(fm["review_ids"])
    overlap = sorted(reviewed_before & set(slice_ids))
    if overlap:
        raise SystemExit(f"ranks {RANK_LO}-{RANK_HI} overlap already-reviewed ids: {overlap}")

    fr = rebuild_frame(mbpp)
    if fr["ordered"] != committed:
        raise SystemExit("recomputed eligible order does not reproduce the committed frame")
    recomputed_excl = {str(k): v for k, v in sorted(fr["excluded"].items())}
    if recomputed_excl != fm["excluded"]:
        raise SystemExit("recomputed exclusions do not reproduce the committed frame")

    cf = carried_forward(fm)
    records = []
    for rank, t in zip(range(RANK_LO, RANK_HI + 1), slice_ids):
        row = mbpp[t]
        used = {k: row.get(k) for k in SOURCE_FIELDS_READ}
        ep, arity, ep_info = M.entry_point(used["code"])
        sr = M.spec_review(row, ep, arity, ep_info)
        records.append({
            "rank": rank, "task_id": t, "seed_hash": M.seed_key(t),
            "text": used["text"], "text_sha256": sha256_text(used["text"]),
            "reference_code_sha256": sha256_text(used["code"]),
            "test_list_sha256": sha256_text(json.dumps(used["test_list"])),
            "entry_point": ep, "arity": arity,
            "n_official_tests": len(used["test_list"]),
            "n_challenge_tests": len(used["challenge_test_list"] or []),
            "provisional_family": fr["fam_label"][t],
            "family_size_in_frame": fr["fam_size"][t],
            "nearest_prior_seen": fr["nearest_prior"][t],
            "nearest_in_frame": fr["nearest_frame"][t],
            "spec_review": sr,
            "mechanical_decision": sr["decision"],
            "outcome_information_used": "none",
        })

    inputs_opened = sorted({
        rel(FRAME_DIR / "manifest.json"), rel(FRAME_DIR / "records.json"),
        rel(MRL15_SCRIPT), src_info["mbpp_path"], rel(M.PRIOR_CONFIG),
        rel(M.SCREEN_DIR / "usable_ids.json"), rel(M.SCREEN_DIR / "summary.json"),
        rel(M.SCREEN_DIR / "per_candidate.json"), rel(E12_DOC),
    })
    offending = sorted(p for p in inputs_opened
                       if any(m in p.lower() for m in FORBIDDEN_INPUT_MARKERS))
    if offending:
        raise SystemExit(f"outcome-bearing input path opened: {offending}")

    manifest = {
        "task": "MRL-22 mechanical screen of candidate-frame ranks 21-40 "
                "(lead commit c32923c, docs/mrl21_review_mrl22_20260923.md)",
        "status": "mechanical screen only; not a semantic contract review, not collection "
                  "authorization, not a family-independence certificate",
        "scope": {"ranks": [RANK_LO, RANK_HI], "n_records": len(records),
                  "task_ids_in_committed_order": slice_ids,
                  "frame_dir": rel(FRAME_DIR), "frame_manifest_sha256": fm_sha,
                  "frame_eligible_ordered_ids_n": len(committed),
                  "ranks_reviewed_before": sorted(reviewed_before),
                  "no_backfill_beyond_rank_40": True, "no_rerank": True,
                  "ranks_41_198_inspected": False,
                  "protected_note": "only committed[20:40] was sliced; no record beyond "
                                    "rank 40 was loaded, scored or reported"},
        "source": {**src_info, "screen_verification": fr["screen_info"],
                   "prior_seen": fr["prior_info"],
                   "prior_seen_mbpp_in_source": fr["n_prior_in_source"],
                   "e11_dev_roots": list(M.E11_DEV_ROOTS)},
        "criteria_identity": ident,
        "preregistered": fm["preregistered"],
        "criteria_reproduction": {
            "eligible_ordered_ids_reproduced": True,
            "excluded_map_reproduced": True,
            "note": "the MRL-15 selection was re-executed with the imported constants and "
                    "functions; both the full 198-id order and the exclusion map matched the "
                    "committed frame, so the criteria are provably unchanged",
            "threshold_sensitivity": "unchanged from the MRL-15 manifest "
                                     "(reported-not-used; not recomputed, never selective)"},
        "carried_forward": cf,
        "decision_counts": {d: sum(1 for r in records if r["mechanical_decision"] == d)
                            for d in ("include", "hold", "exclude")},
        "outcome_inspection": {
            "model_outcomes_inspected": False,
            "outcome_fields_read": [],
            "source_fields_read": list(SOURCE_FIELDS_READ),
            "decision_function": ident["decision_function"],
            "decision_function_reads_no_outcome_field": True,
            "note": "the decision function is spec_review, whose inputs are the MBPP task "
                    "text, the parsed reference signature and the source assertion shapes "
                    "only. No grades file, analysis report, public-check record, private "
                    "execution record or hidden score was opened, and no candidate was "
                    "chosen by expected receiver difficulty.",
            "inputs_opened": inputs_opened},
        "execution": {"exec_eval_subprocess": False, "model_calls": 0, "model_tokens": 0,
                      "network": False, "installs": 0,
                      "static_ops": ["ast.parse", "compile", "hashlib.sha256", "json.loads"]},
        "reproduce": "python3 scripts/review_candidate_frame_ranks21_40.py --out-dir "
                     "results/frame_review_ranks21_40_20260923",
    }
    return manifest, records


def serialize(manifest: dict, records: list) -> tuple[bytes, bytes]:
    rec_bytes = json.dumps(records, indent=1, sort_keys=True).encode()
    manifest = dict(manifest)
    manifest["records_sha256"] = hashlib.sha256(rec_bytes).hexdigest()
    man_bytes = json.dumps(manifest, indent=1, sort_keys=True).encode()
    return man_bytes, rec_bytes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    if not out.is_absolute():
        out = ROOT / out
    existing = [p.name for p in (out / "records.json", out / "manifest.json") if p.exists()]
    if existing:
        raise SystemExit(f"refusing to overwrite existing artifacts in {out}: {existing}")
    if out.resolve() == FRAME_DIR.resolve():
        raise SystemExit("refusing to write into the immutable MRL-15 frame directory")
    manifest, records = build()
    man_bytes, rec_bytes = serialize(manifest, records)
    out.mkdir(parents=True, exist_ok=True)
    (out / "records.json").write_bytes(rec_bytes)
    (out / "manifest.json").write_bytes(man_bytes)
    print(json.dumps({"ranks": [RANK_LO, RANK_HI],
                      "task_ids": manifest["scope"]["task_ids_in_committed_order"],
                      "decisions": manifest["decision_counts"],
                      "records_sha256": hashlib.sha256(rec_bytes).hexdigest(),
                      "model_calls": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
