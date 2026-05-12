# Loometric

Local data foundations for a garment productivity ML engineering project. This first task
contains CSV validation, exploratory data analysis, and a pre-shift leakage assessment.
There is no model training, application server, database, or deployment in this task.

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

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Tests use small synthetic data and temporary directories, and run without the private
CSV. They cover parsing, validation failures, chronology, department WIP reporting,
leakage policy coverage, CLI exit codes, reproducibility, and preservation of raw data.
Type hints are used throughout; no static type checker is configured for this task.

## Layout

```text
data/
  raw/                       # User-supplied immutable CSV (ignored)
  processed/                 # Reserved; no transformed data is written yet
src/loometric/
  cli.py                     # Local orchestration and exit codes
  leakage.py                 # Source-column availability policy
  data/
    schema.py                # Expected columns and domain constraints
    loading.py               # Strict CSV ingestion and normalization
    validation.py            # Structured errors and reviewable warnings
    profiling.py             # Deterministic Markdown EDA report
tests/                       # Synthetic unit and CLI integration tests
docs/
  data_profile.md            # Actual generated findings, or explicit pending status
  prediction_problem.md      # Cutoff, grain, eligibility, and evaluation contract
  decisions/                 # Architecture decisions and rationale
```

See [architecture decisions](docs/decisions/0001-local-data-foundation.md).
The future stack is React, Node.js, PostgreSQL, FastAPI, XGBoost, and OR-Tools.
Those components are deferred; this package establishes the data contract they will
depend on. No credentials, external telemetry, automatic commits, or pushes are used.

