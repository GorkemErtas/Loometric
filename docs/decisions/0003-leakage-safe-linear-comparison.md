# ADR 0003: Provisional pre-shift features and a bounded linear comparison

Status: accepted for A03 / EXP-002.

## Context and options

EXP-001 establishes frozen chronological partitions and two training-mean references.
The next authorized model is ordinary Linear Regression. Source measurement times
are absent, so none of the source names alone prove pre-shift availability. Admitting
conditional planning fields, treating team numbers as magnitudes, fitting encoders
on the whole CSV, or searching many feature combinations would weaken this evidence.

Options include a single four-feature model, a small declared ablation, and a larger
validation-driven search. We choose the bounded ablation to distinguish categorical
and calendar effects without tuning many alternatives.

## Decision

Reuse the existing source loader, fingerprint check, frozen split consumer, reference
estimators, and metric arithmetic without modifying their behavior or split JSON.
After partition verification, consume only training and validation frames. There is
no final-test inference/evaluation option. Source validation still covers the input
CSV, as in EXP-001; this is not performance evaluation or fitting on held-out labels.

A stateless feature builder accepts exactly normalized scheduled date, department,
and team, preserving rows and indices. Department and team assignments are assumed
fixed before shift start. Team IDs become canonical whole-number strings. Derive
weekday (Monday=0) as a category and day of month (1..31) as numeric from date; never
consume source day or quarter. Every input is provisional pending timing evidence.
Reject missing/invalid eligible inputs rather than imputing, dropping, or rounding.
Keep conditional planning fields, realized shift values, and labels outside the
feature boundary. A closed model-feature allowlist rejects their selection.

Fix these four comparisons before inspecting EXP-002 performance, in this order:

1. Department only: control expected to reproduce the department mean.
2. Team only: categorical sensitivity reference.
3. Department + team: additive identity effects, with no interaction terms.
4. Department + team + weekday + day of month: joint calendar addition.

Compare all models and both EXP-001 baselines on the identical validation records.
Primary metric is validation MAE. Rank linear candidates by MAE, with absolute
differences within 1e-12 resolved in declared order. Retain the department baseline
as the reference if no trained model improves it. Report signed absolute and relative
MAE changes, RMSE, R², bias (prediction minus actual), department MAE, residuals,
unclipped prediction ranges, unknown categories, and measured fit/predict times.
There is no adaptive feature search, hyperparameter optimization, or final model
promotion. Adding calendar fields is one joint comparison, not separate tuning of
each field's representation.

Use a scikit-learn Pipeline containing ColumnTransformer and LinearRegression.
OneHotEncoder learns categories from training only, with handle_unknown="ignore",
drop=None, and dense output. Unseen categories produce zeros for that feature;
this permits prediction but is not a validated unseen-team policy. Full one-hot
coding with an intercept is rank deficient; the dense least-squares solution handles
redundant columns. Predictions are reproducible in the recorded environment,
but individual coefficients are not uniquely identifiable causal effects. Dense
output is inexpensive for this small vocabulary and avoids iterative solver settings.
Day of month passes through numerically. No scaling, clipping, regularization,
target transforms, imputation, or random operations are added.

Add scikit-learn through the optional `ml` extra, preserving the existing data-only
installation. Record exact installed packages in `requirements/exp-002.txt`, including
the EXP-001 pins. Keep full numerical results and runtime metadata in an ignored JSON
artifact, and a reviewed Markdown experiment record in Git. The runner does not
overwrite the versioned experiment narrative when re-executed.

## Consequences and limitations

The model boundary remains local Python; no service, storage, registry, or generic
estimator framework is needed. Feature construction, estimator creation, metrics,
and orchestration can be tested independently with synthetic data. Runtime measures
are single local wall-clock measurements and vary. The environment snapshot is not
a cross-platform wheel/hash lock; seeds are inapplicable because fitting is not random.

Team IDs are modeled as shared additive effects across departments; interactions
and historical aggregates are outside this experiment. Day of month imposes a linear,
resetting calendar effect in a short January/February training window. No seasonal,
causal, unseen-factory, or operational validity follows from this comparison. Repeated
validation use can overfit development decisions; preserve the final holdout for a
separately authorized evaluation after model/preprocessing choices are frozen.

References: [OneHotEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html),
[LinearRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html),
and [leakage prevention](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).
