# EXP-001: Naive productivity baselines

Status: executed on training and validation data only. Final test remains reserved.

## Objective and hypothesis

Establish transparent reference errors for pre-shift productivity forecasting before Linear Regression or other ML algorithms. Hypothesis: department-specific historical training means may reduce validation MAE compared with a global training mean. MAE is the primary comparison metric; RMSE, R², bias, and slices provide context.

## Data and prediction-time assumptions

Source: `data/raw/garments_worker_productivity.csv`  
Dataset SHA-256: `763ffcdd39b7f7f360243c2af8f89ed733e8b5f9e511efeb0c886b83e1b76866`  
Frozen split configuration: `configs/chronological_split.json`.

The existing text loader, normalization, and validation checks run before splitting. They retain missing WIP, fractional staffing, and productivity above 1. The historical A01 profile describes the entire source CSV; it is not an untouched exploratory holdout. No test performance is computed here and no test targets estimate baseline parameters.

Prediction cutoff: immediately before the scheduled shift. The department assignment must be known at that time. Global predictions use no features; department predictions use only normalized scheduled department. Date chooses the partition. All training outcomes must have been finalized before the validation period begins. The row key (date, department, team) remains a working assumption because shift IDs are absent.

Excluded inputs: actual_productivity (label only), incentive, idle_time, idle_men, over_time, wip, targeted_productivity, smv, no_of_workers, no_of_style_change, quarter, day, and team. No aggregate includes validation or final test outcomes. No clipping, imputation, scaling, feature selection, or fitted encoding is performed.

### Validation findings inherited from the source checks

- warning: wip: missing values (WIP is assessed separately by department). Count: 506.
- warning: Target above 1 requires domain review; retained as-is. Count: 37.

## Frozen evaluation protocol

Strategy: `distinct-date-floor-60-20-20-v1`. Sort a copy stably by date. For n distinct dates, use boundaries floor(3n/5) and floor(4n/5), selected without target values or model results. This approximates 60/20/20 by observed dates; row counts need not follow the same proportions. No dates are moved to balance departments or improve metrics.

| Partition | First date (inclusive) | Last date (inclusive) | Dates | Rows | Use |
| --- | --- | --- | --- | --- | --- |
| train | 2015-01-01 | 2015-02-10 | 35 | 711 | Estimate means |
| validation | 2015-02-11 | 2015-02-25 | 12 | 232 | Compare baselines |
| test | 2015-02-26 | 2015-03-11 | 12 | 254 | Reserved; no metrics |

There are 59 observed dates: 59.32% training, 20.34% validation, and 20.34% final test. Boundaries require max(train date) < min(validation date) and max(validation date) < min(test date). Every row on a date stays together and every source row appears exactly once. The source fingerprint, counts, policy, and boundaries must match on reuse; a changed file fails rather than silently selecting new partitions.

## Baseline definitions and training statistics

Global mean: mean of the 711 training targets, **0.757869895391**, predicted for every validation record.

Department mean: mean of training targets within each normalized department. An unknown or missing department at prediction time falls back to the global training mean; it never uses validation statistics. The source loader still rejects unknown/missing departments in this historical dataset. No fallback is needed when every validation department has training observations.

| Training department | Target mean |
| --- | --- |
| finishing | 0.784854604966 |
| sewing | 0.738511299391 |

Both estimators are row-weighted arithmetic means. They are fixed throughout validation, not expanding-window predictors. No stochastic operations, seed, hyperparameters, fitted ML algorithms, or model selection search are involved.

## Measured validation performance

All errors are in productivity-ratio units; R² is dimensionless. Bias is mean(prediction − actual), so positive bias means overprediction. R² = 1 − SSE/SST with the validation-target mean used only in its denominator; it is undefined for fewer than two observations or a constant target. All validation rows are included with equal weight.

| Baseline | Training n | Validation n | MAE | RMSE | R² | Prediction bias |
| --- | --- | --- | --- | --- | --- | --- |
| global_mean | 711 | 232 | 0.144606972 | 0.197475686 | -0.105176844 | +0.060919708 |
| department_mean | 711 | 232 | 0.143226295 | 0.196492435 | -0.094198670 | +0.060338141 |

### Department-level validation MAE

| Department | Training n | Validation n | Global MAE | Department MAE |
| --- | --- | --- | --- | --- |
| finishing | 297 | 94 | 0.166818469 | 0.169320624 |
| sewing | 414 | 138 | 0.129477401 | 0.125451896 |

### Comparison

Department mean minus global mean validation MAE: **-0.001380677** (**-0.9548%** relative to the global mean baseline). A negative change is an improvement. The primary-metric comparison favors **department mean**. This is a validation comparison between two predefined references, not final model evaluation or evidence of production readiness.

Departments where the department predictor has higher MAE: finishing. An aggregate improvement does not imply improvement in every department. Negative R² means squared error exceeds the constant validation-mean reference used in the R² denominator; that reference is not a deployable fitted predictor.

## Limitations and leakage risks

The history is short and from one source context; departments and teams recur. This measures later dates for familiar operations, not generalization to unseen factories or teams. Averaging within departments does not establish a causal effect. Validation errors can reflect temporal changes that fixed means cannot track.

Measurement timestamps, shift timing, row grain, productivity units, and values above 1 still need domain confirmation. A01 already profiled all source dates and targets; keep that known limitation distinct from the performance holdout. Repeated validation comparisons in future experiments can overfit the development period. The final test partition must stay fixed and must not be evaluated until one model and its preprocessing are frozen using training/validation only.

## Reproduction and environment

From the repository root with the local CSV and committed split configuration:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/exp-001.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.experiments.naive --dataset 'data/raw/garments_worker_productivity.csv' --split-config 'configs/chronological_split.json'
```

The split configuration is created once with `python -m loometric.data.splitting`; that command refuses to overwrite an existing configuration. Normal experiment runs only read it. Do not regenerate partitions during later model comparisons.

Python: **3.13.14**. pandas: **3.1.1**; numpy: **2.5.5**; pytest: **9.2.0**; ruff: **0.17.5**.

Measured load/validate/split/predict/score wall time: **0.064295 seconds** (report rendering/writing excluded). Runtime varies between runs; fitted means, partitions, predictions, and metrics are deterministic for identical inputs and environment.

Exact environment pins are recorded in `requirements/exp-001.txt`; this is the initial Python 3.13 environment snapshot, not a cross-platform wheel/hash lock.

## Recommended next experiment

EXP-002: an interpretable Linear Regression using the same frozen partitions and only confirmed pre-shift features. Fit any categorical encoding on training rows only, compare validation MAE/RMSE and slices against both EXP-001 references, and leave final test performance uncalculated. No such model is implemented here.
