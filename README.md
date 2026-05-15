# Loometric

Local garment productivity ML engineering project. Current capabilities include CSV
validation, exploratory analysis, a pre-shift leakage assessment, frozen chronological
partitions, and two naive mean baselines evaluated on validation data only.
Application services, databases, optimization, and further ML algorithms are deferred.

## Prediction problem

Immediately before a scheduled shift starts, predict a team's department-level
`actual_productivity` at the end of that shift using only information already available
at the cutoff. The tentative observation key is `(date, department, team)`. The source
does not include shift IDs or measurement timestamps, so that grain and feature timing
need confirmation before training.

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
hand-calculated metrics, train-only statistics, and exclusion of final test scoring.
Type hints are used throughout; no static type checker is configured for this task.

## Layout

```text
data/
  raw/                       # User-supplied immutable CSV (ignored)
  processed/                 # Reserved; no transformed data is written yet
configs/
  chronological_split.json   # Frozen source fingerprint, date ranges, and counts
requirements/
  exp-001.txt                # Exact installed EXP-001 environment snapshot
src/loometric/
  cli.py                     # Local orchestration and exit codes
  leakage.py                 # Source-column availability policy
  baselines.py               # Global and department training-mean predictors
  evaluation.py              # Explicit regression metrics and alignment checks
  experiments/               # EXP-001 orchestration and report rendering
  data/
    schema.py                # Expected columns and domain constraints
    loading.py               # Strict CSV ingestion and normalization
    validation.py            # Structured errors and reviewable warnings
    profiling.py             # Deterministic Markdown EDA report
    splitting.py             # Complete-date chronological partitions and config CLI
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

