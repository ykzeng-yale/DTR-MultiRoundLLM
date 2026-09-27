# BigCodeBench source review: rows32–39

Codex scientific lead,27 September2026. Full source review of both prompts, reference and native tests for eight consecutive rows. [Ledger](../results/bigcodebench_semantic_review_0032_0039_20260927.json) records32 verified field hashes. All remain unresolved/not admitted. The row judgments are lead source judgments; only the mathematical interpretation of39 received separate inference review this turn. No benchmark/reference/test-string/model execution occurred.

## Measurement and specification findings

Task32 checks several specific HTML retrieval cases under mocked requests, including first occurrence and malformed/empty tags. Its reference's `.string` semantics are narrower than an unspecified general text-content extraction contract; nested text needs adjudication rather than silently preferring the reference. Task33 has fixed numerical expected products across signs, zeros and a singleton. Its equality checks do not themselves require an ndarray return type, and do not resolve empty inputs or numerical domains beyond the examples.

Task34's absence-of-full-URL assertion does not exclude residual fragments or verify intended word frequencies and plotted content. Task35 has an explicit return mismatch: the return section describes Axes alone, whereas the reference, Complete example and tests use a DataFrame/Axes tuple. Some tests impose allowed-value membership and line counts without checking all transformed values; the all-allowed comparison reads mutable post-call input. Task36 shares its filtering/density structure but adds Box-Cox. Nonconstant transformed values are not directly checked, and its reference relies on `pd` supplied by test imports rather than the Complete prefix. Moving native code into separate namespaces would therefore be a measurement/environment change requiring explicit review.

Task37 checks full sorted importance/bar-width lists, not truncated zip comparisons. Preserve that positive finite relation. Both the model and plot are candidate-produced, however, so their mutual agreement does not establish that the model was fitted to the intended input, and feature-label mapping is unchecked. Task38 combines concrete example means with two numerical StandardScaler comparisons, but those comparisons read the input after the call. Its `ax.patches is not None` check does not establish that histogram bars exist.

## Task39: structural self-centering

The reference computes row means, then passes that vector to one one-sample t-test against the mean of all entries in the same matrix. For finite real rectangular data with m>=2 rows, k>=1 columns and positive sample variance of row means,

`mean_i(mean_j(x_ij)) = sum_ij(x_ij)/(m*k)`.

In exact arithmetic, the conventional statistic has zero numerator and two-sided p=1. This is structural self-centering, not evidence supporting an externally specified null and not a set of row-specific significance tests. Single-row/zero-variance cases, empty dimensions, nonfinite values, floating-point effects and library conventions are separate. No universal observed return value or runtime behavior is claimed.

The existing internal inference reviewer independently confirms this algebra and interpretation. The native tests check a list result and three line colors/labels, not the indices, coordinates or validity of that statistical procedure. This source finding requires specification adjudication; it is not a result about this project's causal estimators, policy efficacy or the benchmark's overall quality. No alternative statistical task is substituted here.

## Family decisions and next work

Conservatively retain35/36 together for their shared allowed-value filtering and density pipeline. Retain29/38 together for their standardization pipeline before different encoding/summary/plotting outputs. These are provisional scientific task-structure judgments, not exact whole-program identity, automatic library-based clustering or a final family partition. Possible relatives retrieved for34/37/38/39 are listed as **unreviewed**, not silently added to groups. Plotting boilerplate remains insufficient to merge tasks.

The source-order review covers0–39 plus separately selected887:41 reviewed sources, zero admitted families. Larger-scale grouping, prior-exposure crosswalk, specification and endpoint decisions remain outstanding. No unchanged full suite was rerun for these prose/data changes. Docker restoration question remains pending; no reply, service change or permission is inferred, and source/design work remains possible.

Full-project submission readiness **60%, change0 percentage points**. Population/measurement, full prospective freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete. Goal active, Codex-only work.
