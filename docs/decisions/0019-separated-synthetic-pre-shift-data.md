# ADR 0019: Separate synthetic standard-capacity attainment dataset

Status: accepted for M08A before generation. All ranges are synthetic assumptions.

## Context and options

M07B established that M01's historical target has unknown units, shift grain and
crew mappings. Reusing its name, changing its CSV or claiming a conversion would
erase that distinction. Options are reinterpretation, an arbitrary wide random
table, or a separate normalized synthetic process with explicit labor accounting.
Choose the last. No industrial distributions or factory evidence are asserted.

## Decision

Create synthetic-ml-v1, independent of M01 and frozen M02–M04 contracts. One
observation is one dedicated qualified crew, line, stage, style/order and aware
shift. Day/night crews are distinct. Opening stage WIP and planned releases are
exogenous independent order inputs, not a simulated cross-stage factory flow.

Define standard_capacity_attainment = completed good pieces × approved standard
worker-minutes/piece ÷ frozen planned available worker-minutes. The denominator
uses planned staffing and unioned scheduled exclusions, not realized attendance
or unplanned downtime. This is demand-censored attained output per declared labor
budget, not intrinsic efficiency. Only completed pieces earn credit; incomplete
pieces earn none. Zero denominator yields an explicit null label/status, never
imputation. Positive numerator at zero capacity is invalid. Targets above one are
allowed; no clipping or automatic mapping to planning's [0,1] efficiency occurs.
Exact integer/rational arithmetic controls production counts, with fixed 28-digit
Decimal label presentation and decimal strings on the wire.

Generate outcomes with local keyed random streams, latent line/crew effects,
nonlinear skill/complexity/shift interactions, attendance, unplanned losses,
bounded process noise and rare difficult conditions. No latent or realized field
enters the pre-shift feature whitelist. Plans, reference records, outcomes and
membership remain distinct normalized tables. Feature construction never reads
outcomes or fits transformations. A label join explicitly selects training only.

Predeclare chronological whole-local-start-date splits, purged boundary dates and
five future test populations: familiar entities, unseen crew, line, factory and
style. Entity holdouts are chosen before outcomes. Nested unseen-factory/line
identities are reported honestly, not claimed to isolate independent causal effects.
Audit generated labels only for integrity/physical consistency; reserved-test target
statistics/model scoring remain excluded. Future learning/holdout use needs separate
scope. Store generated datasets/reports under existing ignored data paths with
version/configuration/content/environment fingerprints and create-only publication.

## Consequences

The dataset supports reproducible software experiments, not externally validated
factory prediction. Staffing, skill, loss and rate ranges are transparent chosen
assumptions. Finite completed pieces create demand and quantization effects; the
target is not a linear equation of exposed features. M02 unit equivalence can be
documented while WIP, attendance, provenance and >1 target handling need explicit
future adapters. No adapter, model training, serving, scheduler connection or
readiness upgrade is implemented. M01 evidence and reserved final test stay intact.
