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
Ruff lint and formatting pass. Runtime, dashboard and complete regression evidence
will be recorded after their independently verified stages.
