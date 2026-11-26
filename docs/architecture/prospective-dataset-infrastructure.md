# EXP-009 prospective dataset infrastructure

M10A.2, 2026-11-26. Infrastructure implemented; **actual datasets not generated**.
The frozen [EXP-009 protocol](../experiments/EXP-009-prospective-frozen-evaluation.md)
and [configuration](../../configs/prospective_evaluation_v1.json) remain unchanged.
No model is loaded, fitted, tuned or executed. **NO_ML_PROMOTION** is unconditional.

## Boundaries and public entry points

The separate `loometric.prospective_evaluation` package provides offline dataset
infrastructure. It adds no HTTP route, dashboard workflow, model registry or
serving behavior. The shared execution allowlist adds exactly one fixed worker
name; existing callers still select their original workers and budgets.

`service.prepare_sources(generation_authorized=False)` rejects by default before
starting a worker. A future, separately authorized generation invocation must
explicitly pass `True`. This implementation task does not authorize that invocation.
`register_sources(expected_manifest_sha256)` requires the independent eight-case
receipt mapping; `verify_sources(expected_ledger_sha256)` requires the independently
retained ledger hash. These functions own a separate child with the protocol's
2,048 MiB ceiling, 1,200-second operation deadline and one numeric thread. Windows
Job Object/Linux RLIMIT_AS enforcement is reused; unavailable guards fail closed.
There is no automatic generation on import, startup, verification or registration.

The complete prediction/evaluation supervisor and its whole-evaluation budget
accounting are future work. This milestone bounds the individual source/registration
operations and enforces exactly two full generator calls per case; it does not
claim to implement an end-to-end evaluation run or its two-run admission policy.

## Source generation and independent provenance checks

The adapter obtains the eight cases exclusively from the pinned declaration:
seeds 101/211/307/401, baseline/disruption, 112 calendar days from 2032-01-05,
96 working dates, 18 validation dates, 360 planned validation rows and 2,720
source observations per case. Actual eligible-target counts remain unknown.
No physical process, feature, target, unit or threshold is changed.

`generation.py` calls the existing frozen generator exactly twice for each case.
Both copies pass the original physical/accounting/calendar validator. It serializes
and compares every resulting file byte-for-byte before publication. This is
generation-time physical QA, not outcome distribution analysis, model scoring or
inspection of prospective evaluation results. The original writer/quality reporter
is never used: that reporter computes target statistics.

`source.py` independently reconstructs only the frozen generator's pre-cutoff
streams: factory/line/crew/style/standard catalogs, shifts, orders, plans and
membership. It never samples a latent/outcome stream. Actual source records must
match this reconstruction, including roster/skill/complexity/standards, seeded
order quantities/WIP, compatible relationships, full exposure grid and timestamps.
Features are rematerialized through the original outcome-free joins. This catches
rehashed cross-line crew references, copied seed profiles, changed snapshots and
injected predictors, even when namespace strings and metadata look plausible.

Raw IDs remain unchanged. Scoped identities are `(kind, world_id, local_id)`;
matched conditions share the same world. The historical inventory reads only
independently receipt-verified original manifests and five reference tables
(factories, lines, crews, styles, standards). It does not read old features,
outcomes or label files. Its reference receipts and entity-key digest bind the
publication and ledger. Actual new source records must match the new seed's sampler;
changing a prefix alone cannot establish that provenance. Equal sampled attribute
values across worlds are allowed and are not treated as proof of leakage.

## Files, publication and replay evidence

Every case is create-only under the declared ignored root:
`data/processed/prospective_evaluation/exp-009/datasets/{case_id}/`.
The closed set is 17 JSONL files plus the final `manifest.json`:

- Ten normalized source tables, including the opaque global outcomes file.
- The original thirteen-feature view.
- Scoped entity keys and ordered validation observation IDs.
- Four partition-specific label files.

Source/feature records use deterministic sorted-key JSON with exact decimal strings,
finite values and terminal newlines. The manifest binds protocol identity, full
source configuration, case/world/seed/condition, target/units, source-only counts,
environment versions, infrastructure-code hashes, historical inventory, every
file's byte/row/hash identity and the matching two-generation replay identities.
Its core-code list is explicit, so adding a future evaluator module does not
silently alter the data infrastructure identity.

All output is create-only, including partial files and ledgers. The completion
manifest is written last. Interrupted output is retained and rejected; no repair,
overwrite or automatic regeneration occurs. Safe paths reject traversal, absolute
client paths and symlink/junction escapes. File/bundle/root ceilings are 32/64/768 MiB;
manifest/ledger JSON has an additional 64 KiB limit. Root scanning is bounded too.

Baseline/disruption equality covers **all** pre-cutoff tables, features, scoped
entities and score membership, not merely the thirteen input columns. The four
world pairs must be unique and the dataset directory must contain exactly the
eight declared case directories. A ninth directory is not silently ignored.

## Label-blind registration and independent verification

The registrar accepts expected hashes explicitly; it never treats a discovered
manifest hash as its own trust root. It verifies the exact file set and sizes
before decoding, checks all bytes, and parses only allowed pre-cutoff records.
Verified in-memory buffers are compared with the independent source reconstruction
and feature joins. The full manifest must equal the closed expected policy.

Every label file, including validation, and `outcomes.jsonl` is hash-only during
registration. Their newline row counts must match the source partitions; their
JSON/values are not decoded. The dedicated worker's access hook denies ordinary
reads of these files. Only a narrow exact-path hashing capability can read them;
it returns identity metadata and resets even on failure. ML imports/model files
and unrelated historical data access are rejected. A separate decoder allowlist
rejects labels even if a caller already possesses bytes.

The registrar rehashes files and manifest after auditing to detect changes during
inspection. Once all eight cases, paired inputs and historical identities pass,
it writes `receipts/datasets.json` last, without label summaries or predictions.
Retain its returned SHA independently. Verification requires that external SHA,
revalidates the ledger's closed policy and every referenced source, and never
regenerates a source. Declaration-time `NOT_GENERATED` is not edited.

Hashes prove integrity relative to trusted local receipts, not publisher identity
or physical validity of arbitrary newly re-signed labels. Physical validation and
full deterministic replay occur in the producer. Label-blind registration verifies
that attested byte identity and actual pre-cutoff joins, not a second label analysis.

## Executed scope and remaining work

Tests use only private mechanical seeds 99101/99211/99307/99401, 35-day calendars,
two factories and three styles, with private temporary roots. They do not generate
any declared actual case. Tests cover replay, unchanged sources, deterministic
publication, rehashed leakage/aliases, matching pairs, old reference integrity,
independent receipts, incomplete writes, row/size/path limits, mutation during
inspection, ordinary forbidden reads, no ML imports, authorization rejection and
native watchdog behavior. Existing generator and API isolation/contracts are
included in regression verification. Exact counts are recorded in EXP-009's dated
M10A.2 addendum after execution.

Full-scale generation time/memory, actual new-world profiles and actual eligible
counts are **not measured**. No independent evaluation or calibration result is
claimed. The original 60 frozen source/config/pin files and frozen protocol remain
byte-identical. Models, old datasets and serving contracts are untouched.

Next implement the feature-only sealed prediction pass and an independently
receipt-bound validation-label reader, then metrics, uncertainty, acceptance and
whole-run supervision. Commit and verify that implementation before separately
authorizing actual source generation or evaluation. No M10A.2 command executes it.

## M10A.3 implementation follow-up (2026-11-26)

The [frozen evaluation engine](prospective-frozen-evaluation-engine.md) now supplies
the separate sealed prediction pass, receipt-bound validation reader, diagnostics,
acceptance, uncertainty and whole-run supervision described above. This does not
alter M10A.2 source files or receipts. Actual datasets and evaluation remain
unexecuted; authorization is still separate. See the EXP-009 addendum for executed
private-fixture checks and the engine guide for future local use and limitations.
