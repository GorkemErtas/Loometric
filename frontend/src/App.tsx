import { Layout, useRoute } from "./layout/Layout";
import { Capacity } from "./pages/Capacity";
import { Jobs } from "./pages/Jobs";
import { Orders } from "./pages/Orders";
import { Overview } from "./pages/Overview";
import { Resources } from "./pages/Resources";
import { Scenarios } from "./pages/Scenarios";
import { Scheduling } from "./pages/Scheduling";
import { System } from "./pages/System";
import { PlanningProvider } from "./state/PlanningWorkspace";
import { useWorkspace, WorkspaceProvider } from "./state/Workspace";

export function Workspace() {
  const route = useRoute();
  const { dataset, sessionId } = useWorkspace();
  return (
    <PlanningProvider key={`${dataset?.key ?? "empty"}:${sessionId}`}>
      <Layout route={route}>
        <div key={`${route}:${dataset?.key ?? "empty"}`}>
          {route === "overview" ? (
            <Overview />
          ) : route === "orders" ? (
            <Orders />
          ) : route === "resources" ? (
            <Resources />
          ) : route === "capacity" ? (
            <Capacity />
          ) : route === "scheduling" ? (
            <Scheduling />
          ) : route === "scenarios" ? (
            <Scenarios />
          ) : route === "jobs" ? (
            <Jobs />
          ) : (
            <System />
          )}
        </div>
      </Layout>
    </PlanningProvider>
  );
}
export function App() {
  return (
    <WorkspaceProvider>
      <Workspace />
    </WorkspaceProvider>
  );
}
