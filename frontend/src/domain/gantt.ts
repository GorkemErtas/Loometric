import { object, text } from "./json";
import type { Interval, Planning } from "./models";
import type { Comparison } from "./planning";
import { interval } from "./planning";

export function geometry(
  value: Interval,
  horizon: Interval,
): { left: string; width: string } | null {
  // Visualization only: absolute timestamp positions; source strings stay intact.
  const start = Date.parse(horizon.start),
    end = Date.parse(horizon.end),
    a = Date.parse(value.start),
    b = Date.parse(value.end);
  if (![start, end, a, b].every(Number.isFinite) || end <= start || b <= start || a >= end)
    return null;
  return {
    left: `${((Math.max(a, start) - start) / (end - start)) * 100}%`,
    width: `${((Math.min(b, end) - Math.max(a, start)) / (end - start)) * 100}%`,
  };
}
export function elapsedMinutes(value: Interval): string {
  return String((Date.parse(value.end) - Date.parse(value.start)) / 60000);
}
export function calendarBands(planning: Planning, audit: Comparison["audit"] = []) {
  const assignments = new Map(planning.assignments.map((a) => [a.id, a]));
  const stops = new Map(planning.downtime.map((s) => [s.id, s]));
  // Copy approved audit records for annotations only; no feasibility/availability calculation.
  for (const a of audit) {
    if (a.operation === "remove_assignment") assignments.delete(a.target);
    if (a.operation === "add_assignment") {
      const r = object(a.after);
      assignments.set(a.target, {
        id: a.target,
        lineId: text(r.line_id),
        shiftId: text(r.shift_id),
        profileId: text(r.profile_id),
      });
    }
    if (a.operation === "remove_downtime") stops.delete(a.target);
    if (a.operation === "add_downtime" || a.operation === "replace_downtime") {
      const r = object(a.after);
      stops.set(a.target, {
        id: a.target,
        reference: text(r.assignment_id),
        reason: text(r.reason),
        ...interval(r.interval),
      });
    }
  }
  const shifts = [...assignments.values()].flatMap((a) => {
    const shift = planning.shifts.find((s) => s.id === a.shiftId);
    return shift
      ? [
          {
            id: a.id,
            lineId: a.lineId,
            shiftId: shift.id,
            start: shift.start,
            end: shift.end,
            breaks: shift.breaks,
          },
        ]
      : [];
  });
  const downtime = [...stops.values()].flatMap((s) => {
    const assignment = assignments.get(s.reference);
    return assignment ? [{ ...s, lineId: assignment.lineId }] : [];
  });
  const breaks = shifts.flatMap((s) =>
    s.breaks.map((b, index) => ({
      ...b,
      id: `${s.id}:break:${index}`,
      lineId: s.lineId,
      reason: "Declared break",
    })),
  );
  return {
    shifts,
    interruptions: [
      ...downtime,
      ...breaks,
      ...planning.unavailability.map((s) => ({ ...s, lineId: s.reference })),
    ],
  };
}
