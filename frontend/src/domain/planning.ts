import { isLosslessNumber } from "lossless-json";
import { requireCapacityUnits, scheduleReport } from "./adapters";
import { ContractError, decimal, flag, integer, list, object, text, texts } from "./json";
import type { Interval } from "./models";

export const metricDefinitions = [
  ["scheduled_orders", "Completed orders", "order", "integer"],
  ["unscheduled_orders", "Incomplete orders", "order", "integer"],
  ["partial_orders", "Partially allocated orders", "order", "integer"],
  ["scheduled_units", "Finished units", "piece", "integer"],
  ["unscheduled_units", "Unfinished units", "piece", "integer"],
  ["scheduled_operations", "Allocated operations", "operation", "integer"],
  ["unscheduled_operations", "Unscheduled operations", "operation", "integer"],
  ["allocated_stage_units", "Allocated stage units", "stage_piece", "integer"],
  ["on_time_completed_orders", "On-time completed orders", "order", "integer"],
  ["late_completed_orders", "Late completed orders", "order", "integer"],
  ["total_tardiness_minutes", "Completed-order tardiness", "minute", "integer"],
  [
    "priority_weighted_tardiness_minutes",
    "Priority-weighted tardiness",
    "priority_weighted_minute",
    "integer",
  ],
  ["makespan_minutes", "Makespan", "minute", "integer"],
  ["available_line_minutes", "Available line time", "line_minute", "decimal"],
  ["occupied_line_minutes", "Occupied line time", "line_minute", "decimal"],
  ["line_utilization", "Line utilization", "ratio", "decimal"],
  ["available_worker_minutes", "Available crew time", "worker_minute", "decimal"],
  ["consumed_worker_minutes", "Consumed crew time", "worker_minute", "decimal"],
  ["unused_worker_minutes", "Unused crew time", "worker_minute", "decimal"],
  [
    "available_standard_minutes",
    "Available standard capacity",
    "standard_worker_minute",
    "decimal",
  ],
  ["consumed_standard_minutes", "Consumed standard capacity", "standard_worker_minute", "decimal"],
  ["unused_standard_minutes", "Unused standard capacity", "standard_worker_minute", "decimal"],
  ["standard_capacity_utilization", "Standard capacity utilization", "ratio", "decimal"],
  [
    "rounding_slack_standard_minutes",
    "Reserved rounding slack",
    "standard_worker_minute",
    "decimal",
  ],
] as const;
export type MetricKey = (typeof metricDefinitions)[number][0];
export type Metrics = Record<MetricKey, string | null>;
export const objectives = [
  "unfinished_units",
  "priority_weighted_tardiness_minutes",
  "makespan_minutes",
] as const;
export interface ObjectiveComparison {
  relation: "BETTER" | "WORSE" | "TIE";
  deciding: string | null;
  before: Record<string, string>;
  after: Record<string, string>;
  changes: Record<string, string>;
}
export interface Allocation extends Interval {
  orderId: string;
  stage: string;
  lineId: string;
  assignmentId: string;
  shiftId: string;
  profileId: string;
  quantity: string;
  workerMinutes: string;
  standardMinutes: string;
}
export interface OrderOutcome {
  id: string;
  status: string;
  quantity: string;
  finished: string;
  unfinished: string;
  stages: string[];
  completion: string | null;
  tardiness: string | null;
  reasons: string[];
}
export interface VerifiedPlan {
  instanceId: string;
  fingerprint: string;
  feasible: boolean;
  complete: boolean;
  status: string;
  allocations: Allocation[];
  unscheduled: { orderId: string; stage: string; quantity: string; reason: string }[];
  metrics: Metrics | null;
  orders: OrderOutcome[];
  violations: string[];
}
export interface Dispatch extends VerifiedPlan {
  horizon: Interval;
  algorithm: string;
}
export interface OptimizerEvidence {
  status: string;
  solverStatus: string | null;
  version: string | null;
  proven: string;
  full: boolean;
  incumbentPhase: string | null;
  retained: boolean;
  candidate: VerifiedPlan | null;
  comparison: ObjectiveComparison | null;
  phases: {
    phase: string;
    objective: string;
    status: string;
    value: string | null;
    bound: string | null;
    proven: boolean;
  }[];
}
export interface Evaluation {
  selected: VerifiedPlan;
  greedy: VerifiedPlan;
  producer: "greedy" | "cp_sat";
  algorithm: string;
  fallback: string | null;
  proven: string;
  full: boolean;
  optimizer: OptimizerEvidence;
}
export interface MetricDelta {
  before: string | null;
  after: string | null;
  absolute: string | null;
  percentage: string | null;
  points: string | null;
  status: "DEFINED" | "BASELINE_ZERO" | "NULL_VALUE";
  unit: string;
}
export interface Comparison {
  id: string;
  label: string;
  fingerprint: string;
  demandFingerprint: string;
  baseline: Evaluation;
  scenario: Evaluation;
  baselineId: string;
  baselineFingerprint: string;
  scenarioId: string;
  scenarioFingerprint: string;
  baselineHorizon: Interval;
  scenarioHorizon: Interval;
  deltas: Record<MetricKey, MetricDelta>;
  selectedComparison: ObjectiveComparison;
  greedyComparison: ObjectiveComparison;
  audit: {
    index: string;
    operation: string;
    target: string;
    changed: boolean;
    before: unknown;
    after: unknown;
  }[];
  limitations: string[];
  assumptions: string[];
}
export type JobStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED" | "EXPIRED";
export type JobKind = "scheduling" | "scenarios";
export interface JobInfo {
  id: string;
  kind: JobKind;
  status: JobStatus;
  phase: string;
  submitted: string;
  started: string | null;
  completed: string | null;
  expires: string | null;
  cancellationRequested: boolean;
  canCancel: boolean;
  hasResult: boolean;
  errorCode: string | null;
}
export type JobOutput =
  | {
      kind: "scheduling";
      evaluation: Evaluation;
      horizon: Interval;
      instanceId: string;
      fingerprint: string;
    }
  | { kind: "scenarios"; comparison: Comparison };
export interface JobResult {
  id: string;
  output: JobOutput;
  wallSeconds: string | null;
}
export const terminal = (status: JobStatus) => !["QUEUED", "RUNNING"].includes(status);
export function choice<T extends string>(value: unknown, allowed: readonly T[]): T {
  const s = text(value);
  if (!allowed.includes(s as T)) throw new ContractError();
  return s as T;
}
export const nullableText = (v: unknown) => (v === null ? null : text(v));
export function fingerprint(v: unknown): string {
  const s = text(v);
  if (!/^[a-f0-9]{64}$/.test(s)) throw new ContractError();
  return s;
}
export function scalar(v: unknown): string | null {
  if (v === null) return null;
  const s = isLosslessNumber(v) ? v.value : text(v);
  decimal(s.startsWith("-") ? s.slice(1) : s);
  return s;
}
export function interval(v: unknown): Interval {
  const r = object(v);
  const start = text(r.start),
    end = text(r.end);
  if (
    ![start, end].every(
      (s) =>
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(s) &&
        Number.isFinite(Date.parse(s)),
    ) ||
    Date.parse(end) <= Date.parse(start)
  )
    throw new ContractError();
  return { start, end };
}
function metrics(v: unknown): Metrics {
  const r = object(v);
  requireCapacityUnits(r);
  if (r.tardiness_scope !== "COMPLETED_ORDERS_ONLY") throw new ContractError();
  return Object.fromEntries(
    metricDefinitions.map(([key, , , kind]) => [
      key,
      r[key] === null ? null : kind === "integer" ? integer(r[key]) : decimal(text(r[key])),
    ]),
  ) as Metrics;
}
function plan(proposal: unknown, verification: unknown, quality: unknown): VerifiedPlan {
  const p = object(proposal),
    v = object(verification);
  if (integer(p.schema_version) !== "1" || p.policy_version !== "whole-stage-minute-v1")
    throw new ContractError();
  const feasible = flag(v.feasible),
    complete = flag(v.complete);
  if ((feasible && quality === null) || (!feasible && quality !== null)) throw new ContractError();
  const m = quality === null ? null : object(quality);
  return {
    instanceId: text(p.instance_id),
    fingerprint: fingerprint(p.instance_fingerprint),
    feasible,
    complete,
    status: feasible ? (complete ? "VALID_COMPLETE" : "VALID_PARTIAL") : "INVALID",
    violations: list(v.violations).map((item) => text(object(item).code)),
    allocations: list(p.allocations).map((item) => {
      const a = object(item);
      return {
        orderId: text(a.order_id),
        stage: text(a.stage),
        lineId: text(a.line_id),
        assignmentId: text(a.assignment_id),
        shiftId: text(a.shift_id),
        profileId: text(a.profile_id),
        quantity: integer(a.quantity),
        ...interval(a.interval),
        workerMinutes: decimal(text(a.consumed_worker_minutes)),
        standardMinutes: decimal(text(a.consumed_standard_minutes)),
      };
    }),
    unscheduled: list(p.unscheduled).map((item) => {
      const a = object(item);
      return {
        orderId: text(a.order_id),
        stage: text(a.stage),
        quantity: integer(a.quantity),
        reason: text(a.reason),
      };
    }),
    metrics: m ? metrics(m) : null,
    orders: m
      ? list(m.orders).map((item) => {
          const o = object(item);
          return {
            id: text(o.order_id),
            status: choice(o.status, ["COMPLETED", "PARTIAL", "UNSCHEDULED"]),
            quantity: integer(o.quantity),
            finished: integer(o.completed_units),
            unfinished: integer(o.unscheduled_units),
            stages: texts(o.allocated_stages),
            completion: nullableText(o.completion_at),
            tardiness: o.tardiness_minutes === null ? null : integer(o.tardiness_minutes),
            reasons: texts(o.unscheduled_reasons),
          };
        })
      : [],
  };
}
export function dispatchReport(value: unknown): Dispatch {
  const r = object(value);
  const validated = scheduleReport(r);
  const result = plan(r.schedule, r.verification, r.metrics);
  if (result.fingerprint !== validated.fingerprint || result.instanceId !== validated.instanceId)
    throw new ContractError();
  return { ...result, horizon: interval(r.horizon), algorithm: validated.algorithm };
}
function objectiveComparison(value: unknown): ObjectiveComparison {
  const r = object(value);
  const values = (v: unknown) =>
    Object.fromEntries(
      objectives.map((key) => [
        key,
        scalar(object(v)[key]) ??
          (() => {
            throw new ContractError();
          })(),
      ]),
    );
  return {
    relation: choice(r.relation, ["BETTER", "WORSE", "TIE"]),
    deciding: nullableText(r.deciding_objective),
    before: values(r.baseline_objectives),
    after: values(r.scenario_objectives),
    changes: values(r.absolute_changes),
  };
}
export function evaluation(value: unknown): Evaluation {
  const r = object(value),
    o = object(r.optimizer);
  const selected = plan(r.selected_schedule, r.verification, r.metrics),
    greedy = plan(r.greedy_schedule, r.greedy_verification, r.greedy_metrics);
  if (
    selected.fingerprint !== greedy.fingerprint ||
    selected.instanceId !== greedy.instanceId ||
    !selected.feasible ||
    !greedy.feasible
  )
    throw new ContractError();
  const producer = choice(r.selected_producer, ["greedy", "cp_sat"]);
  const proven = integer(r.selected_proven_objectives),
    full = flag(r.selected_full_lexicographic_optimal);
  if (
    BigInt(proven) > 3n ||
    (full && proven !== "3") ||
    (producer === "greedy" && (full || proven !== "0"))
  )
    throw new ContractError();
  return {
    selected,
    greedy,
    producer,
    algorithm: text(r.selected_algorithm),
    fallback: nullableText(r.fallback_reason),
    proven,
    full,
    optimizer: {
      status: text(o.status),
      solverStatus: nullableText(o.solver_status),
      version: nullableText(o.solver_version),
      proven: integer(o.proven_objectives),
      full: flag(o.full_lexicographic_optimal),
      retained: flag(o.used_previous_phase_incumbent),
      incumbentPhase: o.incumbent_phase === null ? null : integer(o.incumbent_phase),
      candidate: o.metrics === null ? null : plan(o.candidate_schedule, o.verification, o.metrics),
      comparison:
        o.comparison_with_greedy === null ? null : objectiveComparison(o.comparison_with_greedy),
      phases: list(o.phases).map((item) => {
        const p = object(item);
        return {
          phase: integer(p.phase),
          objective: text(p.objective),
          status: text(p.solver_status),
          value: scalar(p.objective_value),
          bound: scalar(p.best_objective_bound),
          proven: flag(p.proven_optimal),
        };
      }),
    },
  };
}
export function comparisonReport(value: unknown): Comparison {
  const r = object(value),
    b = object(r.baseline),
    s = object(r.scenario),
    bi = object(b.identity),
    si = object(s.identity);
  if (
    integer(r.schema_version) !== "1" ||
    r.status !== "VALID_COMPARISON" ||
    r.synthetic !== true ||
    r.same_demand_verified !== true ||
    object(r.provenance).synthetic !== true
  )
    throw new ContractError();
  const baseline = evaluation(b.evaluation),
    scenario = evaluation(s.evaluation);
  if (
    baseline.selected.fingerprint !== fingerprint(bi.instance_fingerprint) ||
    scenario.selected.fingerprint !== fingerprint(si.instance_fingerprint) ||
    baseline.selected.instanceId !== text(bi.instance_id) ||
    scenario.selected.instanceId !== text(si.instance_id)
  )
    throw new ContractError();
  const deltas = Object.fromEntries(
    metricDefinitions.map(([key, , unit]) => {
      const d = object(object(r.metric_deltas)[key]);
      const status = choice(d.percentage_status, ["DEFINED", "BASELINE_ZERO", "NULL_VALUE"]);
      const percentage = scalar(d.percentage_change),
        before = scalar(d.baseline),
        after = scalar(d.scenario);
      if (
        d.unit !== unit ||
        before !== baseline.selected.metrics?.[key] ||
        after !== scenario.selected.metrics?.[key] ||
        (status !== "DEFINED" && percentage !== null)
      )
        throw new ContractError();
      return [
        key,
        {
          before,
          after,
          percentage,
          status,
          unit,
          absolute: scalar(d.absolute_change),
          points: scalar(d.percentage_point_change),
        },
      ];
    }),
  ) as Record<MetricKey, MetricDelta>;
  return {
    id: text(r.scenario_id),
    label: text(r.label),
    fingerprint: fingerprint(r.specification_fingerprint),
    demandFingerprint: fingerprint(r.same_demand_fingerprint),
    baseline,
    scenario,
    baselineId: text(bi.instance_id),
    baselineFingerprint: fingerprint(bi.instance_fingerprint),
    scenarioId: text(si.instance_id),
    scenarioFingerprint: fingerprint(si.instance_fingerprint),
    baselineHorizon: interval(bi.horizon),
    scenarioHorizon: interval(si.horizon),
    deltas,
    selectedComparison: objectiveComparison(r.selected_comparison),
    greedyComparison: objectiveComparison(r.greedy_comparison),
    audit: list(r.applied_changes).map((item) => {
      const a = object(item);
      return {
        index: integer(a.index),
        operation: text(a.operation),
        target: text(a.target_id),
        changed: flag(a.changed),
        before: a.before,
        after: a.after,
      };
    }),
    limitations: texts(r.limitations),
    assumptions: texts(object(r.provenance).assumptions),
  };
}
export function jobInfo(value: unknown): JobInfo {
  const r = object(value),
    id = text(r.job_id);
  if (
    !/^[a-f0-9]{32}$/.test(id) ||
    r.polling_url !== `/api/v1/jobs/${id}` ||
    r.result_url !== `/api/v1/jobs/${id}/result`
  )
    throw new ContractError();
  const status = choice(r.status, [
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "EXPIRED",
  ]);
  const hasResult = flag(r.result_available),
    canCancel = flag(r.cancellation_available);
  if ((hasResult && status !== "SUCCEEDED") || (terminal(status) && canCancel))
    throw new ContractError();
  return {
    id,
    status,
    kind: choice(r.job_type, ["scheduling", "scenarios"]),
    phase: choice(r.phase, [
      "QUEUED",
      "STARTING_WORKER",
      "WORKER_RUNNING",
      "CLEANING_UP",
      "TERMINAL",
      "EXPIRED",
    ]),
    submitted: text(r.submitted_at),
    started: nullableText(r.started_at),
    completed: nullableText(r.completed_at),
    expires: nullableText(r.expires_at),
    cancellationRequested: flag(r.cancellation_requested),
    canCancel,
    hasResult,
    errorCode: nullableText(r.error_code),
  };
}
export function jobResult(value: unknown): JobResult {
  const r = object(value);
  const id = text(r.job_id),
    result = object(r.result);
  if (!/^[a-f0-9]{32}$/.test(id)) throw new ContractError();
  const kind = choice(r.job_type, ["scheduling", "scenarios"]);
  let output: JobOutput;
  if (kind === "scenarios") output = { kind, comparison: comparisonReport(result) };
  else {
    if (
      integer(result.schema_version) !== "1" ||
      result.synthetic !== true ||
      result.policy_version !== "whole-stage-minute-v1"
    )
      throw new ContractError();
    const e = evaluation(result.evaluation),
      f = fingerprint(result.instance_fingerprint),
      instanceId = text(result.instance_id);
    if (e.selected.fingerprint !== f || e.selected.instanceId !== instanceId)
      throw new ContractError();
    output = { kind, evaluation: e, horizon: interval(result.horizon), instanceId, fingerprint: f };
  }
  const execution = object(r.execution);
  return { id, output, wallSeconds: scalar(execution.whole_child_wall_seconds) };
}
