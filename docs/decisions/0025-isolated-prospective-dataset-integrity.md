# ADR 0025: Isolated generation and label-blind registration for EXP-009

Status: accepted for M10A.2 implementation, 2026-11-26. Actual generation deferred.

## Context and options

EXP-009 fixes new worlds and frozen models before exposure. Reusing the original
writer would compute target summaries, while the full reader decodes outcomes.
Trusting a namespace prefix or self-discovered receipt would not prove source
provenance. Options are weaken those boundaries, modify the frozen generator, or
add a separate bounded producer/registrar. Choose the separate infrastructure.

## Decision

Keep the protocol, generator and all 60 frozen source/config/pin files unchanged.
Use a fixed, separately allowlisted offline worker under the existing hard memory
guard and whole-child watchdog. Add no HTTP operation. Generation requires an
explicit separate authorization; it is never triggered by inspection or imports.

Generate exactly twice, run physical integrity checks and compare deterministic
file bytes before create-only publication. Independently reconstruct pre-cutoff
catalogs and plans from the frozen RNG key rules to verify actual values, foreign
keys, temporal availability and complete exposure. Preserve raw IDs while auditing
world-scoped identities against receipt-verified historical reference tables.

Register only explicit independent eight-case receipts. Use closed size-limited
manifests and checked buffers, rematerialize all features from the source joins,
verify matched conditions and rehash after inspection. Reserve every label/global
outcome file from JSON decoding; binary hashing needs an exact-path capability
in the isolated worker. Verify opaque row counts without inspecting target values.
Write a separate create-only ledger and require its independent SHA to verify it.

## Consequences

Private mechanical tests can establish producer/reader boundaries without exposing
actual prospective data. The independent pre-cutoff verifier deliberately duplicates
the frozen sampler's source rules and is tested against it; code drift fails closed.
Label-blind inspection binds the trusted producer's replay evidence but does not
authenticate a publisher or independently analyze arbitrary re-signed targets.

There is no actual EXP-009 generation, model loading, fitting, scoring, calibration,
promotion, serving change, merge or deployment. NO_ML_PROMOTION persists. The future
whole-evaluation supervisor, counters and full-scale execution evidence remain
outside M10A.2. See the [implementation guide](../architecture/prospective-dataset-infrastructure.md).
