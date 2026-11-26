# EXP-009 frozen evaluation engine

M10A.3 implements the previously declared offline engine. **Actual EXP-009 datasets
have not been generated; its models have not been evaluated. NO_ML_PROMOTION.**
Implementation alone does not authorize generation or execution. The
[protocol](../experiments/EXP-009-prospective-frozen-evaluation.md),
[configuration](../../configs/prospective_evaluation_v1.json) and
[ADR 0026](../decisions/0026-sealed-offline-frozen-evaluation.md) define the boundary.

## Loading and outcome separation

`frozen_models.py` checks both closed bundles against all independently pinned
manifest and file hashes before calling either existing trusted loader. The
loaders check environment, feature order, pipeline structure and exact buffers
before deserializing. Training fingerprint and support-profile digest must match
EXP-009. Missing, oversized, incompatible or changed artifacts abort; no refit or
fallback is available. The original v1 support profile applies to all four models.

`evaluator.py` first admits a create-only run and verifies the independently
supplied ledger through M10A.2's verifier. That verifier checks actual source
records, seeded profiles, temporal provenance, scoped identities and all paired
inputs without decoding outcomes. The evaluator reconstructs the verified
pre-cutoff projections and uses the frozen categorical/numeric conversions.
The 13-feature contract and target units are unchanged.

For each case, one raw batch `predict` per model covers every defined-capacity
observation. Zero-capacity rows have explicit null predictions and exclusion
reasons. Frozen support policy never removes finite outputs from scientific
scoring. Negative or above-three predictions remain raw and receive abstention
flags. Nonfinite or wrong-shaped outputs invalidate the run with no complete-case
rescue. Matched baseline/disruption inputs and predictions must agree within 1e-12.

All eight cases' vectors are written to `predictions.jsonl`, then bound by
`predictions.receipt.json` to protocol, ledger, environment, evaluation code,
model receipts, counts and vector identity. Only after rereading that disk seal
may labels be opened. The vectors contain no targets, realized outcomes or metrics.

`evaluation_access.py` grants an exact-path, temporary capability only to the
strict validation reader. Before decoding, it checks the whole-pass seal and the
case manifest SHA from the independently verified ledger. It validates exact IDs,
closed fields, availability at shift end plus 120 minutes, source-derived planned
capacity, nonnegative integral completed pieces within offered work and exact
target algebra. It does not open global outcomes or other label partitions.
The seal is rechecked around access; all dataset receipts are reverified before
final publication. Frozen sources and model receipts are checked again too.

The isolated worker rejects ordinary reserved-label reads, historical data outside
the reference-table allowlist, unpinned model paths, network/subprocess operations,
overwrites and mutations of existing files. Integrity checks may stream reserved
bytes through a scoped hash-only capability; this does not expose label values.
Audit hooks provide defense in depth for trusted Python code, not a hostile-host
security boundary. No reader or evaluation endpoint is added to the application.

## Diagnostics and acceptance

`diagnostics.py` reports all seven declared metrics: MAE, RMSE, R², signed bias,
P95 absolute error, worst absolute error and P95 positive error. Quantiles use
linear interpolation; positive error is max(prediction minus actual, 0) over all
defined targets. R² is null for constant targets or fewer than two rows. Empty
cells retain zero counts and null metrics. No estimates are clipped or imputed.

Every model/case includes all five stages, shifts, staffing/load/downtime bands,
calendar weeks, scoped factories/lines/crews/styles and support statuses. Cells
show planned and defined-target row/date/entity counts and low support below 30.
Zero-capacity workload is explicitly undefined. Raw ranges, offered-work ceiling
violations and worst IDs remain visible. Input and final support/reason counts,
coverage and abstention rates have both planned and defined-target denominators;
output-added abstention is separate. Common non-abstained IDs and policy metrics
are secondary and cannot replace raw-population scores.

All six paired model contrasts and baseline/disruption metric changes retain each
world and equal-world macro averages. The identical-input balanced-pair MAE floor
is mean absolute target difference divided by two. The sole primary contrast is
RF Physics minus Forest12 baseline MAE.

World uncertainty exhaustively enumerates 256 ordered four-world resamples with
the same blocks for all contrasts, including condition changes. Date sensitivity
uses exactly 500 whole-date draws per world with the declared per-replicate SHA-256
seed and shared rows/models/conditions. Date error sums/counts are preaggregated;
this is algebraically a complete-date block resample, never individual-row sampling.
Intervals and deterministic draw/result digests are retained. Date sensitivity is
not used for acceptance. Four simulator worlds and correlated repeated entities
cannot establish factory confidence, significance or prediction coverage.

`acceptance.py` implements every frozen minimum-count, gain, world-win, world
regression, primary interval, per-stage, per-case tail and disruption guard.
Insufficient support is INCONCLUSIVE; failed numerical guards are
REPLICATION_NOT_SUPPORTED. Passing guards establish replication evidence only.
Both-zero reference non-regression passes with null percent; positive candidate
error against zero fails, and zero cannot support a strict percentage gain.
Integrity/nonfinite/mismatched evidence is INVALID_EVALUATION. There is no search
for an alternative winner, calibration, capacity application or promotion.

## Create-only publication and reproduction

Under the fixed ignored EXP-009 root, only `runs/a` and `runs/b` are admitted.
A failed or partial directory remains and cannot be retried or overwritten.
The completion marker `manifest.json` is written last and lists exactly:

- `attempt.json`: deterministic protocol, independent ledger, code and environment binding.
- `predictions.jsonl` and `predictions.receipt.json`: complete outcome-free sealed pass.
- `errors.jsonl`: matched signed errors and explicit zero-capacity exclusions.
- `report.json`: diagnostics, comparisons, uncertainty and provisional acceptance.

Run A publishes SEALED_PENDING_REPRODUCTION with decision PENDING_REPRODUCTION.
The report's numerical classification remains provisional. Run B requires A's
independently retained manifest SHA, compares its prediction payload before any
validation access, then checks all five deterministic payloads byte for byte.
Only B can publish REPRODUCTION_VERIFIED and the resulting research classification.
The independent verifier reopens both closed runs, checks externally supplied
manifest receipts, current code/environment/ledger and every payload byte.
Timing, native memory telemetry and execution timestamp are outside deterministic
receipts; the service returns the supervisor's actual measurements separately.

`evaluation_service.py` sends one fixed request to `evaluation_worker.py` through
the shared hard resource supervisor: 2,048 MiB, 1,200 seconds for the entire worker,
one numeric thread, at most 32 raw predict calls and 11,520 scored predictions.
Existing 32 MiB file / 768 MiB root limits apply. No per-phase deadline reset or
budget escalation occurs. Native guard absence fails closed. Timeout/memory failure
does not yield successful evidence; incomplete files remain for inspection.

## Future authorized local use

Use the repository's locked Python 3.13 environment and existing frozen artifacts
from the [local artifact guide](experimental-ml-inference.md#reproducible-v2-artifact-preparation).
Do not republish or retrain anything to repair a mismatch. The app startup commands
in [README](../../README.md#local-setup) remain unchanged; the app does not run this engine.

After separate authorization, prepare and label-blind register sources using the
[M10A.2 workflow](prospective-dataset-infrastructure.md). Retain the returned ledger
SHA independently. Only a separately authorized evaluation may then call the Python
API below. These are future instructions, **not commands executed in M10A.3**:

```python
from loometric.prospective_evaluation.evaluation_service import (
    evaluate_frozen_models,
    verify_frozen_reproduction,
)

# Supply the independently retained registrar receipt, never a freshly derived trust root.
ledger_sha = independently_retained_ledger_sha
a = evaluate_frozen_models(ledger_sha, evaluation_authorized=True)
# Retain a["manifest_sha256"] independently before starting the one reproduction.
b = evaluate_frozen_models(
    ledger_sha,
    run="b",
    expected_original_manifest_sha256=a["manifest_sha256"],
    evaluation_authorized=True,
)
verified = verify_frozen_reproduction(ledger_sha, a["manifest_sha256"], b["manifest_sha256"])
```

Execution defaults to rejection unless authorization is explicitly true. There
are no caller-selectable model/config/dataset paths or threshold overrides. Do
not delete a failed run, enlarge a budget, extend samples, tune, or inspect reserved
labels to seek a favorable result. Any failure requires recording its actual cause
and a reviewed next decision under the frozen protocol.

## Verified scope and limits

Tests use private seeds 99101/99211/99307/99401 and 35-day temporary sources,
plus handmade diagnostic/receipt fixtures and predictors whose `fit` raises.
No actual frozen model is fitted or scored by these engine tests. They exercise
two complete private runs, sealed-byte reproduction, cold-process label guards,
source/label/receipt tampering, nonfinite outputs, matched-pair drift, policy/raw
population separation, exact resampling and every acceptance guard.
Existing generator, API isolation, closed-envelope and native supervisor regressions
are included. Exact executed counts are recorded in EXP-009's M10A.3 addendum.

Actual eight-case elapsed time/memory, eligible counts, new-world support and
prospective performance remain unmeasured. Retained EXP-008's 24.05% MAE gain and
0.82067 R² are spent synthetic validation diagnostics, not new independent results.
Hidden disruptions contain no new predictive signal; group/tail failures and
transport limitations may persist. NO_ML_PROMOTION applies to every possible result.

## M10A.4 actual execution follow-up (2026-11-26)

After explicit authorization and final M10A.3 review/merge, the eight actual
sources were generated twice per case and independently registered before scoring.
Exactly one frozen A and its single B reproduction completed within the original
budgets. An independent verifier accepted all five deterministic payloads as
byte-identical. The decision was **REPLICATION_NOT_SUPPORTED**: all 48 minimum
checks passed, but 31 of 77 numerical guards failed. **NO_ML_PROMOTION.**

The earlier sections describe M10A.3's implementation-time state. Actual numerical
results, per-world/stage tables, every guard, support coverage, resource usage,
receipts, read-only audit commands and limitations now live in the
[M10A.4 experiment record](../experiments/EXP-009-prospective-frozen-results.md).
The engine, protocol, artifacts and serving behavior remain unchanged. Actual
outputs remain create-only and ignored; no retry, fitting or tuning occurred.
