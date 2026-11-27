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
import { sumExact } from "../domain/exact";
import { useI18n } from "../i18n/I18n";
import { useWorkspace } from "../state/Workspace";

export function Overview() {
  const {
    t,
    label: textLabel,
    codeLabel,
    formatExact,
    percentExact,
    dateLabel,
    stageName,
  } = useI18n();

  const { dataset, mode, schedule, scheduleLoading, scheduleError, loadSchedule } = useWorkspace();
  if (!dataset)
    return (
      <Empty title={t("No planning dataset")}>
        {t("There are no synthetic inputs in this catalog.")}
      </Empty>
    );
  const planning = dataset.planning;
  return (
    <div className="page-stack">
      <div className="stat-grid">
        <Stat
          label={t("Orders")}
          value={planning.orders.length}
          detail={t("Declared planning demand")}
          icon="orders"
        />
        <Stat
          label={t("Requested units")}
          value={formatExact(sumExact(planning.orders.map((item) => item.quantity)))}
          unit="pieces"
          detail={t("Sum of unique order quantities")}
          icon="orders"
        />
        <Stat
          label={t("Production lines")}
          value={planning.lines.length}
          detail={t("{p0} declared route capabilities", { p0: planning.capabilities.length })}
          icon="resources"
        />
        <Stat
          label={t("Shifts")}
          value={planning.shifts.length}
          detail={t("{p0} line–shift assignments", { p0: planning.assignments.length })}
          icon="capacity"
        />
      </div>
      <div className="section-grid">
        <Panel
          title={t("Available capacity")}
          description={t("Independent estimates · elapsed minutes per assignment")}
          action={
            <a className="text-link" href="/#/capacity">
              {t("Explore capacity")} <Icon name="arrow" size={16} />
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
                  <span>
                    {t("available worker-minutes across {p0} unique slots", {
                      p0: report.slots.length,
                    })}
                  </span>
                </div>
                <CapacityBars report={report} />
              </>
            )}
          </CapacityContent>
        </Panel>
        <Panel title={t("Planning context")} description={textLabel(dataset.description)}>
          <dl className="context-list">
            <div>
              <dt>{t("Working dates")}</dt>
              <dd>{planning.workingDates.map(dateLabel).join(" · ") || t("None declared")}</dd>
            </div>
            <div>
              <dt>{t("Styles")}</dt>
              <dd>{planning.styles.map((style) => style.id).join(", ") || t("None declared")}</dd>
            </div>
            <div>
              <dt>{t("Capacity basis")}</dt>
              <dd>{t("Declared crews & assumed efficiency")}</dd>
            </div>
            <div>
              <dt>{t("Allocation status")}</dt>
              <dd>
                <Badge>{t("Capacity assessment does not allocate work")}</Badge>
              </dd>
            </div>
          </dl>
          <Notice>
            {t(
              "Independent capacity checks can share the same slot. They do not establish a feasible production plan.",
            )}
          </Notice>
        </Panel>
      </div>
      <Panel
        title={t("Orders at a glance")}
        description={t("Declared demand and delivery windows")}
        action={
          <a className="text-link" href="/#/orders">
            {t("View all orders")} <Icon name="arrow" size={16} />
          </a>
        }
      >
        <TableScroll label={t("Order summary scrollable table")}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("Order / style")}</th>
                <th scope="col" className="numeric">
                  {t("Quantity (pieces)")}
                </th>
                <th scope="col">{t("Required stages")}</th>
                <th scope="col">{t("Due date")}</th>
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
                        <Badge key={stage}>{stageName(stage)}</Badge>
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
          <Empty title={t("No declared orders")}>{t("This input contains no orders.")}</Empty>
        )}
      </Panel>
      <Panel
        title={t("Existing scheduling outcome")}
        description={t(
          "An outcome appears only after you explicitly load a previously saved proposal.",
        )}
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
                  ? t("Reload saved outcome")
                  : t("Load saved outcome")}
            </button>
          )
        }
      >
        {scheduleError && <ErrorNotice error={scheduleError} />}
        {scheduleLoading && (
          <p role="status" className="panel-body">
            {t("Verifying the existing proposal with the local backend…")}
          </p>
        )}
        {!schedule && !scheduleLoading && !scheduleError && (
          <Empty title={t("No schedule outcome loaded")}>
            {dataset.savedProposal
              ? t(
                  "This dataset has a saved proposal. Load it explicitly to inspect its verified partial outcome.",
                )
              : t(
                  "This capacity fixture has no saved schedule. Use Production scheduling to run a verified reference schedule.",
                )}
          </Empty>
        )}
        {schedule && (
          <div className="panel-body">
            <div className="outcome-heading">
              <Badge tone={schedule.feasible ? "teal" : "red"}>{codeLabel(schedule.status)}</Badge>
              <span>
                {mode === "preview"
                  ? t("Saved verification fixture")
                  : t("Existing proposal reverified by the local API")}{" "}
                · {schedule.algorithm}
              </span>
            </div>
            {schedule.metrics ? (
              <>
                <div className="stat-grid outcome-stats">
                  <Stat
                    label={t("Completed units")}
                    value={formatExact(schedule.metrics.completed)}
                    unit="pieces"
                    detail={t("All required stages completed")}
                  />
                  <Stat
                    label={t("Unfinished units")}
                    value={formatExact(schedule.metrics.unfinished)}
                    unit="pieces"
                    detail={t("Remaining declared order demand")}
                  />
                  <Stat
                    label={t("Line utilization")}
                    value={
                      schedule.metrics.lineUtilization === null
                        ? "Not applicable"
                        : percentExact(schedule.metrics.lineUtilization)
                    }
                    detail={t("{p0} / {p1} net line-minutes", {
                      p0: formatExact(schedule.metrics.occupiedLine),
                      p1: formatExact(schedule.metrics.availableLine),
                    })}
                  />
                  <Stat
                    label={t("Standard capacity use")}
                    value={
                      schedule.metrics.standardUtilization === null
                        ? "Not applicable"
                        : percentExact(schedule.metrics.standardUtilization)
                    }
                    detail={t("{p0} / {p1} standard worker-minutes", {
                      p0: formatExact(schedule.metrics.consumedStandard),
                      p1: formatExact(schedule.metrics.availableStandard),
                    })}
                  />
                </div>
                <p className="field-help">
                  {t(
                    "Synthetic verified scheduling metrics; utilization denominators come from the scheduling report. A partial result does not satisfy all demand.",
                  )}
                </p>
              </>
            ) : (
              <Notice>
                {t("No metrics are available for this invalid proposal. {p0}", {
                  p0: schedule.violations.join(", "),
                })}
              </Notice>
            )}
            <details className="details-block">
              <summary>{t("Verified instance fingerprint")}</summary>
              <code className="break-code">{schedule.fingerprint}</code>
            </details>
          </div>
        )}
      </Panel>
      <Provenance />
    </div>
  );
}
