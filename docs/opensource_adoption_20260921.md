# Concrete open-source adoption handoff

21 September 2026. **Initial source-adoption handoff.** The narrow graph component
has subsequently been implemented and checked in the [offline validation
report](graph_offline_validation_20260921.md); the full upstream runners remain
uninstalled and no receiver collection is released. Use the
[source inventory](literature/source_inventory_20260921.json) for exact commits,
URLs, SHA-256 hashes and licenses. It covers 11 repositories and 145 unique source
files, including inspected paper downloads. This is an audit inventory, not a
reproducible environment or proof of complete source review. Retain third-party
licenses and file notices when adapting code; our new commits remain attributed
to Yukang Zeng.

## First offline component: objective feedback without executing model text

Use Reasoning Gym revision `49b07130b3fcd12f2d064bba7c43869543a0e7e7`,
[`reasoning_gym/algorithmic/graph_color.py`](https://github.com/open-thought/reasoning-gym/blob/49b07130b3fcd12f2d064bba7c43869543a0e7e7/reasoning_gym/algorithmic/graph_color.py),
Apache-2.0. Narrowly extract `generate_random_graph`,
`verify_graph_coloring_solution` and `greedy_graph_coloring`, with attribution and
an explicit diff from upstream. Keep our existing collector, immutable records
and inference. Do not import the whole task library.

Required adapter behavior:

- A strict bounded JSON object: every vertex once, no extra/duplicate keys,
  allowed integer colors, excluding booleans/fractions. Binary success is full
  validity; upstream's 0.01 partial score is not success.
- Public fields are whitelisted. The reference `possible_answer` remains outside
  prompts. A public edge-conflict diagnostic is permissible; both diagnostic
  repair arms receive the identical report.
- Bound the generator's attempts. Record failures and the acceptance rule;
  acceptance by a greedy solver changes the generated population.
- Keep relabelings/descendants together. Distinct seeds alone do not establish
  distinct topology families or no pretraining exposure.

Before implementation, freeze a small offline fixture/config file. Proposed cap:
32 seeds; 8–12 vertices; three colors; an exact edge-probability schedule chosen
within 0.1–0.3 before generation; 128 attempts/root; one CPU worker; 60 seconds;
512 MiB memory; 10 MiB artifacts; 16 KiB maximum response text. Check known valid
and invalid mappings, malformed/oversized output, missing and duplicate keys,
wrong color types, deterministic provenance, and reference-field isolation.
This is trusted source/fixture processing, not execution of generated programs.

No receiver call follows automatically. This controlled extension has a complete
public verifier and an ordinary algorithmic solution; it is useful for measurement
and mechanism checks, not sufficient evidence of practical LLM benefit. It does
not replace the seven coding roots. The root design's 132-call *alternative*
development ceiling supersedes the reviewer's exploratory 168-call suggestion
for this five-arm design; neither is an execution freeze.

## Original coding component: defer execution, reuse measurement deliberately

Use EvalPlus revision `26d6d00bb1fd0fa37f39c99d5290da67891d1c5e` as a
source reference for `evalplus/eval/__init__.py`, `evalplus/eval/utils.py` and the
MBPP loader. Code is Apache-2.0 with retained third-party notices. Its guard is
not a security sandbox. Do not run candidates or references until containment
passes controlled checks. Stage exact task/test bytes and block implicit
evaluation-time downloads. Mapping a later Plus endpoint to our existing roots
requires a separately frozen measurement version; it cannot overwrite historical
labels. The unresolved task-402 reference defect and all original exclusions
remain visible. Return the runtime/isolation specification and measured preflight
before requesting model collection.

## Later application: instruction constraints

Multi-IF code revision `1cdb53ed18499ad729e0766e5d3099dd5344406f` is
Apache-2.0. The separately pinned `facebook/Multi-IF` dataset revision
`0ab97ce0b45c7f57772e8ba2ac1616f4b00bd3aa` declares CC-BY-NC-2.0.
Its CSV has not been downloaded; an eventual acquisition can be capped at 8 MiB
and must compute the actual file hash.

Reuse the schema and a reviewed subset of `ifeval.py` strict checkers. Freeze
nonempty constraints and all parameters; reject checker failures rather than
passing them. Keep translated variants together and preserve missing rows.
Adding alternative repair prompts creates an **adapted** task, not the untouched
official turn sequence. Constraint compliance needs a separate semantic-quality
assessment before claiming useful writing assistance.

## Acceptance and resource request

The next deliverable is one narrow adapter with source attribution, fixtures,
exact task/feedback fields and a bounded offline validation report. Preserve the
original collection and analysis framework; do not build another broad harness.
Only after those checks should the coordinator decide which explicit development
target and receiver to freeze. Use the
[literature-guided design](literature_guided_design_20260921.md) for arms, information
boundaries and accounting.

No paid service or key is needed for this step. For the coding track, report a
working isolated evaluator and an existing competent receiver's exact endpoint,
digest, decoding/template and available resource window. If unavailable, provide
a concrete capped resource proposal. Do not silently substitute the small cached
receiver or a different benchmark and call the original question answered.
