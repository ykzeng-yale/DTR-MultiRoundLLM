# Pinned MBPP source cache: acquisition and check (LEAD-PORT-01)

25 September 2026, experiments worker. Several builders read one **gitignored, host-local** file, the official MBPP `mbpp.jsonl`: `scripts/build_e14_release.py`, `scripts/build_e14_release_v2.py`, `scripts/build_dev_release_v3.py` and the MRL-15 / ranks 21–40 frame reviews. The file is not in Git, so on a clean checkout the tests that rebuild those packages **skip with an explicit reason**, and the builders and `verify` entrypoints **fail closed**. A skip does **not** reproduce or re-verify a committed package. Rebuilding requires this exact file.

| Field | Value |
|---|---|
| Source | google-research/google-research at commit `4700efb9afa54286b0e04473ba80a13e8461e25f` (`mbpp/mbpp.jsonl` last changed in `f82046ba`, 2022-03-31) |
| URL | https://raw.githubusercontent.com/google-research/google-research/4700efb9afa54286b0e04473ba80a13e8461e25f/mbpp/mbpp.jsonl |
| SHA256 | `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` (563,743 bytes) |
| License | Repository license file at the same commit (Apache-2.0; SHA256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`). The MBPP dataset is distributed under CC BY 4.0. |
| Recorded acquisition | [landmark_task_source_candidates_20260920.json](../results/landmark_task_source_candidates_20260920.json), acquired 2026-09-20T21:36:07Z |
| Expected local paths | `work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl` (all builders) or `work/sources/mbpp_full.jsonl` (E14 builders) |

Pins in the builders: the E14 lead spec `source_file_sha256` is `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`, and `build_dev_release_v3.MBPP_SHA256` is `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`. Each builder verifies its pin **before reading** and refuses on a mismatch.

Acquisition and check. This is **not run under LEAD-PORT-01**, which authorizes no download; a separate review is needed before anyone fetches the file:

```bash
mkdir -p work/task_sources/mbpp_full_20260920_4700efb9 && curl -fsSL -o work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl https://raw.githubusercontent.com/google-research/google-research/4700efb9afa54286b0e04473ba80a13e8461e25f/mbpp/mbpp.jsonl && echo "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f  work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl" | shasum -a 256 -c -
```

Only after the `OK` line should anyone run a rebuild or `verify`. If the hash differs, stop: the builders will refuse it anyway.
