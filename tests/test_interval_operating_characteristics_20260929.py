from fractions import Fraction
import importlib.util
import json
from pathlib import Path

from experiments.prompt_choice.paired_inference import paired_contrasts

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "interval_operating_characteristics",
    ROOT / "scripts/run_interval_operating_characteristics_20260929.py",
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_all_scenario_truths_and_total_assignments_match_the_frozen_plan():
    plan = json.loads((ROOT / "experiments/prompt_choice/interval_operating_characteristics_plan_20260929.json").read_text())
    assert len(plan["scenarios"]) == 7
    assert len(plan["family_counts"]) == 6
    assert len({plan["base_seed"] + 10000*s["scenario_index"] + n
                for s in plan["scenarios"] for n in plan["family_counts"]}) == 42
    assert 42 * plan["replicates_per_cell"] == plan["total_assigned_replicates"] == 840000
    for scenario in plan["scenarios"]:
        expected = (runner.frac(scenario["truth_d_minus_b1"]), runner.frac(scenario["truth_d_minus_b2"]))
        assert runner.exact_means(scenario) == expected
        assert runner.prepare_support(scenario)[-1][0] == 1000


def test_count_form_matches_frozen_public_paired_contrast_function():
    alpha, n = Fraction(1,20), 4
    cache = {(c,n,alpha): runner.kl_interval(Fraction(c,n), n, alpha)[:2] for c in range(n+1)}
    # All per-row values are exact, bounded family contrasts. The second contrast
    # intentionally differs so the simultaneous public entry point is exercised.
    d1 = [1, -1, 0, 0]
    d2 = [-1, 0, 1, 0]
    families = [{"family_id": f"g{i}", "bounds": {
        "d_minus_b1": (d1[i], d1[i]), "d_minus_b2": (d2[i], d2[i])}}
        for i in range(n)]
    actual = paired_contrasts(families, alpha)["intervals"]
    for name, values in (("d_minus_b1", d1), ("d_minus_b2", d2)):
        positive, negative = sum(v == 1 for v in values), sum(v == -1 for v in values)
        want = runner.sign_split_interval(positive, negative, n, alpha, cache)
        got = tuple(Fraction(actual[name][i]["num"], actual[name][i]["den"]) for i in (0,1))
        assert got == want


def test_draws_are_deterministic_and_preserve_joint_outcome_mapping():
    scenario = {"support": [{"outcomes": [1,0,0], "mass": 100},
                            {"outcomes": [0,1,1], "mass": 100}]}
    cumulative = runner.prepare_support(scenario)
    a = runner.draw_counts(__import__("random").Random(19), cumulative, 30)
    b = runner.draw_counts(__import__("random").Random(19), cumulative, 30)
    assert a == b
    p1,q1,p2,q2 = a
    assert p1 == p2 and q1 == q2
    assert p1 + q1 <= 30 and p2 + q2 <= 30
