import { useState } from "react";
import { CapacityBars, CapacityContent, Provenance } from "../components/Reports";
import { Badge, Empty, Notice, Panel, Stat, TableScroll } from "../components/ui";
import { formatExact, sumExact } from "../domain/exact";
import type { CapacityReport } from "../domain/models";

function CapacityDetails({ report }: { report: CapacityReport }) {
  const [order, setOrder] = useState("");
  const [compatibleOnly, setCompatibleOnly] = useState(true);
  const assessments = report.assessments.filter(
    (item) => (!order || item.orderId === order) && (!compatibleOnly || item.compatible),
  );
  return (
    <>
      <div className="stat-grid stat-grid-three">
        <Stat
          label="Available elapsed time"
          value={formatExact(sumExact(report.slots.map((slot) => slot.available)))}
          unit="minutes"
          detail="Sum across unique assignment slots"
        />
        <Stat
          label="Available crew time"
          value={formatExact(sumExact(report.slots.map((slot) => slot.workerMinutes)))}
          unit="worker-minutes"
          detail="Available time × declared workers (M02)"
        />
        <Stat
          label="Effective standard capacity"
          value={formatExact(sumExact(report.slots.map((slot) => slot.standardMinutes)))}
          unit="standard worker-minutes"
          detail="Reported capacity using assumed efficiency"
        />
      </div>
      <Panel
        title="Capacity by assignment"
        description="Available time after the union of declared blocked intervals"
        action={<Badge tone="teal">{report.status}</Badge>}
      >
        <CapacityBars report={report} />
        <TableScroll label="Capacity report scrollable table">
          <table>
            <thead>
              <tr>
                <th scope="col">Assignment / line</th>
                <th scope="col">Stage / shift</th>
                <th scope="col" className="numeric">
                  Crew
                </th>
                <th scope="col" className="numeric">
                  Available min
                </th>
                <th scope="col" className="numeric">
                  Worker-min
                </th>
                <th scope="col" className="numeric">
                  Standard worker-min
                </th>
                <th scope="col" className="numeric">
                  Blocked min
                </th>
              </tr>
            </thead>
            <tbody>
              {report.slots.map((slot) => (
                <tr key={slot.id}>
                  <th scope="row">
                    <span className="cell-primary">{slot.id}</span>
                    <span className="cell-secondary">{slot.lineId}</span>
                  </th>
                  <td>
                    <span className="cell-primary">{slot.stage}</span>
                    <span className="cell-secondary">{slot.shiftId}</span>
                  </td>
                  <td className="numeric">{formatExact(slot.workers)}</td>
                  <td className="numeric">{formatExact(slot.available)}</td>
                  <td className="numeric">{formatExact(slot.workerMinutes)}</td>
                  <td className="numeric">{formatExact(slot.standardMinutes)}</td>
                  <td className="numeric">
                    <details className="blocked-details">
                      <summary>{formatExact(slot.blocked)}</summary>
                      <span>Breaks: {formatExact(slot.breaks)} min</span>
                      <span>Additional downtime: {formatExact(slot.downtime)} min</span>
                      <span>Additional unavailable: {formatExact(slot.unavailability)} min</span>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        {report.slots.length === 0 && (
          <Empty title="No capacity slots">This report contains no line–shift assignments.</Empty>
        )}
      </Panel>
      <Panel
        title="Independent output assessments"
        description="Potential pieces for one order stage in one slot, considered in isolation"
      >
        <div className="table-toolbar">
          <label className="inline-field">
            Order
            <select
              aria-label="Filter assessments by order"
              value={order}
              onChange={(event) => setOrder(event.target.value)}
            >
              <option value="">All orders</option>
              {report.orders.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.id}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={compatibleOnly}
              onChange={(event) => setCompatibleOnly(event.target.checked)}
            />
            Compatible routes only
          </label>
          <span className="muted">{assessments.length} assessments</span>
        </div>
        <TableScroll label="Capacity report scrollable table">
          <table>
            <thead>
              <tr>
                <th scope="col">Order / style</th>
                <th scope="col">Stage</th>
                <th scope="col">Slot / line</th>
                <th scope="col" className="numeric">
                  Potential pieces
                </th>
                <th scope="col" className="numeric">
                  Required standard min
                </th>
                <th scope="col">Independent check</th>
              </tr>
            </thead>
            <tbody>
              {assessments.map((item) => (
                <tr key={`${item.orderId}:${item.stage}:${item.slotId}`}>
                  <th scope="row">
                    <span className="cell-primary">{item.orderId}</span>
                    <span className="cell-secondary">{item.styleId}</span>
                  </th>
                  <td>{item.stage}</td>
                  <td>
                    <span className="cell-primary">{item.slotId}</span>
                    <span className="cell-secondary">{item.lineId}</span>
                  </td>
                  <td className="numeric">
                    {item.potentialUnits === null ? (
                      <span className="muted">Not applicable</span>
                    ) : (
                      formatExact(item.potentialUnits)
                    )}
                  </td>
                  <td className="numeric">{formatExact(item.requiredStandard)}</td>
                  <td>
                    <Badge tone={item.independentFeasible ? "teal" : "amber"}>
                      {item.independentFeasible ? "Fits independently" : "Restricted"}
                    </Badge>
                    <span className="cell-secondary">
                      {item.reasons.join(" · ") || "No restriction codes"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        {assessments.length === 0 && (
          <Empty title="No matching assessments">
            Adjust the order or route compatibility filter.
          </Empty>
        )}
      </Panel>
      <Panel
        title="Assessment boundaries"
        description="Independent capacity estimates · no allocation performed"
      >
        <ul className="limitation-list">
          {report.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Panel>
    </>
  );
}
export function Capacity() {
  return (
    <div className="page-stack">
      <Notice>
        <strong>Independent assessment only.</strong> Multiple orders can each appear to fit the
        same slot. Potential outputs must not be added together or interpreted as a globally
        feasible schedule.
      </Notice>
      <CapacityContent>
        {(report) => <CapacityDetails key={report.scenarioId} report={report} />}
      </CapacityContent>
      <Provenance />
    </div>
  );
}
