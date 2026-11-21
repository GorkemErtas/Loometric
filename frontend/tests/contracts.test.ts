import { describe, expect, it, vi } from "vitest";
import capacityRaw from "../fixtures/capacity-demo.report.json?raw";
import savedSchedule from "../fixtures/competition.verification.json?raw";
import { ApiClient, ApiError, localOrigin } from "../src/api/client";
import { datasets } from "../src/demo/catalog";
import { capacityReport, planningInput, scheduleReport } from "../src/domain/adapters";
import {
  compareExact,
  formatExact,
  percentExact,
  sumExact,
  visualPercent,
} from "../src/domain/exact";
import { ContractError, encodeExact, object, parseExact } from "../src/domain/json";

const fixture = datasets[0];
if (!fixture) throw new Error("Missing explicit synthetic fixture");
const secret = () => globalThis.crypto.randomUUID().replaceAll("-", "");
const envelope = (data: unknown) =>
  encodeExact({ api_version: "v1", request_id: "00000000-0000-4000-8000-000000000001", data });

describe("exact transport and presentation", () => {
  it("round trips high precision numeric tokens without Number", () => {
    const precision = "0.1234567890123456789012345678";
    const value = object(parseExact(`{"efficiency":${precision},"quantity":9007199254740993}`));
    expect(encodeExact(value)).toBe(`{"efficiency":${precision},"quantity":9007199254740993}`);
    expect(sumExact(["9007199254740993", "2"])).toBe("9007199254740995");
    expect(formatExact(precision)).toBe(precision);
    expect(percentExact(precision)).toBe("12.34567890123456789012345678%");
    expect(percentExact("1.05")).toBe("105%");
    expect(visualPercent("1", "3")).toBe("33.33%");
    expect(compareExact("0.10", "0.1000000000000000000000001")).toBe(-1);
  });
  it.each(["{", '{"x":NaN}', '{"x":1,"x":2}', `${"[".repeat(25)}0${"]".repeat(25)}`])(
    "rejects malformed/ambiguous JSON",
    (value) => {
      expect(() => parseExact(value)).toThrow(ContractError);
    },
  );
  it("retains zero, null and independent report scope", () => {
    expect(fixture.previewCapacity.slots.some((s) => s.standardMinutes === "0")).toBe(true);
    expect(fixture.previewCapacity.assessments.some((a) => a.potentialUnits === null)).toBe(true);
    expect(sumExact(fixture.planning.orders.map((o) => o.quantity))).toBe("480");
    const raw = object(parseExact(encodeExact(fixture.planning.raw)));
    raw.synthetic = false;
    expect(() => planningInput(raw)).toThrow(ContractError);
  });
  it.each(["schema_version", "quantity_unit", "allocation_performed", "duplicate_slot"])(
    "rejects invalid report semantics: %s",
    (key) => {
      const raw = object(parseExact(capacityRaw));
      if (key === "duplicate_slot") {
        const slots = raw.slots;
        if (!Array.isArray(slots)) throw new Error("Missing fixture slots");
        slots.push(slots[0]);
      } else
        raw[key] =
          key === "schema_version" ? parseExact("2") : key === "allocation_performed" ? true : "kg";
      expect(() => capacityReport(raw)).toThrow(ContractError);
    },
  );
  it("rejects metrics for an invalid schedule and mismatched schedule units", () => {
    const raw = object(parseExact(savedSchedule));
    object(raw.verification).feasible = false;
    raw.status = "INVALID";
    expect(() => scheduleReport(raw)).toThrow(ContractError);
    object(raw.verification).feasible = true;
    raw.status = "VALID_PARTIAL";
    object(raw.metrics).quantity_unit = "kg";
    expect(() => scheduleReport(raw)).toThrow(ContractError);
  });
});

describe("local API security and errors", () => {
  it.each([
    "https://example.com",
    "http://127.0.0.1.evil:8000",
    "http://user:secret@127.0.0.1:8000",
    "http://127.0.0.1:8000/path",
    "http://127.0.0.1:8000?token=x",
    "http://127.1:8000",
    "http://2130706433:8000",
  ])("rejects unsupported origin", (origin) => {
    expect(() => localOrigin(origin)).toThrow(ApiError);
  });
  it("sends exact JSON and explicit local request policy", async () => {
    const token = secret();
    let request: RequestInit | undefined;
    const transport: typeof fetch = vi.fn(async (_url, options) => {
      request = options;
      return new Response(envelope(fixture.planning.raw), { status: 200 });
    });
    const client = new ApiClient("http://127.0.0.1:8000", token, transport);
    await expect(client.capacity(fixture.planning)).rejects.toMatchObject({ kind: "contract" });
    expect(request?.headers).toMatchObject({
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    });
    expect(request?.body).toBe(encodeExact({ scenario: fixture.planning.raw }));
    expect(request).toMatchObject({ credentials: "omit", redirect: "error", cache: "no-store" });
    client.disconnect();
    await expect(client.health()).rejects.toMatchObject({ kind: "cancelled" });
  });
  it("does not echo credentials, native exception text or malicious error details", async () => {
    const token = secret();
    const transport: typeof fetch = vi.fn(
      async () =>
        new Response(
          encodeExact({
            api_version: "v1",
            request_id: token,
            error: { code: token, message: `secret ${token} /private/path` },
          }),
          { status: 401 },
        ),
    );
    const client = new ApiClient("http://127.0.0.1:8000", token, transport);
    try {
      await client.capabilities();
      throw new Error("Expected rejected session");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect(String(error)).not.toContain(token);
      expect(String(error)).not.toContain("/private/path");
    }
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
  it.each([
    [429, "busy"],
    [504, "timeout"],
    [422, "validation"],
    [500, "server"],
  ] as const)("maps bounded status %s", async (status, kind) => {
    const client = new ApiClient(
      "http://localhost:8000",
      secret(),
      vi.fn(async () => new Response(envelope({}), { status })),
    );
    await expect(client.capabilities()).rejects.toMatchObject({ kind, status });
  });
  it("rejects unsupported report representations", () => {
    expect(() => capacityReport({ status: "CAPACITY_ASSESSED" })).toThrow(ContractError);
  });
  it("cancels in-flight requests and does not retain a usable disconnected client", async () => {
    const transport: typeof fetch = vi.fn(
      (_url, options) =>
        new Promise<Response>((_done, reject) => {
          options?.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("Aborted", "AbortError")),
            { once: true },
          );
        }),
    );
    const client = new ApiClient("http://127.0.0.1:8000", secret(), transport);
    const pending = expect(client.health()).rejects.toMatchObject({ kind: "cancelled" });
    client.disconnect();
    await pending;
    await expect(client.health()).rejects.toMatchObject({ kind: "cancelled" });
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it("bounds a hung request without exposing native error text", async () => {
    vi.useFakeTimers();
    try {
      const transport: typeof fetch = vi.fn(
        (_url, options) =>
          new Promise<Response>((_done, reject) => {
            options?.signal?.addEventListener(
              "abort",
              () => reject(new Error("native private details")),
              { once: true },
            );
          }),
      );
      const client = new ApiClient("http://127.0.0.1:8000", secret(), transport);
      const pending = expect(client.health()).rejects.toMatchObject({ kind: "timeout" });
      await vi.advanceTimersByTimeAsync(12000);
      await pending;
    } finally {
      vi.useRealTimers();
    }
  });
});
