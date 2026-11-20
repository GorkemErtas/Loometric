# ADR 0011: Isolated, bounded synthetic solver evaluation

Status: accepted for M03C before benchmark execution.

M03C evaluates the frozen M03B optimizer; it does not change constraints, objectives,
dispatch, verification, existing examples or operational contracts. Use a separate
`loometric.benchmarks` evaluation package, standard-library resource controls and the
existing optional OR-Tools dependency. No new dependencies or production features.

Freeze `configs/m03c_benchmark.json` before executing the matrix. Cross three primary
sizes, three aggregate demand/capacity targets and three generator seeds, with three
wall budgets and two repetitions. Retain stress cases and all failures/skips in the
denominator. Resource policy is declared independently of measured performance.

Each serial child waits for the parent's start message before importing the solver
or generating its instance. On Windows the parent first assigns a Job Object with
a process and aggregate job commit-memory limit and kill-on-close (two processes
allow Windows' virtual-environment launcher); on Linux the child applies RLIMIT_AS
before solver imports. Unsupported/unavailable hard memory controls fail closed.
A parent wall watchdog bounds the complete child, including model construction,
verification and serialization. A total batch deadline prevents unbounded runs.
Resource rejection is not mathematical infeasibility. No native search changes.

Windows launch is suspended until job assignment succeeds, preventing the venv
launcher from creating an unassigned interpreter. The child opens the parent's
uniquely named job and checks its own membership and exact aggregate memory limit
before native imports. Querying the unnamed current job can report an outer nested
job in this environment, so an explicit job identity is required. The name is
ephemeral process metadata and never part of deterministic benchmark identity.

Model dimensions are measured by a separate construction using the existing builder,
then that model is discarded before the unchanged optimizer constructs its own.
Record this sizing time separately. Peak memory includes interpreter, imports,
generation, sizing, solving and verification; it is not solver-only allocation.
An additional independent verifier call is timed explicitly for each returned
proposal. That audit time is not claimed to isolate internal optimizer verification.

Separate schedule/proof/identity data from timing, memory and environment metadata.
Repeat all non-resource-skipped cells and compare complete non-runtime results,
including schedule fingerprints and proof statuses. Wall-limited results may differ;
report each mismatch, never remove it or require bitwise repeatability as a false
property of a wall-clock limit. Repeatable instance generation is a separate check.

Bulk instances/results remain ignored. Version only the generator/configuration,
small representative fixture, tests, ADR and human-readable measured report. Tests
cover status/fallback/rejection using explicit controlled injection as well as real
native runs; injected outcomes are not benchmark observations.
