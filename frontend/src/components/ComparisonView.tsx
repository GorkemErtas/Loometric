import { useState } from "react";
import type { Planning } from "../domain/models";
import type { Comparison } from "../domain/planning";
import { useI18n } from "../i18n/I18n";
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
  const { t, codeLabel } = useI18n();

  const [side, setSide] = useState("scenario");
  const selected = side === "baseline" ? c.baseline : c.scenario;
  return (
    <div className="page-stack">
      <Notice>
        <strong>{c.label}</strong>{" "}
        {t(
          "· Same demand verified by the backend. These are hypothetical planning changes, not observed productivity improvements.",
        )}
      </Notice>
      <ScenarioMetrics comparison={c} />
      <div className="two-columns">
        <EvaluationEvidence title={t("Baseline producer & proof")} evaluation={c.baseline} />
        <EvaluationEvidence title={t("Scenario producer & proof")} evaluation={c.scenario} />
      </div>
      <div className="schedule-switch">
        <label htmlFor="comparison-schedule">{t("Inspect verified schedule")}</label>
        <select
          id="comparison-schedule"
          value={side}
          onChange={(event) => setSide(event.target.value)}
        >
          <option value="baseline">
            {t("Baseline · {p0}", { p0: codeLabel(c.baseline.producer) })}
          </option>
          <option value="scenario">
            {t("Scenario · {p0}", { p0: codeLabel(c.scenario.producer) })}
          </option>
        </select>
      </div>
      <Gantt
        key={`${c.fingerprint}:${side}`}
        title={t("{p0} verified Gantt", {
          p0: side === "baseline" ? t("Baseline") : t("Scenario"),
        })}
        plan={selected.selected}
        horizon={side === "baseline" ? c.baselineHorizon : c.scenarioHorizon}
        planning={planning}
        audit={side === "scenario" ? c.audit : []}
      />
      <details className="panel advanced-comparisons">
        <summary>{t("Advanced same-instance algorithm comparisons")}</summary>
        <div className="page-stack">
          <AlgorithmComparison evaluation={c.baseline} />
          <AlgorithmComparison evaluation={c.scenario} />
        </div>
      </details>
    </div>
  );
}
