import captured from "../fixtures/experimental-prediction.response.json?raw";
import { type ModelName, modelNames, type PredictionInputs } from "../src/domain/predictions";

// Captured from the real Windows-guarded API, not bundled into application code.
export function capturedResponse(
  inputs?: PredictionInputs,
  selected: readonly ModelName[] = modelNames,
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
