# Synthetic-ml-v2: proposed observability and diversity experiment

Status: research design proposal only for M09A (2026-11-23). No v2 data, generator,
schema migration or serving artifact is created. V1 and its reserved tests remain
unchanged. The [EXP-008 diagnosis](../experiments/EXP-008-ml-improvement-research.md)
must determine which hypotheses deserve a separately authorized pilot.

## Problem and design boundaries

The v1 process has deliberately hidden persistent line/crew factors and unannounced
disruption. Baseline/disruption can have exactly the same pre-shift feature vector
and different outcomes. Increasing rows cannot reveal an absent cause. Small
development stage cells also repeat only a few entity contexts. WIP/release split
has no separate response mechanism, downtime is redundant with available minutes,
and machine availability is constant after undefined targets are excluded.

Keep the same declared target/grain/units and explicit undefined-capacity policy.
Use a new dataset/generator/feature-schema identity, independent configuration,
content receipts and output root. Never reinterpret or overwrite v1. Do not make
the simulation easier solely to raise model scores or force a weak field to matter.

## Testable hypotheses

| Hypothesis | Controlled design | Evidence that would support it |
| --- | --- | --- |
| Planned-load representation is sufficient for some v1 failures | Keep the original 13 inputs; compare frozen raw and engineered candidates on new development worlds | Matched gains persist across entities/seeds/stages without new information |
| Persistent context is partly learnable from mature history | Add explicit per-crew/line historical summaries based only on already available completed shifts | Forward-only history improves familiar contexts; missing-history/unseen-entity fallback remains explicit |
| A realistic precursor can reduce announced-shift bias | Generate noisy pre-shift absence/material/machine-risk forecasts with timestamped sources and forecast error | Gain over a no-signal control, with measured signal reliability and no oracle scenario field |
| Unannounced shocks remain intrinsically uncertain | Keep a separate shock arm with no pre-shift signal | Matched identical-feature diagnostics retain an error floor and uncertainty degradation |
| Entity diversity matters more than repeated rows | Hold shift count fixed and vary independent line/crew profiles per stage; separately vary repeats per entity | Learning curves identify which sampling axis improves robust errors |
| WIP/release split matters only under an explicit timing mechanism | Keep it a negative control unless timed material readiness is separately justified | Any new effect traces to declared release/material timing, not an arbitrary coefficient |

## Proposed data contract and prediction timestamp

Prediction remains thirty minutes before an aware shift starts. Keep normalized
factories/lines/crews/styles/standards/shifts/orders/plans/outcomes/membership and
add a versioned snapshot provenance table: source_record_id, source_kind, observed_at,
available_at, forecast_for, entity_scope, units and synthetic assumption identity.
Every joined value must be available by cutoff. Late observations and revised
forecasts remain separate versions; never backfill an earlier snapshot.

Potential inputs require separate justification, not automatic inclusion:

- Explicit derived planned labor/load/quantum with the existing unit definitions.
- Forecast attendance count and forecast uncertainty, generated from pre-cutoff
  information with controlled, documented reliability.
- Material-ready opening stock and time-bucketed planned releases, only if a
  separately declared material-arrival mechanism exists.
- Pre-shift maintenance/absence/material-risk indicators with false positives and
  false negatives; no exact latent disruption, future-event or scenario flag.
- Mature past-shift attainment/error summaries with counts and age, derived from
  source records whose labels were available before the new cutoff. No current
  shift label, future neighbor, full-period normalization or full-period target encoding.

IDs are joins/provenance, not numeric predictors. History needs explicit cold-start
and unseen-entity behavior; missing history cannot be silently imputed as known
performance. Realized workers, unplanned losses, difficult-event flags, completed
pieces, closing WIP and demand censoring remain outcome-only fields.

## Controlled generator pilot and stopping rule

Propose four new development-world seeds 101/211/307/401, selected before outcomes;
they do not replace any current world or final test. For each seed compare matched
signal/no-signal arms using common planned conditions and separate keyed streams.
Retain unpredictable shock/noise arms rather than making every loss observable.
The following are concrete proposed pilot assumptions, not industrial estimates:

| Design parameter | Proposed setting |
| --- | --- |
| Calendar and exposure | 112 calendar days, Mon–Sat, at most 40 observations per working date/world |
| Entity diversity | 4/8/16 independent line profiles per stage; two dedicated shift crews per profile |
| Matched sampling | Operate four line profiles/stage/date with balanced rotation; keep total observations fixed across diversity tiers |
| Prior risk state | Factory-shift state sampled before forecast time, prevalence 0.10 |
| Observable forecast | Noisy pre-shift state measurement, sensitivity 0.75/specificity 0.85 against the prior state |
| Later disruption | After cutoff, independent innovation gives event probability 0.60 in high-risk states and 0.05 otherwise; event multiplies rate by 0.8 and adds 60 loss minutes, bounded by availability |
| Unannounced difficult event | Retain independent probability 0.025 with the existing difficult-condition mechanism |
| Forecast timing | Source available 45 minutes before shift; snapshot 35 minutes before shift; prediction 30 minutes before shift |
| No-signal control | Forecast independent of the prior state, with the same marginal distribution; matched outcomes/plans unchanged |
| Partition reservation | Whole-date 50% train, 20% development, 10% calibration, 20% reserved future/entity tests, with purged globally mature boundaries |

The forecast measures an earlier risk state, not the eventual event/target. The
future innovation remains unknown at cutoff. Measure forecast reliability on
authorized development only; do not equate state-detection parameters with
calibrated event probabilities. Reject a forecast copied from realized attendance,
losses, future events or labels. Include unreliable forecasts as a negative control.

Start with the smallest design that supplies at least four independent line profiles
and two distinct shift crews per stage in each development world. Compare 8 and 16
line-profile variants while holding the total number of observed shifts fixed.
At fixed profiles, compare nested training-only 12/24/48-date prefixes to study
repeats per entity, keeping evaluation dates locked and the calendar cap unchanged.
Preserve stage/shift coverage and explicit rare-condition counts. Use training-only
pilot learning curves to choose scale; do not inflate rows until a promotion gate passes.

Stop expansion when prespecified robust MAE/tail gains plateau across profile
counts or when additional repeats fail to improve entity-disjoint diagnostics.
Report failure/uncertainty rather than choosing a favorable world or stage.
At most 24 seed/signal/entity-tier cases would produce 92,160 observation exposures
at this calendar/exposure cap, including matched repeats. This is an upper budget,
not a request to generate them now. A proposed plateau rule is less than 2% macro
development MAE improvement from 8 to 16 profiles without tail/stage improvement;
stop expansion rather than searching for a favorable world. Freeze these budgets,
assumptions and selection/stopping details in the separately authorized pilot
declaration before generation. Current promotion gates remain unchanged.

## Evaluation and acceptance requirements

Use chronological train/development/calibration partitions with purged whole dates
and globally mature labels. Reserve new entity/world/future tests before generation;
do not consume any v1 final test. Use development folds for selection and keep a
distinct calibration period if claiming calibrated intervals. Temporal dependence,
entity clustering and shift must be assessed; exchangeability is not assumed.

Compare Grouped Mean, unchanged M08C candidates and the frozen EXP-008 research
candidate on matched observations/constraints. Report MAE, RMSE, R², bias, tails,
stage/shift/workload/staffing slices, entity counts, signal reliability, uncertainty
coverage/width and identical-input error limits. Preserve existing promotion gates;
any proposed policy revision is a separate prospective decision, never a rewrite
of EXP-006. Include raw 13, derived-only and proposed-signal ablations.

A pilot is useful only if it clarifies observability/diversity tradeoffs with
reproducible receipts, no leakage and explicit negative results. Better simulated
scores are not evidence of real factory accuracy. Any eventual serving change,
factory evidence collection or scheduling integration requires a separate task.
