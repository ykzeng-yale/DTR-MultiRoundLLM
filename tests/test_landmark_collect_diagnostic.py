"""MRL-08: phased diagnostic-v1 collector. Fake receiver only; no network, no model, no candidate execution."""
import copy, hashlib, json, sys, types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "landmark"))
import collect_diagnostic as cd  # noqa: E402

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


TASKS = [{"root_id": f"root{i}", "family_id": f"fam{i}", "prompt": f"Write f for case {i}.", "public_context": "Public examples:\nf(1) == 2"}
         for i in range(7)]


@pytest.fixture
def dm(monkeypatch):
    try:
        module = cd.diagnostic_module()
        module.render_arms  # noqa: B018  (a partially written concurrent module falls back to the stand-in)
        return module
    except (ImportError, AttributeError):
        pass
    head = "Public diagnostic report for the previous answer (execution status is recorded per case):"
    def dbytes(d): return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    def render_arms(base, initial_output, diag):
        prefix = [*base, {"role": "assistant", "content": initial_output}]
        msg = {"role": "user", "content": head + "\n" + dbytes(diag).decode()}
        return {"N0": [*prefix, {"role": "user", "content": "N"}], "S0": [*prefix, {"role": "user", "content": "S0"}],
                "N1": [*prefix, msg, {"role": "user", "content": "N"}], "S1": [*prefix, msg, {"role": "user", "content": "S1"}],
                "R1": [*base, msg, {"role": "user", "content": "R1"}]}
    stand_in = types.SimpleNamespace(SCHEMA="public-diagnostic-v1", DIAGNOSTIC_HEADER=head, N_INSTRUCTION="N", R1_INSTRUCTION="R1",
                                     S1_STRINGS=("a", "b", "c"), diagnostic_bytes=dbytes, render_arms=render_arms)
    monkeypatch.setattr(cd, "diagnostic_module", lambda: stand_in)
    return stand_in


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
                             expected_diagnostics_sha256=sha, adapter=continue_adapter or Fake())
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
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha, adapter=fake)
    with pytest.raises(ValueError, match="expected SHA-256"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=None, adapter=fake)
    assert fake.payloads == [] and not (tmp_path / "C").exists()


def test_continue_refuses_artifact_hash_mismatch(tmp_path, dm):
    cfg = make_config()
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Fake())
    fake = Fake()
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA, root3="0" * 64))
    with pytest.raises(ValueError, match="different initial artifact"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha, adapter=fake)
    # A consistent diagnostic but tampered artifact bytes is refused too (phase-A checksums re-verified).
    sha = write_diagnostics(tmp_path / "diag.json", diagnostics_for(tmp_path / "A", dm.SCHEMA))
    (tmp_path / "A/artifacts/root2.txt").write_text("def f(x):\n    return 2\n")
    with pytest.raises(ValueError, match="changed after completion"):
        cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "diag.json", tmp_path / "C", expected_diagnostics_sha256=sha, adapter=fake)
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
                             expected_diagnostics_sha256=sha, adapter=Fake())
    assert second["phase_attempted_calls"] == 70
    with pytest.raises(ValueError, match="safe artifact file name"):
        cd.assignments(make_config(), [dict(TASKS[0], root_id="mbpp%2F52")])
