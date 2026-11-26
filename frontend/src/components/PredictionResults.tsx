import { modelLabels, type PredictionReport, type PredictionResult } from "../domain/predictions";
import { Badge, Panel, TableScroll } from "./ui";

export const ratio = (value: number | null) => (value === null ? "Abstained" : value.toFixed(5));
function ModelCard({ result }: { result: PredictionResult }) {
  return (
    <article className="prediction-card" aria-label={`${modelLabels[result.model]} result`}>
      <div className="prediction-card-heading">
        <h3>{modelLabels[result.model]}</h3>
        <Badge tone="amber">
          {result.model === "rf_physics"
            ? "RESEARCH CANDIDATE"
            : result.model === "grouped_mean"
              ? "BASELINE"
              : "EXPERIMENTAL"}
        </Badge>
      </div>
      <div className="prediction-value">{ratio(result.prediction)}</div>
      <p>Standard capacity attainment · dimensionless ratio</p>
      <strong
        className={
          result.support === "SUPPORTED_EXPERIMENTAL" ? "prediction-supported" : "prediction-review"
        }
      >
        {result.support.replaceAll("_", " ")}
      </strong>
      <ul className="prediction-reasons">
        {result.reasons.map((reason) => (
          <li key={reason}>{reason.replaceAll("_", " ")}</li>
        ))}
      </ul>
      {result.band && (
        <div className="prediction-band">
          <strong>Descriptive error band</strong>
          <p>
            {ratio(result.band.lower)} to {ratio(result.band.upper)}
          </p>
          <p>
            Training out-of-fold P90 residual radius. Uncalibrated; no coverage guarantee. Retained
            benchmark coverage: {(result.band.coverage * 100).toFixed(2)}%.
          </p>
        </div>
      )}
      {result.model === "rf_physics" && (
        <div className="prediction-weakness">
          <strong>Research evidence · EXP-008</strong>
          <p>24.05% lower retained benchmark MAE compared with Forest12.</p>
          <p>
            Spent validation only. Stage and worst-error gates remain unresolved. No independently
            calibrated prediction band is available.
          </p>
        </div>
      )}
      {result.model === "history_boost" && (
        <div className="prediction-weakness">
          <strong>Mature context · EXP-010</strong>
          <p>
            One frozen residual candidate using earlier same-crew/line reports. Missing or stale
            context abstains.
          </p>
          <p>
            Held-out gains include additional information and new development data. No calibrated
            band or factory validity.
          </p>
        </div>
      )}

      <dl className="prediction-metrics">
        <div>
          <dt>{result.matchedMetrics ? "Matched baseline MAE" : "Validation MAE"}</dt>
          <dd>{result.metrics.mae.toFixed(5)}</dd>
        </div>
        <div>
          <dt>RMSE</dt>
          <dd>{result.metrics.rmse.toFixed(5)}</dd>
        </div>
        <div>
          <dt>R²</dt>
          <dd>{result.metrics.r2.toFixed(5)}</dd>
        </div>
      </dl>
      <p>
        {result.metrics.samples.toLocaleString()}{" "}
        {result.matchedMetrics
          ? "matched baseline held-out rows; equal-world macro metrics"
          : "benchmark validation rows"}
        ; synthetic only.
      </p>
      {result.stageMetrics && (
        <p>
          Selected stage: MAE {result.stageMetrics.mae.toFixed(5)}, n=
          {result.stageMetrics.samples.toLocaleString()}.
        </p>
      )}
      {result.failures.length > 0 && (
        <div className="prediction-weakness">
          <strong>Failed promotion gates</strong>
          <p>{result.failures.join(", ").replaceAll("_", " ")}</p>
          <p>
            Maximum stage regression: +{result.maximumStageRegression?.toFixed(2)}%. Worst-error
            change: {result.worstErrorRegression?.toFixed(2)}%.
          </p>
        </div>
      )}
      <p className="prediction-identity">
        {result.identity} · {result.version}
        <br />
        {result.status}
      </p>
    </article>
  );
}
export function PredictionResults({ report }: { report: PredictionReport }) {
  const forest = report.results.find((r) => r.model === "random_forest");
  return (
    <div className="prediction-results" aria-live="polite">
      {report.historyTrainingRows !== null && (
        <Panel
          title="Matched fresh-world evidence · EXP-010"
          description="All five models scored the same held-out observations. Metrics are equal-world macro averages; max error is the actual condition-wide maximum."
        >
          <p>
            Four new simulated worlds, {report.historyTrainingRows.toLocaleString()} residual
            training rows, one fit and no parameter search. History Boost uses additional mature
            reports; this comparison does not isolate algorithm quality. Published holdout outcomes
            are now inspected.
          </p>
          <TableScroll label="Matched held-out model metrics">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Condition</th>
                  <th>MAE</th>
                  <th>RMSE</th>
                  <th>Macro R²</th>
                  <th>Bias</th>
                  <th>P95 abs</th>
                  <th>Max abs</th>
                </tr>
              </thead>
              <tbody>
                {report.results.flatMap((result) =>
                  result.matchedMetrics
                    ? (["baseline", "disruption"] as const).map((condition) => {
                        const m = result.matchedMetrics?.[condition];
                        if (!m) return null;
                        return (
                          <tr key={`${result.model}-${condition}`}>
                            <td>{modelLabels[result.model]}</td>
                            <td>{condition}</td>
                            <td>{m.mae.toFixed(5)}</td>
                            <td>{m.rmse.toFixed(5)}</td>
                            <td>{m.r2.toFixed(5)}</td>
                            <td>{m.bias.toFixed(5)}</td>
                            <td>{m.p95.toFixed(5)}</td>
                            <td>{m.worst.toFixed(5)}</td>
                          </tr>
                        );
                      })
                    : [],
                )}
              </tbody>
            </table>
          </TableScroll>
          <p>
            Known limits: the candidate's actual worst baseline error increased 9.11% versus RF
            Physics. Missing-history control was worse under disruption; first unannounced shocks
            remain uncertain. NO_ML_PROMOTION applies to every model.
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
          title="Same-input model comparison"
          description="Signed differences in attainment ratio; no model is operationally promoted."
        >
          <TableScroll label="Model prediction differences">
            <table>
              <thead>
                <tr>
                  <th>Left model</th>
                  <th>Right model</th>
                  <th>Left minus right</th>
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
          title="Global Random Forest behavior"
          description="Computed training impurity importance, aggregated over one-hot categories."
        >
          <div className="prediction-explanation">
            <p>
              This describes the fitted forest globally. It does not explain this individual
              prediction. Correlated inputs and feature cardinality can distort importance. No
              causal or SHAP explanation is claimed.
            </p>
            <ol className="importance-list">
              {forest.importance.slice(0, 6).map((row) => (
                <li key={row.feature}>
                  <span>{row.feature.replaceAll("_", " ")}</span>
                  <strong>{(row.importance * 100).toFixed(2)}%</strong>
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
        title="Model provenance and research limits"
        description="Published synthetic research evidence; NO_ML_PROMOTION remains in force."
      >
        <div className="prediction-provenance">
          <p>
            {report.dataset} · {report.experiment} · {report.trainingRows.toLocaleString()} original
            training rows ({report.trainingFirst} to {report.trainingLast}).
          </p>
          <p>
            Manifest SHA-256 <code>{report.manifest}</code>
          </p>
          {report.researchManifest && (
            <p>
              EXP-008 research candidate manifest SHA-256 <code>{report.researchManifest}</code>
            </p>
          )}
          <p>
            Training payload <code>{report.trainingFingerprint}</code>
          </p>
          <p>
            Input receipt <code>{report.inputFingerprint}</code>
          </p>
          <p>
            Whole isolated request: {report.seconds.toFixed(3)} seconds, including startup,
            integrity checks and model loading.
          </p>
          <ul>
            {report.limitations.map((value) => (
              <li key={value}>{value}</li>
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
  const changed = after
    ? (Object.keys(before.inputs) as (keyof PredictionReport["inputs"])[]).filter(
        (key) => before.inputs[key] !== after.inputs[key],
      )
    : [];
  return (
    <Panel
      title="Hypothetical scenario comparison"
      description="A pinned API response and a new request. Differences are not proven causal effects."
    >
      <div className="prediction-scenario-summary">
        <p>
          Before: saved in this tab from a real API response. Modify one or more inputs, then
          predict again.
        </p>
        {after && changed.length === 0 && <p>No input differences between these requests.</p>}
      </div>
      {after ? (
        <>
          <TableScroll label="Scenario input differences">
            <table>
              <thead>
                <tr>
                  <th>Input</th>
                  <th>Before</th>
                  <th>After</th>
                </tr>
              </thead>
              <tbody>
                {changed.map((key) => (
                  <tr key={key}>
                    <td>{key.replaceAll("_", " ")}</td>
                    <td>{String(before.inputs[key])}</td>
                    <td>{String(after.inputs[key])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableScroll>
          <TableScroll label="Before and after model predictions">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Before</th>
                  <th>After</th>
                  <th>After minus before</th>
                  <th>After support</th>
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
                      <td>{b.support.replaceAll("_", " ")}</td>
                    </tr>
                  ) : null;
                })}
              </tbody>
            </table>
          </TableScroll>
          <p className="prediction-scenario-summary">
            Only models present in both requests are compared. No schedule or capacity profile is
            changed.
          </p>
        </>
      ) : (
        <p className="prediction-scenario-summary">
          Waiting for the next real prediction. No after value is assumed.
        </p>
      )}
    </Panel>
  );
}
