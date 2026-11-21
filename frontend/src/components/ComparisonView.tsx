import { useState } from "react";
import type { Planning } from "../domain/models";
import type { Comparison } from "../domain/planning";
import { Gantt } from "./Gantt";
import { AlgorithmComparison, EvaluationEvidence, ScenarioMetrics } from "./PlanningResults";
import { Notice } from "./ui";

export function ComparisonView({
  comparison: c,
  planning,
}: {
  comparison: Comparison;
  planning: Planning;
}) {
  const [side, setSide] = useState("scenario");
  const selected = side === "baseline" ? c.baseline : c.scenario;
  return (
    <div className="page-stack">
      <Notice>
        <strong>{c.label}</strong> · Same demand verified by the backend. These are hypothetical
        planning changes, not observed productivity improvements.
      </Notice>
      <ScenarioMetrics comparison={c} />
      <div className="two-columns">
        <EvaluationEvidence title="Baseline producer & proof" evaluation={c.baseline} />
        <EvaluationEvidence title="Scenario producer & proof" evaluation={c.scenario} />
      </div>
      <div className="schedule-switch">
        <label htmlFor="comparison-schedule">Inspect verified schedule</label>
        <select
          id="comparison-schedule"
          value={side}
          onChange={(event) => setSide(event.target.value)}
        >
          <option value="baseline">Baseline · {c.baseline.producer}</option>
          <option value="scenario">Scenario · {c.scenario.producer}</option>
        </select>
      </div>
      <Gantt
        key={`${c.fingerprint}:${side}`}
        title={`${side === "baseline" ? "Baseline" : "Scenario"} verified Gantt`}
        plan={selected.selected}
        horizon={side === "baseline" ? c.baselineHorizon : c.scenarioHorizon}
        planning={planning}
        audit={side === "scenario" ? c.audit : []}
      />
      <details className="panel advanced-comparisons">
        <summary>Advanced same-instance algorithm comparisons</summary>
        <div className="page-stack">
          <AlgorithmComparison evaluation={c.baseline} />
          <AlgorithmComparison evaluation={c.scenario} />
        </div>
      </details>
    </div>
  );
}
