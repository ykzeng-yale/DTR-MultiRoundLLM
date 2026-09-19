# Causal critic and generative policy: training specification

This is an implementation contract for the next experimental stage. The reference Python package validates finite-state estimation. It does **not** contain a trained neural prompt critic or fine-tuned prompt generator.

## Critic inputs and outputs

Let $Z_t=(H_t,C_t)$ be the pre-selection history and realized slate. A critic $q_{\phi,t}(Z_t,j;\pi)$ predicts final quality or net utility after choosing index $j$ and following a **named frozen continuation** $\pi$. The history encoder receives exact public conversation tokens and permitted public metadata. The action encoder receives the exact candidate string, STOP indicator, and permitted slate features. Use separate quality and cost heads and combine them using a declared utility conversion.

The encoder can share parameters with the generator only within the training partition. Freeze it during evaluation. A low-dimensional representation can improve statistical prediction, but full-history ignorability does not transfer automatically to the representation. Include a history-ablation/aliasing experiment. If the critic omits other candidates, state the slate-exclusion assumption and preserve enough context to define the action.

At a brand-new request, either (i) first run the fixed receiver and predict feedback values from the resulting history, which is the main design, or (ii) define an additional randomized initial-prompt rewrite decision. The original task is baseline, not a manipulable treatment unless the study explicitly defines a rewrite that preserves its target and scoring rules.

## Backward learning for a fixed continuation

For notation here, treat the **realized slate as part of the observed state**, and evaluate a selector under the same natural candidate mechanism. All rewards and costs are encoded in terminal total utility $U$, so stage rewards are $R_t=0$ in this recursion. Let $L_{T+1}=U$ and define $\widehat v_t(z)=\sum_j\pi_t(j\mid z)\widehat q_t(z,j)$. For each held-out fold, evaluate nuisance fits trained on other root tasks and recursively form

$$
L_t=\widehat v_t(Z_t)+\frac{\pi_t(J_t\mid Z_t)}{\widehat b_t(J_t\mid Z_t)}\{L_{t+1}-\widehat q_t(Z_t,J_t)\}.
$$

The action-specific pseudo-outcome is

$$
D_{t,j}=\widehat q_t(Z_t,j)+\frac{\mathbf1(J_t=j)}{\widehat b_t(j\mid Z_t)}\{L_{t+1}-\widehat q_t(Z_t,J_t)\}.
$$

Regress $D_{t,j}$ on $(Z_t,j)$ to obtain a conditional-mean critic under the assumptions in the theory. When candidates are texts generated for each history, $j$ alone has no cross-history semantic meaning; use exact candidate text and declared slate context as model inputs. The labels do not create information about an unseen candidate or an unseen semantic feature. Known experimental probabilities should be used exactly; estimating them unnecessarily can add error.

The theory distinguishes this natural-slate recursion from integrating over a fixed known proposal kernel. Use its corresponding score when claiming efficiency under the latter model. Candidate Monte Carlo integration error is not silently zero. All later continuation labels must be conditionally valid for $D_{t,j}$ to target the desired Q. Current-stage double robustness does not repair an arbitrary wrong continuation. Cross-fitting reduces dependence bias; it does not confer pointwise confidence coverage without conditional-regression assumptions.

### Concrete fitting sequence

1. Partition complete root tasks into folds. Pin $\pi$, candidate-generator version, receiver, horizon, and utility.
2. Fit backward sequential Q on training folds using observed terminal outcomes and target-weighted next-state value. Use identical architectures to define the regression baseline.
3. Compute out-of-fold continuation and action labels with exact design probabilities. Retain extreme labels and report diagnostics; optional clipping is a separate biased sensitivity estimator.
4. Train a second-stage critic on labels. Evaluate its generalization on separate development tasks, and refit only within the training/development boundary after hyperparameters are locked.
5. Keep final testing independent of all fitting and model selection. A shared root prefix never crosses a fold or split.

For high-dimensional language, parameter sharing across stages and candidates is a modeling choice. It needs a fitted-model experiment, approximation-error analysis, and an out-of-task calibration check. The proofs do not assert neural convergence rates without a function class and regularity conditions.

## Candidate selection and stopping

Given a slate, rank candidates by predicted net utility. Compare with STOP, whose value is the expected score of the current artifact minus costs already incurred; the hidden true score is unavailable at serving time. Include uncertainty/supportedness calibration before switching from a reference selector. A bootstrap spread from an arbitrary neural fit is not automatically a valid causal confidence bound.

A conservative deployment rule may switch only if a prespecified lower bound on average improvement in a calibrated subgroup is positive, or use a fixed threshold chosen on development tasks. Report it as a heuristic if no uniform error guarantee has been established. Theory bounds conditioned on a valid simultaneous error event are conditional guarantees, not a claim that an ensemble empirically supplies such an event.

## Generator learning

The simplest generator update fits high-value feedback from training histories. For candidate advantages $\widehat A_{tk}=\widehat q_t(Z_t,k)-\sum_j\pi_{\rm ref}(j\mid Z_t)\widehat q_t(Z_t,j)$, an optional advantage-weighted objective is

$$
\max_\theta\sum_{i,t,k}w_{itk}\log G_\theta(a_{itk}\mid H_{it}),\qquad
w_{itk}\propto\min\{w_{\max},\exp(\widehat A_{itk}/\beta)\}.
$$

Normalize weights within history, tune $\beta$ and $w_{\max}$ on development data, and preserve baseline candidates and exploration. This is a proposal-training heuristic, not an unbiased off-policy policy-gradient theorem. If proposal samples are used in a score-function update, record the proposal law and importance correction, and keep the critic fixed during each actor update. Any reference-policy KL term limits drift but cannot prove identification or prevent reward hacking by itself.

Train on continuation-correct values. Optimizing a one-step average of $Q^\pi$ over historical states may be a policy-improvement surrogate; it is not the gradient of the complete new regime's value without the proper occupancy distribution and policy-gradient conditions. Freeze each actor/selector version and recollect before making a policy-value claim. Changing both actor and continuation means retraining or re-evaluating the critic's target.

## Serving behavior

The virtual user receives an initial task, calls the frozen receiver, creates a candidate slate, estimates supported values, selects a prompt or STOP, and repeats until STOP or the horizon. It logs every transition. Values are always associated with receiver/generator/continuation versions. A receiver update invalidates an unqualified transfer claim. The system falls back to its declared reference policy when support or calibration checks fail.

This architecture supports prompt advice to a human and autonomous feedback as two deployment modes. Their outcomes need not agree: a human may edit the suggestion, supply private information, or ignore STOP. Evaluate human adherence and human-in-the-loop value separately if that becomes the intended application.
