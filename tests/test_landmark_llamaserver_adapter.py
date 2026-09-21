"""The llama-server receiver adapter: translation, fail-closed checks, identity. No network."""
import hashlib, json, os, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "landmark"))
import collect  # noqa: E402

PROPS = {"build_info": "b1-4fea119", "model_path": None, "total_slots": 4,
         "chat_template": "{{ system }}", "default_generation_settings": {"n_ctx": 8192}}


def make(tmp_path, model_name="m.gguf", n_ctx=8192):
    f = tmp_path / model_name
    f.write_bytes(b"weights")
    props = {**PROPS, "model_path": str(f), "default_generation_settings": {"n_ctx": n_ctx}}
    a = collect.LlamaServer({"base_url": "http://127.0.0.1:8193", "model": model_name})
    calls = []

    def fake(endpoint, payload, timeout):
        calls.append((endpoint, payload))
        if endpoint == "/props":
            return props
        if endpoint == "/v1/chat/completions":
            return {"id": "x", "model": model_name,
                    "choices": [{"message": {"content": "def f(): return 1"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 40, "completion_tokens": 9}}
        raise AssertionError(endpoint)
    a.request = fake
    return a, calls, f


def payload(num_ctx=8192):
    return {"model": "m.gguf", "messages": [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}],
            "stream": False, "options": {"temperature": 0.7, "top_p": 0.95, "num_ctx": num_ctx,
                                          "num_predict": 256, "seed": 12345}}


def test_translates_request_and_response_into_the_shape_run_expects(tmp_path):
    a, calls, _ = make(tmp_path)
    out = a.generate(payload(), 5)
    endpoint, body = calls[-1]
    assert endpoint == "/v1/chat/completions"
    assert body == {"messages": payload()["messages"], "stream": False, "cache_prompt": False,
                    "temperature": 0.7, "top_p": 0.95, "max_tokens": 256, "seed": 12345}
    assert out["message"]["content"] == "def f(): return 1"
    assert out["done"] is True and out["prompt_eval_count"] == 40 and out["eval_count"] == 9


def test_fails_closed_when_frozen_context_differs_from_the_server(tmp_path):
    a, _, _ = make(tmp_path, n_ctx=8192)
    with pytest.raises(ValueError, match="num_ctx"):
        a.generate(payload(num_ctx=32768), 5)


def test_prompt_cache_is_always_disabled(tmp_path):
    a, calls, _ = make(tmp_path)
    a.generate(payload(), 5)
    assert calls[-1][1]["cache_prompt"] is False


def test_identity_is_the_digest_of_the_actual_weight_file(tmp_path):
    a, _, f = make(tmp_path)
    md = a.metadata(5)
    assert md["digest"] == hashlib.sha256(b"weights").hexdigest()
    assert a.version(5) == {"version": "b1-4fea119"}


def test_multishard_digest_covers_every_shard(tmp_path):
    s1 = tmp_path / "w-00001-of-00002.gguf"; s1.write_bytes(b"one")
    s2 = tmp_path / "w-00002-of-00002.gguf"; s2.write_bytes(b"two")
    got = collect.LlamaServer.weight_digest(str(s1))
    want = collect.digest([hashlib.sha256(b"one").hexdigest(), hashlib.sha256(b"two").hexdigest()])
    assert got == want
    s2.write_bytes(b"CHANGED")
    assert collect.LlamaServer.weight_digest(str(s1)) != want


def test_length_capped_reply_is_complete_but_reported(tmp_path):
    a, calls, _ = make(tmp_path)
    def capped(endpoint, p, t):
        if endpoint == "/props":
            return {**PROPS, "model_path": "x", "default_generation_settings": {"n_ctx": 8192}}
        return {"choices": [{"message": {"content": "partial"}, "finish_reason": "length"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 256}}
    a.request = capped
    out = a.generate(payload(), 5)
    assert out["done"] is True and out["done_reason"] == "length"


def test_detect_receiver_picks_llama_server_only_when_props_look_like_it():
    cfg = {"base_url": "http://127.0.0.1:1", "model": "m"}
    orig = collect.LlamaServer.props
    try:
        collect.LlamaServer.props = lambda self, t: {"build_info": "b", "default_generation_settings": {}}
        assert isinstance(collect.detect_receiver(cfg), collect.LlamaServer)
        collect.LlamaServer.props = lambda self, t: (_ for _ in ()).throw(OSError("refused"))
        assert isinstance(collect.detect_receiver(cfg), collect.Ollama)
    finally:
        collect.LlamaServer.props = orig
