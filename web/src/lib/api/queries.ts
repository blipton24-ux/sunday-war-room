"use client";

/**
 * Data hooks for client components. Every call goes to this origin's /api/v1 pass-through
 * (ADR-036), so the browser never holds an API token.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createApiClient, unwrap, type Schemas } from "./client";

// Relative base URL: requests go to the same origin that served the page.
export const browserApi = createApiClient({ baseUrl: "" });

export const keys = {
  me: ["me"] as const,
  leagues: ["leagues"] as const,
  teams: (leagueId: number) => ["teams", leagueId] as const,
  matchup: (leagueId: number, week: number) => ["matchup", leagueId, week] as const,
  lineup: (leagueId: number, week: number) => ["lineup", leagueId, week] as const,
  accuracy: (leagueId: number) => ["accuracy", leagueId] as const,
  player: (playerId: number, leagueId: number, week: number) =>
    ["player", playerId, leagueId, week] as const,
  job: (jobId: string) => ["job", jobId] as const,
  waivers: (leagueId: number, horizon: WaiverHorizon) => ["waivers", leagueId, horizon] as const,
  tradeRosters: (leagueId: number) => ["trade-rosters", leagueId] as const,
  tradeIdeas: (leagueId: number, maxLoss: number) => ["trade-ideas", leagueId, maxLoss] as const,
};

export function useTradeRosters(leagueId: number | null) {
  return useQuery({
    queryKey: keys.tradeRosters(leagueId ?? 0),
    enabled: leagueId != null,
    queryFn: () =>
      unwrap(
        browserApi.GET("/api/v1/leagues/{league_id}/trades/rosters", {
          params: { path: { league_id: leagueId! } },
        }),
      ),
  });
}

export function useTradeIdeas(leagueId: number | null, maxLoss: number) {
  return useQuery({
    queryKey: keys.tradeIdeas(leagueId ?? 0, maxLoss),
    enabled: leagueId != null,
    placeholderData: (previous) => previous, // keep the list on screen while the slider moves
    queryFn: () =>
      unwrap(
        browserApi.GET("/api/v1/leagues/{league_id}/trades/suggestions", {
          params: { path: { league_id: leagueId! }, query: { max_loss: maxLoss } },
        }),
      ),
  });
}

export function useEvaluateTrade(leagueId: number | null) {
  return useMutation({
    mutationFn: (body: Schemas["TradeEvaluateIn"]) =>
      unwrap(
        browserApi.POST("/api/v1/leagues/{league_id}/trades/evaluate", {
          params: { path: { league_id: leagueId! } },
          body,
        }),
      ),
  });
}

export type WaiverHorizon = "ros" | "week";

export function useWaivers(leagueId: number | null, horizon: WaiverHorizon) {
  return useQuery({
    queryKey: keys.waivers(leagueId ?? 0, horizon),
    enabled: leagueId != null,
    queryFn: () =>
      unwrap(
        browserApi.GET("/api/v1/leagues/{league_id}/waivers", {
          params: { path: { league_id: leagueId! }, query: { horizon } },
        }),
      ),
  });
}

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: () => unwrap(browserApi.GET("/api/v1/me")),
  });
}

export function useLeagues() {
  return useQuery({
    queryKey: keys.leagues,
    queryFn: () => unwrap(browserApi.GET("/api/v1/leagues")),
    // Poll while any league is syncing so "syncing…" turns into fresh data on its own.
    refetchInterval: (q) =>
      q.state.data?.some((l) => l.sync_status === "queued" || l.sync_status === "running")
        ? 2000
        : false,
  });
}

export function useTeams(leagueId: number | null) {
  return useQuery({
    queryKey: keys.teams(leagueId ?? 0),
    enabled: leagueId != null,
    queryFn: () =>
      unwrap(
        browserApi.GET("/api/v1/leagues/{league_id}/teams", {
          params: { path: { league_id: leagueId! } },
        }),
      ),
  });
}

/** While a game in the matchup is live, re-fetch every 45 s (ADR-045); otherwise never. */
export const LIVE_REFETCH_MS = 45_000;

export function useMatchup(leagueId: number | null, week: number | null) {
  return useQuery({
    queryKey: keys.matchup(leagueId ?? 0, week ?? 0),
    enabled: leagueId != null && week != null,
    refetchInterval: (q) => (q.state.data?.live ? LIVE_REFETCH_MS : false),
    refetchIntervalInBackground: false, // a hidden tab doesn't poll
    queryFn: () =>
      unwrap(
        browserApi.GET("/api/v1/leagues/{league_id}/matchup", {
          params: { path: { league_id: leagueId! }, query: { week: week! } },
        }),
      ),
  });
}

export function useLineup(leagueId: number | null, week: number | null) {
  return useQuery({
    queryKey: keys.lineup(leagueId ?? 0, week ?? 0),
    enabled: leagueId != null && week != null,
    queryFn: () =>
      unwrap(
        browserApi.GET("/api/v1/leagues/{league_id}/lineup", {
          params: { path: { league_id: leagueId! }, query: { week: week! } },
        }),
      ),
  });
}

export function useAccuracy(leagueId: number | null) {
  return useQuery({
    queryKey: keys.accuracy(leagueId ?? 0),
    enabled: leagueId != null,
    queryFn: () =>
      unwrap(
        browserApi.GET("/api/v1/leagues/{league_id}/accuracy", {
          params: { path: { league_id: leagueId! } },
        }),
      ),
  });
}

export function usePlayerProjection(
  playerId: number,
  leagueId: number | null,
  week: number | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: keys.player(playerId, leagueId ?? 0, week ?? 0),
    enabled: enabled && leagueId != null && week != null,
    staleTime: 5 * 60_000,
    queryFn: () =>
      unwrap(
        browserApi.GET("/api/v1/players/{player_id}/projection", {
          params: { path: { player_id: playerId }, query: { league_id: leagueId!, week: week! } },
        }),
      ),
  });
}

/** Polls a background job until it is done or failed. */
export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: keys.job(jobId ?? ""),
    enabled: jobId != null,
    queryFn: () =>
      unwrap(browserApi.GET("/api/v1/jobs/{job_id}", { params: { path: { job_id: jobId! } } })),
    refetchInterval: (q) =>
      q.state.data?.status === "done" || q.state.data?.status === "failed" ? false : 1000,
  });
}

export function isFinished(job: Schemas["JobOut"] | undefined): boolean {
  return job?.status === "done" || job?.status === "failed";
}

// --------------------------------------------------------------------------- mutations
export function useConnectSleeper() {
  return useMutation({
    mutationFn: (username: string) =>
      unwrap(browserApi.POST("/api/v1/platforms/sleeper/connect", { body: { username } })),
  });
}

export function useFollowLeague() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (externalId: string) =>
      unwrap(
        browserApi.POST("/api/v1/leagues", {
          body: { platform: "sleeper", external_id: externalId },
        }),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.leagues }),
  });
}

export function useSetMyTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leagueId, teamId }: { leagueId: number; teamId: number }) =>
      unwrap(
        browserApi.PATCH("/api/v1/leagues/{league_id}", {
          params: { path: { league_id: leagueId } },
          body: { my_team_id: teamId },
        }),
      ),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useUnfollowLeague() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (leagueId: number) =>
      unwrap(
        browserApi.DELETE("/api/v1/leagues/{league_id}", {
          params: { path: { league_id: leagueId } },
        }),
      ),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useRefreshLeague() {
  return useMutation({
    mutationFn: (leagueId: number) =>
      unwrap(
        browserApi.POST("/api/v1/leagues/{league_id}/refresh", {
          params: { path: { league_id: leagueId } },
        }),
      ),
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: () => unwrap(browserApi.DELETE("/api/v1/me")),
  });
}
