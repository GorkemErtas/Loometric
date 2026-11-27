import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import capacity from "../fixtures/competition.capacity.json?raw";
import { App } from "../src/App";
import { datasets } from "../src/demo/catalog";
import { encodeExact, parseExact } from "../src/domain/json";
import { cloneInput, planningOf, rows } from "../src/domain/production";
import { languageStorageKey } from "../src/i18n/locale";
import { ProductionProvider, useProduction } from "../src/state/ProductionWorkspace";
import { useWorkspace, WorkspaceProvider } from "../src/state/Workspace";

const fixture = datasets.find((d) => d.key === "competition");
if (!fixture?.instance) throw new Error("Missing fixture");
const instance = fixture.instance,
  selected = fixture;
const id = "00000000-0000-4000-8000-000000000001";
const response = (data: unknown, status = 200) =>
  new Response(encodeExact({ api_version: "v1", request_id: id, data }), { status });
const validated = () =>
  response({
    schema_version: parseExact("1"),
    policy_version: "whole-stage-minute-v1",
    synthetic: true,
    status: "VALID_INPUT",
    instance_id: instance.instance_id,
    instance_fingerprint: "a".repeat(64),
  });
const metadata = parseExact(
  '{"policy_versions":["whole-stage-minute-v1"],"operations":["capacity","dispatch","verify","compare","validate"],"scheduling_methods":["greedy"],"limits":{"max_orders":32,"max_operations":96},"optimization_jobs":{"limits":{"max_active_jobs":1}},"limitations":["synthetic"],"deferred":{"prediction":"offline"}}',
);
function transport(validation: () => Promise<Response> = async () => validated()) {
  return vi.fn<typeof fetch>(async (url) => {
    const path = String(url).split("/api/v1")[1];
    if (path === "/health")
      return response({ status: "ok", api_version: "v1", service: "loometric" });
    if (path === "/capabilities") return response(metadata);
    if (path === "/planning/capacity") return response(parseExact(capacity));
    if (path === "/scheduling/validate") return validation();
    throw new Error("Unexpected test request");
  });
}
function Harness() {
  const production = useProduction(),
    workspace = useWorkspace();
  return (
    <>
      <button
        type="button"
        onClick={() => void workspace.connect("http://127.0.0.1:8000", "a".repeat(32))}
      >
        Connect
      </button>
      <button type="button" onClick={() => production.replace(instance)}>
        Load input
      </button>
      <button
        type="button"
        onClick={() => {
          const next = cloneInput(production.draft);
          const order = rows(planningOf(next).orders)[0];
          if (order) order.quantity = parseExact("17");
          production.replace(next);
        }}
      >
        Edit quantity
      </button>
      <button type="button" onClick={() => void production.validate()}>
        Validate
      </button>
      <button type="button" onClick={() => void production.activate()}>
        Activate
      </button>
      <button type="button" onClick={workspace.enterPreview}>
        Disconnect
      </button>
      <button type="button" onClick={() => workspace.selectDataset("other")}>
        Switch dataset
      </button>
      <output aria-label="Validated">{production.receipt ? "yes" : "no"}</output>
      <output aria-label="Active dataset">{workspace.dataset?.key}</output>
      <output aria-label="API connected">{workspace.api ? "yes" : "no"}</output>
      <output aria-label="Draft">{encodeExact(production.draft)}</output>
      <output aria-label="Active input">
        {workspace.dataset?.instance ? encodeExact(workspace.dataset.instance) : "none"}
      </output>
      <output aria-label="Message">{production.message}</output>
      <output aria-label="User inputs">
        {workspace.catalog.filter((d) => d.validatedFingerprint).length}
      </output>
    </>
  );
}
function harness(fetcher = transport()) {
  vi.stubGlobal("fetch", fetcher);
  render(
    <WorkspaceProvider catalog={[selected, { ...selected, key: "other" }]}>
      <ProductionProvider>
        <Harness />
      </ProductionProvider>
    </WorkspaceProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Load input" }));
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));
  return fetcher;
}
async function ready() {
  await waitFor(() => expect(screen.getByLabelText("API connected")).toHaveTextContent("yes"));
}
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("draft validation, activation and ownership", () => {
  it.each(["Switch dataset", "Disconnect"])(
    "can validate again after %s interrupts asynchronous activation",
    async (action) => {
      harness();
      await ready();
      fireEvent.click(screen.getByRole("button", { name: "Validate" }));
      await waitFor(() => expect(screen.getByLabelText("Validated")).toHaveTextContent("yes"));
      const original = crypto.subtle.digest.bind(crypto.subtle);
      let finish: (() => void) | undefined;
      vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(
        (...args) =>
          new Promise((resolve, reject) => {
            finish = () => {
              original(...args).then(resolve, reject);
            };
          }),
      );
      fireEvent.click(screen.getByRole("button", { name: "Activate" }));
      await waitFor(() => expect(finish).toBeDefined());
      fireEvent.click(screen.getByRole("button", { name: action }));
      await act(async () => finish?.());
      expect(screen.getByLabelText("Active dataset")).not.toHaveTextContent(/^user-/);
      fireEvent.click(screen.getByRole("button", { name: "Connect" }));
      await ready();
      fireEvent.click(screen.getByRole("button", { name: "Validate" }));
      await waitFor(() => expect(screen.getByLabelText("Validated")).toHaveTextContent("yes"));
    },
  );
  it("sends one exact validation request, activates an independent dataset and keeps only one user input", async () => {
    const fetcher = harness();
    await ready();
    const before = encodeExact(instance);
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    await waitFor(() => expect(screen.getByLabelText("Validated")).toHaveTextContent("yes"));
    expect(
      fetcher.mock.calls.filter(([url]) => String(url).endsWith("/scheduling/validate")),
    ).toHaveLength(1);
    expect(
      String(
        fetcher.mock.calls.find(([url]) => String(url).endsWith("/scheduling/validate"))?.[1]?.body,
      ),
    ).toBe(encodeExact({ instance }));
    fireEvent.click(screen.getByRole("button", { name: "Activate" }));
    fireEvent.click(screen.getByRole("button", { name: "Activate" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Active dataset")).toHaveTextContent(/^user-/),
    );
    expect(screen.getByLabelText("User inputs")).toHaveTextContent("1");
    expect(screen.getByLabelText("Validated")).toHaveTextContent("no");
    fireEvent.click(screen.getByRole("button", { name: "Edit quantity" }));
    expect(screen.getByLabelText("Active input")).toHaveTextContent(before);
    expect(encodeExact(instance)).toBe(before);
    expect(localStorage.length + sessionStorage.length).toBe(1);
  });
  it.each(["Edit quantity", "Switch dataset", "Disconnect"])(
    "ignores late validation after %s and never activates its stale receipt",
    async (action) => {
      let finish: ((response: Response) => void) | undefined;
      const fetcher = harness(
        transport(
          () =>
            new Promise((resolve) => {
              finish = resolve;
            }),
        ),
      );
      await ready();
      fireEvent.click(screen.getByRole("button", { name: "Validate" }));
      await waitFor(() => expect(finish).toBeDefined());
      const signal = fetcher.mock.calls.find(([url]) =>
        String(url).endsWith("/scheduling/validate"),
      )?.[1]?.signal;
      fireEvent.click(screen.getByRole("button", { name: action }));
      await act(async () => finish?.(validated()));
      expect(signal?.aborted).toBe(true);
      expect(screen.getByLabelText("Validated")).toHaveTextContent("no");
      fireEvent.click(screen.getByRole("button", { name: "Activate" }));
      expect(screen.getByLabelText("Active dataset")).not.toHaveTextContent(/^user-/);
    },
  );
  it("clears accepted validation on a session change while retaining the editable draft", async () => {
    harness();
    await ready();
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    await waitFor(() => expect(screen.getByLabelText("Validated")).toHaveTextContent("yes"));
    const before = screen.getByLabelText("Draft").textContent;
    fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
    expect(screen.getByLabelText("Validated")).toHaveTextContent("no");
    expect(screen.getByLabelText("Draft").textContent).toBe(before);
  });
  it("shows only allowlisted domain guidance and clears rejected authentication", async () => {
    let auth = false;
    harness(
      transport(
        async () =>
          new Response(
            encodeExact({
              api_version: "v1",
              request_id: id,
              error: {
                code: auth ? "AUTHENTICATION_REQUIRED" : "DOMAIN_VALIDATION_FAILED",
                message: "secret native path must not render",
                details: [{ domain_code: "BREAK_OUTSIDE_SHIFT" }],
              },
            }),
            { status: auth ? 401 : 422 },
          ),
      ),
    );
    await ready();
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Message")).toHaveTextContent("A break lies outside its shift"),
    );
    expect(screen.queryByText(/secret native path/)).not.toBeInTheDocument();
    auth = true;
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    await waitFor(() => expect(screen.getByLabelText("API connected")).toHaveTextContent("no"));
    expect(screen.getByLabelText("Validated")).toHaveTextContent("no");
  });
});

describe("guided production forms", () => {
  it("edits a copy, rejects duplicate style IDs, and exposes broken references after removal", async () => {
    window.history.replaceState(null, "", "/#/data");
    const user = userEvent.setup();
    render(<App />);
    await user.selectOptions(screen.getByLabelText("Reusable input template"), "competition");
    await user.click(screen.getByRole("button", { name: "Edit a template copy" }));
    await user.click(screen.getByRole("button", { name: "Replace draft" }));
    await user.click(screen.getByRole("button", { name: /Product styles/ }));
    const style = String(rows(planningOf(instance).styles)[0]?.style_id);
    await user.click(screen.getByRole("button", { name: "Add product style" }));
    await user.clear(screen.getByLabelText("Style name / ID"));
    await user.type(screen.getByLabelText("Style name / ID"), style);
    await user.click(screen.getByRole("button", { name: "Add stage standard" }));
    await user.selectOptions(screen.getByLabelText("Supported stage 1"), "sewing");
    await user.type(screen.getByLabelText("Standard worker-minutes per piece 1"), "2.5");
    await user.click(screen.getByRole("button", { name: "Save record" }));
    expect(screen.getByRole("alert")).toHaveTextContent("already used");
    await user.click(screen.getByRole("button", { name: "Cancel editing" }));
    await user.click(screen.getByRole("button", { name: `Remove ${style}` }));
    await user.click(screen.getByRole("button", { name: /Review & validate/ }));
    expect(screen.getByRole("region", { name: "Preliminary input issues" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Export scheduling JSON" })).toBeDisabled();
    expect(rows(planningOf(instance).styles)).toHaveLength(1);
  });
});

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(languageStorageKey, "en-US");
});
