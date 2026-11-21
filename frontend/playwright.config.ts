import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./browser",
  outputDir: "../.tmp/frontend/browser-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45000,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: process.platform === "win32" ? "msedge" : "chromium",
    headless: true,
    viewport: { width: 1440, height: 1050 },
    trace: "off",
    video: "off",
    screenshot: "off",
  },
});
