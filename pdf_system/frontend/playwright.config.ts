import { defineConfig } from "@playwright/test";
import { randomBytes } from "node:crypto";
process.env.SE_SMOKE_ADMIN_PASSWORD ??= randomBytes(16).toString("hex") + "A1";
export default defineConfig({
  timeout: 30_000,
  fullyParallel: true,
  workers: 2,
  reporter: [
    ["list"],
    ["html", { open: "never" }],
    ["json", { outputFile: "test-results/browser-results.json" }],
  ],
  use: {
    ...(process.env.PLAYWRIGHT_CHANNEL
      ? { channel: process.env.PLAYWRIGHT_CHANNEL }
      : {}),
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "contract",
      testDir: "./e2e",
      use: { baseURL: "http://127.0.0.1:5174" },
    },
    {
      name: "real-api",
      testDir: "./e2e-live",
      use: { baseURL: "http://127.0.0.1:5175" },
    },
  ],
  webServer: [
    {
      command: `"${process.execPath}" scripts/start-test-api.mjs`,
      url: "http://127.0.0.1:8015/__smoke_ready",
      reuseExistingServer: false,
      timeout: 45000,
    },
    {
      command: `"${process.execPath}" scripts/start-test-vite.mjs`,
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      timeout: 45000,
      env: { SE_TEST_PORT: "5174", SE_CONTRACT_TEST: "1" },
    },
    {
      command: `"${process.execPath}" scripts/start-test-vite.mjs`,
      url: "http://127.0.0.1:5175",
      reuseExistingServer: false,
      timeout: 45000,
      env: { SE_TEST_PORT: "5175", SE_API_TARGET: "http://127.0.0.1:8015" },
    },
  ],
});
