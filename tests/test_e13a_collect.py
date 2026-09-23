"""E13a real two-arm collection driver (scripts/e13a_collect.py) and its shared stage clock.

Every test goes through the ONE entry point, e13a_collect.dispatch, with a fake adapter injected: there is no
separate mock code path. Nothing here contacts a receiver, starts a llama-server, executes a candidate,
reference solution or benchmark program, or writes inside results/. A run with an injected adapter is
transport-only and is never evidence about either arm.
"""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from experiments.landmark import collect  # noqa: E402
from experiments.landmark import collect_diagnostic as cd  # noqa: E402
import e13a_collect as ec  # noqa: E402
import e13a_stage_clock as sc  # noqa: E402
import build_e13a_release as builder  # noqa: E402

FIVE = ["mbpp/288", "mbpp/652", "mbpp/842", "mbpp/863", "mbpp/966"]
ASSIGNED = ["mbpp/842", "mbpp/288", "mbpp/863", "mbpp/966", "mbpp/652"]

pytestmark = pytest.mark.skipif(not (ec.RUN / "B/diagnostics.json").exists() or not ec.PLAN.exists(),
                               reason="E12 run directory or E13a request plan absent")


# ------------------------------------------------------------------ injected fakes (tests only)
class FakeReceiver:
    """A fake transport that answers the guard's metadata calls with E12's own recorded receiver state.

    No socket, no process, no model: it returns canned text. `fail_at`/`abort_at` are 1-based call indices.
    """

    def __init__(self, state, digest, fail_at=None, abort_at=None):
        self.state, self.digest = state, digest
        self.fail_at, self.abort_at = fail_at, abort_at
        self.calls, self.payloads, self.state_reads = 0, [], 0

    def metadata(self, timeout):
        return {"name": "FAKE", "model_path": "/fake/weights.gguf", "digest": self.digest}

    def version(self, timeout):
        return {"version": "fake-build"}

    def definition(self, timeout):
        return {"template": "FAKE", "parameters": {"n_ctx_per_slot": 8192, "total_slots": 1},
                "model_info": {"model_path": "/fake/weights.gguf"}}

    def receiver_state(self, timeout):
        self.state_reads += 1
        return self.state

    def busy_slots(self, timeout):
        return 0

    def generate(self, payload, timeout):
        self.calls += 1
        self.payloads.append(payload)
        if self.abort_at is not None and self.calls == self.abort_at:
            raise KeyboardInterrupt("simulated abort mid-run")
        if self.fail_at is not None and self.calls == self.fail_at:
            raise OSError("simulated transport failure")
        text = f"```python\ndef solution():\n    return {self.calls}\n```\n"
        return {"message": {"content": text}, "done": True, "prompt_eval_count": 11, "eval_count": 7}


@pytest.fixture(scope="module")
def e12_state():
    completion = json.loads((ec.RUN / "C/completion.json").read_text())
    return completion["model_metadata"]["state_before"]


@pytest.fixture(scope="module")
def stage(tmp_path_factory):
    release = tmp_path_factory.mktemp("five-root-bindings") / "e13a_release"
    builder.build(release)
    return ec.load_stage(release_dir=release)


@pytest.fixture(scope="module")
def plan():
    return ec.load_plan()


def fake(e12_state, stage, **kwargs):
    return FakeReceiver(e12_state, stage["release"]["config"]["model_digest"], **kwargs)


def clock_at(start, *, offset=0.0):
    holder = {"wall": start + timedelta(seconds=offset), "mono": 500.0}
    return sc.StageClock.from_start(start, now_utc=lambda: holder["wall"], monotonic=lambda: holder["mono"]), holder


def attestation(tmp_path, stage, *, start_offset=-60, end_offset=3600, name="ownership.json"):
    now = datetime.now(timezone.utc)
    record = {"receiver_base_url": stage["release"]["config"]["base_url"], "server_pid": 4242,
              "server_start_utc": (now - timedelta(seconds=600)).isoformat().replace("+00:00", "Z"),
              "owner_project": "DTR-MultiRoundLLM", "agreement_ref": "docs/mrl18_review_mrl19_20260923.md",
              "recorded_by": "experiments-agent", "recorded_utc": now.isoformat().replace("+00:00", "Z"),
              "exclusive_window_start_utc": (now + timedelta(seconds=start_offset)).isoformat().replace("+00:00", "Z"),
              "exclusive_window_end_utc": (now + timedelta(seconds=end_offset)).isoformat().replace("+00:00", "Z")}
    path = tmp_path / name
    path.write_text(json.dumps(record, indent=1))
    return path


def ledger_lines(out):
    return [json.loads(x) for x in (out / "collect" / ec.LEDGER).read_text().splitlines() if x.strip()]


def calls_lines(out):
    return [json.loads(x) for x in (out / "collect" / "calls.jsonl").read_text().splitlines() if x.strip()]


# ------------------------------------------------------------------ 1. request reconstruction, before dispatch
def test_requests_are_rebuilt_through_the_existing_instruments(stage, plan):
    built = ec.rebuild(stage, plan)
    assert built["checkpoints"] == FIVE
    assert [r["root_id"] for r in built["roots"]] == ASSIGNED
    assert built["gating"]["private_inputs_used_for_gating"] == []
    assert all(c["fresh_messages_equal_e12_initial_request"] and c["r1_messages_equal_both_e12_r1_requests"]
               and c["r1_previous_answer_removed"] and c["new_seeds_disjoint_from_e12_seeds"]
               for c in built["byte_checks"])
    assert sum(len(r["requests"]) for r in built["roots"]) == 60
    for root in built["roots"]:
        assert {(q["arm"], q["replicate"]) for q in root["requests"]} == \
            {("R1", r) for r in range(2, 8)} | {("FRESH", r) for r in range(6)}
        assert all(q["branch_inclusion_probability"] == 1.0 for q in root["requests"])
        assert root["messages"]["FRESH"] == collect.initial_messages(
            next(t for t in stage["package"]["tasks"] if t["root_id"] == root["root_id"]))


def test_mismatched_rendered_message_is_refused_before_any_dispatch(stage, plan, tmp_path, e12_state):
    tampered = copy.deepcopy(plan)
    tampered["roots"][0]["r1_messages_sha256"] = "0" * 64
    tampered["roots"][0]["requests"][0]["messages_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="pinned bytes"):
        ec.dispatch(stage, tampered, tmp_path / "run", adapter=fake(e12_state, stage))
    assert not (tmp_path / "run").exists()


def test_colliding_seed_is_refused_before_any_dispatch(stage, plan, tmp_path, e12_state):
    table = cd.assignments(stage["package"]["config"], stage["package"]["tasks"])
    seeds = {p["root_id"]: p["seeds"] for p in table}
    tampered = copy.deepcopy(plan)
    root = tampered["roots"][0]["root_id"]
    tampered["roots"][0]["requests"][0]["seed"] = seeds[root]["initial"]
    with pytest.raises(ValueError, match="pinned bytes"):
        ec.dispatch(stage, tampered, tmp_path / "run", adapter=fake(e12_state, stage))
    assert not (tmp_path / "run").exists()


def test_absent_and_duplicate_assignments_are_refused(stage, plan, tmp_path, e12_state):
    absent = copy.deepcopy(plan)
    absent["roots"][1]["requests"] = absent["roots"][1]["requests"][:-1]
    with pytest.raises(ValueError, match="pinned bytes"):
        ec.dispatch(stage, absent, tmp_path / "absent", adapter=fake(e12_state, stage))
    duplicate = copy.deepcopy(plan)
    duplicate["roots"][1]["requests"].append(copy.deepcopy(duplicate["roots"][1]["requests"][0]))
    with pytest.raises(ValueError, match="pinned bytes"):
        ec.dispatch(stage, duplicate, tmp_path / "dup", adapter=fake(e12_state, stage))
    twice = copy.deepcopy(plan)
    twice["roots"].append(copy.deepcopy(twice["roots"][0]))
    with pytest.raises(ValueError, match="pinned bytes"):
        ec.dispatch(stage, twice, tmp_path / "root-twice", adapter=fake(e12_state, stage))
    for name in ("absent", "dup", "root-twice"):
        assert not (tmp_path / name).exists()


# ------------------------------------------------------------------ 2. a happy 60-slot transport-only run
@pytest.fixture(scope="module")
def happy(tmp_path_factory, stage, plan, e12_state):
    out = tmp_path_factory.mktemp("e13a-collect") / "run"
    adapter = fake(e12_state, stage)
    clock, _ = clock_at(datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc))
    result = ec.dispatch(stage, plan, out, adapter=adapter, clock=clock)
    return out, result, adapter, clock


def test_happy_run_dispatches_every_assigned_slot_once(happy):
    out, result, adapter, _ = happy
    assert adapter.calls == 60
    assert result["attempted_calls"] == 60 and result["reserved_completion_tokens"] == 30720
    assert result["assigned_slots"] == result["recorded_slots"] == 60
    assert result["slots_with_output"] == 60 and result["slots_missing"] == 0
    assert result["per_arm"] == {"R1": {"assigned": 30, "with_output": 30, "missing": 0},
                                 "FRESH": {"assigned": 30, "with_output": 30, "missing": 0}}
    assert result["retries"] == 0 and result["backfilled_slots"] == 0
    assert result["outcome_driven_stopping"] is False
    assert result["fatal_error"] is None and result["preflight_failure"] is None
    rows = calls_lines(out)
    assert len(rows) == 60
    assert sorted((r["root_id"], r["arm"], r["replicate"]) for r in rows) == \
        sorted((c["root_id"], c["arm"], c["replicate"]) for c in
               json.loads((out / "collect" / "manifest.json").read_text())["schedule"])
    assert len(list((out / "collect" / "artifacts").glob("*.txt"))) == 60


def test_happy_run_is_labelled_transport_only_and_claims_no_measurement(happy):
    out, result, _, _ = happy
    manifest = json.loads((out / "collect" / "manifest.json").read_text())
    assert manifest["evidence_type"] == ec.TRANSPORT_ONLY and manifest["transport_only"] is True
    assert manifest["real_receiver"] is False and "NOT evidence" in manifest["measurement_note"]
    assert manifest["candidate_executions"] == 0 and manifest["paid_api_spend_usd"] == 0
    assert result["receiver_verification"]["status"] == "transport_only_not_a_measurement"
    assert result["receiver_verification"]["efficacy_interpretable"] is False
    # the reused receiver guard still ran and is recorded underneath
    assert result["receiver_verification"]["receiver_guard"]["status"] == "receiver_guard_checks_passed"
    assert result["candidate_executions"] == 0 and result["paid_api_spend_usd"] == 0


def test_dispatched_request_fields_match_e12s_recorded_requests(happy, stage, plan):
    out, _, adapter, _ = happy
    config = stage["release"]["config"]
    e12 = [json.loads(x) for x in (ec.RUN / "C/calls.jsonl").read_text().splitlines() if x.strip()]
    reference = next(c["request"] for c in e12 if c["arm"] == "R1")
    seeds = {(r["root_id"], q["seed_key"]): q["seed"] for r in plan["roots"] for q in r["requests"]}
    for payload in adapter.payloads:
        assert set(payload) == set(reference)  # model / messages / stream / options / sampler
        assert payload["model"] == config["model"] and payload["stream"] is False
        assert set(payload["options"]) == set(reference["options"])
        assert payload["options"]["num_predict"] == config["max_tokens_per_call"] == 512
        assert {k: payload["options"][k] for k in config["decoding"]} == config["decoding"]
        assert payload["sampler"] == config["sampler"]
    for row in calls_lines(out):
        assert row["request"]["options"]["seed"] == seeds[(row["root_id"], row["seed_key"])]
        assert row["request_sha256"] == collect.digest(row["request"])


def test_order_is_root_balanced_scheduling_only(happy):
    out, _, _, _ = happy
    order = json.loads((out / "collect" / "manifest.json").read_text())["schedule"]
    assert len(order) == 60 and all(o["order_role"] == "scheduling_not_assignment" for o in order)
    assert all(o["branch_inclusion_probability"] == 1.0 for o in order)
    for start in range(0, 60, 5):
        assert sorted(o["root_id"] for o in order[start:start + 5]) == FIVE
    assert [r["root_id"] for r in calls_lines(out)] == [o["root_id"] for o in order]


def test_completion_checksums_cover_everything_written(happy):
    out, result, _, _ = happy
    collect_dir = out / "collect"
    written = {p.relative_to(collect_dir).as_posix() for p in
               [*collect_dir.glob("*.json*"), *collect_dir.glob("artifacts/*.txt")]} - {"completion.json"}
    assert set(result["checksums"]) == written
    for rel, sha in result["checksums"].items():
        assert ec.file_sha(collect_dir / rel) == sha
    assert result["stage_sha256"] == ec.file_sha(ec.STAGE)
    assert result["plan_sha256"] == ec.file_sha(ec.PLAN)
    assert result["inputs"]["B/diagnostics.json"] == ec.file_sha(ec.RUN / "B/diagnostics.json")


def test_ledger_records_every_reservation(happy):
    out, result, _, _ = happy
    lines = ledger_lines(out)
    assert [x["event"] for x in lines[:1]] == ["reserved"] and lines[-1]["event"] == "complete"
    assert sum(1 for x in lines if x["event"] == "dispatch_start") == 60
    assert sum(1 for x in lines if x["event"] == "dispatch_result") == 60
    assert result["ledger_lines"] == len(lines) == 122
    assert lines[-1]["attempted_calls"] == 60
    assert all("utc" in x for x in lines)


def test_refuses_to_overwrite_an_existing_collection_directory(happy, stage, plan, e12_state):
    out, _, _, _ = happy
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        ec.dispatch(stage, plan, out, adapter=fake(e12_state, stage))


def test_dispatch_refuses_a_path_inside_results(stage, plan, e12_state):
    with pytest.raises(ValueError, match="immutable results/"):
        ec.dispatch(stage, plan, ec.RESULTS_DIR / "e13a_should_never_exist", adapter=fake(e12_state, stage))
    assert not (ec.RESULTS_DIR / "e13a_should_never_exist").exists()


# ------------------------------------------------------------------ 3. failures keep their slots
def test_transport_failure_mid_run_keeps_every_assigned_slot(tmp_path, stage, plan, e12_state):
    out = tmp_path / "run"
    adapter = fake(e12_state, stage, fail_at=10)
    result = ec.dispatch(stage, plan, out, adapter=adapter)
    assert adapter.calls == 60                      # dispatch continued; no retry, no backfill
    assert result["attempted_calls"] == 60          # the failed attempt is charged, never refunded
    assert result["reserved_completion_tokens"] == 30720
    assert result["recorded_slots"] == 60 and result["slots_missing"] == 1
    assert result["fatal_error"] is None
    rows = calls_lines(out)
    failed = [r for r in rows if r["missing_reason"] is not None]
    assert len(failed) == 1 and failed[0]["attempted"] is True
    assert "simulated transport failure" in failed[0]["missing_reason"]
    assert failed[0]["output"] is None and failed[0]["prompt_tokens"] is None
    assert len(list((out / "collect" / "artifacts").glob("*.txt"))) == 59
    assert result["attempted_calls_with_unknown_usage"] == 1
    assert result["missing_reasons"] == {failed[0]["missing_reason"]: 1}
    slots = {(s["root_id"], s["arm"], s["replicate"]) for s in result["slots"]}
    assert len(slots) == 60
    lines = ledger_lines(out)
    assert sum(1 for x in lines if x["event"] == "dispatch_result") == 60
    assert any(x["event"] == "dispatch_result" and x["missing_reason"] for x in lines)


def test_ledger_survives_an_abort_mid_run(tmp_path, stage, plan, e12_state):
    out = tmp_path / "run"
    adapter = fake(e12_state, stage, abort_at=20)
    result = ec.dispatch(stage, plan, out, adapter=adapter)
    lines = ledger_lines(out)
    assert lines[0]["event"] == "reserved" and lines[-1]["event"] == "complete"
    aborted = next(r for r in lines if r["event"] == "aborted")
    assert "KeyboardInterrupt" in aborted["error"]
    assert sum(1 for x in lines if x["event"] == "dispatch_start") == 20
    assert sum(1 for x in lines if x["event"] == "dispatch_result") == 19
    assert lines[-1]["attempted_calls"] == 20 and lines[-1]["reserved_completion_tokens"] == 20 * 512
    rows = calls_lines(out)
    assert len(rows) == 60 and sum(r["attempted"] for r in rows) == 20
    assert result["recorded_slots"] == 60 and result["slots_missing"] == 41
    assert rows[19]["missing_reason"] == "interrupted_attempt_outcome_unknown"
    assert rows[19]["attempted"] and rows[19]["prompt_tokens"] is None
    assert all(not row["attempted"] for row in rows[20:])
    assert result["attempted_calls_with_unknown_usage"] == 1
    assert (out / "collect" / "completion.json").exists()
    assert (out / sc.CLOCK_FILE).exists()                    # the aborted phase is still charged


# ------------------------------------------------------------------ 4. caps refuse further dispatch
@pytest.mark.parametrize("cap,reason", [({"max_calls": 3}, "call_budget_exhausted"),
                                        ({"max_completion_tokens": 3 * 512}, "completion_token_budget_exhausted")])
def test_cap_exhaustion_refuses_further_dispatch_and_keeps_slots(tmp_path, stage, plan, e12_state, cap, reason):
    tight = {**stage, "caps": {**stage["caps"], **cap}}
    adapter = fake(e12_state, stage)
    result = ec.dispatch(tight, plan, tmp_path / "run", adapter=adapter)
    assert adapter.calls == 3
    assert result["attempted_calls"] == 3 and result["reserved_completion_tokens"] == 3 * 512
    assert result["recorded_slots"] == 60 and result["slots_missing"] == 57
    assert result["missing_reasons"] == {reason: 57}
    assert [r["missing_reason"] for r in calls_lines(tmp_path / "run")][:3] == [None, None, None]
    assert all(r["attempted"] is False for r in calls_lines(tmp_path / "run") if r["missing_reason"] == reason)


def test_ceilings_cannot_be_raised(stage, plan, tmp_path, e12_state):
    for cap in ({"max_calls": 61}, {"max_completion_tokens": 30721}):
        loose = {**stage, "caps": {**stage["caps"], **cap}}
        with pytest.raises(ValueError, match="exceed this stage's ceilings"):
            ec.dispatch(loose, plan, tmp_path / str(cap), adapter=fake(e12_state, stage))
    assert ec.MAX_CALLS == 60 and ec.MAX_RESERVED_COMPLETION_TOKENS == 30720 == 60 * ec.TOKENS_PER_CALL


# ------------------------------------------------------------------ 5. attestation and the real path
def test_expired_attestation_is_refused(tmp_path, stage, plan, e12_state):
    expired = attestation(tmp_path, stage, start_offset=-7200, end_offset=-3600)
    with pytest.raises(ValueError, match="outside the ownership exclusive window"):
        ec.dispatch(stage, plan, tmp_path / "expired", adapter=fake(e12_state, stage), ownership=expired)
    assert not (tmp_path / "expired").exists()
    short = attestation(tmp_path, stage, end_offset=60, name="short.json")  # window shorter than the phase budget
    with pytest.raises(ValueError, match="window ends before this phase's time budget"):
        ec.dispatch(stage, plan, tmp_path / "short", adapter=fake(e12_state, stage), ownership=short)
    assert not (tmp_path / "short").exists()


def test_a_valid_attestation_is_recorded_and_bounds_dispatch(tmp_path, stage, plan, e12_state):
    ownership = attestation(tmp_path, stage)
    result = ec.dispatch(stage, plan, tmp_path / "run", adapter=fake(e12_state, stage), ownership=ownership)
    manifest = json.loads((tmp_path / "run" / "collect" / "manifest.json").read_text())
    assert manifest["attestation"]["sha256"] == ec.file_sha(ownership)
    assert result["attestation_sha256"] == ec.file_sha(ownership)
    assert result["attempted_calls"] == 60
    assert ledger_lines(tmp_path / "run")[0]["attestation_sha256"] == ec.file_sha(ownership)


def test_real_mode_goes_through_the_e12_real_setup_and_refuses_an_injected_adapter(tmp_path, stage, plan, e12_state):
    ownership = attestation(tmp_path, stage)
    # A real call requires its existing stage clock even when the caller tries to inject a fake adapter.
    with pytest.raises((ValueError, FileNotFoundError), match="clock|Clock"):
        ec.dispatch(stage, plan, tmp_path / "real", adapter=fake(e12_state, stage), real=True, ownership=ownership)
    assert not (tmp_path / "real").exists()
    with pytest.raises(ValueError, match="needs an injected adapter"):
        ec.dispatch(stage, plan, tmp_path / "noadapter", adapter=None)
    assert not (tmp_path / "noadapter").exists()


def test_release_bindings_may_not_change_the_request_bytes(tmp_path):
    forged = tmp_path / "forged_release"
    forged.mkdir()
    config = json.loads((ec.PKG / "config.json").read_text())
    config["model"] = "some-other-model"
    (forged / "config.json").write_text(json.dumps(config))
    (forged / "tasks.jsonl").write_bytes((ec.PKG / "tasks.jsonl").read_bytes())
    with pytest.raises(ValueError, match="would change the request bytes"):
        ec.load_stage(release_dir=forged)


@pytest.fixture
def real_bound_fixture(monkeypatch, e12_state):
    """Real guards/adapter, fake external Git/HTTP/model-file boundaries; no model or program executes.

    The temporary release sits under the repository only so verify_freeze's real path checks are exercised.
    Git reads return a fixed snapshot of those test bytes; no Git ref/config is changed.
    """
    (ROOT / "work").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "work", prefix="e13a-real-guard-test-") as directory:
        base = Path(directory)
        release = base / "e13a_release"
        builder.build(release)
        stage = ec.load_stage(release_dir=release)
        monkeypatch.setattr(ec, "E13A_RELEASE", release)
        manifest = json.loads((release / "release_manifest.json").read_text())
        files = [*release.iterdir(), stage["stage_path"], ec.PLAN, ec.RUN / "ARTIFACT_SHA256SUMS.json",
                 ec.PKG / "release_manifest.json", *collect.HERE.glob("*.py"),
                 *(ROOT / p for p in manifest["execution_source_hashes"])]
        blobs = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files if p.is_file()}
        git_reads, requests = [], []

        def git_read(args, *, text=False, **kwargs):
            git_reads.append(args)
            if args == ["git", "rev-parse", "HEAD"]:
                value = ("a" * 40 + "\n").encode()
            elif args == ["git", "rev-parse", "--show-toplevel"]:
                value = (str(ROOT) + "\n").encode()
            elif len(args) == 3 and args[:2] == ["git", "show"]:
                value = blobs[args[2].split(":", 1)[1]]
            else:
                raise AssertionError(f"Unexpected external command: {args}")
            return value.decode() if text else value

        def http(self, endpoint, payload, timeout):
            requests.append((endpoint, copy.deepcopy(payload), timeout))
            if endpoint == "/props":
                return copy.deepcopy(e12_state)
            if endpoint == "/slots":
                return [{"id": i, "is_processing": False} for i in range(e12_state["total_slots"])]
            if endpoint == "/v1/models":
                return {"data": [{"id": stage["release"]["config"]["model"]}]}
            if endpoint == "/v1/chat/completions":
                return {"choices": [{"message": {"content": "def solution():\n    return 0\n"},
                                     "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}
            raise AssertionError(f"Unexpected HTTP endpoint: {endpoint}")

        original_exists = collect.os.path.exists
        monkeypatch.setattr(collect.subprocess, "check_output", git_read)
        monkeypatch.setattr(collect.LlamaServer, "request", http)
        monkeypatch.setattr(collect.os.path, "exists", lambda p: p == e12_state["model_path"] or original_exists(p))
        monkeypatch.setattr(collect.LlamaServer, "weight_digest",
                            staticmethod(lambda p: stage["release"]["config"]["model_digest"]))
        out = base / "run"
        clock = sc.StageClock.from_start(sc.utc_now(), run_dir=out, stage_sha256=stage["stage_sha256"])
        clock.persist(out / sc.CLOCK_FILE)
        with clock.phase("setup"):
            pass  # mock setup receipt only; no receiver or containment starts
        ownership = attestation(base, stage)
        yield {"stage": stage, "out": out, "ownership": ownership, "blobs": blobs,
               "git_reads": git_reads, "requests": requests}


def test_real_true_guard_path_uses_actual_llamaserver_interface(real_bound_fixture, plan):
    f = real_bound_fixture
    result = ec.dispatch(f["stage"], plan, f["out"], real=True, ownership=f["ownership"])
    assert result["real_receiver"] is True  # API mode exercised under mocked external boundaries, not empirical data
    assert result["adapter"] == "LlamaServer"
    assert result["attempted_calls"] == result["slots_with_output"] == result["recorded_slots"] == 60
    assert result["receiver_verification"]["status"] == "receiver_guard_checks_passed"
    generation = [payload for endpoint, payload, _ in f["requests"] if endpoint == "/v1/chat/completions"]
    assert len(generation) == 60
    for payload in generation:
        assert payload["cache_prompt"] is False and payload["max_tokens"] == 512
        assert all(payload[k] == v for k, v in f["stage"]["release"]["config"]["sampler"].items())
    usage = result["http_request_accounting"]
    assert usage["generation_attempts"] == 60
    assert usage["metadata_attempts"] == sum(endpoint != "/v1/chat/completions" for endpoint, _, _ in f["requests"])
    assert usage["metadata_attempts"] <= 31
    assert all(timeout <= 10 for endpoint, _, timeout in f["requests"] if endpoint != "/v1/chat/completions")
    checked = {args[2].split(":", 1)[1] for args in f["git_reads"] if args[:2] == ["git", "show"]}
    assert set(builder.EXECUTION_SOURCES) <= checked


def test_real_guard_refuses_uncommitted_execution_source_before_http(real_bound_fixture, plan):
    f = real_bound_fixture
    f["blobs"]["scripts/e13a_collect.py"] = b"different committed collector"
    with pytest.raises(ValueError, match="differs from committed HEAD"):
        ec.dispatch(f["stage"], plan, f["out"], real=True, ownership=f["ownership"])
    assert not f["requests"]
    assert not (f["out"] / "collect").exists()


def test_real_preflight_refuses_wrong_weight_digest_preserving_all_slots(real_bound_fixture, plan, monkeypatch):
    f = real_bound_fixture
    monkeypatch.setattr(collect.LlamaServer, "weight_digest", staticmethod(lambda p: "0" * 64))
    result = ec.dispatch(f["stage"], plan, f["out"], real=True, ownership=f["ownership"])
    assert result["attempted_calls"] == 0 and result["slots_missing"] == 60
    assert result["recorded_slots"] == 60
    assert "weight digest" in result["preflight_failure"]
    assert not any(endpoint == "/v1/chat/completions" for endpoint, _, _ in f["requests"])


def test_http_metadata_cap_counts_failed_attempts_without_retry():
    class FailingTransport:
        calls = 0

        def request(self, endpoint, payload, timeout):
            self.calls += 1
            assert timeout <= 10
            raise OSError("synthetic HTTP failure")

    adapter = FailingTransport()
    usage = ec.bound_http_requests(adapter, real=True)
    for _ in range(ec.MAX_COLLECTION_METADATA_HTTP):
        with pytest.raises(OSError, match="synthetic HTTP failure"):
            adapter.request("/props", None, 120)
    with pytest.raises(ValueError, match="cap exhausted"):
        adapter.request("/props", None, 120)
    assert adapter.calls == usage["metadata_attempts"] == usage["errors"] == 31
    assert usage["generation_attempts"] == 0


# ------------------------------------------------------------------ 6. the shared stage clock
def test_collection_is_charged_against_the_phase_cap_and_outer_deadline(tmp_path, stage, plan, e12_state):
    start = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)
    clock, holder = clock_at(start)
    result = ec.dispatch(stage, plan, tmp_path / "run", adapter=fake(e12_state, stage), clock=clock)
    manifest = json.loads((tmp_path / "run" / "collect" / "manifest.json").read_text())
    assert result["caps"]["phase_seconds"] == sc.PHASE_CAPS["collection"] == 480
    assert manifest["config"]["max_seconds"] == 480 <= stage["release"]["config"]["max_seconds"]
    assert manifest["caps"]["ceilings"] == {"max_calls": 60, "max_completion_tokens": 30720}
    assert result["stage_clock"]["caps"]["collection"] == 480
    assert result["stage_clock"]["outer_seconds"] == 2700
    assert clock.spent["collection"] >= 0 and clock.spent["setup"] == 0
    persisted = json.loads((tmp_path / "run" / sc.CLOCK_FILE).read_text())
    assert persisted["start_utc"].startswith("2026-09-23T09:00:00")
    assert persisted["spent"]["collection"] == pytest.approx(clock.spent["collection"])


def test_an_exhausted_clock_refuses_before_anything_is_written(tmp_path, stage, plan, e12_state):
    start = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)
    clock, _ = clock_at(start, offset=2700)
    with pytest.raises(sc.CapExhausted, match="collection"):
        ec.dispatch(stage, plan, tmp_path / "run", adapter=fake(e12_state, stage), clock=clock)
    assert not (tmp_path / "run" / "collect").exists()


def test_a_reloaded_clock_does_not_extend_the_outer_deadline(tmp_path, stage, plan, e12_state):
    start = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)
    first, holder = clock_at(start, offset=2695)          # 5 s of the outer budget left
    ec.dispatch(stage, plan, tmp_path / "run", adapter=fake(e12_state, stage), clock=first)
    path = tmp_path / "run" / sc.CLOCK_FILE
    later = {"wall": start + timedelta(seconds=2699), "mono": 900.0}
    reloaded = sc.StageClock.load(path, now_utc=lambda: later["wall"], monotonic=lambda: later["mono"])
    assert reloaded.start_utc == start                   # a separate command reloads the SAME anchor
    assert reloaded.remaining_outer() == pytest.approx(1.0)
    assert reloaded.remaining("collection") == pytest.approx(1.0)
    later["wall"] = start + timedelta(seconds=2701)
    with pytest.raises(sc.CapExhausted, match="outer_deadline"):
        ec.dispatch(stage, plan, tmp_path / "second", adapter=fake(e12_state, stage), clock=reloaded)
    assert not (tmp_path / "second").exists()
    assert json.loads(path.read_text())["outer_seconds"] == 2700


# ------------------------------------------------------------------ 7. the immutable inputs stay immutable
def test_nothing_writes_inside_results_or_the_frozen_release(tmp_path, stage, plan, e12_state):
    def snapshot(base):
        return {p.relative_to(base).as_posix(): ec.file_sha(p) for p in sorted(base.rglob("*")) if p.is_file()}

    before_run, before_pkg = snapshot(ec.RUN), snapshot(ec.PKG)
    ec.dispatch(stage, plan, tmp_path / "run", adapter=fake(e12_state, stage))
    assert snapshot(ec.RUN) == before_run
    assert snapshot(ec.PKG) == before_pkg


def test_cli_rebuild_only_dispatches_nothing(capsys, tmp_path):
    ec.main(["--out", str(tmp_path / "unused"), "--rebuild-only", "--release-dir", str(ec.PKG)])
    printed = json.loads(capsys.readouterr().out)
    assert printed["requests"] == 60 and printed["dispatched"] == 0 and printed["receiver_calls"] == 0
    assert printed["checkpoints"] == FIVE
    assert not (tmp_path / "unused").exists()
