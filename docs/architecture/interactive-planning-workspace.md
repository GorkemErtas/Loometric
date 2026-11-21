# M06B: Interactive scheduling and what-if workspace

M06B extends the [M06A dashboard](frontend-foundation.md) with three local planning
views. All inputs and results remain **SYNTHETIC**. It consumes the unchanged
[M05A endpoints](api-foundation.md) and [M05B bounded jobs](optimization-jobs-api.md).
No Python scheduling, optimization, capacity, verification or selection algorithm
is ported to TypeScript. See [ADR 0016](../decisions/0016-interactive-planning-and-job-tracking.md).
M01 remains offline; no database, deployment, public authentication, factory system
or ML-to-capacity coupling is introduced. M07 is not implemented.

## Workflows and navigation

The existing Overview, Orders, Production resources, Capacity and API & system
views retain their inspection behavior. New routes are:

| View / route | Workflow |
| --- | --- |
| Production scheduling `/#/scheduling` | Inspect the frozen instance, horizon, order/stage count, constraints and source; run reference dispatch; inspect verified Gantt/unfinished demand; submit the same instance to a bounded scheduling job |
| What-if scenarios `/#/scenarios` | Build an ordered supported change list, declare provenance/budgets, review exact JSON, then run a greedy comparison or submit a CP-SAT comparison job |
| Optimization jobs `/#/jobs` | Inspect local receipts, sequentially poll selected work, explicitly cancel, retrieve and inspect verified results, producer selection and native proof |

Interactive execution requires a configured local API session and an executable
M03/M04 instance. Fixture preview never starts a scheduler/job. The M02 capacity
input and consolidated inspection CSV are not executable scheduling contracts.
Inputs above the HTTP envelope are explicitly unsupported and never truncated:
at most 32 orders, 96 required operations, 64 changes and 256 KiB per request.
The client also respects smaller reported order/operation limits. Larger M03C
benchmark instances are outside that envelope; no benchmark generation is invoked.

The catalog imports the original text of these existing files, without editing
them or inventing a server catalog:

| Selection | Original source | Preview behavior |
| --- | --- | --- |
| Capacity foundation | [M02 demo](../../examples/planning/capacity-demo.json) | Existing saved capacity report; capacity-only |
| Competing orders | [M03A competition](../../examples/scheduling/competition.json) | Existing capacity/saved-verification preview; executable instance |
| Capacity what-if | [M04 capacity baseline](../../examples/scenarios/capacity-baseline.json) | Input-only until real API assessment/dispatch |
| Routing trade-off | [M04 routing baseline](../../examples/scenarios/routing-baseline.json) | Input-only until real API assessment/dispatch |
| Parallel production | [M03A parallel routing](../../examples/scheduling/parallel-routing.json) | Input-only until real API assessment/dispatch |

## State ownership and architecture

| Boundary under `frontend/src/` | Responsibility |
| --- | --- |
| Existing `state/Workspace.tsx` | Memory-only API client/session epoch, selected source, existing capacity and saved verification |
| `state/PlanningWorkspace.tsx` | Dataset/session-scoped reference, ordered draft/review, comparison and at most eight local job receipts; request lock and abort ownership |
| `pages/Jobs.tsx` tracker | One selected receipt's mounted polling/cancellation lifecycle; cleanup never sends an implicit DELETE |
| `domain/planning.ts` | Typed dispatch/evaluation/comparison/job adapters, metric units, identity and proof consistency checks |
| `domain/scenario.ts` | Exact form tokens, explicit existing-reference choices, conflict keys and immutable M04 request construction |
| `domain/jobs.ts` | Bounded tracking policy and monotonic receipt reconciliation |
| `domain/gantt.ts` | Timestamp geometry and projection of approved audit records into calendar annotations |
| `api/client.ts` | Existing exact loopback transport extended with dispatch/compare/job methods and safe job error categories |
| `components/Gantt.tsx`, `PlanningResults.tsx`, `ComparisonView.tsx` | Reused verified allocations, metric/delta/proof presentation and accessible table alternatives |

No new dependency, state framework, router, chart package or backend schema is
needed. The existing 17 exact direct runtime/dev package versions and lockfile are
unchanged. A planning context is keyed by dataset/session epoch and survives page
navigation. Appended changes, provenance, solver mode/budgets, reviewed request,
reference and receipts persist within that context. Transient unsubmitted edit
form fields reset on page remount. Dataset/session change or reload discards the
context; notices explain that server work may continue and IDs should be copied.

Every request is owned by its context. Unmount/session reset aborts the browser
request and late replies cannot populate a new context. A shared synchronous lock
prevents repeated-click duplicate dispatch/comparison/job submissions. The bounded
receipt registry checks response order before React state updates, preventing late
polls from undoing terminal results or cancellation. Forgetting a terminal receipt
releases its local metadata; it does not delete a server record.

## API mapping, identity and exact values

All paths below start `/api/v1`; only existing endpoints are called.

| Method / path | Exact envelope / use |
| --- | --- |
| POST `/scheduling/dispatch` | `{instance}`; returns actual verified reference and authoritative typed-instance fingerprint |
| POST `/scenarios/compare` | `{baseline, specification}` with explicit `greedy` method |
| POST `/jobs/scheduling` | `{instance}`; server-fixed seed 42, worker 1, wall 1 s / deterministic 1 per phase |
| POST `/jobs/scenarios` | `{baseline, specification}` with reviewed explicit CP-SAT configuration |
| GET `/jobs/{id}` | Actual status/phase and volatile retention metadata |
| GET `/jobs/{id}/result` | Verified report after SUCCEEDED/result-available metadata |
| DELETE `/jobs/{id}` | Explicit cancellation only; actual 200/202 race outcome retained |

The existing health, capabilities, capacity and proposal-verification calls remain.
No job-list, progress, recovery, prediction, upload or new optimization route is
invented. Job IDs must be 32 lowercase hexadecimal characters. Returned relative
URLs must match the known local paths; the client does not follow arbitrary URLs.

Run real reference scheduling first. Its response fingerprint binds the editor
and subsequent jobs to the exact instance; JavaScript never recreates Python's
typed canonical hash. Result IDs, baseline/scenario fingerprints, same-demand and
specification fingerprints and actual request IDs stay explicit. Cross-instance
results, contradictory terminal states, proof without an incumbent and unbound
candidate metrics are rejected. Source-file identities continue to use explicitly
labeled LF-normalized text SHA-256; those are distinct from typed-instance hashes.

Existing lossless JSON parsing/encoding preserves planning Decimal **numeric
tokens** and integer precision. Report Decimals and signed deltas remain strings;
BigInt is used only for exact presentation. No planning value passes through
JavaScript Number. Date/Number operations are limited to timestamp layout/duration,
HTTP retry metadata and client timers. Raw timestamps and offsets remain visible.
Unknown versions, altered units, missing fields and invalid numeric syntax fail.

Bearer secrets remain private tab memory, never storage, URL, build environment,
analytics or logs. Only the configured literal loopback origin is used, with the
existing CORS policy and no proxy. Authentication failure stops tracking and clears
the configured client/session. Fixed safe messages and allowed public categories
replace raw native errors. Existing body/depth/response bounds and 12-second client
request deadline remain. Vite's filesystem allowlist adds only the existing
synthetic `examples/scenarios/` directory; protected datasets/artifacts stay outside.

## Verified Gantt semantics

Only independently verified allocations are drawn. An invalid proposal receives
no Gantt or performance metrics. Rows identify production lines; horizontal
positions represent absolute time within the exact reported horizon. Blocks retain
order/stage, full quantity, line/assignment/shift/profile and exact source endpoints.
Elapsed duration is the difference between reported minute-grid endpoints, not a
new processing-time calculation. No block is dragged, rescheduled or widened to
improve appearance; all required work remains allocated or explicitly unscheduled.

Declared shifts, breaks, downtime and unavailable intervals are input annotations,
not inferred machine availability or free capacity. Scenario annotations copy the
backend's approved assignment/downtime audit edits; they do not recompute interval
unions, capacity or feasibility. Calendar bands are intersected with the displayed
horizon; source endpoints remain intact. Allocation results themselves are unchanged.

Blocks are keyboard buttons opening native detail dialogs, with focus returned to
the opener. A named, keyboard-scrollable structured operation table provides exact
times, quantity and duration. The completion table distinguishes COMPLETED, PARTIAL
and UNSCHEDULED orders, with a separate explicit unscheduled-stage/reason panel.
Partial upstream allocations are not finished goods. Zero allocations remain an
explicit partial result, rather than an invented empty success.

## Guided scenario editor

The editor supports precisely the existing M04 operations:

- `set_workers`, `set_efficiency`, `set_availability` target existing lines/profiles.
- `add_assignment` references existing line, profile and shift definitions; a new
  assignment ID is explicit. `remove_assignment` targets an existing assignment.
- `add_downtime`, `replace_downtime`, `remove_downtime` use complete explicit records
  and offset timestamps, referencing baseline or explicitly added assignments.

No line, shift definition, standard, capability or qualification is invented.
Numbers remain editable exact text; invalid values are rejected, never clamped.
Ordered edits can be removed/moved before review. Repeated edits to the same entity
field conflict; assignment/downtime lifecycle operations share their respective
conflict keys. Different worker/availability fields on one line remain distinct.
Removing an assignment does not silently remove its downtime. Python alone validates
the complete final atomic transaction, profile dates, intervals and references.

Scenario ID/label, synthetic source and a canonical assumption entry are explicit.
Review displays the full version-1 M04 JSON, authoritative baseline binding and
ordered changes. Changing draft/provenance/budgets invalidates review and prior
comparison. Reviewed requests are submitted unchanged, without mutating baseline
objects/files. Greedy comparisons use the synchronous endpoint. CP-SAT comparisons
explicitly include seed 42, worker 1, benchmark mode and wall/deterministic budgets
in [0,1] per phase. Zero wall is an intentional no-search diagnostic. Existing
M04 omitted defaults are not rewritten; unsupported budgets are rejected.

## Bounded job lifecycle

Server states QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED and EXPIRED are shown
directly, together with genuinely observed phase/timestamps. There is no percentage
progress. SUCCEEDED means an accepted report completed, not that CP-SAT won or proved
optimal. Missing/expired IDs/results, queue saturation, authentication, deadlines,
worker/resource failures and incomplete reports have explicit error states.

Tracking runs only for the selected receipt while the Jobs view is mounted:
one request at a time, at least one second between status polls, at most 60 status
requests and a 90-second wall deadline that also aborts an in-flight browser request.
Readable Retry-After seconds/dates are honored; guidance beyond the remaining local
budget pauses tracking. The unchanged cross-origin CORS exposes only X-Request-ID,
so Retry-After is not browser-readable there; the documented one-second default is
used. GET busy responses can retry within those bounds; POST never retries itself.
Resume/refresh is an explicit new tracking session. Terminal status stops polling;
a successful retained result is fetched once and bound to its original submission.

Pause/navigation/context reset/disconnect abort local polling only. An admitted
job can keep running, and a lost POST reply can leave an unknown job ID. Submission
is not idempotent. There is no automatic retry with new settings or server-side
enumeration. The backend retains one active/two waiting jobs, 32 records and bounded
result bytes; results expire after 300 seconds and restart loses records. Client
receipts/results are memory-only copies, bounded to eight per context.

Cancel suspends polling, aborts its stale GET, disables duplicate clicks and sends
one explicit DELETE. RUNNING/CLEANING_UP remains pending until native cleanup.
If cancellation wins, CANCELLED has no result. If completion won, SUCCEEDED and
its verified report remain available. A lost cancellation reply does not claim the
server stopped; the UI asks for actual-status refresh. Server cancellation and
whole-job resource enforcement remain entirely in unchanged M05B code.

## Comparison and proof integrity

All 24 scalar metrics and scenario-minus-baseline deltas come from backend reports:
completion/incompletion, finished/unfinished/stage units, on-time/late completion,
tardiness, weighted tardiness, makespan, available/consumed/unused capacity and
utilization. Units and denominators remain explicit. Null/zero-baseline percentage
changes show their backend reason; ratios also retain reported percentage-point
changes. No frontend scheduling outcome, delta, confidence interval or business KPI
is fabricated. Same-instance algorithm reports provide objective differences only;
missing percentage differences are explicitly not reported.

The frozen objective order is unfinished units, completed-order priority-weighted
tardiness, then makespan. Lower tardiness cannot conceal unfinished demand. Selected
producer, strict-better/tie/worse relation and fallback reason remain visible.
Advanced details show native OPTIMAL/FEASIBLE/UNKNOWN, phases, values/bounds, proof
counts and retained incumbent source. FEASIBLE is not promoted; candidate proof
is not transferred to selected greedy. UNKNOWN/no incumbent and resource stops
do not prove infeasibility. A whole-job failure receives no invented fallback result.

## Measured verification and reproduction

Verified 2026-11-21 on Windows, Python 3.13.14, Node 26.13.0/npm 11.20.0 and system
headless Edge. No dependency versions changed. Real browser observations:

| Case | Actual observed behavior |
| --- | --- |
| Capacity what-if, workers 2 → 3 | Greedy finished units 45 → 55, unfinished 10 → 0; backend relation BETTER |
| Scheduling job on unchanged capacity baseline | 45 finished / 10 unfinished; native candidate OPTIMAL on all three objectives, but selected greedy remains 0/3 proof with CP_SAT_NOT_STRICTLY_BETTER |
| Routing what-if, X workers 1 → 2 | Greedy baseline 28, modified greedy 18; bounded CP-SAT selected for modified instance recovers 28; greedy-only regression remains explicit |
| Explicit zero-wall routing comparison job | Native UNKNOWN, no invented candidate; selected greedy, modified instance still 18 vs baseline 28, relation WORSE |
| Separate cancellation workflow | Actual server CANCELLED, disabled further cancellation and no successful result rendered |

These are small synthetic examples on this environment, not scalability, causal
productivity or cross-machine reproducibility claims. Wall-limited outcomes may
vary. Repeated browser runs validate asserted outcomes, not identical runtime,
timestamps, job IDs or arbitrary solver ties.

| Executed check | Actual outcome |
| --- | --- |
| `npm run typecheck` | Pass, strict source/tests/browser/configs |
| `npm run check` | Pass, 47 files, no findings or formatting changes |
| `npm test` | 87 passed in 4 files, 18.56 s |
| `npm run build` | Pass, 61 modules; JS 418.18 kB / 109.71 gzip; CSS 25.32 / 6.12 kB |
| `npm run test:browser` with verified frontend reuse | 8 passed, 49.7 s; prior complete run 49.9 s also passed |
| Full root `.venv` pytest `-q` | 940 passed, 148.23 s |
| Ruff lint / format | Pass; 189 files already formatted |
| `pip check` / recursive M05A pins | No broken requirements; all 39 pins match |
| npm audit / dependency tree | Zero vulnerabilities, all 17 direct packages unchanged |
| Local documentation links | 59 checked, none missing |
| Starting-file SHA-256 audit | 245 of 267 original files unchanged; all frozen backend/domain/fixtures/config/dependencies unchanged |

The small `m04-capacity.report.json` and `m04-additional-workers.report.json` files
under `frontend/fixtures/` are intentionally versioned synthetic test goldens from
the unchanged M02/M04 engines and original capacity/additional-workers examples.
They never substitute for an interactive API response.

Unit/component tests cover all eight edit shapes, exact serialization/immutability,
conflicts, unsupported sizes, signed/null deltas, proof/identity rejection, every
job status, duplicate clicks, stale dataset replies, retained draft mode/budgets,
UNKNOWN fallback, POST timeout without retry, explicit cancellation/completion
races, 404/410/auth failures, session clearing and polling cleanup without DELETE.
Status/failure injections in these tests are controlled test cases, not measured
solver outcomes. Existing Python tests retain their native/clock-fault distinction.

The eight browser workflows include the four preserved M06A cases plus real greedy
→ Gantt → reviewed scenario → comparison → CP-SAT submit/poll/result; real routing
recovery; zero-budget UNKNOWN; and separate real cancellation. Axe A/AA and 2.1 AA
smoke checks pass on tested pages/dialogs at 1440×1050, 820×1100 and 390×844. Tables
scroll inside named focusable regions, navigation remains responsive, keyboard
details work and there is no page-width overflow in tested layouts. These are not
WCAG certification or a claim about untested browsers/platforms.

Initial corrected failures: occupied port 5173, a test row selector matching both
finished/unfinished units, keyboard-inaccessible JSON scrolling, a local Windows
text-encoding mismatch, and minor typing/lint findings. UTF-8 labels, safe receipt
ordering, retained solver mode and strict polling deadline were verified afterward.
The harmless Playwright NO_COLOR/FORCE_COLOR warning remains. No failed run is
counted as a pass; no frozen backend defect or contract modification was needed.

Follow [frontend startup/workflow commands](../../frontend/README.md). The normal
browser harness owns temporary API/Vite processes and an ephemeral token. If this
repository's Vite already runs on 5173, explicitly set
`LOOMETRIC_TEST_REUSE_FRONTEND=1`; it checks package/source identity, owns only the
temporary API and leaves the existing frontend untouched. It never reuses a user's
API/token or kills another listener. Traces/videos/automatic failure screenshots
remain off, credential-bearing failure text is redacted, and evidence stays ignored.

Eight local screenshots in `.tmp/frontend/` have prefix `m06b-`: scheduling-desktop,
scenario-review, scenario-comparison, job-result, routing-recovery, jobs-tablet,
jobs-mobile and cancelled-job (`.png`). None is versioned. The local roadmap records
verified commits/pushes and the exact changed-file groups; it remains ignored.

## Limitations and next milestone

No durable history, job-list/recovery UI, arbitrary instance upload, operation
drag-and-drop, new shift/resource definition or automatic re-optimization exists.
Changing dataset/session loses local draft/results/job IDs; server work may continue.
There is no continuous factory telemetry or M01 serving. Rich calendars and solver
scale remain limited by the unchanged synthetic domain and HTTP envelopes. Linux,
other browsers and public/multi-user operation remain unverified/out of scope.

M07 can start only with a separately defined user workflow and evidence contract.
The typed exact transport, verified visualizations, reviewed M04 drafts and bounded
job lifecycle are ready to reuse. Persistence, larger execution envelopes, factory
data or ML capacity adjustments require their own decisions and validation; none
is inferred from these demonstrations.
