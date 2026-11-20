# ADR 0013: Local API boundary and bounded synchronous execution

Status: accepted for M05A, before HTTP implementation and fixture execution.

Expose existing M02 capacity, M03A dispatch/independent verification and M04 greedy
comparison through an optional `loometric.api` package and `/api/v1`. Domain modules
remain independent of HTTP. Reuse strict parsers, fingerprint checks and serializers;
Pydantic validates closed outer envelopes, without duplicating the domain schemas.
Decode JSON with the existing duplicate-key/Decimal parser, under a hard child guard.
Re-encode Decimal as exact numeric tokens for existing parsers, never binary floats.

Use explicit loopback binding, peer/Host checks, restricted local CORS and a configured
shared Bearer secret. This is local development authorization, not public hosting or
multi-user identity. No server-supplied filesystem paths or artifact loading. Public
health and local OpenAPI are process metadata only. Other endpoints require auth.
Server-generated correlation IDs and sanitized error envelopes replace exception text.

Declare limits in packaged `default_limits.json`: 256 KiB body, depth24, 10,000 nodes,
256 items per collection, 4,096 characters per string, 128 significant numeric digits,
Decimal exponent magnitude100, 32 orders/96 stages per instance, 64 changes.
Accept at most2 MiB of encoded child response, bounding parent-side report handling.
Allow two admitted POST requests, including body reading; 3 seconds to read a body, then
5 seconds for the entire child and 256 MiB hard memory per child. Bounds may only be
reduced through trusted application construction, never raised by HTTP callers.

Run parsing and engines in the existing M03C/M04 process guard via a worker thread.
The event loop stays available. The process watchdog actually kills and reaps the
child (and Windows launcher) before returning a504. A disconnect is not immediate
CPU cancellation: work may finish or hit that same deadline; retain the slot until
cleanup. Cancellation shielding avoids abandoning threads and admitting extra work.
No background jobs, queues, persistence or process pool are added. Native CP-SAT
API requests are rejected; M05B needs separately designed job lifecycle/admission,
ownership, cancellation, result retention and recovery, without changing objectives.

Defer M01 prediction: arbitrary artifact paths/digests, trusted pickle loading and
evidence/review/replay policy cannot safely be converted into generic request fields.
No configured trusted model registry exists. Keep M01 offline and its safety contract
unchanged. Do not import ML or access training/validation/final-test data in this API.

Alternatives: inline engines block the event loop; a timeout around a thread leaves
CPU work running; duplicating domain models risks changed Decimal/policy semantics.
Full async job infrastructure exceeds this milestone. Startup overhead and bounded
synthetic sizes are deliberate costs; resource rejection is not infeasibility proof.
Independent verification returns200 for a well-formed but invalid proposal, with
status INVALID and no metrics; valid partial plans remain VALID_PARTIAL.
