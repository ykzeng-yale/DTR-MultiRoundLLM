#!/usr/bin/env python3
"""Bounded fixed-slate logging smoke test. Not a neural critic or LLM study."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SLATE = [
    {"id": "stop", "text": None},
    {"id": "retry", "text": "Try again. Reconsider your answer and end with FINAL: followed by one integer."},
    {"id": "verify", "text": "Check the calculation and any possible mistake. End with FINAL: followed by one integer."},
    {"id": "decompose", "text": "Break the task into smaller steps, solve each, and check the combined result. End with FINAL: followed by one integer."},
]
SYSTEM = "Solve the user's task. You may explain briefly. End with FINAL: followed by one integer."


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def request(base, endpoint, payload=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(base + endpoint, data=data, headers={"Content-Type": "application/json"})
    # Do not route a loopback run through a configured external HTTP proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as response:
        return json.load(response)


def score(text, answer):
    matches = re.findall(r"^FINAL:\s*(-?\d+)\s*$", text.strip(), flags=re.MULTILINE)
    return int(len(matches) == 1 and int(matches[0]) == answer)


def validate(config, tasks):
    if not isinstance(config["temperature"], (int, float)) or not math.isfinite(config["temperature"]) or config["temperature"] < 0:
        raise ValueError("Temperature must be finite and nonnegative")
    for key in ("seed", "horizon", "max_calls", "max_seconds", "num_predict", "num_ctx"):
        if not isinstance(config[key], int) or isinstance(config[key], bool) or config[key] < (0 if key == "seed" else 1):
            raise ValueError(f"Invalid {key}")
    if config["horizon"] > 6:
        raise ValueError("Smoke harness supports at most six decisions")
    probs = config["selection_probabilities"]
    if len(probs) != len(SLATE) or not all(isinstance(p, (int, float)) and math.isfinite(p) and p > 0 for p in probs):
        raise ValueError("Every slate entry needs a finite, positive probability")
    if not math.isclose(sum(probs), 1, abs_tol=1e-12):
        raise ValueError("Selection probabilities must sum to one")
    if not tasks or len({x["task_id"] for x in tasks}) != len(tasks):
        raise ValueError("Tasks must have unique IDs")
    for task in tasks:
        if not isinstance(task["prompt"], str) or not isinstance(task["answer"], int) or not task["family_id"]:
            raise ValueError("Invalid fixture task")
    if config["max_calls"] < len(tasks) * (config["horizon"] + 1):
        raise ValueError("Call budget must cover every planned task before collection starts")
    parsed = urlparse(config["base_url"])
    if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1") or parsed.username or parsed.password:
        raise ValueError("Only a local HTTP Ollama service is permitted")
    if config["paid_api_budget_usd"] != 0:
        raise ValueError("This harness does not support paid services")


def run(config, tasks, out, dry_run=False):
    validate(config, tasks)
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    rng = random.Random(config["seed"])
    base = config["base_url"].rstrip("/")
    model = config["model"]

    def metadata_request(endpoint, payload=None):
        remaining = config["max_seconds"] - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("Run deadline reached; metadata request skipped")
        return request(base, endpoint, payload, min(60, remaining))
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
    except subprocess.CalledProcessError:
        revision = "uncommitted-initial-development"
    manifest = {"schema_version": "0.1", "evidence_type": "synthetic_smoke" if dry_run else "collector_feasibility",
                "config": config, "config_sha256": digest(config), "tasks_sha256": digest(tasks),
                "code_revision": revision, "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "system_message": SYSTEM, "slate": SLATE, "generator_id": "fixed-slate-v1",
                "planned_tasks": len(tasks), "max_planned_calls": len(tasks) * (config["horizon"] + 1),
                "limitations": ["Fixed templates; no trained critic or free-form generator", "Arithmetic fixtures are harness checks",
                                "Full history sent; production tokenization/truncation audit remains required",
                                "Client deadline stops new dispatch; server cancellation after a timeout is not guaranteed"]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not dry_run:
        try:
            inventory = metadata_request("/api/tags")
            candidates = [m for m in inventory["models"] if m["name"] == model or m.get("model") == model]
            if len(candidates) != 1:
                raise ValueError("Pin the exact locally installed model name, including tag")
            manifest["receiver_metadata"] = candidates[0]
            manifest["service_version"] = metadata_request("/api/version")
            manifest["receiver_definition"] = metadata_request("/api/show", {"model": model})
        except Exception as exc:
            manifest["preflight_error"] = f"{type(exc).__name__}: {exc}"
            (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            raise
    calls = 0
    input_tokens = 0
    output_tokens = 0
    failure_count = 0
    tasks_completed = 0
    unstarted = []
    calls_file = (out / "calls.jsonl").open("x")
    trajectories_file = (out / "trajectories.jsonl").open("x")

    def generate(messages, task_id, stage):
        nonlocal calls, input_tokens, output_tokens
        remaining = config["max_seconds"] - (time.monotonic() - started)
        if calls >= config["max_calls"] or remaining <= 0:
            raise RuntimeError("Run budget exhausted")
        payload = {"model": model, "messages": messages, "stream": False,
                   "options": {"seed": rng.randrange(2**31), "temperature": config["temperature"],
                               "num_predict": config["num_predict"], "num_ctx": config["num_ctx"]}}
        calls += 1
        row = {"task_id": task_id, "stage": stage, "call_index": calls, "request": payload}
        begin = time.monotonic()
        try:
            response = {"message": {"content": "FINAL: 0"}, "done": True, "prompt_eval_count": 0, "eval_count": 0} if dry_run else request(base, "/api/chat", payload, min(120, remaining))
            row["response"] = response
            input_tokens += response.get("prompt_eval_count", 0)
            output_tokens += response.get("eval_count", 0)
            if not response.get("done") or not isinstance(response.get("message", {}).get("content"), str):
                raise ValueError("Incomplete or malformed receiver response")
            return response["message"]["content"]
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            row["seconds"] = time.monotonic() - begin
            calls_file.write(json.dumps(row, ensure_ascii=False) + "\n")
            calls_file.flush()

    try:
        for task_index, task in enumerate(tasks):
            if time.monotonic() - started >= config["max_seconds"]:
                unstarted = [t["task_id"] for t in tasks[task_index:]]
                break
            messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task["prompt"]}]
            row = {"task_id": task["task_id"], "family_id": task["family_id"], "root_id": task["task_id"],
                   "evidence_type": manifest["evidence_type"], "steps": [], "initial_request": task["prompt"],
                   "status": "assigned", "selected_stop": False}
            answer_text = ""
            try:
                answer_text = generate(messages, task["task_id"], 0)
                row["initial_response"] = answer_text
                messages.append({"role": "assistant", "content": answer_text})
                for stage in range(1, config["horizon"] + 1):
                    probabilities = config["selection_probabilities"]
                    selected = rng.choices(range(len(SLATE)), weights=probabilities)[0]
                    step = {"stage": stage, "history": list(messages), "history_sha256": digest(messages),
                            "candidate_slate": SLATE, "candidate_slate_sha256": digest(SLATE),
                            "selection_probabilities": probabilities, "selected_index": selected,
                            "selected_probability": probabilities[selected], "generator_id": "fixed-slate-v1"}
                    row["steps"].append(step)
                    if selected == 0:
                        row["selected_stop"] = True
                        row["status"] = "stopped"
                        break
                    messages.append({"role": "user", "content": SLATE[selected]["text"]})
                    answer_text = generate(messages, task["task_id"], stage)
                    step["response"] = answer_text
                    messages.append({"role": "assistant", "content": answer_text})
                else:
                    row["status"] = "horizon_reached"
                row["quality"] = score(answer_text, task["answer"])
            except Exception as exc:
                failure_count += 1
                row["status"] = "execution_failure"
                row["error"] = f"{type(exc).__name__}: {exc}"
                row["quality"] = 0
            row["final_response"] = answer_text
            row["quality_rule"] = "strict-single-FINAL-integer; execution failure scores zero"
            trajectories_file.write(json.dumps(row, ensure_ascii=False) + "\n")
            trajectories_file.flush()
            tasks_completed += 1
    finally:
        calls_file.close()
        trajectories_file.close()
        manifest["realized"] = {"attempted_calls": calls, "input_tokens": input_tokens, "output_tokens": output_tokens,
                                "assigned_tasks": tasks_completed, "failed_tasks": failure_count, "unstarted_task_ids": unstarted,
                                "wall_seconds": time.monotonic() - started, "paid_api_spend_usd": 0}
        if not dry_run:
            try:
                end_models = metadata_request("/api/tags")["models"]
                end_model = next(m for m in end_models if m["name"] == model or m.get("model") == model)
                manifest["receiver_digest_unchanged"] = end_model["digest"] == manifest["receiver_metadata"]["digest"]
            except Exception as exc:
                manifest["receiver_digest_unchanged"] = None
                manifest["postflight_error"] = f"{type(exc).__name__}: {exc}"
        manifest["output_checksums"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.jsonl")}
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(json.loads(args.config.read_text()), [json.loads(s) for s in args.tasks.read_text().splitlines() if s], args.output, args.dry_run)
    print(json.dumps({"evidence_type": result["evidence_type"], **result["realized"]}, indent=2))
