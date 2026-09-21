"""Offline contract checks; no receiver calls or candidate program execution."""

import ast
import hashlib
import inspect
import itertools
import json
from pathlib import Path
import random
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from experiments.landmark import graph_adapter as adapter
from experiments.landmark.vendor import reasoning_gym_graph_color as upstream


TRIANGLE = {"vertices": [0, 1, 2], "edges": [[0, 1], [0, 2], [1, 2]], "color_options": [1, 2, 3]}
VALID = '{"0":1,"1":2,"2":3}'


def test_frozen_controls():
    config = json.loads((REPO / "experiments/landmark/graph_fixture_config_v1.json").read_text())
    assert len(config["fixed_controls"]) == 15
    for control in config["fixed_controls"]:
        result = adapter.grade_response(config["fixed_control_puzzle"], control["response"])
        assert result["score"] == control["expected_score"], control["name"]
        assert result["status"] == ("missing" if control["response"] is None else "observed")


def test_all_four_vertex_graphs_and_three_color_assignments_independently():
    """64 graphs x 81 assignments; truth does not use the vendored verifier."""
    possible_edges = list(itertools.combinations(range(4), 2))
    cases = 0
    for mask in range(1 << len(possible_edges)):
        edges = [edge for index, edge in enumerate(possible_edges) if mask & (1 << index)]
        puzzle = {"vertices": list(range(4)), "edges": edges, "color_options": [1, 2, 3]}
        for colors in itertools.product((1, 2, 3), repeat=4):
            expected = int(all(colors[u] != colors[v] for u, v in edges))
            response = json.dumps({str(v): colors[v] for v in range(4)})
            result = adapter.grade_response(puzzle, response)
            assert result["status"] == "observed"
            assert result["score"] == expected
            cases += 1
    assert cases == 5184


@pytest.mark.parametrize("response", [
    '{"0":1,"\\u0030":2,"1":2,"2":3}',
    '{"00":1,"1":2,"2":3}',
    '{"0":1e0,"1":2,"2":3}',
    '{"0":1.0,"1":2,"2":3}',
    '{"0":true,"1":2,"2":3}',
    '{"0":"1","1":2,"2":3}',
    '{"0":[1],"1":2,"2":3}',
    '{"0":{"color":1},"1":2,"2":3}',
    '{"0":NaN,"1":2,"2":3}',
    '{"0":Infinity,"1":2,"2":3}',
    '{"0":-Infinity,"1":2,"2":3}',
    '{"0":null,"1":2,"2":3}',
    VALID + ' trailing',
    '```json\n' + VALID + '\n```',
    '[1,2,3]', 'null', 'true', '1', '"text"', '',
    '{"0":' + '9' * 1000 + ',"1":2,"2":3}',
])
def test_adversarial_produced_responses_are_zero(response):
    result = adapter.grade_response(TRIANGLE, response)
    assert result["status"] == "observed"
    assert result["score"] == 0


def test_unicode_escape_for_single_canonical_key_is_valid():
    assert adapter.grade_response(TRIANGLE, '{"\\u0030":1,"1":2,"2":3}')["score"] == 1


def test_utf8_byte_cap_and_depth_are_enforced_before_parsing():
    response = '{"0":"ééé","1":2,"2":3}'
    assert len(response.encode()) > len(response)
    assert adapter.grade_response(TRIANGLE, response, len(response))["diagnostic"]["code"] == "response_too_large"
    assert adapter.grade_response(TRIANGLE, ' ' * 16385)["diagnostic"]["code"] == "response_too_large"
    deep = '{"0":' + '[' * 20 + '1' + ']' * 20 + ',"1":2,"2":3}'
    assert adapter.grade_response(TRIANGLE, deep)["diagnostic"]["code"] == "json_depth_limit"
    assert adapter.grade_response(TRIANGLE, '\ud800')["diagnostic"]["code"] == "invalid_unicode"


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, 16385])
def test_invalid_response_cap_is_caller_error(limit):
    with pytest.raises(ValueError):
        adapter.grade_response(TRIANGLE, VALID, limit)


def test_unavailable_and_caller_error_are_not_malformed_output():
    assert adapter.grade_response(TRIANGLE, None) == {
        "status": "missing", "score": None, "diagnostic": {"code": "missing_output"}}
    assert adapter.grade_response(TRIANGLE, "")["score"] == 0
    with pytest.raises(ValueError):
        adapter.grade_response(TRIANGLE, {"0": 1})


@pytest.mark.parametrize("changes", [
    {"vertices": []}, {"vertices": [0, 0, 1]}, {"vertices": [False, 1, 2]},
    {"vertices": [0.0, 1, 2]}, {"vertices": [-1, 1, 2]}, {"vertices": list(range(129))},
    {"edges": [[0, 0]]}, {"edges": [[1, 0]]}, {"edges": [[0, 3]]},
    {"edges": [[0, 1], [0, 1]]}, {"edges": [[False, 1]]},
    {"edges": [[0, 1, 2]]}, {"edges": "none"},
    {"color_options": []}, {"color_options": [True, 2, 3]},
    {"color_options": [1, 1, 2]}, {"color_options": [0, 1, 2]},
    {"num_colors": 2}, {"num_colors": True}, {"reference": {"0": 1}},
])
def test_invalid_trusted_puzzles_raise(changes):
    puzzle = {**TRIANGLE, **changes}
    with pytest.raises(ValueError):
        adapter.validate_puzzle(puzzle)
    with pytest.raises(ValueError):
        adapter.grade_response(puzzle, None)
    with pytest.raises(ValueError):
        adapter.build_public_task("root", "family", puzzle)


@pytest.mark.parametrize("puzzle", [None, [], {}, {"vertices": [0]}])
def test_invalid_puzzle_schema(puzzle):
    with pytest.raises(ValueError):
        adapter.validate_puzzle(puzzle)


def test_edgeless_graph_and_alternative_solution_are_valid():
    empty_edges = {**TRIANGLE, "edges": []}
    assert adapter.grade_response(empty_edges, '{"0":1,"1":1,"2":1}')["score"] == 1
    assert adapter.grade_response(TRIANGLE, '{"2":1,"0":2,"1":3}')["score"] == 1


def test_diagnostic_is_public_deterministic_and_bounded():
    bad = '{"0":1,"1":1,"2":1}'
    expected = {"code": "edge_conflict", "conflicting_edges": [[0, 1], [0, 2], [1, 2]], "conflict_count": 3}
    assert adapter.grade_response(TRIANGLE, bad)["diagnostic"] == expected
    reordered = {**TRIANGLE, "edges": list(reversed(TRIANGLE["edges"]))}
    assert adapter.grade_response(reordered, bad)["diagnostic"] == expected
    puzzle = {"vertices": list(range(8)), "edges": list(itertools.combinations(range(8), 2)), "color_options": [1]}
    result = adapter.grade_response(puzzle, json.dumps({str(v): 1 for v in range(8)}))
    assert result["diagnostic"]["conflict_count"] == 28
    assert len(result["diagnostic"]["conflicting_edges"]) == adapter.MAX_DIAGNOSTIC_EDGES


def test_public_renderer_matches_collector_schema_and_declares_contract():
    task = adapter.build_public_task("root", "family", {**TRIANGLE, "num_colors": 3})
    assert set(task) == {"root_id", "family_id", "prompt", "public_context"}
    assert all(type(value) is str for value in task.values())
    assert json.loads(task["public_context"]) == TRIANGLE
    assert "exactly once" in task["prompt"] and "UTF-8" in task["prompt"]
    assert "booleans" in task["prompt"] and "exponents" in task["prompt"]
    assert "reference" not in json.dumps(task) and "possible_answer" not in json.dumps(task)
    for value in ("", None, 1, "a" * 257):
        with pytest.raises(ValueError):
            adapter.build_public_task(value, "family", TRIANGLE)


def test_generated_root_reproducible_and_does_not_touch_global_rng():
    before = random.getstate()
    first = adapter.generate_root(71, 8, 0.2, 3, 128)
    second = adapter.generate_root(71, 8, 0.2, 3, 128)
    assert first == second
    assert random.getstate() == before
    assert first["status"] == "generated"
    ref = first["reference"]
    assert all(ref[u] != ref[v] for u, v in first["puzzle"]["edges"])
    assert set(ref) == set(first["puzzle"]["vertices"])
    assert set(ref.values()) <= set(first["puzzle"]["color_options"])


def test_k4_cap_is_retained_without_backfill():
    result = adapter.generate_root(1, 4, 1.0, 3, 3)
    assert result == {"status": "generation_failed", "puzzle": None, "reference": None,
                      "attempts": 3, "reason": "greedy_acceptance_cap_reached"}
    edges = list(itertools.combinations(range(4), 2))
    assert not any(all(colors[u] != colors[v] for u, v in edges)
                   for colors in itertools.product((1, 2, 3), repeat=4))


def test_greedy_rejection_does_not_mean_unsatisfiable(monkeypatch):
    vertices = list(range(8))
    edges = sorted(tuple(sorted((2 * i, 2 * j + 1))) for i in range(4) for j in range(4) if i != j)
    crown = {"vertices": vertices, "edges": edges, "color_options": [1, 2, 3]}
    reference = {str(vertex): 1 + vertex % 2 for vertex in vertices}
    assert adapter.grade_response(crown, json.dumps(reference))["score"] == 1
    assert upstream.greedy_graph_coloring(crown) is None
    calls = []

    def fixed_crown(rng, num_vertices, edge_probability):
        calls.append((num_vertices, edge_probability))
        return vertices, edges

    monkeypatch.setattr(adapter, "generate_random_graph", fixed_crown)
    result = adapter.generate_root(99, 8, 0.3, 3, 2)
    assert len(calls) == 2 and result["status"] == "generation_failed"
    assert "unsatisfiable" not in json.dumps(result)


@pytest.mark.parametrize("changes", [
    {"seed": True}, {"seed": -1}, {"seed": 2**64},
    {"num_vertices": 0}, {"num_vertices": 129}, {"num_vertices": 8.0},
    {"edge_probability": float("nan")}, {"edge_probability": float("inf")},
    {"edge_probability": -0.1}, {"edge_probability": 1.1}, {"edge_probability": True},
    {"edge_probability": 10**1000},
    {"num_colors": 0}, {"num_colors": False}, {"max_attempts": 0}, {"max_attempts": 129},
])
def test_generation_rejects_invalid_config_before_drawing(changes, monkeypatch):
    def forbidden_draw(*args):
        pytest.fail("invalid configuration reached a draw")

    monkeypatch.setattr(adapter, "generate_random_graph", forbidden_draw)
    config = {"seed": 1, "num_vertices": 8, "edge_probability": 0.2, "num_colors": 3, "max_attempts": 128}
    with pytest.raises(ValueError):
        adapter.generate_root(**{**config, **changes})


def test_verifier_inconsistency_is_not_a_false_zero(monkeypatch):
    monkeypatch.setattr(adapter, "verify_graph_coloring_solution", lambda *_: (False, "changed verifier"))
    with pytest.raises(RuntimeError):
        adapter.grade_response(TRIANGLE, VALID)


def test_vendored_function_and_license_hashes_match_manifest():
    directory = Path(upstream.__file__).parent
    manifest = json.loads((directory / "reasoning_gym_graph_color_manifest.json").read_text())
    assert hashlib.sha256(Path(upstream.__file__).read_bytes()).hexdigest() == manifest["local_sha256"]
    assert hashlib.sha256((directory / manifest["license"]["local_path"]).read_bytes()).hexdigest() == manifest["license"]["sha256"]
    for function in manifest["functions"]:
        exact_segment = inspect.getsource(getattr(upstream, function["name"]))
        assert hashlib.sha256(exact_segment.encode()).hexdigest() == function["source_segment_sha256"]
    parsed = ast.parse(Path(upstream.__file__).read_text())
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(parsed))
    assert {node.name for node in parsed.body if isinstance(node, ast.FunctionDef)} == {
        "generate_random_graph", "verify_graph_coloring_solution", "greedy_graph_coloring"}
