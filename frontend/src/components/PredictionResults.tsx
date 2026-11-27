import { modelLabels, type PredictionReport, type PredictionResult } from "../domain/predictions";
import { useI18n } from "../i18n/I18n";
import { Badge, Panel, TableScroll } from "./ui";

function ModelCard({ result }: { result: PredictionResult }) {
  const { t, codeLabel, number, percent, ratio } = useI18n();

  return (
    <article
      className="prediction-card"
      aria-label={t("{p0} result", { p0: modelLabels[result.model] })}
    >
      <div className="prediction-card-heading">
        <h3>{modelLabels[result.model]}</h3>
        <Badge tone="amber">
          {result.model === "rf_physics"
            ? t("RESEARCH CANDIDATE")
            : result.model === "grouped_mean"
              ? t("BASELINE")
              : t("EXPERIMENTAL")}
        </Badge>
      </div>
      <div className="prediction-value">{ratio(result.prediction)}</div>
      <p>{t("Standard capacity attainment · dimensionless ratio")}</p>
      <strong
        className={
          result.support === "SUPPORTED_EXPERIMENTAL" ? "prediction-supported" : "prediction-review"
        }
      >
        {codeLabel(result.support)}
      </strong>
      <ul className="prediction-reasons">
        {result.reasons.map((reason) => (
          <li key={reason}>{codeLabel(reason)}</li>
        ))}
      </ul>
      {result.band && (
        <div className="prediction-band">
          <strong>{t("Descriptive error band")}</strong>
          <p>{t("{p0} to {p1}", { p0: ratio(result.band.lower), p1: ratio(result.band.upper) })}</p>
          <p>
            {t(
              "Training out-of-fold P90 residual radius. Uncalibrated; no coverage guarantee. Retained benchmark coverage: {p0}.",
              { p0: percent(result.band.coverage, 2) },
            )}
          </p>
        </div>
      )}
      {result.model === "rf_physics" && (
        <div className="prediction-weakness">
          <strong>{t("Research evidence · EXP-008")}</strong>
          <p>{t("24.05% lower retained benchmark MAE compared with Forest12.")}</p>
          <p>
            {t(
              "Spent validation only. Stage and worst-error gates remain unresolved. No independently calibrated prediction band is available.",
            )}
          </p>
        </div>
      )}
      {result.model === "history_boost" && (
        <div className="prediction-weakness">
          <strong>{t("Mature context · EXP-010")}</strong>
          <p>
            {t(
              "One frozen residual candidate using earlier same-crew/line reports. Missing or stale context abstains.",
            )}
          </p>
          <p>
            {t(
              "Held-out gains include additional information and new development data. No calibrated band or factory validity.",
            )}
          </p>
        </div>
      )}

      <dl className="prediction-metrics">
        <div>
          <dt>{result.matchedMetrics ? t("Matched baseline MAE") : t("Validation MAE")}</dt>
          <dd>{number(result.metrics.mae, 5)}</dd>
        </div>
        <div>
          <dt>RMSE</dt>
          <dd>{number(result.metrics.rmse, 5)}</dd>
        </div>
        <div>
          <dt>R²</dt>
          <dd>{number(result.metrics.r2, 5)}</dd>
        </div>
      </dl>
      <p>
        {t("{p0} {p1}; synthetic only.", {
          p0: number(result.metrics.samples),
          p1: result.matchedMetrics
            ? t("matched baseline held-out rows; equal-world macro metrics")
            : t("benchmark validation rows"),
        })}
      </p>
      {result.stageMetrics && (
        <p>
          {t("Selected stage: MAE {p0}, n={p1}.", {
            p0: number(result.stageMetrics.mae, 5),
            p1: number(result.stageMetrics.samples),
          })}
        </p>
      )}
      {result.failures.length > 0 && (
        <div className="prediction-weakness">
          <strong>{t("Failed promotion gates")}</strong>
          <p>{result.failures.map(codeLabel).join(", ")}</p>
          <p>
            {t("Maximum stage regression: +{p0}. Worst-error change: {p1}.", {
              p0:
                result.maximumStageRegression == null
                  ? t("Not reported")
                  : percent(result.maximumStageRegression / 100, 2),
              p1:
                result.worstErrorRegression == null
                  ? t("Not reported")
                  : percent(result.worstErrorRegression / 100, 2),
            })}
          </p>
        </div>
      )}
      <p className="prediction-identity">
        {result.identity} · {result.version}
        <br />
        {codeLabel(result.status)}
      </p>
    </article>
  );
}
export function PredictionResults({ report }: { report: PredictionReport }) {
  const { t, backendText, codeLabel, dateLabel, number, percent, ratio } = useI18n();

  const forest = report.results.find((r) => r.model === "random_forest");
  return (
    <div className="prediction-results" aria-live="polite">
      {report.historyTrainingRows !== null && (
        <Panel
          title={t("Matched fresh-world evidence · EXP-010")}
          description={t(
            "All five models scored the same held-out observations. Metrics are equal-world macro averages; max error is the actual condition-wide maximum.",
          )}
        >
          <p>
            {t(
              "Four new simulated worlds, {p0} residual training rows, one fit and no parameter search. History Boost uses additional mature reports; this comparison does not isolate algorithm quality. Published holdout outcomes are now inspected.",
              { p0: number(report.historyTrainingRows) },
            )}
          </p>
          <TableScroll label={t("Matched held-out model metrics")}>
            <table>
              <thead>
                <tr>
                  <th>{t("Model")}</th>
                  <th>{t("Condition")}</th>
                  <th>MAE</th>
                  <th>RMSE</th>
                  <th>{t("Macro R²")}</th>
                  <th>{t("Bias")}</th>
                  <th>{t("P95 abs")}</th>
                  <th>{t("Max abs")}</th>
                </tr>
              </thead>
              <tbody>
                {report.results.flatMap((result) =>
                  result.matchedMetrics
                    ? (["baseline", "disruption"] as const).map((condition) => {
                        const m = result.matchedMetrics?.[condition];
                        if (!m) return null;
                        return (
                          <tr key={`${result.model}-${codeLabel(condition)}`}>
                            <td>{modelLabels[result.model]}</td>
                            <td>{codeLabel(condition)}</td>
                            <td>{number(m.mae, 5)}</td>
                            <td>{number(m.rmse, 5)}</td>
                            <td>{number(m.r2, 5)}</td>
                            <td>{number(m.bias, 5)}</td>
                            <td>{number(m.p95, 5)}</td>
                            <td>{number(m.worst, 5)}</td>
                          </tr>
                        );
                      })
                    : [],
                )}
              </tbody>
            </table>
          </TableScroll>
          <p>
            {t(
              "Known limits: the candidate's actual worst baseline error increased 9.11% versus RF Physics. Missing-history control was worse under disruption; first unannounced shocks remain uncertain. NO_ML_PROMOTION applies to every model.",
            )}
          </p>
        </Panel>
      )}
      <div className="prediction-result-grid">
        {report.results.map((result) => (
          <ModelCard key={result.model} result={result} />
        ))}
      </div>
      {report.differences.length > 0 && (
        <Panel
          title={t("Same-input model comparison")}
          description={t(
            "Signed differences in attainment ratio; no model is operationally promoted.",
          )}
        >
          <TableScroll label={t("Model prediction differences")}>
            <table>
              <thead>
                <tr>
                  <th>{t("Left model")}</th>
                  <th>{t("Right model")}</th>
                  <th>{t("Left minus right")}</th>
                </tr>
              </thead>
              <tbody>
                {report.differences.map((row) => (
                  <tr key={`${row.left}:${row.right}`}>
                    <td>{modelLabels[row.left]}</td>
                    <td>{modelLabels[row.right]}</td>
                    <td>{ratio(row.difference)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableScroll>
        </Panel>
      )}
      {forest && forest.importance.length > 0 && (
        <Panel
          title={t("Global Random Forest behavior")}
          description={t(
            "Computed training impurity importance, aggregated over one-hot categories.",
          )}
        >
          <div className="prediction-explanation">
            <p>
              {t(
                "This describes the fitted forest globally. It does not explain this individual prediction. Correlated inputs and feature cardinality can distort importance. No causal or SHAP explanation is claimed.",
              )}
            </p>
            <ol className="importance-list">
              {forest.importance.slice(0, 6).map((row) => (
                <li key={row.feature}>
                  <span>{codeLabel(row.feature)}</span>
                  <strong>{percent(row.importance, 2)}</strong>
                  <span className="importance-track" aria-hidden="true">
                    <i style={{ width: `${row.importance * 100}%` }} />
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </Panel>
      )}
      <Panel
        title={t("Model provenance and research limits")}
        description={t("Published synthetic research evidence; NO_ML_PROMOTION remains in force.")}
      >
        <div className="prediction-provenance">
          <p>
            {t("{p0} · {p1} · {p2} original training rows ({p3} to {p4}).", {
              p0: report.dataset,
              p1: report.experiment,
              p2: number(report.trainingRows),
              p3: dateLabel(report.trainingFirst),
              p4: dateLabel(report.trainingLast),
            })}
          </p>
          <p>
            {t("Manifest SHA-256")} <code>{report.manifest}</code>
          </p>
          {report.researchManifest && (
            <p>
              {t("EXP-008 research candidate manifest SHA-256")}{" "}
              <code>{report.researchManifest}</code>
            </p>
          )}
          <p>
            {t("Training payload")} <code>{report.trainingFingerprint}</code>
          </p>
          <p>
            {t("Input receipt")} <code>{report.inputFingerprint}</code>
          </p>
          <p>
            {t(
              "Whole isolated request: {p0} seconds, including startup, integrity checks and model loading.",
              { p0: number(report.seconds, 3) },
            )}
          </p>
          <ul>
            {report.limitations.map((value) => (
              <li key={value}>{backendText(value)}</li>
            ))}
          </ul>
        </div>
      </Panel>
    </div>
  );
}
export function ScenarioResults({
  before,
  after,
}: {
  before: PredictionReport;
  after: PredictionReport | null;
}) {
  const { t, codeLabel, number, ratio } = useI18n();

  const changed = after
    ? (Object.keys(before.inputs) as (keyof PredictionReport["inputs"])[]).filter(
        (key) => before.inputs[key] !== after.inputs[key],
      )
    : [];
  return (
    <Panel
      title={t("Hypothetical scenario comparison")}
      description={t(
        "A pinned API response and a new request. Differences are not proven causal effects.",
      )}
    >
      <div className="prediction-scenario-summary">
        <p>
          {t(
            "Before: saved in this tab from a real API response. Modify one or more inputs, then predict again.",
          )}
        </p>
        {after && changed.length === 0 && (
          <p>{t("No input differences between these requests.")}</p>
        )}
      </div>
      {after ? (
        <>
          <TableScroll label={t("Scenario input differences")}>
            <table>
              <thead>
                <tr>
                  <th>{t("Input")}</th>
                  <th>{t("Before")}</th>
                  <th>{t("After")}</th>
                </tr>
              </thead>
              <tbody>
                {changed.map((key) => (
                  <tr key={key}>
                    <td>{codeLabel(key)}</td>
                    <td>
                      {typeof before.inputs[key] === "number"
                        ? number(before.inputs[key])
                        : codeLabel(String(before.inputs[key]))}
                    </td>
                    <td>
                      {typeof after.inputs[key] === "number"
                        ? number(after.inputs[key])
                        : codeLabel(String(after.inputs[key]))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableScroll>
          <TableScroll label={t("Before and after model predictions")}>
            <table>
              <thead>
                <tr>
                  <th>{t("Model")}</th>
                  <th>{t("Before")}</th>
                  <th>{t("After")}</th>
                  <th>{t("After minus before")}</th>
                  <th>{t("After support")}</th>
                </tr>
              </thead>
              <tbody>
                {before.results.map((a) => {
                  const b = after.results.find((r) => r.model === a.model);
                  return b ? (
                    <tr key={a.model}>
                      <td>{modelLabels[a.model]}</td>
                      <td>{ratio(a.prediction)}</td>
                      <td>{ratio(b.prediction)}</td>
                      <td>
                        {ratio(
                          a.prediction === null || b.prediction === null
                            ? null
                            : b.prediction - a.prediction,
                        )}
                      </td>
                      <td>{codeLabel(b.support)}</td>
                    </tr>
                  ) : null;
                })}
              </tbody>
            </table>
          </TableScroll>
          <p className="prediction-scenario-summary">
            {t(
              "Only models present in both requests are compared. No schedule or capacity profile is changed.",
            )}
          </p>
        </>
      ) : (
        <p className="prediction-scenario-summary">
          {t("Waiting for the next real prediction. No after value is assumed.")}
        </p>
      )}
    </Panel>
  );
}
