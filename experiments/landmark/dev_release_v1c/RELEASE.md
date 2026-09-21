# Development release v1c — all seven roots graded

Identical to release v1 (`../dev_release_v1/RELEASE.md`) in every respect that reaches the receiver: same
public tasks, same receiver, same decoding, same seed, same budgets. The **only** change is in the private
grading spec: root 402 carries reference-repair-v1 (`return C[r] % p`) instead of the defective original, so
the grader's reference gate can pass and 402's outputs can be graded. The builder rebuilt the repaired source
from the pinned original and accepted it only because it hashes to the frozen `50fafebe…`; the grader
re-validates it against the full private suite before grading any 402 candidate.

Why this is not selection on outcomes: no output of root 402 has ever been executed or graded — it was blocked
in release v1 before execution. The repair was decided and validated (`docs/landmark_reference_validation_results.md`)
before this release was frozen.

Because the receiver is deterministic under fixed seeds (release v1 re-ran 49/49 byte-identical), this
re-collection is expected to reproduce release v1's outputs exactly. That is checked, not assumed: any output
that differs is reported. Everything reported for release v1 is reported here, now over seven roots.
