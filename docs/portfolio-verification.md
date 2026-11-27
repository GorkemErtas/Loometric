# Final portfolio verification

Verified on Windows / Python 3.13.14 / Node 26.13.0 / npm 11.20.0 / Edge,
2026-11-26. No public service was deployed.

M10A.4 passed its pre-merge review (263 selected regressions, frozen-source,
artifact, dataset and A/B receipt checks) and was fast-forward merged/pushed to
main at `bb8a4e230b12ba79d34370b5d6218b7c42150b83`. Its history was preserved.
Final development used the separate `feature/final-history-candidate-portfolio`
branch. The EXP-010 declaration/code and independent candidate receipt were
committed and pushed before their respective data-exposure boundaries.
The verified integration is commit `23a300ea1790c97a9ad9921c3a3f90c52a0f62d9`
(`feat(ml): integrate verified History Boost as fifth experimental model`);
its feature-branch remote SHA was independently confirmed after push.

Final pre-merge review checked implementation `29145d540e7ce3347f83bbbdbb3586aa2e784e21`
with a complete **1,561-test** backend run. No blocking correctness, security or
compatibility findings remain for the documented local-demo scope. Only this
verification record and exact startup instructions changed after that code
checkpoint; all four existing feature commits and verified model receipts remain
preserved. No additional feature, model, real training run or research experiment
was added by the pre-merge review.

## Scientific result

One actual residual estimator fit, no parameter search or favorable retry.
Four new development worlds and four fresh held-out worlds use the unchanged
synthetic process under matched baseline/disruption. All 41 predeclared demo
integration guards passed; A/B prediction vectors and reports are byte-identical.
History Boost was integrated as the fifth optional experimental model.

| Condition | Candidate MAE | RF Physics MAE | Candidate RMSE | Candidate macro R2 |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 0.05590135 | 0.10932347 | 0.09832114 | 0.81017281 |
| Disruption | 0.08893545 | 0.22453752 | 0.13297610 | 0.12239264 |

The [experiment](experiments/EXP-010-mature-history-candidate.md),
[aggregates](experiments/EXP-010-results.json) and
[execution metadata](experiments/EXP-010-execution.json) retain all comparisons,
slices, bootstrap intervals, resource measurements, guards and negative findings.
The additional mature-history information/new development data confound an
algorithm-only comparison. Actual worst baseline error rose 9.11%; missing-history
control was inferior, and disruption bias/first unannounced shocks remain.
Published holdout outcomes are now spent; B is reproduction, not new independent
validation. There is no factory validation, calibrated candidate interval or
operational promotion. **NO_ML_PROMOTION** is unchanged.

## Executed checks

| Check | Actual outcome |
| --- | --- |
| Complete final Python suite: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **1,561 passed**, 860.12s |
| Earlier implementation candidate/artifact/CLI/deployment/API focused regression | **65 passed**, 47.88s |
| Earlier V1/v2/v3 auth, watchdog and cancellation admission | **9 passed**, 1.41s; also included in the final full run |
| Current Python collection | **1,561 tests**, all executed together in the final full run |
| `npm test` | **199 passed** in 9 files, 20.72s |
| `npm run test:browser` | **13 passed**, 2.5min; real backend, Windows/Edge, no retries |
| Earlier fifth-model browser/screenshot refresh | **1 passed**, 30.0s |
| Production preview plus real five-model API smoke | Passed; five exact frozen-fixture outputs, ten pairwise differences, candidate REVIEW_REQUIRED |
| Ruff lint / `ruff format --check .` | Passed; **347 files** formatted |
| `pip check` / Biome / TypeScript / production build | Passed; Biome checked 64 files |
| Read-only `python -m loometric.final_candidate verify` | VERIFIED, NO_ML_PROMOTION |

Counts overlap; do not sum focused tests into a fictitious single full-suite run.
The earlier implementation checkpoint had 1,544 tests plus focused coverage for
later additions. The final pre-merge run supersedes that checkpoint with all
1,561 tests executed together. The earlier focused backend command was:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider `
  tests/experimental_ml/test_history_v3.py `
  tests/final_candidate/test_published_evidence.py `
  tests/api/test_deployment_boundary.py `
  tests/api/test_http.py::test_complete_http_workflow_matches_engines_and_is_reproducible
```

The additional API command selected `test_auth_origin_and_size_limits_do_not_launch_worker`,
`test_prediction_worker_uses_existing_hard_watchdog` and
`test_task_cancellation_does_not_release_slot_before_cleanup` in
`tests/experimental_ml/test_api.py`, each across all three versions.

Private fixtures exercise tampering before unpickling, incomplete/oversized
publication, revoked policy, environment/code/profile drift, verified-buffer
replacement, prohibited training/source reads, inconsistent history, candidate-only
selection, old-model prediction parity and legacy availability after v3 tampering.
Shared-slot cancellation and hard watchdog checks retain the original limits.
Existing prospective leakage/join/entity/receipt/reserved-label regressions pass.
Tests fit and score private mechanical fixtures only; actual EXP-009/010 datasets
and model-training/evaluation runs are not executed by the regression suite.

Browser workflows cover planning/optimization/cancellation, input import/export,
legacy predictions and all-five comparison, missing/stale history, review,
zero-capacity abstention, errors, keyboard/accessibility and mobile layout.
Accessibility scans report no tested WCAG-rule violations; this is not a full
accessibility certification. Owned listeners closed, session tokens were redacted
and discarded. The existing NO_COLOR/FORCE_COLOR warning remained harmless.

The additional production smoke served the compiled `/assets/` build through
`npm run preview` and connected a real loopback API. All five hypothetical point
estimates matched the retained API fixture exactly. Inference used 5.197823s and
226,971,648 peak committed bytes within 10s /768 MiB. Its owned listeners closed
and session token was discarded. The [startup guide](deployment.md#local-production-build-demo)
records the exact commands, connection settings and historical-context example.

## Integrity and deliverables

The sixty frozen source pins, four frozen candidate core files and both legacy
bundles were independently verified. Historical ten manifests/170 files and
EXP-009 eight manifests/136 files remain unchanged. EXP-009 A/B receipts and all
five deterministic payloads remain intact. EXP-010 sixteen manifests/96 source
files and A/B prediction/report hashes passed independent checks. Reserved labels
were hashed opaquely during integrity audits, never decoded for this milestone.

Only intentionally curated aggregates/receipts, code/config/tests/documentation
and actual [desktop](screenshots/final-predictions-desktop.png)/
[mobile](screenshots/final-predictions-mobile.png) screenshots are versioned.
Datasets, model binaries, full vectors, local journals, build outputs, secrets,
AGENTS.md and the local COMMIT_PLAN.md remain ignored/untracked.

An ignored local archive at `.tmp/portfolio-demo/loometric-model-bundles.zip`
contains exactly eleven verified v1/v2/v3 bundle files, 20,826,544 bytes, no
datasets/credentials. SHA256:
`3fbbbd465fa09eda20ead96ade5d271a5ba6e58cfc2d7ee74e68750e4ae3bddb`.
Its sibling receipt and CRC/file-by-file comparison were verified. Preserve the
independent source registries when transferring it; a checksum alone is not a
publisher authentication mechanism.

## Demo and deployment boundary

Use the [README setup](../README.md#local-setup),
[v3 preparation/verification](architecture/mature-history-experimental-inference.md#reproducible-artifact-preparation)
and [deployment guide](deployment.md). Local API plus the production frontend
preview is ready for a single-user portfolio demonstration. No automatic training
runs at startup/inference. Keep one backend worker and the existing resource caps.

The optional Caddy gateway template has exact-origin/loopback security regression
coverage, but Caddy was absent: template runtime, TLS provisioning, DNS and public
hosting were not executed or verified. Validate that configuration on the chosen
host before a separately authorized deployment. Windows artifact compatibility
is verified; Linux container portability and a second training-binary replay are
not claimed. No database, durable jobs or multi-tenant production service is added.

A sandbox Vitest attempt initially ran no tests because native worker spawning
was denied; the native rerun passed. A private fixture's early OpenBLAS import hit
the hard memory guard; applying the production thread settings before that test
import fixed the fixture. No resource limit or scientific criterion was relaxed.

## Turkish / English localization — 2026-11-27

The dashboard now defaults to `tr-TR` and offers `en-US` through the responsive
header selector. The typed catalog covers navigation, page content, forms, native
and domain validation, errors, code labels, tables, Gantt details, charts and model
evidence. Only the language string is persisted; API credentials, drafts, requests,
results and jobs retain their previous memory-only ownership.

Intl display preserves exact planning decimal digits and source time offsets.
Turkish identifiers, free text and long decimal tokens survive form edits, language
switches and scheduling JSON export without changing machine contracts. The five
model names, payload enum values and model outputs remain unchanged. No backend,
ML dependency, estimator, feature schema or research artifact was modified.

Frontend verification on the existing Windows / Edge environment: **217 unit and
component tests passed** (19.95 seconds), including 18 localization cases. Biome
checked 74 files; TypeScript and the production build passed. Vite reports a chunk
above its 500 kB advisory threshold; no dependency or lazy network loading was added.
The final complete real-backend browser run passed **18 workflows in 3.0 minutes**.
It covers all ten pages in both languages at 1440px and 390px, mobile navigation,
axe accessibility smoke checks, switching/persistence, errors, modals, exact Turkish
form/export data and unchanged five-model requests/results. The owned API/frontend
listeners closed and the temporary token was discarded. The historical Python
results above were not rerun for this frontend presentation task.

Current screenshots were captured from that run and copied byte-for-byte:

- [Turkish overview and selector](screenshots/localization-overview-tr.png),
  [English overview and selector](screenshots/localization-overview-en.png).
- [Turkish five-model desktop](screenshots/final-predictions-desktop.png),
  [English five-model desktop](screenshots/final-predictions-desktop-en.png).
- [Turkish mobile candidate](screenshots/final-predictions-mobile.png),
  [English mobile candidate](screenshots/final-predictions-mobile-en.png).

The bilingual model captures use one actual v3 response: predictions are
0.9036296370677777, 0.8945601867754494, 0.7628348220475517,
0.8919168184750277 and 0.834534223925279, with ten pairwise comparisons.
Switching language makes no additional request; JSON enum values, model names and
NO_ML_PROMOTION remain unchanged. All inputs are explicitly hypothetical.

One initial cold inference request reached the unchanged native deadline and
returned HTTP 504; later real five-model checks passed with the same limits.
Intermediate browser runs found missing dynamic demo text, a screen-reader label
escaping its mobile table scroll region, and notice-link contrast. These were
corrected without changing scheduling calculations or process budgets. A sandbox
Vitest attempt started no tests (EPERM); actual unit evidence comes from native
subprocess runs. Browser snapshots are smoke evidence, not WCAG certification.
