/**
 * Connecting ESPN (P3, ADR-051/052): a public league from a pasted link with no login, a private
 * one with two cookies, what happens when ESPN refuses them, and the reconnect and disconnect
 * paths. ESPN is a stand-in serving a made-up league (web/e2e/mock_espn.py); each test uses its
 * own throwaway user.
 */
import { expect, test, type Page } from "@playwright/test";

import { closeDb, signIn, uniqueEmail } from "./support/helpers";
import {
  ESPN,
  PRIVATE_NAME,
  PUBLIC_NAME,
  connectPrivateLeague,
  espnAccount,
  expireEspnCookies,
  leagueLink,
} from "./support/espn";

test.afterAll(closeDb);

async function startEspn(page: Page, label: string): Promise<string> {
  const email = uniqueEmail(label);
  await signIn(page, email);
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByRole("button", { name: /^ESPN/ }).click();
  await expect(page.getByRole("heading", { name: "Connect ESPN" })).toBeVisible();
  return email;
}

async function fillCookies(page: Page, s2: string, swid: string): Promise<void> {
  await page.getByLabel(/^espn_s2/).fill(s2);
  await page.getByLabel(/^SWID/).fill(swid);
  await page.getByRole("button", { name: "Connect ESPN" }).click();
}

test("a public league connects from a pasted link, with no cookies asked for", async ({ page }) => {
  const email = await startEspn(page, "espnpublic");
  await page.getByLabel("ESPN league link").fill(leagueLink(ESPN.public_league));
  await page.getByRole("button", { name: "Check my league" }).click();

  await expect(page.getByRole("heading", { name: "Pick your leagues" })).toBeVisible();
  const league = page.getByRole("button", { name: new RegExp(PUBLIC_NAME) });
  await expect(league).toHaveAttribute("aria-pressed", "true");
  await expect(league).toContainText("4 teams");
  await page.getByRole("button", { name: "Follow 1 league" }).click();

  await expect(page.getByRole("heading", { name: "Which team is yours?" })).toBeVisible();
  await page.getByRole("button", { name: /^Team 2 owner2/ }).click();
  await expect(page.getByText("saved")).toBeVisible();
  await page.getByRole("button", { name: "Go to my war room →" }).click();
  await expect(page).toHaveURL(/\/$/);

  const leagues = await (await page.request.get("/api/v1/leagues")).json();
  expect(leagues).toHaveLength(1);
  expect(leagues[0]).toMatchObject({ platform: "espn", name: PUBLIC_NAME, needs_reconnect: false });
  expect(leagues[0].my_team_id).not.toBeNull();
  expect(await espnAccount(email)).toBeUndefined(); // nothing was stored: no login was needed
});

test("a private league link says so, then two cookies connect it and preselect my team", async ({ page }) => {
  const email = await startEspn(page, "espnprivate");
  await page.getByLabel("ESPN league link").fill(leagueLink(ESPN.private_league));
  await page.getByRole("button", { name: "Check my league" }).click();

  await expect(page.getByRole("heading", { name: "Connect your private ESPN league" })).toBeVisible();
  await expect(page.getByText(/That league is private/)).toBeVisible();
  await expect(page.getByRole("img", { name: /developer tools/ })).toBeVisible(); // the guide's picture
  await expect(page.getByText(/never changes anything/)).toBeVisible(); // what we do with the cookies

  await fillCookies(page, ESPN.good_s2, ESPN.good_swid);
  await expect(page.getByRole("heading", { name: "Pick your leagues" })).toBeVisible();
  await expect(page.getByRole("button", { name: new RegExp(PRIVATE_NAME) })).toBeVisible();
  await expect(page.getByRole("button", { name: new RegExp(PUBLIC_NAME) })).toBeVisible(); // all my leagues
  await page.getByRole("button", { name: new RegExp(PUBLIC_NAME) }).click(); // leave this one out
  await page.getByRole("button", { name: "Follow 1 league" }).click();

  await expect(page.getByRole("heading", { name: "Which team is yours?" })).toBeVisible();
  // ESPN says Team 2 is mine, so it is marked and chosen for me; one tap confirms it.
  const mine = page.getByRole("button", { name: /^Team 2 owner2 · you/ });
  await expect(mine).toBeVisible();
  await mine.click();
  await expect(page.getByText("saved")).toBeVisible();

  // Stored encrypted: the saved value is not the cookie, and no screen or API shows it.
  const account = await espnAccount(email);
  expect(account?.status).toBe("ok");
  expect(account?.credentials_encrypted).toBeTruthy();
  expect(account?.credentials_encrypted).not.toContain(ESPN.good_s2);
  const me = JSON.stringify(await (await page.request.get("/api/v1/me")).json());
  expect(me).not.toContain(ESPN.good_s2);
  expect(me).toContain('"platform":"espn"');
});

test("cookies ESPN refuses are explained, and nothing is left behind as working", async ({ page }) => {
  const email = await startEspn(page, "espnrefused");
  await page.goto("/onboarding?platform=espn&cookies=1");
  await fillCookies(page, ESPN.revoked_s2, ESPN.good_swid);
  await expect(page.getByRole("alert")).toContainText(/ESPN didn't accept those values/);
  expect((await espnAccount(email))?.status).toBe("needs_reconnect");
});

test("pasting something that isn't a league link is explained", async ({ page }) => {
  await startEspn(page, "espnbadlink");
  await page.getByLabel("ESPN league link").fill("https://example.com/not-espn");
  await page.getByRole("button", { name: "Check my league" }).click();
  await expect(page.getByText(/leagueId/)).toBeVisible();
});

test("a league ESPN doesn't know, and one we can't score yet, each get a plain message", async ({ page }) => {
  await startEspn(page, "espnodd");
  await page.getByLabel("ESPN league link").fill("1");
  await page.getByRole("button", { name: "Check my league" }).click();
  await expect(page.getByText(/ESPN doesn't know that league/)).toBeVisible();

  await page.getByLabel("ESPN league link").fill(leagueLink(ESPN.category_league));
  await page.getByRole("button", { name: "Check my league" }).click();
  await expect(page.getByText(/head-to-head points/)).toBeVisible();
});

test("when ESPN refuses a user's cookies the app asks them to reconnect, and reconnecting resumes it", async ({
  page,
}) => {
  const email = uniqueEmail("espnexpired");
  await signIn(page, email);
  await connectPrivateLeague(page);
  await page.goto("/");
  await expect(page.getByText(PRIVATE_NAME).first()).toBeVisible();
  await expect(page.getByText(/Your ESPN sign-in expired/)).toHaveCount(0);

  await expireEspnCookies(email);
  await page.goto("/lineup");
  await expect(page.getByText(/Your ESPN sign-in expired, so your ESPN leagues have paused/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Reconnect ESPN" })).toBeVisible(); // not someone else's data

  await page.goto("/settings");
  await expect(page.getByText(/Sign-in expired: reconnect to resume/)).toBeVisible();
  await expect(page.getByText(/Sign-in expired: reconnect ESPN/)).toBeVisible(); // on the league itself

  await page.getByRole("link", { name: "Reconnect", exact: true }).first().click();
  await expect(page).toHaveURL(/onboarding\?platform=espn&cookies=1/);
  await fillCookies(page, ESPN.good_s2, ESPN.good_swid);
  await expect(page.getByRole("heading", { name: "Pick your leagues" })).toBeVisible();
  expect((await espnAccount(email))?.status).toBe("ok");

  await page.goto("/");
  await expect(page.getByText(/Your ESPN sign-in expired/)).toHaveCount(0);
});

test("disconnecting ESPN deletes the saved cookies and keeps your leagues", async ({ page }) => {
  const email = uniqueEmail("espnout");
  await signIn(page, email);
  await connectPrivateLeague(page);

  await page.goto("/settings");
  await expect(page.getByText("Connected", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Disconnect" }).click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog.getByText("Disconnect ESPN?")).toBeVisible();
  await dialog.getByRole("button", { name: "Disconnect" }).click();
  await expect(page.getByRole("status").filter({ hasText: "ESPN disconnected" })).toBeVisible();

  const account = await espnAccount(email);
  expect(account?.credentials_encrypted).toBeNull(); // the saved values are gone
  const leagues = await (await page.request.get("/api/v1/leagues")).json();
  expect(leagues).toHaveLength(1); // still followed; it asks to reconnect
  expect(leagues[0].needs_reconnect).toBe(true);
});
