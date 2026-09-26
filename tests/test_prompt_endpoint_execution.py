"""MRL-34 mocked tests for the endpoint audit adapter (LEAD-ENDPOINT-03). Synthetic packages and fake runners only: no
sandbox, candidate, reference, control or model program is launched; fake runners return canned dictionaries and never
run the program text they receive."""
import ast
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from experiments.prompt_choice import endpoint_audit as ea

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("run_policy_endpoint_audit", ROOT / "scripts/run_policy_endpoint_audit.py")
ad = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ad)

SYN = {
    877: {"text": "SYNTHETIC FIXTURE: order the letters.", "code": "def sort_String(str):\n    return ''.join(sorted(str))",
          "task_id": 877, "test_setup_code": "",
          "test_list": ['assert sort_String("ba") == "ab"', 'assert sort_String("dc") == "cd"', 'assert sort_String("fe") == "ef"'],
          "challenge_test_list": []},
    345: {"text": "SYNTHETIC FIXTURE: pair differences.", "code": "def diff_consecutivenums(nums):\n    return nums[1:]",
          "task_id": 345, "test_setup_code": "",
          "test_list": ["assert diff_consecutivenums([1, 2]) == [1]", "assert diff_consecutivenums([3, 5, 4]) == [2, -1]",
                        "assert diff_consecutivenums([0, 7]) == [7]"],
          "challenge_test_list": []},
}


@pytest.fixture
def package(tmp_path):
    path = tmp_path / "syn.jsonl"
    data = ("\n".join(json.dumps(SYN[r]) for r in (345, 877)) + "\n").encode()
    path.write_bytes(data)
    pins = {r: {"entry_point": ea.RECORD_PINS[r]["entry_point"], "text_sha256": ea.raw_sha256(SYN[r]["text"]),
                "reference_sha256": ea.raw_sha256(SYN[r]["code"]),
                "assertion_sha256": tuple(ea.raw_sha256(t) for t in SYN[r]["test_list"])} for r in ea.ROOTS}
    return ea._build_synthetic_for_tests(path, hashlib.sha256(data).hexdigest(), pins)


def private_runner(outcomes):
    """Fake runner: returns a canned grader result per call from `outcomes` (1 pass, 0 fail); public calls get no output
    (so check_artifact reports unavailable). It never executes the program text."""
    calls = []

    def run(program, **kw):
        calls.append(kw)
        start = re.search(r"__LANDMARK_GRADER_STARTED__[0-9a-f]{24}", program)
        if start is None:  # a public diagnostic harness
            return {"stdout": "", "returncode": 0, "timed_out": False}
        sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
        ok = outcomes.pop(0) if outcomes else 1
        return {"stdout": start.group(0) + "\n", "stdout_tail": sentinel if ok else "AssertionError", "timed_out": False,
                "returncode": 0 if ok else 1, "sandbox_kind": "seatbelt", "passed": bool(ok), "executed": True, "seconds": 0.01}
    run.calls = calls
    return run


def test_exact_36_slot_order_and_distinct_battery_specs(package):
    slots = ad.slot_plan(package)
    assert len(slots) == 36 and [s["slot_index"] for s in slots] == list(range(36))
    assert [s["check"] for s in slots[:3]] == ["public", "original_private", "supplement_v1"]
    assert [s["task_id"] for s in slots[::18]] == ["mbpp/877", "mbpp/345"]
    kinds = [s["artifact_kind"] for s in slots[::3]]
    assert kinds[:6] == ["reference", *ea.CONTROL_ORDER[877]] and kinds[6:] == ["reference", *ea.CONTROL_ORDER[345]]
    assert sum(s["check"] == "public" for s in slots) == 12 and sum(s["check"] != "public" for s in slots) == 24
    for pub, priv in zip(package["public_records"], package["private_records"]):
        task, specs = ad.task_and_specs(pub, priv)
        assert set(specs) == {"original_private", "supplement_v1"}
        assert specs["original_private"]["private_assertions"] != specs["supplement_v1"]["private_assertions"]
        assert specs["original_private"]["public_assertions"] == [pub["public_assertion"]["text"]]
        assert specs["original_private"]["preamble"] == [] and len(specs["supplement_v1"]["negative_controls"]) == 5


def test_mock_run_accounts_every_slot_and_keeps_inputs_immutable(package, tmp_path):
    before = copy.deepcopy(package)
    runner = private_runner([])
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", runner, designation=ad.MOCK_DESIGNATION)
    assert package == before
    assert receipt["designation"] == "mock_runner_not_an_audit_result" and receipt["run_status"] == "completed"
    assert receipt["totals"]["slots"] == 36 and receipt["totals"]["sandbox_launch_attempts"] == len(runner.calls) == 36
    lines = [json.loads(x) for x in (tmp_path / "run/slots_private.jsonl").read_text().splitlines()]
    assert [x["event"] for x in lines].count("launch_attempt") == 36 and [x["event"] for x in lines].count("slot") == 36
    pub = [r for r in receipt["slots"] if r["check"] == "public"]
    assert all(r["outcome"] is None and r["public_statuses"] == ["unavailable"] for r in pub)  # unknown, never pass/fail
    assert all(r["outcome"] == 1 for r in receipt["slots"] if r["check"] != "public")
    assert set(receipt["classification"].values().__iter__().__next__()) >= {"verdict"}
    assert json.loads((tmp_path / "run/start_manifest.json").read_text())["slots"] == ad.slot_plan(package)


def rec(task, artifact, kind, check, outcome):
    return {"task_id": task, "artifact_id": artifact, "artifact_kind": kind, "check": check, "outcome": outcome}


@pytest.mark.parametrize("kind,outcomes,verdict", [
    ("reference", (1, 1, 1), "confirmed"), ("reference", (1, 1, 0), "contradicted"), ("reference", (None, 1, 1), "unknown"),
    ("reference", (None, 0, None), "contradicted"),
    ("lookup_original_examples", (1, 1, 0), "confirmed"), ("lookup_original_examples", (1, 1, 1), "contradicted"),
    ("lookup_original_examples", (None, 1, 0), "unknown"), ("lookup_original_examples", (1, None, 0), "unknown"),
    ("reverse_input", (None, 0, None), "confirmed"), ("reverse_input", (1, 1, 0), "contradicted"),
    ("reverse_input", (1, None, 0), "unknown"),
])
def test_prediction_classification_never_turns_unknown_into_pass_or_fail(kind, outcomes, verdict):
    rows = [rec("mbpp/877", "a", kind, c, o) for c, o in zip(ad.CHECKS, outcomes)]
    assert ad.classify(rows)["mbpp/877|a"]["verdict"] == verdict


@pytest.mark.parametrize("statuses,want", [(["pass"], 1), (["wrong_value"], 0), (["format_error"], 0), (["timeout"], None),
                                           (["unavailable"], None), (["output_limit"], None), ([], None)])
def test_public_outcome_mapping(statuses, want):
    assert ad.public_outcome([{"status": s} for s in statuses]) == want


def test_time_cap_retains_every_unattempted_slot(package, tmp_path):
    ticks = iter(range(0, 10_000, 40))  # each clock read advances 40 s: the 180 s budget runs out after a few slots
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION,
                           clock=lambda: next(ticks))
    statuses = [r["status"] for r in receipt["slots"]]
    assert len(statuses) == 36 and "cap_unattempted" in statuses
    first = statuses.index("cap_unattempted")
    assert all(s == "cap_unattempted" for s in statuses[first:]) and receipt["run_status"] == "completed"
    assert receipt["totals"]["sandbox_launch_attempts"] == first


def test_start_cap_retains_every_unattempted_slot(package, tmp_path):
    limits = dict(ad.LIMITS, max_sandbox_starts=5)
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION,
                           limits=limits)
    assert receipt["totals"]["sandbox_launch_attempts"] == 5
    assert [r["status"] for r in receipt["slots"]][5:] == ["cap_unattempted"] * 31


def test_launch_is_counted_even_when_the_runner_raises(package, tmp_path):
    def boom(program, **kw):
        raise RuntimeError("runner failed")
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", boom, designation=ad.MOCK_DESIGNATION)
    assert receipt["totals"]["sandbox_launch_attempts"] == 36
    assert all(r["launched"] and r["outcome"] is None for r in receipt["slots"])
    assert {r["reason"] for r in receipt["slots"] if r["check"] != "public"} == {"grader_execution_unavailable"}


def test_interrupted_run_writes_an_interrupted_receipt(package, tmp_path):
    calls, base = [], private_runner([])

    def interrupt(program, **kw):
        calls.append(1)
        if len(calls) == 3:
            raise KeyboardInterrupt
        return base(program, **kw)
    with pytest.raises(KeyboardInterrupt):
        ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", interrupt, designation=ad.MOCK_DESIGNATION)
    receipt = json.loads((tmp_path / "run/receipt_private.json").read_text())
    assert receipt["run_status"] == "interrupted:KeyboardInterrupt" and receipt["totals"]["slots"] == 36
    assert receipt["totals"]["sandbox_launch_attempts"] == 3
    statuses = [r["status"] for r in receipt["slots"]]
    assert statuses[2] == "interrupted_result_unknown" and statuses[3:] == ["interrupted_unattempted"] * 33
    assert json.loads((tmp_path / "run/public_projection.json").read_text())["run_status"] == "interrupted:KeyboardInterrupt"


def test_output_is_never_overwritten(package, tmp_path):
    ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION)
    before = {p: p.read_bytes() for p in (tmp_path / "run").iterdir()}
    with pytest.raises(FileExistsError):
        ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION)
    assert {p: p.read_bytes() for p in (tmp_path / "run").iterdir()} == before


def test_public_projection_excludes_private_bodies_expected_values_and_output(package, tmp_path):
    outcomes = [1, 0] * 12
    ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner(outcomes), designation=ad.MOCK_DESIGNATION)
    text = (tmp_path / "run/public_projection.json").read_text()
    projection = json.loads(text)
    secrets_ = []
    for priv in package["private_records"]:
        secrets_ += [priv["reference"]["code"], *[c["code"] for c in priv["controls"]]]
        for b in priv["batteries"].values():
            for c in b["cases"]:
                secrets_ += [c.get("text") or c["assertion_text"], c["expected_literal"]]
    for s in secrets_:
        assert s not in text and json.dumps(s)[1:-1] not in text
    assert "__LANDMARK" not in text and "stdout" not in text and "private_results" not in text
    assert len(projection["slots"]) == 36 and projection["designation"] == ad.MOCK_DESIGNATION
    assert {r["reason"] for r in projection["slots"]} <= ad.EVALUATE_REASONS | {"public_check"}


# ---------------------------------------------------------------- release gates (fake git/binding/attestation)
@pytest.fixture
def work_dir():
    d = ROOT / "work" / f"mrl34_test_{uuid.uuid4().hex}"
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d)


BINDING = {"python_sha256": "0" * 64, "host_sha256": "1" * 64, "profile_sha256": "2" * 64}


def gated(package, work_dir, mutate=None, *, git_blob=True, ancestor=True, attest_ok=True, binding=BINDING, out_exists=False):
    plan = ad.make_plan("synthetic.jsonl", work_dir / "audit_out", package=package, binding=dict(BINDING))
    if mutate:
        mutate(plan)
    if out_exists:
        (work_dir / "audit_out").mkdir()
    path = work_dir / "plan.json"
    path.write_text(json.dumps(plan, sort_keys=True))
    blob = ad.git_blob_sha1(path.read_bytes())

    def git(*args):
        if args[0] == "rev-parse":
            return subprocess.CompletedProcess(args, 0, (blob if git_blob else "f" * 40) + "\n", "")
        return subprocess.CompletedProcess(args, 0 if ancestor else 1, "", "")

    def attest(p):
        if not attest_ok:
            raise ValueError("Containment attestation must be from the last 24 hours")
    return lambda commit="a" * 40, allow=True: ad.verify_release(path, commit, "synthetic.jsonl", git=git, binding=binding,
                                                                 attest=attest, package=package, allow_synthetic=allow)


def test_release_gate_passes_only_when_everything_matches(package, work_dir):
    assert gated(package, work_dir)()["status"] == "prepared_not_released"


@pytest.mark.parametrize("case", ["uncommitted_blob", "not_ancestor", "short_commit", "bound_source", "package", "slots",
                                  "binding", "limits", "attestation_sha", "attestation_invalid", "output_exists", "version"])
def test_release_gate_refuses_every_drift_before_any_launch(package, work_dir, case):
    mutate = {"bound_source": lambda p: p["bound_sources"].update({"experiments/landmark/grade.py": "0" * 64}),
              "package": lambda p: p["package"]["public_record_sha256"].update({"mbpp/877": "0" * 64}),
              "slots": lambda p: p["slots"].pop(),
              "limits": lambda p: p["limits"].update(total_elapsed_seconds=999),
              "attestation_sha": lambda p: p["attestation"].update(sha256="0" * 64),
              "version": lambda p: p.update(version="other")}.get(case)
    check = gated(package, work_dir, mutate, git_blob=case != "uncommitted_blob", ancestor=case != "not_ancestor",
                  attest_ok=case != "attestation_invalid", out_exists=case == "output_exists",
                  binding=dict(BINDING, host_sha256="9" * 64) if case == "binding" else BINDING)
    with pytest.raises(ad.ReleaseRefused):
        check("abc123" if case == "short_commit" else "a" * 40)


def test_release_gate_refuses_absent_source(work_dir, package):
    plan = ad.make_plan("synthetic.jsonl", work_dir / "o", package=package, binding=BINDING)
    path = work_dir / "plan.json"
    path.write_text(json.dumps(plan))
    git = lambda *a: subprocess.CompletedProcess(a, 0, ad.git_blob_sha1(path.read_bytes()) if a[0] == "rev-parse" else "", "")
    with pytest.raises(ad.ReleaseRefused, match="source/package"):
        ad.verify_release(path, "a" * 40, work_dir / "absent.jsonl", git=git, binding=BINDING, attest=lambda p: None)


def test_plan_holds_hashes_only_and_binds_every_imported_source(package, work_dir):
    plan = ad.make_plan("synthetic.jsonl", work_dir / "o", package=package, binding=BINDING)
    text = json.dumps(plan)
    for priv in package["private_records"]:
        for body in [priv["reference"]["code"], *[c["code"] for c in priv["controls"]]]:
            assert json.dumps(body)[1:-1] not in text
        for c in priv["batteries"]["original_private"]["cases"]:
            assert json.dumps(c["text"])[1:-1] not in text
    bound = set(plan["bound_sources"])
    assert {"experiments/landmark/grade.py", "experiments/landmark/public_check.py", "experiments/landmark/sandbox.py",
            "experiments/landmark/diagnostic.py", "experiments/landmark/collect.py", "experiments/landmark/analyze.py",
            "experiments/common/integrity.py", "experiments/prompt_choice/endpoint_audit.py", "scripts/run_policy_endpoint_audit.py",
            "experiments/prompt_choice/endpoint_audit_source_v1.json", "experiments/prompt_choice/endpoint_execution_source_v1.json",
            "scripts/check_landmark_sandbox.py"} <= bound
    assert all(plan["bound_sources"][p] == hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in bound)
    assert plan["limits"] == {"max_sandbox_starts": 36, "total_elapsed_seconds": 180, "retained_output_bytes": 8 * 1024 * 1024,
                              "model_calls": 0, "downloads": 0, "paid_spend": 0}


def test_adapter_source_imports_the_sandbox_only_after_the_gates_and_never_executes_code():
    tree = ast.parse((ROOT / "scripts/run_policy_endpoint_audit.py").read_text())
    top = {a.name for n in tree.body if isinstance(n, ast.ImportFrom) for a in n.names}
    assert "sandbox" not in top
    child = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_child")
    lines = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and any(a.name == "sandbox" for a in n.names)]
    inside = [n.lineno for n in ast.walk(child) if isinstance(n, ast.ImportFrom) and any(a.name == "sandbox" for a in n.names)]
    gate = [n.lineno for n in ast.walk(child) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "verify"]
    assert lines == inside and len(lines) == 1 and gate and gate[0] < lines[0]
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    assert not called & {"eval", "exec", "compile", "__import__", "Popen", "system"}


def test_config_mirrors_adapter_and_pins_contract():
    cfg = json.loads((ROOT / "experiments/prompt_choice/endpoint_execution_source_v1.json").read_text())
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "5f5ec8b:docs/policy_endpoint_execution_contract_20260926.md"],
                          capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == cfg["lead_contract"]["sha256"]
    assert cfg["version"] == ad.VERSION and cfg["execution_released"] is False and cfg["runs_authorized"] == 0
    assert cfg["package_identities"] == ad.PACKAGE_IDENTITIES and cfg["future_run_limits"] == ad.LIMITS
    assert cfg["planned_slots"] == 36 and cfg["predictions"] == ad.PREDICTIONS
    assert {k: v for k, v in cfg["supervisor"].items() if k != "kind"} == ad.SUPERVISOR
    assert cfg["retained_bytes_rule"]["worst_slot_bytes"] == ad.WORST_SLOT_BYTES
    review = (ROOT / "docs/policy_endpoint_source_review_20260926.md").read_text()
    for h in [*ad.PACKAGE_IDENTITIES["public_record_sha256"].values(), *ad.PACKAGE_IDENTITIES["private_record_sha256"].values(),
              ad.PACKAGE_IDENTITIES["builder_sha256"], ad.PACKAGE_IDENTITIES["config_sha256"]]:
        assert h in review


# ---------------------------------------------------------------- MRL-34-R1 regressions
@pytest.mark.parametrize("case", ["extra_field", "predictions", "supervisor", "source_path", "per_call", "retained_rule"])
def test_r1_whole_canonical_plan_is_validated(package, work_dir, case):
    mutate = {"extra_field": lambda p: p.update(note="committed metadata is not its own proof"),
              "predictions": lambda p: p["predictions"].update(reference="anything"),
              "supervisor": lambda p: p["supervisor"].update(total_seconds=900),
              "source_path": lambda p: p["source"].update(path="other.jsonl"),
              "per_call": lambda p: p["per_call_bound_seconds"].update(public=1),
              "retained_rule": lambda p: p["retained_bytes_rule"].update(worst_slot_bytes=1)}[case]
    with pytest.raises(ad.ReleaseRefused):
        gated(package, work_dir, mutate)()


def test_r1_synthetic_package_and_output_outside_work_are_refused(package, work_dir, tmp_path):
    with pytest.raises(ad.ReleaseRefused, match="production"):
        gated(package, work_dir)(allow=False)
    with pytest.raises(ad.ReleaseRefused, match="inside work"):
        gated(package, work_dir, lambda p: p.update(output_directory=str(tmp_path / "outside")))()


def test_r1_retained_bytes_bound_all_files_and_worst_case_next_slot(package, tmp_path):
    cap = ad.WORST_SLOT_BYTES + ad.FINALIZATION_RESERVE_BYTES + 20_000
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION,
                           limits=dict(ad.LIMITS, retained_output_bytes=cap))
    statuses = [r["status"] for r in receipt["slots"]]
    assert "output_cap_unattempted" in statuses and len(statuses) == 36
    totals = ad.finalize_totals(tmp_path / "run", cap=cap)
    assert totals["within_cap"] and totals["total_bytes"] == sum(f.stat().st_size for f in (tmp_path / "run").iterdir()) <= cap
    ad.run_audit(package, ad.slot_plan(package), tmp_path / "run2", private_runner([]), designation=ad.MOCK_DESIGNATION)
    assert ad.finalize_totals(tmp_path / "run2")["within_cap"]
    stored = json.loads((tmp_path / "run2/receipt_private.json").read_text())
    assert not any(k in r for r in stored["slots"] for k in ad.RAW_FIELDS)  # no raw duplication in the receipt


def test_r1_raw_runner_results_program_hash_and_public_nonce_are_kept_privately(package, tmp_path):
    ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION)
    rows = [json.loads(x) for x in (tmp_path / "run/slots_private.jsonl").read_text().splitlines()]
    public = [r for r in rows if r["event"] == "slot" and r["check"] == "public"]
    assert len(public) == 12
    for r in public:
        assert re.fullmatch(r"[0-9a-f]{32}", r["public_nonce"])
        (call,) = r["private_runner_calls"]
        assert re.fullmatch(r"[0-9a-f]{64}", call["program_sha256"]) and call["result"] == {"stdout": "", "returncode": 0, "timed_out": False}
    private = [r for r in rows if r["event"] == "slot" and r["check"] != "public"]
    assert all(r["private_runner_calls"][0]["result"]["sandbox_kind"] == "seatbelt" for r in private)
    assert not any("private_run" in r for r in rows)  # R2: the raw run is serialized once, not twice
    projection = (tmp_path / "run/public_projection.json").read_text()
    for r in public:
        assert r["public_nonce"] not in projection and r["private_runner_calls"][0]["program_sha256"] not in projection


class FakeChild:
    def __init__(self, waits):
        self.pid, self.waits = 4242, list(waits)

    def wait(self, timeout):
        w = self.waits.pop(0)
        if w is None:
            raise subprocess.TimeoutExpired("child", timeout)
        return w


@pytest.mark.parametrize("waits,group_gone,killed,exit_code,cleanup", [
    ([0], True, False, 0, "confirmed"), ([None, -15], True, True, -15, "confirmed"),
    ([None, None, -9], False, True, -9, "unresolved"), ([None, None, None], False, True, None, "unresolved"),
])
def test_r1_external_supervisor_kills_only_its_owned_group_and_records_observed_cleanup(waits, group_gone, killed, exit_code, cleanup):
    sent, child = [], FakeChild(waits)

    def killpg(pid, sig):
        sent.append((pid, sig))
        if sig == 0 and group_gone:
            raise ProcessLookupError
    started = []
    record = ad.supervise(["child"], 180, popen=lambda cmd, **kw: started.append(kw) or child, killpg=killpg, clock=iter(range(100)).__next__)
    assert started == [{"start_new_session": True}] and all(pid == 4242 for pid, _ in sent)
    assert record["killed_at_deadline"] is killed and record["child_exit"] == exit_code
    assert record["adapter_group_cleanup"].startswith(cleanup)
    assert ad.SUPERVISOR["total_seconds"] == 180 and ad.SUPERVISOR["slot_budget_seconds"] < 180 - ad.SUPERVISOR["kill_reserve_seconds"]


def test_r2_high_escaping_bounded_stream_witness_stays_within_the_cap(package, tmp_path):
    def noisy(program, **kw):  # lead's witness: 60,000-byte streams of an ASCII control byte, authentic markers
        start = re.search(r"__LANDMARK_GRADER_STARTED__[0-9a-f]{24}", program)
        if start is None:
            return {"stdout": "\x01" * 60000, "stderr": "\x01" * 60000, "returncode": 0, "timed_out": False}
        sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
        return {"stdout": start.group(0) + "\n" + "\x01" * 59900, "stderr": "\x01" * 60000, "stdout_tail": sentinel,
                "timed_out": False, "returncode": 0, "sandbox_kind": "seatbelt", "passed": True, "executed": True}
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", noisy, designation=ad.MOCK_DESIGNATION)
    total = sum(f.stat().st_size for f in (tmp_path / "run").iterdir())
    assert total <= ad.LIMITS["retained_output_bytes"] and len(receipt["slots"]) == 36


# ---------------------------------------------------------------- MRL-35 regressions
def _write_log(out, lines):
    out.mkdir()
    (out / "slots_private.jsonl").write_text(lines)


@pytest.mark.parametrize("lines,status", [
    ('{"event": "launch_attempt", "launch_number": 1}\n', "unresolved"),                                   # killed mid-launch
    ('{"event": "launch_attempt", "launch_number": 1}\n{"event": "launch_return", "launch_number": 1, "returned": "raised"}\n', "unresolved"),
    ('{"event": "launch_attempt", "launch_number": 1}\n{"event": "launch_ret', "unresolved"),               # truncated log
    ('{"event": "launch_attempt", "launch_number": 1}\n{"event": "launch_return", "launch_number": 1, "returned": "normal"}\n',
     "confirmed_by_normal_runner_returns"),
])
def test_mrl35_detached_payload_cleanup_needs_completion_evidence(tmp_path, lines, status):
    _write_log(tmp_path / "run", lines)
    assert ad.detached_payload_cleanup(tmp_path / "run")["status"] == status
    assert ad.detached_payload_cleanup(tmp_path / "absent")["status"] == "no_launch_possible"
    (tmp_path / "nolog").mkdir()
    assert ad.detached_payload_cleanup(tmp_path / "nolog")["status"] == "unresolved"


class _Child:
    pid = 5151

    def __init__(self, rc):
        self.rc = rc

    def wait(self, timeout):
        return self.rc


def _supervised(tmp_path, *, group_gone=True, detached="confirmed_by_normal_runner_returns", audit_complete=True, rc=0):
    work = tmp_path / "w"
    work.mkdir(exist_ok=True)
    out = work / "out"
    out.mkdir()
    (out / "receipt_private.json").write_text(json.dumps({"audit_complete": audit_complete}))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"output_directory": str(out)}))

    def killpg(pid, sig):
        assert pid == 5151
        if sig == 0 and group_gone:
            raise ProcessLookupError
    return ad.execute_supervised("src.jsonl", plan, "a" * 40, popen=lambda cmd, **kw: _Child(rc), killpg=killpg,
                                 clock=iter(range(0, 1000, 1)).__next__, detached=lambda o: {"status": detached}), out


def test_mrl35_cli_success_requires_every_piece_of_evidence(tmp_path):
    code, record, totals = _supervised(tmp_path)[0]
    assert code == 0 and record["within_total_deadline"] and totals["within_cap"]


@pytest.mark.parametrize("kw", [dict(group_gone=False), dict(detached="unresolved"), dict(audit_complete=False), dict(rc=4)])
def test_mrl35_cli_is_nonzero_when_cleanup_or_completeness_is_unresolved(tmp_path, kw):
    (code, record, totals), out = _supervised(tmp_path, **kw)
    assert code == 3
    assert json.loads((out / "supervisor.json").read_text())["child_pid"] == 5151


def test_mrl35_final_on_disk_totals_equal_measured_files_including_supervisor_and_itself(tmp_path):
    (code, record, totals), out = _supervised(tmp_path)
    measured = {f.name: f.stat().st_size for f in out.iterdir()}
    assert set(totals["files"]) == set(measured) - {"retained_totals.json"} and "supervisor.json" in totals["files"]
    assert totals["total_bytes"] == sum(measured.values()) and totals["totals_file_bytes"] == measured["retained_totals.json"]
    assert json.loads((out / "retained_totals.json").read_text()) == totals


def test_mrl35_preparation_delay_counts_against_the_total_deadline(package, tmp_path):
    now = [1000.0]
    plan = tmp_path / "plan.json"
    plan.write_text("{}")

    def slow_verify(plan_path, commit, source):
        now[0] += 170.0  # a slow gate: the outer deadline keeps running
        return {"slots": ad.slot_plan(package), "output_directory": str(tmp_path / "run")}
    receipt = ad.run_child("src", plan, "a" * 40, 1000.0 + ad.SUPERVISOR["total_seconds"], clock=lambda: now[0],
                           verify=slow_verify, runner=private_runner([]), build=lambda s: package)
    assert receipt["totals"]["sandbox_launch_attempts"] == 0 and len(receipt["slots"]) == 36
    assert {r["status"] for r in receipt["slots"]} == {"cap_unattempted"} and receipt["audit_complete"] is False


def test_mrl35_raw_omission_marks_the_audit_incomplete_and_stays_within_the_cap(package, tmp_path):
    def oversize(program, **kw):  # outside the sandbox bound on purpose: forces the hard cap path
        start = re.search(r"__LANDMARK_GRADER_STARTED__[0-9a-f]{24}", program)
        if start is None:
            return {"stdout": "\x01" * 400000, "stderr": "", "returncode": 0, "timed_out": False}
        sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
        return {"stdout": start.group(0) + "\n" + "\x01" * 400000, "stderr": "", "stdout_tail": sentinel, "timed_out": False,
                "returncode": 0, "sandbox_kind": "seatbelt", "passed": True, "executed": True}
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", oversize, designation=ad.MOCK_DESIGNATION)
    assert receipt["raw_records_complete"] is False and receipt["audit_complete"] is False and receipt["raw_omitted_slots"]
    rows = [json.loads(x) for x in (tmp_path / "run/slots_private.jsonl").read_text().splitlines()]
    omitted = [r for r in rows if r.get("raw_retained") is False]
    assert omitted and all("private_runner_calls" not in r and r["omitted_raw_digest_sha256"] for r in omitted)
    assert ad.finalize_totals(tmp_path / "run")["within_cap"] and len(receipt["slots"]) == 36
    assert json.loads((tmp_path / "run/public_projection.json").read_text())["audit_complete"] is False


def test_mrl35_finalization_itself_cannot_breach_the_cap(package, tmp_path, monkeypatch):
    monkeypatch.setitem(ad.LIMITS, "retained_output_bytes", 40_000)  # finalization budget smaller than the full receipt
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION,
                           limits=dict(ad.LIMITS, retained_output_bytes=10**9))
    stored = json.loads((tmp_path / "run/receipt_private.json").read_text())
    assert stored["slots_omitted_for_cap"] is True and stored["audit_complete"] is False
    assert len([x for x in (tmp_path / "run/slots_private.jsonl").read_text().splitlines() if '"event": "slot"' in x]) == 36
