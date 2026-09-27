# Startup failure diagnostic

The frozen3cb10f8 calibration stopped before all nine generation assignments: launcher observed SIGXFSZ(-25), empty log, no guard-trigger and no memory samples. Preserve `results/receiver_resource_calibration_20260927/`; no same-run retry.

Freeze three infrastructure-only `llama-server --version` probes with the same pinned26 build files: no file-size limit,8MiB,64MiB. Each has5second wall timeout and at most4KiB retained stdout/stderr; the known version command does not load model weights. Commands run sequentially; total≤20seconds, $0, no candidate/test code or generation. Captured output is trusted pinned-tool output; this diagnostic is not a general bounded-capture runner. Retain all outcomes; do not infer cause from a signal alone. If file-limit association is reproduced, fix the launcher's log capture using bounded parent transport under a separate freeze rather than increasing experimental budgets or modifying the receiver.
