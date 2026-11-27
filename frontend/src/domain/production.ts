import { isLosslessNumber } from "lossless-json";
import { planningInput } from "./adapters";
import { compareExact } from "./exact";
import { ContractError, encodeExact, type JsonObject, object, parseExact, text } from "./json";
import type { Capabilities, Dataset } from "./models";

export const stages = ["cutting", "sewing", "finishing", "quality_control", "packing"] as const;
export const MAX_IMPORT_BYTES = 262144;
export class WorkspaceInputError extends Error {}
export interface InputIssue {
  path: string;
  message: string;
}
type Rule = (value: unknown, path: string, issues: InputIssue[]) => void;
const issue = (issues: InputIssue[], path: string, message: string) => {
  if (issues.length < 100) issues.push({ path, message });
};
const canonical: Rule = (v, p, e) => {
  if (
    typeof v !== "string" ||
    !v ||
    v !== v.trim() ||
    Array.from(v).some((c) => (c.codePointAt(0) ?? 0) < 32)
  )
    issue(e, p, "Enter nonblank text without surrounding spaces or control characters.");
};
const literal =
  (expected: unknown): Rule =>
  (v, p, e) => {
    if (v !== expected) issue(e, p, "Unsupported version, unit or synthetic provenance.");
  };
const enumeration =
  (choices: readonly string[]): Rule =>
  (v, p, e) => {
    if (typeof v !== "string" || !choices.includes(v)) issue(e, p, "Choose a supported value.");
  };
const stage = enumeration(stages);
const numeric =
  (kind: "count" | "positive" | "standard" | "fraction" | "offset"): Rule =>
  (v, p, e) => {
    if (!isLosslessNumber(v)) {
      issue(e, p, "Use an exact JSON numeric token.");
      return;
    }
    const token = v.value;
    if (kind === "offset") {
      if (
        !/^-?(0|[1-9]\d*)$/.test(token) ||
        token.length > 5 ||
        BigInt(token) < -1439n ||
        BigInt(token) > 1439n
      )
        issue(e, p, "Choose an integer fixed offset between -1439 and 1439 minutes.");
      return;
    }
    const match = /^(0|[1-9]\d*)(?:\.(\d+))?(?:[eE]([+-]?\d{1,3}))?$/.exec(token);
    if (
      !match ||
      token.replace(/\D/g, "").length > 128 ||
      Math.abs(Number(match?.[3] ?? "0") - (match?.[2]?.length ?? 0)) > 100
    ) {
      issue(e, p, "Enter an exact nonnegative number within the API numeric bounds.");
      return;
    }
    if ((kind === "count" || kind === "positive") && !/^(0|[1-9]\d*)$/.test(token))
      issue(e, p, "Enter a whole integer count.");
    if ((kind === "positive" || kind === "standard") && compareExact(token, "0") <= 0)
      issue(e, p, "Enter a value greater than zero.");
    if (kind === "fraction" && compareExact(token, "1") > 0)
      issue(e, p, "Efficiency must be between zero and one; it is never clamped.");
  };
export function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith("0000")) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}
const date: Rule = (v, p, e) => {
  if (typeof v !== "string" || !validDate(v)) issue(e, p, "Enter a valid YYYY-MM-DD date.");
};
const timestamp: Rule = (v, p, e) => {
  const m =
    typeof v === "string"
      ? /^(\d{4}-\d{2}-\d{2})T([01]\d|2[0-3]):([0-5]\d):00(?:\.0{1,6})?(Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.exec(
          v,
        )
      : null;
  if (!m || !validDate(m[1] ?? ""))
    issue(e, p, "Use a valid minute-aligned timestamp with seconds and explicit offset.");
};
const array =
  (rule: Rule, nonempty = false): Rule =>
  (v, p, e) => {
    if (!Array.isArray(v)) {
      issue(e, p, "Expected a list.");
      return;
    }
    if (nonempty && !v.length) issue(e, p, "Add at least one item.");
    v.forEach((item, i) => {
      rule(item, `${p}[${i}]`, e);
    });
  };
const shape =
  (rules: Record<string, Rule>, optional: readonly string[] = []): Rule =>
  (v, p, e) => {
    if (!v || typeof v !== "object" || Array.isArray(v) || isLosslessNumber(v)) {
      issue(e, p, "Expected a record.");
      return;
    }
    const record = v as JsonObject;
    if (Object.keys(record).some((key) => !Object.hasOwn(rules, key)))
      issue(e, p, "Unsupported fields; only scheduling instance data is accepted.");
    for (const [key, rule] of Object.entries(rules)) {
      if (Object.hasOwn(record, key)) rule(record[key], `${p}.${key}`, e);
      else if (!optional.includes(key)) issue(e, `${p}.${key}`, "Required field is missing.");
    }
  };
const interval = shape({ start: timestamp, end: timestamp });
const schema = shape({
  schema_version: numeric("positive"),
  policy_version: literal("whole-stage-minute-v1"),
  instance_id: canonical,
  calendar_utc_offset_minutes: numeric("offset"),
  allocation_granularity_minutes: numeric("positive"),
  horizon: interval,
  planning: shape({
    schema_version: numeric("positive"),
    scenario_id: canonical,
    synthetic: literal(true),
    assumptions: array(canonical, true),
    styles: array(
      shape({
        style_id: canonical,
        output_unit: literal("piece"),
        standards: array(
          shape({
            stage,
            standard_minutes_per_unit: numeric("standard"),
            measurement_unit: literal("worker_minutes_per_piece"),
          }),
          true,
        ),
      }),
      true,
    ),
    orders: array(
      shape({
        order_id: canonical,
        style_id: canonical,
        quantity: numeric("positive"),
        priority: numeric("positive"),
        release_date: date,
        due_date: date,
        required_stages: array(stage, true),
      }),
      true,
    ),
    lines: array(
      shape({
        line_id: canonical,
        stage,
        worker_count: numeric("count"),
        availability: enumeration(["available", "unavailable"]),
      }),
      true,
    ),
    shifts: array(shape({ shift_id: canonical, interval, breaks: array(interval) })),
    capacity_profiles: array(
      shape(
        {
          profile_id: canonical,
          line_id: canonical,
          effective_date: date,
          assumed_efficiency: numeric("fraction"),
          source_id: canonical,
          evidence_status: literal("synthetic"),
          evidence_reference: (v, p, e) => {
            if (v !== null) canonical(v, p, e);
          },
        },
        ["evidence_reference"],
      ),
    ),
    capabilities: array(
      shape({
        capability_id: canonical,
        line_id: canonical,
        style_id: canonical,
        stage,
        workforce_basis: canonical,
      }),
    ),
    calendar: shape({
      calendar_id: canonical,
      working_dates: array(date),
      assignments: array(
        shape({
          assignment_id: canonical,
          line_id: canonical,
          shift_id: canonical,
          profile_id: canonical,
        }),
      ),
      planned_downtime: array(
        shape({ downtime_id: canonical, assignment_id: canonical, interval, reason: canonical }),
      ),
      unavailable_periods: array(
        shape({ period_id: canonical, line_id: canonical, interval, reason: canonical }),
      ),
    }),
  }),
});
export const cloneInput = (value: JsonObject): JsonObject => object(parseExact(encodeExact(value)));
export const rows = (value: unknown): JsonObject[] => value as JsonObject[];
export const planningOf = (draft: JsonObject) => object(draft.planning);
export const calendarOf = (draft: JsonObject) => object(planningOf(draft).calendar);
export function newInput(): JsonObject {
  const id = `synthetic:workspace-${crypto.randomUUID()}`;
  return object(
    parseExact(
      encodeExact({
        schema_version: parseExact("1"),
        policy_version: "whole-stage-minute-v1",
        instance_id: id,
        horizon: { start: "", end: "" },
        calendar_utc_offset_minutes: "",
        allocation_granularity_minutes: parseExact("1"),
        planning: {
          schema_version: parseExact("1"),
          scenario_id: id,
          synthetic: true,
          assumptions: [],
          styles: [],
          orders: [],
          lines: [],
          shifts: [],
          capacity_profiles: [],
          capabilities: [],
          calendar: {
            calendar_id: `calendar-${crypto.randomUUID()}`,
            working_dates: [],
            assignments: [],
            planned_downtime: [],
            unavailable_periods: [],
          },
        },
      }),
    ),
  );
}
function boundInput(raw: unknown, capabilities: Capabilities | null): void {
  const limit = (name: string, ceiling: number) => {
    const value = capabilities?.limits.find((entry) => entry.name === name)?.value;
    return value && BigInt(value) < BigInt(ceiling) ? Number(value) : ceiling;
  };
  const source = encodeExact({ instance: raw });
  if (new TextEncoder().encode(source).length > limit("max_body_bytes", MAX_IMPORT_BYTES))
    throw new WorkspaceInputError(
      "The complete request exceeds the API file/body size limit; nothing was truncated.",
    );
  parseExact(source, MAX_IMPORT_BYTES);
  let nodes = 0;
  const visit = (v: unknown, depth: number) => {
    if (++nodes > limit("max_nodes", 10000) || depth > limit("max_depth", 24))
      throw new WorkspaceInputError("Input exceeds the API nesting or node limit.");
    if (
      typeof v === "string" &&
      (Array.from(v).length > limit("max_string_length", 4096) ||
        /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(v))
    )
      throw new WorkspaceInputError("Input contains oversized or invalid Unicode text.");
    if (isLosslessNumber(v) && v.value.length > limit("max_number_length", 128))
      throw new WorkspaceInputError("Input exceeds the API numeric limit.");
    if (Array.isArray(v)) {
      if (v.length > limit("max_collection_items", 256))
        throw new WorkspaceInputError("A list exceeds the API collection limit.");
      v.forEach((item) => {
        visit(item, depth + 1);
      });
    } else if (v && typeof v === "object" && !isLosslessNumber(v)) {
      const entries = Object.entries(v);
      if (entries.length > limit("max_collection_items", 256))
        throw new WorkspaceInputError("A record exceeds the API collection limit.");
      for (const [key, item] of entries) {
        visit(key, depth + 1);
        visit(item, depth + 1);
      }
    }
  };
  visit({ instance: raw }, 1);
  const p = object(object(raw).planning);
  if (
    Array.isArray(p.orders) &&
    (p.orders.length > limit("max_orders", 32) ||
      p.orders.reduce(
        (n, order) =>
          n +
          (Array.isArray(object(order).required_stages)
            ? (object(order).required_stages as unknown[]).length
            : 0),
        0,
      ) > limit("max_operations", 96))
  )
    throw new WorkspaceInputError(
      "Input exceeds the API limit of at most 32 orders / 96 operations; nothing was truncated.",
    );
}
export function inspectInput(
  raw: JsonObject,
  capabilities: Capabilities | null = null,
): InputIssue[] {
  const errors: InputIssue[] = [];
  try {
    boundInput(raw, capabilities);
  } catch (e) {
    return [
      {
        path: "Input",
        message:
          e instanceof WorkspaceInputError
            ? e.message
            : "Malformed or unsupported scheduling input.",
      },
    ];
  }
  schema(raw, "Instance", errors);
  const p = planningOf(raw);
  if (
    [raw.schema_version, p.schema_version, raw.allocation_granularity_minutes].some(
      (v) => !isLosslessNumber(v) || v.value !== "1",
    )
  )
    issue(errors, "Policy", "Only schema 1 and one-minute allocation are supported.");
  let model: ReturnType<typeof planningInput>;
  try {
    model = planningInput(p);
  } catch {
    return errors;
  }
  const collections = [
    ["Styles", model.styles],
    ["Orders", model.orders],
    ["Lines", model.lines],
    ["Profiles", model.profiles],
    ["Shifts", model.shifts],
    ["Capabilities", model.capabilities],
    ["Assignments", model.assignments],
    ["Downtime", model.downtime],
    ["Unavailable periods", model.unavailability],
  ] as const;
  for (const [name, collection] of collections)
    if (new Set(collection.map((x) => x.id)).size !== collection.length)
      issue(errors, name, "Duplicate identifiers must be resolved.");
  const ref = (exists: boolean, path: string) => {
    if (!exists) issue(errors, path, "Missing or conflicting reference; edit the affected record.");
  };
  for (const order of model.orders) {
    const style = model.styles.find((s) => s.id === order.styleId);
    ref(
      !!style && order.stages.every((s) => style.standards.some((x) => x.stage === s)),
      "Orders / style stages",
    );
    if (order.release > order.due)
      issue(errors, "Orders / dates", "Release cannot follow due date.");
    if (new Set(order.stages).size !== order.stages.length)
      issue(errors, "Orders / stages", "Repeated stages are unsupported.");
  }
  for (const style of model.styles)
    if (new Set(style.standards.map((s) => s.stage)).size !== style.standards.length)
      issue(errors, "Styles / standards", "Each stage needs exactly one standard.");
  for (const profile of model.profiles)
    ref(
      model.lines.some((l) => l.id === profile.lineId),
      "Profiles / line",
    );
  const capabilityKeys = model.capabilities.map((c) => encodeExact([c.lineId, c.styleId, c.stage]));
  if (new Set(capabilityKeys).size !== capabilityKeys.length)
    issue(errors, "Capabilities", "Duplicate line/style/stage capability.");
  for (const c of model.capabilities)
    ref(
      model.lines.some((l) => l.id === c.lineId && l.stage === c.stage) &&
        model.styles.some(
          (s) => s.id === c.styleId && s.standards.some((x) => x.stage === c.stage),
        ),
      "Capabilities / line and style stage",
    );
  for (const a of model.assignments)
    ref(
      model.lines.some((l) => l.id === a.lineId) &&
        model.shifts.some((s) => s.id === a.shiftId) &&
        model.profiles.some((p) => p.id === a.profileId && p.lineId === a.lineId),
      "Assignments / line, shift and profile",
    );
  for (const d of model.downtime)
    ref(
      model.assignments.some((a) => a.id === d.reference),
      "Downtime / assignment",
    );
  for (const u of model.unavailability)
    ref(
      model.lines.some((l) => l.id === u.reference),
      "Unavailability / line",
    );
  if (new Set(model.workingDates).size !== model.workingDates.length)
    issue(errors, "Calendar / working dates", "Remove duplicate working dates.");
  return [...new Map(errors.map((e) => [`${e.path}:${e.message}`, e])).values()];
}
export function importInput(source: string, capabilities: Capabilities | null = null): JsonObject {
  try {
    const raw = object(parseExact(source, MAX_IMPORT_BYTES));
    const issues = inspectInput(raw, capabilities);
    if (issues.length) throw new WorkspaceInputError(`${issues[0]?.path}: ${issues[0]?.message}`);
    return raw;
  } catch (error) {
    if (error instanceof WorkspaceInputError) throw error;
    throw new WorkspaceInputError(
      "Import requires bounded, unique-key UTF-8 scheduling JSON. CSV and inspection exports are unsupported.",
    );
  }
}
export async function readInputFile(
  file: File,
  capabilities: Capabilities | null,
): Promise<JsonObject> {
  if (file.size > MAX_IMPORT_BYTES)
    throw new WorkspaceInputError("File exceeds the 256 KiB limit; nothing was read or uploaded.");
  try {
    return importInput(
      new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer()),
      capabilities,
    );
  } catch (e) {
    if (e instanceof WorkspaceInputError) throw e;
    throw new WorkspaceInputError("Cannot read a strict UTF-8 scheduling JSON file.");
  }
}
export function exportInput(raw: JsonObject, capabilities: Capabilities | null = null): string {
  const issues = inspectInput(raw, capabilities);
  if (issues.length)
    throw new WorkspaceInputError("Resolve preliminary input errors before exporting.");
  return `${encodeExact(raw)}\n`;
}
export interface InputValidation {
  instanceId: string;
  fingerprint: string;
}
export function inputValidation(value: unknown): InputValidation {
  const r = object(value);
  if (
    Object.keys(r).sort().join(",") !==
      "instance_fingerprint,instance_id,policy_version,schema_version,status,synthetic" ||
    encodeExact(r.schema_version) !== "1" ||
    r.synthetic !== true ||
    r.status !== "VALID_INPUT" ||
    r.policy_version !== "whole-stage-minute-v1" ||
    !/^[a-f0-9]{64}$/.test(text(r.instance_fingerprint))
  )
    throw new ContractError();
  return { instanceId: text(r.instance_id), fingerprint: text(r.instance_fingerprint) };
}
export async function userDataset(raw: JsonObject, validation: InputValidation): Promise<Dataset> {
  const instance = importInput(encodeExact(raw));
  if (instance.instance_id !== validation.instanceId)
    throw new WorkspaceInputError("Validation identity does not match this draft.");
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(encodeExact(instance)),
  );
  return {
    key: `user-${crypto.randomUUID()}`,
    name: "My synthetic production input",
    description: "User-defined synthetic assumptions, validated by local Python",
    sourceFile: "Local user workspace · exact serialized input (LF)",
    sourceHash: Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join(""),
    planning: planningInput(instance.planning),
    instance,
    previewCapacity: null,
    previewSchedule: null,
    savedProposal: null,
    validatedFingerprint: validation.fingerprint,
  };
}
