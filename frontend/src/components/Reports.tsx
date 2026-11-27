import type { ReactNode } from "react";
import { visualPercent } from "../domain/exact";
import type { CapacityReport } from "../domain/models";
import { useI18n } from "../i18n/I18n";
import { useWorkspace } from "../state/Workspace";
import { Badge, Empty, ErrorNotice, Panel } from "./ui";

export function CapacityContent({ children }: { children: (report: CapacityReport) => ReactNode }) {
  const { t } = useI18n();

  const { capacity, status, error, mode, refresh, health } = useWorkspace();
  if (status === "loading")
    return (
      <div className="loading-state" role="status">
        <span className="spinner" />
        {t("Loading the local capacity report…")}
      </div>
    );
  if (error)
    return (
      <>
        <ErrorNotice error={error} />
        <div className="inline-actions">
          {health && (
            <button type="button" className="button" onClick={refresh}>
              {t("Retry capacity request")}
            </button>
          )}
          <span>{t("Use Configure API to connect or replace the session.")}</span>
        </div>
      </>
    );
  if (!capacity)
    return (
      <Empty title={t("No capacity report loaded")}>
        {mode === "api"
          ? t("Connect the local API to request a report for the selected dataset.")
          : t("This input has no saved capacity preview. Connect the local API to assess it.")}
      </Empty>
    );
  return children(capacity);
}
export function CapacityBars({ report }: { report: CapacityReport }) {
  const { t, formatExact } = useI18n();

  return (
    <figure className="capacity-figure">
      <figcaption className="chart-legend">
        <span>
          <i className="legend-dot" />
          {t("Available elapsed minutes")}
        </span>
        <span>
          <i className="legend-dot legend-muted" />
          {t("Blocked minutes")}
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
              <span>
                {" "}
                / {formatExact(slot.gross)} {t("min")}
              </span>
            </div>
          </div>
        ))}
      </div>
      <p className="chart-note">
        {t(
          "Each bar is one assignment’s available / gross elapsed minutes. These slots are not allocated to orders.",
        )}
      </p>
    </figure>
  );
}
export function Provenance() {
  const { t, backendText } = useI18n();

  const { dataset, mode, requestId, capacity } = useWorkspace();
  if (!dataset) return null;
  return (
    <Panel
      title={t("Data provenance")}
      action={
        <Badge>
          {mode === "preview"
            ? t("Bundled fixture")
            : capacity
              ? t("API response")
              : t("Input only · no API report")}
        </Badge>
      }
    >
      <dl className="provenance-grid">
        <div>
          <dt>{t("Source input")}</dt>
          <dd>
            <code>
              {dataset.validatedFingerprint
                ? t("Local user workspace · exact serialized input (LF)")
                : dataset.sourceFile}
            </code>
          </dd>
        </div>
        <div>
          <dt>{t("Scenario ID")}</dt>
          <dd>{dataset.planning.id}</dd>
        </div>
        <div className="full-width">
          <dt>{t("Source SHA-256 (LF-normalized text)")}</dt>
          <dd>
            <code>{dataset.sourceHash}</code>
          </dd>
        </div>
        {requestId && (
          <div className="full-width">
            <dt>{t("Capacity request ID")}</dt>
            <dd>
              <code>{requestId}</code>
            </dd>
          </div>
        )}
      </dl>
      <details className="details-block">
        <summary>
          {t("Planning assumptions ({p0})", { p0: dataset.planning.assumptions.length })}
        </summary>
        <ul>
          {dataset.planning.assumptions.map((value) => (
            <li key={value}>{dataset.validatedFingerprint ? value : backendText(value)}</li>
          ))}
        </ul>
      </details>
    </Panel>
  );
}
