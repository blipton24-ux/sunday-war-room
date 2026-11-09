import { describe, expect, expectTypeOf, it } from "vitest";

import { ApiError, createApiClient, isApiError, unwrap, type Schemas } from "./client";

interface Recorded {
  url: string;
  method: string;
  authorization: string | null;
}

/** A fake server: records each request and answers with the given status and JSON body. */
function fakeServer(status: number, body: unknown, contentType = "application/json") {
  const calls: Recorded[] = [];
  const fetch = async (request: Request): Promise<Response> => {
    calls.push({
      url: request.url,
      method: request.method,
      authorization: request.headers.get("Authorization"),
    });
    const text = typeof body === "string" ? body : JSON.stringify(body);
    return new Response(status === 204 ? null : text, {
      status,
      headers: { "content-type": contentType },
    });
  };
  return { calls, fetch };
}

describe("createApiClient", () => {
  it("builds path and query parameters", async () => {
    const server = fakeServer(200, []);
    const api = createApiClient({ baseUrl: "http://api.test", fetch: server.fetch });
    await api.GET("/api/v1/leagues/{league_id}/matchup", {
      params: { path: { league_id: 7 }, query: { week: 9 } },
    });
    expect(server.calls[0]?.url).toBe("http://api.test/api/v1/leagues/7/matchup?week=9");
  });

  it("sends the signed-in user's token as a bearer header", async () => {
    const server = fakeServer(200, []);
    const api = createApiClient({
      baseUrl: "http://api.test",
      getToken: async () => "tok-123",
      fetch: server.fetch,
    });
    await api.GET("/api/v1/leagues");
    expect(server.calls[0]?.authorization).toBe("Bearer tok-123");
  });

  it("sends no Authorization header when signed out", async () => {
    const server = fakeServer(200, []);
    const api = createApiClient({
      baseUrl: "http://api.test",
      getToken: () => null,
      fetch: server.fetch,
    });
    await api.GET("/api/v1/leagues");
    expect(server.calls[0]?.authorization).toBeNull();
  });
});

describe("unwrap", () => {
  it("returns the data on success", async () => {
    const leagues = [{ id: 1, name: "Fixture League" }];
    const server = fakeServer(200, leagues);
    const api = createApiClient({ baseUrl: "http://api.test", fetch: server.fetch });
    expect(await unwrap(api.GET("/api/v1/leagues"))).toEqual(leagues);
  });

  it("turns the API's error shape into an ApiError with its code", async () => {
    const server = fakeServer(404, { detail: "League not found", code: "league_not_found" });
    const api = createApiClient({ baseUrl: "http://api.test", fetch: server.fetch });
    const failure = unwrap(
      api.GET("/api/v1/leagues/{league_id}/teams", { params: { path: { league_id: 999 } } }),
    );
    await expect(failure).rejects.toMatchObject({
      status: 404,
      code: "league_not_found",
      message: "League not found",
    });
    await failure.catch((e: unknown) => {
      expect(isApiError(e, "league_not_found")).toBe(true);
      expect(isApiError(e, "rate_limited")).toBe(false);
    });
  });

  it("still gives callers an ApiError when the body isn't the API's shape", async () => {
    const server = fakeServer(502, "<html>Bad Gateway</html>", "text/html");
    const api = createApiClient({ baseUrl: "http://api.test", fetch: server.fetch });
    const failure = unwrap(api.GET("/api/v1/leagues"));
    await expect(failure).rejects.toBeInstanceOf(ApiError);
    await expect(failure).rejects.toMatchObject({ status: 502, code: "http_error" });
  });
});

/**
 * Compile-time contract. Never called: `npm run typecheck` is what runs this. If the backend
 * renames or removes a field, these lines stop compiling, which is the point of the
 * generated client.
 */
export function typeContract(m: Schemas["MatchupOut"], l: Schemas["LineupOut"]) {
  expectTypeOf(m.outlook).toEqualTypeOf<Schemas["WinOutlook"] | null>();
  expectTypeOf(m.me.starters[0]!.game_status).toEqualTypeOf<
    "upcoming" | "in_progress" | "final" | "bye"
  >();
  expectTypeOf(l.swaps[0]!.gain).toEqualTypeOf<number>();
  expectTypeOf<Schemas["ErrorOut"]>().toEqualTypeOf<{ detail: string; code: string }>();

  // @ts-expect-error `projected_points` doesn't exist: this is what a stale name looks like
  void m.me.starters[0]!.projected_points;
}
