import { Layout, useRoute } from "./layout/Layout";
import { Capacity } from "./pages/Capacity";
import { Orders } from "./pages/Orders";
import { Overview } from "./pages/Overview";
import { Resources } from "./pages/Resources";
import { System } from "./pages/System";
import { useWorkspace, WorkspaceProvider } from "./state/Workspace";

export function Workspace() {
  const route = useRoute();
  const { dataset } = useWorkspace();
  return (
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
        ) : (
          <System />
        )}
      </div>
    </Layout>
  );
}
export function App() {
  return (
    <WorkspaceProvider>
      <Workspace />
    </WorkspaceProvider>
  );
}
