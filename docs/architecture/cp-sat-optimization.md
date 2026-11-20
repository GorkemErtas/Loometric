# M03B: CP-SAT optimization under whole-stage-minute-v1

M03B adds an optional OR-Tools producer of the existing ProposedSchedule contract.
It preserves the [M03A scheduling policy](scheduling-contract.md), reference dispatcher,
independent verifier, metrics and all five original benchmark instances. All measured
cases are synthetic; results are not factory performance or operational validation.
See [ADR 0010](../decisions/0010-cp-sat-strict-lexicographic-scheduling.md).

## Dependency and architecture

The optional `optimization` extra pins **OR-Tools 9.15.6755**. The reproducible full
environment in [requirements/m03b.txt](../../requirements/m03b.txt) includes the
unchanged EXP-002/EXP-001 pins and five exact additions: ortools 9.15.6755,
absl-py 2.5.1, immutabledict 4.3.1, protobuf 6.33.6 and typing-extensions 4.16.0.
Recorded environment: Python 3.13.14, Windows x86-64. No previously installed package
version changed. Native CP-SAT execution and dependency consistency were checked.

| Module | Responsibility |
| --- | --- |
| `optimization/configuration.py` | Explicit seed, workers, phase budgets and benchmark settings |
| `optimization/model.py` | Numeric preflight, eligible alternatives, integer variables and constraints |
| `optimization/adapter.py` | Native values to the unchanged ProposedSchedule schema |
| `optimization/solver.py` | Proof-gated phases, incumbent handling, verification and objective consistency |
| `optimization/comparison.py` | Pure lexicographic comparison of independently accepted metrics |
| Existing `scheduling/cli.py` | Lazy optimizer command and separately verified reference comparison |

The optimizer core and adapter never import the reference dispatcher. The CLI alone
runs the unchanged reference for comparison. Dispatch/verify remain usable without
OR-Tools or site packages; only optimize imports the optional dependency. No solver
installation, model retraining or artifact loading occurs implicitly at runtime.

## Mathematical formulation

All times are integer minutes relative to the horizon's UTC start. Let H be its
length, Q_o the finished-goods quantity of order o and K_o its ordered unique stages.
Each stage's eligible alternatives are compatible line/assignment/working-fragment
triples derived from M02 calendar intervals, with positive crew and efficiency.

For alternative a, crew W_a, efficiency E_a and stage-specific standard S_ok:

`d_oka = ceil(Q_o * S_ok / (W_a * E_a))`

S is standard worker-minutes per piece, d is elapsed minutes. The existing exact
rational helper computes this ceiling, with no float division or alternate labor
scaling. An operation reserves d*W raw worker-minutes and d*W*E effective standard
minutes. Rounding slack remains reserved. Alternatives too long for their fragment
are excluded; no preemption, splitting or break-crossing relaxation is introduced.

Each operation has these variables:

| Variable | Domain / meaning |
| --- | --- |
| p_ok | Boolean operation presence |
| y_oka | Boolean selection of one eligible alternative |
| s_ok, e_ok | Integer start/end in [0,H], both zero when absent |
| c_o | Presence of the final stage; prefix constraints make this full-order completion |
| raw_tardy_o | max(0, e_final − D_o), including an unused raw value when absent |
| T_o | raw_tardy_o if completed, otherwise zero |
| U | Unfinished finished-goods units |
| T_w | Completed-order priority-weighted tardiness |
| C_max | Maximum allocated operation end, with absent ends zero |

Hard constraints are:

1. `sum_a y_oka = p_ok`. A present stage selects exactly one alternative; a stage
   with no alternatives is absent. Every allocation uses the full Q_o.
2. A selected alternative creates an optional interval of fixed duration d_oka.
   Its start is at least the fragment start, hard release and horizon start, and
   at most fragment end minus d_oka. The entire operation fits one uninterrupted
   fragment of one shift; partial use of that shift is allowed.
3. `NoOverlap` on all alternative intervals sharing a production line. The line's
   whole declared dedicated crew is reserved; no cross-line worker sharing is added.
4. `p_ok <= p_o,previous`. When a successor is present, its start is at least the
   predecessor's end. Upstream partial work remains allowed, as in M03A.
5. Absent start/end values are zero. Completed-order tardiness equals the raw max;
   incomplete-order tardiness is zero through reified linear equalities.

Release is local midnight in the instance's declared fixed offset. D_o is midnight
after its due date, converted to relative UTC minutes. Due dates are soft: completion
exactly at the deadline is on time; late completion is permitted within the horizon.
No shared workers, setups, material inventories, initial WIP, rework, splitting,
alternate routing or ML capacity factor is introduced.

## Numeric safety and exact objectives

Before creating CpModel, preflight checks H, release/deadline offsets, total quantity,
priority weights and aggregate weighted-tardiness bounds. Encoded integer values are
conservatively limited to **2^53−1**: integer objectives remain exactly representable
through double-valued solver telemetry, with headroom below native int64 limits.
The weighted upper bound is `sum_o w_o * max(0,H-D_o)`. Unsupported ranges fail with
INTEGER_RANGE_UNSUPPORTED. No coefficient is silently scaled, clipped or rounded.
Long durations excluded before variable creation need not fit a native variable.
The constructed model must also pass native `model.validate()`.

The strict lexicographic vector is:

1. `U = sum_o Q_o * (1-c_o)`.
2. `T_w = sum_o w_o * T_o`, where `w_o=max(instance priorities)+1-priority_o`.
3. `C_max=max_ok e_ok`, including all allocated upstream work.

This is implemented by three separate minimization solves. After an independently
verified **OPTIMAL** phase, constrain that objective to its exact integer optimum
before replacing the objective for the next solve. Only the aggregate optimum is
fixed: lower phases can change which orders, alternatives and start times achieve it.
There is no arbitrary weighted sum or fourth tie-breaking objective.

M03A reports null makespan when there are no allocations. CP-SAT and objective
comparison use zero for that empty-allocation objective while preserving the null
metric. Raw metric deltas involving null remain null; objective deltas use the
documented zero convention. An empty solution must be an actual solver incumbent,
never a schedule fabricated after UNKNOWN.

## Phase budgets, proof and timeout behavior

Default configuration, declared before benchmark execution:

| Setting | Value |
| --- | --- |
| Random seed | 42 |
| Search workers | 1 |
| Wall limit | 10 seconds per phase |
| Deterministic limit | 1 internal solver-time unit per phase |
| Absolute / relative gap tolerance | Both explicitly zero |
| Benchmark mode | Enabled; rejects multiple workers |

At most three phase solves run. Budgets apply to solver calls, not model construction,
adaptation, verification or serialization. Internal deterministic time is not a
wall-clock guarantee. A wall-cap stop can change outcomes across machines/load even
with one worker. Non-benchmark mode permits an explicitly requested worker count
without a reproducibility promise. Zero budgets are allowed and tested.

| Phase outcome | Implemented action |
| --- | --- |
| OPTIMAL with valid adapted incumbent | Accept it, record the proof, fix the objective and advance if another phase remains |
| FEASIBLE | Verify and return its incumbent; stop without fixing/advancing or claiming full lexicographic optimality |
| First-phase UNKNOWN | Return UNKNOWN with no schedule or candidate metrics; preserve any finite returned bound |
| Later UNKNOWN | Keep only the real previously verified incumbent; mark the fallback, its source phase and incomplete proof explicitly |
| INFEASIBLE / MODEL_INVALID without incumbent | Report that actual status; no fabricated schedule or metrics |
| Contradictory later no-solution result | Surface the contradiction and suppress accepted results |
| Bad adapter, verifier rejection or objective mismatch | Return INVALID, diagnostics and null accepted metrics |

Every attempted phase records status, exact incumbent objective when present, finite
returned bound, whether it was proven, and whether preceding objectives were proven.
Unexecuted phases are absent, not assigned invented statuses. UNKNOWN can return a
useful bound without an incumbent; default returned zero is valid for these
nonnegative objectives. Bounds for INFEASIBLE/MODEL_INVALID are suppressed. No gap is
invented, and FEASIBLE is not promoted even if its returned bound equals an incumbent.

`full_lexicographic_optimal` requires all three verified, zero-gap OPTIMAL phases.
This can accompany VALID_PARTIAL: the best feasible plan need not complete every
order. Solver proof and schedule completeness are distinct fields.

## Adapter, verification and output

The adapter copies IDs, full quantities, selected profile, exact capacity claims and
UTC timestamps into the unchanged ProposedSchedule. Every required stage is either
allocated or explicitly unscheduled. Existing reason codes are reused. In particular,
CAPACITY_RESERVED labels a supported alternative not selected by this incumbent;
it does not prove that every gap is full. This also covers omitting upstream work
that cannot complete its route. Downstream absent stages retain
PREDECESSOR_UNSCHEDULED. Reason labels remain diagnostics, not infeasibility proofs.

Every phase incumbent passes the **unchanged** independent verifier. Metrics are then
recomputed independently and the entire three-objective vector must match CP-SAT's
integer variable values, even in an early phase. A feasible proposal with inconsistent
model objectives is still an INVALID optimizer result; verifier findings and engine
diagnostics are kept distinct. No verifier rule is weakened.

The optimize JSON includes algorithm identity, solver version/configuration, phase
proof metadata, proposed schedule, independent verification, metrics, objective
vector, termination/fallback diagnostics and same-instance reference comparison.
All runtime fields are isolated under `runtime`: model-build duration, individual
solve-call/native wall/deterministic times, optimizer total and reference total.
No incumbent means candidate metrics remain null even though the separately verified
reference can still be shown. Missing optional dependencies produce explicit install
guidance; the CLI never installs packages itself.

An accepted complete or partial incumbent exits 0, including an explicitly unproven
or retained fallback. UNKNOWN without an incumbent, invalid results and invalid inputs
exit 2. Users must inspect proof fields; exit 0 does not mean an optimality proof or
authorization for real production decisions.

## Reproduction

From the repository root in the recorded environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/m03b.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .

.\.venv\Scripts\python.exe -m loometric.scheduling optimize `
  --instance examples/scheduling/competition.json `
  --seed 42 --workers 1 --time-limit-seconds 10 `
  --deterministic-time-limit 1 --benchmark-mode

.\.venv\Scripts\python.exe -m loometric.scheduling optimize `
  --instance examples/scheduling/hand-enumerated.json
```

`pip install -e ".[dev,ml,optimization]"` installs supported extras; the requirements
snapshot additionally pins their measured dependency closure. The six JSON inputs
are versioned, all hypothetical. Generated optimizer/reference reports belong in
ignored `.tmp/` or `data/processed/`, never Git. Dispatch and verify commands retain
their original interfaces and exact report contents.

## Measured benchmark comparison

The five original frozen M03A instances were reused exactly. One additional
[hand-enumerated instance](../../examples/scheduling/hand-enumerated.json) was declared
before execution: one worker, efficiency/standard both one, 10 available minutes,
whole batches A6/B5/C5 and priorities 1/2/3, with a deadline 480 minutes before the
horizon. Exhaustive enumeration of 294 absence/start combinations independently
finds `(U,T_w,C_max)=(6,1460,10)` by completing B then C. The reference chooses A.
A second independent small oracle verifies that the third objective removes idle
time when higher objectives tie.

All listed candidates passed independent verification. Each of all **18 phases**
returned OPTIMAL with the returned bound equal to its objective. Phase-two bounds
are conditional on optimal U; phase-three bounds are conditional on optimal U/T_w.
Full lexicographic proof holds for these finite synthetic instances only.

| Instance | Reference (U, T_w, C_max) | CP-SAT (U, T_w, C_max) | Lexicographic result |
| --- | --- | --- | --- |
| competition | (80, 0, 225) | (60, 0, 300) | BETTER |
| parallel-routing | (0, 1881, 164) | (0, 1881, 164) | TIE |
| calendar-fragments | (80, 0, 443) | (80, 0, 443) | TIE |
| limits | (239, 0, 75) | (239, 0, 0) | BETTER |
| zero-capacity | (10, 0, 0) | (10, 0, 0) | TIE |
| hand-enumerated | (10, 1458, 6) | (6, 1460, 10) | BETTER |

| Instance | Producer | Completed orders | Finished units | Unfinished units | On-time orders | Late orders |
| --- | --- | --- | --- | --- | --- | --- |
| competition | Reference | 1 | 60 | 80 | 1 | 0 |
| competition | CP-SAT | 1 | 80 | 60 | 1 | 0 |
| parallel-routing | Reference | 3 | 90 | 0 | 1 | 2 |
| parallel-routing | CP-SAT | 3 | 90 | 0 | 1 | 2 |
| calendar-fragments | Reference | 2 | 70 | 80 | 2 | 0 |
| calendar-fragments | CP-SAT | 2 | 70 | 80 | 2 | 0 |
| limits | Reference | 0 | 0 | 239 | 0 | 0 |
| limits | CP-SAT | 0 | 0 | 239 | 0 | 0 |
| zero-capacity | Reference | 0 | 0 | 10 | 0 | 0 |
| zero-capacity | CP-SAT | 0 | 0 | 10 | 0 | 0 |
| hand-enumerated | Reference | 1 | 6 | 10 | 0 | 1 |
| hand-enumerated | CP-SAT | 2 | 10 | 6 | 0 | 2 |

| Instance | Producer | Weighted tardiness min | Total tardiness min | Makespan min | Line utilization % | Unused standard min |
| --- | --- | --- | --- | --- | --- | --- |
| competition | Reference | 0 | 0 | 225 | 46.8750 | 816 |
| competition | CP-SAT | 0 | 0 | 300 | 62.5000 | 576 |
| parallel-routing | Reference | 1881 | 1237 | 164 | 21.8750 | 4227 |
| parallel-routing | CP-SAT | 1881 | 1237 | 164 | 21.8750 | 4227 |
| calendar-fragments | Reference | 0 | 0 | 443 | 73.0556 | 310.4 |
| calendar-fragments | CP-SAT | 0 | 0 | 443 | 73.0556 | 310.4 |
| limits | Reference | 0 | 0 | 75 | 20.8333 | 336 |
| limits | CP-SAT | 0 | 0 | null | 0.0000 | 576 |
| zero-capacity | Reference | 0 | 0 | null | null | 0 |
| zero-capacity | CP-SAT | 0 | 0 | null | null | 0 |
| hand-enumerated | Reference | 1458 | 486 | 6 | 60.0000 | 4 |
| hand-enumerated | CP-SAT | 1460 | 975 | 10 | 100.0000 | 0 |

Utilization percentages are rounded to four decimal places for display; JSON retains the declared precision.

The hierarchy matters: competition completes 20 more units despite a 75-minute
makespan regression. The analytical case completes four more units despite two more
weighted tardiness minutes and four more makespan minutes. Limits completes no
additional goods; its tertiary improvement removes an unnecessary unfinished prefix
and produces a real empty incumbent. Zero completed-order tardiness in limits/zero
capacity is not evidence that unfinished goods meet their due dates. Three objective
tuples tie. No general optimizer superiority or speedup is inferred.

Reported wall times below are single serial measurements after the regression suite
finished, rounded to six decimal places. Optimizer total includes construction,
adaptation, verification and metrics; reference total includes dispatch, verification
and metrics. Python startup/imports, instance loading and JSON serialization are
excluded. Native solver time sums the three phases. These local measurements are
not controlled performance estimates or statistical comparisons.

| Instance | Optimizer total s | Native solver sum s | Reference total s |
| --- | --- | --- | --- |
| competition | 0.049416 | 0.008279 | 0.001003 |
| parallel-routing | 0.035159 | 0.009607 | 0.001448 |
| calendar-fragments | 0.037009 | 0.008884 | 0.001467 |
| limits | 0.030569 | 0.004756 | 0.001582 |
| zero-capacity | 0.027050 | 0.002944 | 0.000801 |
| hand-enumerated | 0.040288 | 0.011245 | 0.001411 |

## Verification and limits

Final full pytest: **639 passed in 43.63 s** (580 existing + 59 optimization cases).
Tests cover optional intervals, competition, alternatives, prefix precedence,
interruptions, releases/deadlines, exact rounding, empty/partial allocations, integer
bounds before model creation, configuration, proof gates and verifier rejection.
The exhaustive oracles check objective correctness without CP-SAT helpers. A real
zero-wall-budget run returns UNKNOWN without a fabricated schedule. Controlled
status/fault injection checks FEASIBLE, later UNKNOWN fallback, INFEASIBLE,
MODEL_INVALID, contradictory phases, invalid adapters and objective mismatches;
these injections are not claimed as observed benchmark timeout outcomes.

Six default cases each reproduced all non-runtime fields on two complete runs.
All 18 benchmark phases reported OPTIMAL with matching objective/bound values and
all candidates passed the unchanged verifier. Final review also retained finite
UNKNOWN-phase bounds; objective values remain null when there is no incumbent.
That reporting correction passed its 23 focused solver tests and the final full
suite above. No mathematical formulation or benchmark parameter changed.

Ruff lint/format and dependency checks pass. All 23 exact pins match, including all
18 prior pins. Every previously installed package version is preserved. The initial
editable-metadata refresh hit sandbox temporary-directory permissions and succeeded
with normal local temp access. An initial range test had a zero tardiness domain;
its fixture dates were corrected to exercise the intended nonzero overflow bound.
No scheduling constraint, objective hierarchy or frozen benchmark was relaxed.

Every deterministic non-runtime field matched across two full runs per instance;
the serial timing capture was also checked against that content. Fixed solver
version, seed, workers, budgets and model ordering support reproducibility in this
environment, not across solver versions or wall-cap interruptions. No unique
tie-breaking optimum is promised beyond the declared three objectives.

The unchanged dispatcher/verifier/metrics/policy and prior architecture/experiment
documents are protected by hashes. All five original dispatch stdout snapshots stay
byte-identical. There is no M01 artifact or protected ML validation/test consumption;
a separate guarded optimizer process tests that boundary. Legacy commands still run
without site packages and optimize gives guidance when its extra is missing.

Limitations remain those of whole-stage-minute-v1: static synthetic dedicated crews,
stage standards and efficiencies, fixed offsets, no sharing/setups/materials/initial
WIP/splitting/rework, conservative numeric range and small tested instances. Time
limits can yield unproven or absent incumbents; no fallback is presented as a full
proof. Unscheduled diagnostics are not global infeasibility certificates. Proof
certifies this mathematical model, not factory readiness or business optimality.

Recommended next milestone: a predeclared larger synthetic benchmark and timeout/
proof robustness audit under the same policy before adding production features or
integration. No further milestone, API, database, frontend, deployment or ML-to-capacity
integration starts here.

Primary references: [pinned OR-Tools release](https://pypi.org/project/ortools/9.15.6755/),
[CP-SAT integer model/status guidance](https://developers.google.com/optimization/cp/cp_solver),
and [v9.15 budget/gap/seed parameters](https://github.com/google/or-tools/blob/v9.15/ortools/sat/sat_parameters.proto).
