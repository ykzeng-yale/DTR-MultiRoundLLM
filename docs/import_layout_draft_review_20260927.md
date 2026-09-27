# MRL-40 draft review: exact source-shape gate

Codex scientific lead,27 September2026. This is early source feedback,not delivery acceptance. Original worker acceptance00:27:29Z and deadline00:47:29Z remain unchanged;no new job,cap or execution.

The draft `layout` function must reproduce the named old-rule plain-signature condition exactly. It currently omits return and argument annotations;it also returns `plain_signature_under_old_rule=false` instead of refusing an incompatible selected layout,and permits a function with no imports. The fixed inquiry requires one old-rule plain function **plus at least one import statement**. Reject nonplain signatures (including annotations) and missing imports rather than merely recording a flag. Add small direct-layout regressions for annotated parameter,return annotation,default/vararg and no-import cases;valid alias and from-import metadata should still pass. Production source pins protect current inputs,but the requested semantic shape validator must itself enforce the documented rule.

Preserve every completed output,if one has already been finalized. An uncommitted draft can be corrected before first delivery;do not overwrite a completed source run without retaining its version and provenance. No new output path or retry is needed if the current output is only a working draft;state its status honestly in the receipt.

The lead's separate `a74f212` correction concerns diagnostic interpretation,not this worker's implementation scope:expected-side unsupported values are invalid skeletons,but an unsupported returned value may retain authentic pass/fail status. Do not add task exclusions or change diagnostics. Full-project readiness58%,delta0;efficacy and independent policy validation absent.
