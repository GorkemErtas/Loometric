import type { JsonObject } from "./json";
import {
  ContractError,
  reportedDecimal as decimal,
  flag,
  inputDecimal,
  integer,
  list,
  nullableDecimal,
  object,
  text,
  texts,
} from "./json";
import type { Capabilities, CapacityReport, Interval, Planning, ScheduleReport } from "./models";

function interval(value: unknown): Interval {
  const item = object(value);
  return { start: text(item.start), end: text(item.end) };
}
function requireCapacityUnits(raw: JsonObject): void {
  if (
    raw.quantity_unit !== "piece" ||
    raw.elapsed_time_unit !== "minute" ||
    raw.labor_unit !== "worker_minute" ||
    raw.capacity_unit !== "standard_worker_minute"
  ) {
    throw new ContractError();
  }
}
export function planningInput(value: unknown): Planning {
  const raw = object(value);
  if (integer(raw.schema_version) !== "1" || raw.synthetic !== true) throw new ContractError();
  return {
    id: text(raw.scenario_id),
    raw,
    assumptions: texts(raw.assumptions),
    orders: list(raw.orders).map((value) => {
      const r = object(value);
      return {
        id: text(r.order_id),
        styleId: text(r.style_id),
        quantity: integer(r.quantity),
        priority: integer(r.priority),
        release: text(r.release_date),
        due: text(r.due_date),
        stages: texts(r.required_stages),
      };
    }),
    styles: list(raw.styles).map((value) => {
      const r = object(value);
      return {
        id: text(r.style_id),
        standards: list(r.standards).map((s) => {
          const a = object(s);
          return {
            stage: text(a.stage),
            minutes: inputDecimal(a.standard_minutes_per_unit),
            unit: text(a.measurement_unit),
          };
        }),
      };
    }),
    lines: list(raw.lines).map((value) => {
      const r = object(value);
      return {
        id: text(r.line_id),
        stage: text(r.stage),
        workers: integer(r.worker_count),
        availability: text(r.availability),
      };
    }),
    profiles: list(raw.capacity_profiles).map((value) => {
      const r = object(value);
      return {
        id: text(r.profile_id),
        lineId: text(r.line_id),
        effectiveDate: text(r.effective_date),
        efficiency: inputDecimal(r.assumed_efficiency),
        source: text(r.source_id),
        evidence: text(r.evidence_status),
      };
    }),
    shifts: list(raw.shifts).map((value) => {
      const r = object(value);
      return {
        id: text(r.shift_id),
        ...interval(r.interval),
        breaks: list(r.breaks).map(interval),
      };
    }),
    capabilities: list(raw.capabilities).map((value) => {
      const r = object(value);
      return {
        id: text(r.capability_id),
        lineId: text(r.line_id),
        styleId: text(r.style_id),
        stage: text(r.stage),
        basis: text(r.workforce_basis),
      };
    }),
    workingDates: texts(object(raw.calendar).working_dates),
    assignments: list(object(raw.calendar).assignments).map((value) => {
      const r = object(value);
      return {
        id: text(r.assignment_id),
        lineId: text(r.line_id),
        shiftId: text(r.shift_id),
        profileId: text(r.profile_id),
      };
    }),
    downtime: list(object(raw.calendar).planned_downtime).map((value) => {
      const r = object(value);
      return {
        id: text(r.downtime_id),
        reference: text(r.assignment_id),
        reason: text(r.reason),
        ...interval(r.interval),
      };
    }),
    unavailability: list(object(raw.calendar).unavailable_periods).map((value) => {
      const r = object(value);
      return {
        id: text(r.period_id),
        reference: text(r.line_id),
        reason: text(r.reason),
        ...interval(r.interval),
      };
    }),
  };
}

export function capacityReport(value: unknown): CapacityReport {
  const raw = object(value);
  requireCapacityUnits(raw);
  if (
    integer(raw.schema_version) !== "1" ||
    raw.status !== "CAPACITY_ASSESSED" ||
    raw.synthetic !== true ||
    raw.allocation_performed !== false ||
    raw.assessment_scope !== "INDEPENDENT_ORDER_STAGE_SLOT" ||
    raw.schedule_feasibility !== "NOT_ASSESSED"
  )
    throw new ContractError();
  const result: CapacityReport = {
    scenarioId: text(raw.scenario_id),
    status: "CAPACITY_ASSESSED",
    assumptions: texts(raw.assumptions),
    limitations: texts(raw.limitations),
    slots: list(raw.slots).map((value) => {
      const r = object(value);
      const a = object(r.availability);
      return {
        id: text(r.assignment_id),
        lineId: text(r.line_id),
        shiftId: text(r.shift_id),
        stage: text(r.stage),
        start: text(r.shift_start),
        end: text(r.shift_end),
        workers: integer(r.worker_count),
        efficiency: decimal(r.assumed_efficiency),
        gross: decimal(a.gross_elapsed_minutes),
        available: decimal(a.available_elapsed_minutes),
        blocked: decimal(a.blocked_union_minutes),
        breaks: decimal(a.break_minutes),
        downtime: decimal(a.planned_downtime_additional_minutes),
        unavailability: decimal(a.unavailable_additional_minutes),
        workerMinutes: decimal(r.available_worker_minutes),
        standardMinutes: decimal(r.effective_capacity_standard_minutes),
      };
    }),
    assessments: list(raw.assessments).map((value) => {
      const r = object(value);
      return {
        orderId: text(r.order_id),
        styleId: text(r.style_id),
        stage: text(r.stage),
        slotId: text(r.assignment_id),
        lineId: text(r.line_id),
        compatible: flag(r.compatible),
        potentialUnits: r.potential_units === null ? null : integer(r.potential_units),
        requiredStandard: decimal(r.required_standard_minutes),
        shortfall: nullableDecimal(r.shortfall_standard_minutes),
        independentFeasible: flag(r.independent_slot_feasible),
        reasons: texts(r.reason_codes),
      };
    }),
    orders: list(raw.orders).map((value) => {
      const r = object(value);
      return {
        id: text(r.order_id),
        independentSlots: flag(r.all_stages_have_independent_slot),
      };
    }),
  };
  if (new Set(result.slots.map((slot) => slot.id)).size !== result.slots.length)
    throw new ContractError();
  return result;
}

export function scheduleReport(value: unknown): ScheduleReport {
  const raw = object(value);
  const verified = object(raw.verification);
  const feasible = flag(verified.feasible);
  const complete = flag(verified.complete);
  const expectedStatus = feasible ? (complete ? "VALID_COMPLETE" : "VALID_PARTIAL") : "INVALID";
  const m = raw.metrics === null ? null : object(raw.metrics);
  if (m) requireCapacityUnits(m);
  if (
    integer(raw.schema_version) !== "1" ||
    raw.synthetic !== true ||
    raw.policy_version !== "whole-stage-minute-v1" ||
    raw.status !== expectedStatus ||
    !/^[a-f0-9]{64}$/.test(text(raw.instance_fingerprint)) ||
    (!feasible && m !== null)
  )
    throw new ContractError();
  return {
    instanceId: text(raw.instance_id),
    fingerprint: text(raw.instance_fingerprint),
    status: text(raw.status),
    algorithm: text(raw.algorithm),
    feasible,
    complete,
    violations: list(verified.violations).map((v) => text(object(v).code)),
    metrics:
      m === null
        ? null
        : {
            completed: integer(m.scheduled_units),
            unfinished: integer(m.unscheduled_units),
            availableLine: decimal(m.available_line_minutes),
            occupiedLine: decimal(m.occupied_line_minutes),
            availableWorker: decimal(m.available_worker_minutes),
            consumedWorker: decimal(m.consumed_worker_minutes),
            availableStandard: decimal(m.available_standard_minutes),
            consumedStandard: decimal(m.consumed_standard_minutes),
            lineUtilization: nullableDecimal(m.line_utilization),
            standardUtilization: nullableDecimal(m.standard_capacity_utilization),
          },
  };
}

export function capabilities(value: unknown): Capabilities {
  const raw = object(value);
  const entries = (value: unknown) =>
    Object.entries(object(value)).map(([name, value]) => ({ name, value: integer(value) }));
  return {
    policies: texts(raw.policy_versions),
    operations: texts(raw.operations),
    methods: texts(raw.scheduling_methods),
    limits: entries(raw.limits),
    jobLimits: entries(object(raw.optimization_jobs).limits),
    limitations: texts(raw.limitations),
    prediction: text(object(raw.deferred).prediction),
  };
}
export function unwrap(value: unknown): { data: JsonObject; requestId: string } {
  const envelope = object(value);
  if (envelope.api_version !== "v1" || !/^[a-f0-9-]{36}$/.test(text(envelope.request_id)))
    throw new ContractError();
  return { data: object(envelope.data), requestId: text(envelope.request_id) };
}
