# ADR 0008: Independent planning domain and interval-based capacity assessment

Status: accepted for M02. Formulas and assumptions declared before scenario execution.

## Context and options

Loometric needs explicit production resources, units and constraints before a
scheduler. M01's productivity forecasts have unverified units/timing and cannot
serve as an operational capacity multiplier. Real factory rules are unavailable;
all runnable examples must be clearly synthetic.

Options are an optimizer/service now, a generic operations framework, or a small
independent domain and deterministic capacity assessment. Choose the last using
standard-library frozen dataclasses, enums, aware timestamps and Decimal arithmetic.
No existing ML modules, data, artifacts, dependencies or evaluation protocols change.

## Decision

Create `loometric.planning` with separate domain/validation, scenario integrity,
availability, capacity calculation, JSON loading and CLI/reporting responsibilities.
Styles provide positive **stage-specific worker-minutes per piece**. Orders carry
their own ordered, unique required stages; there is no universal factory route.
Lines declare a stage, integer dedicated crew size and availability. A capability
explicitly binds a line/style/stage and documents why that crew can perform the work.
No cross-line labor transfer, shared-crew allocation or role/machine bottleneck is
silently inferred. A profile supplies an explicit [0,1] capacity-derating fraction,
effective date, source and synthetic/verified evidence status; this fraction is
unrelated to M01's productivity ratio. Verified is a caller assertion requiring an
evidence reference, not software certification.

Calendar working dates are explicit, not a guessed weekly pattern. A shift belongs
to its start timestamp's local date, including overnight shifts. Assignments bind a
line, shift and explicit effective profile. References and IDs must be valid;
same-line assignments cannot overlap in absolute time. Selected profiles must
belong to the line and be effective by shift start; selecting/freshening profiles
is explicit, with no automatic latest-profile policy or invented expiry.

Use explicit break intervals, not only an aggregate duration: without positions,
break/downtime overlap cannot be resolved defensibly. Planned downtime is scoped to
an assignment and must lie within the shift. Line unavailability may span several
shifts and is intersected with each. Union all blocked intervals before subtraction,
including overlaps between breaks, stoppages and unavailability. Reject overlapping
break definitions; overlapping reasons for downtime are retained and counted once.
Intervals are half-open, adjacent assignments are allowed, zero-length downtime
is allowed and shifts require positive elapsed duration. Perform comparisons and
duration arithmetic in UTC. Offsets/local dates are caller supplied; no factory
timezone, recurrence, holiday or overtime rules are invented.

For net available elapsed minutes M, dedicated workers W, efficiency E and stage
standard S: available labor A=M*W; effective standard-minute capacity C=A*E;
order demand R=quantity*S; potential pieces=floor(C/S); required raw worker-minutes
R/E when E>0; standard-minute shortfall=max(0,R-C). Zero efficiency yields zero
capacity and no finite raw labor requirement. Use fixed 28-digit Decimal arithmetic
and explicit decimal-string results, avoiding binary-float unit conversions.

Assess every order/stage against calendar line/shift slots independently, exposing
compatibility and insufficient-capacity reason codes. Require the entire assessed
slot inside release/due date boundaries for a positive independent-slot indicator;
do not guess partial-shift allocation or completion times. Priority is recorded
(1 highest) but does not drive allocation. Repeat capacity for separate hypothetical
orders without summing it or claiming reservations. Return schedule feasibility
as NOT_ASSESSED, even when every stage has a sufficient independent slot. Stage
precedence is declared but not scheduled; cross-order competition, material/WIP,
transport, setups, machine/role capacity and optimization belong to later work.

Strict versioned JSON rejects unknown/missing fields, duplicate keys, nonfinite
values, guessed dates/timestamps and unsupported units. Scenario errors have explicit
codes. Reports are deterministic, synthetic-labeled and contain no execution-clock
metadata. CLI loads only the requested scenario and never reads ML data/artifacts.

## Consequences

The foundation is executable without factory data or an ML environment. Future
scheduling must allocate shared slots once, respect each order's precedence and
release/due boundaries, model finite worker/machine resources, and define WIP and
setup semantics before any OR-Tools comparison. This milestone creates neither a
schedule nor operational feasibility evidence. No API, database, frontend or M03
implementation is introduced.
