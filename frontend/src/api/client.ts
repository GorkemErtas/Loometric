import { capabilities, capacityReport, scheduleReport, unwrap } from "../domain/adapters";
import type { JsonObject } from "../domain/json";
import { ContractError, encodeExact, object, parseExact, text } from "../domain/json";
import type { Planning } from "../domain/models";

export type ApiFailure =
  | "network"
  | "authentication"
  | "validation"
  | "busy"
  | "timeout"
  | "contract"
  | "server"
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
};
export class ApiError extends Error {
  constructor(
    readonly kind: ApiFailure,
    readonly status: number | null = null,
    readonly requestId: string | null = null,
  ) {
    super(messages[kind]);
  }
}

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
}

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
  ): Promise<ApiResult<T>> {
    if (this.#session.signal.aborted) throw new ApiError("cancelled");
    const controller = new AbortController();
    let timedOut = false;
    const cancel = () => controller.abort();
    this.#session.signal.addEventListener("abort", cancel, { once: true });
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
        method: encoded ? "POST" : "GET",
        headers,
        ...(encoded ? { body: encoded } : {}),
        credentials: "omit",
        redirect: "error",
        referrerPolicy: "no-referrer",
        cache: "no-store",
        signal: controller.signal,
      });
      const raw = parseExact(await responseText(response));
      if (!response.ok) {
        const envelope = object(raw);
        const id = typeof envelope.request_id === "string" ? envelope.request_id : "";
        const safeId = /^[0-9a-f-]{36}$/.test(id) && !id.includes(this.#token) ? id : null;
        const kind =
          response.status === 401 || response.status === 403
            ? "authentication"
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
        throw new ApiError(kind, response.status, safeId);
      }
      const result = unwrap(raw);
      return { data: adapt(result.data), requestId: result.requestId };
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (controller.signal.aborted) throw new ApiError(timedOut ? "timeout" : "cancelled");
      throw new ApiError(error instanceof ContractError ? "contract" : "network");
    } finally {
      clearTimeout(timer);
      this.#session.signal.removeEventListener("abort", cancel);
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
}
