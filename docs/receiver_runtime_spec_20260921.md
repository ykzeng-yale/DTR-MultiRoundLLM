# Receiver and runtime specification, with resource window


> **Lead resolution, 21 September:** [consolidated decisions and required corrections](worker_issues_resolution_20260921.md) govern use of this historical report. Preserve original records. In particular, the pilot does not establish population efficacy, complete receiver-law verification or categorical sample-size feasibility. The working useful-gain threshold is now five percentage points for a future frozen policy comparison; no new trial is released.

**Experiments workstream, 2026-09-21T12:39Z.** Item (3) of the J4 assignment in
`docs/experimental_status_rulings_20260921.md`: "return the available isolated environment and
receiver/runtime specification, with resource window." Gathered read-only: **zero model calls, zero
installs, zero candidate or reference executions.** Nothing here is a validation result; it is an
inventory of what exists and what constrains a frozen run.

## Machine

| item | value |
|---|---|
| host | Apple M5, 10 cores, 32 GB unified memory, macOS (Darwin 25.5) |
| memory free / inactive / wired | 1.02 GB / 11.21 GB / 5.16 GB |
| **swap** | **25.3 GB used of 26.6 GB — 1.28 GB free** |
| isolation | macOS Seatbelt sandbox available, profile sha256 `6a60de2e5a47f95c…`, RLIMIT_NPROC 64, no network, home-directory reads and writes denied |

**Swap is the binding constraint.** GPU-resident weights and KV cache are not pageable, so another
receiver cannot be loaded while the two below are resident. Any frozen run must either attach to
them or have them stopped first.

## Receivers available now

| port | model | build | context per slot | slots | busy now | owner |
|---|---|---|---|---|---|---|
| 8191 | Qwen2.5-7B-Instruct, q4_k_m, 2 shards | `b1-4fea119` | **8192** | 4 | **0** | sibling `DTR-AgentEvals` session |
| 8193 | Qwen2.5-3B-Instruct, q4_k_m | `b1-4fea119` | **8192** | 4 | **0** | sibling `DTR-AgentEvals` session |

Both were launched with `-c 32768 -np 4`: the 32768 is the **total** KV pool, so the real
per-conversation budget is **8192 tokens** — the figure any context-length constraint must use.

Both run build `b1-4fea119`, which **matches the commit pinned in
`experiments/env/llama_server_manifest.json`** (`4fea119`), so outputs from them are
reproducible against our hashed copy in `work/bin/`. But both processes run from the sibling
session's **ephemeral scratchpad binary**, have been up 1 day 19 hours, and die with that session or
a reboot. A frozen run should therefore record `/props` `build_info` and per-slot `n_ctx` at every
chunk and halt on any change.

**The chat template silently injects a default system message** ("You are Qwen, created by Alibaba
Cloud…") on both servers. A frozen protocol must send an **explicit** system message so the injected
default never reaches the receiver, and must record the rendered prompt hash per call.

## Alternative runtimes

`ollama`, `mlx_lm.server` and `vllm` are **absent** on this machine, and nothing was installed.
So the receiver is llama.cpp `llama-server` or nothing. The earlier note that "current Ollama support
differs from the source study's llama-server" is moot here; there is no Ollama to differ.

Cached weights also include Qwen2.5-Coder-7B-Instruct, Qwen3-4B-Instruct-2507 and
granite-3.3-8b-instruct (GGUF). **Weight files were not hashed in this pass** — hashing is deferred to
the execution job so this pass stays inside its 30-minute cap; the multi-shard 7B must have every
shard hashed.

## Resource window

The sibling project's stages have **all completed** — log, live and branch, each reporting
"errors this invocation: 0" — and neither server has a busy slot. **So the GPU is free of generation
load now, and memory, not compute, is what limits a run.** Two workable options for a bounded
development batch:

1. **Attach** to the idle 3B on 8193 (build matches our manifest). No new memory needed. Cost: the
   run depends on a process owned by another session.
2. **Replace**: the sibling session stops its two servers, and we launch the 3B from our pinned
   `work/bin/` copy at `-c 8192 -np 4`, which states the true per-slot budget and frees roughly
   1.5 GB of wired KV. Cleaner provenance; needs the sibling's servers stopped, which is not ours to do
   without the owner.

At the measured multi-turn throughput of 909 calls/hour for the 3B (`docs/pilot_findings.md`), the
ruling's 168-call / 20-minute development ceiling is about 11 minutes of generation, well inside
either window.

## Not done in this pass, and why

Weight hashing, reference/control execution in the sandbox, and any receiver call. The ruling
requires those to follow a committed validation contract and a passed containment check, and bounds
this pass to zero executions. They are the next bounded job, not this one.
