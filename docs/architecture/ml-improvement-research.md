# M09A: Offline ML improvement research

This is a separate research package, `loometric.ml_research`, with no changes to
the M08C registry, serving artifacts/API/dashboard or frozen planning engines.
The target and thirteen original pre-shift inputs remain synthetic-ml-v1 standard
capacity attainment. [ADR0022](../decisions/0022-development-only-ml-improvement-research.md)
and the [pre-fit declaration](../../configs/ml_improvement_v1.json) define the
bounded study. Actual findings and receipts belong to
[EXP-008](../experiments/EXP-008-ml-improvement-research.md).

## Evidence boundaries and scientific questions

The original validation sets have been repeatedly inspected. They can explain
packing/cutting regressions, workload censoring, stress bias and descriptive error
bands, but cannot be fresh confirmation or select new candidates. Reserved final
tests remain untouched. Synthetic worlds share an assumed law; their seeds and
profiles are not independent real factories. Repeated observations on the same
crews/lines must not be counted as independent entity evidence.

The study asks whether planned feature representation, regularization or partial
pooling improves prediction, and which failures reflect unavailable information.
The simulator has latent line/crew/shift effects, absence/loss/noise and difficult
events. These are not pre-shift observations. It is invalid to reconstruct hidden
RNG streams, add scenario flags, or use realized losses/attendance/censoring as
predictors. A large residual alone does not identify its hidden cause.

## Receipt-bound data and diagnosis

Reuse the M08B development-only loader and independently retained ten source
receipts in the frozen study declaration, canonical SHA
`40b75e3a5854679f990cb1c6647302752ede45ed33773787172179d85c181c52`.
The corrected EXP-006 manifest must match
`cd19c78c8321ac1bb69dc16d61dc7de01469e35f0d35afe3a3d8c8dca4e8b7b4`.
All file bytes are checked before decoding. Global outcomes, gap/test labels and
QA reports remain opaque; only authorized train/validation labels are decoded.
No actual dataset generation or whole-bundle outcome reader is called.

Project factory/line/crew/style IDs only from the receipt-bound, outcome-free
feature view for authorized observations, checking that file before/after the
projection. Join them to diagnostic metadata only; they never enter an estimator.
Count rows, dates and distinct entities in each stage. Undefined zero-capacity
labels remain audited exclusions under the original policy, never imputed.

Reconstruct the retained Grouped Mean/Forest12/Hist31 validation vectors on exactly
the same IDs/order. Require equal target values and reproduce the historical
metrics before analysis. Report MAE/RMSE/R², bias, P90/P95/worst errors, positive
tails, physical offered-work ceiling violations, stage/shift/staffing/workload/
planned-stop/censoring slices and explicit interaction cells. No predictions are
clipped or silently excluded. Censoring is an outcome diagnostic only.

For each historical model pair and stage, resample whole local start dates 500
times and report the descriptive 2.5/97.5% interval for matched MAE differences.
Positive left-minus-right means the left model is worse. These intervals are
conditional date-resampling sensitivity, not independent-crew/factory confidence
intervals or significance proof. Persistent entity effects remain correlated
across dates; small cells and three development seeds limit inference.

Baseline/disruption validation inputs must be exactly identical within each
seed, with identical frozen predictions. For each such paired target difference
delta, any single prediction for that identical input has balanced-pair mean
absolute error at least abs(delta)/2. Aggregate this over the observed pairs;
the analogous empirical RMSE bound is sqrt(mean(delta²))/2. This is a bound for
that balanced paired sample, not a universal Bayes-error estimate. More rows of
the same uninformative inputs cannot reveal which hidden scenario occurred.

## Predeclared original-training candidate protocol

Canonical EXP-008 declaration SHA:
`475da83d18ca820618520a6acfea1c6f2c6b799843f9d316ddc9b73e2d8d7591`.
It was committed before actual comparisons. Three new expanding windows use date
fifths [2/5,3/5),[3/5,4/5),[4/5,1). Remove the preceding observed date from every
training prefix and require all training labels to mature before the first
evaluation cutoff. Evaluation windows are disjoint. This reuses original training
data, including dates previously studied in M08B; it is not an untouched holdout.

Compare three references (Grouped Mean, raw Forest12, raw Hist31) and six fixed
candidates. All tree seeds 42, one numerical thread, full training-fitted OHE,
no early stopping/internal random validation split, no pooling of worlds.

| Candidate | Fixed change |
| --- | --- |
| rf_physics | Forest12 plus planned derived features |
| rf_physics_regularized | Same features; 150 trees, depth 8, leaf minimum 15, max_features 0.8 |
| hist_physics | Hist31 plus planned derived features |
| hist_physics_regularized | Same features; 150 iterations, 15 leaves, L2=20 |
| hist_residual | Training-fitted Grouped Mean plus regularized histogram residual model |
| hist_stage_shrunk | Global regularized histogram plus supported stage models blended by n/(n+200) |

Histogram rate 0.05; stage models need at least 200 training rows and five training
dates, otherwise use global. Signed residuals have a distinct response guard;
original attainment labels remain nonnegative. All fit matrices must equal their
original-training rows. Record case, scope, response kind, IDs/payload hashes, dates,
rows, parameters, seed and environment. At most 300 estimator fits, 20,000 rows/fit
and 1200 seconds checked between fits. These bounds are not an OS training watchdog.

The stateless feature transformer appends eleven features to the original order:
planned available worker-minutes; offered standard-work/load ratio; the attainment
quantum of one completed piece; declared ordinal skill×complexity; opening WIP
share; planned downtime/480; five stage×load interactions. None uses a label,
realized outcome, identity, seed/scenario, timestamp or fitted aggregate. Explicit
units and raw/engineered order are bound into each report. The ordinal interaction
does not claim a calibrated physical skill scale. Stock sums and positive planned
capacity are validated; no imputation or clipping occurs.

For quantity Q (pieces), standard S (worker-minutes/piece), planned workers W,
available minutes M and planned downtime D (minutes), the exact appended columns are:

| Derived column | Definition | Unit |
| --- | --- | --- |
| planned_worker_minutes | M × W | worker-minutes |
| planned_load_ratio | Q × S / (M × W) | standard worker-minutes / planned worker-minutes |
| one_piece_attainment_quantum | S / (M × W) | attainment ratio per completed piece |
| skill_complexity_interaction | declared skill level × declared complexity level | ordinal product, not a physical scale |
| opening_wip_share | opening WIP / Q | pieces / pieces |
| planned_downtime_fraction | D / 480 | minutes / nominal shift minutes |
| load_at_{stage}, five columns in declared stage order | planned_load_ratio × indicator(stage) | standard worker-minutes / planned worker-minutes |

Use half the mean development-world MAE and half benchmark MAE. Candidate research
designation requires ≥5% macro gain versus Grouped Mean, ≥2% versus the strongest
raw tree, improvement in every world, ≥2/3 temporal wins/world, ≤5% stage/P95-positive
regression and ≤10% worst-error regression against Grouped Mean. Stage/tail guards
apply per world to pooled nonoverlapping OOF observations. A fixed 1% simplicity
preference resolves near ties. Seal/hash this decision before fitting final
training-only models and running any outer diagnostics. Designation can be
RESEARCH_CANDIDATE or NO_RESEARCH_CANDIDATE; **NO_ML_PROMOTION always remains**.

Report every candidate on all ten original validation/scenario sets without
reranking after those results. Stress profiles reuse the corresponding baseline
model after verifying identical training payloads. Refit reference predictions
must match every retained M08B observation within 1e-12. Apply unchanged numerical
M08B stage/tail/stress thresholds as separately labeled spent diagnostics, never a
retroactive promotion decision or an alternative validation selection rule.

## Feature inspection and uncertainty

On each held-out original-training fold, select up to 1000 IDs using only a seeded
ID hash. Inspect raw forest/histogram predictors with three within-date shuffles
per input and coherent demand/capacity block. Both models receive identical
sample IDs/permutations. Report MAE increases, individual repetitions, variability,
changed-row fraction and known physical inconsistency rate. Marginal stock/time
shuffles can break accounting identities; these sensitivities are not feasible
production interventions. Joint demand/capacity shuffles preserve those tested
identities but do not prove joint entity/process support.

Weekday is constant within date and therefore unidentifiable by this blocked
permutation. Do not infer irrelevance from zero change. Compare training-fold
forest impurity importance and the existing receipt-verified M08C full-benchmark
forest importance (metadata/bytes only, no model loading). High-cardinality and
correlated predictors can distort importance. The method follows the
[scikit-learn permutation-importance guidance](https://scikit-learn.org/stable/modules/permutation_importance.html)
and its [correlated-feature example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html).
Importance is model/data-specific predictive behavior, not intrinsic or causal value.

Retrain both raw trees on the same folds while excluding three declared blocks:
clock (shift/weekday), planned downtime, WIP/release split. Exclude columns from
the fitted transformer, preserving rows and all remaining inputs. These ablations
are not selectable candidates. Clock jointly removes shift and weekday and cannot
attribute its result to either alone. Redundant-feature removal is different from
an impossible marginal perturbation; interpret both together.

Fit joint support counts on training stage×shift×staffing×planned-load cells;
flag counts < 20, load outside the training range and declared high load > 1.5.
Report errors, bias and positive tails for flagged/unflagged contexts, including
empty slices. Such feature-only flags cannot identify hidden shift when inputs
are unchanged. Derive descriptive stage/load P90 residual radii from the new
training OOF errors, support minimum 30, falling back to stage/global radii. Compare
coverage/width to stage-only radii on spent diagnostics. Selection reuses those
folds; intervals are uncalibrated and have no coverage guarantee. Do not label
them confidence intervals or serve them through M08C.

## Reproduction and artifacts

Retain the existing locked environment and M08A/M08B/M08C source artifacts. From
the repository root:

```powershell
.venv/Scripts/python.exe -m loometric.ml_research run --output data/processed/ml_research/exp-008-a
.venv/Scripts/python.exe -m loometric.ml_research run --output data/processed/ml_research/exp-008-b
```

Outputs are create-only inside the ignored research root, distinct from serving
and historical experiment roots. Publish reports, historical diagnosis,
permutation/ablation evidence, matched OOF/spent predictions, fit provenance,
environment/config/code hashes and a benchmark-training-only research model.
If no candidate qualifies, its artifact is explicitly an **unselected lowest-OOF-
MAE candidate**, not an approved replacement. Save timing/lifetime-memory logs
separately from deterministic identities. The manifest is written last.

```powershell
.venv/Scripts/python.exe -m loometric.ml_research inspect --artifact data/processed/ml_research/exp-008-a --expected-fingerprint d2fe121d592a5934753c555815a255620d0010838dc90957af5e3e73319a9cdb
```

Inspection verifies a closed, size-limited file set, environment, configuration,
sealed selection and exact research-code bytes without unpickling. There is no
prediction/serve/generate command. Actual two-run reproduction and all receipts
must be reported; do not claim reproducibility from synthetic fixtures alone.

## Executed result and verification

Both actual EXP-008 runs completed 252 estimator fits and reproduced all eight
deterministic output files byte-for-byte. `rf_physics` is the RESEARCH_CANDIDATE,
with training OOF macro MAE 0.062226692 versus strongest raw reference 0.098562873.
The decision was sealed before spent diagnostics. Its spent benchmark MAE 0.057931365
improves on raw forest 0.076277437, but cutting/disruption and worst-error numerical
guards still fail. Conditional residual bands collapse to about 40% coverage under
hidden shift. NO_ML_PROMOTION and the served models remain unchanged.

Full verification passed **1,230 Python tests**, **162 frontend tests**, **12 real
backend browser workflows**, root/frontend lint/format/type/build, dependency
consistency and zero npm audit findings. No dependencies were added. The preservation
audit confirms 753/754 initial files unchanged with README the only expected existing
edit; original data/experiments/serving/planning stay intact. Detailed findings,
failure limits, timings, receipts and test evidence are in EXP-008.

M09A delivers research evidence and a [v2 design proposal](synthetic-ml-v2-proposal.md).
No dataset replacement, automatic training/promotion, deployment,
real-factory accuracy claim, capacity conversion or scheduling integration.
