# ADR 0020: Bounded synthetic model development, guarded promotion and local artifacts

Status: accepted before EXP-006 model fitting. Policy: synthetic-training-v1.

## Context and options

M08A provides explicit synthetic attained-standard-output units and reserved
populations. Its general reader also parses reserved outcomes, which is unsuitable
for M08B's stricter development-only boundary. Options are reuse that whole-reader,
train on a wide generated table, or add a receipt-bound development reader and a
separate offline study. Choose the last, preserving all M01–M08A source contracts.

## Decision

Verify retained manifest, every file's bytes/counts and content fingerprint before
loading. Reserved outcome/gap/test files are hashed as opaque bytes only. Decode
pre-shift references and only train/validation label files; never call the M08A
generator, whole-bundle reader or quality audit on study data. Reconstruct eligible
features with M08A helpers, validate exact target algebra, then convert to finite
float64 with absolute error at most1e-12. Audit and exclude undefined zero-capacity
labels from regression, retaining their IDs/counts/reasons and no-prediction status.
No imputation, clipping, metadata predictors or historical-source mixing occurs.

Predeclare the entire study in configs/synthetic_training_v1.json using independently
retained M08A receipts. Four baseline worlds: three development seeds and benchmark
seed42. Six development stress datasets reuse their corresponding baseline-trained
models after verifying identical training content. They are paired simulations,
not independent factory evidence. Profiles/seeds are never pooled for training.

Within each original training partition use three expanding windows starting at
floor(n/2), floor(2n/3), floor(5n/6) dates, width floor(n/6), one purged preceding
date and strict absolute label maturity. Fit every transformation only on that
prefix. Compare global/stage/grouped means, Ridge alpha1/10, forests150 trees
depth6/12 leaves10/5, and histogram boosting150 iterations leaves15/31 L2=5/10.
One-hot stage/shift/weekday, numeric scaling for Ridge only; no early stopping or
implicit internal validation split. Fixed model seed42, RF one worker, numerical
thread pools one, fixed estimator/row/search bounds. No new dependencies.

The grouped baseline uses stage × shift × planned-load band (≤0.6, (0.6,1], >1),
minimum10 training observations, then stage/shift, stage, global fallback. The
stage guard and both tail guards apply to every world/scenario cell, rather than
only a pooled average. Staffing bands are1–5/6–10/11+, interruption bands0/1–30/31+
minutes. These diagnostic boundaries are fixed before fitting, not learned from
held-out labels. Runtime bounds are estimator/row/search/thread limits; elapsed
time is checked between fits, not an OS guarantee against a hung native call.

Select one configuration per family using training-fold MAE, weighted half to the
mean development-seed score and half to benchmark; all worlds remain correlated
synthetic evidence. Outer validation can admit or reject these fixed finalists,
not retune them. The naive reference is the best training-fold naive model.
Promotion requires at least5% macro-profile baseline-validation MAE improvement,
positive improvement in every baseline world, at least2/3 temporal wins per world,
no stage MAE regression over5%, no stress-scenario macro MAE regression and no
stress-seed regression over10%, plus P95 positive-error regression at most5% and
worst absolute-error regression at most10%. Also beat the strongest aggregate
outer-validation naive comparator by5%. These are experimental engineering gates,
not factory-acceptable risk thresholds. Within1% of the best eligible score prefer
Ridge, histogram boosting, then forest. If none qualifies, NO_ML_PROMOTION and
retain the training-fold-selected naive baseline. Never force a complex winner.

Use training-OOF absolute-residual P90, per stage with minimum30 observations or
global fallback, as a descriptive risk radius. Model selection reused those folds:
bands are not calibrated confidence/conformal intervals. Report their empirical
outer-validation coverage/width without a coverage guarantee. No test calibration.
Zero capacity, invalid inputs and unknown categories abstain. Training-support
extrapolation and predictions beyond training-label support require review; finite
values above1 remain permitted. Raw validation metrics retain all defined-label
observations, including flagged contexts, with separate support/risk counts.

Publish the selected benchmark-training-only candidate or naive baseline as an
ignored create-only versioned artifact with exact configuration, feature order,
training/dataset/split/environment/support/risk/validation identities and receipts.
Store transparent means as JSON; ML pipelines as trusted-local joblib bytes.
Provide integrity inspection only, no automatic deserializer or serving endpoint.
Separate deterministic metrics/receipts from measured timing/process-memory logs.
Reproduce the full study and compare selection, predictions and metrics, documenting
floating tolerances. No refit on validation, final-test scoring or planning adapter.

## Consequences

Results concern synthetic demand-censored attainment, not intrinsic efficiency,
worker performance or measured factory improvement. Original unseen entity tests
remain reserved and explicitly deferred. Distribution shift can be invisible to
the feature schema, and descriptive bands cannot guarantee safety. M08C requires
separate scope, a trusted loading/input contract and review of evidence/limitations;
M08B does not begin it or authorize capacity conversion.
