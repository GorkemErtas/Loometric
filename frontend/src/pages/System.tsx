import { Badge, Empty, ErrorNotice, Notice, Panel } from "../components/ui";
import { formatExact } from "../domain/exact";
import { useWorkspace } from "../state/Workspace";

export function System() {
  const { mode, status, origin, health, capabilities, error, enterPreview, refresh } =
    useWorkspace();
  return (
    <div className="page-stack">
      <div className="two-columns">
        <Panel
          title="Local API session"
          description="Actual responses from the configured loopback backend"
          action={
            <Badge tone={status === "connected" ? "teal" : status === "error" ? "red" : "neutral"}>
              {status}
            </Badge>
          }
        >
          <dl className="context-list">
            <div>
              <dt>Data mode</dt>
              <dd>{mode === "preview" ? "Explicit fixture preview" : "Local API"}</dd>
            </div>
            <div>
              <dt>API origin</dt>
              <dd>{origin ?? "Not connected"}</dd>
            </div>
            <div>
              <dt>Health response</dt>
              <dd>{health ? `${health.status} · last successful check` : "Not checked"}</dd>
            </div>
            <div>
              <dt>API version</dt>
              <dd>{health?.version ?? "Not loaded"}</dd>
            </div>
            <div>
              <dt>Credential storage</dt>
              <dd>Tab memory only</dd>
            </div>
          </dl>
          {status === "loading" && (
            <p role="status" className="panel-body">
              Checking the backend and loading capacity…
            </p>
          )}
          {error && <ErrorNotice error={error} />}
          <div className="panel-actions">
            {mode === "api" && (
              <button className="button" type="button" onClick={enterPreview}>
                Clear session & use fixture preview
              </button>
            )}
            {status === "connected" && (
              <button className="button" type="button" onClick={refresh}>
                Refresh capacity report
              </button>
            )}
          </div>
        </Panel>
        <Panel title="Workspace boundaries" description="Local-only M06B workspace">
          <div className="boundary-list">
            <div>
              <IconText label="Planning & capacity" detail="M02 independent assessment reports" />
            </div>
            <div>
              <IconText
                label="Existing schedule inspection"
                detail="Explicit read-only verification; no solver run"
              />
            </div>
            <div>
              <IconText
                label="Productivity prediction"
                detail="M01 remains offline; no live prediction API"
              />
            </div>
            <div>
              <IconText
                label="Interactive scheduling & what-if"
                detail="Available in dedicated scheduling, scenarios and jobs views"
              />
            </div>
          </div>
        </Panel>
      </div>
      {capabilities ? (
        <>
          <Panel title="Reported capabilities" description="Loaded from GET /api/v1/capabilities">
            <dl className="context-list">
              <div>
                <dt>Policy versions</dt>
                <dd>{capabilities.policies.join(", ")}</dd>
              </div>
              <div>
                <dt>Backend operations</dt>
                <dd>{capabilities.operations.join(", ")}</dd>
              </div>
              <div>
                <dt>Synchronous scheduling methods</dt>
                <dd>{capabilities.methods.join(", ")}</dd>
              </div>
              <div>
                <dt>Prediction availability</dt>
                <dd>{capabilities.prediction}</dd>
              </div>
            </dl>
            <Notice>
              Backend capabilities describe the server. This read-only dashboard exposes capacity
              and existing-proposal verification only.
            </Notice>
          </Panel>
          <Panel
            title="Synchronous execution limits"
            description="Exact integer values returned by the current backend"
          >
            <LimitTable values={capabilities.limits} />
          </Panel>
          <Panel
            title="Bounded job limits"
            description="M05B server metadata only; dedicated job views submit, track and cancel bounded work"
          >
            <LimitTable values={capabilities.jobLimits} />
          </Panel>
          <Panel title="Backend limitations">
            <ul className="limitation-list">
              {capabilities.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Panel>
        </>
      ) : (
        <Panel title="Backend capabilities">
          <Empty title="Capabilities not loaded">
            Configure a local API session to inspect the actual server limits and supported
            operations.
          </Empty>
        </Panel>
      )}
    </div>
  );
}
function IconText({ label, detail }: { label: string; detail: string }) {
  return (
    <>
      <strong>{label}</strong>
      <p>{detail}</p>
    </>
  );
}
function LimitTable({ values }: { values: { name: string; value: string }[] }) {
  return (
    <div className="limit-grid">
      {values.map((item) => (
        <div key={item.name}>
          <code>{item.name}</code>
          <strong>{formatExact(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}
