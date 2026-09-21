#!/usr/bin/env python3
"""Source-only builder for the public-diagnostic development release v2 (MRL-08 field 14).

Appends the fixed public examples to each v1c public task, rebinds every private spec's
public_task_sha256 and recomputes the grading-contract digest. Private assertions and
reference code stay byte-identical to v1c. Executes no benchmark, reference, control or
candidate code; writes only to a new directory under work/ and never overwrites. This is
a proposed release package, not a freeze: the final literal-overlap audit, receiver config
and template-render checks remain separate gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import diagnostic, grade
from experiments.landmark.collect import digest, file_sha

V1C = ROOT / "experiments/landmark/dev_release_v1c"
EXAMPLES = ROOT / "docs/public_diagnostic_examples_v1.json"
UNCHANGED = ("root_id", "entry_point", "public_assertions", "private_assertions", "preamble", "reference_code", "negative_controls")


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def jsonl_bytes(rows):
    # Same serialization as the v1c release files (verified byte-identical on v1c).
    return ("\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def rebind(tasks, specs, examples):
    """Return (new_tasks, new_specs): examples appended once, specs rebound, private bytes unchanged."""
    examples = examples["cases"] if isinstance(examples, dict) else examples
    order = [t["root_id"] for t in tasks]
    if [e["root_id"] for e in examples] != order or sorted(s["root_id"] for s in specs) != sorted(order) or len(set(order)) != len(order):
        raise ValueError("examples, tasks and specs must cover the same roots in the fixed task order")
    by_root = {s["root_id"]: s for s in specs}
    new_tasks, new_specs = [], []
    for task, ex in zip(tasks, examples):
        spec = by_root[task["root_id"]]
        if ex["entry_point"] != spec["entry_point"]:
            raise ValueError(f"{task['root_id']}: example entry point differs from the private spec")
        if diagnostic.EXAMPLES_HEADER in task["public_context"]:
            raise ValueError(f"{task['root_id']}: public examples already present; refusing to append twice")
        if spec["public_task_sha256"] != digest(task):
            raise ValueError(f"{task['root_id']}: input spec does not bind the input task")
        rendered = diagnostic.render_public_examples(ex["entry_point"], ex["cases"])
        new_task = {**task, "public_context": task["public_context"] + "\n\n" + rendered}
        new_spec = {**spec, "public_task_sha256": digest(new_task)}
        for key in UNCHANGED:
            if canon(new_spec[key]) != canon(spec[key]):
                raise AssertionError(f"{task['root_id']}: {key} changed")
        new_tasks.append(new_task)
        new_specs.append(new_spec)
    grade.validate_specs(new_tasks, new_specs)  # static only: AST parse and literal exposure checks
    return new_tasks, new_specs


def check_against_v1c(old_specs, new_specs):
    old = {s["root_id"]: s for s in old_specs}
    for s in new_specs:
        for key in ("private_assertions", "reference_code"):
            if canon(s[key]) != canon(old[s["root_id"]][key]):
                raise AssertionError(f"{s['root_id']}: {key} is not byte-identical to v1c")


def build(output):
    output = Path(output).resolve()
    work = (ROOT / "work").resolve()
    if work not in output.parents:
        raise SystemExit(f"output must be under {work}")
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing {output}")
    tasks, specs = load_jsonl(V1C / "tasks.jsonl"), load_jsonl(V1C / "private_specs.jsonl")
    new_tasks, new_specs = rebind(tasks, specs, json.loads(EXAMPLES.read_text(encoding="utf-8")))
    check_against_v1c(specs, new_specs)
    task_bytes, spec_bytes = jsonl_bytes(new_tasks), jsonl_bytes(new_specs)
    manifest = {
        "schema_version": "landmark-dev-release-v2-proposal", "status": "source-only build; not frozen or released",
        "roots": [t["root_id"] for t in new_tasks],
        "tasks_sha256": hashlib.sha256(task_bytes).hexdigest(), "private_specs_sha256": hashlib.sha256(spec_bytes).hexdigest(),
        "grading_contract_sha256": grade.digest(grade.contract(new_specs)),
        "v1c_tasks_sha256": file_sha(V1C / "tasks.jsonl"), "v1c_private_specs_sha256": file_sha(V1C / "private_specs.jsonl"),
        "v1c_grading_contract_sha256": grade.digest(grade.contract(specs)),
        "examples_sha256": file_sha(EXAMPLES), "builder_sha256": file_sha(Path(__file__)),
        "diagnostic_sha256": file_sha(Path(diagnostic.__file__)),
        "public_task_sha256": {s["root_id"]: s["public_task_sha256"] for s in new_specs},
        "private_assertions_and_reference_code_identical_to_v1c": True,
        "pending": ["final literal-overlap audit (PASS/HOLD)", "landmark-v2 receiver config binding", "template render check"],
        "executions": 0, "model_calls": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "tasks.jsonl").write_bytes(task_bytes)
    (output / "private_specs.jsonl").write_bytes(spec_bytes)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, help="new directory under work/; must not exist")
    print(json.dumps(build(parser.parse_args().output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
