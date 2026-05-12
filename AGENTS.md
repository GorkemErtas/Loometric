# Loometric — Codex Engineering Instructions

> This file is the standing engineering contract for all Codex tasks in this repository. Read it before planning or changing code. Also read `docs/COMMIT_PLAN.md`, relevant architecture decisions, and the affected modules. If instructions conflict, explain the conflict and request clarification rather than silently overriding requirements.

## 1. Product mission and boundaries

Loometric is a **local-only, portfolio-grade garment production intelligence platform**. It will combine production analytics, pre-shift productivity forecasting, production scheduling optimization, and scenario comparison. It is not an SAP product and must not imply access to real Sun Tekstil data or systems. Do not deploy, publish services, connect external production systems, or introduce cloud infrastructure without explicit approval.

Think of the **whole product** before every change: user workflows, data contracts, prediction-time information availability, scheduling constraints, persistence, API boundaries, UI behavior, tests, reproducibility, and future maintainability. Implement only the scope requested in the current task. Avoid speculative functionality and overengineering.

Planned stack (adopt incrementally, not all at once): Python, pandas, scikit-learn, XGBoost/LightGBM when justified, FastAPI for ML, OR-Tools for optimization, Node.js/TypeScript API, PostgreSQL, React/TypeScript dashboard, Docker Compose for local development. Favor existing project conventions over adding new dependencies.

## 2. Engineering decision-making

- Act as a senior software engineer and applied ML engineer: identify assumptions, constraints, failure modes, alternatives, and tradeoffs before implementing nontrivial changes.
- Use clean code and pragmatic clean architecture: clear domain boundaries, dependency direction, separation of concerns, small cohesive modules, explicit interfaces at real boundaries, descriptive names, and minimal duplication.
- Apply SOLID where it improves maintainability; do not create interfaces, factories, layers, or abstractions without a concrete need.
- Preserve backwards compatibility where practical; document migrations and contract changes.
- Validate inputs, handle errors deliberately, avoid silent failures and hidden mutable state, use type hints/types, structured logging, configuration outside source code, and safe defaults.
- Keep data ingestion, feature engineering, training, evaluation, inference, scheduling, and presentation independently testable.
- Favor deterministic, reproducible execution. Pin or lock dependencies, set seeds where relevant, and record environment and configuration.
- Use test-driven thinking: add or update targeted unit, integration, contract, and end-to-end tests as appropriate. Never claim tests passed unless executed.
- Security basics: no secrets in Git, no hard-coded credentials, parameterized queries, input validation, least-privilege local configuration.
- For meaningful architecture or methodological changes, add a short Architecture Decision Record under `docs/decisions/` with context, options, decision, and consequences.

## 3. ML scientific rigor

Initial real-data task: predict `actual_productivity` using the garment worker productivity dataset. The primary intended use case is **pre-shift forecasting**, not post-shift explanation. A feature is allowed only if its value would be available at the actual prediction timestamp. Explicitly assess `incentive`, `idle_time`, `idle_men`, `over_time`, `wip`, and all other candidate features for timing and leakage. Treat planned and realized values as different concepts. Do not silently impute, drop, clip, or relabel data.

- Define prediction timestamp, target, feature availability, unit of analysis, and evaluation protocol before model training.
- Start with a naive baseline, then simple interpretable models, then more complex models only if justified by measured improvement.
- Use a reproducible chronological split where feasible; assess temporal overlap, team grouping, and leakage. Keep a final holdout untouched during model selection. Select models using training/validation only, then evaluate the chosen model once on the final holdout.
- Report MAE, RMSE, R² and relevant distributional or slice metrics for regression. Report relative improvements against an explicitly named baseline; never invent results.
- Record each experiment's dataset fingerprint, split definition, feature set, preprocessing, seed, parameters, dependency versions, metrics, runtime, and conclusions.
- Separate real-world dataset evaluation from synthetic simulation outcomes. Never represent synthetic delay prediction performance as externally validated factory performance.
- Hyperparameter tuning is **not** fine-tuning a pretrained language model; call it hyperparameter optimization. Prevent test-set tuning and data leakage inside cross-validation pipelines.
- Save reports in `docs/experiments/` using stable experiment IDs (e.g., `EXP-001-naive-baseline.md`). Save generated artifacts in appropriate ignored paths unless small, useful, and intentionally versioned.
- If a proposed result cannot be reproduced, state the limitation and do not promote the model.

## 4. Optimization and simulation rigor

Model production tasks, capacities, shifts, precedence, compatible lines, material availability, and setup times explicitly. Start with a deterministic reference scheduler (e.g., earliest due date), then compare OR-Tools solutions on the **same instances and constraints**. Report feasibility, constraint violations, objective components, lateness/tardiness, utilization, and runtime. Do not claim optimality without solver evidence. Keep scenario assumptions and synthetic data generation documented and seeded.

## 5. Frontend/backend product quality

Design workflows around planners and operations analysts: order intake, production status, capacity, risk, scheduling, scenario comparison, and evidence-based reporting. Prefer accessible, responsive, understandable UI over decorative dashboards. Define API schemas, validation, error states, loading states, and data provenance. Distinguish measured facts, ML predictions, optimizer suggestions, and demo/synthetic values in the UI. Avoid fabricated business KPIs.

## 6. Task execution protocol (every Codex request)

1. Read `AGENTS.md`, `docs/COMMIT_PLAN.md`, relevant ADRs, and the code affected by the task.
2. Summarize the requested scope, dependencies, acceptance criteria, and any assumptions or risks.
3. Check how the change fits the complete architecture and the next planned phases; do not implement unrelated future features.
4. Make the smallest coherent set of changes with tests and documentation.
5. Run relevant formatting, linting, tests, and reproducibility checks; report exactly what ran, passed, failed, or could not run.
6. Update `docs/COMMIT_PLAN.md` to reflect actual progress, affected files, validation evidence, and a suggested commit boundary. Update ADRs and experiment reports when appropriate.
7. At the end, report: summary, changed files, design decisions, actual verification results, known limitations, suggested commit message(s), and the next logical task.

Never silently modify unrelated files, delete data, rewrite history, or perform destructive operations. Ask before substantial dependency, architecture, or schema changes.

## 7. Commit and history policy

- **Do not run `git commit`, `git push`, `git rebase`, `git reset --hard`, force-push, alter Git author/committer timestamps, or create tags unless explicitly instructed for that exact action.**
- The user controls all commits, including any date metadata. Never invent an earlier development history or falsify experiment timestamps. Preserve original history when importing genuinely older work.
- Plan small, reviewable, logically ordered commits with Conventional Commits (`chore:`, `data:`, `feat:`, `fix:`, `test:`, `refactor:`, `docs:`).
- Record **proposed** commits separately from **completed** commits; do not mark a commit complete merely because code is implemented. Only record a commit hash after verifying it exists.
- If one task spans several commits, propose an ordered staging plan with exact file groups and dependencies. Avoid splitting changes into nonfunctional or misleading historical states.
- Every ML experiment should have a reproducible report and corresponding code/config changes; note actual measured improvements and regressions, not just successes.
- Do not backdate or fabricate changelog entries. Use actual experiment execution dates when known, otherwise omit dates.

## 8. Documentation source of truth

- `AGENTS.md`: permanent development rules.
- `docs/COMMIT_PLAN.md`: current roadmap, task status, suggested commit groups, and verification checklist.
- `docs/decisions/`: architectural and scientific decisions.
- `docs/experiments/`: immutable-in-spirit experiment records; corrections should be explicit.
- `README.md`: concise user-facing project description, local setup, current capabilities, and limitations.

If the repo is newly initialized, create only the directories and files needed for the current task. Do not pretend future modules already exist.
