# EXP-009 actual prospective frozen evaluation — M10A.4

Authorized 2026-11-26. The [frozen protocol](EXP-009-prospective-frozen-evaluation.md)
and [configuration](../../configs/prospective_evaluation_v1.json) remain unchanged.
Four frozen M09B models, eight declared new-world cases, no fitting, tuning,
calibration, sample extension or threshold changes. **NO_ML_PROMOTION.**

## Pre-merge verification and preserved history

M10A.3 passed final review: 263 selected Python regressions in 280.44s, 183 frontend
tests in 21.06s and 12 Windows/Edge browser workflows in 2.0m. Root Ruff lint/format
(322 files), dependency check and frozen source/artifact/dataset audits passed.
Main was fast-forwarded from `157b72a` to
`e10c9bce84ef9b16352785ba6ccf891cec153da7`; the remote hash was verified. Both
`9460eca` (engine) and `e10c9bc` (evidence documentation) remain in history.
Actual execution uses separate branch `feature/m10a4-exp009-prospective-results`.

Before actual generation, commit `eeb36596bcd4cdbd1f4787eb8c57f73231324d09`
adapted four absence assertions into a metadata-only preservation fixture. Four
focused tests passed in 43.91s and the commit/push was verified. Private regression
tests can now coexist with actual outputs without opening their labels or modifying
their files. Engine, generator and protocol sources were not changed.

## Source preparation, registered before scoring

This section and the small, intentionally versioned
[source receipt record](EXP-009-source-receipts.json) were recorded and pushed
before model scoring. They contain metadata/hashes, not datasets or label values.

Exactly eight actual cases were generated: seeds 101, 211, 307 and 401, each under
baseline and hidden disruption. Every case passed two full deterministic generator
passes and physical QA before create-only publication. Each has 2,720 source rows,
18 scoring dates and 360 planned validation observations: 21,760 source exposures,
2,880 scoring exposures and 1,440 distinct paired scoring observations in total.
The hypothetical scoring calendar is 2032-03-11 through 2032-03-31. All original
parameters, 13 features, target definition and units are preserved.

The producer's eight returned manifest hashes were retained outside the dataset
root and supplied explicitly to a separate label-blind registrar. Independent
verification then accepted the externally retained ledger receipt:

`cb0acaa9513c06769d88272ec53bc22890603122751956352630f417556eb2a9`

Verification checked actual seeded source joins, entity provenance/disjointness,
temporal availability, exact exposure grids, matched pre-cutoff bytes, closed
manifests, every file identity and deterministic replay attestations. No model was
loaded or scoring label decoded in these source operations. Train/gap/test labels
and global outcomes remained opaque outside the producer's physical QA.

| Operation | Whole child seconds | Peak committed bytes | Status |
| --- | ---: | ---: | --- |
| Preparation, two passes/case | 49.596908 | 55,898,112 | SOURCE_GENERATION_REPLAY_VERIFIED |
| Independent label-blind registration | 18.842456 | 76,488,704 | REGISTERED_LABEL_BLIND_REPLAY_VERIFIED |
| Independent ledger/source verification | 16.778931 | 72,306,688 | INDEPENDENT_LEDGER_AND_SOURCES_VERIFIED |

All operations used native Windows Job Object aggregate-commit enforcement,
2,048 MiB / 1,200 seconds and one numeric thread. Actual UTC timestamps and full
operation responses are retained in ignored `.tmp/exp009-m10a4/`. Dataset bytes,
model binaries, label/prediction vectors and full generated run artifacts stay
under ignored paths. Deterministic receipts exclude timing/peak/timestamp telemetry.

The frozen configuration's NOT_GENERATED field describes declaration-time state;
it is intentionally unchanged. At this receipt-recording stage, evaluation had
not begun and no validation results were inspected. Later execution results belong
in a separate dated section below, including failures without retries.
