import { describe, expect, it, vi } from "vitest";
import { datasets } from "../src/demo/catalog";
import { encodeExact, object, parseExact } from "../src/domain/json";
import type { Capabilities } from "../src/domain/models";
import {
  calendarOf,
  cloneInput,
  exportInput,
  importInput,
  inputValidation,
  inspectInput,
  newInput,
  planningOf,
  readInputFile,
  rows,
  userDataset,
} from "../src/domain/production";

const source = datasets.find((d) => d.key === "competition")?.instance;
if (!source) throw new Error("Missing synthetic fixture");
const input = () => cloneInput(source);
const first = (value: unknown) => object(rows(value)[0]);
const limits = (name: string, value: string): Capabilities => ({
  policies: [],
  operations: [],
  methods: [],
  limits: [{ name, value }],
  jobLimits: [],
  limitations: [],
  prediction: "offline",
});

describe("strict local synthetic instance contracts", () => {
  it("imports all original executable catalog inputs without changing their numeric tokens", () => {
    for (const dataset of datasets.filter((d) => d.instance)) {
      const before = encodeExact(dataset.instance);
      expect(encodeExact(importInput(before))).toBe(before);
      expect(exportInput(importInput(before))).toBe(`${before}\n`);
      expect(inspectInput(object(dataset.instance))).toEqual([]);
    }
    expect(() => importInput(encodeExact(datasets[0]?.planning.raw))).toThrow();
  });
  it("preserves exact Decimal lexemes, huge integer counts, optional null/evidence and collection order", () => {
    const raw = input(),
      p = planningOf(raw);
    first(first(p.styles).standards).standard_minutes_per_unit = parseExact(
      "0.1234567890123456789012345678",
    );
    first(p.capacity_profiles).assumed_efficiency = parseExact("0.8000000000000000000000000001e0");
    first(p.orders).quantity = parseExact("9007199254740993123456789");
    first(p.capacity_profiles).evidence_reference = null;
    const serialized = exportInput(raw);
    expect(serialized).toContain('"standard_minutes_per_unit":0.1234567890123456789012345678');
    expect(serialized).toContain('"assumed_efficiency":0.8000000000000000000000000001e0');
    expect(serialized).toContain('"quantity":9007199254740993123456789');
    expect(exportInput(importInput(serialized))).toBe(serialized);
    first(p.capacity_profiles).evidence_reference = "Synthetic laboratory assumption";
    expect(exportInput(importInput(exportInput(raw)))).toBe(exportInput(raw));
  });
  it.each([
    [
      "missing style reference",
      (r: ReturnType<typeof input>) => {
        first(planningOf(r).orders).style_id = "absent";
      },
    ],
    [
      "duplicate IDs",
      (r: ReturnType<typeof input>) => {
        const p = planningOf(r);
        rows(p.orders).push(cloneInput(first(p.orders)));
      },
    ],
    [
      "zero quantity",
      (r: ReturnType<typeof input>) => {
        first(planningOf(r).orders).quantity = parseExact("0");
      },
    ],
    [
      "fractional workers",
      (r: ReturnType<typeof input>) => {
        first(planningOf(r).lines).worker_count = parseExact("1.5");
      },
    ],
    [
      "invalid date",
      (r: ReturnType<typeof input>) => {
        first(planningOf(r).orders).due_date = "2030-02-30";
      },
    ],
    [
      "release after due",
      (r: ReturnType<typeof input>) => {
        first(planningOf(r).orders).release_date = "2099-01-01";
      },
    ],
    [
      "unrecognized fields",
      (r: ReturnType<typeof input>) => {
        planningOf(r).source_sha256 = "inspection metadata";
      },
    ],
    [
      "non-synthetic",
      (r: ReturnType<typeof input>) => {
        planningOf(r).synthetic = false;
      },
    ],
    [
      "wrong schema",
      (r: ReturnType<typeof input>) => {
        r.schema_version = parseExact("2");
      },
    ],
    [
      "wrong policy",
      (r: ReturnType<typeof input>) => {
        r.policy_version = "other";
      },
    ],
    [
      "quoted Decimal",
      (r: ReturnType<typeof input>) => {
        first(planningOf(r).capacity_profiles).assumed_efficiency = "0.8";
      },
    ],
    [
      "efficiency above one",
      (r: ReturnType<typeof input>) => {
        first(planningOf(r).capacity_profiles).assumed_efficiency = parseExact("1.01");
      },
    ],
    [
      "negative standard",
      (r: ReturnType<typeof input>) => {
        first(first(planningOf(r).styles).standards).standard_minutes_per_unit = parseExact("-0.1");
      },
    ],
    [
      "duplicate standard",
      (r: ReturnType<typeof input>) => {
        const s = first(planningOf(r).styles);
        rows(s.standards).push(cloneInput(first(s.standards)));
      },
    ],
    [
      "duplicate capability",
      (r: ReturnType<typeof input>) => {
        const p = planningOf(r),
          copy = cloneInput(first(p.capabilities));
        copy.capability_id = "another";
        rows(p.capabilities).push(copy);
      },
    ],
    [
      "conflicting profile line",
      (r: ReturnType<typeof input>) => {
        first(planningOf(r).capacity_profiles).line_id = "absent";
      },
    ],
    [
      "missing assignment",
      (r: ReturnType<typeof input>) => {
        first(calendarOf(r).assignments).shift_id = "absent";
      },
    ],
    [
      "unknown downtime reference",
      (r: ReturnType<typeof input>) => {
        calendarOf(r).planned_downtime = [
          {
            downtime_id: "D",
            assignment_id: "absent",
            reason: "synthetic",
            interval: { start: "2030-01-07T08:00:00+03:00", end: "2030-01-07T08:01:00+03:00" },
          },
        ];
      },
    ],
    [
      "invalid timestamp",
      (r: ReturnType<typeof input>) => {
        object(r.horizon).start = "2030-02-30T08:00:00+03:00";
      },
    ],
    [
      "non-minute boundary",
      (r: ReturnType<typeof input>) => {
        object(r.horizon).start = "2030-01-07T08:00:01+03:00";
      },
    ],
    [
      "wrong standard unit",
      (r: ReturnType<typeof input>) => {
        first(first(planningOf(r).styles).standards).measurement_unit = "elapsed_minutes";
      },
    ],
  ])("rejects %s without mutating the input", (_, mutate) => {
    const raw = input();
    mutate(raw);
    const before = encodeExact(raw);
    expect(inspectInput(raw).length).toBeGreaterThan(0);
    expect(() => importInput(before)).toThrow();
    expect(encodeExact(raw)).toBe(before);
  });
  it("leaves interval interaction checks to Python, explicitly requiring backend validation", () => {
    const raw = input(),
      shift = first(planningOf(raw).shifts);
    shift.breaks = [{ start: "2030-01-01T00:00:00+03:00", end: "2030-01-01T00:01:00+03:00" }];
    expect(inspectInput(raw)).toEqual([]);
    expect(importInput(exportInput(raw))).toBeDefined();
  });
  it("starts empty with generated identities and frozen metadata, without production assumptions", () => {
    const a = newInput(),
      b = newInput();
    expect(a.instance_id).not.toBe(b.instance_id);
    expect(planningOf(a).assumptions).toEqual([]);
    expect(inspectInput(a).length).toBeGreaterThan(0);
    expect(() => exportInput(a)).toThrow();
  });
  it.each([
    "record_id,source_sha256\na,b",
    '{"instance_id":"a","instance_id":"b"}',
    `${"[".repeat(25)}0${"]".repeat(25)}`,
    " ".repeat(262145),
    '{"x":NaN}',
    '{"x":Infinity}',
    '{"__proto__":{"polluted":true}}',
  ])("rejects invalid or unsafe import with safe errors", (source) => {
    expect(() => importInput(source)).toThrow();
    expect({}).not.toHaveProperty("polluted");
  });
  it.each([
    "max_orders",
    "max_operations",
    "max_body_bytes",
    "max_nodes",
    "max_depth",
    "max_collection_items",
    "max_string_length",
    "max_number_length",
  ])("honors smaller server %s limits", (name) => {
    expect(() => importInput(encodeExact(input()), limits(name, "1"))).toThrow();
  });
  it("rejects oversized files before reading and rejects invalid UTF-8, without network access", async () => {
    const arrayBuffer = vi.fn(),
      fetcher = vi.spyOn(globalThis, "fetch");
    await expect(
      readInputFile({ size: 262145, arrayBuffer } as unknown as File, null),
    ).rejects.toThrow("256 KiB");
    expect(arrayBuffer).not.toHaveBeenCalled();
    await expect(
      readInputFile(
        { size: 1, arrayBuffer: async () => new Uint8Array([255]).buffer } as File,
        null,
      ),
    ).rejects.toThrow("UTF-8");
    expect(fetcher).not.toHaveBeenCalled();
    fetcher.mockRestore();
  });
  it("requires matching validation identity and produces an independent immutable dataset copy", async () => {
    const raw = input(),
      before = encodeExact(raw),
      validation = { instanceId: String(raw.instance_id), fingerprint: "a".repeat(64) };
    const dataset = await userDataset(raw, validation);
    first(planningOf(raw).orders).quantity = parseExact("999");
    expect(encodeExact(dataset.instance)).toBe(before);
    expect(dataset.sourceHash).toMatch(/^[a-f0-9]{64}$/);
    expect(dataset.validatedFingerprint).toBe(validation.fingerprint);
    await expect(userDataset(raw, { ...validation, instanceId: "other" })).rejects.toThrow();
  });
  it("accepts only the exact validation response schema and no feasibility claim", () => {
    const raw = object(
      parseExact(
        '{"schema_version":1,"policy_version":"whole-stage-minute-v1","synthetic":true,"status":"VALID_INPUT","instance_id":"local","instance_fingerprint":"' +
          "a".repeat(64) +
          '"}',
      ),
    );
    expect(inputValidation(raw).instanceId).toBe("local");
    expect(() => inputValidation({ ...raw, feasible: true })).toThrow();
    expect(() => inputValidation({ ...raw, instance_fingerprint: "invalid" })).toThrow();
  });
});
