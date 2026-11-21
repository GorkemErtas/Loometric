# Loometric local dashboard

React/strict TypeScript local workspace for synthetic M02–M04 inputs and the existing
M05A/M05B APIs. Five inspection pages are joined by Production scheduling, What-if
scenarios and Optimization jobs. Python owns all scheduling/optimization/verification.

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
on the same fixed origin. Nothing is published. No dependency was added for M06B.
Actual checks: 87 unit/component tests, 8 real-backend browser workflows, strict
type/lint/format/build, zero npm audit findings, 940 preserved Python tests. Windows /
Edge is the verified browser environment; smoke checks are not WCAG certification.
M01 remains offline; persistent data, deployment, factory integration and M07 remain
separate work. The HTTP envelope remains 32 orders/96 operations/64 changes.
