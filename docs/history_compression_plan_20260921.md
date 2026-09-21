# Exact diagnostic of the compressed E0 regression

21 September 2026. Freeze this plan, configuration and implementation before
running the three-cell numerical report. This is deterministic finite-law
enumeration, not a model experiment, new Monte Carlo sample or fitted learner.

The matched estimator comparison uses the same fitted state/time Q for both
methods. Its remaining limitation is whether omitted observed history changes
the regression target even at infinite training size. Compute that population
regression limit in three **existing** E0 cells: base (kappa=1,floor=.10), uniform
logger (0,.20), weak overlap (2.5,.02); all use horizon 3, cmult=1, gz=0 and no
mislabeling/template offsets. The target remains the fixed uniform five-action
policy, including absorbing STOP. No parameter is chosen after the output.

For each cell, enumerate the logger's active mass over latent ease, latent error
type and current state at each decision. At the terminal boundary set V to the
correct-state indicator. Work backward: regress the next compressed V on current
state/action under that logger mass, handling STOP as current correctness; average
Q over the uniform target action law. Average the initial V under the original
initial distribution. This is the population counterpart of `fit_q` without
empty-cell fallbacks, not the correct full-history Q assumed by a robustness claim.

Separately traverse every observed state/action history using posterior latent
weights updated by the exact transition law. Current action assignment has gz=0,
so its factors are constant in the latent variables given the observed history
and cancel from this posterior. Never expose the realized latent type to a
deployable rule. This is an **oracle full-history value reference** based on a
known law, not a trained comparator. Compare its initial mean with the existing
latent-state dynamic-program truth for the same uniform policy.

Report both values, the compressed limit minus truth, and maximum discrepancies.
Check T=1, uniform logging, and a latent-invariant transition kernel as zero-bias
controls; report any failed control. Validate source/config hashes and do not
overwrite outputs. Independent internal mathematical review checks the population
recursion and observation boundary. No finite-sample advantage, confidence coverage,
prompt-policy efficacy or useful real-world effect follows from this calculation.

Resource cap: one CPU process, 60 seconds for the three-cell report, at most 10 MiB
output, no new packages, receiver calls, candidate/reference code, GPU or paid spend.
The exact reference imports the existing trusted E0 law; no sampled trajectories
are generated. Record actual runtime and software/source versions. Unit checks
are separate from the frozen report. This bounded lead task does not replace
worker-owned MRL-01–04 or release new collection. A learned adequate-history
comparator and the broader literature-guided simulation remain outstanding.

The population limit averages independently sampled task latents, not infinitely
many repeats of a fixed 230-task roster. Synthetic state history includes the
distinction between visible-pass/hidden-fail and correct states; it is not
automatically an available deployment-public feature set. At gz=0 there is no
latent treatment-selection confounding given the current observed state. Any
off-policy compression bias here comes from omitted history and changed latent
mixtures across logger/target occupancies. Uniform-logger aggregate agreement does
not prove conditional Q sufficiency, and the .02 floor is weak, not absent, overlap.
