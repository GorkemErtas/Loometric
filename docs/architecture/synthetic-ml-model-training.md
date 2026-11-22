# M08B: Offline synthetic model training and robust evaluation

Policy: `synthetic-training-v1`. Experiment: EXP-006. Dataset: `synthetic-ml-v1`.
This milestone trains and evaluates offline synthetic regressors. It creates no
ML endpoint, frontend prediction page, database, deployment, automatic retraining
or prediction-to-capacity adapter. M01–M08A data/contracts and planning algorithms
remain unchanged. [ADR 0020](../decisions/0020-synthetic-model-development-and-promotion.md)
and the [predeclared configuration](../../configs/synthetic_training_v1.json) fix
the experiment before fitting; [EXP-006](../experiments/EXP-006-synthetic-productivity.md)
records actual results, fingerprints, corrections, costs and limitations.

## Target and population

Predict `standard_capacity_attainment` thirty minutes before a scheduled synthetic
shift. The target is completed good pieces × declared standard worker-minutes per
piece / frozen planned available worker-minutes. It is **demand-censored attained
output**, not intrinsic worker efficiency. Absences and unplanned loss reduce the
numerator; the denominator remains the plan. Values above one are legitimate and
are never clipped. Nothing establishes equivalent semantics for historical M01
`actual_productivity`, or authorizes mapping either target to M02 efficiency.
See the [data foundation](synthetic-ml-data-foundation.md),
[dictionary](../data/synthetic-ml-v1-dictionary.md) and
[M07B compatibility audit](ml-planning-compatibility.md).

| Baseline world | Original training / eligible / undefined | Original validation / eligible / undefined |
| --- | --- | --- |
| Development seed 19 | 540 / 537 / 3 | 180 / 180 / 0 |
| Development seed 42 | 540 / 532 / 8 | 180 / 178 / 2 |
| Development seed 73 | 540 / 535 / 5 | 180 / 179 / 1 |
| Benchmark seed 42 | 14,880 / 14,711 / 169 | 4,880 / 4,833 / 47 |

Undefined zero-planned-capacity labels are excluded **only from regression** with
IDs, counts, reason `ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET` and no-prediction
status retained in `undefined-label-exclusions.jsonl`. They are not imputed as zero
or silently discarded. Inference on such a context must abstain. All models use
identical defined-label observations in each evaluation, including contexts flagged
for review. Conditional support-filtered metrics never replace the primary metrics.

Three development seeds each have baseline, disruption and workload-surge datasets.
Their training content must exactly match the corresponding baseline; stress
evaluations reuse its already trained models. Benchmark is seed42/baseline only.
No sources are pooled for fitting. These are paired/generated worlds sharing a
process, assumptions, identifiers and sometimes seed-specific structures; they
are not independent factory replications or grounds for population confidence
intervals. Raw counts describe simulation exposure, not independent sample size.

## Receipt-bound development loading

`loometric.synthetic_training.data.load_development(directory,
expected_fingerprint=...)` requires an independently retained manifest receipt.
The ten committed bindings come from prior M08A generation receipts retained
outside the dataset directories. Never discover the expected value by hashing an
untrusted current manifest and then accepting it as its own authority.

The loader first verifies the M08A manifest/policy and **every file's bytes and row
counts**, including the aggregate content fingerprint. Reserved `outcomes.jsonl`,
`labels.gap.jsonl`, `labels.test.jsonl`, and QA reports remain opaque byte streams:
no target decoder, dataframe conversion, model, distribution statistic or score
receives them. Integrity scanning does not inspect reserved values. The M08A
generator, whole-bundle reader and QA audit are not called on study datasets.
Their broader label-inspection behavior is deliberately outside this boundary.

Decode typed pre-shift references/plans and membership metadata; select only train
and validation IDs; decode only those two label files. Check closed schemas,
references, unique identities, chronological membership, declared pre-shift capture,
crew/process/style correspondence, exact stock/capacity/target algebra, label
finalization delay and absolute-time maturity before validation. Reconstruct the
feature view with unchanged M08A helpers and compare it to the materialized view.
Reverify file hashes after loading to reject input drift during the read.

Retain exact decimal source strings until validation. Convert model numbers to
finite float64 only if absolute conversion error is at most `1e-12`; counts,
ordinals and booleans retain their validated meaning. The target still has its
M08A 28-significant-digit Decimal source definition. Grouped workload bands use
exact rational arithmetic reconstructed from the validated integral counts and
at-most-two-decimal standards, preventing binary rounding at 0.6/1 boundaries.

The model matrix contains exactly the thirteen M08A input columns in their declared
order. Stage, shift kind and weekday are categorical; the other ten are numeric.
No observation/factory/line/crew/style ID, raw timestamp, seed, scenario, partition,
population, actual attendance/loss, completed pieces, closing WIP or latent process
variable enters the matrix. Dataframe indices identify observations for alignment,
not predictors. A schema guard rejects extra or reordered columns. Model fitting
requires aligned finite targets; validation never fits preprocessing.

## Baselines, preprocessing and bounded search

| Model | Fixed policy |
| --- | --- |
| Global mean | Arithmetic mean of eligible training labels |
| Stage mean | Training stage mean; unseen stage falls back to global mean |
| Grouped mean | Stage × shift × planned-load band; minimum10 training rows; fallback stage/shift → stage → global |
| Ridge | Alpha1 or10; numeric StandardScaler; dense full one-hot categories; solver SVD |
| Random Forest | 150 trees, depth6/leaf minimum10 or depth12/leaf minimum5, random state42, one worker |
| Histogram boosting | 150 iterations, learning rate0.05, leaves15/L2=5 or leaves31/L2=10, random state42, no early stopping/internal validation split |

Planned load is order pieces × standard / planned available worker-minutes, using
no outcomes. Bands are low≤0.6, nominal(0.6,1], high>1. Diagnostic staffing bands
are1–5/6–10/11+ workers; interruption bands are0/1–30/31+ planned minutes. These
boundaries are predeclared, not chosen from error slices. Global/stage baselines
are recorded even when the grouped baseline is strongest.

Each fold fits fresh preprocessing. One-hot uses `handle_unknown="ignore"`, no
dropped category, dense output. Unknown categories therefore produce an all-zero
group mechanically; support policy still abstains on them. Ridge scales numeric
inputs with training-only means/scales. Trees pass numeric values through. There
is no target scaling, missing-value imputation or feature selection. The raw
predictor is not an approved operational input gate.

## Temporal development and model-selection rule

On eligible original-training dates, use three expanding evaluation windows
starting at floor(n/2), floor(2n/3), floor(5n/6), each width floor(n/6), with one
preceding observed date purged from that fold's training prefix. Evaluation windows
are disjoint, and every fold checks that all prefix labels mature strictly before
its first evaluation cutoff. Outer validation never enters these folds. Source
embargo/gap dates remain excluded as well. No reserved entity population is scored.

Compare all three naive models and all six ML configurations on the same fold
observations. The search score gives half its weight to mean development-seed MAE
and half to benchmark MAE; fold means are equally weighted within each world.
Select one configuration per family and the naive reference using this score only.
Outer validation admits or rejects those fixed finalists; it cannot retune their
hyperparameters. Dataset counts, date ranges, training IDs/payload fingerprints,
preprocessing state, estimator parameters and model seed accompany every fit.

Promotion requires all the following frozen gates:

- At least5% macro-profile baseline-validation MAE improvement over the selected
  naive reference and the strongest aggregate outer-validation naive comparator.
- Strict improvement in every baseline world and at least two temporal fold wins
  out of three in every world.
- At most5% stage MAE regression in **every** world/scenario stage cell.
- No mean stress-scenario MAE regression; no individual stress-seed regression
  above10%.
- At most5% P95 positive-error regression and10% worst absolute-error regression
  in every world/scenario cell.

Among eligible candidates within1% of the best macro MAE, prefer Ridge, histogram
boosting, then forest. These are experimental engineering criteria, not approved
factory loss tolerances or statistical significance thresholds. Zero-reference
percentage comparisons that imply an undefined increase are reported null and
fail the gate, not serialized as Infinity. If none qualifies, retain the training-
fold-selected naive baseline and report **NO_ML_PROMOTION**. No forced winner.

The actual study executes132 fits:108 training-fold fits and24 full-original-
training finalist/reference fits. Limits are144 fits,20,000 rows per fit, fixed
feature/estimator bounds, RF one worker and numerical thread pools one. A600-second
budget is checked between fits, not enforced as a native-call OS watchdog. Existing
security worker allowlists and process policies are unchanged. Measured runtime,
batch prediction cost and whole-process lifetime peak working set are separate
from deterministic selection; memory is not attributed to individual estimators.

## Metrics, error slices and risk

Every primary metric includes all eligible observations. Report MAE, RMSE, R²,
prediction-minus-actual bias, median/P90/P95/max absolute error, signed-error tails,
P95 positive error, range counts and worst observation identities. Constant/single-
sample target R² is null. Each subgroup has its own count; cells under30 observations
are marked low support. Slices cover stage, day/night, staffing, planned workload,
interruptions, low demand, actual demand censoring and calendar week. Demand
censoring is an outcome-derived **diagnostic**, never a predictive feature.

Compute absolute-residual P90 from original-training OOF predictions, by stage
when at least30 rows are available, otherwise global fallback. Prediction±radius
is a descriptive development error band. The same folds also selected configurations;
this is not independent calibration, a confidence interval or a conformal guarantee.
Outer-validation coverage/width is empirical only. Band endpoints and point
predictions remain unclipped. Nothing is calibrated against reserved test labels.

Feature support uses original-training categories, numeric bounds and label bounds.
The offline support assessor abstains for unknown categories, missing/extra fields,
nonfinite/physically invalid inputs, zero planned capacity, negative/nonfinite
predictions and predictions beyond the v1 physical envelope. Numeric extrapolation
or a prediction beyond observed training-label support requires review. A finite
prediction above one is permitted. The assessor concerns features only; it cannot
validate unseen factory/crew transport or detect an unobserved future disruption.
Even SUPPORTED_EXPERIMENTAL grants no serving/capacity permission.

## Artifacts and reproducibility

The final artifact is fitted on **benchmark original training only**, including
14,711 defined labels. There is no refit on validation or test. The selected result
may be the explicit naive fallback. Store means as transparent JSON; an eligible
ML pipeline would use trusted-local joblib bytes. This milestone provides only
metadata/byte integrity inspection, never an automatic executable deserializer.

All outputs use new directories under ignored `data/processed/synthetic_training/`:
`report.json`, `training-oof.jsonl`, `validation-predictions.jsonl`,
`undefined-label-exclusions.jsonl`, model JSON/pipeline, `measurements.json` and
completion-marker `manifest.json`. The manifest binds configuration, exact feature
order, model identity, source manifest/content/split/training identities, training
dates, preprocessing/support/risk, validation evidence, environment and file hashes.
Separate nondeterministic timing/memory measurements are not part of the deterministic
artifact fingerprint. An independently retained receipt is required for inspection.
Hashes prove integrity relative to that receipt, not publisher authenticity or
safe execution. Existing outputs cannot be overwritten; interrupted incomplete
directories require a fresh path and are not automatically deleted.

```powershell
.venv/Scripts/python.exe -m loometric.synthetic_training run --output data/processed/synthetic_training/my-exp-006
.venv/Scripts/python.exe -m loometric.synthetic_training inspect --artifact data/processed/synthetic_training/my-exp-006 --expected-fingerprint <retained-receipt>
```

There is no partition override, automatic source regeneration, test-evaluation
command, artifact execution endpoint or planner application switch. A run uses
the ten explicit expected receipts in its versioned configuration. Different
environments require a separately reviewed regeneration/reproduction decision;
no silent migration is performed. The experiment report records actual independent
repeatability, numerical tolerances, model-selection decision and full regression QA.

## Executed verification and preservation

| Command | Actual result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/synthetic_training -q -p no:cacheprovider` | 61 passed in43.58s after the exact-band correction |
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | 1,142 passed in242.82s, normal pytest temporary directory |
| `.venv/Scripts/python.exe -m ruff check . --no-cache` | Passed |
| `.venv/Scripts/python.exe -m ruff format --check . --no-cache` | All checked files formatted |
| `.venv/Scripts/python.exe -m pip check` | No broken requirements |
| `npm run typecheck` in frontend | Passed |
| `npm run check` in frontend | Biome passed,55 files |
| `npm test` in frontend | 139 passed across6 files,21.17s |
| `npm run build` in frontend | Type check/Vite passed,65 modules |
| `npm run test:browser` in frontend | 10 passed in1.1m; owned listeners closed/credentials discarded |
| `npm ls --depth=0`, `npm audit --audit-level=low` in frontend | 17 exact direct dependencies present,zero vulnerabilities |
| Two corrected independent study runs and receipt inspection | All six deterministic output files byte-identical; metadata/byte checks passed without executable loading |

Tests cover receipt/content verification before decoding, closed feature order,
explicit null-target exclusions, train-only scaling/encoding/means/fits, unknown
groups/categories, exact workload thresholds, hand-calculated metrics, fold label
maturity and anti-overlap, all promotion gates/fallback, support/range/abstention,
uncalibrated bands, artifact tampering and no automatic joblib loading. Private
fixtures deliberately replace reserved/gap/outcome JSON with undecodable bytes;
authorized X/y remain unchanged. Fit spies verify all132 fits receive only original
training IDs. Existing full-suite fits use private fixtures, not the real M01 CSV
or actual reserved synthetic labels.

Verification corrections are explicit: a perfect-baseline unit case initially
failed percentage JSON serialization; undefined increases are now null with failed
gates. Provisional study a/b was superseded after an exact0.6 workload-band audit
found one floating-boundary mismatch; regression and corrected c/d repeat are
recorded in EXP-006. A local read-only summary helper's shell quoting error was
corrected without changing results. Routine formatting issues and a Ruff cache
write warning were resolved; final checks use `--no-cache`. Failed/provisional
work is not counted as final evidence. Normal native/temp process permissions
were used for pytest/browser tests. Only the existing NO_COLOR/FORCE_COLOR browser
warning remained. Windows is verified; other hosts and environments are not.

An independent SHA audit preserves665 of666 original tracked/existing-data files
byte-for-byte; README is the sole intended modified original. This covers original
M01 data/artifacts/splits/experiment reports, all M08A source bundles and frozen
planning/security/frontend code. All39 Python pins match, dependencies/lock/ignore
files are unchanged, and all59 relative links in the affected documentation resolve.
The study configuration still equals its committed pre-fit declaration and all ten
expected source receipts match independent M08A records. Generated models, reports,
predictions and local AGENTS/plan files remain ignored/untracked.

## M08C readiness and remaining blockers

**Offline artifact/evidence only; ML serving and planning are NOT authorized.**
The experiment's exact decision and failed gates are in EXP-006. Do not translate
an aggregate error reduction into permission to apply capacity, or suppress weaker
stages. All unseen crew/line/factory/style test populations remain reserved for a
separately defined and explicitly approved final-evaluation milestone. No tests
were consumed merely to fill generalization tables.

Before a separately scoped M08C, define a strict live-input/cutoff/source-context
contract, trusted loading policy, scoped synthetic demonstration workflow, visible
abstention/review and baseline fallback, latency/resource behavior and session/error
semantics. Uncalibrated error bands, invisible shift, weak subgroup evidence and
unassessed entity transport remain scientific limitations. Real-factory use would
need independent authorized evidence and operational controls. M02's [0,1]
efficiency remains a different declared planning assumption; conversion is absent.
M08B stops here.
