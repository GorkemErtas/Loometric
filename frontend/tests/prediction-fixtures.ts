import captured from "../fixtures/experimental-prediction.response.json?raw";
import capturedV2 from "../fixtures/experimental-prediction-v2.response.json?raw";
import capturedV3 from "../fixtures/experimental-prediction-v3.response.json?raw";
import { legacyModelNames, type ModelName, type PredictionInputs } from "../src/domain/predictions";

// Captured from the real Windows-guarded API, not bundled into application code.
export function capturedResponse(
  inputs?: PredictionInputs,
  selected: readonly ModelName[] = legacyModelNames.filter((name) => name !== "rf_physics"),
) {
  const raw = JSON.parse(captured);
  if (inputs) raw.data.inputs = inputs;
  raw.data.results = raw.data.results.filter((r: { model: ModelName }) =>
    selected.includes(r.model),
  );
  raw.data.differences = raw.data.differences.filter(
    (d: { left: ModelName; right: ModelName }) =>
      selected.includes(d.left) && selected.includes(d.right),
  );
  return raw;
}

// Captured from the guarded v2 endpoint with all four actual estimators.
export function capturedV2Response(
  inputs?: PredictionInputs,
  selected: readonly ModelName[] = legacyModelNames,
) {
  const raw = JSON.parse(capturedV2);
  if (inputs) raw.data.inputs = inputs;
  raw.data.results = selected.map((name) =>
    raw.data.results.find((r: { model: ModelName }) => r.model === name),
  );
  raw.data.differences = raw.data.differences.filter(
    (d: { left: ModelName; right: ModelName }) =>
      selected.includes(d.left) && selected.includes(d.right),
  );
  if (!selected.includes("rf_physics")) raw.data.provenance.research_candidate = null;
  return raw;
}

// Real five-model local inference with explicitly hypothetical mature context.
export function capturedV3Response() {
  return JSON.parse(capturedV3);
}
