import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collector", ROOT / "experiments" / "collect_ollama.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def config_tasks():
    config = json.loads((ROOT / "experiments" / "collector_config.json").read_text())
    tasks = [json.loads(line) for line in (ROOT / "experiments" / "smoke_tasks.jsonl").read_text().splitlines()]
    return config, tasks


def test_invalid_propensity_and_budget_rejected_before_collection():
    config, tasks = config_tasks()
    config["selection_probabilities"] = [0.1] * 4
    with pytest.raises(ValueError, match="sum to one"):
        collector.validate(config, tasks)
    config["selection_probabilities"] = [0.25] * 4
    config["max_calls"] = 1
    with pytest.raises(ValueError, match="budget"):
        collector.validate(config, tasks)


def test_dry_run_never_calls_network_and_does_not_send_hidden_answers(tmp_path, monkeypatch):
    config, tasks = config_tasks()
    # A distinctive hidden answer must not appear in the model request.
    tasks[0]["answer"] = 7345623456
    monkeypatch.setattr(collector, "request", lambda *a, **k: pytest.fail("Network called in dry run"))
    out = tmp_path / "run"
    manifest = collector.run(config, tasks, out, dry_run=True)
    calls = (out / "calls.jsonl").read_text()
    assert "7345623456" not in calls
    assert manifest["evidence_type"] == "synthetic_smoke"
    assert manifest["realized"]["assigned_tasks"] == 4
    assert manifest["realized"]["attempted_calls"] <= 16
    for line in (out / "trajectories.jsonl").read_text().splitlines():
        row = json.loads(line)
        assert all(step["selected_probability"] == step["selection_probabilities"][step["selected_index"]] for step in row["steps"])


def test_stop_has_no_followup_receiver_call(tmp_path, monkeypatch):
    config, tasks = config_tasks()
    monkeypatch.setattr(collector.random.Random, "choices", lambda *a, **k: [0])
    out = tmp_path / "stop"
    result = collector.run(config, tasks, out, dry_run=True)
    assert result["realized"]["attempted_calls"] == len(tasks)
    rows = [json.loads(x) for x in (out / "trajectories.jsonl").read_text().splitlines()]
    assert all(row["status"] == "stopped" and len(row["steps"]) == 1 for row in rows)


def test_execution_failures_remain_in_denominator(tmp_path, monkeypatch):
    config, tasks = config_tasks()
    def mock_service(base, endpoint, payload=None, timeout=60):
        if endpoint == "/api/tags":
            return {"models": [{"name": config["model"], "digest": "fixed"}]}
        if endpoint in ("/api/version", "/api/show"):
            return {"version": "mock"}
        raise TimeoutError("planned failure")
    monkeypatch.setattr(collector, "request", mock_service)
    out = tmp_path / "failure"
    result = collector.run(config, tasks, out)
    rows = [json.loads(x) for x in (out / "trajectories.jsonl").read_text().splitlines()]
    assert len(rows) == len(tasks)
    assert all(row["status"] == "execution_failure" and row["quality"] == 0 for row in rows)
    assert result["realized"]["failed_tasks"] == len(tasks)
    assert result["realized"]["attempted_calls"] == len(tasks)
    assert result["receiver_digest_unchanged"]


def test_output_directory_is_immutable_and_score_parser_is_strict(tmp_path):
    config, tasks = config_tasks()
    with pytest.raises(FileExistsError):
        collector.run(config, tasks, tmp_path, dry_run=True)
    assert collector.score("FINAL: 45", 45) == 1
    assert collector.score("FINAL: 44\nFINAL: 45", 45) == 0
    assert collector.score("I think 45", 45) == 0


def test_nonfinite_temperature_rejected():
    config, tasks = config_tasks()
    config["temperature"] = float("nan")
    with pytest.raises(ValueError, match="Temperature"):
        collector.validate(config, tasks)
