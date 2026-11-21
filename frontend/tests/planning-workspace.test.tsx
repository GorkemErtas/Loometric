import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import golden from "../fixtures/m04-additional-workers.report.json?raw";
import capacity from "../fixtures/m04-capacity.report.json?raw";
import { App } from "../src/App";
import { Gantt } from "../src/components/Gantt";
import { datasets } from "../src/demo/catalog";
import { calendarBands, geometry } from "../src/domain/gantt";
import { encodeExact, object, parseExact } from "../src/domain/json";
import { dispatchReport, jobResult } from "../src/domain/planning";
import { validateResult } from "../src/state/PlanningWorkspace";
import { dispatchFixture, jobFixture } from "./planning-fixtures";

const requestId = "00000000-0000-4000-8000-000000000001";
const response = (data: unknown, status = 200) =>
  new Response(encodeExact({ api_version: "v1", request_id: requestId, data }), { status });
const rejected = (status: number) =>
  new Response(
    encodeExact({
      api_version: "v1",
      request_id: requestId,
      error: {
        code: status === 410 ? "JOB_EXPIRED" : "AUTHENTICATION_REQUIRED",
        message: "Never echo native details",
      },
    }),
    { status },
  );
const metadata = () =>
  parseExact(
    '{"policy_versions":["whole-stage-minute-v1"],"operations":["capacity","dispatch","verify","compare"],"scheduling_methods":["greedy"],"limits":{"max_orders":32,"max_operations":96,"max_changes":64},"optimization_jobs":{"limits":{"max_active_jobs":1}},"limitations":["synthetic only"],"deferred":{"prediction":"M01 offline"}}',
  );
const source = datasets.find((d) => d.key === "capacityScenario");
if (!source) throw new Error("Missing frozen source");
function output() {
  const r = object(parseExact(golden)),
    b = object(r.baseline),
    e = object(b.evaluation),
    identity = object(b.identity),
    optimizer = object(e.optimizer);
  optimizer.status = "UNKNOWN";
  optimizer.solver_status = "UNKNOWN";
  e.fallback_reason = "UNKNOWN";
  return {
    job_id: "a".repeat(32),
    job_type: "scheduling",
    result: {
      schema_version: parseExact("1"),
      policy_version: "whole-stage-minute-v1",
      synthetic: true,
      instance_id: identity.instance_id,
      instance_fingerprint: identity.instance_fingerprint,
      horizon: identity.horizon,
      evaluation: e,
    },
    execution: { whole_child_wall_seconds: parseExact("0.1234") },
  };
}
function transport(
  overrides: {
    dispatch?: () => Promise<Response>;
    jobStatus?: number;
    cancelStatus?: "CANCELLED" | "SUCCEEDED";
    submitStatus?: number;
  } = {},
) {
  return vi.fn<typeof fetch>(async (url, options) => {
    const path = String(url).split("/api/v1")[1];
    if (path === "/health")
      return response({ status: "ok", api_version: "v1", service: "loometric" });
    if (path === "/capabilities") return response(metadata());
    if (path === "/planning/capacity") return response(parseExact(capacity));
    if (path === "/scheduling/dispatch")
      return overrides.dispatch ? overrides.dispatch() : response(dispatchFixture());
    if (path === "/scenarios/compare") {
      const raw = object(parseExact(golden)),
        input = object(object(parseExact(String(options?.body))).specification);
      raw.scenario_id = input.scenario_id;
      raw.label = input.label;
      return response(raw);
    }
    if (path === "/jobs/scheduling")
      return overrides.submitStatus
        ? rejected(overrides.submitStatus)
        : response(jobFixture(), 202);
    if (path === `/jobs/${"a".repeat(32)}`) {
      if (options?.method === "DELETE")
        return response(jobFixture(overrides.cancelStatus ?? "CANCELLED"));
      return overrides.jobStatus
        ? rejected(overrides.jobStatus)
        : response(jobFixture("SUCCEEDED"));
    }
    if (path === `/jobs/${"a".repeat(32)}/result`) return response(output());
    throw new Error("Unexpected endpoint in isolated UI test");
  });
}
async function navigate(route: string) {
  await act(async () => {
    window.location.hash = `/${route}`;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}
async function connect() {
  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText("Planning dataset"), "capacityScenario");
  await user.click(screen.getByRole("button", { name: "Configure API" }));
  await user.type(screen.getByLabelText("Bearer token"), crypto.randomUUID().replaceAll("-", ""));
  await user.click(screen.getByRole("button", { name: "Connect & load capacity" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Run reference scheduling" })).toBeEnabled(),
  );
}
async function reference() {
  await userEvent.setup().click(screen.getByRole("button", { name: "Run reference scheduling" }));
  await screen.findByRole("figure", {
    name: "Verified production schedule: allocated operations by production line",
  });
}
async function submit() {
  await userEvent.setup().click(screen.getByRole("button", { name: "Submit bounded CP-SAT job" }));
  await screen.findByLabelText("Job ID");
}
beforeEach(() => window.history.replaceState(null, "", "/#/scheduling"));
afterEach(() => vi.unstubAllGlobals());

describe("verified planning UI", () => {
  it("requires an executable input and an actual API session", async () => {
    const fetcher = transport();
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    expect(screen.getByRole("button", { name: "Run reference scheduling" })).toBeDisabled();
    expect(screen.getByText(/not an executable scheduling instance/)).toBeVisible();
    await userEvent
      .setup()
      .selectOptions(screen.getByLabelText("Planning dataset"), "capacityScenario");
    expect(screen.getByRole("button", { name: "Run reference scheduling" })).toBeDisabled();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("deduplicates clicks, draws verified allocations and exposes exact accessible details", async () => {
    let finish: ((r: Response) => void) | undefined;
    const fetcher = transport({
      dispatch: () =>
        new Promise((done) => {
          finish = done;
        }),
    });
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await connect();
    const button = screen.getByRole("button", { name: "Run reference scheduling" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(finish).toBeDefined());
    expect(
      fetcher.mock.calls.filter((c) => String(c[0]).endsWith("/scheduling/dispatch")),
    ).toHaveLength(1);
    await act(async () => {
      finish?.(response(dispatchFixture()));
    });
    expect(document.querySelectorAll(".gantt-operation")).toHaveLength(2);
    expect(screen.getByText("UNSCHEDULED", { selector: ".unfinished-list .badge" })).toBeVisible();
    await userEvent.setup().click(screen.getByRole("button", { name: /^Inspect operation A/ }));
    expect(screen.getByRole("dialog")).toHaveTextContent("2030-01-07T05:00:00+00:00");
    expect(screen.getByRole("dialog")).toHaveTextContent("Elapsed duration from endpoints");
    expect(localStorage.length + sessionStorage.length).toBe(0);
  });
  it("builds/reviews ordered exact changes and displays only backend comparison deltas", async () => {
    const user = userEvent.setup(),
      fetcher = transport();
    vi.stubGlobal("fetch", fetcher);
    const before = encodeExact(source.instance);
    render(<App />);
    await connect();
    await reference();
    await navigate("scenarios");
    await user.clear(screen.getByLabelText("Worker count (exact integer)"));
    await user.type(screen.getByLabelText("Worker count (exact integer)"), "3");
    await user.click(screen.getByRole("button", { name: "Add change to review" }));
    await user.click(screen.getByRole("button", { name: "Add change to review" }));
    expect(screen.getByRole("alert")).toHaveTextContent("already has an edit");
    await user.click(screen.getByRole("button", { name: "Review exact specification" }));
    expect(document.querySelector(".review-json")?.textContent).toContain('"worker_count": 3');
    await user.click(screen.getByRole("button", { name: "Run reviewed greedy comparison" }));
    const table = await screen.findByRole("region", { name: "Scenario metric differences" });
    expect(within(table).getByRole("row", { name: /Unfinished units/ })).toHaveTextContent("-100%");
    expect(encodeExact(source.instance)).toBe(before);
    expect(
      fetcher.mock.calls.filter((c) => String(c[0]).endsWith("/scenarios/compare")),
    ).toHaveLength(1);
  });
  it("never paints late results onto another dataset", async () => {
    let finish: ((r: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      transport({
        dispatch: () =>
          new Promise((done) => {
            finish = done;
          }),
      }),
    );
    render(<App />);
    await connect();
    await userEvent.setup().click(screen.getByRole("button", { name: "Run reference scheduling" }));
    await userEvent.setup().selectOptions(screen.getByLabelText("Planning dataset"), "competition");
    await act(async () => {
      finish?.(response(dispatchFixture()));
    });
    expect(document.querySelectorAll(".gantt-operation")).toHaveLength(0);
    expect(screen.queryByText("No reference schedule loaded")).toBeVisible();
  });
  it("retains the reviewed solver mode and budgets across page navigation", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", transport());
    render(<App />);
    await connect();
    await reference();
    await navigate("scenarios");
    await user.click(
      screen.getByRole("checkbox", { name: "Request bounded CP-SAT comparison job" }),
    );
    await user.clear(screen.getByLabelText("Wall seconds per phase (0–1)"));
    await user.type(screen.getByLabelText("Wall seconds per phase (0–1)"), "0");
    await user.click(screen.getByRole("button", { name: "Review exact specification" }));
    await navigate("orders");
    await navigate("scenarios");
    expect(
      screen.getByRole("checkbox", { name: "Request bounded CP-SAT comparison job" }),
    ).toBeChecked();
    expect(screen.getByLabelText("Wall seconds per phase (0–1)")).toHaveValue("0");
    expect(
      screen.getByRole("button", { name: "Submit reviewed CP-SAT comparison job" }),
    ).toBeVisible();
  });
  it("rejects invalid Gantt rendering and keeps approved calendar annotations separate", () => {
    const plan = dispatchReport(dispatchFixture()),
      before = encodeExact(source.planning.raw);
    const bands = calendarBands(source.planning, [
      {
        index: "1",
        operation: "remove_downtime",
        target: "STOP",
        changed: true,
        before: {},
        after: null,
      },
    ]);
    expect(bands.interruptions).toHaveLength(0);
    expect(encodeExact(source.planning.raw)).toBe(before);
    expect(geometry(plan.allocations[0] ?? plan.horizon, plan.horizon)).toMatchObject({
      left: "0%",
    });
    render(
      <Gantt
        plan={{ ...plan, feasible: false, status: "INVALID", metrics: null }}
        horizon={plan.horizon}
        planning={source.planning}
      />,
    );
    expect(document.querySelectorAll(".gantt-operation")).toHaveLength(0);
    expect(screen.getByText(/independent verification rejected/)).toBeVisible();
  });
});

describe("bounded job UI", () => {
  it("submits once, polls, retrieves UNKNOWN greedy fallback and shows verified results", async () => {
    const fetcher = transport();
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await connect();
    await reference();
    const button = screen.getByRole("button", { name: "Submit bounded CP-SAT job" });
    fireEvent.click(button);
    fireEvent.click(button);
    await screen.findByText("Verified job result", {}, { timeout: 5000 });
    expect(
      fetcher.mock.calls.filter((c) => String(c[0]).endsWith("/jobs/scheduling")),
    ).toHaveLength(1);
    expect(screen.getByRole("region", { name: "Producer & solver evidence" })).toHaveTextContent(
      "Selected: greedy",
    );
    expect(screen.getByRole("region", { name: "Producer & solver evidence" })).toHaveTextContent(
      "UNKNOWN",
    );
    expect(
      screen.getByText("No accepted optimizer incumbent or candidate metrics are available.", {
        exact: false,
      }),
    ).toBeInTheDocument();
  });
  it("explicit cancellation stops only on the server's receipt and never fetches a cancelled result", async () => {
    const fetcher = transport();
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await connect();
    await reference();
    await submit();
    await userEvent.setup().click(screen.getByRole("button", { name: "Cancel server job" }));
    expect(await screen.findAllByText("CANCELLED", { exact: true })).toHaveLength(2);
    expect(fetcher.mock.calls.filter((c) => c[1]?.method === "DELETE")).toHaveLength(1);
    expect(fetcher.mock.calls.some((c) => String(c[0]).endsWith("/result"))).toBe(false);
  });
  it("shows completion-winning cancellation races and retrieves the successful result", async () => {
    const fetcher = transport({ cancelStatus: "SUCCEEDED" });
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await connect();
    await reference();
    await submit();
    await userEvent.setup().click(screen.getByRole("button", { name: "Cancel server job" }));
    expect(await screen.findByText(/Completion won the race/)).toBeVisible();
    await screen.findByText("Verified job result", {}, { timeout: 5000 });
    expect(screen.queryByText("CANCELLED", { exact: true })).not.toBeInTheDocument();
  });
  it.each([410, 404, 401])(
    "stops on missing/expired/authentication status HTTP %s",
    async (status) => {
      const fetcher = transport({ jobStatus: status });
      vi.stubGlobal("fetch", fetcher);
      render(<App />);
      await connect();
      await reference();
      await submit();
      await waitFor(() => expect(screen.getByRole("alert")).toBeVisible(), { timeout: 5000 });
      expect(screen.queryByText("Verified job result", { exact: true })).not.toBeInTheDocument();
      expect(fetcher.mock.calls.filter((c) => c[1]?.method === "DELETE")).toHaveLength(0);
      if (status === 401) expect(screen.queryByLabelText("Job ID")).not.toBeInTheDocument();
    },
  );
  it("does not retry POST timeouts and warns about unknown admission outcomes", async () => {
    const fetcher = transport({ submitStatus: 504 });
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await connect();
    await reference();
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Submit bounded CP-SAT job" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("deadline");
    expect(screen.getByText(/A lost POST reply may leave work/)).toBeVisible();
    expect(
      fetcher.mock.calls.filter((c) => String(c[0]).endsWith("/jobs/scheduling")),
    ).toHaveLength(1);
  });
  it("stops polling on page leave and clears tracking on session clear without DELETE", async () => {
    const fetcher = transport();
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await connect();
    await reference();
    await submit();
    await navigate("system");
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Clear session & use fixture preview" }));
    await act(async () => {
      await new Promise((done) => setTimeout(done, 1100));
    });
    expect(fetcher.mock.calls.some((c) => String(c[0]).endsWith(`/jobs/${"a".repeat(32)}`))).toBe(
      false,
    );
    await navigate("jobs");
    expect(screen.getByText("No submitted jobs in this context")).toBeVisible();
    expect(fetcher.mock.calls.some((c) => c[1]?.method === "DELETE")).toBe(false);
  });
  it("rejects unbound result identity rather than accepting another instance's metrics", () => {
    const result = jobResult(output());
    expect(() =>
      validateResult(
        {
          id: result.id,
          baselineId: "wrong",
          fingerprint: "b".repeat(64),
          specification: null,
          retryAfterMs: null,
        },
        result,
      ),
    ).toThrow();
  });
});
