"""MRL-06: landmark-v2 receiver-law guards. Fake receivers only; no network, no model."""
import copy, json, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "landmark"))
import collect  # noqa: E402

# Structure of the real b1-4fea119 /props (sampler defaults as observed 2026-09-21), trimmed.
PARAMS = {"seed": 4294967295, "temperature": 0.8, "top_k": 40, "top_p": 0.95, "min_p": 0.05, "typical_p": 1.0,
          "top_n_sigma": -1.0, "xtc_probability": 0.0, "repeat_penalty": 1.0, "repeat_last_n": 64,
          "presence_penalty": 0.0, "frequency_penalty": 0.0, "dry_multiplier": 0.0, "mirostat": 0,
          "samplers": ["penalties", "dry", "top_n_sigma", "top_k", "typ_p", "top_p", "min_p", "xtc", "temperature"]}
SAMPLER = {k: PARAMS[k] for k in collect.PINNED_SAMPLER}
PASSED = {"status": "receiver_guard_checks_passed", "scope": "sampled receiver-state and idle-slot checks only",
          "efficacy_interpretation": "not granted by the receiver guard; requires the complete release evidence"}


def props(model_path, **override):
    p = {"build_info": "b1-4fea119", "model_path": str(model_path), "total_slots": 2, "chat_template": "{{ system }}",
         "bos_token": "", "eos_token": "<|im_end|>", "endpoint_props": False, "is_sleeping": False,
         "default_generation_settings": {"n_ctx": 8192, "params": copy.deepcopy(PARAMS)}}
    p.update(override)
    return p


class FakeServer(collect.LlamaServer):
    """Serves /props, /slots and completions; `script` maps the n-th /props read to a mutation."""

    def __init__(self, config, weights, script=None, busy=0, fail_props_from=None, slots=None):
        super().__init__(config)
        self.weights, self.script, self.busy, self.fail_from = weights, script or {}, busy, fail_props_from
        self.slots = slots  # if given, served verbatim as /slots (malformed-inventory cases)
        self.props_reads, self.bodies = 0, []

    def request(self, endpoint, payload, timeout):
        if endpoint == "/props":
            self.props_reads += 1
            if self.fail_from is not None and self.props_reads >= self.fail_from:
                raise ConnectionError("receiver gone")
            p = props(self.weights)
            for n, mutate in self.script.items():
                if self.props_reads >= n:
                    mutate(p)
            return p
        if endpoint == "/slots":
            if self.slots is not None:
                return copy.deepcopy(self.slots)
            return [{"id": 0, "is_processing": self.busy > 0}, {"id": 1, "is_processing": self.busy > 1}]
        if endpoint == "/v1/chat/completions":
            self.bodies.append(payload)
            return {"id": "x", "model": "m.gguf", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                    "choices": [{"message": {"content": "def f():\n    return 1"}, "finish_reason": "stop"}]}
        raise AssertionError(endpoint)


def config_v2(weights, **over):
    cfg = json.loads((ROOT / "experiments/landmark/dev_release_v1c/config.json").read_text())
    cfg.update(schema_version="landmark-v2", sampler=dict(SAMPLER), sampler_law="server_defaults_pinned", model="m.gguf",
               receiver_state_sha256=collect.digest(collect.receiver_state(props(weights))))
    cfg.update(over)
    return cfg


def tasks():
    return [json.loads(l) for l in (ROOT / "experiments/landmark/dev_release_v1c/tasks.jsonl").read_text().splitlines() if l.strip()][:3]


@pytest.fixture
def weights(tmp_path):
    f = tmp_path / "m.gguf"
    f.write_bytes(b"weights")
    return f


def go(tmp_path, cfg, server):
    cfg["model_digest"] = server.weight_digest(server.weights)
    return collect.run(cfg, tasks(), tmp_path / "out", adapter=server)


def test_state_excludes_only_volatile_fields_and_sees_sampler_and_template_changes(weights):
    base = collect.digest(collect.receiver_state(props(weights)))
    assert collect.digest(collect.receiver_state(props(weights, is_sleeping=True))) == base
    changed = props(weights)
    changed["default_generation_settings"]["params"]["min_p"] = 0.1
    assert collect.digest(collect.receiver_state(changed)) != base
    assert collect.digest(collect.receiver_state(props(weights, chat_template="{{ other }}"))) != base
    assert collect.digest(collect.receiver_state(props(weights, new_upgrade_field=1))) != base  # fail closed


def test_v2_config_must_pin_every_listed_sampler_setting(weights):
    cfg = config_v2(weights)
    collect.validate(cfg, tasks())
    del cfg["sampler"]["min_p"]
    with pytest.raises(ValueError, match="pins exactly"):
        collect.validate(cfg, tasks())


def test_pinned_sampler_is_sent_in_every_request(tmp_path, weights):
    cfg = config_v2(weights)
    server = FakeServer(cfg, weights)
    out = go(tmp_path, cfg, server)
    assert out["receiver_verification"] == PASSED  # MRL-06: narrow guard status replaces efficacy_interpretable=True
    assert server.bodies and all(b["top_k"] == 40 and b["min_p"] == 0.05 for b in server.bodies)
    assert out["attempted_calls"] == len(server.bodies) == 3 * (1 + 3 * cfg["branch_replicates"])


def test_frozen_state_mismatch_dispatches_nothing(tmp_path, weights):
    cfg = config_v2(weights, receiver_state_sha256="0" * 64)
    server = FakeServer(cfg, weights)
    out = go(tmp_path, cfg, server)
    assert out["attempted_calls"] == 0 and not server.bodies
    assert out["receiver_verification"]["status"] == "preflight_failed_no_dispatch"


def test_busy_receiver_fails_the_lease_check(tmp_path, weights):
    cfg = config_v2(weights)
    out = go(tmp_path, cfg, FakeServer(cfg, weights, busy=1))
    assert out["attempted_calls"] == 0 and "lease check failed" in out["preflight_failure"]


def test_mid_run_drift_stops_future_dispatch_and_keeps_collected_outputs(tmp_path, weights):
    cfg = config_v2(weights)
    per_root = 1 + 3 * cfg["branch_replicates"]
    # /props reads: metadata=1, state_before=2, root1 check=3, root2 check=4 -> drift appears at root 2
    server = FakeServer(cfg, weights, script={4: lambda p: p["default_generation_settings"]["params"].update(top_k=20)})
    out = go(tmp_path, cfg, server)
    assert out["attempted_calls"] == per_root  # root 1 only
    assert "receiver_drift_before_" in out["fatal_error"] and "default_generation_settings" in out["fatal_error"]
    v = out["receiver_verification"]
    assert v["efficacy_interpretable"] is False and v["status"] == "receiver_not_verified_outputs_retained"
    kept = [json.loads(l) for l in (tmp_path / "out/calls.jsonl").read_text().splitlines()]
    assert sum(c["output"] is not None for c in kept) == per_root  # nothing deleted


def test_unverifiable_postflight_marks_evidence_not_interpretable(tmp_path, weights):
    cfg = config_v2(weights)
    n_roots = 3
    # reads: metadata, state_before, 3 root checks -> 5; the postflight metadata read is the 6th
    out = go(tmp_path, cfg, FakeServer(cfg, weights, fail_props_from=2 + n_roots + 1))
    assert out["attempted_calls"] == n_roots * (1 + 3 * cfg["branch_replicates"])
    v = out["receiver_verification"]
    assert v["efficacy_interpretable"] is False and any("postflight_unverifiable" in r for r in v["reasons"])


def test_v1_schema_is_reported_as_partial_guard(tmp_path, weights):
    cfg = json.loads((ROOT / "experiments/landmark/dev_release_v1c/config.json").read_text())
    cfg["model"] = "m.gguf"
    server = FakeServer(cfg, weights)
    out = go(tmp_path, cfg, server)
    assert out["receiver_verification"]["status"] == "v1_partial_guard"
    assert "top_k" not in server.bodies[0]  # v1 request bytes unchanged


# ---- MRL-06 lead counterexamples (docs/lead_review_mrl05_08_20260921.md) ----

@pytest.mark.parametrize("key,value", [
    ("min_p", 2), ("min_p", -0.1), ("min_p", True), ("top_k", 20.5), ("top_k", 20.0), ("top_k", -1), ("top_k", True),
    ("typical_p", 0), ("typical_p", 1.5), ("top_n_sigma", -0.5), ("xtc_probability", 1.5), ("repeat_penalty", 0),
    ("repeat_last_n", -2), ("repeat_last_n", 64.0), ("presence_penalty", 2.5), ("frequency_penalty", float("nan")),
    ("frequency_penalty", -2.01), ("dry_multiplier", -1), ("mirostat", 3), ("mirostat", 1.0), ("mirostat", False),
    ("top_k", "40"), ("min_p", None), ("repeat_penalty", float("inf"))])
def test_sampler_field_domains_reject_counterexamples(weights, key, value):
    cfg = config_v2(weights)
    cfg["sampler"][key] = value
    with pytest.raises(ValueError, match="field domains"):
        collect.validate(cfg, tasks())


def test_sampler_field_domain_boundaries_are_accepted(weights):
    cfg = config_v2(weights)
    cfg["sampler"].update(top_k=0, min_p=1, typical_p=1.0, top_n_sigma=-1, xtc_probability=0, repeat_penalty=1e-6,
                          repeat_last_n=-1, presence_penalty=-2, frequency_penalty=2.0, dry_multiplier=0, mirostat=2)
    collect.validate(cfg, tasks())


def test_sampler_law_is_required_and_closed(weights):
    cfg = config_v2(weights)
    del cfg["sampler_law"]
    with pytest.raises(ValueError, match="keys differ"):
        collect.validate(cfg, tasks())
    with pytest.raises(ValueError, match="sampler_law"):
        collect.validate(config_v2(weights, sampler_law="whatever"), tasks())


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(default_generation_settings=None),
    lambda p: p.pop("default_generation_settings"),
    lambda p: p["default_generation_settings"].update(params=None),
    lambda p: p["default_generation_settings"].update(n_ctx=0),
    lambda p: p["default_generation_settings"].update(n_ctx="8192"),
    lambda p: p["default_generation_settings"]["params"].pop("min_p"),
    lambda p: p["default_generation_settings"]["params"].update(top_k=True),
    lambda p: p["default_generation_settings"]["params"].update(top_k=None),
    lambda p: p["default_generation_settings"]["params"].update(samplers="top_k;min_p"),
    lambda p: p["default_generation_settings"]["params"].update(samplers=["top_k", 3]),
    lambda p: p["default_generation_settings"]["params"].pop("samplers"),
    lambda p: p.update(build_info=""), lambda p: p.update(chat_template=None),
    lambda p: p.update(total_slots=0), lambda p: p.update(total_slots=True), lambda p: p.pop("total_slots")])
def test_null_or_malformed_receiver_state_fails_closed(weights, mutate):
    p = props(weights)
    mutate(p)
    with pytest.raises(ValueError, match="typed state schema"):
        collect.receiver_state(p)


def test_null_generation_settings_at_preflight_dispatch_nothing(tmp_path, weights):
    cfg = config_v2(weights)
    # /props reads: metadata=1, state_before=2 -> the frozen-state read sees null generation settings
    server = FakeServer(cfg, weights, script={2: lambda p: p.update(default_generation_settings=None)})
    out = go(tmp_path, cfg, server)
    assert out["attempted_calls"] == 0 and not server.bodies and "typed state schema" in out["preflight_failure"]
    assert out["receiver_verification"]["status"] == "preflight_failed_no_dispatch"


@pytest.mark.parametrize("slots", [
    [], {}, None, [{"id": 0, "is_processing": False}],                                   # empty / wrong type / short
    [{"id": 0, "is_processing": False}, {"id": 1}],                                        # missing is_processing
    [{"id": 0, "is_processing": False}, {"id": 1, "is_processing": 0}],                    # int, not bool
    [{"id": 0, "is_processing": False}, {"id": "1", "is_processing": False}],              # str id
    [{"id": 0, "is_processing": False}, {"id": True, "is_processing": False}],             # bool id
    [{"id": 0, "is_processing": False}, {"id": 0, "is_processing": False}],                # duplicate id
    [{"id": 0, "is_processing": False}, {"id": 2, "is_processing": False}],                # not 0..n-1
    [{"id": 0, "is_processing": False}, {"id": 1, "is_processing": False}, {"id": 2, "is_processing": False}],
    [{"id": 0, "is_processing": False}, "slot1"]])
def test_empty_or_malformed_slots_are_unverified_not_idle(weights, slots):
    server = FakeServer(config_v2(weights), weights, slots=slots if slots is not None else "not-a-list")
    server.receiver_state(5)  # current state: total_slots=2
    assert server.busy_slots(5) is None


def test_well_formed_slot_inventory_counts_busy_slots(weights):
    server = FakeServer(config_v2(weights), weights, slots=[{"id": 1, "is_processing": True}, {"id": 0, "is_processing": False}])
    server.receiver_state(5)
    assert server.busy_slots(5) == 1


def test_empty_slots_at_preflight_dispatch_nothing(tmp_path, weights):
    cfg = config_v2(weights)
    server = FakeServer(cfg, weights, slots=[])
    out = go(tmp_path, cfg, server)
    assert out["attempted_calls"] == 0 and not server.bodies
    assert "lease check failed: busy slots = None" in out["preflight_failure"]


def test_request_top_k_differing_from_snapshot_fails_under_server_defaults_pinned(tmp_path, weights):
    cfg = config_v2(weights, sampler={**SAMPLER, "top_k": 20})  # snapshot (frozen, matching digest) says top_k=40
    collect.validate(cfg, tasks())
    server = FakeServer(cfg, weights)
    out = go(tmp_path, cfg, server)
    assert out["attempted_calls"] == 0 and not server.bodies
    assert "server_defaults_pinned" in out["preflight_failure"] and "top_k" in out["preflight_failure"]
    v = out["receiver_verification"]
    assert v["status"] == "preflight_failed_no_dispatch" and v["efficacy_interpretable"] is False


def test_request_top_k_differing_from_snapshot_is_recorded_under_declared_override(tmp_path, weights):
    cfg = config_v2(weights, sampler={**SAMPLER, "top_k": 20}, sampler_law="declared_override")
    server = FakeServer(cfg, weights)
    out = go(tmp_path, cfg, server)
    md = out["model_metadata"]
    assert md["sampler_law"] == "declared_override"
    assert md["sampler_overrides"] == {"top_k": {"request": 20, "server_default": 40}}
    assert server.bodies and all(b["top_k"] == 20 for b in server.bodies)
    assert out["receiver_verification"] == PASSED


def test_server_float32_reporting_matches_pinned_request(tmp_path, weights):
    f32 = 0.05000000074505806  # how b1-4fea119 reports min_p=0.05
    assert collect.sampler_differences(SAMPLER, {**PARAMS, "min_p": f32}) == {}
    assert collect.sampler_differences(SAMPLER, {**PARAMS, "min_p": 0.06}) == {"min_p": {"request": 0.05, "server_default": 0.06}}
    assert collect.sampler_differences(SAMPLER, {**PARAMS, "top_k": None})["top_k"]["server_default"] is None
    mutate = lambda p: p["default_generation_settings"]["params"].update(min_p=f32)
    frozen = props(weights)
    mutate(frozen)
    cfg = config_v2(weights, receiver_state_sha256=collect.digest(collect.receiver_state(frozen)))
    out = go(tmp_path, cfg, FakeServer(cfg, weights, script={1: mutate}))
    assert out["receiver_verification"] == PASSED and out["model_metadata"]["sampler_overrides"] == {}


def test_passing_guard_is_narrow_and_records_non_exclusive_lease(tmp_path, weights):
    cfg = config_v2(weights)
    out = go(tmp_path, cfg, FakeServer(cfg, weights))
    v = out["receiver_verification"]
    assert v == PASSED and "efficacy_interpretable" not in v
    assert out["model_metadata"]["lease"] == "sampled_idle_slots_only_not_exclusive"
    assert out["model_metadata"]["receiver_guard_limits"]
    written = (tmp_path / "out/completion.json").read_text()
    assert '"efficacy_interpretable": true' not in written


def test_v1_config_is_unaffected_by_v2_keys(tmp_path, weights):
    cfg = json.loads((ROOT / "experiments/landmark/dev_release_v1c/config.json").read_text())
    cfg["model"] = "m.gguf"
    server = FakeServer(cfg, weights)
    out = go(tmp_path, cfg, server)
    assert not any(k in server.bodies[0] for k in (*collect.PINNED_SAMPLER, "sampler_law"))
    assert "lease" not in out["model_metadata"] and "sampler_overrides" not in out["model_metadata"]
