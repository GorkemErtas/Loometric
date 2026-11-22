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

Acceptance checks declared before implementation: exact Decimal/fingerprint
equivalence, no dispatch side effect, valid input, closed envelopes, duplicates/references/date/quantity errors,
shift/break/profile/downtime/offset rules, synthetic-only enforcement, body/depth/
collection/order/stage limits, authentication/Host/origin checks and safe errors.
Frontend tests must also cover lossless local import/export, stale validation and
dataset/session isolation. A real-backend browser creates an input via forms,
validates, activates, dispatches and displays independently verified Gantt output.

## Guided workflow and fields

Open **Production data** (`/#/data`). Start empty or explicitly replace the draft
with an editable template copy. Template replacement has a discard confirmation;
import's file control explicitly states that it replaces the draft. Original
repository examples and fixtures remain unchanged. An empty input supplies only
metadata and empty collections; no standards, workers, efficiency, time bounds,
working dates, capabilities or planning assumptions are invented.

| Step | User-facing values | Contract and relationships |
| --- | --- | --- |
| Planning assumptions | Horizon start/end with seconds and explicit offset; fixed calendar UTC offset in integer minutes; synthetic assumptions, one per line | Positive horizon; offset -1439 through 1439; shift starts use that offset; every assumption is explicit canonical text |
| Product styles | Editable style name/ID; add/remove supported stages and exact standard worker-minutes per piece | `piece` output; each stage has one positive labor standard; no elapsed-time or machine-rate conversion |
| Production orders | Editable order ID, style dropdown, integer quantity and priority, release/due dates, ordered stages with append/earlier/later/remove | Quantity/priority positive; priority 1 highest; release ≤ due; no stage revisits; each stage needs a standard on the chosen style |
| Production lines | Editable line name/ID, stage dropdown, dedicated integer crew, explicit available/unavailable choice | Nonnegative workers; zero is valid zero capacity; no assumed transfers or shared crews |
| Line capabilities | Line/style/stage dropdowns; synthetic crew qualification basis | Exact line/style/stage match; no duplicate triple or inferred unrestricted qualification |
| Capacity profiles | Line dropdown, effective date, exact efficiency fraction, synthetic assumption source; optional synthetic evidence reference | Efficiency [0,1]; source required; evidence status fixed synthetic; profile must belong to the assigned line and be effective by shift start |
| Shifts and breaks | Editable shift name/ID; explicit start/end timestamps; add/remove positioned break start/end rows | Positive shift; minute grid; breaks contained and non-overlapping; an empty list explicitly means no breaks |
| Working dates | Add/remove individual dates | No recurring weekly calendar, holidays or daylight-saving inference; an overnight shift belongs to its local start date |
| Shift assignments | Existing line/shift/profile dropdowns | Profile choices restricted to the selected line; line ownership, effective date, working date and line overlap validated by Python |
| Planned downtime | Existing assignment dropdown, explicit start/end timestamps and reason | Entire stop inside the assigned shift; no automatic deletion when its assignment is removed |
| Unavailable periods | Existing line dropdown, explicit start/end timestamps and reason | Line-wide exclusions may span shifts; interval/capacity interactions belong to Python |
| Review | Counts, preliminary issues, validation status, accepted fingerprint/request ID, optional exact JSON | Explicit Validate, Activate, scheduling/capacity navigation and export; no feasibility or optimizer proof inferred from validation |

Supported stages remain cutting, sewing, finishing, quality_control and packing.
Dates are `YYYY-MM-DD`; timestamps such as `2030-01-07T08:00:00+03:00` retain their
explicit offsets. All scheduling boundaries align to whole UTC minutes. Due dates
are soft scheduling deadlines at the following local midnight; capacity assessment
keeps its existing conservative whole-slot semantics. Complete batches occupy one
uninterrupted compatible working fragment, with no preemption, splitting or rework.

New instance/scenario/calendar identities are generated; new order/style/line/shift
names are suggested and editable. Profile, qualification, assignment and stop IDs
are generated and checked for collection uniqueness. Dropdown descriptions include
production references so users do not repeatedly type technical IDs. Schema 1,
`whole-stage-minute-v1`, one-minute allocation, output/standard units and synthetic
evidence status are system metadata. Existing imported IDs/versions/optional evidence
are preserved; import never relabels real data as synthetic. `record_id`,
`json_pointer`, `source_sha256`, benchmark fields and credentials are not form fields
and are rejected as extra input properties.

The eight steps keep entity forms separate. Lists have add/edit/remove controls;
style standards and break rows are repeatable, and routes have ordering controls.
Open forms require Save or Cancel before changing steps or replacing the draft.
Leaving the page discards unsaved form fields; saved draft records and the selected
step survive navigation. Removal and renaming retain dependent records, expose
reference errors and require explicit repair. Nothing cascades or silently repairs.
Summary errors disable export/validation until preliminary issues are resolved.

## Validation ownership and immutable activation

`frontend/src/domain/production.ts` owns bounded decoding, closed field shapes,
version/unit checks, exact scalar syntax, date validity, duplicate IDs/stages,
reference/qualification checks and simple date ordering. Checks are preliminary,
with at most 100 displayed issues. They do not implement processing durations,
interval unions, break/assignment overlaps, capacity, feasibility or a scheduler.
For example, a structurally valid break outside its shift may enter a draft;
Python rejects it with BREAK_OUTSIDE_SHIFT. The explicit validation status remains
**NOT AUTHORITATIVELY VALIDATED** until a successful API response is accepted.

The production state provider owns one saved draft and a validation receipt bound
to its exact serialized content, selected dataset and API session. Any edit,
replacement, import or dataset/session change invalidates that receipt and aborts
pending local validation. Late replies and delayed activation hashes cannot populate
a new context. A synchronous lock prevents duplicate validation/activation. A context
change resets that lock and hides prior receipts immediately, allowing revalidation.
Only allowlisted static domain-code guidance reaches the form; raw native exception
messages, arbitrary keys, submitted values and paths never become error messages.

Activate makes an independent copy with a new client selection key. The existing
workspace retains at most one user dataset, alongside the original catalog; later
activation replaces that user entry. Selecting it triggers the existing local capacity
assessment. Dispatch must return the fingerprint accepted during validation before
its report is accepted. The source-text SHA-256 over compact UTF-8 JSON (without
the export's final LF) is separately labeled and never substitutes for Python's
typed instance fingerprint.

Existing dataset/session-keyed M06B state then supplies greedy scheduling, verified
Gantt, all eight M04 change types, comparisons and bounded scheduling/scenario jobs.
Changing active input clears previous reference/review/comparison/receipts and
aborts local requests, without implicitly cancelling server jobs. The same API
limits, atomic transformation validation, fingerprint binding, independent verifier,
producer/proof distinctions, eight-receipt cap and bounded polling/cancel behavior
remain in force. Every backend execution validates again; a frontend receipt is
neither a server credential nor permission to bypass validation.

## Local import/export and security

Import checks file size **before reading**, then uses fatal UTF-8 decoding and the
existing lossless parser. Duplicate JSON keys, unknown/missing fields, unsupported
versions/units, invalid scalars/references, oversized files/collections/nodes and
excessive nesting reject. The complete `{instance}` request must fit the byte and
depth limits, not just the bare file. Published smaller order/operation/body and
structural limits are respected. Inputs are rejected intact, never truncated or
silently simplified. CSV inspection exports and M02 capacity-only JSON are not M03
scheduling instances. A rejected import preserves the existing draft.

Import performs **no upload, HTTP request, server filesystem access or URL fetch**. Only explicit
Validate sends the complete input to the configured authenticated loopback API.
An imported draft still needs authoritative validation before activation. Offline
export is allowed after preliminary checks; it does not imply calendar validity or
scheduling feasibility and includes no validation assertion in the instance schema.

Export downloads `loometric-synthetic-instance.json` containing only the closed
instance and a final LF. Repeated serialization of the same input is deterministic.
JSON whitespace is normalized; property/collection order, IDs, optional evidence
presence/null and numeric lexemes are retained. Decimal input is an unquoted JSON
number, never a binary-float conversion or rounded display value. For example,
`0.1234567890123456789012345678`, explicit trailing zeros and supported exponent
tokens survive import/export. Counts beyond JavaScript's safe integer range also
survive; backend solver/model bounds still apply separately.

The export code receives the draft only. API origins/tokens, validation receipts,
request IDs, jobs, reports and file paths are outside its schema. Bearer secrets
remain in the existing private tab client, without browser/server persistence,
analytics or logs. Free-text production assumptions are user supplied; the editor
does not request credentials or fetch evidence links. Reload loses saved draft,
active user copy, session and results. No database, server file store, cloud or
production-system connection is introduced.

## Executed evidence and reproduction

Verified 2026-11-22 on Windows with the existing Python 3.13.14, Node 26.13.0 /
npm 11.20.0 and headless system Edge. No dependency was added or upgraded.

The browser test constructs a new input exclusively through the forms:

- Style TEE-USER; ORDER-USER: 10 pieces, priority 1, sewing, release/due 2030-01-07.
- SEW-USER: two workers, explicit qualified capability, assumed efficiency
  `0.8000000000000000000000000000`, standard `2.5000000000000000000000000000`.
- Horizon/shift 08:00–09:00 +03:00; explicit working date, profile and assignment.
- Five-minute break 08:20–08:25, downtime 08:40–08:45 and line unavailability
  08:50–08:55, leaving 45 available elapsed minutes / 90 worker-minutes /
  72 effective standard worker-minutes in the unchanged Python assessment.

Actual greedy result: **VALID_COMPLETE, 10 finished / 0 unfinished, 16-minute
makespan**, allocation 08:00–08:16 +03:00 (reported UTC 05:00–05:16). Changing the
crew to three in a reviewed same-demand what-if gives 11-minute makespan and BETTER
under the frozen objective hierarchy, while finished quantity remains ten. A real
bounded CP-SAT scheduling job returns an independently verified result. These small
synthetic outcomes are not factory performance or a scalability claim. Generated
identity UUIDs/request IDs/job IDs vary; the exported input reproduces its own exact
fingerprint and results. Runtime/solver ties are not cross-machine guarantees.

The new browser cases additionally prove exact file round trips, offline import
with zero API calls, CSV/oversize rejection preserving the draft, no token in export,
no browser storage and accessible responsive review at 1440×1050, 820×1100 and
390×844. Four screenshots under ignored `.tmp/frontend/m07a-*` and the user-created
input under `.tmp/m07a/` are local evidence only, not versioned artifacts.

Focused contract tests cover valid catalog inputs, Decimal/exponent/trailing-zero
tokens, large counts, optional evidence, duplicates, malformed/unknown references,
quantities/dates/units/provenance, unsupported schema, bounds and invalid UTF-8.
Component tests cover copied forms, duplicate rejection, explicit dependent-record
repair, single submission, immutable activation, late validation, session/dataset
isolation, allowlisted domain errors, rejected authentication and interrupted-hash
recovery. Fault injection tests are controlled ownership checks, not native solver
measurements. Existing Python tests cover complete interval/capacity algorithms.

| Executed check | Final result |
| --- | --- |
| Frontend strict TypeScript | Pass, included in production build |
| Biome lint/format | Pass, 55 files, no findings |
| Vitest | 139 passed, 6 files, 19.56s |
| Production build | Pass, 65 modules; JS 458.67 kB / 121.63 gzip; CSS 29.65 / 6.87 kB |
| Real API / Edge browser suite | 10 passed, 1.0 min; includes all eight preserved M06A/M06B cases |
| Focused Python API suite | 129 passed, 83.69s |
| Complete Python regression | 952 passed, 152.81s |
| Ruff lint/format and pip check | Pass; no broken requirements |
| Dependency preservation | All 39 existing Python pins and 17 direct frontend versions unchanged |
| npm vulnerability audit | Zero findings |

The READMEs and ignored local roadmap also record these results. No aborted or
failed verification run is represented as passing.

Initial corrected failures included sandbox worker/cache permissions, status-text
contrast, an implicit select label and routine lint/typing/spacing. One browser run
overlapped a source edit; the unchanged-source rerun passed. An initial full pytest
run put `--basetemp` under `.tmp`, inadvertently changing a benchmark output-boundary
test into full benchmark execution. Its owned process tree was stopped, and the
normal-temp full regression passed **952 tests in 152.81s**. A delayed-hash test
exposed blocked revalidation after a context change; a lock reset plus synchronous
receipt ownership mask corrected it. These failures remain explicit evidence.

Run the [frontend verification commands](../../frontend/README.md) and root
`.venv/Scripts/python.exe -m pytest -q`. Keep pytest's default temporary directory
for the existing benchmark output-boundary tests. The browser harness owns and
closes temporary local servers and discards its ephemeral token; its existing
explicit frontend-reuse option remains available.

## Remaining limitations and M07A boundary

One draft and one active user input are memory-only. Export before reload; there is
no autosave, durable history, undo/redo or multi-user isolation. Unsaved open-form
fields reset on page departure. Dates/times use explicit fixed offsets and minute
boundaries, without recurring shifts, holiday generation or daylight-saving rules.
Full calendar validation requires the local API; offline checks and export cannot
assert domain validity. Unsupported sizes and solver resource stops stay explicit.
The existing whole-batch constraints and API limits remain unchanged. Linux/macOS
and other browsers were not verified. Accessibility checks cover tested states,
not WCAG certification. No database, deployment, factory data, ML serving, new
optimization algorithm, frozen domain changes or M07B work is included.
