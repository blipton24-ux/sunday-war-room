import { describe, expect, it } from "vitest";

import { BadProxyPath, upstreamUrl } from "./upstream";

const API = "http://api.internal:8000";

describe("upstreamUrl", () => {
  it("maps /api/v1/<path> onto the API with the query string", () => {
    expect(upstreamUrl(["leagues", "7", "matchup"], "?week=9", API).toString()).toBe(
      "http://api.internal:8000/api/v1/leagues/7/matchup?week=9",
    );
  });

  it.each([
    [[".."], "parent"],
    [["leagues", "..", "..", "docs"], "climb to /docs"],
    [["."], "dot"],
    [["a/b"], "decoded slash"],
    [["a\\b"], "backslash"],
    [[""], "empty"],
    [[], "no path"],
  ])("refuses %j (%s)", (segments) => {
    expect(() => upstreamUrl(segments, "", API)).toThrow(BadProxyPath);
  });

  it("encodes characters that would change the meaning of the URL", () => {
    const url = upstreamUrl(["jobs", "a?b#c"], "", API);
    expect(url.pathname).toBe("/api/v1/jobs/a%3Fb%23c");
    expect(url.search).toBe("");
  });
});
