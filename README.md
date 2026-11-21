# Loometric

Local garment productivity ML engineering project. Current capabilities include CSV
validation, exploratory analysis, a pre-shift leakage assessment, frozen chronological
partitions, two naive mean baselines, Linear Regression, Random Forest Regression,
an expanding-window temporal audit, saved-prediction error/readiness analysis, and
an experimental offline prediction contract with explicit artifact generation.
A separate planning foundation validates synthetic production scenarios and calculates
deterministic shift capacity. Its reference scheduler now reserves finite capacity
and independently verifies complete or partial schedules without forecasting.
An optional OR-Tools CP-SAT engine optimizes the same frozen scheduling policy,
with independently verified results and explicit lexicographic proof status.
An offline synthetic benchmark runner audits solver budgets, scale, proof status,
resource limits and same-instance comparisons with the reference scheduler.
An immutable what-if engine compares explicit synthetic capacity changes, with
same-demand deltas and verified greedy fallback for optional solver attempts.
A bounded local FastAPI layer exposes capacity, greedy scheduling, independent
verification and scenario comparison with authentication and native process limits.
Its bounded asynchronous CP-SAT jobs support polling, verified results and real
native cancellation, with volatile local retention.
Models are selected on validation only; the final test remains reserved. Persistent
jobs, databases, deployment and further ML algorithms are deferred.

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
needs a package index; analysis stays offline and the optional API uses loopback HTTP
only. No cloud service is configured.

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

## EXP-005: error analysis and experimental prediction readiness

[EXP-005](docs/experiments/EXP-005-error-analysis.md) reuses the same saved EXP-004
predictions for 393 original-training observations on 20 dates. Models are not
retrained or tuned; original validation and test remain excluded from diagnostics.
The loader verifies artifact identity, folds, aligned targets/metadata, fixed
parameters, and recorded metrics before joining team identifiers.

| Model | MAE | Bias | Absolute-error median | Absolute-error P95 | Errors >=0.30 |
| --- | --- | --- | --- | --- | --- |
| Department mean | 0.147273373 | -0.007933222 | 0.134205331 | 0.378168359 | 34 |
| Linear A | 0.141037325 | -0.005961664 | 0.124371194 | 0.339531775 | 35 |
| Frozen forest | 0.148426346 | -0.023333554 | 0.129913097 | 0.352088849 | 33 |

The largest four errors contribute only about 3–4% of absolute error, while the
largest 40 contribute about 25–27%. A common 353-row sensitivity population retains
the same MAE ordering after excluding the baseline's worst 40 rows. Tail exclusions
are descriptive checks, not cleaned-data results or new model selection.

Bias changes direction across windows. Finishing has higher pooled error, and the
forest worsens finishing while improving sewing relative to the department mean.
Sixteen of 24 department/team groups have fewer than 20 rows; every team/window
cell is small. Stored IDs show variation, without establishing stable rosters,
worker performance, or a causal explanation.

The evidence supports an **explicitly experimental retrospective review tool** with
baseline comparison, provenance, support counts, limitations, and human oversight.
Live production readiness is unverified: feature/assignment timing, label latency,
target meaning, freshness, uncertainty, monitoring, and operational oversight need
real factory evidence. The report distinguishes confirmed software behavior from
provisional assumptions and unverified operational requirements.

```powershell
.\.venv\Scripts\python.exe -m loometric.experiments.errors
```

Use the unchanged CSV/split and existing EXP-004 JSON. Missing or inconsistent saved
predictions fail explicitly. Detailed groups, concentration, sensitivity, target
distributions, and high-error observation details stay in ignored
`data/processed/exp-005-error-analysis.json`. No raw observations are added to Git.
See [ADR 0006](docs/decisions/0006-saved-prediction-error-audit.md).

## M01: Experimental offline prediction

The local `loometric.prediction` CLI explicitly trains the frozen B_RF-01 and
Department Mean artifacts on the original **711 training rows**, then separately
loads a verified artifact for prediction. Inference never retrains. Strict versioned
requests include scheduled date, department/team, aware cutoff/snapshot timestamps
and provenance. Outputs include both predictions, artifact/model identity, warnings,
and VALID_EXPERIMENTAL, REVIEW_REQUIRED or ABSTAIN status. Every result requires
human review and is ineligible for automated staffing or scheduling decisions.

```powershell
$receipt = .\.venv\Scripts\python.exe -m loometric.prediction train `
  --artifact data/processed/m01-b-rf01
if ($LASTEXITCODE -ne 0) { throw "Artifact generation failed" }
$modelFingerprint = ($receipt | ConvertFrom-Json).artifact_fingerprint
.\.venv\Scripts\python.exe -m loometric.prediction predict `
  --artifact data/processed/m01-b-rf01 --expected-fingerprint $modelFingerprint `
  --request examples/offline-prediction/request.json `
  --policy examples/offline-prediction/review-policy.json `
  --at "2030-01-03T06:45:00+03:00"
```

Use the existing ML environment; choose a new artifact directory. Load only trusted
locally generated joblib artifacts using a separately retained training fingerprint.
Artifacts remain ignored. Two real builds were byte-identical; the synthetic replay
returned **0.820818668** versus baseline **0.738511299**, with REVIEW_REQUIRED for
unverified timing/freshness. These are example predictions, not accuracy results.
No new validation/test scoring occurs. The forest's temporal advantage remains
inconsistent; no production readiness or automatic decision authorization follows.

See the [input/output contract, measured checks and reproduction guide](docs/architecture/offline-prediction-contract.md)
and [ADR 0007](docs/decisions/0007-experimental-offline-prediction-contract.md).
There is no HTTP endpoint, database, frontend or optimizer in this milestone.

## M02: Synthetic production planning foundation

The independent `loometric.planning` package models orders, per-stage style standards,
line capabilities, shifts, calendars, efficiency profiles and planned downtime.
It calculates available worker-minutes, effective standard-minute capacity, whole
pieces, demand and shortfalls. Explicit interval unions prevent overlapping breaks,
stoppages and unavailability from being subtracted twice. No new dependencies or
ML artifacts are needed.

```powershell
.\.venv\Scripts\python.exe -m loometric.planning `
  --scenario examples/planning/capacity-demo.json
```

The entirely synthetic example gives sewing capacity of **96 pieces** on the day
shift after downtime and **120 pieces** on the evening shift. Finishing supports
**202 pieces**; zero-worker and unavailable lines yield zero. Structured reason codes
explain incompatible or insufficient slots. A second executable
`examples/planning/invalid-quantity.json` demonstrates strict rejection (exit 2).
Two complete report runs are byte-identical.

Each order/stage/slot assessment is independent: capacity is never reserved or
summed across orders, and every result states `schedule_feasibility=NOT_ASSESSED`.
The system does not establish a feasible multi-stage or multi-order schedule.
Crew capabilities, standards and efficiencies are explicit synthetic assumptions;
experimental ML predictions never become operating capacity automatically.

See the [domain, units, formulas, measured examples and limitations](docs/architecture/production-planning-domain.md)
and [ADR 0008](docs/decisions/0008-independent-planning-capacity-foundation.md).
The reference scheduling and optional CP-SAT layers are described below. APIs,
databases and frontend remain deferred.

## M03A: Reference scheduling and independent verification

The `loometric.scheduling` CLI allocates competing orders under the frozen
`whole-stage-minute-v1` policy: full-quantity, nonpreemptive stages within a single
uninterrupted shift fragment, one-minute granularity, hard release dates and soft
due dates. The deterministic reference ranks priority, due date and order ID, respects
precedence and reserves each selected line/crew interval before continuing.

```powershell
.\.venv\Scripts\python.exe -m loometric.scheduling dispatch `
  --instance examples/scheduling/competition.json

.\.venv\Scripts\python.exe -m loometric.scheduling verify `
  --instance examples/scheduling/competition.json `
  --schedule examples/scheduling/invalid-overlap.json
```

The independent verifier recomputes processing/availability and rejects wrong units,
quantities, overlaps, calendar violations and broken precedence. Only verified
proposals receive completion, tardiness, utilization, unused-capacity and makespan
metrics. VALID_PARTIAL remains distinct from INVALID; unfinished upstream work is
visible without being counted as finished goods. No optimality claim is made.

Five synthetic benchmarks reproduced byte-for-byte. The competition case completes
**60 units** and leaves **80 units** unscheduled despite both orders independently
fitting M02's slot. Parallel routing completes **90 units**, including two late
orders, with **1,237 minutes** total tardiness. Calendar fragments, unsupported
large operations, zero capacity and corrupted proposals are covered. Dispatch and
verify remain independent of OR-Tools and ML packages.

See the [frozen scheduling contract, complete measured results and M03B requirements](docs/architecture/scheduling-contract.md)
and [ADR 0009](docs/decisions/0009-reference-scheduling-policy.md).
Splitting, preemption, shared crews, material/WIP constraints and setups are deferred.
The M03B optimizer is described below. APIs, databases and frontend remain deferred.

## M03B: CP-SAT scheduling optimization

The optional optimizer uses **OR-Tools 9.15.6755** and the unchanged M03A instances,
duration rules, proposal contract, verifier and metrics. It minimizes unfinished
finished-goods units, then completed-order priority-weighted tardiness, then
makespan. Each objective is fixed only after its phase is proven OPTIMAL with zero
gap tolerances. FEASIBLE stops with an explicitly unproven incumbent; UNKNOWN never
fabricates a schedule. Every accepted incumbent passes independent verification.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/m03b.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.scheduling optimize `
  --instance examples/scheduling/competition.json `
  --seed 42 --workers 1 --time-limit-seconds 10 `
  --deterministic-time-limit 1 --benchmark-mode
```

The pinned snapshot preserves all prior dependency versions. The `optimization`
extra also supports a development install with `pip install -e ".[dev,ml,optimization]"`.
Budgets apply per phase. Structured JSON separates runtime from schedules, metrics,
proof statuses, returned bounds and the independently verified reference comparison.

All six synthetic cases reproduced identical non-runtime results on two runs;
all **18 objective phases were OPTIMAL**. Competition finishes **80 vs 60 units**,
while makespan worsens **300 vs 225 minutes**. The hand-enumerated case finishes
**10 vs 6 units**, while weighted tardiness worsens **1460 vs 1458 minutes**.
The limits case improves only makespan by omitting unfinished upstream work; it
finishes no additional goods. The other three objective vectors tie. These results
support the declared hierarchy on small synthetic cases, without establishing
factory readiness or general performance gains.

See the [formulation, complete benchmark tables, measured runtimes, timeout policy and reproduction instructions](docs/architecture/cp-sat-optimization.md)
and [ADR 0010](docs/decisions/0010-cp-sat-strict-lexicographic-scheduling.md).
At M03B completion, the suite passed **639 tests**. Shared workers, setups, materials,
splitting, WIP, ML-derived capacity and application integration remain deferred.

## M03C: Synthetic scalability and solver robustness

The [predeclared audit](docs/experiments/M03C-solver-scalability.md) uses the unchanged
solver, verifier, reference dispatcher and scheduling policy. A versioned generator
varies orders, resources, stages, calendars, compatibility and aggregate demand.
It makes no calibrated factory-realism claim and uses no ML inputs.

```powershell
.\.venv\Scripts\python.exe -m loometric.benchmarks `
  --config configs/m03c_benchmark.json `
  --output-dir data/processed/m03c-local-run
```

The fixed matrix covers 8/24/60-order cases, three load targets, three generator
seeds, 1/5/10-second phase budgets, deterministic limit 1.0, one solver worker and
two repetitions. The 150-order stress tier stays visible as resource-skipped.
Native jobs run serially under hard memory and whole-process wall limits. Windows
launch starts suspended, and the worker confirms its memory-limited job membership.
Inputs, journals and results remain local and ignored; existing evidence is never
overwritten. The report distinguishes missing incumbents, unproven solutions,
complete proofs, and BETTER/TIE/WORSE comparisons. Wall-limited outcomes may differ
between repetitions.

Across 162 native runs: **90 better, 6 ties, 7 worse, 59 without an incumbent**;
**70** completed the full lexicographic proof. All **103** returned candidates and
all **36** reference inputs passed independent saved-result audits. Small cases
proved all 54 runs; 60-order cases yielded no useful improvement. Ten of 81 repeated
pairs differed under wall limits, despite fixed seeds and one worker. Peak job
committed memory was **441.02 MiB** under a **768 MiB** cap. At M03C completion, the
suite passed **716 tests**. These observations support bounded local workflows with explicit
proof/abstention handling; they do not establish general production readiness.

## M04: Conditional production scenarios

The local `loometric.scenarios` CLI binds an ordered change specification to an exact
baseline fingerprint. It atomically changes workers, profile efficiency, assignments,
planned downtime or line availability, preserving orders, standards, dates and the
frozen scheduling policy. Invalid references and conflicting edits fail explicitly.

```powershell
.\.venv\Scripts\python.exe -m loometric.scenarios `
  --baseline examples/scenarios/capacity-baseline.json `
  --scenario examples/scenarios/additional-workers.json

.\.venv\Scripts\python.exe -m loometric.scenarios `
  --baseline examples/scenarios/routing-baseline.json `
  --scenario examples/scenarios/capacity-optimizer-recovery.json
```

Greedy is always independently verified. Explicit optional CP-SAT runs under existing
resource limits; its verified incumbent replaces greedy only when strictly better
in frozen objective order. Ties, worse results, UNKNOWN and resource/dependency
failures retain greedy with an explicit reason. Candidate proof and selected producer
remain separate. Greedy needs no optional solver package.

Worked examples finish **45→55 units** with additional workers. A smaller downtime
reduction increases capacity **45→50 standard minutes** while still finishing **45**.
A routing example shows greedy worsening **28→18 units** despite capacity increasing
**30→40**; optional CP-SAT recovers **28 units** and improves makespan **10→9 minutes**.
These are conditional synthetic calculations, without measured factory-productivity
or causal claims. Utilization changes expose their capacity denominators.

All 14 specifications reproduced twice (12 valid, two rejected as declared); native
comparison excludes measured runtime. At the M04 milestone, **812 tests** passed.
See the [schema, worked results, metrics, selection policy and limitations](docs/architecture/what-if-scenario-engine.md)
and [ADR 0012](docs/decisions/0012-atomic-what-if-and-verified-selection.md).
M05A exposes bounded greedy API operations and M05B adds bounded optimization jobs
below; databases, frontend and deployment remain deferred.

## Synthetic data CSV inspection

View all tracked M02–M04 synthetic fixtures and all 36 predeclared M03C generated
instances in one local CSV:

```powershell
.\.venv\Scripts\python.exe -m loometric.synthetic_export
```

Open `data/processed/synthetic-data-view.csv` in VS Code. Current output has
**20,645 rows and 80 columns**, including 12 purely transformed what-if inputs.
Filter by `source_id` and `record_type`; order quantities and resource entities
remain separate rows with explicit relationship IDs. These are alternative input
views, not independent orders/capacity to sum across scenarios. Invalid examples
retain their error codes. No scheduler, CP-SAT or new performance metrics run.
The generated CSV stays ignored; existing fixtures and benchmark definitions stay
unchanged. See [all columns, row grain, provenance, counts and checks](docs/synthetic-data-view.md).

## M05A: Local planning API foundation

Optional FastAPI endpoints under `/api/v1`: GET `health`, GET `capabilities`, POST
`planning/capacity`, POST `scheduling/dispatch`, POST `scheduling/verify` and POST
`scenarios/compare`. OpenAPI JSON and self-contained documentation are at
`/api/v1/openapi.json` and `/api/v1/docs`. Domain contracts/engines remain unchanged.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/m05a.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ".[dev,ml,optimization,api]"
$env:LOOMETRIC_API_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -m loometric.api
```

The supported server binds 127.0.0.1:8000, requires a configured Bearer token for all
operations except health/docs, rejects nonlocal peers/Hosts and restricts CORS.
Requests are limited to 256 KiB, 32 orders/96 stages, 64 scenario changes and two
concurrent expensive calls. A guarded 256 MiB child performs parsing/engine work with
a 5-second watchdog; body reading has a separate 3-second deadline. Native timeout
actually kills/reaps the worker; disconnects retain their slot until cleanup.
Exact Decimal numbers, fingerprints, independent verification, synthetic provenance
and valid-partial status survive transport. No API training, artifact/data loading
or synchronous CP-SAT is exposed; M01 stays offline. M05B job endpoints appear below.

Run [the client](examples/api/workflow.py) in a terminal with the same token/port,
or execute the self-contained live-server test:

```powershell
.\.venv\Scripts\python.exe examples/api/workflow.py
.\.venv\Scripts\python.exe -m pytest tests/api/test_local_server.py -q
```

The real loopback workflow repeats twice with identical summaries: synthetic
baseline 45 completed units versus 55 after hypothetical additional workers.
M05A verification record: **76 API tests** and **888 total tests** passed; Ruff lint/166-file
format check, dependency pins, wheel contents and protected-file checks passed.
These are conditional fixture calculations, not factory measurements. See
[API contracts, security, limits, errors and verification evidence](docs/architecture/api-foundation.md)
and [ADR 0013](docs/decisions/0013-local-api-and-bounded-synchronous-execution.md).
The shared-secret policy supports local development; public hosting is unsupported.

## M05B: Bounded asynchronous optimization jobs

Authenticated endpoints: POST `/api/v1/jobs/scheduling`, POST `/api/v1/jobs/scenarios`,
GET `/api/v1/jobs/{job_id}`, GET `/api/v1/jobs/{job_id}/result`, and DELETE
`/api/v1/jobs/{job_id}`. Submissions return 202 with opaque IDs; lifecycle states are
QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED and EXPIRED. Results retain the existing
independent verifier, greedy baseline, strict-better selection and proof distinctions.

One active job and two waiting entries use a fixed supervisor, separate from M05A's
two synchronous slots. Defaults: 15s whole-job watchdog, 768 MiB outer Windows aggregate
memory, 512 MiB/5s nested optimizer, 1s wall/1 deterministic unit per phase, seed 42 and
one solver worker. Storage is bounded to 32 records and 8 MiB retained plus reserved
result bytes, 2 MiB per result; terminal results expire after 300s and tombstones after
another 300s. Cancellation stops the native process tree before releasing capacity.
Restart loses all job records; no durable-job or crash-recovery claim is made.

With the same server/token environment as M05A:

```powershell
.\.venv\Scripts\python.exe examples/api/jobs_workflow.py
.\.venv\Scripts\python.exe -m pytest tests/api/test_job_live.py -q
```

The real local HTTP workflow ran twice. In the modified synthetic routing input,
greedy finishes 18 units and CP-SAT recovers 28 with all three objectives proven;
the original baseline already finishes 28. Both cancellation examples ended CANCELLED.
Verification: **940 tests passed**, including 117 API tests; Ruff/pins/packaging checks
and native cancellation/shutdown evidence are documented in the
[job API architecture](docs/architecture/optimization-jobs-api.md) and
[ADR 0014](docs/decisions/0014-bounded-local-optimization-jobs.md).
The frozen optimizer/scenario/ML contracts remain unchanged. No dependencies added;
Linux execution remains unverified on this Windows host. M06 is not started.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
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
Error-analysis checks cover hand-calculated summaries/tails, group support, identical
sensitivity populations, artifact drift, no refitting, and holdout isolation.
Offline-prediction checks cover strict request/provenance contracts, source-bound
review policy, unknown/stale inputs, trusted artifact compatibility/integrity,
deterministic artifacts/inference, training-only label loading and explicit abstention.
Planning checks cover dimensional capacity arithmetic, interval unions, references,
capabilities, zero capacity, independent-order scope and operation without ML packages
or protected data access.
Scheduling checks cover exact rounded durations, finite reservations, precedence,
strict proposal accounting, corrupted-schedule rejection, finished-goods metrics,
deterministic benchmarks and isolation from ML/solver/protected data dependencies.
Optimization checks cover optional alternatives, resource constraints, integer
bounds, proof gates, time limits, independent verification, exhaustive small-case
oracles, deterministic output and byte-identical reference reports.
Scalability checks cover generated-schema validity, pressure arithmetic, input
fingerprints, resource enforcement, wall-watchdog cleanup, incomplete-proof states,
independent audit rejection and retained skip/result evidence.
Scenario checks cover immutable baselines, atomic edits, strict provenance/schema,
same-demand deltas, hand-calculated outcomes, unknown/feasible/proven solver states,
strict-better selection and verified greedy fallback.
API checks cover all endpoints, Decimal round trips, strict input validation, auth/CORS,
limits, real process termination, AnyIO/direct asyncio cancellation, safe errors,
protected-data isolation and a repeated real loopback client workflow.
Job checks add atomic queue/result admission, lifecycle races, retention/expiry,
native cancellation/shutdown, proof/objective/fallback evidence and restart semantics.
Install requirements/m05a.txt and all four extras (`dev,ml,optimization,api`) for the
complete suite. Earlier M03B/ML dependency pins remain unchanged.
Type hints are used throughout; no static type checker is configured for this task.

## Layout

```text
data/
  raw/                       # User-supplied immutable CSV (ignored)
  processed/                 # Local numerical experiment artifacts (ignored)
configs/
  chronological_split.json   # Frozen source fingerprint, date ranges, and counts
  m03c_benchmark.json         # Predeclared synthetic matrix, budgets and resource guards
requirements/
  exp-001.txt                # Exact installed EXP-001 environment snapshot
  exp-002.txt                # EXP-001 pins plus exact ML dependency closure
  m03b.txt                   # Prior pins plus exact optional OR-Tools dependency closure
src/loometric/
  api/                       # Local sync operations and bounded volatile jobs; no model serving
  execution.py               # Shared hard process limits and bounded native workers
  cli.py                     # Local orchestration and exit codes
  leakage.py                 # Source-column availability policy
  baselines.py               # Global and department training-mean predictors
  evaluation.py              # Explicit regression metrics and alignment checks
  error_analysis.py          # Pure saved-prediction error, group, and tail diagnostics
  features.py                # Stateless provisional pre-shift feature boundary
  preprocessing.py           # Shared training-fitted categorical encoding/metadata
  linear.py                  # Training-fitted one-hot/OLS pipeline constructor
  forest.py                  # Fixed forest profiles, pipeline, and importance summaries
  experiments/               # Local experiment runners and saved-prediction audit CLI
  prediction/                # Offline contracts, policy, artifacts, inference and CLI
  planning/                  # Independent domain, availability, capacity and scenario CLI
  scheduling/                # Frozen contracts, reference dispatch, verifier, metrics and CLI
  optimization/              # CP-SAT model, proof-gated solves, adapter and comparison
  benchmarks/                # Synthetic generator, isolated resource guards and audit CLI
  scenarios/                 # Immutable capacity edits, verified selection, deltas and CLI
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
  architecture/              # Prediction, planning and scheduling contracts/lifecycles
examples/offline-prediction/  # Synthetic request and non-operational review policy
examples/planning/            # Synthetic capacity and invalid-input scenarios
examples/scheduling/          # Synthetic benchmarks and deliberately invalid proposals
examples/scenarios/           # Small explicit what-if inputs, including conflicts/regressions
examples/api/                 # Exact-number synthetic HTTP client workflow
```

See [architecture decisions](docs/decisions/0001-local-data-foundation.md).
The future stack includes React, Node.js, PostgreSQL and XGBoost.
Those components are deferred; this package establishes the data and evaluation
contracts they will depend on. `docs/COMMIT_PLAN.md` is an intentionally ignored local
roadmap. Analysis commands make no network calls and use no embedded credentials
or external telemetry.

