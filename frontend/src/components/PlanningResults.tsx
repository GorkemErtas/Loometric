import { encodeExact } from "../domain/json";
import type { Comparison, Evaluation, Metrics } from "../domain/planning";
import { metricDefinitions, objectives } from "../domain/planning";
import { executionBlock } from "../domain/scenario";
import { useI18n } from "../i18n/I18n";
import { usePlanning } from "../state/PlanningWorkspace";
import { useWorkspace } from "../state/Workspace";
import { Badge, Empty, ErrorNotice, JsonBlock, Notice, Panel, Stat, TableScroll } from "./ui";

export function PlanningGate() {
  const { t, validationMessage } = useI18n();

  const { api, dataset, capabilities, error, status } = useWorkspace();
  const blocked = executionBlock(dataset, capabilities);
  return (
    <>
      {!api && (
        <Notice>
          {t(
            "Connect the local API to execute planning workflows. Fixture preview never starts a scheduler or job.",
          )}
        </Notice>
      )}
      {status === "loading" && (
        <p role="status" className="panel-body">
          {t("Loading the local session / selected capacity…")}
        </p>
      )}
      {error && <ErrorNotice error={error} />}{" "}
      {blocked && <Notice>{validationMessage(blocked)}</Notice>}
    </>
  );
}
export function ActionStatus() {
  const { validationMessage } = useI18n();

  const { busy, error } = usePlanning();
  return (
    <>
      {busy && (
        <div className="loading-state" role="status">
          <span className="spinner" />
          {validationMessage(busy)}…
        </div>
      )}
      {error && <ErrorNotice error={error} />}
    </>
  );
}
export function PlanSummary({ metrics }: { metrics: Metrics | null }) {
  const { t, metricText } = useI18n();

  if (!metrics)
    return (
      <Empty title={t("No accepted metrics")}>
        {t("Invalid or missing results do not receive invented performance metrics.")}
      </Empty>
    );
  return (
    <div className="stat-grid">
      <Stat
        label={t("Finished units")}
        value={metricText(metrics.scheduled_units, "piece")}
        unit="pieces"
        detail={t("All required stages completed")}
      />
      <Stat
        label={t("Unfinished units")}
        value={metricText(metrics.unscheduled_units, "piece")}
        unit="pieces"
        detail={t("Includes all incomplete order demand")}
      />
      <Stat
        label={t("Line utilization")}
        value={metricText(metrics.line_utilization, "ratio")}
        detail={t("{p0} / {p1} net line-minutes", {
          p0: metricText(metrics.occupied_line_minutes, "line_minute"),
          p1: metricText(metrics.available_line_minutes, "line_minute"),
        })}
      />
      <Stat
        label={t("Standard capacity use")}
        value={metricText(metrics.standard_capacity_utilization, "ratio")}
        detail={t("{p0} / {p1} standard worker-minutes", {
          p0: metricText(metrics.consumed_standard_minutes, "standard_worker_minute"),
          p1: metricText(metrics.available_standard_minutes, "standard_worker_minute"),
        })}
      />
    </div>
  );
}
export function EvaluationEvidence({
  evaluation: e,
  title = "Producer & solver evidence",
}: {
  evaluation: Evaluation;
  title?: string;
}) {
  const { t, label: textLabel, codeLabel, formatSignedExact } = useI18n();

  return (
    <Panel title={textLabel(title)} description={t("Selection and proof are different claims")}>
      <div className="producer-summary">
        <Badge tone={e.producer === "cp_sat" ? "teal" : "neutral"}>
          {t("Selected: {p0}", { p0: codeLabel(e.producer) })}
        </Badge>
        <Badge tone={e.selected.complete ? "teal" : "amber"}>{codeLabel(e.selected.status)}</Badge>
        <span>{e.algorithm}</span>
        <p>
          {t("Selected-plan proof: {p0} / 3 objectives · {p1}", {
            p0: e.proven,
            p1: e.full ? t("full lexicographic proof") : t("no full lexicographic claim"),
          })}
        </p>
        <p>
          {t("Fallback / retention reason:")}{" "}
          <code>
            {e.fallback
              ? codeLabel(e.fallback)
              : t("Not required — verified candidate was strictly better")}
          </code>
        </p>
      </div>
      <details className="details-block">
        <summary>
          {t("Advanced optimizer evidence ({p0})", {
            p0: codeLabel(e.optimizer.solverStatus ?? e.optimizer.status),
          })}
        </summary>
        <dl className="detail-grid">
          <div>
            <dt>{t("Attempt / native status")}</dt>
            <dd>
              {codeLabel(e.optimizer.status)} /{" "}
              {e.optimizer.solverStatus
                ? codeLabel(e.optimizer.solverStatus)
                : t("Not run / unavailable")}
            </dd>
          </div>
          <div>
            <dt>{t("Solver version")}</dt>
            <dd>{e.optimizer.version ?? t("Not reported")}</dd>
          </div>
          <div>
            <dt>{t("Candidate proof")}</dt>
            <dd>
              {t("{p0} / 3 · full: {p1}", {
                p0: e.optimizer.proven,
                p1: codeLabel(String(e.optimizer.full)),
              })}
            </dd>
          </div>
          <div>
            <dt>{t("Incumbent source")}</dt>
            <dd>
              {e.optimizer.incumbentPhase === null
                ? t("No incumbent")
                : t("Phase {p0}{p1}", {
                    p0: e.optimizer.incumbentPhase,
                    p1: e.optimizer.retained ? t(" — retained earlier incumbent") : "",
                  })}
            </dd>
          </div>
        </dl>
        {!e.optimizer.candidate && (
          <Notice>
            {t(
              "No accepted optimizer incumbent or candidate metrics are available. A resource stop or UNKNOWN is not proof of infeasibility.",
            )}
          </Notice>
        )}
        <TableScroll label={t("CP-SAT proof phases")}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("Phase")}</th>
                <th scope="col">{t("Objective")}</th>
                <th scope="col">{t("Native status")}</th>
                <th scope="col">{t("Value / bound")}</th>
                <th scope="col">{t("Proven")}</th>
              </tr>
            </thead>
            <tbody>
              {e.optimizer.phases.map((p) => (
                <tr key={p.phase}>
                  <th scope="row">{p.phase}</th>
                  <td>{codeLabel(p.objective)}</td>
                  <td>{codeLabel(p.status)}</td>
                  <td>
                    {p.value === null ? t("No incumbent") : formatSignedExact(p.value)} /{" "}
                    {p.bound === null ? t("Not reported") : formatSignedExact(p.bound)}
                  </td>
                  <td>{codeLabel(String(p.proven))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        <p className="field-help">
          {t(
            "FEASIBLE remains unproven. Candidate proof is never transferred to a selected greedy schedule. Objective order: unfinished pieces → completed-order priority-weighted tardiness → makespan.",
          )}
        </p>
      </details>
    </Panel>
  );
}
export function AlgorithmComparison({ evaluation: e }: { evaluation: Evaluation }) {
  const { t, label: textLabel, codeLabel, formatSignedExact, metricText } = useI18n();

  const evidence = e.optimizer.comparison;
  return (
    <Panel
      title={t("Greedy vs selected result")}
      description={t("Same instance, frozen objective order; backend-provided metrics")}
    >
      <TableScroll label={t("Algorithm metric comparison")}>
        <table>
          <thead>
            <tr>
              <th scope="col">{t("Metric / unit")}</th>
              <th scope="col">{t("Verified greedy")}</th>
              <th scope="col">{t("Selected {p0}", { p0: codeLabel(e.producer) })}</th>
              <th scope="col">{t("Optimizer candidate")}</th>
            </tr>
          </thead>
          <tbody>
            {metricDefinitions.map(([key, label, unit]) => (
              <tr key={key}>
                <th scope="row">
                  {textLabel(String(label))}
                  <span className="cell-secondary">{codeLabel(unit)}</span>
                </th>
                <td>{metricText(e.greedy.metrics?.[key] ?? null, unit)}</td>
                <td>{metricText(e.selected.metrics?.[key] ?? null, unit)}</td>
                <td>{metricText(e.optimizer.candidate?.metrics?.[key] ?? null, unit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableScroll>
      {evidence ? (
        <div className="panel-body">
          <Badge
            tone={
              evidence.relation === "BETTER"
                ? "teal"
                : evidence.relation === "WORSE"
                  ? "amber"
                  : "neutral"
            }
          >
            {t("Candidate vs greedy: {p0}", { p0: codeLabel(evidence.relation) })}
          </Badge>
          <p className="field-help">
            {t("Deciding objective: {p0}", {
              p0: evidence.deciding ? codeLabel(evidence.deciding) : t("None — tie"),
            })}
          </p>
          <dl className="objective-grid">
            {objectives.map((key) => (
              <div key={key}>
                <dt>{codeLabel(key)}</dt>
                <dd>
                  {evidence.before[key]} → {evidence.after[key]} · Δ{" "}
                  {formatSignedExact(evidence.changes[key] ?? "0")}
                </dd>
              </div>
            ))}
          </dl>
          <p className="field-help">
            {t(
              "Backend comparison supplies objective differences only; unreported same-instance percentage differences are not invented.",
            )}
          </p>
        </div>
      ) : (
        <Notice>
          {t(
            "No accepted candidate comparison is available. The selected verified greedy result remains explicit.",
          )}
        </Notice>
      )}
    </Panel>
  );
}
export function ScenarioMetrics({ comparison: c }: { comparison: Comparison }) {
  const {
    t,
    backendText,
    label: textLabel,
    codeLabel,
    percentValueExact,
    formatSignedExact,
    metricText,
  } = useI18n();

  return (
    <Panel
      title={t("Baseline vs scenario")}
      description={t(
        "Backend-provided scenario-minus-baseline deltas; conditional synthetic planning",
      )}
    >
      <div className="comparison-headline">
        <Badge
          tone={
            c.selectedComparison.relation === "BETTER"
              ? "teal"
              : c.selectedComparison.relation === "WORSE"
                ? "amber"
                : "neutral"
          }
        >
          {codeLabel(c.selectedComparison.relation)}
        </Badge>
        <span>
          {t("Deciding objective: {p0}", {
            p0: c.selectedComparison.deciding
              ? codeLabel(c.selectedComparison.deciding)
              : t("None — tie"),
          })}
        </span>
        <span>
          {t("Greedy-only relation: {p0}", { p0: codeLabel(c.greedyComparison.relation) })}
        </span>
      </div>
      <TableScroll label={t("Scenario metric differences")}>
        <table>
          <thead>
            <tr>
              <th scope="col">{t("Metric / unit")}</th>
              <th scope="col">{t("Baseline · {p0}", { p0: codeLabel(c.baseline.producer) })}</th>
              <th scope="col">{t("Scenario · {p0}", { p0: codeLabel(c.scenario.producer) })}</th>
              <th scope="col">{t("Absolute Δ")}</th>
              <th scope="col">{t("Relative Δ")}</th>
            </tr>
          </thead>
          <tbody>
            {metricDefinitions.map(([key, label, unit]) => {
              const d = c.deltas[key];
              return (
                <tr key={key}>
                  <th scope="row">
                    {textLabel(String(label))}
                    <span className="cell-secondary">{codeLabel(unit)}</span>
                  </th>
                  <td>{metricText(d.before, unit)}</td>
                  <td>{metricText(d.after, unit)}</td>
                  <td>
                    {d.absolute === null ? t("Not applicable") : formatSignedExact(d.absolute)}
                    {unit === "ratio" && d.points !== null && (
                      <span className="cell-secondary">
                        {t("{p0} percentage points", { p0: formatSignedExact(d.points) })}
                      </span>
                    )}
                  </td>
                  <td>
                    {d.percentage === null ? (
                      <span className="cell-secondary">
                        {t("Not applicable · {p0}", { p0: d.status })}
                      </span>
                    ) : (
                      percentValueExact(d.percentage)
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableScroll>
      <Notice>
        {t(
          "Tardiness covers completed orders only. Compare unfinished demand first. Utilization denominators can change; greater hypothetical capacity does not guarantee a better schedule or observed productivity.",
        )}
      </Notice>
      <details className="details-block">
        <summary>
          {t("Verified change audit & identities ({p0} changes)", { p0: c.audit.length })}
        </summary>
        <dl className="detail-grid">
          <div className="full-width">
            <dt>{t("Baseline fingerprint")}</dt>
            <dd>
              <code>{c.baselineFingerprint}</code>
            </dd>
          </div>
          <div className="full-width">
            <dt>{t("Derived scenario ID / fingerprint")}</dt>
            <dd>
              {c.scenarioId}
              <br />
              <code>{c.scenarioFingerprint}</code>
            </dd>
          </div>
          <div className="full-width">
            <dt>{t("Specification fingerprint")}</dt>
            <dd>
              <code>{c.fingerprint}</code>
            </dd>
          </div>
          <div className="full-width">
            <dt>{t("Verified same-demand fingerprint")}</dt>
            <dd>
              <code>{c.demandFingerprint}</code>
            </dd>
          </div>
        </dl>
        {c.audit.map((a) => (
          <div className="audit-record" key={a.index}>
            <strong>
              {a.index}. {codeLabel(a.operation)} · {a.target} ·{" "}
              {a.changed ? t("Changed") : t("explicit no-op")}
            </strong>
            <JsonBlock label={t("Change {p0} before and after", { p0: a.index })}>
              {encodeExact({ before: a.before, after: a.after })}
            </JsonBlock>
          </div>
        ))}
        <ul>
          {c.limitations.map((l) => (
            <li key={l}>{backendText(l)}</li>
          ))}
        </ul>
      </details>
    </Panel>
  );
}
