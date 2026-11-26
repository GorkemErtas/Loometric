# ADR 0026: Seal the entire frozen inference pass before validation access

Status: accepted for M10A.3 implementation (2026-11-26); actual EXP-009 unexecuted.

## Context and options

[EXP-009](../experiments/EXP-009-prospective-frozen-evaluation.md) fixes four models,
eight paired development cases, independent dataset receipts, numerical criteria
and a two-run budget. M10A.2 supplies label-blind source verification. Existing
serving readers implement an interactive policy population; using those responses
would discard abstained rows and cannot provide the declared raw scientific scores.

An incremental predict/score loop would expose outcomes before other cases are
predicted. An unrestricted research runner would weaken partition and budget
boundaries. Choose a dedicated offline two-pass worker with fixed configuration,
independent ledger input and no integration into serving or model selection.

## Decision

Verify both closed frozen bundles before executable deserialization. Reuse their
existing loaders, which deserialize checked in-memory buffers and verify frozen
pipeline/environment contracts. Use the original training support profile and the
same 13-column conversion contract; never fit, calibrate, clip or replace outputs.

Verify the ledger and all source joins before loading models. Infer one batch per
model/case on defined planned capacity, then check paired inputs/predictions. Write
all eight vectors and their receipt before opening any validation label. Read back
the disk vectors for scoring. A narrow reader checks the whole-pass seal and the
independently registered manifest before decoding exactly that case's validation
IDs, times, denominator and target algebra. Other source partitions, global outcomes
and historical label files remain inaccessible except opaque integrity hashing.

Write deterministic matched errors, diagnostics and acceptance evidence separately
from supervisor measurements. Run A remains PENDING_REPRODUCTION. Run B requires
the original manifest receipt, verifies prediction equality before label access
and compares every deterministic payload byte before publication. A separate
read-only verifier checks both completed runs. Numerical evidence cannot become
final without reproduction; every state preserves NO_ML_PROMOTION.

Use the existing hard-memory/whole-process watchdog with a new fixed worker name;
do not alter API worker budgets or requests. The single 2,048 MiB/1,200 second
boundary includes receipt verification, loading, inference, labels, uncertainty
and reporting. Enforce 32 raw predict calls and 11,520 predictions, one numeric
thread, create-only a/b directories and existing file/root ceilings. Retain failed
attempts without retries, deletion, extra runs or budget escalation.

## Consequences

The frozen protocol, generator, source identities, artifacts, promotion gates and
serving behavior remain unchanged. New modules have no training/publishing entry
point. Private mechanical tests exercise sequencing, tampering, partition access,
thresholds, resampling and byte reproduction. They provide implementation evidence,
not prospective model results or full-scale resource measurements.

Python audit hooks constrain trusted worker code and accidental access; they are
not protection against a hostile local administrator or arbitrary native code.
Receipts establish integrity relative to independently retained trusted hashes,
not publisher authentication or external factory validity. See the
[engine guide](../architecture/prospective-frozen-evaluation-engine.md).
