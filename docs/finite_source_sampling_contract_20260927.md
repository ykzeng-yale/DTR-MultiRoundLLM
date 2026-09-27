# Uniform untouched-family sampling from a finite source

Codex scientific lead, 27 September 2026. Prospective design and classical concentration argument, not a receiver result, adopted roster, power calculation or collection release. This supplies the missing without-replacement sampling argument identified in the [family clarification](policy_family_independence_clarification_20260926.md). Earlier negative findings and exclusions remain unchanged.

## Target and assumptions

Conditional on frozen development information F, let an eligible evaluation frame contain N families. Policies, receiver, endpoint, family membership, within-family aggregation weights and complete execution law are fixed in F. No family in this frame contributed receiver outcomes to policy development or selection; source/measurement exposure must be separately recorded. Untouched by this development process does not mean absent from receiver pretraining.

For each family g, define the complete latent two-contrast vector D_g in [-1,1]^2 under that law. Assume the N vectors are mutually independent conditional on F. They may have different distributions, and the two contrasts or branches within a family may be arbitrarily dependent. Shared canonical branches still require the declared correct conditional action marginals. The independent-family law is an assumption supported by operational isolation, not established by distinct names or by this proof.

Choose fixed n with 1 <= n <= N, then draw a uniform n-element subset S independently of all evaluation execution inputs conditional on F. Uniform subset selection is by construction of a future validated sampler; no sampler or realized assignment table is frozen here. Do not replace held families, choose n after outcomes, or treat completed cases as the original sample. The target for contrast j is

`theta_j = (1/N) sum_g E[D_gj | F]`.

This is the equal-family mean in the declared finite eligible source. It is not the average only over the realized sample, not a random-frame superpopulation effect, and not a claim about arbitrary programming tasks, humans or pretrained-model novelty. Root weights inside each family are fixed before outcomes; a family containing more benchmark IDs receives no extra total population weight.

## Why the existing KL rule applies

For either sign let X_g=max(±D_gj,0), mu=N^-1 sum_g E[X_g|F], and a_g(t)=E[exp(t X_g)|F]>0. For every real t, independence of the complete family vectors and uniform selection give

`E[exp(t sum_{g in S} X_g) | F] = e_n(a_1,...,a_N) / choose(N,n)`.

Here e_n is the elementary symmetric polynomial. Its classical Maclaurin bound is at most `(N^-1 sum_g a_g)^n`. One elementary justification fixes the sum of positive a_g and averages any pair: e_n has the form C+(a+b)B+ab A with A>=0, so averaging cannot decrease it; the equal-vector limit has value choose(N,n) times the nth power of the mean. For n=1 equality is immediate. Convexity on [0,1] then gives

`a_g(t) <= 1 - E[X_g|F] + exp(t) E[X_g|F]`,

hence the preceding moment generating function is at most `(1-mu+mu exp(t))^n`. Chernoff optimization for positive and negative t yields the same one-sided binary-KL bounds used by the [accepted inference contract](paired_kl_inference_contract_20260926.md). This is an application of classical symmetric-mean and bounded-variable concentration arguments, not a novel theorem. No assertion that the sampled observations are independent is needed or made.

Apply the same alpha/8 allocation to four sign means for the two contrasts. The resulting intervals jointly cover the finite-frame theta vector with probability at least 1-alpha conditional on F, over both subset selection and execution. Correlation between contrasts requires no additional assumption. At n=N the selection uncertainty disappears, but execution uncertainty remains; this interval uses no finite-population correction and need not have zero width. At n=1 the argument reduces to the mixture distribution over families.

The accepted pathwise missingness envelope contains the complete-data intervals for each assigned sample, so retains this coverage under its existing latent-outcome and containment conditions. It does not repair nonexistent endpoints, an incorrect frame or an integrity breach. Measurement sensitivity must use the same finite-frame weights and execution law.

Do not condition this statement on the realized S while retaining the full-frame target. Conditional on S, the independent-execution interval instead targets the average expectation over S, as in the earlier fixed-roster clarification. Likewise, conditioning on deterministic realized model seeds changes the execution expectation. F fixes sampling and execution laws, not the draws that this probability statement averages over. Selection influenced by prospective grades, adaptive replacement, common random service drift, dependent family vectors or unequal inclusion probabilities fall outside this proof.

## Integrated population and measurement proposal

The next candidate design uses the pinned BigCodeBench v0.1.4 source as a source-relative population proposal, with the following decisions settled before receiver outcomes:

1. Review the entire 1,140-row source, not only easily executable scalar tasks. Form operational semantic families, document uncertain relationships and crosswalk prior development exposure. Exact duplicate1120/1121 stays together. Library names are not family labels. Freeze the complete admission/exclusion ledger with reasons; unresolved specification or grading-integrity cases remain unresolved, not silent failures or favorable exclusions.
2. Reserve whole families for development and evaluation before any new receiver policy fitting. Native task628 and its family are measurement-development exposed; its status must be explicit. Source-only lead review is a different exposure class and is not concealed. Conservative prior family exclusions remain intact. Actual split sizes require the finished frame and a finite joint precision/resource assessment; none is invented from 1,140 IDs.
3. Evaluate a frozen learned policy against the same fixed-recipe and budget-aware redraw comparators under the existing landmark contract. Use uniform family sampling without replacement from the remaining untouched eligible evaluation frame, under the argument above. The supported actions, STOP/fallback law and all rendering changes must be committed before collection. A landmark result is a prerequisite, not completion of the original repeated-interaction objective.
4. Treat original native-test score Z as a named measurement outcome only. Do not call it semantic correctness Y or silently repair native suites. A distinct semantic endpoint requires a separately frozen specification and validation design. The first-method-public split remains rejected for release; a public-check/private-score protocol requires source isolation, truthful supervisor transport, bounded feedback and overlap adjudication. Status serialization alone does not supply these properties. No benchmark-grade result alone establishes semantic policy benefit.
5. Complete a bounded development protocol only after these population/measurement commitments and operational qualification. Use its disagreement estimates for transparent joint scenario planning, not for selecting favorable held-out families. Keep the useful-gain threshold, inference method, same-receiver contract and historical negatives. Freeze the full evaluation size, assignment law, cap/missingness handling and analysis before evaluation outcomes. Count development, evaluation and qualification resources separately; $0 paid experimental services remains binding.

This is a concrete proposed source/sampling path, not adoption of BigCodeBench or a substitute success criterion. The original task still requires useful supported history-conditional decisions, independent evaluation and a justified connection to repeated prompting/STOP. If measurement or the feasible population cannot support that test, record that limitation and do not redefine the project as a benchmark-score success.

## Verification and progress

The existing internal inference reviewer accepts the argument, including joint-over-selection-and-execution coverage, n=N and pathwise missingness. Four new tests plus46 existing inference tests pass. The accompanying exact finite-law tests enumerate subset selection and stochastic outcomes, check the moment bound with rational arithmetic for both signs and all subset sizes in specified heterogeneous laws, and check simultaneous interval coverage under those laws. These are synthetic enumeration checks, not proof for all laws or evidence that real executions satisfy independence. The argument above supplies the general result under its assumptions. No new estimator or model collection is introduced.

Full-project submission readiness **60%, change 0 percentage points**; no credit for an unimplemented sampling proposal. Population admission/measurement, full prospective freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete. Codex-only implementation; continuous goal active.
