/**
 * P2 live game day against the seeded world: Ja'Marr Chase's game is mid 3rd quarter on the
 * scoreboard (the seed stores what the live tick would). ADR-044/045.
 */
import { expect, test } from "@playwright/test";

test.describe("Live game day", () => {
  test("the matchup shows it's live, with the game clock and points so far", async ({ page }) => {
    await page.goto("/matchup");
    await expect(page.getByText(/Week 9 · live, updated/)).toBeVisible();
    await expect(page.getByText(/4:12 - 3rd/).first()).toBeVisible(); // Chase's game clock
    await expect(page.getByText(/Game clocks are unavailable/)).toHaveCount(0);
  });

  test("the API reports live state and the screen polls while it lasts", async ({ page }) => {
    await page.goto("/");
    const leagues = await (await page.request.get("/api/v1/leagues")).json();
    const body = await (await page.request.get(`/api/v1/leagues/${leagues[0].id}/matchup`)).json();
    expect(body.live).toBe(true);
    expect(body.clock_source).toBe("scoreboard");
    const chase = body.me.starters.find((s: { name: string }) => s.name === "Ja'Marr Chase");
    expect(chase.game_status).toBe("in_progress");
    expect(chase.game_detail).toBe("4:12 - 3rd");
    expect(chase.remaining_fraction).toBeCloseTo(0.32, 2);

  });

  test("while live, the Matchup screen asks for fresh scores on its own", async ({ page }) => {
    test.setTimeout(90_000); // one 45-second poll
    await page.goto("/matchup");
    await expect(page.getByText(/live, updated/)).toBeVisible();
    const again = page.waitForRequest((r) => r.url().includes("/matchup"), { timeout: 60_000 });
    await expect(again).resolves.toBeTruthy();
  });
});
