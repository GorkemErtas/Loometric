import { Gantt } from "../components/Gantt";
import { ActionStatus, PlanningGate, PlanSummary } from "../components/PlanningResults";
import { Badge, Empty, JsonBlock, Notice, Panel } from "../components/ui";
import { encodeExact } from "../domain/json";
import { interval } from "../domain/planning";
import { executionBlock } from "../domain/scenario";
import { useI18n } from "../i18n/I18n";
import { usePlanning } from "../state/PlanningWorkspace";
import { useWorkspace } from "../state/Workspace";

export function Scheduling() {
  const { t, label: textLabel, clockLabel } = useI18n();

  const { dataset, api, capabilities, status } = useWorkspace();
  const { reference, busy, jobs, runReference, submitJob } = usePlanning();
  const blocked = executionBlock(dataset, capabilities),
    disabled = !api || !!blocked || !!busy || status === "loading";
  const horizon = dataset?.instance ? interval(dataset.instance.horizon) : null;
  return (
    <div className="page-stack">
      <PlanningGate />
      {dataset && (
        <Panel
          title={t("Frozen scheduling input")}
          description={textLabel(dataset.description)}
          action={<Badge tone="amber">{t("SYNTHETIC INPUT")}</Badge>}
        >
          <dl className="provenance-grid">
            <div>
              <dt>{t("Instance")}</dt>
              <dd>
                {dataset.instance ? String(dataset.instance.instance_id) : t("Capacity-only input")}
              </dd>
            </div>
            <div>
              <dt>{t("Envelope")}</dt>
              <dd>
                {t("{p0} orders · {p1} operations / maximum 32 orders, 96 operations", {
                  p0: dataset.planning.orders.length,
                  p1: dataset.planning.orders.reduce((n, o) => n + o.stages.length, 0),
                })}
              </dd>
            </div>
            <div className="full-width">
              <dt>{t("Horizon / source offsets")}</dt>
              <dd>
                {horizon
                  ? t("{p0} → {p1}", { p0: clockLabel(horizon.start), p1: clockLabel(horizon.end) })
                  : t("Not a scheduling contract")}
              </dd>
            </div>
            <div className="full-width">
              <dt>{t("Source")}</dt>
              <dd>
                <code>{dataset.sourceFile}</code>
              </dd>
            </div>
          </dl>
          <div className="panel-actions">
            <a className="button" href="/#/orders">
              {t("Inspect orders & stages")}
            </a>
            <a className="button" href="/#/resources">
              {t("Inspect resources & calendar")}
            </a>
          </div>
          <details className="details-block">
            <summary>{t("Frozen policy & complete input")}</summary>
            <p>
              {t(
                "whole-stage-minute-v1: full-batch, nonpreemptive stages, one compatible line and one working fragment; precedence and finite line reservations. Priority 1 is highest. No splitting, shared crews, materials, setups, initial WIP or ML capacity.",
              )}
            </p>
            <JsonBlock label={t("Complete frozen scheduling input")}>
              {dataset.instance
                ? encodeExact(dataset.instance)
                : t(
                    "The consolidated CSV and capacity exports are inspection data, not executable scheduling instances.",
                  )}
            </JsonBlock>
          </details>
          <div className="workflow-actions">
            <button
              type="button"
              className="button button-primary"
              disabled={disabled}
              onClick={() => void runReference()}
            >
              {reference ? t("Run reference again") : t("Run reference scheduling")}
            </button>
            <button
              type="button"
              className="button"
              disabled={disabled || !reference?.data.feasible || jobs.length >= 8}
              onClick={() => void submitJob(false)}
            >
              {t("Submit bounded CP-SAT job")}
            </button>
            <a className="text-link" href="/#/scenarios">
              {t("Build a what-if scenario →")}
            </a>
          </div>
          <p className="table-footnote">
            {t(
              "Inputs exceeding this HTTP envelope are unsupported and never truncated. Jobs use server-fixed seed 42, worker 1, 1 s wall / 1 deterministic unit per phase.",
            )}
          </p>
        </Panel>
      )}
      <Notice>
        {t(
          "Submitting creates server work. POST is not idempotent: repeated submissions can create duplicates. Leaving a page stops polling; changing dataset/session clears local tracking and results. Jobs may continue on the server. Copy the job ID first; only explicit Cancel requests termination.",
        )}
      </Notice>
      <ActionStatus />
      {reference && dataset ? (
        <>
          <div className="report-receipt">
            <Badge tone="teal">{t("Actual API response")}</Badge>
            <span>
              {t("Dispatch request ID:")} <code>{reference.requestId}</code>
            </span>
            <span>
              {t("Instance fingerprint:")} <code>{reference.data.fingerprint}</code>
            </span>
          </div>
          <PlanSummary metrics={reference.data.metrics} />
          <Gantt
            plan={reference.data}
            horizon={reference.data.horizon}
            planning={dataset.planning}
          />
        </>
      ) : (
        !busy && (
          <Empty title={t("No reference schedule loaded")}>
            {t(
              "Select Competing orders, Capacity what-if, Routing trade-off or Parallel production, connect the local API and run the reference scheduler.",
            )}
          </Empty>
        )
      )}
    </div>
  );
}
