#!/usr/bin/env python3
"""Build a source-only contract REVIEW package; never execute benchmark code.

The seven tasks retain the original fixed-slate identities. This is an explicitly
changed development endpoint, not a benchmark result or an experiment freeze.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark.collect import digest, file_sha
from experiments.landmark.grade import contract, validate_specs
from experiments.common.integrity import hack_gate

VERSION_V2 = "landmark-curated-development-contracts-v2"
V2_HOLD_STATES = {
    402: {"reference_repair_proposed_awaiting_isolated_execution"},
    357: {"discrimination_defect_fixed_in_v2_awaiting_isolated_validation"},
}
RETAINED = [52, 357, 373, 378, 402, 489, 509]
SOURCE_SHA = "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"
VERSION = "landmark-curated-development-contracts-v1"


def boundary_assertion(entry_point, arguments, case):
    # literal_eval accepts only literals, never calls or arbitrary expressions.
    args = ast.literal_eval(case["args_literal"])
    expected = ast.literal_eval(case["expected_literal"])
    if not isinstance(args, list) or len(args) != len(arguments):
        raise ValueError("Boundary arguments must be a literal list of the declared arity")
    return f"assert {entry_point}({', '.join(repr(x) for x in args)}) == {expected!r}"


def reference_code(row, cfg, adopt):
    """The reference placed in the private spec.

    Default: the pinned original, exactly as before. With adopt=True and a task carrying a
    `reference_repair`, the repaired reference is rebuilt from the original by the recorded change and
    accepted ONLY if it hashes to the frozen `repaired_raw_sha256`. Nothing is taken on trust from the
    contract's prose; and the grader still re-validates the reference against the full private suite
    before it grades any candidate for that root.
    """
    repair = cfg.get("reference_repair")
    if not adopt or not repair:
        return row["code"]
    if row["code"].count("return C[r]") != 1:
        raise ValueError("Recorded repair does not apply to this reference")
    repaired = row["code"].replace("return C[r]", "return C[r] % p", 1)
    if hashlib.sha256(repaired.encode()).hexdigest() != repair["repaired_raw_sha256"]:
        raise ValueError("Rebuilt repaired reference does not match its frozen hash")
    return repaired


def build(source, config, adopt_reference_repairs=False):
    if config["version"] not in (VERSION, VERSION_V2) or config["source_sha256"] != SOURCE_SHA:
        raise ValueError("Unexpected source or specification version")
    if file_sha(source) != SOURCE_SHA:
        raise ValueError("Pinned source bytes do not match")
    ids = [t["source_task_id"] for t in config["tasks"]]
    if ids != RETAINED:
        raise ValueError("Preserve all seven retained IDs in order; do not backfill")
    if config["family_id"] != "unresolved_development_family" or config["public_assertions"] != []:
        raise ValueError("This review version has one unresolved family and no public tests")
    full = {}
    for line in Path(source).read_text().splitlines():
        row = json.loads(line)
        if row["task_id"] in full:
            raise ValueError("Duplicate source task ID")
        full[row["task_id"]] = row
    tasks, specs, provenance = [], [], []
    for cfg in config["tasks"]:
        row = full[cfg["source_task_id"]]
        tree = ast.parse(row["code"])
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
            raise ValueError("Reference interface requires manual review")
        fn = tree.body[0]
        args = fn.args
        if (fn.name != cfg["entry_point"] or [a.arg for a in args.args] != cfg["arguments"]
            or args.posonlyargs or args.kwonlyargs or args.defaults or args.kwarg or args.vararg
            or fn.decorator_list or fn.returns or any(a.annotation for a in args.args)):
            raise ValueError("Declared interface does not match reviewed source")
        if row["test_setup_code"].strip() or row["challenge_test_list"]:
            raise ValueError("Unexpected setup/challenge tests require review")
        if config["version"] == VERSION:
            required_status = {"known_reference_boundary_defect" if row["task_id"] == 402
                               else "awaiting_isolated_reference_and_control_validation"}
        else:
            # v2 hold states. Every one is still a hold: none of them asserts a validated reference, so
            # building from v2 can no more clear a validation hold than building from v1 could.
            required_status = V2_HOLD_STATES.get(row["task_id"], {"awaiting_isolated_reference_and_control_validation"})
        if cfg["status"] not in required_status:
            raise ValueError("Source-only preparation cannot clear a validation hold")
        signature = f"def {fn.name}({', '.join(cfg['arguments'])}):"
        task = {"root_id": f"mbpp/{row['task_id']}", "family_id": config["family_id"],
                "prompt": cfg["prompt"], "public_context":
                f"Required function interface: {signature}\n{config['format_instruction']}"}
        added = [boundary_assertion(fn.name, cfg["arguments"], c) for c in cfg["boundary_cases"]]
        # v2 annotates added cases/controls with added_in/reason for the audit trail. They are
        # documentation, not part of the executable spec, whose controls must be exactly {code, rationale}.
        controls = [{"code": c["code"], "rationale": c["rationale"]} for c in cfg["negative_controls"]]
        for control in controls:
            if hack_gate(control["code"], fn.name):
                raise ValueError("Control has a static integrity flag; cannot assume an executed failure")
        spec = {"root_id": task["root_id"], "public_task_sha256": digest(task),
                "entry_point": fn.name, "public_assertions": [],
                "private_assertions": [*row["test_list"], *added], "preamble": [],
                "reference_code": reference_code(row, cfg, adopt_reference_repairs), "negative_controls": controls}
        tasks.append(task)
        specs.append(spec)
        provenance.append({"root_id": task["root_id"], "status": cfg["status"],
            "source_row_sha256": digest(row), "original_text_sha256": digest(row["text"]),
            "original_reference_sha256": digest(row["code"]),
            "original_assertions_sha256": digest(row["test_list"]),
            "original_assertion_count": len(row["test_list"]),
            "authored_boundary_assertion_count": len(added),
            "authored_assertions_sha256": digest(added), "negative_control_count": len(controls),
            "public_task_sha256": digest(task), "private_spec_sha256": digest(spec)})
    validate_specs(tasks, specs)
    return tasks, specs, provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT/"experiments/landmark/task_contracts_v1.json")
    parser.add_argument("--adopt-reference-repairs", action="store_true",
                        help="Place hash-verified recorded reference repairs in the private specs (recorded in the manifest)")
    parser.add_argument("--out", type=Path, required=True,
                        help="Unused directory under ignored work/; contains PRIVATE reference/tests")
    args = parser.parse_args(argv)
    output = args.out.resolve()
    if not output.is_relative_to((ROOT/"work").resolve()):
        raise ValueError("Private source-derived artifacts must stay under ignored work/")
    if output.exists():
        raise FileExistsError("Use a new output directory; completed packages are immutable")
    started = time.monotonic()
    config = json.loads(args.config.read_text())
    tasks, specs, provenance = build(args.source, config, adopt_reference_repairs=args.adopt_reference_repairs)
    frozen_grader = contract(specs)
    output.mkdir(parents=True, exist_ok=False)
    (output/"public_tasks.REVIEW_ONLY.jsonl").write_text("".join(json.dumps(t, sort_keys=True)+"\n" for t in tasks))
    (output/"private_specs.REVIEW_ONLY.json").write_text(json.dumps(specs, indent=2)+"\n")
    (output/"grading_contract.REVIEW_ONLY.json").write_text(json.dumps(frozen_grader, indent=2)+"\n")
    manifest = {"version": config["version"], "adopt_reference_repairs": bool(args.adopt_reference_repairs), "evidence_class": "source-only contract preparation",
        "ready_for_collection": False, "reference_controls_executed": False,
        "blocking_conditions": ["host containment not established", "mbpp/402 original reference conflicts with p=1,r=0",
            "other references/controls not executed", "families and independent policy-test cohort unresolved",
            "receiver and complete experiment freeze absent"],
        "source_sha256": file_sha(args.source), "source_url": config["source_url"],
        "dataset_license": config["dataset_license"], "configuration_sha256": file_sha(args.config),
        "builder_sha256": file_sha(__file__), "grader_contract_sha256": digest(frozen_grader),
        "public_tasks_canonical_sha256": digest(tasks), "private_specs_canonical_sha256": digest(specs),
        "artifacts": {p.name: file_sha(p) for p in sorted(output.iterdir())}, "tasks": provenance,
        "accounting": {"model_calls": 0, "model_tokens": 0, "benchmark_reference_control_executions": 0,
            "sandbox_launches": 0, "external_spend_usd": 0,
            "builder_wall_seconds": time.monotonic()-started}}
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps({"output": str(output), "ready_for_collection": False, "roots": len(tasks),
                      "private_assertions": sum(len(s["private_assertions"]) for s in specs)}))


if __name__ == "__main__":
    main()
