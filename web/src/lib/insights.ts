/**
 * Things the screens show that are derived from API data on the client: Heads-up alerts,
 * the matchup status chip, top performers, boom/bust labels. Pure functions (unit tested),
 * so every number on screen traces back to an API field.
 */
import type { Schemas } from "@/lib/api/client";

import { f1, lastName } from "./format";
import { slotLabel } from "./positions";

type Line = Schemas["PlayerLine"];
type Lineup = Schemas["LineupOut"];

/** What the player row's big number shows. */
export function headlinePoints(p: Line): { main: string; sub: string } {
  if (p.game_status === "bye") return { main: "--", sub: "on bye" };
  if (p.actual_points != null) {
    return { main: f1(p.actual_points), sub: p.projection ? `proj ${f1(p.projection.points)}` : "final" };
  }
  if (p.game_status === "in_progress" && p.live_points != null) {
    // Live (P2): points so far, and where he's heading with the time left.
    const left = (p.projection?.points ?? 0) * (p.remaining_fraction ?? 1);
    return { main: f1(p.live_points), sub: `heading to ${f1(p.live_points + left)}` };
  }
  if (!p.projection) return { main: "--", sub: "no projection" };
  return { main: f1(p.projection.points), sub: `${f1(p.projection.p10)}–${f1(p.projection.p90)}` };
}

/** The number used for sorting and totals: actual if final, else the projection. */
export function bestPoints(p: Line): number {
  if (p.actual_points != null) return p.actual_points;
  if (p.game_status === "in_progress" && p.live_points != null) {
    return p.live_points + (p.projection?.points ?? 0) * (p.remaining_fraction ?? 1);
  }
  return p.projection?.points ?? 0;
}

export type Vibe = "boom" | "bust" | null;

/** Boom: final score at or above the 90th percentile. Bust: at or below the 10th. */
export function vibe(p: Line): Vibe {
  if (p.actual_points == null || !p.projection) return null;
  if (p.actual_points >= p.projection.p90 && p.projection.p90 > 0) return "boom";
  if (p.actual_points <= p.projection.p10) return "bust";
  return null;
}

/** "Boom or bust" when the 80% range is wider than 1.2x the projection (mockup rule). */
export function rangeStyle(projection: Schemas["ProjectionOut"]): "steady" | "volatile" {
  if (projection.points <= 0) return "steady";
  return (projection.p90 - projection.p10) / projection.points > 1.2 ? "volatile" : "steady";
}

export interface Status {
  emoji: string;
  label: string;
  tone: "good" | "ok" | "bad";
}

/** The matchup status chip, from my win chance. */
export function matchupStatus(winProbability: number): Status {
  if (winProbability >= 0.75) return { emoji: "😎", label: "Cruising", tone: "good" };
  if (winProbability >= 0.55) return { emoji: "🙂", label: "Ahead", tone: "good" };
  if (winProbability > 0.45) return { emoji: "🤞", label: "Coin flip", tone: "ok" };
  if (winProbability > 0.25) return { emoji: "😬", label: "Behind", tone: "bad" };
  return { emoji: "🆘", label: "Long shot", tone: "bad" };
}

export function winTone(p: number): "good" | "ok" | "bad" {
  return p >= 0.6 ? "good" : p >= 0.4 ? "ok" : "bad";
}

export function topPerformers(lines: readonly Line[], n = 6): Line[] {
  return lines
    .filter((p) => p.game_status !== "bye" && (p.actual_points != null || p.projection))
    .toSorted((a, b) => bestPoints(b) - bestPoints(a))
    .slice(0, n);
}

/** Starters whose games aren't final yet. */
export function stillToPlay(lines: readonly Line[]): number {
  return lines.filter((p) => p.game_status === "upcoming" || p.game_status === "in_progress").length;
}

export interface Alert {
  key: string;
  player: Line;
  title: string;
  detail: string;
  tone: "bad" | "warn" | "good";
}

const OUT = new Set(["out", "ir", "pup", "sus", "na", "cov"]);

/** The Home screen's Heads-up list: problems first (bye, out), then doubts, then booms. */
export function headsUp(lineup: Lineup): Alert[] {
  const swapIn = new Map(lineup.swaps.map((s) => [s.player_out?.player_id, s]));
  const alerts: Alert[] = [];
  for (const p of lineup.starters) {
    const slot = slotLabel(p.slot);
    const fix = swapIn.get(p.player_id);
    const fixText = fix
      ? `${fix.player_in.name} (${f1(fix.player_in.projection?.points)} proj) is your best bench option.`
      : "";
    const status = (p.injury_status ?? "").toLowerCase();
    if (p.game_status === "bye") {
      alerts.push({ key: `bye-${p.player_id}`, player: p, tone: "bad",
        title: `${p.name} is on bye in your ${slot}`, detail: fixText || "No bench player can fill it." });
    } else if (OUT.has(status) && p.game_status === "upcoming") {
      alerts.push({ key: `out-${p.player_id}`, player: p, tone: "bad",
        title: `${p.name} is listed ${p.injury_status}`, detail: fixText || "Projected for 0 points." });
    } else if ((status === "questionable" || status === "doubtful") && p.game_status === "upcoming") {
      alerts.push({ key: `q-${p.player_id}`, player: p, tone: "warn",
        title: `${p.name} is ${status}`, detail: "The projection already includes the discount." });
    } else if (vibe(p) === "boom") {
      alerts.push({ key: `boom-${p.player_id}`, player: p, tone: "good",
        title: `${lastName(p.name)} boomed`,
        detail: `${f1(p.actual_points)} points, above the ${f1(p.projection?.p90)} ceiling.` });
    }
  } // prettier-ignore
  const order = { bad: 0, warn: 1, good: 2 } as const;
  return alerts.toSorted((a, b) => order[a.tone] - order[b.tone]);
}
