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

