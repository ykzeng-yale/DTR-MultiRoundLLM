#!/usr/bin/env python3
"""MRL-15 prospective candidate-frame review (source-only, static).

Starts from the 396 mechanically screened MBPP IDs, applies fixed source-only
exclusions (prior-seen roots, near-duplicate / provisional-family screen), orders
the remaining frame by a fixed seeded hash and reviews the first 20 records
statically. Nothing is executed: reference code is only parsed with ast.parse /
compile(); no model, receiver, sandbox or subprocess is used.

Committed records contain the public MBPP task text but only sha256 digests of
reference code and test assertions.

Reproduce:
  python3 scripts/review_candidate_frame_mrl15.py --out-dir results/frame_review_mrl15_<UTC>
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import keyword
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MBPP_PATH = Path(__file__).resolve().parents[1] / "work/sources/mbpp_full.jsonl"  # durable, gitignored raw data; sha-pinned
MBPP_SHA256 = "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"
SCREEN_DIR = ROOT / "results/pool_screen_20260921T131231Z"
PRIOR_CONFIG = ROOT / "experiments/landmark/dev_release_v1c/config.json"
E11_DEV_ROOTS = [52, 357, 373, 378, 402, 489, 509]
SEED = "mrl15-frame-seed-20260922"
N_REVIEW = 20
# Fixed BEFORE computing any similarity (pre-registered in the manifest).
SIM_THRESHOLD = 0.5
SENSITIVITY_THRESHOLDS = (0.4, 0.6, 0.7)  # reported only; never used to select roots
SIM_RULE = ("score = max(Jaccard(text tokens), Jaccard(code identifier tokens)); "
            "tokens = lowercase [a-z0-9_]+ ; code tokens exclude Python keywords and "
            "builtins-free list below; pairs with score >= threshold are near-duplicates")
CODE_STOP = set(keyword.kwlist) | {
    "self", "range", "len", "int", "str", "list", "dict", "set", "tuple", "print",
    "i", "j", "k", "x", "n", "0", "1", "2", "res", "result", "return",
}
TEXT_STOP = {"write", "a", "the", "to", "function", "python", "of", "given", "in",
             "and", "for", "from", "is", "an", "by", "using", "find", "check",
             "whether", "or", "with", "be", "that"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def seed_key(task_id: int) -> str:
    return sha256_text(f"{SEED}:{task_id}")


def load_mbpp() -> dict[int, dict]:
    raw = MBPP_PATH.read_bytes()
    got = sha256_bytes(raw)
    if got != MBPP_SHA256:
        raise SystemExit(f"MBPP sha256 mismatch: {got}")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return {int(r["task_id"]): r for r in rows}


def verify_screen() -> tuple[list[int], dict]:
    usable = json.loads((SCREEN_DIR / "usable_ids.json").read_text())
    summary = json.loads((SCREEN_DIR / "summary.json").read_text())
    per = json.loads((SCREEN_DIR / "per_candidate.json").read_text())
    gate = {int(r["task_id"]): r["gate"] for r in per}
    problems = []
    if len(usable) != summary["usable_upper_bound"]:
        problems.append("usable count != summary.usable_upper_bound")
    if len(set(usable)) != len(usable):
        problems.append("duplicate usable ids")
    not_usable = [t for t in usable if gate.get(int(t)) != "USABLE"]
    if not_usable:
        problems.append(f"ids not USABLE in per_candidate: {not_usable[:10]}")
    n_usable_pc = sum(1 for g in gate.values() if g == "USABLE")
    if n_usable_pc != len(usable):
        problems.append("per_candidate USABLE count differs from usable_ids")
    if problems:
        raise SystemExit("screen verification failed: " + "; ".join(problems))
    info = {"usable_ids": len(usable), "summary": summary,
            "per_candidate_usable": n_usable_pc,
            "all_marked_usable": True,
            "usable_ids_sha256": sha256_bytes((SCREEN_DIR / "usable_ids.json").read_bytes())}
    return sorted(int(t) for t in usable), info


def map_prior_seen() -> tuple[set[int], dict]:
    cfg = json.loads(PRIOR_CONFIG.read_text())
    ids = cfg["prior_seen_root_ids"]
    mapped, unmapped_non_mbpp, malformed = set(), [], []
    for s in ids:
        m = re.fullmatch(r"mbpp/(\d+)", str(s))
        if m:
            mapped.add(int(m.group(1)))
        elif str(s).startswith("humaneval/"):
            unmapped_non_mbpp.append(s)
        else:
            malformed.append(s)
    info = {"config_sha256": sha256_bytes(PRIOR_CONFIG.read_bytes()),
            "n_prior_seen_ids": len(ids), "n_mapped_mbpp": len(mapped),
            "n_humaneval_not_mbpp": len(unmapped_non_mbpp),
            "unmappable_other": malformed,
            "note": "humaneval/* ids are a different benchmark and cannot map to MBPP "
                    "task_ids; no HumanEval source is pinned, so they are not "
                    "similarity-screened (limitation)."}
    return mapped, info


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


def entry_point(code: str) -> tuple[str | None, int | None, dict]:
    tree = ast.parse(code)
    compile(code, "<reference>", "exec", dont_inherit=True)  # static compilation only; never executed; no inherited __future__ flags
    defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    other = [type(n).__name__ for n in tree.body
             if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not defs:
        return None, None, {"module_level_other": other}
    f = defs[-1]
    a = f.args
    arity = len(a.posonlyargs) + len(a.args)
    return f.name, arity, {"module_level_other": other, "n_defaults": len(a.defaults),
                           "varargs": a.vararg is not None or a.kwarg is not None,
                           "n_top_level_defs": len(defs)}


def test_features(tests: list[str], ep: str) -> dict:
    called_names, call_arities, feats = set(), set(), set()
    for t in tests:
        try:
            node = ast.parse(t).body[0]
        except SyntaxError:
            feats.add("unparseable_assertion")
            continue
        if not isinstance(node, ast.Assert):
            feats.add("non_assert_statement")
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)):
            feats.add("not_simple_equality")
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                called_names.add(sub.func.id)
                if sub.func.id == ep:
                    call_arities.add(len(sub.args) + len(sub.keywords))
            if isinstance(sub, ast.Constant) and isinstance(sub.value, float):
                feats.add("float_literal")
            if isinstance(sub, (ast.Set, ast.Dict, ast.SetComp, ast.DictComp)):
                feats.add("set_or_dict_literal")
        if isinstance(test, ast.Compare):
            lhs = test.left
            if not (isinstance(lhs, ast.Call) and isinstance(lhs.func, ast.Name)
                    and lhs.func.id == ep):
                feats.add("lhs_not_direct_entry_call")
            rhs = test.comparators[0] if test.comparators else None
            if isinstance(rhs, ast.Constant) and isinstance(rhs.value, str):
                feats.add("string_expected")
    extra = sorted(called_names - {ep})
    return {"called_names_other": extra, "call_arities": sorted(call_arities),
            "features": sorted(feats), "entry_called": ep in called_names}


def spec_review(row: dict, ep: str, arity: int, ep_info: dict) -> dict:
    tf = test_features(row["test_list"], ep)
    text = row["text"].lower()
    flags = []
    if ep and ep.lower() not in text and ep.replace("_", " ").lower() not in text:
        flags.append(("function_name_unstated",
                      "task text does not name the entry point; tests call it by name"))
    if not tf["entry_called"]:
        flags.append(("entry_not_called", "tests never call the reference entry point"))
    if tf["call_arities"] and any(a != arity for a in tf["call_arities"]):
        flags.append(("arity_mismatch",
                      f"tests call with {tf['call_arities']} args; def has {arity}"))
    if tf["called_names_other"]:
        flags.append(("extra_constructs_in_tests",
                      f"tests call other names {tf['called_names_other']}"))
    if "float_literal" in tf["features"]:
        flags.append(("float_formatting",
                      "expected values contain float literals compared by equality"))
    if "set_or_dict_literal" in tf["features"]:
        flags.append(("ordering_or_container_convention",
                      "tests compare set/dict literals; container type/order unstated"))
    if "not_simple_equality" in tf["features"] or "lhs_not_direct_entry_call" in tf["features"]:
        flags.append(("nonstandard_assertion_shape",
                      "assertion is not `entry(...) == expected`"))
    if "string_expected" in tf["features"] and re.search(r"match|found|yes|no", " ".join(row["test_list"]).lower()):
        flags.append(("unstated_output_string",
                      "expected output is a literal message string not given in text"))
    if ep_info.get("module_level_other"):
        flags.append(("module_level_state",
                      f"reference has module-level {ep_info['module_level_other']}"))
    if ep_info.get("n_top_level_defs", 1) > 1:
        flags.append(("helper_functions", "reference defines helper functions"))
    if len(row["test_list"]) < 3:
        flags.append(("few_tests", f"only {len(row['test_list'])} official tests"))
    names = {f for f, _ in flags}
    serious = names & {"entry_not_called", "arity_mismatch"}
    moderate = names & {"float_formatting", "ordering_or_container_convention",
                        "unstated_output_string", "nonstandard_assertion_shape",
                        "extra_constructs_in_tests", "module_level_state"}
    if serious:
        decision, unc = "exclude", "low"
    elif len(moderate) >= 2:
        decision, unc = "hold", "medium"
    elif moderate:
        decision, unc = "hold", "high"
    else:
        decision, unc = "include", "medium" if "function_name_unstated" in names else "low"
    return {"flags": [{"flag": f, "reason": r} for f, r in flags],
            "decision": decision, "uncertainty": unc,
            "note": "static heuristic review from source only; the function-name "
                    "convention is universal in MBPP and is supplied to the model by "
                    "the harness interface, so alone it does not block inclusion"}


class UF:
    def __init__(self, items):
        self.p = {i: i for i in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            lo, hi = min(ra, rb), max(ra, rb)
            self.p[hi] = lo


def build() -> tuple[dict, list]:
    mbpp = load_mbpp()
    frame, screen_info = verify_screen()
    prior_mbpp, prior_info = map_prior_seen()
    missing = [t for t in frame if t not in mbpp]
    if missing:
        raise SystemExit(f"frame ids missing from MBPP source: {missing}")
    prior_all = set(prior_mbpp) | set(E11_DEV_ROOTS)
    prior_in_source = sorted(t for t in prior_all if t in mbpp)
    counts = {"start_frame": len(frame)}
    excluded = {}

    # Step (i): prior-seen roots.
    step1 = []
    for t in frame:
        if t in prior_all:
            src = []
            if t in prior_mbpp:
                src.append("dev_release_v1c.prior_seen_root_ids")
            if t in E11_DEV_ROOTS:
                src.append("E11/dev inspected root")
            excluded[t] = {"step": "i_prior_seen", "reason": " + ".join(src)}
        else:
            step1.append(t)
    counts["after_i_prior_seen"] = len(step1)

    feats = {t: (text_tokens(mbpp[t]["text"]), code_tokens(mbpp[t]["code"]))
             for t in set(frame) | set(prior_in_source)}

    # Step (ii-a): near-duplicate of any prior-seen root.
    nearest_prior = {}
    for t in frame:
        best = (-1.0, None)
        for p in prior_in_source:
            if p == t:
                continue
            s = sim(feats[t], feats[p])
            if s > best[0] or (s == best[0] and p < (best[1] or 10**9)):
                best = (s, p)
        nearest_prior[t] = {"task_id": best[1], "score": best[0]}
    step2 = []
    for t in step1:
        if nearest_prior[t]["score"] >= SIM_THRESHOLD:
            excluded[t] = {"step": "ii_near_duplicate_of_prior_seen",
                           "reason": f"score {nearest_prior[t]['score']} >= {SIM_THRESHOLD} "
                                     f"vs prior-seen mbpp/{nearest_prior[t]['task_id']}"}
        else:
            step2.append(t)
    counts["after_ii_prior_seen_near_duplicate"] = len(step2)

    # Step (ii-b): within-frame provisional families (union-find), keep one per family.
    uf = UF(step2)
    nearest_frame = {}
    for a in step2:
        best = (-1.0, None)
        for b in step2:
            if a == b:
                continue
            s = sim(feats[a], feats[b])
            if s > best[0] or (s == best[0] and b < (best[1] or 10**9)):
                best = (s, b)
            if s >= SIM_THRESHOLD and a < b:
                uf.union(a, b)
        nearest_frame[a] = {"task_id": best[1], "score": best[0]}
    fams: dict[int, list[int]] = {}
    for t in step2:
        fams.setdefault(uf.find(t), []).append(t)
    fam_label = {}
    for root, members in fams.items():
        for m in members:
            fam_label[m] = f"PF-{min(members)}" if len(members) > 1 else f"PF-{m}"
    step3 = []
    for root, members in sorted(fams.items()):
        keep = min(members, key=seed_key)
        step3.append(keep)
        for m in members:
            if m != keep:
                excluded[m] = {"step": "ii_within_frame_family",
                               "reason": f"provisional family {fam_label[m]}; kept "
                                         f"{keep} (smallest seeded hash)"}
    counts["after_ii_within_frame_family"] = len(step3)
    counts["n_multi_member_families"] = sum(1 for m in fams.values() if len(m) > 1)
    # Frame-size uncertainty under pre-declared alternative thresholds (source-only; selection unchanged).
    sens = {}
    for th in SENSITIVITY_THRESHOLDS:
        s2 = [t for t in step1 if nearest_prior[t]["score"] < th]
        u = UF(s2)
        for i, a in enumerate(s2):
            for b in s2[i + 1:]:
                if sim(feats[a], feats[b]) >= th:
                    u.union(a, b)
        sens[str(th)] = {"after_ii_prior_seen_near_duplicate": len(s2),
                         "after_ii_within_frame_family": len({u.find(t) for t in s2})}
    counts["threshold_sensitivity_reported_not_used"] = sens

    ordered = sorted(step3, key=lambda t: (seed_key(t), t))
    review_ids = ordered[:N_REVIEW]

    records = []
    for rank, t in enumerate(review_ids, 1):
        row = mbpp[t]
        ep, arity, ep_info = entry_point(row["code"])
        records.append({
            "rank": rank, "task_id": t, "seed_hash": seed_key(t),
            "text": row["text"], "text_sha256": sha256_text(row["text"]),
            "reference_code_sha256": sha256_text(row["code"]),
            "test_list_sha256": sha256_text(json.dumps(row["test_list"])),
            "entry_point": ep, "arity": arity,
            "n_official_tests": len(row["test_list"]),
            "n_challenge_tests": len(row.get("challenge_test_list") or []),
            "provisional_family": fam_label[t],
            "family_size_in_frame": len(fams[uf.find(t)]),
            "nearest_prior_seen": nearest_prior[t],
            "nearest_in_frame": nearest_frame[t],
            "spec_review": spec_review(row, ep, arity, ep_info),
        })

    manifest = {
        "task": "MRL-15 prospective candidate-frame review (lead ruling 3)",
        "status": "preparation only; not collection authorization; not a family-"
                  "independence certificate",
        "source": {"mbpp_path": str(MBPP_PATH), "mbpp_sha256": MBPP_SHA256,
                   "mbpp_rows": len(mbpp), "screen_dir": str(SCREEN_DIR.relative_to(ROOT)),
                   "screen_verification": screen_info, "prior_seen": prior_info,
                   "e11_dev_roots": E11_DEV_ROOTS},
        "preregistered": {"seed": SEED, "order_key": f'sha256(f"{SEED}:{{task_id}}")',
                          "n_review": N_REVIEW, "similarity_threshold": SIM_THRESHOLD,
                          "similarity_rule": SIM_RULE,
                          "family_rule": "union-find over within-frame pairs with score >= "
                                         "threshold; keep member with smallest seeded hash",
                          "outcome_information_used": "none"},
        "counts": counts,
        "prior_seen_mbpp_in_source": len(prior_in_source),
        "excluded": {str(k): v for k, v in sorted(excluded.items())},
        "eligible_ordered_ids": ordered,
        "review_ids": review_ids,
        "decision_counts": {d: sum(1 for r in records if r["spec_review"]["decision"] == d)
                            for d in ("include", "hold", "exclude")},
        "execution": {"exec_eval_subprocess": False, "model_calls": 0,
                      "static_ops": ["ast.parse", "compile"]},
        "reproduce": "python3 scripts/review_candidate_frame_mrl15.py --out-dir "
                     "results/frame_review_mrl15_<UTC>",
    }
    return manifest, records


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    manifest, records = build()
    out = Path(args.out_dir)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    rec_bytes = json.dumps(records, indent=1, sort_keys=True).encode()
    manifest["records_sha256"] = sha256_bytes(rec_bytes)
    (out / "records.json").write_bytes(rec_bytes)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(json.dumps({"counts": manifest["counts"], "decisions": manifest["decision_counts"],
                      "review_ids": manifest["review_ids"],
                      "records_sha256": manifest["records_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
