# ADR 0012: Atomic capacity scenarios with verified greedy fallback

Status: accepted for M04 before implementation and worked-example execution.

## Context and decision

M02/M03 provide validated capacity entities, a deterministic reference, independent
verification and optional bounded CP-SAT. M03C demonstrated absent, worse and
time-sensitive optimizer incumbents. What-if calculations must preserve demand,
keep a usable verified reference and distinguish capacity assumptions from scheduling.

Use a separate `loometric.scenarios` package with a versioned specification bound
to the exact baseline ID/fingerprint. Initial inputs are explicitly synthetic, as
in existing planning/scheduling CLIs. Require source ID, label and assumptions.
Operations cover line workers/availability, profile efficiency, assignment add/remove
and downtime add/remove/full replacement. Added assignments reference already
declared shifts/profiles/calendars/capabilities; no new resource defaults or shifts.

Apply the ordered list to local copies as an atomic transaction. Each operation
requires its target to exist (or be absent for additions). Reject more than one
change to the same entity field; assignment/downtime lifecycle operations share
one conflict key per ID. Workers and availability may both change on one line.
Validate the complete final M02 aggregate and M03 instance once. Intermediate
dangling references are permitted inside the transaction; final dangling references,
overlaps, invalid intervals/profile dates and unsupported fields are errors. There
is no last-write-wins behavior, inferred cleanup or partial returned scenario.

Preserve orders, styles/standards, priorities, dates, capabilities, shift definitions,
working dates, horizon, offset and whole-stage-minute-v1. Derived instance identity
includes baseline binding, ordered changes and provenance; execution settings are
excluded from transformation identity and separately included in specification
identity. The audit trail records before/after values and no-op changes explicitly.
Changed hypothetical efficiency profiles take the scenario's synthetic source.

Always dispatch and independently verify greedy for baseline and scenario. Optional
CP-SAT is explicitly requested, single-worker, at most10 wall seconds and1 internal
deterministic unit per phase, under the existing model/memory/watchdog envelope.
Its adapter output is re-verified and metrics recomputed. Select it only if its
frozen objective tuple is strictly smaller than that instance's greedy tuple.
Ties, worse candidates, no incumbent, invalid evidence, missing optional dependency
and resource stops retain greedy with an explicit reason. Proof belongs to the
optimizer candidate; it is never transferred to a different selected greedy plan.

Move the existing generic process guard/limits into `loometric.execution` and the
existing lossless instance serializer into scheduling loading, retaining M03C import
compatibility. This supplies concrete shared boundaries without making the scenario
domain depend on an evaluation package. Do not modify optimizer/reference/verifier.

## Comparison and consequences

Calculate scenario-minus-baseline scalar deltas with Decimal arithmetic. Percentage
changes require nonnull operands and nonzero baseline; otherwise emit null and an
explicit reason. Preserve null empty-plan makespan while using the existing zero
objective convention. Report utilization denominators and same-instance greedy vs
selected comparisons. These are conditional planning results, not causal productivity,
financial savings or business guarantees. Native runtime/memory remain separate.

The independent worked cases are declared before execution: a45-minute net slot,
workers2, efficiency0.5 and standard1 provides45 standard minutes. Batches20/25/10
finish45 units with15-minute downtime; workers3 allow55 units. Removing downtime
also permits55. Reducing downtime to10 minutes offers50 standard minutes but still
finishes45 because whole batches cannot use the remaining fragments.

A routing counterexample has10-minute simultaneous lines X(workers1),Y(workers2).
Priority1 batch18 can use both; priority2 batch10 can use only X, standard1/efficiency1.
Greedy completes28 units using Y then X. Increasing X to workers2 makes the first
batch choose X on its ID tie; only18 units finish. A feasible28-unit plan still
exists on Y/X. The engine must report this greedy regression despite added capacity;
an optional verified strictly better optimizer incumbent may recover it.
