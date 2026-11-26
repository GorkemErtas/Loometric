# Final portfolio verification

Verified on Windows / Python 3.13.14 / Node 26.13.0 / npm 11.20.0 / Edge,
2026-11-26. No public service was deployed.

M10A.4 passed its pre-merge review (263 selected regressions, frozen-source,
artifact, dataset and A/B receipt checks) and was fast-forward merged/pushed to
main at `bb8a4e230b12ba79d34370b5d6218b7c42150b83`. Its history was preserved.
Final development uses the separate `feature/final-history-candidate-portfolio`
branch. The EXP-010 declaration/code and independent candidate receipt were
committed and pushed before their respective data-exposure boundaries.
The verified integration is commit `23a300ea1790c97a9ad9921c3a3f90c52a0f62d9`
(`feat(ml): integrate verified History Boost as fifth experimental model`);
its feature-branch remote SHA was independently confirmed after push.

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
| Full Python checkpoint: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **1,544 passed**, 850.22s |
| Final candidate/artifact/CLI/deployment/API focused regression | **65 passed**, 47.88s |
| V1/v2/v3 auth, watchdog and cancellation admission | **9 passed**, 1.41s |
| Current Python collection | **1,561 tests**; the 17 cases added after full-suite collection and subsequent changes are covered by the final focused commands |
| `npm test` | **199 passed** in 9 files, 20.85s |
| `npm run test:browser` | **13 passed**, 2.4min; real backend, Windows/Edge, no retries |
| Final fifth-model browser/screenshot refresh | **1 passed**, 30.0s |
| Ruff lint / `ruff format --check .` | Passed; **346 files** formatted |
| `pip check` / Biome / TypeScript / production build | Passed; Biome checked 64 files |
| Read-only `python -m loometric.final_candidate verify` | VERIFIED, NO_ML_PROMOTION |

Counts overlap; do not sum focused tests into a fictitious single full-suite run.
The final focused backend command was:

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
