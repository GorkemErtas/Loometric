# ADR 0001: Local Python data foundation

Status: accepted for Task 1.

## Context

Loometric needs a defensible data and prediction-time contract before model or
application work. The initial input is one local CSV; pre-shift field availability,
WIP reporting rules, and observation grain are not fully established by the file.

## Decision

Use a `src`-layout Python package with pandas for tabular analysis, pytest for
behavioral checks, and Ruff for linting and formatting. Keep dependency and tooling
configuration in `pyproject.toml`. Use type hints and small functions/dataclasses;
defer a static type checker until its value outweighs extra setup.

Separate the schema, ingestion/normalization, validation, descriptive reporting, and
feature-availability policy. A small CLI connects them. This keeps validation reusable
if a later FastAPI service needs it without introducing service or storage abstractions.

Read source values as text, parse dates explicitly as month/day/year, and normalize a
copy. Validate source order before any sorting. Preserve missing WIP and fractional
staffing. Use structured errors for broken data contracts and warnings for findings
that require business review. Report errors before training rather than silently
cleaning them away. Every source field has an availability decision.

Generate deterministic Markdown with a SHA-256 of the input bytes. Keep raw data and
local environments out of Git. The command runs locally with no network calls,
telemetry, credentials, experiment service, or database. Tests use synthetic records,
never a replacement dataset presented as real observations.

## Consequences

The report is readable and reproducible, and the same checks can be reused later.
Pandas is the sole runtime dependency. Dependency ranges live in `pyproject.toml`;
an exact lockfile is deferred because there is no model-training baseline to reproduce
yet. Record interpreter/tool versions when reporting verification.

Invalid schemas and numeric/date failures prevent a successful validation exit.
Department WIP missingness, target overachievement, source-order reversals, and
duplicate keys remain visible warnings. Warnings must be reviewed even when exit code
is zero. The profiler does not infer causal relationships or certify feature timing.

No React, Node.js, PostgreSQL, FastAPI, XGBoost, or OR-Tools scaffolding is added now.
There is no generic repository layer, plugin framework, pipeline engine, notebook
dependency, or model interface. Introduce future components only when a concrete
task needs them. Model training and web development are outside this decision.

