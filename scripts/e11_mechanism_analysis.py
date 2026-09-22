#!/usr/bin/env python3
"""POST-HOC exploratory mechanism analysis of the immutable E11 outputs (not prespecified; descriptive only).

Static only: grade.extract_code + ast.parse on saved receiver outputs. Nothing is executed; no receiver request.
Per continuation it records whether the extracted top-level function(s) are AST-identical to the root's initial
answer, whether extra top-level (non-def/import) code was added, fence count, tokens and the recorded grade.
"""
from __future__ import annotations
import argparse, ast, collections, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark.grade import extract_code  # noqa: E402


def norm(text):
    try:
        code = extract_code(text)
    except Exception:
        return None, "extract_fail"
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None, "parse_fail"
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    extra = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.Import, ast.ImportFrom))]
    return ast.dump(ast.Module(body=fns, type_ignores=[])), ("extra_toplevel" if extra else "clean")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, default=ROOT / "results/e11_dev_v2_20260922T010959Z")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    A = {json.loads(l)["root_id"]: json.loads(l) for l in open(a.run / "A/calls.jsonl")}
    C = [json.loads(l) for l in open(a.run / "C/calls.jsonl")]
    G = {(g["root_id"], g["arm"], g["replicate"]): g.get("outcome") for g in map(json.loads, open(a.run / "D/grades.jsonl"))}
    init = {r: norm(A[r]["output"]) for r in A}
    per_arm, detail = collections.defaultdict(collections.Counter), []
    for c in C:
        fn, fmt = norm(c["output"])
        same = fn is not None and fn == init[c["root_id"]][0]
        fences = c["output"].count("```")
        k = per_arm[c["arm"]]
        k["n"] += 1; k["same_function_as_initial"] += same; k["extra_toplevel_code"] += fmt == "extra_toplevel"
        k["extract_or_parse_fail"] += fmt in ("extract_fail", "parse_fail"); k["completion_tokens"] += c["completion_tokens"] or 0
        detail.append({"root_id": c["root_id"], "arm": c["arm"], "replicate": c["replicate"], "same_function_as_initial": same,
                       "format": fmt, "fence_markers": fences, "completion_tokens": c["completion_tokens"],
                       "grade": G.get((c["root_id"], c["arm"], c["replicate"]))})
    out = {"evidence_class": "post-hoc exploratory static analysis of immutable E11 outputs; NOT a prespecified endpoint; 7 reused roots",
           "inputs": {p: hashlib.sha256((a.run / p).read_bytes()).hexdigest() for p in ("A/calls.jsonl", "C/calls.jsonl", "D/grades.jsonl")},
           "initial_formats": dict(collections.Counter(v[1] for v in init.values())),
           "per_arm": {k: dict(v) for k, v in sorted(per_arm.items())}, "detail": detail}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["per_arm"], indent=1))


if __name__ == "__main__":
    main()
