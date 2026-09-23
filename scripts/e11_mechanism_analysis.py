#!/usr/bin/env python3
"""POST-HOC exploratory mechanism analysis of the immutable E11 outputs (not prespecified; descriptive only).

Static only: grade.extract_code + ast.parse on saved receiver outputs. Nothing is executed; no receiver request.
Per continuation it compares the ordered AST list of ALL top-level FunctionDef nodes, not semantic
equivalence or the task function alone. Helper/duplicate definitions can change this fingerprint; imports
are omitted. Unextractable/unparseable/missing outputs or an absent function list are unassessable, not
changed. Known token sums and unknown-token counts are reported separately.
"""
from __future__ import annotations
import argparse, ast, collections, hashlib, inspect, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark.grade import extract_code  # noqa: E402

EMPTY_FUNCTIONS = ast.dump(ast.Module(body=[], type_ignores=[]))
METRIC_DEFINITIONS = {
    "identity": "Ordered top-level FunctionDef AST identity; not semantic equivalence or task-function rewrite. Imports are omitted; helpers and duplicate definitions are included.",
    "same_function_as_initial": "Legacy name: per-row True/False/None for assessable same/changed/unassessable; per-arm count is an alias of assessable_same, not its denominator.",
    "partition": "n = assessable_same + assessable_changed + unassessable; both outputs need extractable, parseable, nonempty top-level FunctionDef lists.",
    "completion_tokens_known_sum": "Sum of recorded nonnegative integer token counts only; unknown counts do not contribute and are not assumed zero.",
    "completion_tokens_unknown_count": "Number of continuation records with completion_tokens absent or None.",
    "extra_toplevel_code": "Static presence of non-FunctionDef/non-import nodes, not evidence of reliable self-validation; ast.parse is not a compile-validity check.",
}


def norm(text):
    if text is None:
        return None, "output_missing"
    try:
        code = extract_code(text)
    except Exception:
        return None, "extract_fail"
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, TypeError):
        return None, "parse_fail"
    except (MemoryError, RecursionError):
        return None, "parse_unavailable"
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    extra = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.Import, ast.ImportFrom))]
    return ast.dump(ast.Module(body=fns, type_ignores=[])), ("extra_toplevel" if extra else "clean")


def analyze_records(initial_rows, continuation_rows, grades):
    init = {r["root_id"]: norm(r.get("output")) for r in initial_rows}
    per_arm, detail = {}, []
    for c in continuation_rows:
        output = c.get("output")
        fn, fmt = norm(output)
        initial_fn, initial_fmt = init.get(c["root_id"], (None, "missing_initial_record"))
        assessable = fn not in (None, EMPTY_FUNCTIONS) and initial_fn not in (None, EMPTY_FUNCTIONS)
        same = fn == initial_fn if assessable else None
        fences = output.count("```") if isinstance(output, str) else None
        tokens = c.get("completion_tokens")
        if tokens is not None and (type(tokens) is not int or tokens < 0):
            raise ValueError("completion_tokens must be a nonnegative integer or None")
        k = per_arm.setdefault(c["arm"], dict.fromkeys(("n", "same_function_as_initial", "assessable_same",
            "assessable_changed", "unassessable", "extra_toplevel_code", "extract_or_parse_fail",
            "completion_tokens_known_sum", "completion_tokens_unknown_count"), 0))
        k["n"] += 1
        k["same_function_as_initial"] += same is True
        k["assessable_same"] += same is True
        k["assessable_changed"] += same is False
        k["unassessable"] += same is None
        k["extra_toplevel_code"] += fmt == "extra_toplevel"
        k["extract_or_parse_fail"] += fmt in ("extract_fail", "parse_fail")
        if tokens is None:
            k["completion_tokens_unknown_count"] += 1
        else:
            k["completion_tokens_known_sum"] += tokens
        detail.append({"root_id": c["root_id"], "arm": c["arm"], "replicate": c["replicate"],
                       "same_function_as_initial": same, "initial_format": initial_fmt,
                       "format": fmt, "fence_markers": fences, "completion_tokens": tokens,
                       "grade": grades.get((c["root_id"], c["arm"], c["replicate"]))})
    return {"initial_formats": dict(collections.Counter(v[1] for v in init.values())),
            "per_arm": dict(sorted(per_arm.items())), "detail": detail}


def source_provenance():
    module = Path(inspect.getsourcefile(extract_code)).resolve()
    script = Path(__file__).resolve()
    return {"script": {"path": str(script.relative_to(ROOT)), "sha256": hashlib.sha256(script.read_bytes()).hexdigest()},
            "extract_code": {"qualified_name": f"{extract_code.__module__}.{extract_code.__name__}",
                             "module_path": str(module.relative_to(ROOT)),
                             "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, default=ROOT / "results/e11_dev_v2_20260922T010959Z")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    A = [json.loads(l) for l in open(a.run / "A/calls.jsonl")]
    C = [json.loads(l) for l in open(a.run / "C/calls.jsonl")]
    G = {(g["root_id"], g["arm"], g["replicate"]): g.get("outcome") for g in map(json.loads, open(a.run / "D/grades.jsonl"))}
    n_roots = len({r["root_id"] for r in A if r.get("root_id")})
    out = {"analysis_version": "mechanism-static-v3-tristate-run-labelled",
           "run": a.run.name,
           # MRL-18: the label is derived from the run actually analysed. The v2 label was hard-coded to E11 and
           # 7 roots, which mislabelled the E12 report (lead be417b5); it is annotated, not rewritten, in place.
           "evidence_class": (f"post-hoc exploratory static analysis of immutable outputs of run {a.run.name}; "
                              f"NOT a prespecified endpoint; {n_roots} roots"),
           "inputs": {p: hashlib.sha256((a.run / p).read_bytes()).hexdigest() for p in ("A/calls.jsonl", "C/calls.jsonl", "D/grades.jsonl")},
           "provenance": source_provenance(), "metric_definitions": METRIC_DEFINITIONS,
           **analyze_records(A, C, G)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["per_arm"], indent=1))


if __name__ == "__main__":
    main()
