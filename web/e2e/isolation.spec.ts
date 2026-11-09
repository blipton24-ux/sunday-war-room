/**
 * Privacy between people (ADR-019: tenant isolation, checked through the whole stack).
 * Person B is signed in and has the same Sleeper league available, but must never see or
 * change anything that person A follows.
 */
import { expect, test } from "@playwright/test";

import { closeDb, newConnectedUser, signIn, uniqueEmail } from "./support/helpers";

test.afterAll(closeDb);

test("another signed-in person can't see or change your league", async ({ browser }) => {
  const { baseURL } = test.info().project.use;
  const a = await (await browser.newContext({ baseURL })).newPage();
  const { leagueId } = await newConnectedUser(a, "owner");

  const b = await (await browser.newContext({ baseURL })).newPage();
  await signIn(b, uniqueEmail("stranger"));

  // B has no leagues of their own...
  expect(await (await b.request.get("/api/v1/leagues")).json()).toEqual([]);

  // ...and every league-scoped request for A's league is "not found", exactly as if it didn't exist.
  const asked = [
    ["get", `/api/v1/leagues/${leagueId}/matchup?week=9`],
    ["get", `/api/v1/leagues/${leagueId}/lineup?week=9`],
    ["get", `/api/v1/leagues/${leagueId}/teams`],
    ["get", `/api/v1/leagues/${leagueId}/accuracy`],
    ["get", `/api/v1/players/1/projection?league_id=${leagueId}&week=9`],
    ["post", `/api/v1/leagues/${leagueId}/refresh`],
    ["delete", `/api/v1/leagues/${leagueId}`],
  ] as const;
  for (const [method, path] of asked) {
    const res = await b.request[method](path);
    expect(res.status(), `${method} ${path}`).toBe(404);
    expect((await res.json()).code, `${method} ${path}`).toMatch(/league_not_found/);
  }
  const rename = await b.request.patch(`/api/v1/leagues/${leagueId}`, { data: { my_team_id: 1 } });
  expect(rename.status()).toBe(404);

  // A is unaffected by all of that.
  expect((await a.request.get(`/api/v1/leagues/${leagueId}/matchup?week=9`)).status()).toBe(200);
  await a.context().close();
  await b.context().close();
});

test("nothing is available without signing in", async ({ browser }) => {
  const { baseURL } = test.info().project.use;
  const anon = await (await browser.newContext({ baseURL })).newPage();
  for (const path of ["/api/v1/me", "/api/v1/leagues", "/api/v1/leagues/1/matchup", "/api/v1/jobs/abc"]) {
    const res = await anon.request.get(path);
    expect(res.status(), path).toBe(401);
    expect((await res.json()).code, path).toBe("unauthorized");
  }
  // The pass-through refuses paths that try to climb out of /api/v1.
  const climb = await anon.request.get("/api/v1/..%2F..%2Fdocs");
  expect([400, 401, 404]).toContain(climb.status());
  expect(await (await anon.request.get("/api/health")).json()).toEqual({ status: "ok" });
  await anon.context().close();
});
