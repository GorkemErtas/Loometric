# M07A: User-defined production data workspace

This local-only workflow constructs explicitly SYNTHETIC version-1 M02/M03 inputs.
It preserves [M02](production-planning-domain.md), [whole-stage-minute-v1](scheduling-contract.md),
[M04](what-if-scenario-engine.md) and [M05B](optimization-jobs-api.md).
See [ADR 0017](../decisions/0017-user-defined-synthetic-workspace.md).

## Validation endpoint contract (declared before implementation)

POST `/api/v1/scheduling/validate` accepts exactly `{"instance": <M03 instance>}`,
the same closed envelope as dispatch. Successful HTTP 200 uses the existing
`{api_version, request_id, data}` wrapper. Data contains exactly:

- `schema_version`: 1; `policy_version`: `whole-stage-minute-v1`.
- `synthetic`: true; `status`: `VALID_INPUT`.
- `instance_id`: the accepted ID; `instance_fingerprint`: existing Python typed SHA-256.

VALID_INPUT means the complete synthetic domain contract was parsed and validated;
it does not assess capacity, feasibility or optimality. No scheduler, optimizer,
report metrics or job admission runs. Existing parser/_instance functions own all
domain rules; the HTTP adapter introduces no production schema change.

The existing loopback peer/Host, Bearer authentication, explicit local CORS, strict
JSON content type, no compression, no-store, safe error and correlation-ID policies
apply unchanged. No paths, URLs, executable settings, tokens or uploaded files are
accepted. The guarded worker owns parsing and fingerprinting: two admitted POSTs,
3s body deadline, 5s child watchdog, 256 MiB memory, 2 MiB response ceiling.
Existing ceilings remain 256 KiB request, depth 24, 10,000 nodes, 256 items per
collection, 4,096 characters/string, 128 numeric digits, Decimal exponent magnitude
100, 32 orders and 96 required stages. Smaller configured limits still apply.
Reject rather than truncate. Invalid envelope/domain/synthetic inputs use the
existing 400/413/422 categories; saturation/resource failures retain 429/503/504.
Domain failures expose safe codes only, never submitted values or exception text.

Planned acceptance tests: exact Decimal/fingerprint equivalence, no dispatch side
effect, valid input, closed envelopes, duplicates/references/date/quantity errors,
shift/break/profile/downtime/offset rules, synthetic-only enforcement, body/depth/
collection/order/stage limits, authentication/Host/origin checks and safe errors.
Frontend tests must also cover lossless local import/export, stale validation and
dataset/session isolation. A real-backend browser creates an input via forms,
validates, activates, dispatches and displays independently verified Gantt output.

Implementation fields, workflow evidence and limitations will be recorded after
execution; no unexecuted check is claimed as passed.
