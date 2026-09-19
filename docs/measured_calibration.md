# Measured calibration — what a receiver call actually costs on this machine

Every cost figure in this project's designs must trace to a measurement, not an
assumption. This file holds the measurements and their provenance. Update it when a
new measurement supersedes one, and never delete a superseded row.

## Provenance

Source: the sibling project `ykzeng-yale/DTR-AgentEvals`, pilot stage of its
code-routing experiment, `results/code_routing/pilot/episodes.jsonl` — **120
episodes, 163 receiver calls**, read 2026-09-19. Same machine (Apple M5, 32 GB, 10
cores), same inference server (`llama.cpp` `llama-server`, `-ngl 99 -np 4 -c
32768 --jinja`), same task pool (MBPP-sanitized + HumanEval, 591 tasks), same
quantizations. Measured **with a foreign GPU load present** (`--allow-contention`),
which is the condition this project will also run under, so these numbers are
realistic rather than best-case.

These are *coding* tasks with short statements and short answers. Do not carry
these numbers to a different task family without re-measuring.

## Per-call measurements

| model | n calls | prompt tokens (median / p90 / max) | completion tokens (median / p90 / max) | wall seconds per call (median / p90 / max) | implied per-request tok/s (median) |
|---|---|---|---|---|---|
| Qwen2.5-3B-Instruct q4_k_m (port 8193) | 80 | 174 / 443 / 846 | 67 / 164 / 253 | **3.2** / 12.5 / 22.5 | 22.2 |
| Qwen2.5-7B-Instruct q4_k_m (port 8191) | 83 | 103 / 553 / 974 | 67 / 149 / 236 | **6.4** / 16.2 / 26.6 | 10.0 |

Per-request tok/s (22.2, 10.0) is far below the aggregate throughput measured for
these servers (about 116 tok/s for a 3B and 67 tok/s for a 7B at four slots)
because four requests are in flight at once and a sibling job is also on the GPU.
For planning, **use the wall-clock-per-call column and divide by the number of
slots**, not the aggregate tok/s figure.

## Throughput actually sustained

The same project's full log stage sustained **2.28 s per episode** over 4,488
episodes with 0 errors (≈ 2.8 h) at roughly 1.36 receiver calls per episode,
i.e. about **2,150 receiver calls per hour** for a mixed 3B/7B load under
contention. Pure-3B work should reach roughly 4,500 calls/hour
(4 slots ÷ 3.2 s) and pure-7B roughly 2,250 calls/hour (4 slots ÷ 6.4 s).

## What this implies for this project

An episode here is an initial attempt plus up to `T` interventions, so it costs
`T + 1` receiver calls, and the prompt grows with the conversation. Using the
medians above, prompt length at turn `t` is roughly
`93 + t x (67 + intervention_length)`; with interventions of about 40 tokens the
turn-3 prompt is around 375 tokens — small enough that context length is not a
binding constraint for this task family, and that prompt processing is not the
dominant cost.

Planning figures to use until superseded:

| quantity | figure | basis |
|---|---|---|
| receiver call, 3B, 4 slots, contended | **3.2 s wall** | measured, n = 80 |
| receiver call, 7B, 4 slots, contended | **6.4 s wall** | measured, n = 83 |
| verification in the Seatbelt sandbox | **0.03 s** (median), p90 0.04 s | measured, n = 120; and 17.4 s for 1,773 sandbox runs in Audit A1 |
| sustained calls per hour, mixed load, contended | **≈ 2,150** | measured over 4,488 episodes |
| calls per episode at `T` interventions | `T + 1` | by construction |

So a branch-tree node (one receiver call plus one verification) costs about
**3.2 s** on the 3B. Ten thousand nodes is about **9 hours** of contended
wall-clock on the 3B, or about **18 hours** on the 7B. Any design that needs
substantially more than 10,000–20,000 nodes is not affordable here and must be cut
before it is frozen, not after.

## SUPERSEDED for multi-turn work (2026-09-19, later the same day)

The per-call figures above were read from a sibling log dominated by **first**
attempts with short prompts. A pilot on this project's own multi-turn workload
measured **3.96 s per 3B call (909 calls/hour)** and **5.82 s per 7B call (619
calls/hour)** at four slots under foreign load, with median prompts of ~275 tokens and
completions of ~130-175 tokens. Use those for anything multi-turn; the 2,150
calls/hour figure applies only to single-attempt work and makes multi-turn designs look
about 2.4x cheaper than they are. See `docs/pilot_findings.md`.

## Open measurements still needed

* **First-attempt success rate on the 590-task pool, per model.** Required for
  power: if it is near 0 or near 1 the intervention effect is unmeasurable. Needs
  GPU, so it is the first action after the design is frozen. The sibling project's
  pilot reported first-call success of 0.667 (3B) and 0.762 (7B) on its own
  prompting format — high enough that a ceiling effect is a real risk here and the
  task pool may need to be filtered to a harder subset.
* **Degradation rate**: how often a further turn turns a correct answer incorrect.
  Unmeasured, and it is the harm outcome for the stopping experiment.
* **Intervention message lengths** for the frozen taxonomy, once the templates
  exist.
