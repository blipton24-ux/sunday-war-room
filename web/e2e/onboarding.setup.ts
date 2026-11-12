/**
 * A new person's first visit: sign in, connect Sleeper, choose a team, land on Home. This is
 * the main flow from the build plan. It also saves the signed-in state the other specs reuse.
 * (Verification Gaps V-07.)
 */
import { mkdirSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import { FIXTURE_LEAGUE, MY_TEAM, closeDb, magicLinkFor, signIn, uniqueEmail } from "./support/helpers";

test.describe.configure({ mode: "serial" });

let page: Page;
test.beforeAll(async ({ browser }) => {
  const { baseURL } = test.info().project.use;
  page = await (await browser.newContext({ baseURL })).newPage();
});
test.afterAll(async () => {
  await page.context().close();
  await closeDb();
});

test("signed-out visitors are sent to the sign-in screen", async () => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/sign-in$/);
  await expect(page.getByRole("button", { name: "Email me a link" })).toBeVisible();
  // No Google credentials are configured in the test stack, so no Google button is offered.
  await expect(page.getByRole("button", { name: /Sign in with Google/ })).toHaveCount(0);
  await page.goto("/lineup");
  await expect(page).toHaveURL(/\/sign-in$/);
});

test("asking for a link says to check the inbox, then the link signs you in", async () => {
  await signIn(page, uniqueEmail("newcomer"));
  // Signed in but with no league yet: straight to onboarding.
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Where do you play?" })).toBeVisible();
  await page.getByRole("button", { name: /^Sleeper/ }).click();
  await expect(page.getByRole("heading", { name: "Connect Sleeper" })).toBeVisible();
});

test("an unknown Sleeper username gets a clear message", async () => {
  await page.getByLabel("Sleeper username").fill("nobody");
  await page.getByRole("button", { name: "Find my leagues" }).click();
  await expect(page.getByText(/couldn't find a Sleeper account/)).toBeVisible();
});

test("a Sleeper account with no leagues this season is told so", async () => {
  await page.getByLabel("Sleeper username").fill("emptyuser");
  await page.getByRole("button", { name: "Find my leagues" }).click();
  await expect(page.getByRole("heading", { name: "No leagues yet" })).toBeVisible();
  await expect(page.getByText(/has no Sleeper leagues for the 2026 season/)).toBeVisible();
  await page.getByRole("button", { name: "Try another username" }).click();
  await expect(page.getByRole("heading", { name: "Connect Sleeper" })).toBeVisible();
});

test("connecting a real account lists its league, picks the team, and opens Home", async () => {
  await page.getByLabel("Sleeper username").fill("fixtureuser");
  await page.getByRole("button", { name: "Find my leagues" }).click();

  await expect(page.getByRole("heading", { name: "Pick your leagues" })).toBeVisible();
  const league = page.getByRole("button", { name: new RegExp(FIXTURE_LEAGUE) });
  await expect(league).toHaveAttribute("aria-pressed", "true"); // chosen by default
  await expect(league).toContainText("12 teams");
  await page.getByRole("button", { name: "Follow 1 league" }).click();

  // Each league syncs in the background; the team list appears when its sync finishes.
  await expect(page.getByRole("heading", { name: "Which team is yours?" })).toBeVisible();
  // "Team 1" must not also match "Team 10", "Team 11"...: the name is followed by its manager.
  const myTeam = page.getByRole("button", { name: new RegExp(`^${MY_TEAM} manager1 · you`) });
  await expect(myTeam).toBeVisible(); // marked "· you": the team the Sleeper account owns
  await expect(page.getByRole("button", { name: /Go to my war room|Pick a team in each league/ })).toBeDisabled();
  await myTeam.click();
  await expect(page.getByText("saved")).toBeVisible();

  await page.getByRole("button", { name: "Go to my war room →" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Week 9" })).toBeVisible();
  await expect(page.getByText(FIXTURE_LEAGUE).first()).toBeVisible();

  mkdirSync("e2e/.auth", { recursive: true });
  await page.context().storageState({ path: "e2e/.auth/user.json" });
});

test("a sign-in link works only once", async ({ browser }) => {
  const { baseURL } = test.info().project.use;
  const email = uniqueEmail("once");
  const first = await (await browser.newContext({ baseURL })).newPage();
  await first.goto("/sign-in");
  await first.getByLabel("Email").fill(email);
  await first.getByRole("button", { name: "Email me a link" }).click();
  await expect(first.getByText("Check your inbox")).toBeVisible();
  const link = await magicLinkFor(email, baseURL!);

  await first.goto(link);
  await expect(first).toHaveURL(/\/onboarding$/); // the first use signs in

  const second = await (await browser.newContext({ baseURL })).newPage();
  await second.goto(link);
  await second.goto("/");
  await expect(second).toHaveURL(/\/sign-in$/); // the second use signs nobody in
  await first.context().close();
  await second.context().close();
});
