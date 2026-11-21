# ADR 0016: Interactive planning, verified rendering and bounded job tracking

Status: accepted for M06B before interactive workflow implementation.

Extend the existing React client and exact adapters, with no backend or dependency
changes. Keep all M01–M05B engines, schemas, constraints, objectives and limits frozen.
Use the original synthetic instance text. A successful real reference dispatch
supplies the authoritative instance fingerprint; the frontend does not recreate
Python's typed canonical hash. Scenario review requires that fingerprint and an
immutable ordered M04 request with explicit synthetic provenance and solver budgets.

Client validation covers form syntax, existing identifier choices, duplicate edit
keys and the published HTTP envelope. Python remains authoritative for complete
atomic validation, calendar/capacity arithmetic, feasibility, selection and deltas.
Do not apply hypothetical changes to the source baseline or silently repair errors.
Display source timestamps/offsets unchanged; Date arithmetic is used only for Gantt
positions and elapsed duration from reported endpoints, never scheduling decisions.
Render allocations only with independent verification; provide keyboard details and
a structured table, explicit missing work and separate producer/proof evidence.

Add a small planning context scoped to the selected dataset and authenticated API
client, retaining reference results, draft/review, comparisons and at most eight job
receipts in memory across page navigation. Dataset/session changes discard this
local context. Explain before submission/selection that server jobs may continue;
copyable IDs are not credentials. No persistence, job-list or recovery endpoint is
invented. A lost POST reply can represent admitted work: never retry POST automatically.

Poll only while the jobs view is mounted and the selected receipt belongs to this
context. One request at a time, at least one second between polls, maximum 60 polls
or 90 seconds per explicit tracking session; resume is a user action. Honor readable
Retry-After guidance without polling earlier; pause if it exceeds the remaining
tracking budget. Existing cross-origin CORS exposes only X-Request-ID, so unreadable
Retry-After uses the documented one-second guidance, without changing the backend.
Stop on unmount, context change, auth failure, terminal status or local budget.
Only explicit DELETE cancels server work. Suspend polling during cancellation;
display the server's actual race outcome, including an already published success.
No progress percentage, automatic parameter alteration or inferred solver proof.

Alternatives: browser storage would retain secrets/results unexpectedly; a global
state framework or durable queue exceeds this local milestone; embedding Python
business rules risks contract drift; automatic POST retry risks duplicate jobs.
The selected design is bounded and explicit, with the cost that changing the
dataset/session can lose local job IDs and no server enumeration/restart recovery
is available. Retention/UNKNOWN/fallback/resource stops remain distinct from
infeasibility or production performance. M07 and deployment remain separate work.

The browser harness still owns its temporary API and normally owns Vite. An explicit
LOOMETRIC_TEST_REUSE_FRONTEND=1 option may use an existing local Vite only after
checking the workspace package and exact absolute source-module path. It never
stops or claims ownership of that frontend. This supports an active development
session on the fixed CORS port without changing origins or killing a user's process.
