# Frozen one-landmark prompt comparison

**Status:** runnable mock-tested collection and offline analysis scaffold. No receiver calls or candidate programs were executed to validate this package. The supplied fixtures have no empirical outcome labels. The governing study design is [the landmark protocol](../../docs/landmark_experiment_protocol.md); preparing these files does not freeze or authorize a real study.

For each eligible root, collect one initial answer and restore that exact public conversation for generic repair and a frozen history-specific repair message. Independent restart repeats the original public task without the old answer. Each continuation uses one receiver call. With two independent continuations per arm, collection requires seven calls per root; a deployed arm would require two. STOP preserves the initial answer without a continuation call. All three arms are collected with inclusion probability one; seeded execution order is randomized separately. This is a fully branched finite-prompt comparison, not an observational logger or a learned policy.

The history-specific renderer chooses a fixed checklist using the presence of loop-related words or division in the initial answer. It is a deliberately limited syntactic scaffold, **not a validated semantic-feedback method or personalized causal critic**. Both repair arms share exactly the same task, public context, and initial output. Their instructions differ without adding hidden evaluation facts. The generic versus targeted comparison changes wording; repair versus restart additionally changes access to the earlier answer. No public test is executed during collection. `public_context` contains only preapproved public information; its provenance still needs independent content review.

## Run without a model

From the repository root, use a new output directory:

```sh
uv run python experiments/landmark/collect.py --config experiments/landmark/mock_config.json --tasks experiments/landmark/mock_tasks.jsonl --output work/landmark_mock_new
uv run python experiments/landmark/analyze.py --run work/landmark_mock_new --output work/landmark_mock_new_analysis.json
uv run --extra dev pytest -q tests/test_landmark_collector.py
```

The default adapter is mock. A real local Ollama receiver requires the explicit `--real` flag and all freeze checks. The OpenAI-compatible transport is not implemented in this bounded package. `mock_run_v1/` and `mock_analysis_v1.json` preserve an executed two-root transport check. Their ungraded quality bounds are [0,1] and contrast bounds are [−1,1]; no empirical score or confidence interval is manufactured.

## Freeze and information contract

Task JSONL has exactly four string fields: `root_id`, `family_id`, `prompt`, and `public_context`. Extra fields, including solutions or hidden tests, are rejected. Families determine deterministic train/development/test assignments; all branch replicates remain together. Declaring a prior-seen root excludes its entire known family in the supplied task file. `prior_seen_family_ids` handles related roots outside that file. The freeze process must supply the full reviewed exclusion roster, including aliases; the software cannot infer all previous exposure.

This collector implements strict exclusion, not a reused-development mode. The previously analyzed 591-task pool cannot be presented as fresh validation by giving it new seeds or omitting prior-seen IDs. An explicitly reused development study needs a separately reviewed eligibility/evidence contract; it is not silently enabled here.

The config fixes protocol, model name/content digest, server build, decoding, budgets, replicate count, split seeds, exclusions, public dataset source/license, and grading-contract hash. `--print-freeze` prints canonical dataset and executable-source hashes plus the complete seeded order table without any model connection. Fill the real placeholders, commit the task file, config, protocol, and source, then keep `freeze_commit` equal to the literal `HEAD`. At runtime the collector resolves HEAD and verifies the config/task/source bytes against that commit before connecting. This avoids an impossible self-referential commit hash inside a committed config. The runtime manifest records the resolved commit, config/data/code hashes, root IDs, exact messages, random seeds, model definition/template, pre/post receiver digests, and every attempted request/response. A stale explicit commit SHA also fails.

The supplied mock config deliberately fails real-mode validation. A real freeze still needs an approved task/evaluator contract, audited model/tokenizer/context behavior and independently reviewed public/hidden information separation. Model content and server build are checked against the local service. Identical beginning/end digests do not prove the service never changed between calls or establish independent model noise.

## Bounded execution and complete accounting

Before each generation, admission checks call count, remaining client time, request bytes, and worst-case completion-token reservation. Each admitted call permanently reserves its full completion cap, including failed/time-out calls. A reported server completion-cap violation prevents every later dispatch. Actual prompt tokens are recorded separately: **the completion cap is not a certified total-token cap**. Requests use the fixed context size, but this package does not certify the server's tokenizer or rule out silent truncation; that feasibility gate must precede substantive collection. A client timeout can leave server work running, so the wall-clock setting guarantees no new dispatch after expiry, not cancellation of all server computation.

Every assigned root and arm/replicate remains in `roots.jsonl`, including initial failures, unavailable continuations, exclusions, and missing usage. No missing output is relabeled STOP or assigned a quality score. `manifest.json` is written once, append-only JSONL captures calls and roots, and `completion.json` closes the run with checksums and realized costs. Existing output directories and analysis files are refused. Interrupted/incomplete runs lacking the completion record require explicit recovery and are not silently analyzed.

## Offline grades and analysis

There is no candidate-executing grader in this package. After the grading contract is frozen and validated, a grading worker may use the repository's sandbox and frozen scoring/integrity checks to produce grade JSONL. It must pin the public/hidden assertion split, grader source, reference validation, canary/randomness, and expected deterministic grading behavior. The collection process never reads that file.

Each grade row has exactly:

```json
{"root_id":"example","arm":"generic_repair","replicate":0,"output_sha256":"hash from the collected artifact","outcome":1,"missing_reason":null,"grader_id":"frozen grader version","grading_contract_sha256":"same hash as config"}
```

Binary `outcome` may be null with an explicit reason. No hidden grade is accepted for a missing output. Root/arm/replicate, output hash, grading contract and collection checksums are validated; duplicate or mismatched rows fail. Identical output artifacts within a root must receive consistent deterministic grades. Stochastic scoring would require an explicitly extended measurement contract. Run:

```sh
uv run python experiments/landmark/analyze.py --run PATH_TO_RUN --grades PATH_TO_OFFLINE_GRADES --split test --output NEW_ANALYSIS.json
```

Replicates are averaged within each root. Contrasts give every assigned root equal weight and cluster uncertainty by declared family. With fewer than two independent families, incomplete assigned grades, or a failed receiver-identity gate, confidence intervals are suppressed. Complete-case point estimates remain clearly labeled; worst/best [0,1] outcome bounds retain every missing replicate. No missing-at-random assumption is imposed. The normal family-cluster interval is an approximation, particularly weak with few families, and multiple contrasts are not automatically multiplicity-adjusted or promoted to confirmatory tests.

Quality, calls, prompt/completion tokens, and latency are separate. Arm costs count one initial call plus the mean cost of one continuation; total collection costs pay for all generated branches. Failed or unfinished collection costs are not estimates of a complete deployed policy's cost. The analyzer does not train a selector, use evaluation labels to choose prompts, infer one conversation's individual causal effect, or claim that a one-landmark result identifies a full dynamic regime.
