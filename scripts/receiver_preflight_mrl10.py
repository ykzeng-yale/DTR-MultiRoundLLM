#!/usr/bin/env python3
"""MRL-10 / E9: bounded NON-GENERATING preflight on the existing receiver. Preparation only, not a release.

Hard limits (lead MRL-10): at most 50 loopback HTTP requests, 10 s timeout each, no retries; only GET /props,
GET /slots, GET /v1/models and POST /apply-template. No completion/chat/generation endpoint, no POST /props, no
server start/restart. If any slot is busy, it stops (respecting existing jobs) and records the blocker.

Renders all six arm message structures (initial, N0, S0, N1, S1, R1) for the seven built v2 tasks with DECLARED
synthetic initial answers and DECLARED public-diagnostic fixtures. Actual future conversation bytes cannot exist
before generation; these are template fixtures, kept separate from later actual-request hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect, diagnostic  # noqa: E402

MAX_REQUESTS, TIMEOUT = 50, 10.0
ALLOWED = {("GET", "/props"), ("GET", "/slots"), ("GET", "/v1/models"), ("POST", "/apply-template")}
LOOP_CUE_ROOTS = {"mbpp/357", "mbpp/402", "mbpp/509"}  # declared: exercises both S0 branches (loop cue / fallback)
DIAG_PATTERN = {  # declared synthetic diagnostic per root; exercises all three S1 strings
    "mbpp/52": "first_wrong", "mbpp/357": "first_wrong", "mbpp/373": "all_pass", "mbpp/378": "all_pass",
    "mbpp/402": "incomplete", "mbpp/489": "first_wrong", "mbpp/509": "incomplete"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Budget:
    def __init__(self, base_url):
        self.base, self.count, self.log = base_url.rstrip("/"), 0, []

    def call(self, method, path, body=None):
        if (method, path) not in ALLOWED:
            raise ValueError(f"Endpoint not permitted by MRL-10: {method} {path}")
        if self.count >= MAX_REQUESTS:
            raise RuntimeError("Request budget (50) exhausted")
        self.count += 1  # charged before sending; never refunded, never retried
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        t0 = time.monotonic()
        entry = {"n": self.count, "method": method, "path": path, "request_sha256": sha(data) if data else None,
                 "utc": datetime.now(timezone.utc).isoformat()}
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({}), collect.NoRedirect()).open(req, timeout=TIMEOUT) as r:
                raw = r.read()
            entry.update(status="ok", response_sha256=sha(raw), seconds=time.monotonic() - t0)
            self.log.append(entry)
            return raw, data
        except Exception as exc:
            entry.update(status=f"error: {type(exc).__name__}: {exc}", seconds=time.monotonic() - t0)
            self.log.append(entry)
            raise


def synthetic_initial(entry_point, args, root_id):
    body = "    for _ in range(1):\n        pass\n" if root_id in LOOP_CUE_ROOTS else ""
    return f"```python\ndef {entry_point}({', '.join(args)}):\n{body}    return None\n```"


def synthetic_diag(root_id, initial_sha, ex):
    pattern, cases = DIAG_PATTERN[root_id], ex["cases"]
    def ok(c):
        v = diagnostic.literal(c["expected_literal"])
        return {"status": "pass", "returned": v, "value_kind": "int_list" if isinstance(v, list) else "int", "reason": None}
    wrong = {"status": "wrong_value", "returned": -12345, "value_kind": "int", "reason": None}
    if pattern == "all_pass":
        results = [ok(c) for c in cases]
    elif pattern == "first_wrong":
        results = [wrong] + [ok(c) for c in cases[1:]]
    else:  # incomplete: active case timed out, later cases not attempted
        results = [{"status": "timeout", "returned": None, "value_kind": "none", "reason": None}] + [
            {"status": "unavailable", "returned": None, "value_kind": "none", "reason": "not_attempted_after_termination"}
            for _ in cases[1:]]
    return diagnostic.build_diagnostic(root_id, initial_sha, ex["entry_point"], cases, results)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", type=Path, required=True, help="built v2 tasks.jsonl")
    ap.add_argument("--examples", type=Path, default=ROOT / "docs/public_diagnostic_examples_v1.json")
    ap.add_argument("--base-url", default="http://127.0.0.1:8193")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite an existing preflight directory")
    started, t0 = datetime.now(timezone.utc).isoformat(), time.monotonic()
    tasks = [diagnostic.strict_json_loads(l) for l in a.tasks.read_text().splitlines() if l.strip()]
    examples = {e["root_id"]: e for e in diagnostic.strict_json_loads(a.examples.read_bytes())["cases"]}
    a.out.mkdir(parents=True)
    (a.out / "rendered").mkdir()
    b = Budget(a.base_url)
    summary = {"schema": "mrl10-e9-nongenerating-preflight-v1", "started_utc": started, "base_url": a.base_url,
               "tasks_sha256": sha(a.tasks.read_bytes()), "examples_sha256": sha(a.examples.read_bytes()),
               "limits": {"max_requests": MAX_REQUESTS, "timeout_seconds": TIMEOUT, "retries": 0, "endpoints": sorted(map(list, ALLOWED))},
               "declared_fixtures": {"loop_cue_roots": sorted(LOOP_CUE_ROOTS), "diagnostic_pattern": DIAG_PATTERN,
                                     "note": "synthetic initial answers and diagnostics; not receiver outputs"}}
    try:
        raw, _ = b.call("GET", "/slots")
        (a.out / "slots_before.json").write_bytes(raw)
        slots = json.loads(raw)
        busy = sum(bool(s.get("is_processing")) for s in slots) if isinstance(slots, list) else None
        summary["slots_before"] = {"count": len(slots) if isinstance(slots, list) else None, "busy": busy}
        if busy != 0:
            summary["blocker"] = f"receiver busy or /slots unverifiable (busy={busy}); stopped to respect existing jobs"
            return finish(a, b, summary, t0)
        raw, _ = b.call("GET", "/props")
        (a.out / "props_before.json").write_bytes(raw)
        state = collect.receiver_state(json.loads(raw))
        summary["receiver_state_sha256_before"] = collect.digest(state)
        summary["build_info"], summary["model_path"] = state["build_info"], state.get("model_path")
        summary["weight_digest"] = collect.LlamaServer.weight_digest(state["model_path"])  # local file hash, not HTTP
        tmpl = json.loads((ROOT / "experiments/landmark/dev_release_v2_template/config.template.json").read_text())
        summary["sampler_differences_vs_template"] = collect.sampler_differences(tmpl["sampler"], state["default_generation_settings"]["params"])
        raw, _ = b.call("GET", "/v1/models")
        (a.out / "models.json").write_bytes(raw)
        fixtures = []
        for task in tasks:
            rid = task["root_id"]
            ex = examples[rid]
            entry = ex["entry_point"]
            # declared parameter names: the task's own public interface line
            sig = task["public_context"].split("def ", 1)[1].split("):", 1)[0]
            params = [p.strip() for p in sig.split("(", 1)[1].split(",") if p.strip()]
            initial = synthetic_initial(entry, params, rid)
            initial_sha = sha(initial.encode())
            diag = synthetic_diag(rid, initial_sha, ex)
            base = collect.initial_messages(task)
            arms = {"initial": base, **diagnostic.render_arms(base, initial, diag)}
            for arm, msgs in arms.items():
                raw, req = b.call("POST", "/apply-template", {"messages": msgs})
                prompt = json.loads(raw).get("prompt")
                name = f"{rid.replace('/', '%2F')}__{arm}"
                (a.out / "rendered" / f"{name}.request.json").write_bytes(req)
                (a.out / "rendered" / f"{name}.prompt.txt").write_text(prompt if isinstance(prompt, str) else "")
                fixtures.append({"root_id": rid, "arm": arm, "messages_sha256": collect.digest(msgs), "request_sha256": sha(req),
                                 "rendered_prompt_sha256": sha((prompt or "").encode()),
                                 "system_message_present": bool(prompt and collect.SYSTEM in prompt),
                                 "default_qwen_system_absent": bool(prompt and "You are Qwen, created by Alibaba Cloud" not in prompt),
                                 "user_turns": (prompt or "").count("<|im_start|>user"),
                                 "assistant_turns_before_generation_prompt": (prompt or "").count("<|im_start|>assistant") - 1,
                                 "synthetic_initial_sha256": initial_sha, "synthetic_diagnostic_sha256": sha(diagnostic.diagnostic_bytes(diag))})
        summary["template_fixtures"] = fixtures
        raw, _ = b.call("GET", "/props")
        (a.out / "props_after.json").write_bytes(raw)
        after = collect.receiver_state(json.loads(raw))
        summary["receiver_state_sha256_after"] = collect.digest(after)
        summary["state_drift_fields"] = collect.state_drift(state, after)
        raw, _ = b.call("GET", "/slots")
        (a.out / "slots_after.json").write_bytes(raw)
        slots = json.loads(raw)
        summary["slots_after"] = {"busy": sum(bool(s.get("is_processing")) for s in slots) if isinstance(slots, list) else None}
    except Exception as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
    return finish(a, b, summary, t0)


def finish(a, b, summary, t0):
    summary.update(requests_made=b.count, request_log=b.log, wall_seconds=time.monotonic() - t0,
                   finished_utc=datetime.now(timezone.utc).isoformat(), generation_requests=0, model_calls=0)
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: summary.get(k) for k in ("requests_made", "blocker", "error", "receiver_state_sha256_before",
                      "receiver_state_sha256_after", "state_drift_fields", "sampler_differences_vs_template", "wall_seconds")}, indent=1))
    return summary


if __name__ == "__main__":
    main()
