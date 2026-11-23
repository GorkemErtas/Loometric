import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "../src/api/client";
import { parseExact } from "../src/domain/json";
import { initialInputs, inputIssues, predictionReport } from "../src/domain/predictions";
import { capturedResponse } from "./prediction-fixtures";

const adapt = (value: unknown) => predictionReport(parseExact(JSON.stringify(value)));
describe("experimental prediction contract", () => {
  it("accepts captured actual estimator outputs, error metrics and baseline identity", () => {
    const response = capturedResponse(),
      result = adapt(response.data);
    expect(result.results[0]?.prediction).toBe(0.9036296370677777);
    expect(result.results[1]?.prediction).toBe(0.8945601867754494);
    expect(result.results[2]?.status).toBe("BASELINE_COMPARISON_ONLY");
    expect(result.results[0]?.failures).toEqual(["stage_guard"]);
    expect(result.results[0]?.importance).toHaveLength(13);
    expect(result.trainingRows).toBe(14711);
  });
  it.each([
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.synthetic = false;
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.promotion_decision = "PROMOTED";
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.capacity_application_authorized = true;
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.results[0].model_status = "APPROVED";
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.results[0].descriptive_band.coverage_guarantee = true;
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.results[0].support.status = "ABSTAIN";
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.results[0].prediction = -1;
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.results[0].promotion_checks.eligible = true;
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.results[0].global_feature_importance[0].importance = -1;
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.differences[0].left_minus_right = 999;
    },
    (r: ReturnType<typeof capturedResponse>) => {
      r.data.provenance.manifest_sha256 = "untrusted";
    },
  ])("rejects contradictory model, safety and provenance evidence", (mutate) => {
    const r = capturedResponse();
    mutate(r);
    expect(() => adapt(r.data)).toThrow();
  });
  it("accepts explicit abstention without an invented number or band", () => {
    const raw = capturedResponse(initialInputs, ["random_forest"]);
    raw.data.results[0].prediction = null;
    raw.data.results[0].descriptive_band = null;
    raw.data.results[0].support = {
      status: "ABSTAIN",
      reason_codes: ["ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET"],
    };
    expect(adapt(raw.data).results[0]?.prediction).toBeNull();
  });
  it("preserves above-one estimates and unclipped band endpoints", () => {
    const raw = capturedResponse(initialInputs, ["random_forest"]);
    raw.data.results[0].prediction = 1.2;
    raw.data.results[0].descriptive_band.lower = 0.9;
    raw.data.results[0].descriptive_band.upper = 1.5;
    expect(adapt(raw.data).results[0]?.prediction).toBe(1.2);
    expect(adapt(raw.data).results[0]?.band?.upper).toBe(1.5);
  });
  it("checks quantities, integer units, decimal standards and planned time", () => {
    expect(inputIssues(initialInputs)).toEqual([]);
    expect(inputIssues({ ...initialInputs, planned_workers: 0 })).toEqual([]);
    expect(inputIssues({ ...initialInputs, planned_workers: 2.5 })).not.toEqual([]);
    expect(inputIssues({ ...initialInputs, standard_worker_minutes_per_piece: 1.001 })).not.toEqual(
      [],
    );
    expect(inputIssues({ ...initialInputs, order_quantity: 601 })).toContain(
      "Opening WIP plus planned release must equal order quantity.",
    );
    expect(inputIssues({ ...initialInputs, available_minutes: 480 })).not.toEqual([]);
  });
  it("sends closed selected-model input and rejects mismatched response context", async () => {
    const transport = vi.fn<typeof fetch>(
      async () => new Response(JSON.stringify(capturedResponse(initialInputs, ["random_forest"]))),
    );
    const client = new ApiClient(
      "http://127.0.0.1:8000",
      crypto.randomUUID().replaceAll("-", ""),
      transport,
    );
    const response = await client.predictSynthetic(initialInputs, ["random_forest"]);
    expect(response.data.results).toHaveLength(1);
    expect(JSON.parse(String(transport.mock.calls[0]?.[1]?.body))).toEqual({
      schema_version: 1,
      synthetic: true,
      prediction_context: "HYPOTHETICAL_PRE_SHIFT",
      inputs: initialInputs,
      models: ["random_forest"],
    });
    await expect(
      client.predictSynthetic({ ...initialInputs, planned_workers: 8 }, ["random_forest"]),
    ).rejects.toMatchObject({ kind: "contract" });
  });
});
