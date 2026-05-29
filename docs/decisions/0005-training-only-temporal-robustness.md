# ADR 0005: Expanding-window audit inside the frozen training partition

Status: accepted for EXP-004. Policy fixed before executing model comparisons.

## Context and options

EXP-003's selected shallow forest reduces validation MAE by 2.1120%, but its R²
remains negative and only one short validation period was used. A further adaptive
search would spend more of that validation period without establishing stability.
Options are another model search, another use of the original validation block,
or a fixed temporal audit inside original training. Choose the last option.

This is retrospective robustness analysis: B_RF-01 was already selected using the
original validation labels, and the inner evaluation rows were previously training
data in EXP-001 through EXP-003. The audit is not independent confirmation of that
selection, a new untouched holdout, or permission to evaluate the final test.

## Decision

Read and verify the existing dataset fingerprint and chronological split unchanged.
After the existing source/split checks, access only the original training frame.
Do not access original validation/test frames for features, fitting, predictions,
metrics, diagnostics, or model choice. Keep inherited whole-source schema/domain
validation distinct from performance scoring. No split initialization or rewrite.

Within the 35 original training dates, use an initial prefix of 15 observed dates,
then evaluate the next 5 complete observed dates. Expand the training prefix by 5
dates and repeat. Evaluation windows are adjacent and nonoverlapping. This gives
training/evaluation date counts 15/5, 20/5, 25/5, 30/5, covering the final 20 original
training dates exactly once. The initial 15 dates are warm-up training only.
Count observed dates, not rows or equally spaced calendar days; calendar durations
may differ. A generic caller with a trailing incomplete window includes it explicitly
rather than dropping dates. Require at least one evaluation date and fail on invalid
policy/input or an input frame that does not match the supplied training bounds.

The resulting date-only ranges and row counts, inspected before model execution:

| Fold | Training inclusive | Training rows | Evaluation inclusive | Evaluation rows |
| --- | --- | --- | --- | --- |
| F01 | 2015-01-01 to 2015-01-18 | 318 | 2015-01-19 to 2015-01-24 | 98 |
| F02 | 2015-01-01 to 2015-01-24 | 416 | 2015-01-25 to 2015-01-29 | 102 |
| F03 | 2015-01-01 to 2015-01-29 | 518 | 2015-01-31 to 2015-02-04 | 100 |
| F04 | 2015-01-01 to 2015-02-04 | 618 | 2015-02-05 to 2015-02-10 | 93 |

Refit these five fixed references independently for every fold:

1. Global mean of that fold's training labels.
2. Department means of those labels, with the existing global-mean fallback.
3. Existing OLS A: department + categorical team.
4. Existing OLS B: A + categorical weekday + numeric day of month.
5. Frozen B_RF-01 using B, 100 trees, max_depth=3, min_samples_leaf=20,
   random_state=42, n_jobs=1, and all other EXP-003 settings unchanged.

Reuse source normalization, stateless features, preprocessing, model constructors,
and metric/diagnostic arithmetic. Fit each encoder and estimator freshly on only
the earlier fold prefix. Do not warm-start, update within an evaluation window,
reuse a fitted vocabulary, tune hyperparameters, introduce new features, try extra
seeds, or choose a winner from this audit. A later fold may train on earlier-fold
evaluation labels only under the explicit assumption they were finalized by its
cutoff. No embargo is invented without evidence about outcome latency; this remains
a limitation requiring source-owner confirmation.

Report all fold MAE/RMSE/R², prediction-minus-actual bias, department metrics,
training MAE/gap diagnostics, category vocabularies/unknown counts, prediction ranges,
and measured fit/inference runtime. Compare to each fold's department mean using
signed absolute and relative MAE changes. A forest win/loss requires a difference
greater than 1e-12; smaller differences count as ties.

Concatenate the disjoint evaluation predictions for pooled row-weighted metrics.
Also report equal-fold mean MAE, population standard deviation (ddof=0), and range.
These are different summaries when windows contain different numbers of rows.
Do not average fold RMSE or R² as a substitute for recomputing pooled metrics.
Report pooled department errors and forest win/loss/tie counts overall and by
department. Fold standard deviation and win counts are descriptive, not confidence
intervals or significance tests: training prefixes overlap and teams/dates recur.

Store all numerical results and original-training-only out-of-fold predictions in
ignored local JSON. Preserve earlier reports, model settings, dependency snapshots,
raw data, and ignore rules. No new dependencies, model registry, generic CV engine,
backend, UI, gradient boosting, or final-test evaluation is needed.

## Consequences and limitations

The study tests temporal consistency of fixed choices, not improvement from another
search. Different fold training sizes, calendar periods, target distributions, and
recurring teams are confounded; do not attribute changes solely to learning more
data or to drift. A frozen candidate can lose to the baseline on inner periods even
if it won the original validation comparison. Preserve both findings explicitly.

Feature availability remains provisional: scheduled date and assignments must be
known at cutoff, and source snapshots/label-finalization timestamps are missing.
Calendar derivation is deterministic but does not certify the scheduled-date source.
Conditional planning fields and realized shift values stay excluded. Evidence of
instability or unresolved timing should guide whether more complex algorithms are
worth a later bounded experiment; it cannot establish production readiness.

Reference: [scikit-learn temporal-split discussion](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).
We use complete observed-date groups rather than applying its row-index splitter
directly to multiple records per date.
