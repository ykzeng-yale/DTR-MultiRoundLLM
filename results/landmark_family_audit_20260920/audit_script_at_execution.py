#!/usr/bin/env python3
"""Source-only duplicate screening and immutable seeded development curation.

Parses reference ASTs; never imports, evaluates, compiles, or executes task code.
Similarity is a review aid, not a semantic-independence certificate.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata
import warnings

SEED = "landmark-development-20260920-v1"
SLATE_SIZE = 24
EXPECTED_FULL_SHA = "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"
EXPECTED_CANONICAL_SHA = "23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce"
STOP = set("a an the write python function given to of in and or for from with that which is are be as by using find check return".split())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def terms(text: str) -> Counter:
    return Counter(t for t in re.findall(r"\w+", normalize(text)) if t not in STOP)


def select_slate(pool: list[int], seed: str = SEED, size: int = SLATE_SIZE) -> list[int]:
    if len(set(pool)) != len(pool) or len(pool) < size:
        raise ValueError("Candidate IDs must be unique and sufficient for the fixed slate")
    return sorted(pool, key=lambda i: (sha(f"{seed}:{i}".encode()), i))[:size]


def cosine(left: dict, right: dict) -> float:
    denom = math.sqrt(sum(v*v for v in left.values()) * sum(v*v for v in right.values()))
    return sum(v*right.get(k, 0) for k, v in left.items()) / denom if denom else 0.0


def parse_source(source: str) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(source)


class Shape(ast.NodeTransformer):
    """Coarse identifier-erased AST; constants and attribute names remain.

    This intentionally loses binding distinctions and is only a flag for review.
    """
    def visit_Name(self, node):
        node.id = "IDENTIFIER"
        return node

    def visit_arg(self, node):
        node.arg = "ARGUMENT"
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.name = "FUNCTION"
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


def code_features(source: str) -> dict:
    try:
        tree = parse_source(source)
    except SyntaxError:
        return {"parse_error": True, "shape_hashes": [], "node_bigrams": {}, "function_names": []}
    functions = [x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
    hashes = []
    for function in functions:
        normalized = Shape().visit(copy.deepcopy(function))
        hashes.append(sha(ast.dump(normalized, include_attributes=False).encode()))
    types = [type(x).__name__ for x in ast.walk(tree)]
    pairs = Counter(f"{a}/{b}" for a, b in zip(types, types[1:]))
    return {"parse_error": False, "shape_hashes": sorted(set(hashes)),
            "node_bigrams": dict(pairs), "function_names": [f.name for f in functions]}


def interface(source: str) -> dict:
    """Only a zero-default, unannotated single-function interface is exportable."""
    tree = parse_source(source)
    funcs = [x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(funcs) != 1:
        return {"public_signature_candidate": None, "interface_flags": ["multiple_or_missing_top_level_functions"]}
    f = funcs[0]
    flags = []
    args = f.args
    if args.defaults or any(x is not None for x in args.kw_defaults):
        flags.append("defaults_require_manual_leakage_and_semantic_review")
    allargs = args.posonlyargs + args.args + args.kwonlyargs + ([args.vararg] if args.vararg else []) + ([args.kwarg] if args.kwarg else [])
    if f.returns or any(a.annotation for a in allargs):
        flags.append("annotations_require_manual_leakage_and_semantic_review")
    if f.decorator_list:
        flags.append("decorators_require_manual_review")
    signature = None if flags else f"def {f.name}({ast.unparse(args)}):"
    return {"entry_point": f.name, "public_signature_candidate": signature, "interface_flags": flags}


def screen(full: dict[int, dict], canonical: list[dict], candidates: list[int]) -> list[dict]:
    old = []
    for task in canonical:
        old.append({"uid": task["uid"], "variant": "canonical", "prompt": task["prompt"],
                    "code": task.get("reference", "")})
        if task["benchmark"] == "mbpp":
            original = full[int(task["source_task_id"])]
            old.append({"uid": task["uid"], "variant": "full_original", "prompt": original["text"], "code": original["code"]})
    # IDF fit only on source descriptions, across the complete frozen screen corpus.
    documents = [terms(x["prompt"]) for x in old] + [terms(full[i]["text"]) for i in candidates]
    df = Counter(k for doc in documents for k in doc)
    idf = {k: 1.0 + math.log((len(documents)+1)/(n+1)) for k, n in df.items()}
    vector = lambda text: {k: v*idf[k] for k, v in terms(text).items()}
    for task in old:
        task["vector"] = vector(task["prompt"])
        task["features"] = code_features(task["code"])
    rows = []
    for i in sorted(candidates):
        task = full[i]
        v = vector(task["text"])
        features = code_features(task["code"])
        # Collapse source variants by root, retaining the strongest lexical evidence.
        by_uid = {}
        for prior in old:
            lexical = cosine(v, prior["vector"])
            structural = cosine(features["node_bigrams"], prior["features"]["node_bigrams"])
            shape = bool(set(features["shape_hashes"]) & set(prior["features"]["shape_hashes"]))
            names = sorted(set(features["function_names"]) & set(prior["features"]["function_names"]))
            hit = {"prior_uid": prior["uid"], "prior_variant": prior["variant"],
                   "lexical_cosine": round(lexical, 8), "structural_node_bigram_cosine": round(structural, 8),
                   "identifier_erased_function_shape_match": shape, "shared_function_names": names}
            prev = by_uid.get(prior["uid"])
            if prev is None:
                by_uid[prior["uid"]] = hit
            else:
                better = lexical > prev["lexical_cosine"]
                kept = hit if better else prev
                kept["identifier_erased_function_shape_match"] = shape or prev["identifier_erased_function_shape_match"]
                kept["shared_function_names"] = sorted(set(names) | set(prev["shared_function_names"]))
                kept["structural_node_bigram_cosine"] = max(hit["structural_node_bigram_cosine"], prev["structural_node_bigram_cosine"])
                by_uid[prior["uid"]] = kept
        hits = list(by_uid.values())
        top = sorted(hits, key=lambda x: (-x["lexical_cosine"], x["prior_uid"]))[:8]
        structural_hits = sorted((x for x in hits if x["identifier_erased_function_shape_match"] or x["shared_function_names"]), key=lambda x: (-x["lexical_cosine"], x["prior_uid"]))
        rows.append({"task_id": i, "public_description_sha256": sha(task["text"].encode()),
                     "normalized_description_sha256": sha(normalize(task["text"]).encode()),
                     "reference_source_sha256": sha(task["code"].encode()),
                     "top_lexical_prior_roots": top, "structural_or_name_prior_flags": structural_hits,
                     "lexical_review_flag": bool(top and top[0]["lexical_cosine"] >= .6),
                     "reference_parse_error": features["parse_error"], **interface(task["code"])})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path)
    args = parser.parse_args()
    full_bytes, canonical_bytes = args.full.read_bytes(), args.canonical.read_bytes()
    if sha(full_bytes) != EXPECTED_FULL_SHA or sha(canonical_bytes) != EXPECTED_CANONICAL_SHA:
        raise ValueError("Source hashes changed; revise the source contract explicitly")
    full = {x["task_id"]: x for x in map(json.loads, full_bytes.splitlines())}
    canonical = json.loads(canonical_bytes)
    audit_bytes = args.source_audit.read_bytes()
    source_audit = json.loads(audit_bytes)
    candidates = sorted(i for i in source_audit["after_prior_prompt_duplicate_exclusion_ids"] if 11 <= i <= 510)
    if len(candidates) != 242:
        raise ValueError("The frozen official-test candidate pool must have 242 IDs")
    slate = select_slate(candidates)
    rows = screen(full, canonical, candidates)
    rowmap = {x["task_id"]: x for x in rows}
    adjudications = []
    if args.adjudications:
        adjudications = json.loads(args.adjudications.read_text())["adjudications"]
        if {x["task_id"] for x in adjudications} != set(slate) or len(adjudications) != len(slate):
            raise ValueError("Adjudications must cover the entire fixed slate exactly once")
    groups = {}
    for review in adjudications:
        family = review["provisional_family"]
        group = groups.setdefault(family, {"selected_task_ids": [], "strongly_related_prior_roots": [],
                                          "independence_certified": False})
        group["selected_task_ids"].append(review["task_id"])
        if review["prior_relationship"].startswith("strong_"):
            group["strongly_related_prior_roots"] = sorted(set(group["strongly_related_prior_roots"]) | set(review["related_prior_roots"]))
    result = {"status": "source_only_development_curation_not_confirmatory_independence",
              "source_hashes": {"full_mbpp": sha(full_bytes), "canonical_tasks": sha(canonical_bytes),
                                "source_audit": sha(audit_bytes), "screening_script": sha(Path(__file__).read_bytes())},
              "selection": {"seed": SEED, "rule": "ascending SHA256 UTF8(seed + ':' + decimal_id), then ID; take 24",
                            "candidate_count": len(candidates), "candidate_ids": candidates, "selected_rank_order": slate,
                            "replacement_policy": "none", "outcomes_used": False},
              "screening": {"old_roots": len(canonical), "old_description_variants": len(canonical)+427,
                            "lexical": "TF count times IDF, cosine; explicit STOP terms in script; top 8 unique old roots; retains list/string/number tokens",
                            "structural": "identifier-erased function AST exact hash plus AST node-bigram cosine; constants retained; shared function names; best structural flag across source variants may differ from best lexical variant",
                            "threshold": ">=0.60 cosine prompts review only; never auto-certifies/excludes a family",
                            "limitations": "Lexical and AST similarities neither prove semantic equivalence nor certify independence. Structural similarity loses binding details. No task code executed."},
              "selected_screen": [rowmap[i] for i in slate], "adjudications": adjudications,
              "provisional_family_groups": groups,
              "adjudications_sha256": sha(args.adjudications.read_bytes()) if args.adjudications else None}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/"manifest.json").write_text(json.dumps(result, indent=2)+"\n")
    (args.out/"all_candidate_screen.json").write_text(json.dumps(rows, indent=2)+"\n")
    print(json.dumps({"candidate_count": len(candidates), "slate": slate, "adjudications": len(adjudications)}))


if __name__ == "__main__":
    main()
