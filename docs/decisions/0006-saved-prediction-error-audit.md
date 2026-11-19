# ADR 0006: Analyze validated saved predictions without retraining

Status: accepted for EXP-005; diagnostic definitions fixed before execution.

## Context and decision

EXP-004 found that the selected forest's validation advantage was not stable across
inner periods. The next task is to explain errors and assess experimental prediction
readiness, without another model or parameter search. Reuse its saved predictions;
do not rerun the earlier experiments or inspect outer holdout records for diagnostics.

Separate pure error aggregation from the experiment loader/CLI. The latter reuses
source validation and frozen split/fingerprint checks, then consumes only `.train`.
It verifies the EXP-004 identity, split-file hash, fold policy/ranges/counts, exact OOF
row order, dates, departments, targets, prediction lengths/finite values, fixed model
parameters, and reproduced stored metrics. Join team metadata from the original
training frame only. A missing/invalid artifact fails explicitly rather than silently
refitting or inferring a replacement. Record the input artifact's SHA-256 in outputs.

Analyze exactly the same OOF records for department mean, Linear Regression A, and
frozen B_RF-01. Reuse regression metric arithmetic. No learning, target-derived input
features, clipping, imputation, or changes to existing experiment outputs.

Predefine these descriptive summaries:

- Absolute and signed error quantiles, using linear interpolation; bias is prediction
  minus actual. Keep every row in the primary metrics.
- Absolute error >= 0.30 is a descriptive high-error threshold, not a business limit.
- Largest ceil(1%, 5%, 10% of n) errors: shares of total absolute and squared error,
  plus remaining MAE for within-model sensitivity. Ties sort by source row ID.
- A common sensitivity population excludes the department baseline's worst ceil(10%
  of n) rows from every model equally. Report the exclusion/counts explicitly; this
  error-conditioned sample is not a new unbiased performance estimate or model choice.
- Fixed slices: fold, date, department, fold/department, department/team, and
  fold/department/team. Group team within department because roster/ID semantics are
  unverified. Show counts and observed dates. Flag n<20 as low support; n>=20 does
  not establish independence or sufficient statistical power.
- Target distributions use each OOF record once, not three copies. Compare fold
  target means/distributions and the range of fold means for recurring department/team
  IDs. Missing team/window cells remain absent, with coverage and minimum cell size
  reported; do not impute or rank small groups as reliable business findings.

Keep observation-level high-error details and complete numerical diagnostics in
ignored local JSON. Version only code/tests and reviewed aggregate documentation;
do not commit raw records, raw datasets, generated artifacts, or local instructions.

## Consequences and limits

Artifact validation guards against misaligned or stale evidence; it is not a
cryptographic proof of the original model execution. Dataset/artifact identities,
parameters, matched records, and recorded scores provide traceability. Source-wide
schema/domain validation remains inherited and distinct from holdout exploration.

These are retrospective diagnostics on previously used training records. Repeated
teams/dates and overlapping training prefixes invalidate an independent-observation
interpretation. Tail exclusions, quantiles, small-cell variation, and correlations
do not establish causation, significance, calibrated forecast uncertainty, or
production readiness. No new model is selected from this audit.

Readiness distinguishes confirmed engineering behavior from provisional availability
assumptions and unverified operational requirements. A local, explicitly experimental
historical evidence-review application is a possible next milestone; live factory
decisions require real timestamped snapshots, finalized labels, definitions,
freshness agreements, uncertainty/monitoring evidence, and human oversight.
