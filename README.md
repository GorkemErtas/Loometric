# Loometric

Local garment productivity ML engineering project. Current capabilities include CSV
validation, exploratory analysis, a pre-shift leakage assessment, frozen chronological
partitions, two naive mean baselines, Linear Regression, Random Forest Regression,
and an expanding-window temporal audit inside the original training period.
Models are selected on validation only; the final test remains reserved. Application
services, databases, optimization, and further ML algorithms are deferred.

## Prediction problem

Immediately before a scheduled shift starts, predict a team's department-level
`actual_productivity` at the end of that shift using only information already available
at the cutoff. The tentative observation key is `(date, department, team)`. The source
does not include shift IDs or measurement timestamps, so that grain and feature timing
remain provisional assumptions in the current experiments.

Realized overtime, incentives, idle time, and idle staffing are unavailable at the
cutoff. WIP, planned productivity, standard minute value, staffing, and style changes
need verified pre-shift snapshots. The complete policy appears in
[the prediction contract](docs/prediction_problem.md) and in generated profiles.

## Local setup

Python 3.11 or newer is required; Python 3.13 is the initial development environment.
Run commands from the repository root. Package installation is the only step that
needs a package index; runtime code makes no network calls and uses no cloud services.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

On macOS/Linux, use `python3 -m venv .venv` and `.venv/bin/python` for the following
commands. Virtual-environment activation is optional.

## Dataset and report

Place your CSV at:

```text
data/raw/garments_worker_productivity.csv
```

The directory exists; source data is ignored by Git and is never modified by the
workflow. No dataset is downloaded automatically. The generated
[data profile](docs/data_profile.md) describes the local source CSV and records its
SHA-256. Synthetic test records are not used to claim findings about the real data.

```powershell
.\.venv\Scripts\python.exe -m loometric
```

This validates the dataset and writes `docs/data_profile.md`. To choose other paths:

```powershell
.\.venv\Scripts\python.exe -m loometric --dataset data/raw/garments_worker_productivity.csv --output docs/data_profile.md
```

Exit codes: `0` means validation passed (warnings may remain); `1` means validation
errors were found and written into the report; `2` means a missing/unreadable/malformed
CSV, output I/O failure, or invalid CLI usage. A missing or malformed input does not
replace an existing report. A completed report includes the source SHA-256; confirm
it matches the current CSV before treating an earlier report as current.

Checks and EDA include:

- Exact source columns, duplicate headers, CSV record width, numeric parsing,
  finite values, required fields, nonnegative quantities, and integer counts.
- Dates parsed explicitly with `%m/%d/%Y`, weekday agreement, source chronology,
  duplicate rows, and repeated tentative shift keys. Rows are not silently sorted.
- Department normalization (`sweing` to `sewing`, trimming spaces), allowed weekday
  and within-month quarter categories, and observed team IDs.
- WIP missingness **by department**, with observed zeros distinguished from blanks.
  Missing WIP is allowed with a warning; malformed WIP is an error.
- Continuous target distribution, quantiles, bins, department/date summaries,
  numeric summaries, and retrospective correlations. Productivity above 1 is
  flagged for review and retained; no clipping or imputation is performed.
- Explicit availability assessment of every source field and requirements for
  future chronological evaluation.

Fractional `no_of_workers` is retained because the source may report average staffing;
it still must be finite and positive. There is no assumed fixed team roster, staffing
ceiling, production calendar, or statistical outlier threshold.

## EXP-001: chronological splits and naive baselines

The versioned [split configuration](configs/chronological_split.json) binds partitions
to the exact CSV SHA-256. It uses the first floor(60%) and floor(80%) boundaries of
sorted distinct dates. All rows on a date stay together; sorting operates on a copy.

| Partition | Inclusive date range | Distinct dates | Rows |
| --- | --- | --- | --- |
| Training | 2015-01-01 to 2015-02-10 | 35 | 711 |
| Validation | 2015-02-11 to 2015-02-25 | 12 | 232 |
| Final test | 2015-02-26 to 2015-03-11 | 12 | 254 |

Reuse this file for every experiment. Dataset bytes, policy, counts, or boundaries
that disagree with it fail explicitly. No reshuffling or automatic regeneration occurs.
The one-time initializer, `python -m loometric.data.splitting`, refuses to overwrite
an existing configuration and is not part of routine experiment reproduction.

For the recorded Python 3.13.14 environment, install the exact EXP-001 dependency
snapshot before running the experiment (no new ML dependencies are needed):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/exp-001.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.experiments.naive
```

The command generates [EXP-001](docs/experiments/EXP-001-naive-baseline.md). Both
predictors estimate arithmetic target means from training rows only. One predicts the
global mean; the other uses the scheduled department's training mean and falls back
to the global mean for unknown/missing departments. No realized shift feature is used.
Validation MAE is 0.144606972 for the global mean and 0.143226295 for the department
mean, a 0.9548% decrease. Both validation R² values are negative; these are references,
not evidence of production-ready forecasting. The report includes RMSE, signed bias,
department slices, counts, fitted means, environment, and measured runtime.

Final test metrics are never calculated by this command. A01's existing full-source
EDA already described all source targets; the final test is reserved from performance
evaluation, not claimed to be unseen in earlier descriptive analysis. See
[ADR 0002](docs/decisions/0002-chronological-evaluation-and-naive-baselines.md).

## EXP-002: Linear Regression and provisional pre-shift features

The [EXP-002 report](docs/experiments/EXP-002-linear-regression.md) records four fixed
feature comparisons using the unchanged 711 training / 232 validation records.
Department, categorical team ID, date-derived categorical weekday, and numeric day
of month are provisionally available before the shift. All conditional planning
fields, realized shift values, and labels remain excluded as inputs.

A scikit-learn Pipeline contains ColumnTransformer, OneHotEncoder with unknown
category handling, and ordinary LinearRegression. Learned preprocessing and model
fitting use training only. No predictions are clipped or missing inputs imputed.

| Feature set | Validation MAE | Change vs department-mean baseline |
| --- | --- | --- |
| Department only | 0.143226295 | 0.0000% |
| Team only | 0.149747347 | +4.5530% |
| Department + team | 0.150379924 | +4.9946% |
| Department + team + calendar | 0.150551578 | +5.1145% |

**No model improves on the EXP-001 department mean.** Department-only regression
reproduces that predictor: RMSE 0.196492435, R² -0.094198670, bias +0.060338141.
Adding calendar features to department/team increases MAE by 0.1141%, although RMSE
and bias decrease. Team-containing models worsen MAE in both departments relative
to the department mean. Keep the department baseline as the comparison reference.

Install the exact recorded ML environment and run locally:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/exp-002.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.experiments.linear
```

For an unpinned development install, use `pip install -e ".[dev,ml]"`; the `ml`
extra keeps the data-only workflow independent of scikit-learn. The runner writes
`data/processed/exp-002-linear-regression.json` (ignored), preserving the reviewed
Markdown report. Use `--output` for an alternate JSON path. The report documents
runtime, residuals, range checks, exact configuration, environment, and limitations.
Two real-data runs matched after excluding measured runtimes. The final test remains
excluded from all fitting, feature construction, prediction, selection, and metrics.
See [ADR 0003](docs/decisions/0003-leakage-safe-linear-comparison.md).

## EXP-003: a fixed Random Forest comparison

[EXP-003](docs/experiments/EXP-003-random-forest.md) compares six predefined forests:
department/team or department/team/calendar, each with three depth/leaf/tree-count
profiles. All use seed 42, one worker, the same training-fitted categorical encoding,
and the unchanged 711 training / 232 validation observations. No new input fields
or dependencies are added, and final-test data stays excluded from modeling/scoring.

The best candidate, **B_RF-01**, uses department, team, weekday, and day of month,
with **100 trees, max_depth=3, min_samples_leaf=20**. Its validation MAE is
**0.140201317**, a **0.003024977 (2.1120%) decrease** from the department mean and
equivalent best EXP-002 model. Validation RMSE is 0.195062509, R² -0.078331093, and
bias +0.055805734. Finishing/sewing MAE is 0.165290002 / 0.123111924; both improve
on the department mean.

This is the preferred candidate within the fixed validation comparison. The gain is
modest, R² remains negative, and feature timing remains provisional. Deeper profiles
have lower training errors but worse validation MAE. The flexible calendar model's
training/validation MAE is 0.067919069 / 0.159350747, indicating overfitting risk.
Impurity importance is descriptive training attribution, without causal meaning or
demonstrated out-of-sample importance. No significance or operational-readiness claim
is made. The report contains every candidate's metrics, slices, runtimes, residuals,
prediction ranges, importance, and limitations.

Reuse the existing exact ML environment; no new dependency snapshot is needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/exp-002.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.experiments.forest
```

The runner writes ignored `data/processed/exp-003-random-forest.json`; `--output`
chooses an alternate local path. Two real-data runs matched except measured runtimes,
and earlier experiments reproduced after extracting shared preprocessing/diagnostics.
See [ADR 0004](docs/decisions/0004-bounded-random-forest-comparison.md).

## EXP-004: temporal robustness inside training only

[EXP-004](docs/experiments/EXP-004-temporal-robustness.md) audits five fixed models
using four expanding windows inside the original 35 training dates. Begin with
15 observed dates, evaluate the next five, and expand the prefix by five each time.
The evaluation windows cover 393 rows once each; original validation and final test
stay excluded. Every fold fits fresh preprocessing and models on its earlier prefix.

The frozen EXP-003 forest wins **2 windows and loses 2** against the department mean.
Its pooled MAE is **0.148426346**, versus **0.147273373** for that baseline:
**+0.001152973 (+0.7829%)**. Pooled finishing MAE worsens (0.172184645 vs 0.165755260),
while sewing improves (0.132452681 vs 0.134847254). OLS with department/team has
the lowest pooled MAE here, 0.141037325. This is a retrospective audit of fixed
choices, without selecting a new model.

The forest's earlier 2.1120% validation gain remains a valid EXP-003 measurement,
but its advantage is not consistent across these historical windows. Fold sizes,
dates, and training histories differ; scores are not directly interchangeable.
Overlapping training prefixes, recurring teams, and the forest's earlier selection
limit independence. Feature capture times and label-finalization latency remain
unverified. The audit does not justify proceeding directly to gradient boosting
as an evidence-backed increase in complexity.

```powershell
.\.venv\Scripts\python.exe -m loometric.experiments.temporal
```

Reuse the EXP-002 dependency snapshot. The command writes ignored
`data/processed/exp-004-temporal-robustness.json`, including folds, metrics,
department slices, runtime, and original-training-only evaluation predictions.
Two real-data runs matched exactly except runtimes. The report contains all fold
MAE/RMSE/R²/bias, equal-fold and pooled summaries, timing assumptions, limitations,
and reproduction commands. See [ADR 0005](docs/decisions/0005-training-only-temporal-robustness.md).

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Tests use small synthetic data and temporary directories, and run without the private
CSV. They cover parsing, validation failures, chronology, department WIP reporting,
leakage policy coverage, CLI exit codes, reproducibility, and preservation of raw data.
Additional checks cover complete date groups, frozen split reuse, baseline fallback,
hand-calculated metrics, train-only encoding/statistics, unknown categories, restricted
feature inputs, reproducible training, and exclusion of final test prediction/scoring.
Forest checks cover fixed profiles, seed/worker settings, training diagnostics,
validation-only selection/baseline retention, and importance aggregation arithmetic.
Temporal checks cover whole-date windows, expanding prefixes, fresh fold encoders,
pooled metric arithmetic, deterministic predictions, and exclusion of both outer holdouts.
Install the `ml` extra or EXP-002 snapshot to run the complete test suite.
Type hints are used throughout; no static type checker is configured for this task.

## Layout

```text
data/
  raw/                       # User-supplied immutable CSV (ignored)
  processed/                 # Local numerical experiment artifacts (ignored)
configs/
  chronological_split.json   # Frozen source fingerprint, date ranges, and counts
requirements/
  exp-001.txt                # Exact installed EXP-001 environment snapshot
  exp-002.txt                # EXP-001 pins plus exact ML dependency closure
src/loometric/
  cli.py                     # Local orchestration and exit codes
  leakage.py                 # Source-column availability policy
  baselines.py               # Global and department training-mean predictors
  evaluation.py              # Explicit regression metrics and alignment checks
  features.py                # Stateless provisional pre-shift feature boundary
  preprocessing.py           # Shared training-fitted categorical encoding/metadata
  linear.py                  # Training-fitted one-hot/OLS pipeline constructor
  forest.py                  # Fixed forest profiles, pipeline, and importance summaries
  experiments/               # EXP-001 report and EXP-002/EXP-003 JSON runners
  data/
    schema.py                # Expected columns and domain constraints
    loading.py               # Strict CSV ingestion and normalization
    validation.py            # Structured errors and reviewable warnings
    profiling.py             # Deterministic Markdown EDA report
    splitting.py             # Complete-date chronological partitions and config CLI
    temporal.py              # Expanding complete-date windows within verified training
tests/                       # Synthetic unit and CLI integration tests
docs/
  data_profile.md            # Actual generated findings, or explicit pending status
  prediction_problem.md      # Cutoff, grain, eligibility, and evaluation contract
  decisions/                 # Architecture decisions and rationale
  experiments/               # Measured experiment reports
```

See [architecture decisions](docs/decisions/0001-local-data-foundation.md).
The future stack is React, Node.js, PostgreSQL, FastAPI, XGBoost, and OR-Tools.
Those components are deferred; this package establishes the data and evaluation
contracts they will depend on. `docs/COMMIT_PLAN.md` is an intentionally ignored local
roadmap. No credentials, external telemetry, automatic commits, or pushes are used.

