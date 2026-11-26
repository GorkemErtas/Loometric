import { isLosslessNumber } from "lossless-json";
import { ContractError, list, object, text, texts } from "./json";

export const legacyModelNames = [
  "random_forest",
  "histogram_gradient_boosting",
  "grouped_mean",
  "rf_physics",
] as const;
export const modelNames = [...legacyModelNames, "history_boost"] as const;

export type ModelName = (typeof modelNames)[number];

export const modelLabels: Record<ModelName, string> = {
  random_forest: "Random Forest",
  histogram_gradient_boosting: "HistGradientBoosting",
  grouped_mean: "Grouped Mean baseline",
  rf_physics: "RF Physics",
  history_boost: "History Boost",
};

export interface MatureHistory {
  recent_attainment_mean: number | null;
  recent_attainment_std: number | null;
  history_count: number;
  uncensored_history_count: number;
  history_age_hours: number | null;
}
export const emptyHistory: MatureHistory = {
  recent_attainment_mean: null,
  recent_attainment_std: null,
  history_count: 0,
  uncensored_history_count: 0,
  history_age_hours: null,
};
export function historyIssues(h: MatureHistory): string[] {
  const issues: string[] = [];
  if (
    ![h.history_count, h.uncensored_history_count].every(
      (n) => Number.isInteger(n) && n >= 0 && n <= 7,
    ) ||
    h.uncensored_history_count > h.history_count
  )
    issues.push(
      "History counts must be whole numbers from 0 to 7, with uncensored count no larger than total.",
    );
  const available = h.uncensored_history_count >= 2;
  if (
    available
      ? ![h.recent_attainment_mean, h.recent_attainment_std].every(
          (n) => n !== null && Number.isFinite(n) && n >= 0 && n <= 3,
        )
      : h.recent_attainment_mean !== null || h.recent_attainment_std !== null
  )
    issues.push(
      "Mean and standard deviation require at least two uncensored mature reports; otherwise leave both empty.",
    );
  if (
    h.history_count > 0
      ? h.history_age_hours === null ||
        !Number.isFinite(h.history_age_hours) ||
        h.history_age_hours < 0 ||
        h.history_age_hours > 8760
      : h.history_age_hours !== null
  )
    issues.push("History age must describe an existing mature report, from 0 to 8760 hours.");
  return issues;
}

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
function readHistory(value: unknown): MatureHistory {
  const raw = object(value);
  if (Object.keys(raw).length !== 5) throw new ContractError();
  const nullable = (value: unknown) => (value === null ? null : finite(value));
  const h: MatureHistory = {
    recent_attainment_mean: nullable(raw.recent_attainment_mean),
    recent_attainment_std: nullable(raw.recent_attainment_std),
    history_count: finite(raw.history_count),
    uncensored_history_count: finite(raw.uncensored_history_count),
    history_age_hours: nullable(raw.history_age_hours),
  };
  if (historyIssues(h).length) throw new ContractError();
  return h;
}
const rfPhysicsManifest = "55b09223c57e6c52261a71bc777edddc6116b88b8ffae3f7b0f9cc9075cc51f0";
const historyManifest = "75dee7b7cd535c3fa9ea2ea5995d2949b88c117de27c16706fc860c6068374cd";
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
    rf_physics: "rf_physics",
    history_boost: "history_boost",
  }[model];

  const isHistory = model === "history_boost";
  const isResearch = model === "rf_physics" || isHistory;
  if (model === "rf_physics") {
    const provenance = object(raw.provenance);
    if (
      provenance.experiment_id !== "EXP-008" ||
      provenance.manifest_sha256 !== rfPhysicsManifest ||
      provenance.fresh_validation !== false ||
      provenance.support_profile_source !== "V1_BENCHMARK_TRAINING" ||
      finite(provenance.validation_rows) !== 4833 ||
      finite(provenance.validation_rows) !== metrics(raw.validation_metrics).samples ||
      raw.validation_stage_metrics !== null ||
      raw.global_feature_importance !== null ||
      raw.explanation_method !== "NOT_COMPUTED"
    )
      throw new ContractError();
  }
  if (isHistory) {
    const p = object(raw.provenance);
    if (
      p.experiment_id !== "EXP-010" ||
      p.manifest_sha256 !== historyManifest ||
      p.fresh_validation !== false ||
      p.requires_mature_history !== true ||
      p.support_profile_source !== "NEW_DEVELOPMENT_TRAINING_ONLY" ||
      raw.descriptive_band !== null ||
      raw.global_feature_importance !== null
    )
      throw new ContractError();
  }

  if (
    raw.identity !== expectedIdentity ||
    raw.model_version !==
      (isHistory
        ? "synthetic-experimental-v3"
        : isResearch
          ? "synthetic-experimental-v2"
          : "synthetic-experimental-v1") ||
    raw.model_status !==
      (isHistory
        ? "EXPERIMENTAL_HISTORY_CANDIDATE"
        : isResearch
          ? "RESEARCH_CANDIDATE"
          : model === "grouped_mean"
            ? "BASELINE_COMPARISON_ONLY"
            : "EXPERIMENTAL_NOT_PROMOTED") ||
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
  if (isResearch) {
    if (band !== null) throw new ContractError();
  } else if ((band === null) !== (prediction === null)) {
    throw new ContractError();
  }

  let failures: string[] = [],
    maximumStageRegression: number | null = null,
    worstErrorRegression: number | null = null;
  if (model !== "grouped_mean" && !isResearch) {
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
  const matched = raw.matched_metrics === undefined ? null : object(raw.matched_metrics);
  const readMatched = (condition: "baseline" | "disruption") => {
    if (!matched) throw new ContractError();
    const value = object(matched[condition]);
    if (
      finite(value.p95_absolute_error) < 0 ||
      finite(value.actual_worst_absolute_error) < finite(value.p95_absolute_error) ||
      metrics(value).samples !== 1426
    )
      throw new ContractError();
    return {
      ...metrics(value),
      bias: finite(value.bias),
      p95: finite(value.p95_absolute_error),
      worst: finite(value.actual_worst_absolute_error),
    };
  };
  const matchedMetrics = matched
    ? { baseline: readMatched("baseline"), disruption: readMatched("disruption") }
    : null;
  return {
    model,
    identity: text(raw.identity),
    version: text(raw.model_version),
    status: text(raw.model_status),
    prediction,
    support: text(support.status),
    reasons,
    band,
    metrics: matchedMetrics?.baseline ?? metrics(raw.validation_metrics),
    matchedMetrics,
    stageMetrics:
      matchedMetrics || raw.validation_stage_metrics === null
        ? null
        : metrics(raw.validation_stage_metrics),
    failures,
    maximumStageRegression,
    worstErrorRegression,
    importance,
  };
}
export function predictionReport(value: unknown) {
  const raw = object(value);
  const schemaVersion = finite(raw.schema_version);
  if (
    ![1, 2, 3].includes(schemaVersion) ||
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
    results.length > (schemaVersion === 3 ? 5 : schemaVersion === 2 ? 4 : 3) ||
    (schemaVersion !== 3 && results.some((r) => r.model === "history_boost")) ||
    (schemaVersion !== 3 && results.some((r) => r.matchedMetrics !== null)) ||
    (schemaVersion === 1 && results.some((r) => r.model === "rf_physics")) ||
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
  if (
    new Set(differences.map(({ left, right }) => [left, right].sort().join(":"))).size !==
    differences.length
  )
    throw new ContractError();
  const hasResearch = results.some((r) => r.model === "rf_physics");

  let researchManifest: string | null = null;

  if (hasResearch) {
    const research = object(provenance.research_candidate);

    if (
      ![2, 3].includes(schemaVersion) ||
      research.model !== "rf_physics" ||
      research.experiment_id !== "EXP-008" ||
      research.fresh_validation !== false
    )
      throw new ContractError();

    researchManifest = fingerprint(research.manifest_sha256);

    if (researchManifest !== rfPhysicsManifest) throw new ContractError();
  } else if (schemaVersion >= 2 && provenance.research_candidate !== null) {
    throw new ContractError();
  }
  let historyTrainingRows: number | null = null;
  if (results.some((r) => r.model === "history_boost")) {
    const h = object(provenance.history_candidate);
    if (
      schemaVersion !== 3 ||
      h.model !== "history_boost" ||
      h.experiment_id !== "EXP-010" ||
      h.manifest_sha256 !== historyManifest ||
      h.fresh_validation !== false ||
      h.matched_evaluation !== "FOUR_NEW_WORLD_HELDOUT_ONLINE_MATURE_HISTORY" ||
      results.some((r) => r.matchedMetrics === null)
    )
      throw new ContractError();
    historyTrainingRows = finite(h.training_rows);
    if (historyTrainingRows !== 5700) throw new ContractError();
  } else if (schemaVersion === 3 && provenance.history_candidate !== null) {
    throw new ContractError();
  }

  const history = schemaVersion === 3 ? readHistory(raw.history) : null;
  const candidate = results.find((r) => r.model === "history_boost");
  if (
    candidate &&
    candidate.prediction !== null &&
    (!history ||
      history.uncensored_history_count < 2 ||
      history.history_age_hours === null ||
      history.history_age_hours > 72)
  )
    throw new ContractError();

  const execution = object(raw.execution);
  return {
    schemaVersion,
    researchManifest,
    historyTrainingRows,
    history,
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
