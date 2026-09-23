"""Tests for scripts/build_e14_request_plan.py (source only; no receiver, candidate or reference execution).

Every test reads the frozen E12 artifacts and the release package's PUBLIC files. The one test that touches
dev_release_v3/private_specs.jsonl reads its assertion text ONLY to prove that text is absent from the emitted
plan; no grade, score or private execution record is read anywhere, and nothing here is fed into a prompt.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect  # noqa: E402
from experiments.landmark import diagnostic  # noqa: E402

PLAN_PATH = ROOT / "results/e14_request_plan_20260923.json"
PROPOSAL = ROOT / "docs/e14_same_prefix_revision_proposal_20260923.md"
RUN = ROOT / "results/e12_dev_v3_20260922T030255Z"
PKG = ROOT / "experiments/landmark/dev_release_v3"
ROOTS = ["mbpp/918", "mbpp/825", "mbpp/816", "mbpp/895", "mbpp/868", "mbpp/154", "mbpp/651", "mbpp/499", "mbpp/974"]


def _module():
    spec = importlib.util.spec_from_file_location("build_e14_request_plan", ROOT / "scripts/build_e14_request_plan.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _module()


@pytest.fixture(scope="module")
def plan(mod):
    return mod.build()


def test_emitted_plan_matches_a_fresh_build(plan):
    assert PLAN_PATH.exists(), "run scripts/build_e14_request_plan.py --out results/e14_request_plan_20260923.json"
    on_disk = json.loads(PLAN_PATH.read_text())
    assert on_disk == plan


def test_status_is_proposed_not_released(plan):
    for token in ("PROPOSED", "NOT RELEASED", "no receiver call made"):
        assert token in plan["status"]
    assert plan["endpoint_label"] == "e14-endpoint-v1"
    assert plan["budget"]["paid_spend_usd"] == 0


def test_108_slot_shape_and_label_sets(plan):
    assert [r["root_id"] for r in plan["roots"]] == ROOTS
    assert plan["assignment"] == {**plan["assignment"], "n_roots": 9, "n_arms": 2, "replicates_per_cell": 6,
                                 "inclusion_probability": 1.0, "total_calls": 108,
                                 "per_arm_calls": {"NEUTRAL": 54, "DIRECTED": 54},
                                 "order_role": "scheduling_not_assignment"}
    slots = [(r["root_id"], q["arm"], q["replicate"], q["seed_key"])
             for r in plan["roots"] for a in r["arms"].values() for q in a["requests"]]
    assert len(slots) == 108 and len(set(slots)) == 108
    for r in plan["roots"]:
        assert {q["seed_key"] for q in r["arms"]["NEUTRAL"]["requests"]} == {f"N1:{i}" for i in range(2, 8)}
        assert {q["seed_key"] for q in r["arms"]["DIRECTED"]["requests"]} == {f"S1:{i}" for i in range(2, 8)}
    order = plan["scheduling_order"]
    assert len(order) == 108
    assert {(o["root_id"], o["arm"], o["replicate"]) for o in order} == {(s[0], s[1], s[2]) for s in slots}
    # root-balanced: every root's 12 slots are contiguous
    positions = {}
    for i, o in enumerate(order):
        positions.setdefault(o["root_id"], []).append(i)
    for rid, idx in positions.items():
        assert idx == list(range(idx[0], idx[0] + 12)), rid
    assert plan["budget"]["receiver_calls"] == 108
    assert plan["budget"]["max_tokens_per_call"] == 512
    assert plan["budget"]["reserved_completion_tokens"] == 55296


def test_prefix_is_byte_identical_between_arms_and_holds_the_previous_answer(mod, plan):
    config = json.loads((PKG / "config.json").read_text())
    tasks = {json.loads(x)["root_id"]: json.loads(x)
             for x in (PKG / "tasks.jsonl").read_text().splitlines() if x.strip()}
    rows = {json.loads(x)["root_id"]: json.loads(x)
            for x in (RUN / "A/roots.jsonl").read_text().splitlines() if x.strip()}
    diagnostics = diagnostic.strict_json_loads((RUN / "B/diagnostics.json").read_bytes())
    assert config["seed"] == 20260921
    for r in plan["roots"]:
        rid = r["root_id"]
        row = rows[rid]
        text = (RUN / "A" / row["artifact"]).read_bytes()
        assert hashlib.sha256(text).hexdigest() == r["initial_artifact_sha256"] == row["artifact_sha256"]
        arms = diagnostic.render_arms(collect.initial_messages(tasks[rid]), text.decode("utf-8"), diagnostics[rid])
        n1, s1 = arms["N1"][:4], arms["S1"][:4]
        assert n1 == s1
        assert collect.digest(n1) == collect.digest(s1) == r["prefix_messages_sha256"]
        assert r["prefix_message_count"] == 4 and r["prefix_roles"] == ["system", "user", "assistant", "user"]
        assert n1[2] == {"role": "assistant", "content": text.decode("utf-8")}
        shared = diagnostic.diagnostic_message(diagnostics[rid])
        assert n1[3] == s1[3] == shared
        assert hashlib.sha256(shared["content"].encode("utf-8")).hexdigest() == r["diagnostic_message_sha256"]
        assert r["diagnostic_message_bytes"] <= diagnostic.MAX_DIAGNOSTIC_BYTES
        # each full arm message list is the shared prefix plus one differing final turn
        for name in ("NEUTRAL", "DIRECTED"):
            tail = {"role": "user", "content": r["arms"][name]["instruction"] + "\n\n" + plan["contract"]["text"]}
            assert collect.digest([*n1, tail]) == r["arms"][name]["messages_sha256"]
        assert r["arms"]["NEUTRAL"]["messages_sha256"] != r["arms"]["DIRECTED"]["messages_sha256"]


def test_diagnostics_validate_against_the_frozen_public_examples(plan):
    examples = {e["root_id"]: e for e in json.loads((PKG / "public_examples_v3.json").read_text())["cases"]}
    diagnostics = diagnostic.strict_json_loads((RUN / "B/diagnostics.json").read_bytes())
    for r in plan["roots"]:
        ex = examples[r["root_id"]]
        diagnostic.validate_diagnostic(diagnostics[r["root_id"]], ex["entry_point"], ex["cases"])
        assert r["public_case_statuses"] == [c["status"] for c in diagnostics[r["root_id"]]["cases"]]


def test_contract_identity_and_hash_match_the_proposal_bytes(mod, plan):
    text = mod.contract_text(PROPOSAL)
    assert plan["contract"]["text"] == text
    assert plan["contract"]["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert plan["contract"]["label"] == "terminal-output-contract-v1"
    # the exact line is quoted in section 2 of the proposal
    assert ("> `" + text + "`") in PROPOSAL.read_text(encoding="utf-8").splitlines()
    assert plan["proposal"]["sha256"] == hashlib.sha256(PROPOSAL.read_bytes()).hexdigest()
    suffix = "\n\n" + text
    for r in plan["roots"]:
        tails = {name: r["arms"][name]["instruction"] + suffix for name in ("NEUTRAL", "DIRECTED")}
        for name, tail in tails.items():
            assert tail.endswith(suffix)
            assert tail[len(r["arms"][name]["instruction"]):] == suffix
            assert hashlib.sha256(tail.encode("utf-8")).hexdigest() == r["arms"][name]["message4_sha256"]
        # contract bytes are identical in both arms: strip the instruction, what remains is the same object
        assert tails["NEUTRAL"][len(r["arms"]["NEUTRAL"]["instruction"]):] == \
               tails["DIRECTED"][len(r["arms"]["DIRECTED"]["instruction"]):]


def test_directed_string_is_select_s1_of_the_frozen_diagnostic(plan):
    diagnostics = diagnostic.strict_json_loads((RUN / "B/diagnostics.json").read_bytes())
    for r in plan["roots"]:
        diag = diagnostics[r["root_id"]]
        expected = diagnostic.select_s1(diag)
        assert r["arms"]["DIRECTED"]["instruction"] == expected
        assert expected == diagnostic.S1_STRINGS[r["directed_s1_index"]]
        statuses = [c["status"] for c in diag["cases"]]
        if r["directed_s1_index"] == 0:
            assert r["directed_selection"]["trigger_status"] in diagnostic.PAYLOAD_FAILURES
        elif r["directed_s1_index"] == 1:
            assert r["directed_selection"]["trigger_status"] in diagnostic.INCOMPLETE
            assert not any(s in diagnostic.PAYLOAD_FAILURES for s in statuses)
        else:
            assert set(statuses) == {"pass"}
        assert r["arms"]["NEUTRAL"]["instruction"] == diagnostic.N_INSTRUCTION


def test_seeds_are_disjoint_from_every_seed_e12_spent(plan):
    config = json.loads((PKG / "config.json").read_text())
    calls = [json.loads(x) for rel in ("A/calls.jsonl", "C/calls.jsonl")
             for x in (RUN / rel).read_text().splitlines() if x.strip()]
    for r in plan["roots"]:
        spent_labels = sorted({c["seed_key"] for c in calls if c["root_id"] == r["root_id"]})
        assert spent_labels == r["spent_labels"]
        assert spent_labels == ["N0:0", "N0:1", "N1:0", "N1:1", "R1:0", "R1:1", "S0:0", "S0:1", "S1:0", "S1:1",
                                "initial"]
        spent = {k: collect.seeded(config, r["root_id"], k) for k in spent_labels}
        assert spent == r["spent_seeds"]
        new = [q for a in r["arms"].values() for q in a["requests"]]
        for q in new:
            assert q["seed"] == collect.seeded(config, r["root_id"], q["seed_key"])
            assert q["seed_key"] not in spent
            assert q["seed"] not in set(spent.values())
        assert len({q["seed"] for q in new}) == len(new) == 12


def test_refuses_on_a_tampered_artifact_byte(mod, tmp_path):
    run = tmp_path / "e12"
    shutil.copytree(RUN, run, ignore=shutil.ignore_patterns("D"))
    art = run / "A/artifacts/mbpp%2F918.txt"
    art.write_bytes(art.read_bytes() + b"x")
    with pytest.raises(ValueError):
        mod.build(run=run)


def test_refuses_on_a_tampered_contract_quote(mod, tmp_path):
    doc = tmp_path / "proposal.md"
    text = PROPOSAL.read_text(encoding="utf-8")
    doc.write_text(text.replace("## 2. Common terminal-output contract", "## 2. Contract"), encoding="utf-8")
    with pytest.raises(ValueError):
        mod.contract_text(doc)


def test_refuses_a_private_artifact_path(mod):
    with pytest.raises(ValueError):
        mod.assert_public_only(["results/e12_dev_v3_20260922T030255Z/D/grades.jsonl"])
    with pytest.raises(ValueError):
        mod.assert_public_only(["experiments/landmark/dev_release_v3/private_specs.jsonl"])


def test_refuses_to_overwrite(mod, tmp_path):
    out = tmp_path / "plan.json"
    out.write_text("{}")
    with pytest.raises(SystemExit):
        mod.main(["--out", str(out)])
    assert out.read_text() == "{}"


def test_plan_names_only_public_files_and_leaks_no_private_assertion(plan):
    opened = plan["private_information_barrier"]["files_opened"]
    assert plan["private_information_barrier"]["no_private_grade_spec_or_hidden_score_read"] is True
    mod = _module()
    mod.assert_public_only(opened)  # the enumerated list itself passes the private-path screen
    assert any("B/diagnostics.json" in p for p in opened) and any("A/roots.jsonl" in p for p in opened)
    serialized = json.dumps(plan, ensure_ascii=False)
    # private_specs.jsonl assertion text is read here ONLY to prove none of it appears in the plan.
    specs = [json.loads(x) for x in (PKG / "private_specs.jsonl").read_text().splitlines() if x.strip()]
    texts = []
    for s in specs:
        for v in s.values():
            if isinstance(v, str):
                texts.append(v)
            elif isinstance(v, list):
                texts += [x for x in v if isinstance(x, str)]
            elif isinstance(v, dict):
                texts += [x for x in v.values() if isinstance(x, str)]
    assertions = [t for t in texts if "assert" in t]
    assert assertions, "expected private assertion strings to scan against"
    for t in assertions:
        assert t not in serialized
    # no private-artifact PATH is referenced anywhere in the plan
    for path in ("private_specs.jsonl", "D/grades.jsonl", "D/private_execution_records.json", "D/summary.json",
                 "D/grading_attempts.jsonl", "analysis_report.json", "analysis_input.json"):
        assert path not in serialized
    assert not any("/D/" in p or p.endswith("private_specs.jsonl") for p in opened)
