# Offline graph measurement: executed validation and limits

21 September 2026, 01:36 UTC continuation. **This is deterministic task/measurement
validation, not an LLM experiment, prompt-effect estimate or policy trial.**
The original seven coding roots and all their holds are unchanged.

## What was frozen and run

The [offline protocol](graph_offline_protocol_20260921.md) and 32-root configuration
were committed at `58847236039b84f561bcc94c2ad53bd7e72e0fa1` before implementation.
The adapter, attributed source extraction, runner and tests were committed at
`61136c329768e9d826f89f70ca39a5483e36a680` before the batch. The runner verifies those
config bytes and its committed source bytes before generating tasks.

Three pure functions from the pinned Reasoning Gym source are now vendored with
the Apache-2.0 license and exact extraction hashes. The wrapper enforces a stricter
JSON contract and bounded generation. It imports neither the full upstream package
nor an external model runtime. The existing three-arm landmark collector is
unchanged; it does **not** implement the newly proposed five-arm study.

| Quantity | Observed |
|---|---:|
| Assigned offline roots | 32 |
| Accepted roots under the frozen greedy-success rule | 32 |
| Graph-generation attempts | 42 |
| Generation-cap failures / unattempted roots | 0 / 0 |
| Frozen hand-authored controls matched | 15 / 15 |
| Exact duplicate graph groups | 0 |
| Receiver calls / receiver tokens / external spend | 0 / 0 / $0 |
| Whole-process runtime | 0.233 seconds |
| Runner runtime including artifact writing | 0.177 seconds |
| Peak resident memory | 26,132,480 bytes (24.92 MiB) |
| Artifact bytes | 58,262 |

The whole invocation had a 60-second parent timeout; the validation loop also has
an alarm. RSS is checked between bounded roots and reported as peak RSS, not an
OS-enforced address-space limit. Output size is checked before writing. The batch
stayed within the 512-MiB and 10-MiB ceilings. Ten unsuccessful greedy proposals
preceded acceptance; they are not failed receiver answers or proof those graphs
were uncolorable. No candidate program, coding reference, sandbox launch, model
download or package installation occurred.

The [run summary](../results/graph_offline_20260921_run.json) records both freeze
commits, usage and the immutable manifest hash. Generated public tasks, private
reference colorings, every root's ledger and control outcomes remain in ignored
`work/graph_offline_20260921_0136_v1/`. The [independent review](../results/graph_offline_20260921_independent_review.json)
verified file/source hashes, root bindings, all 32 reference colorings and all 15
controls without regenerating tasks or calling a model.

## Validation that matters for measurement

The full project suite passes **222 tests and 8 subtests in 1.52 seconds**. This
includes an independent direct-edge truth comparison of every simple graph on
four vertices and every three-color assignment: 64 × 81 = 5,184 cases. Those
enumerated cases are not independent empirical observations or trained-model
examples. Valid color permutations remain valid; the grader does not demand one
particular reference coloring.

Adversarial checks cover duplicate and escaped-duplicate JSON keys, malformed or
oversized output, noncanonical vertex names, extra/missing keys, booleans, decimals,
exponents, non-finite constants, wrong color domains and excessive nesting.
Invalid trusted puzzle specifications raise an error; they do not create a zero
receiver grade. A genuinely absent response remains missing. The 15 frozen
controls include that missing-output case, so “15/15 matched” is not 15 successful
answers. All public rendering is whitelisted and never receives the reference.

Independent review found and repaired an interrupted-write inconsistency before
execution: public and private exports could have disagreed if interruption occurred
between appends. The runner now accepts one complete record, then derives both
exports and ledger counts from it. Seven focused failure tests check interruption
before/after acceptance, unknown attempt counts, bounded failure artifacts,
changed-config refusal and immutable successful/failed directories. A start marker
and an atomic final manifest distinguish incomplete artifact writes from a
completed validation record. These injected failures are software checks, not
observed service-failure rates.

## Scientific judgment and next release gate

This establishes a usable **offline** checker/fixture component for a controlled
graph-feedback extension. It does not establish the effectiveness of feedback,
history-dependent selection, causal estimation, stopping or an autonomous policy.
The accepted graph population is deliberately selected by a cheap greedy
algorithm; that algorithm already supplies a valid solution for each accepted
root. Consequently these tasks cannot, on their own, justify using an LLM for
practical graph solving. Their role is a transparent feedback-mechanism test.

A complete public verifier can validate STOP on a passing answer by construction.
That is not an empirical discovery or a guarantee for coding with sparse tests.
All 32 roots remain in one shared development family. Exact duplicate screening
does not establish isomorphism-free families, independence, pretraining novelty or
unseen-family generalization.

Next, freeze a graph-specific instruction renderer, diagnostic/no-diagnostic
access, restart state and receiver/decoding contract before any model calls, or
continue the original coding task once isolation/reference validation is available.
The present adapter does not authorize either collection. The later independent
policy trial still needs untouched roots, a competent fixed comparator, a useful
gain, precision/futility rules and a complete cost budget. The resource inquiry
asks for an existing Linux/GPU environment or permission to prepare a capped API
proposal; no resource or paid-service approval has been assumed.

The theoretical manuscript's live source pointers were also corrected after an
independent review: the superseded literature audit cannot govern novelty claims.
Historical documents stay intact; current README/theory link to the corrected
primary-source and methods reviews. No new foundational theorem is claimed.

**Planning progress remains 49%, Δ=0 percentage points.** This completes the narrow
offline component, but the fixed rubric's pending measurement/receiver release,
fresh prompt experiment and independent policy validation remain open. The full
project is not submission-ready.

## Reproduction

At implementation commit `61136c3`, with the documented Python environment and
dependencies, use a new directory:

```bash
uv run --extra dev pytest -q
.venv/bin/python scripts/validate_graph_offline.py --output work/graph_offline_reproduction_new
```

The published execution also wrapped the second command in a 60-second process
timeout. Compare generated task/control/ledger payload hashes, not runtime fields
or the whole manifest hash, which includes machine-specific runtime provenance.
Retain any new run separately; never overwrite the recorded run. This is optional
reproduction guidance, not a request to repeat unchanged work every hour.
