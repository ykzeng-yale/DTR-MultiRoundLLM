# MRL-15 prospective candidate-frame review (2026-09-22)

Preparation only. This does not authorize collection and does not certify family independence. It is source-only and static: reference code was parsed with `ast.parse` and `compile()` and never executed; zero model calls; no receiver outcomes were used.

Output: `results/frame_review_mrl15_20260922T021202Z/` (manifest.json, records.json; records_sha256 `96dad5032cd9b346e1f4056fba6d8a3ab52533b9a702f0e791d710cd5efa0e74`).

Reproduce: `python3 scripts/review_candidate_frame_mrl15.py --out-dir results/frame_review_mrl15_<UTC>` (records.json is byte-identical across runs).

## Frame counts (measured)

- Screened frame: 396 (summary and per_candidate verified; every id marked USABLE). MBPP sha256 verified.
- After (i) prior-seen roots removed: 384. Sources: 434 mbpp/* ids from dev_release_v1c plus E11/dev roots 52,357,373,378,402,489,509. 164 humaneval/* ids cannot map to MBPP task_ids and were not similarity-screened.
- After (ii) near-duplicate of a prior-seen root (score >= 0.5): 235.
- After (ii) keeping one root per within-frame provisional family: 198 (the eligible frame; 26 multi-member families).

The similarity score is max(token-Jaccard of task text, token-Jaccard of reference-code identifiers), with the 0.5 threshold fixed before computing. It flags duplicates only and does not show independence. Because it compares against 434 prior-seen MBPP roots, the step is broad and probably over-excludes (149 removed). Order key: `sha256("mrl15-frame-seed-20260922:{task_id}")`.

## First 20 records

| rank | task_id | entry point / arity | tests | family | nearest prior-seen (score) | decision (uncertainty) | flags |
|---|---|---|---|---|---|---|---|
| 1 | 918 | `coin_change`/3 | 3 | PF-918 | 253 (0.2) | include (low) | - |
| 2 | 825 | `access_elements`/2 | 3 | PF-825 | 71 (0.25) | include (medium) | function_name_unstated |
| 3 | 359 | `Check_Solution`/3 | 3 | PF-359 | 160 (0.3333) | hold (high) | function_name_unstated, unstated_output_string |
| 4 | 842 | `get_odd_occurence`/2 | 3 | PF-29 | 767 (0.3333) | include (medium) | function_name_unstated |
| 5 | 31 | `func`/2 | 3 | PF-31 | 130 (0.2941) | include (low) | - |
| 6 | 847 | `lcopy`/1 | 3 | PF-847 | 587 (0.4) | include (medium) | function_name_unstated |
| 7 | 816 | `clear_tuple`/1 | 3 | PF-816 | 394 (0.2222) | include (medium) | function_name_unstated |
| 8 | 895 | `max_sum_subseq`/1 | 3 | PF-895 | 777 (0.3333) | include (medium) | function_name_unstated |
| 9 | 868 | `length_Of_Last_Word`/1 | 3 | PF-813 | 90 (0.4) | include (medium) | function_name_unstated |
| 10 | 288 | `modular_inverse`/3 | 3 | PF-288 | 101 (0.2) | include (low) | - |
| 11 | 154 | `specified_element`/2 | 3 | PF-49 | 265 (0.3333) | include (low) | - |
| 12 | 907 | `lucky_num`/1 | 3 | PF-907 | 422 (0.375) | include (low) | - |
| 13 | 863 | `find_longest_conseq_subseq`/2 | 3 | PF-863 | 633 (0.2222) | include (medium) | function_name_unstated |
| 14 | 966 | `remove_empty`/1 | 3 | PF-361 | 780 (0.4286) | include (medium) | function_name_unstated |
| 15 | 652 | `matrix_to_list`/1 | 3 | PF-652 | 75 (0.375) | include (medium) | function_name_unstated |
| 16 | 349 | `check`/1 | 3 | PF-349 | 760 (0.375) | hold (high) | unstated_output_string |
| 17 | 963 | `discriminant_value`/3 | 3 | PF-963 | 93 (0.4) | include (low) | - |
| 18 | 651 | `check_subset`/2 | 3 | PF-651 | 2 (0.4) | include (medium) | function_name_unstated |
| 19 | 499 | `diameter_circle`/1 | 3 | PF-499 | 139 (0.3333) | include (medium) | function_name_unstated |
| 20 | 974 | `min_sum_path`/1 | 3 | PF-147 | 126 (0.2857) | include (medium) | function_name_unstated |

Decisions: {'exclude': 0, 'hold': 2, 'include': 18}. Records 359 and 349 are on hold because they expect literal message strings that the task text never states.

Limitations: the specification flags are static heuristics. The function name is not in the text for most MBPP tasks, and the harness supplies it, so that flag alone does not block inclusion. HumanEval prior-seen roots were not screened. Reference code and assertions appear only as sha256 digests.
