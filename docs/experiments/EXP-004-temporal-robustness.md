# EXP-004: Temporal robustness and expanding-window evaluation

Status: executed twice using only the original training partition. The frozen forest wins 2 of 4 windows and loses 2; pooled MAE is 0.7829% higher than the department mean. The EXP-003 validation advantage is not temporally consistent in this audit. Original validation and final-test performance are not evaluated here.

## Objective, hypothesis, and interpretation boundary

Audit whether EXP-003's already selected shallow B_RF-01 forest maintains its advantage over fixed simple references across earlier chronological windows. All model settings and the fold policy were declared before model execution in ADR 0005 and task commentary. No hyperparameter, feature, fold, or seed search is performed and this runner does not select a new model.

This is a retrospective audit, not independent confirmation: B_RF-01 was selected using the original validation labels in EXP-003, and the inner evaluation rows previously served as training data in EXP-001 through EXP-003. No current original validation or test frame enters features, fitting, prediction, diagnostics, or metrics.

Predict `actual_productivity` immediately before a scheduled team/department shift. The tentative `(date, department, team)` row key, shift identity, target units, capture times, and label-finalization latency remain unverified. Real-source measurements support the reported experiment; synthetic records are used only in tests.

## Dataset identity and unchanged outer split

Source: `data/raw/garments_worker_productivity.csv`.

Dataset SHA-256: `763ffcdd39b7f7f360243c2af8f89ed733e8b5f9e511efeb0c886b83e1b76866`.

Frozen split: `configs/chronological_split.json`, SHA-256: `c38de7e418b1d75a0d4e51ceec63344675afd8acc3de34d85e88315bd686a727`.

| Outer partition | Inclusive dates | Dates | Rows | EXP-004 use |
| --- | --- | --- | --- | --- |
| train | 2015-01-01 to 2015-02-10 | 35 | 711 | Inner folds only |
| validation | 2015-02-11 to 2015-02-25 | 12 | 232 | Excluded |
| test | 2015-02-26 to 2015-03-11 | 12 | 254 | Reserved; excluded |

The unchanged loader, normalization, dataset fingerprint verification, complete-date split consumer, policy/count checks, and strict outer chronology are reused. No split is initialized, regenerated, or rewritten. The existing source-wide schema/domain validation still checks the CSV (including inherited WIP/target warnings); it is not test performance evaluation. A01 previously profiled the whole source, so unseen exploratory holdout status is not claimed. Earlier experiment reports remain unchanged.

## Fixed expanding-window protocol

Use the first 15 **observed training dates** as warm-up, evaluate the next five complete observed dates, then expand the prefix by five dates. Evaluation windows are adjacent and disjoint; all 393 rows from the last 20 original training dates are predicted once. The first 318 rows are warm-up only. Missing calendar dates are not invented; five observed dates need not have equal calendar duration. The generic generator includes an explicitly recorded partial final window, although all four real windows are full.

| Fold | Training inclusive | Train dates | Train n | Evaluation inclusive | Evaluation dates | Evaluation n |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | 2015-01-01 to 2015-01-18 | 15 | 318 | 2015-01-19 to 2015-01-24 | 5 | 98 |
| F02 | 2015-01-01 to 2015-01-24 | 20 | 416 | 2015-01-25 to 2015-01-29 | 5 | 102 |
| F03 | 2015-01-01 to 2015-01-29 | 25 | 518 | 2015-01-31 to 2015-02-04 | 5 | 100 |
| F04 | 2015-01-01 to 2015-02-04 | 30 | 618 | 2015-02-05 to 2015-02-10 | 5 | 93 |

Each fold starts with fresh estimators and encoders, fitted only on its earlier prefix. Parameters remain fixed. No fitted vocabulary is reused, no warm-start or within-window update occurs, and no prediction is clipped. Earlier evaluation labels can enter a later prefix only under the assumption that they were finalized before that later cutoff. No embargo is guessed without latency evidence; this assumption needs source-owner confirmation.

## Fixed models and feature availability

| Model | Estimator inputs | Configuration |
| --- | --- | --- |
| global_mean | None | Fold-training global target mean |
| department_mean | department | Fold-training department means; global-training fallback |
| linear_A | department, team | Existing ordinary LinearRegression |
| linear_B | department, team, day_of_week, day_of_month | Existing ordinary LinearRegression |
| forest_B_RF-01 | Same as linear_B | Frozen B_RF-01: 100 trees, max_depth=3, min_samples_leaf=20, random_state=42, n_jobs=1 |

Both linear models and the forest reuse the existing Pipeline with ColumnTransformer, dense full OneHotEncoder (`handle_unknown="ignore"`, `drop=None`, `sparse_output=False`), numeric day-of-month passthrough, and `remainder="drop"`. Team is a categorical string identifier. All learned transformations fit only the fold prefix. OLS parameters remain `fit_intercept=True`, `copy_X=True`, `positive=False`, `n_jobs=None`, `tol=1e-6` in the pinned environment.

The forest retains all EXP-003 settings: squared_error, bootstrap=True, max_features=1.0, min_samples_split=2, max_samples=None, oob_score=False, warm_start=False, ccp_alpha=0, max_leaf_nodes=None, min_impurity_decrease=0, min_weight_fraction_leaf=0, monotonic_cst=None, verbose=0. Fits/predictions are sequential; seed 42 is fixed for each fresh forest. Bootstrap resamples only the fold prefix. No new dependencies or model artifacts are versioned.

| Input / outcome | Eligibility and assumption | Evidence still needed |
| --- | --- | --- |
| Scheduled date -> weekday/day of month | Provisional; deterministic calendar derivation from the scheduled local date | Verify that recorded date identifies the scheduled shift and was available before start |
| department | Provisional scheduled assignment at cutoff; existing normalization | Versioned pre-shift assignment snapshot and source capture time |
| team | Provisional scheduled categorical identity at cutoff | Stable ID semantics and pre-shift roster/assignment snapshot |
| Historical actual_productivity | Training label only, never an input feature | Outcome finalization before the next fold's first predicted shift |
| targeted_productivity, smv, wip, no_of_workers, no_of_style_change | Conditional; excluded | Frozen planning definitions and pre-shift capture/revision timestamps |
| over_time, incentive, idle_time, idle_men | Realized shift fields; excluded | Separately identified planned fields would require a new evidence-backed contract |
| Source day / quarter / raw date | Excluded as direct model inputs | Quarter semantics remain unverified; calendar is derived instead |

No feature has been promoted from provisional to verified. Missing eligible inputs fail; there is no imputation, target-derived feature, relabeling of realized values, or row dropping. Training vocabularies and unknown counts are recorded per fold; real evaluation has zero unknown categories for every fitted encoder. Synthetic tests exercise the unknown-category zero encoding, which does not establish real unseen-team validity.

## Complete per-fold model results

MAE/RMSE/bias use productivity-ratio units; R² is dimensionless. Bias is prediction minus actual. All models score the identical rows within a fold. Signed MAE change is candidate minus that fold's **department mean**, and relative change divides by its unrounded MAE. Negative means improvement. Training MAE is diagnostic only.

| Fold | Model | Train MAE | Evaluation MAE | RMSE | R² | Bias | MAE change | Relative change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | global_mean | 0.112837630 | 0.128936838 | 0.171694614 | -0.071542955 | +0.044364472 | -0.000495018 | -0.3825% |
| F01 | department_mean | 0.113734129 | 0.129431856 | 0.171673099 | -0.071274419 | +0.043193456 | +0.000000000 | +0.0000% |
| F01 | linear_A | 0.097037806 | 0.148463471 | 0.190166764 | -0.314514780 | +0.040825793 | +0.019031615 | +14.7040% |
| F01 | linear_B | 0.095705100 | 0.149969284 | 0.185195517 | -0.246686274 | -0.001101056 | +0.020537428 | +15.8674% |
| F01 | forest_B_RF-01 | 0.106097660 | 0.133959397 | 0.167051595 | -0.014372559 | +0.004299211 | +0.004527541 | +3.4980% |
| F02 | global_mean | 0.118922580 | 0.148410667 | 0.182077693 | -0.018649026 | -0.024636133 | +0.002127245 | +1.4542% |
| F02 | department_mean | 0.119945372 | 0.146283422 | 0.179668253 | 0.008132225 | -0.024288181 | +0.000000000 | +0.0000% |
| F02 | linear_A | 0.110001520 | 0.133595005 | 0.166780228 | 0.145326547 | -0.021753372 | -0.012688417 | -8.6739% |
| F02 | linear_B | 0.107160430 | 0.158208474 | 0.184301484 | -0.043683349 | -0.080829346 | +0.011925052 | +8.1520% |
| F02 | forest_B_RF-01 | 0.110627409 | 0.158533498 | 0.186630164 | -0.070224199 | -0.064187011 | +0.012250076 | +8.3742% |
| F03 | global_mean | 0.123335626 | 0.172729227 | 0.206650449 | -0.028912461 | -0.034640940 | +0.002669187 | +1.5696% |
| F03 | department_mean | 0.124113492 | 0.170060041 | 0.204000365 | -0.002692146 | -0.035397544 | +0.000000000 | +0.0000% |
| F03 | linear_A | 0.111033346 | 0.155612687 | 0.191668366 | 0.114870928 | -0.031228005 | -0.014447354 | -8.4954% |
| F03 | linear_B | 0.111186608 | 0.155940185 | 0.194430540 | 0.089175536 | -0.021286185 | -0.014119856 | -8.3029% |
| F03 | forest_B_RF-01 | 0.114296211 | 0.163874294 | 0.200781174 | 0.028703779 | -0.022891391 | -0.006185747 | -3.6374% |
| F04 | global_mean | 0.130251896 | 0.142868557 | 0.180770118 | -0.003834496 | -0.011172484 | +0.000210486 | +0.1475% |
| F04 | department_mean | 0.130136172 | 0.142658071 | 0.178389688 | 0.022428968 | -0.014339422 | +0.000000000 | +0.0000% |
| F04 | linear_A | 0.116741117 | 0.125702037 | 0.158154983 | 0.231622586 | -0.010776530 | -0.016956034 | -11.8858% |
| F04 | linear_B | 0.116613565 | 0.125190269 | 0.159080923 | 0.222599105 | -0.005194426 | -0.017467803 | -12.2445% |
| F04 | forest_B_RF-01 | 0.120495201 | 0.135975128 | 0.171363946 | 0.097914418 | -0.008120379 | -0.006682943 | -4.6846% |

## Pooled out-of-fold comparison and temporal variation

Pooled metrics are recalculated from all 393 disjoint evaluation predictions, preserving row alignment. Pooled MAE is row weighted; equal-fold mean MAE gives each window equal weight. Fold RMSE/R² are not averaged to obtain pooled values. Training rows overlap across folds, so no pooled training score is represented as independent evidence.

| Model | Pooled MAE | Pooled RMSE | Pooled R² | Pooled bias | MAE change vs department | Relative change |
| --- | --- | --- | --- | --- | --- | --- |
| global_mean | 0.148431035 | 0.185888682 | -0.005911241 | -0.006789573 | +0.001157662 | +0.7861% |
| department_mean | 0.147273373 | 0.183976395 | 0.014678476 | -0.007933222 | +0.000000000 | +0.0000% |
| linear_A | 0.141037325 | 0.177493819 | 0.082892533 | -0.005961664 | -0.006236048 | -4.2343% |
| linear_B | 0.147763276 | 0.181593395 | 0.040038406 | -0.027898720 | +0.000489903 | +0.3326% |
| forest_B_RF-01 | 0.148426346 | 0.182224476 | 0.033354617 | -0.023333554 | +0.001152973 | +0.7829% |

| Model | Equal-fold mean MAE | Fold MAE std (ddof=0) | Minimum fold MAE | Maximum fold MAE |
| --- | --- | --- | --- | --- |
| global_mean | 0.148236322 | 0.015820997 | 0.128936838 | 0.172729227 |
| department_mean | 0.147108347 | 0.014660526 | 0.129431856 | 0.170060041 |
| linear_A | 0.140843300 | 0.011810985 | 0.125702037 | 0.155612687 |
| linear_B | 0.147327053 | 0.013130213 | 0.125190269 | 0.158208474 |
| forest_B_RF-01 | 0.148085579 | 0.013272665 | 0.133959397 | 0.163874294 |

The frozen forest loses F01/F02 and wins F03/F04: **2 wins, 2 losses, 0 ties**. A difference within absolute 1e-12 is a tie. Its pooled MAE is **0.148426346**, versus the department mean's **0.147273373**: **+0.001152973 (+0.7829%)**. Its pooled RMSE is slightly lower than the department mean, but MAE remains the declared primary comparison. Equal-fold mean MAE leads to the same qualitative conclusion. Forest fold MAE ranges from 0.133959397 to 0.163874294; outcomes do not support a consistent advantage.

OLS A has the lowest pooled MAE in this fixed audit and improves on the department mean in F02/F03/F04, while losing F01. This differs from EXP-002's original validation ranking; it is not a new model selection or proof of universal superiority. Preserve EXP-003's measured original-validation result (forest MAE 0.140201317, department mean 0.143226295, a 2.1120% decrease). Those later records and training histories differ from this audit, so their absolute scores are not directly interchangeable.

## Department-level findings

Evaluation finishing/sewing counts are F01 39/59, F02 45/57, F03 41/59, F04 33/60. Pooled counts are 158 finishing and 235 sewing.

| Fold | Model | Finishing MAE | Sewing MAE |
| --- | --- | --- | --- |
| F01 | global_mean | 0.184069176 | 0.092493428 |
| F01 | department_mean | 0.186137095 | 0.091948732 |
| F01 | linear_A | 0.203702026 | 0.111949850 |
| F01 | linear_B | 0.198568103 | 0.117844640 |
| F01 | forest_B_RF-01 | 0.184073834 | 0.100832904 |
| F02 | global_mean | 0.165575977 | 0.134859106 |
| F02 | department_mean | 0.158016180 | 0.137020719 |
| F02 | linear_A | 0.152298652 | 0.118828968 |
| F02 | linear_B | 0.181132481 | 0.140110575 |
| F02 | forest_B_RF-01 | 0.184319329 | 0.138176263 |
| F03 | global_mean | 0.188202103 | 0.161976890 |
| F03 | department_mean | 0.178249775 | 0.164368870 |
| F03 | linear_A | 0.175402587 | 0.141860383 |
| F03 | linear_B | 0.176746454 | 0.141481591 |
| F03 | forest_B_RF-01 | 0.179161137 | 0.153251233 |
| F04 | global_mean | 0.145375452 | 0.141489765 |
| F04 | department_mean | 0.136697439 | 0.145936419 |
| F04 | linear_A | 0.127143842 | 0.124909044 |
| F04 | linear_B | 0.129565163 | 0.122784077 |
| F04 | forest_B_RF-01 | 0.132918726 | 0.137656150 |

| Model | Pooled finishing MAE | Pooled sewing MAE |
| --- | --- | --- |
| global_mean | 0.171792994 | 0.132723845 |
| department_mean | 0.165755260 | 0.134847254 |
| linear_A | 0.165728299 | 0.124436585 |
| linear_B | 0.173527675 | 0.130440830 |
| forest_B_RF-01 | 0.172184645 | 0.132452681 |

The forest has 2 wins / 2 losses / 0 ties in **each** department, but on different windows. Finishing improves in F01/F04 and worsens in F02/F03; sewing improves in F03/F04 and worsens in F01/F02. Pooled finishing forest MAE (0.172184645) is worse than the department mean (0.165755260); pooled sewing (0.132452681) is better than that reference (0.134847254). The net effect is a small aggregate MAE regression. Finishing is harder in the first three windows, but sewing has higher forest error in F04. Slice difficulty and benefits are not temporally uniform.

## Diagnostic context and runtime

| Fold | Training target mean | Evaluation target mean | Forest train MAE | Forest eval-minus-train MAE | Forest bias |
| --- | --- | --- | --- | --- | --- |
| F01 | 0.756403301 | 0.712038829 | 0.106097660 | 0.027861737 | +0.004299211 |
| F02 | 0.745952055 | 0.770588188 | 0.110627409 | 0.047906089 | -0.064187011 |
| F03 | 0.750803186 | 0.785444126 | 0.114296211 | 0.049578083 | -0.022891391 |
| F04 | 0.756408516 | 0.767580999 | 0.120495201 | 0.015479927 | -0.008120379 |

Training size increases while the evaluated period changes. Target means also change; these are descriptive observations, not evidence of a specific causal drift mechanism. F01/F02 calendar days extend beyond the prefix's day-of-month range, and F03 crosses the month boundary; that changes calendar support. No feature representation was revised in response. The forest's largest gap occurs in F03, yet it beats the baseline there, so gap size alone does not explain the ranking. Bias changes sign across periods; pooled bias can conceal opposite errors and does not establish calibrated predictions.

| Fold | Forest residual P05 | Forest residual median | Forest residual P95 | Prediction min | Prediction max | Below 0 / above 1 / outside prefix target range |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | -0.225091926 | -0.045113075 | 0.337832449 | 0.683267523 | 0.758945884 | 0 / 0 / 0 |
| F02 | -0.292653827 | -0.092840595 | 0.291792805 | 0.663095902 | 0.717821815 | 0 / 0 / 0 |
| F03 | -0.231528169 | -0.066461846 | 0.427981209 | 0.629119393 | 0.798576247 | 0 / 0 / 0 |
| F04 | -0.226624846 | -0.038433850 | 0.374460584 | 0.649467737 | 0.805352646 | 0 / 0 / 0 |

No forest prediction lies below zero or above one, and no prediction is clipped. One is only a diagnostic reference: source values above one may be legitimate and remain unmodified. The JSON retains residual quantiles/bins/ranges and training/evaluation metrics for every model, without using outer holdout outcomes.

| Fold | Model | Fit seconds | Training prediction seconds | Evaluation prediction seconds |
| --- | --- | --- | --- | --- |
| F01 | global_mean | 0.000077 | 0.000049 | 0.000030 |
| F01 | department_mean | 0.002443 | 0.000566 | 0.000647 |
| F01 | linear_A | 0.047601 | 0.001982 | 0.005085 |
| F01 | linear_B | 0.004882 | 0.005656 | 0.003439 |
| F01 | forest_B_RF-01 | 0.081033 | 0.006934 | 0.006586 |
| F02 | global_mean | 0.000084 | 0.000052 | 0.000121 |
| F02 | department_mean | 0.000602 | 0.000452 | 0.000391 |
| F02 | linear_A | 0.003801 | 0.001851 | 0.002064 |
| F02 | linear_B | 0.005655 | 0.003071 | 0.002500 |
| F02 | forest_B_RF-01 | 0.078410 | 0.008561 | 0.006496 |
| F03 | global_mean | 0.000118 | 0.000066 | 0.000030 |
| F03 | department_mean | 0.000710 | 0.000473 | 0.000301 |
| F03 | linear_A | 0.003661 | 0.002118 | 0.002080 |
| F03 | linear_B | 0.004349 | 0.002812 | 0.002143 |
| F03 | forest_B_RF-01 | 0.067407 | 0.006839 | 0.005906 |
| F04 | global_mean | 0.000090 | 0.000047 | 0.000027 |
| F04 | department_mean | 0.000662 | 0.000407 | 0.000300 |
| F04 | linear_A | 0.003333 | 0.002169 | 0.001760 |
| F04 | linear_B | 0.005097 | 0.002549 | 0.009949 |
| F04 | forest_B_RF-01 | 0.097902 | 0.013285 | 0.014922 |

Measured full run: **0.715067 seconds**, including load, source validation, split checks, fold features, fitting/prediction, and scoring/aggregation. JSON construction/writing and interpreter imports are excluded. Per-model fit includes pipeline construction and learned preprocessing; feature construction/metric diagnostics are outside those timers. Prediction timers cover the relevant full batch. These are single local wall-clock measurements and vary.

## Reproduction, environment, and actual verification

No dependency was installed or upgraded. Reuse `requirements/exp-002.txt`, including the EXP-001 exact pins. Recorded environment: Windows 11; Python 3.13.14, pandas 3.1.1, numpy 2.5.5, scikit-learn 1.9.1, scipy 1.18.1, joblib 1.6.0, threadpoolctl 3.8.0; pytest 9.2.0 and Ruff 0.17.5. This is not a cross-platform wheel/hash lock.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/exp-002.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.experiments.temporal
.\.venv\Scripts\python.exe -m loometric.experiments.temporal --output .tmp/exp-004-reproduction.json
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
```

Run from the repository root with the existing CSV and split. The default output is ignored `data/processed/exp-004-temporal-robustness.json`; it includes original-training-only out-of-fold row IDs/dates/departments/actuals/predictions, folds, exact model parameters, metrics, comparisons, environment, fingerprints, and runtime. The reviewed Markdown is preserved on reruns. There are no fold-search, model-tuning, original-validation-scoring, or final-test-evaluation CLI options. Do not regenerate the split.

- Full pytest: **241 passed in 22.25 seconds** (210 previous + 31 new cases), with normal local filesystem access using the established permission for pytest temp/cache paths. Warnings remain errors. No pytest failure occurred in this task.
- Initial Ruff import/line-length findings were corrected by import fixes/formatting; lint and formatting checks subsequently passed.
- Two real-data runs exited 0. All non-runtime JSON fields, including every individual prediction, match exactly after excluding keys ending in `_seconds`.
- Final Ruff lint and formatting checks passed. `pip check` passed, and all 18
  exact dependency pins match the installed environment.
- All eight protected dataset/split/earlier-report/profile/rule fingerprints are
  unchanged. The original split SHA-256 remains the recorded value above.
- All five pooled metric sets independently match scikit-learn calculations from
  the saved 393 original-training-only predictions. All 65 main per-fold, pooled,
  department, and runtime table rows match the measured JSON.
- `git diff --check` passed; the index is empty. AGENTS.md and the local commit
  plan remain ignored and untracked. No Git history or timestamps were changed.

Tests cover complete date groups, strict chronology, expanding prefix inclusion, nonoverlapping evaluation, partial tails, invalid policy/date/partition inputs, reproducible folds, fresh train-only pipelines, unknown future categories, later-label isolation, outer-holdout poisoning, fixed model settings, deterministic predictions, win/loss ties, pooled metric agreement with scikit-learn, unequal-window weighting, and CLI input/fingerprint preservation. They use synthetic records and do not require the private CSV. No static type checker was run.

## Conclusions, limitations, and gradient boosting decision

[ADR 0005](../decisions/0005-training-only-temporal-robustness.md) records the methodological decision. Existing shared features, preprocessing, baseline/OLS/forest constructors, and metrics are reused; earlier experiment modules are unchanged. No generic cross-validation framework, new dependency, infrastructure, or service layer is introduced.

The forest's modest original-validation gain is **not temporally stable** in this four-window audit. It wins half the windows, regresses in pooled MAE, and has mixed department outcomes. The simpler OLS A has better pooled MAE here, while original-validation rankings differ. This supports caution about selecting by a single short period, not automatic promotion of a different model from retrospective results.

Four overlapping training prefixes, 20 evaluated historical dates, recurring teams, one seed, unverified feature/label timing, and earlier whole-source EDA limit inference. The audit does not isolate training-size, calendar, and distribution effects. Fold standard deviation and win counts are descriptive; they are not confidence intervals, independent trials, or evidence of statistical significance. No operational, seasonal, unseen-team/factory, or final-test performance claim is supported.

**Proceeding directly to gradient boosting is not scientifically justified as an evidence-backed complexity increase.** The present bottleneck is inconsistent temporal benefit plus uncertain information availability, not a demonstrated lack of estimator capacity. Prioritize a prediction-time evidence/label-latency review and a documented temporal error analysis. A later separately authorized, tightly bounded boosting hypothesis could still be studied, but it must not be presented as an expected improvement or reuse this audit as independent model-selection evidence. No boosting, outer holdout evaluation, backend, frontend, or optimization work was started.
