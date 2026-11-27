import { useState } from "react";
import { CapacityBars, CapacityContent, Provenance } from "../components/Reports";
import { Badge, Empty, Notice, Panel, Stat, TableScroll } from "../components/ui";
import { sumExact } from "../domain/exact";
import type { CapacityReport } from "../domain/models";
import { useI18n } from "../i18n/I18n";

function CapacityDetails({ report }: { report: CapacityReport }) {
  const { t, backendText, codeLabel, formatExact, stageName } = useI18n();

  const [order, setOrder] = useState("");
  const [compatibleOnly, setCompatibleOnly] = useState(true);
  const assessments = report.assessments.filter(
    (item) => (!order || item.orderId === order) && (!compatibleOnly || item.compatible),
  );
  return (
    <>
      <div className="stat-grid stat-grid-three">
        <Stat
          label={t("Available elapsed time")}
          value={formatExact(sumExact(report.slots.map((slot) => slot.available)))}
          unit="minutes"
          detail={t("Sum across unique assignment slots")}
        />
        <Stat
          label={t("Available crew time")}
          value={formatExact(sumExact(report.slots.map((slot) => slot.workerMinutes)))}
          unit="worker-minutes"
          detail={t("Available time × declared workers")}
        />
        <Stat
          label={t("Effective standard capacity")}
          value={formatExact(sumExact(report.slots.map((slot) => slot.standardMinutes)))}
          unit={t("standard worker-minutes")}
          detail={t("Reported capacity using assumed efficiency")}
        />
      </div>
      <Panel
        title={t("Capacity by assignment")}
        description={t("Available time after the union of declared blocked intervals")}
        action={<Badge tone="teal">{codeLabel(report.status)}</Badge>}
      >
        <CapacityBars report={report} />
        <TableScroll label={t("Capacity report scrollable table")}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("Assignment / line")}</th>
                <th scope="col">{t("Stage / shift")}</th>
                <th scope="col" className="numeric">
                  {t("Crew")}
                </th>
                <th scope="col" className="numeric">
                  {t("Available min")}
                </th>
                <th scope="col" className="numeric">
                  {t("Worker-min")}
                </th>
                <th scope="col" className="numeric">
                  {t("Standard worker-min")}
                </th>
                <th scope="col" className="numeric">
                  {t("Blocked min")}
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
                    <span className="cell-primary">{stageName(slot.stage)}</span>
                    <span className="cell-secondary">{slot.shiftId}</span>
                  </td>
                  <td className="numeric">{formatExact(slot.workers)}</td>
                  <td className="numeric">{formatExact(slot.available)}</td>
                  <td className="numeric">{formatExact(slot.workerMinutes)}</td>
                  <td className="numeric">{formatExact(slot.standardMinutes)}</td>
                  <td className="numeric">
                    <details className="blocked-details">
                      <summary>{formatExact(slot.blocked)}</summary>
                      <span>{t("Breaks: {p0} min", { p0: formatExact(slot.breaks) })}</span>
                      <span>
                        {t("Additional downtime: {p0} min", { p0: formatExact(slot.downtime) })}
                      </span>
                      <span>
                        {t("Additional unavailable: {p0} min", {
                          p0: formatExact(slot.unavailability),
                        })}
                      </span>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        {report.slots.length === 0 && (
          <Empty title={t("No capacity slots")}>
            {t("This report contains no line–shift assignments.")}
          </Empty>
        )}
      </Panel>
      <Panel
        title={t("Independent output assessments")}
        description={t("Potential pieces for one order stage in one slot, considered in isolation")}
      >
        <div className="table-toolbar">
          <label className="inline-field">
            {t("Order")}
            <select
              aria-label={t("Filter assessments by order")}
              value={order}
              onChange={(event) => setOrder(event.target.value)}
            >
              <option value="">{t("All orders")}</option>
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
            {t("Compatible routes only")}
          </label>
          <span className="muted">{t("{p0} assessments", { p0: assessments.length })}</span>
        </div>
        <TableScroll label={t("Capacity report scrollable table")}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("Order / style")}</th>
                <th scope="col">{t("Stage")}</th>
                <th scope="col">{t("Slot / line")}</th>
                <th scope="col" className="numeric">
                  {t("Potential pieces")}
                </th>
                <th scope="col" className="numeric">
                  {t("Required standard min")}
                </th>
                <th scope="col">{t("Independent check")}</th>
              </tr>
            </thead>
            <tbody>
              {assessments.map((item) => (
                <tr key={`${item.orderId}:${stageName(item.stage)}:${item.slotId}`}>
                  <th scope="row">
                    <span className="cell-primary">{item.orderId}</span>
                    <span className="cell-secondary">{item.styleId}</span>
                  </th>
                  <td>{stageName(item.stage)}</td>
                  <td>
                    <span className="cell-primary">{item.slotId}</span>
                    <span className="cell-secondary">{item.lineId}</span>
                  </td>
                  <td className="numeric">
                    {item.potentialUnits === null ? (
                      <span className="muted">{t("Not applicable")}</span>
                    ) : (
                      formatExact(item.potentialUnits)
                    )}
                  </td>
                  <td className="numeric">{formatExact(item.requiredStandard)}</td>
                  <td>
                    <Badge tone={item.independentFeasible ? "teal" : "amber"}>
                      {item.independentFeasible ? t("Fits independently") : t("Restricted")}
                    </Badge>
                    <span className="cell-secondary">
                      {item.reasons.map(codeLabel).join(" · ") || t("No restriction codes")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        {assessments.length === 0 && (
          <Empty title={t("No matching assessments")}>
            {t("Adjust the order or route compatibility filter.")}
          </Empty>
        )}
      </Panel>
      <Panel
        title={t("Assessment boundaries")}
        description={t("Independent capacity estimates · no allocation performed")}
      >
        <ul className="limitation-list">
          {report.limitations.map((item) => (
            <li key={item}>{backendText(item)}</li>
          ))}
        </ul>
      </Panel>
    </>
  );
}
export function Capacity() {
  const { t } = useI18n();

  return (
    <div className="page-stack">
      <Notice>
        <strong>{t("Independent assessment only.")}</strong>{" "}
        {t(
          "Multiple orders can each appear to fit the same slot. Potential outputs must not be added together or interpreted as a globally feasible schedule.",
        )}
      </Notice>
      <CapacityContent>
        {(report) => <CapacityDetails key={report.scenarioId} report={report} />}
      </CapacityContent>
      <Provenance />
    </div>
  );
}
