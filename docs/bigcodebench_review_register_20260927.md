# Consolidated source-review register

Codex scientific lead, 27 September 2026. This replaces manual counting across scattered review batches with a reproducible source register. It is **not** an admitted population, final family partition, untouched-task certificate or release to collect outcomes.

The [register](../results/bigcodebench_review_register_20260927.json) covers all 1,140 source tasks: 57 have recorded four-field semantic review evidence (0–55 and 887), 1,083 remain pending, and zero are admitted. A pending entry is retained rather than omitted. The separately recorded task628 reference/control measurement exposure does not imply that its full semantic-family review is complete. Empty exposure lists explicitly mean no exposure recorded here, not untouched: the broader prior-development crosswalk is pending for every row.

Ten evidence-attributed constraint records preserve the provisional co-split groups and the exact four-field duplicate pair1120/1121. Superseding groups retain provenance:29/38 and29/38/47 remain separate evidence records. They cannot be counted as separate independent families. Any eventual split must satisfy every retained constraint jointly, or document a scientifically justified superseding adjudication before outcomes. This register does not construct a transitive global family partition; missing links do not certify independence. Exact shared statements, shared solution bodies alone and shared libraries are not promoted into family constraints.

The builder checks all reviewed task IDs, row indices and four field hashes against the pinned-source inventory. It rejects conflicting source hashes, stale field bindings, duplicate reviewed IDs within a document, unknown constraint members and any attempt to label a task admitted under this source-only schema. Known exposure records bind the same four fields plus saved evidence-file hashes, checked at build time. Existing output paths are refused. It reads JSON only and executes no benchmark source.

## Reproduce

From the repository root, choose an unused output path:

```sh
.venv/bin/python scripts/build_bigcodebench_review_register.py \
  --inventory results/bigcodebench_rows_inventory_20260927.json \
  --reviews \
    results/bigcodebench_semantic_review_0000_0015_20260927.json \
    results/bigcodebench_semantic_review_0016_0023_20260927.json \
    results/bigcodebench_semantic_review_0024_0031_20260927.json \
    results/bigcodebench_semantic_review_0032_0039_20260927.json \
    results/bigcodebench_semantic_review_0040_0055_20260927.json \
    results/bigcodebench_source_relation_887_20260927.json \
  --exposures results/bigcodebench_known_exposures_20260927.json \
  --out /tmp/bigcodebench_review_register_new.json
.venv/bin/python -m pytest -q tests/test_bigcodebench_review_register.py
```

The full suite passes 2,315 tests plus8 subtests in35.84seconds. Fourteen focused tests pass, including stale evidence, invalid constraints, duplicate handling, changed exposure receipts, overwrite refusal and the distinction between a partial match and a four-field duplicate. A separate lead reconciliation verifies the exact reviewed-ID set, all1,140 row dispositions, eight input-file hashes, task628 exposure and the duplicate constraint without calling the builder. This checks bookkeeping, not the correctness of every semantic judgment. See the [reconciliation](../results/bigcodebench_review_register_validation_20260927.json).

## Scientific next step and efficiency

Continue substantive source/family review in larger batches, starting at56 and following unresolved semantic relatives; use the register to avoid rereading completed sources or losing constraints. Do not claim efficiency from bookkeeping alone: the global family/exposure and measurement decisions remain substantial unfinished work. A future admission contract needs explicit, outcome-independent specification rules and a qualified execution/measurement environment. Neither the count1,140 nor the count57 establishes a feasible independent evaluation sample. The current source inquiry is not a reason to change the useful-gain threshold, comparison policies or original scientific target.

No new benchmark or receiver calls; $0 paid experimental services. Codex implements directly. The Docker restoration question remains pending; no restart or permission is inferred. There is no long-running experimental job to monitor.

Full-project readiness remains **60%, change 0 percentage points**. No additional credit is earned by consolidation. Population/family/measurement validation, complete prospective freeze, independent policy evaluation and final manuscript/raw-environment reproduction remain incomplete; efficacy is unestablished.

The owner subsequently requested a token-saving goal pause. No experiment is running, so the heartbeat stays paused; this is not a wait for forthcoming results. Resume substantive work on owner instruction.
