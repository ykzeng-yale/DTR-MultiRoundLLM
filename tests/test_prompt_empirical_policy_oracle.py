"""Codex independent finite oracle; synthetic enumeration, not sampled/model evidence.

Does not use the implementation's row builder, value calculator, or map enumerator.
Three families have sizes 1, 2, 2; the last includes a common missing-outcome root.
All 3**8 assignments of {0, 1, missing} to the eight action slots are checked.
"""
from fractions import Fraction
from itertools import product

from experiments.prompt_choice import empirical_policy as ep


def test_independent_exhaustive_missing_score_and_family_weight_oracle():
    identities = ep.load_identity()
    maps = list(product((0, 1), repeat=4))
    actions = ("PATCH", "RETHINK")
    cells = ("00", "01", "10", "11")
    # Integer oracle weights in sixths; common missing root is the remaining 1/6.
    weights = (2, 1, 1, 1)
    for scores in product((0, 1, None), repeat=8):
        lower = tuple(0 if x is None else x for x in scores)
        upper = tuple(1 if x is None else x for x in scores)
        values = [sum(weights[i] * lower[2*i + m[i]] for i in range(4)) for m in maps]
        fixed = [sum(weights[i] * lower[2*i + a] for i in range(4)) for a in (0, 1)]
        b1 = int(fixed[1] > fixed[0])
        maximizers = [m for m, v in zip(maps, values) if v == max(values)]
        chosen = min(maximizers, key=lambda m: sum(a != b1 for a in m))
        roots = [
            {"root_id": f"toy/{i}",
             "state": {"has_payload_failure": i >= 2, "has_incomplete": bool(i % 2)},
             "outcomes": {actions[a]: [scores[2*i + a]] for a in (0, 1)}}
            for i in range(4)
        ]
        common = {"root_id": "toy/common", "state": None,
                  "common_outcome": None, "invalid_disposition": "synthetic_missing"}
        data = {"partition": "development", "replicates": 1, "families": [
            {"family_id": "toy/A", "roots": roots[:1]},
            {"family_id": "toy/B", "roots": roots[1:3]},
            {"family_id": "toy/C", "roots": roots[3:] + [common]},
        ]}
        result = ep.fit(data, identities)
        assert result["artifact"]["b1"] == actions[b1]
        assert result["artifact"]["map"] == dict(zip(cells, (actions[a] for a in chosen)))
        report = result["report"]
        expected = {
            "d_value": (max(values), 1 + sum(weights[i] * upper[2*i + chosen[i]] for i in range(4))),
            "b1_value": (fixed[b1], 1 + sum(weights[i] * upper[2*i + b1] for i in range(4))),
        }
        for key, bounds in expected.items():
            for side, numerator in zip(("lower", "upper"), bounds):
                actual = report[key][side]
                assert Fraction(actual["num"], actual["den"]) == Fraction(numerator, 6)
