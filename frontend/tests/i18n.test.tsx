import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App";
import { ApiError, validationGuidance } from "../src/api/client";
import { ErrorNotice } from "../src/components/ui";
import { datasets } from "../src/demo/catalog";
import {
  clockLabel,
  dateLabel,
  formatExact,
  percentExact,
  percentValueExact,
} from "../src/domain/exact";
import { metricDefinitions } from "../src/domain/planning";
import {
  fields,
  historyIssues,
  initialInputs,
  inputIssues,
  modelLabels,
} from "../src/domain/predictions";
import { exportInput, importInput } from "../src/domain/production";
import { codeLabels } from "../src/i18n/codes";
import { createI18n, I18nProvider } from "../src/i18n/I18n";
import { languageStorageKey, readLocale } from "../src/i18n/locale";
import { messages } from "../src/i18n/messages";
import { hasMessage } from "../src/i18n/translate";
import { routes } from "../src/layout/Layout";

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  window.history.replaceState(null, "", "/#/overview");
});
afterEach(() => vi.restoreAllMocks());

describe("translation contracts", () => {
  it("has complete UTF-8 Turkish messages and identical interpolation parameters", () => {
    const parameters = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    for (const [english, turkish] of Object.entries(messages)) {
      expect(turkish.trim(), english).not.toBe("");
      expect(turkish, english).not.toMatch(/\ufffd|Ã.|â€/);
      expect(parameters(turkish), english).toEqual(parameters(english));
    }
  });

  it("covers every route, field, metric, API guidance and static form label", () => {
    const labels = [
      ...routes.flatMap((r) => [r.label, r.description]),
      ...fields.flatMap(([, label, help]) => [label, help]),
      ...metricDefinitions.map(([, label]) => label),
      ...Object.values(validationGuidance),
      ...Object.values(codeLabels),
      ...datasets.flatMap((dataset) => [dataset.name, dataset.description]),
    ];
    for (const dir of ["components", "layout", "pages"]) {
      for (const file of readdirSync(resolve("src", dir)).filter((f) => f.endsWith(".tsx"))) {
        const source = readFileSync(resolve("src", dir, file), "utf8");
        for (const m of source.matchAll(/\b(?:label|help|description):\s*("(?:[^"\\]|\\.)*")/g))
          labels.push(JSON.parse(m[1] ?? '""'));
      }
    }
    for (const label of labels) expect(hasMessage(label), label).toBe(true);
  });

  it("maps supported codes without changing enum values or model names", () => {
    const tr = createI18n("tr-TR"),
      en = createI18n("en-US");
    expect(tr.codeLabel("VALID_PARTIAL")).toBe("Geçerli kısmi çizelge");
    expect(tr.codeLabel("ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET")).toContain("kapasite sıfır");
    expect(tr.codeLabel("OUTSIDE_TRAINING_SUPPORT:planned_workers")).toBe(
      "Eğitim desteği dışında: Planlanan işçi sayısı",
    );
    expect(en.codeLabel("REVIEW_REQUIRED")).toBe("Review required");
    expect(tr.codeLabel("FUTURE_CODE")).toBe("Tanınmayan durum (FUTURE_CODE)");
    for (const name of Object.values(modelLabels)) expect(tr.label(name)).toBe(name);
  });

  it("localizes existing dynamic validator messages at display time", () => {
    const tr = createI18n("tr-TR");
    const issue = inputIssues({ ...initialInputs, planned_workers: 101 })[0];
    expect(tr.validationMessage(issue ?? "")).toBe(
      "Planlanan işçi sayısı için 0–100 aralığında tam sayı gerekir.",
    );
    expect(
      tr.validationMessage("Label must be nonblank canonical text without control characters."),
    ).toContain("Etiket");
    expect(
      tr.validationMessage("Instance.planning.orders[0].quantity: Enter a whole integer count."),
    ).toBe("Instance.planning.orders[0].quantity: Tam sayı adet girin.");
    for (const issue of historyIssues({
      recent_attainment_mean: null,
      recent_attainment_std: null,
      history_count: 9,
      uncensored_history_count: 0,
      history_age_hours: null,
    }))
      expect(tr.validationMessage(issue)).not.toBe(issue);
    expect(tr.t("Order {p0}", { p0: "ÇİĞ-{p1}-<b>" })).toBe("Sipariş ÇİĞ-{p1}-<b>");
  });
});

describe("locale formatting and data integrity", () => {
  it.each(["tr-TR", "en-US"] as const)(
    "preserves large counts and all decimal digits in %s",
    (locale) => {
      const value = "90071992547409931234567890.1234567890123456789012345678";
      const actual = formatExact(value, locale);
      expect(actual.replaceAll(locale === "tr-TR" ? "." : ",", "").replace(",", ".")).toBe(value);
      expect(percentExact("0.46875", locale)).toBe(locale === "tr-TR" ? "%46,875" : "46.875%");
    },
  );
  it("uses Intl for numbers, percentages, dates and source wall clocks", () => {
    const tr = createI18n("tr-TR");
    expect(tr.number(12345.678, 3)).toBe("12.345,678");
    expect(tr.percent(0.12345, 2)).toBe("%12,35");
    expect(percentValueExact("-12.123456789012345678901", "tr-TR")).toBe(
      "-%12,123456789012345678901",
    );
    expect(formatExact("-0.000000001", "tr-TR")).toBe("-0,000000001");
    expect(dateLabel("2030-02-03", "tr-TR")).toBe("03 Şub 2030");
    expect(clockLabel("2030-02-03T00:30:00+03:00", "tr-TR")).toBe("03 Şub 2030, 00:30 +03:00");
    expect(clockLabel("2030-02-03T23:30:00-05:00", "tr-TR")).toBe("03 Şub 2030, 23:30 -05:00");
  });
  it("leaves Turkish user text, identifiers, exact tokens and exported JSON unchanged", () => {
    const raw = readFileSync(resolve("..", "examples/scenarios/capacity-baseline.json"), "utf8");
    const input = importInput(raw);
    (input.planning as { assumptions: string[] }).assumptions = [
      "ŞİŞE üretimi, çığ ve ölçü; Overview {p0}",
    ];
    const before = exportInput(input);
    createI18n("tr-TR").dateLabel("2030-01-07");
    createI18n("en-US").number(12345);
    expect(exportInput(importInput(before))).toBe(before);
    expect(before).toContain("ŞİŞE üretimi");
    expect(before).toContain('"sewing"');
  });
});

describe("language lifecycle", () => {
  it("defaults to Turkish without persisting anything and switches document metadata", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "Genel bakış" })).toBeVisible();
    expect(document.documentElement.lang).toBe("tr-TR");
    expect(localStorage.length).toBe(0);
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    expect(screen.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
    expect(document.title).toBe("Overview · Loometric");
    expect(document.documentElement.lang).toBe("en-US");
    expect(localStorage.length).toBe(1);
    expect(localStorage.getItem(languageStorageKey)).toBe("en-US");
    expect(sessionStorage.length).toBe(0);
    cleanup();
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
  });
  it.each(["fr-FR", "TR", "null", "", '{"token":"ignored"}'])(
    "uses Turkish for unsupported preference %s",
    (stored) => {
      localStorage.setItem(languageStorageKey, stored);
      expect(readLocale()).toBe("tr-TR");
    },
  );
  it("keeps switching usable when storage reads and writes throw", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    expect(document.documentElement.lang).toBe("en-US");
  });
  it("preserves prediction edits and selection while translating field/help text", () => {
    window.history.replaceState(null, "", "/#/predictions");
    render(<App />);
    fireEvent.change(screen.getByLabelText("Planlanan işçi sayısı"), { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText("Model", { exact: true }), { target: { value: "all" } });
    fireEvent.change(screen.getByLabelText("Olgunlaşmış geçmiş rapor sayısı"), {
      target: { value: "7" },
    });
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    expect(screen.getByLabelText("Planned workers")).toHaveValue(9);
    expect(screen.getByLabelText("Model", { exact: true })).toHaveValue("all");
    expect(screen.getByLabelText("Mature history count")).toHaveValue(7);
    fireEvent.click(screen.getByRole("button", { name: "Türkçe" }));
    expect(screen.getByLabelText("Planlanan işçi sayısı")).toHaveValue(9);
    expect(screen.getByRole("option", { name: "Kalite kontrol" })).toHaveValue("quality_control");
  });
  it("localizes a retained API error without displaying server diagnostics", () => {
    const error = new ApiError("server", 503, null, null, "EXPERIMENTAL_ARTIFACT_UNAVAILABLE");
    const { rerender } = render(
      <I18nProvider initialLocale="tr-TR">
        <ErrorNotice error={error} />
      </I18nProvider>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Güvenilir deneysel model dosyaları kullanılamıyor",
    );
    rerender(
      <I18nProvider key="en" initialLocale="en-US">
        <ErrorNotice error={error} />
      </I18nProvider>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Trusted experimental model artifacts unavailable",
    );
  });
  it("localizes native required-field validity and clears it after editing", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "API ayarları" }));
    const token = screen.getByLabelText("Bearer anahtarı") as HTMLInputElement;
    expect(token.checkValidity()).toBe(false);
    expect(token.validationMessage).toBe("Bu zorunlu alanı doldurun.");
    fireEvent.input(token, { target: { value: "a".repeat(32) } });
    expect(token.checkValidity()).toBe(true);
  });
});
