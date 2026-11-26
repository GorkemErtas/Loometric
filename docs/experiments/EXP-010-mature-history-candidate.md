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
