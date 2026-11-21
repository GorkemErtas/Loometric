import { type FormEvent, useEffect, useState } from "react";
import { Badge, Icon, Modal } from "../components/ui";
import { usePlanning } from "../state/PlanningWorkspace";
import { useWorkspace } from "../state/Workspace";

export const routes = [
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
    description: "Explore independent order-stage-slot assessments from M02.",
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
    <Modal title="Connect to local API" onClose={onClose}>
      <p>Start the existing FastAPI server, then enter its local origin and session token.</p>
      <form onSubmit={submit} className="form-stack" autoComplete="off">
        <label>
          API origin
          <input
            name="origin"
            type="url"
            defaultValue={origin ?? "http://127.0.0.1:8000"}
            required
            spellCheck={false}
          />
        </label>
        <label>
          Bearer token
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
          Kept in this tab’s memory only. Reloading or clearing the session removes it. Use a
          literal localhost or 127.0.0.1 origin; frontend port 5173 is required by CORS.
        </p>
        <div className="modal-actions">
          <button type="button" className="button" onClick={onClose}>
            Cancel
          </button>
          <button className="button button-primary" type="submit">
            Connect & load capacity
          </button>
        </div>
      </form>
    </Modal>
  );
}
export function Layout({ route, children }: { route: Route; children: React.ReactNode }) {
  const { catalog, dataset, mode, status, selectDataset } = useWorkspace();
  const { jobs } = usePlanning();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [connectionOpen, setConnectionOpen] = useState(false);
  const current = routes.find((item) => item.key === route) ?? routes[0];
  useEffect(() => {
    document.title = `${current.label} · Loometric`;
    document.getElementById("workspace-content")?.focus({ preventScroll: true });
  }, [current]);
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
        Skip to content
      </button>
      <aside
        id="workspace-navigation"
        className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}
        aria-label="Workspace navigation"
      >
        <a className="brand" href="/#/overview">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
          </span>
          <span>
            Loometric<span className="brand-sub">PRODUCTION INTELLIGENCE</span>
          </span>
        </a>
        <div className="nav-section-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {routes.map((item) => (
            <a
              key={item.key}
              href={`/#/${item.key}`}
              className={`nav-link ${route === item.key ? "active" : ""}`}
              aria-current={route === item.key ? "page" : undefined}
              onClick={() => setMobileOpen(false)}
            >
              <Icon name={item.key} />
              {item.label}
              {route === item.key && <span className="nav-current" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="local-dot" /> LOCAL WORKSPACE
          <p>
            Synthetic planning data
            <br />
            M06B · Planning workspace
          </p>
          <span className="sidebar-version">No live factory connection</span>
        </div>
      </aside>
      <div className="workspace-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button menu-toggle"
              aria-label="Toggle navigation"
              aria-controls="workspace-navigation"
              aria-expanded={mobileOpen}
              type="button"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              <Icon name="menu" />
            </button>
            <span>Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{current.label}</strong>
          </div>
          <div className="topbar-right">
            <span
              className={`connection-label ${status === "error" ? "connection-error" : ""}`}
              role="status"
            >
              <span
                className={`status-dot ${mode === "api" && status === "connected" ? "status-ok" : ""}`}
              />
              {label}
            </span>
            <button
              className="button button-small"
              type="button"
              onClick={() => setConnectionOpen(true)}
            >
              <Icon name="link" size={15} />
              Configure API
            </button>
          </div>
        </header>
        <main id="workspace-content" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <div className="eyebrow">PRODUCTION WORKSPACE</div>
              <h1>{current.label}</h1>
              <p>{current.description}</p>
            </div>
            <div className="dataset-control">
              <label htmlFor="dataset-select">Planning dataset</label>
              <select
                id="dataset-select"
                value={dataset?.key ?? ""}
                onChange={(event) => selectDataset(event.target.value)}
                disabled={catalog.length === 0}
              >
                {catalog.length === 0 && <option value="">No datasets available</option>}
                {catalog.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.name}
                  </option>
                ))}
              </select>
              {jobs.length > 0 && (
                <small className="context-change-warning">
                  Changing dataset/session discards local job IDs. Copy them first; server jobs may
                  continue.
                </small>
              )}
            </div>
          </div>
          <div className="source-strip">
            <Badge tone="amber">SYNTHETIC</Badge>
            <strong>{mode === "preview" ? "Fixture preview" : "Local API mode"}</strong>
            <span>{dataset?.planning.id ?? "No dataset selected"}</span>
            <span className="source-strip-end">
              {mode === "preview"
                ? dataset?.previewCapacity
                  ? "Saved M02 report · explicit demo mode"
                  : "Input-only preview · connect API for reports"
                : ["scheduling", "scenarios", "jobs"].includes(route)
                  ? "M05A / M05B · interactive planning"
                  : "M05A · read-only inspection"}
            </span>
          </div>
          {children}
          <footer className="page-footer">
            <span>Loometric · Local production planning</span>
            <span>Inputs, capacity estimates and verified schedules are labeled separately.</span>
          </footer>
        </main>
      </div>
      {connectionOpen && <ConnectionDialog onClose={() => setConnectionOpen(false)} />}
    </div>
  );
}
