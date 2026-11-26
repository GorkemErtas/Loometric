# Experimental synthetic estimator inference

Current final milestone: [History Boost v3](mature-history-experimental-inference.md)
adds an optional fifth experimental model and matched EXP-010 comparison. V1/v2
contracts and the historical records below remain preserved. The UI offers both
original-four and all-five comparison; all models retain NO_ML_PROMOTION.

## RF Physics v2 integration and regression repair

M09B finalizes the additive integration on 2026-11-25. The earlier M08C record
below describes the original v1 behavior and its historical verification.

The dashboard now defaults to **RF Physics** (`rf_physics`), a separately
receipt-bound EXP-008 **RESEARCH_CANDIDATE**. **Compare all four models** executes
it alongside Forest12, Hist31 and Grouped Mean and returns six signed differences.
The existing v1 route and three-model response remain compatible. Selecting only
legacy models still uses v1; a selection including RF Physics uses
`POST /api/v1/predictions/synthetic/v2`, with `schema_version: 2` and the same
closed thirteen inputs. The outer API envelope remains `api_version: "v1"`.
API v2 uses `synthetic-ml-v1` data; it does not generate the proposed v2 dataset.

The frozen ignored candidate bundle under `data/processed/experimental_ml/v2`
must already exist. Its manifest receipt is
`55b09223c57e6c52261a71bc777edddc6116b88b8ffae3f7b0f9cc9075cc51f0`.
Inference never publishes, fits or repairs artifacts automatically. Its metadata
keeps `serving_authorized: false`; the separate experimental serving receipt
permits only hypothetical synthetic research requests, never production serving
or capacity application. Missing, revoked or inconsistent policy fails closed.

Both v2 response-level and per-model provenance identify EXP-008, the candidate
receipt and `fresh_validation: false`. RF Physics's retained benchmark metrics
use 4,833 **spent validation** rows. Its example prediction is
**0.8919168184750277**. No independently calibrated band, stage metrics, promotion
approval or feature explanation is invented. **NO_ML_PROMOTION** persists.

| Spent benchmark metric | RF Physics | Raw Forest12 |
| --- | ---: | ---: |
| MAE | 0.057931364704274735 | 0.07627743732687367 |
| RMSE | 0.09936276695864536 | 0.11161282998389319 |
| R² | 0.8206691735917163 | 0.7737253842072748 |
| Eligible rows | 4,833 | 4,833, matched IDs |

The relative MAE reduction is `(Forest12 MAE - RF Physics MAE) / Forest12 MAE`,
**24.05%**, not a gain in factory productivity. Selection was sealed on original-
training folds before these outer diagnostics. The outer validation had already
been repeatedly inspected; reproducing predictions on it does not restore its
independence. Reserved entity/final-test labels remain untouched. Independent
validation requires a separately declared evaluation on new seeds/entity profiles,
with a separate calibration period, as proposed in EXP-008.

The candidate still has hidden-disruption bias (+0.1857–0.1950), an 11.71% cutting
MAE regression in seed-73 disruption against Grouped Mean, and worst-error
regressions against Grouped Mean (18.25% in seed-42 surge; 16.66% on benchmark).
Benchmark offered-work ceiling violations fall from 1,086 to 205 but are not eliminated. The research
conditional residual bands cover only about 40% under disruption and are not
served. The reused v1 marginal support profile cannot certify joint support,
new-factory transfer or detection of an unobservable shock. No predictions,
labels or interval endpoints are clipped to conceal these failures. Full slices
and counts remain in [EXP-008](../experiments/EXP-008-ml-improvement-research.md).

Support uses v1's original benchmark training population, independently checked
against EXP-008's retained training provenance. V2 pins the training fingerprint
`8ae08345a01c025b5e34a736b848100bc530c4987ac0d750543a7e07847171e8`
and canonical profile digest
`f2e50ecd9b0a589d88a3706f3a31a17f621a5de13b1bf3b9a33380dbaca1e4a3`.
The profile was recomputed offline from all 14,711 original training rows and
matched exactly. That support check uses training rows only; the separate parity
replay uses spent validation. No new fit or reserved-label decoding was performed.
Profile or training-source drift fails before prediction. The fixed 768 MiB,
10-second, one-thread, single-slot worker and cancellation cleanup apply to both
routes, as do the 8 KiB request and 128 KiB response ceilings.

[ADR0023](../decisions/0023-rf-physics-v2-regression-contract.md) records these
regression boundaries. Coverage includes native authenticated execution, artifact
tampering before unpickling, policy revocation, checked-buffer loading, v1 parity,
candidate abstention, training-only support and cross-version cancellation.

## Reproducible v2 artifact preparation

Run offline commands from the repository root with the existing Python 3.13.14
environment locked by `requirements/m05a.txt`. Use the installation and two-terminal
startup commands in [README](../../README.md#local-setup); keep the API token in
the backend process environment and the dashboard session's password field.
The UI runs on `http://127.0.0.1:5173`; the supported single-worker API startup is
`.venv/Scripts/python.exe -m loometric.api`, on loopback port 8000 by default.
Use no cloud service, remote factory system or client-bundled token.

Prerequisites, in order:

1. Retain or reproduce the ten original M08A `synthetic-ml-v1` bundles following
   [data reproduction commands](../data/synthetic-ml-v1-quality-and-reproduction.md#reproduction-commands).
   Their exact directories and independent receipts
   are in `configs/synthetic_training_v1.json`; do not create a new dataset version.
2. Retain or reproduce corrected EXP-006 `data/processed/synthetic_training/exp-006-c`
   using the [training workflow](synthetic-ml-model-training.md). Its receipt is
   `cd19c78c8321ac1bb69dc16d61dc7de01469e35f0d35afe3a3d8c8dca4e8b7b4`.
3. Prepare v1 using the fixed refits below, if it does not already exist. V1's
   independent package receipt is `src/loometric/experimental_ml/trusted_v1.json`.
4. Retain or reproduce EXP-008 at `data/processed/ml_research/exp-008-a` using the
   [research workflow](ml-improvement-research.md#reproduction-and-artifacts).
   Inspect its receipt before v2 preparation. This is historical reproduction,
   not a new search or independent validation milestone.
5. Prepare v2 once, then check the bundle and retained-prediction parity:

```powershell
# Only if EXP-006-c is absent, after all ten dataset receipts match:
.venv/Scripts/python.exe -m loometric.synthetic_training run --output data/processed/synthetic_training/exp-006-c

# Run only if v1 is absent; this refits the fixed original-training models.
.venv/Scripts/python.exe -m loometric.experimental_ml publish --version v1

# Only if EXP-008-a is absent; its research diagnosis requires the verified v1 metadata.
.venv/Scripts/python.exe -m loometric.ml_research run --output data/processed/ml_research/exp-008-a

# Metadata/hash inspection only; no executable model is loaded.
.venv/Scripts/python.exe -m loometric.ml_research inspect --artifact data/processed/ml_research/exp-008-a --expected-fingerprint d2fe121d592a5934753c555815a255620d0010838dc90957af5e3e73319a9cdb

# Run only if v2 is absent; this copies the frozen model, without fitting/loading it.
.venv/Scripts/python.exe -m loometric.experimental_ml_v2.publish
.venv/Scripts/python.exe -c "from loometric.experimental_ml_v2.artifacts import verified_bundle; metadata, _ = verified_bundle(); print(metadata['model'], metadata['promotion_decision'])"

# Offline only: re-predict the same authorized, spent benchmark validation rows.
.venv/Scripts/python.exe -m loometric.experimental_ml_v2.parity
.venv/Scripts/python.exe -m loometric.experimental_ml_v2.compare
```

V2 contains only `manifest.json`, `metadata.json` and `rf_physics.joblib`. Preparation
must reproduce manifest SHA-256
`55b09223c57e6c52261a71bc777edddc6116b88b8ffae3f7b0f9cc9075cc51f0`
and source-model SHA-256
`4f64df4485927c1fdc6eb4bd4a1d65f70a0d6dd9634e002c0f17a427a8d2a30c`
(18,361,466 model bytes). It rejects a serving-receipt mismatch before creating
output. The publisher never overwrites an existing directory; use verified existing
bundles or explicitly investigate a failed/partial publication. Do not delete
historical outputs, edit the trusted receipts to accept drift, or expect a fresh
dependency environment to reproduce them automatically. Environment/research-code
drift fails closed. Both directories and all source datasets/models stay ignored.

The parity tool checks all 4,833 original validation IDs and predictions against
receipt-bound EXP-008 diagnostics, with tolerance 1e-12. Its metrics are expressly
`fresh_validation: false`. The comparison tool shows frozen same-input scenario
predictions; it does not apply support policy or provide causal recommendations.
Serving uses the guarded API, not these offline tools. A checkout without local
artifacts can still run the Python fixture and frontend unit suites; browser
estimator tests require the verified actual v1/v2 bundles.

## M09B final verification

Final execution on 2026-11-25 passed **1,307 Python tests** (528.28s),
**183 frontend tests** (19.18s), and **12 real-backend browser workflows** (1.9m),
without failures or skipped tests. Ruff lint/format, `pip check`, strict TypeScript,
Biome and the production build passed. Actual training-source/support verification,
zero-difference spent-prediction parity and byte-identical v2 preparation passed.
The temporary smoke script was removed after its permanent native/browser coverage
passed. Initial sandbox permission failures were resolved by running native suites
with normal local permissions. The browser harness closed its owned listeners and
discarded the token; only the known NO_COLOR/FORCE_COLOR warning remained.
Windows/Edge is verified; no other-platform or accessibility-certification claim
is made. Full command outcomes and scoped reproduction evidence are recorded in
the [EXP-008 integration addendum](../experiments/EXP-008-ml-improvement-research.md#m09b-integration-addendum-2026-11-25).

The cancellation regression tests both versions and retains the inference slot until
cleanup across competing versions. OpenAPI covers all thirteen routes and each
prediction schema's version/model limits. Permanent tests cover artifact and support
drift, authorization revocation, native error mapping, create-only preparation and
retained-prediction parity. Frontend fixtures are test-only and absent from the app
bundle. The browser suite runs default RF Physics, four-model comparison, scenario,
review, abstention, cancellation, errors and legacy v1, plus existing planning jobs.
Windows exposes aggregate committed-memory telemetry; Linux uses RLIMIT_AS and
does not claim equivalent telemetry. No resource limit or assertion is relaxed.

The earlier M08C implementation and its historical verification follow.

## M08C implementation record

M08C connects actual fitted Forest12 and Hist31 pipelines, plus a transparent
Grouped Mean comparison baseline, to the local API and **AI Predictions** page.
Both ML models remain **EXPERIMENTAL_NOT_PROMOTED**. The original
[EXP-006 NO_ML_PROMOTION](../experiments/EXP-006-synthetic-productivity.md) decision
is unchanged. [ADR0021](../decisions/0021-experimental-synthetic-estimator-inference.md)
defines this separately authorized research boundary; the [EXP-007 record](../experiments/EXP-007-experimental-inference.md)
contains artifact receipts, parity and measured execution evidence.

## Target and permissible use

One hypothetical observation represents a dedicated crew/line performing one
order's stage during a shift. Predict thirty minutes before shift start, using
only planned conditions available then. User inputs are an explicit synthetic
pre-shift scenario, not verified measurements or claims about a particular
factory/crew. Source timestamps and identities are deliberately not invented.
This workflow does not certify a real-world source's point-in-time availability.

`standard_capacity_attainment` = completed good pieces × declared standard
worker-minutes/piece ÷ frozen planned available worker-minutes. The dimensionless
ratio is demand-censored standard output attainment, not guaranteed output,
intrinsic employee efficiency or M02 `assumed_efficiency`. Finite values above one
are valid and retained. Predictions/bands never change schedules or capacity.

## Offline artifact workflow

Use the existing locked Python ML/API environment. No new dependencies. The
original M08A benchmark bundle and corrected M08B `exp-006-c` must already exist
with their independently retained receipts. Publication never regenerates data
or runs model selection. See the [M08A](synthetic-ml-data-foundation.md) and
[M08B](synthetic-ml-model-training.md) reproduction instructions for prerequisites.

```powershell
.venv/Scripts/python.exe -m loometric.experimental_ml publish --version v1
.venv/Scripts/python.exe -m loometric.experimental_ml publish --version v1-reproduction
```

These two allowlisted versions are create-only, under ignored
`data/processed/experimental_ml/`. Existing directories fail before data loading
or fitting. Incomplete publications fail closed; investigate them explicitly
rather than overwriting. The runtime always uses `v1`; the reproduction directory
is offline evidence, never an automatically selected fallback.

Training uses the identical fixed M08B feature ordering/preprocessing/configuration
and seed42 on **14,711 benchmark original-training labels**, dated 2030-01-07 to
2030-08-10. The169 undefined zero-capacity training rows remain excluded/audited.
No validation/test rows enter fitting. The retained M08B manifest, original study
configuration and benchmark dataset receipt must match before any fit. Reserved
outcome/gap/test files are hashed as opaque bytes, never decoded or scored.

The publisher verifies **all4,833 benchmark validation predictions per model**
against the original saved EXP-006 predictions, tolerance1e-12; actual maximum
difference is0.0 for all three. Serialized/reloaded predictions are exactly equal.
Two independent actual publications produced all five files byte-identically.

Artifacts contain fitted preprocessing/pipelines, transparent baseline means,
feature schema, fixed specifications/seed, source/content/split/training receipts,
dates/counts, environment/dependency versions, support, original validation and
subgroup failures, parity, training-OOF residual references and computed global
forest importance. `metadata.json` is versioned for future explicit comparisons;
no automatic training, tuning, registry discovery or promotion runs during serving.

## Trusted loading and process isolation

The separately versioned package file
[`trusted_v1.json`](../../src/loometric/experimental_ml/trusted_v1.json) pins the
manifest SHA-256 and exact local directory independently of generated bytes.
Requests cannot supply paths, files, receipts, limits, model parameters, training
flags or arbitrary versions. No upload/deserialization endpoint exists.

The loader rejects directory/file symlink or junction escapes, limits manifest
size to1MiB and each closed artifact file to64MiB, checks the manifest receipt,
all four file hashes, environment, feature order and metadata policy, then loads
the already verified in-memory model bytes. Replacing a file after verification
cannot change those buffers. It validates loaded estimator types, pipeline steps,
preprocessing parameters and baseline state. A hash binds trusted configuration
to bytes; it does not authenticate a publisher. Local administrators, package
configuration and the pinned Python dependency environment remain trusted.

The API process imports no pandas/scikit-learn/joblib and reads no training or
test data. A separately allowlisted worker starts under the existing hard guard
before importing ML: Windows Job Object aggregate committed memory or Linux
RLIMIT_AS, a768MiB ceiling, ten-second whole-child watchdog and one numerical
thread. Unsupported/unavailable enforcement fails closed. A single inference
slot rejects concurrent work with429 instead of queueing. Global POST admission,
three-second body deadline and loopback/Bearer/CORS checks remain in force.

Accepted prediction bodies are at most8KiB (the existing streaming guard first
bounds all HTTP bodies at256KiB). Worker output is capped at128KiB. At most three
models execute for one validated observation. Children load models per request;
no resident model pool hides unbounded native state. Cancellation retains the
slot until bounded cleanup completes; cancelling a browser request does not
promise immediate native cancellation. A timeout kills/reaps the worker before
returning504. Planning workers, numeric precision, limits and algorithms remain
unchanged. New prediction failures are sanitized and never expose paths/pickles.

## Versioned API

`POST /api/v1/predictions/synthetic` requires the existing local Bearer token.
`GET /api/v1/capabilities` advertises the endpoint/models/limits; artifact
availability is verified on each prediction, not claimed by that metadata call.
`GET /api/v1/openapi.json` documents the closed request. Restart an older API
process to load the new route. A complete [example request](../../examples/api/synthetic-prediction.json)
is intentionally synthetic and contains no outcomes or credentials.

```json
{
  "schema_version": 1,
  "synthetic": true,
  "prediction_context": "HYPOTHETICAL_PRE_SHIFT",
  "models": ["random_forest", "histogram_gradient_boosting", "grouped_mean"],
  "inputs": {
    "stage": "sewing", "shift_kind": "day", "weekday": 0,
    "planned_workers": 6, "skill_level": 3, "style_complexity": 3,
    "standard_worker_minutes_per_piece": 4,
    "planned_machine_available": true, "available_minutes": 420,
    "planned_downtime_minutes": 30, "opening_wip_pieces": 100,
    "planned_release_pieces": 500, "order_quantity": 600
  }
}
```

Every input object has exactly those thirteen fields; ordering in JSON is
irrelevant. The engine restores the original fitted feature order, converts
weekday to its trained categorical string and machine availability to its trained
numeric value. Strict UTF-8 JSON rejects duplicate keys and nonfinite numbers.
Booleans do not count as integers, numeric strings are rejected and no imputation
or clipping occurs. Standards are positive numeric values at most100 with at most
two decimal places. Integer bounds: workers0–100, skill/complexity1–5, weekday0–6,
available/downtime0–480, nonnegative WIP/release≤1,000,000, positive quantity≤1,000,000.
Opening WIP plus planned release must equal quantity. Available time already
excludes the union of planned stops; available plus downtime cannot exceed480.
No second subtraction occurs; client checks are repeated authoritatively in Python.

Valid categorical identifiers absent from training, including Sunday, return
ABSTAIN. Invalid type/range/consistency/envelope returns422. Zero workers/time or
an unavailable machine returns ABSTAIN before estimator execution, with null
prediction/band. Numeric features or outputs beyond training support require
REVIEW_REQUIRED. Negative/nonfinite/>3 model outputs abstain. Support is based
on declared marginal feature/category and training-label ranges, not proof of
joint support, unseen-entity transport or resistance to hidden shift.

Actual response values for the example:

| Model | Prediction | Status |
| --- | ---: | --- |
| random_forest | 0.9036296370677777 | EXPERIMENTAL_NOT_PROMOTED |
| histogram_gradient_boosting | 0.8945601867754494 | EXPERIMENTAL_NOT_PROMOTED |
| grouped_mean | 0.7628348220475517 | BASELINE_COMPARISON_ONLY |

The standard success envelope contains `api_version`, server `request_id` and
`data`. Data includes target/units, echoed inputs/input SHA, model results,
signed pairwise differences, provenance, limitations and execution measurements.
Each result contains model identity/version/status, nullable prediction, support
and reason codes, retained benchmark/stage MAE/RMSE/R²/sample counts, promotion
checks, descriptive residual band and available global explanation. No fallback
number replaces a failed/abstained ML prediction. All selected models receive
the same input vector. ML wire estimates are finite float64 numbers in a separate
frontend adapter; frozen exact planning-decimal adapters are unchanged.

Safe failures:401 authentication,403 local/origin boundary,413 byte ceiling,
422 invalid input,429 busy,503 unavailable/incompatible/tampered artifacts or
resource guard,504 deadline. Missing local models display setup guidance;
inference never builds them automatically. Errors return fixed codes/messages
and correlation IDs; secrets remain outside arguments, URLs, files and logs.

## Dashboard and scenario ownership

Open `/#/predictions`, connect through **Configure API**, review the thirteen
guided fields/units and explicitly confirm hypothetical synthetic pre-shift use.
Random Forest is the default and is visibly experimental. Choose the boosting
model, baseline or **Compare all three models**, then **Predict**. No successful
prediction value or chart is rendered before an actual API response.

Cards show actual estimates/support/bands and original validation errors, including
selected-stage errors and failed promotion gates. Grouped Mean is labeled baseline,
not an ML estimator. Forest packing regression51.84% and histogram stage/worst-error
failures remain prominent. The global forest display uses computed fitted-tree
impurity importance, aggregated to original columns. It is biased by correlation
and cardinality, neither causal nor an individual explanation. No SHAP is claimed.

**Use as scenario baseline** pins a real response in tab memory. Edits immediately
clear the current result and abort/disown its pending response. A new explicit
request supplies after values; show changed inputs and common models' signed
after-minus-before differences/support. Different selected-model sets compare only
their intersection. These are hypothetical contrasts, not causal effects. Sessions,
planning-context changes, navigation or reload discard the page's research state;
there is no database or browser storage. A pinned result survives input edits but
never migrates across sessions. No planning operation is invoked by prediction.

Loading, safe failures, abstention, review, success and empty states are explicit.
Per-request generation IDs, AbortController, session ownership and exact echoed
input/model-order checks prevent late responses from overwriting edited inputs.
Native work can continue until its hard cleanup/deadline despite browser abort.

## Evidence, limitations and future milestones

Complete verification: **1,202 Python tests**, **162 frontend tests**, **12 real-backend
browser workflows** passed, plus root Ruff, frontend lint/type/build, dependency
consistency and zero npm audit findings. No new dependencies. The full preservation
audit retains all original source data, models, splits, EXP-006 and planning engines;
only twelve expected pre-existing app/package/test/documentation files changed.
The detailed commands/results, corrected intermediate failures, screenshots and
limitations are recorded in [EXP-007](../experiments/EXP-007-experimental-inference.md).

The four initial cold requests took3.029–4.001seconds of whole-child wall time,
including imports, checked artifact loading and prediction, excluding HTTP transit
and browser rendering; Windows aggregate committed
memory was200,183,808–200,581,120bytes under768MiB. These are host-specific samples,
not a latency SLA or per-model microbenchmark. The forest file is23,718,378bytes;
histogram558,505bytes; baseline3,449bytes. No warm-serving claim is made.
An additional genuine above-one example returned1.0846155586330681, exactly its
retained authorized validation prediction. Its first attempt hit the ten-second
watchdog; the unchanged rerun succeeded. The timing cause is unestablished, and
the fixed deadline and visible timeout remain part of the research contract.

Changing workers6→8 in the example gives forest0.7758056870789638 and
histogram0.6891308994297132; baseline stays0.7628348220475517. This example shows
executed estimator behavior, not a causal productivity recommendation. Zero workers
abstains;30workers requires review. Training-OOF bands have no calibrated coverage
guarantee: their benchmark coverage is91.25%forest, with severe degradation under
hidden disruption in EXP-006. Coverage is historical aggregate evidence, not the
probability that an individual new target lies inside its displayed interval.

Future work requires separately scoped datasets/receipts, comparison experiments,
subgroup improvements, uncertainty calibration and drift monitoring before any
promotion proposal. Unseen factory/line/crew/style tests remain untouched for an
explicitly approved final-evaluation milestone. Real-factory decisions would need
independent authorized evidence and operational controls. No automatic retraining,
automatic model promotion, database, deployment, external factory connection,
M02 conversion or planning integration is implemented or begun here.
