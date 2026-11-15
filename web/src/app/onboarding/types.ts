import type { FoundLeague } from "@/lib/espn";

export type Platform = "sleeper" | "espn";

/** Leagues a connect step found, ready to follow. */
export interface Offer {
  platform: Platform;
  /** What was connected, for the "Found N leagues for ___" line (a Sleeper username). */
  label: string | null;
  season: number;
  leagues: FoundLeague[];
  /** Sleeper: the connected user's id, to preselect the team they own. */
  ownerId?: string | null;
}

/** A followed league: its id, its first-sync job, and how to preselect the user's team. */
export interface Followed {
  external: FoundLeague;
  platform: Platform;
  leagueId: number;
  jobId: string;
  ownerId?: string | null;
}

export type Stage = "platform" | "sleeper" | "espn-link" | "espn-cookies";
