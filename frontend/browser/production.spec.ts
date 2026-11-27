import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";
import { parse, stringify } from "lossless-json";

const origin = process.env.LOOMETRIC_BROWSER_ORIGIN,
  token = process.env.LOOMETRIC_BROWSER_TOKEN;
if (!origin || !token) throw new Error("Use the owned local browser harness.");
test.use({ actionTimeout: 10000 });
const stamp = (time: string) => `2030-01-07T${time}:00+03:00`;
const step = (page: Page, name: string) =>
  page
    .getByRole("navigation", { name: "Production data steps" })
    .getByRole("button", { name: new RegExp(name) })
    .click();
async function save(page: Page) {
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await expect(page.getByRole("button", { name: "Save record", exact: true })).toHaveCount(0);
}
async function axe(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    result.violations.map((v) => ({ id: v.id, targets: v.nodes.map((n) => n.target) })),
  ).toEqual([]);
}
async function connect(page: Page) {
  await page.getByRole("button", { name: "Configure API" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("API origin").fill(origin ?? "");
  await dialog.getByLabel("Bearer token").fill(token ?? "");
  await dialog.getByRole("button", { name: "Connect & load capacity" }).click();
  await expect(page.getByText("Local API response loaded", { exact: true })).toBeVisible({
    timeout: 15000,
  });
}
async function exported(page: Page) {
  const waiting = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export scheduling JSON" }).click();
  const download = await waiting,
    stream = await download.createReadStream();
  const buffers = [];
  for await (const chunk of stream) buffers.push(chunk);
  return Buffer.concat(buffers).toString("utf8");
}

test("creates production data through forms, validates, activates, schedules and compares verified results", async ({
  page,
}) => {
  test.setTimeout(90000);
  const errors: string[] = [],
    paths: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.url().startsWith(`${origin}/api/v1`))
      paths.push(`${r.method()} ${new URL(r.url()).pathname}`);
  });
  await page.goto("/#/data");
  await page.getByLabel("Horizon start (with offset)", { exact: true }).fill(stamp("08:00"));
  await page.getByLabel("Horizon end (with offset)", { exact: true }).fill(stamp("09:00"));
  await page.getByLabel("Fixed calendar UTC offset (minutes)", { exact: true }).fill("180");
  await page
    .getByLabel("Synthetic planning assumptions (one per line)", { exact: true })
    .fill(
      "Entirely synthetic M07A browser input. Dedicated qualified crew; hypothetical standards and efficiency; no setup, shared labor, materials or initial WIP.",
    );
  await page.getByRole("button", { name: "Save planning assumptions" }).click();
  await expect(
    page.getByText("Planning assumptions saved. Continue with product styles."),
  ).toBeVisible();
  await step(page, "Product styles");
  await page.getByRole("button", { name: "Add product style", exact: true }).click();
  await page.getByLabel("Style name / ID", { exact: true }).fill("TEE-USER");
  await page.getByRole("button", { name: "Add stage standard" }).click();
  await page.getByLabel("Supported stage 1", { exact: true }).selectOption("sewing");
  await page
    .getByLabel("Standard worker-minutes per piece 1", { exact: true })
    .fill("2.5000000000000000000000000000");
  await axe(page);
  await save(page);
  await step(page, "Production orders");
  await page.getByRole("button", { name: "Add production order", exact: true }).click();
  await page.getByLabel("Order ID", { exact: true }).fill("ORDER-USER");
  await page.getByLabel("Product style", { exact: true }).selectOption("TEE-USER");
  await page.getByLabel("Quantity (pieces)", { exact: true }).fill("10");
  await page.getByLabel("Priority (1 is highest)", { exact: true }).fill("1");
  await page.getByLabel("Release date", { exact: true }).fill("2030-01-07");
  await page.getByLabel("Due date", { exact: true }).fill("2030-01-07");
  await page.getByLabel("Add required stage", { exact: true }).selectOption("sewing");
  await page.getByRole("button", { name: "Append stage" }).click();
  await save(page);
  await step(page, "Lines & capabilities");
  await page.getByRole("button", { name: "Add production line", exact: true }).click();
  await page.getByLabel("Line name / ID", { exact: true }).fill("SEW-USER");
  await page.getByLabel("Line stage", { exact: true }).selectOption("sewing");
  await page.getByLabel("Dedicated worker count", { exact: true }).fill("2");
  await page.getByLabel("Line availability", { exact: true }).selectOption("available");
  await save(page);
  await page.getByRole("button", { name: "Add line capability", exact: true }).click();
  await page.getByLabel("Production line", { exact: true }).selectOption("SEW-USER");
  await page.getByLabel("Qualified product style", { exact: true }).selectOption("TEE-USER");
  await page.getByLabel("Qualified stage", { exact: true }).selectOption("sewing");
  await page
    .getByLabel("Synthetic crew qualification basis", { exact: true })
    .fill("Synthetic dedicated crew assumed qualified for this style and stage.");
  await save(page);
  await step(page, "Capacity profiles");
  await page.getByRole("button", { name: "Add capacity profile", exact: true }).click();
  await page.getByLabel("Production line", { exact: true }).selectOption("SEW-USER");
  await page.getByLabel("Profile effective date", { exact: true }).fill("2030-01-07");
  await page
    .getByLabel("Assumed efficiency (0–1)", { exact: true })
    .fill("0.8000000000000000000000000000");
  await page
    .getByLabel("Synthetic assumption source", { exact: true })
    .fill("synthetic:m07a-browser");
  await page
    .getByLabel("Synthetic evidence reference (optional)", { exact: true })
    .fill("Explicit browser-test assumption, no factory measurement.");
  await save(page);
  await step(page, "Shifts & breaks");
  await page.getByRole("button", { name: "Add shift", exact: true }).click();
  await page.getByLabel("Shift name / ID", { exact: true }).fill("DAY-USER");
  await page.getByLabel("Shift start (with offset)", { exact: true }).fill(stamp("08:00"));
  await page.getByLabel("Shift end (with offset)", { exact: true }).fill(stamp("09:00"));
  await page.getByRole("button", { name: "Add break", exact: true }).click();
  await page.getByLabel("Break start (with offset) 1", { exact: true }).fill(stamp("08:20"));
  await page.getByLabel("Break end (with offset) 1", { exact: true }).fill(stamp("08:25"));
  await save(page);
  await step(page, "Production calendar");
  await page.getByLabel("Working date", { exact: true }).fill("2030-01-07");
  await page.getByRole("button", { name: "Add working date", exact: true }).click();
  await page.getByRole("button", { name: "Add shift assignment", exact: true }).click();
  await page.getByLabel("Production line", { exact: true }).selectOption("SEW-USER");
  await page.getByLabel("Declared shift", { exact: true }).selectOption("DAY-USER");
  await page.getByLabel("Capacity profile", { exact: true }).selectOption({ index: 1 });
  await save(page);
  await page.getByRole("button", { name: "Add planned downtime", exact: true }).click();
  await page.getByLabel("Affected assignment", { exact: true }).selectOption({ index: 1 });
  await page.getByLabel("Downtime start (with offset)", { exact: true }).fill(stamp("08:40"));
  await page.getByLabel("Downtime end (with offset)", { exact: true }).fill(stamp("08:45"));
  await page
    .getByLabel("Downtime reason", { exact: true })
    .fill("Synthetic maintenance assumption");
  await save(page);
  await page.getByRole("button", { name: "Add unavailable period", exact: true }).click();
  await page.getByLabel("Production line", { exact: true }).selectOption("SEW-USER");
  await page.getByLabel("Unavailable start (with offset)", { exact: true }).fill(stamp("08:50"));
  await page.getByLabel("Unavailable end (with offset)", { exact: true }).fill(stamp("08:55"));
  await page
    .getByLabel("Unavailability reason", { exact: true })
    .fill("Synthetic line unavailability");
  await save(page);
  await step(page, "Review & validate");
  await expect(page.getByRole("button", { name: "Export scheduling JSON" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Validate with local Python" })).toBeDisabled();
  expect(paths).toEqual([]);
  const created = await exported(page);
  expect(created).toContain('"standard_minutes_per_unit":2.5000000000000000000000000000');
  expect(created).toContain('"assumed_efficiency":0.8000000000000000000000000000');
  await writeFile(resolve("..", ".tmp/m07a/user-created-instance.json"), created);
  await connect(page);
  await page.getByRole("button", { name: "Validate with local Python", exact: true }).click();
  await expect(page.getByText("PYTHON VALIDATED", { exact: true })).toBeVisible({ timeout: 15000 });
  await axe(page);
  await page.getByRole("main").focus();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: resolve("..", ".tmp/frontend/m07a-review-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Activate validated copy", exact: true }).click();
  await expect(page.getByLabel("Planning dataset")).toHaveValue(/^user-/);
  await page.getByRole("link", { name: "Open production scheduling", exact: true }).click();
  const run = page.getByRole("button", { name: "Run reference scheduling", exact: true });
  await expect(run).toBeEnabled({ timeout: 15000 });
  await run.click();
  await expect(page.locator(".gantt-operation")).toHaveCount(1, { timeout: 15000 });
  await expect(
    page.getByRole("region", { name: "Verified production schedule operation table" }),
  ).toContainText("ORDER-USER");
  await expect(
    page.getByRole("region", { name: "Verified production schedule operation table" }),
  ).toContainText("16");
  await axe(page);
  await page.getByRole("main").focus();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: resolve("..", ".tmp/frontend/m07a-user-gantt.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "What-if scenarios", exact: true }).click();
  await page.getByLabel("Worker count (exact integer)").fill("3");
  await page.getByRole("button", { name: "Add change to review" }).click();
  await page.getByRole("button", { name: "Review exact specification" }).click();
  await page.getByRole("button", { name: "Run reviewed greedy comparison" }).click();
  await expect(page.locator(".comparison-headline")).toContainText("Better", { timeout: 15000 });
  await page.getByRole("link", { name: "Production scheduling", exact: true }).click();
  await page.getByRole("button", { name: "Submit bounded CP-SAT job" }).click();
  await expect(page.getByText("Verified job result", { exact: true })).toBeVisible({
    timeout: 25000,
  });
  expect(paths.filter((p) => p === "POST /api/v1/scheduling/validate")).toHaveLength(1);
  expect(paths.filter((p) => p === "POST /api/v1/scheduling/dispatch")).toHaveLength(1);
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(1);
  expect(created).not.toContain(token);
  expect(errors).toEqual([]);
});

test("local import/export is lossless and offline; bad imports leave the existing draft intact", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (r) => {
    if (r.url().startsWith(`${origin}/api/v1`)) calls.push(r.url());
  });
  const source = await readFile(resolve("..", "examples/scheduling/competition.json"), "utf8");
  await page.goto("/#/data");
  const importer = page.locator('input[type="file"]');
  await importer.setInputFiles({
    name: "synthetic.json",
    mimeType: "application/json",
    buffer: Buffer.from(source),
  });
  await expect(page.getByRole("heading", { name: "Review the complete input" })).toBeVisible();
  const result = await exported(page);
  expect(result).toBe(`${stringify(parse(source))}\n`);
  await expect(page.getByText("NOT AUTHORITATIVELY VALIDATED", { exact: true })).toBeVisible();
  await importer.setInputFiles({
    name: "inspection.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("record_id,json_pointer,source_sha256\na,b,c"),
  });
  await expect(page.getByRole("alert")).toContainText("CSV");
  expect(await exported(page)).toBe(result);
  await importer.setInputFiles({
    name: "oversized.json",
    mimeType: "application/json",
    buffer: Buffer.alloc(262145, 32),
  });
  await expect(page.getByRole("alert")).toContainText("256 KiB");
  expect(calls).toEqual([]);
  for (const viewport of [
    { width: 820, height: 1100 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await axe(page);
    await page.getByRole("main").focus();
    await page.evaluate(() => window.scrollTo(0, 0));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: resolve("..", `.tmp/frontend/m07a-data-${viewport.width}.png`),
      fullPage: true,
    });
  }
});

// Existing workflow assertions explicitly exercise the selectable English locale.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("loometric.language", "en-US");
  });
});
