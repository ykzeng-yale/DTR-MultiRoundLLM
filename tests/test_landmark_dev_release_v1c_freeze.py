"""v1c differs from v1 only in the grading side, and binds to the grader's own contract digest."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "experiments/landmark"))
from experiments.landmark import grade  # noqa: E402
import collect  # noqa: E402
V1, V1C = ROOT / "experiments/landmark/dev_release_v1", ROOT / "experiments/landmark/dev_release_v1c"
load = lambda d, f: [json.loads(l) for l in (d / f).read_text().splitlines() if l.strip()]


def test_everything_the_receiver_sees_is_identical_to_v1():
    assert load(V1, "tasks.jsonl") == load(V1C, "tasks.jsonl")
    a, b = (json.loads((d / "config.json").read_text()) for d in (V1, V1C))
    assert {k for k in a if a[k] != b[k]} == {"protocol_version", "grading_contract_sha256"}


def test_v1c_binds_to_the_graders_contract_and_402_carries_the_repair():
    specs, cfg = load(V1C, "private_specs.jsonl"), json.loads((V1C / "config.json").read_text())
    assert cfg["grading_contract_sha256"] == grade.digest(grade.contract(specs))
    ref = [s for s in specs if s["root_id"] == "mbpp/402"][0]["reference_code"]
    assert ref.rstrip().endswith("return C[r] % p")
    collect.validate(cfg, load(V1C, "tasks.jsonl"), real=True)
