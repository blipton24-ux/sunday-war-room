import { describe, expect, it } from "vitest";

import {
  COOKIE_CONSENT,
  cookieSteps,
  detectBrowser,
  espnConnectPath,
  isMyTeam,
  isPhoneLike,
  readLeagues,
  readProbe,
} from "./espn";

const CHROME =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";
const EDGE = `${CHROME} Edg/130.0`;
const FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0";
const SAFARI =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15";
const IPHONE_CHROME =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0 Mobile/15E148 Safari/604.1";

describe("detectBrowser", () => {
  it("tells the common browsers apart (Edge and Chrome both say Chrome)", () => {
    expect(detectBrowser(CHROME)).toBe("chrome");
    expect(detectBrowser(EDGE)).toBe("edge");
    expect(detectBrowser(FIREFOX)).toBe("firefox");
    expect(detectBrowser(SAFARI)).toBe("safari");
    expect(detectBrowser(IPHONE_CHROME)).toBe("chrome");
    expect(detectBrowser("curl/8")).toBe("other");
  });
});

describe("cookieSteps", () => {
  it("names both cookies in every browser's steps", () => {
    for (const b of ["chrome", "edge", "firefox", "safari", "other"] as const) {
      const text = cookieSteps(b).join(" ");
      expect(text).toContain("espn_s2");
      expect(text).toContain("SWID");
      expect(text).toContain("signed in");
    }
  });

  it("points Firefox at Storage, Chrome at Application, and Safari at the Develop menu", () => {
    expect(cookieSteps("firefox").join(" ")).toContain("Storage tab");
    expect(cookieSteps("chrome").join(" ")).toContain("Application tab");
    expect(cookieSteps("safari").join(" ")).toContain("Develop");
  });
});

describe("isPhoneLike", () => {
  it("is a touch screen that is narrow", () => {
    expect(isPhoneLike(true, 390)).toBe(true);
    expect(isPhoneLike(true, 1200)).toBe(false); // a touch laptop
    expect(isPhoneLike(false, 390)).toBe(false); // a narrow desktop window
  });
});

describe("readProbe", () => {
  const league = { external_id: "1", name: "L", season: 2026, total_teams: 2, team_id: null };

  it("reads a public league with its teams", () => {
    const out = readProbe({
      public: true,
      leagues: [league],
      teams: [{ external_id: "1", name: "A" }],
    });
    expect(out).toEqual({
      kind: "public",
      league: league,
      teams: [{ external_id: "1", name: "A" }],
    });
  });

  it("reads private and unsupported leagues", () => {
    expect(readProbe({ private: true, external_id: "9" })).toEqual({
      kind: "private",
      externalId: "9",
    });
    expect(readProbe({ unsupported: "category league" })).toEqual({
      kind: "unsupported",
      message: "category league",
    });
  });

  it("returns null for anything else rather than guessing", () => {
    expect(readProbe(null)).toBeNull();
    expect(readProbe({})).toBeNull();
    expect(readProbe({ public: true, leagues: [] })).toBeNull();
    expect(readProbe({ public: true, leagues: [{ name: "no id" }] })).toBeNull();
  });
});

describe("readLeagues", () => {
  it("keeps ESPN's team id for preselecting my team", () => {
    const got = readLeagues({
      leagues: [{ external_id: "7", name: "Private", season: 2026, total_teams: 10, team_id: "3" }],
    });
    expect(got?.[0]?.team_id).toBe("3");
  });

  it("is null when a league is malformed", () => {
    expect(readLeagues({ leagues: [{ external_id: 5 }] })).toBeNull();
    expect(readLeagues({ nope: 1 })).toBeNull();
  });
});

describe("isMyTeam", () => {
  const team = { external_id: "3", owner_external_id: "{GUID}" };
  it("uses ESPN's team id when there is one", () => {
    expect(isMyTeam(team, { teamId: "3" })).toBe(true);
    expect(isMyTeam(team, { teamId: "4" })).toBe(false);
  });
  it("falls back to the owner id (Sleeper)", () => {
    expect(isMyTeam(team, { ownerId: "{GUID}" })).toBe(true);
    expect(isMyTeam(team, { ownerId: "x" })).toBe(false);
    expect(isMyTeam(team, {})).toBe(false);
  });
});

describe("copy", () => {
  it("promises read-only use and a way to delete", () => {
    expect(COOKIE_CONSENT).toMatch(/never changes anything/);
    expect(COOKIE_CONSENT).toMatch(/delete them/);
  });
  it("links back to the cookie step", () => {
    expect(espnConnectPath()).toBe("/onboarding?platform=espn&cookies=1");
  });
});
