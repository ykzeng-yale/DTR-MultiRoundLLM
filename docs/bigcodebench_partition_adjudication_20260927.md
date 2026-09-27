# Adjudication of native-test split flags

Codex scientific lead,27 September2026. Source-only follow-up to the [partition feasibility audit](bigcodebench_measurement_feasibility_20260927.md). The previous turn made concrete progress by identifying unresolved measurement boundaries; this turn resolves specific false positives and confirms a stronger limitation. No receiver, reference, control or benchmark test was executed.

## Findings

The pinned1,140-row source contains6,425 directly declared `TestCases` test-method definitions but only **6,419 distinct directly declared method names**. Six earlier definitions are shadowed by later definitions: one each in tasks90,392 and1006, and three in804. The analysis records Python's direct class-name binding order; arbitrary class-body mutation, decorators, inherited discovery and runtime behavior remain unexecuted. This is not a verified runtime test count. The generic earlier6,434 count included test functions outside the selected class and must not be used as its size.

Comparing complete method ASTs with only the method name normalized leaves public/private matches in tasks **59,427,537,628,681,684,739 and1112**. This comparison includes argument lists, decorators and bodies. Earlier body-only matches for604 and773 do **not** survive: their decorators and/or signatures differ. Thus neither the625 assertion-overlap flags nor all14 body-only pairs establish repeated test conditions.

Task628's five test methods have identical complete normalized ASTs: each invokes the function and checks plot-title/axis-label properties. Under the proposed first-method-public rule, **none of its four private methods has distinct method structure**. This does not prove identical stochastic realizations, general equivalence of all runtime states or semantic correctness. It does prove that this split adds no differently written private method for that task. Other identical-method pairs can generate random data or call state-dependent helpers; do not report them as deterministic identical input/output cases.

Task719's inheritance flag resolves to imported `pyfakefs.fake_filesystem_unittest.TestCase`, with explicit fake-filesystem setup. It requires dependency/fixture support, not an assumption that its tests are malformed. The26 class-assignment flags remain review items rather than automatic exclusions.

## Measurement consequence

The one-public/rest-private proposal remains **not released**. A defensible native-test design needs a prespecified method for constructing or auditing distinct private behavioral checks, retaining every source disposition. Status-only feedback prevents direct exposure of assertion text only if rendering and execution isolation enforce it; it does not repair a weak private endpoint. Do not move to a task subset selected by these flags and call it the full benchmark population.

For task628 specifically, repetition can measure stability of the same property, not automatically discrimination against an implementation that satisfies that property while violating the requested function. A separately specified wrong-control/reference audit is necessary. No control has been run and no failure rate is inferred. This negative source finding is preserved without changing the five-point useful-gain criterion or the original supported prompt/STOP question.

## Reproduction

[Builder](../scripts/adjudicate_bigcodebench_partition_flags_20260927.py), [immutable output](../results/bigcodebench_partition_adjudication_20260927.json), and [focused tests](../tests/test_bigcodebench_partition_adjudication.py). The builder pins the original Parquet hash, refuses overwrite, never imports dataset code, and records every task. Three new tests verify decorator-sensitive comparison, actual last-definition accounting, unchanged input AST and nonexecution; together with the six original partition tests, **9 tests pass**. AST hashes are structural evidence only; the raw source stays in ignored storage.

```sh
work/source_reader_20260927/bin/python scripts/adjudicate_bigcodebench_partition_flags_20260927.py \
 --source work/task_sources/bigcodebench_v014_20260927/v0.1.4.parquet \
 --out /tmp/bigcodebench_partition_adjudication_new.json
.venv/bin/python -m pytest -q tests/test_bigcodebench_partition_adjudication.py tests/test_bigcodebench_test_partition.py
```

Full-project readiness **60%, change0 percentage points**. No efficacy or trial-release credit. Population/measurement, complete prospective freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete. Codex owns implementation directly; goal remains active.
