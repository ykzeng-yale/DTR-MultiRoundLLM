# LEAD-SOURCE-02: completed row inventory and measurement decision

Codex, 27 September 2026. Direct implementation following the owner's instruction to end Claude Code dependence. This completes the missing row-reading work from the closed, partial MRL-41 inquiry. It is source feasibility, not a receiver experiment or adoption of a population.

## Verified results

The pinned v0.1.4 Parquet contains **1,140 rows, 1,140 unique task IDs, nine string columns, and no null or blank required fields**. Every entry point is `task_func`. All library-list and structured-document fields parse as literal/JSON data. All complete-prompt-plus-reference programs and test programs parse as Python ASTs; 6,434 functions with `test_` names are present. Parsing is not an executed reference check or proof that unittest discovers that many independent tests.

Tasks **1120 and 1121 are exact duplicates** in Complete prompt, Instruct prompt, canonical solution and test source. They must not be placed on opposite sides of any future split. Two additional pairs have identical solution-body bytes: 130/131 and 814/826. Identical bodies alone do not establish identical complete tasks. Absence of other exact-byte duplicates does not establish semantic independence.

Declared task-library frequencies include pandas426, numpy334, matplotlib309, random212, os202, sklearn152, requests40 and subprocess31. These are overlapping metadata counts, not families, network-use determinations or admissibility decisions. The full inventory preserves each row's field hashes, declared libraries and static parse results without publishing raw task/reference/test text.

[Inventory](../results/bigcodebench_rows_inventory_20260927.json), SHA256 `156459daa189f39605040f74ddcd7f47b5fb57ac294fa8103842dd45a7567c6c`; [separate direct recount](../results/bigcodebench_rows_validation_20260927.json). The recount independently checks footer row count, all 10,260 field hashes, duplicate groups and library counts without calling the inventory summarizer. Both use the same PyArrow decoder, so this is implementation cross-checking, not independent decoder validation.

## Measurement decision

**Do not drop the new source into the current literal-case measurement pipeline.** Its unittest suites, fixtures, stochastic functions and nonliteral objects require an explicit new measurement version. Silently extracting convenient scalar-returning tasks would define a restricted population and could defeat the stated reason for investigating library-mediated tasks. The current source inventory does not justify that restriction.

The source is large enough to merit a measurement-design assessment, but 1,140 IDs are not 1,140 independent families. A future source-relative target must state the prompt variant, semantic-family/admission rule, prior-exposure crosswalk, sampling law, split and within-family weighting before receiver outcomes. Existing MBPP exclusions and all negative outcomes remain unchanged. BigCodeBench has not been adopted as an efficacy population.

A concrete alternative to investigate is a benchmark-native public test with a bounded status-only feedback record, with all remaining tests private. That would permit nonliteral objects without transferring expected values through diagnostic text, but it is a **proposed new measurement contract**, not an implemented repair of the current literal-case contract. It needs deterministic test selection, fixture isolation, exception redaction, reference/wrong-control auditing, and analysis of overlap between public and private assertions. No extraction, test execution, dependency-stack installation or receiver call is released by this source result.

Source inspection already exposes a specification issue on task0: the signature default is `list(range(1, 3))`, whereas its prose describes a default range from1 through10. This is a source discrepancy, not a measured reference failure. It illustrates why syntactic validity alone cannot admit the entire benchmark. It must be resolved under a declared contract, not repaired after outcomes.

## Reproduction and resources

Use the original five-file acquisition receipt; do not redownload or substitute releases. The reader is PyArrow19.0.1 (Apache licence), installed without dependencies into ignored `work/source_reader_20260927`, separately from the project environment. [Reader environment receipt](../results/source_reader_environment_20260927.json). The installed directory is163,104,631 bytes; source acquisition was2,383,786 bytes; the inventory is1,689,460 bytes. This remains below the new512MiB retained-data cap. Installation reported a29.2MiB package download and completed in seconds. The inventory command completed in under one second after reader setup; the direct recount took0.050seconds. These are source-tool timings, not model costs. Zero paid experimental services, receiver calls or benchmark executions.

```sh
work/source_reader_20260927/bin/python scripts/inventory_bigcodebench_rows_20260927.py \
  --source work/task_sources/bigcodebench_v014_20260927/v0.1.4.parquet \
  --out /tmp/bigcodebench_inventory_new.json
.venv/bin/python -m pytest -q tests/test_bigcodebench_rows_inventory.py
```

Choose an unused output path; existing outputs are refused. Seven focused tests cover duplicates, missing/malformed metadata, schema refusal, nonexecution of malicious literal/source fixtures, input-hash refusal and overwrite refusal. Full suite: **2,219 tests plus8 subtests passed in38.70seconds**, run directly by Codex. Source AST parsing emitted invalid-escape SyntaxWarnings; there were no syntax failures. No task source was evaluated or imported.

Full-project submission readiness **58%, change0 percentage points**. This resolves an engineering blocker without earning independent-policy or efficacy credit. Population/family/sampling, the complete prospective freeze, untouched-family evaluation and final manuscript/environment reproduction remain incomplete. Codex owns subsequent implementation directly; no Claude handoff or acknowledgement is required.
