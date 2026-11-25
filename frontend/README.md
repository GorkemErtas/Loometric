# Loometric local dashboard

React/strict TypeScript local workspace for synthetic M02–M04 inputs and the existing
M05A/M05B APIs. Five inspection pages are joined by Production scheduling, What-if
scenarios and Optimization jobs. **Production data** adds the M07A guided input
workflow. Python owns all scheduling/optimization/verification and full domain validation.
**AI Predictions** adds actual experimental RF Physics, Forest12/Hist31 inference
and a Grouped Mean comparison baseline, independently of the selected planning dataset.

Use Node 22.12+, 24 or 26+ (verified with Node 26.13.0 / npm 11.20.0).
From the repository root:

```powershell
cd frontend
npm ci --ignore-scripts
npm run dev
```

Open **http://127.0.0.1:5173**. The explicit fixture preview needs no running
backend. Select **Capacity foundation** or **Competing orders**; each page labels
the synthetic source. No server catalog is assumed. The latter contains a saved
partial scheduling outcome, loaded only through **Load saved outcome**.
Capacity what-if, Routing trade-off and Parallel production are additional original
repository instances. They show inputs until actual API assessment/dispatch; no
saved capacity result is invented for them. The consolidated CSV is not an input.

For real local API reports, start the existing backend in a separate root terminal:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/m05a.txt -e .
$env:LOOMETRIC_API_TOKEN = (.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))")
.\.venv\Scripts\python.exe -m loometric.api
```

Use **Configure API** and privately copy that terminal session's environment value
into the password field. The default API origin is **http://127.0.0.1:8000**.
Use the existing local API startup/secret-management rules. No `VITE_*` token,
`.env` credential, proxy, remote host or browser storage is needed. Configure the
same token as the running server, without putting it in a command argument/URL.
**API & system → Clear session & use fixture preview** discards the token and
aborts requests. Reloading also discards the session. Health is a last checked
response, not continuous monitoring. Failed API requests never use a cached
capacity report as a substitute.

For **AI Predictions** (`/#/predictions`), first publish the trusted local models
from the root, using the existing locked ML/API environment and retained M08A/M08B
source artifacts:

```powershell
.venv/Scripts/python.exe -m loometric.experimental_ml publish --version v1
.venv/Scripts/python.exe -m loometric.experimental_ml_v2.publish
```

The v2 command also needs the retained, receipt-verified EXP-008 research artifact.
Follow the [complete preparation order and checks](../docs/architecture/experimental-ml-inference.md#reproducible-v2-artifact-preparation)
before either publication; skip a create-only command if its verified output already exists.
Existing output is never overwritten; inference never trains automatically. The
versioned independent registry pins its manifest receipt. Missing/incompatible
artifacts fail visibly instead of substituting a baseline or preview prediction.
Connect the API, review the guided thirteen-feature hypothetical pre-shift inputs
and confirm synthetic use. **RF Physics** is the default experimental research candidate;
choose **Compare all four models** to execute it alongside Random Forest,
HistGradientBoosting and the transparent Grouped Mean baseline. The candidate's
separate trusted v2 bundle must already exist; inference never creates it. See the
[v2 artifact and API contract](../docs/architecture/experimental-ml-inference.md#rf-physics-v2-integration-and-regression-repair).
The M08B **NO_ML_PROMOTION** decision
and failed subgroup gates remain visible beside actual results and validation errors.

Use **Use as scenario baseline**, change inputs and **Predict** again for actual
before/after results and input differences. No after value is assumed while the
request is pending. Edits abort/disown old requests and clear the current output;
session/context replacement, navigation or reload clears this page's research
state. Predictions never mutate the production workspace or invoke scheduling.
Zero capacity abstains, out-of-support conditions require review and valid values
above one remain unclipped. Descriptive residual bands are uncalibrated. The
target is synthetic standard capacity attainment, not guaranteed pieces or intrinsic
employee efficiency. Global forest importance describes training behavior, not
causation or an individual prediction. Read the [API and research contract](../docs/architecture/experimental-ml-inference.md).

The complete browser suite needs both trusted `v1` and `v2` artifacts; it does not
generate them or consume reserved-test labels. The test-only saved prediction
response fixtures were captured from the actual v1/v2 APIs and are never imported by the app.
M08C verification:162 frontend tests,12 real-backend browser workflows, strict
type/lint/build checks and zero npm audit findings. Complete Python regression:
1,202 passed. The desktop/mobile prediction/scenario/error screenshots remain
under ignored `.tmp/frontend/`; no production artifacts or credentials are bundled.

M09B finalization passed **183 frontend tests**, **12 real-backend browser workflows**
and **1,307 Python tests**, plus lint/type/build checks, on Windows/Edge. Details are in the
[inference guide](../docs/architecture/experimental-ml-inference.md#m09b-final-verification)
and the [EXP-008 integration addendum](../docs/experiments/EXP-008-ml-improvement-research.md#m09b-integration-addendum-2026-11-25).
V1 compatibility, candidate provenance, revoked experimental authorization, tampering,
training support consistency and create-only artifact preparation have permanent
regressions. RF Physics's 24.05% MAE reduction versus Forest12 and R² 0.82067 use
spent synthetic benchmark validation; independent validation remains pending.

For a user-defined input, open **Production data** (`/#/data`):

1. Start empty, edit a reusable template copy, or import a local schema-1 scheduling
   JSON file. Import replaces the draft only after preliminary checks and makes no
   API request. CSV inspection exports and capacity-only M02 files are unsupported.
2. Set explicit horizon/offset/assumptions. Add styles with exact worker-minutes per
   piece, orders with ordered stages, dedicated lines and crew qualifications,
   synthetic efficiency profiles, dated shifts/breaks and calendar assignments/stops.
   Reference dropdowns reuse declared entities. Add/edit/remove controls retain
   dependent records for explicit repair; nothing is silently inferred or deleted.
3. Review preliminary errors and counts. Save/cancel open forms before changing
   steps. Connect the local API and click **Validate with local Python**. The new
   bounded POST `/api/v1/scheduling/validate` uses the existing strict Python parser
   and returns its accepted fingerprint without dispatching or assessing capacity.
   Run the API from this checkout; restart an older running server to load the new route.
4. Click **Activate validated copy**, then open Scheduling and run the reference.
   The same input is available to Capacity, verified Gantt, reviewed M04 what-if
   comparisons and bounded scheduling/scenario jobs. Activation replaces the one
   user input and discards old local planning results/job IDs; server jobs may continue.
5. Use **Export scheduling JSON** to keep a local copy. Import/export preserve exact
   numeric tokens, including Decimal precision/trailing zeros and large counts.
   Files are strict UTF-8, at most 256 KiB, with bounded nesting/collections; the
   complete API envelope must fit too. Unsupported inputs reject without truncation.

**PYTHON VALIDATED** describes the complete input contract, not scheduling feasibility.
Frontend checks are preliminary, and offline export does not certify domain validity.
Any edit/import/replacement/dataset/session change invalidates the receipt; stale
replies cannot activate another draft. The original template files remain unchanged.
One draft and one active user input stay in tab memory; saved records survive page
navigation, while unsaved open forms reset on departure. Reload loses the draft,
active input, session and results. No database or automatic browser storage is used.
Read the [complete M07A fields, ownership and evidence](../docs/architecture/user-defined-production-workspace.md)
and [ADR 0017](../docs/decisions/0017-user-defined-synthetic-workspace.md).

For the reproducible interactive workflow:

1. Select **Capacity what-if** and connect the API. In **Production scheduling**,
   inspect the source/horizon/constraints, then **Run reference scheduling**.
2. Inspect the verified Gantt; activate a block by keyboard for exact operation
   details. The table and explicit unfinished-work panel show all demand.
3. Open **What-if scenarios**. Add `set workers` for LINE with worker count `3`.
   Review the exact fingerprint-bound specification, then run the reviewed greedy
   comparison. This synthetic example finishes 45 → 55 pieces.
4. For CP-SAT comparison, check the explicit job option, review its unchanged
   numeric budgets, then submit. Alternatively submit a bounded scheduling job
   from Scheduling. Jobs uses actual status/result/proof and producer selection.
5. Use **Pause local tracking**, **Resume / refresh status** or **Cancel server job**
   deliberately. Pause/navigation never cancels server work. Copy IDs before changing
   dataset/session: local receipts/results/drafts are discarded and jobs may continue.

The editor supports all existing worker/efficiency/availability, assignment and
downtime changes, with existing declared IDs/definitions only. It preserves ordered
edits and exact numeric tokens; Python validates the final atomic transaction.
Scenario mode/budgets and reviewed drafts survive navigation within one context.
Job POST is not idempotent, never auto-retried and can admit work before a lost reply.
Polling is sequential, ≥1 second apart, ≤60 status requests / 90 seconds per explicit
tracking session. Only explicit DELETE requests server cancellation. Receipts are
limited to eight in current tab/context; server retention/restart remain volatile.

**Routing trade-off**, X workers 1 → 2, demonstrates greedy regression 28 → 18;
bounded CP-SAT recovered 28 in the recorded workflow. Setting wall seconds to zero
is an explicit diagnostic: UNKNOWN retains verified greedy, never an invented
optimizer result. FEASIBLE and candidate proof remain separate from selected-plan
proof. Read the [complete contracts and measured evidence](../docs/architecture/interactive-planning-workspace.md).

```powershell
npm run typecheck
npm run check
npm test
npm run build
npm run test:browser
```

`check` runs Biome lint and formatting checks. `format` applies safe fixes.
The browser command owns a temporary loopback FastAPI process and Vite on **5173**,
uses an ephemeral token, runs headless Edge on Windows / Chromium elsewhere, and
closes its owned servers. Normally an occupied 5173 fails. To explicitly reuse this
repository's already-running local Vite without stopping it:

```powershell
$env:LOOMETRIC_TEST_REUSE_FRONTEND = "1"
npm run test:browser
Remove-Item Env:LOOMETRIC_TEST_REUSE_FRONTEND
```

The harness checks the served package and absolute workspace source-module path;
only its temporary API is owned/closed in reuse mode. It never reuses a user's API
or token. Python `.venv` needs the existing M05A pins, including OR-Tools for native jobs.
On Linux/macOS, install the Chromium browser once with `npx playwright install
chromium` and use `.venv/bin/python` for the backend. Browser dependencies/platforms
other than the recorded Windows/Edge environment have not been verified here.
Screenshots and transient browser evidence go to ignored `.tmp/frontend/`.
No credential-bearing traces, videos or automatic failure screenshots are enabled.

`npm run build` emits ignored `dist/`; `npm run preview` serves that local build
on the same fixed origin. Nothing is published. No dependency was added for M07A.
Actual M07A checks: 139 unit/component tests, 10 real-backend browser workflows, strict
type/lint/format/build, zero npm audit findings, 952 Python tests. Windows /
Edge is the verified browser environment; smoke checks are not WCAG certification.
The browser creates ten pieces with exact standard 2.5, two workers and efficiency
0.8, plus explicit breaks/downtime/unavailability: VALID_COMPLETE, ten finished,
16-minute makespan; a reviewed three-worker scenario gives 11 minutes, and the
bounded CP-SAT job returns a verified result. These are synthetic demonstrations.
M01 remains offline; persistent data, deployment, factory integration and M07B remain
separate work. The HTTP envelope remains 32 orders/96 operations/64 changes.
