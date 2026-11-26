# EXP-009: Prospective frozen model evaluation protocol

Predeclared 2026-11-26 for **M10A.1**. **NOT EXECUTED. NO_ML_PROMOTION.**
No prospective outcomes, predictions, scores, dataset receipts or model fits exist
from this task. Execution needs separate authorization. This document and its
configuration must be committed before any prospective outcome inspection.

## Question, evidence role and scope

Does the already selected RF Physics representation improve frozen-model transfer
to new development worlds, compared with the same frozen Grouped Mean, Forest12
and Hist31 models? Does that improvement survive matched hidden disruption?
The source [EXP-008](EXP-008-ml-improvement-research.md) benchmark improvement
(24.05% MAE versus Forest12, R² 0.82067) is **spent validation**, not the answer
to this prospective question. No model is selected, reranked, refitted or tuned here.

This evaluates the first hypothesis of the [v2 proposal](../architecture/synthetic-ml-v2-proposal.md)
using the original 13 inputs. It does **not** implement the proposal's signals,
history, diversity tiers, learning curves or new process law. New seeds give fresh
pseudorandom entity profiles conditional on the same assumed simulator; they are
not independent factories, real-world evidence or a test of a new industrial law.
Four worlds limit uncertainty estimates and subgroup transport claims.

The [machine-readable declaration](../../configs/prospective_evaluation_v1.json)
has canonical SHA-256
`2c64f2eccbf310ba2079d8c47fc11ab78e076cd8081937ebc56468975443b0e5`.
Canonicalization is sorted-key UTF-8 JSON, compact separators, finite numbers and
one terminal newline. The independent digest is pinned in
[`protocol.py`](../../src/loometric/prospective_evaluation/protocol.py).
Formatting alone may change; scientific/policy edits require an explicit new
reviewed declaration before exposure, never a receipt replacement after results.

## Frozen models and reproducibility boundary

Base revision: `2427b0948f33c4a7224555b92a97b73ce50095d3`, synchronized with
`origin/main` before creating `feature/m10a-prospective-frozen-evaluation`.

| Public model | Frozen identity | Bundle | Executable/state file |
| --- | --- | --- | --- |
| grouped_mean | grouped_mean | synthetic-experimental-v1 | grouped_mean.json |
| random_forest | forest-12 | synthetic-experimental-v1 | random_forest.joblib |
| histogram_gradient_boosting | hist-31 | synthetic-experimental-v1 | histogram_gradient_boosting.joblib |
| rf_physics | rf_physics | synthetic-experimental-v2 | rf_physics.joblib |

V1 manifest: `bc5e255d8d58fc49e8b37bb44d58647c47402d4cf5f46a525ff9a1b513d28a34`.
V2 manifest: `55b09223c57e6c52261a71bc777edddc6116b88b8ffae3f7b0f9cc9075cc51f0`.
The configuration pins every model/state/metadata file digest and 60 existing
source/config/dependency-pin files. The existing locked environment must match
the bundles; record its actual versions and the later evaluation-code identity.
Hashes bind trusted local configuration to bytes, not publisher identity.

The future offline evaluator must verify all checked bytes before deserializing
the same in-memory buffers. Do not invoke publishers, training builders, `fit`,
`fit_transform`, `partial_fit`, hyperparameter optimization, early stopping,
feature selection, model selection or new calibration. Missing/incompatible
artifacts abort; no refit/fallback is permitted. Preprocessing, derived features,
category mappings, baseline means and numerical seed 42 remain frozen.

## Target, timestamp and feature availability

One observation is a dedicated qualified crew/line doing one order's stage in an
aware shift. Cutoff is **30 minutes before start**, snapshot five minutes before
cutoff. Every referenced factory/line/crew/style/standard/shift/order record must
be available by cutoff. Shift length is 480 minutes; label availability is shift
end plus 120 minutes. All source timestamps must be aware minute timestamps.

Preserve `standard_capacity_attainment` = completed good pieces × standard
worker-minutes/piece / (planned workers × planned available minutes), in
`dimensionless_standard_worker_minutes_per_planned_worker_minute`. Available
minutes already exclude break/planned-stop unions; never subtract downtime twice.
It is demand-censored output attainment, not intrinsic efficiency or guaranteed
pieces. Zero planned denominator produces the original explicit null/status;
audit every such observation without imputation or prediction. Above-one values
remain valid. No label, point estimate or interval is clipped.

The exact input order remains:

```text
stage, shift_kind, weekday, planned_workers, skill_level, style_complexity,
standard_worker_minutes_per_piece, planned_machine_available, available_minutes,
planned_downtime_minutes, opening_wip_pieces, planned_release_pieces, order_quantity
```

Validate physical inputs and decimal/float conversion under the existing
[inference](../architecture/experimental-ml-inference.md) and
[data](../architecture/synthetic-ml-data-foundation.md) contracts. Restore trained
categorical weekdays and numeric machine availability exactly. All thirteen
fields are planned inputs; identities, dates, condition, seed, realized staffing,
unplanned loss, difficult events, completed pieces, closing WIP, current labels
and demand censoring are excluded from estimator inputs. Planned WIP/release,
planned stops and planned labor are never replaced with realized values.

## Worlds, sample sizes and matching

Freeze seeds **101, 211, 307, 401**, each with `baseline` and `disruption`:
eight cases. Use unchanged `stage-shift-process-v1` and all original development
parameter values except the declared start/calendar: **2032-01-05, 112 calendar
days**, Mon–Sat, 3 factories, 2 lines/stage/factory, 6 styles, two dedicated shift
crews per active line. These remain hypothetical dates and synthetic assumptions.
The configuration explicitly records every generator parameter.

Use the generator's existing date/entity assignment, with **no training on any
new prefix**. Only each new world's source `validation` partition is authorized
for scoring. New `train`, `gap`, `test` labels and the global outcomes file remain
opaque to the evaluator, even though the generator constructs them. Old M01 and
all old M08A reserved labels remain entirely outside the study.

| Design quantity | Fixed planned count |
| --- | ---: |
| Working dates/world | 96 |
| Source train / gap / validation / test dates | 56 / 2 / 18 / 20 |
| Scoring dates | 2032-03-11–2032-03-31, 18 dates |
| Active scoring factories / lines / distinct shift crews | 2 / 10 / 20 per world |
| Scoring rows/date | 20 |
| Scoring rows/condition/seed | 360, including undefined-capacity observations |
| Scoring rows/stage/condition/seed | 72 |
| Distinct paired scoring observations across four worlds | 1,440 |
| Baseline/disruption scoring exposures | 2,880 |
| Source rows/case, including unscored partitions | 2,720 |
| All source exposures, eight cases | 21,760 |
| Maximum four-model scored prediction attempts/run | 11,520 |

Counts are derived from calendar/entity rules, not generated outcomes or a power
calculation. Eligible non-null-target counts are unknown. Require at least 300
valid targets/case, 50/stage/case, 15 valid dates/case and per stage, and at least
two active lines/four distinct crews per stage. Insufficient support is
INCONCLUSIVE; never add seeds, extend dates, resample profiles or manufacture rows
until a gate passes. Missing planned observations are integrity failures, not
ordinary null-target exclusions. Report actual style/entity/date counts.

Within a seed, use common keyed random streams, identical entities, plans, date
membership, IDs and input bytes. Disruption adds 60 unplanned loss minutes bounded
by available time and multiplies latent rate by 4/5 on the generator's existing
post-prefix conditions. It supplies **no pre-shift signal**. Only the authorized
validation portion is scored. Verify exact feature/membership/profile digests and
one-to-one pairing before reading scoring labels. Predictions must agree across
conditions within 1e-12; otherwise the evaluation is invalid. Feature-only support
cannot detect a hidden shock whose inputs are identical.

## Entity separation, temporal provenance and label sealing

The generator reuses raw names such as `F00` for different seeds. Preserve its
local records and RNG keys; define global identity as **(world_id, local_id)**,
scoped to the entity table. Use `exp-009-world-{seed}` for both matched conditions;
case IDs include seed and condition. The pair key excludes condition.

New RNG seeds must differ from 19/42/73, and manifests must prove the declared
seed/code/config provenance rather than relabeling an old profile. Reject copied
historical provenance and cross-world aliases. Inventory historical entities
from receipt-verified reference tables only, never old outcome/target files.
Audit qualified entity disjointness across new worlds and historical worlds;
within-world matched conditions intentionally share entities. Namespace changes
alone do not prove statistical independence: report repeated entity counts,
profile provenance and the common-law limitation, including any coincident sampled
attribute values rather than rejecting unfavorable coincidences.

The conservative historical calendar/label upper bound is **2031-01-08 UTC**,
derived from the original calendars plus delay allowance, without reading old
reserved labels. Every new cutoff must be later. Verify start-date ownership,
aware offsets, exact cutoff/snapshot/delay, all source availability timestamps
and no future-derived feature joins. This creates chronological separation from
all old source periods; it does not simulate an evolving process law.

The future execution must separate:

1. Generation, physical/integrity validation, deterministic replay and label-blind
   receipt registration, before any model-error inspection.
2. An outcome-free feature reader and frozen prediction pass, with file-access
   guards prohibiting all label/outcome files. Eligibility depends on planned
   denominator only. Seal predictions, input/ID/support receipts and model receipts.
3. Only then read the new cases' `labels.validation.jsonl`, verify availability and
   score the sealed vectors. Never use the existing `read_bundle` (global outcomes)
   or `load_development` (also decodes training labels) as an evaluation shortcut.

Current metadata checks test these rules on handcrafted provenance. They cannot
certify nonexistent future datasets; actual joins, receipt verification, physical
QA, exposure tracking and runtime file-access guards belong to the next implementation.

## Integrity identities and ignored outputs

New dataset identity: **synthetic-prospective-exp009-v1**, preserving the original
feature/target contract and underlying generator identity. This is a separate
experiment envelope, not the proposed signal-bearing synthetic-ml-v2 dataset.
Keep all original writers, data, manifests and serving registries unchanged.

The future dedicated writer must use create-only paths under:

```text
data/processed/prospective_evaluation/exp-009/
  datasets/exp-009-development-{seed}-{baseline|disruption}/
  receipts/datasets.json
  runs/a/
  runs/b/
```

Bind normalized/derived bytes, canonical features, score membership, scoped
entities, configuration, protocol SHA, code/environment, seed/condition and row
counts in closed manifests, written last. Independently regenerate each source
twice before scoring. Register all eight verified dataset receipts in a separate
label-blind create-only ledger and retain its SHA independently. A later evaluator
must receive that expected ledger SHA explicitly; discovering a hash from the
directory it is about to trust is insufficient. No future dataset hash is invented
in today's declaration: receipt state is **NOT_GENERATED**.
That field records the declaration-time state. Later receipts belong in the
ledger and dated result addenda, without editing this frozen configuration.

Later run manifests must bind the ledger, frozen bundles, sealed predictions,
exclusions, support statuses/reasons, matched errors, metrics/slices, bootstrap
specification and conclusions. Reproduce deterministic result bytes in `a` and
`b`; keep wall time, memory and execution timestamps separate. Reproduction does
not provide another independent validation sample. Retain failed/incomplete runs
as failures, never overwrite or delete historical outputs or selectively report.

## Metrics, coverage populations and comparisons

For each of all four frozen models, seed and condition, report **MAE, RMSE, R²,
bias (prediction minus actual), P95 absolute error, worst absolute error and P95
positive error**. Quantiles use linear interpolation. R² is null for constant or
fewer-than-two targets; empty cells retain count 0 with null metrics. Never silently
drop missing/invalid outputs, clip estimates or substitute the baseline.
For residual `e = prediction - actual`, P95 positive error is the 95th percentile
of `max(e, 0)` across all eligible rows, preserving the existing metric definition;
it is not the percentile conditional on overprediction. MAE is mean abs(e), RMSE
is sqrt(mean(e²)), worst error is max abs(e), and R² is 1 - SSE/SST when defined.

Primary scientific metrics use **all defined targets and raw finite frozen
predictions**, including numeric extrapolation and finite outputs outside policy
bounds. Such outputs still receive their policy-abstention flag. Nonfinite outputs
invalidate the evaluation rather than yielding an attractive complete-case score.
Zero-capacity targets remain audited exclusions with explicit counts/reasons.

Apply the unchanged marginal support assessor and frozen original-training
profile (digest and training fingerprint are in configuration). Report pre-input
and final per-model SUPPORTED_EXPERIMENTAL / REVIEW_REQUIRED / ABSTAIN counts,
reasons, coverage and abstention rates on **all planned rows**, and separately on
defined-target rows. Input and output abstentions must be distinguished. Policy
error metrics on the common non-abstained intersection are secondary and must
show every denominator; they never replace all-defined-target comparisons.

Report stage, shift, staffing1–5/6–10/11+, planned-load≤3/5, (3/5,1], >1,
planned downtime0/1–30/31+, calendar week, factory/line/crew/style and support-status
slices. Include row/date/entity counts and flag fewer than 30 rows. Stage guards
apply separately to every seed/condition/stage; no pooled cell can conceal a failure.
Worst-row identities and finite output-range/physical-ceiling counts remain visible.

The single primary contrast is **RF Physics minus Forest12 baseline MAE**, using
paired observations and equal-weight seed means. Also report all six model pairs
per condition, RF Physics versus Grouped Mean/Hist31, and matched baseline-to-
disruption changes in error/bias/tails. Report every world and the equal-seed macro
metrics separately by condition; optional row-pooled summaries are descriptive
and never replace macro gates. Compare matched errors, not unmatched means.
For identical-input target pairs report mean abs(target_baseline-target_disruption)/2,
the empirical balanced-pair MAE lower bound for a single common prediction.
These are simulator contrasts, not proven causal factory interventions.

## Uncertainty and multiplicity

The primary uncertainty display enumerates all **4^4=256 ordered world-cluster
bootstrap resamples**, drawing four seed blocks with replacement. Reuse each
resample for all models/conditions; compute equal-seed mean paired MAE differences
and linear 2.5/97.5 percentiles. Preserve/restate the four observed world contrasts.
Apply the same matched world resamples to secondary model/condition MAE contrasts.
With only four synthetic worlds these are coarse descriptive resampling intervals,
not calibrated 95% factory confidence, population significance or prediction coverage.

As sensitivity only, use 500 paired whole-local-start-date block resamples within
each world, RNG seed 20261126, keeping all rows/models/conditions on a sampled
date together. Persistent entities cross dates, so this is conditional temporal
sensitivity, not independent-crew uncertainty. It cannot override primary guards.
For replicate0–499, seed a local `random.Random` from the big-endian integer SHA-256
of UTF-8 `EXP-009|date-bootstrap-v1|20261126|{world_id}|{replicate}`. Sample 18
dates with replacement from that world's sorted 18 scoring dates. No global RNG
state or outcome-derived clustering/order is used.
No p-value search or best-of-six winner selection: one primary baseline contrast;
all other comparisons/slices are explicitly descriptive with complete reporting.

There is no calibration period in this frozen replication study. Do not fit new
residual bands or claim independent coverage. RF Physics's band remains absent;
any separate future calibration study needs its own prospective declaration.

## Predeclared acceptance, including negative results

Validity first: all eight complete cases, exact byte/row/ID/model/code/environment
receipts, all leakage checks, successful prediction sealing, finite outputs,
deterministic reproduction and no forbidden reads/fits. Violation means
**INVALID_EVALUATION**. Valid but insufficient target/date/entity counts mean
**INCONCLUSIVE**, with no sample-size extension.

Only if validity/support pass, label RF Physics evidence
**FROZEN_CANDIDATE_REPLICATION_SUPPORTED** when **all** conditions hold:

- Baseline macro MAE improves≥5% versus Grouped Mean and≥2% versus Forest12.
- Baseline MAE beats Forest12 in at least 3/4 worlds; no baseline world regresses
  more than 5% against Forest12. The primary world-bootstrap interval's upper
  endpoint is strictly below 0; this is a declared consistency guard, not a significance proof.
- Stage MAE regresses at most 5% against Grouped Mean in **every** seed/condition/stage.
- P95 absolute error and P95 positive error regress at most 5%, and worst absolute
  error at most 10%, against Grouped Mean in every seed/condition.
- Hidden-disruption macro MAE does not regress against Grouped Mean, and no
  disruption seed regresses more than10% against it.

Other numerical outcomes, including a primary interval crossing 0, mean
**REPLICATION_NOT_SUPPORTED**, not proof that all models are inferior. Relative
gain is100×(reference-candidate)/reference; regression reverses the numerator.
When reference error is 0, both 0 passes a non-regression guard; positive candidate
error fails with a null percentage. Strict improvement cannot be claimed over 0.
No alternate model is selected when RF Physics fails. Report every failed check.

These are new replication-evidence criteria, not edits to EXP-006/008 promotion
gates. **NO_ML_PROMOTION remains regardless of any result.** No serving, dashboard
default, registry, uncertainty display, planning capacity or schedule is changed.

## Computational budget and stopping rules

Per future full run: **zero fits/tuning/calibration**, eight cases, at most 32 raw
model predict calls and 11,520 scored prediction attempts. Use one numeric thread,
2,048 MiB memory ceiling and 1,200-second whole-run deadline. The future harness
must enforce the latter limits in an isolated offline process; today's protocol
validator does not claim to implement that watchdog. No API worker limit changes.

At most two independent source generations/case and two complete evaluation
runs (original/reproduction). File/bundle/root caps are 32/64/768 MiB respectively.
Abort on integrity failure, nonfinite output, memory/deadline exhaustion or
budget breach; retain an explicitly incomplete/failure record. No automatic budget
increase, fallback world, retries searching for favorable scores or adaptive stopping.
Environment failures may be investigated before exposure; any corrected execution
must retain failure history and the same frozen declaration/inputs.

## Implementation plan and current verification

M10A.1 delivers only the configuration, pure calendar/provenance/paired-receipt
validation, tests and this protocol plus [ADR0024](../decisions/0024-prospective-frozen-model-evaluation.md).
No runner/CLI, generator adapter, dataset writer or model loader is added.

After a separately authorized next task:

1. Implement the isolated offline source writer/receipt registrar with explicit
   new identity/output root; preserve original generator/writer/readers. Test on
   private mechanical fixtures, including unreadable reserved labels and aliasing.
2. Implement the feature-only sealed frozen prediction pass, strict receipt-bound
   validation-label reader, unchanged shadow support assessment, full metrics and
   matched comparisons. Spies must fail any fit/tune and any forbidden file access.
3. Implement deterministic world/date resampling, all acceptance states, guarded
   resources, create-only reports and independent reproduction inspection. Test
   zero-denominator/null/nonfinite/empty-slice and loss-selection failures.
4. Complete and commit the verified implementation **before** any real source
   generation. Obtain execution authorization, register data receipts before
   scoring, execute once plus reproduction, then append actual results and limits.

Relevant preparation checks (commands run from repository root):

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/prospective_evaluation
.venv/Scripts/python.exe -m ruff check . --no-cache
.venv/Scripts/python.exe -m ruff format --check . --no-cache
.venv/Scripts/python.exe -m pip check
```

Executed preparation checks on 2026-11-26:

| Check | Actual result |
| --- | --- |
| New protocol suite plus existing v2 closed-envelope regressions | **50 passed**, 2.27s (39 protocol + 11 request-contract cases); no skips |
| Root Ruff lint and format checks with `--no-cache` | Passed; 301 Python files formatted |
| `pip check` | No broken requirements |
| Frozen source/config/pin/registry identity verification | All 60 declared files match |
| Existing v1/v2 bundle hash inspection during preparation | Both independent manifest receipts and every file matched; no pickle loaded |
| Cold-process protocol/data-access guard | Passed; no pandas/NumPy/scikit-learn/joblib imports or dataset/artifact reads by the protocol module |
| Documentation and repository policy | 22 relative links/anchors resolve; balanced fences; 425 tracked/proposed files pass artifact and credential-pattern checks |

The first sandbox test attempt had 21 passing cases and 18 temporary-directory setup
errors (WinError 5); normal local process permissions resolved them without changing
assertions. One test-string lint line wrap was corrected. Final tests use only
calendar arithmetic, handcrafted provenance and strict declaration/receipt metadata.
No actual prospective entity/label audit or scoring result is claimed.

The full training/research/browser suites were **not rerun** for this declaration:
they exercise fitted models and are outside the no-fit preparation scope. No
prospective runner or execution command exists. All datasets/model binaries/generated
outputs remain ignored and untracked; the EXP-009 output directory is absent.

## M10A.2 infrastructure addendum (2026-11-26)

The frozen declaration, configuration, thresholds and preceding M10A.1 record
remain unchanged. M10A.2 implements source production and integrity infrastructure
only. **Actual EXP-009 datasets have not been generated; no prospective model,
prediction, score, fit or calibration has been run. NO_ML_PROMOTION remains.**

The separate adapter runs the original generator twice and performs physical
integrity checks plus complete byte replay before create-only publication. The
registrar independently reconstructs pre-cutoff catalogs/plans and rematerializes
the feature joins from verified source buffers. It checks new seed provenance,
world-scoped entities, exact exposure and temporal metadata, historical reference
receipts, all matched baseline/disruption inputs and closed independent hashes.
It never JSON-decodes any label or global-outcome file; opaque row counts are
verified against source membership. A separate independently receipt-bound ledger
is written only after all eight cases pass, including a final file rehash.

The dedicated offline worker uses the existing native hard guard at 2,048 MiB,
1,200 seconds and one numeric thread. Ordinary reserved-file reads/model access
are denied. Generation is disabled by default and requires separate explicit
authorization. Existing API workers, routes, serving and frozen artifacts are
unchanged. The shared worker allowlist receives one fixed additional name.
See [ADR0025](../decisions/0025-isolated-prospective-dataset-integrity.md) and the
[implementation guide](../architecture/prospective-dataset-infrastructure.md).

| Executed check | Actual result |
| --- | --- |
| Initial new infrastructure tests | 41 passed, 72.28s |
| Selected final infrastructure/protocol/original generator/native resources/API isolation/OpenAPI/v2 request-contract regression | **187 passed**, 97.66s; no skips |
| Additional cold-process complete registrar/independent verifier under access guard | **1 passed**, 28.13s; no ML imports or label decoding |
| Root Ruff lint/format; dependency consistency | Passed; 310 formatted Python files; no broken requirements |
| Frozen protocol and source/config/pin preservation | Original configuration digest unchanged; all 60 source hashes match |
| Frozen model preservation, opaque byte verification only | Both independent bundle receipts and all six model/state/metadata hashes match; no deserialization |
| Historical dataset preservation, no target decoding | All ten manifests and 170 file hashes match their independently retained receipts |
| Actual prospective output root | Absent; no actual dataset or ledger receipt claimed |
| Documentation and repository policy | 27 relative links/anchors resolve; 434 tracked/proposed files pass artifact/credential-pattern checks |

Private mechanical fixtures use seeds 99101/99211/99307/99401, 35-day calendars,
two factories/three styles and temporary directories. They cover successful
publication/replay/registration, tampering, correctly rehashed leakage/entity
aliases, policy/manifest closure, matched pairs, opaque row counts, incomplete
writes, size/path limits, racing changes, authorization and native timeouts.
The full training/model-serving/browser suites were not run; selected tests
exercise no trained model. Historical synthetic tests use private mechanical
inputs and are not prospective evaluation evidence.

Limitations: full-scale generation time/memory and actual new-world/entity/eligible
counts are unknown. The label-blind registrar verifies the trusted producer's
replay identity and pre-cutoff joins, not arbitrary newly re-signed target values.
Whole-evaluation supervision, model inference, validation-label unsealing and
evaluation remain future work. The implemented source operations have individual
hard ceilings; no end-to-end execution or evaluation-budget claim is made here.
Generated artifacts remain ignored/untracked; no merge or service deployment occurs.
