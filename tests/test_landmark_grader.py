"""Private grading validation with mocked execution; no candidate programs run."""
import copy
import json
from pathlib import Path
import re
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.landmark import collect, grade
from experiments.landmark.analyze import analyze


@pytest.fixture
def fixture_data():
    tasks=[{"root_id":f"test-{i}","family_id":f"family-{i}","prompt":"Implement f(x).","public_context":"The public example is f(0)=1."} for i in range(2)]
    specs=[{"root_id":t["root_id"],"public_task_sha256":collect.digest(t),"entry_point":"f",
            "public_assertions":["assert f(0)==1"],"private_assertions":["assert f(2)==3"],
            "preamble":[],"reference_code":"def f(x):\n    return x+1\n",
            "negative_controls":[{"code":"def f(x):\n    return 0\n","rationale":"Constant zero is wrong for the private input2 whose specified output is3."}]} for t in tasks]
    cfg=json.loads((ROOT/"experiments/landmark/mock_config.json").read_text())
    cfg["branch_replicates"]=1
    cfg["grading_contract_sha256"]=collect.digest(grade.contract(specs))
    return tasks,specs,cfg


class CodeMock(collect.Mock):
    def generate(self,payload,timeout):
        return {"message":{"content":"def f(x):\n    return x+1\n"},"done":True,"prompt_eval_count":0,"eval_count":0}


def make_run(tmp_path,data):
    tasks,specs,cfg=data
    collect.run(cfg,tasks,tmp_path/"run",adapter=CodeMock())
    return tmp_path/"run"


def fake_pass(program,**kwargs):
    sentinel=re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]+",program).group(0)
    start=re.search(grade.STARTED+r"[0-9a-f]{24}",program).group(0)
    if "return 0" in program:
        return {"passed":False,"returncode":1,"stdout":start+"\n","stdout_tail":"AssertionError","timed_out":False,"executed":True,"sandbox_kind":"seatbelt","seconds":.01}
    return {"passed":True,"returncode":0,"stdout":start+"\n"+sentinel+"\n",
            "stdout_tail":sentinel+"\n","timed_out":False,"executed":True,"sandbox_kind":"seatbelt","seconds":.01}


def authorize_mock(monkeypatch,tmp_path):
    path=tmp_path/"mock-attestation.json"
    path.write_text("{}\n")
    monkeypatch.setattr(grade,"verify_attestation",lambda _: {"passed":True,"mock":True})
    return path


def test_default_grading_is_missing_and_never_executes(tmp_path,fixture_data):
    run=make_run(tmp_path,fixture_data)
    result=grade.grade_collection(run,fixture_data[1],tmp_path/"grades",_runner=lambda *_a,**_k:pytest.fail("Executed"))
    assert result["sandbox_executions"]==0
    assert result["grade_rows"]==result["missing_grade_rows"]==8
    report=analyze(run,tmp_path/"grades/grades.jsonl")
    assert report["quality"]["stop"]["all_assigned_mean_bounds"]==[0,1]


def test_missing_attestation_blocks_requested_execution(tmp_path,fixture_data):
    run=make_run(tmp_path,fixture_data)
    result=grade.grade_collection(run,fixture_data[1],tmp_path/"grades",execute=True,_runner=lambda *_a,**_k:pytest.fail("Executed"))
    assert result["sandbox_executions"]==0
    assert result["blocked_reason"].startswith("containment_gate:")


@pytest.mark.parametrize("defect",["empty","overlap","vacuous","root_hash","exposed","duplicate"])
def test_private_test_gates_fail_before_execution(fixture_data,defect):
    tasks,specs,_=copy.deepcopy(fixture_data)
    if defect=="empty":specs[0]["private_assertions"]=[]
    if defect=="overlap":specs[0]["private_assertions"]=list(specs[0]["public_assertions"])
    if defect=="vacuous":specs[0]["private_assertions"]=["assert True"]
    if defect=="root_hash":specs[0]["public_task_sha256"]="wrong"
    if defect=="duplicate":specs[0]["private_assertions"]*=2
    if defect=="exposed":
        tasks[0]["public_context"]+="assert f(2)==3"
        specs[0]["public_task_sha256"]=collect.digest(tasks[0])
    with pytest.raises(ValueError):grade.validate_specs(tasks,specs)


def test_grades_bind_all_artifacts_and_reuse_identical_grade(tmp_path,fixture_data,monkeypatch):
    run=make_run(tmp_path,fixture_data)
    att=authorize_mock(monkeypatch,tmp_path)
    result=grade.grade_collection(run,fixture_data[1],tmp_path/"grades",execute=True,attestation_path=att,_runner=fake_pass)
    assert result["sandbox_executions"]==6  # Reference, negative control, one identical artifact per root.
    assert result["missing_grade_rows"]==0
    report=analyze(run,tmp_path/"grades/grades.jsonl")
    assert report["quality"]["stop"]["observed"]["mean"]==1
    assert report["contrasts"]["history_specific_repair_minus_generic_repair"]["complete_pairs"]["mean"]==0


def test_budget_exhaustion_preserves_ungraded_assignments(tmp_path,fixture_data,monkeypatch):
    run=make_run(tmp_path,fixture_data)
    att=authorize_mock(monkeypatch,tmp_path)
    result=grade.grade_collection(run,fixture_data[1],tmp_path/"grades",execute=True,attestation_path=att,max_executions=1,_runner=fake_pass)
    assert result["sandbox_executions"]==1
    assert result["missing_grade_rows"]==8


def test_failed_reference_makes_candidate_grades_missing(tmp_path,fixture_data,monkeypatch):
    run=make_run(tmp_path,fixture_data)
    att=authorize_mock(monkeypatch,tmp_path)
    def reject(program,**kwargs):
        out=fake_pass(program,**kwargs)
        out.update(passed=False,returncode=1,stdout_tail="AssertionError")
        return out
    result=grade.grade_collection(run,fixture_data[1],tmp_path/"grades",execute=True,attestation_path=att,_runner=reject)
    assert result["sandbox_executions"]==2 and result["missing_grade_rows"]==8


def test_environment_abort_is_missing_not_wrong_answer(fixture_data):
    def abort(*_a,**_k):
        return {"passed":False,"returncode":-6,"stdout":"","stdout_tail":"","timed_out":False,"executed":True,"sandbox_kind":"seatbelt","seconds":.01}
    out=grade.evaluate(fixture_data[1][0],"def f(x): return x+1",abort)
    assert out["outcome"] is None and out["reason"]=="grader_environment_failed_before_payload"


def test_executed_wrong_output_is_zero_and_empty_test_cannot_pass(fixture_data):
    def fail(program,**kwargs):
        out=fake_pass(program,**kwargs)
        out.update(passed=False,returncode=1,stdout_tail="AssertionError")
        return out
    assert grade.evaluate(fixture_data[1][0],"def f(x): return 999",fail)["outcome"]==0
    assert grade.evaluate(fixture_data[1][0],"",fake_pass)["outcome"]==0


def test_failed_real_attestation_rejected_before_runner():
    path=ROOT/"results/landmark_grading_validation_20260920/strict_canaries_v1/attestation.json"
    with pytest.raises(ValueError,match="did not pass"):
        grade.verify_attestation(path)


def test_private_assertions_not_in_collection_and_public_tests_not_in_program(fixture_data):
    tasks,specs,_=fixture_data
    for task in tasks:
        assert "f(2)" not in json.dumps(collect.initial_messages(task))
    program,_,rejection=grade.prepare_program(specs[0],specs[0]["reference_code"])
    assert rejection is None
    assert "assert f(2)==3" in program
    assert "assert f(0)==1" not in program


def test_mutated_collection_rejected_before_grading(tmp_path,fixture_data):
    run=make_run(tmp_path,fixture_data)
    with (run/"roots.jsonl").open("a") as f:f.write("\n")
    with pytest.raises(ValueError,match="checksum"):
        grade.grade_collection(run,fixture_data[1],tmp_path/"grades")


def test_contract_mismatch_rejected(tmp_path,fixture_data):
    run=make_run(tmp_path,fixture_data)
    specs=copy.deepcopy(fixture_data[1])
    specs[0]["private_assertions"]=["assert f(8)==9"]
    with pytest.raises(ValueError,match="not frozen"):
        grade.grade_collection(run,specs,tmp_path/"grades")


def test_nonexistent_attestation_still_emits_missing_rows(tmp_path,fixture_data):
    run=make_run(tmp_path,fixture_data)
    result=grade.grade_collection(run,fixture_data[1],tmp_path/"grades",execute=True,attestation_path=tmp_path/"absent.json")
    assert result["missing_grade_rows"]==8 and result["attestation_sha256"] is None


def test_static_flags_need_review_not_false_negative_quality(fixture_data):
    code="class Legitimate:\n    def __iter__(self):\n        return iter([])\ndef f(x):\n    return x+1\n"
    out=grade.evaluate(fixture_data[1][0],code,lambda *_a,**_k:pytest.fail("Executed flagged code"))
    assert out["outcome"] is None and out["reason"]=="integrity_review_required"


def test_no_negative_controls_is_not_a_valid_endpoint(fixture_data):
    tasks,specs,_=copy.deepcopy(fixture_data)
    specs[0]["negative_controls"]=[]
    with pytest.raises(ValueError,match="known-wrong"):
        grade.validate_specs(tasks,specs)


def test_accepting_wrong_control_prevents_candidate_grades(tmp_path,fixture_data,monkeypatch):
    run=make_run(tmp_path,fixture_data)
    att=authorize_mock(monkeypatch,tmp_path)
    def inert(program,**kwargs):
        return fake_pass(program.replace("return 0","return 42"),**kwargs)
    result=grade.grade_collection(run,fixture_data[1],tmp_path/"grades",execute=True,attestation_path=att,_runner=inert)
    assert result["sandbox_executions"]==4 and result["missing_grade_rows"]==8
    rows=[json.loads(x) for x in (tmp_path/"grades/grades.jsonl").read_text().splitlines()]
    assert all(r["missing_reason"]=="negative_control_validation_failed_or_unavailable" for r in rows)


def test_output_hash_checked_even_if_container_checksums_are_consistent(tmp_path,fixture_data):
    run=make_run(tmp_path,fixture_data)
    rows=[json.loads(x) for x in (run/"roots.jsonl").read_text().splitlines()]
    rows[0]["arms"]["stop"][0]["output_sha256"]="0"*64
    (run/"roots.jsonl").write_text("".join(json.dumps(x)+"\n" for x in rows))
    completion=json.loads((run/"completion.json").read_text())
    completion["checksums"]["roots.jsonl"]=collect.file_sha(run/"roots.jsonl")
    (run/"completion.json").write_text(json.dumps(completion))
    with pytest.raises(ValueError,match="does not bind"):
        grade.grade_collection(run,fixture_data[1],tmp_path/"grades")


def test_assigned_callable_is_not_rejected_by_ast_form(fixture_data):
    program,_,rejection=grade.prepare_program(fixture_data[1][0],"f = lambda x: x+1")
    assert rejection is None and "f = lambda" in program


# MRL-14: candidate compile-validity in the static gate (static compilation only; nothing is executed).
def _spec(entry="f"):
    return {"root_id":"t","entry_point":entry,"private_assertions":[f"assert {entry}(2)==3"],"preamble":[]}


def _never(*_a,**_k):
    raise AssertionError("runner must not be called for a static rejection")


@pytest.mark.parametrize("code",[
    "def f(x):\n    return x+1\nreturn f\n",
    "def f(x):\n    return x+1\nbreak\n",
    "def f(x):\n    return x+1\ncontinue\n",
    "def f(x):\n    return x+1\nawait f(1)\n",
])
def test_candidate_compile_errors_are_static_candidate_failures(code):
    import ast
    ast.parse(code)  # the old gate accepted these
    result=grade.evaluate(_spec(),code,_never)
    assert result["outcome"]==0 and result["reason"]=="candidate_compile_error" and result["sandbox_executed"] is False
    assert result["details"].startswith("SyntaxError at line ") and "Traceback" not in result["details"]


@pytest.mark.parametrize("code",[
    "from __future__ import annotations\ndef f(x: 'int') -> int:\n    return x+1\n",
    "def f(x):\n    return x+1\n",
])
def test_valid_candidates_pass_the_compile_gate_and_reach_the_runner(code):
    import ast
    assert grade.candidate_compile_error(code,ast.parse(code)) is None
    result=grade.evaluate(_spec(),code,fake_pass)
    assert result["outcome"]==1 and result["reason"]=="private_tests_passed"


def test_null_byte_is_a_static_candidate_failure_without_runner():
    code="def f(x):\n    return x+1\n\x00\n"
    assert grade.candidate_compile_error(code,__import__("ast").parse("def f(x):\n    return x+1\n")) is not None
    result=grade.evaluate(_spec(),code,_never)
    # On this interpreter ast.parse itself rejects null bytes first (existing unparseable path); either way
    # it is a static outcome-0 candidate failure with zero sandbox starts.
    assert result["outcome"]==0 and result["sandbox_executed"] is False
    assert result["reason"] in {"unparseable_output","candidate_compile_error"}


def test_saved_e11_s0_module_level_returns_are_static_compile_errors():
    calls=ROOT/"results/e11_dev_v2_20260922T010959Z/C/calls.jsonl"
    rows=[json.loads(l) for l in calls.read_text().splitlines() if l.strip()]
    entries={"mbpp/378":"move_first","mbpp/489":"frequency_Of_Largest"}
    seen=set()
    for r in rows:
        if r["root_id"] in entries and r["arm"]=="S0" and r["replicate"]==1:
            assert r["output_sha256"]==collect.digest(r["output"])  # read-only, bound to its saved hash
            code=grade.extract_code(r["output"])
            result=grade.evaluate(_spec(entries[r["root_id"]]),code,_never)
            assert result["outcome"]==0 and result["reason"]=="candidate_compile_error" and result["sandbox_executed"] is False
            assert "'return' outside function" in result["details"]
            seen.add(r["root_id"])
    assert seen==set(entries)


def test_valid_candidate_whose_program_does_not_start_is_an_environment_fault():
    def no_start(program,**kwargs):
        return {"passed":False,"returncode":1,"stdout":"","stdout_tail":"","timed_out":False,"executed":True,"sandbox_kind":"seatbelt","seconds":.01}
    result=grade.evaluate(_spec(),"def f(x):\n    return x+1\n",no_start)
    assert result["outcome"] is None and result["reason"]=="grader_environment_failed_before_payload"


def test_contract_records_the_bumped_grader_version():
    c=grade.contract([])
    assert c["grader_version"]==grade.GRADER_VERSION=="landmark-grader-v5-parse-and-compile-fault-attribution"
    assert "candidate_compile" in c


@pytest.mark.parametrize("code,compiles",[
    ("import os\nfrom __future__ import annotations\ndef f(x):\n    return x\n", False),  # late future import
    ("def f(x):\n    return x+1\nreturn f\n", False),                                    # module-level return
    ("def f(x):\n    return x+1\nbreak\n", False),                                       # break outside loop
    ('"""doc"""\nfrom __future__ import annotations\ndef f(x: int) -> int:\n    return x\n', True),  # docstring then future
    ("from __future__ import annotations\ndef f(x: 'int') -> int:\n    return x+1\n", True),        # valid future
])
def test_private_and_public_compile_gates_agree_on_the_candidate_as_written(code,compiles):
    """MRL-14 review: both gates compile the candidate exactly as written (no future-hoisting rewrite first)."""
    import ast
    from experiments.landmark import public_check as pc
    try:
        compile(code,"<candidate>","exec",dont_inherit=True); plain=True
    except SyntaxError:
        plain=False
    assert plain is compiles
    assert (grade.candidate_compile_error(code,ast.parse(code)) is None) is compiles
    program,_,rejection=grade.prepare_program(_spec(),code)
    assert (program is not None) is compiles
    if not compiles:
        assert rejection["outcome"]==0 and rejection["reason"]=="candidate_compile_error"
    assert (pc.static_code(code) is not None) is compiles


# MRL-15: injected compiler faults at the private entry points (compile is monkeypatched; nothing executes).
_VALID = "def f(x):\n    return x+1\n"
_FAULTS = [MemoryError, RecursionError, TypeError, OverflowError, KeyError]


def _raising_compile(exc_type):
    def fake(*args, **kwargs):
        raise exc_type("injected compiler fault")
    return fake


@pytest.mark.parametrize("exc_type", _FAULTS)
def test_injected_compile_fault_is_unavailable_not_candidate_failure(fixture_data, monkeypatch, exc_type):
    spec = fixture_data[1][0]
    monkeypatch.setattr(grade, "compile", _raising_compile(exc_type), raising=False)
    program, sentinel, rejection = grade.prepare_program(spec, _VALID)
    assert program is None and rejection["outcome"] is None and rejection["reason"] == "grader_compile_resource_fault"
    assert exc_type.__name__ in rejection["details"]
    calls = []
    result = grade.evaluate(spec, _VALID, lambda *a, **k: calls.append(1) or {})
    assert calls == [] and result["outcome"] is None and result["sandbox_executed"] is False
    assert result["reason"] == "grader_compile_resource_fault"
    with pytest.raises(grade.CompileResourceFault):
        grade.candidate_compile_error(_VALID)


def test_injected_valueerror_without_null_byte_is_a_fault_but_null_byte_is_candidate(fixture_data, monkeypatch):
    spec = fixture_data[1][0]
    monkeypatch.setattr(grade, "compile", _raising_compile(ValueError), raising=False)
    assert grade.prepare_program(spec, _VALID)[2]["reason"] == "grader_compile_resource_fault"
    assert grade.candidate_compile_error("x = 1\x00\n") is not None


@pytest.mark.parametrize("exc_type", [SyntaxError, IndentationError, TabError])
def test_injected_syntaxerror_family_remains_candidate_compile_error(fixture_data, monkeypatch, exc_type):
    spec = fixture_data[1][0]
    monkeypatch.setattr(grade, "compile", _raising_compile(exc_type), raising=False)
    result = grade.evaluate(spec, _VALID, lambda *a, **k: pytest.fail("runner must not be called"))
    assert result["outcome"] == 0 and result["reason"] == "candidate_compile_error" and result["sandbox_executed"] is False


# MRL-15 review: ast.parse (in hack_gate and prepare_program) runs before compile() and raises the same resource
# faults; they are attributed as grader faults, never scored and never propagated. Static parsing only.
_PARSE_FAULT_INPUTS = ["x = " + "-" * 200000 + "1\n", "x = " + "+".join(["1"] * 300000) + "\n"]


def _raising_parse(exc_type):
    def fake(*args, **kwargs):
        raise exc_type("injected parser fault")
    return fake


@pytest.mark.parametrize("exc_type", _FAULTS)
def test_injected_parse_fault_is_unavailable_not_candidate_failure(fixture_data, monkeypatch, exc_type):
    spec = fixture_data[1][0]
    monkeypatch.setattr(grade.ast, "parse", _raising_parse(exc_type))
    calls = []
    result = grade.evaluate(spec, _VALID, lambda *a, **k: calls.append(1) or {})
    monkeypatch.undo()
    assert calls == [] and result["outcome"] is None and result["sandbox_executed"] is False
    assert result["reason"] == "grader_compile_resource_fault" and exc_type.__name__ in result["details"]


def test_injected_parse_syntaxerror_remains_unparseable(fixture_data, monkeypatch):
    spec = fixture_data[1][0]
    monkeypatch.setattr(grade.ast, "parse", _raising_parse(SyntaxError))
    result = grade.evaluate(spec, _VALID, lambda *a, **k: pytest.fail("runner must not be called"))
    monkeypatch.undo()
    assert result["outcome"] == 0 and result["reason"] == "unparseable_output"


@pytest.mark.parametrize("code", _PARSE_FAULT_INPUTS)
def test_overcomplex_source_is_grader_fault_not_crash(fixture_data, code):
    spec = fixture_data[1][0]
    result = grade.evaluate(spec, code, lambda *a, **k: pytest.fail("runner must not be called"))
    assert result["outcome"] is None and result["reason"] == "grader_compile_resource_fault"
    assert result["sandbox_executed"] is False
