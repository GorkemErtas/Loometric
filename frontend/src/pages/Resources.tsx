import { Badge, Empty, Notice, Panel, TableScroll } from "../components/ui";
import { useI18n } from "../i18n/I18n";

import { useWorkspace } from "../state/Workspace";

export function Resources() {
  const { t, backendText, codeLabel, formatExact, percentExact, dateLabel, clockLabel, stageName } =
    useI18n();

  const { dataset } = useWorkspace();
  if (!dataset)
    return (
      <Empty title={t("No resources loaded")}>{t("Choose a bundled planning dataset.")}</Empty>
    );
  const planning = dataset.planning;
  return (
    <div className="page-stack">
      <Notice>
        {t(
          "Crews and efficiency are declared synthetic planning assumptions. Available time is a capacity input; allocated work appears only in an explicitly loaded verified schedule.",
        )}
      </Notice>
      <div className="resource-grid">
        {planning.lines.map((line) => (
          <Panel
            key={line.id}
            title={line.id}
            description={stageName(line.stage)}
            action={
              <Badge tone={line.availability === "available" ? "teal" : "amber"}>
                {codeLabel(line.availability)}
              </Badge>
            }
          >
            <div className="line-crew">
              <strong>{formatExact(line.workers)}</strong>
              <span>{t("declared workers")}</span>
            </div>
            <div className="resource-section">
              <h3>{t("Line–style capabilities")}</h3>
              {planning.capabilities
                .filter((item) => item.lineId === line.id)
                .map((item) => (
                  <div className="capability-row" key={item.id}>
                    <Badge>{item.styleId}</Badge>
                    <span>
                      {stageName(item.stage)} ·{" "}
                      {dataset.validatedFingerprint ? item.basis : backendText(item.basis)}
                    </span>
                    <small>{item.id}</small>
                  </div>
                ))}
            </div>
            <div className="resource-section">
              <h3>{t("Capacity profiles")}</h3>
              {planning.profiles
                .filter((profile) => profile.lineId === line.id)
                .map((profile) => (
                  <div key={profile.id} className="profile-row">
                    <div>
                      <strong>{percentExact(profile.efficiency)}</strong>
                      <span>{t("assumed efficiency")}</span>
                    </div>
                    <p>
                      {t("{p0} · effective {p1}", {
                        p0: profile.id,
                        p1: dateLabel(profile.effectiveDate),
                      })}
                    </p>
                    <small>
                      {profile.source} · {codeLabel(profile.evidence)}
                    </small>
                  </div>
                ))}
            </div>
            <div className="resource-section">
              <h3>{t("Assignments")}</h3>
              {planning.assignments
                .filter((assignment) => assignment.lineId === line.id)
                .map((assignment) => (
                  <div key={assignment.id} className="assignment-row">
                    <strong>{assignment.shiftId}</strong>
                    <span>{assignment.id}</span>
                    <small>{t("Profile: {p0}", { p0: assignment.profileId })}</small>
                  </div>
                ))}
            </div>
          </Panel>
        ))}
      </div>
      {planning.lines.length === 0 && (
        <Empty title={t("No production lines")}>{t("No lines are declared in this input.")}</Empty>
      )}
      <Panel
        title={t("Shift calendar")}
        description={t(
          "Input intervals with explicit timezone offsets; no browser timezone conversion",
        )}
      >
        <TableScroll label={t("Shift calendar scrollable table")}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("Shift")}</th>
                <th scope="col">{t("Start")}</th>
                <th scope="col">{t("End")}</th>
                <th scope="col">{t("Declared breaks")}</th>
              </tr>
            </thead>
            <tbody>
              {planning.shifts.map((shift) => (
                <tr key={shift.id}>
                  <th scope="row">{shift.id}</th>
                  <td>{clockLabel(shift.start)}</td>
                  <td>{clockLabel(shift.end)}</td>
                  <td>
                    {shift.breaks.length
                      ? shift.breaks.map((item) => (
                          <div key={item.start}>
                            {clockLabel(item.start)} → {clockLabel(item.end)}
                          </div>
                        ))
                      : "None declared"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
      </Panel>
      <div className="two-columns">
        <Panel
          title={t("Planned downtime")}
          description={t("References a specific line–shift assignment")}
        >
          <div className="stop-list">
            {planning.downtime.map((stop) => (
              <div key={stop.id}>
                <Badge tone="amber">{stop.id}</Badge>
                <strong>
                  {dataset.validatedFingerprint ? stop.reason : backendText(stop.reason)}
                </strong>
                <p>{stop.reference}</p>
                <small>
                  {clockLabel(stop.start)} → {clockLabel(stop.end)}
                </small>
              </div>
            ))}
          </div>
          {planning.downtime.length === 0 && (
            <Empty title={t("No planned downtime")}>
              {t("No downtime intervals are declared.")}
            </Empty>
          )}
        </Panel>
        <Panel
          title={t("Line unavailability")}
          description={t("Input restrictions, not measured production losses")}
        >
          <div className="stop-list">
            {planning.unavailability.map((stop) => (
              <div key={stop.id}>
                <Badge>{stop.reference}</Badge>
                <strong>
                  {dataset.validatedFingerprint ? stop.reason : backendText(stop.reason)}
                </strong>
                <p>{stop.id}</p>
                <small>
                  {clockLabel(stop.start)} → {clockLabel(stop.end)}
                </small>
              </div>
            ))}
          </div>
          {planning.unavailability.length === 0 && (
            <Empty title={t("No unavailable periods")}>
              {t("No additional unavailable intervals are declared.")}
            </Empty>
          )}
        </Panel>
      </div>
    </div>
  );
}
