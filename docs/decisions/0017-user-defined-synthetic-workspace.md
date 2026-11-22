# ADR 0017: User-defined synthetic inputs with explicit authoritative validation

Status: accepted for M07A before implementation.

Extend the existing React workspace with an in-memory, guided version-1 M02/M03
instance editor. Use native accessible forms, exact numeric text and the existing
lossless JSON codec. Generate only identity/version/unit metadata; require explicit
standards, crews, efficiency, capability evidence, dates, offsets and assumptions.
Templates copy existing synthetic instances without altering their source files.
Keep one editable draft and one immutable active user input, without persistence.

Frontend validation owns closed field shapes, scalar syntax, references, duplicate
IDs and conservative API envelope checks. It is preliminary. Python alone owns
complete domain validation, interval interactions, capacity and scheduling. Import
reads bounded local UTF-8 JSON without network requests. Unknown fields, CSV,
duplicate keys, unsupported versions and oversized inputs reject without repair.
Export contains only the closed synthetic instance, never session or job metadata.
Preserve numeric tokens, optional evidence and collection order in round trips.

Existing capacity validation accepts only M02; dispatch also schedules, and verify
requires a proposal. Add POST /api/v1/scheduling/validate with the existing closed
{instance} envelope. Reuse _instance, strict Decimal decoding, synthetic/order/stage
limits, admission and the existing hard guarded child. Return schema_version=1,
policy_version, synthetic=true, status=VALID_INPUT, instance_id and the existing
typed instance_fingerprint. No feasibility, metrics, schedule or optimality claim.
Document this contract and security/tests before implementation in the workspace
architecture guide. Existing routes/contracts and all domain algorithms stay frozen.

Bind successful validation to the exact serialized draft and current API session.
Any edit, import, replacement or session change invalidates that receipt and aborts
pending local validation. Ignore late replies. Activation copies the accepted input
into the existing dataset selection and clears earlier planning results/receipts.
Backend validation remains mandatory on every execution; a frontend receipt is no
server authorization token. Existing M04 fingerprint and M05B job safeguards apply.

Alternatives: duplicating Python intervals/capacity risks drift; running dispatch
as a validation button hides computation; browser storage adds unrequested retention.
Costs: explicit local API connection for authoritative validation and activation,
bounded inputs, lost drafts on reload and no durable or multi-user data history.
No new dependency, database, server storage, deployment or M07B work is introduced.
