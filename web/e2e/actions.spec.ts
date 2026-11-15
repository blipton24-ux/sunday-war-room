/**
 * Everything a person can click that changes something: refresh, switching league, theme, my
 * team, unfollow, sign out, delete account. Each test signs in a throwaway user, so nothing
 * depends on another test. (Verification Gaps V-08, V-09.)
 */
import { expect, test } from "@playwright/test";

import { FIXTURE_LEAGUE, closeDb, db, newConnectedUser } from "./support/helpers";

test.afterAll(closeDb);

test("refresh syncs in the background, and a second refresh right away is politely refused", async ({ page }) => {
  await newConnectedUser(page, "refresh");
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Week 9" })).toBeVisible();
  await page.waitForTimeout(4500); // the test stack allows one refresh every 4 seconds

  const toast = page.getByRole("status");
  await page.getByRole("button", { name: "Refresh league" }).click();
  await expect(toast).toHaveText("Syncing in the background…");
  await expect(toast).toHaveText("League updated", { timeout: 20_000 });

  await page.getByRole("button", { name: "Refresh league" }).click(); // straight away: too soon
  await expect(toast).toHaveText(/Refreshed moments ago/);
});

test("the league menu lists leagues, settings and sign out, and can connect another league", async ({ page }) => {
  await newConnectedUser(page, "menu");
  await page.goto("/");
  await page.getByRole("button", { name: new RegExp(FIXTURE_LEAGUE) }).click();
  for (const name of [FIXTURE_LEAGUE, "+ Connect a league", "Settings", "Sign out"]) {
    await expect(page.getByRole("menuitem", { name: new RegExp(name.replace("+", "\\+")) })).toBeVisible();
  }
  await page.getByRole("menuitem", { name: "+ Connect a league" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Where do you play?" })).toBeVisible();
});

test("the theme toggle sticks across a reload and shows in Settings", async ({ page }) => {
  await newConnectedUser(page, "theme");
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.goto("/settings");
  await expect(page.getByRole("radio", { name: "Light" })).toBeChecked();
  await page.getByRole("radio", { name: "Match my phone" }).click(); // back to following the phone (dark here)
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("choosing a different team in Settings changes whose matchup you see", async ({ page }) => {
  await newConnectedUser(page, "team");
  await page.goto("/matchup");
  await expect(page.getByText("Team 1", { exact: true }).first()).toBeVisible();

  await page.goto("/settings");
  await page.getByLabel("My team").selectOption({ label: "Team 2 (manager2)" });
  await expect(page.getByRole("status")).toHaveText("Team saved");

  await page.goto("/matchup");
  await expect(page.getByText("Team 2", { exact: true }).first()).toBeVisible();
});

test("unfollowing a league asks first, then removes it and sends you to connect another", async ({ page }) => {
  await newConnectedUser(page, "unfollow");
  await page.goto("/settings");
  await page.getByRole("button", { name: "Unfollow" }).click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog.getByText("Unfollow Fixture League?")).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText(FIXTURE_LEAGUE).first()).toBeVisible(); // still followed

  await page.getByRole("button", { name: "Unfollow" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Unfollow" }).click();
  await expect(page.getByRole("status")).toHaveText("League removed");
  await expect(page).toHaveURL(/\/onboarding$/); // nothing left to look at: straight to connecting one
});

test("signing out ends the session everywhere it matters", async ({ page }) => {
  await newConnectedUser(page, "signout");
  await page.goto("/");
  await page.getByRole("button", { name: new RegExp(FIXTURE_LEAGUE) }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.goto("/lineup");
  await expect(page).toHaveURL(/\/sign-in$/); // pages are protected again
  expect((await page.request.get("/api/v1/me")).status()).toBe(401); // and so is the data
});

test("deleting the account removes the person and what they followed, but not the shared league", async ({ page }) => {
  const { email } = await newConnectedUser(page, "delete");
  const users = async () => (await db().query("select id from users where email = $1", [email])).rows;
  const [{ id: userId }] = await users();
  const followed = async () =>
    Number((await db().query("select count(*) from league_memberships where user_id = $1", [userId])).rows[0].count);
  expect(await followed()).toBe(1);

  await page.goto("/settings");
  await page.getByRole("button", { name: "Delete account" }).click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog.getByText("This can't be undone.")).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click(); // changing your mind is safe
  expect(await users()).toHaveLength(1);

  await page.getByRole("button", { name: "Delete account" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Delete account" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);

  expect(await users()).toHaveLength(0);
  expect(await followed()).toBe(0);
  const leagues = await db().query("select count(*) from leagues");
  expect(Number(leagues.rows[0].count)).toBeGreaterThanOrEqual(1); // the league belongs to no one person
});
