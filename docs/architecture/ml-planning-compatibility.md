# M07B: ML compatibility audit and integration readiness

Audit date: 2026-11-22. Policy: `m01-planning-audit-v1`, schema version 1.

**Target-to-efficiency conversion is BLOCKED. Overall integration is NOT_READY.**
The existing model can produce an experimental historical productivity estimate,
but its target units, source shift grain, effective crew identity and transfer to
the synthetic planning domain are unverified. A ratio in the interval [0,1] does
not establish compatible units. This milestone adds assessment and retrospective
inspection only. It does not fit a model, execute new predictions, change capacity,
modify a scenario, serve ML over HTTP or begin M08.

## Evidence and scope

Repository evidence is the [prediction problem](../prediction_problem.md),
[data profile](../data_profile.md),
[EXP-001](../experiments/EXP-001-naive-baseline.md),
[EXP-002](../experiments/EXP-002-linear-regression.md),
[EXP-003](../experiments/EXP-003-random-forest.md),
[EXP-004](../experiments/EXP-004-temporal-robustness.md),
[EXP-005](../experiments/EXP-005-error-analysis.md), source code and existing ignored
local artifacts. The audit preserves those reports, artifact bytes and model
selection. It is not a new model-performance experiment.

The [UCI source metadata](https://archive.ics.uci.edu/dataset/597/productivity)
(dataset 597, DOI 10.24432/C51S6D) describes productivity on a zero-to-one scale,
SMV as allotted task time, and team/staff fields. It supplies no auditable target
equation, denominator, worker-minute basis, shift identity or capture/revision
timestamps. Existing local profiling records 37 target values above one and 506
missing WIP values; the metadata's range is therefore insufficient to resolve
the target. These are prior profile findings, not a new examination of holdout
labels. The publisher links for DOI 10.1504/IJBIDM.2021.118183 returned HTTP 403;
full text and source-owner definitions were unavailable. No formula is inferred
from an inaccessible paper or from the dataset's field names.

Planning semantics come from the unchanged
[M02 domain](production-planning-domain.md),
[M03 scheduling contract](scheduling-contract.md),
[CP-SAT policy](cp-sat-optimization.md),
[M04 scenario contract](what-if-scenario-engine.md),
[local API](api-foundation.md), [job lifecycle](optimization-jobs-api.md),
[dashboard](frontend-foundation.md),
[interactive workflow](interactive-planning-workspace.md) and
[M07A workspace](user-defined-production-workspace.md).
[ADR 0018](../decisions/0018-offline-ml-planning-compatibility.md) records the new
offline boundary. Existing frozen contracts and algorithms remain unchanged.

## Actual ML pipeline and temporal evidence

The target is the source column `actual_productivity`, a scalar observed after
production. Its physical calculation, denominator, aggregation weights and label
finalization latency remain unknown. The intended prediction timestamp is before
the scheduled shift; `(date, department, team)` is a tentative observation key,
not proof of one row per unique shift, line, order or stable crew. The source has
no shift ID, intraday timestamp, timezone, roster or style/order keys.

The 1,197-row, 59-observed-date source uses the frozen distinct-date chronological
split, with all rows on a date together. Same team labels recur across partitions;
this is future-date evaluation, not held-out-team or held-out-factory evidence.
Friday is absent from the training weekday vocabulary. There is a calendar gap
between some observed dates; distinct-date counts are not elapsed-day counts.

| Partition | Rows / observed dates | Inclusive dates | M07B use |
| --- | --- | --- | --- |
| Original training | 711 / 35 | 2015-01-01–2015-02-10 | Training-only parsing and saved inner-OOF inspection |
| Outer validation | 232 / 12 | 2015-02-11–2015-02-25 | Existing aggregate reports only; no new predictions or label scoring |
| Reserved final test | 254 / 12 | 2015-02-26–2015-03-11 | No evaluation, tuning or target parsing in the new inspector |

Earlier dataset profiling described the complete CSV; the final test is reserved
for performance evaluation, not represented as unseen by all historical EDA.
Source bytes and all date cells are scanned for fingerprint/partition integrity.
Only original-training non-date fields and targets are interpreted by M07B.

Actual feature sets are A = `department`, `team`; B = A plus derived
`day_of_week` and `day_of_month`; the restricted department-only comparator also
exists. Cleaning normalizes the documented `sweing` spelling and surrounding
department whitespace. Team IDs become canonical strings, not numeric magnitude.
Calendar features derive from the parsed scheduled date (weekday Monday = 0).
Categorical columns use dense `OneHotEncoder(handle_unknown="ignore", drop=None)`;
numeric day-of-month passes through. Other columns drop. Encoders fit only on the
appropriate training prefix. There is no imputation, scaling, target transform,
target trimming or prediction clipping. An unknown category becomes an all-zero
encoding for its column group; that behavior provides no generalization evidence.

The frozen B_RF-01 is `RandomForestRegressor(n_estimators=100, max_depth=3,
min_samples_leaf=20, random_state=42, n_jobs=1)` with the existing remaining sklearn
defaults recorded in the manifest. Deeper variants overfit in EXP-003; the selected
model/configuration remains frozen. Hyperparameter optimization and model promotion
are outside this audit.

Realized `incentive`, `idle_time`, `idle_men` and `over_time` are excluded for timing
leakage. `wip`, `smv`, `no_of_workers`, `targeted_productivity` and
`no_of_style_change` lack verified pre-cutoff definitions/snapshots and are also
excluded. Planned staffing/overtime/WIP must be separate, timestamped concepts;
renaming realized columns does not make them known before the shift. Raw `quarter`
and `day` are not model inputs, and raw date is only the calendar-feature source.

The existing [M01 input contract](offline-prediction-contract.md) requires canonical
sewing/finishing, a canonical positive team string, scheduled date, aware cutoff
and snapshot timestamps, and a source ID; shift ID is optional there. It rejects
post-cutoff snapshots. Training-end checks and unseen-team/weekday warnings do not
prove that the historical source had valid pre-shift snapshots. M07B additionally
checks declared as-of order and an explicit matching planning shift strictly after
the cutoff. These are timestamp assertions, not evidence of capture/revision or
label availability. Invalid/negative/nonfinite model outputs abstain under M01;
above-one values remain visible for review. No M01 output authorizes decisions.

## Measured performance: keep evaluation populations separate

These outer-validation results are transcribed from the existing experiment
records, not recomputed by M07B. Bias means prediction minus actual. Values remain
in the unresolved target scale; none are capacity percentages or factory gains.

| Model / features | n | MAE | RMSE | R² | Bias |
| --- | ---: | ---: | ---: | ---: | ---: |
| Global training mean | 232 | 0.144606972 | 0.197475686 | -0.105176844 | +0.060919708 |
| Department training mean | 232 | 0.143226295 | 0.196492435 | -0.094198670 | +0.060338141 |
| OLS department only | 232 | 0.143226295 | 0.196492435 | -0.094198670 | +0.060338141 |
| OLS A | 232 | 0.150379924 | 0.203566618 | -0.174404317 | +0.059444997 |
| OLS B | 232 | 0.150551578 | 0.202288571 | -0.159704139 | +0.052828789 |
| Frozen B_RF-01 | 232 | 0.140201317 | 0.195062509 | -0.078331093 | +0.055805734 |

The forest's MAE is 2.1120% lower than the department mean on the reused outer
validation period; all listed R² values are negative. This modest selected-period
gain is not deployment evidence. Forest finishing MAE is 0.165290002 (n=94), versus
0.169320624 for department mean; sewing is 0.123111924 (n=138), versus 0.125451896.
The forest predicts 0.670713284–0.819861050. Its residual P05/median/P95 are
-0.200426033 / +0.005735321 / +0.445088627; min/max are -0.334323478 / +0.531434743,
population standard deviation 0.186909343. There are 45 residuals above +0.2 and
15 at or below -0.2. These are descriptive errors, not prediction intervals.

Saved **inner original-training OOF** predictions support the following separate
inspection. Four disjoint evaluation windows contain 393 rows / 20 observed dates,
2015-01-19–2015-02-10 (row ordinals 318–710, after a 318-row warm-up). Each model
uses the same evaluation observations. No saved fold estimator is executed.

| Fold | Training rows / through | Evaluation rows / dates |
| --- | --- | --- |
| F01 | 318 / 2015-01-18 | 98 / 2015-01-19–2015-01-24 |
| F02 | 416 / 2015-01-24 | 102 / 2015-01-25–2015-01-29 |
| F03 | 518 / 2015-01-29 | 100 / 2015-01-31–2015-02-04 |
| F04 | 618 / 2015-02-04 | 93 / 2015-02-05–2015-02-10 |

| Saved OOF model | n | MAE | RMSE | R² | Bias |
| --- | ---: | ---: | ---: | ---: | ---: |
| Department mean (declared baseline) | 393 | 0.147273373 | 0.183976395 | 0.014678476 | -0.007933222 |
| OLS A | 393 | 0.141037325 | 0.177493819 | 0.082892533 | -0.005961664 |
| Frozen B_RF-01 | 393 | 0.148426346 | 0.182224476 | 0.033354617 | -0.023333554 |

The forest wins two folds and loses two; pooled MAE is **0.7829% worse** than the
department baseline (+0.001152973). Finishing MAE is 0.172184645 (n=158), versus
baseline 0.165755260; sewing is 0.132452681 (n=235), versus 0.134847254. Forest
absolute-error median/P95/P99/max are 0.129913097 / 0.352088849 / 0.467322230 /
0.500235749. Thirty-three rows have absolute error at least 0.30 (8.3969%).
EXP-005's ten worst forest rows all overpredict low targets. Team/window slices
have low support, and repeated team IDs do not establish unchanged rosters.
Descriptive error quantiles do not give calibrated coverage or confidence bounds.
OLS A's lower pooled MAE does not change model selection in this milestone.
This retrospective audit reuses original training after outer-validation model
selection; it is not independent model confirmation or a replacement final test.

The inspector reconstructs each fold's training category vocabulary and unknown
counts without fitting an encoder. The real saved rows have zero unknown-category
contexts for these three evaluated categorical feature groups. This says nothing
about an unseen crew, Friday, new style, cutting, quality control, packing, another
factory, or a 2030 synthetic planning date.

## Retained provenance and artifact integrity

These are existing local inputs, ignored by Git. The two M01 generations were
already byte-identical; M07B checks metadata and bytes without deserialization.

| Input / identity | SHA-256 or canonical fingerprint |
| --- | --- |
| `data/raw/garments_worker_productivity.csv` | `763ffcdd39b7f7f360243c2af8f89ed733e8b5f9e511efeb0c886b83e1b76866` |
| `configs/chronological_split.json` | `c38de7e418b1d75a0d4e51ceec63344675afd8acc3de34d85e88315bd686a727` |
| EXP-002 saved aggregate JSON | `0297db31aced6011bc48013f2678f24d07e8bb7f0961e27d8712b0de0d2aeba1` |
| EXP-003 saved aggregate JSON | `dcd252efac46ff0d0e42b219a14165e03fa70db882faa0c39b690761db5d1821` |
| EXP-004 saved OOF JSON | `a65f2643c273dfabb13964a28197bf6ca35b7ed2a97ce64373d8825b05d31843` |
| M01 manifest canonical fingerprint, generations `m01-b-rf01-a` and `-b` | `e70256ebc3713aa4a5a7fa10b9a8f8454b4a7f468339b6e3c9b12998a5f94332` |
| Both M01 `pipeline.joblib` files (23,238 bytes) | `4535b22ea767a2e743cbb144e22ea5d01eb13a529eb1ef112ec1c3b9c4bd16d1` |
| M01 model configuration | `9942cfe8cc7f779a42cf25f60e39310ea2f2dd35e688a089c6815ee222e2571c` |
| M01 training lineage | `6dedf035f086d99504af5d85c956547b90a197f80a83fdd8f811b64dce099bed` |

The manifests record original-training-only construction, exact configuration,
category vocabularies and environment (Python 3.13.14, pandas 3.1.1, NumPy 2.5.5,
scikit-learn 1.9.1, SciPy 1.18.1, joblib 1.6.0, threadpoolctl 3.8.0 and Loometric
0.1.0). The inspector requires the existing environment/configuration, not a silent
cross-version migration. Hashes bind bytes to an independently retained receipt;
they do not authenticate a publisher or prove serialized estimator behavior.

EXP-002/003 JSON contains aggregate metrics, **no saved per-row outer-validation
predictions**. EXP-004 contains saved OOF predictions but no serialized fold models.
M07B cannot reconstruct outer-validation prediction rows without new inference,
which this task excludes. The OOF report therefore sets
`model_artifact_fingerprint: null`; its source-artifact and per-configuration
fingerprints identify saved fold predictions, not the accuracy of the full-training
M01 binary. Fold-specific learned baseline means are recorded separately from
the fixed baseline algorithm identity. No binary is unpickled, fitted or predicted.

## Complete mapping matrix

Each row states a possible mapping, not an implemented adapter. **Accepted** means
only the stated historical/structural role; it never authorizes operational
capacity. **Conditional** requires the listed missing evidence. **Rejected** means
no direct mapping under the frozen contracts. Critical risk can invalidate units,
crew exclusivity or feasible-capacity claims; high risk affects timing, identity,
support or transport; medium risk affects calendar/provenance assertions.

### Source fields and derived inputs

| Source field / meaning | Destination field / meaning | Unit compatibility | Temporal availability | Entity / grain compatibility | Required transformation | Available evidence | Missing evidence | Risk | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `date`: recorded production day | `Shift.interval`, `ProductionCalendar.working_dates`, scheduling local date | Calendar day only; no elapsed minutes | Calendar is knowable; historical recording timestamp absent | Team/department day versus aware shift | Explicit factory offset, shift key and day-boundary mapping | Parsed dates; fixed planning offset | Source timezone, cross-midnight rules, unique shift linkage | High | Conditional; date alone cannot construct a shift |
| `day`: source weekday text | Calendar validation / derived model weekday | Weekday label | Derived before cutoff if scheduled date known | Date-level, not resource availability | Validate against date; derive weekday instead of trusting text | Existing weekday-agreement checks | Source calendar semantics | Medium | Accepted for historical consistency; no capacity mapping |
| `quarter`: within-month source category | No matching planning field | Category, not fiscal/production quarter | Derivable convention, not snapshot evidence | Calendar group, not shift | None in current model; do not invent planning quarter | Excluded from frozen feature sets | Operational meaning and predictive justification | Medium | Rejected as planning input |
| `department`: sewing/finishing | `ProductionLine.stage`, order stage, `LineCapability.stage` | Process labels, not numeric units | Assignment may be planned; source timing unverified | Department may contain several lines/tasks; not a stage identity proof | Owner-approved process taxonomy, scoped to effective context | Two normalized source labels, same-named planning stages | Process boundaries, task content, qualifications | High | Conditional for sewing/finishing; rejected for cutting/QC/packing |
| `team`: associated numeric ID | `ProductionLine.line_id`, dedicated crew basis, assignment | Identifier only; no numeric equivalence | Historical roster timing absent | Repeated team label versus exclusive qualified crew/line | Effective-dated source-team → crew → line mapping; no numeric cast/join | Training IDs 1–12; one-hot strings | Roster continuity, uniqueness, skills, shared-worker exclusion | Critical | Conditional as review lead; direct team-ID=line-ID mapping rejected |
| `targeted_productivity`: recorded target | `CapacityProfile.assumed_efficiency` or order priority | Ratio semantics not established | Planned intent plausible; no frozen pre-shift revision | Team target versus assignment capacity | Separate timestamped planned goal; no current conversion | Excluded timing-sensitive source field | Goal formula, revisions, relationship to standards | Critical | Rejected as efficiency or priority |
| `smv`: allotted task time | `StageStandard.standard_minutes_per_unit` | Unknown labor/clock/task basis versus worker-minutes per piece | No dated approved style standard | Source task/team row versus style × stage | Approve standard basis, stages, piece unit and additive labor accounting | Source field, explicit M02 unit | Owner formula, labor content, style IDs, standard version/effectivity | Critical | Conditional only after standard certification; no direct copy |
| `wip`: work in progress | Order quantity/release, initial operation state | Stock/count definition versus ordered pieces | Opening snapshot and cutoff missing | Row-level WIP versus stage/order inventory | New explicitly defined opening-WIP contract would be needed | 506 missing in earlier profile; not a feature | Order/stage attribution, stock units and opening balances | High | Rejected under current scheduling policy, which has no initial-WIP mapping |
| `over_time`: realized overtime | `Shift.interval`, added assignment / available minutes | Reported duration may be labor-minutes; planning uses elapsed intervals | Realized after shift; planned overtime is different | Team total versus a specific line/shift interval | Separately captured planned start/end and crew | Explicit leakage exclusion | Pre-cutoff plan, labor/elapsed basis, breaks and overlap rules | Critical | Rejected as shift extension or capacity |
| `incentive`: realized reward | Efficiency or scenario capacity adjustment | Reward units versus fraction/worker-minutes | Post-shift leakage | Outcome-associated team value versus future resource | None permitted; new planned policy would need causal evidence | Explicit exclusion | Policy timing, causal effect and transferable response | High | Rejected |
| `idle_time`: realized idle duration | `ProductionCalendar.planned_downtime` / unavailable interval | Duration alone lacks interval and labor basis | Realized after production | Team aggregate versus dated assignment/line interval | Independently known planned outage interval with reason | Explicit exclusion | Timestamped start/end, affected resource, overlap with breaks | Critical | Rejected; no inferred downtime |
| `idle_men`: realized idle workers | `ProductionLine.worker_count` / qualified crew | Workers superficially match count, but different denominator | Realized after production | Idle subset versus dedicated staffed crew | Separate qualified pre-shift roster, not subtraction | Explicit exclusion | Membership, timing and double-counting rules | Critical | Rejected |
| `no_of_style_change`: recorded changes | `ProductStyle`, capability, setup duration | Count versus style identity / setup minutes | No pre-cutoff planned sequence | Team aggregate versus ordered style operations | Explicit planned sequence and future approved setup contract | Excluded field; current scheduler has no setup model | Style IDs, sequence, transition times, capture timing | High | Rejected under current contracts |
| `no_of_workers`: realized team staffing | `ProductionLine.worker_count`, M04 `set_workers` | Source can be fractional; planning count is nonnegative integer | No verified planned roster | Aggregate staffing versus dedicated qualified crew | Separate planned headcount and effective roster; never round silently | Excluded feature; explicit M02 crew assumption | FTE/headcount definition, shift grain, qualifications and availability | Critical | Conditional evidence route; direct copy/rounding rejected |
| `actual_productivity`: historical response | Observed evidence; proposed `CapacityProfile.assumed_efficiency` | Formula/denominator unknown versus [0,1] standard-capacity factor | Target observed after production, never an input before cutoff | Unverified team/department day versus line-stage-shift profile | No justified mathematical conversion | Existing target, >1 prior observations, measured prediction errors | Numerator, denominator, labor basis, losses and aggregation weights | Critical | Accepted as historical target; efficiency substitution BLOCKED |
| Derived `day_of_week` | B model input; possible calendar category check | Monday=0 categorical code | Available from declared date | Date category, not available crew/capacity | Deterministic date derivation | Frozen features; training vocabulary lacks Friday | Transfer to future calendar/work practices | High | Accepted as experimental feature; conditional context support |
| Derived `day_of_month` | B model input; no capacity field | Calendar integer, not quantity or duration | Available from declared date | Date category, not production state | Deterministic day number, no extrapolation claim | Frozen numeric passthrough | Stability across months, years and factories | High | Accepted as experimental feature only |

### Prediction context and missing planning entities

| Source field / meaning | Destination field / meaning | Unit compatibility | Temporal availability | Entity / grain compatibility | Required transformation | Available evidence | Missing evidence | Risk | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M01 predicted productivity | `CapacityProfile.assumed_efficiency`, M04 `set_efficiency` | Unresolved target versus explicit [0,1] factor | Forecast at declared cutoff; not a measured fact | Model has no line/style/standard/roster response inputs | No supported conversion; preserve raw value | Frozen experimental model and saved errors | All target/unit, process, crew, timing, transport and uncertainty gates | Critical | Rejected for application; BLOCKED even when value is 0.8 |
| M01 scheduled date/cutoff/snapshot/source/shift ID | `Shift`, `ShiftAssignment`, calendar and audit provenance | Date/time/identity only | Check snapshot ≤ as-of ≤ cutoff < shift start and post-training context | Declared external linkage, absent in training CSV | Require exact explicit shift/date ID; retain source/version fingerprints | Strict typed M01 context and aware planning intervals | Trusted capture/revision history, freshness and label latency | High | Accepted for declared structural checks; semantic timing conditional |
| No source style identifier | `ProductStyle.style_id`, style standard set | Missing identity | Planned style could be known before shift, not present here | Model averages over unidentified styles | Obtain explicit style/order lineage and versioned standards | Synthetic style IDs are user declarations | Source style history and validation by style | Critical | Rejected for inferred style or style-response prediction |
| No source order, pieces, priority, release, due date or route | `ProductionOrder` fields and required stages | Missing pieces/dates/identities | Planner can declare independently; no model evidence | Team row versus order-stage operation | User-declared demand remains separate | Existing synthetic order contracts | Historical order attribution, demand and route evidence | Critical | Rejected as derived ML order intake or completion prediction |
| No approved labor standard / qualified crew | `StageStandard` + `LineCapability.workforce_basis` | Missing worker-minute basis and skill qualification | Standards/qualification must be effective at cutoff | Task aggregate versus style-stage-qualified-line relation | Explicit approved records and qualification scope | Strict synthetic capability contract | Source process/standard/roster evidence | Critical | Rejected as inferred capability or standard |
| No actual line key, availability or downtime intervals | `ProductionLine`, `ProductionCalendar` | Missing identity and elapsed intervals | No pre-shift availability snapshot | Team label cannot locate a dedicated line | Independently declare line/availability and approved calendar | M02 validates unique assignments and interval constraints | Historical line linkage, outages and resource exclusivity | Critical | Rejected as inferred line availability/calendar |
| No source profile or assignment key | `CapacityProfile.profile_id/effective_date/source_id/evidence_status`, `ShiftAssignment` | Missing profile provenance; ratio unresolved | Effective date and plan revision required | Team/day versus explicit line/shift/profile tuple | Reference existing declared profile without replacing it | M02/M07A synthetic provenance | Approved profile source, revision and field-to-source linkage | High | Conditional reference check only; no upgrade to measured evidence |
| No source horizon, offset, minute grid or operation allocation | `SchedulingInstance` and verified schedule | Missing time/grid/resource contract | Historical date alone cannot define horizon | Row prediction versus multi-order constrained instance | Keep unchanged validated scheduling instance and independent verifier | M03 whole-stage-minute-v1 constraints | Factory calendar, route and allocation linkage | Critical | Accepted as independent synthetic context; rejected as ML-generated schedule |
| No intervention or resource-response model | M04 scenario specification and immutable change set | No causal efficiency/headcount response | Hypothetical edit is explicitly chosen, not observed | Constant department/team/date forecast versus changed workers/styles/downtime | Future separately approved scenario only after gates; no automatic change object | Existing synthetic changes, fingerprints and same-demand verifier | Intervention evidence, versioned conversion, explicit approval and rollback | Critical | Accepted as independent what-if workflow; ML adapter rejected in M07B |

No mapping manufactures missing stages, skills, workers, orders or setup times.
Model input acceptance and a matching synthetic capability are distinct from
source-to-factory process evidence. The old scheduling policy still does not model
setups, initial WIP or material constraints; ML cannot silently supply those.

## Why target-to-efficiency conversion is blocked

Planning capacity uses available elapsed minutes `M`, dedicated qualified workers
`W` and explicit efficiency `E` in [0,1]: worker-minute budget = `M × W`, standard
worker-minute budget = `M × W × E`. Stage demand is pieces `Q` times approved
worker-minutes per piece `S`. Scheduling reserves whole-minute uninterrupted
operations using the same labor basis and independently verifies allocations.

No evidence establishes that source productivity equals standard worker-minutes
earned divided by available worker-minutes, what losses are in that denominator,
or how daily department/team responses aggregate into a single assignment. If its
denominator already discounts staffing, overtime, breaks or idle labor, applying
it to `M × W` and separately removing downtime can count labor/losses twice.
If its SMV is clock time per multiworker task, copying it into labor content can
multiply workers twice. These are unresolved possibilities, not claims about the
publisher's actual calculation. Neither a regression coefficient nor correlation
identifies a physical or causal conversion.

Values above one are valid retained source observations under the current data
policy but invalid as M02 efficiency. Clamping destroys information and does not
repair semantics. Even [0,1] forecasts cannot become capacity assumptions without
an approved unit conversion and uncertainty policy. A wrong conversion can inflate
capacity, shorten operation durations, hide tardiness or report conditional
feasibility against an unjustified budget. Independent verification can confirm
constraints **given declared assumptions**; it cannot validate those assumptions
against a factory. The model also cannot estimate a changed worker count, style,
line, qualification or unseen stage because these responses were not established.

## Versioned offline assessment interface

The pure [assessment function](../../src/loometric/compatibility/assessment.py)
accepts frozen typed `AssessmentRequest`, `ModelProfile` and unchanged
`SchedulingInstance`. Its import path needs no pandas/sklearn/data reads. JSON
ingestion and artifact inspection are separate local boundaries. There is no
capacity calculator, scenario-engine call, model execution or mutation in the
assessment. Schema artifacts are
[request v1](../contracts/ml-planning-assessment-request-v1.schema.json) and
[assessment v1](../contracts/ml-planning-assessment-v1.schema.json), using JSON
Schema 2020-12. The typed parser is authoritative for cross-field/time/Decimal
constraints; a generic schema check alone cannot establish compatibility.

Requests contain only schema version, the existing M01 input context, a declared
productivity numeric token or null, M01 prediction status, retained model and
configuration fingerprints, aware as-of timestamp, declared observation grain,
assignment/order IDs and explicit evidence references. Original/final-test target
fields and unknown keys are rejected. Numeric strings and booleans cannot replace
the prediction token. Nonfinite JSON, duplicate keys, excessive nesting, records,
strings or numeric magnitude are rejected. Assessment inputs/manifests are limited
to 256 KiB, saved OOF JSON to 4 MiB, pipeline integrity bytes to 16 MiB. The JSON
parser bounds nesting to 24 and Decimal tokens to 128 digits / exponent magnitude
100. Normal finite negatives and values above one are retained and assessed,
never clamped. In-process nonfinite Decimals produce explicit incompatible results;
they cannot enter through JSON.

| Mapping status | Meaning in this policy |
| --- | --- |
| COMPATIBLE | A specific structural proposition was checked, e.g. hashes or declared shift/date linkage; does not imply physical unit equivalence |
| CONDITIONAL | Matching known label/range, but process/crew/domain evidence is unproved |
| INCOMPATIBLE | A concrete mismatch, such as wrong stage, grain, shift, identity, timestamp, invalid/absent prediction or value above planning range |
| INSUFFICIENT_EVIDENCE | Required semantic evidence is missing, including target formula and source shift grain |

Overall status is INCOMPATIBLE if any concrete mismatch exists, otherwise
INSUFFICIENT_EVIDENCE. This version cannot return overall COMPATIBLE/READY.
Every output fixes `integration_readiness=NOT_READY`,
`target_to_efficiency=BLOCKED`, `capacity_application_authorized=false`,
`converted_efficiency=null` and `final_test_evaluated=false`. Construction rejects
attempts to fabricate those claims. `candidate_value_origin` explicitly says
`DECLARED_OFFLINE_CONTEXT_NOT_REEXECUTED`: an assessment does not authenticate that
the declared number came from a model. Matching manifest/binary integrity does
not change that limitation.

Evidence references contain a gate, canonical reference and context fingerprint.
They are review leads, not read or verified approvals. The context fingerprint
binds request content except references, model metadata and the original instance
fingerprint; removing references avoids a circular hash. A separate complete
request fingerprint includes references. Stale context references are incompatible.
Providing all correctly scoped references still cannot pass the scientific gates.
The audit hash uses canonical sorted compact JSON with exact Decimal strings;
existing M01 manifest and M03 instance fingerprints retain their own unchanged
algorithms. Do not interchange these identities.

Outputs contain deterministic reason codes, all 12 gates, declared prediction,
source/model/configuration/pipeline/dataset/split identities, original instance
identity and both request/context hashes. No wall-clock runtime or random value
enters the assessment. Supported source departments are sewing/finishing only;
unknown teams or an unseen weekday remain unvalidated. A known source team is
never automatically a qualified crew. An order/style/stage must also have an
explicit synthetic capability. Only `date_department_team_unverified` is the
M01 grain declaration; other grains are incompatible, and that declaration still
does not prove shift grain.

### Offline commands

Use the existing local ML environment and independently retained receipt hashes.
Outputs must be new paths; omit `--output` for JSON on stdout. Existing files are
never overwritten. Exit 0 means an audit was produced, including blocked audits;
it never means READY. Invalid/missing/drifted inputs return exit 2 with a fixed
error envelope that does not echo arbitrary source values or paths.

```powershell
.venv/Scripts/python.exe -m loometric.compatibility assess --request examples/compatibility/request.json --instance examples/scheduling/competition.json --artifact data/processed/m01-b-rf01-a --expected-fingerprint e70256ebc3713aa4a5a7fa10b9a8f8454b4a7f468339b6e3c9b12998a5f94332 --output .tmp/m07b/my-context-assessment.json
.venv/Scripts/python.exe -m loometric.compatibility inspect-saved --expected-predictions-sha256 a65f2643c273dfabb13964a28197bf6ca35b7ed2a97ce64373d8825b05d31843 --output .tmp/m07b/my-saved-inspection.json
```

The example's declared 0.8 is **synthetic context input**, not a new ML result. Its
matched sewing assignment still produces INSUFFICIENT_EVIDENCE / NOT_READY /
BLOCKED. The artifact boundary checks exact retained manifest, environment,
configuration, training lineage and pipeline-byte hashes without `joblib.load`.

The saved inspector has no partition selector, fit, predict or final-test option.
It checks the EXP-004 digest, uses M01's training-only CSV loader, and reuses
EXP-005's fold/row/target/frozen-parameter/metric checks. It recomputes MAE, RMSE,
R², bias, signed/absolute-error quantiles, department/fold metrics and changes
against department mean from the existing authorized inner-OOF targets. No rows
are trimmed. Optional `--include-observations` includes all 393 matched target and
prediction rows in the local report. Aggregates are default. Keep such generated
reports under ignored paths. Missing saved files fail; no retraining fallback
exists. Every report records source/data/split/configuration provenance, environment,
zero models fitted, zero new predictions and explicit population limitations.

## Measurable readiness gates

All gates below are mandatory for a future READY policy. Current PASS values have
the narrow software scope shown; they are not operating approval. Missing evidence
is BLOCKED, a failed measurable comparison is FAIL, and work never performed is
NOT_ASSESSED. No gate is satisfied merely by submitting a reference string.

| Gate | Current status | Evidence / criterion checked | Evidence required before a future pass |
| --- | --- | --- | --- |
| `target_units` | BLOCKED | No verified numerator, denominator, aggregation or worker-minute equation; >1 contradiction unresolved | Owner-approved versioned target formula, units, loss treatment, standards basis, aggregation and reconciliation examples including >1 values; reviewed dimensionally valid conversion |
| `feature_timing` | BLOCKED | Restricted features avoid known realized leakage; source capture/revision and label latency absent | Immutable pre-cutoff snapshots with capture/effective/revision timestamps for every feature, label-finalization policy, declared freshness limits and reproducible point-in-time joins with no future revisions |
| `department_stage` | BLOCKED; FAIL for incompatible requested stage | Sewing/finishing labels only; cutting/QC/packing unsupported | Approved process taxonomy scoped to exact line/style/stage, operation boundaries and independent evaluation on each authorized process; reject all others |
| `team_crew` | BLOCKED | Known team label does not establish roster, skill or exclusivity | Effective-dated team/crew/line crosswalk with worker membership, qualifications, staffing basis and checks excluding shared-worker double allocation |
| `observation_grain` | BLOCKED | Date/department/team tentative; shift ID and aggregation unverified | Unique source observation key, shift/timezone/day-boundary mapping, target aggregation weights and reconciled shift-level samples; any disaggregation requires evidence |
| `domain_shift` | BLOCKED | 2015 source versus hypothetical future styles/calendars/crews; no external validation | Declared deployment population and support bounds; representative independently collected authorized observations, date/team/style/crew slices and documented drift limits |
| `model_quality` | FAIL | Audit minimum criterion: frozen forest pooled inner-OOF MAE must improve on department mean; actual +0.7829% worse, two wins/two losses | Predeclared baseline, metrics, minimum useful improvement and slice tolerances approved before independent validation; consistent evidence, without retuning reserved test |
| `uncertainty` | NOT_ASSESSED | Error tails described; no calibrated predictive interval or decision-loss policy | Predeclared coverage/width and slice/sample thresholds; calibration on authorized separate data, held-out coverage assessment, cost/abstention thresholds and failure analysis |
| `artifact_integrity` | PASS for inspected M01 copies | Retained manifest/config/environment/lineage and binary hashes agree; prior two generations byte-identical | Continue exact reproducibility, ownership and receipt retention; future execution additionally needs separately authorized trusted loading/behavior verification; digest checks alone are not semantic approval |
| `supported_inputs` | PASS for declared known-category, valid-time example; BLOCKED/FAIL otherwise | Strict M01 fields, known vocabulary and ordered timestamps; no inference executed | Verified cutoff provenance and scope enforcement for every input; explicit abstention for unknown crew/process/calendar/domain, with supported future bounds justified by data |
| `prediction_range` | BLOCKED; FAIL for absent/abstained/negative/nonfinite/>1 candidate | Invalid candidates explicit, no clamping; [0,1] still lacks unit conversion | Owner-approved handling for target >1 and invalid values, conversion domain/range proof, visible abstention and downstream refusal; no silent clipping |
| `operational_safety` | NOT_ASSESSED | No production intervention or automatic application implemented | Named accountable reviewer, explicit hypothetical-scenario approval, audit receipts, monitoring and drift policy, tested fallback to manually justified capacity, rollback to prior immutable profile and stop/review procedure |

Thresholds not present in existing evidence are deliberately **unset**, not invented
numbers. Before a future evaluation, an accountable owner must approve numerical
freshness, error, uncertainty, support and drift tolerances and the authorization
scope. All mandatory gates must pass under a separately reviewed policy/version;
M07B cannot unlock that policy. No new final-test evaluation is authorized here.
Any later one-time final-test use must retain the existing frozen selection and
predeclared evaluation protocol; it cannot become tuning or transport evidence
for an unrelated factory merely by being scored.

## Future architecture proposal, not an implementation

```mermaid
flowchart LR
  H[Historical training data] --> A[Validated ML artifact]
  A --> P[Offline prediction context]
  P --> G[Compatibility and confidence gates]
  G --> R[Explicit reviewer approval]
  R --> C[Hypothetical capacity scenario]
  C --> V[Existing independent schedule verification]
  V --> D[Comparison dashboard]
```

The edges after the compatibility gates remain blocked. An eventual separate
conversion adapter would need an approved, versioned physical formula, input
support checks, uncertainty/abstention policy, exact prediction/model/data/context
receipts and reviewer approval. Its only permissible planning product would be an
explicit hypothetical scenario with its own source/assumptions, linked to the
unaltered base instance. Only then could unchanged M04 changes and independent
M03 verification compare identical demand under declared capacity. No such
adapter, confidence gate implementation or approval service exists in M07B.

Historical observed productivity, predicted productivity, hypothetical efficiency,
verified conditional feasibility and actual factory performance must remain five
distinct evidence types. A future dashboard should expose their sources and
limitations separately. Optimizer proof applies to the declared mathematical
instance, not to forecast accuracy, real capacity or business benefit. A feasible
synthetic schedule never constitutes measured production performance.

## Verification and preservation

Focused tests cover matching and unsupported processes, unknown teams/unverified
crews, target/grain/timing blockers, negative/nonfinite/>1 values, no clamping,
context-bound references, forged readiness, deterministic fingerprints, unchanged
instances, metadata drift and model-execution prohibitions. Synthetic saved-data
tests poison **both outer partitions' labels and non-date features** with invalid
text while rebinding only their synthetic fingerprints; inspection still produces
identical authorized metrics. Other tests inject final-test dates/row IDs, target,
parameter, metric, vocabulary and unknown-count drift and require rejection.
CLI tests verify closed fields, safe errors and create-only output behavior.

Two real `--include-observations` runs produced identical bytes, SHA-256
`f01b3ef254dde52fdbd69f80d5bb09e629a98273bc8a7142d702377b8f421ae2` in the recorded
environment. Their 393-row scores match existing EXP-004/005; no model or binary
was executed. Reports remain ignored under `.tmp/m07b/`.

Executed checks in the recorded environment:

| Command (repository root unless stated) | Actual result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/compatibility tests/test_error_experiment.py -q -p no:cacheprovider` | 73 passed in 11.92s |
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | 1,001 passed in 115.55s, normal pytest temporary directory |
| `.venv/Scripts/python.exe -m ruff check .` | Passed |
| `.venv/Scripts/python.exe -m ruff format --check .` | All checked files already formatted |
| `.venv/Scripts/python.exe -m pip check` | No broken requirements |
| `npm run typecheck` in `frontend` | Passed |
| `npm run check` in `frontend` | Biome passed, 55 files |
| `npm test` in `frontend` | 139 passed across 6 files, 25.18s |
| `npm run build` in `frontend` | Type check and Vite passed, 65 modules |
| `npm run test:browser` in `frontend` | 10 passed in 1.0m; owned API/Vite listeners closed and credentials discarded |
| `npm ls --depth=0`, `npm audit --audit-level=low` in `frontend` | All 17 exact direct dependencies present; zero vulnerabilities |

Verification corrections: synthetic test code initially used an incorrect import
and inappropriate Decimal serialization/create-only fixture overwrite; these were
corrected before the 73-case pass. The first complete Python run caught a duplicate
`test_cli.py` module basename shared with existing scenario tests. The new module
was renamed `test_compatibility_cli.py`; the subsequent unchanged-code full run
passed all 1,001 cases. Failed/collection-error runs are not counted as passes.
Normal process/temp permissions were needed for the existing pytest/browser/native
tooling; the default sandbox restrictions are not interpreted as product failures.
The browser runner reported only its existing NO_COLOR/FORCE_COLOR environment
warning. A generic JSON Schema validator is not installed; schema files are parsed
and reviewed locally, while typed contract and behavior tests execute without
adding a dependency. Publisher full-text availability remains the evidence limit
described above.

No new dependency, final-test score, model fit/inference on the real CSV, historical
experiment edit, scheduling change, API route, dashboard change or deployment was
introduced. Existing full-suite model tests use their synthetic fixtures. A source,
split, artifact and tracked-file SHA audit verifies preservation independently;
local instruction/plan files and all generated reports remain ignored/untracked.
The final SHA comparison preserved 305 of 306 original inputs byte-for-byte; the
sole expected modified original is README. All 39 Python pins match the installed
environment, all original frontend package/lock files are unchanged, and 62
relative README/audit/ADR links resolve. Both JSON Schemas parse and their field
sets match the typed contracts; the actual declared-context report matches fixed
policy values and all 12 distinct gate identities. This is a local consistency
review, not a claim that an uninstalled generic schema validator was executed.

## M08 prerequisites and recommendation

Recommend a separately scoped evidence-definition and data-contract phase first:
obtain approved target/standard formulas and reconciliation examples; define
effective crew/process/shift/style mappings and snapshot/label timing; declare the
intended inference population and measurable acceptance tolerances; then design
independent quality, uncertainty and rollback validation before any conversion
proposal. Collect evidence only with explicit authorization; this repository has
no access to a real factory. A new dataset or revised feature/grain contract may be
necessary and must be reviewed rather than silently substituted into M01.

Do not begin model serving, a retraining campaign or ML-driven scheduling. A future
conversion needs a new ADR/policy decision and explicit hypothetical-scenario
review. M07B ends with an auditable **NOT_READY / BLOCKED** conclusion.
