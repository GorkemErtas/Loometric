import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { PredictionResults, ScenarioResults } from "../components/PredictionResults";
import { Badge, Empty, ErrorNotice, Panel } from "../components/ui";
import {
  emptyHistory,
  fields,
  historyIssues,
  initialInputs,
  inputIssues,
  legacyModelNames,
  type MatureHistory,
  type ModelName,
  modelLabels,
  modelNames,
  type PredictionInputs,
  type PredictionReport,
} from "../domain/predictions";
import { useI18n } from "../i18n/I18n";
import { useWorkspace } from "../state/Workspace";

export function Predictions() {
  const { t, validationMessage, label: textLabel, stageName, formValidation } = useI18n();

  const { api, sessionId, rejectSession } = useWorkspace();
  const [inputs, setInputs] = useState<PredictionInputs>({ ...initialInputs });
  const [selection, setSelection] = useState<ModelName | "all" | "legacy">("rf_physics");
  const [history, setHistory] = useState<MatureHistory>({ ...emptyHistory });
  const [declared, setDeclared] = useState(false);
  const [report, setReport] = useState<PredictionReport | null>(null);
  const [before, setBefore] = useState<PredictionReport | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);
  const revision = useRef(0),
    pending = useRef<AbortController | null>(null);
  const owner = useRef({ api, sessionId });
  useEffect(() => {
    if (owner.current.api !== api || owner.current.sessionId !== sessionId) {
      owner.current = { api, sessionId };
      setReport(null);
      setBefore(null);
      setError(null);
      setLoading(false);
      setRequestId(null);
    }
    return () => {
      revision.current++;
      pending.current?.abort();
    };
  }, [api, sessionId]);
  function invalidate() {
    revision.current++;
    pending.current?.abort();
    pending.current = null;
    setLoading(false);
    setReport(null);
    setRequestId(null);
    setError(null);
  }
  function change<K extends keyof PredictionInputs>(key: K, value: PredictionInputs[K]) {
    invalidate();
    setInputs((current) => ({ ...current, [key]: value }));
  }
  const usesHistory = selection === "all" || selection === "history_boost";
  const issues = [...inputIssues(inputs), ...(usesHistory ? historyIssues(history) : [])];
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!api || !declared || issues.length || loading) return;
    invalidate();
    const current = ++revision.current,
      controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    try {
      const response = await api.predictSynthetic(
        { ...inputs },
        selection === "all"
          ? [...modelNames]
          : selection === "legacy"
            ? [...legacyModelNames]
            : [selection],
        controller.signal,
        history,
      );
      if (current !== revision.current || controller.signal.aborted) return;
      setReport(response.data);
      setRequestId(response.requestId);
    } catch (caught) {
      if (current !== revision.current || controller.signal.aborted) return;
      const failure = caught instanceof ApiError ? caught : new ApiError("contract");
      setError(failure);
      if (failure.kind === "authentication") rejectSession(failure);
    } finally {
      if (current === revision.current) {
        setLoading(false);
        pending.current = null;
      }
    }
  }
  return (
    <div className="predictions-page">
      <div className="prediction-intro">
        <div>
          <Badge tone="amber">{t("EXPERIMENTAL · SYNTHETIC ONLY")}</Badge>
          <h2>{t("Explore planned production conditions")}</h2>
          <p>
            {t(
              "Execute actual fitted models against hypothetical pre-shift inputs. Forecast standard capacity attainment, not guaranteed production output or intrinsic employee efficiency.",
            )}
          </p>
        </div>
        <div className="prediction-policy">
          <strong>{t("NO ML PROMOTION")}</strong>
          <span>{t("Research and demonstration")}</span>
          <span>{t("Human review required")}</span>
        </div>
      </div>
      <div className="prediction-caution">
        <strong>{t("Known subgroup failures remain visible.")}</strong>{" "}
        {t(
          "Forest12 packing MAE regressed 51.84% in development seed 19 (36 rows). Hist31 failed stage and worst-error gates. Lower aggregate MAE does not establish superiority in every stage.",
        )}
      </div>
      <div className="prediction-caution">
        <strong>{t("RF Physics · EXP-008.")}</strong>{" "}
        {t(
          "Retained benchmark MAE improved by 24.05% compared with Forest12. Stage-specific and worst-error regressions remain unresolved. EXP-009 prospective validation failed the complete replication criteria.",
        )}
      </div>
      <div className="prediction-caution">
        <strong>{t("History Boost · EXP-010.")}</strong>{" "}
        {t(
          "One fixed residual fit passed fresh held-out demonstration guards using mature past-shift context. Missing or stale history abstains. Baseline worst error still increased 9.11%; first unannounced shocks remain uncertain.",
        )}
      </div>
      {!api && (
        <div className="notice" role="status">
          <p>
            {t(
              "Connect with Configure API to run actual models. Example inputs below are editable; no prediction is generated in preview mode.",
            )}
          </p>
        </div>
      )}
      <Panel
        title={t("Hypothetical pre-shift inputs")}
        description={t(
          "One order-stage on one dedicated crew and line. All values must be planned and available before shift start.",
        )}
      >
        <form {...formValidation} onSubmit={submit} className="prediction-form">
          <div className="prediction-form-toolbar">
            <label>
              {t("Model")}
              <select
                aria-label={t("Model")}
                value={selection}
                onChange={(event) => {
                  invalidate();
                  setSelection(event.target.value as ModelName | "all" | "legacy");
                }}
              >
                {modelNames.map((name) => (
                  <option key={name} value={name}>
                    {modelLabels[name]} ·{" "}
                    {name === "history_boost"
                      ? t("MATURE HISTORY REQUIRED")
                      : name === "rf_physics"
                        ? t("RESEARCH CANDIDATE")
                        : name === "grouped_mean"
                          ? t("comparison baseline")
                          : t("EXPERIMENTAL")}
                  </option>
                ))}
                <option value="legacy">{t("Compare all four original models")}</option>
                <option value="all">{t("Compare all five models")}</option>
              </select>
            </label>
            <p>
              {t(
                "Default: RF Physics, an experimental research candidate with lower retained benchmark MAE. No operational promotion or factory validation is implied.",
              )}
            </p>
          </div>
          <fieldset>
            <legend>{t("Production context")}</legend>
            <div className="prediction-fields">
              <label>
                {t("Production stage")}
                <select
                  value={inputs.stage}
                  onChange={(event) => change("stage", event.target.value)}
                >
                  {["cutting", "sewing", "finishing", "quality_control", "packing"].map((stage) => (
                    <option key={stage} value={stage}>
                      {stageName(stage)}
                    </option>
                  ))}
                </select>
                <span>{t("Single process stage for this observation.")}</span>
              </label>
              <label>
                {t("Shift")}
                <select
                  value={inputs.shift_kind}
                  onChange={(event) => change("shift_kind", event.target.value)}
                >
                  <option value="day">{t("Day")}</option>
                  <option value="night">{t("Night")}</option>
                </select>
                <span>{t("Frozen planned shift type.")}</span>
              </label>
              <label>
                {t("Shift start weekday")}
                <select
                  value={inputs.weekday}
                  onChange={(event) => change("weekday", Number(event.target.value))}
                >
                  {[
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday — outside v1 support",
                  ].map((day, index) => (
                    <option key={textLabel(day)} value={index}>
                      {textLabel(day)}
                    </option>
                  ))}
                </select>
                <span>{t("Local weekday of shift start, including for night shifts.")}</span>
              </label>
            </div>
          </fieldset>
          {usesHistory && (
            <fieldset>
              <legend>{t("Mature historical context · optional fifth model")}</legend>
              <p>
                {t(
                  "Use only the last seven same-crew and same-line reports available before the 30-minute pre-shift cutoff. Mean/std exclude past shifts whose output was limited by offered work. Leave missing history empty; History Boost will abstain. These editable values are hypothetical, not imported factory measurements.",
                )}
              </p>
              <div className="prediction-fields">
                {(
                  [
                    ["history_count", "Mature history count", 0, 7, 1],
                    ["uncensored_history_count", "Uncensored history count", 0, 7, 1],
                    ["recent_attainment_mean", "Recent uncensored attainment mean", 0, 3, 0.001],
                    [
                      "recent_attainment_std",
                      "Recent uncensored attainment standard deviation",
                      0,
                      3,
                      0.001,
                    ],
                    ["history_age_hours", "Latest mature report age (hours)", 0, 8760, 0.5],
                  ] as const
                ).map(([key, label, min, max, step]) => (
                  <label key={key}>
                    {textLabel(String(label))}
                    <input
                      type="number"
                      value={history[key] ?? ""}
                      min={min}
                      max={max}
                      step={step}
                      onChange={(event) => {
                        invalidate();
                        setBefore(null);
                        const value = event.target.value;
                        setHistory((current) => ({
                          ...current,
                          [key]: value === "" ? (key.endsWith("count") ? 0 : null) : Number(value),
                        }));
                      }}
                    />
                  </label>
                ))}
              </div>
              <p>
                {t(
                  "At least two uncensored reports and age ≤ 72 hours are required for a candidate point estimate.",
                )}
              </p>
            </fieldset>
          )}
          <fieldset>
            <legend>{t("Planned crew, time and demand")}</legend>
            <div className="prediction-fields">
              {fields.map(([key, label, help, min, max, step]) => (
                <div key={key} className="prediction-field">
                  <label htmlFor={`prediction-${key}`}>{textLabel(String(label))}</label>
                  <input
                    id={`prediction-${key}`}
                    type="number"
                    required
                    min={min}
                    max={max}
                    step={step}
                    value={Number.isNaN(inputs[key]) ? "" : inputs[key]}
                    onChange={(event) =>
                      change(
                        key,
                        event.target.value === "" ? Number.NaN : Number(event.target.value),
                      )
                    }
                    aria-describedby={`help-${key}`}
                  />
                  <span id={`help-${key}`}>{textLabel(help)}</span>
                </div>
              ))}
            </div>
          </fieldset>
          <label className="prediction-checkbox">
            <input
              type="checkbox"
              checked={inputs.planned_machine_available}
              onChange={(event) => change("planned_machine_available", event.target.checked)}
            />
            {t("Planned machine available")}
            <span>{t("Unavailable machine or zero labor/time produces abstention.")}</span>
          </label>
          <label className="prediction-checkbox">
            <input
              type="checkbox"
              checked={declared}
              onChange={(event) => {
                invalidate();
                setDeclared(event.target.checked);
              }}
            />
            {t("I am testing hypothetical synthetic pre-shift conditions.")}
            <span>
              {t("No measured factory accuracy or operational authorization is implied.")}
            </span>
          </label>
          {issues.length > 0 && (
            <div className="prediction-issues" role="alert">
              <strong>{t("Check input consistency")}</strong>
              <ul>
                {issues.map((issue) => (
                  <li key={validationMessage(issue)}>{validationMessage(issue)}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="prediction-actions">
            <button
              className="button button-primary"
              type="submit"
              disabled={!api || !declared || issues.length > 0 || loading}
            >
              {loading ? t("Running actual estimators…") : t("Predict")}
            </button>
            {loading && (
              <button className="button" type="button" onClick={invalidate}>
                {t("Cancel request")}
              </button>
            )}
            {report && (
              <button className="button" type="button" onClick={() => setBefore(report)}>
                {t("Use as scenario baseline")}
              </button>
            )}
            {before && (
              <button className="button" type="button" onClick={() => setBefore(null)}>
                {t("Clear scenario baseline")}
              </button>
            )}
            <span role="status">
              {loading
                ? t("Loading trusted models and computing predictions.")
                : requestId
                  ? t("API response · {p0}", { p0: requestId })
                  : t("No current prediction response.")}
            </span>
          </div>
        </form>
      </Panel>
      {error && (
        <>
          <ErrorNotice error={error} />
          {error.code === "EXPERIMENTAL_ARTIFACT_UNAVAILABLE" && (
            <p>
              {t(
                "Publish the trusted local experimental artifacts using the documented offline setup, then retry.",
              )}
            </p>
          )}
        </>
      )}
      {before && <ScenarioResults before={before} after={report} />}
      {report ? (
        <PredictionResults report={report} />
      ) : (
        !loading &&
        !error && (
          <Empty title={t("Your next prediction starts with a real request")}>
            {t(
              "Review the inputs and synthetic declaration, then predict. Editing inputs clears the current result; a pinned scenario baseline stays visible until the session changes.",
            )}
          </Empty>
        )
      )}
    </div>
  );
}
