/**
 * The installable-app behavior in a real browser: manifest and icons, the service worker taking
 * control, what it keeps (only fixed files, never data), and the offline screen.
 * (Verification Gaps V-20, V-21.) Installing onto a real phone is checked by hand.
 */
import { mkdirSync } from "node:fs";

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { closeDb, newConnectedUser } from "./support/helpers";

const SHOTS = "e2e/.results/pwa";
test.afterAll(closeDb);

const PRECACHED = ["/offline.html", "/icons/icon-192.png", "/icons/icon-512.png"];

test("the manifest and every icon it names are served", async ({ page }) => {
  await page.goto("/sign-in");
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute("href", "/manifest.webmanifest");
  const manifest = await (await page.request.get("/manifest.webmanifest")).json();
  expect(manifest).toMatchObject({ name: "Sunday War Room", display: "standalone", start_url: "/" });
  for (const icon of manifest.icons) {
    const res = await page.request.get(icon.src);
    expect(res.status(), icon.src).toBe(200);
    expect(res.headers()["content-type"], icon.src).toContain(icon.type);
  }
  await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveCount(1);
  const worker = await page.request.get("/sw.js");
  expect(worker.headers()["cache-control"]).toContain("no-store"); // updates must always be noticed
  expect(worker.headers()["content-type"]).toContain("javascript");
});

test("the service worker takes control and keeps only fixed files, never data or pages", async ({ page }) => {
  await newConnectedUser(page, "pwa");
  await page.goto("/");
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload(); // now controlled by the worker
  expect(await page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
  for (const path of ["/lineup", "/matchup", "/accuracy", "/settings"]) {
    await page.goto(path);
    await expect(page.getByRole("heading").first()).toBeVisible();
    await page.waitForLoadState("networkidle");
  }

  const kept = await page.evaluate(async () => {
    const paths: string[] = [];
    for (const name of await caches.keys()) {
      for (const request of await (await caches.open(name)).keys()) paths.push(new URL(request.url).pathname);
    }
    return paths;
  });
  expect(kept.length).toBeGreaterThan(PRECACHED.length); // it did keep the app's files
  for (const path of kept) {
    expect(path.startsWith("/_next/static/") || PRECACHED.includes(path), `unexpected cache entry ${path}`).toBe(true);
  }
  expect(kept.filter((p) => p.startsWith("/api/"))).toEqual([]); // nothing about the user
});

test("with no connection a page load shows the offline screen, and Try again recovers", async ({ page, context }) => {
  await newConnectedUser(page, "offline");
  await page.goto("/lineup");
  await expect(page.getByRole("heading", { name: "Lineup" })).toBeVisible();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  expect(await page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);

  mkdirSync(SHOTS, { recursive: true });
  for (const scheme of ["dark", "light"] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await context.setOffline(true);
    await page.goto("/lineup");
    await expect(page.getByRole("heading", { name: "You're offline" })).toBeVisible();
    await expect(page.getByText(/Your leagues and settings are safe/)).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/offline-${scheme}.png` });
    // The offline page carries its own colors (it must work with nothing else loaded): check it too.
    const found = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(found.violations.map((v) => `${v.id}: ${v.nodes[0]?.failureSummary}`), `${scheme} offline page`).toEqual([]);
    await context.setOffline(false);
  }

  await context.setOffline(true);
  await page.goto("/lineup");
  await context.setOffline(false);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { name: "Lineup" })).toBeVisible();
  await expect(page).toHaveURL(/\/lineup$/);
});

test("Settings offers installing, or explains how for this browser", async ({ page }) => {
  await newConnectedUser(page, "install");
  await page.goto("/settings");
  await expect(page.getByText("Add it to your home screen")).toBeVisible();
  // A browser that fires the install prompt shows a button; others get plain instructions.
  await expect(page.getByRole("button", { name: "Install app" }).or(page.getByText(/Add to Home Screen/).first())).toBeVisible();
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: `${SHOTS}/settings-install.png`, fullPage: true });
});
