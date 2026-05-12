# Loometric data profile

Source: `data/raw/garments_worker_productivity.csv`  
SHA-256: `763ffcdd39b7f7f360243c2af8f89ed733e8b5f9e511efeb0c886b83e1b76866`  
Rows: **1197**; columns: **15**; validation: **PASS**.

This report describes the supplied CSV only. It does not train a model, infer measurement timing, remove rows, or save a transformed dataset. Numeric summaries exclude missing, unparseable, and nonfinite values; validation reports those issues.

## Validation

| Severity | Code | Count | Finding |
| --- | --- | --- | --- |
| warning | missing_values | 506 | wip: missing values (WIP is assessed separately by department). |
| warning | target_above_one | 37 | Target above 1 requires domain review; retained as-is. |

Counts refer to affected values or rows unless the finding describes schema columns. Duplicate counts count repetitions after the first occurrence. Warnings require review but do not cause a nonzero exit; errors do.

## Dates and chronology

| Check | Observed |
| --- | --- |
| Explicit input format | MM/DD/YYYY (%m/%d/%Y) |
| First date | 2015-01-01 |
| Last date | 2015-03-11 |
| Distinct dates | 59 |
| Missing/invalid dates | 0 |
| Weekday disagreements | 0 |
| Date reversals in source row order | 0 |
| Unobserved calendar dates within range | 11 |
| Exact normalized duplicate rows | 0 |
| Repeated complete (date, department, team) keys | 0 |
| Minimum rows per observed date | 15 |
| Maximum rows per observed date | 24 |

Unobserved calendar dates: 2015-01-02, 2015-01-09, 2015-01-16, 2015-01-23, 2015-01-30, 2015-02-06, 2015-02-13, 2015-02-20, 2015-02-21, 2015-02-27, 2015-03-06.

Dates are not silently sorted. Repeated dates are expected for multiple teams; all rows on one date must stay together in future chronological evaluation. Missing calendar dates do not prove missing shifts without a production calendar. The source contains dates but no shift times, shift IDs, or measurement timestamps.

## Categories

Whitespace is trimmed; department spelling `sweing` is mapped to `sewing`. Raw files remain unchanged. Category values outside the contract are errors.


Raw department labels (quotes expose trailing spaces):

| Raw label | Rows |
| --- | --- |
| 'sweing' | 691 |
| 'finishing ' | 257 |
| 'finishing' | 249 |


### department

Expected categories: sewing, finishing.

| Category | Rows | Percent of all rows |
| --- | --- | --- |
| finishing | 506 | 42.27% |
| sewing | 691 | 57.73% |

Unobserved allowed categories: none.


### quarter

Expected categories: Quarter1, Quarter2, Quarter3, Quarter4, Quarter5.

| Category | Rows | Percent of all rows |
| --- | --- | --- |
| Quarter1 | 360 | 30.08% |
| Quarter2 | 335 | 27.99% |
| Quarter3 | 210 | 17.54% |
| Quarter4 | 248 | 20.72% |
| Quarter5 | 44 | 3.68% |

Unobserved allowed categories: none.


### day

Expected categories: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday.

| Category | Rows | Percent of all rows |
| --- | --- | --- |
| Monday | 199 | 16.62% |
| Saturday | 187 | 15.62% |
| Sunday | 203 | 16.96% |
| Thursday | 199 | 16.62% |
| Tuesday | 201 | 16.79% |
| Wednesday | 208 | 17.38% |

Unobserved allowed categories: Friday.


### team

Team numbers are identifiers, not an ordinal production measure. Positive integer IDs are required; no closed team roster is assumed.

| Team | Rows |
| --- | --- |
| 1 | 105 |
| 2 | 109 |
| 3 | 95 |
| 4 | 105 |
| 5 | 93 |
| 6 | 94 |
| 7 | 96 |
| 8 | 109 |
| 9 | 104 |
| 10 | 100 |
| 11 | 88 |
| 12 | 99 |


`quarter` is a source within-month category, not a financial/calendar quarter. Its allowed labels are checked; its exact date-bucket semantics need confirmation.

## Missing WIP by department

| Department | Rows | Missing WIP | Missing % | Observed zeros | Min | Median | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| finishing | 506 | 506 | 100.00% | 0 | N/A | N/A | N/A |
| sewing | 691 | 0 | 0.00% | 0 | 7 | 1039 | 23122 |

Missing WIP and observed zero WIP are counted separately. The missingness indicator in this table includes blanks and values that failed numeric parsing; parsing failures also fail validation. Department association can suggest a structural reporting pattern, but does not establish why values are absent. Do not fill WIP with zero or a global mean. First confirm applicability by department and that WIP was recorded before the shift. Any later imputation must be fit using training dates only.

## Target distribution

The target is continuous productivity at the end of the shift. Negative values, missing/nonfinite observations, or a constant target fail validation. Values above 1 are retained and flagged for domain review; they are not silently clipped.

| Measure | Value |
| --- | --- |
| Finite observations | 1197 |
| Missing or invalid observations | 0 |
| Unique finite values | 879 |
| Mean | 0.735091 |
| Standard deviation (sample) | 0.174488 |
| Skewness | -0.807492 |
| Quantile 0 | 0.233705 |
| Quantile 0.01 | 0.263593 |
| Quantile 0.25 | 0.650307 |
| Quantile 0.5 | 0.773333 |
| Quantile 0.75 | 0.850253 |
| Quantile 0.99 | 1.00516 |
| Quantile 1 | 1.12044 |

| Target range | Rows | Percent of finite observations |
| --- | --- | --- |
| < 0 (invalid) | 0 | 0.00% |
| 0 to < 0.25 | 6 | 0.50% |
| 0.25 to < 0.50 | 127 | 10.61% |
| 0.50 to < 0.75 | 348 | 29.07% |
| 0.75 to 1.00 (inclusive) | 679 | 56.73% |
| > 1.00 (review) | 37 | 3.09% |

### Target by department

| Department | Finite targets | Mean | Median |
| --- | --- | --- | --- |
| finishing | 506 | 0.752951 | 0.805909 |
| sewing | 691 | 0.722013 | 0.750608 |

### Target by date

| Date | Finite targets | Mean | Median |
| --- | --- | --- | --- |
| 2015-01-01 | 19 | 0.718711 | 0.750428 |
| 2015-01-03 | 21 | 0.802773 | 0.800149 |
| 2015-01-04 | 21 | 0.780174 | 0.800238 |
| 2015-01-05 | 22 | 0.796027 | 0.800248 |
| 2015-01-06 | 21 | 0.805508 | 0.800594 |
| 2015-01-07 | 22 | 0.766212 | 0.800594 |
| 2015-01-08 | 22 | 0.760329 | 0.800386 |
| 2015-01-10 | 22 | 0.771305 | 0.800811 |
| 2015-01-11 | 23 | 0.749045 | 0.800247 |
| 2015-01-12 | 23 | 0.755194 | 0.800274 |
| 2015-01-13 | 22 | 0.755566 | 0.803078 |
| 2015-01-14 | 21 | 0.705987 | 0.800313 |
| 2015-01-15 | 19 | 0.758076 | 0.800031 |
| 2015-01-17 | 21 | 0.73073 | 0.800117 |
| 2015-01-18 | 19 | 0.677029 | 0.692045 |
| 2015-01-19 | 19 | 0.713374 | 0.750063 |
| 2015-01-20 | 15 | 0.697731 | 0.750032 |
| 2015-01-21 | 19 | 0.722101 | 0.750345 |
| 2015-01-22 | 22 | 0.674154 | 0.685193 |
| 2015-01-24 | 23 | 0.748193 | 0.800537 |
| 2015-01-25 | 21 | 0.775002 | 0.800386 |
| 2015-01-26 | 19 | 0.798373 | 0.800034 |
| 2015-01-27 | 21 | 0.784047 | 0.803542 |
| 2015-01-28 | 21 | 0.707524 | 0.755556 |
| 2015-01-29 | 20 | 0.791644 | 0.852014 |
| 2015-01-31 | 24 | 0.854955 | 0.971867 |
| 2015-02-01 | 19 | 0.784116 | 0.850114 |
| 2015-02-02 | 19 | 0.700392 | 0.799963 |
| 2015-02-03 | 19 | 0.784193 | 0.800259 |
| 2015-02-04 | 19 | 0.785273 | 0.779792 |
| 2015-02-05 | 18 | 0.799848 | 0.823036 |
| 2015-02-07 | 19 | 0.76978 | 0.799963 |
| 2015-02-08 | 19 | 0.759322 | 0.800355 |
| 2015-02-09 | 18 | 0.735646 | 0.794983 |
| 2015-02-10 | 19 | 0.773327 | 0.796756 |
| 2015-02-11 | 19 | 0.792223 | 0.800402 |
| 2015-02-12 | 19 | 0.682148 | 0.656667 |
| 2015-02-14 | 17 | 0.702282 | 0.750392 |
| 2015-02-15 | 19 | 0.690723 | 0.700573 |
| 2015-02-16 | 18 | 0.69879 | 0.750504 |
| 2015-02-17 | 20 | 0.703756 | 0.700751 |
| 2015-02-18 | 21 | 0.670933 | 0.734646 |
| 2015-02-19 | 20 | 0.689016 | 0.700572 |
| 2015-02-22 | 20 | 0.655498 | 0.713982 |
| 2015-02-23 | 19 | 0.679018 | 0.750294 |
| 2015-02-24 | 19 | 0.685892 | 0.750177 |
| 2015-02-25 | 21 | 0.716683 | 0.750207 |
| 2015-02-26 | 21 | 0.634143 | 0.700252 |
| 2015-02-28 | 21 | 0.649101 | 0.700237 |
| 2015-03-01 | 20 | 0.668748 | 0.691785 |
| 2015-03-02 | 20 | 0.734732 | 0.762065 |
| 2015-03-03 | 22 | 0.670633 | 0.726495 |
| 2015-03-04 | 21 | 0.718668 | 0.799976 |
| 2015-03-05 | 19 | 0.731563 | 0.800402 |
| 2015-03-07 | 19 | 0.711334 | 0.749987 |
| 2015-03-08 | 22 | 0.73738 | 0.800218 |
| 2015-03-09 | 22 | 0.728803 | 0.794977 |
| 2015-03-10 | 23 | 0.754781 | 0.758229 |
| 2015-03-11 | 24 | 0.727973 | 0.750244 |

Daily summaries describe observed variation; they do not establish a trend or prove stability outside the observed period.

## Numeric summary

| Column | Finite n | Missing/invalid | Mean | Std | Min | P25 | Median | P75 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| team | 1197 | 0 | 6.4269 | 3.46396 | 1 | 3 | 6 | 9 | 12 |
| targeted_productivity | 1197 | 0 | 0.729632 | 0.097891 | 0.07 | 0.7 | 0.75 | 0.8 | 0.8 |
| smv | 1197 | 0 | 15.0622 | 10.9432 | 2.9 | 3.94 | 15.26 | 24.26 | 54.56 |
| wip | 691 | 506 | 1190.47 | 1837.46 | 7 | 774.5 | 1039 | 1252.5 | 23122 |
| over_time | 1197 | 0 | 4567.46 | 3348.82 | 0 | 1440 | 3960 | 6960 | 25920 |
| incentive | 1197 | 0 | 38.2105 | 160.183 | 0 | 0 | 0 | 50 | 3600 |
| idle_time | 1197 | 0 | 0.730159 | 12.7098 | 0 | 0 | 0 | 0 | 300 |
| idle_men | 1197 | 0 | 0.369256 | 3.26899 | 0 | 0 | 0 | 0 | 45 |
| no_of_style_change | 1197 | 0 | 0.150376 | 0.427848 | 0 | 0 | 0 | 0 | 2 |
| no_of_workers | 1197 | 0 | 34.6099 | 22.1977 | 2 | 9 | 34 | 57 | 89 |
| actual_productivity | 1197 | 0 | 0.735091 | 0.174488 | 0.233705 | 0.650307 | 0.773333 | 0.850253 | 1.12044 |

## Retrospective associations

Pairwise Pearson correlations use finite complete pairs only (at least three pairs and variation in both fields). Different rows can contribute to each pair. Team IDs are excluded because they are categorical. These are retrospective associations, not causal effects, feature recommendations, or evidence of prediction-time availability. High correlation with an unavailable field cannot justify using it.

| Column | Complete pairs | Correlation with actual_productivity |
| --- | --- | --- |
| targeted_productivity | 1197 | 0.421594 |
| smv | 1197 | -0.122089 |
| wip | 691 | 0.131147 |
| over_time | 1197 | -0.0542058 |
| incentive | 1197 | 0.0765376 |
| idle_time | 1197 | -0.0808508 |
| idle_men | 1197 | -0.181734 |
| no_of_style_change | 1197 | -0.207366 |
| no_of_workers | 1197 | -0.0579906 |

## Pre-shift problem and leakage assessment

Predict a scheduled team's department-level `actual_productivity` for one upcoming shift using information frozen immediately before that shift starts. The tentative source grain is (date, department, team); repeated keys need source-owner review because the CSV does not identify individual shifts.

| Column | Availability | Pre-shift interpretation |
| --- | --- | --- |
| date | pre_shift | Shift date is known; also the future split boundary. |
| quarter | conditional | Source means a within-month bucket, not a calendar quarter; verify and derive from date. |
| department | pre_shift | Scheduled department; normalize sweing and whitespace. |
| day | pre_shift | Known calendar value; derive from the scheduled date. |
| team | pre_shift | Scheduled team identity; treat as categorical. |
| targeted_productivity | conditional | Use only a frozen target set before the shift; later revisions would leak information. |
| smv | conditional | Use only the standard minute value of the style assigned before the shift. |
| wip | conditional | Measurement time is unknown; only a verified opening backlog snapshot is eligible. |
| over_time | post_shift | Realized overtime is not known before the shift; planned overtime needs a separate field. |
| incentive | post_shift | Realized payment can depend on output; a preannounced incentive plan is a separate field. |
| idle_time | post_shift | Downtime accumulates during the shift. |
| idle_men | post_shift | Idle staffing is observed during the shift. |
| no_of_style_change | conditional | A realized count is unavailable; require a frozen planned style-change count. |
| no_of_workers | conditional | Require planned staffing, not realized attendance or a shift-average headcount. |
| actual_productivity | target | Post-shift outcome; never an input for the same shift. |

Only `pre_shift` fields are eligible by default. `conditional` fields remain excluded until their timestamps and business definitions are verified. `post_shift` fields and the target are excluded. These are conservative availability assumptions, not facts established by this CSV, which has no measurement timestamps.

Future evaluation must use strictly increasing date blocks with every record from a date in the same partition. Do not randomly split rows: teams repeat, and same-date shifts share context. Fit any imputation, encoding, scaling, or selection on the training period only. No split or preprocessing fit is performed in this task.

## Next data decisions

Confirm row grain, productivity units and values above 1, pre-shift field timestamps, fractional staffing, within-month quarter semantics, and department WIP reporting. Resolve validation errors before any training. Choose future date boundaries based on the available history; no dates or split ratios are guessed here.
