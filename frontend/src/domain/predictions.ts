import { isLosslessNumber } from "lossless-json";
import { ContractError, list, object, text, texts } from "./json";

export const modelNames = ["random_forest", "histogram_gradient_boosting", "grouped_mean"] as const;
export type ModelName = (typeof modelNames)[number];
export const modelLabels: Record<ModelName, string> = {
  random_forest: "Random Forest",
  histogram_gradient_boosting: "HistGradientBoosting",
  grouped_mean: "Grouped Mean baseline",
};
export interface PredictionInputs {
  stage: string;
  shift_kind: string;
  weekday: number;
  planned_workers: number;
  skill_level: number;
  style_complexity: number;
  standard_worker_minutes_per_piece: number;
  planned_machine_available: boolean;
  available_minutes: number;
  planned_downtime_minutes: number;
  opening_wip_pieces: number;
  planned_release_pieces: number;
  order_quantity: number;
}
export const initialInputs: PredictionInputs = {
  stage: "sewing",
  shift_kind: "day",
  weekday: 0,
  planned_workers: 6,
  skill_level: 3,
  style_complexity: 3,
  standard_worker_minutes_per_piece: 4,
  planned_machine_available: true,
  available_minutes: 420,
  planned_downtime_minutes: 30,
  opening_wip_pieces: 100,
  planned_release_pieces: 500,
  order_quantity: 600,
};
export const fields = [
  [
    "planned_workers",
    "Planned workers",
    "Dedicated crew headcount; 0 means undefined planned capacity.",
    0,
    100,
    1,
  ],
  ["skill_level", "Skill level", "Declared crew qualification level, from 1 to 5.", 1, 5, 1],
  ["style_complexity", "Product complexity", "Declared style complexity, from 1 to 5.", 1, 5, 1],
  [
    "standard_worker_minutes_per_piece",
    "Standard worker-minutes per piece",
    "Declared labor standard per completed good piece; at most 2 decimals.",
    0.01,
    100,
    0.01,
  ],
  [
    "available_minutes",
    "Planned available time (minutes)",
    "Elapsed time after the union of breaks, downtime and machine stops. Exclude stops once.",
    0,
    480,
    1,
  ],
  [
    "planned_downtime_minutes",
    "Planned downtime (minutes)",
    "Already accounted for in available time; do not subtract it again.",
    0,
    480,
    1,
  ],
  [
    "opening_wip_pieces",
    "Opening WIP (pieces)",
    "Pieces already waiting at this production stage before shift start.",
    0,
    1000000,
    1,
  ],
  [
    "planned_release_pieces",
    "Planned release (pieces)",
    "Pieces planned to enter this stage; opening WIP + release must equal order quantity.",
    0,
    1000000,
    1,
  ],
  [
    "order_quantity",
    "Order quantity (pieces)",
    "Total work declared for this order-stage observation.",
    1,
    1000000,
    1,
  ],
] as const;
export type NumericField = (typeof fields)[number][0];
export function inputIssues(inputs: PredictionInputs): string[] {
  const issues: string[] = [];
  for (const [key, label, , minimum, maximum, step] of fields) {
    const value = inputs[key];
    if (
      !Number.isFinite(value) ||
      value < minimum ||
      value > maximum ||
      (step === 1
        ? !Number.isInteger(value)
        : Math.abs(value * 100 - Math.round(value * 100)) > 1e-8)
    )
      issues.push(
        `${label} requires a ${step === 1 ? "whole number" : "number with at most two decimals"} from ${minimum} to ${maximum}.`,
      );
  }
  if (inputs.opening_wip_pieces + inputs.planned_release_pieces !== inputs.order_quantity)
    issues.push("Opening WIP plus planned release must equal order quantity.");
  if (inputs.available_minutes + inputs.planned_downtime_minutes > 480)
    issues.push("Available time plus planned downtime must fit within a 480 minute shift.");
  return issues;
}
// This separate ML wire contract intentionally carries finite float64 estimates.
// Frozen planning decimal adapters never call this conversion.
function finite(value: unknown): number {
  const number = isLosslessNumber(value) ? Number(value.value) : value;
  if (typeof number !== "number" || !Number.isFinite(number)) throw new ContractError();
  return number;
}
function identity(value: unknown): ModelName {
  if (!modelNames.includes(value as ModelName)) throw new ContractError();
  return value as ModelName;
}
function fingerprint(value: unknown): string {
  const result = text(value);
  if (!/^[a-f0-9]{64}$/.test(result)) throw new ContractError();
  return result;
}
function metrics(value: unknown) {
  const raw = object(value);
  const result = {
    mae: finite(raw.mae),
    rmse: finite(raw.rmse),
    r2: finite(raw.r2),
    samples: finite(raw.samples),
  };
  if (
    result.mae < 0 ||
    result.rmse < 0 ||
    !Number.isSafeInteger(result.samples) ||
    result.samples < 1
  )
    throw new ContractError();
  return result;
}
export function readInputs(value: unknown): PredictionInputs {
  const raw = object(value);
  if (Object.keys(raw).length !== 13 || typeof raw.planned_machine_available !== "boolean")
    throw new ContractError();
  const inputs: PredictionInputs = {
    ...initialInputs,
    stage: text(raw.stage),
    shift_kind: text(raw.shift_kind),
    weekday: finite(raw.weekday),
    planned_machine_available: raw.planned_machine_available,
  };
  for (const [key] of fields) inputs[key] = finite(raw[key]);
  if (
    inputIssues(inputs).length ||
    !Number.isInteger(inputs.weekday) ||
    inputs.weekday < 0 ||
    inputs.weekday > 6
  )
    throw new ContractError();
  return inputs;
}
export function sameInputs(a: PredictionInputs, b: PredictionInputs): boolean {
  return (Object.keys(initialInputs) as (keyof PredictionInputs)[]).every(
    (key) => a[key] === b[key],
  );
}
function readResult(value: unknown) {
  const raw = object(value),
    model = identity(raw.model),
    support = object(raw.support);
  const expectedIdentity = {
    random_forest: "forest-12",
    histogram_gradient_boosting: "hist-31",
    grouped_mean: "grouped_mean",
  }[model];
  if (
    raw.identity !== expectedIdentity ||
    raw.model_version !== "synthetic-experimental-v1" ||
    raw.model_status !==
      (model === "grouped_mean" ? "BASELINE_COMPARISON_ONLY" : "EXPERIMENTAL_NOT_PROMOTED") ||
    !["ABSTAIN", "REVIEW_REQUIRED", "SUPPORTED_EXPERIMENTAL"].includes(text(support.status))
  )
    throw new ContractError();
  const prediction = raw.prediction === null ? null : finite(raw.prediction);
  if (
    (support.status === "ABSTAIN") !== (prediction === null) ||
    (prediction !== null && (prediction < 0 || prediction > 3))
  )
    throw new ContractError();
  const reasons = texts(support.reason_codes);
  if (reasons.length === 0 || reasons.some((r) => !/^[A-Z_:a-z_]+$/.test(r)))
    throw new ContractError();
  let band: { lower: number; upper: number; radius: number; coverage: number } | null = null;
  if (raw.descriptive_band !== null) {
    const b = object(raw.descriptive_band),
      diagnostic = object(b.empirical_benchmark_validation);
    if (
      b.interpretation !== "DEVELOPMENT_RESIDUAL_BAND_NOT_CALIBRATED" ||
      b.coverage_guarantee !== false ||
      b.selection_reused_folds !== true
    )
      throw new ContractError();
    band = {
      lower: finite(b.lower),
      upper: finite(b.upper),
      radius: finite(b.radius),
      coverage: finite(diagnostic.empirical_coverage),
    };
    if (
      prediction === null ||
      band.radius < 0 ||
      band.lower > prediction ||
      band.upper < prediction ||
      band.coverage < 0 ||
      band.coverage > 1
    )
      throw new ContractError();
  }
  if ((band === null) !== (prediction === null)) throw new ContractError();
  let failures: string[] = [],
    maximumStageRegression: number | null = null,
    worstErrorRegression: number | null = null;
  if (model !== "grouped_mean") {
    const checks = object(raw.promotion_checks),
      gates = object(checks.gates);
    if (checks.eligible !== false || Object.values(gates).some((v) => typeof v !== "boolean"))
      throw new ContractError();
    failures = Object.entries(gates)
      .filter(([, pass]) => pass === false)
      .map(([key]) => key);
    if (!failures.length) throw new ContractError();
    maximumStageRegression = finite(checks.maximum_stage_regression_percent);
    worstErrorRegression = finite(object(checks.tail_regression_percent).worst_absolute_error);
  } else if (raw.promotion_checks !== null) throw new ContractError();
  const importance =
    raw.global_feature_importance === null
      ? []
      : list(raw.global_feature_importance).map((value) => {
          const row = object(value);
          return { feature: text(row.feature), importance: finite(row.importance) };
        });
  if (
    model === "random_forest" &&
    (importance.length !== 13 ||
      new Set(importance.map((r) => r.feature)).size !== 13 ||
      importance.some((r) => !(r.feature in initialInputs) || r.importance < 0) ||
      Math.abs(importance.reduce((sum, r) => sum + r.importance, 0) - 1) > 1e-8)
  )
    throw new ContractError();
  return {
    model,
    identity: text(raw.identity),
    version: text(raw.model_version),
    status: text(raw.model_status),
    prediction,
    support: text(support.status),
    reasons,
    band,
    metrics: metrics(raw.validation_metrics),
    stageMetrics:
      raw.validation_stage_metrics === null ? null : metrics(raw.validation_stage_metrics),
    failures,
    maximumStageRegression,
    worstErrorRegression,
    importance,
  };
}
export function predictionReport(value: unknown) {
  const raw = object(value);
  if (
    finite(raw.schema_version) !== 1 ||
    raw.synthetic !== true ||
    raw.prediction_context !== "HYPOTHETICAL_PRE_SHIFT" ||
    raw.target !== "standard_capacity_attainment" ||
    raw.units !== "dimensionless_standard_worker_minutes_per_planned_worker_minute" ||
    raw.promotion_decision !== "NO_ML_PROMOTION" ||
    raw.capacity_application_authorized !== false ||
    raw.target_to_efficiency !== "NOT_IMPLEMENTED"
  )
    throw new ContractError();
  const results = list(raw.results).map(readResult);
  if (
    results.length < 1 ||
    results.length > 3 ||
    new Set(results.map((r) => r.model)).size !== results.length
  )
    throw new ContractError();
  const provenance = object(raw.provenance),
    training = object(provenance.training),
    source = object(training.source);
  if (provenance.dataset_version !== "synthetic-ml-v1" || training.partition !== "train")
    throw new ContractError();
  const differences = list(raw.differences).map((value) => {
    const row = object(value),
      left = identity(row.left),
      right = identity(row.right);
    const a = results.find((r) => r.model === left),
      b = results.find((r) => r.model === right);
    if (!a || !b || a === b) throw new ContractError();
    const difference = row.left_minus_right === null ? null : finite(row.left_minus_right);
    const expected =
      a.prediction === null || b.prediction === null ? null : a.prediction - b.prediction;
    if (
      expected === null
        ? difference !== null
        : difference === null || Math.abs(difference - expected) > 1e-12
    )
      throw new ContractError();
    return { left, right, difference };
  });
  if (differences.length !== (results.length * (results.length - 1)) / 2) throw new ContractError();
  const execution = object(raw.execution);
  return {
    inputs: readInputs(raw.inputs),
    inputFingerprint: fingerprint(raw.input_fingerprint),
    results,
    differences,
    manifest: fingerprint(provenance.manifest_sha256),
    dataset: text(provenance.dataset_version),
    experiment: text(provenance.experiment_id),
    trainingRows: finite(training.rows),
    trainingFirst: text(training.first_date),
    trainingLast: text(training.last_date),
    trainingFingerprint: fingerprint(source.train_fingerprint),
    limitations: texts(raw.limitations),
    seconds: finite(execution.whole_child_wall_seconds),
  };
}
export type PredictionReport = ReturnType<typeof predictionReport>;
export type PredictionResult = PredictionReport["results"][number];
