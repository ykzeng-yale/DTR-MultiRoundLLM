#!/usr/bin/env python3
"""MRL-36: deterministic source inputs for the lead's family/contract adjudication of the 43 unresolved roots.

Preparation only (docs/policy_candidate_audit_inputs_20260926.md): no family decision, semantic repair, benchmark,
reference or assertion execution, model call, download or fit. Benchmark text is read as inert text/AST; literal flags come
from ast.literal_eval on single AST nodes only (never eval/exec/compile). Every record is family_adjudication=pending and
approved=false. Similarity uses the exact pinned helper scripts/review_candidate_frame_mrl15.py (verified by SHA256 before
import): score = max(text-token Jaccard, code-token Jaccard). The tracked output keeps hashes, scores, UIDs, public
descriptions, type names, container sizes and flags only: no raw code, assertions, fixture inputs or expected values.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "policy-candidate-audit-inputs-v1"
EXPECTED_IDS = (911, 667, 344, 524, 814, 187, 194, 356, 366, 302, 877, 345, 885, 679, 176, 354, 169, 901, 200, 685, 883,
                711, 340, 613, 548, 506, 654, 710, 955, 298, 827, 547, 828, 192, 703, 700, 811, 961, 833, 903, 656, 36, 921)
E11_ROOTS = (52, 357, 373, 378, 402, 489, 509)
MEASUREMENT_DEVELOPMENT = {877: "measurement_development (LEAD-ENDPOINT-01/06 panel)",
                           345: "measurement_development (LEAD-ENDPOINT-01/06 panel)"}
TOP_K = 6
DEFAULT_PATHS = {
    "reconciliation": "results/policy_full_frame_reconciliation_20260926.json",
    "frame_review_161_198": "results/policy_frame_review_ranks161_198_20260926.json",
    "mbpp": "work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl",
    "pool": "work/data/tasks.json",
    "helper": "scripts/review_candidate_frame_mrl15.py",
}
PINS = {  # sha256 of the raw file bytes
    "mbpp": "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f",
    "pool": "23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce",
    "helper": "9882fb0c507fb1f2da930f46bdea36eae13e681561985695cf7ddd2890f9a720",
    "frame_review_161_198": "e9dea0d196118dd776162cc15285fffac6edf500b8ae5186b367c3896e3de00e",
    "reconciliation": "744b0f393ba7b739ed64087d190d406908fe8f8b6063032a6b300cd1f4cbfbff",  # as committed at 7acbcba
}


class InputRefused(ValueError):
    """An input file is missing, does not match its pin, or has an unexpected structure."""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def read_pinned(path, pin) -> bytes:
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        raise InputRefused(f"{path}: unreadable ({type(e).__name__})") from None
    if pin is not None and sha256_bytes(data) != pin:
        raise InputRefused(f"{path}: sha256 {sha256_bytes(data)} != pin {pin}")
    return data


def load_helper(path, pin):
    read_pinned(path, pin)  # verify the exact trusted helper before importing it
    spec = importlib.util.spec_from_file_location("mrl15_helper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # module-level constants and defs only; its main() is guarded
    return module


# ---------------------------------------------------------------- inert AST features
def _literal_info(node) -> dict:
    try:
        value = ast.literal_eval(node)  # a single literal node; no name lookup, call or evaluation
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return {"literal": False, "node_type": type(node).__name__, "status": "nonliteral_unsupported"}
    info = {"literal": True, "node_type": type(node).__name__, "value_type": type(value).__name__,
            "value_repr_sha256": sha256_text(repr(value))}
    if isinstance(value, (list, tuple, set, dict, str, bytes, frozenset)):
        info["container_size"] = len(value)
    return info


def first_assertion_shape(text: str, entry_point: str | None) -> dict:
    """Shape and literal flags of the public first assertion; values are never retained, only hashes/types/sizes."""
    out = {"assertion_sha256": sha256_text(text)}
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        return {**out, "parse": f"unparseable ({type(e).__name__})"}
    body = tree.body
    if len(body) != 1 or not isinstance(body[0], ast.Assert):
        return {**out, "parse": "not a single assert", "statement_types": [type(n).__name__ for n in body]}
    test = body[0].test
    out.update(parse="single_assert", has_message=body[0].msg is not None, test_node=type(test).__name__)
    if not isinstance(test, ast.Compare):
        out["shape"] = "unsupported_non_compare"
        return out
    out["compare_ops"] = [type(op).__name__ for op in test.ops]
    left = test.left
    if isinstance(left, ast.Call):
        func = left.func
        name = func.id if isinstance(func, ast.Name) else None
        out.update(left="Call", call_func_node=type(func).__name__, call_name_is_entry_point=bool(name and name == entry_point),
                   n_args=len(left.args), n_keywords=len(left.keywords),
                   args=[_literal_info(a) for a in left.args],
                   keywords=[{"arg": k.arg, **_literal_info(k.value)} for k in left.keywords])
    else:
        out.update(left=type(left).__name__, left_is_call=False, left_info=_literal_info(left))
    out["comparators"] = [_literal_info(c) for c in test.comparators]
    literal_args = isinstance(left, ast.Call) and all(a["literal"] for a in out["args"] + out["keywords"])
    out["all_call_arguments_literal"] = bool(literal_args)
    out["expected_literal"] = all(c["literal"] for c in out["comparators"])
    out["note"] = "syntax flag only; not a diagnostic-display approval or a semantic type guarantee"
    return out


def _entry_point(code: str):
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return None
    defs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    return defs[-1] if defs else None


# ---------------------------------------------------------------- retrieval
def comparators(pool_rows, mbpp, e11_roots, helper) -> list:
    """(uid, scope, variant, features, public description) for every prior comparator variant."""
    out = []
    for r in pool_rows:
        uid = r["uid"]
        out.append((uid, "canonical_pool", "canonical", (helper.text_tokens(r["prompt"]), helper.code_tokens(r["reference"])),
                    r["prompt"]))
        if r.get("benchmark") == "mbpp":
            tid = int(r["source_task_id"])
            if tid in mbpp:
                m = mbpp[tid]
                out.append((uid, "canonical_pool", "original_mbpp", (helper.text_tokens(m["text"]), helper.code_tokens(m["code"])),
                            m["text"]))
    for tid in e11_roots:
        m = mbpp[tid]
        out.append((f"mbpp/{tid}", "e11_dev", "original_mbpp", (helper.text_tokens(m["text"]), helper.code_tokens(m["code"])),
                    m["text"]))
    return out


def top_prior(root_feats, root_uid, comps, helper, k=TOP_K) -> list:
    best = {}
    for uid, scope, variant, feats, desc in comps:
        if uid == root_uid:
            continue  # self exclusion
        score = helper.sim(root_feats, feats)
        key = (-score, uid, scope, variant)
        if uid not in best or key < best[uid][0]:
            best[uid] = (key, {"uid": uid, "scope": scope, "winning_variant": variant, "score": score,
                               "public_description": desc})
    ranked = sorted(best.values(), key=lambda kv: kv[0])  # score desc, then UID, then scope ascending
    return [v for _, v in ranked[:k]]


def top_frame(root, frame_feats, frame_meta, mbpp, helper, k=TOP_K) -> list:
    rows = []
    for tid, feats in frame_feats.items():
        if tid == root:
            continue
        s = helper.sim(frame_feats[root], feats)
        meta = frame_meta[tid]
        rows.append(((-s, tid), {"task_id": tid, "source_rank": meta["rank"], "score": s,
                                 "historical_class": meta["historical_class"], "source_disposition": meta["source_disposition"],
                                 "current_overlay": meta["current_overlay"], "public_description": mbpp[tid]["text"]}))
    rows.sort(key=lambda kv: kv[0])
    return [v for _, v in rows[:k]]


# ---------------------------------------------------------------- build
def build(reconciliation: dict, mbpp: dict, pool_rows: list, helper, provenance: dict) -> dict:
    records = reconciliation["records"]
    if len(records) != 198 or len({r["task_id"] for r in records}) != 198:
        raise InputRefused("reconciliation must hold exactly 198 unique fixed-frame roots")
    selected = [r for r in sorted(records, key=lambda r: r["rank"])
                if r["historical_class"] == "candidate" and r["prior_receiver_development"] is False
                and r["current_overlay"] == "none"]
    ids = tuple(r["task_id"] for r in selected)
    if ids != EXPECTED_IDS:
        raise InputRefused(f"selected roots {ids} differ from the 43 IDs fixed by MRL-36")
    uids = [r["uid"] for r in pool_rows]
    if len(uids) != len(set(uids)):
        raise InputRefused("duplicate UID in the canonical pool")
    missing = [t for t in [*(r["task_id"] for r in records), *E11_ROOTS] if t not in mbpp]
    if missing:
        raise InputRefused(f"roots missing from the MBPP source: {missing}")
    frame_meta = {r["task_id"]: r for r in records}
    frame_feats = {t: (helper.text_tokens(mbpp[t]["text"]), helper.code_tokens(mbpp[t]["code"])) for t in frame_meta}
    comps = comparators(pool_rows, mbpp, E11_ROOTS, helper)
    pool_uids = set(uids)
    out = []
    for r in selected:
        t = r["task_id"]
        m = mbpp[t]
        ep = _entry_point(m["code"])
        exposure = {"prior_receiver_development": r["prior_receiver_development"],
                    "in_canonical_prior_pool": f"mbpp/{t}" in pool_uids, "e11_dev_root": t in E11_ROOTS,
                    "measurement_development": MEASUREMENT_DEVELOPMENT.get(t),
                    "provenance": "results/policy_full_frame_reconciliation_20260926.json records[] and pinned inputs",
                    "note": "false means none recorded in these sources, not certified unexposed or absent from model training"}
        out.append({
            "task_id": t, "uid": f"mbpp/{t}", "rank": r["rank"],
            "source_hashes": {"description_sha256": sha256_text(m["text"]), "reference_sha256": sha256_text(m["code"]),
                              "assertion_sha256": [sha256_text(a) for a in m["test_list"]]},
            "earlier_source_review": {k: r[k] for k in ("source_record", "source_disposition", "source_review_basis",
                                                         "historical_class", "current_overlay")},
            "exposure_tags": exposure,
            "prior_neighbors_top6": top_prior(frame_feats[t], f"mbpp/{t}", comps, helper),
            "frame_neighbors_top6": top_frame(t, frame_feats, frame_meta, mbpp, helper),
            "public_first_assertion": first_assertion_shape(m["test_list"][0], ep),
            "family_adjudication": "pending", "approved": False,
        })
    return {"version": VERSION, "assignment": "MRL-36", "record_type": "preparation_inputs_not_a_family_decision",
            "provenance": provenance, "n_roots": len(out), "root_order": list(ids),
            "similarity_rule": helper.SIM_RULE + " (thresholds are not eligibility rules here)",
            "retrieval": {"prior_scopes": ["canonical_pool (591 UIDs; canonical prompt/reference and, for MBPP UIDs, the "
                                           "original MBPP text/code variant)", "e11_dev (7 original MBPP roots)"],
                          "per_uid_score": "max over that UID's variants; ties broken by UID then scope ascending",
                          "frame": "all 198 fixed-frame roots, original MBPP text/code; self excluded", "top_k": TOP_K},
            "records": out,
            "limitations": ["Lexical similarity is retrieval evidence for manual review, not a family, eligibility or "
                            "independence decision.",
                            "HumanEval pool UIDs are compared through their canonical prompt/reference only.",
                            "Literal flags are syntactic (ast.literal_eval on single nodes); nonliteral expressions are "
                            "unsupported, not evaluated.",
                            "No exposure guarantee: absent tags mean nothing was recorded in these sources.",
                            "Every record is family_adjudication=pending, approved=false; Codex adjudicates."]}


def load_inputs(paths: dict, pins: dict):
    recon_bytes = read_pinned(paths["reconciliation"], pins["reconciliation"])
    frame_bytes = read_pinned(paths["frame_review_161_198"], pins["frame_review_161_198"])
    mbpp_bytes = read_pinned(paths["mbpp"], pins["mbpp"])
    pool_bytes = read_pinned(paths["pool"], pins["pool"])
    helper = load_helper(paths["helper"], pins["helper"])
    try:
        recon = json.loads(recon_bytes)
        frame = json.loads(frame_bytes)
        mbpp = {}
        for line in mbpp_bytes.decode("utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if int(row["task_id"]) in mbpp:
                    raise InputRefused(f"duplicate MBPP task_id {row['task_id']}")
                mbpp[int(row["task_id"])] = row
        pool = json.loads(pool_bytes)
    except (ValueError, KeyError, UnicodeDecodeError) as e:
        raise InputRefused(f"malformed input: {type(e).__name__}") from None
    if frame.get("retrieval_helper_sha256") != pins["helper"]:
        raise InputRefused("frame review's retrieval helper pin differs from the helper pin")
    provenance = {name: {"path": str(Path(p).as_posix()), "sha256": sha256_bytes(Path(p).read_bytes())} for name, p in paths.items()}
    provenance["preparation_script"] = {"path": "scripts/prepare_policy_candidate_audit.py", "sha256": sha256_bytes(Path(__file__).read_bytes())}
    return recon, mbpp, pool, helper, provenance


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name, default in DEFAULT_PATHS.items():
        ap.add_argument(f"--{name.replace('_', '-')}", default=default)
    ap.add_argument("--out", required=True, help="new output file (never overwritten)")
    a = ap.parse_args(argv)
    paths = {name: getattr(a, name) for name in DEFAULT_PATHS}
    if Path(a.out).exists():
        print(f"refused: output {a.out} already exists (never overwritten)")
        return 2
    try:
        recon, mbpp, pool, helper, prov = load_inputs(paths, PINS)
        doc = build(recon, mbpp, pool, helper, prov)
        with open(a.out, "x", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False) + "\n")
    except (InputRefused, FileExistsError) as e:
        print(f"refused: {type(e).__name__}: {e}")
        return 2
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
