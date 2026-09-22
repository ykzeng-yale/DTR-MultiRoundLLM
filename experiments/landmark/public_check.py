"""Public-example executor source for the MRL-08 diagnostic (source only; this module never runs anything).

It builds the harness program that an attested isolated runner (sandbox.run_program) would execute on the
three fixed public cases, and classifies that runner's stdout into per-case results in the shape consumed by
diagnostic.build_diagnostic: {status, returned, value_kind, reason}. No private spec, hidden test, reference
program, private grade, release or work path is an input here (assert_public_inputs_only guards callers).

Precedence table (frozen; first matching row wins, tested in tests/test_landmark_public_check.py):
  0  static gate, decided BEFORE any run, using the private grader's own rule (grade.extract_code + parse +
     non-empty body) plus static compilation (MRL-14: compile(code, "<candidate>", "exec", dont_inherit=True),
     never executed): ambiguous fences / unparseable / empty / not compilable (e.g. module-level return,
     break/continue outside a loop) -> every case format_error (no runner call). MRL-15: only a SyntaxError
     (incl. IndentationError/TabError) or a null-byte ValueError is the candidate's own compile error; any other
     compile() exception (MemoryError, RecursionError, TypeError, OverflowError, ...) is a grader-side fault ->
     every case unavailable, reason infrastructure_not_started (no runner call; never format_error). The same holds
     for a MemoryError/RecursionError from ast.parse (MRL-15 review).
     Integrity flags from the grader's hack_gate (other than parse-error) -> every case unavailable,
     reason protocol_integrity_review (the grader itself refuses to grade these; never a pass).
  1  runner raised, or stdout does not begin with this run's start marker -> every case unavailable,
     reason infrastructure_not_started (a harness/infrastructure fault). When classify() is given the
     candidate code and that code does not compile, the missing marker is the candidate's own SyntaxError ->
     every case format_error instead (check_artifact never reaches this: row 0 already caught it).
  2  any forged (wrong nonce), duplicate, out-of-order, malformed, inconsistent or extra result line, or a
     partial final line while the output cap was NOT reached -> every case unavailable, reason
     protocol_integrity_review (a tampered stream never yields a pass).
  3  each authentic result line -> its own status (pass, wrong_value, interface_error, program_exception,
     timeout from the per-case soft alarm). Candidate definition failure -> program_exception on all cases
     (definition exceeding the soft alarm -> timeout on all cases);
     entry point missing/not callable -> interface_error on all cases; signature bind failure -> that case.
  4  first case without a result line (the active case) when the process ended early:
     output cap reached (stdout >= cap bytes, or SIGXFSZ) -> output_limit;
     else parent wall timeout, SIGXCPU (aggregate RLIMIT_CPU) or SIGKILL -> timeout;
     else (other abnormal end, e.g. os._exit or a crash) -> program_exception.
  5  every later case -> unavailable, reason not_attempted_after_termination.

Shared state across the three cases: they run sequentially in ONE process against ONE candidate module
namespace, so module globals, caches, mutated default arguments and imported-module state persist from case
to case (as in the private grader, which also runs all assertions in one module). Arguments and expected
values are rebuilt by a fresh ast.literal_eval per case, so a candidate that mutates its input cannot alter a
later case's arguments. The soft alarm can be caught or reset by candidate code; the hard limits (aggregate
RLIMIT_CPU and the parent wall timeout) are what actually bound execution.

Authentication scope: the nonce and start marker are embedded in the program text, which candidate code can
read (its run directory, frames). They reject stale/accidental/extra output and simple spoofs; they do NOT
authenticate results against candidate-controlled globals. This checker is scoped to reviewed ordinary
benchmark code, not adversarial security guarantees.
"""
from __future__ import annotations
import ast
import inspect
import json
from pathlib import Path
import re
import signal

from experiments.landmark import diagnostic, sandbox
from experiments.landmark.grade import extract_code
from experiments.common.integrity import hack_gate

ROOT = Path(__file__).resolve().parents[2]
STATUSES = ("pass", "wrong_value", "format_error", "interface_error", "program_exception", "timeout", "unavailable", "output_limit")
# Statuses the harness itself may emit; the rest are assigned by the parent (static gate / termination).
PAYLOAD_STATUSES = frozenset({"pass", "wrong_value", "interface_error", "program_exception", "timeout"})
VALUE_KINDS = frozenset({"int", "int_list", "unsupported", "none"})
UNAVAILABLE_REASONS = ("not_attempted_after_termination", "infrastructure_not_started", "protocol_integrity_review")
PUBLIC_STARTED = "__LANDMARK_PUBLIC_STARTED__"
RESULT_KEYS = frozenset({"n", "i", "status", "returned", "value_kind"})
MAX_ABS_INT = 10**18
MAX_LIST_LEN = 16

_run_defaults = inspect.signature(sandbox.run_program).parameters
PUBLIC_LIMITS = {
    "per_case_alarm_seconds": 2,           # soft: signal.setitimer(ITIMER_REAL); candidate code can defeat it
    "aggregate_cpu_seconds": 5,            # hard: RLIMIT_CPU (sandbox preexec and again inside the harness)
    "parent_wall_seconds": 10,             # hard: parent kills the process group (sandbox.run_program timeout_s)
    # Actual numeric caps read from the existing sandbox, not the phrase "existing caps".
    "memory_bytes": _run_defaults["mem_bytes"].default,        # 512 MiB requested via RLIMIT_DATA
    "memory_enforcement": "best_effort_RLIMIT_DATA_request_not_guaranteed_containment_on_macOS",
    "output_cap_bytes": _run_defaults["output_cap"].default,   # RLIMIT_FSIZE on stdout and parent read cap
    "nproc": 1,
}


def display_value(value):
    """Bounded display policy -> (value_kind, returned). Display never changes pass status.

    Exact int (not bool, not an int subclass) with abs < 10**18 -> "int"; exact list of <= 16 such ints ->
    "int_list" (copied); None -> "none"; anything else -> "unsupported" with returned None. Never calls the
    candidate object's repr/str; only type() identity checks and abs() on exact ints."""
    if type(value) is int and abs(value) < 10**18:
        return "int", value
    if type(value) is list and len(value) <= 16 and all(type(x) is int and abs(x) < 10**18 for x in value):
        return "int_list", [int(x) for x in value]
    if value is None:
        return "none", None
    return "unsupported", None


def assert_public_inputs_only(paths):
    """Read allowlist guard: the public executor must never be handed private specs, releases or work paths."""
    def named_private(path):
        parts = [x.lower() for x in path.parts[1:]] if path.is_absolute() else [x.lower() for x in path.parts]
        if parts[:1] == ["private"] and parts[1:2] in (["tmp"], ["var"], ["etc"]):
            parts = parts[1:]  # macOS system symlink prefix (/tmp -> /private/tmp), not a private input
        return any("private" in x for x in parts)
    for p in paths:
        resolved = Path(p).resolve()
        # Both the given and the resolved path are checked, each with the same system-prefix exemption.
        if named_private(resolved) or named_private(Path(p)):
            raise ValueError(f"Private path is not a public executor input: {p}")
        try:
            rel = resolved.relative_to(ROOT).parts
        except ValueError:
            continue
        if rel[:1] == ("work",) or (rel[:2] == ("experiments", "landmark") and len(rel) > 2 and rel[2].startswith("dev_release")):
            raise ValueError(f"Release/work path is not a public executor input: {p}")


class CompileResourceFault(RuntimeError):
    """compile() raised something that is not the candidate's own compile error (MRL-15): a grader-side
    resource limit or internal fault, never a format_error."""


def candidate_compile_status(code):
    """MRL-15 tri-state of compile(code, "<candidate>", "exec", dont_inherit=True) (only builds a code object;
    nothing is executed): "ok"; "candidate_error" for a SyntaxError (incl. IndentationError/TabError) or a
    ValueError for null bytes in the candidate text; "fault" for anything else compile() raises (MemoryError,
    RecursionError, TypeError -- the input is a str, so internal -- OverflowError, ...)."""
    try:
        compile(code, "<candidate>", "exec", dont_inherit=True)
    except SyntaxError:
        return "candidate_error"
    except ValueError:
        return "candidate_error" if isinstance(code, str) and "\x00" in code else "fault"
    except Exception:
        return "fault"
    return "ok"


def candidate_compiles(code):
    """MRL-14: True when compile(code, "<candidate>", "exec", dont_inherit=True) succeeds. compile() only builds a
    code object; nothing is executed. It catches what ast.parse accepts but the compiler rejects (module-level
    return, break/continue outside a loop, misplaced __future__ imports, ...). dont_inherit=True keeps this
    module's own `from __future__ import annotations` from leaking into the check. MRL-15: a compiler fault
    (see candidate_compile_status) raises CompileResourceFault instead of returning False."""
    status = candidate_compile_status(code)
    if status == "fault":
        raise CompileResourceFault("compile() raised a non-candidate exception")
    return status == "ok"


def static_code(output):
    """The grader's own format rule (grade.extract_code, then parse, then non-empty body) plus, since MRL-14, a
    successful static compilation of the candidate. Returns code or None. MRL-15: raises CompileResourceFault
    when compile() fails for a grader-side reason (never reported as None / format_error)."""
    try:
        code = extract_code(output)
    except ValueError:
        return None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    except ValueError as exc:
        if not (isinstance(code, str) and "\x00" in code):
            raise CompileResourceFault(f"ast.parse raised {type(exc).__name__}") from exc
        return None  # a null byte in the candidate text is the candidate's own error
    except Exception as exc:  # MRL-15 review: parser MemoryError / RecursionError is a grader-side fault
        raise CompileResourceFault(f"ast.parse raised {type(exc).__name__}") from exc
    if not tree.body or not candidate_compiles(code):
        return None
    return code


def static_format_check(code, entry_point):
    """True when the answer is well-formed under the grader's rule. Entry-point existence is NOT checked here:
    lookup and signature inspection are runtime operations (interface_error), per lead field 5."""
    return static_code(code) is not None


def uniform_results(cases, status, reason=None):
    return [{"status": status, "returned": None, "value_kind": "none", "reason": reason} for _ in cases]


def format_error_results(cases):
    """All-format_error results, decided before execution; requires no runner."""
    return uniform_results(cases, "format_error")


def _check_nonce(nonce):
    if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{16,64}", nonce):
        raise ValueError("Nonce must be 16-64 lowercase hex characters")


def _case_literals(cases):
    out = []
    for case in cases:
        args = diagnostic.literal(case["args_literal"])
        diagnostic.literal(case["expected_literal"])
        if not isinstance(args, (list, tuple)):
            raise ValueError("args_literal must be a list or tuple literal")
        out.append((case["args_literal"], case["expected_literal"]))
    return out


_HARNESS = r'''import os as _pc_os, sys as _pc_sys, json as _pc_json, ast as _pc_ast, signal as _pc_signal, inspect as _pc_inspect, resource as _pc_resource
try:
    _pc_resource.setrlimit(_pc_resource.RLIMIT_CPU, ({cpu}, {cpu}))
except (ValueError, OSError):
    pass  # the sandbox preexec already applied an equal or lower hard limit
_pc_out = _pc_os.fdopen(_pc_os.dup(1), "w", encoding="utf-8")  # save the real stdout before silencing
_pc_out.write({start!r} + "\n"); _pc_out.flush()
_pc_null = _pc_os.open(_pc_os.devnull, _pc_os.O_WRONLY)
_pc_os.dup2(_pc_null, 1)
_pc_sys.stdout = open(_pc_os.devnull, "w")  # candidate prints are discarded
{display_src}
class _PcAlarm(BaseException):
    pass
def _pc_on_alarm(signum, frame):
    raise _PcAlarm()
_pc_signal.signal(_pc_signal.SIGALRM, _pc_on_alarm)
_PC_NONCE = {nonce!r}
_PC_CASES = {cases!r}
def _pc_emit(i, status, value_kind="none", returned=None):
    _pc_out.write(_pc_json.dumps({{"n": _PC_NONCE, "i": i, "status": status, "returned": returned, "value_kind": value_kind}}, sort_keys=True, separators=(",", ":")) + "\n")
    _pc_out.flush()
_pc_ns = {{"__name__": "__main__", "__builtins__": __builtins__}}
_pc_fn = None
_pc_setup = None
try:
    _pc_signal.setitimer(_pc_signal.ITIMER_REAL, {alarm})
    try:
        exec(compile({code!r}, "<candidate>", "exec"), _pc_ns)  # candidate definition, own namespace
    finally:
        _pc_signal.setitimer(_pc_signal.ITIMER_REAL, 0)
except _PcAlarm:
    _pc_setup = "timeout"
except BaseException:
    _pc_setup = "program_exception"
if _pc_setup is None:
    # Entry point resolved at RUNTIME; missing or non-callable is an interface error for every case.
    _pc_fn = _pc_ns.get({entry!r})
    if not callable(_pc_fn):
        _pc_setup = "interface_error"
for _pc_i, (_pc_args_lit, _pc_exp_lit) in enumerate(_PC_CASES):
    if _pc_setup is not None:
        _pc_emit(_pc_i, _pc_setup)
        continue
    _pc_args = list(_pc_ast.literal_eval(_pc_args_lit))  # fresh arguments per case
    _pc_expected = _pc_ast.literal_eval(_pc_exp_lit)
    try:
        _pc_sig = _pc_inspect.signature(_pc_fn)
    except (TypeError, ValueError):
        _pc_sig = None  # no introspectable signature: the call itself decides
    if _pc_sig is not None:
        try:
            _pc_sig.bind(*_pc_args)
        except TypeError:
            _pc_emit(_pc_i, "interface_error")
            continue
    _pc_status, _pc_kind, _pc_ret = "program_exception", "none", None
    try:
        _pc_signal.setitimer(_pc_signal.ITIMER_REAL, {alarm})
        try:
            _pc_value = _pc_fn(*_pc_args)
            # Private Python equality semantics (7.0 == 7, True == 1); an exception in == is the program's.
            _pc_status = "pass" if bool(_pc_value == _pc_expected) else "wrong_value"
            _pc_kind, _pc_ret = _pc_display_value(_pc_value)
        finally:
            _pc_signal.setitimer(_pc_signal.ITIMER_REAL, 0)
    except _PcAlarm:
        _pc_status, _pc_kind, _pc_ret = "timeout", "none", None
    except BaseException:
        _pc_status, _pc_kind, _pc_ret = "program_exception", "none", None
    _pc_emit(_pc_i, _pc_status, _pc_kind, _pc_ret)
'''


def build_public_program(code, entry_point, cases, nonce):
    """Harness text only (nothing is executed here). code must already have passed static_code."""
    _check_nonce(nonce)
    if not isinstance(entry_point, str) or not entry_point.isidentifier():
        raise ValueError("Need an identifier entry point")
    if not isinstance(code, str) or static_code(code) is None:
        raise ValueError("Candidate must pass the static format gate before a program is built")
    display_src = inspect.getsource(display_value).replace("def display_value(", "def _pc_display_value(", 1)
    return _HARNESS.format(cpu=PUBLIC_LIMITS["aggregate_cpu_seconds"], start=PUBLIC_STARTED+nonce,
        display_src=display_src, nonce=nonce, cases=_case_literals(cases), alarm=PUBLIC_LIMITS["per_case_alarm_seconds"],
        code=code, entry=entry_point)


def _authentic(obj, index, nonce, expected):
    """Strict shape/consistency check of one parsed result line against its public expected value.

    Types are checked exactly before any set membership, so malformed fields are rejected, never a TypeError.
    A bounded int/int_list return must agree with the status under the private assert's Python ==
    (pass iff returned == expected); an unsupported return keeps the executor's in-isolation result."""
    if not isinstance(obj, dict) or set(obj) != RESULT_KEYS or type(obj["n"]) is not str or obj["n"] != nonce:
        return False
    status, kind, returned = obj["status"], obj["value_kind"], obj["returned"]
    if type(obj["i"]) is not int or obj["i"] != index or type(status) is not str or type(kind) is not str:
        return False
    if status not in PAYLOAD_STATUSES or kind not in VALUE_KINDS:
        return False
    if status not in ("pass", "wrong_value"):
        return kind == "none" and returned is None
    if kind == "none":  # a None return is compared under == like any other value
        return returned is None and (status == "pass") == (expected is None)
    if kind == "unsupported":
        return returned is None
    if display_value(returned) != (kind, returned):
        return False
    return (status == "pass") == bool(returned == expected)


def classify(stdout, returncode, timed_out, cases, nonce, output_cap=None, code=None):
    """Runner output -> per-case results (build_diagnostic shape). See the module precedence table.

    code (optional, MRL-14): the candidate source. With the start marker absent, infrastructure_not_started is
    kept unless the candidate has its own compile error (SyntaxError or null-byte ValueError), which is
    format_error; a compiler fault (MRL-15) keeps infrastructure_not_started."""
    _check_nonce(nonce)
    cap = PUBLIC_LIMITS["output_cap_bytes"] if output_cap is None else output_cap
    n = len(cases)
    start = PUBLIC_STARTED + nonce + "\n"
    if not isinstance(stdout, str) or not stdout.startswith(start):
        if code is not None and (not isinstance(code, str) or candidate_compile_status(code) == "candidate_error"):
            return format_error_results(cases)  # the candidate's own compile error, not an infrastructure fault
        return uniform_results(cases, "unavailable", "infrastructure_not_started")
    review = uniform_results(cases, "unavailable", "protocol_integrity_review")
    cap_hit = len(stdout.encode("utf-8")) >= cap or returncode == -signal.SIGXFSZ
    *lines, partial = stdout[len(start):].split("\n")
    if len(lines) > n:
        return review
    expected = [diagnostic.literal(c["expected_literal"]) for c in cases]  # public literals, never executed
    results = []
    for i, line in enumerate(lines):
        try:
            obj = diagnostic.strict_json_loads(line)  # a duplicate key makes the stream protocol_integrity_review
        except ValueError:
            return review
        if not _authentic(obj, i, nonce, expected[i]):
            return review
        results.append({"status": obj["status"], "returned": obj["returned"], "value_kind": obj["value_kind"], "reason": None})
    if partial and not cap_hit:
        return review  # malformed trailing bytes without reaching the cap
    if len(results) == n:
        return results if not partial else review  # a complete run followed by extra bytes is not authentic
    if cap_hit:
        active = "output_limit"
    elif timed_out or returncode is None or returncode in (-signal.SIGXCPU, -signal.SIGKILL):
        active = "timeout"
    else:
        active = "program_exception"
    results.append({"status": active, "returned": None, "value_kind": "none", "reason": None})
    results += uniform_results(cases[len(results):], "unavailable", "not_attempted_after_termination")
    return results


def check_artifact(output, entry_point, cases, runner, nonce):
    """Static gate, then at most one injected runner call, then classify. The runner is always injected."""
    try:
        code = static_code(output)
    except CompileResourceFault:
        return uniform_results(cases, "unavailable", "infrastructure_not_started")  # grader fault, no runner call
    if code is None:
        return format_error_results(cases)
    if [f for f in hack_gate(code, entry_point) if f != "parse-error"]:
        return uniform_results(cases, "unavailable", "protocol_integrity_review")
    program = build_public_program(code, entry_point, cases, nonce)
    try:
        run = runner(program, timeout_s=PUBLIC_LIMITS["parent_wall_seconds"], cpu_seconds=PUBLIC_LIMITS["aggregate_cpu_seconds"],
            output_cap=PUBLIC_LIMITS["output_cap_bytes"])
    except Exception:
        return uniform_results(cases, "unavailable", "infrastructure_not_started")
    return classify(run.get("stdout", ""), run.get("returncode"), bool(run.get("timed_out")), cases, nonce, code=code)
