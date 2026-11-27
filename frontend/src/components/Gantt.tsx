import { useState } from "react";
import { calendarBands, elapsedMinutes, geometry } from "../domain/gantt";
import type { Interval, Planning } from "../domain/models";
import type { Allocation, Comparison, VerifiedPlan } from "../domain/planning";
import { useI18n } from "../i18n/I18n";
import { Badge, Empty, Modal, Notice, Panel, TableScroll } from "./ui";

export function Gantt({
  plan,
  horizon,
  planning,
  audit = [],
  title = "Verified production schedule",
}: {
  plan: VerifiedPlan;
  horizon: Interval;
  planning: Planning;
  audit?: Comparison["audit"];
  title?: string;
}) {
  const { t, label: textLabel, codeLabel, formatExact, clockLabel, stageName } = useI18n();

  const [selected, setSelected] = useState<Allocation | null>(null);
  if (!plan.feasible)
    return (
      <Panel title={textLabel(title)}>
        <Notice>
          {t(
            "INVALID: independent verification rejected this proposal. No Gantt or performance metrics are accepted. {p0}",
            { p0: plan.violations.join(", ") },
          )}
        </Notice>
      </Panel>
    );
  const bands = calendarBands(planning, audit);
  const colors = ["#08776c", "#426a91", "#805b8e", "#956026"];
  const lines = [
    ...new Set([
      ...planning.lines.map((line) => line.id),
      ...plan.allocations.map((a) => a.lineId),
    ]),
  ];
  return (
    <div className="page-stack">
      <Panel
        title={textLabel(title)}
        description={t("Allocated blocks come from independently verified backend results")}
        action={<Badge tone={plan.complete ? "teal" : "amber"}>{codeLabel(plan.status)}</Badge>}
      >
        <div className="gantt-heading">
          <span>{t("Time axis · exact reported horizon")}</span>
          <span className="gantt-source">{t("SYNTHETIC · {p0}", { p0: plan.instanceId })}</span>
        </div>
        <figure
          className="gantt-figure"
          aria-label={t("{p0}: allocated operations by production line", { p0: textLabel(title) })}
        >
          <div className="gantt-axis">
            <span>{t("Production line")}</span>
            <div>
              <time dateTime={horizon.start}>{clockLabel(horizon.start)}</time>
              <time dateTime={horizon.end}>{clockLabel(horizon.end)}</time>
            </div>
          </div>
          {lines.map((line) => (
            <div className="gantt-row" key={line}>
              <div className="gantt-line">
                <strong>{line}</strong>
                <span>
                  {stageName(
                    planning.lines.find((item) => item.id === line)?.stage ?? "reported line",
                  )}
                </span>
              </div>
              <div className="gantt-track">
                {bands.shifts
                  .filter((b) => b.lineId === line)
                  .map((b) => {
                    const style = geometry(b, horizon);
                    return (
                      style && (
                        <span
                          key={b.id}
                          className="gantt-shift"
                          style={style}
                          title={t("Declared shift {p0}: {p1} → {p2}", {
                            p0: b.shiftId,
                            p1: clockLabel(b.start),
                            p2: clockLabel(b.end),
                          })}
                          aria-hidden="true"
                        />
                      )
                    );
                  })}
                {bands.interruptions
                  .filter((b) => b.lineId === line)
                  .map((b) => {
                    const style = geometry(b, horizon);
                    return (
                      style && (
                        <span
                          key={b.id}
                          className="gantt-interruption"
                          style={style}
                          title={t("{p0}: {p1} → {p2}", {
                            p0: "reference" in b ? b.reason : t("Declared break"),
                            p1: clockLabel(b.start),
                            p2: clockLabel(b.end),
                          })}
                          aria-hidden="true"
                        />
                      )
                    );
                  })}
                {plan.allocations
                  .filter((a) => a.lineId === line)
                  .map((a) => {
                    const style = geometry(a, horizon);
                    return (
                      style && (
                        <button
                          key={`${a.orderId}:${a.stage}`}
                          type="button"
                          className="gantt-operation"
                          style={{
                            ...style,
                            backgroundColor:
                              colors[
                                planning.orders.findIndex((o) => o.id === a.orderId) % colors.length
                              ] ?? colors[0],
                          }}
                          onClick={() => setSelected(a)}
                          aria-label={t(
                            "Inspect operation {p0} {p1} on {p2}, {p3} pieces, {p4} to {p5}",
                            {
                              p0: a.orderId,
                              p1: stageName(a.stage),
                              p2: a.lineId,
                              p3: formatExact(a.quantity),
                              p4: clockLabel(a.start),
                              p5: clockLabel(a.end),
                            },
                          )}
                          title={t("{p0} · {p1} · {p2} → {p3}", {
                            p0: a.orderId,
                            p1: stageName(a.stage),
                            p2: clockLabel(a.start),
                            p3: clockLabel(a.end),
                          })}
                        >
                          <strong>{a.orderId}</strong>
                          <span>{stageName(a.stage)}</span>
                        </button>
                      )
                    );
                  })}
              </div>
            </div>
          ))}
          <figcaption className="gantt-legend">
            <span>
              <i className="gantt-key gantt-key-operation" />
              {t("Verified allocation")}
            </span>
            <span>
              <i className="gantt-key gantt-key-shift" />
              {t("Declared shift window")}
            </span>
            <span>
              <i className="gantt-key gantt-key-stop" />
              {t("Declared interruption")}
            </span>
          </figcaption>
          <p className="chart-note">
            {t(
              "Positions use absolute timestamp geometry only. Blocks are not moved, resized or rescheduled. Calendar annotations use declared inputs{p0}. Use the table for exact times and on small screens.",
              { p0: audit.length ? t(" and the backend’s approved change audit") : "" },
            )}
          </p>
        </figure>
        {plan.allocations.length === 0 && (
          <Empty title={t("No verified allocations")}>
            {t(
              "The verified partial plan contains no allocated operations; all work remains explicit below.",
            )}
          </Empty>
        )}
        <details className="gantt-table" open>
          <summary>
            {t("Structured operation table ({p0})", { p0: plan.allocations.length })}
          </summary>
          <TableScroll label={t("{p0} operation table", { p0: textLabel(title) })}>
            <table>
              <thead>
                <tr>
                  <th scope="col">{t("Order / stage")}</th>
                  <th scope="col">{t("Line / assignment")}</th>
                  <th scope="col">{t("Start → end (source offsets)")}</th>
                  <th scope="col" className="numeric">
                    {t("Pieces")}
                  </th>
                  <th scope="col" className="numeric">
                    {t("Elapsed min")}
                  </th>
                  <th scope="col">{t("Details")}</th>
                </tr>
              </thead>
              <tbody>
                {plan.allocations.map((a) => (
                  <tr key={`${a.orderId}:${a.stage}`}>
                    <th scope="row">
                      <span className="cell-primary">{a.orderId}</span>
                      <span className="cell-secondary">{stageName(a.stage)}</span>
                    </th>
                    <td>
                      <span className="cell-primary">{a.lineId}</span>
                      <span className="cell-secondary">{a.assignmentId}</span>
                    </td>
                    <td>
                      <time dateTime={a.start}>{clockLabel(a.start)}</time>
                      <span className="cell-secondary">→ {clockLabel(a.end)}</span>
                    </td>
                    <td className="numeric">{formatExact(a.quantity)}</td>
                    <td className="numeric">{formatExact(elapsedMinutes(a))}</td>
                    <td>
                      <button
                        type="button"
                        className="text-link"
                        onClick={() => setSelected(a)}
                        aria-label={t("Operation details {p0} {p1}", {
                          p0: a.orderId,
                          p1: stageName(a.stage),
                        })}
                      >
                        {t("Inspect")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableScroll>
        </details>
      </Panel>
      <Panel
        title={t("Order completion & unfinished work")}
        description={t(
          "Finished units require all stages. A valid partial plan leaves demand unfinished.",
        )}
      >
        <TableScroll label={t("Verified order outcomes")}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("Order")}</th>
                <th scope="col">{t("Outcome")}</th>
                <th scope="col" className="numeric">
                  {t("Finished pieces")}
                </th>
                <th scope="col" className="numeric">
                  {t("Unfinished pieces")}
                </th>
                <th scope="col">{t("Allocated stages / completion")}</th>
              </tr>
            </thead>
            <tbody>
              {plan.orders.map((order) => (
                <tr key={order.id}>
                  <th scope="row">{order.id}</th>
                  <td>
                    <Badge tone={order.status === "COMPLETED" ? "teal" : "amber"}>
                      {codeLabel(order.status)}
                    </Badge>
                  </td>
                  <td className="numeric">{formatExact(order.finished)}</td>
                  <td className="numeric">{formatExact(order.unfinished)}</td>
                  <td>
                    {order.stages.map(stageName).join(", ") || t("None allocated")}
                    <span className="cell-secondary">
                      {order.completion
                        ? clockLabel(order.completion)
                        : t("No completed-order timestamp")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        <div className="unfinished-list">
          {plan.unscheduled.map((item) => (
            <div key={`${item.orderId}:${stageName(item.stage)}`}>
              <Badge tone="amber">{t("UNSCHEDULED")}</Badge>
              <strong>
                {item.orderId} · {stageName(item.stage)}
              </strong>
              <span>{t("{p0} pieces", { p0: formatExact(item.quantity) })}</span>
              <code>{codeLabel(item.reason)}</code>
            </div>
          ))}
          {plan.unscheduled.length === 0 && <p>{t("All required operations are allocated.")}</p>}
        </div>
      </Panel>
      {selected && (
        <Modal
          title={t("Operation {p0} · {p1}", {
            p0: selected.orderId,
            p1: stageName(selected.stage),
          })}
          onClose={() => setSelected(null)}
        >
          <dl className="detail-grid">
            <div>
              <dt>{t("Order / stage")}</dt>
              <dd>
                {selected.orderId} / {stageName(selected.stage)}
              </dd>
            </div>
            <div>
              <dt>{t("Line / assignment")}</dt>
              <dd>
                {selected.lineId} / {selected.assignmentId}
              </dd>
            </div>
            <div>
              <dt>{t("Shift / profile")}</dt>
              <dd>
                {selected.shiftId} / {selected.profileId}
              </dd>
            </div>
            <div>
              <dt>{t("Quantity")}</dt>
              <dd>{t("{p0} pieces", { p0: formatExact(selected.quantity) })}</dd>
            </div>
            <div className="full-width">
              <dt>{t("Exact reported interval")}</dt>
              <dd>
                {clockLabel(selected.start)}
                <br />
                {clockLabel(selected.end)}
              </dd>
            </div>
            <div>
              <dt>{t("Elapsed duration from endpoints")}</dt>
              <dd>{t("{p0} minutes", { p0: formatExact(elapsedMinutes(selected)) })}</dd>
            </div>
            <div>
              <dt>{t("Reported reserved labor")}</dt>
              <dd>{t("{p0} worker-minutes", { p0: formatExact(selected.workerMinutes) })}</dd>
            </div>
            <div>
              <dt>{t("Reported standard capacity")}</dt>
              <dd>
                {t("{p0} standard worker-minutes", { p0: formatExact(selected.standardMinutes) })}
              </dd>
            </div>
          </dl>
          <Notice>
            {t(
              "Verified synthetic allocation. No drag-and-drop editing or inferred machine availability.",
            )}
          </Notice>
        </Modal>
      )}
    </div>
  );
}
