/**
 * P2 Waivers screen against the seeded world: a FAAB league ($100), where the free agent
 * Jaydon Blue has been a breakout RB, so he is the top add (ADR-047).
 */
import { expect, test } from "@playwright/test";

const BREAKOUT = "Jaydon Blue";

test.describe("Waivers", () => {
  test("ranks free agents by what they add to my lineup, with status and a bid guide", async ({ page }) => {
    await page.goto("/waivers");
    await expect(page.getByRole("heading", { name: "Waivers" })).toBeVisible();
    await expect(page.getByText(/weeks 9–17, playoff weeks count 1\.5×/)).toBeVisible();
    await expect(page.locator("p", { hasText: "FAAB:" })).toContainText(/\$\d+ of \$100 left/);

    const rows = page.getByRole("listitem");
    await expect(rows.first()).toContainText(BREAKOUT);
    await expect(rows.first()).toContainText(/\+\d+\.\d/);
    await expect(rows.first()).toContainText("pts/wk to your lineup");
    await expect(rows.first().getByText("Free agent · add now")).toBeVisible();
    await expect(rows.first().getByText(/^Bid \$\d+/)).toBeVisible();
  });

  test("the toggle switches to this week only", async ({ page }) => {
    await page.goto("/waivers");
    const thisWeek = page.getByRole("button", { name: "This week" });
    await expect(page.getByRole("button", { name: "Rest of season" })).toHaveAttribute("aria-pressed", "true");
    await thisWeek.click();
    await expect(thisWeek).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("week 9 only")).toBeVisible();
  });

  test("the API matches what the screen shows", async ({ page }) => {
    await page.goto("/");
    const leagues = await (await page.request.get("/api/v1/leagues")).json();
    const res = await page.request.get(`/api/v1/leagues/${leagues[0].id}/waivers`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.waiver_kind).toBe("faab");
    expect(body.players[0].player.name).toBe(BREAKOUT);
    expect(body.players[0].gain).toBeGreaterThan(0);
  });
});
