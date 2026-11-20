# M03A: Scheduling contract, verifier and reference dispatcher

The scheduling policy is **whole-stage-minute-v1**, frozen before implementation
and benchmark execution in [ADR 0009](../decisions/0009-reference-scheduling-policy.md).
All examples are synthetic. No OR-Tools, ML capacity conversion, API, database or
frontend is introduced. M01 and M02 retain their existing behavior.

## Frozen supported subset

Version-1 instances embed M02 planning entities, an explicit scheduling horizon,
fixed calendar UTC offset and exactly one-minute allocation granularity. All time
boundaries align to UTC minutes; shift starts use the declared calendar offset.
Orders supply their own ordered stages and stage-specific worker-minutes per piece.

Whole order/stage quantities are processed nonpreemptively on one compatible line,
using its complete declared crew, within one uninterrupted working interval of one
shift. Partial use of a shift is allowed. Operations cannot span breaks, downtime,
unavailability or shifts; splitting, rework, WIP, setups, shared crews and materials
are unsupported. Unsupported large operations remain explicitly unscheduled.

Duration is ceil(quantity*stage_standard/(workers*efficiency)) elapsed minutes using
exact rational arithmetic. The whole rounded interval's worker-minutes and effective
standard-minute capacity are reserved. Predecessors finish before successors start.
Release dates are hard local-midnight bounds. Due dates are soft next-midnight
deadlines, permitting measurable late completions inside the horizon. This refines
timed scheduling without changing M02's independent full-slot assessment.

The reference ranks priority, due date, order ID; each stage takes the earliest
feasible gap, breaking ties by finish time and stable resource IDs. It reserves
capacity before continuing. Every stage is allocated or explicitly unscheduled;
partial upstream work remains visible. There is no global optimality claim.

An independent verifier gates all quality metrics. Finished units count only fully
scheduled orders; incomplete orders retain their full unscheduled finished-goods
quantity. Tardiness covers completed orders only. Priority weights are
max(instance priorities)+1-priority. Makespan is measured from horizon start.
Utilization and unused capacity use declared available resources inside the horizon.

Implementation interfaces, commands, verified benchmark results and exact M03B
adapter requirements will be recorded here after the frozen policy is implemented.
