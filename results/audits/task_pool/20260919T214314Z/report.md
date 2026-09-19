# Audit A1 — task-pool validity

Run 20260919T214314Z, 3.12.13, sandbox `seatbelt`, 4 workers, 17.2 s.

Task file `/Users/yukangzengcmac/DTR-MultiRoundLLM/work/data/tasks.json`

sha256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`

## Result

| check | quantity | value |
|---|---|---|
| — | tasks | 591 (MBPP 427, HumanEval 164) |
| S1 | references defining their entry point | 591 / 591 |
| S2 | MBPP visible assert identifiable as `test_list[0]` | 591 / 591 |
| S2 | minimum hidden asserts per MBPP task | 2 |
| S3 | references passing their full test set | 591 / 591 |
| S4 | references passing the hidden-only program | 591 / 591 |
| S5 | tasks passed by a do-nothing stub | 1 |
| S6 | median share of the solution BODY already visible | 0.1212 (MBPP 0.1395, HumanEval 0.0794) |
| S6 | tasks with >= 60% of the body already visible | 0 |
| S6 | median share of the *whole reference* visible (artifact: HumanEval references embed the prompt) | 0.1789 |
| — | **usable tasks** | **590** |
| — | excluded | 1 |

## Pass/fail rules

| rule | statement | pass |
|---|---|---|
| S1 | every reference defines its entry point | yes |
| S2 | MBPP visible assert is identifiable as test_list[0] for every task, and >= 1 hidden assert remains | yes |
| S3 | >= 98% of references pass their own full test set | yes |
| S4 | the hidden-only split does not break any reference that passed the full set | yes |
| S5 | no task is passed by a do-nothing stub | **NO** |

All rules pass: **no**

## Excluded tasks

| uid | ref full | ref hidden | stub passes |
|---|---|---|---|
| mbpp/794 | True | True | True |

## Reading

S3/S4 establish that the outcome is well defined: a task whose own reference cannot pass its assertions has no attainable outcome and must be dropped. S5 establishes that the outcome can *move*: a pool where a stub passes measures nothing. S2 is what makes the treatment separable from the outcome in this project — the single assertion shown to the receiver is identifiable, so it can be excluded from grading and interventions can be audited for quoting a graded assertion. S6 bounds how much of the answer is visible before any intervention is sent.

