import { capabilities, capacityReport, scheduleReport, unwrap } from "../domain/adapters";
import type { JsonObject } from "../domain/json";
import { ContractError, encodeExact, object, parseExact, text } from "../domain/json";
import type { Planning } from "../domain/models";
import {
  comparisonReport,
  dispatchReport,
  type JobKind,
  jobInfo,
  jobResult,
} from "../domain/planning";
import { inputValidation } from "../domain/production";

export type ApiFailure =
  | "network"
  | "authentication"
  | "validation"
  | "busy"
  | "timeout"
  | "contract"
  | "server"
  | "missing"
  | "expired"
  | "not_ready"
  | "cancelled";
const messages: Record<ApiFailure, string> = {
  network: "The local backend is unreachable. Check the server and configured origin.",
  authentication: "The local session was rejected. Check the Bearer token and allowed origin.",
  validation: "The backend rejected this input. No capacity or schedule result was accepted.",
  busy: "The local execution slots are busy. Wait briefly and retry.",
  timeout: "The bounded request reached its deadline. Retry when the local backend is ready.",
  contract: "The backend response does not match the supported API contract.",
  server: "The backend could not complete this request. No replacement result was invented.",
  cancelled: "The local request was cancelled.",
  missing:
    "The job is missing. Its record may have expired or the local server may have restarted.",
  expired: "The server's volatile result retention has expired. No result is available.",
  not_ready: "The job result is unavailable in its current state. Inspect its actual status.",
};
export class ApiError extends Error {
  constructor(
    readonly kind: ApiFailure,
    readonly status: number | null = null,
    readonly requestId: string | null = null,
    readonly retryAfterMs: number | null = null,
    readonly code: string | null = null,
    readonly domainCode: string | null = null,
  ) {
    super(messages[kind]);
  }
}
export const validationGuidance: Record<string, string> = {
  BREAK_OUTSIDE_SHIFT: "A break lies outside its shift. Check Shifts & breaks.",
  OVERLAPPING_BREAKS: "Breaks overlap. Check Shifts & breaks.",
  OVERLAPPING_ASSIGNMENTS: "Assignments overlap on the same line. Check the production calendar.",
  DOWNTIME_OUTSIDE_SHIFT:
    "Downtime lies outside its assigned shift. Check the production calendar.",
  PROFILE_NOT_EFFECTIVE: "A capacity profile is not effective at shift start. Check profile dates.",
  PROFILE_LINE_MISMATCH: "The selected profile belongs to another line. Check assignments.",
  NONWORKING_DATE:
    "An assigned shift starts on an undeclared working date. Add that date explicitly.",
  CALENDAR_OFFSET_MISMATCH: "A shift start uses a different offset from the fixed calendar offset.",
  UNSUPPORTED_TIME_GRID:
    "All horizon, shift, break and stop boundaries must align to whole minutes.",
  INVALID_INTERVAL: "An interval ends before it starts. Check its explicit endpoints.",
  INVALID_SHIFT: "A shift must end after it starts.",
  INVALID_HORIZON: "The scheduling horizon must end after it starts.",
  UNKNOWN_REFERENCE:
    "A required entity reference is missing. Review orders, resources and calendar.",
  DUPLICATE_IDENTIFIER: "An identifier is repeated. Review the affected entity lists.",
  INVALID_ORDER_DATES: "An order release date follows its due date.",
  CAPABILITY_STAGE_MISMATCH:
    "A qualification must match both its line stage and a supported style stage.",
};

export function localOrigin(value: string): string {
  try {
    const url = new URL(value);
    if (
      url.protocol !== "http:" ||
      !["127.0.0.1", "localhost"].includes(url.hostname) ||
      !url.port ||
      Number(url.port) < 1024 ||
      Number(url.port) > 65535 ||
      url.pathname !== "/" ||
      url.search ||
      url.hash ||
      url.username ||
      url.password ||
      (value !== url.origin && value !== `${url.origin}/`)
    )
      throw new Error();
    return url.origin;
  } catch {
    throw new ApiError("validation");
  }
}

async function responseText(response: Response): Promise<string> {
  const reader = response.body?.getReader();
  if (!reader) return "";
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 2 * 1024 * 1024 + 1024) {
        await reader.cancel();
        throw new ContractError();
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const buffer = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    buffer.set(chunk, offset);
    offset += chunk.length;
  }
  return new TextDecoder("utf-8", { fatal: true }).decode(buffer);
}

export interface ApiResult<T> {
  data: T;
  requestId: string;
  retryAfterMs: number | null;
}

export function retryAfter(value: string | null): number | null {
  if (value === null) return null;
  if (/^\d{1,6}$/.test(value)) return Number(value) * 1000;
  const date = Date.parse(value);
  return Number.isFinite(date) ? Math.max(0, date - Date.now()) : null;
}
const publicCodes = new Set([
  "JOB_QUEUE_FULL",
  "JOB_REGISTRY_FULL",
  "JOB_RESULT_CAPACITY",
  "JOB_SOLVER_POLICY",
  "JOB_NOT_FOUND",
  "JOB_EXPIRED",
  "JOB_NOT_READY",
  "JOB_FAILED",
  "JOB_CANCELLED",
  "SERVER_BUSY",
  "COMPLEXITY_LIMIT_EXCEEDED",
  "SCENARIO_CONFLICT",
  "INVALID_INPUT",
  "BODY_TOO_LARGE",
  "EXECUTION_TIMEOUT",
  "JOB_SERVICE_UNAVAILABLE",
]);
const jobPath = (id: string) => {
  if (!/^[a-f0-9]{32}$/.test(id)) throw new ApiError("validation");
  return `/jobs/${id}`;
};

export class ApiClient {
  readonly origin: string;
  #token: string;
  #session = new AbortController();

  constructor(
    origin: string,
    token: string,
    private readonly transport: typeof fetch = (...args) => globalThis.fetch(...args),
  ) {
    this.origin = localOrigin(origin);
    if (!/^[A-Za-z0-9_-]{32,128}$/.test(token)) throw new ApiError("authentication");
    this.#token = token;
  }
  disconnect(): void {
    this.#session.abort();
    this.#token = "";
  }

  private async request<T>(
    path: string,
    adapt: (value: unknown) => T,
    body?: JsonObject,
    signal?: AbortSignal,
    method?: "DELETE",
  ): Promise<ApiResult<T>> {
    if (this.#session.signal.aborted || signal?.aborted) throw new ApiError("cancelled");
    const controller = new AbortController();
    let timedOut = false;
    const cancel = () => controller.abort();
    this.#session.signal.addEventListener("abort", cancel, { once: true });
    signal?.addEventListener("abort", cancel, { once: true });
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 12000);
    try {
      const encoded = body === undefined ? undefined : encodeExact(body);
      if (encoded && new TextEncoder().encode(encoded).length > 262144)
        throw new ApiError("validation", 413);
      const headers = {
        Authorization: `Bearer ${this.#token}`,
        ...(encoded ? { "Content-Type": "application/json" } : {}),
      };
      const response = await this.transport(`${this.origin}/api/v1${path}`, {
        method: method ?? (encoded ? "POST" : "GET"),
        headers,
        ...(encoded ? { body: encoded } : {}),
        credentials: "omit",
        redirect: "error",
        referrerPolicy: "no-referrer",
        cache: "no-store",
        signal: controller.signal,
      });
      const raw = parseExact(await responseText(response));
      const retry = retryAfter(response.headers.get("Retry-After"));
      if (!response.ok) {
        const envelope = object(raw);
        const id = typeof envelope.request_id === "string" ? envelope.request_id : "";
        const safeId = /^[0-9a-f-]{36}$/.test(id) && !id.includes(this.#token) ? id : null;
        const kind =
          response.status === 401 || response.status === 403
            ? "authentication"
            : response.status === 404
              ? "missing"
              : response.status === 410
                ? "expired"
                : response.status === 409
                  ? "not_ready"
                  : response.status === 429
                    ? "busy"
                    : response.status === 408 || response.status === 504
                      ? "timeout"
                      : response.status === 413 ||
                          response.status === 415 ||
                          response.status === 422 ||
                          response.status === 400
                        ? "validation"
                        : "server";
        let code = "";
        let domainCode: string | null = null;
        try {
          const detail = object(envelope.error);
          code = text(detail.code);
          if (code === "DOMAIN_VALIDATION_FAILED" && Array.isArray(detail.details)) {
            const candidate = object(detail.details[0]).domain_code;
            if (typeof candidate === "string" && Object.hasOwn(validationGuidance, candidate))
              domainCode = candidate;
          }
        } catch {
          /* Optional safe error category. */
        }
        throw new ApiError(
          kind,
          response.status,
          safeId,
          retry,
          publicCodes.has(code) ? code : null,
          domainCode,
        );
      }
      const result = unwrap(raw);
      return { data: adapt(result.data), requestId: result.requestId, retryAfterMs: retry };
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (controller.signal.aborted) throw new ApiError(timedOut ? "timeout" : "cancelled");
      throw new ApiError(error instanceof ContractError ? "contract" : "network");
    } finally {
      clearTimeout(timer);
      this.#session.signal.removeEventListener("abort", cancel);
      signal?.removeEventListener("abort", cancel);
    }
  }
  health() {
    return this.request("/health", (value) => {
      const data = object(value);
      if (data.status !== "ok" || data.api_version !== "v1" || data.service !== "loometric")
        throw new ContractError();
      return { status: "ok" as const, version: "v1" as const };
    });
  }
  capabilities() {
    return this.request("/capabilities", capabilities);
  }
  async capacity(planning: Planning) {
    const response = await this.request("/planning/capacity", capacityReport, {
      scenario: planning.raw,
    });
    if (response.data.scenarioId !== planning.id) throw new ApiError("contract");
    return response;
  }
  async verify(instance: JsonObject, proposal: JsonObject) {
    const response = await this.request("/scheduling/verify", scheduleReport, {
      instance,
      schedule: proposal,
    });
    if (response.data.instanceId !== text(instance.instance_id)) throw new ApiError("contract");
    return response;
  }
  async dispatch(instance: JsonObject, signal?: AbortSignal) {
    const r = await this.request("/scheduling/dispatch", dispatchReport, { instance }, signal);
    if (r.data.instanceId !== text(instance.instance_id)) throw new ApiError("contract");
    return r;
  }
  async validateInput(instance: JsonObject, signal?: AbortSignal) {
    const result = await this.request(
      "/scheduling/validate",
      inputValidation,
      { instance },
      signal,
    );
    if (result.data.instanceId !== text(instance.instance_id)) throw new ApiError("contract");
    return result;
  }
  async compare(baseline: JsonObject, specification: JsonObject, signal?: AbortSignal) {
    const r = await this.request(
      "/scenarios/compare",
      comparisonReport,
      { baseline, specification },
      signal,
    );
    if (
      r.data.baselineId !== text(baseline.instance_id) ||
      r.data.baselineFingerprint !== text(specification.baseline_fingerprint) ||
      r.data.id !== text(specification.scenario_id)
    )
      throw new ApiError("contract");
    return r;
  }
  async submitScheduling(instance: JsonObject, signal?: AbortSignal) {
    return this.submit("scheduling", { instance }, signal);
  }
  async submitScenario(baseline: JsonObject, specification: JsonObject, signal?: AbortSignal) {
    return this.submit("scenarios", { baseline, specification }, signal);
  }
  private async submit(kind: JobKind, body: JsonObject, signal?: AbortSignal) {
    const r = await this.request(`/jobs/${kind}`, jobInfo, body, signal);
    if (r.data.kind !== kind) throw new ApiError("contract");
    return r;
  }
  async job(id: string, signal?: AbortSignal) {
    const r = await this.request(jobPath(id), jobInfo, undefined, signal);
    if (r.data.id !== id) throw new ApiError("contract");
    return r;
  }
  async cancelJob(id: string, signal?: AbortSignal) {
    const r = await this.request(jobPath(id), jobInfo, undefined, signal, "DELETE");
    if (r.data.id !== id) throw new ApiError("contract");
    return r;
  }
  async result(id: string, signal?: AbortSignal) {
    const r = await this.request(`${jobPath(id)}/result`, jobResult, undefined, signal);
    if (r.data.id !== id) throw new ApiError("contract");
    return r;
  }
}
