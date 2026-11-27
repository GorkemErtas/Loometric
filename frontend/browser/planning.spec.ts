import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

const origin = process.env.LOOMETRIC_BROWSER_ORIGIN,
  token = process.env.LOOMETRIC_BROWSER_TOKEN;
if (!origin || !token) throw new Error("Use the owned browser harness.");
async function connect(page: Page, dataset: string) {
  await page.goto("/#/scheduling");
  await page.getByLabel("Planning dataset").selectOption(dataset);
  await page.getByRole("button", { name: "Configure API" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("API origin").fill(origin ?? "");
  await dialog.getByLabel("Bearer token").fill(token ?? "");
  await dialog.getByRole("button", { name: "Connect & load capacity" }).click();
  await expect(
    page.getByRole("button", { name: "Run reference scheduling", exact: true }),
  ).toBeEnabled({ timeout: 15000 });
  await page.getByRole("button", { name: "Run reference scheduling", exact: true }).click();
  await expect(page.locator(".gantt-operation").first()).toBeVisible({ timeout: 15000 });
}
async function axe(page: Page) {
  const current = await page.evaluateHandle(() => document.activeElement);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  await current.evaluate((element) => {
    if (element instanceof HTMLElement) element.focus({ preventScroll: true });
  });
  await current.dispose();
  expect(result.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) }))).toEqual(
    [],
  );
}
const screenshot = async (page: Page, name: string) => {
  await page.getByRole("main").focus();
  await page.evaluate(() => window.scrollTo(0, 0));
  return page.screenshot({ path: resolve("..", ".tmp/frontend", `${name}.png`), fullPage: true });
};
async function workers(page: Page, value: string) {
  await page.getByRole("link", { name: "What-if scenarios", exact: true }).click();
  await page.getByLabel("Change operation").selectOption("set_workers");
  await page.getByLabel("Worker count (exact integer)").fill(value);
  await page.getByRole("button", { name: "Add change to review" }).click();
}

test("real dispatch, verified Gantt, reviewed what-if, bounded scheduling job and selected result", async ({
  page,
}) => {
  test.setTimeout(75000);
  const requests: string[] = [],
    errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.url().startsWith(`${origin}/api/v1`))
      requests.push(`${r.method()} ${new URL(r.url()).pathname}`);
  });
  await connect(page, "capacityScenario");
  await expect(page.locator(".gantt-operation")).toHaveCount(2);
  await expect(page.locator(".unfinished-list")).toContainText("C");
  await expect(page.locator(".unfinished-list")).toContainText("UNSCHEDULED");
  await axe(page);
  await screenshot(page, "m06b-scheduling-desktop");
  await page.locator(".gantt-operation").first().focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toContainText("Elapsed duration from endpoints");
  await expect(page.getByRole("dialog")).toContainText("+00:00");
  await axe(page);
  await page.keyboard.press("Escape");
  await expect(page.locator(".gantt-operation").first()).toBeFocused();
  await workers(page, "3");
  await page.getByRole("button", { name: "Review exact specification" }).click();
  await expect(page.locator(".review-json")).toContainText('"worker_count": 3');
  await expect(page.locator(".review-json")).toContainText(
    '"baseline_fingerprint": "6a6410ea81529136f8df10e547672b0231255b79c614a1f34e0a37599afc438c"',
  );
  await axe(page);
  await screenshot(page, "m06b-scenario-review");
  await page.getByRole("button", { name: "Run reviewed greedy comparison" }).click();
  const table = page.getByRole("region", { name: "Scenario metric differences" });
  await expect(table.getByRole("row", { name: /^Finished units/ })).toContainText("45", {
    timeout: 15000,
  });
  await expect(table.getByRole("row", { name: /^Finished units/ })).toContainText("55");
  await expect(page.locator(".comparison-headline")).toContainText("Better");
  await axe(page);
  await screenshot(page, "m06b-scenario-comparison");
  await page.getByRole("link", { name: "Production scheduling", exact: true }).click();
  await page.getByRole("button", { name: "Submit bounded CP-SAT job" }).click();
  await expect(page.getByLabel("Job ID")).toHaveValue(/^[a-f0-9]{32}$/, { timeout: 15000 });
  await expect(page.getByText("Verified job result", { exact: true })).toBeVisible({
    timeout: 25000,
  });
  await expect(page.getByRole("heading", { name: "Selected optimizer-job Gantt" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Producer & solver evidence" })).toContainText(
    "Selected: Greedy",
  );
  await page.getByText(/Advanced optimizer evidence/).click();
  await expect(page.getByRole("region", { name: "CP-SAT proof phases" })).toContainText("Optimal");
  await axe(page);
  await screenshot(page, "m06b-job-result");
  expect(requests.filter((s) => s === "POST /api/v1/scheduling/dispatch")).toHaveLength(1);
  expect(requests.filter((s) => s === "POST /api/v1/scenarios/compare")).toHaveLength(1);
  expect(requests.filter((s) => s === "POST /api/v1/jobs/scheduling")).toHaveLength(1);
  expect(requests.some((s) => /\/prediction|\/optimize|\/catalog/.test(s))).toBe(false);
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(1);
  expect(await page.content()).not.toContain(token);
  expect(errors).toEqual([]);
});

test("real CP-SAT scenario job reports routing recovery and producer-specific proof", async ({
  page,
}) => {
  test.setTimeout(60000);
  await connect(page, "routingScenario");
  await workers(page, "2");
  await page.getByLabel("Request bounded CP-SAT comparison job").check();
  await page.getByRole("button", { name: "Review exact specification" }).click();
  await page.getByRole("button", { name: "Submit reviewed CP-SAT comparison job" }).click();
  await expect(page.getByText("Verified job result", { exact: true })).toBeVisible({
    timeout: 30000,
  });
  await expect(page.getByRole("region", { name: "Scenario producer & proof" })).toContainText(
    "Selected: CP-SAT",
  );
  const table = page.getByRole("region", { name: "Scenario metric differences" });
  await expect(table.getByRole("row", { name: /^Finished units/ })).toContainText("28");
  await expect(page.locator(".comparison-headline")).toContainText("Greedy-only relation: Worse");
  await axe(page);
  await screenshot(page, "m06b-routing-recovery");
});

test("real zero-wall scenario job keeps explicit UNKNOWN fallback; tablet/mobile remain usable", async ({
  page,
}) => {
  test.setTimeout(60000);
  await connect(page, "routingScenario");
  await workers(page, "2");
  await page.getByLabel("Request bounded CP-SAT comparison job").check();
  await page.getByLabel("Wall seconds per phase (0–1)").fill("0");
  await page.getByRole("button", { name: "Review exact specification" }).click();
  await expect(page.locator(".review-json")).toContainText('"wall_time_seconds_per_phase": 0');
  await page.getByRole("button", { name: "Submit reviewed CP-SAT comparison job" }).click();
  await expect(page.getByText("Verified job result", { exact: true })).toBeVisible({
    timeout: 25000,
  });
  const proof = page.getByRole("region", { name: "Scenario producer & proof" });
  await expect(proof).toContainText("Selected: Greedy");
  await expect(proof).toContainText("UNKNOWN");
  await expect(page.locator(".comparison-headline")).toContainText("Worse");
  await page.setViewportSize({ width: 820, height: 1100 });
  await axe(page);
  await screenshot(page, "m06b-jobs-tablet");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  await axe(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await screenshot(page, "m06b-jobs-mobile");
});

test("explicit real job cancellation reaches server CANCELLED without a fabricated result", async ({
  page,
}) => {
  test.setTimeout(60000);
  await connect(page, "capacityScenario");
  await workers(page, "3");
  await page.getByLabel("Request bounded CP-SAT comparison job").check();
  await page.getByRole("button", { name: "Review exact specification" }).click();
  await page.getByRole("button", { name: "Submit reviewed CP-SAT comparison job" }).click();
  const cancel = page.getByRole("button", { name: "Cancel server job" });
  await expect(cancel).toBeEnabled({ timeout: 15000 });
  await cancel.click();
  await expect(page.getByRole("region", { name: "Selected job lifecycle" })).toContainText(
    "Cancelled",
    { timeout: 15000 },
  );
  await expect(page.getByText("Verified job result", { exact: true })).toHaveCount(0);
  await expect(cancel).toBeDisabled();
  await axe(page);
  await screenshot(page, "m06b-cancelled-job");
});

// Existing workflow assertions explicitly exercise the selectable English locale.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("loometric.language", "en-US");
  });
});
