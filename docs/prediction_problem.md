# Pre-shift productivity prediction

## Decision and target

The intended prediction supports planning before an upcoming garment-production
shift. Predict the continuous `actual_productivity` outcome for a scheduled team in
a department, with the input snapshot frozen immediately before that shift starts.
This is a regression problem. The CSV does not establish exact productivity units,
how the ratio was calculated, or the business action a prediction should trigger.
Confirm those definitions before selecting metrics or operational thresholds.

The working row key is `(date, department, team)`, subject to verification. The CSV
has neither a shift ID nor start/end times. Multiple rows sharing that key are flagged
for review rather than discarded. Even a unique key does not prove shift-level grain.
Calendar dates are local source dates; no timezone conversion is inferred.

## Availability at the cutoff

| Source fields | Initial decision | Evidence required |
| --- | --- | --- |
| date, day | Eligible | Derive calendar inputs from scheduled shift date. Use date for future split boundaries. |
| department, team | Eligible | Scheduled team/department assignment at cutoff; team is categorical. |
| quarter | Conditional; excluded initially | Confirm within-month bucket semantics, then derive from date. Quarter1–Quarter5 are not calendar quarters. |
| targeted_productivity | Conditional; excluded initially | Frozen planning target timestamped before shift start; no later revisions. |
| smv | Conditional; excluded initially | Standard minute value for the style assigned at cutoff. |
| wip | Conditional; excluded initially | Opening backlog snapshot, measurement timestamp, and department applicability. |
| no_of_workers | Conditional; excluded initially | Planned staffing rather than realized attendance or average headcount. |
| no_of_style_change | Conditional; excluded initially | Planned changes; a realized same-shift count is unavailable. |
| over_time, incentive | Excluded | Realized totals are unavailable at cutoff. Planned overtime or an incentive schedule must be separately identified and timestamped. |
| idle_time, idle_men | Excluded | Observed during the shift. |
| actual_productivity | Label only; excluded from inputs | Observed after the shift. |

These are conservative engineering assumptions. Column names and correlations do not
prove timing. The CSV contains no feature capture times; obtain source-owner evidence
before admitting a conditional field. Do not backfill an input with a value revised
after the shift. The source-column policy is also encoded in `src/loometric/leakage.py`.

## Missing data and normalization

Normalize department whitespace and the source spelling `sweing` to `sewing` on a
copy, preserving raw bytes. Profile WIP missingness separately for each department
and distinguish missingness from observed zero. A concentration of missing WIP in a
department can reflect reporting rules, but the CSV alone cannot establish that
explanation. Do not impute or infer structural zero yet. Fractional worker counts
need a definition, not automatic rounding.

The target must be numeric, finite, nonnegative, and variable. Values above 1 may
represent overachievement; retain and flag them pending domain confirmation.
There is no arbitrary upper clipping threshold. No rows are silently removed.

## Future evaluation contract

Use earlier dates for training and later dates for validation/test. All rows for the
same date must stay in one partition, with `max(train_date) < min(validation_date)`
and the corresponding boundary before test. Check sufficient distinct dates first.
No random row split is acceptable because teams repeat and same-day observations
share operating conditions. Sort a copy only after validating original chronology.

Choose boundaries from the observed date span and planning horizon. A short history
cannot support claims about seasonal or long-term generalization. Repeated teams in
future periods match the initial use case; performance on unseen teams is a separate
question and would require additional grouped evaluation.

Fit imputers, encoders, scalers, feature selection, and any learned transformations on
the training period only. Any later historical/rolling features must use outcomes
available before the predicted shift; exclude same-day outcomes when shift ordering
is unknown. Target-derived aggregates must not include validation or test outcomes.
No feature fitting, temporal split, model, or optimization is implemented in Task 1.

## A02: frozen partitions and EXP-001

A02 establishes the evaluation protocol after the A01 data foundation. The source
fingerprint and partitions are persisted in `configs/chronological_split.json`.
The rule uses sorted distinct dates and integer boundaries floor(3n/5), floor(4n/5):

| Partition | First date | Last date | Dates | Rows |
| --- | --- | --- | --- | --- |
| Training | 2015-01-01 | 2015-02-10 | 35 | 711 |
| Validation | 2015-02-11 | 2015-02-25 | 12 | 232 |
| Final test | 2015-02-26 | 2015-03-11 | 12 | 254 |

Endpoints are inclusive. With 59 observed dates this gives 59.32%/20.34%/20.34%; no
boundary adjustment based on targets, department balance, or measured errors is made.
Sort only a copy, keep dates intact, verify strict non-overlap and complete coverage,
and fail on source/config drift instead of silently repartitioning. The saved split
is shared by future experiments, including algorithms and feature engineering.

EXP-001 estimates one global training-target mean and one mean per training
department. At prediction time, only scheduled department is passed to the latter;
unknown/missing departments fall back to the global training mean. The historical
source validator continues to reject unknown/missing departments in the input CSV.
Every training label must have been available before the validation period starts.
No other source field enters prediction, and statistics remain fixed in validation.

Only validation MAE, RMSE, R², prediction bias, and department MAE are calculated.
Positive bias means overprediction. R² is explicitly undefined for a single sample
or constant actual targets. Primary comparison uses validation MAE; final test
performance remains uncalculated until a later, separately authorized final evaluation.

The pre-existing A01 data profile describes the whole CSV, including dates now
reserved for final test. This limits claims that the holdout is untouched by EDA;
it does not authorize using those labels for fitting or performance-based selection.
See [ADR 0002](decisions/0002-chronological-evaluation-and-naive-baselines.md) and
the measured [EXP-001 report](experiments/EXP-001-naive-baseline.md).

## A03: provisional pre-shift feature boundary and EXP-002

EXP-002 uses the same frozen partitions and compares four declared linear feature
sets on validation only. All eligibility remains provisional: the source contains
no capture timestamps. Scheduled department/team assignment must be frozen before
the shift, the scheduled date must already be known, and training outcomes must be
finalized before validation starts.

| Model feature | Representation | Availability assumption |
| --- | --- | --- |
| department | Training-fitted one-hot category | Scheduled department known at cutoff; reuse existing source normalization. |
| team | Training-fitted one-hot category | Scheduled team ID known at cutoff; numeric whole IDs become strings, never magnitudes. |
| day_of_week | Date-derived one-hot category, Monday=0 | Derive from scheduled local date; ignore source day. |
| day_of_month | Date-derived numeric integer 1..31 | Derive from the same scheduled date; no outcome information. |

No other source field is admitted. In particular, the evidence required for
targeted_productivity, smv, wip, no_of_workers, and no_of_style_change has not been
supplied. Realized overtime, incentives, idle time/staffing, and the label remain
excluded. Quarter semantics remain unverified. No planned values are substituted
for realized values or inferred from them.

The stateless builder accepts only date, department, and team. Only training rows
fit the encoder and estimator together in a Pipeline. Unknown categories encode as
zeros for their feature; missing eligible inputs fail instead of being imputed.
Calendar features are a joint addition to the department/team model. No test frame
is passed to feature construction, fitting, inference, metrics, or selection.
See [ADR 0003](decisions/0003-leakage-safe-linear-comparison.md) and
[EXP-002](experiments/EXP-002-linear-regression.md) for the protocol and results.

