// Takes the README screenshots from the seeded end-to-end stack (demo data: a recorded Sleeper
// league and an invented NFL week; no real person's league).
//
//   npm run e2e:up && npm run screenshots     (set PW_CHANNEL=msedge on Windows)
//
// Writes PNGs to ../docs/screenshots.
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { chromium, devices } from "@playwright/test";

import { closeDb, newConnectedUser } from "../e2e/support/helpers.ts";

const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:13000";
const channel = process.env.PW_CHANNEL || undefined;
const out = fileURLToPath(new URL("../../docs/screenshots/", import.meta.url));
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel });
const screens = [
  ["home", "/"],
  ["matchup", "/matchup"],
  ["lineup", "/lineup"],
  ["accuracy", "/accuracy"],
] as const;

for (const [kind, device] of [
  // Phone captures are left out until backlog U-13 (header overlap at 390px) is fixed.
  ["desktop", { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } }],
] as const) {
  const context = await browser.newContext({ ...device, baseURL, colorScheme: "dark" });
  const page = await context.newPage();
  await newConnectedUser(page, `shots-${kind}`);
  for (const [name, path] of screens) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800); // let fonts and headshots settle
    await page.screenshot({ path: `${out}${name}-${kind}.png`, fullPage: false });
    console.log(`${name}-${kind}.png`);
  }
  await context.close();
}
await browser.close();
await closeDb();
