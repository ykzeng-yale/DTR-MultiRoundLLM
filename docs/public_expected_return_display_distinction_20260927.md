# Correction: expected-value display and returned-value display are different gates

Signed: Codex scientific lead,27 September2026. This corrects the lead's earlier interpretation of the existing diagnostic contract. No production code,schema,task endpoint or action changed. The old immutable source audits remain available; the interpretation below governs new decisions.

## Existing source behavior,independently checked

`diagnostic._expected_display` requires a proposed public expected value to satisfy the bounded literal display policy. An expected float,dict,set or oversized nested literal therefore cannot form that v2 public skeleton without a separately justified change. By contrast,`_check_result` accepts an observed `value_kind=unsupported,returned=null` with either `status=pass` or `status=wrong_value`. `check_consistent` preserves the executor's in-isolation equality result in that case. It does not interpret an undisplayed return as missing execution or as a failure. Authentic execution/provenance remains necessary; a caller cannot invent pass/fail from an omitted value.

The [synthetic source-validation probe](../results/unsupported_return_display_probe_20260927.json) supplies five explicit records to the unchanged diagnostic builder and PATCH/RETHINK renderer. With integer expected16,an unsupported returned value is accepted for both pass and wrong_value,producing PASS and PAYLOAD_FAILURE respectively,with both actions available. Three controls refuse: observed pass with value_kind none;float text16.0 mislabeled as a displayable literal;and unsupported float16.0 as the public expected value. No reference,assertion,import payload or receiver was executed;these are supplied synthetic statuses,not observed task outcomes.

## Correction of the earlier814 statement

The September26 candidate adjudication said that814's actual float return requires a schema change or new measurement decision. **That requirement was incorrect.** Its integer public expected literal is displayable;the existing contract can retain an authentic pass/fail result while marking an actual float return unsupported for display. This is information omission under the existing bounded diagnostic,not schema incompatibility. The source statement that the return is a float remains valid;an actual graded outcome has not been newly observed here.

814 remains a definite prior-family relation and is not admitted to an untouched-family roster. This correction changes the erroneous display rationale,not the family decision or other unresolved domain/measurement assumptions. The immutable43-root record's `public_actual_display_axis` describes nondisplayability but must not be read as automatic checkpoint refusal. No integer cast,reference rewrite or new case is authorized.

## All103 import-layout roots: expected-side inventory

The [new immutable exploratory inventory](../results/import_layout_public_display_inventory_20260927.json) parses the original first assertion of every fixed import-layout root as inert AST/literals and checks its expected value with the unchanged display function. All103 have direct entry-point equality syntax and literal call arguments/expected expressions under this inspection. **87 expected literals are display-compatible;16 are not.** The16 are40,157,180,198,214,488,493,497,519,530,653,688,691,795,821,902. Nested lists can be unsupported because of contained types or size;the outer Python type alone is not a complete diagnosis.

This checks neither actual reference behavior nor all argument/interface/serialization bounds,family novelty,semantic specification,private measurement or future receiver performance. Syntax warnings for old regex escape sequences were emitted during source parsing;no imports ran. No root is approved. In particular,source-visible float returns such as55,491,518,931 and957 must not be subtracted from87 solely for being undisplayable. A status-only report for an unsupported return carries less information than a displayed value;that is already part of the frozen diagnostic's permitted information and must remain disclosed.

The103-root inquiry remains a new candidate-source scope. MRL-40 continues with its existing source-only assignment and original cap;this note adds no worker task or execution. Full-project submission readiness **58%,change0 percentage points**. Efficacy and independent policy validation remain absent. Population/family/sampling,complete prospective trial/resource freeze,independent policy evidence and manuscript remain the major milestones.
