# Synthetic ML v1 data dictionary

Version: `synthetic-ml-v1`, schema 1; generator `stage-shift-process-v1`.
All sources below are **synthetic declarations or simulated outcomes**, never
measured factory data. IDs are canonical strings scoped to the bundle receipt.
Timestamps are ISO 8601 with seconds and explicit offsets; minute boundaries only.
Integers exclude booleans; all normalized fields are mandatory/non-null. The only
nullable numeric field is the derived target at zero planned capacity.

`catalog time` means UTC midnight seven days before configured start date.
`plan time` means cutoff−5 minutes; `label time` means shift end+configured delay
(default 120 minutes). An `available_at` records when **every field in that row**
is available, including identity and classification. Membership/configuration are
design metadata chosen before any outcomes, not predictors. The typed definitions
are in [contracts.py](../../src/loometric/synthetic_ml/contracts.py).

## Normalized tables

| Table.field | Definition and unit | Source | Availability | Justification / role |
| --- | --- | --- | --- | --- |
| factories.factory_id | Factory identity | Configured catalog | Catalog time | Foreign-key scope; context only |
| factories.utc_offset_minutes | Fixed minutes east of UTC, +120/+180/+330 | Synthetic calendar declaration | Catalog time | Interpret shifts; no country/DST inference |
| factories.available_at | Catalog availability timestamp | Generator reference clock | Catalog time | Point-in-time evidence |
| lines.line_id | Stable dedicated line identity | Factory × stage × ordinal catalog | Catalog time | Resource identity; context only |
| lines.factory_id | Factory foreign key | Catalog | Catalog time | Resource ownership |
| lines.stage | cutting/sewing/finishing/quality_control/packing | Declared process catalog | Catalog time | Candidate categorical input |
| lines.available_at | Line declaration timestamp | Generator reference clock | Catalog time | Availability check |
| crews.crew_id | Stable qualified crew identity | Line × day/night × base/held-out cohort | Catalog time | Exclusive dedicated resource; context only |
| crews.line_id | Dedicated line foreign key | Catalog | Catalog time | No shared labor/cross-line transfer |
| crews.shift_kind | day or night | Crew roster declaration | Catalog time | Separate crews for distinct daily slots |
| crews.qualified_stage | Stage the synthetic crew may execute | Matching line declaration | Catalog time | Qualification check, not measured skill certification |
| crews.roster_size | Integer workers in the fixed roster | Seeded catalog draw | Catalog time | Upper bound for planned staffing |
| crews.skill_level | Declared ordinal 1–5 | Seeded catalog draw | Catalog time | Candidate input; synthetic proficiency assumption |
| crews.available_at | Roster/skill/qualification declaration time | Generator reference clock | Catalog time | No retrospective roster revision |
| styles.style_id | Stable style identity | Configured catalog | Catalog time | Context and standard lookup |
| styles.complexity | Declared ordinal 1–5 | Seeded style draw | Catalog time | Candidate input and standard/rate context |
| styles.available_at | Style definition timestamp | Generator reference clock | Catalog time | Availability check |
| standards.standard_id | Style-stage standard version identity in v1 | Catalog | Catalog time | Plan foreign key; no implicit latest-version selection |
| standards.style_id | Style foreign key | Catalog | Catalog time | Standard scope |
| standards.stage | Production stage | Catalog | Catalog time | Exactly one standard per style/stage |
| standards.worker_minutes_per_piece | Positive additive labor standard; at most two decimal places | Seeded declared standard | Catalog time | Exact numerator unit and known input; decimal string on wire |
| standards.available_at | Standard approval/declaration timestamp in simulation | Generator reference clock | Catalog time | Prevent future standard revisions |
| shifts.shift_id | Factory/date/day-night shift identity | Explicit synthetic calendar | Start−1 day | Plan foreign key; context only |
| shifts.factory_id | Factory foreign key | Calendar declaration | Start−1 day | Offset/resource scope |
| shifts.kind | day or night | Calendar declaration | Start−1 day | Candidate shift-condition input |
| shifts.start | Aware start, 08:00 or 20:00 local | Calendar declaration | Start−1 day | Calendar date ownership and cutoff basis |
| shifts.end | Aware end eight hours later | Calendar declaration | Start−1 day | Planned shift duration; night crosses midnight |
| shifts.break_start | Explicit break beginning four hours after start | Calendar declaration | Start−1 day | Interval union, not guessed duration |
| shifts.break_end | Break end, 30 minutes later | Calendar declaration | Start−1 day | Planned excluded interval |
| shifts.available_at | Shift-definition capture timestamp | Generator | Start−1 day | Availability check |
| orders.order_id | Independent stage-order identity | Planned workload draw | Cutoff−1 hour | Plan foreign key; context only |
| orders.style_id | Planned style foreign key | Seeded pre-shift style choice | Cutoff−1 hour | Standard/complexity lookup |
| orders.quantity | Positive integer pieces in this stage order | Planned workload draw | Cutoff−1 hour | Demand cap; equals opening WIP+planned release |
| orders.available_at | Order-plan capture time | Generator | Cutoff−1 hour | Prevent future demand revisions |
| plans.observation_id | Stable observation identity | Shift/line binding | Plan time | Join key only, excluded from predictive inputs |
| plans.line_id | Scheduled line foreign key | Plan | Plan time | Context and stage lookup |
| plans.crew_id | Scheduled qualified crew foreign key | Plan | Plan time | Context and skill/staffing lookup |
| plans.shift_id | Scheduled shift foreign key | Plan | Plan time | Calendar/cutoff lookup |
| plans.order_id | Single independent order foreign key | Plan | Plan time | Workload/style lookup |
| plans.standard_id | Explicit style-stage standard foreign key | Plan | Plan time | Units and standard version |
| plans.planned_workers | Nonnegative integer planned headcount ≤ roster | Seeded plan | Plan time | Candidate staffing input; differs from actual attendance |
| plans.machine_available | Declared planned machine availability boolean | Seeded plan, 1% unavailable | Plan time | Candidate availability input, not actual uptime telemetry |
| plans.downtime_start | Explicit planned stop start | Plan | Plan time | Half-open interval; union with breaks |
| plans.downtime_end | Planned stop end, possibly equal to start | Seeded 0…configured max duration | Plan time | Excluded elapsed time; never actual downtime |
| plans.opening_wip_pieces | Declared integer stage stock snapshot | Seeded pre-cutoff snapshot | Plan time | Candidate opening workload; synthetic, not end-of-shift WIP |
| plans.planned_release_pieces | Integer pieces planned available at shift start | Planned order remainder | Plan time | Candidate workload; arrival uncertainty not modeled |
| plans.snapshot_at | Common plan/WIP capture and availability timestamp | Generator | Cutoff−5 minutes | No late plan/WIP revisions |
| plans.cutoff | Prediction cutoff timestamp | Shift start−30 minutes | Known at plan time | Availability boundary; metadata, not predictive time ID |
| outcomes.observation_id | Original observation foreign key | Simulated production | Label time | Explicit label join only |
| outcomes.realized_workers | Integer attending workers ≤ planned workers | Simulated absence draws | Label time | Outcome only; never substitutes for planned staffing |
| outcomes.unplanned_loss_minutes | Additional whole net elapsed minutes lost after planned exclusions | Simulated loss/condition/scenario | Label time | Outcome only; no overlap/double subtraction from denominator |
| outcomes.difficult_condition | Realized rare-condition boolean | Simulated process draw | Label time | Audit truth, never a feature |
| outcomes.completed_good_pieces | Integer completed good stage pieces | Rational process capacity, bounded by order | Label time | Label numerator source; no partial-piece credit |
| outcomes.closing_wip_pieces | Remaining pieces = order−completed | Simulated stock balance | Label time | Outcome only; retained on original order |
| outcomes.available_at | Outcome/label finalization timestamp | Shift end+declared latency | Label time | Split-maturity check |
| membership.observation_id | Observation foreign key | Declared split design | Before outcomes | Evaluation join only |
| membership.partition | train/validation/gap/test | Whole start-date design | Before outcomes | Explicit data access scope; never a feature |
| membership.population | familiar or named future test population | Entity cohort/date design | Before outcomes | Generalization grouping; never a feature |

## Model-ready feature view

Every `features.jsonl` row has `observation_id`, `cutoff`, `context` and `inputs`.
The first two and context factory/line/crew/style IDs are provenance only. Their
availability is inherited from the plan/references above. Date-encoded IDs, raw
timestamps, seed/scenario and membership must not be automatically encoded as inputs.
The feature builder does not read outcomes or membership and learns no statistics.

| inputs field | Definition / unit | Source and availability | Justification |
| --- | --- | --- | --- |
| stage | Five-stage category | lines.stage, catalog time | Scheduled process |
| shift_kind | day/night category | shifts.kind, start−1 day | Scheduled shift condition |
| weekday | Monday=0…Saturday=5 | Shift local start date, start−1 day | Known calendar context; no claimed causal weekly effect |
| planned_workers | Integer headcount | plans, plan time | Declared labor budget |
| skill_level | Ordinal 1–5 | crews, catalog time | Declared synthetic crew proficiency |
| style_complexity | Ordinal 1–5 | styles, catalog time | Planned product context |
| standard_worker_minutes_per_piece | Exact positive labor standard | standards, catalog time | Required labor per completed piece |
| planned_machine_available | Boolean | plans, plan time | Known planned availability |
| available_minutes | Whole elapsed minutes after unioned planned exclusions | Shift+plan, all pre-cutoff | Known planned labor-time basis |
| planned_downtime_minutes | Whole minutes in explicit planned stop, before overlap union | plans, plan time | Visible interruption plan; not an actual loss |
| opening_wip_pieces | Integer opening stock | plans, plan time | Known declared stage workload |
| planned_release_pieces | Integer planned release | plans, plan time | Remaining planned workload |
| order_quantity | Positive integer total offered stage pieces | orders, cutoff−1 hour | Demand cap; accounting redundancy is explicit |

These are raw model-ready inputs, not an encoded matrix or trained preprocessing
artifact. Realized quantity, staffing, loss, condition, overtime, idle time, closing
WIP, target values and target aggregates are excluded.

## Derived label views

Files `labels.train.jsonl`, `labels.validation.jsonl`, `labels.gap.jsonl` and
`labels.test.jsonl` preserve every observation, including undefined targets.

| Field | Meaning / unit | Source / availability | Role |
| --- | --- | --- | --- |
| observation_id | Original join key | Plan | Exact identity, no inferred alignment |
| status | VALID or ZERO_PLANNED_CAPACITY | Exact target policy; label time | Explicit null policy |
| standard_capacity_attainment | Decimal ratio or null | Completed good pieces × standard / frozen planned available labor; label time | New synthetic response; may exceed one |
| available_at | Finalization timestamp | Outcome, label time | Point-in-time join/maturity evidence |
| planned_available_worker_minutes | Available planned minutes × planned workers | Pre-cutoff plan | Reconciliation denominator; stored with label, not automatically a feature |
| earned_standard_worker_minutes | Completed good pieces × standard | Outcome+declared standard; label time | Exact numerator, never a predictive input |

Ratios use fixed 28-digit Decimal presentation, no clipping. Derived exact decimals
are strings, null is JSON null, and counts are integer tokens. Label/feature files
are verified against recomputation from normalized tables during receipt-bound read-back.

## Configuration and artifact metadata

The versioned JSON configuration lists `schema_version=1`, `dataset_version`,
unique `seeds`, named `scenarios` and named size `profiles`. Profile fields are
the typed [GenerationConfig](../../src/loometric/synthetic_ml/configuration.py).
Every setting is a synthetic design declaration available before generation:

| Setting | Unit / purpose | Default |
| --- | --- | --- |
| seed, scenario | Independent synthetic world and declared stress case | 42, baseline |
| start_date, calendar_days | Synthetic local horizon start / calendar exposure | 2030-01-07, 56 |
| factories, lines_per_stage, styles | Catalog dimensions, including reserved entities | 3, 2, 6 |
| workers_min, workers_max | Integer roster-size bounds | 4, 16 |
| standard_hundredths_min/max | Integer hundredths of worker-minute/piece | 50, 1500 |
| workload_percent_min/max | Integer percent of nominal 450-minute labor budget | 35, 160 |
| planned_downtime_max | Whole elapsed minutes | 60 |
| process_noise_bps | Symmetric bounds for each discrete noise draw, basis points | 1800 |
| difficult_per_thousand | Synthetic event probability numerator /1000 | 25 |
| label_delay_minutes | Minutes after shift end until label availability | 120 |
| embargo_dates | Working start dates excluded before validation/test | 1 |

The benchmark profile changes horizon/factories/lines-per-stage/styles to
364/5/3/12; other defaults remain explicit in the saved expanded configuration.
Configuration is bounded to 32 KiB and at most 150,000 candidate line-shifts before
allocation. Invalid ranges, booleans as counts, unknown fields or insufficient
chronological/generalization exposure fail explicitly.

`manifest.json` records schema/dataset/generator versions, synthetic=true, expanded
configuration, profile, configuration-file SHA-256, canonical configuration and
content fingerprints, per-file SHA-256 and JSONL row counts, ordered feature columns,
Python/Loometric versions, reserved-test policy and false training/conversion flags.
Its fingerprint is SHA-256 of sorted compact UTF-8 canonical JSON plus one LF;
exact decimals/dates use the same string representation as records. No runtime,
absolute output path or execution timestamp affects content. Receipts are integrity
identities, not factory authentication.

`quality.json` contains named validation results, explicit warnings, null quality
score, replay verification, row/partition/population/catalog counts, entity coverage,
date/maturity boundaries, feature distributions and mean deltas, development-only
target statistics/status counts and difficult-condition counts, reserved-test policy
and scope limitations. Numeric statistics are exact-rational calculations presented
as Decimal strings; quantiles use linear interpolation on sorted values. These
statistics are descriptive QA, not model-performance metrics or independent evidence
that the assumed process matches industry. `audit.md` is its concise local summary.
