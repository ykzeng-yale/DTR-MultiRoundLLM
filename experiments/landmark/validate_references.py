#!/usr/bin/env python3
"""Isolated reference and negative-control validation of the v2 development contracts.

Executes, inside the attested landmark sandbox, exactly:
  * each root's ORIGINAL benchmark reference against its full v2 private suite;
  * for MBPP 402, additionally the REPAIRED reference (reference-repair-v1);
  * every frozen negative control.

Expected outcomes are pre-registered in docs/landmark_reference_validation_contract.md and committed
BEFORE this is run. The clearing rule is the grading-validation rule already in the repo: a root clears
only if its positive reference passes (outcome 1) AND every negative control actually executes and
fails (outcome 0). A parse rejection, an environment failure or a timeout-before-payload never stands in
for a demonstrated failure. Nothing here changes a spec after seeing an outcome.

Refuses to run without a passing containment attestation from the last 24 hours bound to this host,
interpreter, runner, profile and checker (grade.verify_attestation). No model is called.
"""
from __future__ import annotations

import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.landmark import grade, sandbox  # noqa: E402

REPAIRED_402_SUFFIX = "return C[r] % p"


def repaired_402(original: str) -> str:
    """Apply reference-repair-v1 exactly: append ' % p' to the return expression, nothing else."""
    if original.count("return C[r]") != 1:
        raise ValueError("402 reference does not have the single expected return statement")
    fixed = original.replace("return C[r]", REPAIRED_402_SUFFIX, 1)
    if len(fixed) != len(original) + len(" % p"):
        raise ValueError("repair is not the four-character change")
    return fixed


def expected(root_id: str, kind: str) -> int:
    if kind == "control":
        return 0
    if root_id == "mbpp/402" and kind == "reference_original":
        return 0          # pre-registered: fails (0,0,1) and (4,0,1)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs", type=Path, required=True)
    ap.add_argument("--attestation", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    grade.verify_attestation(a.attestation)            # raises unless containment passed, fresh and bound
    specs = json.loads(a.specs.read_text())
    a.out.mkdir(parents=True, exist_ok=False)
    rows, started = [], time.monotonic()
    for spec in specs:
        rid = spec["root_id"]
        jobs = [("reference_original", spec["reference_code"])]
        if rid == "mbpp/402":
            jobs.append(("reference_repaired", repaired_402(spec["reference_code"])))
        jobs += [("control", c["code"]) for c in spec["negative_controls"]]
        for kind, code in jobs:
            r = grade.evaluate(spec, code, sandbox.run_program)
            rows.append({"root_id": rid, "kind": kind, "outcome": r["outcome"], "reason": r["reason"],
                         "sandbox_executed": r.get("sandbox_executed"), "expected": expected(rid, kind),
                         "as_preregistered": r["outcome"] == expected(rid, kind),
                         "code_sha256": grade.digest(code) if hasattr(grade, "digest") else None,
                         "stderr_tail": ((r.get("run") or {}).get("stderr") or "")[-300:]})
    verdict = {}
    for spec in specs:
        rid = spec["root_id"]
        mine = [x for x in rows if x["root_id"] == rid]
        positive = [x for x in mine if x["kind"] == ("reference_repaired" if rid == "mbpp/402" else "reference_original")]
        controls = [x for x in mine if x["kind"] == "control"]
        ok_pos = bool(positive) and all(x["outcome"] == 1 for x in positive)
        ok_ctl = bool(controls) and all(x["outcome"] == 0 and x["sandbox_executed"] for x in controls)
        verdict[rid] = {"cleared": ok_pos and ok_ctl, "positive_reference_passes": ok_pos,
                        "every_control_executed_and_failed": ok_ctl,
                        "all_outcomes_as_preregistered": all(x["as_preregistered"] for x in mine)}
    summary = {"executed_programs": len(rows), "sandbox_seconds_wall": round(time.monotonic() - started, 2),
               "model_calls": 0, "roots_cleared": sum(v["cleared"] for v in verdict.values()),
               "all_as_preregistered": all(x["as_preregistered"] for x in rows), "verdict": verdict}
    (a.out / "rows.json").write_text(json.dumps(rows, indent=2))
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
