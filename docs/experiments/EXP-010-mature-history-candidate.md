# EXP-010: One bounded mature-history candidate

Predeclared 2026-11-26, before new generation, fitting or held-out inspection.
**NO_ML_PROMOTION.** Configuration: [final_candidate_v1.json](../../configs/final_candidate_v1.json).

The final milestone tests one candidate, not a search. All EXP-009 outcomes are
spent development evidence. Frozen source files, models and old reserved datasets
remain unchanged and are never training data for this candidate.

## Design and pre-shift provenance

Keep the original target, units, original 13 planned inputs, process law, difficult
events, noise and unannounced disruption. Add only mature same-crew/line history:
mean/std of uncensored past attainment, total/uncensored counts, latest report age.
Take the last seven eligible reports; fewer than two uncensored reports gives
explicit missing mean/std. Eligibility requires an earlier shift and label
availability no later than the current cutoff (30 minutes before start).
Use world-scoped entity identities; never feed IDs, scenario, future values,
realized current staffing/loss, completed pieces or current censoring to a model.

This implements the v2 proposal's history hypothesis only. No new process mechanism,
oracle risk forecast, diversity sweep, learning curve or calibration claim is added.
The same generator law with a separately versioned history projection prevents
manufacturing easier outcomes solely to improve scores.

Development worlds: seeds 1103/1201/1301/1409, start 2033-01-03. Fresh held-out worlds:
2503/2609/2707/2801, start 2034-01-02. Each uses 112 calendar days, original default
development parameters and matched baseline/disruption arms. Separate create-only
roots under `data/processed/final_candidate/exp-010` hold sources and receipts.
No old or EXP-009 label file is read. Original source gap/test labels remain reserved.

Training uses development baseline source-train observations once, plus the first
eight source-validation dates in both arms. Exclude one following validation date
as an embargo; the last nine dates are development checks only. Verify global
training-label maturity before their cutoffs. No parameter changes follow checks.
Held-out fitting is forbidden, including its prefix. Prefix and earlier held-out
reports may supply mature historical context only. The complete 18 source-validation
dates (360 planned rows/case) are evaluated with immutable parameters. This online
context use is disclosed and does not constitute parameter training on the holdout.

## Candidate, controls and budget

History Boost adds one fixed residual HistGradientBoosting prediction to frozen
RF Physics. Parameters are in config: 160 iterations, learning rate .05, 15 leaves,
minimum leaf 30, L2 1, absolute-error loss, no early stopping, seed42. Predeclare
the head `min(max(foundation + residual, 0), offered_work_attainment)`. No post-result
clipping choice is permitted. Freeze the candidate binary before holdout exposure.

Compare the four frozen models on the same IDs/labels, using their unchanged 13
inputs and raw outputs. Also evaluate this same fitted candidate with all history
explicitly missing (no extra fit), to expose the contribution of new information.
Report raw scientific errors independently of serving support/abstention policy.

Maximum one estimator fit; zero hyperparameter trials/calibration fits; one numeric
thread; 2,048 MiB and 1,200 seconds per isolated operation. At most 16 source cases,
two generator passes/case, 43,520 source rows and 10,000 fit rows. No extension or
favorable retry. Maximum 48 top-level batch predict calls per held-out pass (six
views × eight cases; each candidate view also invokes its immutable foundation).
One held-out scoring pass and one frozen prediction/report reproduction; never fit
again to reproduce the candidate. Raw artifacts stay ignored; curate evidence only.

## Metrics and integration criteria

Report all seven EXP-009 metrics, per-world/stage performance, output-envelope
violations, support/abstention, cold-start/available-history counts, resource use
and actual source/model receipts. Use equal-world macro summaries separately by
condition. Enumerate 256 paired four-world bootstrap resamples; primary contrast
is candidate-minus-RF-Physics baseline MAE. Other contrasts are descriptive.

Every integration guard is frozen before training:

- At least 300 valid targets/case, finite/aligned paired evidence and reproduced bytes.
- At least 5% macro MAE gain against **both** Forest12 and RF Physics in each condition.
- No macro RMSE or P95 absolute regression against RF Physics in either condition.
- No condition/stage macro MAE regression above 10% versus the better Forest12/RF Physics.
- No world/condition MAE regression above 10% versus RF Physics.
- Condition-wide worst error no more than 10% above RF Physics.
- At least three of four world MAE wins against RF Physics per condition.
- Primary world bootstrap interval upper bound strictly below zero.
- At least 2% macro MAE gain versus the missing-history control in each condition.

Passing permits only optional experimental demo integration, never operational
promotion or a claim of uniform stage/factory superiority. Failure remains visible
and prevents presenting the candidate as a superior fifth model. No tuning follows
held-out evidence. Four simulated worlds, online context and unobservable first
shocks limit generalization; no independent prediction coverage is claimed.

## Frozen development result before held-out generation (2026-11-26)

Declaration/code commit `e2c68accb0e1b7a820c01701595ef4bd4d4af776` was pushed before
actual generation or fitting. Preparation/protocol checks: 59 passed in 26.76s.
Exactly one actual residual estimator fit used 5,700 defined development targets
dated 2033-01-03 through 2033-03-18. Original models were loaded, never refitted.
The eight development sources each passed two full deterministic generation passes.

The fixed development check gave History Boost macro MAE 0.052965324 baseline and
0.057152379 disruption, versus frozen RF Physics 0.108530350 / 0.208913496.
These are development results only; no hyperparameter or feature change followed.
The candidate was frozen while the heldout source directory was still absent:

`320d7ea2cbc9d23f9c92953e3eb0d848bfd3b6b0e5710801016753bf54dcf2a4`

The independent [candidate receipt](EXP-010-candidate-receipt.json) binds executable
bytes, exact training fingerprint/seeds/dates, source receipts, code, configuration
and environment. This receipt is committed and pushed before fresh held-out
generation/evaluation. Training operation: 46.469847s, peak aggregate committed
memory 289,505,280 bytes, native Windows Job guard, one numeric thread; 2,048 MiB /
1,200s caps unchanged. No other actual estimator fit occurred.


## Actual held-out result and frozen reproduction (2026-11-26)

Candidate receipt commit `b950018d08c09a4e41088f437fa5a61210fd2a2f` was pushed before generation/scoring of the new 2034 worlds. Exactly one A scoring pass and its single B reproduction completed. All 41 predeclared demonstration guards passed; no parameter, seed, threshold or dataset extension followed exposure. The candidate is eligible for optional experimental integration only. **NO_ML_PROMOTION** remains unconditional.

All models used the same 1,426 defined targets per condition (2,852 total; 2,880 planned, 28 excluded zero-capacity targets). Seeds 2503/2609/2707/2801 contribute 355/356/357/358 defined targets in each arm. Metrics below are equal-world macro averages; R2 is the mean world R2, not pooled R2. P95 is the mean world percentile. Worst is the actual condition-wide maximum, not the mean world maximum. Bias is prediction minus observed attainment. Units remain dimensionless standard worker-minutes per planned worker-minute.

| Condition | Model | MAE | RMSE | Macro R2 | Bias | Macro P95 abs | Actual worst abs |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | Grouped Mean | 0.13837471 | 0.17593831 | 0.39274335 | 0.03125908 | 0.35369442 | 0.63778751 |
| baseline | Random Forest (Forest12) | 0.12228832 | 0.16853343 | 0.44439778 | 0.02772650 | 0.35851526 | 0.66716786 |
| baseline | HistGradientBoosting (Hist31) | 0.11802068 | 0.16041952 | 0.49569424 | 0.02252908 | 0.32912821 | 0.65692877 |
| baseline | RF Physics | 0.10932347 | 0.16765693 | 0.44558076 | 0.02390977 | 0.37293162 | 0.85021742 |
| baseline | History Boost | 0.05590135 | 0.09832114 | 0.81017281 | 0.00738717 | 0.19938581 | 0.92765843 |
| disruption | Grouped Mean | 0.23994719 | 0.29184392 | -3.22406696 | 0.22923256 | 0.52818909 | 0.76874443 |
| disruption | Random Forest (Forest12) | 0.23056244 | 0.28369487 | -2.99472048 | 0.22569999 | 0.51574669 | 0.90130719 |
| disruption | HistGradientBoosting (Hist31) | 0.22582037 | 0.27651773 | -2.78403413 | 0.22050256 | 0.49555130 | 0.77029320 |
| disruption | RF Physics | 0.22453752 | 0.28872642 | -3.14335951 | 0.22188326 | 0.55703661 | 1.08435675 |
| disruption | History Boost | 0.08893545 | 0.13297610 | 0.12239264 | 0.06961269 | 0.28657840 | 0.86567867 |

Relative candidate MAE reductions (same targets and equal-world aggregation):

| Condition | vs RF Physics | vs Random Forest | vs Grouped Mean | vs same candidate, missing history |
| --- | ---: | ---: | ---: | ---: |
| baseline | 48.87% | 54.29% | 59.60% | 49.21% |
| disruption | 60.39% | 61.43% | 62.94% | 64.82% |

### Per-world and stage diagnostics

| Seed | Condition | History Boost MAE | RF Physics MAE | Random Forest MAE | Defined targets |
| --- | --- | ---: | ---: | ---: | ---: |
| 2503 | baseline | 0.05449787 | 0.10329127 | 0.13062087 | 355 |
| 2503 | disruption | 0.09347317 | 0.22653707 | 0.23760030 | 355 |
| 2609 | baseline | 0.05484219 | 0.11186190 | 0.12950532 | 356 |
| 2609 | disruption | 0.08273839 | 0.21010171 | 0.21360585 | 356 |
| 2707 | baseline | 0.05585533 | 0.10814231 | 0.11333956 | 357 |
| 2707 | disruption | 0.08895793 | 0.22677469 | 0.22818500 | 357 |
| 2801 | baseline | 0.05840998 | 0.11399839 | 0.11568752 | 358 |
| 2801 | disruption | 0.09057229 | 0.23473663 | 0.24285862 | 358 |

| Condition | Stage | History Boost MAE | RF Physics MAE | Random Forest MAE |
| --- | --- | ---: | ---: | ---: |
| baseline | cutting | 0.05436053 | 0.14510492 | 0.14135825 |
| baseline | finishing | 0.05563504 | 0.08222342 | 0.09667829 |
| baseline | packing | 0.06292742 | 0.11647224 | 0.14723588 |
| baseline | quality_control | 0.05777817 | 0.09865980 | 0.11595795 |
| baseline | sewing | 0.04865195 | 0.10397881 | 0.11013629 |
| disruption | cutting | 0.09077524 | 0.28925715 | 0.27788292 |
| disruption | finishing | 0.09302439 | 0.23591149 | 0.25839335 |
| disruption | packing | 0.08694168 | 0.19056855 | 0.21069996 |
| disruption | quality_control | 0.09130342 | 0.20748823 | 0.19180601 |
| disruption | sewing | 0.08263291 | 0.20029471 | 0.21464613 |

History Boost wins MAE in all four worlds in each condition. The primary paired four-world bootstrap interval for candidate minus RF Physics baseline MAE is **[-0.05630406, -0.05049215]** (256 ordered resamples). The reverse contrast is stored in the aggregate JSON with opposite signs. Other model/condition intervals are descriptive. Only four worlds and a shared generator law limit uncertainty interpretation.

The [aggregate record](EXP-010-results.json) retains all six model views, all seven error metrics plus P95 positive error, every world/stage cell, paired bootstrap intervals, support counts, offered-work violations, source receipts and all 41 guards. It contains no individual labels or prediction vectors. No row-level source, executable model or generated dataset is committed.

### Support, resource and integrity evidence

| Condition | Candidate supported | Candidate review | Scientific abstention | Available history |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1361 | 65 | 0 | 1371/1426 |
| disruption | 1405 | 21 | 0 | 1416/1426 |

Scientific metrics include every defined target, including missing context: no support-based deletion improves scores. Marginal training support is not proof of factory/entity transfer. The additive demo policy is stricter: at least two uncensored mature reports and age <=72h are required; missing/stale context returns ABSTAIN. This policy does not change the frozen experiment scores or criteria. No conditional policy-filtered performance claim is made.

| Isolated operation | Wall seconds | Peak committed bytes |
| --- | ---: | ---: |
| develop | 46.469847 | 289,505,280 |
| heldout | 49.850166 | 269,168,640 |
| reproduce | 9.299025 | 267,993,088 |

All operations stayed within 2,048 MiB /1,200s with one numeric thread. Development performed one estimator fit on 5,700 targets. Each of sixteen source cases passed two deterministic generator passes. Independently audited 16 manifests/96 source files, all 60 frozen EXP-009 source pins, legacy artifact bundles and the frozen candidate core. A/B prediction vectors and report bytes are identical; report SHA256 is `efa3b39c1bb7db1fb60c2fcdbe5678c1933e599f8f5e8a89c4692cf03089491c`. B is deterministic reproduction, not a second independent validation sample or a repeated training run.

Independent [execution metadata](EXP-010-execution.json) retains actual UTC timestamps, resources and receipts. The [v3 registry](../../src/loometric/final_candidate/trusted_v3.json) independently pins the create-only publication. No training-binary replay was performed: B reused the same frozen candidate, as declared.

### Negative findings and limits

- Baseline actual worst error **0.92765843**, versus RF Physics **0.85021742**, increased **9.11%**. This passes the declared 10% ceiling but rules out uniform superiority.
- Missing-history control MAE **0.11005795 /0.25277363** (baseline/disruption) is worse than RF Physics **0.10932347 /0.22453752**. Extra history matters; cold-start superiority is not established.
- Disruption bias remains **+0.06961269**, R2 only **0.12239264** and worst error **0.86567867**. First unannounced shocks remain hidden.
- Gains mix one changed estimator, a predeclared physical head, extra historical features and new development data. They cannot be attributed solely to the boosting algorithm or compared numerically with EXP-008/009 across different worlds.
- Held-out entities have earlier mature context but no parameter fitting. This is forward-only online context evaluation, not an unseen-history or entirely new factory cold start.
- Four synthetic worlds under the original process law do not establish external factory performance, calibrated uncertainty, production safety or scheduling capacity applicability.
- The fresh heldout was independent of candidate selection when first opened. Its now-inspected outcomes are spent; repeated A/B bytes do not restore independence. All old and new reserved source gap/test labels remain unused.
