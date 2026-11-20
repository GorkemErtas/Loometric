# Synthetic production data CSV view

Regenerate from the repository root in the existing local environment:

```powershell
.\.venv\Scripts\python.exe -m loometric.synthetic_export
```

Open `data/processed/synthetic-data-view.csv` in VS Code's CSV table viewer. It is
UTF-8, comma-delimited, has one header, uses standard CSV quoting and LF record
terminators, and remains Git-ignored. Fields containing quotes/commas/newlines are
quoted correctly. No new dependency, solver execution, ML artifact or service is
needed. `--root <repository-root>` is available when running from another directory.
Only this fixed CSV destination is written, using a temporary sibling and atomic
replacement. A failed export preserves the previous complete CSV. Ignore rules
must already exclude the destination; the utility does not change Git configuration.

## Coverage and provenance

The exporter reads working-tree bytes at **Git-tracked** JSON paths under
`examples/planning`, `examples/scheduling`, `examples/scheduling-scalability` and
`examples/scenarios`. Untracked examples and ignored reports are not discovered.
Paths sort lexicographically; collection order remains the source's array order.
`source_sha256` hashes the bytes actually read, not an assumed HEAD blob. The utility
does not imply that a locally edited tracked input has been committed.

| Source category | Views |
| --- | ---: |
| M02 planning fixtures | 2 |
| M03/M04 scheduling-instance fixtures, including representative M03C input | 9 |
| Proposed schedule fixtures | 2 |
| M04 what-if specifications | 14 |
| Applied, valid M04 input variants | 12 |
| Generated M03C benchmark instances | 36 |
| Total source views | 75 |

The 27 versioned fixture files remain unchanged. The two invalid what-if
specifications have no partially applied variant. Their original changes remain
inspectable with INVALID_INPUT and SCENARIO_CONFLICT or UNKNOWN_REFERENCE. The
zero-quantity M02 example remains quantity 0 with INVALID_INTEGER. The two corrupted
schedule proposals retain their source consumption values and independent verifier
codes RESOURCE_OVERLAP / PRECEDENCE_VIOLATION; they are not accepted schedules.

For M03C, use the unchanged `load_design` and `generate_instance` functions with
`configs/m03c_benchmark.json`: all four tiers, three pressures 45/90/135 and seeds 19/42/73.
This creates **36 distinct inputs**, including all nine stress inputs with 750 stages
each. Benchmark resource rejections for solving do not exclude generation. The three
wall budgets and two repetitions describe 216 planned solver runs over those inputs;
they do not create 216 independent production instances. Their settings are retained
as metadata, and no solver run is started. Defaults and complete per-case generator
parameters, including dates, releases and priorities, are retained as JSON.

Valid what-if specifications are applied using the existing pure atomic
`apply_scenario` transformation, without dispatch or optimization. Baseline binding
requires the exact instance ID **and** fingerprint; there is no ID-only fallback.
Input with `greedy_with_cp_sat` is inspectable and its capacity changes can be
projected without executing that requested method. Altered worker/efficiency values
are hypothetical transformed inputs, not measured outcomes.

## Row grain and joins

This is one table with an explicit `record_type`, not an order × stage × line × shift
join. Each source view has one `source` row, followed by entity and relationship rows.
An order has exactly one `order` row per source view; its ordered stages are separate
`order_stage` children. A line, shift, profile, assignment, stop and unavailability
period each have their own row. Standards belong to styles, breaks to shifts, and
working dates/assignments/stops/unavailability to a calendar.

- `record_id` is unique across the CSV: source ID, record type and JSON pointer.
  `parent_record_id` names another CSV row; it is empty only on source rows.
- Entity IDs are scoped by `source_id`. Join assignments to lines/shifts/profiles
  using `(source_id, line_id/shift_id/profile_id)`. Join downtime through assignment ID.
  Join orders to styles and stages through order/style IDs, never row positions alone.
- `context_source_id` binds a proposal/specification to its exact original instance.
  `baseline_source_id` and `specification_source_id` identify a transformed variant's
  original inputs. Root JSON pointers are the empty string; indices are zero-based.
- `quantity` appears only on `order` rows. `worker_count` appears only on `line` rows.
  Proposed stage quantities and requested staffing changes have separate columns.
  Compatible-line arrays list declared style/stage capabilities, **not** available,
  eligible, assigned, reserved or optimized capacity.
- Baselines, alternatives and repeated fixture content are not independent workloads.
  In particular, `representative.json` and generated `small-p90-s42` have the same
  instance fingerprint but distinct source IDs. Deduplicate by instance fingerprint
  when comparing unique content; select one source view when inspecting one scenario.
  Never sum demand/capacity across source views as if they coexist.

Useful VS Code filters: `record_type=order` for demand; `order_stage` for routes and
declared compatible lines; `assignment` plus `line`/`capacity_profile` for resource
inputs; `downtime` / `break` / `unavailability` for calendar restrictions;
`scenario_change` for requested edits; `source_kind=benchmark_generated` for M03C;
`source_id` ending `#applied` for a hypothetical variant. A resource row deliberately
does not repeat every order's quantity or the crew size from a different entity row.

## Schema version 1: all 80 columns

Every row has exactly these columns in this order; groups below follow CSV order.

| Group | Columns |
| --- | --- |
| Record identity | `view_schema_version`, `record_id`, `parent_record_id`, `record_type`, `json_pointer` |
| Source and validation | `source_id`, `source_path`, `source_sha256`, `source_kind`, `value_origin`, `context_source_id`, `baseline_source_id`, `specification_source_id`, `validation_status`, `validation_codes_json` |
| Input identity/policy | `instance_id`, `instance_fingerprint`, `scenario_id`, `baseline_instance_id`, `baseline_fingerprint`, `claimed_instance_fingerprint`, `policy_version`, `schema_version` |
| Generation/execution declarations | `benchmark_case`, `benchmark_tier`, `seed`, `target_load_percent`, `generation_config_json`, `benchmark_execution_config_json` |
| Demand/routing | `order_id`, `style_id`, `quantity`, `priority`, `release_date`, `due_date`, `required_stages_json`, `stage`, `sequence_index`, `compatible_line_ids_json` |
| Resources/standards | `line_id`, `worker_count`, `availability`, `capability_id`, `workforce_basis`, `standard_minutes_per_unit`, `measurement_unit`, `output_unit` |
| Shifts/profiles | `shift_id`, `interval_start`, `interval_end`, `profile_id`, `effective_date`, `assumed_efficiency`, `profile_source_id`, `evidence_status`, `evidence_reference` |
| Calendar/restrictions | `calendar_id`, `working_date`, `assignment_id`, `downtime_id`, `period_id`, `reason` |
| Scheduling context | `horizon_start`, `horizon_end`, `calendar_utc_offset_minutes`, `allocation_granularity_minutes` |
| Scenario provenance | `label`, `provenance_source_id`, `synthetic`, `assumptions_json`, `scheduling_request_json` |
| Requested changes | `operation`, `new_worker_count`, `new_assumed_efficiency`, `new_availability` |
| Untrusted proposal values | `proposed_quantity`, `proposed_required_standard_minutes`, `proposed_consumed_worker_minutes`, `proposed_consumed_standard_minutes` |
| Remaining source fields | `attributes_json` |

Cells are text; do not use a viewer's binary-float display as an authoritative Decimal
conversion. Quantities are pieces, priority 1 is highest, workers are dedicated crew
counts, efficiency is an assumed [0,1] derating fraction. Standards retain explicit
measurement units; proposal consumption retains its raw worker/standard-minute units.
Dates/timestamps/offsets and whole-stage-minute-v1 are preserved. This view introduces
no net-capacity calculations or interval merging, which would duplicate domain logic.

Blank cells mean absent/not applicable, never zero, false, an empty set or inferred
default. Zero is `0`, booleans are `true`/`false`, applicable empty arrays are `[]`.
For a missing optional scheduling request the JSON cell stays blank; the exporter
does not insert a guessed or materialized default. `attributes_json` retains each
entity's unexpanded input fields. Expanded child collections live in their own rows;
root/planning rows contain their noncollection metadata. JSON cells use the existing
report serializer: exact Decimal values are strings, dates are ISO text, integer and
boolean types remain JSON primitives. These cells support inspection; they are not
replacement CLI input contracts. The source byte hash and input pointers preserve
lineage to original numeric tokens. No Decimal passes through binary float conversion.

`instance_fingerprint` is computed with the existing validated input contract;
`claimed_instance_fingerprint` is the proposal's supplied claim. A fingerprint is
identity metadata, not evidence of schedule feasibility or authentic factory data.
VALID_INPUT means the domain input can be constructed, not that its demand is
feasible. Proposal status is the independent verifier's INVALID / VALID_PARTIAL /
VALID_COMPLETE. Invalid source values remain visible; they are never repaired.

`value_origin` distinguishes `source_input`, `generated_input` and `transformed_input`.
The JSON pointer points into the corresponding original/generated/transformed
document. For generated rows the source file/hash refer to the frozen design;
for transformed rows they refer to the specification, with a separate baseline link.
No versioned fixture is a verified scheduling-result report. Accordingly the CSV
contains **no computed performance metrics**, runtimes, capacity KPIs, solver proofs
or made-up outcomes. Proposed labor numbers remain untrusted source assertions.
Only validation/verifier status, identities and static relationship lookups are
derived inspection metadata. Historical Markdown results and ignored local reports
are not scraped, rebound or promoted to independently verified result records.

## Measured inventory and checks

Current output: **20,645 data rows**, **80 columns**, **75 source views**,
17,969,832 bytes, excluding the header from the row count. There are 2,250 order
entity rows, including repeated alternative inputs; this is not 2,250 independent
production orders. The generated subset has 2,178 order rows and 9,162 stage rows.

| Record type | Rows |
| --- | ---: |
| source | 75 |
| planning | 59 |
| style | 137 |
| style_standard | 397 |
| order | 2,250 |
| order_stage | 9,246 |
| line | 387 |
| capability | 1,019 |
| shift | 215 |
| break | 366 |
| capacity_profile | 387 |
| calendar | 59 |
| working_date | 140 |
| assignment | 2,944 |
| downtime | 2,924 |
| unavailability | 2 |
| scenario_specification | 14 |
| scenario_change | 18 |
| proposed_allocation | 6 |

Reproducible checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_synthetic_export.py -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
git check-ignore data/processed/synthetic-data-view.csv
```

Tests check the frozen row counts, complete generation grid/seeds/defaults, source
hashes, unique IDs, relationships, quantity/staffing grain, invalid fixtures,
baseline immutability, exact Decimal text, CSV quoting/Unicode/blanks, atomic failure
and byte-identical regeneration. A clean Python `-S` subprocess blocks imports of
CP-SAT, dispatcher, scheduling metrics, ML and API packages and denies other data
file access while running the real CLI. No CSV, raw input, artifact, ignored report
or local instruction file belongs in the implementation commit.

Measured verification on the current snapshot: **241 tests passed, 1 deselected in
11.09s**, comprising all 11 export tests and 230 existing planning/input/generation
contract tests. The deselected generation test dispatches a schedule; it is outside
this read-only export check. The full application suite was not run because it also
executes CP-SAT and API workflows. Command for this solver-free regression selection:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_synthetic_export.py tests/planning/test_domain.py tests/planning/test_loading_cli.py tests/scenarios/test_contract_application.py tests/scheduling/test_contracts.py tests/benchmarks/test_generation.py -k "not large_generated_instance_passes_unchanged_reference_verifier" -q
```

Ruff lint and the 169-file formatting check passed; `pip check` reported no broken
requirements. Two independent CLI runs produced identical bytes and summary counts:
SHA-256 `18335e9cffb75374a4b5d7115d2df22cd07ad18cb170c5780c3020061754ec6c`.
All 80 columns are documented above. 205 pre-existing tracked files remain byte-identical;
only README is intentionally updated among prior files. There is no dependency or
ignore-rule change. An initial test-only file audit rejected the temporary-file
library's directory-open event; its allowance was corrected before the passing run.
