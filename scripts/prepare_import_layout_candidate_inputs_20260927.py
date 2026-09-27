#!/usr/bin/env python3
"""MRL-40: static source inputs for the explicitly new import-layout inquiry (source only).

Inspects the 103 historical G2 interface exclusions marked one_function_imports_only=true in the lead's interface-shape audit
(docs/import_layout_candidate_scope_20260927.md). Every row stays a historical G2 exclusion; nothing is admitted, grouped or
reopened. Pure JSON/text/hash/token work plus inert ast.parse inspection: no exec, eval, compile, benchmark-module import,
subprocess or network. Similarity reimplements the pinned MRL-15 helper definitions exactly (max of text-token and code-token
Jaccard, rounded to 4 places); scores are evidence locators only, never thresholds. Tracked output holds hashes, public
descriptions (MBPP, CC BY 4.0, per the acquisition record) and layout metadata, never reference code or assertions.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import keyword
import re
import warnings
from pathlib import Path

VERSION = "import-layout-candidate-inputs-v1"
ISSUING_COMMIT = "163874e"
INPUTS = {
    "mbpp": ("work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl", "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"),
    "canonical_pool": ("work/data/tasks.json", "23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce"),
    "interface_audit": ("results/interface_exclusion_shape_audit_20260927.json", "52ce58aaf96431a24a55770e9391a5b83e0f1d24c8e0d81b50c078e1e9ed70e8"),
    "lineage_r1": ("results/source_frame_lineage_20260927_r1.json", "c3e2e63dbc41934eb8ddf02c7fa170b4ed48f09683f4833ac35ead8ae9b516b6"),
    "prior_seen_config": ("experiments/landmark/dev_release_v1c/config.json", "9b22b94cfdabf48ae36e8bdf27d748adc71465ace2b56e0ae5ff30d1a61b062a"),
    "mrl15_manifest": ("results/frame_review_mrl15_20260922T021718Z/manifest.json", "4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc"),
    "reconciliation_198": ("results/policy_full_frame_reconciliation_20260926.json", "744b0f393ba7b739ed64087d190d406908fe8f8b6063032a6b300cd1f4cbfbff"),
    "similarity_helper": ("scripts/review_candidate_frame_mrl15.py", "9882fb0c507fb1f2da930f46bdea36eae13e681561985695cf7ddd2890f9a720"),
}
EXPECTED_N = 103
TOP_K = 6
# Exact copies of the pinned helper's definitions (scripts/review_candidate_frame_mrl15.py, sha256 9882fb0c...).
CODE_STOP = set(keyword.kwlist) | {"self", "range", "len", "int", "str", "list", "dict", "set", "tuple", "print",
                                   "i", "j", "k", "x", "n", "0", "1", "2", "res", "result", "return"}
TEXT_STOP = {"write", "a", "the", "to", "function", "python", "of", "given", "in", "and", "for", "from", "is", "an", "by",
             "using", "find", "check", "whether", "or", "with", "be", "that"}


class InquiryRefused(ValueError):
    """An input, selection, shape or comparator check failed; nothing is written."""


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def text_tokens(s: str) -> frozenset:
    return frozenset(t for t in re.findall(r"[a-z0-9_]+", s.lower()) if t not in TEXT_STOP)


def code_tokens(s: str) -> frozenset:
    return frozenset(t for t in re.findall(r"[a-z0-9_]+", s.lower()) if t not in CODE_STOP)


def jac(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def sim(fa: tuple, fb: tuple) -> float:
    return round(max(jac(fa[0], fb[0]), jac(fa[1], fb[1])), 4)


def read_pinned(path, pin) -> bytes:
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        raise InquiryRefused(f"{path}: unreadable ({type(e).__name__}); production never falls back") from None
    if hashlib.sha256(data).hexdigest() != pin:
        raise InquiryRefused(f"{path}: sha256 differs from the pin")
    return data


def load_production(root=Path(".")) -> dict:
    d = {}
    for name, (rel, pin) in INPUTS.items():
        raw = read_pinned(Path(root) / rel, pin)
        if name == "mbpp":
            d[name] = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        elif name != "similarity_helper":
            d[name] = json.loads(raw)
    return d


def layout(code: str) -> dict:
    """Old-rule layout check: exactly one top-level plain function and only import statements besides it (inert AST)."""
    try:
        with warnings.catch_warnings():  # MBPP references contain invalid string escapes; parsing is inert either way
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        raise InquiryRefused(f"reference does not parse: {type(e).__name__}") from None
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    others = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.Import, ast.ImportFrom))]
    if len(funcs) != 1 or others:
        raise InquiryRefused(f"layout is not one function plus imports only: {len(funcs)} functions, "
                             f"other nodes {[type(n).__name__ for n in others]}")
    f = funcs[0]
    a = f.args
    # Exact old-rule plain condition (scripts/screen_landmark_pool.py interface()): no posonly/kwonly args, defaults, *args,
    # **kwargs, decorators, return annotation or argument annotations. Refused, not merely flagged.
    if a.posonlyargs or a.kwonlyargs or a.defaults or a.kwarg or a.vararg or f.decorator_list or f.returns \
            or any(x.annotation for x in a.args):
        raise InquiryRefused("function signature is not plain under the old rule")
    imports = []
    for n in tree.body:
        if isinstance(n, ast.Import):
            imports.append({"kind": "import", "module": None, "level": 0,
                            "names": [{"name": x.name, "alias": x.asname} for x in n.names]})
        elif isinstance(n, ast.ImportFrom):
            imports.append({"kind": "from", "module": n.module, "level": n.level,
                            "names": [{"name": x.name, "alias": x.asname} for x in n.names]})
    if not imports:
        raise InquiryRefused("layout has no import statement (the inquiry requires one plain function plus imports)")
    return {"function_name": f.name, "n_positional_params": len(a.args), "plain_signature_under_old_rule": True,
            "top_level_imports": imports, "n_import_statements": len(imports),
            "note": "reference layout metadata only; module names are not runtime-availability or security evidence and are "
                    "not content permitted for a future receiver prompt"}


def reconcile_inputs(d: dict) -> dict:
    """Pure inquiry over already-loaded inputs (the explicit synthetic seam for tests)."""
    mbpp = {}
    for row in d["mbpp"]:
        t = row.get("task_id")
        if type(t) is not int or t in mbpp:
            raise InquiryRefused(f"missing, non-integer or duplicate MBPP task_id {t!r}")
        mbpp[t] = row
    audit = d["interface_audit"]
    selected = sorted(r["task_id"] for r in audit["records"] if r.get("one_function_imports_only") is True)
    if len(selected) != len(set(selected)) or len(selected) != audit.get("one_function_imports_only") or len(selected) != d.get("expected_n", EXPECTED_N):
        raise InquiryRefused(f"selection has {len(selected)} IDs; audit declares {audit.get('one_function_imports_only')}")
    audit_by = {r["task_id"]: r for r in audit["records"]}
    lineage = {r["task_id"]: r for r in d["lineage_r1"]["rows"]}
    pool = d["canonical_pool"]
    pool_by = {r["uid"]: r for r in pool}
    if len(pool_by) != len(pool):
        raise InquiryRefused("duplicate canonical-pool UID")
    config_ids = list(d["prior_seen_config"]["prior_seen_root_ids"])
    e11 = [f"mbpp/{t}" for t in d["mrl15_manifest"]["source"]["e11_dev_roots"]]
    e12 = [f"mbpp/{r['task_id']}" for r in d["reconciliation_198"]["records"] if r.get("prior_receiver_development") is True]
    scopes = {}
    for scope, uids in (("canonical_pool", list(pool_by)), ("prior_seen_config", config_ids), ("e11_dev", e11),
                        ("e12_recorded_receiver_development", e12)):
        for u in uids:
            scopes.setdefault(u, set()).add(scope)
    comparators = []  # (uid, variant, features, description, description_sha256, reference_sha256, scopes)
    for u in sorted(scopes):
        variants = []
        if u in pool_by:
            p = pool_by[u]
            variants.append(("canonical", p["prompt"], p["reference"]))
        if u.startswith("mbpp/"):
            t = int(u.split("/")[1])
            if t in mbpp:
                variants.append(("original_mbpp", mbpp[t]["text"], mbpp[t]["code"]))
        if not variants:
            raise InquiryRefused(f"comparator {u} ({sorted(scopes[u])}) has no source in the named inputs")
        for label, text, code in variants:
            comparators.append((u, label, (text_tokens(text), code_tokens(code)), text, sha256_text(text), sha256_text(code),
                                sorted(scopes[u])))
    feats = {}
    rows = []
    for t in selected:
        if t not in mbpp:
            raise InquiryRefused(f"selected root {t} missing from the MBPP source")
        src = mbpp[t]
        ar = audit_by[t]
        if ar.get("historical_gate") != "G2_interface" or lineage.get(t, {}).get("terminal_category") != "mechanical_interface":
            raise InquiryRefused(f"root {t} is not a historical G2 interface exclusion in the audit and accepted lineage")
        if ar.get("reference_sha256") != sha256_text(src["code"]):
            raise InquiryRefused(f"root {t}: reference hash differs from the interface audit")
        lay = layout(src["code"])
        feats[t] = (text_tokens(src["text"]), code_tokens(src["code"]))
        uid = f"mbpp/{t}"
        flags = lineage[t]["flags_from_named_records"]
        rows.append({
            "task_id": t, "uid": uid,
            "source_digests": {"text_sha256": sha256_text(src["text"]), "reference_sha256": sha256_text(src["code"]),
                               "assertion_sha256": [sha256_text(a) for a in src["test_list"]]},
            "public_description": src["text"],
            "historical_gate": ar["historical_gate"], "historical_reason": ar.get("historical_reason"),
            "layout": lay,
            "setup_nonempty": bool(src.get("test_setup_code")), "challenge_test_count": len(src.get("challenge_test_list") or []),
            "exposure_flags_from_named_records": {
                "prior_identity_scopes": sorted(scopes.get(uid, set())),
                "in_canonical_pool": uid in pool_by, "in_prior_seen_config": uid in set(config_ids),
                "e11_dev_root": uid in set(e11), "e12_recorded_receiver_development": uid in set(e12),
                "lineage_r1_category": lineage[t]["terminal_category"], "lineage_r1_flags": flags,
            },
            "exposure": "unknown beyond the named records (no claim about model pretraining or cross-workspace use)",
            "approved_for_evaluation": False,
        })
    for row in rows:
        t, uid = row["task_id"], row["uid"]
        best = {}
        for u, label, f, text, dsha, rsha, sc in comparators:
            if u == uid:
                continue  # identical UID excluded from neighbours; its prior identity is kept in the flags above
            score = sim(feats[t], f)
            key = (-score, label)
            if u not in best or key < best[u][0]:
                best[u] = (key, {"uid": u, "score": score, "winning_variant": label, "public_description": text,
                                 "description_sha256": dsha, "reference_sha256": rsha, "provenance_scopes": sc})
        ranked = sorted(best.values(), key=lambda kv: (kv[0][0], kv[1]["uid"], kv[0][1]))
        row["prior_neighbors_top6"] = [v for _, v in ranked[:TOP_K]]
        within = sorted(((-sim(feats[t], feats[o]), o) for o in feats if o != t))
        row["within_103_neighbors_top6"] = [{"uid": f"mbpp/{o}", "task_id": o, "score": -s, "winning_variant": "original_mbpp",
                                             "public_description": mbpp[o]["text"], "description_sha256": sha256_text(mbpp[o]["text"]),
                                             "reference_sha256": sha256_text(mbpp[o]["code"])} for s, o in within[:TOP_K]]
    return {"version": VERSION, "issuing_commit": ISSUING_COMMIT, "record_type": "source_inquiry_not_admission",
            "attribution": "Public descriptions are from MBPP (google-research), CC BY 4.0, per the acquisition record.",
            "n_rows": len(rows),
            "summary_counts": {
                "one_function_imports_only": len(rows),
                "in_prior_seen_config": sum(r["exposure_flags_from_named_records"]["in_prior_seen_config"] for r in rows),
                "in_canonical_pool": sum(r["exposure_flags_from_named_records"]["in_canonical_pool"] for r in rows),
                "nonempty_challenge_lists": sum(r["challenge_test_count"] > 0 for r in rows),
                "nonempty_setup": sum(r["setup_nonempty"] for r in rows),
                "plain_signature_under_old_rule": sum(r["layout"]["plain_signature_under_old_rule"] for r in rows)},
            "prior_uid_universe": {"n_uids": len(scopes), "scopes": {s: sum(s in v for v in scopes.values()) for s in
                                   ("canonical_pool", "prior_seen_config", "e11_dev", "e12_recorded_receiver_development")}},
            "similarity_rule": "max(Jaccard(text tokens), Jaccard(code tokens)) rounded to 4 places, reimplemented from the pinned "
                               "MRL-15 helper; UID score = max over its variants (tie: variant label); ranking by score, then UID; "
                               "within-103 ties by numeric task_id; evidence locators only, never thresholds",
            "limits": ["Every row remains a historical G2 exclusion; nothing is admitted, grouped or reopened.",
                       "Import metadata describes the reference layout; it is not runtime-availability, safety or prompt content.",
                       "Lexical neighbours are not semantic-family decisions.",
                       "Exposure is unknown beyond the named records."],
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
        doc = reconcile_inputs(load_production())
    except InquiryRefused as e:
        print(f"refused: {e}")
        return 2
    doc["input_sha256"] = {n: pin for n, (_, pin) in INPUTS.items()}
    doc["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with open(out, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, sort_keys=True, ensure_ascii=False, indent=1) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
