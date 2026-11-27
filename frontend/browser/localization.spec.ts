import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";
import { messages } from "../src/i18n/messages";

const routes = [
  { key: "predictions", label: "AI Predictions" },
  { key: "data", label: "Production data" },
  { key: "overview", label: "Overview" },
  { key: "orders", label: "Orders" },
  { key: "resources", label: "Production resources" },
  { key: "capacity", label: "Capacity" },
  { key: "scheduling", label: "Production scheduling" },
  { key: "scenarios", label: "What-if scenarios" },
  { key: "jobs", label: "Optimization jobs" },
  { key: "system", label: "API & system" },
] as const;

const origin = process.env.LOOMETRIC_BROWSER_ORIGIN;
const token = process.env.LOOMETRIC_BROWSER_TOKEN;
if (!origin || !token) throw new Error("Use the owned browser harness.");
const screenshot = (name: string) => resolve("..", ".tmp/frontend", `${name}.png`);

async function layout(page: Page) {
  const overflow = await page.evaluate(() => ({
    fits: document.documentElement.scrollWidth <= innerWidth,
    width: document.documentElement.scrollWidth,
    viewport: innerWidth,
    scrollX,
    wide: [
      ...document.querySelectorAll(
        ".app-shell, .workspace-shell, main, .table-scroll, .panel, .sr-only",
      ),
    ]
      .filter((e) => e.scrollWidth > e.clientWidth)
      .map((e) => ({
        tag: e.tagName,
        cls: e.className,
        width: e.clientWidth,
        scroll: e.scrollWidth,
        right: e.getBoundingClientRect().right,
        overflow: getComputedStyle(e).overflowX,
      })),
    elements: [...document.querySelectorAll(".app-shell *")]
      .filter(
        (e) =>
          e.getBoundingClientRect().right > innerWidth + 1 &&
          !e.closest(".table-scroll,.json-scroll,.sidebar,.gantt-figure"),
      )
      .map((e) => `${e.tagName}.${e.className}`)
      .slice(0, 15),
  }));
  expect(overflow.fits, `${new URL(page.url()).hash}: ${JSON.stringify(overflow)}`).toBe(true);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(result.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) }))).toEqual(
    [],
  );
}
async function translated(page: Page) {
  const english = Object.entries(messages)
    .filter(([en, tr]) => en !== tr && !en.includes("{"))
    .map(([en]) => en);
  const untranslated = await page.evaluate((english) => {
    const walker = document.createTreeWalker(
      document.querySelector(".app-shell") ?? document.body,
      NodeFilter.SHOW_TEXT,
    );
    const result: string[] = [];
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const parent = node.parentElement;
      if (
        !parent ||
        parent.closest("pre,code,script,style,input,textarea") ||
        !parent.getClientRects().length
      )
        continue;
      const value = node.textContent?.trim() ?? "";
      if (english.includes(value)) result.push(value);
    }
    return result;
  }, english);
  expect(untranslated).toEqual([]);
  await expect(page.locator(".source-strip")).not.toContainText(/M0[1-9][A-C]?/);
}
async function connectEnglish(page: Page) {
  await page.getByRole("button", { name: "English" }).click();
  await page.getByRole("button", { name: "Configure API" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("API origin").fill(origin ?? "");
  await dialog.getByLabel("Bearer token").fill(token ?? "");
  await dialog.getByRole("button", { name: "Connect & load capacity" }).click();
  await expect(page.getByText("Local API response loaded", { exact: true })).toBeAttached({
    timeout: 15000,
  });
}

for (const viewport of [
  { width: 1440, height: 1050 },
  { width: 390, height: 844 },
]) {
  test(`all ten pages switch cleanly at ${viewport.width}px with Turkish as default`, async ({
    page,
  }) => {
    test.setTimeout(90000);
    await page.setViewportSize(viewport);
    await page.goto("/#/overview");
    await expect(page.locator("html")).toHaveAttribute("lang", "tr-TR");
    expect(await page.evaluate(() => localStorage.length)).toBe(0);
    for (const route of routes) {
      await page.goto(`/#/${route.key}`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(messages[route.label]);
      await translated(page);
      await layout(page);
      await page.getByRole("button", { name: "English" }).click();
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(route.label);
      await layout(page);
      await page.getByRole("button", { name: "Türkçe" }).click();
    }
    if (viewport.width === 390) {
      await page.getByRole("button", { name: "Gezinme menüsünü aç/kapat" }).click();
      await page.getByRole("link", { name: "Siparişler", exact: true }).click();
      await expect(page.getByRole("heading", { level: 1 })).toHaveText("Siparişler");
      await page.getByRole("button", { name: "English" }).click();
      await page.reload();
      await expect(page.getByRole("heading", { level: 1 })).toHaveText("Orders");
    } else {
      await page.goto("/#/overview");
      await page.screenshot({ path: screenshot("localization-overview-tr"), fullPage: true });
      await page.getByRole("button", { name: "English" }).click();
      await page.screenshot({ path: screenshot("localization-overview-en"), fullPage: true });
    }
    expect(await page.evaluate(() => ({ ...localStorage }))).toEqual({
      "loometric.language": "en-US",
    });
  });
}

test("all five real model results switch language without another request, with desktop/mobile evidence", async ({
  page,
}) => {
  test.setTimeout(75000);
  const bodies: unknown[] = [],
    errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().includes("/predictions/"))
      bodies.push(JSON.parse(r.postData() ?? "{}"));
  });
  await page.goto("/#/predictions");
  await connectEnglish(page);
  await page.getByLabel("Model", { exact: true }).selectOption("all");
  for (const [name, value] of [
    ["Mature history count", "7"],
    ["Uncensored history count", "4"],
    ["Recent uncensored attainment mean", "0.85"],
    ["Recent uncensored attainment standard deviation", "0.1"],
    ["Latest mature report age (hours)", "16"],
  ] as const)
    await page.getByLabel(name, { exact: true }).fill(value);
  await page
    .getByRole("checkbox", { name: /I am testing hypothetical synthetic pre-shift conditions/ })
    .check();
  await page.getByRole("button", { name: "Türkçe" }).click();
  const response = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/predictions/synthetic/v3"),
  );
  await page.getByRole("button", { name: "Tahmin et", exact: true }).click();
  const data = (await (await response).json()).data;
  expect(data.results.map((r: { prediction: number }) => r.prediction)).toEqual([
    0.9036296370677777, 0.8945601867754494, 0.7628348220475517, 0.8919168184750277,
    0.834534223925279,
  ]);
  expect(data.promotion_decision).toBe("NO_ML_PROMOTION");
  expect(data.capacity_application_authorized).toBe(false);
  expect(data.differences).toHaveLength(10);
  await expect(page.getByRole("article", { name: "History Boost sonucu" })).toContainText(
    "0,83453",
  );
  await translated(page);
  await expect(page.locator("main")).not.toContainText("Tanınmayan durum");
  await layout(page);
  const heading = page.getByRole("heading", {
    name: "Yeni dünyalarda eşleştirilmiş bulgular · EXP-010",
  });
  await heading.evaluate((element) => element.scrollIntoView({ block: "start" }));
  await page.locator(".table-scroll").evaluateAll((elements) => {
    for (const element of elements) element.scrollLeft = 0;
  });
  await page.screenshot({ path: screenshot("localized-predictions-desktop-tr") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("article", { name: "History Boost sonucu" }).scrollIntoViewIfNeeded();
  await layout(page);
  await page.screenshot({ path: screenshot("localized-predictions-mobile-tr") });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.getByRole("article", { name: "History Boost result" })).toContainText(
    "0.83453",
  );
  await page.getByRole("article", { name: "History Boost result" }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: screenshot("localized-predictions-mobile-en") });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page
    .getByRole("heading", { name: "Matched fresh-world evidence · EXP-010" })
    .evaluate((element) => element.scrollIntoView({ block: "start" }));
  await page.locator(".table-scroll").evaluateAll((elements) => {
    for (const element of elements) element.scrollLeft = 0;
  });
  await page.screenshot({ path: screenshot("localized-predictions-desktop-en") });
  expect(bodies).toHaveLength(1);
  expect(bodies[0]).toMatchObject({
    schema_version: 3,
    synthetic: true,
    prediction_context: "HYPOTHETICAL_PRE_SHIFT",
    models: [
      "random_forest",
      "histogram_gradient_boosting",
      "grouped_mean",
      "rf_physics",
      "history_boost",
    ],
    inputs: { stage: "sewing", shift_kind: "day", planned_workers: 6 },
    history: {
      history_count: 7,
      uncensored_history_count: 4,
      recent_attainment_mean: 0.85,
      recent_attainment_std: 0.1,
      history_age_hours: 16,
    },
  });
  expect(Object.keys(bodies[0] as object).sort()).toEqual([
    "history",
    "inputs",
    "models",
    "prediction_context",
    "schema_version",
    "synthetic",
  ]);
  expect(await page.evaluate(() => ({ ...localStorage }))).toEqual({
    "loometric.language": "en-US",
  });
  expect(await page.evaluate(() => sessionStorage.length)).toBe(0);
  expect(await page.content()).not.toContain(token);
  await page.reload();
  await expect(page.getByText("API disconnected", { exact: true })).toBeAttached();
  await expect(page.getByLabel("Planned workers", { exact: true })).toHaveValue("6");
  expect(errors).toEqual([]);
});

test("Turkish order modal, errors and Turkish user text survive switching", async ({ page }) => {
  await page.goto("/#/orders");
  await page.getByRole("searchbox").fill("O-MULTI");
  await page.getByRole("button", { name: "O-MULTI incele", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("Tanımlı rota uyumluluğu");
  await layout(page);
  await page.keyboard.press("Escape");
  await page.getByRole("searchbox").fill("eşleşmeyen-ŞİĞ");
  await expect(page.getByText("Eşleşen sipariş yok", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.getByRole("searchbox")).toHaveValue("eşleşmeyen-ŞİĞ");
  await expect(page.getByText("No matching orders", { exact: true })).toBeVisible();
  await page.goto("/#/data");
  await page.getByRole("button", { name: "Türkçe" }).click();
  const assumptions = page.getByLabel("Sentetik planlama varsayımları (her satıra bir tane)");
  await assumptions.fill("ŞİŞE üretimi; çığ, ölçü, güvenilirlik {p0}");
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.getByLabel("Synthetic planning assumptions (one per line)")).toHaveValue(
    "ŞİŞE üretimi; çığ, ölçü, güvenilirlik {p0}",
  );
  await page.getByRole("button", { name: "Discard unsaved changes" }).click();
  await page.getByRole("button", { name: "Configure API" }).click();
  await page.getByLabel("API origin").fill(origin ?? "");
  await page.getByLabel("Bearer token").fill("x".repeat(32));
  await page.getByRole("button", { name: "Connect & load capacity" }).click();
  await page.getByRole("link", { name: "API & system", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("session was rejected");
  await page.getByRole("button", { name: "Türkçe" }).click();
  await expect(page.getByRole("alert")).toContainText("Yerel oturum reddedildi");
  await translated(page);
});

test("Turkish production forms retain exact decimals, Turkish identifiers and export contracts across a switch", async ({
  page,
}) => {
  await page.goto("/#/data");
  await page.getByLabel("Yeniden kullanılabilir girdi şablonu").selectOption("competition");
  await page.getByRole("button", { name: "Şablon kopyasını düzenle" }).click();
  await page.getByRole("button", { name: "Taslağı değiştir", exact: true }).click();
  await page
    .getByLabel("Sentetik planlama varsayımları (her satıra bir tane)")
    .fill("ŞİŞE üretimi; çığ, ölçü ve güvenilirlik {p0}");
  await page.getByRole("button", { name: "Planlama varsayımlarını kaydet" }).click();
  await page.getByRole("button", { name: /Ürün modelleri/ }).click();
  await page.getByRole("button", { name: "ürün modeli ekle", exact: true }).click();
  await page.getByLabel("Ürün modeli adı / kimliği").fill("ÜRÜN-ŞĞİ");
  await page.getByRole("button", { name: "Aşama standardı ekle" }).click();
  await page.getByLabel("Desteklenen aşama 1").selectOption("sewing");
  await page.getByLabel("Adet başına standart işçi-dakika 1").fill("2.500000000000000000001");
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.getByLabel("Style name / ID")).toHaveValue("ÜRÜN-ŞĞİ");
  await expect(page.getByLabel("Standard worker-minutes per piece 1")).toHaveValue(
    "2.500000000000000000001",
  );
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export scheduling JSON" }).click();
  const download = await pending;
  const file = await download.path();
  expect(file).not.toBeNull();
  const content = readFileSync(file ?? "", "utf8");
  expect(content).toContain("ŞİŞE üretimi; çığ, ölçü ve güvenilirlik {p0}");
  expect(content).toContain('"style_id":"ÜRÜN-ŞĞİ"');
  expect(content).toContain('"standard_minutes_per_unit":2.500000000000000000001');
  expect(content).toContain('"stage":"sewing"');
  expect(content).toContain('"measurement_unit":"worker_minutes_per_piece"');
  await page.getByRole("button", { name: "Türkçe" }).click();
  await expect(page.locator(".production-records")).toContainText("2,500000000000000000001");
  expect(await page.evaluate(() => ({ ...localStorage }))).toEqual({
    "loometric.language": "tr-TR",
  });
  await layout(page);
});
