import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "../src/api/client";
import { parseExact } from "../src/domain/json";
import {
  initialInputs,
  inputIssues,
  modelNames,
  predictionReport,
} from "../src/domain/predictions";
import { capturedResponse, capturedV2Response } from "./prediction-fixtures";

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
  it("accepts v2 four-model provenance and spent validation without inventing a research band", () => {
    const result = adapt(capturedV2Response().data);
    expect(result.schemaVersion).toBe(2);
    expect(result.results.map((r) => r.model)).toEqual(modelNames);
    expect(result.differences).toHaveLength(6);
    const research = result.results[3];
    expect(research?.prediction).toBe(0.8919168184750277);
    expect(research?.status).toBe("RESEARCH_CANDIDATE");
    expect(research?.metrics.samples).toBe(4833);
    expect(research?.band).toBeNull();
    expect(research?.importance).toEqual([]);
    expect(result.researchManifest).toBe(
      capturedV2Response().data.results[3].provenance.manifest_sha256,
    );
  });
  it.each([
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.schema_version = 1;
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.provenance.research_candidate = null;
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.provenance.research_candidate.manifest_sha256 = "a".repeat(64);
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.provenance.research_candidate.fresh_validation = true;
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.provenance.research_candidate.experiment_id = "EXP-006";
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].provenance.manifest_sha256 = "a".repeat(64);
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].provenance.experiment_id = "EXP-006";
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].provenance.fresh_validation = true;
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].provenance.support_profile_source = "VALIDATION";
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].provenance.validation_rows = 4832;
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].validation_metrics.samples = 4832;
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].model_status = "EXPERIMENTAL_NOT_PROMOTED";
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].descriptive_band = r.data.results[0].descriptive_band;
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].global_feature_importance = r.data.results[0].global_feature_importance;
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].explanation_method = "SHAP";
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.results[3].promotion_checks = { eligible: true };
    },
    (r: ReturnType<typeof capturedV2Response>) => {
      r.data.differences[5] = r.data.differences[0];
    },
  ])("rejects contradictory v2 candidate provenance or comparison evidence", (mutate) => {
    const raw = capturedV2Response();
    mutate(raw);
    expect(() => adapt(raw.data)).toThrow();
  });
  it.each([{ models: modelNames }, { models: ["rf_physics"] as const }])(
    "uses the v2 endpoint for selected RF Physics models $models",
    async ({ models }) => {
      const transport = vi.fn<typeof fetch>(
        async () => new Response(JSON.stringify(capturedV2Response(initialInputs, models))),
      );
      const client = new ApiClient(
        "http://127.0.0.1:8000",
        crypto.randomUUID().replaceAll("-", ""),
        transport,
      );
      const response = await client.predictSynthetic(initialInputs, [...models]);
      expect(response.data.results.map((r) => r.model)).toEqual(models);
      expect(String(transport.mock.calls[0]?.[0])).toBe(
        "http://127.0.0.1:8000/api/v1/predictions/synthetic/v2",
      );
      expect(JSON.parse(String(transport.mock.calls[0]?.[1]?.body))).toEqual({
        schema_version: 2,
        synthetic: true,
        prediction_context: "HYPOTHETICAL_PRE_SHIFT",
        inputs: initialInputs,
        models,
      });
    },
  );
  it("accepts explicit v2 legacy-only responses and rejects response-version downgrade", async () => {
    expect(
      adapt(capturedV2Response(initialInputs, ["random_forest"]).data).researchManifest,
    ).toBeNull();
    const transport = vi.fn<typeof fetch>(
      async () => new Response(JSON.stringify(capturedResponse())),
    );
    const client = new ApiClient(
      "http://127.0.0.1:8000",
      crypto.randomUUID().replaceAll("-", ""),
      transport,
    );
    await expect(client.predictSynthetic(initialInputs, [...modelNames])).rejects.toMatchObject({
      kind: "contract",
    });
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
    expect(String(transport.mock.calls[0]?.[0])).toBe(
      "http://127.0.0.1:8000/api/v1/predictions/synthetic",
    );
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
