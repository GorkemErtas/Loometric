# ADR 0009: Frozen M03A scheduling subset and independent feasibility gate

Status: accepted for M03A. Policy declared before scheduling implementation or benchmarks.

## Context and options

M02 assesses each order independently and does not reserve capacity. Sufficient
independent slots cannot establish a competing-order or precedence-feasible plan.
Before CP-SAT, Loometric needs a strict shared problem/result contract, a transparent
reference dispatcher and an independent verifier on identical synthetic instances.
M01 forecasts still have no verified mapping to capacity.

Options include shift-bucket allocation, preemptive/split processing, or continuous
whole-stage operations. Freeze the last, on a discrete one-minute grid, to make
breaks, precedence and finite reservations explicit without inventing WIP semantics.
Use standard-library code and reuse M02 entities, intervals, validation and units.
Do not add OR-Tools or modify ML experiments, boundaries or artifacts.

## Frozen policy: whole-stage-minute-v1

- A version-1 instance embeds a validated M02 scenario and declares an instance ID,
  horizon, fixed calendar UTC offset and allocation granularity of exactly 1 minute.
  All interval endpoints must align to UTC minutes. Shift starts must use the
  declared calendar offset, preserving M02's local working-date/profile semantics.
- Each order's unique ordered required stages are full-batch operations. No
  splitting, partial quantities, preemption, stage revisits, machine sharing,
  worker transfers, setup times, material constraints or initial WIP are supported.
- One operation occupies one declared compatible line/assignment and its entire
  dedicated crew for one contiguous available interval inside that shift and the
  horizon. Partial shift use is allowed; crossing a break, downtime, unavailability
  or shift boundary is forbidden. Half-open boundaries permit adjacency.
- For quantity Q, stage labor standard S, crew W and efficiency E, duration is
  ceil(Q*S/(W*E)) elapsed minutes, calculated with exact rational arithmetic.
  Reserve duration*W raw worker-minutes and duration*W*E standard-minute capacity;
  rounding slack is reserved, not available to another operation. Zero W or E
  cannot process an operation. Decimal output uses M02's 28-digit convention.
- Release is a hard lower bound at local midnight in the declared fixed offset.
  Due is a soft deadline at midnight following the due date. Completion exactly
  at the deadline is on time; later completion is allowed inside the horizon and
  counted as tardy. M02's conservative full-slot due-date assessment remains
  unchanged; this separate scheduling policy evaluates actual timed operations.
- An immediate predecessor must finish before or exactly when its successor
  starts. Stages of one order cannot overlap; different orders may run on different
  declared lines concurrently. Transfer/setup/yield/WIP assumptions remain unsupported.
- The offline serial dispatcher ranks orders by ascending priority (1 highest),
  due date, then stable ID. For each stage find the earliest available gap at or
  after release, horizon start and predecessor completion. Candidate ties resolve
  by start, finish, line ID, shift ID, assignment ID. Reserve the interval before
  continuing. Future releases leave earlier gaps available for other orders.
- A failed stage remains explicitly unscheduled with its full quantity and a reason;
  downstream stages remain unscheduled with PREDECESSOR_UNSCHEDULED. Already scheduled
  upstream work stays as partial work, not finished goods. No rollback, backtracking,
  hidden reranking or optimality claim.
- Large/fragmented operations that cannot fit a full working fragment are reported
  REQUIRES_SPLITTING_OR_PREEMPTION, not declared physically impossible. Horizon,
  release and prior reservations have separate diagnostic reasons. Reasons explain
  the reference run and are not infeasibility proofs.
- Every required order/stage appears exactly once as allocated or unscheduled.
  A proposed result contains references, full quantities, explicit times and
  consumed labor/capacity. Its instance fingerprint binds the versioned inputs.
- The verifier accepts arbitrary typed proposals, never imports dispatcher logic,
  and independently rebuilds static availability and requirements. It checks
  references, quantities, units, compatibility, processing time/consumption, working
  windows, line overlap, horizon/release and stage precedence. Valid partial plans
  are distinct from invalid proposals; invalid proposals get no quality metrics.
- Finished units count an order's quantity only when every required stage is
  scheduled. Unfinished orders retain their full finished-goods quantity as
  unscheduled; stage-unit allocations are separate diagnostics. Tardiness totals
  cover completed orders only and must not be used to prefer an incomplete plan.
- Priority weight is max(instance priorities)+1-priority. Tardiness and weighted
  tardiness use elapsed minutes beyond the soft deadline. Makespan is the latest
  allocated end minus horizon start (null for no allocations). Utilization is
  reserved time/capacity divided by available time/capacity within the horizon;
  zero denominators yield null. Per-resource metrics preserve nonfungible stages.

## Consequences

Add a small `loometric.scheduling` package for contracts/static requirements,
dispatcher, verifier, metrics, loading and CLI. Extend M02 interval/serialization
utilities only where shared behavior is needed, preserving existing APIs/output.
Strict synthetic benchmarks and deliberately corrupted proposals test both accepted
partial plans and verifier rejection. Generated reports remain ignored.

M03B must consume the same instance, eligible fragments, integer durations,
precedence, releases, resources, rounding and result contract. Its adapter must pass
this verifier before metrics are computed. A separately authorized CP-SAT task may
compare completion, weighted tardiness and makespan under an explicit objective and
solver limits; it must not silently add splitting, WIP, setup, staffing or ML inputs.
No CP-SAT dependency, frontend/backend/database, deployment or M03B work starts here.
