# MRL-15 independent implementation review

Reviewed worker revision: `25e65151029fc66c68629e3d56ec78cda2f83c7a` (`25e6515`). Scope: grader fault-attribution changes in `c215f18..3d76a0a` and saved evidence in `results/validation_mrl15_20260922T021743Z/`. The reviewed `grade.py` and `public_check.py` are byte-identical to their `3d76a0a` versions.

**Decision: accept grader v5 for the current ordinary benchmark scope.** No material blocking regression was found. Candidate syntax failures remain observed failures; parser/compiler resource or internal faults remain unavailable before dispatch. The principal changed paths are `experiments/landmark/grade.py:135–181` and `experiments/landmark/public_check.py:124–171,360–365`.

## Independent checks

- Ran `.venv/bin/python -m pytest -q tests/test_landmark_grader.py tests/test_landmark_public_check.py`: **168 passed in 0.59 seconds**. These tests use static parsing/compilation and mocked execution; no candidate program, reference, control, sandbox, model or receiver was executed by this review.
- Independently recomputed all four artifact hashes in `ARTIFACT_SHA256SUMS.json`; all match. Recorded source, task, specification and attestation hashes match the pinned files. The saved attestation's verified fields also match its source artifact.
- E8 records exactly **24 `program_start` and 24 `job_result` events**: seven reference outcomes of 1 and seventeen control outcomes of 0. Every job records one start, `sandbox_executed=true`, no timeout and the expected outcome.
- E6 records exactly **seven starts and seven results**, with all **21 public reference cases passing**. Summary totals agree with the ledgers.
- The attestation was **21,656.21 seconds old** at E8 reservation, within its 24-hour limit. Ledger reservation-to-completion spans are **0.523839 seconds for E8** and **0.277555 seconds for E6**; these are recorded wall-clock spans, not independent CPU or energy measurements.

## Scope and limits

This is an independent reconciliation of source, mocked/static checks and saved execution records; the remote executions were not repeated. The 31-start evidence supports compatibility and control discrimination on the **seven existing development roots**. Injected fault attribution is supported by mocked/static tests, not by inducing resource faults in the live sandbox.

This review does not regrade E11's two missing artifacts, validate the proposed fresh task frame, establish general evaluator accuracy or establish adversarial security. The E11 evidence remains immutable. No new collection or expanded execution budget is authorized by this review, and no efficacy or project-readiness increase follows from these checks.

E12 remains a separate release decision. Its new population, package paths and execution counts must be bound and validated explicitly; acceptance of this seven-root instrument check does not transfer the historical release's fixed paths or count limits to E12.
