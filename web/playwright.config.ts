import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests (ADR-019, ADR-040): a real browser against the full Docker stack.
 *
 *   npm run e2e:up      start the stack (db, redis, api, worker, web + a stand-in Sleeper, seeded)
 *   npm run e2e         run the tests
 *   npm run e2e:down    stop it
 *
 * PW_CHANNEL=msedge uses the Edge already installed on Windows (no browser download).
 * CI uses Playwright's own Chromium.
 */
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:13000";
const channel = process.env.PW_CHANNEL || undefined;
const storageState = "e2e/.auth/user.json";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./e2e/.results",
  // One shared database, and tests that depend on its state: run one at a time, in order.
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL,
    channel,
    colorScheme: "dark", // the app follows the system setting; "dark" is its first-visit default
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    // 1. A new person signs in and connects a league; saves the signed-in state for the rest.
    { name: "setup", testMatch: /onboarding\.setup\.ts/, use: { ...devices["Desktop Chrome"], channel } },
    // 2. Every screen, as that person, on a laptop.
    {
      name: "desktop",
      testMatch: /(screens|accessibility)\.spec\.ts/,
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"], channel, storageState },
    },
    // 3. The same screens on a phone.
    {
      name: "mobile",
      testMatch: /mobile\.spec\.ts/,
      dependencies: ["setup"],
      use: { ...devices["iPhone 14"], defaultBrowserType: "chromium", channel, storageState },
    },
    // 4. Things that change data or sign people out, each with its own throwaway user.
    {
      name: "actions",
      testMatch: /(actions|isolation|pwa)\.spec\.ts/,
      dependencies: ["desktop", "mobile"],
      use: { ...devices["Desktop Chrome"], channel },
    },
  ],
});
