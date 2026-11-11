/**
 * Everything the ESPN connect screens know that isn't React: reading the worker's job results,
 * recognising the browser, and the plain-language steps for copying the two ESPN cookies
 * (ADR-051). Kept free of imports so it can be unit tested.
 */

export interface FoundLeague {
  external_id: string;
  name: string;
  season: number;
  total_teams: number | null;
  /** ESPN's id for the user's own team in this league (from the cookie connect). */
  team_id?: string | null;
}

export interface PublicTeam {
  external_id: string;
  name: string;
}

export type ProbeOutcome =
  | { kind: "public"; league: FoundLeague; teams: PublicTeam[] }
  | { kind: "private"; externalId: string }
  | { kind: "unsupported"; message: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** The leagues a connect or probe job found, or null if the result isn't shaped like one. */
export function readLeagues(result: unknown): FoundLeague[] | null {
  if (!isRecord(result) || !Array.isArray(result.leagues)) return null;
  const out: FoundLeague[] = [];
  for (const raw of result.leagues) {
    if (!isRecord(raw) || typeof raw.external_id !== "string" || typeof raw.name !== "string") {
      return null;
    }
    out.push({
      external_id: raw.external_id,
      name: raw.name,
      season: typeof raw.season === "number" ? raw.season : 0,
      total_teams: typeof raw.total_teams === "number" ? raw.total_teams : null,
      team_id: typeof raw.team_id === "string" ? raw.team_id : null,
    });
  }
  return out;
}

/** What a "is this league public?" job found out. */
export function readProbe(result: unknown): ProbeOutcome | null {
  if (!isRecord(result)) return null;
  if (typeof result.unsupported === "string") {
    return { kind: "unsupported", message: result.unsupported };
  }
  if (result.private === true) {
    return { kind: "private", externalId: String(result.external_id ?? "") };
  }
  const leagues = readLeagues(result);
  if (result.public === true && leagues && leagues[0]) {
    const teams = Array.isArray(result.teams)
      ? result.teams.filter(isRecord).map((t) => ({
          external_id: String(t.external_id),
          name: String(t.name),
        }))
      : [];
    return { kind: "public", league: leagues[0], teams };
  }
  return null;
}

export type BrowserKind = "chrome" | "edge" | "firefox" | "safari" | "other";

export function detectBrowser(userAgent: string): BrowserKind {
  if (/Edg(e|A|iOS)?\//.test(userAgent)) return "edge";
  if (/Firefox\/|FxiOS\//.test(userAgent)) return "firefox";
  if (/Chrome\/|CriOS\//.test(userAgent)) return "chrome";
  if (/Safari\//.test(userAgent)) return "safari";
  return "other";
}

export const BROWSER_NAMES: Record<BrowserKind, string> = {
  chrome: "Chrome",
  edge: "Edge",
  firefox: "Firefox",
  safari: "Safari",
  other: "your browser",
};

/** A phone or tablet held in the hand: copying cookies isn't possible there. */
export function isPhoneLike(coarsePointer: boolean, viewportWidth: number): boolean {
  return coarsePointer && viewportWidth < 820;
}

/** The steps for copying `espn_s2` and `SWID`, for one browser. Plain words, no jargon. */
export function cookieSteps(browser: BrowserKind): string[] {
  const open = "On a computer, open fantasy.espn.com in a new tab and make sure you're signed in.";
  const copy =
    "Double-click the Value next to espn_s2 and copy it (Ctrl+C, or Cmd+C on a Mac). Paste it into the first box here. Do the same for SWID in the second box.";
  switch (browser) {
    case "firefox":
      return [
        open,
        "Press F12 to open the developer tools, then click the Storage tab.",
        "On the left, open Cookies and click https://www.espn.com.",
        "In the list, find the rows named espn_s2 and SWID.",
        copy,
      ];
    case "safari":
      return [
        open,
        "Turn on the Develop menu once: Safari > Settings > Advanced > Show features for web developers.",
        "Choose Develop > Show Web Inspector, then click the Storage tab.",
        "On the left, open Cookies and click www.espn.com.",
        "Find the rows named espn_s2 and SWID.",
        copy,
      ];
    default: // Chrome, Edge and other Chromium browsers share the same developer tools
      return [
        open,
        "Press F12 to open the developer tools, then click the Application tab (it may be behind the » arrows).",
        "On the left, under Storage, open Cookies and click https://www.espn.com.",
        "In the list, find the rows named espn_s2 and SWID.",
        copy,
      ];
  }
}

/** Shown before any cookie is pasted: what we keep, why, and how to undo it. */
export const COOKIE_CONSENT =
  "These two values work like a password for your ESPN fantasy account. Sunday War Room saves them encrypted, uses them only to read your leagues, and never changes anything on ESPN. They stop working if you sign out of ESPN or change your ESPN password. You can delete them any time in Settings.";

/** The link people are emailed to finish connecting on a computer. */
export function espnConnectPath(): string {
  return "/onboarding?platform=espn&cookies=1";
}

/** Does this team belong to the user? ESPN tells us by team id; Sleeper by owner id. */
export function isMyTeam(
  team: { external_id: string; owner_external_id: string | null },
  mine: { teamId?: string | null; ownerId?: string | null },
): boolean {
  if (mine.teamId != null) return team.external_id === mine.teamId;
  if (mine.ownerId != null) return team.owner_external_id === mine.ownerId;
  return false;
}
