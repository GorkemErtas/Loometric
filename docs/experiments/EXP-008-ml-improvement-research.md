# EXP-008: ML error diagnosis and controlled improvement research

Executed 2026-11-23. **RESEARCH_CANDIDATE: rf_physics. NO_ML_PROMOTION remains unchanged.**
No serving artifact/registry, original data/generator, EXP-006/007, final test or
planning engine was changed. This is evidence about an assumed synthetic process,
not real-factory accuracy or productivity improvement.

## Declaration, evidence role and source identities

The [declaration](../../configs/ml_improvement_v1.json) and
[ADR0022](../decisions/0022-development-only-ml-improvement-research.md) were committed
and pushed as `af1e8bf26af62e940ddf9156512aeffe382c433f` before actual comparisons.
The verified runtime was committed/pushed as
`812cdf7845a1592f632d5410f3b7aeee780707c0` before the first actual run.
Canonical protocol SHA-256:
`475da83d18ca820618520a6acfea1c6f2c6b799843f9d316ddc9b73e2d8d7591`.
Original study configuration SHA:
`40b75e3a5854679f990cb1c6647302752ede45ed33773787172179d85c181c52`.
The independently retained corrected EXP-006 artifact receipt is
`cd19c78c8321ac1bb69dc16d61dc7de01469e35f0d35afe3a3d8c8dca4e8b7b4`.

The [original source declaration](../../configs/synthetic_training_v1.json) binds
all ten retained synthetic-ml-v1 source receipts. Four baseline worlds are fitted
separately; six paired development stress worlds reuse their baseline models.
No pooling, new actual dataset generation or reserved/gap/global-outcome decoding
occurs. Only authorized train/validation labels are parsed; other values remain
opaque integrity-checked bytes. Zero-capacity targets retain their original
audited exclusion identities/reasons, without imputation.

| Baseline source | Train eligible / undefined | Validation eligible / undefined | Source manifest |
| --- | --- | --- | --- |
| benchmark-42-baseline | 14711 / 169 | 4833 / 47 | `7e7dae049270675c2eac4f8ad05d55a9ac84cc9c1160e0a6b7e9f4010a64f7eb` |
| development-19-baseline | 537 / 3 | 180 / 0 | `64330160688ce4c089a22a320cb604e587eed4204d4a43493117f7bd2855f359` |
| development-42-baseline | 532 / 8 | 178 / 2 | `e6af2f894ef3d9edf1c6cee75603f52cd26bc66a55fcaa9d8178056e49b17b3e` |
| development-73-baseline | 535 / 5 | 179 / 1 | `713cf810b17a7d9e37889ea1d086d5892eacc0f58bfcbb574adc4564656e959b` |

There are 16,315 eligible original-training observations across four separately
fitted worlds, 5,370 baseline validation exposures and 6,444 validation/scenario
exposures including paired repeats. These are not pooled independent samples.
Development training/validation dates remain 2030-01-07–02-06 /02-08–02-18;
benchmark training/validation dates remain 2030-01-07–08-10 /08-13–10-22.

The target is completed good pieces × standard worker-minutes/piece divided by
frozen planned available worker-minutes. It is dimensionless, demand-censored
attainment, not intrinsic efficiency or guaranteed output. Values above one remain
valid. All errors below use that ratio's units; bias is prediction minus actual.

Original validation was already repeatedly inspected. It is **spent diagnostic
evidence**, not a fresh holdout or candidate-selection input. New research folds
reuse original training data that M08B also studied. Per-seed refitting tests an
approach within multiple synthetic worlds, not transport of one fitted artifact
to a new factory/world. Shared simulator law and overlapping profile mechanisms
do not make these independent real factories.

## Root causes and matched historical failures

All historical Grouped Mean/Forest12/Hist31 predictions and metrics reproduce
exactly on matched original validation IDs. Source context is joined only for
diagnosis, never as a predictor. The original packing failure has 36 rows but only
nine start dates, two lines, four crews and two factories. It cannot be treated as
36 independent crews. Its original raw-forest excess MAE is 0.044581985; the
500-date-cluster descriptive resampling interval is[0.007693170,0.079987224].
This indicates sensitivity within that particular observed world; persistent
crew effects across dates prevent an independent-factory confidence claim.

Raw-forest packing regressions relative to Grouped Mean are +51.8408% for seed 19,
but improvements of 18.4866% and 33.7010% for seeds 42/73. There is no evidence for a
universal intrinsic packing defect. Ratio representation and small repeated
contexts matter. Under surge, seed 19 packing excess MAE is 0.033858326 with
date-resampling interval[0.014057603,0.053863957].

Seed 73 disruption cutting has 35 rows/nine dates. Raw-forest excess MAE 0.028399253
has interval[-0.026188203,0.067311048], spanning zero. That stage regression is
not distinguished confidently from date variability. Systematic disruption
overprediction across the full matched worlds is a separate, stronger finding.

| Diagnostic cell | n | Grouped MAE | Raw RF MAE | Raw Hist MAE | Research RF MAE |
| --- | --- | --- | --- | --- | --- |
| development-19-baseline / packing | 36 | 0.085998 | 0.130580 | 0.113799 | 0.039313 |
| development-19-workload_surge / packing | 36 | 0.085298 | 0.119156 | 0.113275 | 0.065322 |
| development-73-disruption / cutting | 35 | 0.191013 | 0.219412 | 0.191626 | 0.213382 |

The generator imposes hidden persistent line/crew effects, shared shift effects,
unplanned losses/absence/noise and a declared rare difficult condition. It has no
direct universal packing-rate multiplier. Individual difficult-event flags were
not observed: reading the global outcome table would decode reserved values.
Large residuals cannot identify which unobserved mechanism caused them.

Baseline/disruption inputs and all three frozen predictions are identical for
all 537 development validation observations. The conditional target changes are:

| Paired seed | n | Mean absolute target change | Balanced empirical MAE lower bound | Balanced empirical RMSE lower bound |
| --- | --- | --- | --- | --- |
| 19 | 180 | 0.198543 | 0.099272 | 0.119460 |
| 42 | 178 | 0.194429 | 0.097215 | 0.118237 |
| 73 | 179 | 0.193782 | 0.096891 | 0.119007 |

For each identical-input pair, a single prediction's balanced mean absolute
error is at least half the target difference. These bounds apply to this paired
sample/equal mixture, not a universal Bayes error or an estimated factory shock
frequency. More rows or hyperparameters cannot reveal a missing scenario signal.

Across all 16,315 eligible training rows, machine availability is constantly true,
opening WIP+planned release=order quantity and available minutes+planned downtime
=450 exactly. These are structural v1 identities, not evidence that the fields
are unimportant in factories. 6,975 training labels are demand-censored; workload
strongly caps attained output. Standards and complexity are also correlated by
the declared generator. Opening stock/release split is randomized and does not
separately govern arrival timing/material feasibility. V1 is independent stage
orders, not an end-to-end material-flow simulation.

## Permutation importance, impurity and controlled ablation

Raw-tree permutation probes use only each held-out original-training fold,
three deterministic within-date shuffles and up to 1000 IDs selected without
labels. Both models use exactly the same probe IDs/permutations. The summary
below averages folds within each world, then uses half the three-development-world
mean and half benchmark. It is model-specific predictive sensitivity, not causal
importance. Existing M08C MDI is the actual full-benchmark forest's impurity
importance, read through its independently verified manifest without unpickling;
its scale/data differ from held-out PFI and are not directly interchangeable.

| Input / block | Existing RF MDI % | RF PFI delta MAE | Hist PFI delta MAE |
| --- | --- | --- | --- |
| joint_demand | block | 0.137667 | 0.158429 |
| order_quantity | 37.340 | 0.128990 | 0.137623 |
| joint_capacity | block | 0.060371 | 0.071677 |
| planned_workers | 20.089 | 0.059109 | 0.070565 |
| standard_worker_minutes_per_piece | 18.139 | 0.044094 | 0.054877 |
| skill_level | 10.169 | 0.031333 | 0.029533 |
| stage | 5.684 | 0.016064 | 0.014001 |
| shift_kind | 2.553 | 0.005470 | 0.004075 |
| planned_release_pieces | 1.444 | 0.002049 | 0.004751 |
| opening_wip_pieces | 1.440 | 0.001814 | 0.005095 |
| style_complexity | 0.476 | 0.000356 | 0.000186 |
| available_minutes | 0.989 | 0.000043 | 0.001004 |
| planned_downtime_minutes | 0.970 | 0.000030 | 0.000006 |
| planned_machine_available | 0.000 | 0.000000 | 0.000000 |
| weekday | 0.708 | 0.000000 | 0.000000 |

Weekday never changes within a date block: its zero PFI is **unidentifiable**,
not proof of irrelevance. The v1 mechanism declares no annual/weekday response
law; clock ablation jointly removes shift and weekday and cannot isolate either.
Machine availability is constant after undefined-target exclusions. Marginal
WIP/release/quantity permutations violate stock identities on roughly 94–95% of
probe rows; available-time permutation violates the tested time identity on
roughly 94%. Coherent demand/capacity blocks have zero violations of those tested
identities, without proving complete joint entity/process support. Marginal
importance must not be described as a feasible operational intervention.

Controlled ablations keep identical training/evaluation rows and tree settings,
omitting columns from preprocessing instead of imputing values. They are not
selectable candidates. Negative percentage means lower MAE after removal:

| Raw model / removed block | Reference macro MAE | Ablated macro MAE | Change |
| --- | --- | --- | --- |
| forest-12/omit_clock | 0.100285 | 0.102118 | 1.8275% |
| forest-12/omit_planned_downtime | 0.100285 | 0.100284 | -0.0015% |
| forest-12/omit_stock_split | 0.100285 | 0.097177 | -3.0997% |
| hist-31/omit_clock | 0.098563 | 0.099891 | 1.3480% |
| hist-31/omit_planned_downtime | 0.098563 | 0.098564 | 0.0015% |
| hist-31/omit_stock_split | 0.098563 | 0.096834 | -1.7538% |

Removing stock split improves every world: forest improvements 1.49–8.47%,
histogram 0.97–4.16%. These variables are redundant/noisy proxies in v1, although
marginal perturbation can appear useful. Removing downtime changes macro error
by only about 0.0015%, consistent with redundancy through available minutes.
Clock removal hurts benchmark 3.48–4.90% but is mixed across small development
worlds. Skill/standard/quantity/staffing are more stable predictive signals.
These findings motivate a future prespecified pruning test; no declared candidate
was changed after seeing ablation results. See the primary methodological
[permutation guidance](https://scikit-learn.org/stable/modules/permutation_importance.html)
and [correlated-feature example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html).

## Candidate protocol and sealed selection

Three new expanding original-training date windows evaluate[2/5,3/5),[3/5,4/5),
[4/5,1), purge the preceding observed date and require global label maturity.
Evaluation observations are disjoint. Fit counts include internal baseline/stage
fits, with a maximum 300,20,000 rows/fit, one thread, seed 42 and no early stopping.
Clock/downtime/stock ablations use both raw models only. No tuning/selection uses
outer validation. All fixed settings and eleven planned derived feature definitions
are in the committed declaration, artifact report and
[architecture](../architecture/ml-improvement-research.md).

| World | R01 train/evaluate | R02 train/evaluate | R03 train/evaluate |
| --- | --- | --- | --- |
| benchmark-42-baseline | 5780 / 2926 | 8706 / 2922 | 11628 / 3003 |
| development-19-baseline | 179 / 120 | 299 / 98 | 399 / 120 |
| development-42-baseline | 178 / 118 | 296 / 97 | 393 / 119 |
| development-73-baseline | 180 / 118 | 298 / 98 | 397 / 119 |

There are 9,858 matched OOF exposures across four separately fitted worlds,
88,722 OOF prediction records for nine models and 57,996 spent diagnostic records.
The macro score gives half weight to mean development worlds and half benchmark.
No pooled R² is implied by that engineering weighting.

| Model | Training OOF macro MAE | Benchmark OOF MAE | Benchmark OOF RMSE | Benchmark OOF R² |
| --- | --- | --- | --- | --- |
| forest-12 | 0.100285 | 0.083715 | 0.119917 | 0.733490 |
| grouped_mean | 0.143712 | 0.120954 | 0.159197 | 0.530299 |
| hist-31 | 0.098563 | 0.086623 | 0.121896 | 0.724619 |
| hist_physics | 0.066708 | 0.062256 | 0.104128 | 0.799048 |
| hist_physics_regularized | 0.069276 | 0.067724 | 0.110034 | 0.775608 |
| hist_residual | 0.080049 | 0.073256 | 0.113711 | 0.760362 |
| hist_stage_shrunk | 0.065649 | 0.060470 | 0.102160 | 0.806575 |
| rf_physics | 0.062227 | 0.061363 | 0.104213 | 0.798721 |
| rf_physics_regularized | 0.074740 | 0.069080 | 0.113446 | 0.761478 |

All six improved candidates pass the predeclared research designation guards
on these training folds. `rf_physics` wins with macro MAE 0.062226692,
36.8660% lower than strongest raw Hist31 and 56.7004% lower than Grouped Mean.
It wins 3/3 temporal folds in every world; its least favorable stage cell still
improves 40.9252% against Grouped Mean on pooled training OOF. Its worst-error
regression is 0.7728%, below the unchanged research 10% threshold.
Its advantage over the next candidate exceeds the predeclared 1% simplicity band.

Selection was sealed before any outer diagnostic as
`d1302e12c71d3d7adea55676977e405cb9dbc28e6c635f9a69cad6d5a6017a2b`.
The selected architecture uses the exact Forest12 tree settings and stateless
planned ratio/capacity/interactions. Its gains do not require a replacement dataset.
This control changes an eleven-feature bundle; it does not isolate the benefit
of planned load alone or establish a causal effect of any derived feature.
Regularization, residual modeling and partial pooling do not beat it on the
declared macro rule. Stage-specific models fit only in sufficiently supported
benchmark prefixes; small development worlds use the global fallback.

## Spent validation and stress diagnostics, after selection

These are diagnostic reuses of already-inspected validation, not fresh accuracy
confirmation. The benchmark has 4,833 defined-label rows:

| Model | MAE | RMSE | R² | Bias | P95 positive error | Worst absolute error |
| --- | --- | --- | --- | --- | --- | --- |
| forest-12 | 0.076277 | 0.111613 | 0.773725 | 0.000055 | 0.176480 | 0.901035 |
| grouped_mean | 0.122346 | 0.161097 | 0.528606 | 0.001345 | 0.256437 | 0.918865 |
| hist-31 | 0.084485 | 0.119294 | 0.741510 | -0.000530 | 0.193253 | 0.917217 |
| hist_physics | 0.059499 | 0.100510 | 0.816503 | 0.000499 | 0.160441 | 1.117878 |
| hist_physics_regularized | 0.065706 | 0.107074 | 0.791755 | 0.000274 | 0.175974 | 1.100748 |
| hist_residual | 0.071517 | 0.110868 | 0.776736 | 0.000196 | 0.182119 | 1.071220 |
| hist_stage_shrunk | 0.057310 | 0.097755 | 0.826427 | 0.001016 | 0.155655 | 1.049645 |
| rf_physics | 0.057931 | 0.099363 | 0.820669 | -0.000422 | 0.159712 | 1.071964 |
| rf_physics_regularized | 0.068065 | 0.111453 | 0.774373 | -0.000538 | 0.183595 | 1.066552 |

The selected candidate reduces spent benchmark MAE about 24.05% versus the raw
forest. Partially pooled histogram has a slightly lower benchmark MAE but was
not selected by the predeclared multi-world training rule; it is not substituted
after inspecting these validation numbers.

| Case | n | Grouped MAE | Raw RF MAE | Raw Hist MAE | Research RF MAE | Research RF bias |
| --- | --- | --- | --- | --- | --- | --- |
| benchmark-42-baseline | 4833 | 0.122346 | 0.076277 | 0.084485 | 0.057931 | -0.000422 |
| development-19-baseline | 180 | 0.119761 | 0.099885 | 0.098261 | 0.054300 | -0.005944 |
| development-19-disruption | 180 | 0.218462 | 0.197587 | 0.197269 | 0.196245 | 0.192599 |
| development-19-workload_surge | 180 | 0.126361 | 0.109564 | 0.107587 | 0.079662 | -0.018855 |
| development-42-baseline | 178 | 0.143584 | 0.101733 | 0.096871 | 0.057220 | -0.008727 |
| development-42-disruption | 178 | 0.234598 | 0.190620 | 0.196584 | 0.187515 | 0.185703 |
| development-42-workload_surge | 178 | 0.131884 | 0.101859 | 0.100785 | 0.075725 | -0.002824 |
| development-73-baseline | 179 | 0.150780 | 0.108102 | 0.101793 | 0.052053 | 0.001248 |
| development-73-disruption | 179 | 0.227985 | 0.196372 | 0.189635 | 0.197574 | 0.195030 |
| development-73-workload_surge | 179 | 0.146153 | 0.097282 | 0.094463 | 0.064781 | 0.003032 |

Research RF's macro spent-validation gain versus Grouped Mean is 56.8123%;
disruption/surge mean MAE improvements are 14.6408%/45.5566%. These aggregate
gains do not remove failures. Cutting under seed 73 disruption is 11.7107% worse
than Grouped Mean (0.213381948 vs 0.191012969, n 35). The largest worst-error
regression is 18.2478% in seed 42 surge, and benchmark worst error increases 16.6618%
from 0.918864545 to 1.071964275. All six improved candidates fail stage and worst-
error numerical checks on the spent diagnostics. Original EXP-006 gates, metrics
and NO_ML_PROMOTION remain unchanged; no operational/model-serving upgrade occurs.

The candidate's disruption bias remains +0.1857–0.1950. Stronger baseline point
predictions cannot identify hidden shifts with unchanged inputs. Physical offered-
work ceiling violations fall from 1,086 raw-forest predictions to 205 research-
forest predictions on benchmark, but remain nonzero. No post-hoc clipping is used
to conceal them. This motivates a separately declared censoring-aware model test.

## Risk and uncertainty

Feature-only joint support uses training stage×shift×staffing×load cells, count < 20;
also flag load outside training range and high load > 1.5. Sparse joint support
flags 174/180,128/178 and 135/179 baseline development rows, but none of 4,833
benchmark rows. It can overflag small worlds and cannot distinguish disruption:
all baseline/disruption feature flags are identical. Surge load extrapolation is
identified on 55/180,66/178 and 65/179 rows. Support is a diagnostic, not readiness.

Descriptive stage/load P90 residual bands use new training OOF errors, minimum 30
then stage/global fallback. Their folds were reused for selection; no calibration
or confidence guarantee is claimed. Comparison with stage-only OOF radii:

| Case | Conditional coverage | Conditional width | Stage-only coverage | Stage-only width |
| --- | --- | --- | --- | --- |
| benchmark-42-baseline | 90.85% | 0.268250 | 91.10% | 0.308035 |
| development-19-baseline | 96.67% | 0.359963 | 92.78% | 0.308578 |
| development-19-disruption | 41.67% | 0.359963 | 36.67% | 0.308578 |
| development-19-workload_surge | 92.22% | 0.394012 | 85.00% | 0.308578 |
| development-42-baseline | 93.26% | 0.301629 | 90.45% | 0.279575 |
| development-42-disruption | 39.89% | 0.301629 | 38.76% | 0.279575 |
| development-42-workload_surge | 90.45% | 0.311859 | 84.27% | 0.279575 |
| development-73-baseline | 93.85% | 0.346383 | 89.94% | 0.311071 |
| development-73-disruption | 40.22% | 0.346383 | 36.87% | 0.311071 |
| development-73-workload_surge | 93.30% | 0.361339 | 89.94% | 0.311071 |

Conditional bands narrow benchmark mean width while retaining similar empirical
coverage, but disruption coverage falls to 39.89–41.67%. Sharper point forecasts
and narrower residual bands do not confer shift robustness. Full flagged/unflagged
MAE, bias, tails/counts, including empty slices, remain in the artifact report.

## Dataset decision and next experiment

A separately versioned v2 design is justified **for observability and independent
entity-diversity research**, not as a prerequisite for the representation gains
above or as arbitrary row inflation. The [concrete proposal](../architecture/synthetic-ml-v2-proposal.md)
defines timestamped noisy pre-shift forecasts, mature history, cold starts,
signal/no-signal controls and independent-profile learning curves. It preserves
an unannounced-shock arm and demands explicit causal/physical assumptions rather
than manufacturing a useful target dependence for a weak predictor. No v2 data,
generator, schema migration or serving replacement is generated here.

Recommended next experiment: prospectively evaluate the frozen research candidate
against Grouped Mean/raw trees on new development-only seeds and entity profiles,
with a separate calibration period. Predeclare any stock-pruning/censoring-aware
variant; do not retune against these spent validation sets or consume v1 final
tests. Only then test v2 noisy-observable signals against matched no-signal arms.

## Reproduction, artifacts and executed verification

Outputs are create-only ignored `data/processed/ml_research/exp-008-a` and
`exp-008-b`. The benchmark research artifact fits only the original 14,711 training
labels. Manifest hashes bind environment/config/code, all reports/predictions,
selection seal and the non-serving model. Timing/memory is separate.

| Receipt/file | SHA-256 |
| --- | --- |
| manifest.json | `d2fe121d592a5934753c555815a255620d0010838dc90957af5e3e73319a9cdb` |
| ablations.json | `86e0b1dde5478c25d54bd1490c03130f61ae29653e8775104f970bc263bfc325` |
| historical-diagnosis.json | `2ba6a090131b6a3b26cde2270d3f5d0e638cde75dbbb3f3415761c2fc88ecaa7` |
| permutation-importance.json | `3cd81e430789f85e912fccd1caf81e6c977113500c8dcb066c97f95448c37678` |
| report.json | `dcbd0bfa0bfd4ede558e874dba56d1524e476e6c996546ffeab158e2ee592d44` |
| research-model.joblib | `4f64df4485927c1fdc6eb4bd4a1d65f70a0d6dd9634e002c0f17a427a8d2a30c` |
| spent-diagnostics.jsonl | `332dc3062e49194ad6b7590b800af3d97f8fed842ecf1726c930a9c5cf60675e` |
| training-oof.jsonl | `c566bb6a708415c337e9ad2575be9e4057295aead72f7370839e55be1e89e9ef` |

Run/inspect commands and complete methods are in the architecture guide.
Inspection of the actual first artifact passed without executing a pickle.
The first actual run completed 252 estimator fits in 293.2561 seconds after
historical diagnosis; whole-process lifetime peak working set 411,832,320 bytes.
This excludes source-loading/initial-diagnosis time and is not per-model memory.
The 1200 second check occurs between fits, not as an OS kill guarantee.

Both actual runs completed 252 estimator fits with identical sealed selection,
reports, predictions and serialized model. **All eight deterministic files are
byte-identical**, including the manifest. Timing logs are excluded deliberately.
Run b took 315.3908 seconds after diagnosis and peak working set 410,759,168 bytes;
research model size 18,361,466 bytes. All 19,332 retained reference predictions
across ten cases match exactly. Metadata-only inspection of both actual artifacts
passed, with serving authorization false and no executable model loaded.

Focused synthetic-fixture verification passed 28 tests/47.08s,
including repeated study/model parity, feature units, opaque reserved labels,
matched comparisons, selection sealing, artifact/code drift and no serving-root
publication. One new serialization test initially lacked a NumPy import; it was
fixed before any actual experiment. Routine formatting/patch-context issues were
corrected without changing the predeclared models/features/criteria.

| Executed completion check | Actual result |
| --- | --- |
| Full Python `pytest -q -p no:cacheprovider`, normal native/temp permissions | **1,230 passed**, 337.76s |
| Full frontend Vitest | **162 passed**, 8 files, 21.73s |
| Complete real-backend Edge browser suite | **12 passed**, 1.5m |
| Root Ruff lint/format and `pip check` | Passed |
| Frontend Biome/typecheck/build | Passed, 63 checked files/68 built modules |
| Exact dependency closure and npm audit | 39 historical Python pin entries match, 17 exact direct npm dependencies, zero vulnerabilities; no new packages |
| Independent preservation audit | 753/754 starting files byte-identical; README is the only expected pre-existing edit |
| Independent declaration/code/receipt audit | Pre-fit config matches its committed version; all eight deterministic outputs and code identities match |
| Local file policy and documentation | Instructions/local plan/data/models/evidence ignored and untracked; 67 relative documentation links resolve |

The browser suite executed the unchanged M08C actual estimators, comparison,
scenario/review/abstention/cancellation/error workflows and existing scheduling,
optimization and production workspace. Desktop/mobile axe smoke checks passed.
Owned API/Vite listeners were closed and ephemeral credentials discarded. Only
the known NO_COLOR/FORCE_COLOR warning remained. Windows/Edge is the verified
environment; no other-platform or accessibility-certification claim is made.

All historical datasets/artifacts/splits/experiments, M08C registry/serving behavior
and frozen planning contracts are preserved. No actual study run failed or changed
the predeclared hypotheses after results. No v2 generation, operational promotion,
deployment, capacity conversion or follow-on milestone was started. M09A stops here.
