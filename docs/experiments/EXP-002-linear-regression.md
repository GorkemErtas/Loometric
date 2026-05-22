# EXP-002: Linear Regression and leakage-safe feature engineering

Status: executed on training and validation only. No trained configuration improves
the EXP-001 department-mean baseline. Final test performance remains uncalculated.

## Objective and prediction contract

Test whether ordinary least-squares Linear Regression with a small, declared set of
provisional pre-shift features improves validation MAE over both EXP-001 references.
The target is `actual_productivity` for a scheduled team in a department, predicted
immediately before shift start. `(date, department, team)` is a tentative row key;
shift IDs, capture timestamps, precise productivity units, and outcome-finalization
times are absent. All training outcomes must be finalized before validation starts.

This is real-source dataset evaluation, not synthetic factory simulation or evidence
of operational forecasting validity. Synthetic records are used only in tests.

## Dataset identity and preserved partitions

Source: `data/raw/garments_worker_productivity.csv`.

Dataset SHA-256:
`763ffcdd39b7f7f360243c2af8f89ed733e8b5f9e511efeb0c886b83e1b76866`.

Split file: `configs/chronological_split.json`, SHA-256:
`c38de7e418b1d75a0d4e51ceec63344675afd8acc3de34d85e88315bd686a727`.

The existing split file is reused byte for byte. Its existing consumer verifies the
source fingerprint, date-only policy, boundaries, counts, strict temporal ordering,
and complete whole-date assignment. No configuration is regenerated or saved.

| Partition | Inclusive dates | Distinct dates | Rows | Use |
| --- | --- | --- | --- | --- |
| Training | 2015-01-01 to 2015-02-10 | 35 | 711 | Fit encoders, regressors, and baseline means |
| Validation | 2015-02-11 to 2015-02-25 | 12 | 232 | Fixed comparisons and diagnostics |
| Final test | 2015-02-26 to 2015-03-11 | 12 | 254 | Reserved; no fitting, feature construction, prediction, selection, or metrics |

The original loader and normalization are unchanged: whitespace and `sweing` are
normalized on a copy; no rows are dropped or targets clipped. Existing source-wide
validation reports 506 missing WIP values and 37 targets above 1. These inherited
schema/domain checks are separate from performance evaluation. A01 already profiled
all source targets, including the later holdout; an unseen exploratory holdout is
not claimed. Neither test targets nor test features enter EXP-002 models/diagnostics.

## Exact feature sets and availability assumptions

Every feature is **provisionally eligible** because measurement timestamps are
unavailable. The source's historical assignment must match the scheduled assignment
at cutoff; field names alone cannot establish this.

| Feature | Representation | Availability assumption |
| --- | --- | --- |
| department | One-hot category | Scheduled department fixed before shift start; reuse source normalization. |
| team | One-hot category | Scheduled team ID fixed before shift start. Whole numeric IDs become canonical strings (`1.0` becomes `"1"`), never continuous magnitudes. |
| day_of_week | Date-derived one-hot category, Monday=0 to Sunday=6 | Scheduled local shift date known at cutoff; source `day` is not consumed. |
| day_of_month | Date-derived numeric day, 1..31 | Same known scheduled date; no outcome or future aggregate required. |

The stateless builder accepts exactly date, department, and team. It preserves rows
and indices, rejects missing/invalid eligible values, and never consumes the label.
The pipeline feature selector has a closed allowlist. Source `day`, `quarter`, raw
date, realized `over_time`, `incentive`, `idle_time`, `idle_men`, and all target values
are excluded as estimator inputs. `targeted_productivity`, `smv`, `wip`,
`no_of_workers`, and `no_of_style_change` remain excluded: the contract requires
timing/business evidence that has not been supplied. Planned and realized values
are not relabeled or substituted for each other.

Before inspecting EXP-002 performance, the following four comparisons were fixed
in `features.FEATURE_SETS`; no other feature subsets or parameter settings were tried:

| Configuration | Exact estimator inputs | Encoded columns |
| --- | --- | --- |
| department_only | department | 2 |
| team_only | team | 12 |
| department_team | department, team | 14 |
| department_team_calendar | department, team, day_of_week, day_of_month | 21 |

Department only is a baseline-equivalence control. Comparing department/team with
department only measures the addition of team; comparing it with team only measures
the addition of department. Calendar features are one joint addition. This protocol
does not isolate weekday from day of month, and the results do not justify additional
validation-driven attempts in this experiment.

Primary comparison: lowest validation MAE among these four; ties within 1e-12 resolve
in declared order. Baselines use the identical training labels and 232 validation
records. Model selection uses training/validation only; the department baseline
remains the reference when no trained candidate improves it.

## Model and preprocessing configuration

`Pipeline(preprocessing=ColumnTransformer(...), regression=LinearRegression(...))`.
Categorical columns use `OneHotEncoder(handle_unknown="ignore", drop=None,
sparse_output=False)`. Numeric day of month passes through. `remainder="drop"`.
The fitted pipeline encapsulates the learned encoder and estimator; stateless
calendar derivation is separate. Encoders and regressors fit **only the 711 training
records**, independently for each declared set.

Recorded LinearRegression parameters: `fit_intercept=True`, `copy_X=True`,
`positive=False`, `n_jobs=None`, `tol=1e-6`. This is unregularized ordinary least
squares with dense encoded input. Full one-hot coding plus an intercept introduces
redundancy handled by least squares; individual coefficients are not uniquely
identifiable causal effects. Team effects are shared additively across departments;
there are no interactions, scaling, imputation, clipping, target transforms,
historical aggregates, or hyperparameter optimization. There are no random
operations; seed is inapplicable rather than a missing reproducibility setting.

Unknown categories produce zeros for their feature. The training vocabulary contains
2 departments, team IDs 1 through 12, and weekdays 0, 1, 2, 3, 5, 6. No Friday is
observed in training. There are **zero unknown categorical values in validation**;
unseen-category behavior is tested synthetically, not validated on real unseen teams.

## Measured validation results

All rows have equal weight. MAE/RMSE/bias are in productivity-ratio units. R² is
dimensionless and uses the validation mean only in its denominator. Bias and residuals
are prediction minus actual; positive values indicate overprediction.

| Configuration | MAE | RMSE | R² | Prediction bias |
| --- | --- | --- | --- | --- |
| EXP-001 global_mean | 0.144606972 | 0.197475686 | -0.105176844 | +0.060919708 |
| EXP-001 department_mean | 0.143226295 | 0.196492435 | -0.094198670 | +0.060338141 |
| department_only | 0.143226295 | 0.196492435 | -0.094198670 | +0.060338141 |
| team_only | 0.149747347 | 0.204339468 | -0.183338602 | +0.059731772 |
| department_team | 0.150379924 | 0.203566618 | -0.174404317 | +0.059444997 |
| department_team_calendar | 0.150551578 | 0.202288571 | -0.159704139 | +0.052828789 |

Both baseline metrics reproduce EXP-001. Department-only OLS reproduces the training
department means and ties their validation MAE. **There is no improvement over the
department baseline.** Its 0.9548% advantage over the global mean was already present
in EXP-001. Every team-containing model regresses in MAE and RMSE against both
references, and every R² is negative. The calendar model has lower bias/RMSE than the
department/team model but worse MAE; this does not change the declared criterion.

### Absolute and relative MAE changes

Change = candidate MAE minus named reference MAE. Relative change = 100 times change
divided by reference MAE. Negative means improvement; positive means regression.

| Candidate | Change vs global | Relative vs global | Change vs department | Relative vs department |
| --- | --- | --- | --- | --- |
| department_only | -0.001380677 | -0.9548% | 0.000000000 | 0.0000% |
| team_only | +0.005140376 | +3.5547% | +0.006521053 | +4.5530% |
| department_team | +0.005772953 | +3.9922% | +0.007153630 | +4.9946% |
| department_team_calendar | +0.005944607 | +4.1109% | +0.007325284 | +5.1145% |

| Predeclared addition | Reference | Absolute MAE change | Relative change |
| --- | --- | --- | --- |
| Team added to department | department_only | +0.007153630 | +4.9946% |
| Department added to team | team_only | +0.000632577 | +0.4224% |
| Calendar added to department/team | department_team | +0.000171654 | +0.1141% |

Neither identity addition helps this validation MAE. Joint calendar features also
fail to improve it. These are predictive ablations over a short window, not causal
effects or proof that the features are universally unhelpful.

### Department-level MAE

| Configuration | Finishing (train 297 / validation 94) | Sewing (train 414 / validation 138) |
| --- | --- | --- |
| global_mean | 0.166818469 | 0.129477401 |
| department_mean | 0.169320624 | 0.125451896 |
| department_only | 0.169320624 | 0.125451896 |
| team_only | 0.169917902 | 0.136007984 |
| department_team | 0.171561932 | 0.135951600 |
| department_team_calendar | 0.170533311 | 0.136940833 |

Finishing is harder for every configuration. The department mean already worsens
finishing relative to the global mean, despite better aggregate MAE. Every
team-containing candidate worsens both departments relative to the department mean.
Calendar addition reduces finishing MAE from 0.171561932 to 0.170533311, while sewing
worsens from 0.135951600 to 0.136940833; aggregate MAE rises.

## Residual and range diagnostics

Quantiles use linear interpolation; standard deviations use population `ddof=0`.

| Configuration | Min residual | P05 | Median | P95 | Max residual | Residual std |
| --- | --- | --- | --- | --- | --- | --- |
| department_only | -0.361972619 | -0.241065395 | +0.037892782 | +0.432776986 | +0.546812938 | 0.186998892 |
| team_only | -0.314130119 | -0.208120329 | +0.010220217 | +0.476603652 | +0.581131893 | 0.195414261 |
| department_team | -0.291305948 | -0.192862120 | +0.015311952 | +0.464026361 | +0.606780695 | 0.194693761 |
| department_team_calendar | -0.309435676 | -0.202608199 | +0.011112655 | +0.453139689 | +0.600871867 | 0.195268494 |

| Configuration | (-inf,-0.2] | (-0.2,-0.1] | (-0.1,0] | (0,0.1] | (0.1,0.2] | (0.2,inf) |
| --- | --- | --- | --- | --- | --- | --- |
| department_only | 16 | 18 | 70 | 48 | 33 | 47 |
| team_only | 13 | 32 | 69 | 42 | 29 | 47 |
| department_team | 11 | 30 | 71 | 43 | 31 | 46 |
| department_team_calendar | 13 | 30 | 68 | 46 | 30 | 45 |

Positive mean and median residuals show persistent overprediction. The positive tail
is larger than the negative tail in these summaries: the department-only P95 error
is +0.4328 versus P05 -0.2411, with 47 residuals above +0.2 versus 16 at/below -0.2.
The added features do not resolve this error pattern. Normality, independence, and
statistical significance have not been established; repeated teams/dates complicate
row-independent uncertainty estimates.

| Configuration | Minimum prediction | Maximum prediction | Below 0 | Above 1 | Outside training target range |
| --- | --- | --- | --- | --- | --- |
| global_mean | 0.757869895 | 0.757869895 | 0 | 0 | 0 |
| department_mean | 0.738511299 | 0.784854605 | 0 | 0 | 0 |
| department_only | 0.738511299 | 0.784854605 | 0 | 0 | 0 |
| team_only | 0.647272220 | 0.849346179 | 0 | 0 | 0 |
| department_team | 0.631522708 | 0.871657987 | 0 | 0 | 0 |
| department_team_calendar | 0.607428274 | 0.894638025 | 0 | 0 | 0 |

There are no negative predictions or predictions above 1 in validation. The [0,1]
interval is only a diagnostic reference: source targets above 1 may be legitimate,
and no proven upper business limit exists. No predictions are clipped. Ordinary
linear regression remains unbounded for future inputs; this sample cannot certify
plausibility on other dates or categories.

## Measured runtime and environment

One local run, `perf_counter` wall seconds. Fit timings include estimator/pipeline
construction and training; inference covers the complete validation batch and output
Series construction. Feature building, diagnostics, I/O, and reporting are excluded
from those per-model timers. They are not production latency benchmarks.

| Configuration | Training seconds | Validation inference seconds (232 rows) |
| --- | --- | --- |
| global_mean | 0.000154 | 0.000050 |
| department_mean | 0.000815 | 0.000517 |
| department_only | 0.036740 | 0.001821 |
| team_only | 0.003692 | 0.002720 |
| department_team | 0.004177 | 0.002345 |
| department_team_calendar | 0.006052 | 0.003006 |

Shared train/validation feature construction: **0.005684 seconds**.
Load, source validation, split verification, features, all fits/predictions, comparisons,
and diagnostics: **0.140375 seconds**, excluding JSON construction/writing. First-fit
initialization and local workload affect individual times; rerun durations vary.

Recorded environment: Windows 11, Python **3.13.14**, pandas **3.1.1**, numpy
**2.5.5**, scikit-learn **1.9.1**, scipy **1.18.1**, joblib **1.6.0**,
threadpoolctl **3.8.0**; pytest **9.2.0**, Ruff **0.17.5**. Exact dependency closure
is in `requirements/exp-002.txt`, including the unchanged EXP-001 pins. This is an
installed-environment snapshot, not a cross-platform wheel/hash lock.

## Reproduction and verification

Run from the repository root with the existing local CSV and frozen split file:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/exp-002.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.experiments.linear
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

The runner writes `data/processed/exp-002-linear-regression.json` (ignored), containing
all metrics, feature/baseline comparisons, residual quantiles/bins, category
vocabularies, unknown-category counts, configuration, environment, dataset/split
fingerprints, and measured runtime. Use `--output .tmp/exp-002-reproduction.json`
for a second artifact; there is no test-scoring option. Do not run the split initializer.
The reviewed Markdown narrative is preserved across reruns.

Two real-data runs produced identical numerical results and metadata after excluding
fields ending in `_seconds`. Reproducible model predictions and coefficients are
also covered by synthetic tests. Frozen split bytes, raw CSV, and the EXP-001 report
are preserved.

Executed verification:

- `.venv/Scripts/python.exe -m pytest`: **166 passed in 7.20 seconds** (109 existing
  tests plus 57 new cases), with normal local filesystem access. An initial sandbox
  run could not access pytest temporary/cache directories. Its separate pandas
  deprecated-accessor failure was corrected to `dt.day_of_week` before the successful
  full runs; warnings remain errors in the test configuration.
- `.venv/Scripts/python.exe -m ruff check .`: passed.
- `.venv/Scripts/python.exe -m ruff format --check .`: passed.
- `.venv/Scripts/python.exe -m pip check`: passed; all 18 exact environment pins
  matched installed versions.
- Two real-data experiment runs: exit 0 and identical non-runtime JSON fields.
- Dataset, frozen split, EXP-001 report, and A01 profile hashes unchanged;
  `git diff --check` passed. No static type checker was run.

New cases cover the closed feature/input allowlists, date/team semantics, invalid
inputs, training-only vocabulary and fit indices, unknown categories, deterministic
predictions/coefficients, baseline equivalence, hand-calculated MAE changes and
diagnostics, frozen split identity/drift rejection, CLI input preservation, and
validation-only scoring. A test substitutes an object with no final-test frame;
another poisons synthetic final-test labels and assignments without affecting the
development results. No private CSV is needed to run the suite.

## Decisions, limitations, and next experiment

[ADR 0003](../decisions/0003-leakage-safe-linear-comparison.md) explains the closed
feature boundary, bounded comparisons, dense one-hot pipeline, optional ML dependency,
and artifacts. No final-test evaluation, Random Forest, boosting, service, frontend,
or scheduling work is included.

Keep the department mean as the comparison reference. The best linear candidate is
department only, an equivalent predictor with more machinery. Team/calendar
expansion is not supported by validation MAE. Feature timing is provisional, target
units/grain remain uncertain, and the short recurring-team history cannot establish
seasonal, unseen-team, unseen-factory, or deployment performance. Day of month assumes
a linear effect that resets monthly; team effects assume shared additive meaning
across departments. Validation reuse can bias future decisions; a narrow experiment
budget and a frozen final holdout remain necessary. No confidence interval or causal
claim is made.

Recommended EXP-003: a small, predefined Random Forest comparison on the same frozen
training/validation partitions and provisional eligible inputs, explicitly testing
whether nonlinear categorical interactions improve on the unchanged department mean.
Declare feature sets, seed, and a very small configuration budget before running;
report both department slices and regressions. Do not add conditional planning fields
without timestamp evidence or evaluate the final test. This is a proposed next task,
not an implemented algorithm or an asserted improvement.
