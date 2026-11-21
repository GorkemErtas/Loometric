import { Badge, Empty, Notice, Panel, TableScroll } from "../components/ui";
import { clockLabel, dateLabel, formatExact, percentExact, stageName } from "../domain/exact";
import { useWorkspace } from "../state/Workspace";

export function Resources() {
  const { dataset } = useWorkspace();
  if (!dataset)
    return <Empty title="No resources loaded">Choose a bundled planning dataset.</Empty>;
  const planning = dataset.planning;
  return (
    <div className="page-stack">
      <Notice>
        Crews and efficiency are declared synthetic planning assumptions. Available time is a
        capacity input; allocated work appears only in an explicitly loaded verified schedule.
      </Notice>
      <div className="resource-grid">
        {planning.lines.map((line) => (
          <Panel
            key={line.id}
            title={line.id}
            description={stageName(line.stage)}
            action={
              <Badge tone={line.availability === "available" ? "teal" : "amber"}>
                {line.availability}
              </Badge>
            }
          >
            <div className="line-crew">
              <strong>{formatExact(line.workers)}</strong>
              <span>declared workers</span>
            </div>
            <div className="resource-section">
              <h3>Line–style capabilities</h3>
              {planning.capabilities
                .filter((item) => item.lineId === line.id)
                .map((item) => (
                  <div className="capability-row" key={item.id}>
                    <Badge>{item.styleId}</Badge>
                    <span>
                      {item.stage} · {item.basis}
                    </span>
                    <small>{item.id}</small>
                  </div>
                ))}
            </div>
            <div className="resource-section">
              <h3>Capacity profiles</h3>
              {planning.profiles
                .filter((profile) => profile.lineId === line.id)
                .map((profile) => (
                  <div key={profile.id} className="profile-row">
                    <div>
                      <strong>{percentExact(profile.efficiency)}</strong>
                      <span>assumed efficiency</span>
                    </div>
                    <p>
                      {profile.id} · effective {dateLabel(profile.effectiveDate)}
                    </p>
                    <small>
                      {profile.source} · {profile.evidence}
                    </small>
                  </div>
                ))}
            </div>
            <div className="resource-section">
              <h3>Assignments</h3>
              {planning.assignments
                .filter((assignment) => assignment.lineId === line.id)
                .map((assignment) => (
                  <div key={assignment.id} className="assignment-row">
                    <strong>{assignment.shiftId}</strong>
                    <span>{assignment.id}</span>
                    <small>Profile: {assignment.profileId}</small>
                  </div>
                ))}
            </div>
          </Panel>
        ))}
      </div>
      {planning.lines.length === 0 && (
        <Empty title="No production lines">No lines are declared in this input.</Empty>
      )}
      <Panel
        title="Shift calendar"
        description="Input intervals with explicit timezone offsets; no browser timezone conversion"
      >
        <TableScroll label="Shift calendar scrollable table">
          <table>
            <thead>
              <tr>
                <th scope="col">Shift</th>
                <th scope="col">Start</th>
                <th scope="col">End</th>
                <th scope="col">Declared breaks</th>
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
        <Panel title="Planned downtime" description="References a specific line–shift assignment">
          <div className="stop-list">
            {planning.downtime.map((stop) => (
              <div key={stop.id}>
                <Badge tone="amber">{stop.id}</Badge>
                <strong>{stop.reason}</strong>
                <p>{stop.reference}</p>
                <small>
                  {clockLabel(stop.start)} → {clockLabel(stop.end)}
                </small>
              </div>
            ))}
          </div>
          {planning.downtime.length === 0 && (
            <Empty title="No planned downtime">No downtime intervals are declared.</Empty>
          )}
        </Panel>
        <Panel
          title="Line unavailability"
          description="Input restrictions, not measured production losses"
        >
          <div className="stop-list">
            {planning.unavailability.map((stop) => (
              <div key={stop.id}>
                <Badge>{stop.reference}</Badge>
                <strong>{stop.reason}</strong>
                <p>{stop.id}</p>
                <small>
                  {clockLabel(stop.start)} → {clockLabel(stop.end)}
                </small>
              </div>
            ))}
          </div>
          {planning.unavailability.length === 0 && (
            <Empty title="No unavailable periods">
              No additional unavailable intervals are declared.
            </Empty>
          )}
        </Panel>
      </div>
    </div>
  );
}
