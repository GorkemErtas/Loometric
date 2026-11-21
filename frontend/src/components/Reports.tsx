import type { ReactNode } from "react";
import { formatExact, visualPercent } from "../domain/exact";
import type { CapacityReport } from "../domain/models";
import { useWorkspace } from "../state/Workspace";
import { Badge, Empty, ErrorNotice, Panel } from "./ui";

export function CapacityContent({ children }: { children: (report: CapacityReport) => ReactNode }) {
  const { capacity, status, error, mode, refresh, health } = useWorkspace();
  if (status === "loading")
    return (
      <div className="loading-state" role="status">
        <span className="spinner" />
        Loading the local capacity report…
      </div>
    );
  if (error)
    return (
      <>
        <ErrorNotice error={error} />
        <div className="inline-actions">
          {health && (
            <button type="button" className="button" onClick={refresh}>
              Retry capacity request
            </button>
          )}
          <span>Use Configure API to connect or replace the session.</span>
        </div>
      </>
    );
  if (!capacity)
    return (
      <Empty title="No capacity report loaded">
        {mode === "api"
          ? "Connect the local API to request a report for the selected dataset."
          : "Choose a bundled synthetic dataset to inspect its saved report."}
      </Empty>
    );
  return children(capacity);
}
export function CapacityBars({ report }: { report: CapacityReport }) {
  return (
    <figure className="capacity-figure">
      <figcaption className="chart-legend">
        <span>
          <i className="legend-dot" />
          Available elapsed minutes
        </span>
        <span>
          <i className="legend-dot legend-muted" />
          Blocked minutes
        </span>
      </figcaption>
      <div className="capacity-bars">
        {report.slots.map((slot) => (
          <div key={slot.id} className="capacity-bar-row">
            <div>
              <strong>{slot.lineId}</strong>
              <span className="capacity-slot-label">
                {slot.shiftId} · {slot.id}
              </span>
            </div>
            <div className="bar-track" aria-hidden="true">
              <span style={{ width: visualPercent(slot.available, slot.gross) }} />
            </div>
            <div className="bar-value">
              <strong>{formatExact(slot.available)}</strong>
              <span> / {formatExact(slot.gross)} min</span>
            </div>
          </div>
        ))}
      </div>
      <p className="chart-note">
        Each bar is one assignment’s available / gross elapsed minutes. These slots are not
        allocated to orders.
      </p>
    </figure>
  );
}
export function Provenance() {
  const { dataset, mode, requestId, capacity } = useWorkspace();
  if (!dataset) return null;
  return (
    <Panel
      title="Data provenance"
      action={
        <Badge>
          {mode === "preview"
            ? "Bundled fixture"
            : capacity
              ? "API response"
              : "Input only · no API report"}
        </Badge>
      }
    >
      <dl className="provenance-grid">
        <div>
          <dt>Source input</dt>
          <dd>
            <code>{dataset.sourceFile}</code>
          </dd>
        </div>
        <div>
          <dt>Scenario ID</dt>
          <dd>{dataset.planning.id}</dd>
        </div>
        <div className="full-width">
          <dt>Source SHA-256 (LF-normalized text)</dt>
          <dd>
            <code>{dataset.sourceHash}</code>
          </dd>
        </div>
        {requestId && (
          <div className="full-width">
            <dt>Capacity request ID</dt>
            <dd>
              <code>{requestId}</code>
            </dd>
          </div>
        )}
      </dl>
      <details className="details-block">
        <summary>Planning assumptions ({dataset.planning.assumptions.length})</summary>
        <ul>
          {dataset.planning.assumptions.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      </details>
    </Panel>
  );
}
