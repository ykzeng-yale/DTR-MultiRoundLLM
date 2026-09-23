#!/usr/bin/env python3
"""Source-only validation that terminal-output-contract-v1 is checkable by the FROZEN instrument, unchanged.

Evidence class: static measurement-contract validation. Zero executions: no receiver, no candidate, no
reference, no containment, no sandbox. The only operations are the frozen extractor (grade.extract_code),
ast.parse and hashing.

The corrected E14 proposal requires a validation pass for terminal-output-contract-v1 before any primary
collection. This script does the half that needs no execution: it shows, clause by clause, whether the existing
extractor plus a static AST check can decide compliance WITHOUT altering the scorer. The remaining half -- that
a compliant output still reaches the private suite and scores as before -- requires a released containment run
and is explicitly NOT claimed here.

It also reports how E13a's 60 already-saved outputs stand against these clauses. That is descriptive only. Those
outputs were produced under prompts that carried NO contract, so their compliance rate does not predict
behaviour under the contract, does not repair E13a's -0.1000, and identifies no formatting mechanism.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark.grade import extract_code  # noqa: E402
from experiments.landmark.diagnostic import DIAGNOSTIC_HEADER  # noqa: E402

PROPOSAL = ROOT / "docs/e14_same_prefix_revision_proposal_20260923.md"
E13A = ROOT / "results/e13a_two_arm_20260923T061500Z"
CONTRACT_LABEL = "terminal-output-contract-v1"

CLAUSES = {
    "fenced_block_present": "CONTRACT CLAUSE, **NOT ENFORCEABLE BY THE FROZEN INSTRUMENT**: the contract asks for "
                            "a triple-backtick block, but grade.extract_code returns the whole text when no fence "
                            "is present, so a completely unfenced answer is accepted and scored normally. Only "
                            "the weaker 'not ambiguously fenced' is decided by the instrument. Making the fence "
                            "itself a requirement would need a scorer change, which is not requested.",
    "not_ambiguously_fenced": "what grade.extract_code actually decides: with any '```' present, exactly one block "
                              "and exactly two markers, else ValueError. No scorer change needed.",
    "parses_as_python": "ast.parse accepts the extracted text. Static; no execution.",
    "only_function_and_imports": "every top-level node is FunctionDef/AsyncFunctionDef/Import/ImportFrom. "
                                 "Static AST check; no scorer change needed.",
    "no_test_calls_or_asserts": "no top-level Expr/Call and no Assert anywhere. Static AST check.",
    "no_diagnostic_text_copied": "the diagnostic header string does not appear in the output text.",
}
ENFORCEABILITY_FINDING = (
    "The contract's fence clause is NOT enforceable by the frozen instrument. grade.extract_code returns the "
    "whole text when no '```' appears, so an unfenced answer is extracted, parsed and scored exactly as a fenced "
    "one. The instrument can only reject AMBIGUOUS fencing. Consequence for the design: compliance with the "
    "fence clause is unobservable in the endpoint, so the contract must either be reworded to match what the "
    "instrument decides, or the fence must be dropped from the asserted requirements. Changing the scorer to "
    "enforce it is a different measurement and is not requested.")
NOT_VALIDATED_HERE = [
    "That a compliant output still reaches the private suite and scores as it did before: that needs a released "
    "containment run with reference and negative-control rechecks, and is not claimed by this script.",
    "That instructing the contract changes what the receiver emits: unmeasurable without a receiver call.",
    "That any share of E13a's -0.1000 was caused by formatting: explicitly not claimed.",
]


def check(text):
    """Clause-by-clause static verdict for one output text."""
    out = {"fenced_block_present": None, "not_ambiguously_fenced": None, "parses_as_python": False,
           "only_function_and_imports": False, "no_test_calls_or_asserts": False,
           "no_diagnostic_text_copied": None, "extractor_error": None}
    if not isinstance(text, str):
        out["extractor_error"] = "output_missing"
        return out
    out["fenced_block_present"] = "```" in text
    out["no_diagnostic_text_copied"] = DIAGNOSTIC_HEADER not in text
    try:
        code = extract_code(text)
        out["not_ambiguously_fenced"] = True
    except ValueError as exc:
        out["not_ambiguously_fenced"] = False
        out["extractor_error"] = str(exc)
        return out
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, TypeError):
        out["extractor_error"] = "ast_parse_failed"
        return out
    out["parses_as_python"] = True
    allowed = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Import, ast.ImportFrom)
    out["only_function_and_imports"] = all(isinstance(n, allowed) for n in tree.body)
    has_call_stmt = any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) for n in tree.body)
    out["no_test_calls_or_asserts"] = not has_call_stmt and not any(
        isinstance(n, ast.Assert) for n in ast.walk(tree))
    return out


def contract_compliant(v):
    """Every contract clause, including the fence the frozen instrument cannot enforce."""
    return bool(v["fenced_block_present"] and v["not_ambiguously_fenced"] and v["parses_as_python"]
                and v["only_function_and_imports"] and v["no_test_calls_or_asserts"]
                and v["no_diagnostic_text_copied"])


def instrument_scoreable(v):
    """What the FROZEN instrument decides: an output it can extract and parse. The fence clause is absent."""
    return bool(v["not_ambiguously_fenced"] and v["parses_as_python"])


compliant = contract_compliant


FIXTURES = {
    "compliant_minimal": ("```python\ndef f(x):\n    return x\n```", True),
    "compliant_with_import": ("```python\nimport math\n\n\ndef f(x):\n    return math.sqrt(x)\n```", True),
    "two_blocks": ("```python\ndef f(x):\n    return x\n```\n```python\nprint(f(1))\n```", False),
    "unfenced": ("def f(x):\n    return x", False),
    "prose_then_fence": ("Here is my answer:\n```python\ndef f(x):\n    return x\n```", True),
    "test_call_inside": ("```python\ndef f(x):\n    return x\n\n\nprint(f(1))\n```", False),
    "assert_inside": ("```python\ndef f(x):\n    return x\n\n\nassert f(1) == 1\n```", False),
    "unparseable": ("```python\ndef f(x)\n    return x\n```", False),
    "diagnostic_echo": (f"```python\n# {DIAGNOSTIC_HEADER}\ndef f(x):\n    return x\n```", False),
    "empty_module": ("```python\n```", True),
}


def build():
    contract_text = None
    for line in PROPOSAL.read_text().splitlines():
        if line.strip().startswith("> `Return the complete solution"):
            contract_text = line.strip()[3:-1]
            break
    if not contract_text:
        raise SystemExit("contract text not found in the proposal; refusing to invent it")

    fixtures = {}
    for name, (text, expected) in FIXTURES.items():
        v = check(text)
        fixtures[name] = {"expected_contract_compliant": expected,
                          "observed_contract_compliant": contract_compliant(v),
                          "observed_instrument_scoreable": instrument_scoreable(v), "clauses": v,
                          "agrees": contract_compliant(v) == expected}

    calls = [json.loads(l) for l in (E13A / "collect/calls.jsonl").read_text().splitlines() if l.strip()]
    per_arm, per_clause = {}, {}
    for c in calls:
        arm = c["arm"]
        v = check(c.get("output"))
        a = per_arm.setdefault(arm, {"outputs": 0, "contract_compliant": 0, "instrument_scoreable": 0})
        a["outputs"] += 1
        a["contract_compliant"] += int(contract_compliant(v))
        a["instrument_scoreable"] += int(instrument_scoreable(v))
        for k, val in v.items():
            if k == "extractor_error":
                continue
            per_clause.setdefault(arm, {}).setdefault(k, {"true": 0, "false": 0})
            per_clause[arm][k]["true" if val else "false"] += 1

    return {
        "validation_version": "e14-output-contract-validation-v1",
        "evidence_class": ("static measurement-contract validation; 0 executions; the private-suite half is NOT "
                           "validated here and needs a released containment run"),
        "contract": {"label": CONTRACT_LABEL, "text": contract_text,
                     "sha256": hashlib.sha256(contract_text.encode()).hexdigest(),
                     "source": "docs/e14_same_prefix_revision_proposal_20260923.md section 2"},
        "instrument": {"extractor": "experiments.landmark.grade.extract_code",
                       "extractor_rule": "with any '```' present, exactly one block and exactly two markers, else "
                                         "ValueError; otherwise the whole text",
                       "scorer_changed": False,
                       "grade_module_sha256": hashlib.sha256((ROOT / "experiments/landmark/grade.py").read_bytes()).hexdigest()},
        "clauses": CLAUSES,
        "enforceability_finding": ENFORCEABILITY_FINDING,
        "not_validated_here": NOT_VALIDATED_HERE,
        "fixtures": fixtures,
        "all_fixtures_agree": all(f["agrees"] for f in fixtures.values()),
        "e13a_saved_outputs_descriptive": {
            "note": ("Descriptive only. These outputs were produced under prompts carrying NO contract, so this "
                     "compliance rate does not predict behaviour under the contract, does not repair E13a's "
                     "-0.1000 and identifies no formatting mechanism."),
            "per_arm": per_arm, "per_clause": per_clause,
            "inputs": {"collect/calls.jsonl": hashlib.sha256((E13A / "collect/calls.jsonl").read_bytes()).hexdigest()},
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    rec = build()
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"all_fixtures_agree": rec["all_fixtures_agree"],
                      "per_arm": rec["e13a_saved_outputs_descriptive"]["per_arm"]}, indent=1))


if __name__ == "__main__":
    main()
