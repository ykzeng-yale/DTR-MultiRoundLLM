"""Guards the development release freeze against the convention error that superseded its first run.

The first collection was frozen with the SHA-256 of the grading-contract FILE, while grade.py binds a
collection to digest(contract(specs)) -- which covers the specs and the grader, sandbox and integrity
sources. The grader rightly refused to grade it. These tests make that impossible to repeat.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "experiments/landmark"))
from experiments.landmark import grade  # noqa: E402
import collect  # noqa: E402

D = ROOT / "experiments/landmark/dev_release_v1"
CFG = json.loads((D / "config.json").read_text())
SPECS = [json.loads(l) for l in (D / "private_specs.jsonl").read_text().splitlines() if l.strip()]
TASKS = [json.loads(l) for l in (D / "tasks.jsonl").read_text().splitlines() if l.strip()]


def test_grading_contract_hash_uses_the_graders_own_convention():
    assert CFG["grading_contract_sha256"] == grade.digest(grade.contract(SPECS))


def test_private_specs_are_in_the_format_the_grader_reads_and_bind_the_public_tasks():
    grade.validate_specs(TASKS, SPECS)


def test_release_config_validates_in_real_mode():
    collect.validate(CFG, TASKS, real=True)
