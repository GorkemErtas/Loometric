import { ContractError } from "./json";
import { type JobInfo, terminal } from "./planning";

export const trackingLimits = { polls: 60, milliseconds: 90000, interval: 1000 } as const;
export function trackingDelay(
  started: number,
  now: number,
  polls: number,
  retryAfterMs: number | null,
): number | null {
  const delay = Math.max(trackingLimits.interval, retryAfterMs ?? trackingLimits.interval);
  if (polls >= trackingLimits.polls || now + delay - started >= trackingLimits.milliseconds)
    return null;
  return delay;
}
export function reconcileJob(previous: JobInfo, next: JobInfo): JobInfo {
  if (previous.id !== next.id || previous.kind !== next.kind) throw new ContractError();
  if (terminal(previous.status)) {
    if (!terminal(next.status)) return previous; // An older poll cannot roll back a terminal receipt.
    if (next.status !== previous.status && next.status !== "EXPIRED") throw new ContractError();
  }
  if (previous.cancellationRequested && !next.cancellationRequested && !terminal(next.status))
    return previous;
  return next;
}
