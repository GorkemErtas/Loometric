import { useState } from "react";
import { clockLabel, formatExact, stageName } from "../domain/exact";
import { calendarBands, elapsedMinutes, geometry } from "../domain/gantt";
import type { Interval, Planning } from "../domain/models";
import type { Allocation, Comparison, VerifiedPlan } from "../domain/planning";
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
  const [selected, setSelected] = useState<Allocation | null>(null);
  if (!plan.feasible)
    return (
      <Panel title={title}>
        <Notice>
          INVALID: independent verification rejected this proposal. No Gantt or performance metrics
          are accepted. {plan.violations.join(", ")}
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
        title={title}
        description="Allocated blocks come from independently verified backend results"
        action={<Badge tone={plan.complete ? "teal" : "amber"}>{plan.status}</Badge>}
      >
        <div className="gantt-heading">
          <span>Time axis · exact reported horizon</span>
          <span className="gantt-source">SYNTHETIC · {plan.instanceId}</span>
        </div>
        <figure
          className="gantt-figure"
          aria-label={`${title}: allocated operations by production line`}
        >
          <div className="gantt-axis">
            <span>Production line</span>
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
                          title={`Declared shift ${b.shiftId}: ${b.start} → ${b.end}`}
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
                          title={`${b.reason}: ${b.start} → ${b.end}`}
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
                          aria-label={`Inspect operation ${a.orderId} ${a.stage} on ${a.lineId}, ${a.quantity} pieces, ${a.start} to ${a.end}`}
                          title={`${a.orderId} · ${a.stage} · ${a.start} → ${a.end}`}
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
              Verified allocation
            </span>
            <span>
              <i className="gantt-key gantt-key-shift" />
              Declared shift window
            </span>
            <span>
              <i className="gantt-key gantt-key-stop" />
              Declared interruption
            </span>
          </figcaption>
          <p className="chart-note">
            Positions use absolute timestamp geometry only. Blocks are not moved, resized or
            rescheduled. Calendar annotations use declared inputs
            {audit.length ? " and the backend’s approved change audit" : ""}. Use the table for
            exact times and on small screens.
          </p>
        </figure>
        {plan.allocations.length === 0 && (
          <Empty title="No verified allocations">
            The verified partial plan contains no allocated operations; all work remains explicit
            below.
          </Empty>
        )}
        <details className="gantt-table" open>
          <summary>Structured operation table ({plan.allocations.length})</summary>
          <TableScroll label={`${title} operation table`}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Order / stage</th>
                  <th scope="col">Line / assignment</th>
                  <th scope="col">Start → end (source offsets)</th>
                  <th scope="col" className="numeric">
                    Pieces
                  </th>
                  <th scope="col" className="numeric">
                    Elapsed min
                  </th>
                  <th scope="col">Details</th>
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
                      <time dateTime={a.start}>{a.start}</time>
                      <span className="cell-secondary">→ {a.end}</span>
                    </td>
                    <td className="numeric">{formatExact(a.quantity)}</td>
                    <td className="numeric">{elapsedMinutes(a)}</td>
                    <td>
                      <button
                        type="button"
                        className="text-link"
                        onClick={() => setSelected(a)}
                        aria-label={`Operation details ${a.orderId} ${a.stage}`}
                      >
                        Inspect
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
        title="Order completion & unfinished work"
        description="Finished units require all stages. A valid partial plan leaves demand unfinished."
      >
        <TableScroll label="Verified order outcomes">
          <table>
            <thead>
              <tr>
                <th scope="col">Order</th>
                <th scope="col">Outcome</th>
                <th scope="col" className="numeric">
                  Finished pieces
                </th>
                <th scope="col" className="numeric">
                  Unfinished pieces
                </th>
                <th scope="col">Allocated stages / completion</th>
              </tr>
            </thead>
            <tbody>
              {plan.orders.map((order) => (
                <tr key={order.id}>
                  <th scope="row">{order.id}</th>
                  <td>
                    <Badge tone={order.status === "COMPLETED" ? "teal" : "amber"}>
                      {order.status}
                    </Badge>
                  </td>
                  <td className="numeric">{formatExact(order.finished)}</td>
                  <td className="numeric">{formatExact(order.unfinished)}</td>
                  <td>
                    {order.stages.map(stageName).join(", ") || "None allocated"}
                    <span className="cell-secondary">
                      {order.completion ?? "No completed-order timestamp"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        <div className="unfinished-list">
          {plan.unscheduled.map((item) => (
            <div key={`${item.orderId}:${item.stage}`}>
              <Badge tone="amber">UNSCHEDULED</Badge>
              <strong>
                {item.orderId} · {stageName(item.stage)}
              </strong>
              <span>{formatExact(item.quantity)} pieces</span>
              <code>{item.reason}</code>
            </div>
          ))}
          {plan.unscheduled.length === 0 && <p>All required operations are allocated.</p>}
        </div>
      </Panel>
      {selected && (
        <Modal
          title={`Operation ${selected.orderId} · ${stageName(selected.stage)}`}
          onClose={() => setSelected(null)}
        >
          <dl className="detail-grid">
            <div>
              <dt>Order / stage</dt>
              <dd>
                {selected.orderId} / {selected.stage}
              </dd>
            </div>
            <div>
              <dt>Line / assignment</dt>
              <dd>
                {selected.lineId} / {selected.assignmentId}
              </dd>
            </div>
            <div>
              <dt>Shift / profile</dt>
              <dd>
                {selected.shiftId} / {selected.profileId}
              </dd>
            </div>
            <div>
              <dt>Quantity</dt>
              <dd>{formatExact(selected.quantity)} pieces</dd>
            </div>
            <div className="full-width">
              <dt>Exact reported interval</dt>
              <dd>
                {selected.start}
                <br />
                {selected.end}
              </dd>
            </div>
            <div>
              <dt>Elapsed duration from endpoints</dt>
              <dd>{elapsedMinutes(selected)} minutes</dd>
            </div>
            <div>
              <dt>Reported reserved labor</dt>
              <dd>{formatExact(selected.workerMinutes)} worker-minutes</dd>
            </div>
            <div>
              <dt>Reported standard capacity</dt>
              <dd>{formatExact(selected.standardMinutes)} standard worker-minutes</dd>
            </div>
          </dl>
          <Notice>
            Verified synthetic allocation. No drag-and-drop editing or inferred machine
            availability.
          </Notice>
        </Modal>
      )}
    </div>
  );
}
