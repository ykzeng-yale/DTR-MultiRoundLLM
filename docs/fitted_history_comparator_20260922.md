# Fitted complete-history comparator: source validation

22 September 2026. Lead-owned work for issue #2. **Evidence classification:
implementation and deterministic fixtures, not a Monte Carlo study or an LLM
experiment.** Existing corrected E0 and matched-fit results remain unchanged.

## What is now available

`experiments/e0/history_estimators.py` wraps the existing backward tabular
regression and sequential DR score without changing either pinned implementation.
At active decision t the predictor is

    H_t = (S_0, ..., S_t; A_0, ..., A_{t-1}).

It includes the entire recorded synthetic state/action prefix. It excludes the
current action from the predictor key (the action is the regression response
stratum), future states/actions, latent ease/type, propensities, terminal outcome
and task identity. Training outcomes are regression targets; known propensities
enter the DR correction; task identities define the folds. These legitimate uses
are distinct from using those quantities as decision-time predictors.

All trajectories from the same root task stay in one fold. An optional explicit
fold vector permits a later matched comparison to reuse exactly the same root
folds. Noncontiguous root labels are encoded without treating their numeric value
as an array position. In each training fold, Q is fitted once. Both held-out
plug-in predictions and DR scores use that same Q, fallback, key and target policy.
The module returns episode scores and the auditable fold fits; pass the returned
`task_index` to the existing `task_clustered` function for equal-root summaries.
The existing normal interval is not newly validated by this wrapper.

## Scope of history adequacy

The population sequential-regression target is justified for the declared E0
law with **`gz=0`, `mislabel=0`, supported actions and correctly recorded complete
prefixes**. At an active decision, assignment depends only on recorded S_t. Given
H_t, assignment is therefore independent of persistent latent ease/type (E,Z).
More explicitly, the factors for earlier action assignment in the likelihood of
H_t depend on its observed states/actions, so they cancel from the posterior over
(E,Z). The state transitions still update that posterior. Conditioning on current
A_t introduces no additional latent selection. Backward conditioning of the
terminal outcome under the fixed target continuation then gives the population
Q recursion using H_t.

This is a representation/identification argument in a specified synthetic law.
It does **not** prove that finitely observed tabular cells estimate Q accurately.
The actual synthetic state S distinguishes levels of quality, including true
correctness. It is declared observed in E0 and is not asserted to be an available
public feature of a real LLM interaction. Repeated episodes share root latents,
which is why their folds and uncertainty units remain roots.

With `gz>0`, logging can depend on hidden Z, so the above unweighted Q-regression
argument does not apply. Supplying exact latent-dependent assignment probabilities
to DR does not make this Q learner an adequate-history regression for that cell.
With treatment mislabeling, the recorded action need not be the intervention that
generated the outcome. Neither condition is repaired by the new key. Supported action classes retain
the declared within-class template mixture; complete history does not identify
the value of a changed generator or version law.

## Deterministic verification and limitations

The main fixture has two distinct initial states followed by RETRY and the same
second-stage wrong state. Every second-stage action is represented equally.
STOP has outcome zero in both prefixes; all continuing actions have outcome zero
in one prefix and one in the other. Under uniform five-arm continuation, the
fitted complete-history second-stage values are 0 and .8, and first-stage RETRY
Q propagates those values. Compressed state-only fitting instead pools the
second-stage value to .4. This tests backward fitting on supplied records without
an oracle Q table or sampled simulator data.

Additional fixtures check held-out outcome isolation, prior-action distinctions,
root-fold integrity, training-only fallback, absorbing STOP and matching Q use
between plug-in and DR. Exact commands, pass counts, runtime and source hashes
are recorded in [the validation artifact](../results/e0_history_source_validation_20260922.json).
Independent mathematical and source reviewers checked the scope and implementation.

The existing fallback pools training outcomes by action and stage, then by stage
when an action is absent; an empty training stage uses zero. This is an unsmoothed
fallback, not a practical regularization strategy. Rare nonempty cells and unseen
prefixes can still be unstable. Expanding the key may exacerbate sparsity. No
lower RMSE, nuisance convergence, finite-sample coverage or learned-policy benefit
is inferred from these fixtures. Historical weak-overlap failures are retained.

## Next discriminating work

Issue #2 remains open. A later committed numerical protocol must compare this
available fitted prefix learner with the compressed learner on the same roots,
folds, policy and truth, add an explicit training-only regularization rule, and
specify fresh seeds, sample sizes, resource limits, failures and Monte Carlo
precision before execution. Any template-mixture condition must use its actual
replicate-specific fixed mixture and matching policy truth. The eight-cell proposal remains unexecuted. No
numerical grid or new receiver collection is authorized by this source delivery.

The current priority stays E12 and then independent policy validation. This
source work is separate from the experiment worker's receiver ownership and
accepted 07:10–08:20 UTC window. Overall milestone completion stays **55%, change
0 percentage points** under the fixed rubric. Prompt efficacy is unestablished;
the full project is not submission-ready.
