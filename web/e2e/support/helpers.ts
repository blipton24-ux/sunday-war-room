/**
 * Shared test helpers. Signing in uses the app's real flow end to end: the test asks for a
 * magic link in the UI, then reads the one-time token the app stored in its own database, the
 * way the email would have delivered it. There is no test-only login in the app itself.
 */
import { expect, type Page } from "@playwright/test";
import pg from "pg";

const DATABASE_URL = process.env.E2E_DATABASE_URL ?? "postgres://swr:swr@localhost:55432/swr";
export const FIXTURE_LEAGUE = "Fixture League";
export const MY_TEAM = "Team 1";

let pool: pg.Pool | undefined;
export function db(): pg.Pool {
  return (pool ??= new pg.Pool({ connectionString: DATABASE_URL, max: 2 }));
}

export function uniqueEmail(label = "user"): string {
  return `${label}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}@example.com`;
}

/** The one-time sign-in link the app just "emailed" to this address. */
export async function magicLinkFor(email: string, baseURL: string): Promise<string> {
  for (let i = 0; i < 40; i++) {
    const { rows } = await db().query(
      "select identifier from verifications where value like $1 order by id desc limit 1",
      [`%"email":"${email}"%`],
    );
    if (rows[0]) {
      const token = String(rows[0].identifier).replace(/^magic-link:/, "");
      return `${baseURL}/api/auth/magic-link/verify?token=${encodeURIComponent(token)}&callbackURL=%2F`;
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`no magic link was created for ${email}`);
}

/** Sign in through the real screen and the real link. Ends signed in on whatever page follows. */
export async function signIn(page: Page, email: string): Promise<void> {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Email me a link" }).click();
  await expect(page.getByText("Check your inbox")).toBeVisible();
  const baseURL = new URL(page.url()).origin;
  await page.goto(await magicLinkFor(email, baseURL));
}

async function pollJob(page: Page, jobId: string): Promise<{ status: string; result: unknown }> {
  for (let i = 0; i < 60; i++) {
    const res = await page.request.get(`/api/v1/jobs/${jobId}`);
    const job = await res.json();
    if (job.status === "done" || job.status === "failed") return job;
    await page.waitForTimeout(500);
  }
  throw new Error(`job ${jobId} did not finish`);
}

/**
 * Connect the fixture Sleeper user, follow the league and choose "Team 1", by calling the same
 * API the screens call. For tests that need a connected user but aren't about onboarding.
 */
export async function connectFixtureLeague(page: Page): Promise<number> {
  const connect = await page.request.post("/api/v1/platforms/sleeper/connect", {
    data: { username: "fixtureuser" },
  });
  expect((await pollJob(page, (await connect.json()).job_id)).status).toBe("done");

  const follow = await page.request.post("/api/v1/leagues", {
    data: { platform: "sleeper", external_id: "1100000000000000001" },
  });
  expect(follow.status()).toBe(202);
  const { league, job_id: jobId } = await follow.json();
  expect((await pollJob(page, jobId)).status).toBe("done");

  const teams = await (await page.request.get(`/api/v1/leagues/${league.id}/teams`)).json();
  const mine = teams.find((t: { name: string }) => t.name === MY_TEAM);
  const set = await page.request.patch(`/api/v1/leagues/${league.id}`, {
    data: { my_team_id: mine.id },
  });
  expect(set.status()).toBe(200);
  return league.id;
}

/** A signed-in user with the fixture league connected, ready to use the app. */
export async function newConnectedUser(page: Page, label = "user"): Promise<{ email: string; leagueId: number }> {
  const email = uniqueEmail(label);
  await signIn(page, email);
  return { email, leagueId: await connectFixtureLeague(page) };
}

export async function closeDb(): Promise<void> {
  await pool?.end();
  pool = undefined;
}
