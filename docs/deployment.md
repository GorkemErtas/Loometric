# Portfolio demo and deployment preparation

The verified application stays local by default. No external service has been
published. Keep one API worker: scenarios/jobs/sessions are memory-only, so a
restart clears them and multiple workers would not share their registries.
Models remain experimental, synthetic and NO_ML_PROMOTION.

## Local production-build demo

Use the locked Python environment and artifact instructions in README. Never
train automatically during API startup or inference. Model bundles are ignored
and must be prepared independently with trusted receipts.

```powershell
# Terminal 1, repository root; token is generated per session and never saved in Git.
$env:LOOMETRIC_API_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -m loometric.api

# Terminal 2
cd frontend
npm ci --ignore-scripts
npm run build
npm run preview
```

Open http://127.0.0.1:5173, configure http://127.0.0.1:8000 and enter the session
token. Export a synthetic scenario to retain it across restarts. Do not export
credentials; the browser keeps them in memory and clears them with its session.

## Optional HTTPS gateway configuration

The provided [Caddyfile](../deployment/Caddyfile) prepares an explicit same-host
HTTPS gateway: static files come only from `frontend/dist`; `/api/*` proxies to
127.0.0.1:8000. The API remains bound to loopback, checks Bearer credentials and
ignores forwarded peer headers. Public origin trust is opt-in and exact; it does
not allow arbitrary remote API origins or relax resource limits.

After choosing a real hostname and separately authorizing its deployment, set
the same canonical HTTPS origin in the API and gateway terminals:

```powershell
$env:LOOMETRIC_PUBLIC_ORIGIN = "https://your-demo.example"
$env:LOOMETRIC_FRONTEND_DIST = (Resolve-Path frontend/dist).Path.Replace('\', '/')
# Keep the existing API token in the API terminal; restart that one worker with
# LOOMETRIC_PUBLIC_ORIGIN set there too.
caddy validate --config deployment/Caddyfile --adapter caddyfile
caddy run --config deployment/Caddyfile --adapter caddyfile
```

Use the current HTTPS site origin in Configure API. The frontend accepts that
exact origin; HTTP loopback development remains supported. Wrong Host, remote
direct peer, unapproved Origin and malformed configuration remain rejected.
No wildcard CORS, proxy-header trust, embedded token or automatic training is added.

The template follows Caddy's official
[SPA/API pattern](https://caddyserver.com/docs/caddyfile/patterns#single-page-apps-spas)
and [reverse-proxy documentation](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
Serving a domain requires its own DNS, reachable gateway and TLS configuration;
none was provisioned by this task. Never serve the repository root, data folders,
local journals or model binaries as static files.

## Runtime and operating limits

Existing frozen artifacts bind their exact Python/library/platform environment.
The complete five-model demo targets the validated Windows environment; Linux
container portability of those Windows receipts has not been established. A
different environment fails closed rather than silently refitting or accepting
incompatible executable artifacts. There is no claim that an untested container
can load the existing bundles.

Prediction requests retain the existing 768 MiB / 10 second isolated worker,
single numeric thread, one inference slot, 8 KiB input and 128 KiB output limits.
Scheduling/job resource controls are unchanged. Keep the locked dependency files,
verify artifact receipts before startup and expose only the gateway, never the
backend directly. Protect the shared demonstration token outside the repository;
this is a single-user portfolio deployment, not a multi-tenant production service.
