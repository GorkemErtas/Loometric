import { describe, expect, it, vi } from "vitest";
import { ApiClient, localOrigin } from "../src/api/client";
import { parseExact } from "../src/domain/json";
import {
  emptyHistory,
  historyIssues,
  initialInputs,
  modelNames,
  predictionReport,
} from "../src/domain/predictions";
import { capturedV3Response } from "./prediction-fixtures";

const adapt = (raw: unknown) => predictionReport(parseExact(JSON.stringify(raw)));
describe("mature-history fifth experimental model", () => {
  it("decodes actual five-model outputs and matched same-world evidence", () => {
    const r = adapt(capturedV3Response().data);
    expect(r.schemaVersion).toBe(3);
    expect(r.results.map((v) => v.model)).toEqual(modelNames);
    expect(r.results[4]?.prediction).toBe(0.834534223925279);
    expect(r.results[4]?.metrics.mae).toBe(0.05590134548980302);
    expect(r.results.every((v) => v.metrics.samples === 1426)).toBe(true);
    expect(r.historyTrainingRows).toBe(5700);
    expect(r.results[4]?.band).toBeNull();
    expect(r.differences).toHaveLength(10);
  });
  it.each([
    (r: ReturnType<typeof capturedV3Response>) => {
      r.schema_version = 2;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.provenance.history_candidate.fresh_validation = true;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.provenance.history_candidate.training_rows = 10;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.results[4].provenance.manifest_sha256 = "a".repeat(64);
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.results[4].provenance.requires_mature_history = false;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.results[4].model_status = "APPROVED";
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.results[4].matched_metrics.baseline.samples = 4833;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.results[4].matched_metrics.baseline.p95_absolute_error = -1;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      delete r.results[0].matched_metrics;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.history = emptyHistory;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.history.history_age_hours = 73;
    },
    (r: ReturnType<typeof capturedV3Response>) => {
      r.history.current_actual_attainment = 1;
    },
  ])("rejects altered evidence, promotion or invalid context", (mutate) => {
    const raw = capturedV3Response().data;
    mutate(raw);
    expect(() => adapt(raw)).toThrow();
  });
  it("sends only closed v3 hypothetical inputs and rejects mismatched history", async () => {
    const raw = capturedV3Response();
    const transport = vi.fn<typeof fetch>(async () => new Response(JSON.stringify(raw)));
    const client = new ApiClient(
      "http://127.0.0.1:8000",
      crypto.randomUUID().replaceAll("-", ""),
      transport,
    );
    await client.predictSynthetic(initialInputs, [...modelNames], undefined, raw.data.history);
    expect(String(transport.mock.calls[0]?.[0])).toMatch(/\/synthetic\/v3$/);
    expect(JSON.parse(String(transport.mock.calls[0]?.[1]?.body))).toEqual({
      schema_version: 3,
      synthetic: true,
      prediction_context: "HYPOTHETICAL_PRE_SHIFT",
      inputs: initialInputs,
      models: modelNames,
      history: raw.data.history,
    });
    await expect(client.predictSynthetic(initialInputs, [...modelNames])).rejects.toMatchObject({
      kind: "contract",
    });
  });
  it("preserves explicit missing context and consistency checks", () => {
    expect(historyIssues(emptyHistory)).toEqual([]);
    expect(historyIssues({ ...emptyHistory, recent_attainment_mean: 1 })).not.toEqual([]);
    expect(historyIssues({ ...emptyHistory, history_count: 1 })).not.toEqual([]);
  });
  it("allows an exact HTTPS page origin while retaining loopback development", () => {
    expect(localOrigin("https://demo.example", "https://demo.example")).toBe(
      "https://demo.example",
    );
    expect(localOrigin("http://127.0.0.1:8000", "https://demo.example")).toBe(
      "http://127.0.0.1:8000",
    );
    for (const value of [
      "https://other.example",
      "http://demo.example",
      "https://demo.example/path",
      "https://user@demo.example",
    ])
      expect(() => localOrigin(value, "https://demo.example")).toThrow();
  });
});
