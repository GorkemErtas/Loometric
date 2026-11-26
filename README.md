# Loometric

A local garment production planning and analytics project. Build synthetic production
scenarios, compare schedules and explore experimental pre-shift forecasts.

**Stack:** Python, FastAPI, pandas, scikit-learn, OR-Tools, React and TypeScript.

## Features

- Create or import synthetic orders, resources, shifts and calendars.
- Calculate capacity, generate schedules and inspect independently verified Gantt results.
- Compare what-if scenarios and run bounded optimization jobs with cancellation.
- Compare RF Physics, Random Forest, histogram boosting and Grouped Mean predictions.
- Validate garment productivity CSVs and reproduce documented offline ML experiments.

## Local setup

Requires Python 3.13 and Node.js 22.12+ (22.x), 24.x or 26+.
Commands below use Windows PowerShell from the repository root.

**Dashboard:**

```powershell
cd frontend
npm ci --ignore-scripts
npm run dev
```

Open **http://127.0.0.1:5173**. Fixture preview works without a backend.

**Backend:** open another terminal in the repository root.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements/m05a.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ".[dev,ml,optimization,api]"
$env:LOOMETRIC_API_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -m loometric.api
```

In the dashboard, select **Configure API**, use **http://127.0.0.1:8000** and enter
that terminal session's Bearer token. API documentation: **http://127.0.0.1:8000/api/v1/docs**.

**AI Predictions** defaults to RF Physics and requires trusted local v1/v2 model
artifacts, which are not included in Git. Prepare them separately using the
[reproducible artifact setup](docs/architecture/experimental-ml-inference.md#reproducible-v2-artifact-preparation)
before requesting predictions; the rest of the app can run without them.
Models are never trained automatically during inference.

## Checks

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
cd frontend
npm test
npm run typecheck
npm run check
npm run build
```

Run `npm run test:browser` from `frontend/` for browser workflows; trusted local
model artifacts are required. Detailed verification results are in the
[inference guide](docs/architecture/experimental-ml-inference.md).
M09B verification: **1,307 Python tests**, **183 frontend tests** and
**12 real-backend browser workflows** passed on Windows/Edge, plus lint/type/build checks.

## Scope and limitations

- Planning demos use synthetic data; there is no connection to factory systems.
- Forecasts estimate synthetic standard capacity attainment, not employee efficiency
  or guaranteed output. Models remain experimental: **NO_ML_PROMOTION**.
- RF Physics metrics come from previously inspected validation data. No independently
  calibrated prediction band is available. Predictions never set planning capacity or efficiency.
- Sessions, drafts and jobs are memory-only. No database or cloud deployment is included.

On 4,833 **spent synthetic benchmark validation** rows, RF Physics MAE is
**0.05793136**, a **24.05% reduction versus Forest12** (0.07627744); RMSE is
**0.09936277** and R² **0.82067**. These are reproduced historical diagnostics,
not independent validation or factory-performance evidence. Hidden disruptions,
stage regressions and worst errors remain unresolved; see [EXP-008](docs/experiments/EXP-008-ml-improvement-research.md).

## Documentation

- [Dashboard setup and workflows](frontend/README.md)
- [Planning and capacity](docs/architecture/production-planning-domain.md),
  [scheduling](docs/architecture/scheduling-contract.md) and
  [scenario comparison](docs/architecture/what-if-scenario-engine.md)
- [Prediction contracts](docs/architecture/experimental-ml-inference.md) and
  [RF Physics research](docs/experiments/EXP-008-ml-improvement-research.md)
- [EXP-009 prospective frozen-model protocol](docs/experiments/EXP-009-prospective-frozen-evaluation.md)
  — predeclared; evaluation not executed.
- [Dataset profile](docs/data_profile.md) and [pre-shift feature policy](docs/prediction_problem.md)
- [Architecture decisions](docs/decisions/) and [experiment reports](docs/experiments/)
