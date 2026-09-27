# Native-test measurement feasibility — 27 September 2026

Codex direct source audit. This advances the population/measurement decision without executing benchmark code or changing the scientific target. No receiver result or evaluation roster is produced.

## Evidence and decision

The pinned upstream evaluator loads `TestCases` specifically using `loadTestsFromTestCase`; it does not load every class in the module. Source: https://github.com/bigcode-project/bigcodebench/blob/09dd993f46c3fbf3a799465bb96d524edcb0b199/bigcodebench/eval/__init__.py . The inspected file is7,366 bytes, SHA256 `d5fd553559ac1b76659ebc32ae30e3e779449ecd31c5201f2301319ceeee01fe`; saved as ignored `work/task_sources/bigcodebench_v014_20260927/upstream_eval.py`. Only source text was read.

[Static partition inventory](../results/bigcodebench_test_partition_20260927.json) applies one deterministic candidate rule to all1,140 rows: lexicographically first directly declared `TestCases` method beginning `test` supplies public status; remaining methods are private. This is an evaluated source proposal, not an adopted endpoint. There are6,425 directly declared methods under that rule, compared with6,434 `test_` functions anywhere in the earlier generic AST scan. Neither count is a runtime test count.

- 1,109 rows have the basic partition structure;31 require review:4 duplicate method-name rows,26 class-assignment rows and1 nonstandard-inheritance row. These flags are not exclusions and do not establish validity for the remaining rows.
- 625 rows share at least one identical assertion AST between the candidate public method and a private method, or have identical method bodies. Reused variable names with different local/fixture values can cause this flag; it is **not625 proven duplicate cases**. Conversely, unequal ASTs do not guarantee independent or semantically distinct checks.
- Eight rows define additional classes, and69 contain executable module-level nodes beyond imports/functions/classes. The scan records these rather than importing them. Fixture, decorator and module initialization behavior still requires isolated runtime auditing.

**Decision:** do not release the naive first-method partition for policy collection. It lacks evidence that the public/private checks test distinct behavior, run independently or reject meaningful wrong implementations. Do not select a different public test after receiver outcomes or discard flagged tasks to produce an easier population. The next measurement implementation should preserve the full source roster and report per-task dispositions under an explicit new contract. Any restricted admissible population must be named and justified before outcomes.

## Information contract for the proposed status-only variant

A possible native-test intervention observes one fixed categorical record: `PASS`, `FAIL`, or `INCOMPLETE`. It must not include exception messages, stdout, stack traces, test names, test source, actual/expected values or private outcomes. Three possible values carry at most log2(3) bits per observed check **conditional on the public task and fixed test-selection rule**, if the stated channel is the entire observed record and no timing/length side channel is exposed. This elementary alphabet bound is not zero answer leakage, semantic sufficiency, or a bound on all information available from the task. Repeated/adaptive diagnostics change the information budget and need their own contract.

A test failure must be distinguishable in private audit logs from unavailable infrastructure. The public renderer may use INCOMPLETE for declared infrastructure failures but may not convert missing outcomes into STOP. The endpoint still needs a separate binary/missing grading law, cap and failure accounting. Public and private runs require fresh state; loading the complete test module into either process can expose unused test source to candidate code and therefore cannot be treated as an established secrecy barrier. Stronger module separation and containment require implementation and adversarial tests before execution is trusted.

## Validation and limitations

The source tool uses AST parsing only. Six new synthetic checks cover lexical ordering, fixture inventory, duplicate bodies/assertions, duplicate method definitions, additional-class handling, nonexecution and nonstandard inheritance/async holds. All26 relevant inventory tests pass. No generated or third-party program was executed. Decorator representations are hashed, not copied into the public inventory. The first unpublished inventory containing decorator strings was moved to ignored source storage; the published artifact retains hashes instead.

An external reporter describes a vacuous-test defect for task541 in the v0.1.4 set: [upstream annotation issue44](https://github.com/bigcode-project/bigcodebench-annotation/issues/44). This is **reported evidence, not independently reproduced here**, and is not used to count failures, remove tasks or claim a benchmark-wide defect rate. It reinforces the need for wrong-control validation but does not replace it.

Full-project readiness **60%, change0 percentage points**. Source feasibility narrows the next measurement decision; it establishes no policy benefit, family independence or trial freeze. Codex continues direct implementation. The goal remains active; Claude delegation stays ended.
