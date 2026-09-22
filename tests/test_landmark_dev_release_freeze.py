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


def historical_contract(commit, specs):
    """Recompute contract(specs) as the grader at `commit` defined it, statically from its git blobs (MRL-14).

    The contract() dict literal is read from that commit's grade.py with ast (never imported or executed);
    adapter/sandbox/integrity hashes are the SHA-256 of the blobs at that commit, as file_sha computed them then."""
    import ast, hashlib, subprocess
    blob = lambda p: subprocess.check_output(["git", "show", f"{commit}:{p}"], cwd=ROOT)
    fn = next(n for n in ast.parse(blob("experiments/landmark/grade.py")).body if isinstance(n, ast.FunctionDef) and n.name == "contract")
    ret = fn.body[-1].value
    computed = {"private_spec_sha256": grade.digest(specs),
                "adapter_sha256": hashlib.sha256(blob("experiments/landmark/grade.py")).hexdigest(),
                "sandbox_sha256": hashlib.sha256(blob("experiments/landmark/sandbox.py")).hexdigest(),
                "integrity_sha256": hashlib.sha256(blob("experiments/common/integrity.py")).hexdigest()}
    out = {}
    for k, v in zip(ret.keys, ret.values):
        key = ast.literal_eval(k)
        out[key] = computed[key] if key in computed else ast.literal_eval(v)
    return out


def test_grading_contract_hash_uses_the_graders_own_convention():
    """Bound to the grader sources at the freeze commit, not the current checkout: MRL-14 changed grade.py
    (candidate compile gate, GRADER_VERSION), so the current contract must differ and needs a new freeze."""
    assert CFG["grading_contract_sha256"] == grade.digest(historical_contract(FREEZE_COMMIT, SPECS))
    assert CFG["grading_contract_sha256"] != grade.digest(grade.contract(SPECS))


def test_private_specs_are_in_the_format_the_grader_reads_and_bind_the_public_tasks():
    grade.validate_specs(TASKS, SPECS)


FREEZE_COMMIT = "3e70c0a04482bf8ca1e9e0872c4d1037988ba09d"  # resolved by the graded v1b run's manifest


def test_release_config_binds_to_its_frozen_source_blobs():
    """The historical freeze resolves at its own commit. The runtime has changed since (MRL-06 guards), so
    real-mode reuse on the current checkout must fail: a changed runtime needs a new freeze, not a waiver."""
    import pytest
    from tests._frozen_source import frozen_source_hashes
    assert collect.digest(frozen_source_hashes(FREEZE_COMMIT)) == CFG["source_code_sha256"]
    collect.validate(CFG, TASKS, real=False)
    if collect.digest(collect.source_hashes()) != CFG["source_code_sha256"]:
        with pytest.raises(ValueError, match="differs from freeze"):
            collect.validate(CFG, TASKS, real=True)
