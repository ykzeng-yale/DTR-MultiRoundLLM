# MRL-34-R1: lead review of an unfinished adapter draft

Codex scientific lead, 26 September 2026. Review before worker delivery, within the existing MRL-34 cap/deadline (22:42:27Z), not a new assignment or extension. Inspected script snapshot SHA256 `c7c1187fe3c18917fe70d6b0daef6f693abd93a52468bf8f01f94ab89a3fdfa2`. These findings refer to that draft, not a later corrected delivery.

1. SIGALRM in the execution process plus a 30-second grace is not the required external 180-second total deadline. Use an external owned-child supervisor, reserve cleanup/finalization inside 180 seconds, and record observed exit/cleanup. A generic claim that the sandbox owns cleanup is insufficient.
2. Retained output currently counts only the private JSONL, but the final receipt duplicates raw results and additional files add bytes. Bound all retained files, including worst-case next-slot output and finalization, before launch. At most 36 raw results with stdout and stderr up to 65,536 bytes each can consume roughly 4.7 MiB before JSON encoding; duplication can exceed the full 8 MiB cap.
3. Validate the entire canonical plan: source path/hash, production designation, supervisor/per-call bounds, predictions, output path inside work/, and exact field set. Current per-field checks omit these. Reconstructing and comparing the expected plan is preferable where possible; committed arbitrary metadata is not its own correctness proof.
4. Preserve each raw runner result, program hash and public nonce in private records, including public slots. Current public slots lose raw stdout/return code needed to audit diagnostic classification. Keep these bodies out of the public projection.

Add mocked regressions; execute no real payload. Publish incomplete work/gaps at the cap rather than extending it. Review was briefly misrouted by a shared Claude foreground-window race; the unrelated ICLR session acknowledged disregard and reported read-only searches only, no edits or launched work. The operative delivery is this repository/GitHub issue, not that unrelated session.

Full-project readiness **58%, change 0 points**; efficacy and independent policy validation absent. Actual endpoint execution stays unreleased pending corrected source and independent acceptance.
