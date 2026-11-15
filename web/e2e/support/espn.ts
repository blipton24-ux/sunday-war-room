/**
 * ESPN helpers for the end-to-end tests. The stand-in ESPN server and these tests share one set
 * of made-up values (api/tests/fixtures/espn_league/cookies.json), so a cookie can't drift between
 * them. None of it is a real credential.
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, type Page } from "@playwright/test";

import { db } from "./helpers";

const FIXTURES = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../../api/tests/fixtures/espn_league/cookies.json",
);

export const ESPN = JSON.parse(readFileSync(FIXTURES, "utf-8")) as {
  good_s2: string;
  good_swid: string;
  revoked_s2: string;
  public_league: string;
  private_league: string;
  category_league: string;
};

export const PUBLIC_NAME = "ESPN Fixture League";
export const PRIVATE_NAME = "ESPN Private League";

export function leagueLink(id: string): string {
  return `https://fantasy.espn.com/football/league?leagueId=${id}`;
}

async function pollJob(page: Page, jobId: string): Promise<{ status: string }> {
  for (let i = 0; i < 60; i++) {
    const job = await (await page.request.get(`/api/v1/jobs/${jobId}`)).json();
    if (job.status === "done" || job.status === "failed") return job;
    await page.waitForTimeout(500);
  }
  throw new Error(`job ${jobId} did not finish`);
}

/**
 * Connect ESPN with the good cookies and follow the private league through the same API the
 * screens call. Ends with the league synced. Returns the league id.
 */
export async function connectPrivateLeague(page: Page): Promise<number> {
  const connect = await page.request.post("/api/v1/platforms/espn/credentials", {
    data: { espn_s2: ESPN.good_s2, swid: ESPN.good_swid },
  });
  expect(connect.status()).toBe(202);
  expect((await pollJob(page, (await connect.json()).job_id)).status).toBe("done");

  const follow = await page.request.post("/api/v1/leagues", {
    data: { platform: "espn", external_id: ESPN.private_league },
  });
  expect(follow.status()).toBe(202);
  const { league, job_id: jobId } = await follow.json();
  expect((await pollJob(page, jobId)).status).toBe("done");
  return league.id;
}

/** Pretend ESPN refused this user's cookies (what the worker records when it does). */
export async function expireEspnCookies(email: string): Promise<void> {
  await db().query(
    `update platform_accounts set status = 'needs_reconnect'
       where platform = 'espn' and user_id = (select id from users where email = $1)`,
    [email],
  );
}

export async function espnAccount(
  email: string,
): Promise<{ status: string; credentials_encrypted: string | null } | undefined> {
  const { rows } = await db().query(
    `select pa.status, pa.credentials_encrypted from platform_accounts pa
       join users u on u.id = pa.user_id where u.email = $1 and pa.platform = 'espn'`,
    [email],
  );
  return rows[0];
}
