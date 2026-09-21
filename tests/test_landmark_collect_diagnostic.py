"""MRL-08: phased diagnostic-v1 collector. Fake receiver only; no network, no model, no candidate execution."""
import copy, hashlib, json, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect_diagnostic as cd  # noqa: E402

collect = cd.collect  # the exact module object the collector uses (isinstance checks against collect.Mock)
PARAMS = {"seed": 4294967295, "temperature": 0.8, "top_k": 40, "top_p": 0.95, "min_p": 0.05, "typical_p": 1.0,
          "top_n_sigma": -1.0, "xtc_probability": 0.0, "repeat_penalty": 1.0, "repeat_last_n": 64,
          "presence_penalty": 0.0, "frequency_penalty": 0.0, "dry_multiplier": 0.0, "mirostat": 0,
          "samplers": ["penalties", "dry", "top_n_sigma", "top_k", "typ_p", "top_p", "min_p", "xtc", "temperature"]}


def props():
    return {"build_info": "b1-fake", "chat_template": "{{ system }}", "total_slots": 1, "is_sleeping": False,
            "default_generation_settings": {"n_ctx": 8192, "params": copy.deepcopy(PARAMS)}}


class Fake:
    """Receiver double: `mutate_after` = number of generate calls after which the /props state drifts."""

    def __init__(self, mutate_after=None, fail_every=None, busy=0):
        self.mutate_after, self.fail_every, self.busy = mutate_after, fail_every, busy
        self.payloads = []

    def _props(self):
        p = props()
        if self.mutate_after is not None and len(self.payloads) >= self.mutate_after:
            p["chat_template"] = "{{ changed }}"
        return p

    def metadata(self, timeout): return {"name": "fake", "digest": "d" * 64}
    def version(self, timeout): return {"version": "b1-fake"}
    def definition(self, timeout): return {"template": "{{ system }}", "parameters": {}, "model_info": {}}
    def receiver_state(self, timeout): return collect.receiver_state(self._props())
    def busy_slots(self, timeout): return self.busy

    def generate(self, payload, timeout):
        self.payloads.append(payload)
        if self.fail_every and len(self.payloads) % self.fail_every == 0:
            raise ConnectionError("receiver dropped the request")
        return {"message": {"content": f"def f(x):\n    return x + {len(self.payloads)}"}, "done": True,
                "prompt_eval_count": 40, "eval_count": 20}


def make_config(**over):
    cfg = json.loads((ROOT / "experiments/landmark/mock_config.json").read_text())
    cfg.update(schema_version="landmark-v2", sampler={k: PARAMS[k] for k in collect.PINNED_SAMPLER},
               receiver_state_sha256=collect.digest(collect.receiver_state(props())), branch_replicates=2,
               max_calls=77, max_completion_tokens=39424, max_tokens_per_call=512, max_request_bytes=65536, max_seconds=1200)
    if "sampler_law" in getattr(collect, "V2_KEYS", ()):
        cfg["sampler_law"] = "server_defaults_pinned"
    cfg.update(over)
    return cfg


PUBLIC_CASES = [{"case_id": "c1", "args_literal": "[1]", "expected_literal": "2"}]
TASKS = [{"root_id": f"root{i}", "family_id": f"fam{i}", "prompt": f"Write f for case {i}.",
          "public_context": "Public examples (inputs and required outputs):\nf(1) == 2"} for i in range(7)]


def public_for(tasks):
    return {t["root_id"]: {"entry_point": "f", "cases": copy.deepcopy(PUBLIC_CASES)} for t in tasks}


@pytest.fixture
def dm():
    return cd.diagnostic_module()  # the real renderer/validator (no stand-in: validation must run)


def diagnostics_for(initial_dir, schema, **override_sha):
    out = {}
    for line in (Path(initial_dir) / "roots.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row.get("artifact_sha256"):
            out[row["root_id"]] = {"schema_version": schema, "root_id": row["root_id"],
                                   "initial_artifact_sha256": override_sha.get(row["root_id"], row["artifact_sha256"]),
                                   "cases": [{"case_id": "c1", "call": "f(1)", "expected": 2, "status": "wrong_value",
                                              "returned": 3, "value_kind": "int", "reason": None}]}
    return out


def write_diagnostics(path, diags):
    path.write_text(json.dumps(diags, sort_keys=True))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_both(tmp_path, dm, cfg=None, initial_adapter=None, continue_adapter=None):
    cfg = cfg or make_config()
    first = cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=initial_adapter or Fake())
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA))
    second = cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C",
                             expected_diagnostics_sha256=sha, public_examples=public_for(TASKS), adapter=continue_adapter or Fake())
    return first, second


def calls(path):
    return [json.loads(x) for x in (path / "calls.jsonl").read_text().splitlines()]


def test_seventy_seven_planned_calls_and_full_reservation(tmp_path, dm):
    a, b = Fake(), Fake()
    first, second = run_both(tmp_path, dm, initial_adapter=a, continue_adapter=b)
    assert first["planned_calls"] == second["planned_calls"] == {"initial": 7, "continue": 70, "total": 77}
    assert (first["attempted_calls"], first["phase_attempted_calls"]) == (7, 7)
    assert (second["attempted_calls"], second["phase_attempted_calls"], len(b.payloads)) == (77, 70, 70)
    assert second["reserved_completion_tokens"] == 39424 == 77 * 512
    # MRL-06: a passing guard is the narrow collect.py status and never grants efficacy interpretation.
    for v in (first["receiver_verification"], second["receiver_verification"]):
        assert v == collect.receiver_verification(None, None, {"postflight_drift_fields": [], "digest_unchanged": True}, None, None, True)
        assert v["status"] == "receiver_guard_checks_passed" and "efficacy_interpretable" not in v
    assert first["model_metadata"]["receiver_guard_limits"] == list(collect.GUARD_LIMITS)
    assert first["model_metadata"]["sampler_overrides"] == {} and first["model_metadata"]["lease"] == collect.LEASE
    rows = [json.loads(x) for x in (tmp_path / "C/roots.jsonl").read_text().splitlines()]
    assert all(r["status"] == "outputs_complete" and set(r["arms"]) == set(cd.DIAG_ARMS) and r["branch_inclusion_probability"] == 1.0
               for r in rows)
    # Every continuation's request carries the arm's rendered messages; R1 omits the previous answer.
    for rec in calls(tmp_path / "C"):
        roles = [m["role"] for m in rec["request"]["messages"]]
        assert ("assistant" in roles) == (rec["arm"] != "R1")
    assert second["candidate_executions"] == 0


def test_seeds_differ_across_arms_and_replicates(tmp_path, dm):
    run_both(tmp_path, dm)
    recs = calls(tmp_path / "A") + calls(tmp_path / "C")
    by_root = {}
    for r in recs:
        by_root.setdefault(r["root_id"], {})[r["seed_key"]] = r["request"]["options"]["seed"]
    for root, seeds in by_root.items():
        assert set(seeds) == {"initial", *(f"{a}:{i}" for a in cd.DIAG_ARMS for i in range(2))}
        assert len(set(seeds.values())) == 11
        assert all(v == collect.seeded(make_config(), root, k) for k, v in seeds.items())
    orders = {tuple((e["arm"], e["replicate"]) for e in p["branch_order"]) for p in cd.assignments(make_config(), TASKS)}
    assert len(orders) > 1  # randomized scheduling differs across roots


def test_continue_refuses_changed_diagnostics_file(tmp_path, dm):
    cfg = make_config()
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Fake())
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA))
    (tmp_path / "diag.json").write_text((tmp_path / "diag.json").read_text() + " ")
    fake = Fake()
    with pytest.raises(ValueError, match="bound SHA-256"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha, public_examples=public_for(TASKS), adapter=fake)
    with pytest.raises(ValueError, match="expected SHA-256"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=None, adapter=fake)
    assert fake.payloads == [] and not (tmp_path / "C").exists()


def test_continue_refuses_artifact_hash_mismatch(tmp_path, dm):
    cfg = make_config()
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Fake())
    fake = Fake()
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA, root3="0" * 64))
    with pytest.raises(ValueError, match="different initial artifact"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha, public_examples=public_for(TASKS), adapter=fake)
    # A consistent diagnostic but tampered artifact bytes is refused too (phase-A checksums re-verified).
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA))
    (tmp_path / "A/artifacts/root2.txt").write_text("def f(x):\n    return 2\n")
    with pytest.raises(ValueError, match="changed after completion"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha, public_examples=public_for(TASKS), adapter=fake)
    assert fake.payloads == [] and not (tmp_path / "C").exists()


def test_drift_within_continue_stops_dispatch_and_keeps_outputs(tmp_path, dm):
    fake = Fake(mutate_after=15)  # drifts after the second root's 10 calls began; detected before the next root
    first, second = run_both(tmp_path, dm, continue_adapter=fake)
    assert second["fatal_error"].startswith("receiver_drift_before_")
    assert second["phase_attempted_calls"] == len(fake.payloads) == 20  # two full roots, then no dispatch
    recs = calls(tmp_path / "C")
    assert len(recs) == 70 and sum(r["output"] is not None for r in recs) == 20
    assert all(r["missing_reason"].startswith("receiver_drift_before_") for r in recs if not r["attempted"])
    assert second["receiver_verification"]["efficacy_interpretable"] is False
    assert second["receiver_verification"]["status"] == "receiver_not_verified_outputs_retained"


def test_drift_between_phases_blocks_continue_dispatch(tmp_path, dm):
    fake = Fake(mutate_after=0)  # state already differs from phase A at the A/C boundary
    first, second = run_both(tmp_path, dm, continue_adapter=fake)
    assert "receiver_drift_between_phases" in second["preflight_failure"] and fake.payloads == []
    assert second["receiver_verification"]["status"] == "preflight_failed_no_dispatch"
    assert (tmp_path / "A/artifacts/root0.txt").exists() and first["attempted_calls"] == 7  # phase A outputs kept


def test_budgets_never_refunded_across_phases(tmp_path, dm):
    cfg = make_config(max_calls=40)
    fake = Fake(fail_every=3)  # failed/uncertain calls still consume call and token budget
    first, second = run_both(tmp_path, dm, cfg=cfg, continue_adapter=fake)
    assert second["attempted_calls"] == 40 and second["reserved_completion_tokens"] == 40 * 512
    assert len(fake.payloads) == 33  # 40 minus the 7 initial calls carried from phase A
    recs = calls(tmp_path / "C")
    assert sum(r["attempted"] and r["output"] is None for r in recs) == 11
    assert sum(r["missing_reason"] == "call_budget_exhausted" for r in recs) == 70 - 33
    # Token reservation binds independently of the call cap.
    cfg = make_config(max_completion_tokens=10 * 512)
    _, second = run_both(tmp_path / "t", dm, cfg=cfg)
    assert second["attempted_calls"] == 10 and second["reserved_completion_tokens"] == 5120
    assert sum(r["missing_reason"] == "completion_token_budget_exhausted" for r in calls(tmp_path / "t/C")) == 67


def test_initial_phase_writes_artifacts_bound_by_sha(tmp_path, dm):
    first = cd.run_initial(make_config(), TASKS, tmp_path / "A", adapter=Fake())
    rows = [json.loads(x) for x in (tmp_path / "A/roots.jsonl").read_text().splitlines()]
    for row in rows:
        data = (tmp_path / "A" / row["artifact"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["artifact_sha256"] and data.decode() == row["initial"]["output"]
    assert "artifacts/root0.txt" in first["checksums"] and len(first["model_metadata"]["interim_checks"]) == 7


def test_real_root_ids_with_slash_are_collected(tmp_path, dm):
    # The dev release roots are "mbpp/52" etc.; the artifact file name encodes "/" and stays inside artifacts/.
    tasks = [dict(t, root_id=f"mbpp/{50 + i}") for i, t in enumerate(TASKS)]
    first = cd.run_initial(make_config(), tasks, tmp_path / "A", adapter=Fake())
    rows = [json.loads(x) for x in (tmp_path / "A/roots.jsonl").read_text().splitlines()]
    assert [r["artifact"] for r in rows] == [f"artifacts/mbpp%2F{50 + i}.txt" for i in range(7)]
    assert all(f"artifacts/mbpp%2F{50 + i}.txt" in first["checksums"] for i in range(7))
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA))
    second = cd.run_continue(make_config(), tasks, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C",
                             expected_diagnostics_sha256=sha, public_examples=public_for(tasks), adapter=Fake())
    assert second["phase_attempted_calls"] == 70
    with pytest.raises(ValueError, match="safe artifact file name"):
        cd.assignments(make_config(), [dict(TASKS[0], root_id="mbpp%2F52")])


def test_collect_is_one_module_object():
    from experiments.landmark import diagnostic
    assert diagnostic.collect is cd.collect
    assert cd.diagnostic_module() is diagnostic


def test_continue_refuses_extra_diagnostic_field_before_dispatch(tmp_path, dm):
    cfg = make_config()
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Fake())
    diags = diagnostics_for(tmp_path / "A", dm.SCHEMA)
    diags[sorted(diags)[-1]]["cases"][0]["hidden_note"] = "x"  # one extra per-case field in the last root
    sha = write_diagnostics(tmp_path / "diag.json", diags)
    fake = Fake()
    with pytest.raises(ValueError, match="fails validation"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha, public_examples=public_for(TASKS), adapter=fake)
    assert fake.payloads == [] and not (tmp_path / "C").exists()


@pytest.mark.parametrize("field,value", [("call", "assert f(99) == 12345  # PRIVATE HIDDEN TEST"), ("expected", 12345),
                                         ("case_id", "hidden_7"), ("extra_case", None), ("expected_type", None)])
def test_continue_refuses_non_public_case_content_before_dispatch(tmp_path, dm, field, value):
    cfg = make_config()
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Fake())
    diags = diagnostics_for(tmp_path / "A", dm.SCHEMA)
    case = diags[sorted(diags)[-1]]["cases"]
    if field == "extra_case":
        case.append(dict(case[0], case_id="c2", call="f(2)", expected=4, status="pass", returned=None, value_kind="none"))
    elif field == "expected_type":
        case[0]["expected"] = [2]
    else:
        case[0][field] = value
    sha = write_diagnostics(tmp_path / "diag.json", diags)
    fake = Fake()
    with pytest.raises(ValueError, match="fails validation"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C",
                        expected_diagnostics_sha256=sha, public_examples=public_for(TASKS), adapter=fake)
    assert fake.payloads == [] and not (tmp_path / "C").exists()


def test_continue_refuses_public_examples_not_in_the_prompt(tmp_path, dm):
    cfg = make_config()
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Fake())
    diags = diagnostics_for(tmp_path / "A", dm.SCHEMA)
    for d in diags.values():
        d["cases"][0].update(call="f(99)", expected=12345)
    sha = write_diagnostics(tmp_path / "diag.json", diags)
    public = public_for(TASKS)
    for ex in public.values():
        ex["cases"] = [{"case_id": "c1", "args_literal": "[99]", "expected_literal": "12345"}]  # not the prompt's cases
    fake = Fake()
    with pytest.raises(ValueError, match="not the ones rendered"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C",
                        expected_diagnostics_sha256=sha, public_examples=public, adapter=fake)
    with pytest.raises(ValueError, match="public examples"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C",
                        expected_diagnostics_sha256=sha, adapter=fake)
    assert fake.payloads == [] and not (tmp_path / "C").exists()


# ---- MRL-09 real-mode wiring: fakes only; every refusal happens with zero adapter requests ----
from datetime import datetime, timedelta, timezone  # noqa: E402

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _strict_loads(monkeypatch):
    dmod = cd.diagnostic_module()
    if not hasattr(dmod, "strict_json_loads"):  # the 'strict' agent owns it; stand-in only until it lands
        def strict(data):
            def hook(pairs):
                keys = [k for k, _ in pairs]
                if len(keys) != len(set(keys)):
                    raise ValueError("duplicate key")
                return dict(pairs)
            return json.loads(data, object_pairs_hook=hook)
        monkeypatch.setattr(dmod, "strict_json_loads", strict, raising=False)


class NoRequests:
    """LlamaServer stand-in: constructing it is allowed; any request fails the test."""
    constructed = 0

    def __init__(self, config):
        NoRequests.constructed += 1

    def __getattr__(self, name):
        pytest.fail(f"adapter request made: {name}")


def real_config(**over):
    cfg = make_config(model="qwen2.5-coder-7b", model_digest="a" * 64, server_build="b1", grading_contract_sha256="c" * 64,
                      dataset_sha256=collect.digest(TASKS), source_code_sha256=collect.digest(collect.source_hashes()),
                      freeze_commit="HEAD", protocol_version="landmark-v2-diag", dataset_source="mbpp", dataset_license="cc-by-4.0",
                      receiver_state_sha256=collect.digest(collect.receiver_state(props())))
    cfg.update(over)
    return cfg


def ownership(cfg, **over):
    rec = {"receiver_base_url": cfg["base_url"], "server_pid": 4242, "server_start_utc": "2026-09-21T08:00:00Z",
           "owner_project": "DTR-MultiRoundLLM", "exclusive_window_start_utc": "2026-09-21T09:00:00Z",
           "exclusive_window_end_utc": "2026-09-21T18:00:00Z", "agreement_ref": "docs/lead_review_mrl05_08_20260921.md",
           "recorded_by": "experiments", "recorded_utc": "2026-09-21T08:30:00Z"}
    rec.update(over)
    return rec


@pytest.fixture
def realenv(monkeypatch, tmp_path):
    NoRequests.constructed = 0
    freezes = []
    monkeypatch.setattr(collect, "LlamaServer", NoRequests)
    monkeypatch.setattr(collect, "verify_freeze", lambda *a: freezes.append(a) or {"resolved_commit": "f" * 40, "tracked_file_hashes": {}})
    return freezes


def write_own(tmp_path, rec):
    path = tmp_path / "own.json"
    path.write_text(json.dumps(rec))
    return path


def real_initial(tmp_path, cfg, own_path, now=NOW):
    return cd.run_initial(cfg, TASKS, tmp_path / "A", real=True, config_path=tmp_path / "c.json", tasks_path=tmp_path / "t.jsonl",
                          ownership=own_path, now_utc=lambda: now)


def test_complete_ownership_record_passes():
    cfg = real_config()
    assert cd.validate_ownership(ownership(cfg), cfg, NOW) == ownership(cfg)


@pytest.mark.parametrize("over", [{"agreement_ref": "UNRESOLVED: lead signs"}, {"recorded_by": "todo"}, {"owner_project": "placeholder"},
                                  {"recorded_by": ""}, {"server_pid": 0}, {"receiver_base_url": "http://127.0.0.1:9999"},
                                  {"exclusive_window_end_utc": "2026-09-21T11:00:00Z"}, {"server_start_utc": "yesterday"},
                                  {"exclusive_window_start_utc": "2026-09-21T09:00:00"}])
def test_bad_ownership_records_rejected(over):
    cfg = real_config()
    with pytest.raises(ValueError):
        cd.validate_ownership(ownership(cfg, **over), cfg, NOW)


def test_ownership_missing_field_and_window_uses_injected_clock():
    cfg = real_config()
    rec = ownership(cfg)
    del rec["agreement_ref"]
    with pytest.raises(ValueError, match="fields differ"):
        cd.validate_ownership(rec, cfg, NOW)
    with pytest.raises(ValueError, match="outside"):
        cd.validate_ownership(ownership(cfg), cfg, NOW + timedelta(hours=7))
    with pytest.raises(ValueError, match="outside"):
        cd.validate_ownership(ownership(cfg), cfg, NOW - timedelta(hours=4))


@pytest.mark.parametrize("case", ["unresolved", "no_record", "placeholder", "base_url", "window", "freeze", "not_hex", "injected_adapter"])
def test_real_refusals_make_zero_requests(tmp_path, monkeypatch, realenv, case):
    cfg = real_config()
    own = write_own(tmp_path, ownership(cfg))
    now = NOW
    kw = {}
    if case == "unresolved":
        cfg = real_config(server_build="UNRESOLVED: record llama-server build_info")
    elif case == "no_record":
        own = None
    elif case == "placeholder":
        own = write_own(tmp_path, ownership(cfg, agreement_ref="TODO"))
    elif case == "base_url":
        own = write_own(tmp_path, ownership(cfg, receiver_base_url="http://127.0.0.1:1"))
    elif case == "window":
        now = NOW + timedelta(days=1)
    elif case == "freeze":
        monkeypatch.setattr(collect, "verify_freeze", lambda *a: (_ for _ in ()).throw(ValueError("Working file differs from freeze")))
    elif case == "not_hex":
        cfg = real_config(receiver_state_sha256="deadbeef")
    elif case == "injected_adapter":
        kw["adapter"] = NoRequests(cfg)
        NoRequests.constructed = 0
    with pytest.raises(ValueError):
        cd.run_initial(cfg, TASKS, tmp_path / "A", real=True, config_path=tmp_path / "c.json", tasks_path=tmp_path / "t.jsonl",
                       ownership=own, now_utc=lambda: now, **kw)
    assert NoRequests.constructed == 0 and not (tmp_path / "A").exists()


def test_real_refusal_on_duplicate_key_ownership(tmp_path, realenv):
    cfg = real_config()
    path = tmp_path / "own.json"
    path.write_text(json.dumps(ownership(cfg))[:-1] + ', "recorded_by": "someone else"}')
    with pytest.raises(ValueError):
        real_initial(tmp_path, cfg, path)
    assert NoRequests.constructed == 0


def test_real_initial_uses_freeze_and_llamaserver_and_records_ownership(tmp_path, monkeypatch, realenv):
    cfg = real_config()
    own = write_own(tmp_path, ownership(cfg))
    made = []

    class Server(Fake):  # the LlamaServer stand-in that a fully verified real run reaches (fake transport, no network)
        def __init__(self, config):
            super().__init__()
            made.append(config)

    monkeypatch.setattr(collect, "LlamaServer", Server)
    result = real_initial(tmp_path, cfg, own)
    manifest = json.loads((tmp_path / "A" / "manifest.json").read_text())
    assert made == [cfg] and len(realenv) == 1 and realenv[0][2:] == (tmp_path / "c.json", tmp_path / "t.jsonl")
    assert manifest["evidence_type"] == "ungraded_real_collection" and manifest["freeze"]["resolved_commit"] == "f" * 40
    assert manifest["ownership"] == {"sha256": hashlib.sha256(own.read_bytes()).hexdigest(), "record": ownership(cfg)}
    assert result["attempted_calls"] == 7


def test_continue_refuses_duplicate_keys_in_diagnostics(tmp_path, dm):
    cd.run_initial(make_config(), TASKS, tmp_path / "A", adapter=Fake())
    diags = diagnostics_for(tmp_path / "A", dm.SCHEMA)
    text = json.dumps(diags, sort_keys=True)
    first = sorted(diags)[0]
    text = "{" + json.dumps(first) + ": " + json.dumps(diags[first]) + ", " + text[1:]
    (tmp_path / "diag.json").write_text(text)
    sha = hashlib.sha256((tmp_path / "diag.json").read_bytes()).hexdigest()
    fake = Fake()
    with pytest.raises(ValueError):
        cd.run_continue(make_config(), TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C",
                        expected_diagnostics_sha256=sha, public_examples=public_for(TASKS), adapter=fake)
    assert fake.payloads == [] and not (tmp_path / "C").exists()


def test_continue_real_refuses_before_requests(tmp_path, realenv, dm):
    cd.run_initial(make_config(), TASKS, tmp_path / "A", adapter=Fake())
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA))
    cfg = real_config()
    with pytest.raises(ValueError, match="ownership"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha,
                        public_examples=public_for(TASKS), real=True, config_path=tmp_path / "c.json", tasks_path=tmp_path / "t.jsonl",
                        ownership=None, now_utc=lambda: NOW)
    assert NoRequests.constructed == 0 and not (tmp_path / "C").exists()


def test_cli_real_requires_ownership(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["collect_diagnostic", "--phase", "initial", "--config", "c", "--tasks", "t", "--output", "o", "--real"])
    with pytest.raises(SystemExit):
        cd.main()
    assert "--ownership" in capsys.readouterr().err


# --- MRL-09 adversarial findings 10-12 (each demonstrated on fakes before the fix) ---

def _counting_server(monkeypatch):
    class Server(Fake):
        def __init__(self, config):
            super().__init__()
            Server.last = self
    monkeypatch.setattr(collect, "LlamaServer", Server)
    return Server


def test_ownership_window_is_a_dispatch_guard(tmp_path, monkeypatch, realenv):
    cfg = real_config()  # max_seconds must fit inside the window at setup
    end = NOW + timedelta(minutes=35)
    own = write_own(tmp_path, ownership(cfg, exclusive_window_end_utc=end.isoformat().replace("+00:00", "Z")))
    Server = _counting_server(monkeypatch)
    t = [NOW]

    def advancing():  # setup reads NOW+10m; each request then adds 10 minutes of UTC
        t[0] += timedelta(minutes=10)
        return t[0]
    assert cfg["max_seconds"] <= 20 * 60
    result = cd.run_initial(cfg, TASKS, tmp_path / "A", real=True, config_path=tmp_path / "c.json",
                            tasks_path=tmp_path / "t.jsonl", ownership=own, now_utc=advancing)
    assert result["attempted_calls"] == 2 and len(Server.last.payloads) == 2  # the third request would be past the window
    rows = [json.loads(l) for l in (tmp_path / "A" / "calls.jsonl").read_text().splitlines()]
    assert rows[2]["missing_reason"] == "ownership_window_expired" and rows[0]["output"] is not None  # outputs kept


def test_window_shorter_than_time_budget_is_refused_at_setup(tmp_path, realenv):
    cfg = real_config()
    end = NOW + timedelta(seconds=cfg["max_seconds"] - 1)
    own = write_own(tmp_path, ownership(cfg, exclusive_window_end_utc=end.isoformat().replace("+00:00", "Z")))
    with pytest.raises(ValueError, match="time budget"):
        real_initial(tmp_path, cfg, own)
    assert NoRequests.constructed == 0 and not (tmp_path / "A").exists()


def test_real_continue_refuses_a_mock_initial_phase(tmp_path, monkeypatch, realenv, dm):
    cfg = real_config()
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Fake())  # mock transport, same config
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA))
    own = write_own(tmp_path, ownership(cfg))
    Server = _counting_server(monkeypatch)
    with pytest.raises(ValueError, match="real initial phase"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha,
                        public_examples=public_for(TASKS), real=True, config_path=tmp_path / "c.json",
                        tasks_path=tmp_path / "t.jsonl", ownership=own, now_utc=lambda: NOW)
    assert Server.last.payloads == [] and not (tmp_path / "C").exists()


def test_cli_real_refuses_unresolved_bytes_even_behind_a_duplicate_key(tmp_path, monkeypatch):
    cfg = real_config()
    text = json.dumps(cfg)[:-1] + ', "server_build": "b1"}'
    text = text.replace('"server_build": "b1",', '"server_build": "UNRESOLVED: record llama-server build_info",', 1)
    (tmp_path / "c.json").write_text(text)
    (tmp_path / "t.jsonl").write_text("".join(json.dumps(t) + "\n" for t in TASKS))
    (tmp_path / "own.json").write_text(json.dumps(ownership(cfg)))
    monkeypatch.setattr(collect, "LlamaServer", NoRequests)
    NoRequests.constructed = 0
    monkeypatch.setattr(sys, "argv", ["collect_diagnostic", "--phase", "initial", "--config", str(tmp_path / "c.json"),
                                      "--tasks", str(tmp_path / "t.jsonl"), "--output", str(tmp_path / "A"), "--real",
                                      "--ownership", str(tmp_path / "own.json")])
    with pytest.raises(SystemExit):
        cd.main()
    assert NoRequests.constructed == 0 and not (tmp_path / "A").exists()
