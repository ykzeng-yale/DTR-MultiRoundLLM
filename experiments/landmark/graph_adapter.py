"""Bounded data-only measurement adapter for the separate graph extension.

The response is parsed as JSON, never evaluated as Python. A complete public
constraint verifier differs from the incomplete public tests of the coding track.
Only the three attributed pure functions are imported; not Reasoning Gym itself.
"""

import json
import math
from random import Random

from .vendor.reasoning_gym_graph_color import (
    generate_random_graph,
    greedy_graph_coloring,
    verify_graph_coloring_solution,
)

MAX_VERTICES = 128
MAX_COLORS = 128
MAX_ATTEMPTS = 128
MAX_RESPONSE_BYTES = 16384
MAX_JSON_DEPTH = 8
MAX_DIAGNOSTIC_EDGES = 16


def _integer(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")


def validate_puzzle(puzzle):
    """Reject malformed trusted inputs rather than assigning a receiver failure.

    Preserve vertex order: it is part of the frozen greedy acceptance rule.
    Undirected edges have canonical ascending endpoints and no duplicates.
    Private/reference metadata is outside this strict puzzle schema.
    """
    required = {"vertices", "edges", "color_options"}
    if type(puzzle) is not dict or not required <= puzzle.keys() or puzzle.keys() - required - {"num_colors"}:
        raise ValueError("puzzle must contain only vertices, edges, color_options and optional num_colors")
    vertices = puzzle["vertices"]
    if type(vertices) is not list or not 1 <= len(vertices) <= MAX_VERTICES:
        raise ValueError("vertices must be a nonempty bounded list")
    for vertex in vertices:
        _integer(vertex, "vertex", 0, 2**31 - 1)
    if len(set(vertices)) != len(vertices):
        raise ValueError("vertices must be distinct")
    colors = puzzle["color_options"]
    if type(colors) is not list or not 1 <= len(colors) <= MAX_COLORS:
        raise ValueError("color_options must be a nonempty bounded list")
    for color in colors:
        _integer(color, "color", 1, MAX_COLORS)
    if len(set(colors)) != len(colors):
        raise ValueError("color_options must be distinct")
    if "num_colors" in puzzle:
        _integer(puzzle["num_colors"], "num_colors", 1, MAX_COLORS)
        if puzzle["num_colors"] != len(colors):
            raise ValueError("num_colors disagrees with color_options")
    edges = puzzle["edges"]
    if type(edges) is not list or len(edges) > len(vertices) * (len(vertices) - 1) // 2:
        raise ValueError("edges must be a bounded list")
    vertex_set = set(vertices)
    seen = set()
    for edge in edges:
        if type(edge) not in (list, tuple) or len(edge) != 2 or any(type(v) is not int for v in edge):
            raise ValueError("each edge must have exactly two integer endpoints")
        u, v = edge
        if u not in vertex_set or v not in vertex_set or u >= v or (u, v) in seen:
            raise ValueError("edges must have declared, distinct, ascending endpoints and no duplicates")
        seen.add((u, v))


def _result(score, code, **details):
    return {"status": "missing" if score is None else "observed", "score": score,
            "diagnostic": {"code": code, **details}}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("nonstandard JSON numeric constant")


def _bounded_int(value):
    # Valid colors are small; avoid constructing arbitrarily large integers.
    if len(value) > 20:
        raise ValueError("JSON integer exceeds representation bound")
    return int(value)


def _depth_within_bound(text):
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                return False
        elif character in "]}":
            depth -= 1
    # Syntax, balance, and trailing text are checked by json.loads.
    return True


def grade_response(puzzle, response, max_response_bytes=MAX_RESPONSE_BYTES):
    """Return binary public-constraint quality, preserving truly absent outputs.

    Produced malformed strings are zero under the declared strict format.
    A non-string, non-None API argument is a caller error, not a receiver failure.
    Diagnostics use public puzzle/response data only, never a reference coloring.
    """
    validate_puzzle(puzzle)
    _integer(max_response_bytes, "max_response_bytes", 1, MAX_RESPONSE_BYTES)
    if response is None:
        return _result(None, "missing_output")
    if type(response) is not str:
        raise ValueError("response must be a produced string or None")
    # Every Unicode character needs at least one UTF-8 byte. Check length before
    # encoding so an oversized supplied object does not cause a second large copy.
    if len(response) > max_response_bytes:
        return _result(0, "response_too_large")
    try:
        encoded_length = len(response.encode("utf-8"))
    except UnicodeEncodeError:
        return _result(0, "invalid_unicode")
    if encoded_length > max_response_bytes:
        return _result(0, "response_too_large")
    if not _depth_within_bound(response):
        return _result(0, "json_depth_limit")
    try:
        coloring = json.loads(response, object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant, parse_int=_bounded_int)
    except (ValueError, RecursionError):
        return _result(0, "invalid_json")
    if type(coloring) is not dict:
        return _result(0, "expected_json_object")
    expected = {str(vertex) for vertex in puzzle["vertices"]}
    if set(coloring) != expected:
        return _result(0, "vertex_keys_mismatch",
                       missing_vertices=sorted(expected - coloring.keys(), key=int),
                       extra_vertex_count=len(coloring.keys() - expected))
    if any(type(value) is not int for value in coloring.values()):
        return _result(0, "colors_must_be_integers")
    allowed = set(puzzle["color_options"])
    invalid = sorted((vertex for vertex in puzzle["vertices"] if coloring[str(vertex)] not in allowed))
    if invalid:
        return _result(0, "color_out_of_domain", vertices=invalid)
    valid, _message = verify_graph_coloring_solution(puzzle, coloring)
    if valid:
        return _result(1, "valid")
    conflicts = sorted([u, v] for u, v in puzzle["edges"] if coloring[str(u)] == coloring[str(v)])
    if not conflicts:
        # A changed/broken trusted verifier must not masquerade as model error.
        raise RuntimeError("upstream verifier disagrees with the validated graph contract")
    return _result(0, "edge_conflict", conflicting_edges=conflicts[:MAX_DIAGNOSTIC_EDGES],
                   conflict_count=len(conflicts))


def build_public_task(root_id, family_id, puzzle):
    """Render exactly the four public collector fields, without reference data."""
    validate_puzzle(puzzle)
    for name, value in (("root_id", root_id), ("family_id", family_id)):
        if type(value) is not str or not value or len(value) > 256:
            raise ValueError(f"{name} must be a nonempty string of at most 256 characters")
    public = {"vertices": list(puzzle["vertices"]),
              "edges": [list(edge) for edge in puzzle["edges"]],
              "color_options": list(puzzle["color_options"])}
    prompt = (
        "Color every vertex of the undirected graph. Endpoints of each edge must have different colors. "
        "Use only the allowed integer colors. Return exactly one JSON object and no other text or code fence. "
        "The keys must be the canonical decimal strings of all declared vertices, each appearing exactly once; "
        "include no additional keys. Values must be JSON integers: booleans, decimals, exponents, strings, "
        "arrays, and objects are not accepted as colors. Output is limited to 16384 UTF-8 bytes."
    )
    return {"root_id": root_id, "family_id": family_id, "prompt": prompt,
            "public_context": json.dumps(public, sort_keys=True, separators=(",", ":"))}


def generate_root(seed, num_vertices, edge_probability, num_colors, max_attempts):
    """First greedy-accepted draw from one private RNG, or a retained cap failure.

    Greedy rejection does not establish mathematical non-colorability. The
    reference is private grading material, never input to public rendering.
    """
    _integer(seed, "seed", 0, 2**64 - 1)
    _integer(num_vertices, "num_vertices", 1, MAX_VERTICES)
    _integer(num_colors, "num_colors", 1, MAX_COLORS)
    _integer(max_attempts, "max_attempts", 1, MAX_ATTEMPTS)
    if type(edge_probability) not in (int, float) or not 0 <= edge_probability <= 1 or not math.isfinite(edge_probability):
        raise ValueError("edge_probability must be a finite number in [0, 1]")
    rng = Random(seed)
    for attempt in range(1, max_attempts + 1):
        vertices, edges = generate_random_graph(rng, num_vertices, edge_probability)
        puzzle = {"vertices": vertices, "edges": edges, "num_colors": num_colors,
                  "color_options": list(range(1, num_colors + 1))}
        validate_puzzle(puzzle)
        reference = greedy_graph_coloring(puzzle)
        if reference is not None:
            if not verify_graph_coloring_solution(puzzle, reference)[0]:
                raise RuntimeError("upstream generator returned an invalid reference")
            return {"status": "generated", "puzzle": puzzle, "reference": reference, "attempts": attempt}
    return {"status": "generation_failed", "puzzle": None, "reference": None,
            "attempts": max_attempts, "reason": "greedy_acceptance_cap_reached"}
