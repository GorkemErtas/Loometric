# ADR 0004: A fixed six-candidate Random Forest comparison

Status: accepted for A04 / EXP-003. Comparison declared before model execution.

## Context and options

EXP-002's additive linear models do not improve on the department-mean reference.
The authorized next question is whether tree interactions/nonlinear calendar effects
help on the same future dates. Options are one forest, a small declared comparison,
or a large hyperparameter search. With only 711 training rows and repeated use of
232 validation rows, choose a small comparison. No improvement is assumed.

## Decision

Reuse the source loader, closed provisional feature boundary, frozen split file and
fingerprint verification, mean baselines, linear pipeline, and regression metrics.
Extract EXP-002's unchanged encoder constructor and vocabulary inspection into
`preprocessing.py`; move its unchanged residual/MAE-change helpers to `evaluation.py`.
Keep those names importable through `experiments.linear` for compatibility. No
generic estimator interface, factory framework, new dependency, or schema is needed.

Feature sets are exactly A = department + categorical team and B = A + categorical
date-derived weekday + numeric day of month. Use the same dense full one-hot encoding
with unknown handling as EXP-002, fitted independently on training rows within each
Pipeline. All feature eligibility remains provisional without source timestamps.
No additional fields, historical target aggregates, imputation, scaling, or clipping.

Evaluate these three fixed profiles crossed with A and B, in feature-set order and
then profile order (six candidates total):

| Profile | n_estimators | max_depth | min_samples_leaf | Rationale |
| --- | --- | --- | --- | --- |
| RF-01 | 100 | 3 | 20 | Strong smoothing and shallow interactions on a small dataset |
| RF-02 | 200 | 6 | 10 | Moderate capacity with a larger averaging ensemble |
| RF-03 | 300 | None | 2 | Flexible diagnostic of interaction fit and overfitting risk |

All use RandomForestRegressor with random_state=42, n_jobs=1,
criterion="squared_error", max_features=1.0, bootstrap=True, min_samples_split=2,
max_samples=None, oob_score=False, and warm_start=False. Record all installed
estimator defaults in JSON. Sequential fits/prediction and a fixed seed provide
repeatability in the pinned environment. Bootstrap sampling is internal training
resampling, not a random train/validation/test split. No OOB or final-test score is
used, and no configurations are revised after observing validation results.

Profiles vary bundled capacity settings; they do not estimate an isolated causal
effect of depth, leaf size, or tree count. The flexible profile is a diagnostic,
not a default model recommendation. No exhaustive grid, random search, or CV tuning.

Compute in-sample training MAE only to diagnose fit. Select the forest with lowest
validation MAE; ties within absolute 1e-12 resolve in declared order. Prefer that
forest to the department baseline only if its validation MAE is lower by more than
1e-12; otherwise explicitly retain the baseline. Baseline and two matching linear
references are fitted on the same training rows and scored on the same validation
rows. They do not enter the six-candidate search. The best EXP-002 linear model is
already equivalent to the department baseline.

Report validation MAE, RMSE, R², prediction-minus-actual bias, department MAE,
residuals, prediction ranges, signed absolute/relative MAE changes, fit/predict times,
and the validation-minus-training MAE gap. Do not use training error, slices,
importance, runtime, or the final test to change selection. A train/validation gap
can reflect temporal change or unavailable predictors as well as overfitting; it
does not prove a cause. No significance claim or confidence interval is inferred.

Record impurity-based importance per encoded column and sums for each original
feature using fitted preprocessing metadata. This uses training data only and is
descriptive: category cardinality, available split points, correlated/redundant
one-hot columns, and profile capacity affect it. It is not causal or validated
out-of-sample importance and will not trigger feature selection.

After source/split verification, only train and validation frames enter feature
construction, fitting, prediction, metrics, selection, or diagnostics. Preserve the
existing whole-source schema/domain checks; these are not test performance scoring.
The CLI exposes no test-evaluation or model-search controls. Store numerical JSON
locally under ignored `data/processed/`; preserve reviewed experiment Markdown.
Reuse `requirements/exp-002.txt` unchanged because the installed dependency closure
already supplies RandomForestRegressor. Do not duplicate an identical lock snapshot.

## Consequences and limits

Earlier CLI contracts and result structures remain intact. Reproduce EXP-001 and
EXP-002 numerical outputs after the extraction. New tests use synthetic records,
check the exact declared plan, train-only fitting, deterministic predictions,
unknown categories, metric/importance arithmetic, baseline retention and final-test
isolation. No private CSV is required by tests.

The comparison can reveal predictive gains on one short validation period only.
Pre-shift availability, row grain, target meaning, repeated teams, A01's full-source
EDA, and repeated validation use remain limitations. A single seed and period do not
establish robustness. Any improvement requires later evidence before operational
use; final test evaluation requires a separate task after choices are frozen.

References: [RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)
and [impurity-importance limitations](https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_importances.html).
