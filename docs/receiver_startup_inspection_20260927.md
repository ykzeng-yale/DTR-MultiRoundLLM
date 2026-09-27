# Bounded startup-state inspection

Follow-up to6bd5e0c: all three `--version` commands timed out at5seconds, including the uncapped command. This does not support attributing the calibration failure specifically to8MiB RLIMIT_FSIZE. No model was loaded or request dispatched. All owned probe children were killed/reaped by subprocess timeout.

One new `--version` diagnostic may run at most30seconds without RLIMIT_FSIZE, with bounded retained stdout/stderr64KiB and an owned-process sample1second after3seconds. Inspect PID/start/state, wait channel and stack to distinguish loader/crash-reporting stalls from model inference. No model argument, no receiver generation, no downloads, signing changes, quarantine removal, service restart or security-setting bypass. Save raw stack in ignored work and a sanitized diagnostic summary. Stop only this exact Popen child; no relaunch loop. This is a new infrastructure question, not a retry of the frozen nine-call experiment.
