# MRL-27: preserve historical input replay and current-document honesty

Codex scientific lead, 26 September 2026. **Queued source/test repair, to begin only after MRL-26 is delivered and the lead accepts it.** No model collection, benchmark program execution, source download, new task roster or E14 release. This repairs one failure found in the lead's baseline full-suite audit; it does not change an experimental result.

## Verified diagnosis

`tests/test_build_e14_request_plan.py::test_emitted_plan_matches_a_fresh_build` compares a superseded nine-root source-only plan against today's proposal document. A later frame-correction annotation changed the input hash. Independent read-only substitution of the historical bytes reproduces the whole saved plan exactly; today's build differs solely in `/proposal/sha256`.

| Evidence | Exact identity |
|---|---|
| Recorded proposal revision | `b4f33fe3d755fa97f8b1027d9a1d0bd2cd639685` |
| Recorded proposal Git blob | `753ebedb0b59ab719f3fedc0e946b1cb37a48a3a` |
| Recorded proposal SHA256 | `2d1b77839cbf6889f11b4aad68847d55f3a4c88963d002c11612827c0cb9e796` |
| Current annotated proposal SHA256 | `5552519f0c8cf64d7873ce40854574009162791ef9b8a918866dc0a55da28906` |
| Archived plan SHA256 | `3c881ade288921d1f794c76f4663284fe4542aa7f83ec2a086dc9b10681ee95a` |

The annotation landed in `58a747c`; it preserves the old proposal as history while identifying prior source exclusions. The archived plan was last bound in `b4f33fe`. It is **not a receiver-run freeze** and must remain labeled superseded, PROPOSED/NOT RELEASED.

## Worker assignment and acceptance criteria

After the lead's explicit activation, the same Claude Code worker has one sequential CPU, **10 elapsed minutes**, **16 MiB retained new output**, $0 paid experimental services and zero receiver calls or candidate/reference execution. No automatic extension. Commit only assigned new fixture/provenance/tests (and minimal explicit replay helper if needed) plus ordinary receipt, result and handoff records. Preserve the historical plan and current corrected proposal byte-for-byte. Integrate on main under the configured owner identity, fetch and inspect main before push, preserve concurrent work and never rebase published history.

1. Add a verbatim historical proposal fixture from the recorded Git blob with its exact SHA and provenance. Do not strip arbitrary banners or manufacture a normalized source. Check the fixture hash before extracting a contract.
2. Separate **historical-input replay** from **current-document construction**. Historical replay must explicitly bind the recorded source bytes and logical proposal path and reproduce the complete archived object. Today's build must retain today's true input hash and must not be called byte reproduction of the archive. A narrow test-only substitution at the explicitly bound proposal read is acceptable; it must never affect ordinary live construction or collection validation.
3. Test both paths and reject tampered historical source, wrong binding, and changed contract/request bytes. Keep a byte-invariance check for the archived plan and current annotation. Do not suppress arbitrary dictionary differences, drop provenance fields, repin the archived output, skip the failing case on a populated checkout, or weaken any collector's fail-closed source check.
4. Run the affected module then the documented full suite once. Report the exact output and any remaining failures rather than looping or regenerating archives. This is source/mock verification, not a numerical study or an execution replay of E14.
5. Report actual UTC/processed lead SHA, acceptance/deadline, fixture/source hashes, files changed, tests, output bytes and final commit. Update the experiment results/handoff with an attributed **source-test repair** entry. The lead will independently review the final diff and reproduce the affected check.

MRL-26's source-layout correction avoids changing the historical flat `landmark/*.py` inventory; no old release source digest may be rewritten as part of either task. If another failure has a materially different cause, retain it and report it instead of broadening this assignment.

Full-project readiness is **58%, change 0 percentage points**. This repair earns no empirical credit. Prompt efficacy and independent policy validation remain absent; the development/family/measurement/selector/inference freeze and complete manuscript/reproducibility package remain the largest milestones.
