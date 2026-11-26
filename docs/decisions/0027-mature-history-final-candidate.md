# ADR 0027: One mature-history candidate and additive experimental API

Status: accepted for the final milestone, before EXP-010 generation/training.

## Context and decision

EXP-009 improved average MAE but failed uncertainty, stage and tail checks. The
v2 proposal identifies persistent context and unobserved disruption as different
problems. Choose one bounded history hypothesis, retaining the original process
law and unpredictable innovations. No signal is copied from current outcomes.

Use seven already mature same-crew/line observations, with uncensored attainment
mean/std, observation counts and age. Censoring is determined only from completed
past shifts. Current/future observations and other entities are excluded; missing
history stays explicit. These are legitimate pre-shift historical measurements,
not planned values silently replaced by realized current-shift values.

Fit exactly one fixed residual HistGradientBoosting model over frozen RF Physics.
The fixed model head bounds its sum by zero and offered-work attainment. This
inductive constraint is declared before results and applies equally at evaluation
and serving. Report it separately from the unchanged legacy estimators; additional
history information means gains cannot be attributed to algorithm choice alone.

Use new development and held-out world seeds in the committed EXP-010 config.
Freeze executable candidate bytes before held-out generation/scoring. Forward-only
held-out history may use earlier reports once mature, with no parameter updates;
this is an online historical-context evaluation, not an unseen-context cold start.
The first unannounced shock remains unpredictable. Compare all four unchanged
models and the same candidate with explicitly missing history, without another fit.

Integrate only if every predeclared demonstration guard passes. Add API v3 and a
fifth optional model; preserve v1/v2 schemas, frozen source/artifact identities,
reserved datasets, resource budgets and unconditional NO_ML_PROMOTION. Never
mutate planning efficiency/capacity. Actual public deployment is not authorized;
prepare a reviewed production build, explicit proxy configuration and instructions.
