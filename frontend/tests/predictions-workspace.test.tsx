import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import capacity from "../fixtures/capacity-demo.report.json?raw";
import { App } from "../src/App";
import { initialInputs, type ModelName, type PredictionInputs } from "../src/domain/predictions";
import { capturedResponse } from "./prediction-fixtures";

const id = "00000000-0000-4000-8000-000000000001";
const reply = (data: unknown) =>
  new Response(JSON.stringify({ api_version: "v1", request_id: id, data }));
function transport(
  predict?: (
    input: PredictionInputs,
    models: ModelName[],
    options?: RequestInit,
  ) => Promise<Response>,
) {
  return vi.fn<typeof fetch>(async (url, options) => {
    const path = String(url).split("/api/v1")[1];
    if (path === "/health") return reply({ status: "ok", api_version: "v1", service: "loometric" });
    if (path === "/capabilities")
      return reply({
        policy_versions: ["whole-stage-minute-v1"],
        operations: ["capacity", "verify"],
        scheduling_methods: ["greedy"],
        limits: { max_orders: 32 },
        optimization_jobs: { limits: { max_active_jobs: 1 } },
        limitations: ["synthetic only"],
        deferred: { prediction: "M01 offline" },
      });
    if (path === "/planning/capacity")
      return new Response(`{"api_version":"v1","request_id":"${id}","data":${capacity}}`);
    if (path === "/predictions/synthetic") {
      const body = JSON.parse(String(options?.body));
      return predict
        ? predict(body.inputs, body.models, options)
        : new Response(JSON.stringify(capturedResponse(body.inputs, body.models)));
    }
    throw new Error("Unexpected endpoint in prediction test");
  });
}
async function connect() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Configure API" }));
  await user.type(screen.getByLabelText("Bearer token"), crypto.randomUUID().replaceAll("-", ""));
  await user.click(screen.getByRole("button", { name: "Connect & load capacity" }));
  await screen.findByText("Local API response loaded");
  await user.click(
    screen.getByLabelText("I am testing hypothetical synthetic pre-shift conditions.", {
      exact: false,
    }),
  );
  return user;
}
beforeEach(() => {
  window.history.replaceState(null, "", "/#/predictions");
});
afterEach(() => vi.unstubAllGlobals());

it("requires connection and explicit declaration and has no fabricated preview prediction", () => {
  const calls = transport();
  vi.stubGlobal("fetch", calls);
  render(<App />);
  expect(screen.getByRole("heading", { name: "AI Predictions", level: 1 })).toBeVisible();
  expect(screen.getByLabelText("Model")).toHaveValue("random_forest");
  expect(screen.getByRole("button", { name: "Predict" })).toBeDisabled();
  expect(screen.queryByText("0.90363")).not.toBeInTheDocument();
  expect(calls).not.toHaveBeenCalled();
});
it("renders actual response, all-model differences, failed gates and global explanation", async () => {
  const calls = transport();
  vi.stubGlobal("fetch", calls);
  render(<App />);
  const user = await connect();
  await user.selectOptions(screen.getByLabelText("Model"), "all");
  await user.click(screen.getByRole("button", { name: "Predict" }));
  expect(await screen.findByText("0.90363")).toBeVisible();
  expect(screen.getByText("0.89456")).toBeVisible();
  expect(screen.getByText("0.76283")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Global Random Forest behavior" })).toBeVisible();
  expect(screen.getByRole("region", { name: "Model prediction differences" })).toBeVisible();
  expect(screen.getAllByText(/Maximum stage regression/)[0]).toHaveTextContent("51.84%");
  expect(screen.getByText(/NO ML PROMOTION/)).toBeVisible();
  expect(
    calls.mock.calls.some(([url]) => /\/jobs|\/dispatch|\/scenarios\/compare/.test(String(url))),
  ).toBe(false);
  expect(localStorage.length + sessionStorage.length).toBe(0);
});
it("pins a scenario, shows changed inputs and compares only actual subsequent responses", async () => {
  vi.stubGlobal("fetch", transport());
  render(<App />);
  const user = await connect();
  await user.click(screen.getByRole("button", { name: "Predict" }));
  await screen.findByText("0.90363");
  await user.click(screen.getByRole("button", { name: "Use as scenario baseline" }));
  fireEvent.change(screen.getByLabelText("Planned workers", { exact: true }), {
    target: { value: "8" },
  });
  expect(screen.queryByText("0.90363")).not.toBeInTheDocument();
  expect(screen.getByText(/Waiting for the next real prediction/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Predict" }));
  const table = await screen.findByRole("region", { name: "Before and after model predictions" });
  expect(within(table).getByText("Random Forest")).toBeVisible();
  const inputs = screen.getByRole("region", { name: "Scenario input differences" });
  expect(within(inputs).getByText("planned workers")).toBeVisible();
  expect(within(inputs).getByText("8")).toBeVisible();
  expect(screen.getByText(/Differences are not proven causal effects/)).toBeVisible();
});
it("shows loading, aborts edited requests and ignores late responses", async () => {
  let resolve: ((response: Response) => void) | undefined;
  let signal: AbortSignal | null | undefined;
  vi.stubGlobal(
    "fetch",
    transport(async (_input, _models, options) => {
      signal = options?.signal;
      return new Promise<Response>((done) => {
        resolve = done;
      });
    }),
  );
  render(<App />);
  const user = await connect();
  await user.click(screen.getByRole("button", { name: "Predict" }));
  expect(screen.getByRole("button", { name: "Running actual estimators…" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Planned workers", { exact: true }), {
    target: { value: "8" },
  });
  expect(signal?.aborted).toBe(true);
  await act(async () => {
    resolve?.(new Response(JSON.stringify(capturedResponse(initialInputs, ["random_forest"]))));
  });
  expect(screen.queryByText("0.90363")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Predict" })).toBeEnabled();
});
it("blocks inconsistent values and displays safe API errors without fallback", async () => {
  vi.stubGlobal(
    "fetch",
    transport(
      async () =>
        new Response(
          JSON.stringify({
            api_version: "v1",
            request_id: id,
            error: {
              code: "EXPERIMENTAL_ARTIFACT_UNAVAILABLE",
              message: "private exception must not be shown",
            },
          }),
          { status: 503 },
        ),
    ),
  );
  render(<App />);
  const user = await connect();
  fireEvent.change(screen.getByLabelText("Order quantity (pieces)", { exact: true }), {
    target: { value: "601" },
  });
  expect(screen.getByRole("button", { name: "Predict" })).toBeDisabled();
  expect(screen.getByRole("alert")).toHaveTextContent("Opening WIP plus planned release");
  fireEvent.change(screen.getByLabelText("Order quantity (pieces)", { exact: true }), {
    target: { value: "600" },
  });
  await user.click(screen.getByRole("button", { name: "Predict" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Request unavailable");
  expect(screen.getByText("EXPERIMENTAL_ARTIFACT_UNAVAILABLE")).toBeVisible();
  expect(screen.queryByText(/private exception/)).not.toBeInTheDocument();
  expect(screen.queryByText("0.90363")).not.toBeInTheDocument();
});
it("renders review and zero-capacity abstention without an invented estimate", async () => {
  vi.stubGlobal(
    "fetch",
    transport(async (input, models) => {
      const r = capturedResponse(input, models),
        result = r.data.results[0];
      if (input.planned_workers === 0) {
        result.prediction = null;
        result.descriptive_band = null;
        result.support = {
          status: "ABSTAIN",
          reason_codes: ["ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET"],
        };
      } else
        result.support = {
          status: "REVIEW_REQUIRED",
          reason_codes: ["OUTSIDE_TRAINING_SUPPORT:planned_workers"],
        };
      return new Response(JSON.stringify(r));
    }),
  );
  render(<App />);
  const user = await connect();
  await user.click(screen.getByRole("button", { name: "Predict" }));
  expect(await screen.findByText("REVIEW REQUIRED")).toBeVisible();
  fireEvent.change(screen.getByLabelText("Planned workers", { exact: true }), {
    target: { value: "0" },
  });
  await user.click(screen.getByRole("button", { name: "Predict" }));
  expect(await screen.findByText("Abstained")).toBeVisible();
  expect(screen.queryByText("0.90363")).not.toBeInTheDocument();
});
it("session replacement clears a pinned prediction and cancels pending research work", async () => {
  vi.stubGlobal("fetch", transport());
  render(<App />);
  const user = await connect();
  await user.click(screen.getByRole("button", { name: "Predict" }));
  await screen.findByText("0.90363");
  await user.click(screen.getByRole("button", { name: "Use as scenario baseline" }));
  await user.click(screen.getByRole("button", { name: "Configure API" }));
  await user.type(screen.getByLabelText("Bearer token"), crypto.randomUUID().replaceAll("-", ""));
  await user.click(screen.getByRole("button", { name: "Connect & load capacity" }));
  await waitFor(() =>
    expect(
      screen.queryByRole("heading", { name: "Hypothetical scenario comparison" }),
    ).not.toBeInTheDocument(),
  );
  expect(screen.queryByText("0.90363")).not.toBeInTheDocument();
});
