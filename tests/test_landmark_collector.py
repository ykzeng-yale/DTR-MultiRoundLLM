"""Transport/analysis identities only: no model connection or code execution."""
import copy
import json
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1] / "experiments" / "landmark"
sys.path.insert(0, str(BASE.parents[1]))
from experiments.landmark import collect as landmark
from experiments.landmark import analyze as landmark_analysis


@pytest.fixture
def config():
    return json.loads((BASE / "mock_config.json").read_text())


@pytest.fixture
def tasks():
    return [json.loads(line) for line in (BASE / "mock_tasks.jsonl").read_text().splitlines()]


class DistinctMock(landmark.Mock):
    def __init__(self):
        self.requests = []

    def generate(self, payload, timeout):
        self.requests.append(copy.deepcopy(payload))
        return {"message": {"content": f"mock answer for range {payload['options']['seed']}"}, "done": True,
                "prompt_eval_count": 7, "eval_count": 3}


def roots(path):
    return [json.loads(line) for line in (path / "roots.jsonl").read_text().splitlines()]


def grade_rows(run, config):
    result = []
    for root in roots(run):
        if root["excluded"]:
            continue
        for arm, artifacts in root["arms"].items():
            for artifact in artifacts:
                result.append({"root_id": root["root_id"], "arm": arm, "replicate": artifact["replicate"],
                    "output_sha256": artifact["output_sha256"], "outcome": int(arm == "history_specific_repair"),
                    "missing_reason": None, "grader_id": "mock-fixture-only", "grading_contract_sha256": config["grading_contract_sha256"]})
    return result


def save_grades(path, rows):
    path.write_text("".join(json.dumps(row)+"\n" for row in rows))
    return path


def test_all_branches_restore_prefix_and_restart_discards_answer(tmp_path, config, tasks):
    adapter = DistinctMock()
    result = landmark.run(config, tasks, tmp_path/"run", adapter=adapter)
    assert result["attempted_calls"] == 14
    assert result["reserved_completion_tokens"] == 448
    for root in roots(tmp_path/"run"):
        prefix = root["landmark_prefix"]
        initial = root["initial"]
        assert root["branch_inclusion_probability"] == 1
        assert root["arms"]["stop"][0]["output"] == initial["output"]
        assert landmark.digest(prefix) == root["landmark_prefix_sha256"]
        for arm in landmark.ARMS:
            assert len(root["arms"][arm]) == 2
            for rec in root["arms"][arm]:
                messages = rec["request"]["messages"]
                assert messages == initial["request"]["messages"] if arm == "independent_restart" else messages[:-1] == prefix
        assert len(set(root["seeds"].values())) == 7
        assert root["feedback_feature"] == "loop"


def test_strict_schema_blocks_hidden_fields_before_dispatch(tmp_path, config, tasks):
    tasks[0]["hidden_answer"] = "secret"
    with pytest.raises(ValueError, match="Tasks must contain only"):
        landmark.run(config, tasks, tmp_path/"run")
    assert not (tmp_path/"run").exists()


def test_mock_never_initializes_network_adapter(tmp_path, config, tasks, monkeypatch):
    monkeypatch.setattr(landmark, "Ollama", lambda *_: pytest.fail("network adapter initialized"))
    landmark.run(config, tasks, tmp_path/"run")


def test_family_split_and_prior_seen_root_excludes_entire_family(config, tasks):
    tasks[1]["family_id"] = tasks[0]["family_id"]
    config["prior_seen_root_ids"] = [tasks[0]["root_id"]]
    table = landmark.assignments(tasks, config)
    assert all(row["excluded"] for row in table)
    assert table[0]["split"] == table[1]["split"]
    assert table == landmark.assignments(tasks, config)


@pytest.mark.parametrize("limit,value,expected", [("max_calls", 2, "call_budget_exhausted"), ("max_completion_tokens", 64, "completion_token_budget_exhausted")])
def test_budget_retains_all_assigned_roots_and_branches(tmp_path, config, tasks, limit, value, expected):
    config[limit] = value
    result = landmark.run(config, tasks, tmp_path/"run", adapter=DistinctMock())
    assert result["attempted_calls"] == 2
    data = roots(tmp_path/"run")
    assert len(data) == 2
    assert all(len(r["arms"]) == 4 for r in data)
    assert data[1]["initial"]["missing_reason"] == expected
    report = landmark_analysis.analyze(tmp_path/"run")
    assert report["assigned_roots"] == 2
    assert report["contrasts"]["generic_repair_minus_independent_restart"]["all_assigned_mean_bounds"] == [-1, 1]


def test_server_cap_violation_stops_all_later_dispatch(tmp_path, config, tasks):
    class BadServer(DistinctMock):
        def generate(self, payload, timeout):
            out = super().generate(payload, timeout)
            out["eval_count"] = 33
            return out
    adapter = BadServer()
    result = landmark.run(config, tasks, tmp_path/"run", adapter=adapter)
    assert result["attempted_calls"] == 1
    assert len(adapter.requests) == 1
    assert roots(tmp_path/"run")[1]["initial"]["missing_reason"] == "server_violated_completion_token_cap"


def test_deadline_prevents_later_calls(tmp_path, config, tasks):
    state = [0.0]
    class Slow(DistinctMock):
        def generate(self, payload, timeout):
            assert 0 < timeout <= 1
            state[0] = 2.0
            return super().generate(payload, timeout)
    config["max_seconds"] = 1
    result = landmark.run(config, tasks, tmp_path/"run", adapter=Slow(), clock=lambda: state[0])
    assert result["attempted_calls"] == 1
    assert roots(tmp_path/"run")[1]["initial"]["missing_reason"] == "time_budget_exhausted"


def test_failed_initial_retained_with_unknown_usage(tmp_path, config, tasks):
    class Failing(landmark.Mock):
        def generate(self, payload, timeout):
            raise TimeoutError("test failure")
    result = landmark.run(config, tasks, tmp_path/"run", adapter=Failing())
    assert result["attempted_calls"] == 2
    assert result["attempted_calls_with_unknown_usage"] == 2
    assert all(r["status"] == "initial_failed" for r in roots(tmp_path/"run"))


def test_real_placeholders_fail_before_output_or_connection(tmp_path, config, tasks):
    with pytest.raises(ValueError, match="frozen model_digest"):
        landmark.run(config, tasks, tmp_path/"run", real=True)
    assert not (tmp_path/"run").exists()


def test_existing_run_is_never_overwritten(tmp_path, config, tasks):
    landmark.run(config, tasks, tmp_path/"run")
    before = (tmp_path/"run"/"manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        landmark.run(config, tasks, tmp_path/"run")
    assert (tmp_path/"run"/"manifest.json").read_bytes() == before


def test_ungraded_outputs_get_bounds_not_scores(tmp_path, config, tasks):
    landmark.run(config, tasks, tmp_path/"run")
    report = landmark_analysis.analyze(tmp_path/"run")
    for arm in landmark_analysis.ALL_ARMS:
        assert report["quality"][arm]["observed"]["mean"] is None
        assert report["quality"][arm]["observed"]["ci95"] is None
        assert report["quality"][arm]["all_assigned_mean_bounds"] == [0, 1]


def test_partial_replicates_preserve_all_root_bounds_no_single_pair_ci(tmp_path, config, tasks):
    landmark.run(config, tasks, tmp_path/"run", adapter=DistinctMock())
    rows = grade_rows(tmp_path/"run", config)
    rows = [r for r in rows if (r["root_id"], r["arm"], r["replicate"]) != ("mock-a", "history_specific_repair", 1)]
    report = landmark_analysis.analyze(tmp_path/"run", save_grades(tmp_path/"grades.jsonl", rows))
    result = report["contrasts"]["history_specific_repair_minus_generic_repair"]
    assert result["complete_pairs"]["n_roots"] == 1
    assert result["complete_pairs"]["ci95"] is None
    assert result["all_assigned_mean_bounds"] == [.75, 1]


def test_replicates_do_not_inflate_roots_and_family_ci_requires_two_clusters(tmp_path, config, tasks):
    tasks[1]["family_id"] = tasks[0]["family_id"]
    landmark.run(config, tasks, tmp_path/"run", adapter=DistinctMock())
    report = landmark_analysis.analyze(tmp_path/"run", save_grades(tmp_path/"grades.jsonl", grade_rows(tmp_path/"run", config)))
    paired = report["contrasts"]["history_specific_repair_minus_generic_repair"]["complete_pairs"]
    assert paired["n_roots"] == 2 and paired["n_families"] == 1
    assert paired["mean"] == 1 and paired["ci95"] is None
    assert report["realized_cost"]["generic_repair"]["attempted_calls"]["mean_observed"] == 2
    assert report["actual_collection_cost"]["attempted_calls"] == 14


@pytest.mark.parametrize("defect", ["hash", "duplicate", "replicate", "contract"])
def test_grade_binding_rejects_invalid_rows(tmp_path, config, tasks, defect):
    landmark.run(config, tasks, tmp_path/"run", adapter=DistinctMock())
    rows = grade_rows(tmp_path/"run", config)
    if defect == "hash": rows[0]["output_sha256"] = "wrong"
    if defect == "duplicate": rows.append(rows[0])
    if defect == "replicate": rows[0]["replicate"] = 9
    if defect == "contract": rows[0]["grading_contract_sha256"] = "wrong"
    with pytest.raises(ValueError):
        landmark_analysis.analyze(tmp_path/"run", save_grades(tmp_path/"grades.jsonl", rows))


def test_mutated_collection_is_rejected(tmp_path, config, tasks):
    landmark.run(config, tasks, tmp_path/"run")
    with (tmp_path/"run"/"roots.jsonl").open("a") as f:
        f.write("\n")
    with pytest.raises(ValueError, match="checksum"):
        landmark_analysis.analyze(tmp_path/"run")


def test_runtime_head_freeze_checks_committed_bytes_without_self_reference(tmp_path, config, tasks, monkeypatch):
    code = tmp_path/"collect.py"
    code.write_text("# frozen code\n")
    cfg = tmp_path/"config.json"
    cfg.write_text(json.dumps(config))
    dataset = tmp_path/"tasks.jsonl"
    dataset.write_text("".join(json.dumps(t)+"\n" for t in tasks))
    snapshot = {p.name: p.read_bytes() for p in (code, cfg, dataset)}
    monkeypatch.setattr(landmark, "HERE", tmp_path)
    def fake_git(args, **kwargs):
        if args[1:3] == ["rev-parse", "--show-toplevel"]: return str(tmp_path)+"\n"
        if args[1:3] == ["rev-parse", "HEAD"]: return "a"*40+"\n"
        if args[1] == "show": return snapshot[args[2].split(":", 1)[1]]
        pytest.fail(str(args))
    monkeypatch.setattr(landmark.subprocess, "check_output", fake_git)
    assert landmark.verify_freeze(config, tasks, cfg, dataset)["resolved_commit"] == "a"*40
    code.write_text("# changed\n")
    with pytest.raises(ValueError, match="differs from freeze"):
        landmark.verify_freeze(config, tasks, cfg, dataset)
