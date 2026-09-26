"""MRL-38 mocked tests for the nine-root audit adapter (LEAD-ENDPOINT-08), adapted from the accepted MRL-34/35 tests. Synthetic packages and fake runners only: no
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
import time
import uuid
from pathlib import Path

import pytest

from experiments.prompt_choice import nine_root_endpoint_audit as ea

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("run_nine_root_endpoint_audit", ROOT / "scripts/run_nine_root_endpoint_audit.py")
ad = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ad)

SIG = {356: ("find_angle", ["a", "b"]), 885: ("is_Isomorphic", ["str1", "str2"]), 354: ("tn_ap", ["a", "n", "d"]),
       901: ("smallest_multiple", ["n"]), 654: ("rectangle_perimeter", ["l", "b"]), 703: ("is_key_present", ["d", "x"]),
       700: ("count_range_in_list", ["li", "min", "max"]), 656: ("find_Min_Sum", ["a", "b", "n"]), 36: ("find_Nth_Digit", ["p", "q", "N"])}


def synthetic_jsonl(path):
    rows = []
    for r, (entry, params) in SIG.items():
        tests = [f"assert {entry}({', '.join(str(k + i) for k in range(len(params)))}) == {10 + i}" for i in range(3)]
        rows.append(json.dumps({"text": f"SYNTHETIC FIXTURE {r}", "code": f"def {entry}({','.join(params)}):\n    return 0\n",
                                "task_id": r, "test_setup_code": "", "test_list": tests, "challenge_test_list": []}))
    data = ("\n".join(rows) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def package(tmp_path):
    path = tmp_path / "syn.jsonl"
    return ea._build_synthetic_for_tests(path, synthetic_jsonl(path))


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
    assert len(slots) == 162 and [s["slot_index"] for s in slots] == list(range(162))
    assert [s["check"] for s in slots[:3]] == ["public", "original_private", "supplement_v1"]
    assert [s["task_id"] for s in slots[::18]] == [f"mbpp/{r}" for r in ea.ROOTS]
    kinds = [s["artifact_kind"] for s in slots[::3]]
    assert kinds == ["reference", *ea.CONTROL_KINDS] * 9
    assert sum(s["check"] == "public" for s in slots) == 54 and sum(s["check"] != "public" for s in slots) == 108
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
    assert receipt["totals"]["slots"] == 162 and receipt["totals"]["sandbox_launch_attempts"] == len(runner.calls) == 162
    lines = [json.loads(x) for x in (tmp_path / "run/slots_private.jsonl").read_text().splitlines()]
    assert [x["event"] for x in lines].count("launch_attempt") == 162 and [x["event"] for x in lines].count("slot") == 162
    pub = [r for r in receipt["slots"] if r["check"] == "public"]
    assert all(r["outcome"] is None and r["public_statuses"] == ["unavailable"] for r in pub)  # unknown, never pass/fail
    assert all(r["outcome"] == 1 for r in receipt["slots"] if r["check"] != "public")
    assert all({"batteries", "joint_pass", "public_observed"} <= set(v) for v in receipt["classification"].values())
    assert len(receipt["classification"]) == 54
    assert json.loads((tmp_path / "run/start_manifest.json").read_text())["slots"] == ad.slot_plan(package)


def rec(task, artifact, kind, check, outcome):
    return {"task_id": task, "artifact_id": artifact, "artifact_kind": kind, "check": check, "outcome": outcome}


@pytest.mark.parametrize("pred,outcomes,verdicts,joint", [
    ((True, True), (1, 1, 1), ("confirmed", "confirmed"), 1), ((True, True), (1, 0, 1), ("contradicted", "confirmed"), 0),
    ((True, False), (None, 1, 0), ("confirmed", "confirmed"), 0), ((True, False), (1, 1, 1), ("confirmed", "contradicted"), 1),
    ((True, False), (1, None, 0), ("unknown", "confirmed"), None), ((False, False), (0, 0, None), ("confirmed", "unknown"), None),
])
def test_per_battery_classification_against_package_predictions(pred, outcomes, verdicts, joint):
    rows = [rec("mbpp/885", "a", "wrong_rule_2", c, o) for c, o in zip(ad.CHECKS, outcomes)]
    out = ad.classify(rows, {"mbpp/885|a": {"original_private": pred[0], "supplement_v1": pred[1]}})["mbpp/885|a"]
    assert (out["batteries"]["original_private"]["verdict"], out["batteries"]["supplement_v1"]["verdict"]) == verdicts
    assert out["joint_pass"] == joint and out["public_observed"] == outcomes[0]  # public reported, never predicted


def test_root_specific_predictions_come_from_the_package(package):
    preds = ad.package_predictions(package)
    assert len(preds) == 54
    assert preds["mbpp/885|mbpp/885/control/wrong_rule_2"] == {"original_private": True, "supplement_v1": False}
    assert preds["mbpp/901|mbpp/901/control/wrong_rule_1"] == {"original_private": True, "supplement_v1": False}
    assert preds["mbpp/700|mbpp/700/control/wrong_rule_2"] == {"original_private": True, "supplement_v1": False}
    assert preds["mbpp/356|mbpp/356/control/wrong_rule_1"] == {"original_private": False, "supplement_v1": False}
    assert all(v == {"original_private": True, "supplement_v1": True} for k, v in preds.items() if k.endswith("|reference"))


@pytest.mark.parametrize("statuses,want", [(["pass"], 1), (["wrong_value"], 0), (["format_error"], 0), (["timeout"], None),
                                           (["unavailable"], None), (["output_limit"], None), ([], None)])
def test_public_outcome_mapping(statuses, want):
    assert ad.public_outcome([{"status": s} for s in statuses]) == want


def test_time_cap_retains_every_unattempted_slot(package, tmp_path):
    ticks = iter(range(0, 10_000, 40))  # each clock read advances 40 s: the 180 s budget runs out after a few slots
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION,
                           clock=lambda: next(ticks))
    statuses = [r["status"] for r in receipt["slots"]]
    assert len(statuses) == 162 and "cap_unattempted" in statuses
    first = statuses.index("cap_unattempted")
    assert all(s == "cap_unattempted" for s in statuses[first:]) and receipt["run_status"] == "completed"
    assert receipt["totals"]["sandbox_launch_attempts"] == first


def test_start_cap_retains_every_unattempted_slot(package, tmp_path):
    limits = dict(ad.LIMITS, max_sandbox_starts=5)
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION,
                           limits=limits)
    assert receipt["totals"]["sandbox_launch_attempts"] == 5
    assert [r["status"] for r in receipt["slots"]][5:] == ["cap_unattempted"] * 157


def test_launch_is_counted_even_when_the_runner_raises(package, tmp_path):
    def boom(program, **kw):
        raise RuntimeError("runner failed")
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", boom, designation=ad.MOCK_DESIGNATION)
    assert receipt["totals"]["sandbox_launch_attempts"] == 162
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
    assert receipt["run_status"] == "interrupted:KeyboardInterrupt" and receipt["totals"]["slots"] == 162
    assert receipt["totals"]["sandbox_launch_attempts"] == 3
    statuses = [r["status"] for r in receipt["slots"]]
    assert statuses[2] == "interrupted_result_unknown" and statuses[3:] == ["interrupted_unattempted"] * 159
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
    for s in [x for x in secrets_ if len(x) >= 6]:  # short synthetic literals (e.g. '11') also occur inside hex hashes
        assert s not in text and json.dumps(s)[1:-1] not in text
    assert "__LANDMARK" not in text and "stdout" not in text and "private_results" not in text
    assert len(projection["slots"]) == 162 and projection["designation"] == ad.MOCK_DESIGNATION
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
    plan = ad.make_plan("synthetic.jsonl", work_dir / "audit_out", package=package, binding=dict(BINDING), allow_synthetic=True)
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
    plan = ad.make_plan("synthetic.jsonl", work_dir / "o", package=package, binding=BINDING, allow_synthetic=True)
    path = work_dir / "plan.json"
    path.write_text(json.dumps(plan))
    git = lambda *a: subprocess.CompletedProcess(a, 0, ad.git_blob_sha1(path.read_bytes()) if a[0] == "rev-parse" else "", "")
    with pytest.raises(ad.ReleaseRefused, match="source/package"):
        ad.verify_release(path, "a" * 40, work_dir / "absent.jsonl", git=git, binding=BINDING, attest=lambda p: None)


def test_plan_holds_hashes_only_and_binds_every_imported_source(package, work_dir):
    plan = ad.make_plan("synthetic.jsonl", work_dir / "o", package=package, binding=BINDING, allow_synthetic=True)
    text = json.dumps(plan)
    for priv in package["private_records"]:
        for body in [priv["reference"]["code"], *[c["code"] for c in priv["controls"]]]:
            assert json.dumps(body)[1:-1] not in text
        for c in priv["batteries"]["original_private"]["cases"]:
            assert json.dumps(c["text"])[1:-1] not in text
    bound = set(plan["bound_sources"])
    assert {"experiments/landmark/grade.py", "experiments/landmark/public_check.py", "experiments/landmark/sandbox.py",
            "experiments/landmark/diagnostic.py", "experiments/landmark/collect.py", "experiments/landmark/analyze.py",
            "experiments/common/integrity.py", "experiments/prompt_choice/nine_root_endpoint_audit.py",
            "experiments/prompt_choice/endpoint_audit.py", "scripts/run_nine_root_endpoint_audit.py",
            "experiments/prompt_choice/nine_root_endpoint_source_v1.json",
            "experiments/prompt_choice/nine_root_endpoint_execution_source_v1.json", "scripts/check_landmark_sandbox.py",
            "results/nine_root_measurement_source_review_20260926.json"} <= bound
    assert all(plan["bound_sources"][p] == hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in bound)
    assert plan["limits"] == {"max_sandbox_starts": 162, "total_elapsed_seconds": 600, "retained_output_bytes": 8 * 1024 * 1024,
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
    cfg = json.loads((ROOT / "experiments/prompt_choice/nine_root_endpoint_execution_source_v1.json").read_text())
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "43b6c44:docs/nine_root_measurement_execution_contract_20260926.md"],
                          capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == cfg["lead_contract"]["sha256"]
    assert cfg["version"] == ad.VERSION and cfg["execution_released"] is False and cfg["runs_authorized"] == 0
    assert cfg["package_identities"] == ad.PACKAGE_IDENTITIES and cfg["future_run_limits"] == ad.LIMITS
    assert cfg["planned_slots"] == ad.N_SLOTS == 162 and cfg["planned_artifacts"] == 54
    assert {k: v for k, v in cfg["supervisor"].items() if k != "kind"} == ad.SUPERVISOR
    receipt = json.loads((ROOT / ad.REVIEW_RECEIPT).read_text())
    assert hashlib.sha256((ROOT / ad.REVIEW_RECEIPT).read_bytes()).hexdigest() == ad.REVIEW_RECEIPT_SHA256
    assert {k: receipt["package_identities"][k] for k in ad.PACKAGE_IDENTITIES} == ad.PACKAGE_IDENTITIES


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
    assert "output_cap_unattempted" in statuses and len(statuses) == 162
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
    assert len(public) == 54
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
    assert ad.SUPERVISOR["total_seconds"] == 600 and ad.SUPERVISOR["slot_budget_seconds"] == 580 < 600 - ad.SUPERVISOR["kill_reserve_seconds"]


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
    assert total <= ad.LIMITS["retained_output_bytes"] and len(receipt["slots"]) == 162


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


class _Guard:
    made = []

    def __init__(self, delay):
        self.delay, self.started, self.cancelled = delay, False, False
        _Guard.made.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True


class _Child:
    pid = 5151

    def __init__(self, rc):
        self.rc = rc

    def wait(self, timeout):
        return self.rc


def _supervised(tmp_path, *, group_gone=True, detached="confirmed_by_normal_runner_returns", audit_complete=True, rc=0,
                create_run=True, out=None, clock=None, detached_fn=None):
    work = tmp_path / "w"
    work.mkdir(exist_ok=True)
    out = work / "out" if out is None else out
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"output_directory": str(out)}))

    def popen(cmd, **kw):  # a fake child: when it "runs", it creates the bound run directory with this execution's token
        token = cmd[cmd.index("--run-token") + 1]
        assert "--deadline-monotonic" in cmd
        if create_run:
            out.mkdir()
            (out / "start_manifest.json").write_text(json.dumps({"run_token": token}))
            (out / "receipt_private.json").write_text(json.dumps({"audit_complete": audit_complete}))
        return _Child(rc)

    def killpg(pid, sig):
        assert pid == 5151
        if sig == 0 and group_gone:
            raise ProcessLookupError
    sup = tmp_path / "sup"
    result = ad.execute_supervised("src.jsonl", plan, "a" * 40, popen=popen, killpg=killpg,
                                   clock=clock or iter(range(0, 1000, 1)).__next__,
                                   detached=detached_fn or (lambda o: {"status": detached}), supervisor_root=sup,
                                   watchdog=lambda delay, action: _Guard(delay))
    return result, out, sup


def test_mrl35_cli_success_requires_every_piece_of_evidence(tmp_path):
    (code, record, totals), out, sup = _supervised(tmp_path)
    assert code == 0 and record["run_directory_bound"] and totals["within_total_deadline"] and totals["within_cap"]


@pytest.mark.parametrize("kw", [dict(group_gone=False), dict(detached="unresolved"), dict(audit_complete=False), dict(rc=4)])
def test_mrl35_cli_is_nonzero_when_cleanup_or_completeness_is_unresolved(tmp_path, kw):
    (code, record, totals), out, sup = _supervised(tmp_path, **kw)
    assert code == 3
    (run,) = sup.iterdir()
    assert json.loads((run / "supervisor.json").read_text())["child_pid"] == 5151


def test_mrl35_final_on_disk_totals_equal_measured_files_including_supervisor_and_itself(tmp_path):
    (code, record, totals), out, sup = _supervised(tmp_path)
    (run,) = sup.iterdir()
    measured = {f.name: f.stat().st_size for f in run.iterdir()}
    measured.update({f.as_posix(): f.stat().st_size for f in out.iterdir()})
    assert set(totals["files"]) == set(measured) - {"retained_totals.json"} and "supervisor.json" in totals["files"]
    assert totals["total_bytes"] == sum(measured.values()) and totals["totals_file_bytes"] == measured["retained_totals.json"]
    saved = json.loads((run / "retained_totals.json").read_text())
    assert saved == {k: v for k, v in totals.items() if k not in ("final_elapsed_seconds", "within_total_deadline")}
    assert "within_total_deadline" not in saved  # never claimed on disk before the post-finalizer check


def test_mrl35_r1_lead_refusal_counterexample_never_mutates_an_unverified_existing_directory(tmp_path):
    # The lead's probe: an unverified plan points to an existing directory outside work/, and the child refuses (exit 2).
    existing = tmp_path / "elsewhere"
    existing.mkdir()
    (existing / "original.txt").write_text("original")
    (code, record, totals), out, sup = _supervised(tmp_path, rc=2, create_run=False, out=existing)
    assert code == 3 and sorted(p.name for p in existing.iterdir()) == ["original.txt"]
    assert (existing / "original.txt").read_text() == "original"
    assert record["run_directory_bound"] is False and record["detached_payload_cleanup"]["status"] == "unresolved"
    (run,) = sup.iterdir()
    assert sorted(p.name for p in run.iterdir()) == ["retained_totals.json", "supervisor.json"]


def test_mrl35_r1_replayed_existing_run_is_not_bound_or_mutated(tmp_path):
    old = tmp_path / "w" / "out"
    old.mkdir(parents=True)
    (old / "start_manifest.json").write_text(json.dumps({"run_token": "0" * 32}))
    before = {p.name: p.read_bytes() for p in old.iterdir()}
    (code, record, totals), out, sup = _supervised(tmp_path, rc=0, create_run=False, out=old)
    assert code == 3 and record["run_directory_existed_at_start"] and not record["run_directory_bound"]
    assert {p.name: p.read_bytes() for p in old.iterdir()} == before


def test_mrl35_r1_deadlines_use_the_monotonic_clock():
    import inspect
    for fn in (ad.execute_supervised, ad.supervise, ad.run_child, ad.run_audit):
        assert inspect.signature(fn).parameters["clock"].default is time.monotonic
    tree = ast.parse((ROOT / "scripts/run_policy_endpoint_audit.py").read_text())
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "time"
                and isinstance(n.value, ast.Name) and n.value.id == "time"]


def test_mrl35_r1_finalization_overrun_is_measured_and_never_success(tmp_path):
    now = [0.0]

    def slow_detached(out):  # parent finalization work runs past the total deadline
        now[0] += ad.SUPERVISOR["total_seconds"] + 1
        return {"status": "confirmed_by_normal_runner_returns"}
    (code, record, totals), out, sup = _supervised(tmp_path, clock=lambda: now[0], detached_fn=slow_detached)
    assert code == 3 and totals["within_total_deadline"] is False
    assert totals["final_elapsed_seconds"] > ad.SUPERVISOR["total_seconds"]


def test_mrl35_preparation_delay_counts_against_the_total_deadline(package, tmp_path):
    now = [1000.0]
    plan = tmp_path / "plan.json"
    plan.write_text("{}")

    def slow_verify(plan_path, commit, source):
        now[0] += 590.0  # a slow gate: the outer deadline keeps running
        return {"slots": ad.slot_plan(package), "output_directory": str(tmp_path / "run")}
    receipt = ad.run_child("src", plan, "a" * 40, 1000.0 + ad.SUPERVISOR["total_seconds"], clock=lambda: now[0],
                           verify=slow_verify, runner=private_runner([]), build=lambda s: package)
    assert receipt["totals"]["sandbox_launch_attempts"] == 0 and len(receipt["slots"]) == 162
    assert {r["status"] for r in receipt["slots"]} == {"cap_unattempted"} and receipt["audit_complete"] is False


def test_mrl35_raw_omission_marks_the_audit_incomplete_and_stays_within_the_cap(package, tmp_path):
    def oversize(program, **kw):  # outside the sandbox bound on purpose: forces the hard cap path
        start = re.search(r"__LANDMARK_GRADER_STARTED__[0-9a-f]{24}", program)
        if start is None:
            return {"stdout": "\x01" * 1400000, "stderr": "", "returncode": 0, "timed_out": False}
        sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
        return {"stdout": start.group(0) + "\n" + "\x01" * 1400000, "stderr": "", "stdout_tail": sentinel, "timed_out": False,
                "returncode": 0, "sandbox_kind": "seatbelt", "passed": True, "executed": True}
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", oversize, designation=ad.MOCK_DESIGNATION)
    assert receipt["raw_records_complete"] is False and receipt["audit_complete"] is False and receipt["raw_omitted_slots"]
    rows = [json.loads(x) for x in (tmp_path / "run/slots_private.jsonl").read_text().splitlines()]
    omitted = [r for r in rows if r.get("raw_retained") is False]
    assert omitted and all("private_runner_calls" not in r and r["omitted_raw_digest_sha256"] for r in omitted)
    assert ad.finalize_totals(tmp_path / "run")["within_cap"] and len(receipt["slots"]) == 162
    assert json.loads((tmp_path / "run/public_projection.json").read_text())["audit_complete"] is False


def test_mrl35_finalization_itself_cannot_breach_the_cap(package, tmp_path, monkeypatch):
    monkeypatch.setitem(ad.LIMITS, "retained_output_bytes", 40_000)  # finalization budget smaller than the full receipt
    receipt = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION,
                           limits=dict(ad.LIMITS, retained_output_bytes=10**9))
    stored = json.loads((tmp_path / "run/receipt_private.json").read_text())
    assert stored["slots_omitted_for_cap"] is True and stored["audit_complete"] is False
    assert len([x for x in (tmp_path / "run/slots_private.jsonl").read_text().splitlines() if '"event": "slot"' in x]) == 162


def test_mrl35_r2_lead_slow_finalizer_counterexample_is_never_success(tmp_path, monkeypatch):
    # The lead's probe: the clock advances 181 s inside a wrapper around the real finalize_totals.
    now = [0.0]
    real = ad.finalize_totals

    def slow(*a, **kw):
        result = real(*a, **kw)
        now[0] += 601.0
        return result
    monkeypatch.setattr(ad, "finalize_totals", slow)
    _Guard.made.clear()
    (code, record, totals), out, sup = _supervised(tmp_path, clock=lambda: now[0])
    assert code == 3 and totals["within_total_deadline"] is False and totals["final_elapsed_seconds"] >= 601
    (run,) = sup.iterdir()
    assert "within_total_deadline" not in json.loads((run / "retained_totals.json").read_text())
    (guard,) = _Guard.made
    assert guard.started and guard.cancelled and guard.delay == ad.SUPERVISOR["total_seconds"]


def test_mrl35_r2_watchdog_is_fail_closed_by_default():
    import inspect
    assert inspect.signature(ad.execute_supervised).parameters["watchdog"].default is ad._fail_closed_watchdog
    fired = []
    timer = ad._fail_closed_watchdog(0.01, lambda: fired.append(True))
    assert timer.daemon
    timer.start()
    timer.join(1)
    assert fired == [True]
    src = (ROOT / "scripts/run_policy_endpoint_audit.py").read_text()
    assert "guard = watchdog(max(0.0, deadline - clock()), lambda: os._exit(5))" in src


# ---------------------------------------------------------------- MRL-38 specific refusals and 36-slot regression
@pytest.mark.parametrize("case", ["package_refusal", "synthetic", "changed_control_kind", "wrong_adapted_public", "old_description_field"])
def test_mrl38_package_gate_refuses_before_any_plan_or_dispatch(package, case):
    pkg = copy.deepcopy(package)
    if case == "package_refusal":
        pkg["manifest"]["refusals"] = [{"task_id": "mbpp/901", "refusal": "structure changed"}]
    elif case == "changed_control_kind":
        pkg["private_records"][0]["controls"][0]["kind"] = "reverse_input"
    elif case == "wrong_adapted_public":
        pkg["public_records"][6]["adapted_public_contract"] = "Count integer entries only."
    elif case == "old_description_field":
        pkg["public_records"][0]["description"] = "old two-root field"
    with pytest.raises(ad.ReleaseRefused):
        ad.validate_package(pkg, allow_synthetic=case != "synthetic")


def test_mrl38_obsolete_36_slot_plan_and_old_version_are_refused(package, work_dir):
    with pytest.raises(ad.ReleaseRefused):
        gated(package, work_dir, lambda p: p.update(slots=p["slots"][:36]))()
    with pytest.raises(ad.ReleaseRefused):
        gated(package, work_dir, lambda p: p.update(version="prompt-choice-endpoint-execution-v1"))()


def test_mrl38_a_36_slot_run_is_never_a_complete_162_slot_audit(package, tmp_path):
    receipt = ad.run_audit(package, ad.slot_plan(package)[:36], tmp_path / "run", private_runner([]), designation=ad.MOCK_DESIGNATION)
    assert receipt["run_status"] == "completed" and receipt["totals"]["slots"] == 36 and receipt["audit_complete"] is False
    full = ad.run_audit(package, ad.slot_plan(package), tmp_path / "run2", private_runner([]), designation=ad.MOCK_DESIGNATION)
    assert full["totals"]["slots"] == 162 and full["totals"]["sandbox_launch_attempts"] == 162 and full["audit_complete"] is True


def test_mrl38_old_two_root_adapter_is_unchanged_and_not_imported():
    assert hashlib.sha256((ROOT / "scripts/run_policy_endpoint_audit.py").read_bytes()).hexdigest() == \
        "bd30976a65b1e2728e4038ab5176ebbc63189f3ac8d690c8c95f72aa68ef05a6"
    tree = ast.parse((ROOT / "scripts/run_nine_root_endpoint_audit.py").read_text())
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
               {f"{n.module}.{a.name}" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert not any("run_policy_endpoint_audit" in m or m == "experiments.prompt_choice.endpoint_audit" for m in imported)
    assert "experiments.prompt_choice.nine_root_endpoint_audit" in imported
    assert ad.LIMITS["max_sandbox_starts"] == 162 and ad.LIMITS["total_elapsed_seconds"] == 600 and ad.N_SLOTS == 162


def test_mrl38_plan_names_the_current_decision_and_refuses_synthetic_production_plans(package, work_dir):
    plan = ad.make_plan("synthetic.jsonl", work_dir / "o", package=package, binding=BINDING, allow_synthetic=True)
    assert plan["decision"] == "LEAD-ENDPOINT-08" and plan["contract"] == "docs/nine_root_measurement_execution_contract_20260926.md"
    assert plan["version"] == "prompt-choice-nine-root-execution-v1" and len(plan["slots"]) == 162
    with pytest.raises(ad.ReleaseRefused):  # the production plan path never accepts a synthetic package
        ad.make_plan("synthetic.jsonl", work_dir / "o", package=package, binding=BINDING)
    src = (ROOT / "scripts/run_nine_root_endpoint_audit.py").read_text()
    assert "LEAD-ENDPOINT-03" not in src and "180 s" not in src and "MRL-33 production" not in src
