# EXP-007: Fixed experimental synthetic estimator publication and inference

Executed 2026-11-23. This is an implementation/parity study, not model selection,
new accuracy evidence or a revision to [EXP-006](EXP-006-synthetic-productivity.md).
Decision remains **NO_ML_PROMOTION**. [ADR0021](../decisions/0021-experimental-synthetic-estimator-inference.md)
records the separately authorized experimental serving policy.

## Fixed training and retained validation evidence

Source: synthetic-ml-v1 benchmark seed42 baseline, original train only,
2030-01-07 through 2030-08-10, 14,711 defined labels; 169 explicitly undefined
zero-capacity observations excluded. Dataset manifest:
`7e7dae049270675c2eac4f8ad05d55a9ac84cc9c1160e0a6b7e9f4010a64f7eb`.
Authorized training payload:
`8ae08345a01c025b5e34a736b848100bc530c4987ac0d750543a7e07847171e8`.
The exact study declaration and independently retained receipts are unchanged in
[configuration](../../configs/synthetic_training_v1.json).

Reproduce Forest12, Hist31 and Grouped Mean using the original thirteen-feature
ordering, train-fitted preprocessing, seed42 and one numerical thread. No tuning,
pooling, refitting on validation, new calibration or reserved-test decoding/scoring.
Only the benchmark dataset is loaded, through the M08B development-only reader;
reserved/gap/global outcome files remain integrity-checked opaque bytes.

All **4,833 validation predictions per model** match the retained corrected EXP-006
predictions with **maximum absolute difference0.0**. Reloaded serialized models
also match every prediction exactly. Validation labels never enter fit. These
checks establish reproduction of existing evidence, not a new holdout evaluation.

| Model | Status | Retained benchmark MAE | RMSE | R² |
| --- | --- | ---: | ---: | ---: |
| Forest12 | EXPERIMENTAL_NOT_PROMOTED | 0.076277437 | 0.111612830 | 0.773725384 |
| Hist31 | EXPERIMENTAL_NOT_PROMOTED | 0.084484980 | 0.119293904 | 0.741509791 |
| Grouped Mean | BASELINE_COMPARISON_ONLY | 0.122346291 | 0.161097272 | 0.528606086 |

Forest fails the stage guard: development19 baseline packing n36 MAE0.130579885
versus baseline0.085997900 (+51.8408%). Hist fails stage (+32.7993% maximum) and
worst absolute error (+23.1450% maximum) guards. Lower aggregate errors do not
establish superiority in every production stage. The full frozen checks and stage
validation metrics are included in the new metadata without changing EXP-006.

## Artifacts and reproducibility

Two independent offline publications (`v1`, `v1-reproduction`) produced all five
files byte-identically under ignored `data/processed/experimental_ml/`. Timing is
kept outside deterministic identities. No original artifact was overwritten.

| File | SHA-256 |
| --- | --- |
| manifest.json | `bc5e255d8d58fc49e8b37bb44d58647c47402d4cf5f46a525ff9a1b513d28a34` |
| random_forest.joblib | `790f9916209ffc1854e18b6033de9f5864c181d6593ed82768d8a3ca4b83401f` |
| histogram_gradient_boosting.joblib | `c608da41ae1ea348f02155551bbff4ed82659527d8c649002f75e63dd99d4680` |
| grouped_mean.json | `6e952eeb9335441d92ed8783258ab0070256beef7eabb217b5bc7d60597823b4` |
| metadata.json | `2647561b8146d1bea27428b26e15fb55510172b1159f0c3cc11759edf7e8ed74` |

The grouped baseline's bytes also match its original EXP-006 model. A separately
versioned package registry pins the manifest receipt; artifact bytes cannot set
their own trust root. Environment, dependencies, exact schema, preprocessing,
model parameters, source/split/training fingerprints, dates, support, parity,
uncalibrated training-OOF residual references and retained metrics are bound by
the new manifest. No automatic deserialization of arbitrary files is exposed.

## Scientific interpretation

All predictions concern hypothetical synthetic demand-censored standard capacity
attainment: earned standard worker-minutes divided by frozen planned available
worker-minutes. Values above one are retained. They are not guaranteed piece output,
intrinsic employee efficiency, M02 assumed_efficiency or real-factory accuracy.
Hidden shift can evade support checks; unseen entity evaluation remains reserved.
Training-OOF residual bands are descriptive and uncalibrated, not confidence
intervals. Scenario differences cannot establish causation.

Global forest impurity importance is computed from the actual fitted trees and
aggregated over declared one-hot categories to the original thirteen features.
It is a training statistic biased by cardinality and correlated inputs; it does
not explain an individual prediction. Hist local/SHAP explanations are not computed.

## Execution and verification

Artifact-stage tests:14 passed, including private-data reproduction, actual loaded
estimator parity, altered retained predictions, create-only output, wrong receipt,
all-file tampering before deserialization, environment drift and replacement of
model files after verification. The loader executes the already checked buffers.
Ruff lint and formatting pass.

M08C completion verification (2026-11-23):

| Executed check | Actual result |
| --- | --- |
| Full Python `pytest -q -p no:cacheprovider`, normal native/temp permissions | **1,202 passed**,255.75s |
| New experimental Python tests |60 collected, all pass in the full suite |
| Full frontend Vitest | **162 passed**,8files,22.09s |
| Final focused frontend prediction verification after label correction |23 passed,7.57s |
| Complete real-backend Edge browser suite | **12 passed**,1.4m |
| Root Ruff lint and format check | Pass,264 Python files formatted |
| Frontend Biome, TypeScript and refreshed Vite production build | Pass,63 checked files/68 built modules |
| `pip check`, Python snapshot pins, `npm ls --depth=0`, `npm audit --audit-level=low` | Pass,39 historical Python pin entries match,17 exact direct npm dependencies,zero vulnerabilities |
| Two actual publications and independently pinned registry check | All five deterministic files byte-identical; all14,499 retained predictions match exactly |
| Source preservation audit |704/716 starting files unchanged;12 expected application/package/test/docs edits only |
| Documentation links / ignored outputs |68 relative links resolve; instructions/local plan/models/evidence remain ignored and untracked |

The native HTTP tests run private fitted artifacts under the actual guard while
an audit hook prohibits repository training/test-data and fixture-source access.
They exercise auth, tampering, no planning mutation, safe errors, hard deadline,
single-slot admission and cancellation ownership. Other focused tests cover
exact thirteen-feature ordering, actual estimator calls, no inference-time fits,
unknown categories, physical validation, out-of-support review, zero capacity,
above-one preservation, failed model outputs and pairwise arithmetic.

The real browser executes all three actual estimators, compares returned values
with rendered cards, pins a response, changes workers6→8, checks numerical/input
differences, reviews30workers and abstains at zero. It verifies loading, edit-time
cancellation of a delayed real response, explicit503 handling without fake values,
desktop/mobile axe smoke checks, no page overflow or planning requests, and no
credential persistence. Four screenshots are under ignored `.tmp/frontend/`:
`m08c-predictions-desktop.png`, `m08c-scenario-comparison.png`,
`m08c-predictions-mobile.png`, `m08c-predictions-error.png`. Owned API/Vite listeners
were closed and ephemeral credentials discarded. These are tested Windows/Edge
views, not a WCAG conformance or other-platform claim.

Actual guarded example, sewing/day/Monday, standard4, available420minutes,
downtime30, skill/complexity3, WIP100+release500=quantity600:

| Planned workers | Forest12 | Hist31 | Grouped Mean |
| --- | ---: | ---: | ---: |
|6|0.9036296370677777|0.8945601867754494|0.7628348220475517|
|8|0.7758056870789638|0.6891308994297132|0.7628348220475517|

Zero workers returns null/ABSTAIN for all three;30workers returns REVIEW_REQUIRED.
Four initial whole-child wall measurements span3.029–4.001seconds and Windows
aggregate committed memory200,183,808–200,581,120bytes under the768MiB/10second
guard. These include import/check/load/predict and exclude HTTP transit/rendering;
they are host-specific samples, not a latency SLA. Forest23,718,378bytes,
histogram558,505bytes, baseline3,449bytes. API/page artifacts stay local.

An additional actual endpoint request reconstructed only the thirteen pre-shift
features for authorized validation observation
`OBS-SH-F01-2030-08-13-day-L-F01-sewing-00`. The forest returned
**1.0846155586330681**, exactly its retained EXP-006 prediction, without clipping.
No target label was needed for this check. Its first attempt reached the ten-second
watchdog and returned sanitized504; the unchanged request/artifacts succeeded on
the development rerun. The timing variation's cause was not established. Keep the
hard deadline and explicit timeout state; do not infer a cold-start latency SLA
or add automatic retries from this result.

Superseded verification failures are explicit. Initial expanded tests exposed
missing residual-band metadata in a private fixture and the old OpenAPI route
count; both were corrected. Strict TypeScript/control-label issues and the sandbox
native-worker EPERM were resolved with normal process permissions. First browser
run passed11/failed1 on the model selector's exact label; its association was fixed
and all12 reran successfully. Full Python initially stopped during collection on
a new `test_artifacts` basename collision; the new module was uniquely renamed,
then the unchanged full-suite invocation passed all1,202. A local preservation
helper's unsupported multi-path `git check-ignore --quiet` invocation was corrected
and the complete audit reran successfully. No automatic approval rejection,
dependency change, test-set consumption or scientific gate relaxation occurred.
