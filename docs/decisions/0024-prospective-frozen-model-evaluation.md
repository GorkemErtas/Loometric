# ADR 0024: Prospective frozen-model replication before new signals

Status: accepted for M10A.1 protocol preparation (2026-11-26), before generation.

## Context and options

EXP-008 improves retained benchmark point error, but its outer validation is spent
and hidden disruption/subgroup/tail failures remain. Options are retune against
those diagnostics, consume existing reserved tests, immediately implement the full
v2 signal proposal, or prospectively compare frozen M09B models on new worlds.
Choose the bounded frozen comparison, as requested. This supplies future research
evidence without promoting a model or changing a production workflow.

## Decision

Predeclare EXP-009 in `configs/prospective_evaluation_v1.json` before outcome
generation/inspection. Pin four model artifacts, environment/source receipts,
13-feature/target/units and the original generator law. Use seeds 101/211/307/401,
112-day calendars starting 2032-01-05 and matched baseline/hidden-disruption arms.
Score only the 18 new validation dates: 360 planned observations/seed/condition.
Other new source label partitions and every old reserved label remain opaque.

Raw generator entity names repeat across seeds. Scope identity by world and local
ID, audit seed/profile provenance and qualified disjointness, and preserve shared
identities within matched conditions. Namespace separation alone is not proof of
independent factory profiles. Cutoff/snapshot/reference availability and a later
synthetic calendar must be verified. Seal feature-only predictions before reading
the new validation labels; no model/preprocessing fit, tuning or calibration.

Separate all-defined-target raw scientific errors from unchanged policy coverage,
support and abstention metrics; never make a model appear better by silently
discarding hard rows. Predeclare equal-world matched comparisons, one primary
RF Physics/Forest12 baseline contrast, exhaustive four-world resampling and
date-block sensitivity. Freeze subgroup/tail/support and replication criteria.
These classify evidence only. NO_ML_PROMOTION is unconditional; historical gates
are untouched. Four simulator seeds do not establish factory confidence or coverage.

Use separate create-only ignored dataset/receipt/result roots and new experiment
dataset identities. Future receipts are unknown until independently reproduced
generation and label-blind registration; never invent their hashes. Keep timing
outside deterministic receipts and require independent expected ledger integrity.
The future isolated offline harness must enforce fixed zero-fit/time/memory/size
budgets without changing existing API/worker/serving contracts.

## Consequences

This milestone adds declaration/metadata checks only. The
[EXP-009 protocol](../experiments/EXP-009-prospective-frozen-evaluation.md) defines
samples, metrics, criteria, limitations and the separately authorized implementation
plan. No prospective outcomes, actual sample audit, scores or fits are produced.
Existing data/artifacts, generators, promotion gates, reserved tests, serving and
planning remain unchanged. No dependency, signal-bearing dataset v2, deployment,
model replacement or operational claim is introduced.
