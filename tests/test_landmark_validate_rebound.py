"""Source/mock tests for the versioned rebound E8 validator. FAKE runners only; sandbox.run_program is poisoned."""
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import grade, sandbox  # noqa: E402
from experiments.landmark import validate_rebound_references as V  # noqa: E402

SPECS = ROOT / "experiments/landmark/dev_release_v1c/private_specs.jsonl"
TASKS = ROOT / "experiments/landmark/dev_release_v1c/tasks.jsonl"
SHA = hashlib.sha256(SPECS.read_bytes()).hexdigest()
FAKE_ATT = {"schema_version": "landmark-containment-v1", "passed": True, "checked_at": "2026-09-21T00:00:00+00:00",
            "binding": {"fake": True}, "script_sha256": "0" * 64, "checks": [{"name": "fake", "passed": True}]}


def _specs():
    return [json.loads(l) for l in SPECS.read_text().splitlines()]


REF_BODIES = [ast.unparse(ast.parse(s["reference_code"])) for s in _specs()]


class FakeRunner:
    """Pass iff the program embeds a frozen reference body; never executes anything."""
    FAKE_RUNNER = True

    def __init__(self, raise_at=None):
        self.calls, self.raise_at = [], raise_at

    def __call__(self, program, **kw):
        compile(program, "<fake>", "exec")  # static only
        self.calls.append(program)
        if self.raise_at is not None and len(self.calls) == self.raise_at:
            raise KeyboardInterrupt("simulated interruption mid-run")
        start = re.search(grade.STARTED + r"[0-9a-f]{24}", program).group(0)
        sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
        ok = any(body in program for body in REF_BODIES)
        return {"stdout": start + "\n", "stdout_tail": sentinel + "\n" if ok else "", "stderr": "", "timed_out": False,
                "returncode": 0 if ok else 1, "passed": ok, "executed": True, "sandbox_kind": "seatbelt"}


@pytest.fixture(autouse=True)
def _guards(monkeypatch):
    def poisoned(*a, **k):
        raise AssertionError("tests must never reach sandbox.run_program")
    monkeypatch.setattr(sandbox, "run_program", poisoned)
    monkeypatch.setattr(grade, "verify_attestation", lambda p: dict(FAKE_ATT))


@pytest.fixture
def att(tmp_path):
    p = tmp_path / "attestation.json"
    p.write_text(json.dumps(FAKE_ATT))
    return p


def _ledger(out):
    return [json.loads(l) for l in (out / V.LEDGER).read_text().splitlines()]


def test_plan_has_exactly_24_jobs_from_real_v1c_specs_and_no_402_rewrite():
    specs = _specs()
    grade.validate_specs([json.loads(l) for l in TASKS.read_text().splitlines()], specs)
    jobs = V.plan_jobs(specs)
    V.check_plan(jobs)
    assert len(jobs) == 24 and sum(j["kind"] == "reference" for j in jobs) == 7
    j402 = [j for j in jobs if j["root_id"] == "mbpp/402"]
    s402 = next(s for s in specs if s["root_id"] == "mbpp/402")
    assert [j["kind"] for j in j402] == ["reference", "control", "control"]
    assert j402[0]["code"] == s402["reference_code"] and j402[0]["expected_outcome"] == 1
    src = Path(V.__file__).read_text()
    body = src.split('"""', 2)[2]  # no root-specific logic or repair rewrite outside the docstring
    assert "mbpp" not in body and "repair" not in body.lower() and "replace(" not in body


def test_full_fake_run_24_starts_7_pass_17_fail_and_durable_ledger(tmp_path, att):
    runner = FakeRunner()
    out = tmp_path / "out"
    s = V.run(SPECS, SHA, TASKS, out, att, True, runner=runner)
    assert s["planned_starts"] == 24 and s["actual_starts"] == 24 == len(runner.calls)
    assert (s["passes"], s["fails"], s["matches_expected"]) == (7, 17, True)
    ev = _ledger(out)
    assert ev[0]["event"] == "reserved" and set(ev[0]["source_sha256"]) == {"validator", "grade", "sandbox", "integrity"}
    assert ev[0]["runner"]["qualname"] == "FakeRunner" and ev[0]["attestation"]["verified_fields"]["passed"] is True
    assert [e["event"] for e in ev].count("job_start") == 24 and [e["event"] for e in ev].count("job_result") == 24
    assert [e["event"] for e in ev].count("program_start") == 24 and ev[-1]["event"] == "complete"
    r402 = next(e for e in ev if e["event"] == "job_result" and e["root_id"] == "mbpp/402" and e["kind"] == "reference")
    assert r402["outcome"] == 1 and r402["starts"] == 1
    assert json.loads((out / V.SUMMARY).read_text())["actual_starts"] == 24


def test_all_pass_runner_does_not_match_expected(tmp_path, att):
    class AllPass(FakeRunner):
        def __call__(self, program, **kw):
            r = super().__call__(program, **kw)
            sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
            return {**r, "passed": True, "returncode": 0, "stdout_tail": sentinel + "\n"}
    s = V.run(SPECS, SHA, TASKS, tmp_path / "o", att, True, runner=AllPass())
    assert s["passes"] == 24 and s["matches_expected"] is False


def test_ledger_durable_when_runner_raises_midway(tmp_path, att):
    runner = FakeRunner(raise_at=5)
    out = tmp_path / "out"
    with pytest.raises(KeyboardInterrupt):
        V.run(SPECS, SHA, TASKS, out, att, True, runner=runner)
    ev = _ledger(out)
    assert ev[-1]["event"] == "INCOMPLETE" and ev[-1]["actual_starts"] == 5 and ev[-1]["jobs_completed"] == 4
    assert [e["event"] for e in ev].count("program_start") == 5
    assert not (out / V.SUMMARY).exists()
    with pytest.raises(FileExistsError):  # no rerun into the same directory, ledger kept
        V.run(SPECS, SHA, TASKS, out, att, True, runner=FakeRunner())
    assert _ledger(out) == ev


def test_refuses_without_real(tmp_path, att):
    with pytest.raises(PermissionError):
        V.run(SPECS, SHA, TASKS, tmp_path / "o", att, False, runner=FakeRunner())
    assert not (tmp_path / "o").exists()


def test_attestation_verified_first(tmp_path, att, monkeypatch):
    def bad(p):
        raise ValueError("Containment attestation did not pass")
    monkeypatch.setattr(grade, "verify_attestation", bad)
    with pytest.raises(ValueError, match="Containment"):  # even with a wrong sha, attestation fails first
        V.run(SPECS, "0" * 64, TASKS, tmp_path / "o", att, True, runner=FakeRunner())
    assert not (tmp_path / "o").exists()


def test_refuses_sha_mismatch(tmp_path, att):
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        V.run(SPECS, "0" * 64, TASKS, tmp_path / "o", att, True, runner=FakeRunner())
    assert not (tmp_path / "o").exists()


def test_refuses_validate_specs_failure(tmp_path, att):
    tasks = TASKS.read_text().splitlines()
    t = tmp_path / "tasks.jsonl"
    t.write_text("\n".join(tasks[:-1]) + "\n")
    with pytest.raises(ValueError, match="exactly the declared public roots"):
        V.run(SPECS, SHA, t, tmp_path / "o", att, True, runner=FakeRunner())
    assert not (tmp_path / "o").exists()


def test_refuses_existing_out(tmp_path, att):
    (tmp_path / "o").mkdir()
    runner = FakeRunner()
    with pytest.raises(FileExistsError):
        V.run(SPECS, SHA, TASKS, tmp_path / "o", att, True, runner=runner)
    assert runner.calls == [] and list((tmp_path / "o").iterdir()) == []


def test_refuses_job_count_not_24(tmp_path, att, monkeypatch):
    specs = _specs()
    specs[0]["negative_controls"].append(dict(specs[0]["negative_controls"][0], rationale="extra control"))
    specs[0]["negative_controls"][-1]["code"] += "\n# extra"
    p = tmp_path / "specs.jsonl"
    p.write_text("".join(json.dumps(s) + "\n" for s in specs))
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="exactly 24"):
        V.run(p, sha, TASKS, tmp_path / "o", att, True, runner=FakeRunner())
    assert not (tmp_path / "o").exists()


def test_refuses_undeclared_runner(tmp_path, att):
    with pytest.raises(ValueError, match="FAKE_RUNNER"):
        V.run(SPECS, SHA, TASKS, tmp_path / "o", att, True, runner=lambda program, **kw: {})


def test_cli_requires_real(tmp_path, att, capsys):
    with pytest.raises(PermissionError):
        V.main(["--specs", str(SPECS), "--specs-sha256", SHA, "--tasks", str(TASKS), "--out", str(tmp_path / "o"),
                "--attestation", str(att)])
