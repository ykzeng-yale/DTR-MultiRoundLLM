"""Public executor source tests with injected stdout only; no harness or candidate program is ever run."""
import json
from pathlib import Path
import signal
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import public_check as pc

NONCE = "0123456789abcdef0123456789abcdef"
CASES = [{"case_id": f"public-52-{i}", "args_literal": a, "expected_literal": e}
         for i, (a, e) in enumerate([("[7,11]", "77"), ("[13,9]", "117"), ("[2,17]", "34")], 1)]
GOOD = "def parallelogram_area(b, h):\n    return b * h\n"


def line(i, status="pass", returned=77, kind="int", nonce=NONCE):
    return json.dumps({"n": nonce, "i": i, "status": status, "returned": returned, "value_kind": kind},
                      sort_keys=True, separators=(",", ":")) + "\n"


def out(*lines, nonce=NONCE):
    return pc.PUBLIC_STARTED + nonce + "\n" + "".join(lines)


def statuses(results):
    return [(r["status"], r["reason"]) for r in results]


def never_run(*a, **k):
    raise AssertionError("runner must not be called")


# ---- limits and allowlist
def test_limits_are_numeric_and_read_from_sandbox():
    L = pc.PUBLIC_LIMITS
    assert (L["per_case_alarm_seconds"], L["aggregate_cpu_seconds"], L["parent_wall_seconds"]) == (2, 5, 10)
    assert L["memory_bytes"] == 512 << 20 and L["output_cap_bytes"] == 65536
    assert "best_effort" in L["memory_enforcement"] and "not_guaranteed" in L["memory_enforcement"]


@pytest.mark.parametrize("path", [ROOT/"experiments/landmark/dev_release_v1c/specs.jsonl", ROOT/"work/x.json",
    "/tmp/some_private_spec.jsonl", ROOT/"docs/../work/y"])
def test_allowlist_rejects_private_release_work(path):
    with pytest.raises(ValueError):
        pc.assert_public_inputs_only([ROOT/"docs/public_diagnostic_examples_v1.json", path])


def test_allowlist_accepts_public_examples():
    pc.assert_public_inputs_only([ROOT/"docs/public_diagnostic_examples_v1.json", ROOT/"experiments/landmark/public_check.py"])


# ---- static format gate (grader's rule), decided before any run
@pytest.mark.parametrize("answer", ["", "```python\nx=1\n```\n```python\ny=2\n```", "def f(:\n", "```python\n```", "# only a comment\n"])
def test_format_errors_need_no_runner(answer):
    assert not pc.static_format_check(answer, "parallelogram_area")
    assert statuses(pc.check_artifact(answer, "parallelogram_area", CASES, never_run, NONCE)) == [("format_error", None)]*3
    assert statuses(pc.format_error_results(CASES)) == [("format_error", None)]*3


def test_fenced_and_raw_code_pass_the_gate_and_missing_entry_point_is_runtime():
    assert pc.static_format_check("```python\n"+GOOD+"```", "parallelogram_area")
    assert pc.static_format_check(GOOD, "not_defined_here")  # lookup is a runtime interface check


def test_integrity_flag_is_review_not_run():
    code = "class A:\n    def __eq__(self, o):\n        return True\ndef parallelogram_area(b,h):\n    return A()\n"
    assert statuses(pc.check_artifact(code, "parallelogram_area", CASES, never_run, NONCE)) == [("unavailable", "protocol_integrity_review")]*3


# ---- harness text: compiled, never executed
def test_harness_compiles_and_embeds_contract_pieces():
    program = pc.build_public_program(GOOD, "parallelogram_area", CASES, NONCE)
    compile(program, "<public-harness>", "exec")
    for piece in (pc.PUBLIC_STARTED+NONCE, "RLIMIT_CPU, (5, 5)", "ITIMER_REAL, 2", "_pc_os.dup(1)", "dup2(_pc_null, 1)",
                  "inspect.signature", ".bind(*_pc_args)", "literal_eval(_pc_args_lit)", "def _pc_display_value("):
        assert piece in program
    assert program.index(pc.PUBLIC_STARTED) < program.index("exec(compile(")


def test_build_rejects_bad_inputs():
    with pytest.raises(ValueError): pc.build_public_program(GOOD, "f", CASES, "not-hex")
    with pytest.raises(ValueError): pc.build_public_program(GOOD, "1bad", CASES, NONCE)
    with pytest.raises(ValueError): pc.build_public_program("def f(:", "f", CASES, NONCE)


def test_check_artifact_calls_runner_once_with_public_limits():
    calls = []
    def fake(program, **kw):
        calls.append(kw); compile(program, "<p>", "exec")
        return {"stdout": out(line(0), line(1, returned=117), line(2, "wrong_value", 35)), "returncode": 0, "timed_out": False}
    res = pc.check_artifact("```python\n"+GOOD+"```", "parallelogram_area", CASES, fake, NONCE)
    assert calls == [{"timeout_s": 10, "cpu_seconds": 5, "output_cap": 65536}]
    assert [r["status"] for r in res] == ["pass", "pass", "wrong_value"] and res[2]["returned"] == 35


def test_runner_exception_is_infrastructure():
    def boom(program, **kw): raise RuntimeError("Verified Seatbelt isolation is required")
    assert statuses(pc.check_artifact(GOOD, "parallelogram_area", CASES, boom, NONCE)) == [("unavailable", "infrastructure_not_started")]*3


# ---- precedence table via injected stdout
def test_no_start_marker_is_infrastructure_not_started():
    for stdout in ("", "Traceback\n", out(line(0), nonce="f"*32), line(0)):
        assert statuses(pc.classify(stdout, 0, False, CASES, NONCE)) == [("unavailable", "infrastructure_not_started")]*3


def test_authentic_lines_keep_their_statuses():
    stdout = out(line(0, "interface_error", None, "none"), line(1, "program_exception", None, "none"), line(2, "timeout", None, "none"))
    assert [r["status"] for r in pc.classify(stdout, 0, False, CASES, NONCE)] == ["interface_error", "program_exception", "timeout"]


@pytest.mark.parametrize("rc,timed_out", [(-9, True), (-signal.SIGXCPU, False), (-signal.SIGKILL, False), (None, False)])
def test_termination_active_case_timeout_later_unavailable(rc, timed_out):
    assert statuses(pc.classify(out(line(0)), rc, timed_out, CASES, NONCE)) == [
        ("pass", None), ("timeout", None), ("unavailable", "not_attempted_after_termination")]


def test_crash_active_case_program_exception():
    assert statuses(pc.classify(out(), 1, False, CASES, NONCE)) == [("program_exception", None)] + [("unavailable", "not_attempted_after_termination")]*2


def test_output_cap_active_case_output_limit():
    stdout = out(line(0)) + '{"n":"' + NONCE + '","i":1,"sta'
    assert statuses(pc.classify(stdout, -signal.SIGXFSZ, False, CASES, NONCE)) == [
        ("pass", None), ("output_limit", None), ("unavailable", "not_attempted_after_termination")]
    capped = pc.classify(stdout, 0, False, CASES, NONCE, output_cap=len(stdout.encode()))
    assert [r["status"] for r in capped] == ["pass", "output_limit", "unavailable"]


def test_all_results_present_survive_nonzero_exit():
    stdout = out(line(0), line(1, returned=117), line(2, returned=34))
    assert [r["status"] for r in pc.classify(stdout, -signal.SIGXCPU, True, CASES, NONCE)] == ["pass"]*3


# ---- spoof / tamper: never pass
REVIEW = [("unavailable", "protocol_integrity_review")]*3


@pytest.mark.parametrize("stdout", [
    out(line(0, nonce="e"*32), line(1), line(2)),                       # forged nonce
    out(line(0), line(0), line(1)),                                     # duplicate
    out(line(1), line(0), line(2)),                                     # out of order
    out(line(0), line(1), line(2), line(2)),                            # extra line
    out(line(0), line(1), line(2)) + "PASS\n",                         # extra non-JSON line
    out(line(0), line(1), line(2)) + "trailing",                       # trailing bytes after a complete run
    out(line(0), "not json\n", line(2)),                                # malformed
    out(line(0) + line(1)[:-8]),                                        # truncated without reaching the cap
    out(line(0, "format_error", None, "none"), line(1), line(2)),      # status the harness cannot emit
    out(line(0, "pass", True, "int"), line(1), line(2)),               # bool smuggled as int display
    out(line(0, "pass", 10**18, "int"), line(1), line(2)),             # oversized display
    out(line(0, "timeout", 77, "int"), line(1), line(2)),              # value on a non-returning status
    out(json.dumps({"n": NONCE, "i": 0, "status": "pass", "returned": 77, "value_kind": "int", "x": 1}) + "\n"),  # extra key
])
def test_tampered_streams_are_review_never_pass(stdout):
    res = pc.classify(stdout, 0, False, CASES, NONCE)
    assert statuses(res) == REVIEW and all(r["status"] != "pass" for r in res)


# ---- display policy (pure function; display never changes status)
@pytest.mark.parametrize("value,expected", [
    (77, ("int", 77)), (-(10**18) + 1, ("int", -(10**18) + 1)), (10**18, ("unsupported", None)),
    (True, ("unsupported", None)), (False, ("unsupported", None)), (7.0, ("unsupported", None)),
    ([1, 2, 3], ("int_list", [1, 2, 3])), ([], ("int_list", [])), (list(range(16)), ("int_list", list(range(16)))),
    (list(range(17)), ("unsupported", None)), ([1, True], ("unsupported", None)), ([1, 2.0], ("unsupported", None)),
    ((1, 2), ("unsupported", None)), (None, ("none", None)), ("77", ("unsupported", None)), ([[1]], ("unsupported", None)),
])
def test_display_policy(value, expected):
    assert pc.display_value(value) == expected


def test_int_subclass_is_unsupported_without_repr():
    class Sneaky(int):
        def __repr__(self): raise AssertionError("repr must not be called")
    assert pc.display_value(Sneaky(3)) == ("unsupported", None)


def test_unsupported_display_keeps_pass_status():
    stdout = out(line(0, "pass", None, "unsupported"), line(1, "pass", None, "unsupported"), line(2, "wrong_value", None, "none"))
    assert [(r["status"], r["value_kind"]) for r in pc.classify(stdout, 0, False, CASES, NONCE)] == [
        ("pass", "unsupported"), ("pass", "unsupported"), ("wrong_value", "none")]


def test_results_match_build_diagnostic_shape():
    for r in pc.classify(out(line(0)), -9, True, CASES, NONCE):
        assert set(r) == {"status", "returned", "value_kind", "reason"} and r["status"] in pc.STATUSES
        assert r["value_kind"] in pc.VALUE_KINDS and (r["reason"] is None or r["reason"] in pc.UNAVAILABLE_REASONS)
