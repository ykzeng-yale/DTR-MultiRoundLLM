#!/usr/bin/env python3
"""Collect ungraded same-prefix outputs; default execution is mock only."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re
import subprocess
import time
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ARMS = ("generic_repair", "history_specific_repair", "independent_restart")
SYSTEM = "Complete the public task. Use only the information supplied in this conversation."
GENERIC = "Reconsider your previous answer against the original task and public information. Return your best complete answer."
TARGETED = {
    "loop": "Review the iteration boundaries and empty-input behavior of your previous answer against the original task and public information. Return your best complete answer.",
    "division": "Review division, rounding, and zero-denominator behavior in your previous answer against the original task and public information. Return your best complete answer.",
    "fallback": "Check whether your previous answer satisfies each requirement in the original task and public information. Resolve any discrepancy and return your best complete answer.",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    return {p.name: file_sha(p) for p in sorted(HERE.glob("*.py"))}


def seeded(config, root_id, label):
    return int(digest([config["seed"], root_id, label])[:15], 16) % (2**31)


def split_for(family_id, config):
    u = int(digest([config["split_seed"], family_id])[:16], 16) / 2**64
    train, dev, _ = config["split_fractions"]
    return "train" if u < train else "development" if u < train + dev else "test"


def assignments(tasks, config):
    seen_roots = set(config["prior_seen_root_ids"])
    seen_families = set(config["prior_seen_family_ids"])
    seen_families.update(t["family_id"] for t in tasks if t["root_id"] in seen_roots)
    result = []
    for task in tasks:
        order = [{"arm": arm, "replicate": r} for arm in ARMS for r in range(config["branch_replicates"])]
        random.Random(seeded(config, task["root_id"], "order")).shuffle(order)
        excluded = task["root_id"] in seen_roots or task["family_id"] in seen_families
        result.append({"root_id": task["root_id"], "family_id": task["family_id"],
                       "split": split_for(task["family_id"], config), "excluded": excluded,
                       "exclusion_reason": "previously_seen_root_or_family" if excluded else None,
                       "branch_order": order,
                       "seeds": {s: seeded(config, task["root_id"], s) for s in ("initial", *(a+":"+str(r) for a in ARMS for r in range(config["branch_replicates"])))}})
    return result


def initial_messages(task):
    # Strict task schema excludes answers, hidden tests, and other grader fields.
    public = "Task:\n" + task["prompt"] + "\n\nPublic information:\n" + task["public_context"]
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": public}]


def branches(base, answer):
    prefix = [*base, {"role": "assistant", "content": answer}]
    feature = "loop" if re.search(r"\b(?:for|while|range)\b", answer) else "division" if "/" in answer else "fallback"
    return prefix, feature, {
        "generic_repair": [*prefix, {"role": "user", "content": GENERIC}],
        "history_specific_repair": [*prefix, {"role": "user", "content": TARGETED[feature]}],
        # Restart deliberately removes the old answer, while retaining exactly the same public task.
        "independent_restart": list(base),
    }


def validate(config, tasks, real=False):
    required = {"schema_version", "protocol_version", "freeze_commit", "model", "model_digest", "server_build",
                "base_url", "seed", "split_seed", "split_fractions", "prior_seen_root_ids", "prior_seen_family_ids",
                "max_calls", "max_completion_tokens", "max_seconds", "max_tokens_per_call", "request_timeout_seconds",
                "max_request_bytes", "decoding", "dataset_sha256", "source_code_sha256", "grading_contract_sha256",
                "dataset_source", "dataset_license", "paid_api_budget_usd", "branch_replicates"}
    if set(config) != required:
        raise ValueError(f"Configuration keys differ: missing={required-set(config)}, extra={set(config)-required}")
    if config["schema_version"] != "landmark-v1" or config["paid_api_budget_usd"] != 0:
        raise ValueError("Unsupported schema or paid budget")
    if type(config["branch_replicates"]) is not int or not 1 <= config["branch_replicates"] <= 4:
        raise ValueError("This bounded harness supports one to four continuations per arm")
    for key in ("seed", "split_seed", "max_calls", "max_completion_tokens", "max_tokens_per_call", "max_request_bytes"):
        v = config[key]
        if type(v) is not int or v < (0 if key in ("seed", "split_seed") else 1):
            raise ValueError(f"Invalid {key}")
    for key in ("max_seconds", "request_timeout_seconds"):
        if type(config[key]) not in (int, float) or not math.isfinite(config[key]) or config[key] <= 0:
            raise ValueError(f"Invalid {key}")
    fractions = config["split_fractions"]
    if len(fractions) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in fractions) or not math.isclose(sum(fractions), 1):
        raise ValueError("Invalid family split fractions")
    for key in ("prior_seen_root_ids", "prior_seen_family_ids"):
        if not isinstance(config[key], list) or any(not isinstance(v, str) or not v for v in config[key]):
            raise ValueError("Prior-seen exclusions must be explicit lists of identifiers")
    d = config["decoding"]
    if set(d) != {"temperature", "top_p", "num_ctx"}:
        raise ValueError("Pin exactly temperature, top_p, and num_ctx")
    if any(type(d[k]) not in (int, float) or not math.isfinite(d[k]) for k in ("temperature", "top_p")) or d["temperature"] < 0 or not 0 < d["top_p"] <= 1 or type(d["num_ctx"]) is not int or d["num_ctx"] < 1:
        raise ValueError("Invalid decoding parameters")
    parsed = urlparse(config["base_url"])
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1") or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("Only a loopback HTTP receiver service is supported")
    if not tasks or len({t.get("root_id") for t in tasks}) != len(tasks):
        raise ValueError("Need nonempty unique roots")
    for task in tasks:
        if set(task) != {"root_id", "family_id", "prompt", "public_context"} or any(not isinstance(v, str) for v in task.values()) or not all(task[k] for k in ("root_id", "family_id", "prompt")):
            raise ValueError("Tasks must contain only root_id, family_id, prompt, public_context")
    if real:
        for key in ("model_digest", "dataset_sha256", "source_code_sha256", "grading_contract_sha256"):
            if not isinstance(config[key], str) or not re.fullmatch(r"[0-9a-f]{64}", config[key]):
                raise ValueError(f"Real collection requires a frozen {key}")
        if config["dataset_sha256"] != digest(tasks) or config["source_code_sha256"] != digest(source_hashes()):
            raise ValueError("Dataset or source differs from freeze")
        if config["freeze_commit"] != "HEAD" and not re.fullmatch(r"[0-9a-f]{40}", config["freeze_commit"]):
            raise ValueError("Real collection requires HEAD or an exact freeze commit")
        for key in ("model", "server_build", "protocol_version", "dataset_source", "dataset_license"):
            if not isinstance(config[key], str) or not config[key] or any(x in config[key].upper() for x in ("MOCK", "REQUIRED", "UNFROZEN", "PLACEHOLDER")):
                raise ValueError(f"Real collection requires {key}")


def verify_freeze(config, tasks, config_path, tasks_path):
    """Resolve HEAD at runtime; compare relevant bytes to committed blobs.

    A committed config says HEAD, avoiding a commit containing its own hash.
    Data, configuration, and executable files must all match that same commit.
    """
    if config_path is None or tasks_path is None:
        raise ValueError("Real mode requires the tracked config and task source paths")
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=HERE, text=True).strip())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    if config["freeze_commit"] not in ("HEAD", head):
        raise ValueError("Current checkout differs from freeze commit")
    paths = [Path(config_path).resolve(), Path(tasks_path).resolve(), *sorted(HERE.glob("*.py"))]
    hashes = {}
    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            frozen = subprocess.check_output(["git", "show", head+":"+relative], cwd=root, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:
            raise ValueError(f"Freeze file is not committed: {relative}") from exc
        if frozen != path.read_bytes():
            raise ValueError(f"Working file differs from freeze: {relative}")
        hashes[relative] = hashlib.sha256(frozen).hexdigest()
    if json.loads(Path(config_path).read_text()) != config or [json.loads(x) for x in Path(tasks_path).read_text().splitlines() if x.strip()] != tasks:
        raise ValueError("Runtime values differ from tracked source files")
    return {"resolved_commit": head, "tracked_file_hashes": hashes}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Endpoint redirects are not allowed")


class Ollama:
    def __init__(self, config):
        self.config = config

    def request(self, endpoint, payload, timeout):
        req = urllib.request.Request(self.config["base_url"].rstrip("/") + endpoint,
              data=None if payload is None else json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(req, timeout=timeout) as response:
            return json.load(response)

    def metadata(self, timeout):
        # One request makes the digest check bounded by the caller's remaining time.
        inventory = self.request("/api/tags", None, timeout)
        matches = [m for m in inventory["models"] if self.config["model"] in (m.get("name"), m.get("model"))]
        if len(matches) != 1:
            raise ValueError("Exact installed receiver not found uniquely")
        return matches[0]

    def version(self, timeout):
        return self.request("/api/version", None, timeout)

    def definition(self, timeout):
        return self.request("/api/show", {"model": self.config["model"]}, timeout)

    def generate(self, payload, timeout):
        return self.request("/api/chat", payload, timeout)


class LlamaServer:
    """Receiver adapter for llama.cpp ``llama-server``, the only receiver installed on this host.

    The collector was written against the Ollama API (``/api/chat``, ``options``, ``num_predict``,
    ``num_ctx``), and Ollama is absent here, so without this adapter a real run cannot reach any
    receiver. It speaks llama-server's OpenAI-compatible ``/v1/chat/completions`` and translates both
    ways, so ``run()`` and its accounting are unchanged.

    Identity is checked, not asserted. ``metadata()`` returns the SHA-256 of the actual weight file
    the server reports loading (for a multi-shard GGUF, the digest of every shard's digest in order),
    so ``run()``'s comparison against the frozen ``model_digest`` fails if the weights change.
    ``version()`` returns ``/props`` ``build_info``.

    Two properties are enforced rather than trusted:
      * ``num_ctx`` cannot be set per request on llama-server; it is the per-slot context fixed at
        launch (``-c`` divided by ``-np``). The adapter fails closed if the frozen ``num_ctx`` differs
        from the server's actual per-slot ``n_ctx``.
      * ``cache_prompt`` is disabled. Prompt caching changes batch composition, which llama.cpp does
        not guarantee to be bit-reproducible; branches restored from a common prefix must not differ
        because one of them happened to hit the cache.
    """

    def __init__(self, config):
        self.config = config
        self._props = None

    def request(self, endpoint, payload, timeout):
        req = urllib.request.Request(self.config["base_url"].rstrip("/") + endpoint,
              data=None if payload is None else json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(req, timeout=timeout) as response:
            return json.load(response)

    def props(self, timeout):
        self._props = self.request("/props", None, timeout)
        return self._props

    @staticmethod
    def weight_digest(model_path):
        path = os.path.realpath(model_path)
        m = re.match(r"(.*-)(\d{5})-of-(\d{5})\.gguf$", path)
        if not m:
            return file_sha(path)
        total = int(m.group(3))
        shards = [os.path.realpath(f"{m.group(1)}{i:05d}-of-{m.group(3)}.gguf") for i in range(1, total + 1)]
        return digest([file_sha(s) for s in shards])

    def metadata(self, timeout):
        props = self.props(timeout)
        model_path = props.get("model_path")
        if not model_path or not os.path.exists(model_path):
            raise ValueError("Receiver does not report a readable model_path")
        alias = os.path.basename(model_path)
        if self.config["model"] not in (alias, props.get("model_alias"), os.path.splitext(alias)[0]):
            # accept the configured alias only if it names the loaded file
            models = self.request("/v1/models", None, timeout).get("data", [])
            if not any(self.config["model"] == m.get("id") for m in models):
                raise ValueError("Exact installed receiver not found uniquely")
        return {"name": self.config["model"], "model_path": model_path,
                "digest": self.weight_digest(model_path)}

    def version(self, timeout):
        return {"version": (self._props or self.props(timeout)).get("build_info")}

    def definition(self, timeout):
        props = self._props or self.props(timeout)
        gen = props.get("default_generation_settings") or {}
        return {"template": props.get("chat_template"),
                "parameters": {"n_ctx_per_slot": gen.get("n_ctx"), "total_slots": props.get("total_slots")},
                "model_info": {"model_path": props.get("model_path")}}

    def generate(self, payload, timeout):
        props = self._props or self.props(timeout)
        opts = payload.get("options", {})
        slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
        if opts.get("num_ctx") != slot_ctx:
            raise ValueError(f"Frozen num_ctx={opts.get('num_ctx')} differs from the server's per-slot n_ctx={slot_ctx}")
        body = {"messages": payload["messages"], "stream": False, "cache_prompt": False,
                "temperature": opts["temperature"], "top_p": opts["top_p"],
                "max_tokens": opts["num_predict"], "seed": opts["seed"]}
        out = self.request("/v1/chat/completions", body, timeout)
        choice = (out.get("choices") or [{}])[0]
        usage = out.get("usage") or {}
        finish = choice.get("finish_reason")
        # Translate to the Ollama shape run() expects. A length-capped reply is complete as a
        # response (Ollama also reports done=true with done_reason=length); run() separately
        # enforces the completion-token cap.
        return {"message": {"role": "assistant", "content": (choice.get("message") or {}).get("content")},
                "done": finish in ("stop", "length"), "done_reason": finish,
                "prompt_eval_count": usage.get("prompt_tokens"), "eval_count": usage.get("completion_tokens"),
                "llama_server_raw": {"id": out.get("id"), "model": out.get("model"), "finish_reason": finish}}


def detect_receiver(config, timeout=5.0):
    """Pick the adapter for whichever loopback receiver is actually serving base_url."""
    probe = LlamaServer(config)
    try:
        props = probe.props(timeout)
        if isinstance(props, dict) and "build_info" in props and "default_generation_settings" in props:
            return probe
    except Exception:
        pass
    return Ollama(config)


class Mock:
    def metadata(self, timeout):
        return {"name": "MOCK", "digest": "MOCK"}

    def version(self, timeout):
        return {"version": "MOCK"}

    def definition(self, timeout):
        return {"template": "MOCK", "parameters": "MOCK", "model_info": {"tokenizer": "MOCK"}}

    def generate(self, payload, timeout):
        return {"message": {"content": "MOCK OUTPUT: no empirical outcome."}, "done": True,
                "prompt_eval_count": 0, "eval_count": 0}


def run(config, tasks, output, *, real=False, adapter=None, clock=time.monotonic, config_path=None, tasks_path=None):
    validate(config, tasks, real)
    freeze = verify_freeze(config, tasks, config_path, tasks_path) if real else {"resolved_commit": None, "status": "mock_not_frozen"}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    plan = assignments(tasks, config)
    started = clock()
    adapter = adapter if adapter is not None else detect_receiver(config) if real else Mock()
    manifest = {"schema_version": "landmark-v1", "evidence_type": "ungraded_real_collection" if real else "mock_transport_only",
        "config": config, "config_sha256": digest(config), "dataset_sha256": digest(tasks), "source_hashes": source_hashes(),
        "source_code_sha256": digest(source_hashes()), "freeze": freeze, "tasks": tasks, "assignment_table": plan,
        "assignment_table_sha256": digest(plan), "planned_calls": (1 + 3*config["branch_replicates"]) * sum(not p["excluded"] for p in plan),
        "design": "All three branches are collected; inclusion probability one. Order is randomized, not treatment assignment.",
        "system": SYSTEM, "generic_renderer": GENERIC, "targeted_renderer": TARGETED,
        "limits": ["No hidden grades or candidate execution in collector", "Syntactic feedback scaffold, not validated semantic personalization",
            "Completion-token reservation is hard; input tokens are measured separately", "No tokenizer/truncation certification; real feasibility must audit context handling",
            "Client deadline prevents dispatch; timed-out server computation may continue", "Branch noise independence and server statelessness require audit"]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    attempted = reserved = 0
    fatal = None
    metadata = {}
    rows = []
    calls = []

    def remaining():
        return config["max_seconds"] - (clock() - started)

    def metadata_call(method):
        if remaining() <= 0:
            raise TimeoutError("Run deadline reached before metadata request")
        return method(min(config["request_timeout_seconds"], remaining()))

    try:
        metadata["before"] = metadata_call(adapter.metadata)
        metadata["version"] = metadata_call(adapter.version)
        metadata["definition"] = metadata_call(adapter.definition)
        if real and (metadata["before"].get("digest") != config["model_digest"] or metadata["version"].get("version") != config["server_build"]):
            raise ValueError("Receiver digest or server build differs from freeze")
    except Exception as exc:
        fatal = f"preflight: {type(exc).__name__}: {exc}"
    preflight_failure = fatal

    def generate(messages, p, arm, replicate=0):
        nonlocal attempted, reserved, fatal
        seed_key = "initial" if arm == "initial" else arm+":"+str(replicate)
        payload = {"model": config["model"], "messages": messages, "stream": False,
                   "options": {**config["decoding"], "num_predict": config["max_tokens_per_call"], "seed": p["seeds"][seed_key]}}
        rec = {"root_id": p["root_id"], "arm": arm, "replicate": replicate, "request": payload, "request_sha256": digest(payload),
               "attempted": False, "output": None, "output_sha256": None, "missing_reason": None,
               "prompt_tokens": None, "completion_tokens": None, "seconds": 0.0}
        reason = fatal
        if reason is None and remaining() <= 0: reason = "time_budget_exhausted"
        if reason is None and attempted >= config["max_calls"]: reason = "call_budget_exhausted"
        if reason is None and reserved + config["max_tokens_per_call"] > config["max_completion_tokens"]: reason = "completion_token_budget_exhausted"
        if reason is None and len(json.dumps(payload, ensure_ascii=False).encode()) > config["max_request_bytes"]: reason = "request_byte_cap"
        begin = clock()
        if reason is None:
            attempted += 1
            reserved += config["max_tokens_per_call"]  # Never refund: includes timed-out/uncertain work.
            rec["attempted"] = True
            try:
                response = adapter.generate(payload, min(config["request_timeout_seconds"], remaining()))
                rec["response"] = response
                text = response.get("message", {}).get("content")
                if response.get("done") is not True or not isinstance(text, str) or not text.strip():
                    raise ValueError("Incomplete or empty response")
                for name, key in (("prompt_tokens", "prompt_eval_count"), ("completion_tokens", "eval_count")):
                    value = response.get(key)
                    if type(value) is not int or value < 0:
                        raise ValueError("Missing or invalid token accounting")
                    rec[name] = value
                if rec["completion_tokens"] > config["max_tokens_per_call"]:
                    fatal = "server_violated_completion_token_cap"
                    raise ValueError("Server violated completion-token cap")
                rec["output"], rec["output_sha256"] = text, digest(text)
            except Exception as exc:
                reason = f"generation: {type(exc).__name__}: {exc}"
        rec["seconds"] = clock() - begin
        rec["missing_reason"] = reason
        calls.append(rec)
        with (output / "calls.jsonl").open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    for task, p in zip(tasks, plan):
        row = {**p, "config_sha256": manifest["config_sha256"], "arms": {}}
        if p["excluded"]:
            row["status"] = "excluded_before_collection"
        else:
            base = initial_messages(task)
            initial = generate(base, p, "initial")
            row["initial"] = initial
            row["arms"]["stop"] = [{"replicate": 0, "output": initial["output"], "output_sha256": initial["output_sha256"],
                                   "missing_reason": initial["missing_reason"], "attempted": False,
                                   "prompt_tokens": 0, "completion_tokens": 0, "seconds": 0.0}]
            if initial["output"] is None:
                for arm in ARMS:
                    row["arms"][arm] = [{"replicate": r, "output": None, "output_sha256": None, "missing_reason": "initial_output_unavailable",
                                        "attempted": False, "prompt_tokens": 0, "completion_tokens": 0, "seconds": 0.0} for r in range(config["branch_replicates"])]
                row["status"] = "initial_failed"
            else:
                prefix, feature, messages = branches(base, initial["output"])
                row.update({"landmark_prefix": prefix, "landmark_prefix_sha256": digest(prefix), "feedback_feature": feature,
                            "public_information_sha256": digest(base), "branch_inclusion_probability": 1.0})
                for arm in ARMS:
                    row["arms"][arm] = []
                for entry in p["branch_order"]:
                    arm, replicate = entry["arm"], entry["replicate"]
                    row["arms"][arm].append(generate(messages[arm], p, arm, replicate))
                for arm in ARMS:
                    row["arms"][arm].sort(key=lambda a: a["replicate"])
                row["status"] = "outputs_complete" if all(a["output"] is not None for arm in row["arms"].values() for a in arm) else "outputs_missing"
        rows.append(row)
        with (output / "roots.jsonl").open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        metadata["after"] = metadata_call(adapter.metadata)
        metadata["digest_unchanged"] = metadata["after"].get("digest") == metadata.get("before", {}).get("digest")
    except Exception as exc:
        metadata["postflight_error"] = f"{type(exc).__name__}: {exc}"
        metadata["digest_unchanged"] = None
    completion = {"attempted_calls": attempted, "reserved_completion_tokens": reserved,
        "measured_prompt_tokens": sum(c["prompt_tokens"] or 0 for c in calls),
        "measured_completion_tokens": sum(c["completion_tokens"] or 0 for c in calls),
        "attempted_calls_with_unknown_usage": sum(c["attempted"] and (c["prompt_tokens"] is None or c["completion_tokens"] is None) for c in calls),
        "wall_seconds": clock() - started, "model_metadata": metadata, "preflight_failure": preflight_failure, "fatal_error": fatal,
        "assigned_roots": sum(not p["excluded"] for p in plan), "excluded_roots": sum(p["excluded"] for p in plan),
        "paid_api_spend_usd": 0, "candidate_executions": 0,
        "checksums": {p.name: file_sha(p) for p in sorted(output.glob("*.json*"))}}
    (output / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    return completion


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--real", action="store_true", help="Explicit real local receiver mode; freeze checks required")
    p.add_argument("--print-freeze", action="store_true", help="Print hashes only; no connection or collection")
    args = p.parse_args()
    config = json.loads(args.config.read_text())
    tasks = [json.loads(line) for line in args.tasks.read_text().splitlines() if line.strip()]
    if args.print_freeze:
        print(json.dumps({"dataset_sha256": digest(tasks), "source_code_sha256": digest(source_hashes()), "source_hashes": source_hashes(), "assignment_table": assignments(tasks, config)}, indent=2))
    elif args.output is None:
        p.error("--output is required for collection")
    else:
        print(json.dumps(run(config, tasks, args.output, real=args.real, config_path=args.config, tasks_path=args.tasks), indent=2))


if __name__ == "__main__":
    main()
