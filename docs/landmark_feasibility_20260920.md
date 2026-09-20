# Landmark prompt-choice study: feasibility and evidence audit

Read-only review by Codex subagent `/root/evidence`, 2026-09-20. Hardware/service observations were collected around 21:27 UTC on the current Codex host. No server was started, model invoked, candidate/reference program executed, package installed, or Git state changed. This is a feasibility snapshot, not an experiment or service reservation.

**Conclusion:** a small development run is technically plausible after service and collector setup, using existing small-model files and explicitly reused roots. A genuinely fresh confirmatory coding study is **not ready**: no reachable receiver service was found, the available collector is an arithmetic smoke harness, and every root in the available original benchmark has already been used. Historical manifests from the experiment host must not be mistaken for a running environment on this host.

This snapshot preceded the new `experiments/landmark/` development package in this continuation. That package adds a mock-tested collector/analyzer; it does not establish a live receiver, validated coding scorer, restored-server independence or untouched evaluation roots. Its current readiness is governed by `docs/landmark_experiment_protocol.md`.

## 1. Current receiver and resource status

| Item | Directly observed status |
|---|---|
| Host | `Mac14,5`; 12 CPU cores reported; 34,359,738,368 bytes RAM (32 GiB). No GPU utilization measurement was made. |
| Storage and memory | About 17.4 GiB disk free; about 1.48 GiB swap in use. The memory snapshot showed substantial compression. These observations do not establish spare inference capacity or latency stability. |
| Source-study llama endpoints | Proxy-disabled loopback requests to ports 8191 and 8193 were refused. No active `llama-server` process was observed. |
| Ollama endpoint | Direct requests to `127.0.0.1:11434` for tags, version, and loaded-model metadata were refused. An `ollama` process initially appeared, had no observed TCP listener, and was absent in the later process snapshot. Process presence alone did not establish an available service. |
| Ollama executable | `/opt/homebrew/Cellar/ollama/0.21.2/libexec/ollama`, reached through `/opt/homebrew/bin/ollama`; SHA-256 `7dec6604e03973a90613e6d62962fba1759586db3e10b40a8027cbab17c91c87`. This is executable provenance, not a live server-version response. |
| Historical llama package | `experiments/env/llama_server_manifest.json` records build `0.4.1-dev`, commit `4fea119`, and 26 files copied on the other experiment host. Its declared local `work/bin/` directory is absent here. The historical binary digest is therefore not a verified available receiver on this machine. |
| Source 3B/7B receivers | No corresponding files were found in the audited default Ollama manifests or Hugging Face model-cache entries. No service serves them at the source ports. This is scoped to the inspected locations, not an exhaustive whole-machine search. |

Two generation-model artifacts are available in the default Ollama store. Each manifest-referenced blob was read and its bytes verified against its declared SHA-256, including model, system, template, and license layers:

| Local tag | Weight blob SHA-256 | Weight bytes | Manifest-file SHA-256 |
|---|---|---:|---|
| `qwen2.5:0.5b` | `c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515` | 397,807,936 | `a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67` |
| `qwen2.5:1.5b` | `183715c435899236895da3869489cc30ac241476b4971a20285b1a462818a5b4` | 986,048,512 | `65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b` |

Their local configuration blobs specify the Qwen2 family, GGUF, and `Q4_K_M`. The file hashes above should not be silently substituted for a future service's returned model digest: record and check both at collection. Neither artifact is the source study's frozen 3B or 7B receiver. Choosing either makes a new receiver-specific experiment; there is no current competence or runtime pilot for the proposed coding landmark on it.

The source protocol permitted shared GPU contention on its experiment host. That historical permission and runtime record do not show whether this host is currently uncontended. Before an actual timed batch, inspect active jobs again, coordinate ownership, and record contention and service/build conditions. Do not turn a short process snapshot into a latency guarantee. Use a single receiver and low concurrency for an initial development batch; model loading and sandbox work also consume shared memory/CPU. Client timeouts do not necessarily cancel server work, as the current collector already documents.

## 2. Task provenance: no unused roots in the original pool

The available reconstructed canonical file is the sibling repository's `work/restoration_reconstruction_13bad73/tasks.json`. Its SHA-256 is `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`, matching the frozen source design and logged task hashes. It contains 427 MBPP and 164 HumanEval roots, 591 total.

The frozen design partitions all 591 into **30 pilot + 231 training + 330 confirmation roots**. The completed 4,488-episode log covers the latter 561. The pilot roots are previously used roots, not a remaining fresh holdout. The original confirmation designation also does not survive the current project's repeated outcome inspection as an untouched confirmatory set.

**Equal counts hide different cohorts:** this project's `results/audits/final_pool.json` also contains 561 all-difficulty roots, but only 533 are in the source log. It includes 28 old pilot roots and excludes 28 logged roots. Its 230 “informative” roots are likewise all previously used. Changing random seeds, regenerating answers, using an excluded root, or renaming a split does not produce a new task root. Outcomes selected to construct the informative pool are an additional selection issue, not evidence of new data.

Available exclusion/scoring artifacts include `results/audits/final_pool.json`, `results/audits/scoring_split/20260919T233754Z/`, the task-pool run directories and `NOTES.md`, and the integrity/mutation audit artifacts. These permit reconstruction of earlier inclusion decisions. They do not establish that an excluded task is now valid, that family independence was audited, or that the resulting labels match a newly frozen scoring rule. The four arithmetic fixtures in `experiments/smoke_tasks.jsonl` are familiar harness tests, not fresh confirmatory coding roots.

No separately sequestered, new-root/family coding set with a verified manifest was identified in the inspected project artifacts. A genuinely fresh evaluation therefore requires a separately sourced or constructed task set, deduplication against the full known 591-root union, family-level separation, and evaluator validation before outcome-guided tuning. Different test cases for the same function can strengthen measurement but do not create an independent root. This review neither downloads a new benchmark nor certifies freshness outside the inspected artifacts.

## 3. Collector and measurement readiness

`experiments/collect_ollama.py` is a bounded fixed-slate arithmetic collector. It uses STOP/retry/verify/decompose instructions and scores a strict `FINAL: integer` response. `experiments/collector_config.json` still contains `REPLACE_WITH_EXACT_INSTALLED_MODEL_TAG`. The recorded `collector_smoke_v1` run is explicitly synthetic: its 14 calls produced no model tokens. None of these artifacts constitutes a completed coding landmark collector.

Useful existing pieces are bounded calls/time, local-only service access, complete slate and selection probabilities, request/response hashes, failure retention, and pre/post model inventory checks. Missing for the proposed coding study are a validated coding adapter, exact landmark eligibility/information rules, immutable prefix and branch lineage, restoration checks, distinct branch seeds, the specified continuation horizon, sandboxed outcome scoring, and the locked analysis pipeline. A smoke test of transport alone cannot close these gaps.

`/usr/bin/sandbox-exec` is present and `experiments/common/sandbox.py` supplies the intended isolation pattern. **This review did not test sandbox behavior on this host.** A configuration inherited from another machine/interpreter is not a current containment or evaluator-equivalence test.

The new measurement contract needs to resolve these concrete issues before collection:

1. **Public inputs:** choose and version either independently generated/certified public checks or an explicitly exposed benchmark-assertion split. Do not mix their definitions. The latter changes the endpoint and information intervention. Prompt writers/selectors cannot consume withheld assertion inputs, expected answers, or hidden failure messages while being described as public-only.
2. **Empty checks:** 90 of the 561 source-log roots have zero certified checks. Define a separate no-substantive-check state or a prespecified eligibility rule. A successful load is not evidence of substantive correctness. Any exclusion changes the target population and must precede outcome-based analysis.
3. **Scoring:** source `success_first_candidate`/`success` are original full-benchmark outcomes, not newly hidden-only grades. A new separated endpoint requires fresh sandboxed grading; old scalar labels cannot be relabeled by removing assertions in prose. Passing references and observing no hack flags do not establish discriminative reliability or zero endpoint bias.
4. **Timing:** landmark eligibility and stratification must use only pre-action public history. Follow the declared assignment design: the new exhaustive branch comparison includes every arm with probability one and randomizes order; a later sampled-action logger must record actual action probabilities. Keep receiver and continuation fixed. STOP preserves the prefix artifact and is distinct from execution failure. Account for prefix collection, checking, selection, and each branch's actual costs.
5. **Independence:** keep all branches/seeds of each task family together. A newly drawn continuation on an old root is fresh execution with a reused root, suitable for development or a specifically scoped prospective same-root study; it is not fresh-root generalization.

These are scientific implementation requirements within the already authorized research, not additional permission requests.

## 4. Cheapest defensible next execution

The cheapest currently supported inference exercise, once a local service is available and the exact model tag/config is frozen, is the existing **four-fixture arithmetic smoke test**, capped at 16 calls and 600 seconds. Use the available small model only to validate service transport, logging, STOP, and failures. It supplies no evidence for coding prompt effectiveness.

A minimally relevant **coding development** batch could then use four prespecified reused roots, one initial prefix per root, STOP plus three exact non-STOP feedback choices, and two independent one-step continuations for each non-STOP choice: at most **4 + 4×3×2 = 28 receiver calls**, with STOP requiring no new receiver call. This is an illustrative bounded engineering design subordinate to the coordinating protocol, not a frozen experiment. At 1,024 new tokens per call, its output-token cap is 28,672; input tokens, validation, and selection costs must be reported separately. It needs the missing adapter/scorer/restoration work and a time cap informed by actual service performance. It cannot train or validate a personalized policy, establish superiority, or substitute for a powered multi-round study.

No actual landmark run is ready to dispatch from the inspected state. The barriers are specific and repairable: unavailable service on this host, unavailable frozen 3B/7B runtime here, an unfinished coding collector/measurement contract, and no untouched root set. Large generator training or a large new run would not repair these prerequisites. The next result should be labeled development unless new-root/family evidence and a locked confirmatory design are actually supplied.

## 5. Repository boundary checked

Read-only GitHub inspection found `main` at `17215b54cf2dd2d6b8a5c7759bd6479bdec5c6f3` and [PR #6](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/pull/6) **open** at `a57a9d1c2069fc7342d0fa9d9ee9d198e5ff2527`, matching the local checked-out revision. PR #6 contains scientific diagnosis and advancement gates; its file inventory does not deliver a new coding landmark collector. Open PR status is not integration or experimental readiness. This audit made no Git mutations and leaves the new study design to the coordinating workstream.
