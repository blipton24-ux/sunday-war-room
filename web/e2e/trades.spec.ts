/**
 * P2 Trades screen against the seeded world (ADR-048): the fixture league is a dynasty league
 * with a week-10 trade deadline, so values are labeled "this-season value only".
 */
import { expect, test } from "@playwright/test";

import { MY_TEAM } from "./support/helpers";

test.describe("Trades", () => {
  test("labels the league's trade rules", async ({ page }) => {
    await page.goto("/trades");
    await expect(page.getByRole("heading", { name: "Trades" })).toBeVisible();
    await expect(page.getByText("this-season value only · deadline week 10")).toBeVisible();
  });

  test("ideas respond to the 'acceptable loss' slider", async ({ page }) => {
    await page.goto("/trades");
    const slider = page.getByLabel("How much the other team may lose");
    await expect(slider).toHaveValue("1");
    await expect(page.getByText("up to 1.0 pts/wk")).toBeVisible();
    await slider.fill("0");
    await expect(page.getByText("nothing", { exact: true })).toBeVisible();
    // Either ideas or the explanation that none fit, never a spinner forever.
    await expect(
      page.getByText(/pts\/wk for you|No trade helps your lineup within that limit/).first(),
    ).toBeVisible({ timeout: 20_000 });
  });

  test("evaluates a trade between my team and another", async ({ page }) => {
    await page.goto("/trades");
    const teamA = page.getByLabel("Team A gives");
    await expect(teamA.locator("option:checked")).toHaveText(`${MY_TEAM} (you)`);
    const evaluate = page.getByRole("button", { name: "Evaluate trade" });
    await expect(evaluate).toBeDisabled();

    const cards = page.locator("#analyzer > div");
    await cards.nth(0).getByRole("checkbox").first().check();
    await cards.nth(1).getByRole("checkbox").first().check();
    await expect(evaluate).toBeEnabled();
    await evaluate.click();

    const result = page.locator("[aria-live=polite]");
    await expect(result.getByText("Lineup after")).toHaveCount(2);
    await expect(result.getByText(MY_TEAM, { exact: true })).toBeVisible();
    await expect(result.getByText(/^gets /).first()).toBeVisible();
  });
});
