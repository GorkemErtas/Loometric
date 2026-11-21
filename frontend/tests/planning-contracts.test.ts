import { describe, expect, it, vi } from "vitest";
import golden from "../fixtures/m04-additional-workers.report.json?raw";
import { ApiClient, retryAfter } from "../src/api/client";
import { datasets } from "../src/demo/catalog";
import { reconcileJob, trackingDelay } from "../src/domain/jobs";
import { ContractError, encodeExact, object, parseExact } from "../src/domain/json";
import {
  comparisonReport,
  dispatchReport,
  evaluation,
  jobInfo,
  jobResult,
} from "../src/domain/planning";
import {
  appendChange,
  emptyDraft,
  executionBlock,
  makeChange,
  numericToken,
  type Operation,
  specification,
} from "../src/domain/scenario";
import { dispatchFixture, jobFixture } from "./planning-fixtures";

const source = () => object(parseExact(golden));
const dataset = datasets.find((item) => item.key === "capacityScenario");
if (!dataset?.instance) throw new Error("Missing frozen M04 input");
const envelope = (data: unknown) =>
  encodeExact({ api_version: "v1", request_id: "00000000-0000-4000-8000-000000000001", data });

describe("frozen planning report adapters", () => {
  it("accepts the real M04 report, exact signed deltas and explicit baseline-zero percentages", () => {
    const report = comparisonReport(source());
    expect(report.baseline.selected.metrics?.scheduled_units).toBe("45");
    expect(report.scenario.selected.metrics?.scheduled_units).toBe("55");
    expect(report.deltas.unscheduled_units).toMatchObject({
      absolute: "-10",
      percentage: "-100",
      unit: "piece",
    });
    expect(report.deltas.total_tardiness_minutes).toMatchObject({
      percentage: null,
      status: "BASELINE_ZERO",
    });
    expect(report.baseline.producer).toBe("greedy");
    expect(dispatchReport(dispatchFixture()).allocations).toHaveLength(2);
  });
  it("never transfers candidate proof to selected greedy or fabricates UNKNOWN incumbents", () => {
    const raw = object(object(source().baseline).evaluation),
      optimizer = object(raw.optimizer);
    optimizer.status = "UNKNOWN";
    optimizer.solver_status = "UNKNOWN";
    raw.fallback_reason = "UNKNOWN";
    const report = evaluation(raw);
    expect(report.optimizer.candidate).toBeNull();
    expect(report.producer).toBe("greedy");
    expect(report.full).toBe(false);
    raw.selected_full_lexicographic_optimal = true;
    expect(() => evaluation(raw)).toThrow(ContractError);
  });
  it("rejects mismatched identities, invalid metrics and false same-demand claims", () => {
    const raw = source();
    raw.same_demand_verified = false;
    expect(() => comparisonReport(raw)).toThrow(ContractError);
    const d = dispatchFixture();
    object(d.verification).feasible = false;
    expect(() => dispatchReport(d)).toThrow(ContractError);
  });
  it.each(["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"] as const)(
    "parses actual lifecycle metadata %s",
    (status) => {
      expect(jobInfo(jobFixture(status)).status).toBe(status);
    },
  );
  it("rejects arbitrary polling URLs and mismatched result types", () => {
    expect(() => jobInfo({ ...jobFixture(), polling_url: "https://example.com" })).toThrow(
      ContractError,
    );
    const result = jobResult({
      job_id: "a".repeat(32),
      job_type: "scenarios",
      result: source(),
      execution: { whole_child_wall_seconds: parseExact("0.1234567890123456789") },
    });
    expect(result.wallSeconds).toBe("0.1234567890123456789");
    expect(result.output.kind).toBe("scenarios");
  });
});

describe("immutable guided M04 input", () => {
  const planning = dataset.planning;
  it("binds to real dispatch identity, preserves exact numeric tokens and baseline bytes", () => {
    const before = encodeExact(dataset.instance),
      draft = emptyDraft(),
      value = "0.1234567890123456789012345678";
    draft.changes = appendChange(
      [],
      makeChange("set_efficiency", { profile: "PROFILE", value }, planning, []),
    );
    const spec = specification(dataset, dispatchReport(dispatchFixture()), draft, true);
    expect(spec.baseline_fingerprint).toBe(comparisonReport(source()).baselineFingerprint);
    expect(encodeExact(spec)).toContain(`"assumed_efficiency":${value}`);
    expect(encodeExact(spec)).toContain('"wall_time_seconds_per_phase":1');
    expect(encodeExact(dataset.instance)).toBe(before);
  });
  it.each([
    ["set_workers", { line: "LINE", value: "3" }],
    ["set_efficiency", { profile: "PROFILE", value: "0.75" }],
    ["set_availability", { line: "LINE", value: "unavailable" }],
    ["add_assignment", { id: "ADDED", line: "LINE", profile: "PROFILE", shift: "RESERVE" }],
    ["remove_assignment", { assignment: "ASSIGNMENT" }],
    ["remove_downtime", { downtime: "STOP" }],
    [
      "add_downtime",
      {
        id: "NEW",
        assignment: "ASSIGNMENT",
        start: "2030-01-07T08:10:00+03:00",
        end: "2030-01-07T08:15:00+03:00",
        reason: "Hypothetical",
      },
    ],
    [
      "replace_downtime",
      {
        downtime: "STOP",
        assignment: "ASSIGNMENT",
        start: "2030-01-07T08:20:00+03:00",
        end: "2030-01-07T08:30:00+03:00",
        reason: "Hypothetical",
      },
    ],
  ] as [Operation, Record<string, string>][])(
    "builds supported %s using declared references",
    (op, values) => {
      expect(makeChange(op, values, planning, []).operation).toBe(op);
    },
  );
  it("rejects conflicting lifecycle/field edits and invented resources", () => {
    const change = makeChange("set_workers", { line: "LINE", value: "3" }, planning, []);
    expect(() => appendChange([change], change)).toThrow(/already has an edit/);
    expect(() =>
      makeChange("set_workers", { line: "INVENTED", value: "3" }, planning, []),
    ).toThrow();
    expect(() =>
      appendChange([{ operation: "remove_assignment", assignment_id: "X" }], {
        operation: "add_assignment",
        assignment: { assignment_id: "X" },
      }),
    ).toThrow();
  });
  it.each(["-1", "1.1", "NaN", "0.1e-999", " 0.5", "Infinity"])(
    "rejects unsupported fractional input without clamping: %s",
    (value) => {
      expect(() => numericToken(value, "fraction")).toThrow();
    },
  );
  it("blocks oversized HTTP inputs and rejects using capacity-only inputs as executable contracts", () => {
    expect(executionBlock(datasets[0] ?? null, null)).toMatch(/not an executable/);
    expect(
      executionBlock(
        {
          ...dataset,
          planning: {
            ...planning,
            orders: Array.from({ length: 33 }, () => planning.orders[0]).filter(
              (o) => o !== undefined,
            ),
          },
        },
        null,
      ),
    ).toMatch(/never truncated/);
  });
});

describe("bounded tracking and request policy", () => {
  it("honors retry guidance, pauses at the local budget, and never rolls terminal success back", () => {
    expect(retryAfter("3")).toBe(3000);
    expect(trackingDelay(0, 0, 1, 3000)).toBe(3000);
    expect(trackingDelay(0, 0, 60, null)).toBeNull();
    expect(trackingDelay(0, 89000, 1, 2000)).toBeNull();
    expect(
      reconcileJob(jobInfo(jobFixture("SUCCEEDED")), jobInfo(jobFixture("RUNNING"))).status,
    ).toBe("SUCCEEDED");
    expect(
      reconcileJob(jobInfo(jobFixture("SUCCEEDED")), jobInfo(jobFixture("SUCCEEDED"))).status,
    ).toBe("SUCCEEDED");
    expect(() =>
      reconcileJob(jobInfo(jobFixture("SUCCEEDED")), jobInfo(jobFixture("CANCELLED"))),
    ).toThrow(ContractError);
  });
  it.each([
    [404, "missing"],
    [409, "not_ready"],
    [410, "expired"],
    [429, "busy"],
  ] as const)("surfaces job HTTP %s without automatic POST retry", async (status, kind) => {
    const transport = vi.fn<typeof fetch>(
      async () =>
        new Response(
          '{"request_id":"00000000-0000-4000-8000-000000000001","error":{"code":"JOB_QUEUE_FULL"}}',
          { status, headers: { "Retry-After": "2" } },
        ),
    );
    const client = new ApiClient(
      "http://127.0.0.1:8000",
      crypto.randomUUID().replaceAll("-", ""),
      transport,
    );
    await expect(client.submitScheduling(dataset.instance ?? {})).rejects.toMatchObject({
      kind,
      retryAfterMs: 2000,
    });
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it("cancels only through explicit DELETE and preserves external abort semantics", async () => {
    const transport = vi.fn<typeof fetch>(
      async () => new Response(envelope(jobFixture("CANCELLED"))),
    );
    const client = new ApiClient(
      "http://127.0.0.1:8000",
      crypto.randomUUID().replaceAll("-", ""),
      transport,
    );
    await client.cancelJob("a".repeat(32));
    expect(transport.mock.calls[0]?.[1]?.method).toBe("DELETE");
    const controller = new AbortController();
    controller.abort();
    await expect(client.job("a".repeat(32), controller.signal)).rejects.toMatchObject({
      kind: "cancelled",
    });
    expect(transport).toHaveBeenCalledTimes(1);
  });
});
