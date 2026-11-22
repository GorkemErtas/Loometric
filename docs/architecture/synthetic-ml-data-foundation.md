# M08A: Synthetic ML training data foundation

Dataset: `synthetic-ml-v1`. Generator: `stage-shift-process-v1`. Schema: 1.
Decision: [ADR 0019](../decisions/0019-separated-synthetic-pre-shift-data.md).

This is a separate, assumption-driven synthetic pre-shift prediction problem.
Generated values are not measured factory data or independently validated
industrial distributions. M01's CSV, target, experiments, artifacts, chronological
split and reserved final test are unchanged. The [M07B blockers](ml-planning-compatibility.md)
still apply to M01. No model training, prediction endpoint, scheduling integration
or automatic efficiency conversion is implemented in M08A.

## Prediction problem and exact target

One observation is one dedicated qualified crew on one production line, performing
one style/order's single stage during one aware shift. The unique resource slot is
line × shift; an order appears in exactly one observation. Stages are cutting,
sewing, finishing, quality control and packing. Prediction cutoff is **30 minutes
before shift start**. The plan/WIP snapshot is five minutes before cutoff, orders
are available an hour before cutoff and the shift definition a day before start.
Reference catalog records are declared seven days before the synthetic horizon.

Let `S` be declared standard **worker-minutes per completed good piece**, `Q_good`
the realized integer number of completed good pieces, `W_plan` planned workers,
and `M_plan` available elapsed minutes from the frozen plan:

```text
M_plan = shift minutes − union(breaks, planned downtime, planned machine unavailability)
A_plan = M_plan × W_plan                           [worker-minutes]
E_earned = Q_good × S                              [standard worker-minutes]
standard_capacity_attainment = E_earned / A_plan    [dimensionless, if A_plan > 0]
```

The denominator is frozen **planned** labor, not realized attendance or a revised
end-of-shift budget. Attendance losses and unplanned interruptions reduce realized
output rather than disappearing from the denominator. The target measures attained
standard output against declared available labor. Low workload can cap the numerator,
so this is **demand-censored attainment**, not an intrinsic unconstrained efficiency.
The formula makes no assertion about M01's unresolved `actual_productivity`.

| Condition | Explicit policy |
| --- | --- |
| `A_plan > 0` | Label status VALID; zero completed pieces gives target zero |
| `A_plan = 0` and no completed pieces | Status ZERO_PLANNED_CAPACITY; label null, record retained |
| Positive completed output with zero planned capacity | Invalid under this process; rejected |
| Target above one | Allowed and preserved; the synthetic rate can exceed standard performance |
| Missing/nonpositive/nonfinite standard or invalid quantity | Rejected; no silent dropping or imputation |
| Incomplete order/piece | Only fully completed good pieces earn standard labor; all remaining pieces stay recorded as closing WIP |
| Break/planned downtime overlap | Union intervals in absolute time, subtract once using unchanged M02 availability arithmetic |
| Unplanned downtime/absences | Realized outcome fields only; unplanned loss minutes are additional to already excluded planned intervals |
| Overtime/rework/defects/partial-piece work | Not modeled; no guessed credit, overtime plan or rework route |

Production counts use exact `Fraction` arithmetic and floor only when counting
whole completed pieces. Standards have at most two decimal places. Ratios are
presented with M02's fixed **28-significant-digit Decimal context**, half-even
rounding; no intermediate binary float controls production or labels. Decimal
values serialize as exact decimal **strings**. Counts remain JSON integers.
This is the new dataset's wire format, not a change to M02 input JSON numbers.

For example, 60 completed pieces × 2.5 worker-minutes/piece ÷ 100 planned
worker-minutes gives 1.5, retained without clipping. This example states synthetic
units, not a factory measurement or capacity recommendation.

## Normalized schema and feature boundary

The [versioned dictionary](../data/synthetic-ml-v1-dictionary.md) defines every
normalized field, unit, source, availability and role. Typed frozen records live
in `loometric.synthetic_ml.contracts`. Tables are factories, lines, crews, styles,
standards, shifts, orders, plans, outcomes and membership. Foreign keys are explicit;
the plan binds crew/line/shift/order/standard once. Reference identity is scoped to
the exact dataset receipt: IDs reused in another seed identify slots in a different
synthetic world and must not be pooled as the same factory or crew.

`features.jsonl` is a separate model-ready raw feature view. Each row has
`observation_id`, `cutoff`, `context` IDs and the closed `inputs` whitelist:

```text
stage, shift_kind, weekday, planned_workers, skill_level, style_complexity,
standard_worker_minutes_per_piece, planned_machine_available, available_minutes,
planned_downtime_minutes, opening_wip_pieces, planned_release_pieces, order_quantity
```

Only `inputs` are candidate predictive columns. IDs, cutoff timestamps, partition,
population, seed, scenario and generator metadata are provenance or evaluation
metadata; they must not be automatically encoded as predictors. No target-derived
rolling history, fitted encoding, imputation, scaling or learned aggregate exists.
Future model preprocessing must fit on the training partition only.

Feature construction reads only pre-cutoff references and plans; it never accesses
outcomes or membership. Every joined source must be available by cutoff. The
materializers consume already validated records, normally from receipt-bound
read-back; they are not a replacement for normalized-table integrity validation.
The explicit `training_examples` join retains training labels including null/status
records and never accesses non-training outcome values. Its input must be the
validated, receipt-bound dataset. Training will require a separately documented
undefined-label policy; this milestone does not silently remove those records.

Outcomes are separate, including realized workers, unplanned loss, difficult
condition, completed pieces and closing WIP. Labels are materialized separately
per `train`, `validation`, `gap` and `test`. `labels.test.jsonl` is reserved for
future separately scoped evaluation. Generation/QA performs integrity and physical
checks, but does not compute test-target distributions, fit models or score
predictions. This reservation is not a claim that generated labels were never
constructed or inspected for accounting validity.

## Data-generating process and assumptions

All choices below are synthetic assumptions, not industrial estimates. The JSON
[generation configuration](../../configs/synthetic_ml_v1.json) selects size profiles,
seeds 19/42/73 and baseline/disruption/workload_surge scenarios. Typed parameters
also permit changing staffing, standard, workload, interruption, noise, difficult
condition, label-delay and embargo ranges without changing old contracts.

The generator uses independent `random.Random` streams derived from SHA-256 of
generator version, seed, stream kind and entity/observation key. It does not touch
global random state, read historical data, fit distributions or feed an outcome
into a later plan. Integer draws and rational arithmetic avoid platform math-library
noise. Exact replay is verified before a bundle is published; recorded Python
versions still matter, and cross-platform execution is not claimed as tested.

| Component | Declared v1 assumption / draw |
| --- | --- |
| Factories and calendars | Fixed synthetic offsets +02:00/+03:00/+05:30, cycling by factory; Monday–Saturday start dates, no DST/holidays |
| Lines | All five stages in every factory, configurable lines per stage; one observation at most per line/shift |
| Crews | Dedicated to a line and day/night slot; base and held-out identities; no shared labor across lines; matching-stage qualification is a declared synthetic assumption |
| Roster / planned staffing | Static roster uniformly 4–16 by default; planned workers uniformly max(1, roster−2)…roster |
| Skill / complexity | Ordinal declared levels 1–5; not measured worker qualification scores |
| Standards | Default bounds 0.50–15.00 worker-minutes/piece; style complexity shifts the sampled interval upward within those bounds, independently by style/stage |
| Shifts | Day 08:00–16:00, night 20:00–04:00 next day; separate crews, one explicit 30-minute break after four hours |
| Planned interruptions | Uniform 0–60-minute planned stop beginning 90 minutes after start; independently, 1% declared full machine unavailability |
| Workload | Default 35–160% of nominal 450 × planned workers / standard; integer pieces, minimum one; uses plans only, not latent rate or sampled outcomes |
| Opening WIP / planned release | Uniform integer opening stock from zero to order quantity; planned release is the remainder; available stage work equals their sum |
| Latent line / crew rate | Stable independent factors uniform 0.75–1.25 and 0.85–1.15; never predictive columns |
| Shared shift condition | Hidden factory-shift factor uniform 0.95–1.05, inducing shared conditions across its lines |
| Skill / complexity rate factors | (8000 + 600 × skill)/10000 and (11000 − 200 × complexity)/10000; multiplicative response around declared standards |
| Night condition | Rate multiplier 0.93; synthetic assumption only |
| Attendance | Up to two absences from independent 12% and 3% indicators, bounded by planned workers |
| Unplanned loss | Uniform 0…min(available minutes,35), additional to planned exclusions |
| Noise | Floor of the mean of six independent integer draws in ±1800 basis points by default, as a multiplicative factor; not claimed Gaussian |
| Difficult condition | Default 25/1000 per observation; add 40–120 unplanned loss minutes bounded by available time, multiply rate by 0.65 |
| Label availability | Shift end +120 minutes by default; checked globally across factory offsets at split boundaries |

For each observation, multiply the latent line, crew and shared-shift effects by
the skill, complexity, night, noise and difficult-condition factors. With realized
workers `W_real` and additional loss `L`, possible completed pieces are
`floor((M_plan−L) × W_real × rate / S)`. Actual completed pieces are the minimum
of that value and the available order quantity. Remaining pieces are closing WIP.
The independent validator checks earned labor against a conservative maximum-rate
envelope of 3 × realized usable labor; all configured v1 factors lie below that
envelope. It does not impose a target upper bound of one.

The target is not a linear equation of exposed features: latent profiles, correlated
shift conditions, attendance, stochastic losses, nonlinear multipliers, integer
completion and workload censoring affect it. A metamorphic test changes hidden
noise while all exposed features remain identical and verifies changed outcomes.
The known simulation algorithm is reproducible; that is not evidence that real
factory productivity follows this law.

There is no annual seasonal effect: one short development horizon cannot justify
one. `disruption` applies an additional 60 loss minutes (bounded) and a 0.8 rate
factor in validation/test. `workload_surge` multiplies their planned load percentage
by 1.5 with integer floor. Training/gap behavior remains the baseline. These are
predeclared stress scenarios, not tuned mechanisms or independently isolated causal
effects. Scenario/phase indicators are excluded from predictive inputs.

Each observation has a new independent stage order. Opening stage stock and planned
release are exogenous lots; this is not an end-to-end sewing-to-packing flow or an
upstream material-feasibility simulation. Closing WIP remains attached to its original
order, with no implied disposal or completion. It is not automatically transferred
to the next generated order. This scope preserves within-order piece conservation
without pretending to solve factory routing, inventory carryover or scheduling.

## Splits and generalization design

Construct the working-start-date calendar before sampling outcomes. For `n` dates,
let `a=floor(3n/5)`, `b=floor(4n/5)` and `g=embargo_dates` (default one):

```text
train      = date ordinals [0, a−g)
gap        = [a−g, a) and [b−g, b)
validation = [a, b−g)
test       = [b, n)
```

All factories and shifts sharing a local start date stay in one partition.
The validator additionally requires the latest training label timestamp strictly
before the first validation cutoff, and the latest validation label strictly before
the first test cutoff, using aware absolute-time comparisons. A zero embargo that
fails this check is rejected, not silently enlarged. Night shifts and factory-offset
differences are included. Gap observations are exported/accounted for but excluded
from training and validation. Fractions describe dates, not a row-count target.

The last factory, last line per stage/factory, held-out crew identities and last
style have no development observations. Before test, only other factories/lines,
base crews and other styles are sampled. During test all lines/factories operate;
test-date ordinal modulo three selects base/familiar, held-out crew or held-out
style context on familiar lines. Mutually exclusive population labels use this
precedence: unseen factory → unseen line → unseen crew → unseen style → future
familiar. Membership never uses labels. The report also gives unseen counts for
**every** identity axis in each test population, exposing nested novelty.

An unseen factory necessarily includes unseen lines and crews. An unseen line
includes unseen crews; some such records also use the reserved style/crew cohort.
These are separate stress populations, not experiments isolating a single causal
axis. There are no target-based group balancing or split adjustments.

## Planning compatibility: units match narrowly, no automatic adapter

| Synthetic entity / quantity | M02–M04 relationship | Exact equivalence / explicit adapter requirement |
| --- | --- | --- |
| Factory and offset | No Factory entity; scheduling instance declares one calendar offset | Factory scope must be selected explicitly; never combine different offsets into one unchanged instance |
| Line ID/stage | `ProductionLine.line_id/stage` | Same identity/stage concepts within a receipt; planned worker count is assignment-specific here, static per M02 line, so multi-shift staffing needs an explicit scoped instance |
| Crew, roster and stage qualification | Dedicated qualified crew and `LineCapability.workforce_basis` | Synthetic declaration only; M02 has no crew roster entity; explicit line/style/stage capability records required |
| Style and standard | `ProductStyle`, `StageStandard` | Piece unit and positive standard worker-minutes/piece are exactly the M02 dimensions; explicit version/identity selection still required |
| Order quantity/style | `ProductionOrder.quantity/style_id` | Same pieces/style concepts; release/due/priority and full ordered route are absent and must never be inferred |
| Shift and break | `Shift` aware half-open intervals and breaks | Same time semantics, including overnight start-date ownership; explicit ID/working-date/calendar assembly needed |
| Planned downtime / machine flag | Planned assignment downtime / line availability | Same excluded elapsed-time semantics; union logic reused; per-assignment flag versus static line availability needs an explicit scope |
| Planned available labor | `M × W` worker-minute budget | Exact dimensional match before any derating; actual absences/losses are not planned capacity edits |
| Opening/closing WIP and released pieces | No initial-WIP handling in frozen scheduler | Requires a separately designed future contract; no WIP initialization or routing adapter in M08A |
| Realized target | Proposed `CapacityProfile.assumed_efficiency` | **No equivalence/application authorization**: demand-censored realized value may exceed one; M02 efficiency is a declared [0,1] assumption |
| Membership, provenance and stress case | M04 scenario provenance/changes | No automatic change set; same-demand explicit reviewed assumptions would require separate scope and independent scheduling verification |

Dimensional clarity removes ambiguity for this synthetic label only. It does not
validate M01, upgrade real-factory readiness or justify copying even an in-range
label/prediction into a profile. The frozen M02–M04 schemas, scheduler/verifier and
M07B policy are unchanged. No conversion or planner adapter exists.

## Quality and reproducibility

The [quality/reproduction guide](../data/synthetic-ml-v1-quality-and-reproduction.md)
records exact commands, actual measured sizes, population counts, fingerprints,
development-only descriptive statistics, validation results and remaining limits.
Machine-readable `quality.json` and concise `audit.md` accompany every generated
bundle under ignored `data/processed/synthetic_ml/`.

Validation fails explicitly on bad types/missingness, dangling references, duplicate
keys/slots, nonpositive standards, invalid timestamps, unsupported calendars,
post-cutoff sources, crew/process mismatches, production or stock imbalance,
impossible realized labor, resource overlap, holdout contamination and insufficient
label-maturity gaps. Descriptive feature distributions, train/validation target
distributions, means/quantiles, population/entity counts and temporal comparisons
are reported without a composite quality score. Low variation is an explicit warning,
not a silently repaired column or an industrial-quality claim.

The bundle writer validates and replays the generator before creating a new output
directory. It writes exact normalized and derived files, hashes each and writes
`manifest.json` last as the completion marker. Existing outputs cannot be replaced.
Interrupted writes can leave an incomplete directory; readers require a manifest
and matching receipts, and no automatic deletion/repair is performed. A fresh path
is required for retry. Outputs are restricted to the existing ignored data subtree;
no database, service persistence or new infrastructure is introduced.

Read-back requires an independently retained manifest fingerprint, checks every
file hash/count, validates typed normalized records and recomputes all derived
feature/label file hashes. CLI audit also regenerates the declared process and
compares complete records. Fingerprints prove integrity/replay relative to a receipt,
not authenticity of a factory source. Python/environment and configuration identities
are recorded; wall-clock timestamps/runtimes do not alter deterministic artifacts.

M08A stops at this data foundation. A later milestone must separately define model
baselines, training-only preprocessing, validation selection, undefined-label policy,
uncertainty and one-time reserved-test use. Factory validation and any planning
conversion remain separate, unimplemented work.
