/**
 * Every screen on a phone (iPhone 14 size, touch). The UI spec promises: bottom tabs, one-handed
 * use, touch targets of at least 44 px, nothing wider than the screen. (Verification Gaps V-01.)
 * Screenshots are attached to each test for a human look.
 */
import { expect, test, type Locator, type Page } from "@playwright/test";

const SCREENS: [path: string, heading: RegExp][] = [
  ["/", /^Week 9$/],
  ["/lineup", /^Lineup$/],
  ["/matchup", /^Matchup$/],
  ["/accuracy", /^Accuracy$/],
  ["/settings", /^Settings$/],
];
const MIN_TOUCH = 44;

async function shot(page: Page, name: string): Promise<void> {
  await test.info().attach(name, { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
}

async function horizontalOverflow(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

async function size(
  page: Page,
  name: string | RegExp,
  role: "button" | "link" = "button",
  within?: Locator,
) {
  const box = await (within ?? page).getByRole(role, { name }).first().boundingBox();
  expect(box, `${name} should be on screen`).not.toBeNull();
  return box!;
}

test.describe("phone layout", () => {
  for (const [path, heading] of SCREENS) {
    test(`${path} fits the screen and doesn't scroll sideways`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await page.waitForLoadState("networkidle");
      expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);
      await shot(page, `phone${path === "/" ? "-home" : path.replace("/", "-")}`);
    });
  }

  test("navigation is the bottom tab bar, not the desktop pill bar", async ({ page }) => {
    await page.goto("/");
    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav).toHaveCount(1); // the other one is hidden at this width
    const box = (await nav.boundingBox())!;
    const viewport = page.viewportSize()!;
    expect(box.y + box.height).toBeGreaterThanOrEqual(viewport.height - 1); // pinned to the bottom
    expect(box.width).toBeGreaterThanOrEqual(viewport.width - 1);
    for (const name of ["Home", "Lineup", "Matchup", "Chat"]) {
      const tab = await size(page, name, "link", nav);
      expect(tab.height, `${name} tab height`).toBeGreaterThanOrEqual(MIN_TOUCH);
      expect(tab.width, `${name} tab width`).toBeGreaterThanOrEqual(MIN_TOUCH);
    }
    const more = await size(page, "More", "button", nav);
    expect(more.height).toBeGreaterThanOrEqual(MIN_TOUCH);
  });

  test("tapping a tab changes screens and highlights it", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Lineup" }).tap();
    await expect(page).toHaveURL(/\/lineup$/);
    await expect(page.getByRole("heading", { name: "Lineup" })).toBeVisible();
    await page.getByRole("link", { name: "Matchup" }).tap();
    await expect(page).toHaveURL(/\/matchup$/);
  });

  test("More opens a menu with Waivers, Trades and Accuracy", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "More" }).tap();
    for (const name of ["Waivers", "Trades", "Accuracy"]) {
      await expect(page.getByRole("menuitem", { name })).toBeVisible();
    }
    await page.getByRole("menuitem", { name: "Accuracy" }).tap();
    await expect(page).toHaveURL(/\/accuracy$/);
  });

  test("the header fits and every control is big enough to tap", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Week 9" })).toBeVisible();
    const viewport = page.viewportSize()!;
    const controls: [string, "button" | "link"][] = [
      ["Fixture League", "button"],
      ["Previous week", "button"],
      ["Next week", "button"],
      ["Refresh league", "button"],
      ["Switch to light theme", "button"],
    ];
    for (const [name, role] of controls) {
      const box = await size(page, name, role);
      expect(box.x, `${name} left edge`).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width, `${name} right edge`).toBeLessThanOrEqual(viewport.width);
      expect(Math.min(box.width, box.height), `${String(name)} touch size`).toBeGreaterThanOrEqual(MIN_TOUCH);
    }
  });

  test("player rows are easy to tap and expand in place", async ({ page }) => {
    await page.goto("/lineup");
    const row = page.getByRole("button", { name: /Zay Flowers/ });
    expect((await row.boundingBox())!.height).toBeGreaterThanOrEqual(MIN_TOUCH);
    await row.tap();
    await expect(page.getByText("Why this number")).toBeVisible();
    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);
    await shot(page, "phone-lineup-row-expanded");
  });

  test("the Top performers shelf scrolls sideways without moving the page", async ({ page }) => {
    await page.goto("/lineup");
    const shelf = page.locator(".snap-x").first();
    await expect(shelf).toBeVisible();
    const { scrollWidth, clientWidth } = await shelf.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(scrollWidth).toBeGreaterThan(clientWidth); // there is more to swipe to
    await shelf.evaluate((el) => el.scrollBy({ left: 200 }));
    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0); // the page itself stays put
  });

  test("the matchup board keeps both teams and scores readable", async ({ page }) => {
    await page.goto("/matchup");
    await expect(page.getByText("Projected to win")).toBeVisible();
    for (const text of ["Team 1", "Jordan Love"]) await expect(page.getByText(text).first()).toBeVisible();
    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);
  });
});

test.describe("a small phone (360 px wide)", () => {
  test.use({ viewport: { width: 360, height: 640 } });

  for (const [path, heading] of SCREENS) {
    test(`${path} still fits`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await page.waitForLoadState("networkidle");
      expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);
    });
  }

  test("the header controls all stay on screen", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Week 9" })).toBeVisible();
    for (const name of ["Refresh league", "Next week"]) {
      const box = await size(page, name);
      expect(box.x + box.width).toBeLessThanOrEqual(360);
    }
  });
});
