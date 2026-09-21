#!/usr/bin/env python3
"""Mechanical-gate screen of the fresh candidate pool: an UPPER BOUND on usable roots.

Rules committed before this runs (docs/pool_screen_contract.md). Per candidate, in order:
  G1 provenance   row comes from the pinned full MBPP source (SHA-256 verified before any row is read)
  G2 interface    the reference is exactly one plain function (no decorators, defaults, *args, **kwargs,
                  annotations) -- the builder's own interface rule
  G3 no setup     empty test_setup_code and challenge_test_list -- the builder's own rule
  G4 integrity    the reference passes the static hack gate
  G5 reference    the reference passes ALL of its own original assertions in the attested landmark sandbox,
                  through grade.evaluate (integrity canary and sentinel included)
  G6 discriminates a do-nothing stub with the same interface FAILS those assertions
A candidate passing G1-G6 is mechanically usable. That is necessary, not sufficient: prior-family and
specification review, authored boundary cases and frozen controls still decide real eligibility, so this
count bounds the confirmatory study from above. No model is called.
"""
from __future__ import annotations

import argparse, ast, hashlib, json, sys, time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import grade, sandbox  # noqa: E402
from experiments.common.integrity import hack_gate  # noqa: E402

SOURCE_SHA = "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"


def interface(code):
    tree = ast.parse(code)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(tree.body) != 1 or len(fns) != 1:
        return None, "not_single_function"
    fn, a = fns[0], fns[0].args
    if a.posonlyargs or a.kwonlyargs or a.defaults or a.kwarg or a.vararg or fn.decorator_list or fn.returns \
       or any(x.annotation for x in a.args):
        return None, "nonplain_signature"
    return fn, None


def screen(row):
    code = row["code"]
    try:
        fn, why = interface(code)
    except SyntaxError:
        return "G2_interface", "reference_does_not_parse"
    if fn is None:
        return "G2_interface", why
    if row["test_setup_code"].strip() or row["challenge_test_list"]:
        return "G3_setup", "setup_or_challenge_tests_present"
    if hack_gate(code, fn.name):
        return "G4_integrity", "reference_static_flag"
    spec = {"entry_point": fn.name, "private_assertions": list(row["test_list"]), "preamble": []}
    ref = grade.evaluate(spec, code, sandbox.run_program)
    if ref["outcome"] != 1:
        return "G5_reference", ref["reason"]
    stub = f"def {fn.name}({', '.join(x.arg for x in fn.args.args)}):\n    return None\n"
    st = grade.evaluate(spec, stub, sandbox.run_program)
    if st["outcome"] != 0:
        return "G6_discrimination", "do_nothing_stub_passes" if st["outcome"] == 1 else st["reason"]
    return "USABLE", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--attestation", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if hashlib.sha256(a.source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise SystemExit("G1: pinned source bytes do not match")
    grade.verify_attestation(a.attestation)
    rows = {json.loads(l)["task_id"]: json.loads(l) for l in a.source.read_text().splitlines()}
    ids = json.loads(a.candidates.read_text())["after_prior_prompt_duplicate_exclusion_ids"]
    t0, results = time.monotonic(), []
    for tid in ids:
        gate, why = screen(rows[int(tid)])
        results.append({"task_id": int(tid), "gate": gate, "reason": why})
    a.out.mkdir(parents=True, exist_ok=False)
    usable = [r["task_id"] for r in results if r["gate"] == "USABLE"]
    summary = {"candidates": len(ids), "usable_upper_bound": len(usable),
               "first_failing_gate": dict(Counter(r["gate"] for r in results)),
               "reasons": dict(Counter(f'{r["gate"]}:{r["reason"]}' for r in results if r["reason"])),
               "wall_seconds": round(time.monotonic() - t0, 1), "model_calls": 0}
    (a.out / "per_candidate.json").write_text(json.dumps(results, indent=1))
    (a.out / "usable_ids.json").write_text(json.dumps(usable))
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
