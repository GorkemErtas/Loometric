import { Gantt } from "../components/Gantt";
import { ActionStatus, PlanningGate, PlanSummary } from "../components/PlanningResults";
import { Badge, Empty, JsonBlock, Notice, Panel } from "../components/ui";
import { encodeExact } from "../domain/json";
import { interval } from "../domain/planning";
import { executionBlock } from "../domain/scenario";
import { usePlanning } from "../state/PlanningWorkspace";
import { useWorkspace } from "../state/Workspace";

export function Scheduling() {
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
          title="Frozen scheduling input"
          description={dataset.description}
          action={<Badge tone="amber">SYNTHETIC INPUT</Badge>}
        >
          <dl className="provenance-grid">
            <div>
              <dt>Instance</dt>
              <dd>
                {dataset.instance ? String(dataset.instance.instance_id) : "Capacity-only input"}
              </dd>
            </div>
            <div>
              <dt>Envelope</dt>
              <dd>
                {dataset.planning.orders.length} orders ·{" "}
                {dataset.planning.orders.reduce((n, o) => n + o.stages.length, 0)} operations /
                maximum 32 orders, 96 operations
              </dd>
            </div>
            <div className="full-width">
              <dt>Horizon / source offsets</dt>
              <dd>{horizon ? `${horizon.start} → ${horizon.end}` : "Not a scheduling contract"}</dd>
            </div>
            <div className="full-width">
              <dt>Source</dt>
              <dd>
                <code>{dataset.sourceFile}</code>
              </dd>
            </div>
          </dl>
          <div className="panel-actions">
            <a className="button" href="/#/orders">
              Inspect orders & stages
            </a>
            <a className="button" href="/#/resources">
              Inspect resources & calendar
            </a>
          </div>
          <details className="details-block">
            <summary>Frozen policy & complete input</summary>
            <p>
              whole-stage-minute-v1: full-batch, nonpreemptive stages, one compatible line and one
              working fragment; precedence and finite line reservations. Priority 1 is highest. No
              splitting, shared crews, materials, setups, initial WIP or ML capacity.
            </p>
            <JsonBlock label="Complete frozen scheduling input">
              {dataset.instance
                ? encodeExact(dataset.instance)
                : "The consolidated CSV and M02 capacity exports are inspection data, not executable scheduling instances."}
            </JsonBlock>
          </details>
          <div className="workflow-actions">
            <button
              type="button"
              className="button button-primary"
              disabled={disabled}
              onClick={() => void runReference()}
            >
              {reference ? "Run reference again" : "Run reference scheduling"}
            </button>
            <button
              type="button"
              className="button"
              disabled={disabled || !reference?.data.feasible || jobs.length >= 8}
              onClick={() => void submitJob(false)}
            >
              Submit bounded CP-SAT job
            </button>
            <a className="text-link" href="/#/scenarios">
              Build a what-if scenario →
            </a>
          </div>
          <p className="table-footnote">
            M03C inputs exceeding this HTTP envelope are unsupported and never truncated. Jobs use
            server-fixed seed 42, worker 1, 1 s wall / 1 deterministic unit per phase.
          </p>
        </Panel>
      )}
      <Notice>
        Submitting creates server work. POST is not idempotent: repeated submissions can create
        duplicates. Leaving a page stops polling; changing dataset/session clears local tracking and
        results. Jobs may continue on the server. Copy the job ID first; only explicit Cancel
        requests termination.
      </Notice>
      <ActionStatus />
      {reference && dataset ? (
        <>
          <div className="report-receipt">
            <Badge tone="teal">Actual API response</Badge>
            <span>
              Dispatch request ID: <code>{reference.requestId}</code>
            </span>
            <span>
              Instance fingerprint: <code>{reference.data.fingerprint}</code>
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
          <Empty title="No reference schedule loaded">
            Select Competing orders, Capacity what-if, Routing trade-off or Parallel production,
            connect the local API and run the reference scheduler.
          </Empty>
        )
      )}
    </div>
  );
}
