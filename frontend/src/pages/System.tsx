import { Badge, Empty, ErrorNotice, Notice, Panel } from "../components/ui";
import { useI18n } from "../i18n/I18n";

import { useWorkspace } from "../state/Workspace";

export function System() {
  const { t, backendText, codeLabel } = useI18n();

  const { mode, status, origin, health, capabilities, error, enterPreview, refresh } =
    useWorkspace();
  return (
    <div className="page-stack">
      <div className="two-columns">
        <Panel
          title={t("Local API session")}
          description={t("Actual responses from the configured loopback backend")}
          action={
            <Badge tone={status === "connected" ? "teal" : status === "error" ? "red" : "neutral"}>
              {codeLabel(status)}
            </Badge>
          }
        >
          <dl className="context-list">
            <div>
              <dt>{t("Data mode")}</dt>
              <dd>{mode === "preview" ? t("Explicit fixture preview") : t("Local API")}</dd>
            </div>
            <div>
              <dt>{t("API origin")}</dt>
              <dd>{origin ?? t("Not connected")}</dd>
            </div>
            <div>
              <dt>{t("Health response")}</dt>
              <dd>
                {health
                  ? t("{p0} · last successful check", { p0: codeLabel(health.status) })
                  : t("Not checked")}
              </dd>
            </div>
            <div>
              <dt>{t("API version")}</dt>
              <dd>{health?.version ?? t("Not loaded")}</dd>
            </div>
            <div>
              <dt>{t("Credential storage")}</dt>
              <dd>{t("Tab memory only")}</dd>
            </div>
          </dl>
          {status === "loading" && (
            <p role="status" className="panel-body">
              {t("Checking the backend and loading capacity…")}
            </p>
          )}
          {error && <ErrorNotice error={error} />}
          <div className="panel-actions">
            {mode === "api" && (
              <button className="button" type="button" onClick={enterPreview}>
                {t("Clear session & use fixture preview")}
              </button>
            )}
            {status === "connected" && (
              <button className="button" type="button" onClick={refresh}>
                {t("Refresh capacity report")}
              </button>
            )}
          </div>
        </Panel>
        <Panel title={t("Workspace boundaries")} description={t("Local-only workspace")}>
          <div className="boundary-list">
            <div>
              <IconText
                label={t("Planning & capacity")}
                detail={t("Independent assessment reports")}
              />
            </div>
            <div>
              <IconText
                label={t("Existing schedule inspection")}
                detail={t("Explicit read-only verification; no solver run")}
              />
            </div>
            <div>
              <IconText
                label={t("Productivity prediction")}
                detail={t("Real-data research remains offline; synthetic predictions are separate")}
              />
            </div>
            <div>
              <IconText
                label={t("Interactive scheduling & what-if")}
                detail={t("Available in dedicated scheduling, scenarios and jobs views")}
              />
            </div>
          </div>
        </Panel>
      </div>
      {capabilities ? (
        <>
          <Panel
            title={t("Reported capabilities")}
            description={t("Loaded from GET /api/v1/capabilities")}
          >
            <dl className="context-list">
              <div>
                <dt>{t("Policy versions")}</dt>
                <dd>{capabilities.policies.join(", ")}</dd>
              </div>
              <div>
                <dt>{t("Backend operations")}</dt>
                <dd>{capabilities.operations.map(codeLabel).join(", ")}</dd>
              </div>
              <div>
                <dt>{t("Synchronous scheduling methods")}</dt>
                <dd>{capabilities.methods.map(codeLabel).join(", ")}</dd>
              </div>
              <div>
                <dt>{t("Prediction availability")}</dt>
                <dd>{backendText(capabilities.prediction)}</dd>
              </div>
            </dl>
            <Notice>
              {t(
                "Backend capabilities describe the API. Planning, scenarios, jobs and experimental predictions are available in their dedicated views.",
              )}
            </Notice>
          </Panel>
          <Panel
            title={t("Synchronous execution limits")}
            description={t("Exact integer values returned by the current backend")}
          >
            <LimitTable values={capabilities.limits} />
          </Panel>
          <Panel
            title={t("Bounded job limits")}
            description={t(
              "Server metadata; dedicated job views submit, track and cancel bounded work",
            )}
          >
            <LimitTable values={capabilities.jobLimits} />
          </Panel>
          <Panel title={t("Backend limitations")}>
            <ul className="limitation-list">
              {capabilities.limitations.map((item) => (
                <li key={item}>{backendText(item)}</li>
              ))}
            </ul>
          </Panel>
        </>
      ) : (
        <Panel title={t("Backend capabilities")}>
          <Empty title={t("Capabilities not loaded")}>
            {t(
              "Configure a local API session to inspect the actual server limits and supported operations.",
            )}
          </Empty>
        </Panel>
      )}
    </div>
  );
}
function IconText({ label, detail }: { label: string; detail: string }) {
  const { label: textLabel } = useI18n();

  return (
    <>
      <strong>{textLabel(String(label))}</strong>
      <p>{detail}</p>
    </>
  );
}
function LimitTable({ values }: { values: { name: string; value: string }[] }) {
  const { label: textLabel, formatExact } = useI18n();

  return (
    <div className="limit-grid">
      {values.map((item) => (
        <div key={textLabel(item.name)}>
          <code>{textLabel(item.name)}</code>
          <strong>{formatExact(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}
