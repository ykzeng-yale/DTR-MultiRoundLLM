# Native measurement runtime feasibility — 27 September2026

Codex direct inspection. The preceding turn made source-implementation progress; this turn verifies an operational dependency and available compute rather than treating source tests as an executed measurement audit.

## Executed local probe

A harmless standard-library discovery program was executed through the existing `experiments/common/sandbox.py` runner, capped at5 wall seconds,2 CPU seconds,256MiB requested memory and2KiB returned output. It completed in0.0242seconds under Seatbelt: `unittest` available; `numpy`, `pandas` and `matplotlib` unavailable. [Exact source, limits and result](../results/native_dependency_probe_20260927.json). No benchmark, reference, wrong-control or model-generated payload was run. Requested memory limits are not assumed enforced; the receipt retains actual applied limits.

This agrees with the runner's `-I -S` command and base-interpreter selection. Installing a package in the main project virtual environment does not make it visible to this sandbox. Do not solve this by running benchmark code unsandboxed or granting it repository/home access. A native dependency environment needs an explicitly allowed, immutable dependency location, recorded versions/licences, containment checks and a separately frozen audit. Retain the existing runner and historical measurement versions unchanged.

The current runner also uses `communicate()` before truncating returned stdout/stderr: its returned-output cap is **not** a bound on all intermediate capture memory. This previously available implementation detail matters for adversarial/native payloads. Reuse a reviewed bounded-output execution implementation or repair/test streaming capture before treating the output limit as an operational memory bound. The harmless tiny-output probe does not validate that behavior.

## Read-only compute inspection

Used the owner's mac-ssh-compute skill with existing host-key-verified aliases. No host addresses, keys, credentials or raw process arguments are published. No remote files were transferred, services started, packages installed or peer processes stopped.

| Host | Observed memory/disk state | Relevant runtime observation |
|---|---|---|
| Lead |32GiB RAM; reported51% memory-free metric;15,208MiB swap used;51GiB disk available|No matching llama/Ollama process found in the scoped process-name probe; earlier fixed receiver8193 read-only preflight refused connection|
| Mini |16GiB RAM;74% memory-free metric;225MiB swap used;15GiB disk available;AC|Ollama0.34.0 responds on its loopback endpoint; `/api/ps` lists no loaded models|
| Auxiliary |32GiB RAM;42% memory-free metric;9,440MiB swap used;23GiB disk available;AC|Docker processes active; installed Ollama binary exists; no matching receiver process reported|

These are time-specific snapshots, not capacity reservations or performance benchmarks. The mini's `/api/tags` lists only `BoltonBailey/Kimina-Prover-Distill-1.7B:latest`, digest `84a58ecda1a1e1e2665673da5629ae4c7b081bbb568fefd00ce4179764f93bf0`, declared size4,069,679,610 bytes. This is API metadata, not independent weight hashing or a generation test. It is not the frozen Qwen receiver and is not substituted. No model download or generation occurred.

## Decision and next implementation

Native measurement is not presently runnable unchanged in the audited sandbox. This is an engineering limitation, not proof of task unsuitability or prompt futility. The mini is a possible future compute location after artifact/resource qualification, not an authorized live experiment. Keep the original receiver frozen until a justified, versioned study change; no theorem-prover substitution or additional receiver is adopted.

Next implementation should first reuse or adapt an already bounded sandbox execution path, with synthetic dependency/output/isolation probes, then qualify a pinned dependency environment. Only after that and a fixed measurement plan can reference/wrong-control runs address the native test defects. Population/family/sampling and independent policy evaluation remain separate requirements. Avoid additional descriptive source scans that do not resolve these execution/measurement decisions.

Full-project readiness **60%, change0 percentage points**. Goal remains active; Codex implements directly. No Claude delegation, paid experimental services or efficacy claims.
