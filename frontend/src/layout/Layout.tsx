import { type FormEvent, useEffect, useState } from "react";
import { Badge, Icon, Modal } from "../components/ui";
import { useI18n } from "../i18n/I18n";
import { usePlanning } from "../state/PlanningWorkspace";
import { useWorkspace } from "../state/Workspace";

export const routes = [
  {
    key: "predictions",
    label: "AI Predictions",
    description:
      "Run experimental synthetic ML models, compare a baseline and explore planned conditions.",
  },
  {
    key: "data",
    label: "Production data",
    description: "Build, validate and exchange your own synthetic production inputs.",
  },
  {
    key: "overview",
    label: "Overview",
    description: "A clear view of your planning inputs and available capacity.",
  },
  {
    key: "orders",
    label: "Orders",
    description: "Inspect demand, delivery dates and declared production routes.",
  },
  {
    key: "resources",
    label: "Production resources",
    description: "Understand the people, lines and time behind each capacity slot.",
  },
  {
    key: "capacity",
    label: "Capacity",
    description: "Explore independent order-stage-slot assessments.",
  },
  {
    key: "scheduling",
    label: "Production scheduling",
    description: "Run the reference scheduler and inspect verified production allocations.",
  },
  {
    key: "scenarios",
    label: "What-if scenarios",
    description: "Review explicit capacity assumptions and compare verified same-demand results.",
  },
  {
    key: "jobs",
    label: "Optimization jobs",
    description: "Track bounded jobs, cancel explicitly and inspect verified solver evidence.",
  },
  {
    key: "system",
    label: "API & system",
    description: "Inspect the local connection, capabilities and execution boundaries.",
  },
] as const;
export type Route = (typeof routes)[number]["key"];
const readRoute = (): Route =>
  routes.find((item) => `#/${item.key}` === window.location.hash)?.key ?? "overview";
export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(readRoute);
  useEffect(() => {
    const changed = () => setRoute(readRoute());
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  return route;
}
function ConnectionDialog({ onClose }: { onClose: () => void }) {
  const { t, formValidation } = useI18n();

  const { connect, origin } = useWorkspace();
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const address = String(values.get("origin") ?? "");
    const token = String(values.get("token") ?? "");
    form.reset();
    onClose();
    void connect(address, token);
  };
  return (
    <Modal title={t("Connect to local API")} onClose={onClose}>
      <p>
        {t(
          "Enter the local API origin, or this site's configured HTTPS origin, and your session token.",
        )}
      </p>
      <form {...formValidation} onSubmit={submit} className="form-stack" autoComplete="off">
        <label>
          {t("API origin")}
          <input
            name="origin"
            type="url"
            defaultValue={
              origin ??
              (window.location.protocol === "https:"
                ? window.location.origin
                : "http://127.0.0.1:8000")
            }
            required
            spellCheck={false}
          />
        </label>
        <label>
          {t("Bearer token")}
          <input
            name="token"
            type="password"
            autoComplete="off"
            required
            minLength={32}
            maxLength={128}
            pattern="[A-Za-z0-9_-]+"
            spellCheck={false}
            aria-describedby="token-help"
          />
        </label>
        <p className="field-help" id="token-help">
          {t(
            "Kept in this tab’s memory only. Reloading or clearing the session removes it. Use a literal localhost/127.0.0.1 origin, or the current HTTPS site. Credentials stay in memory.",
          )}
        </p>
        <div className="modal-actions">
          <button type="button" className="button" onClick={onClose}>
            {t("Cancel")}
          </button>
          <button className="button button-primary" type="submit">
            {t("Connect & load capacity")}
          </button>
        </div>
      </form>
    </Modal>
  );
}
export function Layout({ route, children }: { route: Route; children: React.ReactNode }) {
  const { t, locale, setLocale, label: textLabel } = useI18n();

  const { catalog, dataset, mode, status, selectDataset } = useWorkspace();
  const { jobs } = usePlanning();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [connectionOpen, setConnectionOpen] = useState(false);
  const current = routes.find((item) => item.key === route) ?? routes[0];
  const currentLabel = t(current.label);
  useEffect(() => {
    document.title = `${currentLabel} · Loometric`;
  }, [currentLabel]);
  useEffect(() => {
    if (!route) return;
    document.getElementById("workspace-content")?.focus({ preventScroll: true });
  }, [route]);
  const label =
    status === "loading"
      ? "Connecting / loading"
      : status === "error"
        ? "Connection needs attention"
        : mode === "api"
          ? "Local API response loaded"
          : "API disconnected";
  return (
    <div className="app-shell">
      <button
        type="button"
        className="skip-link"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("workspace-content")?.focus({ preventScroll: true });
        }}
      >
        {t("Skip to content")}
      </button>
      <aside
        id="workspace-navigation"
        className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}
        aria-label={t("Workspace navigation")}
      >
        <a className="brand" href="/#/overview">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
          </span>
          <span>
            Loometric<span className="brand-sub">{t("PRODUCTION INTELLIGENCE")}</span>
          </span>
        </a>
        <div className="nav-section-label">{t("WORKSPACE")}</div>
        <nav aria-label={t("Main navigation")}>
          {routes.map((item) => (
            <a
              key={item.key}
              href={`/#/${item.key}`}
              className={`nav-link ${route === item.key ? "active" : ""}`}
              aria-current={route === item.key ? "page" : undefined}
              onClick={() => setMobileOpen(false)}
            >
              <Icon name={item.key} />
              {textLabel(item.label)}
              {route === item.key && <span className="nav-current" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="local-dot" /> {t("LOCAL WORKSPACE")}
          <p>
            {t("Synthetic planning data")}
            <br />
            {t("Production data workspace")}
          </p>
          <span className="sidebar-version">{t("No live factory connection")}</span>
        </div>
      </aside>
      <div className="workspace-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button menu-toggle"
              aria-label={t("Toggle navigation")}
              aria-controls="workspace-navigation"
              aria-expanded={mobileOpen}
              type="button"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              <Icon name="menu" />
            </button>
            <span>{t("Workspace")}</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{textLabel(current.label)}</strong>
          </div>
          <div className="topbar-right">
            <fieldset className="language-selector" aria-label={t("Language")}>
              {(
                [
                  ["tr-TR", "TR", "Türkçe"],
                  ["en-US", "EN", "English"],
                ] as const
              ).map(([value, short, name]) => (
                <button
                  key={value}
                  type="button"
                  lang={value}
                  aria-label={name}
                  aria-pressed={locale === value}
                  onClick={() => setLocale(value)}
                >
                  {short}
                </button>
              ))}
            </fieldset>
            <span
              className={`connection-label ${status === "error" ? "connection-error" : ""}`}
              role="status"
            >
              <span
                className={`status-dot ${mode === "api" && status === "connected" ? "status-ok" : ""}`}
              />
              {textLabel(label)}
            </span>
            <button
              className="button button-small"
              type="button"
              onClick={() => setConnectionOpen(true)}
            >
              <Icon name="link" size={15} />
              {t("Configure API")}
            </button>
          </div>
        </header>
        <main id="workspace-content" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <div className="eyebrow">{t("PRODUCTION WORKSPACE")}</div>
              <h1>{textLabel(current.label)}</h1>
              <p>{textLabel(current.description)}</p>
            </div>
            <div className="dataset-control">
              <label htmlFor="dataset-select">{t("Planning dataset")}</label>
              <select
                id="dataset-select"
                value={dataset?.key ?? ""}
                onChange={(event) => selectDataset(event.target.value)}
                disabled={catalog.length === 0}
              >
                {catalog.length === 0 && <option value="">{t("No datasets available")}</option>}
                {catalog.map((item) => (
                  <option key={item.key} value={item.key}>
                    {textLabel(item.name)}
                  </option>
                ))}
              </select>
              {jobs.length > 0 && (
                <small className="context-change-warning">
                  {t(
                    "Changing dataset/session discards local job IDs. Copy them first; server jobs may continue.",
                  )}
                </small>
              )}
            </div>
          </div>
          <div className="source-strip">
            <Badge tone="amber">{t("SYNTHETIC")}</Badge>
            <strong>
              {route === "predictions"
                ? t("Experimental ML research")
                : mode === "preview"
                  ? t("Fixture preview")
                  : t("Local API mode")}
            </strong>
            <span>
              {route === "predictions"
                ? t("synthetic-ml-v1 · independent of planning dataset")
                : (dataset?.planning.id ?? t("No dataset selected"))}
            </span>
            <span className="source-strip-end">
              {route === "predictions"
                ? t("NO_ML_PROMOTION")
                : mode === "preview"
                  ? dataset?.previewCapacity
                    ? t("Saved capacity report · explicit demo mode")
                    : t("Input-only preview · connect API for reports")
                  : route === "data"
                    ? t("Synthetic data editor")
                    : ["scheduling", "scenarios", "jobs"].includes(route)
                      ? t("Interactive planning")
                      : t("Read-only inspection")}
            </span>
          </div>
          {children}
          <footer className="page-footer">
            <span>{t("Loometric · Local production planning")}</span>
            <span>
              {t("Inputs, capacity estimates and verified schedules are labeled separately.")}
            </span>
          </footer>
        </main>
      </div>
      {connectionOpen && <ConnectionDialog onClose={() => setConnectionOpen(false)} />}
    </div>
  );
}
