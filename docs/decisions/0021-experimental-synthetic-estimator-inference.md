# ADR 0021: Trusted local experimental estimator inference

Status: accepted for M08C (2026-11-23).

## Context and options

EXP-006 retained Grouped Mean because both tree families failed frozen subgroup
promotion gates. The user explicitly authorizes research inference of Forest12
and Hist31 while preserving that finding. Options are baseline-only serving,
silently promoting the best aggregate model, or an explicit experimental registry.
Choose the registry. Neither model becomes an operational recommendation.

## Decision

Refit only the fixed Forest12/Hist31/Grouped Mean configurations on the authorized
benchmark original-training partition, with identical preprocessing and seed42.
Validate every authorized validation prediction against the independently
receipt-bound corrected EXP-006 artifact; no new search, validation refit, test
decoding, calibration, scoring or change to the historical report. Publish new
create-only ignored version directories; reproduce them independently.

Pin a manifest receipt separately from the generated directory. Inference accepts
only model identifiers, never files, paths, receipts, parameters or training flags.
The fixed local v1 directory has a closed file set. Reject path escapes and verify
all size-limited bytes, environment and schema before unpickling. Deserialize the
same checked in-memory bytes, preventing replacement between checking/loading.
Hashes establish integrity against trusted configuration, not publisher identity;
local administrators and the dependency environment remain trusted.

Reuse loopback-only Bearer auth, strict JSON/byte limits and the existing OS child
watchdog. A separate inference worker receives a bounded research request and an
independent receipt. It has its own single execution slot, one numeric thread,
hard memory ceiling and whole-child deadline. Planning workers/limits stay
independent; the HTTP process never imports or deserializes ML. Missing/incompatible
artifacts or unavailable resource enforcement fail closed. No inference-time fits.

The closed thirteen-feature contract uses explicit pre-shift hypothetical values.
Validate numeric types, units, consistency and support; unknown categories or zero
capacity abstain before estimator execution. Out-of-training support requires
review. Keep valid values above one. Return descriptive training-OOF residual
bands, measured validation errors and failed gates. Global forest importance is
actually computed from its fitted trees; it is neither causal nor a local
explanation. Scenario comparisons show predictions/input changes, not causation.

## Consequences

The dashboard executes real fitted estimators for synthetic research only.
NO_ML_PROMOTION and all historical/final-test/planning contracts remain intact.
Cold per-request child startup costs latency, but permits hard resource cleanup
without a resident unbounded native estimator. No database, cloud infrastructure,
automatic retraining/promotion, real-world accuracy claim, capacity conversion or
production schedule mutation is introduced. Future model/dataset versions require
new metadata, independent receipts, parity/validation evidence and explicit policy.
