import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import capacityRaw from "../fixtures/capacity-demo.report.json?raw";
import competitionRaw from "../fixtures/competition.capacity.json?raw";
import { App, Workspace } from "../src/App";
import { datasets } from "../src/demo/catalog";
import { object, parseExact } from "../src/domain/json";
import { languageStorageKey } from "../src/i18n/locale";
import { WorkspaceProvider } from "../src/state/Workspace";

const id = "00000000-0000-4000-8000-000000000001";
const response = (data: string) =>
  new Response(`{"api_version":"v1","request_id":"${id}","data":${data}}`);
const capabilities =
  '{"policy_versions":["whole-stage-minute-v1"],"operations":["capacity","verify"],"scheduling_methods":["greedy"],"limits":{"max_orders":32},"optimization_jobs":{"limits":{"max_active_jobs":1}},"limitations":["synthetic only"],"deferred":{"prediction":"M01 offline"}}';
const token = () => crypto.randomUUID().replaceAll("-", "");
async function navigate(route: string) {
  await act(async () => {
    window.location.hash = `/${route}`;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}
async function configure(secret: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Configure API" }));
  await user.type(screen.getByLabelText("Bearer token"), secret);
  await user.click(screen.getByRole("button", { name: "Connect & load capacity" }));
}
beforeEach(() => {
  window.history.replaceState(null, "", "/#/overview");
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("read-only workspace", () => {
  it("shows source counts, unique slots, provenance and no invented scheduling metrics", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
    expect(screen.getByText("480")).toBeVisible();
    expect(screen.getByText("SYNTHETIC")).toBeVisible();
    expect(screen.getByText("Fixture preview")).toBeVisible();
    expect(screen.getByText("No schedule outcome loaded")).toBeVisible();
    expect(screen.queryByText("Completed units")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".capacity-bar-row")).toHaveLength(6);
    expect(document.querySelector(".bar-track span")?.getAttribute("style")).toMatch(
      /width: \d+(\.\d+)?%;/,
    );
    expect(screen.getByText("examples/planning/capacity-demo.json")).toBeVisible();
  });
  it("searches, sorts, inspects declared routes and presents an empty search state", async () => {
    const user = userEvent.setup();
    render(<App />);
    await navigate("orders");
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(7);
    await user.click(screen.getByRole("button", { name: /Quantity \(pieces\)/ }));
    expect(within(table).getAllByRole("row")[1]).toHaveTextContent("O-QC");
    expect(screen.getByRole("columnheader", { name: /Quantity/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    await user.type(screen.getByRole("searchbox"), "O-MULTI");
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Inspect O-MULTI" }));
    expect(screen.getByRole("dialog", { name: "Order O-MULTI" })).toHaveTextContent(
      "Declared routing compatibility",
    );
    expect(screen.getByRole("dialog")).toHaveTextContent("FIN-01");
    await user.click(screen.getByRole("button", { name: "Close dialog" }));
    await user.clear(screen.getByRole("searchbox"));
    await user.type(screen.getByRole("searchbox"), "absent-order");
    expect(screen.getByText("No matching orders")).toBeVisible();
  });
  it("shows capacity assumptions, zero crews and calendar restrictions", async () => {
    render(<App />);
    await navigate("resources");
    expect(screen.getByRole("heading", { name: "Planned downtime" })).toBeVisible();
    expect(screen.getByText("0", { selector: ".line-crew strong" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Line unavailability" })).toBeVisible();
    expect(screen.getAllByText(/assumed efficiency/).length).toBeGreaterThan(0);
    expect(screen.getByRole("table")).toHaveTextContent("+03:00");
  });
  it("preserves independent capacity scope and incompatible null values", async () => {
    const user = userEvent.setup();
    render(<App />);
    await navigate("capacity");
    expect(screen.getByText("Independent assessment only.")).toBeVisible();
    await user.click(screen.getByRole("checkbox", { name: "Compatible routes only" }));
    expect(screen.getAllByText("Not applicable").length).toBeGreaterThan(0);
    expect(screen.queryByText("Line utilization")).not.toBeInTheDocument();
  });
  it("loads only the explicitly selected saved partial outcome and clears it on dataset change", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.selectOptions(screen.getByLabelText("Planning dataset"), "competition");
    expect(screen.queryByText("Completed units")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Load saved outcome" }));
    expect(screen.getByText("Valid partial schedule")).toBeVisible();
    expect(screen.getByText("Completed units")).toBeVisible();
    expect(screen.getAllByText("46.875%", { selector: ".stat-value" })).toHaveLength(2);
    await user.selectOptions(screen.getByLabelText("Planning dataset"), "capacity");
    expect(screen.queryByText("Completed units")).not.toBeInTheDocument();
  });
  it("handles an empty catalog and reports disconnected capabilities honestly", async () => {
    render(
      <WorkspaceProvider catalog={[]}>
        <Workspace />
      </WorkspaceProvider>,
    );
    expect(screen.getByText("No planning dataset")).toBeVisible();
    expect(screen.getByLabelText("Planning dataset")).toBeDisabled();
    await navigate("system");
    expect(screen.getByText("Capabilities not loaded")).toBeVisible();
    expect(screen.getByText("Not checked")).toBeVisible();
  });
  it("keeps skip navigation on the current page", async () => {
    const user = userEvent.setup();
    render(<App />);
    await navigate("orders");
    await user.click(screen.getByRole("button", { name: "Skip to content" }));
    expect(screen.getByRole("main")).toHaveFocus();
    expect(window.location.hash).toBe("#/orders");
  });
});

describe("API ownership and visible failures", () => {
  it("shows loading, exact actual response ownership and memory-only disconnect", async () => {
    let resolve: ((value: Response) => void) | undefined;
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(response('{"status":"ok","api_version":"v1","service":"loometric"}'))
      .mockResolvedValueOnce(response(capabilities))
      .mockImplementationOnce(
        () =>
          new Promise((done) => {
            resolve = done;
          }),
      );
    vi.stubGlobal("fetch", fetcher);
    const secret = token();
    render(<App />);
    await configure(secret);
    expect(screen.getByText("Loading the local capacity report…")).toBeVisible();
    expect(screen.queryByText("Saved M02 report · explicit demo mode")).not.toBeInTheDocument();
    await act(async () => {
      resolve?.(response(capacityRaw));
    });
    expect(screen.getByText("API response")).toBeVisible();
    expect(screen.getByText(id)).toBeVisible();
    expect(document.body.textContent).not.toContain(secret);
    expect(localStorage.length + sessionStorage.length).toBe(1);
    await navigate("system");
    expect(screen.getByText("v1")).toBeVisible();
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Clear session & use fixture preview" }));
    expect(screen.getByText("Capabilities not loaded")).toBeVisible();
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
  it("shows authentication errors without falling back to the cached capacity report", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response('{"request_id":"bad","error":{}}', { status: 401 })),
    );
    render(<App />);
    await configure(token());
    expect(await screen.findByRole("alert")).toHaveTextContent("session was rejected");
    expect(document.querySelectorAll(".capacity-bar-row")).toHaveLength(0);
    expect(screen.getByText("Local API mode")).toBeVisible();
  });
  it("does not replace a new dataset with a late response from an old one", async () => {
    let oldResolve: ((value: Response) => void) | undefined;
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(response('{"status":"ok","api_version":"v1","service":"loometric"}'))
      .mockResolvedValueOnce(response(capabilities))
      .mockImplementationOnce(
        () =>
          new Promise((done) => {
            oldResolve = done;
          }),
      )
      .mockResolvedValueOnce(response(competitionRaw));
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await configure(token());
    await waitFor(() => expect(oldResolve).toBeDefined());
    fireEvent.change(screen.getByLabelText("Planning dataset"), {
      target: { value: "competition" },
    });
    await screen.findByText("API response");
    expect(document.querySelectorAll(".capacity-bar-row")).toHaveLength(1);
    await act(async () => {
      oldResolve?.(response(capacityRaw));
    });
    expect(document.querySelectorAll(".capacity-bar-row")).toHaveLength(1);
    expect(screen.queryByText("examples/planning/capacity-demo.json")).not.toBeInTheDocument();
  });
  it("uses the latest selected input when the connection handshake finishes", async () => {
    let healthResolve: ((value: Response) => void) | undefined;
    const fetcher = vi
      .fn<typeof fetch>()
      .mockImplementationOnce(
        () =>
          new Promise((done) => {
            healthResolve = done;
          }),
      )
      .mockResolvedValueOnce(response(capabilities))
      .mockResolvedValueOnce(response(competitionRaw));
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await configure(token());
    fireEvent.change(screen.getByLabelText("Planning dataset"), {
      target: { value: "competition" },
    });
    await act(async () => {
      healthResolve?.(response('{"status":"ok","api_version":"v1","service":"loometric"}'));
    });
    await screen.findByText("API response");
    const body = fetcher.mock.calls[2]?.[1]?.body;
    expect(object(object(parseExact(String(body))).scenario).scenario_id).toBe(
      datasets[1]?.planning.id,
    );
  });
});

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(languageStorageKey, "en-US");
});
