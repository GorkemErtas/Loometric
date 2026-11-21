import golden from "../fixtures/m04-additional-workers.report.json?raw";
import { object, parseExact } from "../src/domain/json";
import type { JobStatus } from "../src/domain/planning";

const source = () => object(parseExact(golden));
export function dispatchFixture() {
  const r = source(),
    b = object(r.baseline),
    e = object(b.evaluation),
    i = object(b.identity),
    p = object(e.selected_schedule);
  return {
    ...p,
    synthetic: true,
    algorithm: e.selected_algorithm,
    status: "VALID_PARTIAL",
    horizon: i.horizon,
    schedule: p,
    verification: e.verification,
    metrics: e.metrics,
  };
}
export function jobFixture(status: JobStatus = "RUNNING") {
  const end = !["QUEUED", "RUNNING"].includes(status);
  return {
    job_id: "a".repeat(32),
    job_type: "scheduling",
    status,
    phase: end ? (status === "EXPIRED" ? "EXPIRED" : "TERMINAL") : "WORKER_RUNNING",
    submitted_at: "2030-01-07T08:00:00+00:00",
    started_at: null,
    completed_at: end ? "2030-01-07T08:00:02+00:00" : null,
    expires_at: null,
    cancellation_requested: status === "CANCELLED",
    cancellation_available: !end,
    result_available: status === "SUCCEEDED",
    error_code: status === "FAILED" ? "EXECUTION_TIMEOUT" : null,
    polling_url: `/api/v1/jobs/${"a".repeat(32)}`,
    result_url: `/api/v1/jobs/${"a".repeat(32)}/result`,
  };
}
