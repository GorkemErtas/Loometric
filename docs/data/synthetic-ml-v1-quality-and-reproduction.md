# Synthetic ML v1: quality evidence and reproduction

M08A evidence recorded 2026-11-22 on Windows / Python 3.13.14 using the existing
Loometric 0.1.0 environment. All data below is generated from declared assumptions,
not factory measurements. This is a data-quality/reproducibility record, not a new
ML experiment or model-performance result. See the [architecture](../architecture/synthetic-ml-data-foundation.md),
[dictionary](synthetic-ml-v1-dictionary.md) and
[ADR 0019](../decisions/0019-separated-synthetic-pre-shift-data.md).

## Reproduction commands

Run from repository root using the existing editable installation. Generation uses
standard-library code and existing M02 helpers; no new dependency is required.
Choose a **new** directory under ignored `data/processed/synthetic_ml/`:

```powershell
.venv/Scripts/python.exe -m loometric.synthetic_ml generate --profile development --seed 42 --scenario baseline --output data/processed/synthetic_ml/my-development-42
.venv/Scripts/python.exe -m loometric.synthetic_ml generate --profile benchmark --seed 42 --scenario baseline --output data/processed/synthetic_ml/my-benchmark-42
```

The generation command prints a manifest fingerprint, content fingerprint, row
count and validation status. Retain that receipt independently. To audit the
recorded development run below, while the existing local files are present:

```powershell
.venv/Scripts/python.exe -m loometric.synthetic_ml audit --dataset data/processed/synthetic_ml/m08a-v1-development-42-baseline --expected-fingerprint e6af2f894ef3d9edf1c6cee75603f52cd26bc66a55fcaa9d8178056e49b17b3e
```

For your new path, supply **its own printed** manifest fingerprint. A changed
Python version, expanded configuration, profile or generated report can change
the manifest; do not replace a trusted receipt with a hash taken from an unknown
manifest merely to bypass a mismatch. The content fingerprint identifies the
normalized/derived JSONL files separately from environment and descriptive reports.

Supported declared seeds are 19, 42 and 73; scenarios are `baseline`, `disruption`
and `workload_surge`. Repeat generation with the selected values and distinct
output directories. To change supported ranges/dimensions, create an explicit
configuration JSON following the closed schema and pass `--configuration`; retain
its SHA-256 and use a new bundle. Changing units, target or process rules requires
a new dataset/generator version and decision, not an unnoticed edit to old data.

Exit 0 means valid publication/audit (warnings may be explicit); exit 2 means
invalid/missing/drifted input or output failure. No existing bundle is overwritten.
Generation validates and independently replays before publishing; manifest is
written last. An interrupted incomplete output is not a valid dataset and is not
automatically removed. Audit is read-only and rechecks file integrity, normalized
accounting, derived views and generator replay. No command fits or predicts a model.

## Actual generated exposure and diversity

Development is eight calendar weeks, exposing all weekdays in the declared
Monday–Saturday calendar, five stages and day/night conditions. Benchmark is
52 calendar weeks with more factories, lines and styles. Sizes derive from these
resource/date exposures and the predeclared holdouts, not a claimed minimum row
count for model quality. Neither profile establishes statistical power or factory
representativeness. Only one benchmark seed/scenario was measured; full nine-case
benchmark execution is supported but not claimed as run.

| Profile | Calendar / working-start dates | Factories | Lines | Catalog crews | Styles / standards | Observations |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Development | 56 / 48 | 3 | 30 | 120 | 6 / 30 | 1,360 |
| Benchmark | 364 / 312 | 5 | 75 | 300 | 12 / 60 | 29,370 |

| Profile | Train rows / dates | Validation rows / dates | Gap rows / dates | Reserved test rows / dates |
| --- | --- | --- | --- | --- |
| Development | 540 / 27 | 180 / 9 | 40 / 2 | 600 / 10 |
| Benchmark | 14,880 / 186 | 4,880 / 61 | 160 / 2 | 9,450 / 63 |

| Profile / partition | Inclusive local shift-start dates |
| --- | --- |
| Development train | 2030-01-07–2030-02-06 |
| Development validation | 2030-02-08–2030-02-18 |
| Development gaps | 2030-02-07 and 2030-02-19 |
| Development reserved test | 2030-02-20–2030-03-02 |
| Benchmark train | 2030-01-07–2030-08-10 |
| Benchmark validation | 2030-08-13–2030-10-22 |
| Benchmark gaps | 2030-08-12 and 2030-10-23 |
| Benchmark reserved test | 2030-10-24–2031-01-04 |

Every row on a local start date stays together. Absolute timestamps additionally
verify strict label maturity before the next development/evaluation cutoff. A
purged working date plus excluded Sundays can produce larger elapsed gaps.
Night shifts belong to their start date; label availability can lie on the next day.

| Future test population | Development rows | Benchmark rows | Interpretation |
| --- | ---: | ---: | --- |
| future_familiar | 80 | 1,680 | Familiar factory/line/crew/style on later dates |
| unseen_crew | 60 | 1,680 | New crew on familiar line/process/style |
| unseen_line | 200 | 2,520 | New line and nested crews; some new styles |
| unseen_factory | 200 | 1,890 | New factory with nested new lines/crews and some new styles |
| unseen_style | 60 | 1,680 | Reserved style with familiar factory/line/crew |

In development seed 42, training/validation each cover two factories, ten lines,
twenty crews and five styles. Test covers three factories, thirty lines, 120 crews
and six styles: one factory, twenty lines, 100 crews and one style are unseen
relative to training. The report provides counts for every identity axis within
each population, making nested novelty visible. Populations are disjoint by the
declared precedence, not independently isolated interventions.

## Actual quality and distribution checks

All **nine development combinations** (three seeds × three scenarios), the benchmark
42/baseline case, and an independent development 42/baseline replay completed with
status **VALID**, no variation warnings, validated accounting and successful typed
read-back. Each publication verified generator replay. Two separately written
development baseline bundles had identical bytes in **every file**, including
manifest and reports. Local generation/publication/read-back took 2.042–3.464s
per development combination and 65.785s for the measured benchmark; these are
host/run-specific durations kept outside deterministic dataset artifacts.

All eleven named QA check groups pass: schema/missingness, foreign keys, timestamps
and cutoff ordering, standards, capacity/piece accounting, unique observations and
exclusive resources, whole-date membership, label maturity/embargo, entity holdouts,
feature whitelist/availability, and five-stage/test-population coverage. There is
no composite score or evidence that the assumed distributions represent industry.

The following **validation target means** are descriptive generated outcomes,
not prediction accuracy, model selection or final-test results. The disruption
and surge mechanisms were declared before generation; lower/higher means are
expected consequences of those assumptions, not measured industrial effects.

| Development seed | Baseline | Disruption | Workload surge |
| --- | ---: | ---: | ---: |
| 19 | 0.820400887 | 0.621857610 | 0.917758927 |
| 42 | 0.804846592 | 0.610417161 | 0.900678056 |
| 73 | 0.797875799 | 0.604093522 | 0.892525002 |

| Baseline 42 statistic | Development train | Development validation | Benchmark train | Benchmark validation |
| --- | ---: | ---: | ---: | ---: |
| Valid ratio labels | 532 | 178 | 14,711 | 4,833 |
| Zero-capacity null labels retained | 8 | 2 | 169 | 47 |
| Target mean among valid labels | 0.813728748 | 0.804846592 | 0.804140584 | 0.803456284 |
| Target P95 | 1.180745686 | 1.203685776 | 1.185719514 | 1.190674049 |
| Target maximum | 1.292435578 | 1.309238951 | 1.675097726 | 1.638201856 |
| Values above one, retained | 119 | 35 | 3,080 | 1,009 |

Development baseline 42 has 18 difficult-condition rows in training and five in
validation. Finite counts need not exactly match configured probabilities. The
machine-readable reports retain exact decimal statistics, feature category counts,
numeric distributions/mean deltas, maturity boundaries and entity support. Target
statistics explicitly count valid labels separately from retained undefined labels.
There are **no reserved-test target distribution summaries or model scores**.
Reserved synthetic records are still checked for schema, stock/labor consistency
and exact serialized labels; that does not consume M01's historical final test.

## Provenance and preservation

| Recorded baseline bundle | Fingerprint |
| --- | --- |
| Development 42 manifest | `e6af2f894ef3d9edf1c6cee75603f52cd26bc66a55fcaa9d8178056e49b17b3e` |
| Development 42 JSONL content | `30045aaa720b5d3ae3aa567ca7eadf37baf1d177a22c4e819a14b76a3c968513` |
| Benchmark 42 manifest | `7e7dae049270675c2eac4f8ad05d55a9ac84cc9c1160e0a6b7e9f4010a64f7eb` |
| Benchmark 42 JSONL content | `f8d202a4771e23936a5f3076e57155f08c5bd8298624bf0ff154a7995596d784` |

Generated files remain ignored, including normalized tables, feature/label views,
quality/audit reports and manifests. No generated dataset fixture is needed in Git:
tests construct their own small synthetic records deterministically. Configuration,
code, ADR, dictionary and this measured verification/reproduction guide are versioned.
M01's raw data/model/split/report files and all frozen planning algorithms are
included in the independent preservation-hash check.
That check preserved **428 of 429** original tracked/existing-data files byte for
byte; README is the sole expected modified original. All 39 existing Python pins
match the environment, all frontend dependency/lock and ignore files are unchanged,
and local AGENTS/plan files remain ignored/untracked. Dictionary coverage checks
account for all **58 normalized fields** and **13 candidate inputs**; all 56 relative
links in the affected README/architecture/dictionary/quality/ADR documents resolve.

## Executed regression checks

| Command | Actual result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/synthetic_ml -q -p no:cacheprovider` | 80 passed in 26.06s |
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | 1,081 passed in 193.19s, normal pytest temporary directory |
| `.venv/Scripts/python.exe -m ruff check .` | Passed |
| `.venv/Scripts/python.exe -m ruff format --check .` | All checked files formatted |
| `.venv/Scripts/python.exe -m pip check` | No broken requirements |
| `npm run typecheck` in frontend | Passed |
| `npm run check` in frontend | Biome passed, 55 files |
| `npm test` in frontend | 139 tests across 6 files passed in 22.35s |
| `npm run build` in frontend | Type check and Vite passed, 65 modules |
| `npm run test:browser` in frontend | 10 passed in 1.1m; owned listeners closed and credentials discarded |
| `npm ls --depth=0`, `npm audit --audit-level=low` in frontend | 17 exact direct dependencies present, zero vulnerabilities |
| Receipt-bound CLI audit of development 42 baseline | VALID, 1,360 rows, replay verified, no training/conversion |

Tests include nine seeded/scenario property cases, generalization cohorts,
overnight/global maturity checks, insufficient embargo rejection, Decimal-context
isolation, overlapping planned exclusions, invalid/missing fields/standards,
duplicate resources, stock/labor inconsistency, noise with identical exposed inputs,
strict schema/digest/derived-view corruption and create-only output behavior.
Feature construction is tested with **all outcome/membership access forbidden**;
the train join is tested with **all non-training outcome values forbidden**.
A cold `python -S` run generates/validates while denying historical data access
and asserting no pandas, NumPy, sklearn, joblib or OR-Tools imports.

No focused/full test run failed. Routine formatting and patch-context corrections
were resolved before verified commits. Native/temp-directory permissions were
required for the existing pytest/browser tooling; the browser emitted only its
existing NO_COLOR/FORCE_COLOR warning. This Windows run does not establish Linux,
macOS, DST calendars or real factory behavior. No dependency or ignore rule changed.

## Remaining boundaries

This foundation makes synthetic units, timing and provenance explicit. It does not
provide external process validation, predictive performance, calibrated uncertainty
or operational controls. Future training requires its own declared baselines,
training-only preprocessing, null-label policy, validation selection and preserved
final-test protocol. Mapping into M02 requires explicit factory/resource/calendar
scope and absent order/route/capability evidence. WIP flow, rework and actual
attendance are unsupported planner concepts here. The attained ratio can exceed
one and is workload-censored, so it is not automatically `assumed_efficiency`.
No adapter or automatic conversion is authorized. M08A stops here.
