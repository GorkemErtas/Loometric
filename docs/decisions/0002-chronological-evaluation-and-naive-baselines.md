# ADR 0002: Frozen date partitions and naive reference predictors

Status: accepted for A02 / EXP-001.

## Context and options

A01 validates and profiles one historical garment productivity CSV. Repeated teams
and same-date operating conditions make a random row split optimistic. Holding out
teams alone answers an unseen-team question rather than the initial future-shift
question. Sorting dates and splitting individual rows could still mix the same day
between partitions. Recomputing split boundaries on every experiment permits drift.

We need comparable validation evidence before adding further algorithms. Candidate
references are a global historical mean and a department-specific historical mean.
A third-party ML dependency is unnecessary for their arithmetic or regression metrics.

## Decision

Choose contiguous blocks of complete observed dates. For n sorted distinct dates,
use integer boundaries floor(3n/5) and floor(4n/5); require at least three dates and
nonempty train/validation/test blocks. This is approximately 60/20/20 by dates,
not rows. The real source yields 35/12/12 dates, 711/232/254 rows, with inclusive
ranges 2015-01-01–2015-02-10, 2015-02-11–2015-02-25, and 2015-02-26–2015-03-11.
There is no adjustment based on targets or model results.

Persist the source SHA-256, schema/policy version, exact boundaries, date counts,
and row counts in `configs/chronological_split.json`. The initializer creates a file
exclusively and refuses replacement. Consumers verify the source fingerprint and
date-only policy against that configuration before sorting a copy. Any source or
configuration drift fails; future experiments must reuse the existing configuration.

Reuse A01 ingestion, normalization, and source validation. Add a shared validated-load
wrapper without changing the existing profiling command or checks. Isolate split
policy, mean predictors, metric arithmetic, experiment orchestration, and report
rendering in small modules. Use existing pandas and Python standard-library math;
no scikit-learn or other algorithm dependency is introduced.

Fit both reference predictors using training targets only. The department predictor
accepts only department values at inference and falls back to the global training
mean for unknown/missing values. That is a defensive inference rule; source category
validation is not relaxed. Do not use other source features, target clipping, or
imputation. The baseline is static, not an expanding-window estimate.

Declare validation MAE as the primary comparison. Also report RMSE, R², signed bias
(prediction minus actual), department MAE, and training/validation counts. Return
undefined R² for a singleton or constant actuals instead of silently assigning a
finite surrogate. Require finite, aligned metric inputs without dropping rows.

The experiment runner has no test-evaluation option and scores only validation
rows. Record training means, source/split identity, environment, measured runtime,
results, and limitations in EXP-001. Pin the exact existing environment in
`requirements/exp-001.txt`; numerical results are deterministic, while measured
runtime is expected to vary. No random operation needs a seed.

## Consequences and limits

Later experiments share the same date blocks and reference errors. Whole-date
partitioning prevents same-date overlap, but does not establish when outcomes were
finalized. Training labels must have become available before validation starts.
Short history and recurring teams limit generalization claims. No gap or embargo is
guessed without shift/label latency evidence; revisit the protocol explicitly if
new timing information requires one, retaining the original experiment record.

A01 already inspected the complete source distribution. The final test is reserved
from performance evaluation and fitting, not claimed to be unseen in earlier EDA.
Repeated validation comparisons may still overfit development decisions. A final
model and preprocessing must be chosen on training/validation before one final test
evaluation in a separately authorized task.

The version pins describe the current Python 3.13.14 environment. They do not lock
platform-specific wheels or provide hashes for every supported Python/platform.
The local roadmap is deliberately ignored at the user's request; versioned ADRs,
split configuration, code, tests, and experiment report carry the reviewable evidence.

Linear Regression, Random Forest, feature engineering, boosting, tuning, scheduling,
API, storage, and frontend work remain separate future tasks.
