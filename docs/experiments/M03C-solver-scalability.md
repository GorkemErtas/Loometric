# M03C: Synthetic scheduling scalability and robustness audit

## Predeclared protocol

This design was recorded before executing the matrix. Results are pending. All
instances are hypothetical, without calibrated factory realism. M02/M03A/M03B policy,
model, proof gates, reference and independent verifier remain unchanged.

The source of truth is [the fixed configuration](../../configs/m03c_benchmark.json)
and [ADR 0011](../decisions/0011-bounded-synthetic-solver-audit.md).

| Tier | Orders | Stages | Lines | Days | Shifts/day | Compatible lines/style/stage |
| --- | --- | --- | --- | --- | --- | --- |
| small | 8 | 2 | 4 | 1 | 1 | 2 |
| medium | 24 | 3 | 6 | 2 | 1 | 2 |
| large | 60 | 3 | 9 | 3 | 1 | 2 |
| stress | 150 | 5 | 20 | 7 | 2 | 4 |

Every tier crosses aggregate standard-demand/capacity targets 45%, 90%, 135% and
generator seeds 19, 42, 73. Each instance crosses wall budgets 1, 5, 10 seconds per
phase, always deterministic-time limit 1.0, solver seed 42, one worker, zero gaps.
Two serial repetitions: 36 instances, 108 budget cells, 216 scheduled child runs.
No seed, profile or budget is selected or removed after observing results.

Resource-skipped instances receive one guarded generation/reference audit per
instance. Their skip is reused explicitly across other budgets/repetitions, with
source-cell metadata and no duplicated timing measurement. Thus the intended 216
rows require 162 primary solver children plus nine stress audit children, if the
predeclared stress skips occur. Both primary repetitions always execute separately.

Limits: 300 operations, 20,000 eligible alternatives, 25,000 native variables,
90,000 constraints, 768 MiB process committed memory (Linux: virtual address space),
60 seconds whole-child wall time and 2,400 seconds total batch wall time. The stress
tier has 750 operations and is predeclared to return SKIPPED_RESOURCE_LIMIT; generate
and validate its input, record dimensions/upper bounds, then skip before building
the native model. This guard exercises reporting without risking large search.
All rows, including skips, remain in the report. No time limit means infeasibility.

The pressure target scales per-stage labor standards to aggregate available standard
capacity, after explicit breaks/downtime, using two decimal places. Report realized
ratios. This proxy ignores route compatibility, releases, fragmentation and precedence;
it neither certifies feasibility nor measures real utilization. All variants retain
full-batch, one-fragment processing and the same demand/capacity semantics.

Read returned phase values/bounds conditionally on preceding proven objectives.
Compare only independently verified metrics in frozen lexicographic order. Distinguish
BETTER/TIE/WORSE from NO_COMPARABLE_INCUMBENT and complete proofs from feasible results.
The repeated-run audit compares all deterministic fields, but cannot promise identical
wall-limited native outcomes. Report mismatches and quality regressions explicitly.

## Measured results

Pending implementation and execution; no performance or scalability claim yet.
