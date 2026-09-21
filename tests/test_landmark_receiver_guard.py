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


def props(model_path, **override):
    p = {"build_info": "b1-4fea119", "model_path": str(model_path), "total_slots": 2, "chat_template": "{{ system }}",
         "bos_token": "", "eos_token": "<|im_end|>", "endpoint_props": False, "is_sleeping": False,
         "default_generation_settings": {"n_ctx": 8192, "params": copy.deepcopy(PARAMS)}}
    p.update(override)
    return p


class FakeServer(collect.LlamaServer):
    """Serves /props, /slots and completions; `script` maps the n-th /props read to a mutation."""

    def __init__(self, config, weights, script=None, busy=0, fail_props_from=None):
        super().__init__(config)
        self.weights, self.script, self.busy, self.fail_from = weights, script or {}, busy, fail_props_from
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
            return [{"id": 0, "is_processing": self.busy > 0}, {"id": 1, "is_processing": self.busy > 1}]
        if endpoint == "/v1/chat/completions":
            self.bodies.append(payload)
            return {"id": "x", "model": "m.gguf", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                    "choices": [{"message": {"content": "def f():\n    return 1"}, "finish_reason": "stop"}]}
        raise AssertionError(endpoint)


def config_v2(weights, **over):
    cfg = json.loads((ROOT / "experiments/landmark/dev_release_v1c/config.json").read_text())
    cfg.update(schema_version="landmark-v2", sampler=dict(SAMPLER), model="m.gguf",
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
    assert out["receiver_verification"]["efficacy_interpretable"] is True
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
