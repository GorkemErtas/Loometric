# EXP-006: Synthetic pre-shift attainment models and robust evaluation

Executed 2026-11-22 on authorized synthetic train/validation data only.
**Decision: NO_ML_PROMOTION; retain grouped_mean.** Source: `synthetic-ml-v1`.
This is generated-process evidence, not measured factory forecasting or productivity
improvement. M01's historical experiment results and final test are unchanged.

## Problem, protocol and provenance

Predict completed good pieces × declared standard worker-minutes/piece / frozen
planned available worker-minutes, thirty minutes before a synthetic shift. The
response is demand-censored attainment, not intrinsic efficiency. Above-one values
are legitimate. Undefined zero-capacity labels are excluded from regression with
explicit identity/count/reason and no-prediction records; no imputation or clipping.

[ADR 0020](../decisions/0020-synthetic-model-development-and-promotion.md) and
[configuration](../../configs/synthetic_training_v1.json) were committed before
the study fits. The [architecture](../architecture/synthetic-ml-model-training.md)
documents loading, preprocessing, selection, artifacts and M08C boundaries.
The configuration contains all ten independently retained expected M08A receipts;
the report also records content, generation-configuration, split and authorized
training/validation payload fingerprints for each source.

| Baseline source | Eligible training / undefined | Eligible validation / undefined | Expected manifest fingerprint |
| --- | --- | --- | --- |
| Development19 | 537 / 3 | 180 / 0 | `64330160688ce4c089a22a320cb604e587eed4204d4a43493117f7bd2855f359` |
| Development42 | 532 / 8 | 178 / 2 | `e6af2f894ef3d9edf1c6cee75603f52cd26bc66a55fcaa9d8178056e49b17b3e` |
| Development73 | 535 / 5 | 179 / 1 | `713cf810b17a7d9e37889ea1d086d5892eacc0f58bfcbb574adc4564656e959b` |
| Benchmark42 | 14,711 / 169 | 4,833 / 47 | `7e7dae049270675c2eac4f8ad05d55a9ac84cc9c1160e0a6b7e9f4010a64f7eb` |

The development training dates are 2030-01-07–2030-02-06, validation
2030-02-08–2030-02-18; benchmark training is 2030-01-07–2030-08-10, validation
2030-08-13–2030-10-22. M08A's whole-date gaps and strict global label maturity
remain intact. Each stress source has exactly its seed's baseline training payload;
models are reused for its validation. Profiles/seeds are not pooled for fitting.
The worlds and stress scenarios are correlated simulations sharing one declared
law; no independence-based significance test or factory confidence interval is claimed.

All source files are hashed before decoding and rechecked after loading. Only
train/validation label files are parsed. Reserved outcome/gap/test values and QA
reports are opaque bytes; no study generation, whole-bundle read or QA call parses
them. Pre-shift sources and membership metadata validate the eligible feature view.
No reserved target distribution, prediction, calibration or score is computed.
Unseen crew/line/factory/style evaluation remains separately reserved.

Exact source decimals are validated before finite float64 conversion (absolute
error bound1e-12). The thirteen M08A feature columns retain their order; IDs,
timestamps, seed/scenario/population, realized production/loss/attendance and
latent factors are excluded. Stage, shift and weekday use training-only full dense
one-hot encoding; Ridge alone scales the ten numeric columns using prefix statistics.
Unknown categories mechanically encode as zero but require policy abstention.

## Fixed search and inner temporal evidence

Three expanding original-training folds per world start at floor(n/2), floor(2n/3),
floor(5n/6) eligible dates, width floor(n/6), with one preceding observed date purged.
Evaluation windows do not overlap; all training labels must mature before the first
evaluation cutoff. No outer validation or reserved label enters preprocessing/tuning.

| World | F01 train/evaluation n | F02 train/evaluation n | F03 train/evaluation n |
| --- | --- | --- | --- |
| Development19 | 239 / 80 | 339 / 78 | 417 / 80 |
| Development42 | 238 / 78 | 336 / 77 | 413 / 79 |
| Development73 | 239 / 79 | 338 / 78 | 416 / 79 |
| Benchmark42 | 7,286 / 2,447 | 9,734 / 2,452 | 12,184 / 2,447 |

Search score = half the mean of three development-seed fold-mean MAEs plus half
the benchmark fold-mean MAE. This explicit weighting is an engineering choice,
not evidence of independent populations. All models score identical eligible rows.

| Model | Configuration | Training-fold macro MAE |
| --- | --- | ---: |
| Global mean | Training-only scalar mean | 0.189160217 |
| Stage mean | Training stage means, global fallback | 0.184054455 |
| Grouped mean | Stage/shift/planned-load band, support10, hierarchical fallback | 0.141275349 |
| Ridge1 | Alpha1, SVD, training numeric scaling | 0.157788207 |
| Ridge10 | Alpha10, same preprocessing | 0.157465584 |
| Forest6 | 150 trees, depth6, leaf minimum10 | 0.120331828 |
| Forest12 | 150 trees, depth12, leaf minimum5 | 0.097656006 |
| Hist15 | 150 iterations, learning rate0.05, leaves15, L2=5 | 0.100567507 |
| Hist31 | Same iterations/rate, leaves31, L2=10 | 0.096370655 |

Model seed42, RF one worker and numerical thread pools one. Histogram boosting
has no early stopping/internal validation split. Family finalists are Ridge10,
Forest12 and Hist31; the reference is grouped_mean. Group bands use exact planned
load≤0.6/(0.6,1]/>1 with minimum10 rows; fallback stage/shift → stage → global.
These settings were not revised after outer-validation results.

## Benchmark validation metrics

All rows below use the same **4,833** defined-label benchmark validation observations.
Bias is prediction minus actual; all errors are in synthetic target-ratio units.

| Model | MAE | RMSE | R² | Bias | Median abs. error | P90 abs. error | P95 abs. error | Worst abs. error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Global mean | 0.190904604 | 0.234637838 | -0.000008506 | +0.000684300 | 0.165717645 | 0.385065787 | 0.424779409 | 0.834061272 |
| Stage mean | 0.189290550 | 0.233659918 | 0.008309767 | +0.000675725 | 0.160701403 | 0.385185785 | 0.427815964 | 0.812239698 |
| Grouped mean | 0.122346291 | 0.161097272 | 0.528606086 | +0.001344558 | 0.096179267 | 0.256162458 | 0.324500721 | 0.918864545 |
| Ridge10 | 0.158366595 | 0.199055290 | 0.280294129 | -0.001452418 | 0.133274793 | 0.321643459 | 0.385697976 | 0.957323461 |
| Forest12 | 0.076277437 | 0.111612830 | 0.773725384 | +0.000054756 | 0.049948560 | 0.176101016 | 0.238377673 | 0.901034855 |
| Hist31 | 0.084484980 | 0.119293904 | 0.741509791 | -0.000530179 | 0.059009707 | 0.191893349 | 0.249475176 | 0.917217183 |

Forest12 benchmark MAE is37.6545% lower than grouped mean; Hist31 is30.9460% lower.
These are reductions in synthetic validation error, not factory productivity gains.
Their macro-profile reductions are31.0578% and29.5437%; Ridge10 is17.9384% worse.
The strongest aggregate outer-validation naive comparator is also grouped_mean.
Forest and histogram models win3/3 inner folds in every world, but those reused
selection folds are not independent confirmation.

## Cross-seed and paired stress validation

| World/scenario | n | Grouped mean MAE | Ridge10 MAE | Forest12 MAE | Hist31 MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development19 baseline | 180 | 0.119761398 | 0.143927484 | 0.099884776 | 0.098261197 |
| Development19 disruption | 180 | 0.218462338 | 0.192373967 | 0.197586685 | 0.197269218 |
| Development19 surge | 180 | 0.126360994 | 0.167436668 | 0.109564219 | 0.107587315 |
| Development42 baseline | 178 | 0.143584456 | 0.136939071 | 0.101733086 | 0.096870726 |
| Development42 disruption | 178 | 0.234597657 | 0.202880815 | 0.190620298 | 0.196583751 |
| Development42 surge | 178 | 0.131883915 | 0.173353240 | 0.101858606 | 0.100785346 |
| Development73 baseline | 179 | 0.150779891 | 0.165326594 | 0.108101529 | 0.101793114 |
| Development73 disruption | 179 | 0.227985170 | 0.182171928 | 0.196372109 | 0.189634696 |
| Development73 surge | 179 | 0.146152860 | 0.148599487 | 0.097282259 | 0.094462510 |
| Benchmark42 baseline | 4,833 | 0.122346291 | 0.158366595 | 0.076277437 | 0.084484980 |

Forest baseline improvements are16.5969%,29.1476%,28.3051% across development
seeds19/42/73; Hist31 improvements are17.9525%,32.5340%,32.4889%. Both improve
the macro stress MAE: forest14.1644% disruption /23.6630% surge, histogram14.3247%
/25.1145%. Ridge degrades surge MAE21.0168% on average, up to32.5066% for one seed.
Hidden disruption is absent from predictive inputs, so even models beating a naive
baseline still substantially overpredict its lowered outcomes. For development42
disruption, grouped-mean bias is+0.228837536, forest+0.185927756, histogram+0.189186733.
This is a material risk rather than evidence that an unseen disruption is detected.

## Subgroups, tails and promotion decision

Promotion required≥5% macro improvement, positive improvement in every baseline
world,≥2/3 temporal wins in every world,≤5% stage regression in every cell, no mean
stress regression and≤10% individual stress-seed regression,≤5% positive-error-P95
regression and≤10% worst-error regression in every cell. Within1% of the best
eligible macro score prefer Ridge, histogram, forest. No gate changed after results.

| Finalist | Important passed evidence | Failed frozen gates | Decision |
| --- | --- | --- | --- |
| Forest12 | Every baseline world improves; all temporal folds win; macro/stress/tail guards pass | Stage guard: maximum51.8408% regression | Reject promotion |
| Hist31 | Every baseline world improves; all temporal folds win; macro/stress/positive-tail guards pass | Stage guard32.7993%; worst-error guard23.1450% regression | Reject promotion |
| Ridge10 | Some development cells improve | Macro, seed, temporal, stage, surge and tail guards fail | Reject promotion |

The worst forest stage regression is **development19 baseline packing**, n=36:
MAE0.130579885 versus grouped mean0.085997900 (+51.8408%). Under surge that same
stage worsens39.6942%; development73 disruption cutting worsens14.8677% (n=35).
Histogram packing worsens32.3274% in development19 baseline and32.7993% under surge,
each n=36. Small repeated-context stage cells do not establish significance, but
they fail the predeclared conservative gate. A better average does not erase them.

Every model's full report contains all stage, shift, staffing, workload, planned
interruption, demand-censoring, low-demand and calendar-week slices with counts,
tails and bias; cells below30 observations are flagged low-support. Selected
baseline benchmark examples (rounded; exact values remain in the ignored report):

| Slice | n | Grouped-mean MAE |
| --- | ---: | ---: |
| Day / night | 2,417 / 2,416 | Approximately0.1217 /0.1230 |
| Staffing1–5 /6–10 /11+ | 1,407 /1,370 /2,056 | Approximately0.1344 /0.1160 /0.1183 |
| Low / nominal / high planned load | 841 /1,404 /2,588 | Approximately0.0591 /0.0946 /0.1579 |
| No /1–30 /31+ planned stop minutes | 92 /2,399 /2,342 | Approximately0.1226 /0.1180 /0.1268 |
| Completed all offered pieces / remaining WIP | 2,091 /2,742 | Approximately0.0898 /0.1471 |

The last row uses outcomes for diagnostics only. Low demand often makes output
predictable because it caps attainable work; it is not evidence of high/low
intrinsic worker capability. Capacity-limited rows and quality-control errors remain
harder. The retained baseline's worst benchmark error is0.918864545, its P95 positive
error approximately0.2564. All models' range/tail counts are retained untrimmed;
above-one point predictions are allowed and not relabeled invalid merely for that.

## Descriptive uncertainty and abstention

The selected benchmark baseline has7,346 training-OOF residuals. Its global absolute
P90 is0.250040655; stage radii range0.219984029 (packing, n=1,467) to0.304386700
(quality control, n=1,472); all stage groups exceed minimum30, so none uses fallback.
The resulting empirical benchmark coverage is4,299/4,833 =88.9510%, mean width
0.492877532. It is **not a calibrated90% interval**: folds were reused for selection,
observations are dependent and hidden shift changes the residual distribution.

Selected-baseline empirical coverage under disruption falls to76.6667%,74.1573%,
73.1844% across development seeds19/42/73. Forest/histogram bands are narrower and
can fail more sharply (development42 disruption:53.9326% /52.2472%). No reserved
calibration data is consumed, and no coverage guarantee is claimed.

All models' primary metrics retain flagged defined-label rows. Benchmark has four
feature-review contexts (three opening-WIP extrapolations and one order-quantity
extrapolation);4,829 are within declared feature support. Hidden disruption can
leave the same counts unchanged, so support checks do not detect it. Unknown
categories, invalid schema/numbers/stock, zero capacity and negative/nonfinite or
physically unsupported predictions abstain. Numeric or predicted-label support
extrapolation requires review. Unseen entity transport remains unassessed, regardless
of a syntactically supported feature vector. No capacity permission follows.

## Artifacts, correction and reproduction

Final artifact: benchmark original-training grouped mean,14,711 labels, dates
2030-01-07–2030-08-10, with explicit fallback and no validation refit. It is transparent
JSON, not an executable pickle. The source benchmark content fingerprint is
`f8d202a4771e23936a5f3076e57155f08c5bd8298624bf0ff154a7995596d784`; split fingerprint
`dffe228435e1b0d0cc2dc658f0cf18cb1571fe5a61715ce8e7d2ec78381e6718`, authorized training
payload fingerprint`8ae08345a01c025b5e34a736b848100bc530c4987ac0d750543a7e07847171e8`.

| Final corrected artifact identity | SHA-256 |
| --- | --- |
| Manifest receipt | `cd19c78c8321ac1bb69dc16d61dc7de01469e35f0d35afe3a3d8c8dca4e8b7b4` |
| Transparent model JSON | `6e952eeb9335441d92ed8783258ab0070256beef7eabb217b5bc7d60597823b4` |
| Deterministic report | `e692c9e4db04fafbf7f811e5628f478d3c2e19deeae196072f11c5264c47993c` |

The first two provisional local runs (a/b) reproduced, but an independent workload-
band consistency audit found one benchmark training observation exactly at0.6
misclassified by binary multiplication. The diagnostic exact band exposed it:
100 pieces×4.86 worker-minutes/piece /(405 minutes×2 workers)=0.6 exactly.
Correct the baseline calculation with rational reconstruction of validated decimal
inputs, add a regression and repeat the **unchanged** study as c/d. No feature,
target, hyperparameter, selection threshold or reserved dataset changed. The
provisional artifacts remain ignored/superseded and are not final evidence. Final
baseline benchmark MAE changes slightly; the NO_ML_PROMOTION decision is unchanged.

```powershell
.venv/Scripts/python.exe -m loometric.synthetic_training run --output data/processed/synthetic_training/my-exp-006
.venv/Scripts/python.exe -m loometric.synthetic_training inspect --artifact data/processed/synthetic_training/exp-006-c --expected-fingerprint cd19c78c8321ac1bb69dc16d61dc7de01469e35f0d35afe3a3d8c8dca4e8b7b4
```

The report contains132 fit-provenance entries,72,486 training-OOF prediction rows
(8,054 observation/world exposures repeated across nine models) and38,664 validation
prediction rows (6,444 observation/world/scenario exposures across six finalists/
references). Exclusion audit has273 entries across all ten bindings; paired stress
training records repeat and are not independent additional exclusions.

Python3.13.14, pandas3.1.1, NumPy2.5.5, sklearn1.9.1, SciPy1.18.1, joblib1.6.0 and
threadpoolctl3.8.0 remain unchanged. Numerical comparison tolerance is1e-12 for
metrics/predictions, with exact selection required; deterministic content is
compared byte-for-byte when reproduced. Runtime/memory logs remain separate from
artifact hashes. Corrected runs c/d have **byte-identical** model JSON, manifest,
report, OOF predictions, validation predictions and exclusion audit. All selections,
metrics and predictions match exactly, exceeding the documented tolerance. A
follow-up exact-band audit agrees on every authorized training/validation record.
The retained manifest passes metadata/byte inspection without loading a model.

Study execution after dataset loading took71.0744s and73.1689s; whole-process
lifetime peak working sets were382,869,504 and382,693,376 bytes (about365MiB).
These peaks include loading/imports and cannot be assigned to an individual model.
In run c, full benchmark training took0.5600s grouped mean,0.0789s Ridge10,7.8525s
Forest12 and0.7188s Hist31. Batch validation prediction cost averaged73.11/2.94/
25.02/11.71 microseconds per observation respectively, over4,833 rows. These are
host-specific batch costs, not single-request latency guarantees or promotion gates.
The selected transparent model is3,449 bytes. Native estimator counts/rows/threads
are bounded, but no new OS hard watchdog is claimed.

Focused M08B verification:61 tests passed in43.58s after the exact-band correction;
Ruff lint/format pass. Tests include all-fit train-row spies, private-source reserved
JSON poisoning, metric/selection/uncertainty checks, reproducibility and artifact
tampering/no automatic deserialization. Complete repository regression evidence is
recorded in the architecture guide after execution.

## M08C verdict

**Reproducible offline baseline artifact only; no promoted ML serving candidate.**
There is no inference loader/endpoint, live-input contract or frontend prediction
page. Unseen factory/line/crew/style tests remain explicitly deferred to a separately
approved final-evaluation milestone. Uncalibrated bands, hidden shift, weak subgroup
evidence, trusted loading, source-context/freshness validation, abstention/fallback
and operational controls remain blockers. The target is not M02 assumed efficiency;
no automatic capacity conversion or scheduling integration exists. M08B stops here.
