# ADR 0010: Optional CP-SAT with proof-gated lexicographic optimization

Status: accepted for M03B before optimizer implementation or benchmark comparison.

## Context and decision

M03A froze whole-stage-minute-v1, a reference dispatcher and independent verifier.
M03B adds a producer of the same ProposedSchedule, not new production semantics.
Keep reference dispatch, verification, metrics, policy and frozen instances unchanged.
Use optional OR-Tools 9.15.6755 with exact additions in requirements/m03b.txt; retain
all earlier environment pins and model artifact compatibility. No new service,
database, ML capacity input, splitting, setup, shared-worker or initial-WIP feature.

Build integer time relative to UTC horizon start. Reuse the existing exact rational
ceiling for processing duration. Each order-stage has optional compatible
assignment/fragment alternatives, exactly one when present. Optional intervals must
fit one uninterrupted fragment. NoOverlap is per line; selected stages form a
prefix and each predecessor finishes before its successor starts. Absent starts/ends
are zero. Completion is presence of the final stage. Incomplete orders contribute no
finished goods or tardiness; partial upstream allocations remain permitted by M03A.

Preflight bounds before CpModel creation. Conservatively limit integer dimensions,
objective coefficients and aggregate objective upper bounds to 2^53-1, preserving
exact integer reporting through CP-SAT's double-valued objective/bound telemetry and
leaving headroom below int64. Reject overflow/range violations explicitly; never
scale/round labor differently or relax an unsupported constraint. Validate the built
model before solving as an additional implementation check.

Use three separate minimization solves: unfinished finished-goods quantity,
completed-order priority-weighted tardiness, then horizon-relative makespan. Freeze
an objective equality and advance only after its phase reports OPTIMAL with both
absolute and relative gap limits set to zero. No arbitrary weighted sum.

Default benchmark configuration is seed42, one worker, 10 wall seconds and 1 internal
deterministic-time unit **per phase** (at most three phases). These are software
budgets, not factory thresholds or performance claims. Record all settings, phase
statuses, actual integer objectives, valid returned bounds and runtime separately.
Deterministic limits aid repeatability; reaching a wall cap can still alter outcomes
across hardware/load. Record the solver version and do not promise cross-version ties.

Stop on an unproven FEASIBLE phase and return its independently verified incumbent
without advancing or claiming complete lexicographic optimality. First-phase UNKNOWN
or INFEASIBLE yields no fabricated schedule/metrics. If a later phase has no new
incumbent, retain the last independently verified real incumbent with explicit
fallback/proof metadata; do not promote it to full optimality. MODEL_INVALID and
contradictory solver results are surfaced explicitly. Invalid adapted proposals have
verifier diagnostics and no accepted metrics or feasible/optimal result claim.

The optimizer core/adapter never imports the reference dispatcher. A separate
comparison boundary runs the unchanged reference on the same instance, verifies
both, and compares the three objective values in priority order. Report secondary
regressions as well as improvements, ties and actual proof scope. Existing unscheduled
reason labels remain diagnostic, not mathematical infeasibility certificates.

## Alternatives and consequences

A weighted sum risks changing priorities or overflowing without a proven scaling
bound. Solving lower objectives after an unproven primary objective would misstate
lexicographic proof. Sequential proof gates cost up to three solves but make those
claims explicit and testable. No fourth tie-breaking objective is introduced.

Hand-enumerated/brute-force small cases check objectives independently of CP-SAT;
fault injection tests cover timeouts, solver statuses and invalid adapter output.
All real candidates pass the existing verifier. Generated outputs remain ignored;
previous architecture/experiment reports and protected ML data remain untouched.

References: [CP-SAT statuses](https://developers.google.com/optimization/cp/cp_solver),
[v9.15 solver parameters](https://github.com/google/or-tools/blob/v9.15/ortools/sat/sat_parameters.proto),
and [the pinned release](https://pypi.org/project/ortools/9.15.6755/).
