# STOP comparison supervision and closed-run audit

Decision: **LEAD-E0-STOP-01**. This source package does not release numerical
execution. The comparison plan and exact seed table remain unchanged. No sampled
STOP-comparison result is delivered by this document.

## Scientific decision

Independent review accepts the bounded diagnostic in principle. Its target is the
fixed uniform-five-arm synthetic policy value, 0.6459770061744536. The new question
is whether direct versus recursive use of the known STOP payoff changes nuisance
behavior under the prespecified weak logger. This is a post-result mechanism
study, not completion or confirmation of the closed three-logger study and not
validation of an LLM prompt policy.

The primary paired squared-error difference is history/lambda5 recursive DR minus
history/lambda5 original DR. Its .005 Monte Carlo standard-error threshold is a
precision diagnostic, not significance, practical benefit or futility. Fixed-size
interpretation requires all 96 prespecified datasets and the relevant independence
assumption. A resource-selected prefix retains all 2,304 planned denominators and
is descriptive. No continuation, replacement seeds or outcome-based stopping is
permitted. Exact STOP prediction does not guarantee lower variance or correct
coverage; the known synthetic payoff is not established as available to an LLM.

## Recording repair

The original live recorder replayed all earlier records on every append. With
27 events per successful dataset, that needlessly repeated checks of earlier root
means and retained support payloads in memory. The writer now validates only the
new transition against a detached state and promotes it after durable append.
An invalid second terminal row cannot partially promote the first row. Full replay
and root-mean/interval checks remain in the independent reader. The writer retains
compact event receipts and detached estimator records for the final summary.

Exclusive artifact creation also reserves both temporary and final file sizes
while hard links coexist. The supervisor counts directory entries, including
orphan and temporary files. This makes the cooperative writer's byte accounting
consistent with the monitor during that transient interval.

## Feasibility and remaining release gate

The prior 486-second fit projection excluded this recording overhead and is not a
completion guarantee. Source-layout arithmetic gives 76,308,480 bytes for minimal
arrays and four fold arrays across 96 datasets before NPZ headers. Support JSON,
manifests, summaries, temporary files and final receipts share the remaining
256 MiB. Removing repeated replay addresses a concrete bottleneck; it does not
prove that all 96 jobs finish in 600 seconds or that the total output fits.

The proposed limits remain one CPU worker, one numerical-library thread, 600
seconds, 256 MiB and $0, with zero model calls, tokens and benchmark executions.
A committed source/environment/truth freeze, independently accepted connected
supervisor/auditor, fresh host and lease inspection, and a separate lead release
are required before the first draw. This allowance is separate from MRL-23/E14;
its expired worker window is not renewed. Previous numerical artifacts and
empirical negatives remain immutable.

## Source acceptance and measured validation

Independent scientific and operational reviews accept the final source. All **212
integrated checks pass** (9.40 seconds test time; 9.731 seconds command wall;
8.541 seconds child CPU). Earlier attempts are retained in the
[validation record](../results/e0_stop_anchor_supervision_validation_20260923.json):
one fixture-message mismatch was corrected, and a real signal-error cleanup
failure was repaired before the final passing run. Five test invocations used
27.935 seconds command wall and 23.961 seconds child CPU in total.
Handcrafted-data tests perform fits; mock tests and tiny controlled children check
scheduling and recording. No sampled datasets, model calls/tokens, benchmark
executions or paid cost were incurred. Twenty old source/plan/seed/run hash checks
pass unchanged. This source acceptance adds no numerical performance evidence.

The [runner](../scripts/run_stop_anchor_comparison.py) requires the committed raw
freeze, exact source ancestry and versions, fixed run path, fresh resource receipt,
one owned child and shared output/time budget. Signaling errors are retained;
only an observed exit verifies child closure. The
[final audit](../scripts/reconcile_stop_anchor_run.py) independently binds the
archived release to its committed path and full revision, reconstructs the exact
seed identities, checks strict JSON and torn-tail hashes, verifies actual arrays
and saved-root arithmetic, reconciles reported fit counters and all planned slots,
and checks a stable full-file snapshot. It does not refit Q from arrays or prove
RNG independence. Its derived output must be outside the immutable run directory.

The supervisor's saved duration ends before final receipt serialization/fsync;
`full_process_wall_verified=false` preserves that limitation. A later run must
also have external command timing before full 600-second compliance is claimed.
The byte monitor detects an uncooperative writer's excess; cooperative source
writes enforce the allocated budget. It is not a filesystem containment proof.
