# EXP-009 actual prospective frozen evaluation — M10A.4

Authorized 2026-11-26. The [frozen protocol](EXP-009-prospective-frozen-evaluation.md)
and [configuration](../../configs/prospective_evaluation_v1.json) remain unchanged.
Four frozen M09B models, eight declared new-world cases, no fitting, tuning,
calibration, sample extension or threshold changes. **NO_ML_PROMOTION.**

## Pre-merge verification and preserved history

M10A.3 passed final review: 263 selected Python regressions in 280.44s, 183 frontend
tests in 21.06s and 12 Windows/Edge browser workflows in 2.0m. Root Ruff lint/format
(322 files), dependency check and frozen source/artifact/dataset audits passed.
Main was fast-forwarded from `157b72a` to
`e10c9bce84ef9b16352785ba6ccf891cec153da7`; the remote hash was verified. Both
`9460eca` (engine) and `e10c9bc` (evidence documentation) remain in history.
Actual execution uses separate branch `feature/m10a4-exp009-prospective-results`.

Before actual generation, commit `eeb36596bcd4cdbd1f4787eb8c57f73231324d09`
adapted four absence assertions into a metadata-only preservation fixture. Four
focused tests passed in 43.91s and the commit/push was verified. Private regression
tests can now coexist with actual outputs without opening their labels or modifying
their files. Engine, generator and protocol sources were not changed.

## Source preparation, registered before scoring

This section and the small, intentionally versioned
[source receipt record](EXP-009-source-receipts.json) were recorded and pushed
before model scoring. They contain metadata/hashes, not datasets or label values.

Exactly eight actual cases were generated: seeds 101, 211, 307 and 401, each under
baseline and hidden disruption. Every case passed two full deterministic generator
passes and physical QA before create-only publication. Each has 2,720 source rows,
18 scoring dates and 360 planned validation observations: 21,760 source exposures,
2,880 scoring exposures and 1,440 distinct paired scoring observations in total.
The hypothetical scoring calendar is 2032-03-11 through 2032-03-31. All original
parameters, 13 features, target definition and units are preserved.

The producer's eight returned manifest hashes were retained outside the dataset
root and supplied explicitly to a separate label-blind registrar. Independent
verification then accepted the externally retained ledger receipt:

`cb0acaa9513c06769d88272ec53bc22890603122751956352630f417556eb2a9`

Verification checked actual seeded source joins, entity provenance/disjointness,
temporal availability, exact exposure grids, matched pre-cutoff bytes, closed
manifests, every file identity and deterministic replay attestations. No model was
loaded or scoring label decoded in these source operations. Train/gap/test labels
and global outcomes remained opaque outside the producer's physical QA.

| Operation | Whole child seconds | Peak committed bytes | Status |
| --- | ---: | ---: | --- |
| Preparation, two passes/case | 49.596908 | 55,898,112 | SOURCE_GENERATION_REPLAY_VERIFIED |
| Independent label-blind registration | 18.842456 | 76,488,704 | REGISTERED_LABEL_BLIND_REPLAY_VERIFIED |
| Independent ledger/source verification | 16.778931 | 72,306,688 | INDEPENDENT_LEDGER_AND_SOURCES_VERIFIED |

All operations used native Windows Job Object aggregate-commit enforcement,
2,048 MiB / 1,200 seconds and one numeric thread. Actual UTC timestamps and full
operation responses are retained in ignored `.tmp/exp009-m10a4/`. Dataset bytes,
model binaries, label/prediction vectors and full generated run artifacts stay
under ignored paths. Deterministic receipts exclude timing/peak/timestamp telemetry.

The frozen configuration's NOT_GENERATED field describes declaration-time state;
it is intentionally unchanged. At this receipt-recording stage, evaluation had
not begun and no validation results were inspected. Later execution results belong
in a separate dated section below, including failures without retries.

## Frozen evaluation results (2026-11-26)

**Verified decision: REPLICATION_NOT_SUPPORTED. NO_ML_PROMOTION.**
The execution and reproduction were valid. All 48 minimum-count checks passed;
46 of 77 numerical guards passed and **31 failed**. No run failed technically,
was retried, or was selected after looking at its scores. A was executed once;
B was executed once, using the retained A receipt before inspecting A metrics.
An independent read-only verifier subsequently accepted both completed runs.

All 2,880 planned scoring exposures are accounted for. There are **2,854 defined
targets** (1,427 per condition) and **26 explicit zero-capacity exclusions**
(13 per condition). Every run made 32 raw model-predict calls and 11,416 defined-
target predictions, below the 11,520 ceiling. No fit, tuning trial or calibration
fit occurred. The original 17 source files/case and source receipts were preserved.

### Equal-world macro metrics by condition

Each number below averages the four per-world metrics with equal weights.
In particular, R², P95 and worst columns are averages of world statistics, not
row-pooled statistics. The final column separately shows the actual maximum
absolute error over all defined exposures in that condition. Bias is prediction
minus actual; all metrics use raw unclipped predictions and dimensionless target units.

| Condition | Frozen model | MAE | RMSE | Mean R² | Bias | Mean P95 abs | Mean worst abs | Mean P95 positive | Actual max abs |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | Grouped Mean | 0.131429 | 0.170751 | 0.448863 | 0.008380 | 0.340107 | 0.593825 | 0.262110 | 0.645007 |
| baseline | Forest12 | 0.121178 | 0.170251 | 0.449147 | 0.000412 | 0.362178 | 0.684973 | 0.283800 | 0.883611 |
| baseline | Hist31 | 0.119791 | 0.165997 | 0.476385 | 0.004177 | 0.340403 | 0.701950 | 0.287371 | 0.923256 |
| baseline | RF Physics | 0.115372 | 0.178854 | 0.385709 | 0.000495 | 0.384758 | 0.764882 | 0.302445 | 1.057602 |
| disruption | Grouped Mean | 0.218488 | 0.269217 | -2.463779 | 0.205080 | 0.480959 | 0.737385 | 0.480959 | 0.786014 |
| disruption | Forest12 | 0.203855 | 0.262195 | -2.269717 | 0.197112 | 0.490839 | 0.852039 | 0.490839 | 1.029980 |
| disruption | Hist31 | 0.208100 | 0.265362 | -2.341788 | 0.200877 | 0.507740 | 0.861073 | 0.507740 | 1.069625 |
| disruption | RF Physics | 0.203759 | 0.273431 | -2.545383 | 0.197196 | 0.523439 | 0.932810 | 0.523439 | 1.203971 |

RF Physics baseline macro MAE improves **4.791651% against Forest12** and
**12.217182% against Grouped Mean**. Under disruption, the gains are only
**0.047280% against Forest12** and **6.741679% against Grouped Mean**. These
are ratios of macro MAEs, not averages of per-world percentage gains.

The smaller baseline MAE does not satisfy the full declaration. RF Physics has
higher baseline RMSE and mean worst error, lower macro R² than Forest12, and
fails several stage and tail guards. Its actual worst absolute error reaches
**1.057602 baseline** and **1.203971 disruption**. Hidden disruption raises its
macro bias to **+0.197196** and produces **-2.545383 macro R²**.

### Per-world metrics and relative improvements

Every world has 360 planned rows/condition. Defined counts for seeds
101/211/307/401 are respectively 357/355/357/358 in both matched arms.
All models use exactly the same defined-target IDs within each case.

| Seed / condition | Model | Defined N | MAE | RMSE | R² | Bias | P95 abs | Worst abs | P95 positive |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 101 / baseline | Grouped Mean | 357 | 0.108669 | 0.139200 | 0.520327 | 0.023172 | 0.236014 | 0.645007 | 0.223360 |
| 101 / baseline | Forest12 | 357 | 0.097781 | 0.135868 | 0.543022 | 0.018696 | 0.270171 | 0.568411 | 0.244606 |
| 101 / baseline | Hist31 | 357 | 0.096109 | 0.131897 | 0.569343 | 0.016024 | 0.259366 | 0.600293 | 0.239828 |
| 101 / baseline | RF Physics | 357 | 0.095574 | 0.143329 | 0.491451 | 0.012008 | 0.284883 | 0.583874 | 0.256891 |
| 101 / disruption | Grouped Mean | 357 | 0.222136 | 0.267335 | -3.452868 | 0.211016 | 0.446624 | 0.786014 | 0.446624 |
| 101 / disruption | Forest12 | 357 | 0.210553 | 0.260786 | -3.237370 | 0.206539 | 0.479738 | 0.697500 | 0.479738 |
| 101 / disruption | Hist31 | 357 | 0.208937 | 0.259090 | -3.182448 | 0.203867 | 0.480361 | 0.729382 | 0.480361 |
| 101 / disruption | RF Physics | 357 | 0.202663 | 0.263734 | -3.333699 | 0.199851 | 0.498327 | 0.712963 | 0.498327 |
| 211 / baseline | Grouped Mean | 355 | 0.124471 | 0.166345 | 0.490888 | 0.033742 | 0.339394 | 0.541407 | 0.296745 |
| 211 / baseline | Forest12 | 355 | 0.119338 | 0.170071 | 0.467829 | 0.004300 | 0.363523 | 0.883611 | 0.284897 |
| 211 / baseline | Hist31 | 355 | 0.118074 | 0.164743 | 0.500652 | 0.012739 | 0.328868 | 0.923256 | 0.270331 |
| 211 / baseline | RF Physics | 355 | 0.120438 | 0.191686 | 0.323961 | 0.006343 | 0.400723 | 1.057602 | 0.354469 |
| 211 / disruption | Grouped Mean | 355 | 0.233262 | 0.284197 | -2.806923 | 0.225409 | 0.501030 | 0.687776 | 0.501030 |
| 211 / disruption | Forest12 | 355 | 0.201393 | 0.259291 | -2.168906 | 0.195966 | 0.467127 | 1.029980 | 0.467127 |
| 211 / disruption | Hist31 | 355 | 0.210292 | 0.268447 | -2.396664 | 0.204405 | 0.492574 | 1.069625 | 0.492574 |
| 211 / disruption | RF Physics | 355 | 0.202101 | 0.281665 | -2.739378 | 0.198010 | 0.571590 | 1.203971 | 0.571590 |
| 307 / baseline | Grouped Mean | 357 | 0.150646 | 0.193085 | 0.345217 | 0.024389 | 0.393284 | 0.608090 | 0.304567 |
| 307 / baseline | Forest12 | 357 | 0.144168 | 0.204286 | 0.267047 | 0.022306 | 0.454468 | 0.760312 | 0.386823 |
| 307 / baseline | Hist31 | 357 | 0.143240 | 0.199843 | 0.298577 | 0.030930 | 0.430878 | 0.701222 | 0.422636 |
| 307 / baseline | RF Physics | 357 | 0.143241 | 0.219146 | 0.156536 | 0.027441 | 0.486705 | 0.837500 | 0.418528 |
| 307 / disruption | Grouped Mean | 357 | 0.238116 | 0.292947 | -2.124079 | 0.226298 | 0.511722 | 0.752496 | 0.511722 |
| 307 / disruption | Forest12 | 357 | 0.233519 | 0.302494 | -2.331018 | 0.224214 | 0.576446 | 0.992446 | 0.576446 |
| 307 / disruption | Hist31 | 357 | 0.241595 | 0.307566 | -2.443665 | 0.232838 | 0.589727 | 0.895160 | 0.589727 |
| 307 / disruption | RF Physics | 357 | 0.241547 | 0.317814 | -2.676961 | 0.229350 | 0.609440 | 1.069634 | 0.609440 |
| 401 / baseline | Grouped Mean | 358 | 0.141930 | 0.184375 | 0.439019 | -0.047785 | 0.391735 | 0.580796 | 0.223768 |
| 401 / baseline | Forest12 | 358 | 0.123427 | 0.170781 | 0.518690 | -0.043653 | 0.360549 | 0.527560 | 0.218873 |
| 401 / baseline | Hist31 | 358 | 0.121741 | 0.167507 | 0.536966 | -0.042986 | 0.342499 | 0.583028 | 0.216690 |
| 401 / baseline | RF Physics | 358 | 0.102235 | 0.161255 | 0.570890 | -0.043811 | 0.366721 | 0.580553 | 0.179891 |
| 401 / disruption | Grouped Mean | 358 | 0.180439 | 0.232389 | -1.471245 | 0.157598 | 0.464460 | 0.723256 | 0.464460 |
| 401 / disruption | Forest12 | 358 | 0.169955 | 0.226210 | -1.341574 | 0.161730 | 0.440042 | 0.688230 | 0.440042 |
| 401 / disruption | Hist31 | 358 | 0.171575 | 0.226345 | -1.344374 | 0.162397 | 0.468297 | 0.750126 | 0.468297 |
| 401 / disruption | RF Physics | 358 | 0.168725 | 0.230513 | -1.431493 | 0.161572 | 0.414400 | 0.744671 | 0.414400 |

Positive gain below means lower RF Physics MAE than the named comparator.

| Seed / condition | Gain vs Forest12 (%) | Gain vs Grouped Mean (%) | RF Physics minus Forest12 MAE |
| --- | ---: | ---: | ---: |
| 101 / baseline | 2.257418 | 12.050543 | -0.002207328 |
| 101 / disruption | 3.747292 | 8.766383 | -0.007890029 |
| 211 / baseline | -0.921875 | 3.239922 | +0.001100147 |
| 211 / disruption | -0.351147 | 13.359089 | +0.000707187 |
| 307 / baseline | 0.642900 | 4.915565 | -0.000926854 |
| 307 / disruption | -3.437619 | -1.440597 | +0.008027494 |
| 401 / baseline | 17.169487 | 27.967771 | -0.021191745 |
| 401 / disruption | 0.723828 | 6.492176 | -0.001230179 |

RF Physics wins baseline MAE against Forest12 in 3/4 worlds; seed 211 regresses
by about 0.92%, while seed 401 supplies the largest improvement. Under disruption,
seed 307 regresses against both Forest12 and Grouped Mean. No model was reselected.

### World bootstrap and date-block sensitivity

All intervals use linear 2.5/97.5 percentiles of the 256 ordered four-world draws.
The single acceptance interval is the first row. Other intervals are descriptive.

| Condition / contrast (MAE left minus right) | Lower | Upper | Acceptance role |
| --- | ---: | ---: | --- |
| baseline: RF Physics − Forest12 | -0.016125522 | +0.000273278 | PRIMARY: upper must be < 0; FAIL |
| baseline: RF Physics − Grouped Mean | -0.031622176 | -0.005718927 | Descriptive only |
| disruption: RF Physics − Forest12 | -0.005740725 | +0.005713076 | Descriptive only |
| disruption: RF Physics − Grouped Mean | -0.026299900 | -0.002295605 | Descriptive only |

The primary interval **[-0.016125522, +0.000273278]** includes zero and fails
its strictly-negative-upper-bound criterion. Each of the four observed primary
world contrasts appears above. All six model pairs/condition and condition-change
bootstrap intervals are retained in the [aggregate record](EXP-009-results.json).

500 paired whole-start-date draws/world used the exact predeclared SHA-256 RNG key.
The following intervals have been sign-reversed from the stored Forest12-minus-
RF-Physics contrast to match the primary direction. They cannot override acceptance.

| Seed | Date sensitivity: RF Physics − Forest12 MAE lower | Upper | Undefined draws |
| --- | ---: | ---: | ---: |
| 101 | -0.007080408 | +0.002172451 | 0 |
| 211 | -0.002704571 | +0.005231641 | 0 |
| 307 | -0.006818814 | +0.004926183 | 0 |
| 401 | -0.027930682 | -0.015347903 | 0 |

The identical-input balanced-pair MAE lower bound is **0.098350177** (equal-world
macro); per-world bounds are 0.093921627, 0.095833247, 0.100954431 and 0.102691403.
This describes the two equally weighted target arms sharing one prediction, not
a bound for baseline alone or proof of a causal factory intervention.

### Per-stage metrics for every world, condition and model

Every stage has 72 planned rows/case; actual defined counts are 70–72, with
18 valid dates, two lines and four crews. No stage is pooled to rescue a guard.
All other declared subgroup metrics/counts are in the receipt-bound ignored
`runs/a/report.json`; its complete 1,298,778 bytes reproduce in B. The committed
aggregate record contains these complete stage metrics/counts and all acceptance guards.

| Seed / condition | Stage | Model | Defined N | MAE | RMSE | R² | Bias | P95 abs | Worst abs | P95 positive |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 101 / baseline | cutting | Grouped Mean | 71 | 0.087877 | 0.111585 | 0.573216 | -0.002794 | 0.175736 | 0.472814 | 0.144915 |
| 101 / baseline | cutting | Forest12 | 71 | 0.055676 | 0.083389 | 0.761649 | -0.002762 | 0.162855 | 0.384141 | 0.118848 |
| 101 / baseline | cutting | Hist31 | 71 | 0.065083 | 0.088324 | 0.732604 | 0.000434 | 0.169465 | 0.342489 | 0.134358 |
| 101 / baseline | cutting | RF Physics | 71 | 0.053748 | 0.083997 | 0.758161 | -0.002429 | 0.168706 | 0.418384 | 0.109934 |
| 101 / baseline | finishing | Grouped Mean | 72 | 0.106348 | 0.153632 | 0.506574 | 0.025803 | 0.227234 | 0.645007 | 0.221165 |
| 101 / baseline | finishing | Forest12 | 72 | 0.108051 | 0.146355 | 0.552210 | -0.017243 | 0.262704 | 0.568411 | 0.222663 |
| 101 / baseline | finishing | Hist31 | 72 | 0.092238 | 0.131507 | 0.638460 | -0.018440 | 0.258716 | 0.600293 | 0.187503 |
| 101 / baseline | finishing | RF Physics | 72 | 0.101895 | 0.155491 | 0.494561 | -0.033071 | 0.290061 | 0.583874 | 0.163873 |
| 101 / baseline | packing | Grouped Mean | 72 | 0.099339 | 0.124869 | 0.674464 | -0.007622 | 0.182667 | 0.593471 | 0.154193 |
| 101 / baseline | packing | Forest12 | 72 | 0.087118 | 0.126289 | 0.667022 | -0.037778 | 0.247911 | 0.536826 | 0.082172 |
| 101 / baseline | packing | Hist31 | 72 | 0.078724 | 0.114168 | 0.727870 | -0.039167 | 0.204285 | 0.552925 | 0.067694 |
| 101 / baseline | packing | RF Physics | 72 | 0.076582 | 0.122245 | 0.688004 | -0.062951 | 0.258131 | 0.429343 | 0.008289 |
| 101 / baseline | quality_control | Grouped Mean | 71 | 0.115013 | 0.138743 | 0.094589 | 0.076930 | 0.257471 | 0.448890 | 0.257471 |
| 101 / baseline | quality_control | Forest12 | 71 | 0.113625 | 0.154862 | -0.128019 | 0.109103 | 0.318697 | 0.498340 | 0.318697 |
| 101 / baseline | quality_control | Hist31 | 71 | 0.107016 | 0.144694 | 0.015250 | 0.104111 | 0.281448 | 0.539707 | 0.281448 |
| 101 / baseline | quality_control | RF Physics | 71 | 0.128413 | 0.179317 | -0.512402 | 0.124619 | 0.352897 | 0.526000 | 0.352897 |
| 101 / baseline | sewing | Grouped Mean | 71 | 0.134932 | 0.161189 | 0.379195 | 0.023942 | 0.257669 | 0.552998 | 0.238387 |
| 101 / baseline | sewing | Forest12 | 71 | 0.124441 | 0.154884 | 0.426809 | 0.043460 | 0.273086 | 0.467104 | 0.273086 |
| 101 / baseline | sewing | Hist31 | 71 | 0.137782 | 0.167274 | 0.331434 | 0.034444 | 0.298529 | 0.514840 | 0.267491 |
| 101 / baseline | sewing | RF Physics | 71 | 0.117410 | 0.156246 | 0.416684 | 0.035564 | 0.274791 | 0.513380 | 0.235986 |
| 101 / disruption | cutting | Grouped Mean | 71 | 0.205839 | 0.244515 | -6.427224 | 0.197317 | 0.392166 | 0.635041 | 0.392166 |
| 101 / disruption | cutting | Forest12 | 71 | 0.202109 | 0.238256 | -6.051838 | 0.197349 | 0.382513 | 0.546368 | 0.382513 |
| 101 / disruption | cutting | Hist31 | 71 | 0.201667 | 0.241931 | -6.271031 | 0.200544 | 0.394764 | 0.504716 | 0.394764 |
| 101 / disruption | cutting | RF Physics | 71 | 0.201371 | 0.242735 | -6.319469 | 0.197682 | 0.377289 | 0.580611 | 0.377289 |
| 101 / disruption | finishing | Grouped Mean | 72 | 0.247179 | 0.295081 | -4.163528 | 0.242695 | 0.480777 | 0.786014 | 0.480777 |
| 101 / disruption | finishing | Forest12 | 72 | 0.201409 | 0.243527 | -2.516886 | 0.199649 | 0.441286 | 0.697500 | 0.441286 |
| 101 / disruption | finishing | Hist31 | 72 | 0.200606 | 0.242301 | -2.481570 | 0.198453 | 0.441431 | 0.729382 | 0.441431 |
| 101 / disruption | finishing | RF Physics | 72 | 0.184560 | 0.245559 | -2.575834 | 0.183821 | 0.425371 | 0.712963 | 0.425371 |
| 101 / disruption | packing | Grouped Mean | 72 | 0.169765 | 0.211391 | -2.386209 | 0.154741 | 0.419219 | 0.739201 | 0.419219 |
| 101 / disruption | packing | Forest12 | 72 | 0.126361 | 0.173083 | -1.270129 | 0.124585 | 0.325549 | 0.682557 | 0.325549 |
| 101 / disruption | packing | Hist31 | 72 | 0.128503 | 0.171734 | -1.234886 | 0.123196 | 0.308074 | 0.698655 | 0.308074 |
| 101 / disruption | packing | RF Physics | 72 | 0.102759 | 0.143061 | -0.550907 | 0.099411 | 0.229631 | 0.575073 | 0.229631 |
| 101 / disruption | quality_control | Grouped Mean | 71 | 0.268760 | 0.302964 | -13.581425 | 0.262860 | 0.445618 | 0.613833 | 0.445618 |
| 101 / disruption | quality_control | Forest12 | 71 | 0.296937 | 0.337921 | -17.140409 | 0.295033 | 0.533147 | 0.663283 | 0.533147 |
| 101 / disruption | quality_control | Hist31 | 71 | 0.290166 | 0.330814 | -16.385446 | 0.290041 | 0.544104 | 0.704650 | 0.544104 |
| 101 / disruption | quality_control | RF Physics | 71 | 0.310971 | 0.361171 | -19.722508 | 0.310549 | 0.553209 | 0.690943 | 0.553209 |
| 101 / disruption | sewing | Grouped Mean | 71 | 0.219523 | 0.272331 | -2.001261 | 0.197812 | 0.452210 | 0.684141 | 0.452210 |
| 101 / disruption | sewing | Forest12 | 71 | 0.227262 | 0.283700 | -2.257091 | 0.217330 | 0.477554 | 0.598247 | 0.477554 |
| 101 / disruption | sewing | Hist31 | 71 | 0.224991 | 0.283049 | -2.242163 | 0.208315 | 0.487166 | 0.645983 | 0.487166 |
| 101 / disruption | sewing | RF Physics | 71 | 0.215315 | 0.280122 | -2.175447 | 0.209434 | 0.458997 | 0.644523 | 0.458997 |
| 211 / baseline | cutting | Grouped Mean | 71 | 0.163011 | 0.203290 | 0.488883 | -0.028991 | 0.389509 | 0.540268 | 0.281843 |
| 211 / baseline | cutting | Forest12 | 71 | 0.152055 | 0.209023 | 0.459651 | -0.085049 | 0.418304 | 0.600419 | 0.178613 |
| 211 / baseline | cutting | Hist31 | 71 | 0.135775 | 0.188890 | 0.558728 | -0.084286 | 0.412868 | 0.535563 | 0.119053 |
| 211 / baseline | cutting | RF Physics | 71 | 0.172674 | 0.243386 | 0.267378 | -0.078367 | 0.478101 | 0.607635 | 0.348436 |
| 211 / baseline | finishing | Grouped Mean | 71 | 0.112116 | 0.154172 | 0.478246 | 0.053775 | 0.253272 | 0.531964 | 0.253272 |
| 211 / baseline | finishing | Forest12 | 71 | 0.129588 | 0.163231 | 0.415127 | -0.051468 | 0.298393 | 0.513111 | 0.188600 |
| 211 / baseline | finishing | Hist31 | 71 | 0.118554 | 0.148192 | 0.517933 | -0.039689 | 0.261128 | 0.497375 | 0.202294 |
| 211 / baseline | finishing | RF Physics | 71 | 0.132735 | 0.172915 | 0.343672 | -0.072655 | 0.303750 | 0.459594 | 0.172570 |
| 211 / baseline | packing | Grouped Mean | 72 | 0.104239 | 0.145789 | 0.271512 | 0.070500 | 0.256295 | 0.541407 | 0.256295 |
| 211 / baseline | packing | Forest12 | 72 | 0.128808 | 0.197596 | -0.338231 | 0.107265 | 0.394134 | 0.883611 | 0.394134 |
| 211 / baseline | packing | Hist31 | 72 | 0.140488 | 0.208260 | -0.486575 | 0.112600 | 0.411867 | 0.923256 | 0.411867 |
| 211 / baseline | packing | RF Physics | 72 | 0.157419 | 0.260464 | -1.325254 | 0.144376 | 0.609337 | 1.057602 | 0.609337 |
| 211 / baseline | quality_control | Grouped Mean | 71 | 0.155103 | 0.195716 | 0.274412 | 0.089145 | 0.369753 | 0.437807 | 0.369753 |
| 211 / baseline | quality_control | Forest12 | 71 | 0.120265 | 0.154208 | 0.549546 | 0.081022 | 0.305207 | 0.454509 | 0.305207 |
| 211 / baseline | quality_control | Hist31 | 71 | 0.126206 | 0.154057 | 0.550431 | 0.102285 | 0.266075 | 0.461598 | 0.266075 |
| 211 / baseline | quality_control | RF Physics | 71 | 0.083311 | 0.124547 | 0.706164 | 0.069250 | 0.235683 | 0.410552 | 0.235683 |
| 211 / baseline | sewing | Grouped Mean | 70 | 0.087653 | 0.116580 | 0.707664 | -0.016950 | 0.226052 | 0.426337 | 0.148104 |
| 211 / baseline | sewing | Forest12 | 70 | 0.065076 | 0.105201 | 0.761950 | -0.032236 | 0.272704 | 0.404017 | 0.058061 |
| 211 / baseline | sewing | Hist31 | 70 | 0.068328 | 0.102427 | 0.774336 | -0.029213 | 0.199432 | 0.462632 | 0.070619 |
| 211 / baseline | sewing | RF Physics | 70 | 0.054604 | 0.102070 | 0.775905 | -0.033394 | 0.240728 | 0.425723 | 0.057416 |
| 211 / disruption | cutting | Grouped Mean | 71 | 0.193567 | 0.247228 | -1.034216 | 0.183279 | 0.499393 | 0.530381 | 0.499393 |
| 211 / disruption | cutting | Forest12 | 71 | 0.138583 | 0.184130 | -0.128373 | 0.127220 | 0.399325 | 0.455147 | 0.399325 |
| 211 / disruption | cutting | Hist31 | 71 | 0.138320 | 0.176038 | -0.031374 | 0.127984 | 0.335606 | 0.443097 | 0.335606 |
| 211 / disruption | cutting | RF Physics | 71 | 0.147674 | 0.231119 | -0.777764 | 0.133902 | 0.565150 | 0.633801 | 0.565150 |
| 211 / disruption | finishing | Grouped Mean | 71 | 0.264947 | 0.314956 | -5.906658 | 0.255984 | 0.477591 | 0.663014 | 0.477591 |
| 211 / disruption | finishing | Forest12 | 71 | 0.156076 | 0.205673 | -1.945256 | 0.150741 | 0.399308 | 0.643159 | 0.399308 |
| 211 / disruption | finishing | Hist31 | 71 | 0.171796 | 0.219789 | -2.363420 | 0.162520 | 0.410146 | 0.627424 | 0.410146 |
| 211 / disruption | finishing | RF Physics | 71 | 0.133433 | 0.190824 | -1.535328 | 0.129554 | 0.403217 | 0.589642 | 0.403217 |
| 211 / disruption | packing | Grouped Mean | 72 | 0.280444 | 0.321275 | -8.165183 | 0.276339 | 0.492274 | 0.687776 | 0.492274 |
| 211 / disruption | packing | Forest12 | 72 | 0.318116 | 0.377906 | -11.681052 | 0.313104 | 0.656832 | 1.029980 | 0.656832 |
| 211 / disruption | packing | Hist31 | 72 | 0.320404 | 0.384497 | -12.127247 | 0.318439 | 0.647828 | 1.069625 | 0.647828 |
| 211 / disruption | packing | RF Physics | 72 | 0.351052 | 0.436132 | -15.889764 | 0.350215 | 0.859735 | 1.203971 | 0.859735 |
| 211 / disruption | quality_control | Grouped Mean | 71 | 0.263491 | 0.313241 | -3.052709 | 0.259455 | 0.521155 | 0.541180 | 0.521155 |
| 211 / disruption | quality_control | Forest12 | 71 | 0.252773 | 0.288936 | -2.448210 | 0.251332 | 0.435639 | 0.566837 | 0.435639 |
| 211 / disruption | quality_control | Hist31 | 71 | 0.273865 | 0.310890 | -2.992098 | 0.272596 | 0.432172 | 0.573926 | 0.432172 |
| 211 / disruption | quality_control | RF Physics | 71 | 0.240991 | 0.286278 | -2.385040 | 0.239561 | 0.439777 | 0.522880 | 0.439777 |
| 211 / disruption | sewing | Grouped Mean | 70 | 0.162198 | 0.203255 | -1.719463 | 0.150211 | 0.343814 | 0.587376 | 0.343814 |
| 211 / disruption | sewing | Forest12 | 70 | 0.138895 | 0.179157 | -1.112855 | 0.134924 | 0.313577 | 0.565056 | 0.313577 |
| 211 / disruption | sewing | Hist31 | 70 | 0.144598 | 0.186930 | -1.300169 | 0.137947 | 0.327170 | 0.623671 | 0.327170 |
| 211 / disruption | sewing | RF Physics | 70 | 0.134300 | 0.180160 | -1.136573 | 0.133767 | 0.306723 | 0.586762 | 0.306723 |
| 307 / baseline | cutting | Grouped Mean | 72 | 0.160621 | 0.201917 | 0.531578 | -0.102910 | 0.381782 | 0.491209 | 0.129888 |
| 307 / baseline | cutting | Forest12 | 72 | 0.157956 | 0.216703 | 0.460468 | -0.128997 | 0.430305 | 0.571642 | 0.062947 |
| 307 / baseline | cutting | Hist31 | 72 | 0.152105 | 0.204517 | 0.519438 | -0.116793 | 0.415468 | 0.522225 | 0.062190 |
| 307 / baseline | cutting | RF Physics | 72 | 0.155985 | 0.229831 | 0.393114 | -0.139859 | 0.487075 | 0.532442 | 0.000302 |
| 307 / baseline | finishing | Grouped Mean | 71 | 0.126496 | 0.164166 | 0.058433 | 0.047998 | 0.284723 | 0.594854 | 0.284723 |
| 307 / baseline | finishing | Forest12 | 71 | 0.096395 | 0.143760 | 0.277961 | 0.018154 | 0.270590 | 0.650758 | 0.270590 |
| 307 / baseline | finishing | Hist31 | 71 | 0.088405 | 0.142913 | 0.286448 | 0.021943 | 0.236667 | 0.701222 | 0.236667 |
| 307 / baseline | finishing | RF Physics | 71 | 0.075121 | 0.129480 | 0.414279 | 0.027343 | 0.259786 | 0.563846 | 0.259786 |
| 307 / baseline | packing | Grouped Mean | 71 | 0.165687 | 0.214173 | -1.443007 | 0.151250 | 0.491580 | 0.608090 | 0.491580 |
| 307 / baseline | packing | Forest12 | 71 | 0.198564 | 0.273330 | -2.978958 | 0.184580 | 0.597463 | 0.760312 | 0.597463 |
| 307 / baseline | packing | Hist31 | 71 | 0.201968 | 0.266372 | -2.778972 | 0.195020 | 0.514373 | 0.663026 | 0.514373 |
| 307 / baseline | packing | RF Physics | 71 | 0.195867 | 0.293382 | -3.584189 | 0.183037 | 0.652017 | 0.837500 | 0.652017 |
| 307 / baseline | quality_control | Grouped Mean | 72 | 0.146042 | 0.182047 | -1.674395 | 0.132606 | 0.317453 | 0.480737 | 0.317453 |
| 307 / baseline | quality_control | Forest12 | 72 | 0.147312 | 0.191727 | -1.966381 | 0.133694 | 0.357366 | 0.558540 | 0.357366 |
| 307 / baseline | quality_control | Hist31 | 72 | 0.159061 | 0.202990 | -2.325154 | 0.145525 | 0.374459 | 0.568802 | 0.374459 |
| 307 / baseline | quality_control | RF Physics | 72 | 0.175098 | 0.229848 | -3.263263 | 0.162578 | 0.415107 | 0.591820 | 0.415107 |
| 307 / baseline | sewing | Grouped Mean | 71 | 0.154307 | 0.199213 | 0.398741 | -0.106732 | 0.395894 | 0.439819 | 0.111442 |
| 307 / baseline | sewing | Forest12 | 71 | 0.120373 | 0.171942 | 0.552089 | -0.095342 | 0.373208 | 0.458967 | 0.054085 |
| 307 / baseline | sewing | Hist31 | 71 | 0.114314 | 0.158844 | 0.617731 | -0.090579 | 0.313210 | 0.418008 | 0.071089 |
| 307 / baseline | sewing | RF Physics | 71 | 0.113504 | 0.177478 | 0.522785 | -0.095442 | 0.432960 | 0.526075 | 0.041073 |
| 307 / disruption | cutting | Grouped Mean | 72 | 0.113535 | 0.158360 | 0.112784 | 0.097057 | 0.318677 | 0.544490 | 0.318677 |
| 307 / disruption | cutting | Forest12 | 72 | 0.096859 | 0.145270 | 0.253391 | 0.070970 | 0.312892 | 0.505952 | 0.312892 |
| 307 / disruption | cutting | Hist31 | 72 | 0.102614 | 0.155650 | 0.142889 | 0.083173 | 0.329450 | 0.589027 | 0.329450 |
| 307 / disruption | cutting | RF Physics | 72 | 0.094209 | 0.146394 | 0.241798 | 0.060108 | 0.277077 | 0.568595 | 0.277077 |
| 307 / disruption | finishing | Grouped Mean | 71 | 0.263090 | 0.310015 | -8.471401 | 0.255529 | 0.491817 | 0.752496 | 0.491817 |
| 307 / disruption | finishing | Forest12 | 71 | 0.229699 | 0.283701 | -6.931799 | 0.225685 | 0.453800 | 0.802961 | 0.453800 |
| 307 / disruption | finishing | Hist31 | 71 | 0.233415 | 0.284854 | -6.996391 | 0.229474 | 0.460965 | 0.853425 | 0.460965 |
| 307 / disruption | finishing | RF Physics | 71 | 0.235513 | 0.284029 | -6.950154 | 0.234874 | 0.473686 | 0.716049 | 0.473686 |
| 307 / disruption | packing | Grouped Mean | 71 | 0.356629 | 0.392605 | -17.788583 | 0.349868 | 0.645376 | 0.734474 | 0.645376 |
| 307 / disruption | packing | Forest12 | 71 | 0.383479 | 0.443826 | -23.010862 | 0.383199 | 0.815573 | 0.992446 | 0.815573 |
| 307 / disruption | packing | Hist31 | 71 | 0.393639 | 0.444694 | -23.104899 | 0.393639 | 0.739197 | 0.895160 | 0.739197 |
| 307 / disruption | packing | RF Physics | 71 | 0.382141 | 0.458180 | -24.589181 | 0.381655 | 0.902553 | 1.069634 | 0.902553 |
| 307 / disruption | quality_control | Grouped Mean | 72 | 0.312414 | 0.347672 | -33.681519 | 0.311404 | 0.502741 | 0.610235 | 0.502741 |
| 307 / disruption | quality_control | Forest12 | 72 | 0.312491 | 0.355681 | -35.297663 | 0.312491 | 0.540608 | 0.688038 | 0.540608 |
| 307 / disruption | quality_control | Hist31 | 72 | 0.324322 | 0.366123 | -37.460124 | 0.324322 | 0.561465 | 0.698300 | 0.561465 |
| 307 / disruption | quality_control | RF Physics | 72 | 0.341380 | 0.394765 | -43.713228 | 0.341375 | 0.608044 | 0.721318 | 0.608044 |
| 307 / disruption | sewing | Grouped Mean | 71 | 0.145621 | 0.182348 | -0.162580 | 0.118251 | 0.344068 | 0.488972 | 0.344068 |
| 307 / disruption | sewing | Forest12 | 71 | 0.145880 | 0.181473 | -0.151441 | 0.129642 | 0.306828 | 0.507197 | 0.306828 |
| 307 / disruption | sewing | Hist31 | 71 | 0.154777 | 0.190405 | -0.267585 | 0.134404 | 0.341164 | 0.462786 | 0.341164 |
| 307 / disruption | sewing | RF Physics | 71 | 0.155159 | 0.193660 | -0.311291 | 0.129541 | 0.305879 | 0.525977 | 0.305879 |
| 401 / baseline | cutting | Grouped Mean | 72 | 0.120741 | 0.158798 | 0.549080 | -0.052932 | 0.355220 | 0.490562 | 0.156989 |
| 401 / baseline | cutting | Forest12 | 72 | 0.115833 | 0.159702 | 0.543935 | -0.091477 | 0.320789 | 0.504878 | 0.059746 |
| 401 / baseline | cutting | Hist31 | 72 | 0.123208 | 0.165626 | 0.509472 | -0.103965 | 0.337277 | 0.496243 | 0.049593 |
| 401 / baseline | cutting | RF Physics | 72 | 0.081091 | 0.145182 | 0.623096 | -0.043368 | 0.397853 | 0.518065 | 0.098520 |
| 401 / baseline | finishing | Grouped Mean | 72 | 0.114896 | 0.151937 | 0.482161 | 0.028016 | 0.288442 | 0.494432 | 0.288442 |
| 401 / baseline | finishing | Forest12 | 72 | 0.104898 | 0.149619 | 0.497843 | 0.021575 | 0.321036 | 0.516350 | 0.280190 |
| 401 / baseline | finishing | Hist31 | 72 | 0.089993 | 0.139859 | 0.561217 | 0.008515 | 0.300360 | 0.537961 | 0.300360 |
| 401 / baseline | finishing | RF Physics | 72 | 0.092684 | 0.151176 | 0.487335 | -0.005993 | 0.331568 | 0.555144 | 0.256096 |
| 401 / baseline | packing | Grouped Mean | 71 | 0.141552 | 0.179907 | 0.339682 | 0.053811 | 0.336820 | 0.580796 | 0.295333 |
| 401 / baseline | packing | Forest12 | 71 | 0.148749 | 0.191552 | 0.251430 | 0.040872 | 0.372313 | 0.482531 | 0.351361 |
| 401 / baseline | packing | Hist31 | 71 | 0.138149 | 0.179415 | 0.343286 | 0.056456 | 0.342227 | 0.478459 | 0.325267 |
| 401 / baseline | packing | RF Physics | 71 | 0.109922 | 0.162169 | 0.463474 | 0.009245 | 0.355826 | 0.434518 | 0.256464 |
| 401 / baseline | quality_control | Grouped Mean | 72 | 0.162858 | 0.210255 | 0.277775 | -0.126585 | 0.412442 | 0.514750 | 0.093749 |
| 401 / baseline | quality_control | Forest12 | 72 | 0.113764 | 0.171413 | 0.519974 | -0.074310 | 0.374492 | 0.527560 | 0.094770 |
| 401 / baseline | quality_control | Hist31 | 72 | 0.119470 | 0.173747 | 0.506808 | -0.056920 | 0.356714 | 0.583028 | 0.087756 |
| 401 / baseline | quality_control | RF Physics | 72 | 0.104591 | 0.176844 | 0.489072 | -0.070287 | 0.402469 | 0.580553 | 0.108516 |
| 401 / baseline | sewing | Grouped Mean | 71 | 0.169986 | 0.212670 | 0.340236 | -0.141120 | 0.398142 | 0.494439 | 0.080532 |
| 401 / baseline | sewing | Forest12 | 71 | 0.134394 | 0.178914 | 0.533056 | -0.114739 | 0.354161 | 0.428841 | 0.059047 |
| 401 / baseline | sewing | Hist31 | 71 | 0.138342 | 0.176130 | 0.547477 | -0.118687 | 0.318986 | 0.416256 | 0.063877 |
| 401 / baseline | sewing | RF Physics | 71 | 0.123287 | 0.168968 | 0.583529 | -0.108818 | 0.346171 | 0.410022 | 0.059065 |
| 401 / disruption | cutting | Grouped Mean | 72 | 0.153050 | 0.191418 | -0.982333 | 0.138590 | 0.322863 | 0.617213 | 0.322863 |
| 401 / disruption | cutting | Forest12 | 72 | 0.117000 | 0.148492 | -0.192937 | 0.100044 | 0.258958 | 0.389446 | 0.258958 |
| 401 / disruption | cutting | Hist31 | 72 | 0.113128 | 0.147023 | -0.169453 | 0.087557 | 0.292632 | 0.421673 | 0.292632 |
| 401 / disruption | cutting | RF Physics | 72 | 0.161639 | 0.222234 | -1.671977 | 0.148153 | 0.395846 | 0.592068 | 0.395846 |
| 401 / disruption | finishing | Grouped Mean | 72 | 0.229488 | 0.281255 | -5.482450 | 0.217930 | 0.504471 | 0.673161 | 0.504471 |
| 401 / disruption | finishing | Forest12 | 72 | 0.214130 | 0.272896 | -5.102883 | 0.211490 | 0.506432 | 0.688230 | 0.506432 |
| 401 / disruption | finishing | Hist31 | 72 | 0.201309 | 0.256837 | -4.405713 | 0.198430 | 0.493482 | 0.709841 | 0.493482 |
| 401 / disruption | finishing | RF Physics | 72 | 0.185724 | 0.256525 | -4.392600 | 0.183921 | 0.483397 | 0.727024 | 0.483397 |
| 401 / disruption | packing | Grouped Mean | 71 | 0.272936 | 0.320345 | -4.934905 | 0.265903 | 0.517326 | 0.723256 | 0.517326 |
| 401 / disruption | packing | Forest12 | 71 | 0.255080 | 0.309948 | -4.555909 | 0.252965 | 0.552515 | 0.635870 | 0.552515 |
| 401 / disruption | packing | Hist31 | 71 | 0.269523 | 0.319484 | -4.903031 | 0.268549 | 0.515938 | 0.620919 | 0.515938 |
| 401 / disruption | packing | RF Physics | 71 | 0.222208 | 0.281487 | -3.582394 | 0.221338 | 0.525720 | 0.686004 | 0.525720 |
| 401 / disruption | quality_control | Grouped Mean | 72 | 0.115893 | 0.153530 | -0.137424 | 0.058405 | 0.298475 | 0.540005 | 0.298475 |
| 401 / disruption | quality_control | Forest12 | 72 | 0.125970 | 0.181817 | -0.595167 | 0.110680 | 0.356446 | 0.648806 | 0.356446 |
| 401 / disruption | quality_control | Hist31 | 72 | 0.139733 | 0.199426 | -0.919111 | 0.128071 | 0.386261 | 0.750126 | 0.386261 |
| 401 / disruption | quality_control | RF Physics | 72 | 0.131320 | 0.195247 | -0.839534 | 0.114704 | 0.382796 | 0.744671 | 0.382796 |
| 401 / disruption | sewing | Grouped Mean | 71 | 0.131432 | 0.168541 | -0.259880 | 0.107976 | 0.339897 | 0.355728 | 0.339897 |
| 401 / disruption | sewing | Forest12 | 71 | 0.138337 | 0.174770 | -0.354737 | 0.134356 | 0.322302 | 0.360461 | 0.322302 |
| 401 / disruption | sewing | Hist31 | 71 | 0.135034 | 0.164654 | -0.202434 | 0.130408 | 0.303444 | 0.371066 | 0.303444 |
| 401 / disruption | sewing | RF Physics | 71 | 0.143119 | 0.182255 | -0.473257 | 0.140277 | 0.340589 | 0.413483 | 0.340589 |

### Support coverage, abstentions and physical-envelope diagnostics

All four frozen models have identical support status counts in these cases.
Coverage means non-abstention; REVIEW_REQUIRED is still covered. Its 34 exposures
are 17 per condition in world 401, caused by the original standard-worker-minute
feature bounds. All 26 abstentions are input zero-capacity exclusions. There are
**zero output-added abstentions** and **zero defined-target abstentions**.

| Population, all worlds and both conditions | Denominator | SUPPORTED_EXPERIMENTAL | REVIEW_REQUIRED | ABSTAIN | Non-abstained coverage | Abstention rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| All planned, each model | 2,880 | 2,820 | 34 | 26 | 99.097222% | 0.902778% |
| Defined targets, each model | 2,854 | 2,820 | 34 | 0 | 100% | 0% |

| Seed (each condition) | Planned | Defined | Supported | Review | Input abstentions | Defined coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 101 | 360 | 357 | 357 | 0 | 3 | 100% |
| 211 | 360 | 355 | 355 | 0 | 5 | 100% |
| 307 | 360 | 357 | 357 | 0 | 3 | 100% |
| 401 | 360 | 358 | 341 | 17 | 2 | 100% |

The common non-abstained comparison equals the scientific defined-target
population here; it does not conceal a dropped difficult subpopulation. Marginal
support cannot detect hidden disruption: both arms have identical inputs, outputs
and support decisions despite their different labels and large positive bias.

Finite predictions above offered-work ceilings remain unclipped and are reported
without adding a new abstention rule. Counts below include both identical-input arms.

| Model | Raw minimum | Raw maximum | Above offered-work ceiling |
| --- | ---: | ---: | ---: |
| Grouped Mean | 0.475788 | 1.030618 | 604 |
| Forest12 | 0.385654 | 1.474161 | 596 |
| Hist31 | 0.387944 | 1.368930 | 582 |
| RF Physics | 0.355857 | 1.543404 | 120 |

No model output was nonfinite, below zero or above three. Values above one
remain valid under the fixed contract; no clipping or new calibration was applied.

### Every acceptance guard

Validity checks passed: independent ledger/source/model receipts, source joins and
provenance, partition access guards, complete pre-label prediction sealing, matched
input/prediction vectors, finite outputs, exact A/B reproduction, zero fits/tuning/
calibration and unchanged protocol/budgets. Neither INVALID_EVALUATION nor
INCONCLUSIVE applies. The negative decision follows numerical guards below.

All **48/48** minimum checks passed (eight case checks plus 40 case-stage checks).
Minimum actual case targets 355 ≥ 300; stage targets 70 ≥ 50; case/stage dates
18 ≥ 15; stage lines 2 ≥ 2 and crews 4 ≥ 4. Each check and all actual counts
are retained in the aggregate record; the tables above expose every stage denominator.

All **77** numerical checks are listed below: 46 PASS, **31 FAIL**. Percentage
values for case/stage/tail/disruption guards are RF Physics regression versus
Grouped Mean (baseline world_forest uses Forest12); negative values mean improvement.
The two macro gain checks instead report positive gain. Bounds are exactly frozen.

| Guard | Observed | Frozen requirement | Result |
| --- | ---: | --- | --- |
| baseline_macro_gain_forest | 4.791651% gain | ≥ 2% vs Forest12 | PASS |
| baseline_macro_gain_group | 12.217182% gain | ≥ 5% vs Grouped Mean | PASS |
| baseline_world_wins | 3 | ≥ 3 of 4 baseline worlds | PASS |
| disruption_macro | -6.741679% | Regression ≤ 0% vs Grouped Mean | PASS |
| disruption_seed / 101-disruption | -8.766383% | Regression ≤ 10% vs Grouped Mean | PASS |
| disruption_seed / 211-disruption | -13.359089% | Regression ≤ 10% vs Grouped Mean | PASS |
| disruption_seed / 307-disruption | +1.440597% | Regression ≤ 10% vs Grouped Mean | PASS |
| disruption_seed / 401-disruption | -6.492176% | Regression ≤ 10% vs Grouped Mean | PASS |
| p95_absolute_error / 101-baseline | +20.705989% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_absolute_error / 101-disruption | +11.576304% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_absolute_error / 211-baseline | +18.070104% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_absolute_error / 211-disruption | +14.082988% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_absolute_error / 307-baseline | +23.754118% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_absolute_error / 307-disruption | +19.095842% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_absolute_error / 401-baseline | -6.385467% | Regression ≤ 5% vs Grouped Mean | PASS |
| p95_absolute_error / 401-disruption | -10.778100% | Regression ≤ 5% vs Grouped Mean | PASS |
| p95_positive_error / 101-baseline | +15.012230% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_positive_error / 101-disruption | +11.576304% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_positive_error / 211-baseline | +19.452613% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_positive_error / 211-disruption | +14.082988% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_positive_error / 307-baseline | +37.417329% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_positive_error / 307-disruption | +19.095842% | Regression ≤ 5% vs Grouped Mean | FAIL |
| p95_positive_error / 401-baseline | -19.608482% | Regression ≤ 5% vs Grouped Mean | PASS |
| p95_positive_error / 401-disruption | -10.778100% | Regression ≤ 5% vs Grouped Mean | PASS |
| primary_world_interval | +0.000273278 | Upper < 0 | FAIL |
| stage / 101-baseline / cutting | -38.837270% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 101-baseline / finishing | -4.187619% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 101-baseline / packing | -22.909034% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 101-baseline / quality_control | +11.651087% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 101-baseline / sewing | -12.985758% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 101-disruption / cutting | -2.170465% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 101-disruption / finishing | -25.333475% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 101-disruption / packing | -39.469714% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 101-disruption / quality_control | +15.705782% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 101-disruption / sewing | -1.916852% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 211-baseline / cutting | +5.927854% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 211-baseline / finishing | +18.390693% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 211-baseline / packing | +51.017316% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 211-baseline / quality_control | -46.286312% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 211-baseline / sewing | -37.704275% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 211-disruption / cutting | -23.709101% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 211-disruption / finishing | -49.638111% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 211-disruption / packing | +25.177399% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 211-disruption / quality_control | -8.538969% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 211-disruption / sewing | -17.199568% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 307-baseline / cutting | -2.886618% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 307-baseline / finishing | -40.613889% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 307-baseline / packing | +18.215225% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 307-baseline / quality_control | +19.895490% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 307-baseline / sewing | -26.442439% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 307-disruption / cutting | -17.021464% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 307-disruption / finishing | -10.482174% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 307-disruption / packing | +7.153570% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 307-disruption / quality_control | +9.271581% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 307-disruption / sewing | +6.549688% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 401-baseline / cutting | -32.839260% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 401-baseline / finishing | -19.332454% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 401-baseline / packing | -22.344887% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 401-baseline / quality_control | -35.777361% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 401-baseline / sewing | -27.472605% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 401-disruption / cutting | +5.612057% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 401-disruption / finishing | -19.070397% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 401-disruption / packing | -18.586052% | Regression ≤ 5% vs Grouped Mean | PASS |
| stage / 401-disruption / quality_control | +13.311370% | Regression ≤ 5% vs Grouped Mean | FAIL |
| stage / 401-disruption / sewing | +8.892318% | Regression ≤ 5% vs Grouped Mean | FAIL |
| world_forest / 101-baseline | -2.257418% | Regression ≤ 5% vs Forest12 | PASS |
| world_forest / 211-baseline | +0.921875% | Regression ≤ 5% vs Forest12 | PASS |
| world_forest / 307-baseline | -0.642900% | Regression ≤ 5% vs Forest12 | PASS |
| world_forest / 401-baseline | -17.169487% | Regression ≤ 5% vs Forest12 | PASS |
| worst_absolute_error / 101-baseline | -9.477853% | Regression ≤ 10% vs Grouped Mean | PASS |
| worst_absolute_error / 101-disruption | -9.293799% | Regression ≤ 10% vs Grouped Mean | PASS |
| worst_absolute_error / 211-baseline | +95.343222% | Regression ≤ 10% vs Grouped Mean | FAIL |
| worst_absolute_error / 211-disruption | +75.052776% | Regression ≤ 10% vs Grouped Mean | FAIL |
| worst_absolute_error / 307-baseline | +37.726332% | Regression ≤ 10% vs Grouped Mean | FAIL |
| worst_absolute_error / 307-disruption | +42.144719% | Regression ≤ 10% vs Grouped Mean | FAIL |
| worst_absolute_error / 401-baseline | -0.041815% | Regression ≤ 10% vs Grouped Mean | PASS |
| worst_absolute_error / 401-disruption | +2.960916% | Regression ≤ 10% vs Grouped Mean | PASS |

Failures comprise **14/40 stage guards**, **6/8 P95 absolute**,
**6/8 P95 positive**, **4/8 worst-error guards**, and the **primary interval**.
For example, baseline packing in world 211 regresses 51.017316% against Grouped
Mean; that world's worst baseline error regresses 95.343222%. Pooled MAE gains
cannot override these predeclared case-level failures. Failure is lack of support
for this complete replication claim, not proof that one model is universally inferior.

### Integrity, reproduction and actual resources

| Receipt | SHA-256 |
| --- | --- |
| Independent source ledger | `cb0acaa9513c06769d88272ec53bc22890603122751956352630f417556eb2a9` |
| Completed run A manifest | `5f317667fbdaaa4fa03fe4c836f578e0965217837436b4a50546ffd9eaa834ba` |
| Completed run B manifest | `704a49c3f933ba16452218b6e49bc63c15cfd169e06439e6a52ef6edb8775b9d` |

All five deterministic payloads are byte-identical; completion manifests differ
by their declared original/reproduction state and original-manifest binding.

| Payload, identical in A/B | Bytes | SHA-256 |
| --- | ---: | --- |
| attempt.json | 1,732 | `7e05c71e5267de06fe7e1d3db012dc79edef384f35764ef36431f4e33772ac9a` |
| errors.jsonl | 991,771 | `ed39366c68c4cd0b7d5e340493ac49558b379f92a5693141703d3fbffdd75b92` |
| predictions.jsonl | 4,573,748 | `f717c6df66bfc812d15ddcdb642bf047c6f28523a6ae75aed67e8f00b5ef403d` |
| predictions.receipt.json | 2,800 | `49f7521b637e2bbfe73b5eeb42fc1af9ad49bcbc07eb8cd3c8a88b421f558a11` |
| report.json | 1,298,778 | `ed7abf724f232090e8d1dc4251ea45e7986ba9737c8e79f7ecc69d85a265595d` |

The independent verifier also revalidated current code/environment, both frozen
model bundles, all source receipts and both closed output sets. It never inferred
a new trust root from the files it was checking. Reserved labels remained opaque.

| Operation | Whole child seconds | Peak aggregate committed bytes | Peak MiB |
| --- | ---: | ---: | ---: |
| run-a | 50.211693 | 308,555,776 | 294.262 |
| run-b | 51.567885 | 310,964,224 | 296.559 |
| verify-reproduction | 17.890956 | 130,633,728 | 124.582 |

A and B each used one numeric thread, 32 raw predict calls and 11,416 predictions;
limits stayed 2,048 MiB and 1,200 seconds per full run. Exactly two full runs
were executed. No deadline reset, budget increase, fit/tuning/calibration, clipping,
sample extension, source regeneration, retry or model replacement occurred.
The complete ignored root is 58,224,807 bytes (limit 768 MiB); the largest file is
4,573,748 bytes (32 MiB limit), and the largest dataset bundle is 5,559,847 bytes
(64 MiB limit). Native telemetry is committed separately in the
[execution record](EXP-009-execution-record.json) and excluded from deterministic receipts.

### Evidence and reproducibility

The [canonical aggregate record](EXP-009-results.json) intentionally versions
complete per-world and per-stage metrics/counts, support/reason/abstention summaries,
raw-output summaries, worst IDs, all paired model/condition comparisons, bootstrap
and sensitivity intervals/digests, all guards, environment/code/model pins and
completed-run receipts. It is a projection of the receipt-verified report, without
raw labels, datasets or prediction vectors. Full remaining subgroup diagnostics
stay in ignored receipt-bound reports. Source receipt metadata was pushed before scoring.

The [execution record](EXP-009-execution-record.json) separately retains actual
UTC start/finish times, native measurements, package versions, six operation
responses and request/response journal hashes. Execution telemetry is not expected
byte-identical across separate executions and was never included in the comparison.

The locked environment is Python 3.13.14 on Windows-11-10.0.26300-SP0.
Package versions: joblib 1.6.0, loometric 0.1.0, numpy 2.5.5, pandas 3.1.1, scikit-learn 1.9.1, scipy 1.18.1, threadpoolctl 3.8.0.

The executed sequence was `prepare_sources(generation_authorized=True)` once,
`register_sources(producer_returned_receipts)` once, `verify_sources(retained_ledger)`
once, `evaluate_frozen_models(retained_ledger, evaluation_authorized=True)` once,
one B call with the retained A manifest, and independent `verify_frozen_reproduction`.
All requests used the committed [engine entry points](../architecture/prospective-frozen-evaluation-engine.md#future-authorized-local-use).

Existing outputs must not be deleted or overwritten to rerun this experiment.
To audit this completed local execution without generating data, predicting or
accessing label values, use the independently committed receipt records:

```python
import json
from pathlib import Path

from loometric.prospective_evaluation.evaluation_service import verify_frozen_reproduction
from loometric.prospective_evaluation.service import verify_sources

sources = json.loads(Path("docs/experiments/EXP-009-source-receipts.json").read_text())
results = json.loads(Path("docs/experiments/EXP-009-results.json").read_text())
verify_sources(sources["ledger_sha256"])
verify_frozen_reproduction(
    sources["ledger_sha256"],
    results["reproduction"]["a_manifest_sha256"],
    results["reproduction"]["b_manifest_sha256"],
)
```

A clean-clone reproduction requires the same trusted frozen artifacts and locked
environment plus separate authorization for a fresh audit; the pinned receipts,
parameters, seeds, original implementation and operation sequence above make
that procedure reviewable. No current run or dataset is to be retried or extended.

### Post-execution regression and evidence verification

With the actual datasets and both completed runs present, the selected permanent
regression suite passed again: **263 passed in 239.04s**, no skips. The private
fixtures' metadata snapshots verified actual outputs were not modified. These
were implementation regressions, not another actual evaluation run.

Final Ruff lint/format passed (323 files), dependency and Git whitespace checks
passed, and all source/artifact hashes were rechecked. The 60 frozen source pins,
both model bundles/six files, ten historical manifests/170 opaque file identities,
eight actual manifests/136 opaque file identities and both closed result sets match.
All M10A.3 engine files and shared execution code remain unchanged.

All 8 displayed macro rows, 32 world/model rows, 160 stage/model rows and 77 guard
rows were checked against the receipt-verified report. The canonical aggregate
projection matches the original acceptance/comparison/sensitivity/support sections.
Documentation links/anchors and fences were checked; 450 tracked/proposed files
passed generated-dataset/model/build-artifact and credential-pattern checks.
Source receipt commit time was verified to precede A's actual start time.

### Interpretation, limitations and next research decision

These were fresh synthetic validation worlds when generation/scoring began, with
protocol, models and thresholds committed before exposure. They provide prospective
frozen-transfer evidence under the same simulator law, separate from EXP-008's
**24.05% MAE improvement / 0.82067 R² on spent historical benchmark validation**.
The new 4.791651% baseline MAE gain is much smaller and fails the joint declaration.
These inspected EXP-009 validation outcomes are now spent for future adaptive
development. B repeats the same observations and is not a second independent sample.

Four seeds are only four simulator-world clusters. Bootstrap intervals are coarse
descriptive resampling summaries; repeated entities cross dates, so date sensitivity
is conditional and cannot establish independent-crew or factory uncertainty.
The synthetic 2032 calendar is hypothetical; temporal separation is a provenance
guarantee, not evidence of real future factory performance or an evolving process law.

The target is demand-censored standard-capacity attainment, not employee efficiency
or guaranteed output. Hidden disruption has no new pre-shift signal, leaving large
positive bias, negative R² and no support-policy detection. Stage/tail regressions
and above-offered-work predictions remain. No calibrated candidate prediction band
or externally validated factory accuracy/coverage is established.

No model is promoted or replaced; no API/serving/planning behavior changes.
A future research stage may propose a new predeclared hypothesis and genuinely
available pre-shift signals, with fresh evaluation evidence. It must not tune
against these outcomes and present them as independent validation.
**NO_ML_PROMOTION remains unconditional.**
