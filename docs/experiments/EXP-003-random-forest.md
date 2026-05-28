# EXP-003: Random Forest Regression

Status: executed on training and validation only. The best predefined forest reduces
validation MAE by **2.1120%** against the department-mean baseline. This is a modest
development-period improvement; final test performance remains uncalculated.

## Objective and hypothesis

Evaluate whether nonlinear interactions among the existing provisional pre-shift
inputs improve on the EXP-001 department mean and EXP-002 Linear Regression.
Hypothesis: a constrained forest may capture useful identity/calendar interactions,
while increased capacity may overfit this small chronological dataset. No superiority
was assumed, and no model configurations were revised after observing these results.

The target remains `actual_productivity`, predicted immediately before a scheduled
shift for a team in a department. `(date, department, team)` is a tentative row key:
shift IDs, capture timestamps, target units, and label-finalization times are absent.
Training labels must have been finalized before validation starts. This evaluates
the real-source dataset; synthetic records are used only in tests.

## Dataset identity and frozen evaluation protocol

Source: `data/raw/garments_worker_productivity.csv`.

Dataset SHA-256:
`763ffcdd39b7f7f360243c2af8f89ed733e8b5f9e511efeb0c886b83e1b76866`.

Frozen configuration: `configs/chronological_split.json`, SHA-256:
`c38de7e418b1d75a0d4e51ceec63344675afd8acc3de34d85e88315bd686a727`.

| Partition | Inclusive dates | Distinct dates | Observations | Use |
| --- | --- | --- | --- | --- |
| Training | 2015-01-01 to 2015-02-10 | 35 | 711 | Fit preprocessing/models; diagnose training error |
| Validation | 2015-02-11 to 2015-02-25 | 12 | 232 | Fixed comparison, selection, and diagnostics |
| Final test | 2015-02-26 to 2015-03-11 | 12 | 254 | Reserved; no features, fitting, prediction, selection, or metrics |

The existing loader, department normalization, fingerprint verification, complete-date
split consumer, ordering, and count checks are reused unchanged. No date boundaries
are rewritten or regenerated. There is no random train/test split. Forest bootstrap
sampling occurs within training only. Every validation record has equal metric weight;
none is dropped, imputed, clipped, or relabeled.

Existing whole-source schema/domain validation still runs before partitioning. Its
warnings include 506 missing WIP values and 37 targets above 1. These are inherited
source checks, not final-test performance or feature selection. A01 already profiled
all source targets; the final test is reserved from fitting/performance evaluation,
not claimed unseen in earlier EDA. EXP-001/EXP-002 report files are preserved.

## Exact feature sets and availability assumptions

| Feature | Representation | Provisional pre-shift assumption |
| --- | --- | --- |
| department | Training-learned one-hot category | Scheduled department fixed before shift starts; existing normalization retained. |
| team | Training-learned one-hot category | Scheduled identity fixed before shift; canonical whole-number strings, never continuous magnitudes. |
| day_of_week | Scheduled-date-derived one-hot category, Monday=0 | Scheduled local date known at cutoff; source `day` is not consumed. |
| day_of_month | Scheduled-date-derived numeric day, 1..31 | Same known date, without target information or historical aggregates. |

All timing eligibility remains provisional because source measurement timestamps are
unavailable. No additional features are admitted. `over_time`, `incentive`, `idle_time`,
`idle_men`, labels, source `quarter`/`day`, and unverified `targeted_productivity`,
`smv`, `wip`, `no_of_workers`, and `no_of_style_change` remain excluded. Planned
values are not inferred from realized values. Raw date only derives calendar values
and verifies partitions; it is not passed directly to the estimator.

| Feature configuration | Exact estimator inputs | Encoded columns |
| --- | --- | --- |
| A | department, team | 14 |
| B | department, team, day_of_week, day_of_month | 21 |

Reuse the existing stateless `build_features` boundary. Both OLS and forest now call
the same extracted `build_preprocessor`: ColumnTransformer with dense
`OneHotEncoder(handle_unknown="ignore", drop=None, sparse_output=False)`, numeric
passthrough, and `remainder="drop"`. The encoder and regressor are encapsulated in
a Pipeline fitted only on training rows. Missing eligible inputs fail explicitly.
There is no scaling, imputation, target transformation, or prediction clipping.

Training contains 2 department categories, team IDs 1..12, and weekdays 0,1,2,3,5,6.
There are no unknown categorical values in real validation. Unknown categories encode
as zeros for their feature; synthetic tests verify finite predictions without
refitting, but real unseen-team generalization is not established.

## Predefined forest comparison and selection

The following profiles were fixed in code, ADR 0004, and the task commentary before
real-data execution, crossed with A and B for exactly six forest candidates:

| Profile | n_estimators | max_depth | min_samples_leaf | Reason |
| --- | --- | --- | --- | --- |
| RF-01 | 100 | 3 | 20 | Strong smoothing and shallow interactions for 711 rows |
| RF-02 | 200 | 6 | 10 | Moderate capacity and more ensemble averaging |
| RF-03 | 300 | None | 2 | Flexible comparison to expose possible overfitting |

Common parameters: `random_state=42`, `n_jobs=1`, `criterion="squared_error"`,
`max_features=1.0`, `bootstrap=True`, `min_samples_split=2`, `max_samples=None`,
`oob_score=False`, `warm_start=False`. Remaining installed defaults:
`ccp_alpha=0.0`, `max_leaf_nodes=None`, `min_impurity_decrease=0.0`,
`min_weight_fraction_leaf=0.0`, `monotonic_cst=None`, `verbose=0`.
Fits and predictions execute sequentially. No OOB score or extensive search is used.
Bundled profiles do not isolate the effect of individual hyperparameters.

Selection uses validation MAE only. Ties within absolute 1e-12 resolve in declared
order A_RF-01, A_RF-02, A_RF-03, B_RF-01, B_RF-02, B_RF-03. If no forest lowers the
department baseline's MAE by more than 1e-12, retain that baseline. Training MAE is
in-sample diagnostic evidence only; it does not select a candidate. Department
slices, importance, RMSE, bias, and runtime also do not alter this criterion.

Both EXP-001 baselines and the matching EXP-002 A/B linear models are refitted on
the same training rows and scored on identical validation rows. Their numerical
results reproduce the earlier experiments. The best EXP-002 model, department-only
OLS, is already equivalent to the department mean.

## Complete measured model comparison

All validation errors use the same 232 observations. MAE, RMSE, and bias are in
productivity-ratio units. Bias/residual = prediction minus actual. R² is dimensionless;
negative R² means worse squared error than the validation-mean denominator reference.
That denominator reference is not a fitted deployable predictor.

| Candidate | Training MAE | Validation MAE | Validation RMSE | Validation R² | Validation bias | MAE change vs department | Relative change |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A_RF-01 | 0.121004635 | 0.141104424 | 0.196552259 | -0.094865055 | +0.059330404 | -0.002121870 | -1.4815% |
| A_RF-02 | 0.115796941 | 0.148646671 | 0.201696077 | -0.152920655 | +0.057644012 | +0.005420376 | +3.7845% |
| A_RF-03 | 0.114894146 | 0.155143313 | 0.207022002 | -0.214611882 | +0.056298567 | +0.011917018 | +8.3204% |
| **B_RF-01** | **0.120574554** | **0.140201317** | **0.195062509** | **-0.078331093** | **+0.055805734** | **-0.003024977** | **-2.1120%** |
| B_RF-02 | 0.110770652 | 0.144017573 | 0.193627756 | -0.062526425 | +0.042551728 | +0.000791278 | +0.5525% |
| B_RF-03 | 0.067919069 | 0.159350747 | 0.203474155 | -0.173337688 | +0.029722837 | +0.016124453 | +11.2580% |

Signed change = candidate MAE minus department-mean MAE; relative change = 100 times
that difference divided by the unrounded department-mean MAE. Negative is improvement.

| Reproduced reference | Training MAE | Validation MAE | RMSE | R² | Bias |
| --- | --- | --- | --- | --- | --- |
| EXP-001 global mean | 0.131641143 | 0.144606972 | 0.197475686 | -0.105176844 | +0.060919708 |
| EXP-001 department mean / best EXP-002 OLS | 0.131342115 | 0.143226295 | 0.196492435 | -0.094198670 | +0.060338141 |
| EXP-002 OLS A | 0.117424844 | 0.150379924 | 0.203566618 | -0.174404317 | +0.059444997 |
| EXP-002 OLS B | 0.117129946 | 0.150551578 | 0.202288571 | -0.159704139 | +0.052828789 |

Training errors in this reference table are newly computed diagnostics, not claims
that EXP-001/EXP-002 previously reported them. Baseline means still use training only.

**Best predefined forest and preferred development candidate: B_RF-01**, using
department, team, weekday, day of month; 100 trees, max_depth=3, min_samples_leaf=20,
seed 42, one worker. The result does not authorize a final-test run or deployment.

| Reference | B_RF-01 absolute MAE change | Relative change |
| --- | --- | --- |
| Global mean | -0.004405654 | -3.0466% |
| Department mean / best EXP-002 OLS | -0.003024977 | -2.1120% |
| Matching OLS A | -0.010178607 | -6.7686% |
| Matching OLS B | -0.010350261 | -6.8749% |

Only the two shallow profiles improve on the department mean. All deeper profiles
regress in validation MAE; B_RF-02 has the lowest RMSE but fails the declared MAE
criterion. Every R² remains negative. These are measured differences on one
development period, not a statistical-significance or production-readiness claim.

### Calendar addition at each fixed profile

| Profile | B minus A validation MAE | Relative to A |
| --- | --- | --- |
| RF-01 | -0.000903107 | -0.6400% |
| RF-02 | -0.004629098 | -3.1142% |
| RF-03 | +0.004207434 | +2.7120% |

Calendar helps the shallow/moderate forests relative to their A counterparts but
worsens the flexible forest. This does not establish universal calendar usefulness,
an isolated weekday effect, or an isolated day-of-month effect.

### Department-level validation MAE

Finishing has 297 training / 94 validation rows; sewing has 414 / 138.

| Model | Finishing MAE | Sewing MAE |
| --- | --- | --- |
| Global mean | 0.166818469 | 0.129477401 |
| Department mean / best OLS | 0.169320624 | 0.125451896 |
| OLS A | 0.171561932 | 0.135951600 |
| OLS B | 0.170533311 | 0.136940833 |
| A_RF-01 | 0.166195361 | 0.124013496 |
| A_RF-02 | 0.171271586 | 0.133235497 |
| A_RF-03 | 0.177705664 | 0.139774755 |
| B_RF-01 | 0.165290002 | 0.123111924 |
| B_RF-02 | 0.167405041 | 0.128086979 |
| B_RF-03 | 0.181767367 | 0.144081455 |

The selected forest improves both departments against both mean references and
matching OLS models. Finishing remains the higher-error department. B_RF-02 improves
finishing against the department mean but worsens sewing; aggregate MAE rises.
B_RF-03 worsens both departments substantially.

## Fit diagnostics and overfitting assessment

| Candidate | Validation minus training MAE |
| --- | --- |
| Department mean | +0.011884179 |
| OLS A | +0.032955080 |
| OLS B | +0.033421633 |
| A_RF-01 | +0.020099789 |
| A_RF-02 | +0.032849730 |
| A_RF-03 | +0.040249167 |
| B_RF-01 | +0.019626764 |
| B_RF-02 | +0.033246921 |
| B_RF-03 | +0.091431678 |

Increasing capacity reduces training MAE while validation MAE worsens within both
feature sets. B_RF-03 is the clearest overfitting indicator: training MAE 0.067919069,
validation MAE 0.159350747, a 0.091431678 gap. Its low training error was not used to
select it. A's identity-only inputs also constrain how many distinct observations
can be separated: repeated department/team combinations share the same predictors.

The shallow winner retains a 0.019626764 gap and nontrivial training error. Strong
smoothing limits fit; these results do not prove additional capacity or features
would fix underfitting. Temporal distribution change, uncertain measurement timing,
and unavailable explanatory inputs can also contribute to train/validation gaps.
The observed capacity pattern supports the constrained candidate among this fixed
comparison, without establishing a unique cause of error.

## Residual distribution and prediction ranges

Residuals use prediction minus actual. Quantiles use linear interpolation; standard
deviations are population values (`ddof=0`). Full P25/P75 are in the local JSON.

| Candidate | Min residual | P05 | Median | P95 | Max residual | Residual std |
| --- | --- | --- | --- | --- | --- | --- |
| A_RF-01 | -0.330232064 | -0.193797541 | +0.009508254 | +0.450321181 | +0.544279011 | 0.187383814 |
| A_RF-02 | -0.285770470 | -0.190659373 | +0.008043452 | +0.465424748 | +0.576987542 | 0.193283407 |
| A_RF-03 | -0.293041252 | -0.182245585 | -0.003164891 | +0.475104691 | +0.598579942 | 0.199219931 |
| B_RF-01 | -0.334323478 | -0.200426033 | +0.005735321 | +0.445088627 | +0.531434743 | 0.186909343 |
| B_RF-02 | -0.332390073 | -0.209506666 | -0.005494728 | +0.432169494 | +0.540321174 | 0.188894305 |
| B_RF-03 | -0.434724677 | -0.241649574 | -0.000340969 | +0.416867726 | +0.590530260 | 0.201291541 |

| Candidate | (-inf,-0.2] | (-0.2,-0.1] | (-0.1,0] | (0,0.1] | (0.1,0.2] | (0.2,inf) |
| --- | --- | --- | --- | --- | --- | --- |
| A_RF-01 | 11 | 25 | 60 | 56 | 34 | 46 |
| A_RF-02 | 11 | 31 | 72 | 38 | 33 | 47 |
| A_RF-03 | 10 | 38 | 69 | 36 | 32 | 47 |
| B_RF-01 | 15 | 22 | 62 | 57 | 31 | 45 |
| B_RF-02 | 15 | 28 | 78 | 39 | 30 | 42 |
| B_RF-03 | 22 | 47 | 47 | 46 | 18 | 52 |

All mean biases remain positive. The selected forest's median residual is +0.0057,
but its P95 is +0.4451, with 45 residuals above +0.2 versus 15 at/below -0.2. Its
residual standard deviation (0.186909343) is close to the department baseline's
0.186998892; the gain does not remove large errors or persistent overprediction.
Lower bias alone does not identify the best MAE model. No normality, independence,
confidence interval, or statistical significance is established.

| Candidate | Minimum prediction | Maximum prediction | Below 0 | Above 1 | Outside training target range |
| --- | --- | --- | --- | --- | --- |
| A_RF-01 | 0.669656340 | 0.823427536 | 0 | 0 | 0 |
| A_RF-02 | 0.649279192 | 0.856418403 | 0 | 0 | 0 |
| A_RF-03 | 0.624894163 | 0.870981884 | 0 | 0 | 0 |
| B_RF-01 | 0.670713284 | 0.819861050 | 0 | 0 | 0 |
| B_RF-02 | 0.602434969 | 0.858664623 | 0 | 0 | 0 |
| B_RF-03 | 0.528944306 | 0.922872876 | 0 | 0 | 0 |

No prediction is clipped. [0,1] is a review
reference, not a proven business range: actual productivity above 1 is retained
pending domain interpretation. Range checks do not certify future plausibility.

## Training impurity importance and its limitations

Group importance sums the fitted forest's importance across each original feature's
one-hot columns, using fitted transformer offsets/category widths. Per-encoded-column
values are retained in JSON. Neither target nor validation outcomes enter importance.

| Candidate | department | team | day_of_week | day_of_month |
| --- | --- | --- | --- | --- |
| A_RF-01 | 0.044282 | 0.955718 | — | — |
| A_RF-02 | 0.142389 | 0.857611 | — | — |
| A_RF-03 | 0.156482 | 0.843518 | — | — |
| B_RF-01 | 0.037551 | 0.876901 | 0.001502 | 0.084046 |
| B_RF-02 | 0.074931 | 0.616891 | 0.011267 | 0.296910 |
| B_RF-03 | 0.103447 | 0.363891 | 0.141275 | 0.391387 |

Team accounts for most training impurity reduction in the selected forest; day of
month receives more weight as capacity grows. These are properties of fitted trees,
not causal effects, stable business drivers, or validated out-of-sample importance.
Team has more indicators than department, day of month offers many split points,
and redundant/correlated indicators can share or redistribute credit. The high
calendar importance of B_RF-03 coexists with its worse validation MAE. Importance
was not used to remove features, tune settings, or override MAE selection. No
permutation-importance experiment or significance test was performed.

## Measured runtime and environment

Single local `perf_counter` wall-clock run; times vary and are not deployment latency
benchmarks. Fit times include pipeline construction/encoding/model fitting. Inference
is full-pipeline validation prediction and Series creation for 232 rows. Training
prediction is measured separately and excluded from both fit and validation inference.

| Candidate | Training seconds | Training inference seconds (711 rows) | Validation inference seconds (232 rows) |
| --- | --- | --- | --- |
| A_RF-01 | 0.062809 | 0.006152 | 0.005249 |
| A_RF-02 | 0.132261 | 0.013914 | 0.009589 |
| A_RF-03 | 0.249842 | 0.033527 | 0.019933 |
| B_RF-01 | 0.118519 | 0.007675 | 0.007142 |
| B_RF-02 | 0.250657 | 0.014203 | 0.011928 |
| B_RF-03 | 0.516685 | 0.030814 | 0.025359 |

Shared train/validation feature construction: **0.004263 seconds**.
Full load/validate/split/features/reference fits/six forests/scoring/diagnostics:
**1.754785 seconds**, excluding JSON construction/writing and interpreter imports.
Diagnostics, importance, metric arithmetic, and I/O are outside per-model timers.

Recorded environment: Windows 11, Python **3.13.14**, pandas **3.1.1**, numpy **2.5.5**,
scikit-learn **1.9.1**, scipy **1.18.1**, joblib **1.6.0**, threadpoolctl **3.8.0**;
pytest **9.2.0**, Ruff **0.17.5**. No dependency is added or upgraded.
Reuse the exact closure in `requirements/exp-002.txt`, including EXP-001 pins.
The snapshot is not a cross-platform wheel/hash lock. Seed 42 and one worker make
the recorded execution repeatable, not evidence of stability across seeds/platforms.

## Reproduction and actual verification

From the repository root with the existing local CSV and frozen split file:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/exp-002.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.experiments.forest
.\.venv\Scripts\python.exe -m loometric.experiments.forest --output .tmp/exp-003-reproduction.json
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
```

The runner writes ignored `data/processed/exp-003-random-forest.json`, preserving
the reviewed Markdown narrative. It records exact profiles/features/parameters,
environment, source/split identity, all scores/comparisons/gaps, unknown-category
counts, residuals, ranges, importance, and measured runtimes. There is no final-test
evaluation option or parameter-search switch. Do not regenerate the split file.

- Full pytest: **210 passed in 10.38 seconds**, with normal local filesystem access
  because this workspace's sandbox blocks pytest temporary/cache paths. This
  includes all 166 earlier tests and 44 new cases. Warnings remain errors.
- Ruff lint and formatting checks passed.
- `pip check` passed; all 18 exact pins in the reused EXP-001/EXP-002 closure
  match installed versions. No package was installed or upgraded for EXP-003.
- Two real EXP-003 runs exited 0; all JSON fields matched exactly after excluding
  fields ending in `_seconds`. No configurations changed between runs.
- EXP-001 rerun reproduced the versioned report except runtime. EXP-002 rerun
  reproduced the earlier local JSON except runtimes after the shared extraction.
- Dataset, split, EXP-001/EXP-002 reports, A01 profile, ignore rules, and AGENTS.md
  fingerprints are unchanged. All 48 forest metric/diagnostic table rows were
  checked against the measured JSON. `git diff --check` passed, the index is empty,
  and AGENTS.md / the local commit plan remain ignored and untracked.

New tests cover exact production profiles, seed/worker settings, feature restrictions,
shared encoding metadata, unknown categories, deterministic full-profile forest
predictions/importance, grouped importance arithmetic, selection/tie/baseline
retention, metric agreement with scikit-learn, fingerprint/split drift, and CLI input
preservation. Synthetic orchestration tests use shortened forests for speed; the
production profile constants are checked separately. Test-data poisoning and an
object with no test-frame attribute verify final-test isolation. All tests run
without the private CSV. A static type checker is not configured or claimed.

## Engineering conclusions and limitations

[ADR 0004](../decisions/0004-bounded-random-forest-comparison.md) records the fixed
comparison, selection rule, shared preprocessing/diagnostics extraction, and importance
policy. EXP-001/EXP-002 APIs and numerical behavior are preserved. No factories,
service/storage layer, external system, model registry, or new dependency is added.
No serialized model is versioned; numerical artifacts remain local and ignored.

B_RF-01 is the preferred candidate within this validation experiment, with a modest
2.1120% MAE decrease and improvement in both departments. Stronger training fit is
not reliable evidence of improved future-shift prediction. More trees/depth and
smaller leaves did not produce a better validation-MAE candidate in the fixed plan.
Training impurity importance cannot explain a causal mechanism for the difference.

Major limits remain: one short validation period, one seed, recurring teams, missing
capture/shift timestamps, uncertain row grain/units, source-wide earlier EDA, and
repeated use of the same validation period across model comparisons. The gain is
not a significance claim; R² remains negative and overprediction persists. No
operational or unseen-factory/team performance is established. Final test data is
strictly reserved from modeling and performance evaluation.

Recommended EXP-004: a predefined temporal-robustness audit of the frozen shallow
forest, department mean, and matching linear references using expanding-window folds
inside the original training partition. Freeze features/parameters, declare folds
and any seed-sensitivity checks before execution, report per-window/department
results, and investigate prediction-time evidence. Avoid another adaptive validation
search, unverified new fields, or final-test evaluation. This is a proposed separate
task; no EXP-004 work is started.
