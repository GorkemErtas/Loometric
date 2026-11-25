# ADR 0023: Preserve RF Physics research inference boundaries

Status: accepted for M09B RF Physics integration (2026-11-25).

## Context and options

The existing RF Physics integration adds an experimental v2 API contract and
changes the dashboard's default selection. Tests still assumed twelve OpenAPI
paths, three models and a one-argument prediction worker. Merely adjusting those
expectations would leave candidate provenance and training-support reuse unchecked.
Options were to remove v2, update expectations alone, or retain the additive
integration and verify its boundaries. Choose the last within the requested repair.

## Decision

Keep `POST /api/v1/predictions/synthetic` and its closed v1 schema unchanged.
`POST /api/v1/predictions/synthetic/v2` accepts schema 2 and up to four distinct
models. Both routes share the existing single inference slot, cancellation cleanup,
loopback/Bearer restrictions and fixed memory, deadline and byte limits. The HTTP
process remains ML-free. A v2 contract is not a new synthetic dataset version.

RF Physics remains `RESEARCH_CANDIDATE`, with `NO_ML_PROMOTION`. Its offline
artifact retains `serving_authorized: false`; a separate receipt authorizes only
the explicitly synthetic, hypothetical experimental API context. Missing or
inconsistent policy fails before candidate deserialization. All bytes, source
receipts, environment, research code, feature schema, dataset identity and target
are checked before loading the verified in-memory candidate buffer.
Create-only offline preparation copies the frozen EXP-008 model without fitting
or deserializing it and requires the independent v2 manifest receipt before any
output is created. Existing or partially written output is never overwritten.

The candidate's benchmark original-training partition matches v1's support source.
Pin that training fingerprint and the canonical support-profile digest in v2
configuration. Reject a mismatch before executing any selected estimator rather
than silently reusing a different population's support profile. Offline verification
recomputed the profile from the original 14,711 training rows; serving does not
read training data. Neither model bytes nor generated metadata receipts are changed.

The frontend verifies candidate provenance at both response and per-result levels,
including EXP-008 identity, the independent manifest receipt, spent-validation
status, 4,833 validation rows and the original benchmark training support source.
It requires null candidate bands, stage metrics, promotion checks and importance;
it verifies all six unique pairwise differences for four models. Existing v1
model selections continue to use the v1 endpoint. Unsupported candidate outputs
abstain under the same support policy as v1; valid above-one values are retained.

## Consequences

Private fitted fixtures exercise integrity, policy revocation, prediction parity,
support consistency and native v1/v2 execution without requiring real ignored
research artifacts. Actual captured v1 and v2 response fixtures are test-only.
Browser tests execute the default candidate, all four models and a legacy selection.
The temporary local smoke script is removed only after its successful prediction,
abstention, v1 compatibility, authentication, invalid-model and candidate-only
coverage passes in permanent native and browser tests. No cancellation or resource
limit is relaxed, and no new dependency, actual research experiment, published dataset, promotion, capacity
conversion or deployment is introduced. Future candidate versions require new
independent receipts and evidence.
