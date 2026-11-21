import { compareExact } from "./exact";
import {
  ContractError,
  encodeExact,
  inputDecimal,
  type JsonObject,
  object,
  parseExact,
  text,
} from "./json";
import type { Assignment, Capabilities, Dataset, Planning } from "./models";
import { type Dispatch, interval } from "./planning";

export const operations = [
  "set_workers",
  "set_efficiency",
  "set_availability",
  "add_assignment",
  "remove_assignment",
  "add_downtime",
  "replace_downtime",
  "remove_downtime",
] as const;
export type Operation = (typeof operations)[number];
export type Change = JsonObject & { operation: Operation };
export class EditorError extends Error {}
export interface ScenarioDraft {
  id: string;
  label: string;
  sourceId: string;
  assumptions: string;
  changes: Change[];
  wall: string;
  deterministic: string;
}
export const emptyDraft = (): ScenarioDraft => ({
  id: "planner-scenario",
  label: "Hypothetical capacity change",
  sourceId: "synthetic:local-planner",
  assumptions:
    "Conditional synthetic planning only. Declared crews are assumed qualified; efficiency is hypothetical, not observed productivity.",
  changes: [],
  wall: "1",
  deterministic: "1",
});
export function canonical(value: string, label: string): string {
  if (
    !value ||
    value !== value.trim() ||
    Array.from(value).some((char) => {
      const code = char.codePointAt(0) ?? 0;
      return code < 32 || code === 127;
    }) ||
    value.length > 4096
  )
    throw new EditorError(`${label} must be nonblank canonical text without control characters.`);
  return value;
}
export function numericToken(value: string, kind: "integer" | "fraction"): unknown {
  if (
    value.length > 128 ||
    !(kind === "integer" ? /^(0|[1-9]\d*)$/ : /^(0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d{1,3})?$/).test(
      value,
    )
  )
    throw new EditorError(
      "Enter an exact nonnegative numeric value; it will not be rounded or clamped.",
    );
  try {
    if (kind === "fraction" && compareExact(value, "1") > 0) throw new Error();
    const result = parseExact(value);
    if (kind === "fraction") inputDecimal(result);
    return result;
  } catch {
    throw new EditorError(
      "Fractional values must be between zero and one, with a supported exponent.",
    );
  }
}
export function conflictKey(change: Change): string {
  const op = change.operation;
  if (op === "add_assignment") return `assignment:${text(object(change.assignment).assignment_id)}`;
  if (op === "remove_assignment") return `assignment:${text(change.assignment_id)}`;
  if (op === "add_downtime" || op === "replace_downtime")
    return `downtime:${text(object(change.downtime).downtime_id)}`;
  if (op === "remove_downtime") return `downtime:${text(change.downtime_id)}`;
  return `${op}:${text(op === "set_efficiency" ? change.profile_id : change.line_id)}`;
}
export function appendChange(changes: readonly Change[], change: Change): Change[] {
  if (changes.length >= 64)
    throw new EditorError("The HTTP envelope permits at most 64 ordered changes.");
  if (changes.some((item) => conflictKey(item) === conflictKey(change)))
    throw new EditorError(
      "This entity field already has an edit. Remove that change first; repeated lifecycle edits conflict.",
    );
  return [...changes, object(parseExact(encodeExact(change))) as Change];
}
export function draftAssignments(planning: Planning, changes: readonly Change[]): Assignment[] {
  // Editor reference choices only; no capacity, calendar validation or inference.
  const choices = new Map(planning.assignments.map((a) => [a.id, a]));
  for (const c of changes) {
    if (c.operation === "remove_assignment") choices.delete(text(c.assignment_id));
    if (c.operation === "add_assignment") {
      const a = object(c.assignment);
      choices.set(text(a.assignment_id), {
        id: text(a.assignment_id),
        lineId: text(a.line_id),
        shiftId: text(a.shift_id),
        profileId: text(a.profile_id),
      });
    }
  }
  return [...choices.values()];
}
export function makeChange(
  operation: Operation,
  values: Record<string, string>,
  planning: Planning,
  changes: readonly Change[],
): Change {
  const get = (key: string) => canonical(values[key] ?? "", key);
  const exists = (value: string, ids: string[]) => {
    if (!ids.includes(value)) throw new EditorError("Select an existing baseline reference.");
    return value;
  };
  if (operation === "set_workers" || operation === "set_availability") {
    const line = exists(
      get("line"),
      planning.lines.map((a) => a.id),
    );
    if (operation === "set_workers")
      return { operation, line_id: line, worker_count: numericToken(get("value"), "integer") };
    const availability = exists(get("value"), ["available", "unavailable"]);
    return { operation, line_id: line, availability };
  }
  if (operation === "set_efficiency")
    return {
      operation,
      profile_id: exists(
        get("profile"),
        planning.profiles.map((a) => a.id),
      ),
      assumed_efficiency: numericToken(get("value"), "fraction"),
    };
  if (operation === "remove_assignment")
    return {
      operation,
      assignment_id: exists(
        get("assignment"),
        planning.assignments.map((a) => a.id),
      ),
    };
  if (operation === "remove_downtime")
    return {
      operation,
      downtime_id: exists(
        get("downtime"),
        planning.downtime.map((a) => a.id),
      ),
    };
  if (operation === "add_assignment") {
    const id = get("id");
    if (planning.assignments.some((a) => a.id === id))
      throw new EditorError("Assignment ID already exists.");
    const line = exists(
        get("line"),
        planning.lines.map((a) => a.id),
      ),
      profile = exists(
        get("profile"),
        planning.profiles.filter((a) => a.lineId === line).map((a) => a.id),
      );
    return {
      operation,
      assignment: {
        assignment_id: id,
        line_id: line,
        profile_id: profile,
        shift_id: exists(
          get("shift"),
          planning.shifts.map((a) => a.id),
        ),
      },
    };
  }
  const id =
    operation === "replace_downtime"
      ? exists(
          get("downtime"),
          planning.downtime.map((a) => a.id),
        )
      : get("id");
  if (operation === "add_downtime" && planning.downtime.some((a) => a.id === id))
    throw new EditorError("Downtime ID already exists.");
  let times: { start: string; end: string };
  try {
    times = interval({ start: get("start"), end: get("end") });
  } catch {
    throw new EditorError(
      "Downtime requires explicit offset timestamps and an end after its start.",
    );
  }
  return {
    operation,
    downtime: {
      downtime_id: id,
      assignment_id: exists(
        get("assignment"),
        draftAssignments(planning, changes).map((a) => a.id),
      ),
      interval: times,
      reason: get("reason"),
    },
  };
}
export function executionBlock(
  dataset: Dataset | null,
  capabilities: Capabilities | null,
): string | null {
  if (!dataset?.instance)
    return "This M02 input is a capacity scenario, not an executable scheduling instance. Select a frozen M03/M04 instance.";
  const orders = dataset.planning.orders.length,
    stages = dataset.planning.orders.reduce((total, o) => total + o.stages.length, 0);
  const limit = (key: string, ceiling: bigint) => {
    const reported = capabilities?.limits.find((l) => l.name === key)?.value;
    return reported && BigInt(reported) < ceiling ? BigInt(reported) : ceiling;
  };
  if (BigInt(orders) > limit("max_orders", 32n) || BigInt(stages) > limit("max_operations", 96n))
    return `Unsupported HTTP instance: ${orders} orders / ${stages} operations exceed the published envelope (at most 32 / 96). Inputs are never truncated.`;
  return null;
}
export function specification(
  dataset: Dataset,
  reference: Dispatch,
  draft: ScenarioDraft,
  optimizer: boolean,
): JsonObject {
  if (
    !dataset.instance ||
    reference.instanceId !== text(dataset.instance.instance_id) ||
    !reference.feasible
  )
    throw new EditorError("Run and verify reference scheduling for this exact baseline first.");
  const keys = draft.changes.map(conflictKey);
  if (new Set(keys).size !== keys.length || keys.length > 64)
    throw new EditorError("Resolve conflicting edits or the 64-change envelope first.");
  const scheduling = optimizer
    ? {
        method: "greedy_with_cp_sat",
        solver: {
          random_seed: parseExact("42"),
          workers: parseExact("1"),
          wall_time_seconds_per_phase: numericToken(draft.wall, "fraction"),
          deterministic_time_per_phase: numericToken(draft.deterministic, "fraction"),
          benchmark_mode: true,
        },
      }
    : { method: "greedy" };
  return object(
    parseExact(
      encodeExact({
        schema_version: parseExact("1"),
        baseline_instance_id: reference.instanceId,
        baseline_fingerprint: reference.fingerprint,
        scenario_id: canonical(draft.id, "Scenario ID"),
        label: canonical(draft.label, "Label"),
        provenance: {
          source_id: canonical(draft.sourceId, "Source ID"),
          synthetic: true,
          assumptions: [canonical(draft.assumptions, "Assumptions")],
        },
        changes: draft.changes,
        scheduling,
      }),
    ),
  );
}
export function assertBinding(reference: Dispatch, id: string, hash: string): void {
  if (id !== reference.instanceId || hash !== reference.fingerprint) throw new ContractError();
}
