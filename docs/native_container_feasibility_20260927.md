# Existing container-runtime feasibility

Codex direct read-only inspection, 27 September2026. [Receipt](../results/native_container_feasibility_20260927.json). This follows the source-reviewed native subprocess mismatch; it is not sandbox qualification, benchmark execution or receiver evidence.

The lead has no docker command on PATH and no installation at the checked Docker/OrbStack/UTM app or Homebrew podman/colima paths. Mini has no Docker installation at the checked command/app paths. These checks are not exhaustive proofs of absence.

Aux has Docker.app, an absolute-path Docker client (28.0.4), and live backend/virtualization processes. The engine-info client failed to return useful information. After checking the exact owned probe shell/client PIDs, Codex terminated only those probe processes; no daemon, VM or peer application was stopped. The partial empty/zero fields printed during cancellation are not valid resource measurements.

A separate bounded direct Unix-socket check connected successfully, sent HTTP `/_ping`, and timed out after3.002seconds without a response. The client-version command completed. Thus Docker is installed but engine readiness is **unverified/unavailable for this check**, not permanently stopped. No container/image inventory, execution, or containment result was obtained. Do not start a job or infer that a previous job terminated merely from this timeout.

Aux reports AC power,23GiB available disk,46% system-wide free in the memory-pressure tool, and9,432.12MiB swap used. Mini reports AC and15GiB disk. These heterogeneous metrics are snapshots, not admission certificates; no CPU/GPU capacity or isolation claim follows. Addresses, keys and private runtime inventory are omitted from committed artifacts.

## Execution decision

Do not schedule native benchmark work on this Docker engine on current evidence. Do not retry indefinitely, duplicate jobs, start/restart a VM, install another runtime, prune images or stop peer workloads to create capacity. There is no live experimental process needing a monitoring heartbeat.

The current deny-subprocess Seatbelt runner remains unchanged and qualified only within its existing scope. Allowing arbitrary child commands would require a separate inherited-containment/resource assessment, including descendant cleanup and total resource bounds; changing an allow rule alone is not qualification. Docker availability, even once restored, would still require pinned image/runtime, no network or host mounts, explicit CPU/memory/process/disk/time caps, a supervisor result boundary and harmless containment probes before a frozen native test run.

Scientific source/family review and measurement design can continue independently. This is not a reason to substitute an easier scalar-only population or alter native tests. The whole-source population remains unadopted and no receiver trial is released.

Full-project submission readiness **60%, change0 percentage points**. Population/family/measurement, full prospective freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete; efficacy unestablished. Codex-only execution, goal active, no Claude reliance.
