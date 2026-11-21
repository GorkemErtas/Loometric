import { formatSignedExact, percentExact } from "../domain/exact";
import { encodeExact } from "../domain/json";
import type { Comparison, Evaluation, Metrics } from "../domain/planning";
import { metricDefinitions, objectives } from "../domain/planning";
import { executionBlock } from "../domain/scenario";
import { usePlanning } from "../state/PlanningWorkspace";
import { useWorkspace } from "../state/Workspace";
import { Badge, Empty, ErrorNotice, JsonBlock, Notice, Panel, Stat, TableScroll } from "./ui";

export const metricText = (value: string | null, unit: string) =>
  value === null
    ? "Not applicable"
    : unit === "ratio"
      ? percentExact(value)
      : formatSignedExact(value);
export function PlanningGate() {
  const { api, dataset, capabilities, error, status } = useWorkspace();
  const blocked = executionBlock(dataset, capabilities);
  return (
    <>
      {!api && (
        <Notice>
          Connect the local API to execute planning workflows. Fixture preview never starts a
          scheduler or job.
        </Notice>
      )}
      {status === "loading" && (
        <p role="status" className="panel-body">
          Loading the local session / selected capacity…
        </p>
      )}
      {error && <ErrorNotice error={error} />} {blocked && <Notice>{blocked}</Notice>}
    </>
  );
}
export function ActionStatus() {
  const { busy, error } = usePlanning();
  return (
    <>
      {busy && (
        <div className="loading-state" role="status">
          <span className="spinner" />
          {busy}…
        </div>
      )}
      {error && <ErrorNotice error={error} />}
    </>
  );
}
export function PlanSummary({ metrics }: { metrics: Metrics | null }) {
  if (!metrics)
    return (
      <Empty title="No accepted metrics">
        Invalid or missing results do not receive invented performance metrics.
      </Empty>
    );
  return (
    <div className="stat-grid">
      <Stat
        label="Finished units"
        value={metricText(metrics.scheduled_units, "piece")}
        unit="pieces"
        detail="All required stages completed"
      />
      <Stat
        label="Unfinished units"
        value={metricText(metrics.unscheduled_units, "piece")}
        unit="pieces"
        detail="Includes all incomplete order demand"
      />
      <Stat
        label="Line utilization"
        value={metricText(metrics.line_utilization, "ratio")}
        detail={`${metricText(metrics.occupied_line_minutes, "line_minute")} / ${metricText(metrics.available_line_minutes, "line_minute")} net line-minutes`}
      />
      <Stat
        label="Standard capacity use"
        value={metricText(metrics.standard_capacity_utilization, "ratio")}
        detail={`${metricText(metrics.consumed_standard_minutes, "standard_worker_minute")} / ${metricText(metrics.available_standard_minutes, "standard_worker_minute")} standard worker-minutes`}
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
  return (
    <Panel title={title} description="Selection and proof are different claims">
      <div className="producer-summary">
        <Badge tone={e.producer === "cp_sat" ? "teal" : "neutral"}>Selected: {e.producer}</Badge>
        <Badge tone={e.selected.complete ? "teal" : "amber"}>{e.selected.status}</Badge>
        <span>{e.algorithm}</span>
        <p>
          Selected-plan proof: {e.proven} / 3 objectives ·{" "}
          {e.full ? "full lexicographic proof" : "no full lexicographic claim"}
        </p>
        <p>
          Fallback / retention reason:{" "}
          <code>{e.fallback ?? "Not required — verified candidate was strictly better"}</code>
        </p>
      </div>
      <details className="details-block">
        <summary>
          Advanced optimizer evidence ({e.optimizer.solverStatus ?? e.optimizer.status})
        </summary>
        <dl className="detail-grid">
          <div>
            <dt>Attempt / native status</dt>
            <dd>
              {e.optimizer.status} / {e.optimizer.solverStatus ?? "Not run / unavailable"}
            </dd>
          </div>
          <div>
            <dt>Solver version</dt>
            <dd>{e.optimizer.version ?? "Not reported"}</dd>
          </div>
          <div>
            <dt>Candidate proof</dt>
            <dd>
              {e.optimizer.proven} / 3 · full: {String(e.optimizer.full)}
            </dd>
          </div>
          <div>
            <dt>Incumbent source</dt>
            <dd>
              {e.optimizer.incumbentPhase === null
                ? "No incumbent"
                : `Phase ${e.optimizer.incumbentPhase}${e.optimizer.retained ? " — retained earlier incumbent" : ""}`}
            </dd>
          </div>
        </dl>
        {!e.optimizer.candidate && (
          <Notice>
            No accepted optimizer incumbent or candidate metrics are available. A resource stop or
            UNKNOWN is not proof of infeasibility.
          </Notice>
        )}
        <TableScroll label="CP-SAT proof phases">
          <table>
            <thead>
              <tr>
                <th scope="col">Phase</th>
                <th scope="col">Objective</th>
                <th scope="col">Native status</th>
                <th scope="col">Value / bound</th>
                <th scope="col">Proven</th>
              </tr>
            </thead>
            <tbody>
              {e.optimizer.phases.map((p) => (
                <tr key={p.phase}>
                  <th scope="row">{p.phase}</th>
                  <td>{p.objective}</td>
                  <td>{p.status}</td>
                  <td>
                    {p.value === null ? "No incumbent" : formatSignedExact(p.value)} /{" "}
                    {p.bound === null ? "Not reported" : formatSignedExact(p.bound)}
                  </td>
                  <td>{String(p.proven)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        <p className="field-help">
          FEASIBLE remains unproven. Candidate proof is never transferred to a selected greedy
          schedule. Objective order: unfinished pieces → completed-order priority-weighted tardiness
          → makespan.
        </p>
      </details>
    </Panel>
  );
}
export function AlgorithmComparison({ evaluation: e }: { evaluation: Evaluation }) {
  const evidence = e.optimizer.comparison;
  return (
    <Panel
      title="Greedy vs selected result"
      description="Same instance, frozen objective order; backend-provided metrics"
    >
      <TableScroll label="Algorithm metric comparison">
        <table>
          <thead>
            <tr>
              <th scope="col">Metric / unit</th>
              <th scope="col">Verified greedy</th>
              <th scope="col">Selected {e.producer}</th>
              <th scope="col">Optimizer candidate</th>
            </tr>
          </thead>
          <tbody>
            {metricDefinitions.map(([key, label, unit]) => (
              <tr key={key}>
                <th scope="row">
                  {label}
                  <span className="cell-secondary">{unit}</span>
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
            Candidate vs greedy: {evidence.relation}
          </Badge>
          <p className="field-help">Deciding objective: {evidence.deciding ?? "None — tie"}</p>
          <dl className="objective-grid">
            {objectives.map((key) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>
                  {evidence.before[key]} → {evidence.after[key]} · Δ{" "}
                  {formatSignedExact(evidence.changes[key] ?? "0")}
                </dd>
              </div>
            ))}
          </dl>
          <p className="field-help">
            Backend comparison supplies objective differences only; unreported same-instance
            percentage differences are not invented.
          </p>
        </div>
      ) : (
        <Notice>
          No accepted candidate comparison is available. The selected verified greedy result remains
          explicit.
        </Notice>
      )}
    </Panel>
  );
}
export function ScenarioMetrics({ comparison: c }: { comparison: Comparison }) {
  return (
    <Panel
      title="Baseline vs scenario"
      description="Backend-provided scenario-minus-baseline deltas; conditional synthetic planning"
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
          {c.selectedComparison.relation}
        </Badge>
        <span>Deciding objective: {c.selectedComparison.deciding ?? "None — tie"}</span>
        <span>Greedy-only relation: {c.greedyComparison.relation}</span>
      </div>
      <TableScroll label="Scenario metric differences">
        <table>
          <thead>
            <tr>
              <th scope="col">Metric / unit</th>
              <th scope="col">Baseline · {c.baseline.producer}</th>
              <th scope="col">Scenario · {c.scenario.producer}</th>
              <th scope="col">Absolute Δ</th>
              <th scope="col">Relative Δ</th>
            </tr>
          </thead>
          <tbody>
            {metricDefinitions.map(([key, label, unit]) => {
              const d = c.deltas[key];
              return (
                <tr key={key}>
                  <th scope="row">
                    {label}
                    <span className="cell-secondary">{unit}</span>
                  </th>
                  <td>{metricText(d.before, unit)}</td>
                  <td>{metricText(d.after, unit)}</td>
                  <td>
                    {d.absolute === null ? "Not applicable" : formatSignedExact(d.absolute)}
                    {unit === "ratio" && d.points !== null && (
                      <span className="cell-secondary">
                        {formatSignedExact(d.points)} percentage points
                      </span>
                    )}
                  </td>
                  <td>
                    {d.percentage === null ? (
                      <span className="cell-secondary">Not applicable · {d.status}</span>
                    ) : (
                      `${formatSignedExact(d.percentage)}%`
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableScroll>
      <Notice>
        Tardiness covers completed orders only. Compare unfinished demand first. Utilization
        denominators can change; greater hypothetical capacity does not guarantee a better schedule
        or observed productivity.
      </Notice>
      <details className="details-block">
        <summary>Verified change audit & identities ({c.audit.length} changes)</summary>
        <dl className="detail-grid">
          <div className="full-width">
            <dt>Baseline fingerprint</dt>
            <dd>
              <code>{c.baselineFingerprint}</code>
            </dd>
          </div>
          <div className="full-width">
            <dt>Derived scenario ID / fingerprint</dt>
            <dd>
              {c.scenarioId}
              <br />
              <code>{c.scenarioFingerprint}</code>
            </dd>
          </div>
          <div className="full-width">
            <dt>Specification fingerprint</dt>
            <dd>
              <code>{c.fingerprint}</code>
            </dd>
          </div>
          <div className="full-width">
            <dt>Verified same-demand fingerprint</dt>
            <dd>
              <code>{c.demandFingerprint}</code>
            </dd>
          </div>
        </dl>
        {c.audit.map((a) => (
          <div className="audit-record" key={a.index}>
            <strong>
              {a.index}. {a.operation} · {a.target} · {a.changed ? "changed" : "explicit no-op"}
            </strong>
            <JsonBlock label={`Change ${a.index} before and after`}>
              {encodeExact({ before: a.before, after: a.after })}
            </JsonBlock>
          </div>
        ))}
        <ul>
          {c.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </details>
    </Panel>
  );
}
