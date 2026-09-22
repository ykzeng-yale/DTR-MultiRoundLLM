"""v1c differs from v1 only in the grading side, and binds to the grader's own contract digest."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "experiments/landmark"))
from experiments.landmark import grade  # noqa: E402
import collect  # noqa: E402
V1, V1C = ROOT / "experiments/landmark/dev_release_v1", ROOT / "experiments/landmark/dev_release_v1c"
load = lambda d, f: [json.loads(l) for l in (d / f).read_text().splitlines() if l.strip()]


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


def test_everything_the_receiver_sees_is_identical_to_v1():
    assert load(V1, "tasks.jsonl") == load(V1C, "tasks.jsonl")
    a, b = (json.loads((d / "config.json").read_text()) for d in (V1, V1C))
    assert {k for k in a if a[k] != b[k]} == {"protocol_version", "grading_contract_sha256"}


def test_v1c_binds_to_the_graders_contract_and_402_carries_the_repair():
    specs, cfg = load(V1C, "private_specs.jsonl"), json.loads((V1C / "config.json").read_text())
    # Bound to the grader sources at the v1c freeze commit (MRL-14 changed grade.py; the current contract differs).
    assert cfg["grading_contract_sha256"] == grade.digest(historical_contract("d5efcd8544b0718961190fe06f442d3a1d727ae4", specs))
    assert cfg["grading_contract_sha256"] != grade.digest(grade.contract(specs))
    ref = [s for s in specs if s["root_id"] == "mbpp/402"][0]["reference_code"]
    assert ref.rstrip().endswith("return C[r] % p")
    from tests._frozen_source import frozen_source_hashes
    # Resolved at the v1c run's own freeze commit (its manifest), not the current checkout.
    assert collect.digest(frozen_source_hashes("d5efcd8544b0718961190fe06f442d3a1d727ae4")) == cfg["source_code_sha256"]
    collect.validate(cfg, load(V1C, "tasks.jsonl"), real=False)
