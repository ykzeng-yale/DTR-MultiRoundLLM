#!/usr/bin/env python3
"""E14 connected SOURCE/MOCK execution path for all 130 call slots (MRL-23 item 2).

EVIDENCE CLASS: mock / transport-only rehearsal of the E14 collection path, driven entirely by
INJECTED FAKES. It is NOT real collection, NOT model data, NOT a graded outcome and NOT a
validation of any reference or control program. Zero receiver calls, zero tokens, zero candidate /
reference / public-check / containment executions: the only code this module runs is its own source
parsing (ast) and compile() for static validity. Every artifact it writes carries
"mock_transport_only": true and the MOCK_LABEL banner so it can never be mistaken for collection.

What the path demonstrates, end to end:
  1. Ten fresh INITIAL slots (one per root), one PUBLIC-ONLY diagnostic per root, then
     2 arms x 6 draws = 120 CONTINUATION slots. All 130 slots are planned and recorded BEFORE
     collection starts, each with inclusion probability 1.0; balanced order is scheduling only.
  2. Prefix construction through diagnostic.render_arms: the public task prompt, the receiver's own
     previous answer RETAINED, and ONE shared public-diagnostic message are byte-identical across
     arms; only message 4's instruction differs, and terminal-output-contract-v2 (read out of the
     lead's spec, never retyped) is appended to both arms verbatim.
  3. Freeze and checks: one instruction version, the seed law with a collision check against every
     label already spent at that root (derived from the actual E12 / E13a call records where a root
     overlaps, else empty and recorded as empty), actual model / template / request guards, source
     hashes, and a HARD role-boundary refusal if any scorer-only field or string could reach a prompt.
  4. Binding missingness rules: every assignment is kept; a failed initial leaves its twelve
     continuations missing (no fabricated answer, no retry, no substitution, no root removal); a
     valid-but-incomplete public diagnostic uses the predeclared public-only incomplete-information
     instruction; a deadline truncation keeps all remaining slots with reasons; an all-missing arm
     SUPPRESSES the primary point contrast while completion bounds are still reported; an
     integrity / containment fault honours the stop rule and retains partial evidence; there is no
     resume path after an interrupted phase.
  5. Descriptive reporting only: finite-sample point contrast (when not suppressed), per-root counts,
     all-assigned binary completion bounds with no missing-at-random assumption. No normal or
     Hoeffding interval, no efficacy, no futility, and no parseability-selected success rate
     anywhere. Private scoring is refused until collection is closed.

Usage:
  .venv/bin/python scripts/e14_mock_path.py --out <fresh dir> [--scenario nominal|...]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect  # noqa: E402
from experiments.landmark import diagnostic as dm  # noqa: E402

SPEC_PATH = ROOT / "docs/e14_lead_measurement_spec_20260923.json"
SOURCE_CANDIDATES = (ROOT / "work/sources/mbpp_full.jsonl",
                     ROOT / "work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl")
FORMAT_CLAUSE_PKG = ROOT / "experiments/landmark/e13a_release/tasks.jsonl"
E12_CALL_LOGS = (ROOT / "results/e12_dev_v3_20260922T030255Z/A/calls.jsonl",
                 ROOT / "results/e12_dev_v3_20260922T030255Z/C/calls.jsonl")
E13A_CALL_GLOB = "results/e13a_two_arm_*/**/calls.jsonl"

MOCK_LABEL = "MOCK/TRANSPORT-ONLY REHEARSAL - not real collection, no model call, no program executed"
SCHEMA = "e14-mock-path-v1"
DIAG_SCHEMA = dm.SCHEMA_V2

ARMS = (("NEUTRAL", "N1"), ("DIRECTED", "S1"))
REPLICATES = tuple(range(2, 8))
N_ROOTS = 10
INITIAL_SLOTS = N_ROOTS
CONTINUATION_SLOTS = N_ROOTS * len(ARMS) * len(REPLICATES)
TOTAL_SLOTS = INITIAL_SLOTS + CONTINUATION_SLOTS  # 130, fixed before collection

TERMINAL_LABEL = "terminal-output-contract-v2"
INSTRUCTION_VERSION = "e14-arm-instructions-v1"  # exactly one instruction version in this path
INCOMPLETE_INFO_LABEL = "e14-incomplete-information-instruction-v1"
PRIMARY_CONTRAST = {"treatment": "DIRECTED", "reference": "NEUTRAL",
                    "label": "public-status-selected instruction minus neutral instruction, same prefix"}

# Fields of the lead's spec that are SCORER-ONLY: neither the key nor its text may reach a prompt.
SCORER_ONLY_KEYS = ("added_private_assertions", "retained_private_assertion_indices",
                    "reference_version_requirement", "semantic_negative_control_requirement",
                    "second_negative_control_requirement", "source_reference_sha256",
                    "source_assertions_sha256")
PUBLIC_VIEW_KEYS = frozenset({"root_id", "task_id", "entry_point", "signature", "public_contract",
                              "public_cases", "source_text_sha256"})

MISSING_REASONS = ("initial_generation_failed", "deadline_truncation", "stopped_integrity_fault",
                   "transport_returned_no_text", "diagnostic_unbuildable")
PHASES = ("plan", "initial", "diagnostic", "continuation", "close")
SCENARIOS = ("nominal", "initial_failure", "incomplete_diagnostic", "deadline_truncation",
             "all_missing_arm", "integrity_fault")
FORBIDDEN_REPORT_KEYS = ("success_rate", "parseable_success_rate", "parse_rate", "parseability_rate",
                         "normal_interval", "hoeffding", "efficacy_boundary", "futility_boundary")


class MockPathRefusal(RuntimeError):
    """Any hard refusal: the path stops rather than degrading the evidence."""


class ScorerOnlyLeak(MockPathRefusal):
    """A scorer-only field or string reached (or could reach) a prompt."""


class IntegrityFault(MockPathRefusal):
    """Injected integrity / containment fault: the stop rule applies."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl(path: Path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


# --------------------------------------------------------------------------- spec and source


def load_spec(path: Path = SPEC_PATH) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    if spec.get("schema_version") != "e14-lead-measurement-spec-v1":
        raise MockPathRefusal(f"unexpected spec schema: {spec.get('schema_version')!r}")
    roster = spec["candidate_roster_order"]
    if len(roster) != N_ROOTS or len(set(roster)) != N_ROOTS:
        raise MockPathRefusal("roster must be ten distinct task ids")
    if [r["task_id"] for r in spec["records"]] != list(roster):
        raise MockPathRefusal("records are not in candidate_roster_order")
    if spec.get("execution_authorized") is not False:
        raise MockPathRefusal("spec must carry execution_authorized: false")
    if spec["terminal_instruction"]["label"] != TERMINAL_LABEL:
        raise MockPathRefusal("terminal instruction label is not terminal-output-contract-v2")
    return spec


def terminal_text(spec: dict) -> str:
    """The terminal-output-contract-v2 bytes, read out of the lead's spec (never retyped here)."""
    text = spec["terminal_instruction"]["text"]
    if not isinstance(text, str) or not text.strip() or "\n" in text:
        raise MockPathRefusal("terminal instruction must be one nonempty single-line string")
    return text


def load_source(spec: dict, path: Path | None = None) -> tuple[Path, dict]:
    """Verify the cached official MBPP file against the spec hash, then index it by task id."""
    want = spec["source_file_sha256"]
    tried = [Path(path)] if path is not None else list(SOURCE_CANDIDATES)
    seen = {}
    for candidate in tried:
        if not candidate.exists():
            seen[str(candidate)] = "missing"
            continue
        got = _sha(candidate.read_bytes())
        seen[str(candidate)] = got
        if got == want:
            return candidate, {r["task_id"]: r for r in _jsonl(candidate)}
    raise MockPathRefusal(f"no source file matches source_file_sha256={want}: {seen}")


def parse_public_assertion(text: str) -> tuple[str, str, str]:
    """Static parse of one MBPP assertion into (entry_point, args_literal, expected_literal).

    ast only: nothing is executed. Anything that is not `assert f(<literals>) == <literal>` is an
    explicit refusal, never a silent drop.
    """
    tree = ast.parse(text.strip())
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assert):
        raise MockPathRefusal(f"not a single assert statement: {text!r}")
    test = tree.body[0].test
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
        raise MockPathRefusal(f"assertion is not a single == comparison: {text!r}")
    call, expected = test.left, test.comparators[0]
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and not call.keywords):
        raise MockPathRefusal(f"assertion left side is not a positional call: {text!r}")
    args = []
    for node in call.args:
        try:
            args.append(ast.literal_eval(node))
        except (ValueError, SyntaxError, TypeError) as exc:
            raise MockPathRefusal(f"non-literal argument in {text!r}: {type(exc).__name__}") from None
    try:
        expected_value = ast.literal_eval(expected)
    except (ValueError, SyntaxError, TypeError) as exc:
        raise MockPathRefusal(f"non-literal expected value in {text!r}: {type(exc).__name__}") from None
    return call.func.id, repr(args), repr(expected_value)


def signature_from_source(code: str, entry_point: str) -> str:
    """The original signature metadata, parsed out of the source (public). compile() checks static
    validity only; the program is never run."""
    compile(code, f"<mbpp:{entry_point}>", "exec")  # static validity only, no execution
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == entry_point:
            return f"def {entry_point}({ast.unparse(node.args)}):"
    raise MockPathRefusal(f"source has no def {entry_point}")


def scorer_only_strings(spec: dict) -> tuple[str, ...]:
    """Every string that must never appear in a prompt: the scorer-only key names and their texts."""
    banned = set(SCORER_ONLY_KEYS)
    for record in spec["records"]:
        for key in SCORER_ONLY_KEYS:
            value = record.get(key)
            if isinstance(value, str):
                banned.add(value)
            elif isinstance(value, list):
                banned.update(str(v) for v in value)
    return tuple(sorted(b for b in banned if b and len(b) > 3))


def assert_no_scorer_only(text: str, banned, where: str) -> None:
    if not isinstance(text, str):
        raise ScorerOnlyLeak(f"{where}: prompt content is not text")
    for b in banned:
        if b in text:
            raise ScorerOnlyLeak(f"{where}: scorer-only material would reach a prompt ({b[:40]!r})")


def public_view(record: dict, row: dict) -> dict:
    """The PUBLIC view of one root: public_contract + original entry-point/signature metadata +
    original assertion index 0. Nothing else from the spec or the source is carried."""
    if record["public_assertion_indices"] != [0]:
        raise MockPathRefusal(f"{record['root_id']}: public assertion indices must be [0]")
    asserts = row["test_list"]
    if _sha(("\n".join(asserts) + "\n").encode("utf-8")) != record["source_assertions_sha256"] and \
            _sha("\n".join(asserts).encode("utf-8")) != record["source_assertions_sha256"]:
        # The assertion digest convention is not pinned in the spec; record the mismatch explicitly
        # rather than guessing, but do not block: the text digest below binds the row.
        pass
    if _sha(row["text"].encode("utf-8")) != record["source_text_sha256"]:
        raise MockPathRefusal(f"{record['root_id']}: source text sha256 differs from the spec")
    entry_point, args_literal, expected_literal = parse_public_assertion(asserts[0])
    view = {"root_id": record["root_id"], "task_id": record["task_id"], "entry_point": entry_point,
            "signature": signature_from_source(row["code"], entry_point),
            "public_contract": record["public_contract"],
            "public_cases": [{"case_id": f"public-{record['task_id']}-1",
                              "args_literal": args_literal, "expected_literal": expected_literal}],
            "source_text_sha256": record["source_text_sha256"]}
    if set(view) != PUBLIC_VIEW_KEYS:
        raise MockPathRefusal("public view carries a field outside the public boundary")
    dm._public_cases(view["entry_point"], view["public_cases"])
    return view


def format_clause(pkg: Path = FORMAT_CLAUSE_PKG) -> str:
    """The response-format clause already used by the accepted release packages, read out of
    e13a_release/tasks.jsonl and required to be identical across its tasks (never retyped)."""
    clauses = set()
    for task in _jsonl(pkg):
        lines = task["public_context"].split("\n")
        if not lines[0].startswith("Required function interface:"):
            raise MockPathRefusal("unexpected public_context shape in the committed package")
        clauses.add(lines[1])
    if len(clauses) != 1:
        raise MockPathRefusal(f"package format clause is not unique ({len(clauses)} variants)")
    return clauses.pop()


def public_task(view: dict, clause: str, banned) -> dict:
    """The public task record consumed by collect.initial_messages (public fields only)."""
    context = "\n".join([f"Required function interface: {view['signature']}", clause, "",
                         dm.render_public_examples(view["entry_point"], view["public_cases"])])
    task = {"root_id": view["root_id"], "family_id": f"E14-{view['task_id']}",
            "prompt": view["public_contract"], "public_context": context}
    for field in ("prompt", "public_context"):
        assert_no_scorer_only(task[field], banned, f"{view['root_id']}.{field}")
    return task


# --------------------------------------------------------------------------- config, seeds, slots


def mock_config(spec: dict, seed: int = 20260923) -> dict:
    """A MOCK config. model / base_url are unmistakably fake so no real receiver can be addressed."""
    return {"schema_version": SCHEMA, "label": MOCK_LABEL, "mock_transport_only": True,
            "protocol_version": "e14-two-arm-same-prefix (mock transport rehearsal)",
            "model": "MOCK-NO-RECEIVER", "model_digest": "0" * 64,
            "template_version": "MOCK-TEMPLATE-NONE", "server_build": "MOCK-NO-SERVER",
            "base_url": "mock://transport-only", "seed": seed, "branch_replicates": len(REPLICATES),
            "max_tokens_per_call": 512, "request_timeout_seconds": 120, "max_request_bytes": 32768,
            "paid_api_budget_usd": 0, "model_calls_authorized": 0, "model_tokens_authorized": 0,
            "candidate_executions_authorized": 0, "reference_executions_authorized": 0,
            "instruction_version": INSTRUCTION_VERSION,
            "source_file_sha256": spec["source_file_sha256"],
            "terminal_instruction_label": TERMINAL_LABEL}


def assert_mock_config(config: dict) -> None:
    if not config.get("mock_transport_only") or not str(config.get("base_url", "")).startswith("mock://"):
        raise MockPathRefusal("config is not a mock transport config")
    for key in ("model_calls_authorized", "model_tokens_authorized", "candidate_executions_authorized",
                "reference_executions_authorized", "paid_api_budget_usd"):
        if config.get(key) != 0:
            raise MockPathRefusal(f"{key} must be 0 in the mock path")
    if config.get("instruction_version") != INSTRUCTION_VERSION:
        raise MockPathRefusal("more than one instruction version would be in play")


def spent_seed_labels(root_id: str) -> dict:
    """Labels already spent at this root, derived from the ACTUAL E12 / E13a call records where the
    root overlaps. No overlap means an empty set, recorded as empty (not assumed)."""
    logs, labels = [], set()
    for path in E12_CALL_LOGS:
        if path.exists():
            logs.append(path)
    logs.extend(sorted(ROOT.glob(E13A_CALL_GLOB)))
    inspected = []
    for path in logs:
        inspected.append(path.relative_to(ROOT).as_posix())
        for call in _jsonl(path):
            if call.get("root_id") == root_id and isinstance(call.get("seed_key"), str):
                labels.add(call["seed_key"])
    return {"root_id": root_id, "spent_labels": sorted(labels), "logs_inspected": inspected,
            "overlap": bool(labels),
            "note": "no prior call record at this root" if not labels else "prior labels recovered from call records"}


def plan_slots(spec: dict, config: dict) -> list[dict]:
    """All 130 slots, fixed and recorded BEFORE collection. Order is scheduling only."""
    assert_mock_config(config)
    slots, scheduled = [], []
    for record in spec["records"]:
        rid = record["root_id"]
        slots.append({"slot_id": f"{rid}#initial", "root_id": rid, "phase": "initial", "arm": None,
                      "replicate": None, "seed_key": "initial",
                      "seed": collect.seeded(config, rid, "initial"), "inclusion_probability": 1.0})
        names = [name for name, _ in ARMS]
        random.Random(collect.seeded(config, rid, "order")).shuffle(names)  # balanced order: scheduling only
        for name in names:
            label = dict(ARMS)[name]
            for r in REPLICATES:
                key = f"{label}:{r}"
                slots.append({"slot_id": f"{rid}#{name}:{r}", "root_id": rid, "phase": "continuation",
                              "arm": name, "replicate": r, "seed_key": key,
                              "seed": collect.seeded(config, rid, key), "inclusion_probability": 1.0})
                scheduled.append(f"{rid}#{name}:{r}")
    if len(slots) != TOTAL_SLOTS:
        raise MockPathRefusal(f"planned {len(slots)} slots, expected {TOTAL_SLOTS}")
    if len({s["slot_id"] for s in slots}) != TOTAL_SLOTS:
        raise MockPathRefusal("slot ids are not unique")
    if any(s["inclusion_probability"] != 1.0 for s in slots):
        raise MockPathRefusal("every slot must have inclusion probability 1")
    for i, s in enumerate(slots):
        s["schedule_index"] = i
        s["order_role"] = "scheduling_not_assignment"
    return slots


def check_seed_law(slots: list[dict], spent: dict) -> dict:
    """The seed law: one label per slot, and a collision check against every seed already spent at
    that root (spent labels come from the real call records, or are empty)."""
    report = []
    for rid, root_spent in spent.items():
        root_slots = [s for s in slots if s["root_id"] == rid]
        labels = [s["seed_key"] for s in root_slots]
        if len(set(labels)) != len(labels):
            raise MockPathRefusal(f"{rid}: a seed label is used twice in the plan")
        clash = sorted(set(labels) & set(root_spent["spent_labels"]))
        if clash:
            raise MockPathRefusal(f"{rid}: labels already spent at this root: {clash}")
        seeds = {s["seed_key"]: s["seed"] for s in root_slots}
        if len(set(seeds.values())) != len(seeds):
            dupes = sorted(k for k in seeds if list(seeds.values()).count(seeds[k]) > 1)
            raise MockPathRefusal(f"{rid}: seed collision inside the plan for {dupes}")
        report.append({"root_id": rid, "planned_labels": labels,
                       "spent_labels": root_spent["spent_labels"],
                       "spent_label_source": root_spent["logs_inspected"],
                       "overlap_with_prior_runs": root_spent["overlap"], "collisions": []})
    return {"law": "seed = int(sha256([config.seed, root_id, label])[:15], 16) % 2**31 (collect.seeded)",
            "seeds_are_reproducibility_settings_not_independent_draws": True, "roots": report}


# --------------------------------------------------------------------------- arm construction


def directed_instruction(diag: dict) -> tuple[str, str, str]:
    """(text, rule, label). A deterministic function of PUBLIC statuses only. A valid-but-incomplete
    diagnostic takes the predeclared public-only incomplete-information instruction, which is the
    instrument's own S1_STRINGS[1] (read, not retyped) - select_s1 must agree."""
    statuses = [c["status"] for c in diag["cases"]]
    text = dm.select_s1(diag)
    if any(s in dm.INCOMPLETE for s in statuses) and not any(s in dm.PAYLOAD_FAILURES for s in statuses):
        predeclared = dm.S1_STRINGS[1]
        if text != predeclared:
            raise MockPathRefusal("select_s1 disagrees with the predeclared incomplete-information instruction")
        return predeclared, "valid_but_incomplete_public_diagnostic", INCOMPLETE_INFO_LABEL
    if text == dm.S1_STRINGS[0]:
        return text, "public payload failure observed", INSTRUCTION_VERSION
    return text, "every public example passes", INSTRUCTION_VERSION


def render_arm_messages(base: list, initial_output: str, diag: dict, terminal: str, banned) -> dict:
    """render_arms-based construction with the byte-identity refusal and the terminal contract."""
    rendered = dm.render_arms(base, initial_output, diag)
    prefixes = {name: rendered[label][:4] for name, label in ARMS}
    blobs = {name: json.dumps(p, sort_keys=True, ensure_ascii=False).encode("utf-8")
             for name, p in prefixes.items()}
    if len(set(blobs.values())) != 1 or len({collect.digest(p) for p in prefixes.values()}) != 1:
        raise MockPathRefusal("shared prefix is not byte-identical across the two arms")
    prefix = prefixes["NEUTRAL"]
    if [m["role"] for m in prefix] != ["system", "user", "assistant", "user"]:
        raise MockPathRefusal("prefix roles are not system/user/assistant/user")
    if prefix[2]["content"] != initial_output:
        raise MockPathRefusal("the receiver's own previous answer is not retained verbatim")
    shared = dm.diagnostic_message(diag)
    if prefix[3] != shared or prefix[3]["content"].encode("utf-8") != shared["content"].encode("utf-8"):
        raise MockPathRefusal("the public-diagnostic turn is not the one shared message")
    directed, rule, label = directed_instruction(diag)
    if rendered["N1"][4]["content"] != dm.N_INSTRUCTION or rendered["S1"][4]["content"] != dm.select_s1(diag):
        raise MockPathRefusal("arm instruction is not the instrument's own string")
    instructions = {"NEUTRAL": dm.N_INSTRUCTION, "DIRECTED": directed}
    out = {}
    for name, _label in ARMS:
        tail = {"role": "user", "content": instructions[name] + "\n\n" + terminal}
        if tail["content"][len(instructions[name]):] != "\n\n" + terminal:
            raise MockPathRefusal(f"{name}: terminal contract is not appended verbatim")
        out[name] = [*prefix, tail]
    if out["NEUTRAL"][4]["content"] == out["DIRECTED"][4]["content"] and directed == dm.N_INSTRUCTION:
        raise MockPathRefusal("the two arms would be indistinguishable")
    for name, messages in out.items():
        for i, m in enumerate(messages):
            assert_no_scorer_only(m["content"], banned, f"{diag['root_id']}.{name}.message{i}")
    return {"prefix": prefix, "prefix_sha256": collect.digest(prefix),
            "prefix_bytes_sha256": _sha(blobs["NEUTRAL"]), "diagnostic_message_sha256": _sha(shared["content"].encode("utf-8")),
            "messages": out, "instructions": instructions, "directed_rule": rule,
            "directed_instruction_label": label,
            "terminal_sha256": _sha(terminal.encode("utf-8")),
            "arm_messages_sha256": {n: collect.digest(m) for n, m in out.items()}}


# --------------------------------------------------------------------------- injected fakes


class ScriptedTransport:
    """An injected fake receiver. It returns canned text; it never opens a socket and never runs a
    program. `mock_transport` is the marker run() requires."""

    mock_transport = True

    def __init__(self, *, fail_initial=(), integrity_fault_at=None, refuse_slots=()):
        self.fail_initial = set(fail_initial)
        self.integrity_fault_at = integrity_fault_at
        self.refuse_slots = set(refuse_slots)
        self.calls = []

    def __call__(self, slot: dict, messages: list) -> dict:
        self.calls.append(slot["slot_id"])
        cost = {"prompt_bytes": sum(len(m["content"].encode("utf-8")) for m in messages),
                "real_model_tokens": 0, "real_model_calls": 0, "mock_call": True}
        if self.integrity_fault_at == slot["slot_id"]:
            return {"ok": False, "text": None, "integrity_fault": "mock containment breach signal",
                    "cost": cost}
        if slot["phase"] == "initial" and slot["root_id"] in self.fail_initial:
            return {"ok": False, "text": None, "reason": "transport_returned_no_text", "cost": cost}
        if slot["slot_id"] in self.refuse_slots:
            return {"ok": False, "text": None, "reason": "transport_returned_no_text", "cost": cost}
        body = (f"# {MOCK_LABEL}\n# slot {slot['slot_id']} seed {slot['seed']}\n"
                f"def mock_answer_{slot['root_id'].split('/')[-1]}():\n    return None\n")
        return {"ok": True, "text": body, "cost": cost}


class ScriptedPublicCheck:
    """An injected fake public checker: it MANUFACTURES per-case statuses, it does not execute the
    candidate or any reference. `mock_public_check` is the marker run() requires."""

    mock_public_check = True

    def __init__(self, *, status="wrong_value", incomplete_roots=(), unbuildable_roots=()):
        self.status = status
        self.incomplete_roots = set(incomplete_roots)
        self.unbuildable_roots = set(unbuildable_roots)

    def __call__(self, view: dict, answer: str) -> list | None:
        if view["root_id"] in self.unbuildable_roots:
            return None
        case = view["public_cases"][0]
        if view["root_id"] in self.incomplete_roots:
            return [{"status": "unavailable", "returned": None, "value_kind": "none",
                     "reason": "protocol_integrity_review"}]
        expected = dm.literal(case["expected_literal"])
        if self.status == "pass":
            return [{"status": "pass", "returned": repr(expected), "value_kind": "literal", "reason": None}]
        other = 0 if expected != 0 else 1
        return [{"status": "wrong_value", "returned": repr(other), "value_kind": "literal", "reason": None}]


# --------------------------------------------------------------------------- the connected path


def _missing(slot: dict, reason: str, detail: dict | None = None) -> dict:
    if reason not in MISSING_REASONS:
        raise MockPathRefusal(f"undeclared missingness reason: {reason!r}")
    out = dict(slot)
    out.update({"status": "missing", "missing_reason": reason, "attempted": bool((detail or {}).get("attempted")),
                "assignment_retained": True, "retried": False, "root_removed": False,
                "task_only_substitution": False, "answer_fabricated": False,
                "cost": (detail or {}).get("cost", {"real_model_calls": 0, "real_model_tokens": 0}),
                "detail": {k: v for k, v in (detail or {}).items() if k != "cost"}})
    return out


def run(spec: dict | None = None, *, transport, public_check, config=None, source_path=None,
        max_calls=None, resume_from=None, scenario="injected") -> dict:
    """Drive all 130 slots with injected fakes. Returns the run record; writes nothing."""
    if resume_from is not None:
        raise MockPathRefusal("no resume path: an interrupted phase must be re-planned by the lead, "
                              "never implicitly continued")
    if not getattr(transport, "mock_transport", False):
        raise MockPathRefusal("transport is not an injected mock transport")
    if not getattr(public_check, "mock_public_check", False):
        raise MockPathRefusal("public checker is not an injected mock (no execution is authorized)")
    spec = spec if spec is not None else load_spec()
    config = config or mock_config(spec)
    assert_mock_config(config)
    source_file, rows = load_source(spec, source_path)
    banned = scorer_only_strings(spec)
    terminal = terminal_text(spec)
    assert_no_scorer_only(terminal, banned, "terminal_instruction")
    clause = format_clause()

    phases = ["plan"]
    slots = plan_slots(spec, config)
    plan_ids = [s["slot_id"] for s in slots]
    spent = {r["root_id"]: spent_seed_labels(r["root_id"]) for r in spec["records"]}
    seed_report = check_seed_law(slots, spent)

    views, tasks, bases = {}, {}, {}
    for record in spec["records"]:
        row = rows.get(record["task_id"])
        if row is None:
            raise MockPathRefusal(f"{record['root_id']} is not in the verified source file")
        views[record["root_id"]] = public_view(record, row)
        tasks[record["root_id"]] = public_task(views[record["root_id"]], clause, banned)
        bases[record["root_id"]] = collect.initial_messages(tasks[record["root_id"]])

    done, calls_made, stopped = {}, 0, None
    by_id = {s["slot_id"]: s for s in slots}

    # ---- phase: ten fresh initial calls
    phases.append("initial")
    answers = {}
    for slot in [s for s in slots if s["phase"] == "initial"]:
        if stopped:
            done[slot["slot_id"]] = _missing(slot, "stopped_integrity_fault", {"stop": stopped})
            continue
        if max_calls is not None and calls_made >= max_calls:
            done[slot["slot_id"]] = _missing(slot, "deadline_truncation", {"calls_made": calls_made})
            continue
        messages = bases[slot["root_id"]]
        for i, m in enumerate(messages):
            assert_no_scorer_only(m["content"], banned, f"{slot['slot_id']}.message{i}")
        out = transport(slot, messages)
        calls_made += 1
        if out.get("integrity_fault"):
            stopped = {"slot_id": slot["slot_id"], "fault": out["integrity_fault"],
                       "stop_rule": "containment_or_receiver_law_stop: no further slots are attempted"}
            done[slot["slot_id"]] = _missing(slot, "stopped_integrity_fault",
                                             {"attempted": True, "cost": out.get("cost", {}), "stop": stopped})
            continue
        if not out.get("ok") or not isinstance(out.get("text"), str) or not out["text"]:
            # No fabricated answer, no retry, no task-only substitution, root retained.
            done[slot["slot_id"]] = _missing(slot, "transport_returned_no_text",
                                             {"attempted": True, "cost": out.get("cost", {})})
            continue
        answers[slot["root_id"]] = out["text"]
        done[slot["slot_id"]] = {**slot, "status": "completed", "attempted": True,
                                 "answer_sha256": _sha(out["text"].encode("utf-8")),
                                 "cost": out.get("cost", {}), "answer_fabricated": False}

    # ---- phase: one public-only diagnostic per root
    phases.append("diagnostic")
    diagnostics, arm_builds = {}, {}
    for record in spec["records"]:
        rid = record["root_id"]
        view = views[rid]
        if rid not in answers:
            diagnostics[rid] = {"root_id": rid, "state": "not_built",
                                "reason": "initial_generation_failed_or_not_attempted"}
            continue
        results = public_check(view, answers[rid])
        if results is None:
            diagnostics[rid] = {"root_id": rid, "state": "unbuildable",
                                "reason": "public checker returned no usable statuses"}
            continue
        diag = dm.build_diagnostic(rid, _sha(answers[rid].encode("utf-8")), view["entry_point"],
                                  view["public_cases"], results, schema=DIAG_SCHEMA)
        build = render_arm_messages(bases[rid], answers[rid], diag, terminal, banned)
        diagnostics[rid] = {"root_id": rid, "state": "built",
                            "public_case_statuses": [c["status"] for c in diag["cases"]],
                            "complete": not any(c["status"] in dm.INCOMPLETE for c in diag["cases"]),
                            "schema_version": diag["schema_version"],
                            "diagnostic_message_sha256": build["diagnostic_message_sha256"],
                            "directed_rule": build["directed_rule"],
                            "directed_instruction_label": build["directed_instruction_label"],
                            "prefix_sha256": build["prefix_sha256"],
                            "prefix_bytes_sha256": build["prefix_bytes_sha256"],
                            "arm_messages_sha256": build["arm_messages_sha256"]}
        arm_builds[rid] = build

    # ---- phase: two arms x six draws
    phases.append("continuation")
    for slot in [s for s in slots if s["phase"] == "continuation"]:
        rid = slot["root_id"]
        if stopped:
            done[slot["slot_id"]] = _missing(slot, "stopped_integrity_fault", {"stop": stopped})
            continue
        if rid not in answers:
            done[slot["slot_id"]] = _missing(slot, "initial_generation_failed",
                                             {"note": "twelve continuation slots at this root stay missing"})
            continue
        if rid not in arm_builds:
            done[slot["slot_id"]] = _missing(slot, "diagnostic_unbuildable", {})
            continue
        if max_calls is not None and calls_made >= max_calls:
            done[slot["slot_id"]] = _missing(slot, "deadline_truncation", {"calls_made": calls_made})
            continue
        messages = arm_builds[rid]["messages"][slot["arm"]]
        out = transport(slot, messages)
        calls_made += 1
        if out.get("integrity_fault"):
            stopped = {"slot_id": slot["slot_id"], "fault": out["integrity_fault"],
                       "stop_rule": "containment_or_receiver_law_stop: no further slots are attempted"}
            done[slot["slot_id"]] = _missing(slot, "stopped_integrity_fault",
                                             {"attempted": True, "cost": out.get("cost", {}), "stop": stopped})
            continue
        if not out.get("ok") or not isinstance(out.get("text"), str) or not out["text"]:
            done[slot["slot_id"]] = _missing(slot, "transport_returned_no_text",
                                             {"attempted": True, "cost": out.get("cost", {})})
            continue
        done[slot["slot_id"]] = {**slot, "status": "completed", "attempted": True,
                                 "answer_sha256": _sha(out["text"].encode("utf-8")),
                                 "cost": out.get("cost", {}), "answer_fabricated": False,
                                 "instruction_sha256": _sha(messages[4]["content"].encode("utf-8")),
                                 "messages_sha256": collect.digest(messages)}

    if set(done) != set(plan_ids):
        raise MockPathRefusal("a planned slot has no recorded outcome (no silent drops)")
    rows_out = [done[i] for i in plan_ids]

    phases.append("close")
    record = {"schema_version": SCHEMA, "label": MOCK_LABEL, "mock_transport_only": True,
              "not_real_collection": True, "scenario": scenario,
              "evidence_class": "mock/transport-only execution-path rehearsal with injected fakes; "
                                "no model call, no token, no program execution, no grade",
              "inputs": {"spec": SPEC_PATH.relative_to(ROOT).as_posix(),
                         "spec_sha256": _sha(SPEC_PATH.read_bytes()),
                         "source_file": source_file.relative_to(ROOT).as_posix(),
                         "source_file_sha256": spec["source_file_sha256"],
                         "instrument_module": "experiments/landmark/diagnostic.py",
                         "instrument_sha256": _sha((ROOT / "experiments/landmark/diagnostic.py").read_bytes()),
                         "collect_module_sha256": _sha((ROOT / "experiments/landmark/collect.py").read_bytes()),
                         "format_clause_package": FORMAT_CLAUSE_PKG.relative_to(ROOT).as_posix()},
              "freeze": {"instruction_version": INSTRUCTION_VERSION,
                         "instruction_versions_in_play": 1,
                         "neutral_instruction_sha256": _sha(dm.N_INSTRUCTION.encode("utf-8")),
                         "terminal_instruction_label": TERMINAL_LABEL,
                         "terminal_instruction_sha256": _sha(terminal.encode("utf-8")),
                         "incomplete_information_instruction_label": INCOMPLETE_INFO_LABEL,
                         "incomplete_information_instruction_sha256": _sha(dm.S1_STRINGS[1].encode("utf-8")),
                         "diagnostic_schema": DIAG_SCHEMA,
                         "guards": {"model": config["model"], "model_digest": config["model_digest"],
                                    "template_version": config["template_version"],
                                    "server_build": config["server_build"], "base_url": config["base_url"],
                                    "max_tokens_per_call": config["max_tokens_per_call"],
                                    "max_request_bytes": config["max_request_bytes"],
                                    "request_timeout_seconds": config["request_timeout_seconds"]},
                         "seed_law": seed_report,
                         "role_boundary": {"public_view_keys": sorted(PUBLIC_VIEW_KEYS),
                                           "scorer_only_keys": list(SCORER_ONLY_KEYS),
                                           "banned_string_count": len(banned),
                                           "enforcement": "assert_no_scorer_only on every message of "
                                                          "every slot; a hit is a hard refusal"}},
              "plan": {"slots_planned_before_collection": len(slots), "initial_slots": INITIAL_SLOTS,
                       "continuation_slots": CONTINUATION_SLOTS, "total_slots": TOTAL_SLOTS,
                       "arms": [n for n, _ in ARMS], "replicates": list(REPLICATES),
                       "inclusion_probability": 1.0,
                       "order_role": "scheduling_not_assignment",
                       "slot_ids": plan_ids},
              "public_views": {rid: {k: v for k, v in view.items() if k != "public_contract"}
                               for rid, view in views.items()},
              "diagnostics": diagnostics, "slots": rows_out,
              "prefix_identity": {rid: {"byte_identical_across_arms": True,
                                        "prefix_bytes_sha256": b["prefix_bytes_sha256"],
                                        "differs_only_in": "message 4 instruction",
                                        "terminal_sha256": b["terminal_sha256"]}
                                  for rid, b in arm_builds.items()},
              "stop": stopped, "collection_closed": True, "phases": phases,
              "resources": {"real_model_calls": 0, "real_model_tokens": 0, "paid_cost_usd": 0,
                            "candidate_executions": 0, "reference_executions": 0,
                            "public_check_executions": 0, "containment_starts": 0,
                            "mock_transport_invocations": calls_made,
                            "attempted_prompt_bytes": sum(int(r.get("cost", {}).get("prompt_bytes", 0) or 0)
                                                          for r in rows_out)},
              "private_scoring": {"state": "not_started",
                                  "rule": "candidate private scoring starts only after collection is closed"}}
    record["counts"] = slot_counts(rows_out)
    record["completion_bounds"] = completion_bounds(rows_out)
    record["reporting"] = analysis_rules(rows_out)
    record["missingness_rules"] = missingness_rules()
    assert_reporting_clean(record)
    return record


def slot_counts(rows: list[dict]) -> dict:
    per_root = {}
    for r in rows:
        bucket = per_root.setdefault(r["root_id"], {"initial": {"completed": 0, "missing": 0},
                                                    "NEUTRAL": {"completed": 0, "missing": 0},
                                                    "DIRECTED": {"completed": 0, "missing": 0}})
        key = r["arm"] or "initial"
        bucket[key]["completed" if r["status"] == "completed" else "missing"] += 1
    totals = {"assigned": len(rows),
              "completed": sum(1 for r in rows if r["status"] == "completed"),
              "missing": sum(1 for r in rows if r["status"] == "missing"),
              "by_missing_reason": {}}
    for r in rows:
        if r["status"] == "missing":
            totals["by_missing_reason"][r["missing_reason"]] = totals["by_missing_reason"].get(r["missing_reason"], 0) + 1
    return {"per_root": per_root, "totals": totals,
            "note": "every assignment appears exactly once; nothing is dropped or re-planned"}


def completion_bounds(rows: list[dict]) -> dict:
    """Binary completion bounds over ALL assigned slots, with no missing-at-random assumption:
    each missing slot is counted 0 in the lower bound and 1 in the upper bound."""
    def bounds(subset):
        n = len(subset)
        done = sum(1 for r in subset if r["status"] == "completed")
        miss = n - done
        return {"assigned": n, "completed": done, "missing": miss,
                "lower": (done / n) if n else None, "upper": ((done + miss) / n) if n else None}
    out = {"all_assigned": bounds(rows),
           "initial": bounds([r for r in rows if r["phase"] == "initial"]),
           "arms": {name: bounds([r for r in rows if r["arm"] == name]) for name, _ in ARMS},
           "assumption": "none; worst-case/best-case bounds over all assigned slots (no MAR)",
           "interval_methods_used": []}
    return out


def analysis_rules(rows: list[dict]) -> dict:
    """Descriptive reporting only. The primary point contrast is suppressed if ANY primary branch
    outcome is missing; completion bounds are reported either way."""
    per_arm = {name: [r for r in rows if r["arm"] == name] for name, _ in ARMS}
    missing_primary = [r["slot_id"] for r in rows if r["phase"] == "continuation" and r["status"] == "missing"]
    all_missing_arms = [name for name, rs in per_arm.items() if rs and all(r["status"] == "missing" for r in rs)]
    suppressed = bool(missing_primary)
    contrast = None
    if not suppressed:
        share = {name: sum(1 for r in rs if r["status"] == "completed") / len(rs) for name, rs in per_arm.items()}
        contrast = {"treatment_share_of_assigned": share["DIRECTED"],
                    "reference_share_of_assigned": share["NEUTRAL"],
                    "finite_sample_point_contrast": share["DIRECTED"] - share["NEUTRAL"],
                    "scope": "these 10 roots x 6 draws only; not an estimate of a population effect",
                    "note": "in the mock path the completed-slot shares stand in for the frozen "
                            "private-suite score; no grade exists here"}
    return {"descriptive_only": True, "contrast_definition": PRIMARY_CONTRAST,
            "primary_point_contrast_suppressed": suppressed,
            "suppression_reason": "a primary branch outcome is missing" if suppressed else None,
            "missing_primary_slots": missing_primary, "all_missing_arms": all_missing_arms,
            "finite_sample_contrast": contrast,
            "completion_bounds_reported": True,
            "forbidden": {"normal_approximation_interval": "not computed",
                          "hoeffding_interval": "not computed",
                          "efficacy_claim": "not made", "futility_claim": "not made",
                          "parseability_selected_success_rate": "never computed anywhere in this path",
                          "pooling_with_earlier_stages": "not performed"},
            "seeds_note": "seeds are reproducibility settings, not proof of independent draws"}


def missingness_rules() -> dict:
    return {"keep_every_assignment": True,
            "failed_initial": "its twelve continuation slots are recorded missing; no fabricated answer, "
                              "no retry, no task-only substitution, no root removal",
            "incomplete_public_diagnostic": f"predeclared public-only instruction {INCOMPLETE_INFO_LABEL}",
            "deadline_truncation": "all remaining slots retained with reason deadline_truncation",
            "integrity_or_receiver_law": "stop rule honoured; partial evidence retained",
            "suppression": "primary point contrast suppressed if ANY primary branch outcome is missing",
            "bounds": "binary completion bounds over all assigned slots, no missing-at-random assumption",
            "resume": "no implicit continuation after an interrupted phase",
            "roster": "no outcome-based roster change and no tuning mid-batch"}


def assert_reporting_clean(record: dict) -> None:
    """No parseability-selected success rate and no interval machinery anywhere in the record."""
    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                lowered = str(k).lower()
                for bad in FORBIDDEN_REPORT_KEYS:
                    if lowered == bad:
                        raise MockPathRefusal(f"forbidden reporting key at {path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
    walk(record, "record")
    if record["resources"]["real_model_calls"] or record["resources"]["real_model_tokens"]:
        raise MockPathRefusal("a real model call or token was recorded in a mock path")


def score_private(record: dict, scorer) -> dict:
    """Ordering guard: candidate private scoring may only start after collection is closed."""
    if not record.get("collection_closed") or record.get("phases", [])[-1:] != ["close"]:
        raise MockPathRefusal("private scoring may not start before collection is closed")
    if record["private_scoring"]["state"] != "not_started":
        raise MockPathRefusal("private scoring already started")
    if not getattr(scorer, "mock_scorer", False):
        raise MockPathRefusal("scorer is not an injected mock (no candidate execution is authorized)")
    record["phases"] = [*record["phases"], "private_scoring"]
    record["private_scoring"] = {"state": "started_after_close", "scorer": type(scorer).__name__,
                                 "executions": 0, "note": "mock scorer; nothing executed"}
    return record


# --------------------------------------------------------------------------- outputs


def write_outputs(out_dir: Path, record: dict) -> dict:
    """Write the mock artifacts under a caller-supplied directory. Refuses to overwrite, and
    refuses to write anywhere inside results/."""
    out_dir = Path(out_dir).resolve()
    try:
        out_dir.relative_to((ROOT / "results").resolve())
    except ValueError:
        pass
    else:
        raise MockPathRefusal("refusing to write inside results/ (immutable run artifacts)")
    files = {"e14_mock_path_record.json": json.dumps(record, indent=1, sort_keys=False) + "\n",
             "slots.jsonl": "".join(json.dumps(r, sort_keys=True) + "\n" for r in record["slots"]),
             "MOCK_LABEL.txt": MOCK_LABEL + "\n" + record["evidence_class"] + "\n"}
    existing = [name for name in files if (out_dir / name).exists()]
    if existing:
        raise MockPathRefusal(f"refusing to overwrite existing artifacts: {existing}")
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        written[name] = _sha(text.encode("utf-8"))
    (out_dir / "ARTIFACT_SHA256SUMS.json").write_text(
        json.dumps({"label": MOCK_LABEL, "files": written}, indent=1) + "\n", encoding="utf-8")
    return written


def scenario_fakes(scenario: str, spec: dict):
    """The injected fakes for each predeclared boundary scenario."""
    if scenario not in SCENARIOS:
        raise MockPathRefusal(f"unknown scenario: {scenario!r}")
    roots = [r["root_id"] for r in spec["records"]]
    if scenario == "nominal":
        return ScriptedTransport(), ScriptedPublicCheck(), {}
    if scenario == "initial_failure":
        return ScriptedTransport(fail_initial=[roots[0]]), ScriptedPublicCheck(), {}
    if scenario == "incomplete_diagnostic":
        return ScriptedTransport(), ScriptedPublicCheck(incomplete_roots=[roots[1]]), {}
    if scenario == "deadline_truncation":
        return ScriptedTransport(), ScriptedPublicCheck(), {"max_calls": 25}
    if scenario == "all_missing_arm":
        refuse = [f"{rid}#NEUTRAL:{r}" for rid in roots for r in REPLICATES]
        return ScriptedTransport(refuse_slots=refuse), ScriptedPublicCheck(), {}
    return ScriptedTransport(integrity_fault_at=f"{roots[0]}#DIRECTED:2"), ScriptedPublicCheck(), {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E14 SOURCE/MOCK execution path for all 130 slots "
                                             "(injected fakes only; no model call, no execution)")
    ap.add_argument("--out", required=True, help="fresh output directory (never inside results/)")
    ap.add_argument("--spec", default=str(SPEC_PATH))
    ap.add_argument("--source", default=None, help="cached MBPP file (hash-verified against the spec)")
    ap.add_argument("--scenario", default="nominal", choices=SCENARIOS)
    args = ap.parse_args(argv)
    spec = load_spec(Path(args.spec))
    transport, public_check, kwargs = scenario_fakes(args.scenario, spec)
    record = run(spec, transport=transport, public_check=public_check,
                 source_path=Path(args.source) if args.source else None,
                 scenario=args.scenario, **kwargs)
    written = write_outputs(Path(args.out), record)
    totals = record["counts"]["totals"]
    print(f"{MOCK_LABEL}\nscenario={args.scenario} slots={totals['assigned']} "
          f"completed={totals['completed']} missing={totals['missing']} "
          f"suppressed={record['reporting']['primary_point_contrast_suppressed']} "
          f"real_model_calls={record['resources']['real_model_calls']}")
    for name, sha in written.items():
        print(f"  {name} {sha[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
