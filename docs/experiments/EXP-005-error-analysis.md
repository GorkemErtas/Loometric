# EXP-005: Temporal error analysis and prediction readiness

Status: executed twice using validated saved EXP-004 predictions; no models fitted or tuned. Suitable for an explicitly experimental retrospective evidence-review application with human oversight. Live production forecasting readiness is not established.

## Objective and methodology

Explain where department mean, Linear Regression A, and frozen Random Forest B_RF-01 fail on identical historical observations, assess temporal/team instability, and document the evidence needed before forward-looking operational use. This is descriptive error analysis, not another model search, feature selection, uncertainty calibration, or causal study.

Consume the saved EXP-004 artifact rather than regenerating predictions. Existing source validation and frozen split checks still run. After those checks only `.train` is accessed. Verify experiment/split/policy/fold identities, OOF row order, dates, departments, targets, prediction lengths/finite values, fixed model configurations, and reconstructed stored scores before joining team metadata from original training. Missing or inconsistent artifacts fail; no fallback refit is permitted.

Definitions were fixed before execution in [ADR 0006](../decisions/0006-saved-prediction-error-audit.md): residual = prediction minus actual; linear-interpolated error quantiles; high error = absolute error >=0.30; largest ceil(1%, 5%, 10% of n) error concentration; and a common baseline-selected worst-10% sensitivity population. The threshold is a descriptive ratio-unit reference without an established operational decision meaning. Primary metrics retain all rows.

## Dataset, artifact identity, and exact analyzed population

Dataset SHA-256: `763ffcdd39b7f7f360243c2af8f89ed733e8b5f9e511efeb0c886b83e1b76866`.

Frozen `configs/chronological_split.json` SHA-256: `c38de7e418b1d75a0d4e51ceec63344675afd8acc3de34d85e88315bd686a727`.

Input `data/processed/exp-004-temporal-robustness.json` SHA-256: `a65f2643c273dfabb13964a28197bf6ca35b7ed2a97ce64373d8825b05d31843`.

Exactly **393 OOF observations on 20 dates**, 2015-01-19 through 2015-02-10, from the original 711-row training partition. There are 158 finishing and 235 sewing observations, 24 department/team pairs, and four evaluation windows. Original training row IDs 318..710 appear once per model; warm-up rows 0..317 are not newly analyzed. Original validation (232 rows, 2015-02-11..2015-02-25) and final test (254 rows, 2015-02-26..2015-03-11) are excluded from diagnostic exploration, model selection, and performance evaluation.

| Fold | EXP-004 training dates | Train n | Analyzed evaluation dates | Evaluation n |
| --- | --- | --- | --- | --- |
| F01 | 2015-01-01..2015-01-18 | 318 | 2015-01-19..2015-01-24 | 98 |
| F02 | 2015-01-01..2015-01-24 | 416 | 2015-01-25..2015-01-29 | 102 |
| F03 | 2015-01-01..2015-01-29 | 518 | 2015-01-31..2015-02-04 | 100 |
| F04 | 2015-01-01..2015-02-04 | 618 | 2015-02-05..2015-02-10 | 93 |

Existing whole-source schema/domain validation is retained; it is not exploration of held-out error patterns. Earlier A01 EDA already described the whole source. The forest was selected using original validation in EXP-003, and these inner records previously trained earlier models. EXP-004/EXP-005 are retrospective audits, not independent confirmation or untouched holdout evidence. All earlier reports, dataset/split bytes, and input predictions remain unchanged.

Department mean uses fold-training means. Linear A uses department plus categorical team. The forest additionally uses date-derived categorical weekday and numeric day of month, with the existing 100 trees, max_depth=3, min_samples_leaf=20, random_state=42, n_jobs=1 and all other EXP-003 settings. No features or settings change. Team metadata is a grouping identifier here, never a target-derived input. Local worst-observation records are not versioned.

## Measured aggregate errors and distributions

| Model | n | MAE | RMSE | R² | Bias | Errors >=0.30 | Fraction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| department_mean | 393 | 0.147273373 | 0.183976395 | 0.014678476 | -0.007933222 | 34 | 8.6514% |
| linear_A | 393 | 0.141037325 | 0.177493819 | 0.082892533 | -0.005961664 | 35 | 8.9059% |
| forest_B_RF-01 | 393 | 0.148426346 | 0.182224476 | 0.033354617 | -0.023333554 | 33 | 8.3969% |

| Model | Absolute P25 | Absolute median | Absolute P75 | Absolute P90 | Absolute P95 | Absolute P99 | Maximum absolute error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| department_mean | 0.062254717 | 0.134205331 | 0.209840782 | 0.268365584 | 0.378168359 | 0.475341106 | 0.512066734 |
| linear_A | 0.056827590 | 0.124371194 | 0.197423678 | 0.289859086 | 0.339531775 | 0.472455582 | 0.595200866 |
| forest_B_RF-01 | 0.065239962 | 0.129913097 | 0.214714358 | 0.291574663 | 0.352088849 | 0.467322230 | 0.500235749 |

| Model | Signed P05 | Signed median | Signed P95 |
| --- | --- | --- | --- |
| department_mean | -0.262310050 | -0.056800486 | 0.378168359 |
| linear_A | -0.241240045 | -0.042619618 | 0.335655464 |
| forest_B_RF-01 | -0.250621325 | -0.058465131 | 0.352088849 |

Linear A has the lowest aggregate MAE on this fixed population but also the largest maximum absolute error (0.595200866) and 35 errors >=0.30, compared with 34 for department mean and 33 for the forest. A high-error count or maximum alone does not identify the best average predictor. The forest remains slightly worse than department mean in MAE despite its lower RMSE. These metrics reproduce the selected EXP-004 outputs exactly; there is no new performance gain or model-selection claim.

Mean and median residuals are negative in the pooled population. Fewer large positive errors coexist with many moderate negative errors, so pooled bias alone conceals the error shape. Error quantiles are retrospective empirical summaries, not calibrated prediction intervals or guarantees for the next shift.

## Error concentration and high-error observations

| Model | Largest fraction | Rows | Share of absolute error | Share of squared error | Remaining MAE (model-specific diagnostic) |
| --- | --- | --- | --- | --- | --- |
| department_mean | 1.0000% | 4 | 3.4807% | 7.6297% | 0.143608856 |
| department_mean | 5.0000% | 20 | 14.9757% | 28.5457% | 0.131932245 |
| department_mean | 10.0000% | 40 | 26.1315% | 44.3902% | 0.121115951 |
| linear_A | 1.0000% | 4 | 3.7703% | 8.8760% | 0.137115337 |
| linear_A | 5.0000% | 20 | 15.3190% | 29.7148% | 0.125835736 |
| linear_A | 10.0000% | 40 | 26.6027% | 45.5532% | 0.115247624 |
| forest_B_RF-01 | 1.0000% | 4 | 3.4001% | 7.5364% | 0.144853972 |
| forest_B_RF-01 | 5.0000% | 20 | 14.3621% | 27.2753% | 0.133924649 |
| forest_B_RF-01 | 10.0000% | 40 | 25.1534% | 42.5253% | 0.123680348 |

The largest four errors account for 3.4001–3.7703% of total absolute error and 7.5364–8.8760% of squared error. Thus a handful of observations does **not dominate** the aggregate totals. The largest 40 errors account for 25.1534–26.6027% of absolute error and 42.5253–45.5532% of squared error: the broader tail matters, especially for RMSE. Model-specific remaining MAEs above use different excluded sets and must not be compared as though they score identical records.

| Model | Largest-error observations inspected | Finishing / sewing | Overprediction / underprediction | Actual target range among these observations |
| --- | --- | --- | --- | --- |
| department_mean | 10 | 6 / 4 | 10 / 0 | 0.259375000..0.327407407 |
| linear_A | 10 | 6 / 4 | 10 / 0 | 0.260978788..0.350706422 |
| forest_B_RF-01 | 10 | 5 / 5 | 10 / 0 | 0.260978788..0.350706422 |

Each model's ten largest errors are overpredictions on low realized targets. This is a measured tail association; it does not explain why productivity was low or implicate workers, downtime, incentives, staffing, or a process cause. The selected sets differ by model. Exact row IDs, dates, group IDs, targets, and predictions for these cases are available only in ignored local JSON for review, without publishing raw records.

For a common-population sensitivity check, exclude the department baseline's largest 40 absolute-error rows from **all** three models. Primary results remain the full 393. This leaves the same 353 rows for every model:

| Model | Remaining n | MAE | RMSE | Bias |
| --- | --- | --- | --- | --- |
| department_mean | 353 | 0.121115951 | 0.144759328 | -0.045107145 |
| linear_A | 353 | 0.117193035 | 0.142153178 | -0.041004367 |
| forest_B_RF-01 | 353 | 0.124534837 | 0.147390190 | -0.060081836 |

The aggregate ordering persists: Linear A, department mean, forest. Large baseline errors are not the sole reason for this ordering. Exclusion is outcome/error conditioned and favors its selecting baseline; these lower values are not new unbiased forecasting estimates, cleaned-data results, or grounds to drop rows or promote a model.

## Chronological variation and target distributions

| Model | Fold | n | MAE | Bias | Errors >=0.30 |
| --- | --- | --- | --- | --- | --- |
| department_mean | F01 | 98 | 0.129431856 | +0.043193456 | 10 |
| department_mean | F02 | 102 | 0.146283422 | -0.024288181 | 6 |
| department_mean | F03 | 100 | 0.170060041 | -0.035397544 | 10 |
| department_mean | F04 | 93 | 0.142658071 | -0.014339422 | 8 |
| forest_B_RF-01 | F01 | 98 | 0.133959397 | +0.004299211 | 9 |
| forest_B_RF-01 | F02 | 102 | 0.158533498 | -0.064187011 | 6 |
| forest_B_RF-01 | F03 | 100 | 0.163874294 | -0.022891391 | 10 |
| forest_B_RF-01 | F04 | 93 | 0.135975128 | -0.008120379 | 8 |
| linear_A | F01 | 98 | 0.148463471 | +0.040825793 | 13 |
| linear_A | F02 | 102 | 0.133595005 | -0.021753372 | 6 |
| linear_A | F03 | 100 | 0.155612687 | -0.031228005 | 9 |
| linear_A | F04 | 93 | 0.125702037 | -0.010776530 | 7 |

| Fold | n | Target mean | Population std | P05 | Median | P95 |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | 98 | 0.712038829 | 0.165863903 | 0.392481598 | 0.750057359 | 0.959682197 |
| F02 | 102 | 0.770588188 | 0.180403291 | 0.407936226 | 0.800430047 | 1.000108499 |
| F03 | 100 | 0.785444126 | 0.203726319 | 0.348879434 | 0.827152778 | 1.000464711 |
| F04 | 93 | 0.767580999 | 0.180424531 | 0.361405021 | 0.799963218 | 1.000018551 |

All three pooled biases are negative, but their fold biases reverse from positive in F01 to negative in F02–F04. Forest bias moves from +0.004299211 to -0.064187011, -0.022891391, and -0.008120379. Systematic overprediction does not persist uniformly across these periods; the large-error overprediction tail still persists. Target mean rises from 0.712038829 in F01 to 0.785444126 in F03 and then 0.767580999 in F04. These are descriptive distribution changes. Changing training history, dates, calendar support, and team composition are confounded; no causal drift mechanism is established.

| Date | n | Department MAE | Linear A MAE | Forest MAE | Low support (n<20) |
| --- | --- | --- | --- | --- | --- |
| 2015-01-19 | 19 | 0.125101834 | 0.124275191 | 0.129992427 | True |
| 2015-01-20 | 15 | 0.114605026 | 0.129208784 | 0.116428236 | True |
| 2015-01-21 | 19 | 0.121416732 | 0.144541948 | 0.130055888 | True |
| 2015-01-22 | 22 | 0.141191029 | 0.170655297 | 0.132936045 | False |
| 2015-01-24 | 23 | 0.138051786 | 0.163015052 | 0.152873321 | False |
| 2015-01-25 | 21 | 0.138701761 | 0.119908440 | 0.146736700 | False |
| 2015-01-26 | 19 | 0.126532733 | 0.112408665 | 0.143945174 | True |
| 2015-01-27 | 21 | 0.132329585 | 0.125842234 | 0.146669135 | False |
| 2015-01-28 | 21 | 0.185821212 | 0.170557255 | 0.189143457 | False |
| 2015-01-29 | 20 | 0.146144170 | 0.137422968 | 0.165096167 | False |
| 2015-01-31 | 24 | 0.192515518 | 0.175861955 | 0.186723485 | False |
| 2015-02-01 | 19 | 0.163827848 | 0.148151497 | 0.157818176 | True |
| 2015-02-02 | 19 | 0.185212685 | 0.166971371 | 0.176915994 | True |
| 2015-02-03 | 19 | 0.166359392 | 0.152399946 | 0.159110716 | True |
| 2015-02-04 | 19 | 0.136475426 | 0.129349909 | 0.132790153 | True |
| 2015-02-05 | 18 | 0.149329450 | 0.133667981 | 0.146746003 | True |
| 2015-02-07 | 19 | 0.140843294 | 0.124110087 | 0.132728506 | True |
| 2015-02-08 | 19 | 0.144276152 | 0.133412492 | 0.140990420 | True |
| 2015-02-09 | 18 | 0.161648719 | 0.134816900 | 0.150894084 | True |
| 2015-02-10 | 19 | 0.118543374 | 0.103401714 | 0.109868725 | True |

Thirteen of the 20 daily cells have fewer than 20 rows. Daily changes are useful for locating records to inspect, not for reliable day rankings or independent tests. Repeated teams and shared operating dates preclude treating 393 rows as independent trials.

## Department and team findings

| Model | Department | n | MAE | RMSE | Bias | Errors >=0.30 |
| --- | --- | --- | --- | --- | --- | --- |
| department_mean | finishing | 158 | 0.165755260 | 0.197110652 | -0.023984519 | 14 |
| department_mean | sewing | 235 | 0.134847254 | 0.174591097 | +0.002858713 | 20 |
| forest_B_RF-01 | finishing | 158 | 0.172184645 | 0.201000252 | -0.048925740 | 15 |
| forest_B_RF-01 | sewing | 235 | 0.132452681 | 0.168428146 | -0.006126893 | 18 |
| linear_A | finishing | 158 | 0.165728299 | 0.200866166 | -0.019236806 | 18 |
| linear_A | sewing | 235 | 0.124436585 | 0.159870076 | +0.002963751 | 17 |

Finishing has higher pooled MAE for every model. The forest worsens finishing compared with department mean (0.172184645 vs 0.165755260) and improves sewing (0.132452681 vs 0.134847254). Linear A's finishing MAE is nearly tied with the baseline, while its sewing improvement is larger. Forest bias is more negative in finishing (-0.048925740) than sewing (-0.006126893). These heterogeneous patterns do not justify a single explanation or a claim that every department benefits.

| Department | Team ID | n | Dates | Low support | Department MAE | Linear A MAE | Forest MAE | Windows present | Min window n | Fold target-mean range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| finishing | 1 | 18 | 18 | True | 0.154611202 | 0.126425548 | 0.153623484 | 4/4 | 3 | 0.313872636 |
| finishing | 10 | 12 | 12 | True | 0.150114234 | 0.166761337 | 0.171540516 | 4/4 | 1 | 0.154407634 |
| finishing | 11 | 7 | 7 | True | 0.286396911 | 0.274640969 | 0.287906293 | 3/4 | 1 | 0.437115647 |
| finishing | 12 | 18 | 18 | True | 0.131898289 | 0.134303720 | 0.137582704 | 4/4 | 3 | 0.134898457 |
| finishing | 2 | 17 | 17 | True | 0.165047830 | 0.136310249 | 0.174850297 | 4/4 | 3 | 0.276780828 |
| finishing | 3 | 7 | 7 | True | 0.214835101 | 0.194174841 | 0.225814514 | 3/4 | 1 | 0.293850043 |
| finishing | 4 | 15 | 15 | True | 0.157857188 | 0.148078315 | 0.165828891 | 4/4 | 2 | 0.291260606 |
| finishing | 5 | 9 | 9 | True | 0.162384547 | 0.235382138 | 0.198280469 | 3/4 | 1 | 0.079824153 |
| finishing | 6 | 14 | 14 | True | 0.211551510 | 0.215986707 | 0.214401839 | 4/4 | 1 | 0.314328518 |
| finishing | 7 | 12 | 12 | True | 0.117684248 | 0.133125104 | 0.127103849 | 4/4 | 2 | 0.262762108 |
| finishing | 8 | 17 | 17 | True | 0.174371401 | 0.178595109 | 0.166639011 | 4/4 | 3 | 0.242268638 |
| finishing | 9 | 12 | 12 | True | 0.145732293 | 0.157898122 | 0.142065247 | 3/4 | 4 | 0.218762595 |
| sewing | 1 | 19 | 19 | True | 0.143086966 | 0.098870249 | 0.120157960 | 4/4 | 4 | 0.250105097 |
| sewing | 10 | 20 | 20 | False | 0.133567351 | 0.148950170 | 0.137697016 | 4/4 | 5 | 0.154020714 |
| sewing | 11 | 20 | 20 | False | 0.086310022 | 0.109795119 | 0.090326501 | 4/4 | 5 | 0.267782340 |
| sewing | 12 | 20 | 20 | False | 0.080240033 | 0.099646658 | 0.061272272 | 4/4 | 5 | 0.240195280 |
| sewing | 2 | 20 | 20 | False | 0.180080709 | 0.155109134 | 0.179483009 | 4/4 | 5 | 0.179881250 |
| sewing | 3 | 20 | 20 | False | 0.145045876 | 0.106413312 | 0.142798202 | 4/4 | 5 | 0.200122515 |
| sewing | 4 | 20 | 20 | False | 0.124608431 | 0.110408845 | 0.138269685 | 4/4 | 5 | 0.228482156 |
| sewing | 5 | 19 | 19 | True | 0.095587694 | 0.093112458 | 0.092256170 | 4/4 | 4 | 0.154371985 |
| sewing | 6 | 20 | 20 | False | 0.081648860 | 0.083168129 | 0.100022926 | 4/4 | 5 | 0.178009207 |
| sewing | 7 | 18 | 18 | True | 0.241821217 | 0.208299717 | 0.231875003 | 4/4 | 3 | 0.078008656 |
| sewing | 8 | 19 | 19 | True | 0.240814032 | 0.211430661 | 0.240909196 | 4/4 | 4 | 0.269447772 |
| sewing | 9 | 20 | 20 | False | 0.079800596 | 0.077926064 | 0.067104731 | 4/4 | 5 | 0.155901651 |

There are 24 department/team pairs; 20 appear in all four windows. Sixteen pairs have fewer than 20 pooled observations (48 of 72 model/team summaries). **Every team/window cell is low support.** The n<20 marker is a descriptive guard, not a statistical-power guarantee when n>=20. Missing team/window cells stay absent. Equal team numbers in different departments are kept separate; the source does not establish an unchanged roster or globally stable identity semantics.

For illustration, sewing/team 8 has 19 observations, 4–5 per window. Its fold target mean falls from 0.661243501 to 0.554551423, 0.460277024, and 0.391795729; forest fold MAE ranges from 0.151845082 to 0.342760309. Sewing/team 11 has 20 observations, five per window, with nonmonotonic target means and forest MAE 0.022591247..0.180698038. These stored IDs exhibit temporal variation, but small cells, roster changes, style mix, and measurement definitions cannot be disentangled. Do not infer worker performance or causes. The complete JSON contains all model/team/window errors and target summaries.

## Structured prediction readiness assessment

Confirmed below means a verified software behavior or reproducible property of this historical experiment. It does **not** confirm source timing or factory effectiveness. Provisional means an explicit working assumption; Unverified means required operational evidence or capability is absent.

| Requirement | Status | Current evidence / limit | Real-production evidence or acceptance requirement |
| --- | --- | --- | --- |
| Data/prediction provenance | Confirmed | Dataset/split/artifact hashes, aligned OOF identities, fixed parameters, and scores are checked | Maintain versioned source snapshots and model/config lineage; hashes alone do not attest business semantics |
| Prediction-time features | Provisional | Scheduled date -> calendar and categorical assignments are assumed available before shift | Timestamped snapshots with captured_at/as_of, shift start/timezone, revision history, and audit of all source fields |
| Scheduled team/department | Provisional | Historical IDs are reused; roster stability and scope are not established | Effective-dated assignment/roster records, stable IDs, reassignment times, and scheduled-versus-realized distinctions |
| Label finalization latency | Unverified | Earlier-date labels are assumed finalized before the next fold cutoff | Observed shift end, calculation/finalization/revision times, quality status, and a verified availability lag |
| Target definition and row grain | Unverified | Continuous productivity ratio and (date, department, team) grain are tentative; values >1 retained | Owner-approved formula, units/denominator, shift ID, aggregation/weighting rules, treatment of overachievement, and outcome revisions |
| Data freshness | Unverified | No measured availability SLA or stale-input limit | Source-owner agreements for snapshot age, arrival delays, revisions, rejection/abstention, and label freshness; do not invent numeric limits |
| Missing input handling | Confirmed | Required eligible inputs fail; no silent imputation/drop; WIP is excluded | Measure real missingness and approve planner fallback/abstention; software behavior alone does not prove adequate coverage |
| Unknown team behavior | Confirmed | Existing encoder ignores unknown categories; synthetic tests yield finite predictions | Real unseen-team evidence and an explicit warning/fallback or abstention policy; no unknown categories occur in the real OOF sample |
| Forecast uncertainty | Unverified | Empirical residual quantiles only; no calibrated prediction interval or coverage guarantee | Temporally valid uncertainty/coverage evaluation with adequate group/date support and human-readable limitations |
| Monitoring and response | Unverified | No operational monitoring service or alert thresholds implemented | Log input freshness/missingness/unknown categories and provenance; compare MAE/RMSE/bias against baseline by date/department after labels finalize; define owner-reviewed responses and retraining approval |
| Human oversight | Provisional | Recommended for exploratory comparison, without automated actions | Named analyst review, visible baseline and provenance, limitations/quality flags, recorded overrides, and prohibition on autonomous staffing/scheduling decisions |

Conditional planning fields (targeted_productivity, smv, wip, no_of_workers, no_of_style_change) remain excluded without frozen pre-shift evidence. Realized overtime, incentive, idle time, idle staffing, and same-shift target outcomes remain prohibited inputs. No requirement in this matrix adds a model feature, production connection, monitoring service, or live API.

**Assessment:** an explicitly experimental local retrospective decision-support application may present these saved forecasts, baseline comparisons, support counts, and evidence for human review. Its purpose must be historical investigation, with experimental provenance and limitations visible. Forward-shift reliability, production readiness, or suitability for automated planner decisions is not established. Real factory evidence is required before a live production deployment; none is authorized or implemented here.

## Reproduction and verification

Implementation commit: `dcc8d81af7761880040a4cf9f2a74bcc4c127193` (`feat(analytics): add validated temporal error diagnostics`), verified on GitHub main. No packages were installed or upgraded; reuse `requirements/exp-002.txt` and its EXP-001 pins. Environment: Python 3.13.14, pandas 3.1.1, numpy 2.5.5, scikit-learn 1.9.1; pytest 9.2.0, Ruff 0.17.5. Pins are an installed-environment snapshot, not a wheel/hash lock.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/exp-002.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m loometric.experiments.errors
.\.venv\Scripts\python.exe -m loometric.experiments.errors --output .tmp/exp-005-reproduction.json
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
```

Run from the root with the unchanged local CSV, frozen split, and existing EXP-004 JSON. The CLI accepts `--dataset`, `--split-config`, `--predictions`, and `--output`. Default output is ignored `data/processed/exp-005-error-analysis.json`; it contains detailed groups, target distributions, team stability, tails, common-population sensitivity, and local worst cases. The Markdown report is preserved. Missing/stale predictions fail; this task does not regenerate EXP-004. Retain its artifact with the recorded SHA. No tuning or holdout-evaluation option exists.

Measured load/validation/artifact-match/analysis runtime: **3.802373 seconds**, excluding JSON construction/writing and interpreter imports. Runtime is local wall time, not a deployment latency benchmark.

- Full pytest: **276 passed in 32.82 seconds** (241 previous + 35 new). Normal local filesystem access was used for the established pytest temp/cache restriction. No pytest failure occurred in this task.
- Ruff lint and formatting checks passed after initial import/long-line fixes.
- Dependency checks passed; all 18 exact existing pins match the environment.
- Both real analyses exited 0; every non-runtime JSON field matched exactly.
- Nine protected source/split/earlier-report/profile/ignore/input-artifact fingerprints remained unchanged. No earlier experiment output was overwritten.
- New tests cover hand-calculated errors/tails, support counts, identical-population sensitivity, sparse/zero/singleton behavior, reproducibility, saved-artifact drift, fixed parameters, no fitting, and exclusion of both outer holdouts. No private CSV is required by tests. A static type checker was not run.
- Before the documentation commit, final lint/format/dependency and whitespace
  checks passed. Independent calculations from the unchanged saved forecasts
  confirmed aggregate errors and tail shares; 36 core report rows matched the
  measured JSON. Team support/coverage claims were also checked explicitly.

## Limitations and recommended next milestone

This is one short retrospective source context, 20 evaluated dates, one fixed forest seed, recurring teams, overlapping historical fits, and an already selected forest. Tail masking conditions on known error and cannot estimate next-shift performance. Team/date cells are small, source identities may not describe a constant roster, and measurement/label timing and target units remain uncertain. No confidence interval, significance test, causal explanation, real unseen-team validation, or operational effectiveness claim is made.

Recommended next milestone: define and test the **offline experimental prediction contract** for the existing feature set, including provenance/as-of fields, required-input validation, unknown/stale-input handling, baseline comparison, abstention/human-review rules, and the evidence acceptance criteria above. Use synthetic contract cases while requesting genuine timestamped factory snapshots and finalized-label evidence. Do not promise calibrated uncertainty or business thresholds without data. A later local read-only review interface can be separately scoped after that contract. No next-milestone code, gradient boosting, backend, frontend, scheduling, deployment, or production connection was started.
