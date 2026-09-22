"""Static source/JSON fixtures only; no candidate compilation or execution."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("e11_mechanism_analysis", ROOT / "scripts/e11_mechanism_analysis.py")
mechanism = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mechanism)

GOOD = "def f(x):\n    return x + 1\n"


def row(output, replicate=0, tokens=3, root="r"):
    return {"root_id": root, "arm": "S1", "replicate": replicate,
            "output": output, "completion_tokens": tokens}


def analyze(outputs, initial=GOOD):
    return mechanism.analyze_records([{"root_id": "r", "output": initial}], outputs, {})


def test_tristate_partition_and_unknown_tokens():
    result = analyze([row(GOOD, 0, 5), row("def f(x):\n    return x + 2\n", 1, 0),
                      row("```python\nx=1\n```\n```python\nx=2\n```", 2, None),
                      row("def f(:\n", 3, None)])
    assert [r["same_function_as_initial"] for r in result["detail"]] == [True, False, None, None]
    a = result["per_arm"]["S1"]
    assert (a["n"], a["assessable_same"], a["assessable_changed"], a["unassessable"]) == (4, 1, 1, 2)
    assert a["same_function_as_initial"] == a["assessable_same"]
    assert a["completion_tokens_known_sum"] == 5
    assert a["completion_tokens_unknown_count"] == 2
    assert a["extract_or_parse_fail"] == 2
    assert "completion_tokens" not in a  # an unqualified total must not silently imply full observation


@pytest.mark.parametrize("output", [None, 7, {}, "def f(:\n"])
def test_unassessable_initial_is_not_a_changed_continuation(output):
    result = analyze([row(GOOD)], initial=output)
    assert result["detail"][0]["same_function_as_initial"] is None
    assert result["per_arm"]["S1"]["assessable_changed"] == 0
    assert result["per_arm"]["S1"]["unassessable"] == 1


@pytest.mark.parametrize("output", [None, 7, {}])
def test_absent_or_nonstring_output_has_unknown_fence_count(output):
    detail = analyze([row(output)])["detail"][0]
    assert detail["same_function_as_initial"] is None
    assert detail["fence_markers"] is None


def test_missing_fields_and_initial_record_are_unassessable():
    result = mechanism.analyze_records([], [{"root_id": "r", "arm": "S1", "replicate": 0}], {})
    d = result["detail"][0]
    assert d["same_function_as_initial"] is None
    assert d["initial_format"] == "missing_initial_record"
    assert d["completion_tokens"] is None and d["fence_markers"] is None
    assert result["per_arm"]["S1"]["completion_tokens_unknown_count"] == 1


def test_identity_is_all_function_definitions_not_semantic_equivalence():
    result = analyze([row("import math\n" + GOOD, 0), row(GOOD + GOOD, 1),
                      row(GOOD + "\ndef helper():\n    return 0\n", 2),
                      row(GOOD + "\nassert f(1) == 2\n", 3)])
    assert [r["same_function_as_initial"] for r in result["detail"]] == [True, False, False, True]
    assert result["per_arm"]["S1"]["extra_toplevel_code"] == 1
    assert "not semantic equivalence" in mechanism.METRIC_DEFINITIONS["identity"]


def test_empty_function_lists_do_not_establish_function_identity():
    result = analyze([row("f = lambda x: x+1")], initial="f = lambda x: x+1")
    assert result["detail"][0]["same_function_as_initial"] is None


@pytest.mark.parametrize("tokens", [-1, True, 1.5, "3"])
def test_invalid_token_measurements_are_not_silently_coerced(tokens):
    with pytest.raises(ValueError, match="completion_tokens"):
        analyze([row(GOOD, tokens=tokens)])


def test_synthetic_cli_preserves_inputs_and_binds_source_provenance(tmp_path):
    run = tmp_path / "run"
    records = {"A/calls.jsonl": [{"root_id": "r", "output": GOOD}],
               "C/calls.jsonl": [row(GOOD, tokens=None)],
               "D/grades.jsonl": [{"root_id": "r", "arm": "S1", "replicate": 0, "outcome": None}]}
    original = {}
    for name, rows in records.items():
        path = run / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        original[name] = path.read_bytes()
    output = tmp_path / "result.json"
    mechanism.main(["--run", str(run), "--out", str(output)])
    result = json.loads(output.read_text())
    assert result["analysis_version"] == "e11-mechanism-static-v2-tristate"
    assert result["detail"][0]["grade"] is None
    assert result["per_arm"]["S1"]["completion_tokens_unknown_count"] == 1
    assert result["inputs"] == {k: hashlib.sha256(v).hexdigest() for k, v in original.items()}
    provenance = result["provenance"]
    assert provenance["script"]["sha256"] == hashlib.sha256(Path(mechanism.__file__).read_bytes()).hexdigest()
    extractor = provenance["extract_code"]
    assert extractor["module_path"] == "experiments/landmark/grade.py"
    assert extractor["module_sha256"] == hashlib.sha256((ROOT / extractor["module_path"]).read_bytes()).hexdigest()
    with pytest.raises(SystemExit, match="overwrite"):
        mechanism.main(["--run", str(run), "--out", str(output)])
    assert all((run / k).read_bytes() == v for k, v in original.items())
