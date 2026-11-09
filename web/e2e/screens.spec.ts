/**
 * Every screen, as a signed-in user, against the seeded world (api/tests/e2e_seed.py):
 * "Team 1" has a starter on bye, one in progress, a questionable TE, a QB who boomed, and two
 * swaps to make. (Verification Gaps V-02, V-04, V-05, V-06.)
 */
import { expect, test, type Page } from "@playwright/test";

import { FIXTURE_LEAGUE, MY_TEAM } from "./support/helpers";

async function api<T = unknown>(page: Page, path: string): Promise<T> {
  const res = await page.request.get(path);
  expect(res.status(), path).toBe(200);
  return res.json();
}

test.describe("Home", () => {
  test("shows the week, the score header and what to do next", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Week 9" })).toBeVisible();
    await expect(page.getByText(/starters? still to play/)).toBeVisible();
    await expect(page.getByText(MY_TEAM, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/Cruising: up/)).toBeVisible(); // my QB scored 60
    await expect(page.getByText(/Projected final/)).toBeVisible();
  });

  test("Heads up lists the problems first, then the good news", async ({ page }) => {
    await page.goto("/");
    const alerts = page.locator("section", { has: page.getByRole("heading", { name: "Heads up" }) }).locator("p");
    await expect(alerts).toHaveText([
      "Keenan Allen is on bye in your FLEX",
      "T.J. Hockenson is questionable",
      "Love boomed",
    ]);
    // The bye alert names the best fix from the bench.
    await expect(page.getByText(/Tre' Harris \(\d+\.\d proj\) is your best bench option/)).toBeVisible();
  });

  test("'Fix my lineup' counts the swaps and opens the lineup", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Fix my lineup (2) →" }).click();
    await expect(page).toHaveURL(/\/lineup$/);
  });

  test("the accuracy card reports real graded results and opens the Accuracy screen", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/points off on a typical player/)).toBeVisible();
    await expect(page.getByText(/landed inside our 80% range/)).toBeVisible();
    await page.getByText("How we've been doing").locator("..").getByRole("link").click();
    await expect(page).toHaveURL(/\/accuracy$/);
  });
});

test.describe("Lineup", () => {
  test("the lineup check shows both swaps and the win chance before and after", async ({ page }) => {
    await page.goto("/lineup");
    await expect(page.getByText("2 swaps to make")).toBeVisible();
    const harris = page.getByText("Harris").first();
    await expect(harris).toBeVisible();
    await expect(page.getByText("Allen").first()).toBeVisible();
    await expect(page.getByText(/^\+28\.\d$/)).toBeVisible(); // Allen on bye -> Harris
    await expect(page.getByText(/Win chance \d+% → \d+%\. Make the change in Sleeper\./)).toBeVisible();
  });

  test("starters and bench show their game state", async ({ page }) => {
    await page.goto("/lineup");
    const row = (name: string) => page.getByRole("button", { name: new RegExp(name) });
    await expect(page.getByRole("heading", { name: "Starters" })).toBeVisible();
    await expect(row("Ja'Marr Chase")).toContainText("Live"); // game in progress
    await expect(row("Keenan Allen")).toContainText("BYE");
    await expect(row("Keenan Allen")).toContainText("on bye");
    await expect(row("Hockenson")).toContainText("Q"); // questionable
    await expect(row("Jordan Love")).toContainText("🔥 Boom");
    await expect(row("Jordan Love")).toContainText("proj"); // the frozen projection, beside the actual
    await expect(row("Harris")).toContainText("Start"); // the bench player to swap in
    await expect(page.getByRole("heading", { name: "Top performers" })).toBeVisible();
  });

  test("an upcoming player expands to range, reasons and recent games", async ({ page }) => {
    await page.goto("/lineup");
    await page.getByRole("button", { name: /Zay Flowers/ }).click();
    await expect(page.getByRole("img", { name: /^Range [\d.]+ to [\d.]+, projection [\d.]+$/ })).toBeVisible();
    await expect(page.getByText("Why this number")).toBeVisible();
    await expect(page.getByText("Recent form").first()).toBeVisible();
    await expect(page.getByText("Recent games")).toBeVisible();
    const recent = page.getByText("Recent games").locator("..");
    await expect(recent.getByText(/^Wk \d/)).toHaveCount(4);
    await expect(page.getByText(/Updates until kickoff · model 1\.0\.0/)).toBeVisible();
    // Tapping again collapses it.
    await page.getByRole("button", { name: /Zay Flowers/ }).click();
    await expect(page.getByText("Why this number")).toHaveCount(0);
  });

  test("a finished game shows the frozen projection and the actual score on the bar", async ({ page }) => {
    await page.goto("/lineup");
    await page.getByRole("button", { name: /Jordan Love/ }).click();
    await expect(page.getByText(/Frozen at kickoff · model 1\.0\.0/)).toBeVisible();
    await expect(page.getByRole("img", { name: /, scored [\d.]+$/ })).toBeVisible();
    // The tag appears on the player's row, on the Top performers shelf, and in the detail.
    await expect(page.getByText("🔥 Boom")).toHaveCount(3);
  });

  test("a player on bye explains itself instead of showing a bar", async ({ page }) => {
    await page.goto("/lineup");
    await page.getByRole("button", { name: /Keenan Allen/ }).click();
    await expect(page.getByText("This week").locator("..").getByText("On bye")).toBeVisible();
    await expect(page.getByRole("img", { name: /^Range/ })).toHaveCount(0);
  });
});

test.describe("Matchup", () => {
  test("shows the scoreboard, the projected winner and both lineups side by side", async ({ page }) => {
    const matchup = await api(page, "/api/v1/leagues/1/matchup?week=9");
    await page.goto("/matchup");
    await expect(page.getByRole("heading", { name: "Matchup" })).toBeVisible();
    await expect(page.getByText(MY_TEAM, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(matchup.opponent.name, { exact: true }).first()).toBeVisible();
    // A game is still in progress, so it shows a projection with a win chance, not a final result.
    await expect(page.getByText("Projected to win")).toBeVisible();
    await expect(page.getByText(/\d+% win chance/)).toBeVisible();
    await expect(page.getByText("Live").first()).toBeVisible();
    // Nine starters on each side, joined by their slot.
    await expect(page.getByText("Jordan Love").first()).toBeVisible();
    for (const slot of ["QB", "RB", "WR", "TE", "FLEX", "DST"]) {
      await expect(page.getByText(slot, { exact: true }).first()).toBeVisible();
    }
    await expect(page.getByText(/scores as of/)).toBeVisible();
  });

  test("tells you about league rules it can't score yet", async ({ page }) => {
    await page.goto("/matchup");
    await expect(page.getByText(/Not scored yet in projections: .*st_ff/)).toBeVisible();
  });
});

test.describe("Accuracy", () => {
  test("explains the grading and shows real results by position and week", async ({ page }) => {
    await page.goto("/accuracy");
    await expect(page.getByRole("heading", { name: "Accuracy" })).toBeVisible();
    await expect(page.getByText(/frozen when the player's game kicks off/)).toBeVisible();
    for (const label of ["Typical miss", "Inside 80% range", "Lean"]) {
      await expect(page.getByText(label, { exact: true }).first()).toBeVisible(); // the stat cards
    }
    const weeks = page.locator("section", { has: page.getByRole("heading", { name: "Week by week" }) });
    await expect(weeks.getByText("Week 8")).toBeVisible();
    await expect(weeks.getByText("Week 9")).toBeVisible();
    const positions = page.locator("section", { has: page.getByRole("heading", { name: "By position" }) });
    for (const pos of ["QB", "RB", "WR", "TE"]) await expect(positions.getByText(pos, { exact: true })).toBeVisible();
  });
});

test.describe("Settings", () => {
  test("shows the account, the connected platform, my team and the theme choices", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
    await expect(page.getByText(/@example\.com$/)).toBeVisible();
    await expect(page.getByText("@fixtureuser")).toBeVisible();
    await expect(page.getByText(FIXTURE_LEAGUE).first()).toBeVisible();
    await expect(page.getByLabel("My team").locator("option:checked")).toHaveText(new RegExp(`^${MY_TEAM} `));
    // First visit follows the phone's setting; dark and light are explicit overrides.
    await expect(page.getByRole("radio", { name: "Match my phone" })).toBeChecked();
    for (const name of ["Dark", "Light"]) await expect(page.getByRole("radio", { name })).toBeVisible();
    await expect(page.getByText("Add it to your home screen")).toBeVisible();
  });
});

test.describe("Weeks", () => {
  test("a future week says it isn't here yet and offers the way back", async ({ page }) => {
    await page.goto("/lineup");
    await expect(page.getByRole("heading", { name: "Lineup" })).toBeVisible();
    await page.getByRole("button", { name: "Next week" }).click();
    await expect(page.getByText("Wk 10")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Week 10 isn't here yet" })).toBeVisible();
    await page.getByRole("button", { name: "Back to Week 9" }).click();
    await expect(page.getByText("2 swaps to make")).toBeVisible();
  });

  test("a past week shows what happened", async ({ page }) => {
    await page.goto("/matchup");
    await page.getByRole("button", { name: "Previous week" }).click();
    await expect(page.getByText("Wk 8")).toBeVisible();
    await expect(page.getByText(/Final|won|Projected to win/).first()).toBeVisible();
    await expect(page.getByText(MY_TEAM, { exact: true }).first()).toBeVisible();
  });
});
