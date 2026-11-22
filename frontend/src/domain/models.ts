import type { JsonObject } from "./json";

export interface Interval {
  start: string;
  end: string;
}
export interface Order {
  id: string;
  styleId: string;
  quantity: string;
  priority: string;
  release: string;
  due: string;
  stages: string[];
}
export interface Style {
  id: string;
  standards: { stage: string; minutes: string; unit: string }[];
}
export interface Line {
  id: string;
  stage: string;
  workers: string;
  availability: string;
}
export interface Profile {
  id: string;
  lineId: string;
  effectiveDate: string;
  efficiency: string;
  source: string;
  evidence: string;
}
export interface Shift extends Interval {
  id: string;
  breaks: Interval[];
}
export interface Assignment {
  id: string;
  lineId: string;
  shiftId: string;
  profileId: string;
}
export interface Capability {
  id: string;
  lineId: string;
  styleId: string;
  stage: string;
  basis: string;
}
export interface Stop extends Interval {
  id: string;
  reference: string;
  reason: string;
}
export interface Planning {
  id: string;
  raw: JsonObject;
  assumptions: string[];
  orders: Order[];
  styles: Style[];
  lines: Line[];
  profiles: Profile[];
  shifts: Shift[];
  assignments: Assignment[];
  capabilities: Capability[];
  workingDates: string[];
  downtime: Stop[];
  unavailability: Stop[];
}
export interface Slot {
  id: string;
  lineId: string;
  shiftId: string;
  stage: string;
  start: string;
  end: string;
  workers: string;
  efficiency: string;
  gross: string;
  available: string;
  blocked: string;
  breaks: string;
  downtime: string;
  unavailability: string;
  workerMinutes: string;
  standardMinutes: string;
}
export interface Assessment {
  orderId: string;
  styleId: string;
  stage: string;
  slotId: string;
  lineId: string;
  compatible: boolean;
  potentialUnits: string | null;
  requiredStandard: string;
  shortfall: string | null;
  independentFeasible: boolean;
  reasons: string[];
}
export interface CapacityOrder {
  id: string;
  independentSlots: boolean;
}
export interface CapacityReport {
  scenarioId: string;
  status: "CAPACITY_ASSESSED";
  slots: Slot[];
  assessments: Assessment[];
  orders: CapacityOrder[];
  limitations: string[];
  assumptions: string[];
}
export interface ScheduleReport {
  instanceId: string;
  fingerprint: string;
  status: string;
  algorithm: string;
  feasible: boolean;
  complete: boolean;
  violations: string[];
  metrics: null | {
    completed: string;
    unfinished: string;
    availableLine: string;
    occupiedLine: string;
    availableWorker: string;
    consumedWorker: string;
    availableStandard: string;
    consumedStandard: string;
    lineUtilization: string | null;
    standardUtilization: string | null;
  };
}
export interface Capabilities {
  policies: string[];
  operations: string[];
  methods: string[];
  limits: { name: string; value: string }[];
  limitations: string[];
  prediction: string;
  jobLimits: { name: string; value: string }[];
}
export interface Dataset {
  validatedFingerprint?: string;
  key: string;
  name: string;
  description: string;
  sourceFile: string;
  sourceHash: string;
  planning: Planning;
  instance: JsonObject | null;
  previewCapacity: CapacityReport | null;
  previewSchedule: ScheduleReport | null;
  savedProposal: JsonObject | null;
}
