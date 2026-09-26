# Prior adjudications inside the MRL-15 reserve

**LEAD-FRAME-01 — 26 September 2026, 07:18 UTC.** This is a read-only cross-source exposure and specification audit, not a new manual task review, model experiment, endpoint result, or collection release. The original history-conditional same-prefix prompt-choice target and the E14 NO-GO remain unchanged.

The MRL-15 source-selected convenience frame has 198 ordered MBPP IDs; ranks 41–198 contain 158. Its pinned source is the same full MBPP SHA256 `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` used by the earlier 24-root development-slate audit. Crossing the two committed records shows four later-rank IDs were already manually inspected and marked `exclude_specification_pending_repair`:

| MBPP ID | MRL-15 rank | Earlier specification problem |
|---:|---:|---|
| 159 | 69 | Season convention and return-versus-print mismatch |
| 386 | 91 | Adjacent versus arbitrary swap cost absent from prose |
| 112 | 146 | Undefined cylinder perimeter target |
| 289 | 162 | Year description conflicts with cumulative-year endpoint |

The earlier decision source is `results/landmark_family_audit_20260920/adjudications.json` (SHA256 `8ec2b57352a770a5d5ad2c834a30184c53fd129fc4595ec7a9dd6319a54f001d`); the later order is `results/frame_review_mrl15_20260922T021718Z/manifest.json` (SHA256 `4ffc10f060ae9860c0f8a2a259c7091ec1eb60e7e7bcd178bd65dd9f7df550cc`). Independent `jq` extraction and a separate Python set intersection agree on the four IDs and ranks. The Python check took 0.06 seconds wall. No later versioned specification repair for these four is recorded in the project documentation searched for this audit. This absence is a repository-record finding, not proof no private repair exists.

Thus the 158 later-ranked IDs have **no targeted MRL-15 frame review**, but four **did** receive earlier task-specific manual review with an adverse disposition. The other 154 have no targeted manual review in these *two recorded sweeps*; they are not certified untouched, valid, independent, or representative. The 198 count remains a mechanical convenience-frame count, not an executable roster or family count. The four cannot be silently promoted into a future endpoint/family roster: first reconcile each source version and specification against the earlier exclusion, document any legitimate same-target repair, and then re-adjudicate before inclusion. Do not erase the old decisions or substitute a new task target without labeling it. This correction does not change the E11, E12, E13a or E14 rosters or any observed result.

**Disposition: HOLD new collection.** A future independent policy trial still needs a supported frozen selector/action set, competent fixed and independent-sampling comparators, a defensible exposure-audited family frame, endpoints, assignment and missingness rules, inference, and a numerical local resource cap. No model/receiver calls or tokens, benchmark program executions, downloads, simulation draws, or paid charges were made for this audit; direct cost $0. Overall milestone completion remains **58%, change 0 percentage points**. Prompt efficacy is unestablished, independent policy validation absent, and the full project is not submission-ready.
