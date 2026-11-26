# Mature-history candidate and fifth experimental model

Final milestone, 2026-11-26. [EXP-010](../experiments/EXP-010-mature-history-candidate.md)
implements only the mature-history hypothesis from the existing v2 proposal. One
fixed residual HistGradientBoosting fit uses 5,700 new development targets over
the unchanged frozen RF Physics foundation. No parameter search, new simulator
law, reserved-test evaluation or operational promotion is introduced.

All 41 declared demonstration guards passed on four fresh synthetic worlds before
optional integration. The complete [aggregate results](../experiments/EXP-010-results.json)
include negative findings. Baseline/disruption MAE is 0.05590135 /0.08893545;
baseline actual worst error increased 9.11% versus RF Physics. Extra information,
new training data and a predeclared physical head contribute to these gains.
This is not an algorithm-only comparison or evidence of factory accuracy.

## Data and temporal boundary

The original generator, thirteen planned features, target and units stay frozen.
Separate development seeds 1103/1201/1301/1409 (2033) and heldout seeds
2503/2609/2707/2801 (2034) use the original process, matched baseline/disruption
inputs and isolated create-only storage. The new model receives five additional
historical summaries: uncensored attainment mean/std, total/uncensored counts
and latest report age. They summarize at most seven earlier same-crew/line
reports available by the thirty-minute pre-shift cutoff. IDs are joins, never
predictors; current/future outcomes, other entities and reserved source gap/test
labels are excluded. Missing context remains explicit.

Held-out model parameters are immutable. Earlier held-out reports may become
mature context for a later forecast; this is forward-only online context use,
not fitting on held-out labels or evaluating entirely unseen-history cold starts.
Source manifests bind joins/timestamps, and predictions are sealed before
evaluation labels are accessed. One A evaluation and its one B reproduction
produced identical prediction/report bytes. The inspected holdout is now spent;
B is not independent validation. Model-training binary replay was not performed.

## Additive API and UI

`POST /api/v1/predictions/synthetic/v3` adds `schema_version: 3`, optional
`history` and `history_boost`, with up to five distinct selected models. The
original `inputs` object still has exactly thirteen fields. V1/v2 requests,
responses and four frozen estimators remain compatible. The outer API version
stays `v1`. See the [complete example](../../examples/api/synthetic-prediction-v3.json).

History requires consistent integer counts 0..7; uncensored count cannot exceed
total. Mean/std must both be missing below two uncensored reports and both finite
within 0..3 otherwise. Age must be missing iff no report exists, or within 0..8760
hours. No training flags, paths, model settings or current outcome fields are
accepted. Defaults are explicitly missing, never invented historical measurements.

The demonstration policy requires at least two uncensored reports and age <=72h.
Missing/stale context or undefined capacity abstains. Every candidate point
estimate requires **REVIEW_REQUIRED** because browser history is hypothetical and
self-reported; it is not source-verified. Thirteen-input marginal support comes
only from the new development training rows and does not certify historical
feature/joint support, entity transfer or timestamp truth. Scientific metrics
still include all defined targets, including missing history, without filtering
to improve scores. The demo policy does not revise experiment criteria.

AI Predictions keeps RF Physics as its compatible default, offers original-four
and all-five comparison, and exposes the five history inputs only when needed.
Editing context clears previous results and pinned scenario context. V3 comparison
shows matched EXP-010 baseline/disruption MAE, RMSE, macro R2, bias, P95 absolute
and actual worst error for all selected models, with 1,426 targets per condition.
Historical EXP-008 benchmark metrics remain separately identified as spent.
Ten signed differences describe a five-model request; no causal effect is claimed.
No calibrated candidate interval or fabricated feature explanation is displayed.

## Artifacts and execution

`data/processed/experimental_ml/v3` is ignored and create-only. Its closed set is
`history_boost.joblib`, `metadata.json`, `manifest.json` (completion marker last).
The independent [registry](../../src/loometric/final_candidate/trusted_v3.json)
pins the manifest SHA. Size ceilings: model 32 MiB, metadata 1 MiB, manifest 64 KiB.
All hashes, environment, four frozen candidate source files, configuration, feature
order, target, units and authorization flags are checked before deserializing
verified in-memory bytes. Loaded estimator types/state/profile are checked too.
Incomplete, altered, revoked or incompatible bundles fail closed; no refit/fallback
repairs artifacts. Local code, registry and locked dependencies remain trusted.

The API parent imports no ML stack. V3 shares the existing one-slot, one-thread,
768 MiB /10s native worker, 8 KiB request and 128 KiB response limits. Request
cancellation retains admission until cleanup. Serving reads artifacts only,
never source datasets, labels or evaluation engines. Planning, scheduling and
capacity application remain separate. All five models keep **NO_ML_PROMOTION**;
experimental API permission is distinct from production/capacity authorization.

## Reproducible artifact preparation

Use the repository checkout with Python 3.13.14, the locked requirements and the
matching Windows environment. V1/v2 prerequisites and their independent receipts
are in the [existing preparation guide](experimental-ml-inference.md#reproducible-v2-artifact-preparation).
Never regenerate original reserved datasets to make a loader pass.

For an immediate demo, restore a trusted local archive containing the exact closed
v1/v2/v3 bundles to `data/processed/experimental_ml/`, then verify before startup:

```powershell
.\.venv\Scripts\python.exe -m loometric.final_candidate verify
```

This checks the sixty frozen source pins, v3 registry, model bytes, environment
and published report identity without unpickling. API requests independently
verify every selected bundle. Artifacts stay out of Git and the static web root.
The task prepared an ignored local model-only archive under
`.tmp/portfolio-demo/`; use its SHA receipt and trusted source registries when
transferring to a separately authorized demo host. No credentials/datasets are
included. Verify v1/v2 against their original registries as well.

To reproduce offline from an **empty isolated checkout/output tree** with the
verified original v1/v2 bundles already present, use the committed configuration:

```powershell
foreach ($operation in @('develop', 'evaluate', 'reproduce', 'publish', 'verify')) {
    & .\.venv\Scripts\python.exe -m loometric.final_candidate $operation
    if ($LASTEXITCODE -ne 0) { throw "EXP-010 stopped at $operation; inspect and preserve evidence." }
}
```

These are explicit offline commands, never startup hooks. Development fits once;
evaluation requires the independently committed candidate hash, reproduction
requires the independent report hash, and publication must equal the v3 registry.
Existing attempt/output/publication paths abort rather than overwrite or retry.
A different training binary/report must be investigated; do not revise pins or
retune to force success. Only frozen-model inference/report reproduction was
empirically verified in this task, not a second fit or cross-platform binary replay.
Do not run this loop over the retained actual EXP-010 output tree.

See [deployment instructions](../deployment.md) for local production build,
single-worker startup and the optional same-origin HTTPS gateway configuration.
