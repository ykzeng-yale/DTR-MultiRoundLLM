# MRL-41 terminal partial-delivery review — 27 September 2026

Signed: Codex scientific lead, scheduled three-hour review at 04:31 UTC.

## Disposition

Accept `24842d6ba7cff1aa94f703726f7038460a0495e5` as a **partial source-only inventory**, and close MRL-41. The existing Claude session's terminal message at 01:31:29Z reports stopped implementation; its later messages explicitly distinguish the watcher from a job. Delivery at 01:31:12Z precedes the 01:42:58Z deadline. No new job, lease, installation, download, collection or cap renewal is authorized. The go-ahead was Codex's delegated instruction, not a new owner approval, as corrected in `977e8d3` and acknowledged in `67edcab`.

## Independent validation

Reviewed the builder and all focused tests. Executed `.venv/bin/python -m pytest -q tests/test_bigcodebench_source_inventory.py`: **13 passed in 0.03 seconds**. Rebuilt the document in memory using the five local files and committed acquisition receipt: exact parsed-JSON match to the delivered inventory, including the builder hash. All five hashes and byte sizes verify, totaling 2,383,786 bytes; local and committed acquisition receipts are byte-identical. Saved inventory SHA256: `a4ef12fc420f9af0897e64b793f6fb6559b86aec09b7844b2400bcd31ecf2d24`. No completed artifact was overwritten; no dataset code was imported or executed. No receiver or benchmark run occurred in this review.

The dataset card declares Apache-2.0, nine fields and 1,140 v0.1.4 examples. The requirements contain 74 entries and 71 distinct normalized names. Container markers and footer-length range pass. These checks do not validate Parquet rows, task validity, installability or dependency licence clearance. The worker's full-suite count of 2,212 passes remains **reported**, not independently rerun in this review.

## Limitations and scientific decision

Neither pyarrow nor fastparquet is discoverable in the reviewed project interpreter. This corroborates the partial status; it is not proof that every interpreter on the machine lacks a reader. The builder does not implement row inventory even when a reader is available. Missing outputs remain exact row count/schema, task-ID and prompt duplicates, entry points, per-task libraries and missing fields. No installation or replacement decoder is undertaken under this expired scope.

Compatibility remarks in the output are source-informed questions, partly hard-coded, not row-derived results or independently verified sandbox installability. Network/filesystem needs cannot be assigned to tasks from dependency names. Marker checks do not establish full container validity. The manifest comparison binds this reviewed fixed input; it is not a general untrusted-URL validator.

BigCodeBench remains an inquiry, not an adopted population, family partition, measurement contract or efficacy result. Any future row-reading or environment work requires a separately recorded scope; the present check does not authorize it. Preserve all earlier MBPP exclusions and negative findings.

Full-project submission readiness **58%, change 0 percentage points** under the fixed rubric. No credit is earned or withdrawn for partial metadata verification. Efficacy and total-cost benefit remain unestablished. Population/family/sampling decisions, the full prospective freeze, independent policy evaluation and complete manuscript/environment reproduction remain incomplete. Pause the MRL-41 heartbeat after recording this disposition; leave the continuous goal paused.
