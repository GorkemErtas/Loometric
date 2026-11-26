# ADR 0028: Explicit same-origin HTTPS demo gateway

Status: accepted for deployment preparation, 2026-11-26. No public service launched.

## Context and options

The portfolio needs a production frontend build and a concrete hosting path.
The API currently binds loopback, checks literal local Host/Origin and requires
an in-memory Bearer session. Scheduling and prediction budgets and volatile
registries assume one backend worker. Frozen model environments are platform-bound.

Options considered: retain only the local demo; add an explicit HTTPS gateway
with an exact configured origin; or expose the backend directly and broaden CORS.
Choose the gateway template while keeping the local default. Direct public API
exposure and wildcard trust are unnecessary for this single-user demonstration.

## Decision

Provide a Caddy static-SPA/API template. Only `frontend/dist` is a static root;
`/api/*` proxies to 127.0.0.1:8000. `LOOMETRIC_PUBLIC_ORIGIN` is optional, canonical
HTTPS and exact. When configured, the API admits that additional Host/Origin
only from a direct loopback peer. Forwarded client/host headers do not establish
trust; Uvicorn retains `proxy_headers=False`. Bearer validation, request bounds,
native hard limits and one inference slot remain unchanged.

The frontend permits the current HTTPS page origin in addition to its existing
HTTP loopback development origins. It never embeds credentials or saves them
in browser storage. Package dependencies remain unchanged; Caddy is an optional
operator-provided gateway, not an installed service or automatic deployment.

## Consequences and validation boundary

Keep one backend worker and protect the shared demo token outside Git. Restarts
clear volatile jobs/drafts. This is not a multi-tenant production service.
Matching Windows model environments/receipts are required; Linux container
portability was not verified. Validate the template with the chosen hostname,
filesystem path and Caddy version before any separately authorized deployment.
Caddy was unavailable locally, so TLS provisioning/runtime is not claimed.
Default and opt-in HTTP security boundaries have regression tests; production
frontend build and real-backend browser checks cover application behavior.

See [deployment instructions](../deployment.md). All ML remains synthetic,
experimental and **NO_ML_PROMOTION**, including when hosted behind a gateway.
