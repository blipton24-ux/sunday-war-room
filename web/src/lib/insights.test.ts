import { describe, expect, it } from "vitest";

import type { Schemas } from "@/lib/api/client";

import { f1, initials, lastName, timeAgo } from "./format";
import { headlinePoints, headsUp, matchupStatus, topPerformers, vibe } from "./insights";
import { tint } from "./teams";

type Line = Schemas["PlayerLine"];

function line(over: Partial<Line> & Pick<Line, "player_id" | "name">): Line {
  return {
    position: "WR",
    nfl_team: "DET",
    headshot_url: null,
    slot: "WR",
    injury_status: null,
    opponent: "@GB",
    kickoff_at: null,
    game_status: "upcoming",
    projection: {
      points: 12,
      p10: 5,
      p50: 11,
      p90: 21,
      frozen: false,
      computed_at: "2026-11-05T12:00:00Z",
      model_version: "1.0.0",
    },
    actual_points: null,
    ...over,
  };
}

function lineup(starters: Line[], swaps: Schemas["SwapOut"][] = []): Schemas["LineupOut"] {
  return {
    league_id: 1, week: 10, as_of: null, model_version: "1.0.0", starters, bench: [], optimal: [],
    swaps, current_points: 0, optimal_points: 0,
    win_probability_current: null, win_probability_optimal: null,
  }; // prettier-ignore
}

describe("format", () => {
  it("formats points, initials, names and ages", () => {
    expect(f1(12.345)).toBe("12.3");
    expect(f1(null)).toBe("--");
    expect(initials("Amon-Ra St. Brown")).toBe("AB");
    expect(initials("Steelers")).toBe("ST");
    expect(lastName("Kenneth Walker III")).toBe("Walker");
    expect(lastName("Jauan Jennings")).toBe("Jennings");
    const now = new Date("2026-11-09T12:00:00Z");
    expect(timeAgo("2026-11-09T11:57:00Z", now)).toBe("3m ago");
    expect(timeAgo("2026-11-09T09:00:00Z", now)).toBe("3h ago");
    expect(timeAgo(null, now)).toBe("never");
    expect(tint("#2F6BDB", 0.25)).toBe("#2F6BDB40");
  });
});

describe("player numbers", () => {
  it("shows the projection range before kickoff and the actual after", () => {
    expect(headlinePoints(line({ player_id: 1, name: "A" }))).toEqual({ main: "12.0", sub: "5.0–21.0" });
    expect(headlinePoints(line({ player_id: 1, name: "A", game_status: "final", actual_points: 26.3 })))
      .toEqual({ main: "26.3", sub: "proj 12.0" });
    expect(headlinePoints(line({ player_id: 1, name: "A", game_status: "bye", projection: null })).sub)
      .toBe("on bye");
  }); // prettier-ignore

  it("labels booms and busts only for finished games", () => {
    expect(vibe(line({ player_id: 1, name: "A" }))).toBeNull();
    expect(vibe(line({ player_id: 1, name: "A", game_status: "final", actual_points: 25 }))).toBe("boom");
    expect(vibe(line({ player_id: 1, name: "A", game_status: "final", actual_points: 3 }))).toBe("bust");
  });
});

describe("matchupStatus", () => {
  it.each([
    [0.9, "Cruising"],
    [0.6, "Ahead"],
    [0.5, "Coin flip"],
    [0.3, "Behind"],
    [0.1, "Long shot"],
  ])("%f -> %s", (p, label) => {
    expect(matchupStatus(p).label).toBe(label);
  });
});

describe("headsUp", () => {
  it("puts problems first and names the best replacement", () => {
    const bye = line({ player_id: 1, name: "Jordan Addison", slot: "FLEX", game_status: "bye", projection: null });
    const q = line({ player_id: 2, name: "Isiah Pacheco", position: "RB", injury_status: "Questionable" });
    const boom = line({ player_id: 3, name: "Amon-Ra St. Brown", game_status: "final", actual_points: 26.3 });
    const jennings = line({ player_id: 9, name: "Jauan Jennings", slot: "BN" });
    const alerts = headsUp(lineup([boom, q, bye], [{ slot: "FLEX", player_in: jennings, player_out: bye, gain: 12 }]));
    expect(alerts.map((a) => a.key)).toEqual(["bye-1", "q-2", "boom-3"]);
    expect(alerts[0]!.title).toBe("Jordan Addison is on bye in your FLEX");
    expect(alerts[0]!.detail).toContain("Jauan Jennings (12.0 proj)");
    expect(alerts[2]!.title).toBe("Brown boomed");
  }); // prettier-ignore

  it("says nothing about a healthy, upcoming lineup", () => {
    expect(headsUp(lineup([line({ player_id: 1, name: "A" })]))).toEqual([]);
  });
});

describe("topPerformers", () => {
  it("ranks by actual points when final, else projection, and skips byes", () => {
    const players = [
      line({ player_id: 1, name: "A", projection: { ...line({ player_id: 0, name: "" }).projection!, points: 20 } }),
      line({ player_id: 2, name: "B", game_status: "final", actual_points: 30 }),
      line({ player_id: 3, name: "C", game_status: "bye", projection: null }),
    ];
    expect(topPerformers(players).map((p) => p.player_id)).toEqual([2, 1]);
  }); // prettier-ignore
});
