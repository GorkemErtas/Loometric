# M03C: Synthetic scheduling scalability and robustness audit

## Predeclared protocol

This design was recorded before executing the matrix; measured results follow. All
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
Two serial repetitions: 36 instances, 108 budget cells, 216 scheduled matrix rows.
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
All rows, including skips, remain in the report. Reaching a time limit does not
establish mathematical infeasibility.

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

## Resource-boundary correction before the completed audit

An initial execution under commit 128b3a6 was interrupted during resource review.
Its partial journal is retained locally in data/processed/m03c-audit; it is not
merged into the completed study. Launch could race ahead of parent job assignment.
The corrected launcher starts suspended, attaches the memory-limited job before
resuming, and the child checks membership/limits using the explicit named job.
This correction changes no instances, solver constraints, seeds, budgets or matrix
selection. The entire unchanged matrix is rerun in data/processed/m03c-verified.

## Measured results

The completed audit used harness commit **8dfd38e**, following predeclaration in
**d4efaf6** and **128b3a6**. There were **216 rows**, comprising **162 native solver
runs** plus **54 explicit stress skip rows**. Nine stress reference/generation
children ran once each; cached skip rows identify their source without copying
timing measurements. All primary cells ran twice. Completed batch wall time was
**871.5112 seconds**. No cell was removed or retuned from its observed performance.

Across native runs: **90 BETTER, 6 TIE, 7 WORSE, 59 NO_COMPARABLE_INCUMBENT**.
With the 54 skips included, the non-comparable total is 113. Of the 90 improvements,
**73 improve unfinished units** and **17 improve only makespan**; a secondary-only
improvement must not be described as more finished goods. All seven losses worsen
unfinished units. The supplied reports retain all raw metric deltas, including
secondary regressions. Zero completed-order tardiness is not a success measure for
an incomplete schedule.

**70/162 (43.21%)** native runs proved the full lexicographic objective, 11 proved
two levels, and 81 proved none. The 324 attempted phases comprise **232 OPTIMAL,
33 FEASIBLE and 59 UNKNOWN**; no INFEASIBLE or MODEL_INVALID phase occurred. All
59 UNKNOWN outcomes occurred in phase one with no incumbent. There were **zero
observed retained-earlier-phase fallbacks**; those paths remain covered by explicitly
controlled status tests, not claimed as naturally observed audit events.

Every one of the **103 returned candidates** passed the unchanged independent
verifier and persisted-result metric/objective recomputation. All **36 reference
inputs**, including stress, also passed a separate saved-schedule verification and
metric recomputation. Instance fingerprints and reference results agree across
each case's rows. No invalid candidate, native crash, hard-memory exhaustion,
external watchdog termination or total-batch-limit skip occurred in this completed
audit. Native time-limited absence remains distinct from those resource controls.

## Environment and evidence locations

Measured environment: Python **3.13.14**, Windows-11-10.0.26300-SP0 x86-64,
**12th Gen Intel Core i5-12450H**, 12 logical CPUs, **16,890,519,552 bytes usable
physical RAM** (15.73 GiB). Runs were serial; these are local observations, not
controlled cross-machine performance estimates. The unchanged environment snapshot
is [requirements/m03b.txt](../../requirements/m03b.txt), including its EXP-001/002
includes. All **23 exact pins** matched. Key versions are OR-Tools 9.15.6755,
NumPy 2.5.5, pandas 3.1.1, protobuf 6.33.6, pytest 9.2.0 and Ruff 0.17.5.
Full installed dependency versions are recorded under the result's environment key;
no package was added, upgraded or removed in M03C.

The completed local evidence is `data/processed/m03c-verified/results.json`, its
append-only `runs.jsonl`, and 36 input JSONs in `instances/`. Those generated bulk
files are intentionally ignored. Deterministic case/proposal/proof fields are
separate from measurements and environment. Expanded-design SHA-256 is
`30853dc0119f52aa264a0b01a6671c682411d05d4c968bf72db635e8fe8dc7aa`.
The original fixed configuration is unchanged; per-instance hashes appear below.

## Interpretation and practical limits

Small (8-order/16-operation) workloads completed all **54/54** full proofs. At one
second per phase all 18 runs proved optimal, with optimizer median **0.1456 s** and
maximum **0.2993 s**. Increasing the cap produced no objective gain in these cases.
Greedy's verified total median was **0.0053 s** across small runs. Two small
high-pressure runs per budget tie greedy; those provide no objective benefit from
the additional optimizer runtime. The reported scope is this nine-instance family.

Medium (24-order/72-operation) workloads are budget-sensitive. At one second,
six runs have no incumbent and five are worse than greedy. At five seconds,
17/18 beat greedy but only 6/18 complete proofs. At ten seconds, all 18 beat greedy
but only 8/18 complete proofs; optimizer median is **10.0911 s**, maximum
**20.6617 s**, versus greedy's verified total median **0.0274 s** across medium
runs. A per-phase cap is not a total request-latency cap. Longer-budget available
incumbents did not regress lexicographically within a repetition in this audit;
this does not establish a general monotonic-quality guarantee.

Large (60-order/180-operation) workloads produced **53/54 UNKNOWN** outcomes and
one unproven incumbent, which was worse than greedy. No run proved any objective.
Ten-second optimizer median was **10.1420 s**, while verified greedy total median
was **0.1057 s** across large runs. The native incumbent is not a useful replacement
for greedy on this tested family; the extra runtime usually yields no proposal.
The single available incumbent disappears in its repeated run, further limiting
reliability. Do not infer mathematical infeasibility from these outcomes.

Native model size rises from **104–185 variables / 206–449 constraints** (small),
to **683–1,087 / 1,641–2,853** (medium), to **2,617–4,250 / 6,834–11,733** (large).
Eligible alternatives span **37–118**, **416–820** and **1,954–3,587**, respectively.
Higher pressure often prunes more fragment alternatives because entire batches no
longer fit; it does not simply make every search harder. These bundled size tiers
change horizon/resources too, so no asymptotic scaling exponent is claimed.

Sizing-pass median was **0.0452 s** overall (maximum **0.2329 s**). Additional
candidate-verifier median was **0.001728 s** (maximum **0.007784 s**). Search and
proof completion, rather than model construction or checking, dominate the observed
medium/large latency. Some UNKNOWN returns occur before the numerical wall cap;
exposed status/timing fields do not identify every internal stopping decision.
Recorded per-phase deterministic work never exceeded **0.807781**, below the
configured 1.0 cap; wall time and internal checks still limit these runs. No exact
stop-cause or invented optimality-gap claim is made.

Peak job committed memory was **441.015625 MiB**, below the **768 MiB** hard cap;
maximum sampled working-set peak was **115.949219 MiB**. No actual memory failure
was observed. The stress tier has **750 operations**, **280 assignments**,
**1,120 working fragments** and a **168,000-alternative structural upper bound**,
exceeding both declared 300-operation and 20,000-alternative guards. Native stress
dimensions, solve time and optimality are unmeasured. Greedy still ran and verified
for all nine stress inputs (verified total median **3.6089 s**). This is an explicit
audit-envelope exclusion, not a claim that the hardware cannot run those models.

## Reproducibility and recommended settings

The generator produces identical input fingerprints on repeated construction.
Across **81 actually repeated primary budget pairs**, **71 matched all non-runtime
fields and 10 differed**: nine medium pairs and one large pair. All **27 small
pairs matched**. Cached stress skips are not counted as independent solver repeats.
The complete repeated outcomes are preserved below; no result is averaged away.
One five-second medium case changes from WORSE to BETTER and two one-second medium
cases change from FEASIBLE to fully proven. The 60-order incumbent changes to UNKNOWN.
Fixed seed/one worker is therefore insufficient for exact wall-limited repeatability.
No timing-based tuning or model promotion follows from this audit.

For this small synthetic family, seed42/worker1/deterministic1.0 with **1 s/phase**
was sufficient; it is a measured workload-specific setting, not a new engine default.
For medium workloads, **10 s/phase** is the best tested cap for incumbent quality,
but consumers must accept variable latency and incomplete proof, independently
verify the result and compare it with greedy. For these 60-order workloads, use the
verified reference for a bounded local response rather than assuming CP-SAT produces
a useful incumbent. The optimizer defaults and all model settings remain unchanged.

M04 may proceed only as a scoped local integration milestone that preserves resource
limits, explicit proof/abstention statuses and same-instance reference comparison.
These observations do **not** justify treating CP-SAT as a reliable general-purpose
60-order production scheduler. An optimizer-dependent larger-workload promise remains
gated on a separately authorized study; no M04 or optimization changes start here.

## Reproduction and verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/m03b.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.benchmarks `
  --config configs/m03c_benchmark.json `
  --output-dir data/processed/m03c-new-run

.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
```

Use a new output directory; existing results/journals are never overwritten. No
network is used by benchmark execution. Installation alone needs a package index.
The fixed design contains both repetitions; do not run only selected easy cells.

Full pytest: **716 passed in 63.28 s** (639 existing + 77 benchmark cases).
Native guard and watchdog tests, schema round trips, reproducibility, controlled
FEASIBLE/UNKNOWN/fallback injection, invalid-result/objective rejection and no
protected ML access passed. All six legacy M03B CLI outputs matched their saved
non-runtime results; the full suite protects the five original M03A stdout hashes.
The unchanged model/solver/reference/verifier/metrics and earlier contracts/reports
are among **133 matching protected file fingerprints**. All old instruction/ignore
rules remain unchanged. The original final-test boundary and M01 artifacts are not
consumed by the benchmark. No new dependencies are introduced.

Final Ruff lint passed; Ruff format check passed with **126 files already formatted**;
`pip check` reported **no broken requirements**. All 23 exact pins matched.
Repeated native results are **not** universally identical:
the 10 differences are measured limitations, not a passed exact-repeatability claim.

Development failures were resolved explicitly: the first active-process guard
blocked Windows' two-process venv launcher; an unnamed nested-job query subsequently
caused two guard/CLI tests to fail before the explicit named-job check was added.
The first matrix execution was interrupted at 121 rows for the launch-race fix,
retained separately and excluded from the completed 216-row study. No instance,
solver parameter, objective or constraint was changed in response to performance.

## Repeated-pair differences

O = OPTIMAL, F = FEASIBLE, U = UNKNOWN. Tuples use the frozen objective order. These are all ten non-runtime mismatches; no mismatching pair was removed.

| Instance | Wall s/phase | Repetition 1 tuple | Repetition 2 tuple | Phase states 1 | Phase states 2 |
| --- | --- | --- | --- | --- | --- |
| medium-p45-s42 | 10 | (0,0,2186) | (0,0,2196) | O/O/F | O/O/F |
| medium-p45-s73 | 5 | (12,8831,2279) | (0,0,2230) | F | O/O/F |
| medium-p90-s19 | 1 | (245,5784,2279) | (203,5610,2279) | F | F |
| medium-p90-s42 | 1 | (267,3519,2279) | (204,5761,2279) | F | F |
| medium-p90-s42 | 5 | (139,6335,2280) | (133,4701,2280) | F | F |
| medium-p90-s73 | 1 | (220,7563,2279) | (215,7603,2279) | F | F |
| medium-p90-s73 | 5 | (136,5999,2276) | (133,6049,2276) | F | F |
| medium-p135-s19 | 1 | (282,2508,2280) | (279,0,2280) | F | O/O/O |
| medium-p135-s73 | 1 | (268,5260,2278) | (267,5260,2280) | F | O/O/O |
| large-p135-s42 | 10 | (863,21512,3720) | - | F | U |

## Generator contract and measurement interpretation

`loometric.benchmarks.generation.GenerationConfig` declares every input, including
order/line/stage counts, horizon days, shifts per day, compatibility, quantity and
unscaled standard ranges, priority sampling weights, release spread/due slack,
breaks/downtime, load target, start date and seed. The default expanded configuration
is recorded in result JSON; no external configuration or execution clock enters
instance generation. A local `random.Random` avoids mutating global random state.

Three styles share the first N stages of the existing Stage enumeration. Lines are
distributed cyclically across those stages with hypothetical dedicated crews of
4–8 workers and efficiencies 0.75/0.85/1.0. Each style/stage explicitly declares the
requested number of compatible lines. Orders draw quantities uniformly from 10–25,
unscaled stage standards from 2–5 worker-minutes/piece, and priorities from
(1,1,2,2,3), preserving that sampling multiplicity. When load scaling is enabled,
it supersedes the absolute unscaled standard range; `target_load_percent=None`
retains the literal standards. No learned or target-derived aggregate is used.

The fixed +03:00 synthetic calendar starts 2030-01-07. Horizons begin at local
midnight, with 360-minute shifts at 08:00 (and 16:00 for two-shift configurations).
Each shift has explicit 15-minute breaks at offsets 120 and 240. Each line/shift
has a 10-minute planned stoppage at offset 180 + 5*(line_index mod 3). The resulting
four fragments provide 320 working minutes per assignment. Primary releases are
spread over days 0–min(1,horizon_days-1); due dates are release plus zero or one day.
Releases/deadlines retain the unchanged hard/soft scheduling semantics.

Identifiers derive from generator version and expanded configuration, with stable
collection order. Full SHA-256 fingerprints use the existing canonical typed-input
helper. A lossless instance serializer emits Decimal values as JSON numeric tokens,
so files round-trip through the unchanged strict scheduling parser. Versioned small
fixture: examples/scheduling-scalability/representative.json. Bulk files stay ignored.

Sizing calls the existing model builder once, counts its actual variables,
constraints and optional intervals, discards it and collects garbage before the
unchanged optimizer builds its own. Initial model counts exclude at most two later
objective-fixing equalities. Structural alternative upper bounds count compatible
fragments before release/duration pruning. Sizing overhead is measured separately;
it is not included in optimizer runtime. No constraints are reimplemented here.

The worker separately dispatches, verifies and calculates reference metrics. Every
returned optimizer proposal receives another unchanged independent verification and
metric recomputation; its complete objective vector must match. Invalid candidates
lose accepted metrics and cannot participate in comparisons. The extra audit call's
time is measured separately; internal optimizer verification remains included in
its total. Reference metrics calculation also re-verifies by existing design.

Whole-child wall time includes interpreter/imports, generation, sizing, reference,
optimization, audits and serialization. Native solver wall time includes presolve;
deterministic time is an internal work measure, not seconds. Either per-phase limit
can stop search; the status alone does not identify which stop rule fired. The
60-second external watchdog also bounds preparation and checking. A stopped or
unknown search is not a proof of infeasibility. Peak committed memory is measured
over the Windows job lifetime (launcher plus interpreter); the child's working-set
peak is sampled before final JSON serialization. These quantities are distinct and
are not solver-only memory. Linux's RLIMIT_AS implementation is not locally tested.

The local resource-envelope skip does not establish that 150-order optimization is
physically impossible on this hardware. That tier exceeds declared static limits;
its native scalability remains unmeasured. Size tiers also change resources, stages
and horizon, so this is a study of specified workloads, not an isolated asymptotic
order-count experiment. Repeated runs share identical synthetic inputs and are not
independent factory observations. No confidence intervals or significance claims.

Windows boundary references: [job memory fields](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information),
[explicit job membership](https://learn.microsoft.com/en-us/windows/win32/api/jobapi/nf-jobapi-isprocessinjob),
and [thread resume semantics](https://learn.microsoft.com/en-us/windows/desktop/api/processthreadsapi/nf-processthreadsapi-resumethread).

## Measured matrix summary

| Tier | Wall s/phase | Rows | Incumbents | Full proofs | Better | Tie | Worse | No comparable | Median optimizer s | Max optimizer s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small | 1 | 18 | 18 | 18 | 16 | 2 | 0 | 0 | 0.1456 | 0.2993 |
| small | 5 | 18 | 18 | 18 | 16 | 2 | 0 | 0 | 0.1390 | 0.4209 |
| small | 10 | 18 | 18 | 18 | 16 | 2 | 0 | 0 | 0.1380 | 0.3798 |
| medium | 1 | 18 | 12 | 2 | 7 | 0 | 5 | 6 | 1.0629 | 2.5501 |
| medium | 5 | 18 | 18 | 6 | 17 | 0 | 1 | 0 | 5.0825 | 11.3655 |
| medium | 10 | 18 | 18 | 8 | 18 | 0 | 0 | 0 | 10.0911 | 20.6617 |
| large | 1 | 18 | 0 | 0 | 0 | 0 | 0 | 18 | 1.1482 | 1.1817 |
| large | 5 | 18 | 0 | 0 | 0 | 0 | 0 | 18 | 4.6306 | 5.1261 |
| large | 10 | 18 | 1 | 0 | 0 | 0 | 1 | 17 | 10.1420 | 10.1709 |
| stress | 1 | 18 | 0 | 0 | 0 | 0 | 0 | 18 | - | - |
| stress | 5 | 18 | 0 | 0 | 0 | 0 | 0 | 18 | - | - |
| stress | 10 | 18 | 0 | 0 | 0 | 0 | 0 | 18 | - | - |

## Actual instance identities and dimensions

Model variables/constraints describe the initial native model; proven higher phases add at most two equality constraints. Skipped stress native counts are unmeasured, not zero.

| Instance | Operations | Assignments | Working fragments | Alternative upper bound | Eligible alternatives | Variables | Constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| small-p45-s19 | 16 | 4 | 16 | 128 | 113 | 180 | 434 |
| small-p45-s42 | 16 | 4 | 16 | 128 | 118 | 185 | 449 |
| small-p45-s73 | 16 | 4 | 16 | 128 | 114 | 181 | 437 |
| small-p90-s19 | 16 | 4 | 16 | 128 | 67 | 134 | 296 |
| small-p90-s42 | 16 | 4 | 16 | 128 | 65 | 132 | 290 |
| small-p90-s73 | 16 | 4 | 16 | 128 | 68 | 135 | 299 |
| small-p135-s19 | 16 | 4 | 16 | 128 | 44 | 111 | 227 |
| small-p135-s42 | 16 | 4 | 16 | 128 | 42 | 109 | 221 |
| small-p135-s73 | 16 | 4 | 16 | 128 | 37 | 104 | 206 |
| medium-p45-s19 | 72 | 12 | 48 | 1152 | 799 | 1066 | 2790 |
| medium-p45-s42 | 72 | 12 | 48 | 1152 | 820 | 1087 | 2853 |
| medium-p45-s73 | 72 | 12 | 48 | 1152 | 771 | 1038 | 2706 |
| medium-p90-s19 | 72 | 12 | 48 | 1152 | 638 | 905 | 2307 |
| medium-p90-s42 | 72 | 12 | 48 | 1152 | 619 | 886 | 2250 |
| medium-p90-s73 | 72 | 12 | 48 | 1152 | 585 | 852 | 2148 |
| medium-p135-s19 | 72 | 12 | 48 | 1152 | 431 | 698 | 1686 |
| medium-p135-s42 | 72 | 12 | 48 | 1152 | 416 | 683 | 1641 |
| medium-p135-s73 | 72 | 12 | 48 | 1152 | 418 | 685 | 1647 |
| large-p45-s19 | 180 | 27 | 108 | 4320 | 3587 | 4250 | 11733 |
| large-p45-s42 | 180 | 27 | 108 | 4320 | 3416 | 4079 | 11220 |
| large-p45-s73 | 180 | 27 | 108 | 4320 | 3474 | 4137 | 11394 |
| large-p90-s19 | 180 | 27 | 108 | 4320 | 2941 | 3604 | 9795 |
| large-p90-s42 | 180 | 27 | 108 | 4320 | 2735 | 3398 | 9177 |
| large-p90-s73 | 180 | 27 | 108 | 4320 | 2819 | 3482 | 9429 |
| large-p135-s19 | 180 | 27 | 108 | 4320 | 2153 | 2816 | 7431 |
| large-p135-s42 | 180 | 27 | 108 | 4320 | 1954 | 2617 | 6834 |
| large-p135-s73 | 180 | 27 | 108 | 4320 | 2047 | 2710 | 7113 |
| stress-p45-s19 | 750 | 280 | 1120 | 168000 | - | - | - |
| stress-p45-s42 | 750 | 280 | 1120 | 168000 | - | - | - |
| stress-p45-s73 | 750 | 280 | 1120 | 168000 | - | - | - |
| stress-p90-s19 | 750 | 280 | 1120 | 168000 | - | - | - |
| stress-p90-s42 | 750 | 280 | 1120 | 168000 | - | - | - |
| stress-p90-s73 | 750 | 280 | 1120 | 168000 | - | - | - |
| stress-p135-s19 | 750 | 280 | 1120 | 168000 | - | - | - |
| stress-p135-s42 | 750 | 280 | 1120 | 168000 | - | - | - |
| stress-p135-s73 | 750 | 280 | 1120 | 168000 | - | - | - |

## Same-instance greedy reference results

All reference proposals passed the unchanged verifier, including the nine stress audit inputs. Stress reference work ran once per instance and was explicitly reused across skipped cells.

| Instance | Completed orders | Finished units | Unfinished units | On time | Late | Weighted tardiness min | Total tardiness min | Makespan min | Line utilization % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small-p45-s19 | 7 | 133 | 25 | 7 | 0 | 0 | 0 | 789 | 38.4375 |
| small-p45-s42 | 7 | 129 | 24 | 7 | 0 | 0 | 0 | 793 | 40.6250 |
| small-p45-s73 | 8 | 147 | 0 | 8 | 0 | 0 | 0 | 801 | 45.8594 |
| small-p90-s19 | 4 | 70 | 88 | 4 | 0 | 0 | 0 | 809 | 41.8750 |
| small-p90-s42 | 3 | 42 | 111 | 3 | 0 | 0 | 0 | 811 | 36.9531 |
| small-p90-s73 | 4 | 67 | 80 | 4 | 0 | 0 | 0 | 823 | 53.0469 |
| small-p135-s19 | 2 | 38 | 120 | 2 | 0 | 0 | 0 | 823 | 34.5312 |
| small-p135-s42 | 2 | 32 | 121 | 2 | 0 | 0 | 0 | 838 | 50.2344 |
| small-p135-s73 | 3 | 45 | 102 | 3 | 0 | 0 | 0 | 825 | 40.5469 |
| medium-p45-s19 | 24 | 472 | 0 | 24 | 0 | 0 | 0 | 2265 | 44.9219 |
| medium-p45-s42 | 24 | 451 | 0 | 24 | 0 | 0 | 0 | 2220 | 45.3385 |
| medium-p45-s73 | 24 | 421 | 0 | 24 | 0 | 0 | 0 | 2264 | 45.1823 |
| medium-p90-s19 | 15 | 275 | 197 | 13 | 2 | 2708 | 1077 | 2280 | 59.6094 |
| medium-p90-s42 | 13 | 240 | 211 | 13 | 0 | 0 | 0 | 2279 | 59.7917 |
| medium-p90-s73 | 13 | 219 | 202 | 11 | 2 | 3252 | 1084 | 2267 | 61.1198 |
| medium-p135-s19 | 9 | 154 | 318 | 8 | 1 | 1180 | 590 | 2280 | 50.7552 |
| medium-p135-s42 | 6 | 100 | 351 | 4 | 2 | 4014 | 1338 | 2269 | 43.0990 |
| medium-p135-s73 | 4 | 71 | 350 | 1 | 3 | 6576 | 2192 | 2277 | 48.5156 |
| large-p45-s19 | 60 | 1126 | 0 | 59 | 1 | 510 | 510 | 3371 | 46.3773 |
| large-p45-s42 | 60 | 1064 | 0 | 56 | 4 | 2064 | 2064 | 3426 | 45.9954 |
| large-p45-s73 | 60 | 1026 | 0 | 59 | 1 | 508 | 508 | 3388 | 45.1505 |
| large-p90-s19 | 39 | 733 | 393 | 25 | 14 | 25820 | 12245 | 3716 | 70.3125 |
| large-p90-s42 | 42 | 738 | 326 | 28 | 14 | 23652 | 10761 | 3718 | 71.2731 |
| large-p90-s73 | 43 | 718 | 308 | 31 | 12 | 22367 | 10886 | 3720 | 71.3542 |
| large-p135-s19 | 24 | 420 | 706 | 11 | 13 | 25552 | 9935 | 3719 | 61.7824 |
| large-p135-s42 | 21 | 335 | 729 | 13 | 8 | 19691 | 6741 | 3718 | 59.8611 |
| large-p135-s73 | 22 | 351 | 675 | 9 | 13 | 37091 | 12901 | 3718 | 59.8958 |
| stress-p45-s19 | 150 | 2770 | 0 | 55 | 95 | 291509 | 194830 | 6897 | 43.6094 |
| stress-p45-s42 | 150 | 2644 | 0 | 61 | 89 | 320951 | 202194 | 7023 | 43.8839 |
| stress-p45-s73 | 150 | 2671 | 0 | 63 | 87 | 282497 | 202966 | 7789 | 43.9275 |
| stress-p90-s19 | 60 | 951 | 1819 | 12 | 48 | 365130 | 152539 | 9959 | 37.9319 |
| stress-p90-s42 | 74 | 1127 | 1517 | 8 | 66 | 452089 | 207843 | 9959 | 45.8359 |
| stress-p90-s73 | 65 | 949 | 1722 | 10 | 55 | 387833 | 149601 | 9953 | 34.2969 |
| stress-p135-s19 | 17 | 223 | 2547 | 0 | 17 | 124319 | 51669 | 9949 | 23.2567 |
| stress-p135-s42 | 35 | 421 | 2223 | 3 | 32 | 163807 | 85750 | 9720 | 24.5513 |
| stress-p135-s73 | 32 | 381 | 2290 | 4 | 28 | 163233 | 80223 | 9947 | 20.6317 |

## Complete optimizer results

Each entry represents one actual primary child run. Tuples are (unfinished units, weighted tardiness minutes, makespan minutes). Phase entries are STATUS:incumbent/bound in objective order; a dash is absent, not zero. Bounds for later phases are conditional on earlier proven optima. Full proof requires three proven levels. Native time sums solver wall time; optimizer total also includes construction, adaptation, internal verification and metrics. The audit-verifier column is a separate extra verifier call. Memory is lifetime aggregate job peak committed MiB, including the Windows launcher; it is not peak working set or solver-only allocation.

### Repetition 1, 1 seconds per phase

| Instance | Status | vs greedy | Proof levels | Incumbent tuple | Phase value/bound | Optimizer s | Native s | Audit verify s | Peak commit MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small-p45-s19 | VALID_COMPLETE | BETTER | 3 | (0,0,789) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:789/789 | 0.2715 | 0.2094 | 0.0012 | 410.96 |
| small-p45-s42 | VALID_COMPLETE | BETTER | 3 | (0,0,706) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:706/706 | 0.2719 | 0.2353 | 0.0012 | 410.79 |
| small-p45-s73 | VALID_COMPLETE | BETTER | 3 | (0,0,716) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:716/716 | 0.2413 | 0.2075 | 0.0010 | 409.99 |
| small-p90-s19 | VALID_PARTIAL | BETTER | 3 | (50,0,827) | OPTIMAL:50/50; OPTIMAL:0/0; OPTIMAL:827/827 | 0.1159 | 0.0796 | 0.0011 | 410.38 |
| small-p90-s42 | VALID_PARTIAL | BETTER | 3 | (88,0,816) | OPTIMAL:88/88; OPTIMAL:0/0; OPTIMAL:816/816 | 0.1527 | 0.1117 | 0.0008 | 410.41 |
| small-p90-s73 | VALID_PARTIAL | BETTER | 3 | (65,0,819) | OPTIMAL:65/65; OPTIMAL:0/0; OPTIMAL:819/819 | 0.1680 | 0.1163 | 0.0009 | 410.50 |
| small-p135-s19 | VALID_PARTIAL | BETTER | 3 | (113,0,820) | OPTIMAL:113/113; OPTIMAL:0/0; OPTIMAL:820/820 | 0.0759 | 0.0395 | 0.0008 | 410.69 |
| small-p135-s42 | VALID_PARTIAL | BETTER | 3 | (114,0,837) | OPTIMAL:114/114; OPTIMAL:0/0; OPTIMAL:837/837 | 0.0869 | 0.0432 | 0.0014 | 410.21 |
| small-p135-s73 | VALID_PARTIAL | TIE | 3 | (102,0,825) | OPTIMAL:102/102; OPTIMAL:0/0; OPTIMAL:825/825 | 0.0879 | 0.0515 | 0.0009 | 410.29 |
| medium-p45-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.0823 | 0.9997 | - | 416.63 |
| medium-p45-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.0595 | 1.0008 | - | 417.30 |
| medium-p45-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.0608 | 1.0009 | - | 416.52 |
| medium-p90-s19 | VALID_PARTIAL | WORSE | 0 | (245,5784,2279) | FEASIBLE:245/24 | 1.0735 | 1.0006 | 0.0026 | 415.35 |
| medium-p90-s42 | VALID_PARTIAL | WORSE | 0 | (267,3519,2279) | FEASIBLE:267/0 | 1.0818 | 1.0007 | 0.0024 | 415.18 |
| medium-p90-s73 | VALID_PARTIAL | WORSE | 0 | (220,7563,2279) | FEASIBLE:220/25 | 1.0560 | 1.0006 | 0.0030 | 415.37 |
| medium-p135-s19 | VALID_PARTIAL | BETTER | 0 | (282,2508,2280) | FEASIBLE:282/182 | 1.0703 | 0.9998 | 0.0025 | 413.88 |
| medium-p135-s42 | VALID_PARTIAL | BETTER | 0 | (293,3945,2273) | FEASIBLE:293/107 | 1.0555 | 1.0009 | 0.0022 | 414.45 |
| medium-p135-s73 | VALID_PARTIAL | BETTER | 0 | (268,5260,2278) | FEASIBLE:268/172 | 1.0717 | 1.0006 | 0.0025 | 414.11 |
| large-p45-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1681 | 1.0130 | - | 434.88 |
| large-p45-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1696 | 1.0140 | - | 433.77 |
| large-p45-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1433 | 1.0131 | - | 434.36 |
| large-p90-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1651 | 1.0199 | - | 430.38 |
| large-p90-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 0.9494 | 0.8361 | - | 429.42 |
| large-p90-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1817 | 1.0134 | - | 429.17 |
| large-p135-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 0.7713 | 0.6604 | - | 424.80 |
| large-p135-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 0.6704 | 0.5583 | - | 423.83 |
| large-p135-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 0.7405 | 0.5760 | - | 424.78 |

### Repetition 1, 5 seconds per phase

| Instance | Status | vs greedy | Proof levels | Incumbent tuple | Phase value/bound | Optimizer s | Native s | Audit verify s | Peak commit MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small-p45-s19 | VALID_COMPLETE | BETTER | 3 | (0,0,789) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:789/789 | 0.2475 | 0.2001 | 0.0011 | 410.79 |
| small-p45-s42 | VALID_COMPLETE | BETTER | 3 | (0,0,706) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:706/706 | 0.4209 | 0.3794 | 0.0019 | 411.15 |
| small-p45-s73 | VALID_COMPLETE | BETTER | 3 | (0,0,716) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:716/716 | 0.2675 | 0.2297 | 0.0013 | 410.89 |
| small-p90-s19 | VALID_PARTIAL | BETTER | 3 | (50,0,827) | OPTIMAL:50/50; OPTIMAL:0/0; OPTIMAL:827/827 | 0.1198 | 0.0822 | 0.0010 | 410.37 |
| small-p90-s42 | VALID_PARTIAL | BETTER | 3 | (88,0,816) | OPTIMAL:88/88; OPTIMAL:0/0; OPTIMAL:816/816 | 0.1750 | 0.1168 | 0.0016 | 410.20 |
| small-p90-s73 | VALID_PARTIAL | BETTER | 3 | (65,0,819) | OPTIMAL:65/65; OPTIMAL:0/0; OPTIMAL:819/819 | 0.1413 | 0.1016 | 0.0009 | 410.57 |
| small-p135-s19 | VALID_PARTIAL | BETTER | 3 | (113,0,820) | OPTIMAL:113/113; OPTIMAL:0/0; OPTIMAL:820/820 | 0.1205 | 0.0483 | 0.0012 | 410.99 |
| small-p135-s42 | VALID_PARTIAL | BETTER | 3 | (114,0,837) | OPTIMAL:114/114; OPTIMAL:0/0; OPTIMAL:837/837 | 0.0850 | 0.0440 | 0.0009 | 410.09 |
| small-p135-s73 | VALID_PARTIAL | TIE | 3 | (102,0,825) | OPTIMAL:102/102; OPTIMAL:0/0; OPTIMAL:825/825 | 0.1366 | 0.0932 | 0.0008 | 409.88 |
| medium-p45-s19 | VALID_COMPLETE | BETTER | 2 | (0,0,2232) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2232/2029 | 8.7133 | 8.5825 | 0.0053 | 417.70 |
| medium-p45-s42 | VALID_COMPLETE | BETTER | 2 | (0,0,2196) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2196/2001 | 10.1439 | 10.0078 | 0.0040 | 417.45 |
| medium-p45-s73 | VALID_PARTIAL | WORSE | 0 | (12,8831,2279) | FEASIBLE:12/0 | 5.0952 | 5.0016 | 0.0066 | 417.46 |
| medium-p90-s19 | VALID_PARTIAL | BETTER | 0 | (129,3456,2280) | FEASIBLE:129/24 | 5.1496 | 5.0309 | 0.0077 | 417.06 |
| medium-p90-s42 | VALID_PARTIAL | BETTER | 0 | (139,6335,2280) | FEASIBLE:139/0 | 5.1039 | 5.0045 | 0.0059 | 416.44 |
| medium-p90-s73 | VALID_PARTIAL | BETTER | 0 | (136,5999,2276) | FEASIBLE:136/25 | 5.0758 | 5.0020 | 0.0059 | 416.80 |
| medium-p135-s19 | VALID_PARTIAL | BETTER | 3 | (279,0,2280) | OPTIMAL:279/279; OPTIMAL:0/0; OPTIMAL:2280/2280 | 2.7023 | 2.5978 | 0.0037 | 414.70 |
| medium-p135-s42 | VALID_PARTIAL | BETTER | 3 | (292,1767,2277) | OPTIMAL:292/292; OPTIMAL:1767/1767; OPTIMAL:2277/2277 | 4.6636 | 4.5627 | 0.0035 | 414.75 |
| medium-p135-s73 | VALID_PARTIAL | BETTER | 3 | (267,5260,2280) | OPTIMAL:267/267; OPTIMAL:5260/5260; OPTIMAL:2280/2280 | 3.0565 | 2.9514 | 0.0046 | 414.82 |
| large-p45-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 4.6886 | 4.5247 | - | 435.27 |
| large-p45-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 3.8253 | 3.6590 | - | 434.06 |
| large-p45-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 3.8290 | 3.6906 | - | 434.13 |
| large-p90-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 4.9264 | 4.7980 | - | 430.61 |
| large-p90-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 4.0844 | 3.9574 | - | 429.62 |
| large-p90-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 4.5727 | 4.4076 | - | 429.53 |
| large-p135-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/165 | 5.1143 | 5.0027 | - | 428.94 |
| large-p135-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 5.1261 | 5.0026 | - | 428.88 |
| large-p135-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 5.1045 | 5.0032 | - | 429.20 |

### Repetition 1, 10 seconds per phase

| Instance | Status | vs greedy | Proof levels | Incumbent tuple | Phase value/bound | Optimizer s | Native s | Audit verify s | Peak commit MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small-p45-s19 | VALID_COMPLETE | BETTER | 3 | (0,0,789) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:789/789 | 0.2168 | 0.1751 | 0.0014 | 410.98 |
| small-p45-s42 | VALID_COMPLETE | BETTER | 3 | (0,0,706) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:706/706 | 0.3798 | 0.3269 | 0.0019 | 411.16 |
| small-p45-s73 | VALID_COMPLETE | BETTER | 3 | (0,0,716) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:716/716 | 0.3196 | 0.2652 | 0.0010 | 410.74 |
| small-p90-s19 | VALID_PARTIAL | BETTER | 3 | (50,0,827) | OPTIMAL:50/50; OPTIMAL:0/0; OPTIMAL:827/827 | 0.1199 | 0.0803 | 0.0017 | 410.57 |
| small-p90-s42 | VALID_PARTIAL | BETTER | 3 | (88,0,816) | OPTIMAL:88/88; OPTIMAL:0/0; OPTIMAL:816/816 | 0.1573 | 0.1127 | 0.0009 | 410.60 |
| small-p90-s73 | VALID_PARTIAL | BETTER | 3 | (65,0,819) | OPTIMAL:65/65; OPTIMAL:0/0; OPTIMAL:819/819 | 0.1346 | 0.0976 | 0.0009 | 409.84 |
| small-p135-s19 | VALID_PARTIAL | BETTER | 3 | (113,0,820) | OPTIMAL:113/113; OPTIMAL:0/0; OPTIMAL:820/820 | 0.0889 | 0.0487 | 0.0008 | 409.93 |
| small-p135-s42 | VALID_PARTIAL | BETTER | 3 | (114,0,837) | OPTIMAL:114/114; OPTIMAL:0/0; OPTIMAL:837/837 | 0.0740 | 0.0378 | 0.0007 | 410.21 |
| small-p135-s73 | VALID_PARTIAL | TIE | 3 | (102,0,825) | OPTIMAL:102/102; OPTIMAL:0/0; OPTIMAL:825/825 | 0.1116 | 0.0639 | 0.0008 | 410.43 |
| medium-p45-s19 | VALID_COMPLETE | BETTER | 2 | (0,0,2214) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2214/2029 | 13.8792 | 13.7598 | 0.0068 | 420.10 |
| medium-p45-s42 | VALID_COMPLETE | BETTER | 2 | (0,0,2186) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2186/2001 | 15.1785 | 15.0474 | 0.0069 | 420.22 |
| medium-p45-s73 | VALID_COMPLETE | BETTER | 2 | (0,0,2218) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2218/2014 | 16.9038 | 16.7564 | 0.0068 | 420.20 |
| medium-p90-s19 | VALID_PARTIAL | BETTER | 3 | (113,1662,2280) | OPTIMAL:113/113; OPTIMAL:1662/1662; OPTIMAL:2280/2280 | 20.6617 | 20.4608 | 0.0059 | 417.95 |
| medium-p90-s42 | VALID_PARTIAL | BETTER | 0 | (115,5290,2280) | FEASIBLE:115/0 | 10.0928 | 10.0028 | 0.0045 | 417.38 |
| medium-p90-s73 | VALID_PARTIAL | BETTER | 0 | (122,4491,2280) | FEASIBLE:122/25 | 10.0835 | 10.0029 | 0.0061 | 419.17 |
| medium-p135-s19 | VALID_PARTIAL | BETTER | 3 | (279,0,2280) | OPTIMAL:279/279; OPTIMAL:0/0; OPTIMAL:2280/2280 | 2.7432 | 2.6445 | 0.0046 | 414.61 |
| medium-p135-s42 | VALID_PARTIAL | BETTER | 3 | (292,1767,2277) | OPTIMAL:292/292; OPTIMAL:1767/1767; OPTIMAL:2277/2277 | 4.7779 | 4.6773 | 0.0045 | 415.12 |
| medium-p135-s73 | VALID_PARTIAL | BETTER | 3 | (267,5260,2280) | OPTIMAL:267/267; OPTIMAL:5260/5260; OPTIMAL:2280/2280 | 2.9243 | 2.8336 | 0.0047 | 414.37 |
| large-p45-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1424 | 10.0035 | - | 440.74 |
| large-p45-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1709 | 10.0053 | - | 439.29 |
| large-p45-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1556 | 10.0041 | - | 438.96 |
| large-p90-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1491 | 10.0053 | - | 435.33 |
| large-p90-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1269 | 10.0045 | - | 434.84 |
| large-p90-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1380 | 10.0033 | - | 434.52 |
| large-p135-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/165 | 10.1186 | 10.0035 | - | 429.24 |
| large-p135-s42 | VALID_PARTIAL | WORSE | 0 | (863,21512,3720) | FEASIBLE:863/0 | 10.1634 | 10.0039 | 0.0062 | 428.70 |
| large-p135-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1185 | 10.0041 | - | 429.55 |

### Repetition 2, 1 seconds per phase

| Instance | Status | vs greedy | Proof levels | Incumbent tuple | Phase value/bound | Optimizer s | Native s | Audit verify s | Peak commit MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small-p45-s19 | VALID_COMPLETE | BETTER | 3 | (0,0,789) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:789/789 | 0.2170 | 0.1772 | 0.0010 | 410.57 |
| small-p45-s42 | VALID_COMPLETE | BETTER | 3 | (0,0,706) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:706/706 | 0.2993 | 0.2619 | 0.0013 | 411.05 |
| small-p45-s73 | VALID_COMPLETE | BETTER | 3 | (0,0,716) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:716/716 | 0.2751 | 0.2378 | 0.0011 | 411.01 |
| small-p90-s19 | VALID_PARTIAL | BETTER | 3 | (50,0,827) | OPTIMAL:50/50; OPTIMAL:0/0; OPTIMAL:827/827 | 0.1193 | 0.0831 | 0.0015 | 410.37 |
| small-p90-s42 | VALID_PARTIAL | BETTER | 3 | (88,0,816) | OPTIMAL:88/88; OPTIMAL:0/0; OPTIMAL:816/816 | 0.1394 | 0.1059 | 0.0008 | 410.43 |
| small-p90-s73 | VALID_PARTIAL | BETTER | 3 | (65,0,819) | OPTIMAL:65/65; OPTIMAL:0/0; OPTIMAL:819/819 | 0.1518 | 0.1170 | 0.0009 | 410.72 |
| small-p135-s19 | VALID_PARTIAL | BETTER | 3 | (113,0,820) | OPTIMAL:113/113; OPTIMAL:0/0; OPTIMAL:820/820 | 0.0795 | 0.0447 | 0.0012 | 410.45 |
| small-p135-s42 | VALID_PARTIAL | BETTER | 3 | (114,0,837) | OPTIMAL:114/114; OPTIMAL:0/0; OPTIMAL:837/837 | 0.0715 | 0.0363 | 0.0008 | 410.06 |
| small-p135-s73 | VALID_PARTIAL | TIE | 3 | (102,0,825) | OPTIMAL:102/102; OPTIMAL:0/0; OPTIMAL:825/825 | 0.0846 | 0.0511 | 0.0009 | 409.89 |
| medium-p45-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.0505 | 1.0008 | - | 416.64 |
| medium-p45-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.0516 | 1.0006 | - | 417.14 |
| medium-p45-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.0540 | 1.0010 | - | 416.52 |
| medium-p90-s19 | VALID_PARTIAL | WORSE | 0 | (203,5610,2279) | FEASIBLE:203/24 | 1.0668 | 1.0007 | 0.0028 | 415.57 |
| medium-p90-s42 | VALID_PARTIAL | BETTER | 0 | (204,5761,2279) | FEASIBLE:204/0 | 1.0628 | 1.0007 | 0.0024 | 415.44 |
| medium-p90-s73 | VALID_PARTIAL | WORSE | 0 | (215,7603,2279) | FEASIBLE:215/25 | 1.0630 | 1.0006 | 0.0026 | 415.47 |
| medium-p135-s19 | VALID_PARTIAL | BETTER | 3 | (279,0,2280) | OPTIMAL:279/279; OPTIMAL:0/0; OPTIMAL:2280/2280 | 2.1562 | 2.0709 | 0.0047 | 414.42 |
| medium-p135-s42 | VALID_PARTIAL | BETTER | 0 | (293,3945,2273) | FEASIBLE:293/107 | 1.0540 | 1.0010 | 0.0023 | 414.25 |
| medium-p135-s73 | VALID_PARTIAL | BETTER | 3 | (267,5260,2280) | OPTIMAL:267/267; OPTIMAL:5260/5260; OPTIMAL:2280/2280 | 2.5501 | 2.4614 | 0.0049 | 414.66 |
| large-p45-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1635 | 1.0161 | - | 434.75 |
| large-p45-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1563 | 1.0131 | - | 433.80 |
| large-p45-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1505 | 1.0136 | - | 434.54 |
| large-p90-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1494 | 1.0123 | - | 430.30 |
| large-p90-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1564 | 1.0167 | - | 429.42 |
| large-p90-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 1.1470 | 1.0189 | - | 429.29 |
| large-p135-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 0.7015 | 0.6016 | - | 425.21 |
| large-p135-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 0.7266 | 0.5986 | - | 424.04 |
| large-p135-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 0.7187 | 0.6090 | - | 424.88 |

### Repetition 2, 5 seconds per phase

| Instance | Status | vs greedy | Proof levels | Incumbent tuple | Phase value/bound | Optimizer s | Native s | Audit verify s | Peak commit MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small-p45-s19 | VALID_COMPLETE | BETTER | 3 | (0,0,789) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:789/789 | 0.2183 | 0.1797 | 0.0010 | 410.93 |
| small-p45-s42 | VALID_COMPLETE | BETTER | 3 | (0,0,706) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:706/706 | 0.3058 | 0.2684 | 0.0011 | 410.84 |
| small-p45-s73 | VALID_COMPLETE | BETTER | 3 | (0,0,716) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:716/716 | 0.2667 | 0.2275 | 0.0011 | 410.76 |
| small-p90-s19 | VALID_PARTIAL | BETTER | 3 | (50,0,827) | OPTIMAL:50/50; OPTIMAL:0/0; OPTIMAL:827/827 | 0.1170 | 0.0817 | 0.0010 | 410.14 |
| small-p90-s42 | VALID_PARTIAL | BETTER | 3 | (88,0,816) | OPTIMAL:88/88; OPTIMAL:0/0; OPTIMAL:816/816 | 0.1459 | 0.1069 | 0.0008 | 410.41 |
| small-p90-s73 | VALID_PARTIAL | BETTER | 3 | (65,0,819) | OPTIMAL:65/65; OPTIMAL:0/0; OPTIMAL:819/819 | 0.1365 | 0.1034 | 0.0015 | 410.12 |
| small-p135-s19 | VALID_PARTIAL | BETTER | 3 | (113,0,820) | OPTIMAL:113/113; OPTIMAL:0/0; OPTIMAL:820/820 | 0.0813 | 0.0474 | 0.0009 | 409.80 |
| small-p135-s42 | VALID_PARTIAL | BETTER | 3 | (114,0,837) | OPTIMAL:114/114; OPTIMAL:0/0; OPTIMAL:837/837 | 0.0761 | 0.0411 | 0.0008 | 410.18 |
| small-p135-s73 | VALID_PARTIAL | TIE | 3 | (102,0,825) | OPTIMAL:102/102; OPTIMAL:0/0; OPTIMAL:825/825 | 0.0919 | 0.0579 | 0.0008 | 410.48 |
| medium-p45-s19 | VALID_COMPLETE | BETTER | 2 | (0,0,2232) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2232/2029 | 8.4090 | 8.2879 | 0.0065 | 417.42 |
| medium-p45-s42 | VALID_COMPLETE | BETTER | 2 | (0,0,2196) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2196/2001 | 9.6556 | 9.5331 | 0.0069 | 417.29 |
| medium-p45-s73 | VALID_COMPLETE | BETTER | 2 | (0,0,2230) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2230/2014 | 11.3655 | 11.2414 | 0.0067 | 417.25 |
| medium-p90-s19 | VALID_PARTIAL | BETTER | 0 | (129,3456,2280) | FEASIBLE:129/24 | 5.0865 | 5.0057 | 0.0062 | 417.04 |
| medium-p90-s42 | VALID_PARTIAL | BETTER | 0 | (133,4701,2280) | FEASIBLE:133/0 | 5.0783 | 5.0016 | 0.0058 | 416.08 |
| medium-p90-s73 | VALID_PARTIAL | BETTER | 0 | (133,6049,2276) | FEASIBLE:133/25 | 5.0784 | 5.0015 | 0.0061 | 416.80 |
| medium-p135-s19 | VALID_PARTIAL | BETTER | 3 | (279,0,2280) | OPTIMAL:279/279; OPTIMAL:0/0; OPTIMAL:2280/2280 | 2.2000 | 2.1030 | 0.0050 | 413.96 |
| medium-p135-s42 | VALID_PARTIAL | BETTER | 3 | (292,1767,2277) | OPTIMAL:292/292; OPTIMAL:1767/1767; OPTIMAL:2277/2277 | 4.2606 | 4.1651 | 0.0049 | 414.91 |
| medium-p135-s73 | VALID_PARTIAL | BETTER | 3 | (267,5260,2280) | OPTIMAL:267/267; OPTIMAL:5260/5260; OPTIMAL:2280/2280 | 2.5530 | 2.4577 | 0.0045 | 414.01 |
| large-p45-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 3.8883 | 3.7437 | - | 434.84 |
| large-p45-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 3.4646 | 3.3207 | - | 434.00 |
| large-p45-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 3.5501 | 3.3779 | - | 434.59 |
| large-p90-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 4.7145 | 4.5750 | - | 430.79 |
| large-p90-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 4.1695 | 4.0277 | - | 429.50 |
| large-p90-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 4.2108 | 4.0844 | - | 429.56 |
| large-p135-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/165 | 5.1206 | 5.0031 | - | 429.14 |
| large-p135-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 5.1155 | 5.0029 | - | 429.27 |
| large-p135-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 5.1208 | 5.0033 | - | 429.16 |

### Repetition 2, 10 seconds per phase

| Instance | Status | vs greedy | Proof levels | Incumbent tuple | Phase value/bound | Optimizer s | Native s | Audit verify s | Peak commit MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small-p45-s19 | VALID_COMPLETE | BETTER | 3 | (0,0,789) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:789/789 | 0.2369 | 0.1980 | 0.0010 | 410.82 |
| small-p45-s42 | VALID_COMPLETE | BETTER | 3 | (0,0,706) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:706/706 | 0.2994 | 0.2570 | 0.0014 | 410.42 |
| small-p45-s73 | VALID_COMPLETE | BETTER | 3 | (0,0,716) | OPTIMAL:0/0; OPTIMAL:0/0; OPTIMAL:716/716 | 0.2660 | 0.2270 | 0.0011 | 410.74 |
| small-p90-s19 | VALID_PARTIAL | BETTER | 3 | (50,0,827) | OPTIMAL:50/50; OPTIMAL:0/0; OPTIMAL:827/827 | 0.1201 | 0.0849 | 0.0009 | 410.24 |
| small-p90-s42 | VALID_PARTIAL | BETTER | 3 | (88,0,816) | OPTIMAL:88/88; OPTIMAL:0/0; OPTIMAL:816/816 | 0.1559 | 0.1156 | 0.0008 | 410.46 |
| small-p90-s73 | VALID_PARTIAL | BETTER | 3 | (65,0,819) | OPTIMAL:65/65; OPTIMAL:0/0; OPTIMAL:819/819 | 0.1415 | 0.1059 | 0.0010 | 410.32 |
| small-p135-s19 | VALID_PARTIAL | BETTER | 3 | (113,0,820) | OPTIMAL:113/113; OPTIMAL:0/0; OPTIMAL:820/820 | 0.0817 | 0.0432 | 0.0008 | 410.56 |
| small-p135-s42 | VALID_PARTIAL | BETTER | 3 | (114,0,837) | OPTIMAL:114/114; OPTIMAL:0/0; OPTIMAL:837/837 | 0.0724 | 0.0384 | 0.0008 | 410.34 |
| small-p135-s73 | VALID_PARTIAL | TIE | 3 | (102,0,825) | OPTIMAL:102/102; OPTIMAL:0/0; OPTIMAL:825/825 | 0.0929 | 0.0560 | 0.0008 | 409.86 |
| medium-p45-s19 | VALID_COMPLETE | BETTER | 2 | (0,0,2214) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2214/2029 | 13.3769 | 13.2538 | 0.0078 | 419.95 |
| medium-p45-s42 | VALID_COMPLETE | BETTER | 2 | (0,0,2196) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2196/2001 | 14.7954 | 14.6702 | 0.0067 | 419.80 |
| medium-p45-s73 | VALID_COMPLETE | BETTER | 2 | (0,0,2218) | OPTIMAL:0/0; OPTIMAL:0/0; FEASIBLE:2218/2014 | 16.2973 | 16.1706 | 0.0054 | 420.13 |
| medium-p90-s19 | VALID_PARTIAL | BETTER | 3 | (113,1662,2280) | OPTIMAL:113/113; OPTIMAL:1662/1662; OPTIMAL:2280/2280 | 19.8169 | 19.6918 | 0.0060 | 417.71 |
| medium-p90-s42 | VALID_PARTIAL | BETTER | 0 | (115,5290,2280) | FEASIBLE:115/0 | 10.0894 | 10.0023 | 0.0059 | 418.02 |
| medium-p90-s73 | VALID_PARTIAL | BETTER | 0 | (122,4491,2280) | FEASIBLE:122/25 | 10.0822 | 10.0021 | 0.0073 | 419.44 |
| medium-p135-s19 | VALID_PARTIAL | BETTER | 3 | (279,0,2280) | OPTIMAL:279/279; OPTIMAL:0/0; OPTIMAL:2280/2280 | 2.1621 | 2.0690 | 0.0052 | 414.45 |
| medium-p135-s42 | VALID_PARTIAL | BETTER | 3 | (292,1767,2277) | OPTIMAL:292/292; OPTIMAL:1767/1767; OPTIMAL:2277/2277 | 4.3260 | 4.2339 | 0.0045 | 414.76 |
| medium-p135-s73 | VALID_PARTIAL | BETTER | 3 | (267,5260,2280) | OPTIMAL:267/267; OPTIMAL:5260/5260; OPTIMAL:2280/2280 | 2.7417 | 2.6403 | 0.0042 | 414.28 |
| large-p45-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1662 | 10.0040 | - | 441.02 |
| large-p45-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1410 | 10.0029 | - | 439.54 |
| large-p45-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1491 | 10.0037 | - | 439.38 |
| large-p90-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1424 | 10.0038 | - | 435.75 |
| large-p90-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1416 | 10.0037 | - | 435.17 |
| large-p90-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1404 | 10.0037 | - | 433.97 |
| large-p135-s19 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/165 | 10.1224 | 10.0028 | - | 429.38 |
| large-p135-s42 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1489 | 10.0043 | - | 429.27 |
| large-p135-s73 | UNKNOWN | NO_COMPARABLE_INCUMBENT | 0 | - | UNKNOWN:-/0 | 10.1094 | 10.0033 | - | 429.71 |

All 54 stress rows (nine instances × three budgets × two repetitions) are SKIPPED_RESOURCE_LIMIT, NO_COMPARABLE_INCUMBENT, no optimizer metrics, no phases and no native proof. Reason in every case: operations=750 exceeds declared limit 300. Nine actual guarded reference/structural audits supply the skip rows; other stress rows explicitly identify their source and contain no invented repeated timing. No instance was removed after seeing outcomes.

## Input fingerprints

SHA-256 uses the existing canonical typed SchedulingInstance fingerprint. Generator configuration and version are recorded in the bulk JSON; changing collection order is an identity change.

| Instance | SHA-256 |
| --- | --- |
| small-p45-s19 | b33afb8c9cb36b271617a1b280c1a924d7599b96f2a93bc0fd9c79ead9f2a1e2 |
| small-p45-s42 | 38f9ccac4277608f81cf640ac86a5aba62b00bbe62d3d3efc69a427d2e3fc629 |
| small-p45-s73 | 2ee9fb7cfd4b7631ada738178fc91a90f8e24725ebbb5492de51c7f6eeef40b4 |
| small-p90-s19 | bdb5c4cfde2bb15d0980d708a9fc20b3abecd0babe7a4e4508a6965bd7d4be4f |
| small-p90-s42 | e653938b53f7b6448a1a036a5827adc361d181e5bc245d0fdeb930fabde187ba |
| small-p90-s73 | 501a11e7ab77eae2ed31914472e35bfa03e267fba02055346faf892a9d99bad0 |
| small-p135-s19 | ef4a168a294429788205a8cc679c8d3ced401d3806c37de956ce0a4a3f14fcde |
| small-p135-s42 | 6da30e21e74bb9c3c924c3b8f49a2ba2d3183452517f8aeae67d6291732837f2 |
| small-p135-s73 | 1a6ca521019febfaac6b7249d048dc9a0cbe43a11c9b9aac7954cbec33e62af2 |
| medium-p45-s19 | 3b9c76a8fbffa7587ba864fbc19df0caf2fcb56f0ce2c694f5017cf0c5e916b0 |
| medium-p45-s42 | 22404221e89cfefe3d0bd3a6e6a2df41f6f192211f3f14966226eda3d7ffe120 |
| medium-p45-s73 | 62cd507c4508f1f71848ef8603c9adf91c0dfb3fabb8523c93879edfc88cef03 |
| medium-p90-s19 | 4a8e6b009ab702fff34712d8382ead6653e8aaa710b87e879a055a2c5a8ba854 |
| medium-p90-s42 | 9d7074d61693d1ed6cb6718ed5b15f2694fe5228eee7c8d3d47a0b71b02a9a4b |
| medium-p90-s73 | dcdb73b0b79df0c6ec5a08e56d7ca8a97d085919b41adce9186d39b986554dc8 |
| medium-p135-s19 | e860313723fe139e55cbe147cd5b8c904faa455721df44ae1fe955e2a3532ea3 |
| medium-p135-s42 | deb19831caf2fff9d14e57c2b7e0de03561c3654e07f938c2ec7375b8e8eefe5 |
| medium-p135-s73 | 813397cb865553a21417118d313bd9f31075ef7a93430a29806ef8b49d902eae |
| large-p45-s19 | 1b26ea9ccc0d514d01dc1b73db0c2d98d9e0ea507b423d18f0b79b83eeaacee3 |
| large-p45-s42 | f131c41d56c8255eb2cb9c8fab10d1153bddfc0b4bbc6e0ec814d95f7bc2b1f6 |
| large-p45-s73 | 12e04a40d898e0aa7d946d6856e1e75ef17e8604b9cdebee6649645015b1f408 |
| large-p90-s19 | 5d79ac27ad4af8333e2dbf652618b5f3abf238c12dcc3f31605831914a8fd612 |
| large-p90-s42 | 9e3610fe44705bcc1b49b9287602b3341ab756cc83c9489a8b327fa6b20b62aa |
| large-p90-s73 | 42a5c5ec312dbc4c53c9b954fc4b397ffcf201c0965d2bd3115c99159d6c47db |
| large-p135-s19 | 0c8314a19da64c33de33e35a82a9e30ea89578ed774ddd6ce5ca5113095c0fe1 |
| large-p135-s42 | d78a8129381f1c9cd0f154ec1feeb09c4a314bcccc4b3e6089ff2323210484a1 |
| large-p135-s73 | 8056786bc3725476ebfef9f0d4ef2eb195303d6a48552b894dd40cb0c20929e3 |
| stress-p45-s19 | 36064ee4d8baae8c4fa54cbae14dde6c3f608accae0d640731d52e0409a134ed |
| stress-p45-s42 | e8e7f4043221afaad17b237026fbb3a1b378e2138df919a1fa0c4d94cd029c22 |
| stress-p45-s73 | 0ec8474b7ceaed79ace72594a866de8ddc015ca18fddd9aa3f942bba811ec249 |
| stress-p90-s19 | 63215937006d40c9f0ac628cde59381fb11e4e17476511d05e5bc48c3243deba |
| stress-p90-s42 | 07e94bcd505dc99fe7d7fb134214eb46631b5ac16c16e8c82bec813534d9529c |
| stress-p90-s73 | 7598e428e155ab0cbce8e44c5cea8669d5a065315b7ad93ee79d6afa895204fd |
| stress-p135-s19 | 9edde3ddd8743e9a49ac38f6593aa82e69f73d5c5510c1ec29fc17ae9ec4bfcb |
| stress-p135-s42 | 5e18544a545f8b8c25face1b319b0be7452c5461bfe45824911c9bca46b6e0b6 |
| stress-p135-s73 | 3e1422485d1d78bc68ea052e339fa6520e61df49103719ed0328176daa1e10ab |
