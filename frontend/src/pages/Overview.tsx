import { CapacityBars, CapacityContent, Provenance } from "../components/Reports";
import {
  Badge,
  Empty,
  ErrorNotice,
  Icon,
  Notice,
  Panel,
  Stat,
  TableScroll,
} from "../components/ui";
import { dateLabel, formatExact, percentExact, sumExact } from "../domain/exact";
import { useWorkspace } from "../state/Workspace";

export function Overview() {
  const { dataset, mode, schedule, scheduleLoading, scheduleError, loadSchedule } = useWorkspace();
  if (!dataset)
    return (
      <Empty title="No planning dataset">There are no synthetic inputs in this catalog.</Empty>
    );
  const planning = dataset.planning;
  return (
    <div className="page-stack">
      <div className="stat-grid">
        <Stat
          label="Orders"
          value={planning.orders.length}
          detail="Declared planning demand"
          icon="orders"
        />
        <Stat
          label="Requested units"
          value={formatExact(sumExact(planning.orders.map((item) => item.quantity)))}
          unit="pieces"
          detail="Sum of unique order quantities"
          icon="orders"
        />
        <Stat
          label="Production lines"
          value={planning.lines.length}
          detail={`${planning.capabilities.length} declared route capabilities`}
          icon="resources"
        />
        <Stat
          label="Shifts"
          value={planning.shifts.length}
          detail={`${planning.assignments.length} line–shift assignments`}
          icon="capacity"
        />
      </div>
      <div className="section-grid">
        <Panel
          title="Available capacity"
          description="M02 independent estimates · elapsed minutes per assignment"
          action={
            <a className="text-link" href="/#/capacity">
              Explore capacity <Icon name="arrow" size={16} />
            </a>
          }
        >
          <CapacityContent>
            {(report) => (
              <>
                <div className="capacity-summary">
                  <strong>
                    {formatExact(sumExact(report.slots.map((slot) => slot.workerMinutes)))}
                  </strong>
                  <span>available worker-minutes across {report.slots.length} unique slots</span>
                </div>
                <CapacityBars report={report} />
              </>
            )}
          </CapacityContent>
        </Panel>
        <Panel title="Planning context" description={dataset.description}>
          <dl className="context-list">
            <div>
              <dt>Working dates</dt>
              <dd>{planning.workingDates.map(dateLabel).join(" · ") || "None declared"}</dd>
            </div>
            <div>
              <dt>Styles</dt>
              <dd>{planning.styles.map((style) => style.id).join(", ") || "None declared"}</dd>
            </div>
            <div>
              <dt>Capacity basis</dt>
              <dd>Declared crews & assumed efficiency</dd>
            </div>
            <div>
              <dt>Allocation status</dt>
              <dd>
                <Badge>Not allocated by M02</Badge>
              </dd>
            </div>
          </dl>
          <Notice>
            Independent capacity checks can share the same slot. They do not establish a feasible
            production plan.
          </Notice>
        </Panel>
      </div>
      <Panel
        title="Orders at a glance"
        description="Declared demand and delivery windows"
        action={
          <a className="text-link" href="/#/orders">
            View all orders <Icon name="arrow" size={16} />
          </a>
        }
      >
        <TableScroll label="Order summary scrollable table">
          <table>
            <thead>
              <tr>
                <th scope="col">Order / style</th>
                <th scope="col" className="numeric">
                  Quantity (pieces)
                </th>
                <th scope="col">Required stages</th>
                <th scope="col">Due date</th>
              </tr>
            </thead>
            <tbody>
              {planning.orders.slice(0, 6).map((order) => (
                <tr key={order.id}>
                  <th scope="row">
                    <span className="cell-primary">{order.id}</span>
                    <span className="cell-secondary">{order.styleId}</span>
                  </th>
                  <td className="numeric">{formatExact(order.quantity)}</td>
                  <td>
                    <div className="badge-row">
                      {order.stages.map((stage) => (
                        <Badge key={stage}>{stage}</Badge>
                      ))}
                    </div>
                  </td>
                  <td>{dateLabel(order.due)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        {planning.orders.length === 0 && (
          <Empty title="No declared orders">This input contains no orders.</Empty>
        )}
      </Panel>
      <Panel
        title="Existing scheduling outcome"
        description="An outcome appears only after you explicitly load a previously saved proposal."
        action={
          dataset.savedProposal && (
            <button
              type="button"
              className="button"
              onClick={() => void loadSchedule()}
              disabled={scheduleLoading}
            >
              {scheduleLoading
                ? "Verifying…"
                : schedule
                  ? "Reload saved outcome"
                  : "Load saved outcome"}
            </button>
          )
        }
      >
        {scheduleError && <ErrorNotice error={scheduleError} />}
        {scheduleLoading && (
          <p role="status" className="panel-body">
            Verifying the existing proposal with the local backend…
          </p>
        )}
        {!schedule && !scheduleLoading && !scheduleError && (
          <Empty title="No schedule outcome loaded">
            {dataset.savedProposal
              ? "This dataset has a saved M03A proposal. Load it explicitly to inspect its verified partial outcome."
              : "This capacity fixture has no saved schedule. Use Production scheduling to run a verified reference schedule."}
          </Empty>
        )}
        {schedule && (
          <div className="panel-body">
            <div className="outcome-heading">
              <Badge tone={schedule.feasible ? "teal" : "red"}>{schedule.status}</Badge>
              <span>
                {mode === "preview"
                  ? "Saved M03A verification fixture"
                  : "Existing proposal reverified by M05A"}{" "}
                · {schedule.algorithm}
              </span>
            </div>
            {schedule.metrics ? (
              <>
                <div className="stat-grid outcome-stats">
                  <Stat
                    label="Completed units"
                    value={formatExact(schedule.metrics.completed)}
                    unit="pieces"
                    detail="All required stages completed"
                  />
                  <Stat
                    label="Unfinished units"
                    value={formatExact(schedule.metrics.unfinished)}
                    unit="pieces"
                    detail="Remaining declared order demand"
                  />
                  <Stat
                    label="Line utilization"
                    value={
                      schedule.metrics.lineUtilization === null
                        ? "Not applicable"
                        : percentExact(schedule.metrics.lineUtilization)
                    }
                    detail={`${formatExact(schedule.metrics.occupiedLine)} / ${formatExact(schedule.metrics.availableLine)} net line-minutes`}
                  />
                  <Stat
                    label="Standard capacity use"
                    value={
                      schedule.metrics.standardUtilization === null
                        ? "Not applicable"
                        : percentExact(schedule.metrics.standardUtilization)
                    }
                    detail={`${formatExact(schedule.metrics.consumedStandard)} / ${formatExact(schedule.metrics.availableStandard)} standard worker-minutes`}
                  />
                </div>
                <p className="field-help">
                  Synthetic verified scheduling metrics; utilization denominators come from the
                  scheduling report. A partial result does not satisfy all demand.
                </p>
              </>
            ) : (
              <Notice>
                No metrics are available for this invalid proposal. {schedule.violations.join(", ")}
              </Notice>
            )}
            <details className="details-block">
              <summary>Verified instance fingerprint</summary>
              <code className="break-code">{schedule.fingerprint}</code>
            </details>
          </div>
        )}
      </Panel>
      <Provenance />
    </div>
  );
}
