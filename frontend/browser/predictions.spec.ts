import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

const origin = process.env.LOOMETRIC_BROWSER_ORIGIN,
  token = process.env.LOOMETRIC_BROWSER_TOKEN;
if (!origin || !token) throw new Error("Use the owned browser harness.");
async function connect(page: Page) {
  await page.goto("/#/predictions");
  await page.getByRole("button", { name: "Configure API" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("API origin").fill(origin ?? "");
  await dialog.getByLabel("Bearer token").fill(token ?? "");
  await dialog.getByRole("button", { name: "Connect & load capacity" }).click();
  await expect(page.getByText("Local API response loaded", { exact: true })).toBeVisible();
  await page.getByLabel("I am testing hypothetical synthetic pre-shift conditions.").check();
}
async function predict(page: Page) {
  const invalid = await page
    .locator(".prediction-form input:invalid, .prediction-form select:invalid")
    .evaluateAll((elements) =>
      elements.map((element) => ({
        id: element.id,
        name: element.getAttribute("name"),
        message: (element as HTMLInputElement).validationMessage,
      })),
    );
  expect(invalid).toEqual([]);
  const response = page.waitForResponse(
    (r) =>
      /^\/api\/v1\/predictions\/synthetic(?:\/v[23])?$/.test(new URL(r.url()).pathname) &&
      r.request().method() === "POST",
    { timeout: 15000 },
  );
  await page.getByRole("button", { name: "Predict", exact: true }).click();
  const actual = await response;
  expect(actual.status()).toBe(200);
  return (await actual.json()).data;
}
async function axe(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(result.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) }))).toEqual(
    [],
  );
}
test("actual experimental estimators, comparison, scenario change, review and abstention", async ({
  page,
}) => {
  test.setTimeout(120000);
  const requests: string[] = [],
    errors: string[] = [];
  page.on("request", (r) => {
    if (r.url().startsWith(`${origin}/api/v1`)) requests.push(new URL(r.url()).pathname);
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await connect(page);
  await expect(page.getByLabel("Model", { exact: true })).toHaveValue("rf_physics");
  const candidate = await predict(page);
  expect(candidate.schema_version).toBe(2);
  expect(candidate.results).toHaveLength(1);
  expect(candidate.results[0].prediction).toBe(0.8919168184750277);
  await expect(page.getByRole("article", { name: "RF Physics result" })).toContainText(
    "RESEARCH CANDIDATE",
  );
  await page.getByLabel("Model", { exact: true }).selectOption("legacy");
  const initial = await predict(page);
  expect(initial.results.map((r: { prediction: number }) => r.prediction)).toEqual([
    0.9036296370677777, 0.8945601867754494, 0.7628348220475517, 0.8919168184750277,
  ]);
  expect(initial.differences).toHaveLength(6);
  await expect(page.getByRole("article", { name: "Random Forest result" })).toContainText(
    "0.90363",
  );
  await expect(page.getByRole("region", { name: "Model prediction differences" })).toContainText(
    "0.00907",
  );
  await expect(page.getByRole("heading", { name: "Global Random Forest behavior" })).toBeVisible();
  await axe(page);
  await page.screenshot({
    path: resolve("..", ".tmp/frontend/m08c-predictions-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Use as scenario baseline" }).click();
  await page.getByLabel("Planned workers", { exact: true }).fill("8");
  await expect(
    page.getByText("Waiting for the next real prediction. No after value is assumed."),
  ).toBeVisible();
  const after = await predict(page);
  expect(after.results[0].prediction).toBe(0.7758056870789638);
  const differences = page.getByRole("region", { name: "Before and after model predictions" });
  await expect(differences).toContainText("0.90363");
  await expect(differences).toContainText("0.77581");
  await expect(page.getByRole("region", { name: "Scenario input differences" })).toContainText(
    "Planned workers",
  );
  await page.screenshot({
    path: resolve("..", ".tmp/frontend/m08c-scenario-comparison.png"),
    fullPage: true,
  });
  await page.getByLabel("Planned workers", { exact: true }).fill("30");
  const review = await predict(page);
  expect(review.results[0].support.status).toBe("REVIEW_REQUIRED");
  await expect(page.getByRole("article", { name: "Random Forest result" })).toContainText(
    "Review required",
  );
  await page.getByLabel("Planned workers", { exact: true }).fill("0");
  const zero = await predict(page);
  expect(zero.results.every((r: { prediction: unknown }) => r.prediction === null)).toBe(true);
  await expect(page.getByRole("article", { name: "Random Forest result" })).toContainText(
    "Abstained",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await axe(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({
    path: resolve("..", ".tmp/frontend/m08c-predictions-mobile.png"),
    fullPage: true,
  });
  await page.getByLabel("Planned workers", { exact: true }).fill("6");
  await page.getByLabel("Model", { exact: true }).selectOption("random_forest");
  const legacy = await predict(page);
  expect(legacy.schema_version).toBe(1);
  expect(legacy.results[0].prediction).toBe(initial.results[0].prediction);
  expect(requests.filter((path) => path === "/api/v1/predictions/synthetic/v2")).toHaveLength(5);
  expect(requests.filter((path) => path === "/api/v1/predictions/synthetic")).toHaveLength(1);
  expect(requests.some((path) => /\/scheduling|\/jobs|\/scenarios\/compare/.test(path))).toBe(
    false,
  );
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(1);
  expect(await page.content()).not.toContain(token);
  expect(errors).toEqual([]);
});

test("input validation, delayed real response cancellation and explicit server failure", async ({
  page,
}) => {
  test.setTimeout(60000);
  await connect(page);
  await page.getByLabel("Order quantity (pieces)", { exact: true }).fill("601");
  await expect(page.getByRole("button", { name: "Predict", exact: true })).toBeDisabled();
  await expect(page.getByRole("alert")).toContainText("Opening WIP plus planned release");
  await page.getByLabel("Order quantity (pieces)", { exact: true }).fill("600");
  let release: (() => void) | undefined;
  const delayed = new Promise<void>((done) => {
    release = done;
  });
  let fetched: (() => void) | undefined;
  const completed = new Promise<void>((done) => {
    fetched = done;
  });
  await page.route("**/api/v1/predictions/synthetic/v2", async (route) => {
    const actual = await route.fetch();
    expect(actual.status()).toBe(200);
    fetched?.();
    await delayed;
    try {
      await route.fulfill({ response: actual });
    } catch {
      /* Client deliberately aborted. */
    }
  });
  await page.getByRole("button", { name: "Predict", exact: true }).click();
  await expect(page.getByRole("button", { name: "Running actual estimators…" })).toBeDisabled();
  await completed;
  await page.getByLabel("Planned workers", { exact: true }).fill("8");
  release?.();
  await expect(page.getByRole("button", { name: "Predict", exact: true })).toBeEnabled();
  await expect(page.getByText("0.89192", { exact: true })).toHaveCount(0);
  await page.unroute("**/api/v1/predictions/synthetic/v2");
  // Explicit transport failure is test-only; no simulated successful predictions.
  await page.route("**/api/v1/predictions/synthetic/v2", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        api_version: "v1",
        request_id: "00000000-0000-4000-8000-000000000001",
        error: { code: "EXPERIMENTAL_ARTIFACT_UNAVAILABLE", message: "private diagnostics" },
      }),
    }),
  );
  await page.getByRole("button", { name: "Predict", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Trusted experimental model artifacts unavailable",
  );
  await expect(page.getByText("private diagnostics")).toHaveCount(0);
  await expect(page.getByRole("article", { name: "RF Physics result" })).toHaveCount(0);
  await axe(page);
  await page.screenshot({
    path: resolve("..", ".tmp/frontend/m08c-predictions-error.png"),
    fullPage: true,
  });
});

test("fifth model uses mature history, matched evidence and explicit abstention", async ({
  page,
}) => {
  test.setTimeout(120000);
  const bodies: Record<string, unknown>[] = [];
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().endsWith("/predictions/synthetic/v3")) bodies.push(request.postDataJSON());
  });
  await connect(page);
  await page.getByLabel("Model", { exact: true }).selectOption("all");
  const cold = await predict(page);
  expect(cold.schema_version).toBe(3);
  expect(cold.results[4].prediction).toBeNull();
  expect(cold.results[4].support.reason_codes).toContain("MATURE_HISTORY_REQUIRED");
  for (const [label, value] of [
    ["Mature history count", "7"],
    ["Uncensored history count", "4"],
    ["Recent uncensored attainment mean", "0.85"],
    ["Recent uncensored attainment standard deviation", "0.1"],
    ["Latest mature report age (hours)", "16"],
  ] as const)
    await page.getByLabel(label, { exact: true }).fill(value);
  const mature = await predict(page);
  expect(mature.results.slice(0, 4).map((r: { prediction: number }) => r.prediction)).toEqual([
    0.9036296370677777, 0.8945601867754494, 0.7628348220475517, 0.8919168184750277,
  ]);
  expect(mature.results[4].prediction).toBe(0.834534223925279);
  expect(mature.differences).toHaveLength(10);
  expect(mature.promotion_decision).toBe("NO_ML_PROMOTION");
  expect(mature.capacity_application_authorized).toBe(false);
  const metrics = page.getByRole("region", { name: "Matched held-out model metrics" });
  await expect(metrics.getByRole("row")).toHaveCount(11);
  await expect(metrics).toContainText("0.05590");
  await expect(metrics).toContainText("0.08894");
  await expect(page.getByRole("article", { name: "History Boost result" })).toContainText(
    "0.83453",
  );
  await axe(page);
  await page
    .getByRole("heading", { name: "Matched fresh-world evidence · EXP-010" })
    .evaluate((element) => element.scrollIntoView({ block: "start" }));
  await page.screenshot({ path: resolve("..", ".tmp/frontend/final-predictions-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("article", { name: "History Boost result" }).scrollIntoViewIfNeeded();
  await axe(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: resolve("..", ".tmp/frontend/final-predictions-mobile.png") });
  await page.getByLabel("Latest mature report age (hours)", { exact: true }).fill("73");
  expect((await predict(page)).results[4].prediction).toBeNull();
  await page.getByLabel("Latest mature report age (hours)", { exact: true }).fill("16");
  await page.getByLabel("Planned workers", { exact: true }).fill("0");
  expect(
    (await predict(page)).results.every((r: { prediction: unknown }) => r.prediction === null),
  ).toBe(true);
  expect(bodies).toHaveLength(4);
  expect(Object.keys(bodies[1] ?? {}).sort()).toEqual([
    "history",
    "inputs",
    "models",
    "prediction_context",
    "schema_version",
    "synthetic",
  ]);
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(1);
  expect(await page.content()).not.toContain(token);
  expect(errors).toEqual([]);
});

// Existing workflow assertions explicitly exercise the selectable English locale.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("loometric.language", "en-US");
  });
});
