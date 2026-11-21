# Loometric local dashboard

Read-only React/strict TypeScript workspace for the existing synthetic M02/M03A
inputs and M05A API. No Python calculation, scheduler or ML model is ported here.

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
closes both servers. Stop your development server first; an occupied 5173 fails
instead of reusing another process. Python `.venv` needs the existing M05A pins.
On Linux/macOS, install the Chromium browser once with `npx playwright install
chromium` and use `.venv/bin/python` for the backend. Browser dependencies/platforms
other than the recorded Windows/Edge environment have not been verified here.
Screenshots and transient browser evidence go to ignored `.tmp/frontend/`.
No credential-bearing traces, videos or automatic failure screenshots are enabled.

`npm run build` emits ignored `dist/`; `npm run preview` serves that local build
on the same fixed origin. Nothing is published. Scheduling, what-if interaction,
job submission, persistent data and live prediction remain outside M06A.
