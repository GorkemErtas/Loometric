import { createHash, randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";
import { parse, stringify } from "lossless-json";
import sources from "../fixtures/sources.json" with { type: "json" };

const origin = process.env.LOOMETRIC_BROWSER_ORIGIN;
const token = process.env.LOOMETRIC_BROWSER_TOKEN;
if (!origin || !token)
  throw new Error("Run npm run test:browser to own the bounded local session.");
const headers = {
  Authorization: `Bearer ${token}`,
  Origin: "http://127.0.0.1:5173",
  "Content-Type": "application/json",
};
const read = (path: string) => readFileSync(resolve("..", path), "utf8");
const capture = (name: string) => resolve("..", ".tmp", "frontend", `${name}.png`);
async function configure(page: Page, secret = token) {
  await page.getByRole("button", { name: "Configure API" }).click();
  const dialog = page.getByRole("dialog", { name: "Connect to local API" });
  await dialog.getByLabel("API origin").fill(origin ?? "");
  await dialog.getByLabel("Bearer token").fill(secret ?? "");
  await dialog.getByRole("button", { name: "Connect & load capacity" }).click();
}
async function accessible(page: Page) {
  const focused = await page.evaluateHandle(() => document.activeElement);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  await focused.evaluate((element) => {
    if (element instanceof HTMLElement) element.focus({ preventScroll: true });
  });
  await focused.dispose();
  expect(
    results.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })),
  ).toEqual([]);
}

test("real M05A responses match both saved report fixtures and exact planning decimals", async ({
  request,
}) => {
  for (const source of [sources.capacity, sources.competition]) {
    const input = read(source.file);
    expect(
      createHash("sha256").update(read(source.file).replaceAll("\r\n", "\n")).digest("hex"),
    ).toBe(source.sha256);
    const planning =
      source === sources.capacity
        ? input
        : stringify((parse(input) as { planning: unknown }).planning);
    const result = await request.post(`${origin}/api/v1/planning/capacity`, {
      headers,
      data: `{"scenario":${planning}}`,
    });
    expect(result.status()).toBe(200);
    expect(result.headers()["access-control-allow-origin"]).toBe("http://127.0.0.1:5173");
    const body = parse(await result.text()) as { data: unknown };
    const snapshot =
      source === sources.capacity ? "capacity-demo.report.json" : "competition.capacity.json";
    expect(body.data).toEqual(parse(read(`frontend/fixtures/${snapshot}`)));
  }
  const precise = read(sources.capacity.file).replace(
    '"assumed_efficiency": 0.9',
    '"assumed_efficiency": 0.1234567890123456789012345678',
  );
  expect(precise).not.toBe(read(sources.capacity.file));
  const result = await request.post(`${origin}/api/v1/planning/capacity`, {
    headers,
    data: `{"scenario":${precise}}`,
  });
  expect(result.status()).toBe(200);
  expect(await result.text()).toContain('"assumed_efficiency":"0.1234567890123456789012345678"');
});

test("five pages, real API session, explicit verified outcome and clearing credentials", async ({
  page,
}) => {
  const errors: string[] = [];
  const externalRequests: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (!new URL(request.url()).hostname.match(/^(127\.0\.0\.1|localhost)$/))
      externalRequests.push("external request");
  });
  await page.goto("/#/overview");
  await expect(
    page.locator(".stat").filter({ hasText: "Requested units" }).locator(".stat-value"),
  ).toContainText("480");
  await expect(page.getByText("Fixture preview", { exact: true })).toBeVisible();
  await accessible(page);
  await page.screenshot({ path: capture("overview-desktop"), fullPage: true });
  await page.getByRole("link", { name: "Orders", exact: true }).click();
  await page.getByRole("searchbox").fill("O-MULTI");
  await page.getByRole("button", { name: "Inspect O-MULTI" }).click();
  await expect(page.getByRole("dialog")).toContainText("FIN-01");
  await accessible(page);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Inspect O-MULTI" })).toBeFocused();
  await page.getByRole("searchbox").clear();
  await accessible(page);
  await page.screenshot({ path: capture("orders-desktop"), fullPage: true });
  await page.getByRole("link", { name: "Production resources", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Planned downtime" })).toBeVisible();
  await accessible(page);
  await page.getByRole("link", { name: "Capacity", exact: true }).click();
  await expect(page.getByText("Independent assessment only.")).toBeVisible();
  await accessible(page);
  await page.screenshot({ path: capture("capacity-desktop"), fullPage: true });
  await configure(page);
  await expect(page.getByText("Local API response loaded", { exact: true })).toBeVisible({
    timeout: 20000,
  });
  await expect(page.getByText("API response", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "API & system", exact: true }).click();
  await expect(page.getByText("v1", { exact: true })).toBeVisible();
  await expect(page.getByText("max_body_bytes", { exact: true })).toBeVisible();
  await accessible(page);
  await page.screenshot({ path: capture("system-api"), fullPage: true });
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await page.getByLabel("Planning dataset").selectOption("competition");
  await expect(page.locator(".capacity-bar-row")).toHaveCount(1);
  await expect(page.getByText("Completed units", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Load saved outcome" }).click();
  await expect(page.getByText("VALID_PARTIAL", { exact: true })).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("Completed units", { exact: true })).toBeVisible();
  await expect(page.getByText("46.875%", { exact: true })).toHaveCount(2);
  await accessible(page);
  await page.screenshot({ path: capture("verified-existing-outcome"), fullPage: true });
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
  ).toEqual({ local: 0, session: 0 });
  expect(await page.content()).not.toContain(token);
  await page.getByRole("link", { name: "API & system", exact: true }).click();
  await page.getByRole("button", { name: "Clear session & use fixture preview" }).click();
  await expect(page.getByText("Capabilities not loaded")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Capabilities not loaded")).toBeVisible();
  expect(errors).toEqual([]);
  expect(externalRequests).toEqual([]);
});

test("keyboard focus, tablet/mobile layout, authentication and network error states", async ({
  page,
}) => {
  await page.goto("/#/orders");
  await page.getByRole("button", { name: "Skip to content" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
  expect(new URL(page.url()).hash).toBe("#/orders");
  await page.getByRole("button", { name: "Configure API" }).click();
  const dialog = page.getByRole("dialog");
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  await expect(dialog.locator(":focus")).toHaveCount(1);
  await accessible(page);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Configure API" })).toBeFocused();
  await page.setViewportSize({ width: 820, height: 1100 });
  await page.goto("/#/overview");
  await accessible(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: capture("overview-tablet"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "Capacity", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Capacity" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await accessible(page);
  await page.screenshot({ path: capture("capacity-mobile"), fullPage: true });
  await configure(page, randomBytes(32).toString("base64url"));
  await expect(page.getByRole("alert")).toContainText("session was rejected", { timeout: 15000 });
  await expect(page.locator(".capacity-bar-row")).toHaveCount(0);
  await page.route(`${origin}/**`, (route) => route.abort());
  await configure(page);
  await expect(page.getByRole("alert")).toContainText("unreachable", { timeout: 15000 });
  await accessible(page);
});

test("development filesystem denies raw data, local instructions and model artifacts", async ({
  request,
}) => {
  for (const path of [
    "AGENTS.md",
    "docs/COMMIT_PLAN.md",
    "data/raw/garments_worker_productivity.csv",
    ".git/config",
  ]) {
    const blocked = await request.get(`/@fs/${resolve("..", path).replaceAll("\\", "/")}`);
    expect([403, 404]).toContain(blocked.status());
  }
});
